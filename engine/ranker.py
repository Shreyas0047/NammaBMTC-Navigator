"""
Destination-Aware Boarding Point Ranking Engine.
Evaluates candidate stops based on:
1. Destination reachability with strict direction validation (seq_dest > seq_orig).
2. Estimated street walking distance and walking time.
3. Service frequency (number of daily trips across viable routes).
4. Route variety.
5. Multi-Leg Transfer Graph Search: High-precision 1-transfer and 2-transfer connection engine
   with cluster matching, physical pedestrian proximity constraints, and hub prioritization.
Outputs a structured internal ranking of all viable candidates with transparent score breakdowns.
"""

import math
from typing import List, Dict, Any, Optional
from engine.db import get_db_connection
from engine.spatial_index import find_nearby_stops, haversine
from engine.models import (
    Stop,
    ViableRouteOption,
    CandidateBoardingPoint,
    JourneyRecommendation,
)

# Empirical pedestrian multiplier for Bengaluru street network
STREET_WALK_FACTOR = 1.35
WALKING_SPEED_MPS = 1.2  # 1.2 m/s (~4.3 km/h)

MAJOR_HUBS = [
    "kempegowda bus station", "majestic", "k.r.market", "kr market", "kalasipalya",
    "shivajinagar", "banashankari", "central silk board", "silk board", "hebbal",
    "shanthinagar", "yeshwanthpur", "jayanagar", "vijayanagar", "kengeri",
    "corporation", "kr circle", "maharani", "dairy circle", "nimhans", "domlur",
    "koramangala", "marathahalli", "tin factory", "kr pura", "btm layout",
    "jayadeva", "mico layout"
]


def get_hub_bonus(stop_name: str) -> float:
    """
    Returns hub priority bonus for recognized major transit nodes.
    """
    n = stop_name.lower()
    for premier in [
        "kempegowda bus station", "majestic", "k.r.market", "kr market",
        "shivajinagar", "central silk board", "banashankari", "corporation"
    ]:
        if premier in n:
            return 30.0
    for hub in MAJOR_HUBS:
        if hub in n:
            return 18.0
    return 0.0


def get_destination_stops(dest_lat: float, dest_lon: float) -> List[Any]:
    """
    Finds stops near destination. If doorstep stops (<= 550m) exist, strictly returns
    those to prevent false direct routes that drop passengers 1.5km away.
    Only expands to larger radii if no close stops exist.
    """
    close_stops = find_nearby_stops(dest_lat, dest_lon, radius_meters=550.0)
    if close_stops:
        return close_stops
    for r in [850.0, 1200.0, 1800.0, 2500.0]:
        stops = find_nearby_stops(dest_lat, dest_lon, radius_meters=r)
        if stops:
            return stops
    return []


def find_transfer_candidates(
    origin_stops: List[Any],
    dest_stops: List[Any],
    orig_stop_map: Dict[str, Any],
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
) -> List[CandidateBoardingPoint]:
    """
    Computes 1-transfer transit paths when no direct bus connects origin and destination.
    Finds intersecting transfer stops between origin routes and destination routes.
    Matches interchange stops by physical stop cluster (cluster_name) with strict
    pedestrian proximity constraints to prevent cross-city homonym teleportation.
    """
    o_ids = [s.stop_id for s, _ in origin_stops]
    d_ids = [s.stop_id for s, _ in dest_stops]

    if not o_ids or not d_ids:
        return []

    conn = get_db_connection(readonly=True)
    cur = conn.cursor()

    o_placeholders = ",".join(["?"] * len(o_ids))
    d_placeholders = ",".join(["?"] * len(d_ids))

    q = f"""
        WITH leg1 AS (
            SELECT 
                st_orig.stop_id as orig_stop_id,
                s_x.cluster_name as transfer_cluster,
                s_x.stop_name as transfer_name,
                s_x.stop_desc as transfer_desc,
                s_x.stop_lat as tx_lat1,
                s_x.stop_lon as tx_lon1,
                r.route_short_name as r1_short,
                r.route_long_name as r1_long,
                t.trip_headsign as h1,
                t.direction_id as d1,
                COUNT(DISTINCT t.trip_id) as trip_count1,
                AVG(st_x.stop_sequence - st_orig.stop_sequence) as avg_stops1
            FROM stop_times st_orig
            JOIN stop_times st_x ON st_orig.trip_id = st_x.trip_id AND st_x.stop_sequence > st_orig.stop_sequence
            JOIN stops s_x ON st_x.stop_id = s_x.stop_id
            JOIN trips t ON st_orig.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE st_orig.stop_id IN ({o_placeholders})
            GROUP BY st_orig.stop_id, s_x.cluster_name, r.route_short_name, t.trip_headsign
        ),
        leg2 AS (
            SELECT 
                s_x.cluster_name as transfer_cluster,
                s_x.stop_name as transfer_name,
                s_x.stop_lat as tx_lat2,
                s_x.stop_lon as tx_lon2,
                st_dest.stop_id as dest_stop_id,
                s_dest.stop_name as dest_stop_name,
                s_dest.stop_lat as dest_lat,
                s_dest.stop_lon as dest_lon,
                r.route_short_name as r2_short,
                r.route_long_name as r2_long,
                t.trip_headsign as h2,
                t.direction_id as d2,
                COUNT(DISTINCT t.trip_id) as trip_count2,
                AVG(st_dest.stop_sequence - st_x.stop_sequence) as avg_stops2
            FROM stop_times st_dest
            JOIN stop_times st_x ON st_dest.trip_id = st_x.trip_id AND st_x.stop_sequence < st_dest.stop_sequence
            JOIN stops s_x ON st_x.stop_id = s_x.stop_id
            JOIN stops s_dest ON st_dest.stop_id = s_dest.stop_id
            JOIN trips t ON st_dest.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE st_dest.stop_id IN ({d_placeholders})
            GROUP BY s_x.cluster_name, st_dest.stop_id, r.route_short_name, t.trip_headsign
        )
        SELECT 
            l1.orig_stop_id,
            l1.transfer_cluster,
            l1.transfer_name as transfer_name1,
            l2.transfer_name as transfer_name2,
            l1.transfer_desc,
            l1.tx_lat1, l1.tx_lon1,
            l2.tx_lat2, l2.tx_lon2,
            l1.r1_short, l1.r1_long, l1.h1, l1.d1, l1.trip_count1, l1.avg_stops1,
            l2.dest_stop_id, l2.dest_stop_name, l2.dest_lat, l2.dest_lon,
            l2.r2_short, l2.r2_long, l2.h2, l2.d2, l2.trip_count2, l2.avg_stops2
        FROM leg1 l1
        JOIN leg2 l2 ON l1.transfer_cluster = l2.transfer_cluster
          AND ABS(l1.tx_lat1 - l2.tx_lat2) < 0.005
          AND ABS(l1.tx_lon1 - l2.tx_lon2) < 0.005
        ORDER BY (l1.trip_count1 + l2.trip_count2) DESC
        LIMIT 80
    """

    cur.execute(q, o_ids + d_ids)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return []

    grouped = {}
    for r in rows:
        # Strict physical pedestrian walk validation between arrival & departure poles
        tx_walk_m = haversine(r["tx_lat1"], r["tx_lon1"], r["tx_lat2"], r["tx_lon2"])
        is_hub = get_hub_bonus(r["transfer_cluster"]) > 0
        max_tx = 500.0 if is_hub else 250.0
        if tx_walk_m > max_tx:
            continue

        key = (r["orig_stop_id"], r["transfer_cluster"])
        if key not in grouped:
            tx_disp_name = r["transfer_cluster"]
            tx_desc = f"Change bus at {tx_disp_name}" + (f" (~{round(tx_walk_m)}m walk)" if tx_walk_m > 40 else "")
            grouped[key] = {
                "orig_stop_id": r["orig_stop_id"],
                "transfer_name": tx_disp_name,
                "transfer_desc": tx_desc,
                "tx_lat": r["tx_lat1"],
                "tx_lon": r["tx_lon1"],
                "tx_walk_m": tx_walk_m,
                "dest_lat": r["dest_lat"],
                "dest_lon": r["dest_lon"],
                "leg1": [],
                "leg2": [],
            }

        v1 = ViableRouteOption(
            route_short_name=r["r1_short"],
            route_long_name=r["r1_long"],
            trip_headsign=r["h1"],
            direction_id=str(r["d1"]),
            destination_stop_name=r["transfer_cluster"],
            trip_count=r["trip_count1"],
            transit_stops_count=int(round(r["avg_stops1"])),
        )
        v2 = ViableRouteOption(
            route_short_name=r["r2_short"],
            route_long_name=r["r2_long"],
            trip_headsign=r["h2"],
            direction_id=str(r["d2"]),
            destination_stop_name=r["dest_stop_name"],
            trip_count=r["trip_count2"],
            transit_stops_count=int(round(r["avg_stops2"])),
        )
        if v1 not in grouped[key]["leg1"]:
            grouped[key]["leg1"].append(v1)
        if v2 not in grouped[key]["leg2"]:
            grouped[key]["leg2"].append(v2)

    candidates = []
    for (orig_sid, tx_name), data in grouped.items():
        if orig_sid not in orig_stop_map:
            continue
        stop, h_dist = orig_stop_map[orig_sid]
        est_walk_m = h_dist * STREET_WALK_FACTOR
        walk_min = max(1, math.ceil(est_walk_m / (WALKING_SPEED_MPS * 60.0)))

        total_trips = sum(v.trip_count for v in data["leg1"]) + sum(v.trip_count for v in data["leg2"])
        walk_penalty = est_walk_m * 0.05
        transfer_penalty = 12.0
        tx_walk_penalty = (data["tx_walk_m"] / 100.0) * 2.0
        frequency_bonus = min(25.0, math.log2(1.0 + total_trips) * 3.5)
        hub_bonus = get_hub_bonus(data["transfer_name"])

        # Detour penalty to eliminate backtracking
        detour_penalty = 0.0
        t_dest_lat = dest_lat if dest_lat is not None else data.get("dest_lat")
        t_dest_lon = dest_lon if dest_lon is not None else data.get("dest_lon")
        if t_dest_lat and t_dest_lon:
            direct_dist = max(100.0, haversine(stop.lat, stop.lon, t_dest_lat, t_dest_lon))
            via_dist = haversine(stop.lat, stop.lon, data["tx_lat"], data["tx_lon"]) + haversine(data["tx_lat"], data["tx_lon"], t_dest_lat, t_dest_lon)
            detour_ratio = via_dist / direct_dist
            if detour_ratio > 1.30:
                detour_penalty = min(35.0, (detour_ratio - 1.30) * 30.0)

        composite_score = 58.0 - walk_penalty - transfer_penalty - tx_walk_penalty + frequency_bonus + hub_bonus - detour_penalty
        final_score = max(0.0, min(100.0, composite_score))

        score_breakdown = {
            "base_score": 58.0,
            "walk_penalty": -round(walk_penalty, 2),
            "transfer_penalty": -transfer_penalty,
            "transfer_walk_penalty": -round(tx_walk_penalty, 2),
            "frequency_bonus": round(frequency_bonus, 2),
            "hub_bonus": hub_bonus,
            "detour_penalty": -round(detour_penalty, 2),
            "total_trips_per_day": total_trips,
            "transfers": 1,
            "transfer_hub": data["transfer_name"],
            "haversine_m": round(h_dist),
            "est_street_walk_m": round(est_walk_m),
        }

        data["leg1"].sort(key=lambda x: x.trip_count, reverse=True)
        data["leg2"].sort(key=lambda x: x.trip_count, reverse=True)

        cb = CandidateBoardingPoint(
            stop_id=stop.stop_id,
            stop_name=stop.stop_name,
            stop_desc=stop.stop_desc,
            lat=stop.lat,
            lon=stop.lon,
            walk_distance_m=est_walk_m,
            walk_duration_min=walk_min,
            viable_routes=data["leg1"],
            score=final_score,
            score_breakdown=score_breakdown,
            is_direct=False,
            transfers_count=1,
            transfer_stop_name=data["transfer_name"],
            transfer_stop_desc=data["transfer_desc"],
            leg1_routes=data["leg1"],
            leg2_routes=data["leg2"],
        )
        candidates.append(cb)

    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def find_two_transfer_candidates(
    origin_stops: List[Any],
    dest_stops: List[Any],
    orig_stop_map: Dict[str, Any],
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
) -> List[CandidateBoardingPoint]:
    """
    Computes 2-transfer (3-leg) transit paths when no direct bus or 1-transfer path connects
    origin and destination. Bridges through key intermediate transit hubs.
    Path: Origin -> Interchange 1 (X1) -> Interchange 2 (X2) -> Destination
    """
    o_ids = [s.stop_id for s, _ in origin_stops]
    d_ids = [s.stop_id for s, _ in dest_stops]

    if not o_ids or not d_ids:
        return []

    conn = get_db_connection(readonly=True)
    cur = conn.cursor()

    o_ph = ",".join(["?"] * len(o_ids))
    d_ph = ",".join(["?"] * len(d_ids))

    # 1. Stops / Hubs X1 reachable from Origin, boosted by major hub score
    cur.execute(f"""
        SELECT 
            st_orig.stop_id as orig_stop_id,
            s_x1.cluster_name as x1_cluster,
            s_x1.stop_lat as x1_lat1,
            s_x1.stop_lon as x1_lon1,
            COUNT(DISTINCT t1.trip_id) as trips1,
            CASE 
                WHEN LOWER(s_x1.cluster_name) IN (
                    'kempegowda bus station', 'majestic', 'kr market', 'central silk board',
                    'banashankari bus station', 'corporation', 'tin factory', 'hebbal',
                    'yeshwanthpur', 'kengeri bus station', 'marathahalli bridge'
                ) THEN 1000
                ELSE 0
            END as hub_score
        FROM stop_times st_orig
        JOIN stop_times st_x1 ON st_orig.trip_id = st_x1.trip_id AND st_x1.stop_sequence > st_orig.stop_sequence
        JOIN stops s_x1 ON st_x1.stop_id = s_x1.stop_id
        JOIN trips t1 ON st_orig.trip_id = t1.trip_id
        WHERE st_orig.stop_id IN ({o_ph})
        GROUP BY st_orig.stop_id, s_x1.cluster_name
        ORDER BY hub_score + trips1 DESC
        LIMIT 40
    """, o_ids)
    x1_rows = cur.fetchall()

    # 2. Stops / Hubs X2 that reach Destination, boosted by major hub score
    cur.execute(f"""
        SELECT 
            st_dest.stop_id as dest_stop_id,
            s_x2.cluster_name as x2_cluster,
            s_x2.stop_lat as x2_lat2,
            s_x2.stop_lon as x2_lon2,
            s_dest.stop_name as dest_name,
            COUNT(DISTINCT t3.trip_id) as trips3,
            CASE 
                WHEN LOWER(s_x2.cluster_name) IN (
                    'kempegowda bus station', 'majestic', 'kr market', 'central silk board',
                    'banashankari bus station', 'corporation', 'tin factory', 'hebbal',
                    'yeshwanthpur', 'dairy circle', 'jayadeva hospital'
                ) THEN 1000
                ELSE 0
            END as hub_score
        FROM stop_times st_dest
        JOIN stop_times st_x2 ON st_dest.trip_id = st_x2.trip_id AND st_x2.stop_sequence < st_dest.stop_sequence
        JOIN stops s_x2 ON st_x2.stop_id = s_x2.stop_id
        JOIN stops s_dest ON st_dest.stop_id = s_dest.stop_id
        JOIN trips t3 ON st_dest.trip_id = t3.trip_id
        WHERE st_dest.stop_id IN ({d_ph})
        GROUP BY st_dest.stop_id, s_x2.cluster_name
        ORDER BY hub_score + trips3 DESC
        LIMIT 40
    """, d_ids)
    x2_rows = cur.fetchall()

    if not x1_rows or not x2_rows:
        conn.close()
        return []

    x1_map = {r["x1_cluster"]: r for r in x1_rows}
    x2_map = {r["x2_cluster"]: r for r in x2_rows}

    x1_clusters = list(x1_map.keys())
    x2_clusters = list(x2_map.keys())

    x1_ph = ",".join(["?"] * len(x1_clusters))
    x2_ph = ",".join(["?"] * len(x2_clusters))

    # 3. Connecting routes between X1 and X2
    cur.execute(f"""
        SELECT 
            s1.cluster_name as x1_cluster,
            s1.stop_lat as x1_lat2, s1.stop_lon as x1_lon2,
            s2.cluster_name as x2_cluster,
            s2.stop_lat as x2_lat1, s2.stop_lon as x2_lon1,
            r.route_short_name as r2_short,
            r.route_long_name as r2_long,
            t.trip_headsign as h2,
            t.direction_id as d2,
            COUNT(DISTINCT t.trip_id) as trip_count2,
            AVG(st2.stop_sequence - st1.stop_sequence) as avg_stops2
        FROM stop_times st1
        JOIN stop_times st2 ON st1.trip_id = st2.trip_id AND st2.stop_sequence > st1.stop_sequence
        JOIN stops s1 ON st1.stop_id = s1.stop_id
        JOIN stops s2 ON st2.stop_id = s2.stop_id
        JOIN trips t ON st1.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        WHERE s1.cluster_name IN ({x1_ph})
          AND s2.cluster_name IN ({x2_ph})
          AND s1.cluster_name != s2.cluster_name
        GROUP BY s1.cluster_name, s2.cluster_name, r.route_short_name
        ORDER BY trip_count2 DESC
        LIMIT 30
    """, x1_clusters + x2_clusters)
    mid_rows = cur.fetchall()

    candidates = []
    seen_combos = set()

    for m in mid_rows:
        x1_c = m["x1_cluster"]
        x2_c = m["x2_cluster"]
        r1_info = x1_map.get(x1_c)
        r2_info = x2_map.get(x2_c)
        if not r1_info or not r2_info:
            continue

        # Physical walk checks for both interchanges
        tx1_walk = haversine(r1_info["x1_lat1"], r1_info["x1_lon1"], m["x1_lat2"], m["x1_lon2"])
        max_tx1 = 500.0 if get_hub_bonus(x1_c) > 0 else 250.0
        if tx1_walk > max_tx1:
            continue

        tx2_walk = haversine(m["x2_lat1"], m["x2_lon1"], r2_info["x2_lat2"], r2_info["x2_lon2"])
        max_tx2 = 500.0 if get_hub_bonus(x2_c) > 0 else 250.0
        if tx2_walk > max_tx2:
            continue

        # Ensure Leg 2 covers a genuine transit distance (>= 1.5 km)
        leg2_dist = haversine(m["x1_lat2"], m["x1_lon2"], m["x2_lat1"], m["x2_lon1"])
        if leg2_dist < 1500.0:
            continue

        orig_id = r1_info["orig_stop_id"]
        dest_id = r2_info["dest_stop_id"]
        if orig_id not in orig_stop_map:
            continue

        combo_key = (orig_id, x1_c, x2_c)
        if combo_key in seen_combos:
            continue
        seen_combos.add(combo_key)

        # Leg 1 routes: orig_id -> x1_cluster
        cur.execute("""
            SELECT r.route_short_name, r.route_long_name, t.trip_headsign, t.direction_id,
                   COUNT(DISTINCT t.trip_id) as trip_count,
                   AVG(st2.stop_sequence - st1.stop_sequence) as avg_stops
            FROM stop_times st1
            JOIN stop_times st2 ON st1.trip_id = st2.trip_id AND st2.stop_sequence > st1.stop_sequence
            JOIN stops s2 ON st2.stop_id = s2.stop_id
            JOIN trips t ON st1.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE st1.stop_id = ? AND s2.cluster_name = ?
            GROUP BY r.route_short_name, t.trip_headsign
            ORDER BY trip_count DESC LIMIT 3
        """, (orig_id, x1_c))
        l1_res = cur.fetchall()
        if not l1_res:
            continue

        # Leg 3 routes: x2_cluster -> dest_id
        cur.execute("""
            SELECT r.route_short_name, r.route_long_name, t.trip_headsign, t.direction_id,
                   s_dest.stop_name as dest_name,
                   COUNT(DISTINCT t.trip_id) as trip_count,
                   AVG(st2.stop_sequence - st1.stop_sequence) as avg_stops
            FROM stop_times st1
            JOIN stop_times st2 ON st1.trip_id = st2.trip_id AND st2.stop_sequence > st1.stop_sequence
            JOIN stops s1 ON st1.stop_id = s1.stop_id
            JOIN stops s_dest ON st2.stop_id = s_dest.stop_id
            JOIN trips t ON st1.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE s1.cluster_name = ? AND st2.stop_id = ?
            GROUP BY r.route_short_name, t.trip_headsign
            ORDER BY trip_count DESC LIMIT 3
        """, (x2_c, dest_id))
        l3_res = cur.fetchall()
        if not l3_res:
            continue

        leg1_routes = [
            ViableRouteOption(
                route_short_name=r["route_short_name"],
                route_long_name=r["route_long_name"],
                trip_headsign=r["trip_headsign"],
                direction_id=str(r["direction_id"]),
                destination_stop_name=x1_c,
                trip_count=r["trip_count"],
                transit_stops_count=int(round(r["avg_stops"] or 0)),
            )
            for r in l1_res
        ]
        leg2_routes = [
            ViableRouteOption(
                route_short_name=m["r2_short"],
                route_long_name=m["r2_long"],
                trip_headsign=m["h2"],
                direction_id=str(m["d2"]),
                destination_stop_name=x2_c,
                trip_count=m["trip_count2"],
                transit_stops_count=int(round(m["avg_stops2"] or 0)),
            )
        ]
        leg3_routes = [
            ViableRouteOption(
                route_short_name=r["route_short_name"],
                route_long_name=r["route_long_name"],
                trip_headsign=r["trip_headsign"],
                direction_id=str(r["direction_id"]),
                destination_stop_name=r["dest_name"],
                trip_count=r["trip_count"],
                transit_stops_count=int(round(r["avg_stops"] or 0)),
            )
            for r in l3_res
        ]

        stop, h_dist = orig_stop_map[orig_id]
        est_walk_m = h_dist * STREET_WALK_FACTOR
        walk_min = max(1, math.ceil(est_walk_m / (WALKING_SPEED_MPS * 60.0)))
        total_trips = sum(v.trip_count for v in leg1_routes) + sum(v.trip_count for v in leg2_routes) + sum(v.trip_count for v in leg3_routes)

        walk_penalty = est_walk_m * 0.05
        transfer_penalty = 22.0
        hub_bonus = get_hub_bonus(x1_c) * 0.5 + get_hub_bonus(x2_c) * 0.5
        frequency_bonus = min(25.0, math.log2(1.0 + total_trips) * 3.0)

        # Detour penalty
        detour_penalty = 0.0
        t_dest_lat = dest_lat if dest_lat is not None else r2_info["dest_lat"] if "dest_lat" in r2_info.keys() else None
        t_dest_lon = dest_lon if dest_lon is not None else r2_info["dest_lon"] if "dest_lon" in r2_info.keys() else None
        if t_dest_lat and t_dest_lon:
            direct_dist = max(100.0, haversine(stop.lat, stop.lon, t_dest_lat, t_dest_lon))
            path_dist = haversine(stop.lat, stop.lon, r1_info["x1_lat1"], r1_info["x1_lon1"]) + leg2_dist + haversine(m["x2_lat1"], m["x2_lon1"], t_dest_lat, t_dest_lon)
            detour_ratio = path_dist / direct_dist
            if detour_ratio > 1.35:
                detour_penalty = min(30.0, (detour_ratio - 1.35) * 25.0)

        composite_score = max(0.0, min(100.0, 52.0 - walk_penalty - transfer_penalty + frequency_bonus + hub_bonus - detour_penalty))

        cb = CandidateBoardingPoint(
            stop_id=stop.stop_id,
            stop_name=stop.stop_name,
            stop_desc=stop.stop_desc,
            lat=stop.lat,
            lon=stop.lon,
            walk_distance_m=est_walk_m,
            walk_duration_min=walk_min,
            viable_routes=leg1_routes,
            score=composite_score,
            score_breakdown={
                "base_score": 52.0,
                "walk_penalty": -round(walk_penalty, 2),
                "transfer_penalty": -transfer_penalty,
                "frequency_bonus": round(frequency_bonus, 2),
                "hub_bonus": round(hub_bonus, 2),
                "detour_penalty": -round(detour_penalty, 2),
                "total_trips_per_day": total_trips,
                "transfers": 2,
                "transfer1_hub": x1_c,
                "transfer2_hub": x2_c,
            },
            is_direct=False,
            transfers_count=2,
            transfer_stop_name=x1_c,
            transfer_stop_desc=f"Change to Bus 2 at {x1_c}",
            transfer2_stop_name=x2_c,
            transfer2_stop_desc=f"Change to Bus 3 at {x2_c} towards destination",
            leg1_routes=leg1_routes,
            leg2_routes=leg2_routes,
            leg3_routes=leg3_routes,
        )
        candidates.append(cb)
        if len(candidates) >= 5:
            break

    conn.close()
    candidates.sort(key=lambda c: c.score, reverse=True)
    return candidates


def rank_boarding_points(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    origin_name: str = "Current Location",
    dest_name: str = "Destination",
    walk_radius_m: float = 800.0,
    dest_radius_m: float = 1200.0,
) -> JourneyRecommendation:
    """
    Finds and ranks all viable BMTC boarding points from origin to destination.
    Features:
    1. Strict destination proximity enforcement (no false direct routes to stops 1.5km away).
    2. Zero-hallucination, physical-walk-tested 1-transfer routing.
    3. Multi-hub 2-transfer routing for deep rural / distant suburb origins.
    4. Full score transparency.
    """
    # 1. Resolve true destination stops (doorstep first)
    dest_stops = get_destination_stops(dest_lat, dest_lon)
    if not dest_stops:
        dest_stops = find_nearby_stops(dest_lat, dest_lon, radius_meters=dest_radius_m)

    # 2. Resolve origin boarding stops (ensure sufficient candidate stops around origin)
    origin_stops = find_nearby_stops(origin_lat, origin_lon, radius_meters=walk_radius_m)
    if len(origin_stops) < 3:
        origin_stops = find_nearby_stops(origin_lat, origin_lon, radius_meters=max(walk_radius_m, 1100.0))
    if not origin_stops:
        origin_stops = find_nearby_stops(origin_lat, origin_lon, radius_meters=1600.0)

    if not origin_stops or not dest_stops:
        return JourneyRecommendation(
            origin_name=origin_name,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            dest_name=dest_name,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            primary_candidate=None,
            ranked_candidates=[],
            status="NO_ROUTES_FOUND",
            message="No BMTC bus stops found near your origin or destination.",
        )

    orig_stop_map = {s.stop_id: (s, dist) for s, dist in origin_stops}
    o_ids = list(orig_stop_map.keys())
    d_ids = [s.stop_id for s, _ in dest_stops]

    conn = get_db_connection(readonly=True)
    cur = conn.cursor()
    orig_placeholders = ",".join(["?"] * len(o_ids))
    dest_placeholders = ",".join(["?"] * len(d_ids))

    # 3. Direct Route Query
    query = f"""
        SELECT 
            st1.stop_id as orig_stop_id,
            s2.stop_id as dest_stop_id,
            s2.stop_name as dest_stop_name,
            s2.stop_lat as dest_lat,
            s2.stop_lon as dest_lon,
            r.route_short_name,
            r.route_long_name,
            t.trip_headsign,
            t.direction_id,
            COUNT(DISTINCT t.trip_id) as trip_count,
            AVG(st2.stop_sequence - st1.stop_sequence) as avg_stops_away
        FROM stop_times st1
        JOIN stop_times st2 
          ON st1.trip_id = st2.trip_id 
         AND st2.stop_sequence > st1.stop_sequence
        JOIN stops s2 ON st2.stop_id = s2.stop_id
        JOIN trips t ON st1.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        WHERE st1.stop_id IN ({orig_placeholders})
          AND st2.stop_id IN ({dest_placeholders})
        GROUP BY st1.stop_id, r.route_short_name, t.trip_headsign, s2.stop_name
        ORDER BY trip_count DESC
    """
    cur.execute(query, o_ids + d_ids)
    rows = cur.fetchall()
    conn.close()

    s_routes: Dict[str, List[ViableRouteOption]] = {}
    stop_dest_dists: Dict[str, float] = {}

    for r in rows:
        sid = r["orig_stop_id"]
        v = ViableRouteOption(
            route_short_name=r["route_short_name"],
            route_long_name=r["route_long_name"],
            trip_headsign=r["trip_headsign"],
            direction_id=str(r["direction_id"]),
            destination_stop_name=r["dest_stop_name"],
            trip_count=r["trip_count"],
            transit_stops_count=int(round(r["avg_stops_away"])),
        )
        s_routes.setdefault(sid, []).append(v)
        # Distance from drop-off stop to destination coordinates
        d_dist = haversine(r["dest_lat"], r["dest_lon"], dest_lat, dest_lon)
        if sid not in stop_dest_dists or d_dist < stop_dest_dists[sid]:
            stop_dest_dists[sid] = d_dist

    # 4. If direct routes exist, score them
    if s_routes:
        candidates: List[CandidateBoardingPoint] = []
        for sid, routes in s_routes.items():
            stop, h_dist = orig_stop_map[sid]
            est_walk_m = h_dist * STREET_WALK_FACTOR
            walk_min = max(1, math.ceil(est_walk_m / (WALKING_SPEED_MPS * 60.0)))
            total_trips = sum(ro.trip_count for ro in routes)
            route_count = len(routes)

            walk_penalty = est_walk_m * 0.05
            dest_walk_dist = stop_dest_dists.get(sid, 0.0)
            dest_walk_penalty = max(0.0, (dest_walk_dist - 400.0) * 0.08)

            frequency_bonus = min(30.0, math.log2(1.0 + total_trips) * 4.0)
            route_variety_bonus = min(10.0, route_count * 2.0)

            composite_score = 65.0 - walk_penalty - dest_walk_penalty + frequency_bonus + route_variety_bonus
            final_score = max(0.0, min(100.0, composite_score))

            score_breakdown = {
                "base_score": 65.0,
                "walk_penalty": -round(walk_penalty, 2),
                "dest_walk_penalty": -round(dest_walk_penalty, 2),
                "frequency_bonus": round(frequency_bonus, 2),
                "route_variety_bonus": round(route_variety_bonus, 2),
                "total_trips_per_day": total_trips,
                "unique_routes": route_count,
                "transfers": 0,
                "haversine_m": round(h_dist),
                "est_street_walk_m": round(est_walk_m),
            }

            routes.sort(key=lambda x: x.trip_count, reverse=True)

            cb = CandidateBoardingPoint(
                stop_id=stop.stop_id,
                stop_name=stop.stop_name,
                stop_desc=stop.stop_desc,
                lat=stop.lat,
                lon=stop.lon,
                walk_distance_m=est_walk_m,
                walk_duration_min=walk_min,
                viable_routes=routes,
                score=final_score,
                score_breakdown=score_breakdown,
                is_direct=True,
                transfers_count=0,
            )
            candidates.append(cb)

        candidates.sort(key=lambda c: c.score, reverse=True)
        if candidates:
            return JourneyRecommendation(
                origin_name=origin_name,
                origin_lat=origin_lat,
                origin_lon=origin_lon,
                dest_name=dest_name,
                dest_lat=dest_lat,
                dest_lon=dest_lon,
                primary_candidate=candidates[0],
                ranked_candidates=candidates,
                status="OK",
                message="Found viable direct boarding points.",
            )

    # 5. Fallback A: 1-Transfer Graph Search
    transfer_candidates = find_transfer_candidates(origin_stops, dest_stops, orig_stop_map, dest_lat, dest_lon)
    if transfer_candidates:
        primary = transfer_candidates[0]
        return JourneyRecommendation(
            origin_name=origin_name,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            dest_name=dest_name,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            primary_candidate=primary,
            ranked_candidates=transfer_candidates,
            status="OK",
            message=f"Found 1-transfer journey via {primary.transfer_stop_name}.",
        )

    # 6. Fallback B: 2-Transfer Graph Search
    two_transfer_candidates = find_two_transfer_candidates(origin_stops, dest_stops, orig_stop_map, dest_lat, dest_lon)
    if two_transfer_candidates:
        primary = two_transfer_candidates[0]
        return JourneyRecommendation(
            origin_name=origin_name,
            origin_lat=origin_lat,
            origin_lon=origin_lon,
            dest_name=dest_name,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
            primary_candidate=primary,
            ranked_candidates=two_transfer_candidates,
            status="OK",
            message=f"Found 2-transfer journey via {primary.transfer_stop_name} and {primary.transfer2_stop_name}.",
        )

    # 7. Fallback C: Progressive radius expansion for deep rural / outer suburban origins
    for exp_r in [1800.0, 2600.0]:
        exp_origin = find_nearby_stops(origin_lat, origin_lon, radius_meters=exp_r)
        if exp_origin:
            exp_map = {s.stop_id: (s, dist) for s, dist in exp_origin}
            cands = find_transfer_candidates(exp_origin, dest_stops, exp_map, dest_lat, dest_lon)
            if not cands:
                cands = find_two_transfer_candidates(exp_origin, dest_stops, exp_map, dest_lat, dest_lon)
            if cands:
                primary = cands[0]
                t_desc = f"via {primary.transfer_stop_name}" if primary.transfers_count == 1 else f"via {primary.transfer_stop_name} and {primary.transfer2_stop_name}"
                return JourneyRecommendation(
                    origin_name=origin_name,
                    origin_lat=origin_lat,
                    origin_lon=origin_lon,
                    dest_name=dest_name,
                    dest_lat=dest_lat,
                    dest_lon=dest_lon,
                    primary_candidate=primary,
                    ranked_candidates=cands,
                    status="OK",
                    message=f"Found journey {t_desc}.",
                )

    return JourneyRecommendation(
        origin_name=origin_name,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_name=dest_name,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        primary_candidate=None,
        ranked_candidates=[],
        status="NO_ROUTES_FOUND",
        message="No viable BMTC routes found between these locations.",
    )
