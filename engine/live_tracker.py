"""
BMTC Live Bus Telemetry & Real-Time VTMS Tracker.
Connects directly to BMTC's Vehicle Tracking and Monitoring System (VTMS)
to provide real-time bus locations, approaching counts, live GPS coordinates,
and estimated arrival times.
"""

import json
import math
import ssl
import time
import urllib.request
from typing import Any, Dict, List, Optional, Tuple

# Module-level caches
# Caches route_no.upper() -> routeparentid (permanent for runtime)
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


def resolve_route_parent_id(route_no: str, timeout: float = 3.5) -> Optional[int]:
    """
    Resolves route string (e.g. '365', '500-D', 'KIA-8') to BMTC's internal routeparentid.
    Results are cached in memory.
    """
    clean_no = route_no.strip().upper()
    if clean_no in _ROUTE_ID_CACHE:
        return _ROUTE_ID_CACHE[clean_no]

    # Handle common prefix variations: e.g. "V-365" -> "365" or "V365"
    search_terms = [clean_no]
    if clean_no.startswith("V-"):
        search_terms.append(clean_no[2:])
    elif clean_no.startswith("V") and len(clean_no) > 1 and clean_no[1].isdigit():
        search_terms.append(clean_no[1:])

    for term in search_terms:
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
                    if rno == term:
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


def fetch_route_telemetry_raw(route_id: int, timeout: float = 4.0) -> Optional[Dict[str, Any]]:
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
        # If fetch fails but we have slightly older cache, return it rather than failing
        if route_id in _TELEMETRY_CACHE:
            return _TELEMETRY_CACHE[route_id][1]
        return None


def get_live_route_telemetry(
    route_no: str,
    orig_lat: float,
    orig_lon: float,
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Main entry point for real-time bus tracking.
    Determines route direction (UP vs DOWN), locates active buses,
    filters buses approaching the user's boarding stop, and computes ETAs.
    """
    route_id = resolve_route_parent_id(route_no)
    if not route_id:
        return {
            "live": False,
            "route": route_no,
            "reason": "Route identifier not indexed in live tracking system",
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

        # Check sequence: orig must be before dest in the chosen direction
        up_valid = up_orig_idx != -1 and up_dest_idx != -1 and up_orig_idx < up_dest_idx
        dn_valid = dn_orig_idx != -1 and dn_dest_idx != -1 and dn_orig_idx < dn_dest_idx

        if dn_valid and not up_valid:
            use_up = False
        elif up_valid and not dn_valid:
            use_up = True
        elif dn_valid and up_valid:
            # Pick whichever direction has stops closer to orig/dest
            _, up_d_orig = find_closest_stop(up_stops, orig_lat, orig_lon)
            _, dn_d_orig = find_closest_stop(down_stops, orig_lat, orig_lon)
            use_up = up_d_orig <= dn_d_orig
    else:
        # If no dest coordinates given, test which direction has orig closer
        _, up_d = find_closest_stop(up_stops, orig_lat, orig_lon)
        _, dn_d = find_closest_stop(down_stops, orig_lat, orig_lon)
        use_up = up_d <= dn_d

    chosen_stops = up_stops if use_up else down_stops
    chosen_buses = up_buses if use_up else down_buses
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

        # Urban bus speed average: ~15 km/h -> 4 min per km
        eta_mins = max(1, round((dist_km / 15.0) * 60))

        bus_obj = {
            "vehicle": v_num,
            "vehicle_id": b.get("vehicleid"),
            "type": s_type,
            "lat": round(b_lat, 5),
            "lon": round(b_lon, 5),
            "heading": heading,
            "dist_km": round(dist_km, 2),
            "eta_mins": eta_mins,
            "last_updated": last_refresh,
        }
        all_buses.append(bus_obj)

        # Bus is approaching if bus_stop_idx <= user_stop_idx or it is within 250m
        if user_stop_idx != -1 and bus_stop_idx != -1:
            stops_away = user_stop_idx - bus_stop_idx
            if stops_away >= 0 or dist_km <= 0.25:
                bus_obj_approaching = dict(bus_obj)
                bus_obj_approaching["stops_away"] = max(0, stops_away)
                bus_obj_approaching["is_at_stop"] = dist_km <= 0.25 or stops_away == 0
                approaching_buses.append(bus_obj_approaching)

    # Sort approaching buses by distance to the user
    approaching_buses.sort(key=lambda x: x["dist_km"])

    nearest = approaching_buses[0] if approaching_buses else None

    return {
        "live": True,
        "route": route_no,
        "direction": direction_label,
        "active_buses_total": len(chosen_buses),
        "approaching_count": len(approaching_buses),
        "nearest_bus": nearest,
        "approaching_buses": approaching_buses[:5],  # top 5 nearest approaching
        "all_active_buses": all_buses,
    }
