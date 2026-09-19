"""
BMTC Live Bus Telemetry & Real-Time VTMS Tracker.
Connects directly to BMTC's Vehicle Tracking and Monitoring System (VTMS)
to provide real-time bus locations, approaching counts, live GPS coordinates,
and estimated arrival times. Supports multi-route aggregation and route normalization.
"""

import json
import math
import re
import ssl
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple, Union

# Module-level caches
# Caches route_term.upper() -> routeparentid (permanent for runtime)
_ROUTE_ID_CACHE: Dict[str, int] = {}

# Caches routeparentid -> (timestamp, data) (TTL = 15 seconds)
_TELEMETRY_CACHE: Dict[int, Tuple[float, Dict[str, Any]]] = {}
_CACHE_TTL_SECONDS = 15.0

# SSL context for BMTC government endpoints
_SSL_CTX = ssl.create_default_context()
_SSL_CTX.check_hostname = False
_SSL_CTX.verify_mode = ssl.CERT_NONE

_HEADERS = {
    "Content-Type": "application/json",
    "lan": "en",
    "deviceType": "WEB",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko)",
    "Origin": "https://bmtckiosk.karnataka.gov.in",
    "Referer": "https://bmtckiosk.karnataka.gov.in/",
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Haversine distance between two coordinates in kilometers."""
    r = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlon / 2.0) ** 2
    )
    return r * 2.0 * math.asin(math.sqrt(a))


def clean_route_candidates(route_str: str) -> List[str]:
    """
    Normalizes BMTC GTFS route strings into clean search terms for VTMS.
    Handles prefixes ('O EXP-', 'V-', 'MF-'), direction tags ('_UP', ' DN'),
    and hyphen variations ('365-P' <-> '365P', '356-KA' <-> '356KA').
    """
    s = route_str.strip().upper()
    s_clean = re.sub(r"^(O\s*EXP[\s-]*|EXP[\s-]*|O\s*|V-)", "", s).strip()
    s_clean = re.sub(r"(_UP|_DN|\s+UP|\s+DN)$", "", s_clean).strip()

    parts = s_clean.split()
    first_token = parts[0] if parts else s_clean

    candidates = [s, s_clean, first_token]
    for base in [first_token, s_clean]:
        if "-" in base:
            candidates.append(base.replace("-", ""))
        else:
            m = re.match(r"^([A-Z0-9]+?)([A-Z]+)$", base)
            if m:
                candidates.append(f"{m.group(1)}-{m.group(2)}")

    seen = set()
    res = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            res.append(c)
    return res


def resolve_route_parent_id(route_no: str, timeout: float = 2.0) -> Optional[int]:
    """
    Resolves route string (e.g. '365-P', '356-M', 'O EXP-356KA') to BMTC's internal routeparentid.
    Results are cached in memory.
    """
    clean_no = route_no.strip().upper()
    if clean_no in _ROUTE_ID_CACHE:
        return _ROUTE_ID_CACHE[clean_no]

    candidates = clean_route_candidates(clean_no)

    for term in candidates[:2]:
        try:
            url = "https://bmtcmobileapi.karnataka.gov.in/WebAPI/SearchRoute_v2"
            payload = json.dumps({"routetext": term}).encode("utf-8")
            req = urllib.request.Request(url, data=payload, headers=_HEADERS)
            with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                items = data.get("data", [])
                matched = None
                for it in items:
                    rno = it.get("routeno", "").strip().upper()
                    if rno in candidates or rno == term or rno == clean_no:
                        matched = it
                        break
                if not matched and items:
                    matched = items[0]

                if matched and "routeparentid" in matched:
                    rid = int(matched["routeparentid"])
                    _ROUTE_ID_CACHE[clean_no] = rid
                    return rid
        except Exception:
            continue

    return None


def fetch_route_telemetry_raw(route_id: int, timeout: float = 2.5) -> Optional[Dict[str, Any]]:
    """
    Fetches raw route details & live vehicle mapData from BMTC API.
    Caches responses with a short TTL (15s).
    """
    now = time.time()
    if route_id in _TELEMETRY_CACHE:
        ts, cached_data = _TELEMETRY_CACHE[route_id]
        if now - ts < _CACHE_TTL_SECONDS:
            return cached_data

    try:
        url = "https://bmtcmobileapi.karnataka.gov.in/WebAPI/SearchByRouteDetails_v4"
        payload = json.dumps({"routeid": route_id, "servicetypeid": 0}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers=_HEADERS)
        with urllib.request.urlopen(req, context=_SSL_CTX, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            _TELEMETRY_CACHE[route_id] = (now, data)
            return data
    except Exception:
        if route_id in _TELEMETRY_CACHE:
            return _TELEMETRY_CACHE[route_id][1]
        return None


def get_single_route_telemetry(
    route_no: str,
    orig_lat: float,
    orig_lon: float,
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Fetches real-time bus tracking for a single route.
    Determines route direction (UP vs DOWN), locates active buses,
    detects terminal turnaround vehicles, and computes arrival ETAs.
    """
    route_id = resolve_route_parent_id(route_no)
    if not route_id:
        return {
            "live": False,
            "route": route_no,
            "reason": "Route identifier not indexed in live tracking system",
            "active_buses_total": 0,
            "approaching_count": 0,
            "nearest_bus": None,
            "approaching_buses": [],
            "all_active_buses": [],
        }

    raw = fetch_route_telemetry_raw(route_id)
    if not raw or not isinstance(raw, dict):
        return {
            "live": False,
            "route": route_no,
            "reason": "Live telemetry feed temporarily unreachable",
            "active_buses_total": 0,
            "approaching_count": 0,
            "nearest_bus": None,
            "approaching_buses": [],
            "all_active_buses": [],
        }

    up_stops = raw.get("up", {}).get("data", []) or []
    down_stops = raw.get("down", {}).get("data", []) or []
    up_buses = raw.get("up", {}).get("mapData", []) or []
    down_buses = raw.get("down", {}).get("mapData", []) or []

    # Helper: find closest stop index and distance
    def find_closest_stop(stops: List[Dict[str, Any]], lat: float, lon: float) -> Tuple[int, float]:
        best_idx = -1
        min_d = float("inf")
        for i, s in enumerate(stops):
            slat = s.get("centerlat")
            slon = s.get("centerlong")
            if slat is None or slon is None:
                continue
            d = _haversine(lat, lon, slat, slon)
            if d < min_d:
                min_d = d
                best_idx = i
        return best_idx, min_d

    # Determine travel direction (UP vs DOWN)
    use_up = True
    if dest_lat is not None and dest_lon is not None:
        up_orig_idx, _ = find_closest_stop(up_stops, orig_lat, orig_lon)
        up_dest_idx, _ = find_closest_stop(up_stops, dest_lat, dest_lon)
        dn_orig_idx, _ = find_closest_stop(down_stops, orig_lat, orig_lon)
        dn_dest_idx, _ = find_closest_stop(down_stops, dest_lat, dest_lon)

        up_valid = up_orig_idx != -1 and up_dest_idx != -1 and up_orig_idx < up_dest_idx
        dn_valid = dn_orig_idx != -1 and dn_dest_idx != -1 and dn_orig_idx < dn_dest_idx

        if dn_valid and not up_valid:
            use_up = False
        elif up_valid and not dn_valid:
            use_up = True
        elif dn_valid and up_valid:
            _, up_d_orig = find_closest_stop(up_stops, orig_lat, orig_lon)
            _, dn_d_orig = find_closest_stop(down_stops, orig_lat, orig_lon)
            use_up = up_d_orig <= dn_d_orig
    else:
        _, up_d = find_closest_stop(up_stops, orig_lat, orig_lon)
        _, dn_d = find_closest_stop(down_stops, orig_lat, orig_lon)
        use_up = up_d <= dn_d

    chosen_stops = up_stops if use_up else down_stops
    chosen_buses = up_buses if use_up else down_buses
    opposite_buses = down_buses if use_up else up_buses
    direction_label = "UP" if use_up else "DOWN"

    user_stop_idx, _ = find_closest_stop(chosen_stops, orig_lat, orig_lon)

    approaching_buses = []
    all_buses = []

    for b in chosen_buses:
        b_lat = b.get("centerlat")
        b_lon = b.get("centerlong")
        if b_lat is None or b_lon is None:
            continue

        v_num = b.get("vehiclenumber") or f"Bus #{b.get('vehicleid', 'BMTC')}"
        s_type = b.get("servicetype") or "Ordinary"
        heading = b.get("heading")
        last_refresh = b.get("lastrefreshon") or ""

        # Bus position relative to stops
        bus_stop_idx, _ = find_closest_stop(chosen_stops, b_lat, b_lon)
        dist_km = _haversine(b_lat, b_lon, orig_lat, orig_lon)
        eta_mins = max(1, round((dist_km / 15.0) * 60))

        bus_obj = {
            "route": route_no,
            "vehicle": v_num,
            "vehicle_id": b.get("vehicleid"),
            "type": s_type,
            "lat": round(b_lat, 5),
            "lon": round(b_lon, 5),
            "heading": heading,
            "dist_km": round(dist_km, 2),
            "eta_mins": eta_mins,
            "last_updated": last_refresh,
            "is_terminal_inbound": False,
        }
        all_buses.append(bus_obj)

        # Bus is approaching if bus_stop_idx <= user_stop_idx or it is within 350m
        if user_stop_idx != -1 and bus_stop_idx != -1:
            stops_away = user_stop_idx - bus_stop_idx
            if stops_away >= 0 or dist_km <= 0.35:
                bus_obj_approaching = dict(bus_obj)
                bus_obj_approaching["stops_away"] = max(0, stops_away)
                bus_obj_approaching["is_at_stop"] = dist_km <= 0.35 or stops_away == 0
                approaching_buses.append(bus_obj_approaching)

    # Terminal turnaround check: if user is at the starting terminal (e.g. Anekal or KBS),
    # buses arriving in the opposite direction within 10 km are preparing to turn around.
    is_at_terminal = user_stop_idx <= 2
    if is_at_terminal:
        for ob in opposite_buses:
            ob_lat = ob.get("centerlat")
            ob_lon = ob.get("centerlong")
            if ob_lat is None or ob_lon is None:
                continue

            dist_term = _haversine(ob_lat, ob_lon, orig_lat, orig_lon)
            if dist_term <= 10.0:
                v_num = ob.get("vehiclenumber") or f"Bus #{ob.get('vehicleid', 'BMTC')}"
                s_type = ob.get("servicetype") or "Ordinary"
                eta_term = max(2, round((dist_term / 15.0) * 60))

                inbound_bus = {
                    "route": route_no,
                    "vehicle": v_num,
                    "vehicle_id": ob.get("vehicleid"),
                    "type": s_type,
                    "lat": round(ob_lat, 5),
                    "lon": round(ob_lon, 5),
                    "heading": ob.get("heading"),
                    "dist_km": round(dist_term, 2),
                    "eta_mins": eta_term,
                    "last_updated": ob.get("lastrefreshon") or "",
                    "stops_away": 1,
                    "is_at_stop": dist_term <= 0.35,
                    "is_terminal_inbound": True,
                }
                # Avoid duplicates
                if not any(x["vehicle"] == v_num for x in approaching_buses):
                    approaching_buses.append(inbound_bus)
                if not any(x["vehicle"] == v_num for x in all_buses):
                    all_buses.append(inbound_bus)

    # Sort approaching buses by distance to the user
    approaching_buses.sort(key=lambda x: x["dist_km"])
    nearest = approaching_buses[0] if approaching_buses else None

    # Closest active bus anywhere in fleet for fallback visibility
    nearest_active = None
    if all_buses:
        nearest_active = min(all_buses, key=lambda x: x["dist_km"])

    return {
        "live": True,
        "route": route_no,
        "direction": direction_label,
        "active_buses_total": len(all_buses),
        "approaching_count": len(approaching_buses),
        "nearest_bus": nearest,
        "nearest_active_bus": nearest_active,
        "approaching_buses": approaching_buses[:6],
        "all_active_buses": all_buses,
    }


def get_live_route_telemetry(
    route_no: Union[str, List[str]],
    orig_lat: float,
    orig_lon: float,
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Main entry point for real-time bus tracking.
    Supports single route string or multiple comma-separated routes / list.
    Aggregates approaching buses across candidate routes and picks the earliest arrival.
    """
    # Parse route candidates
    if isinstance(route_no, str):
        raw_routes = [r.strip() for r in route_no.split(",") if r.strip()]
    elif isinstance(route_no, list):
        raw_routes = [str(r).strip() for r in route_no if str(r).strip()]
    else:
        raw_routes = [str(route_no)]

    # Deduplicate preserving order (limit to top 5 routes to prevent rate limit)
    seen = set()
    routes_to_query = []
    for r in raw_routes:
        if r not in seen:
            seen.add(r)
            routes_to_query.append(r)
    routes_to_query = routes_to_query[:5]

    if not routes_to_query:
        return {
            "live": False,
            "route": "",
            "reason": "No valid route number provided",
            "active_buses_total": 0,
            "approaching_count": 0,
            "nearest_bus": None,
            "approaching_buses": [],
            "all_active_buses": [],
        }

    # Query all candidate routes
    results = []
    for r in routes_to_query:
        res = get_single_route_telemetry(
            route_no=r,
            orig_lat=orig_lat,
            orig_lon=orig_lon,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
        )
        if res.get("live"):
            results.append(res)

    if not results:
        # Fallback to single failure response
        first_route = routes_to_query[0]
        return {
            "live": False,
            "route": first_route,
            "routes_queried": routes_to_query,
            "reason": "Live telemetry feed quiet or unindexed for these routes",
            "active_buses_total": 0,
            "approaching_count": 0,
            "nearest_bus": None,
            "approaching_buses": [],
            "all_active_buses": [],
        }

    # Merge approaching buses and active buses across all routes
    merged_approaching: List[Dict[str, Any]] = []
    merged_all: List[Dict[str, Any]] = []
    seen_vehicles = set()

    for r_res in results:
        for b in r_res.get("approaching_buses", []):
            v_key = b.get("vehicle") or b.get("vehicle_id")
            if v_key not in seen_vehicles:
                seen_vehicles.add(v_key)
                merged_approaching.append(b)

    seen_all_vehicles = set()
    for r_res in results:
        for b in r_res.get("all_active_buses", []):
            v_key = b.get("vehicle") or b.get("vehicle_id")
            if v_key not in seen_all_vehicles:
                seen_all_vehicles.add(v_key)
                merged_all.append(b)

    # Sort merged approaching buses by distance / ETA
    merged_approaching.sort(key=lambda x: x["dist_km"])
    nearest = merged_approaching[0] if merged_approaching else None

    # Closest active bus across fleet
    nearest_active = None
    if merged_all:
        nearest_active = min(merged_all, key=lambda x: x["dist_km"])

    primary_route_label = ", ".join([res["route"] for res in results])

    return {
        "live": True,
        "route": primary_route_label,
        "routes_queried": [res["route"] for res in results],
        "direction": results[0].get("direction", "UP"),
        "active_buses_total": len(merged_all),
        "approaching_count": len(merged_approaching),
        "nearest_bus": nearest,
        "nearest_active_bus": nearest_active,
        "approaching_buses": merged_approaching[:8],
        "all_active_buses": merged_all,
    }
