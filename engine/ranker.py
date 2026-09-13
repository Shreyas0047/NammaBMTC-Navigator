"""
Destination-Aware Boarding Point Ranking Engine.
Evaluates candidate stops based on:
1. Destination reachability with strict direction validation (seq_dest > seq_orig).
2. Estimated street walking distance and walking time.
3. Service frequency (number of daily trips across viable routes).
4. Route variety.
5. Multi-Leg Transfer Graph Search: Automatically finds optimal 1-transfer connections
   when no direct bus is available.
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


def find_transfer_candidates(
    origin_stops: List[Any],
    dest_stops: List[Any],
    orig_stop_map: Dict[str, Any],
) -> List[CandidateBoardingPoint]:
    """
    Computes 1-transfer transit paths when no direct bus connects origin and destination.
    Finds intersecting transfer stops between origin routes and destination routes.
    """
    o_ids = [s.stop_id for s, _ in origin_stops]
    d_ids = [s.stop_id for s, _ in dest_stops]

    conn = get_db_connection(readonly=True)
    cur = conn.cursor()

    o_placeholders = ",".join(["?"] * len(o_ids))
    d_placeholders = ",".join(["?"] * len(d_ids))

    q = f"""
        WITH leg1 AS (
            SELECT 
                st_orig.stop_id as orig_stop_id,
                st_x.stop_id as transfer_stop_id,
                r.route_short_name as r1_short,
                r.route_long_name as r1_long,
                t.trip_headsign as h1,
                t.direction_id as d1,
                COUNT(DISTINCT t.trip_id) as trip_count1,
                AVG(st_x.stop_sequence - st_orig.stop_sequence) as avg_stops1
            FROM stop_times st_orig
            JOIN stop_times st_x ON st_orig.trip_id = st_x.trip_id AND st_x.stop_sequence > st_orig.stop_sequence
            JOIN trips t ON st_orig.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE st_orig.stop_id IN ({o_placeholders})
            GROUP BY st_orig.stop_id, st_x.stop_id, r.route_short_name, t.trip_headsign
        ),
        leg2 AS (
            SELECT 
                st_x.stop_id as transfer_stop_id,
                st_dest.stop_id as dest_stop_id,
                s_dest.stop_name as dest_stop_name,
                r.route_short_name as r2_short,
                r.route_long_name as r2_long,
                t.trip_headsign as h2,
                t.direction_id as d2,
                COUNT(DISTINCT t.trip_id) as trip_count2,
                AVG(st_dest.stop_sequence - st_x.stop_sequence) as avg_stops2
            FROM stop_times st_dest
            JOIN stop_times st_x ON st_dest.trip_id = st_x.trip_id AND st_x.stop_sequence < st_dest.stop_sequence
            JOIN stops s_dest ON st_dest.stop_id = s_dest.stop_id
            JOIN trips t ON st_dest.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE st_dest.stop_id IN ({d_placeholders})
            GROUP BY st_x.stop_id, st_dest.stop_id, r.route_short_name, t.trip_headsign
        )
        SELECT 
            l1.orig_stop_id,
            l1.transfer_stop_id,
            s_tx.stop_name as transfer_name,
            s_tx.stop_desc as transfer_desc,
            l1.r1_short, l1.r1_long, l1.h1, l1.d1, l1.trip_count1, l1.avg_stops1,
            l2.dest_stop_id, l2.dest_stop_name,
            l2.r2_short, l2.r2_long, l2.h2, l2.d2, l2.trip_count2, l2.avg_stops2
        FROM leg1 l1
        JOIN leg2 l2 ON l1.transfer_stop_id = l2.transfer_stop_id
        JOIN stops s_tx ON l1.transfer_stop_id = s_tx.stop_id
        ORDER BY (l1.trip_count1 + l2.trip_count2) DESC
        LIMIT 60
    """

    cur.execute(q, o_ids + d_ids)
    rows = cur.fetchall()
    conn.close()

    if not rows:
        return []

    grouped = {}
    for r in rows:
        key = (r["orig_stop_id"], r["transfer_stop_id"])
        if key not in grouped:
            grouped[key] = {
                "orig_stop_id": r["orig_stop_id"],
                "transfer_stop_id": r["transfer_stop_id"],
                "transfer_name": r["transfer_name"],
                "transfer_desc": r["transfer_desc"] or "",
                "leg1": [],
                "leg2": [],
            }

        v1 = ViableRouteOption(
            route_short_name=r["r1_short"],
            route_long_name=r["r1_long"],
            trip_headsign=r["h1"],
            direction_id=str(r["d1"]),
            destination_stop_name=r["transfer_name"],
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
    for (orig_sid, tx_sid), data in grouped.items():
        if orig_sid not in orig_stop_map:
            continue
        stop, h_dist = orig_stop_map[orig_sid]
        est_walk_m = h_dist * STREET_WALK_FACTOR
        walk_min = max(1, math.ceil(est_walk_m / (WALKING_SPEED_MPS * 60.0)))

        total_trips = sum(v.trip_count for v in data["leg1"]) + sum(v.trip_count for v in data["leg2"])
        walk_penalty = est_walk_m * 0.05
        transfer_penalty = 18.0
        frequency_bonus = min(25.0, math.log2(1.0 + total_trips) * 3.5)

        composite_score = 60.0 - walk_penalty - transfer_penalty + frequency_bonus
        final_score = max(0.0, min(100.0, composite_score))

        score_breakdown = {
            "base_score": 60.0,
            "walk_penalty": -round(walk_penalty, 2),
            "transfer_penalty": -transfer_penalty,
            "frequency_bonus": round(frequency_bonus, 2),
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
) -> List[CandidateBoardingPoint]:
    """
    Computes 2-transfer (3-leg) transit paths when no direct bus or 1-transfer path connects
    origin and destination. Bridges through key intermediate interchanges.
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

    # 1. Stops X1 reachable from Origin
    cur.execute(f"""
        SELECT 
            st_orig.stop_id as orig_stop_id,
            st_x1.stop_id as x1_id,
            s_x1.stop_name as x1_name,
            s_x1.stop_desc as x1_desc,
            COUNT(DISTINCT t1.trip_id) as trips1
        FROM stop_times st_orig
        JOIN stop_times st_x1 ON st_orig.trip_id = st_x1.trip_id AND st_x1.stop_sequence > st_orig.stop_sequence
        JOIN stops s_x1 ON st_x1.stop_id = s_x1.stop_id
        JOIN trips t1 ON st_orig.trip_id = t1.trip_id
        WHERE st_orig.stop_id IN ({o_ph})
        GROUP BY st_orig.stop_id, st_x1.stop_id
        ORDER BY trips1 DESC
        LIMIT 40
    """, o_ids)
    x1_rows = cur.fetchall()

    # 2. Stops X2 that can reach Destination
    cur.execute(f"""
        SELECT 
            st_x2.stop_id as x2_id,
            s_x2.stop_name as x2_name,
            s_x2.stop_desc as x2_desc,
            st_dest.stop_id as dest_stop_id,
            s_dest.stop_name as dest_name,
            COUNT(DISTINCT t3.trip_id) as trips3
        FROM stop_times st_dest
        JOIN stop_times st_x2 ON st_dest.trip_id = st_x2.trip_id AND st_x2.stop_sequence < st_dest.stop_sequence
        JOIN stops s_x2 ON st_x2.stop_id = s_x2.stop_id
        JOIN stops s_dest ON st_dest.stop_id = s_dest.stop_id
        JOIN trips t3 ON st_dest.trip_id = t3.trip_id
        WHERE st_dest.stop_id IN ({d_ph})
        GROUP BY st_x2.stop_id, st_dest.stop_id
        ORDER BY trips3 DESC
        LIMIT 40
    """, d_ids)
    x2_rows = cur.fetchall()

    if not x1_rows or not x2_rows:
        conn.close()
        return []

    x1_ids = list({r["x1_id"] for r in x1_rows})
    x2_ids = list({r["x2_id"] for r in x2_rows})

    x1_ph = ",".join(["?"] * len(x1_ids))
    x2_ph = ",".join(["?"] * len(x2_ids))

    # 3. Connecting routes between X1 and X2
    cur.execute(f"""
        SELECT 
            st_x1.stop_id as x1_id,
            s_x1.stop_name as x1_name,
            s_x1.stop_desc as x1_desc,
            st_x2.stop_id as x2_id,
            s_x2.stop_name as x2_name,
            s_x2.stop_desc as x2_desc,
            r.route_short_name as r2_short,
            r.route_long_name as r2_long,
            t.trip_headsign as h2,
            t.direction_id as d2,
            COUNT(DISTINCT t.trip_id) as trip_count2,
            AVG(st_x2.stop_sequence - st_x1.stop_sequence) as avg_stops2
        FROM stop_times st_x1
        JOIN stop_times st_x2 ON st_x1.trip_id = st_x2.trip_id AND st_x2.stop_sequence > st_x1.stop_sequence
        JOIN stops s_x1 ON st_x1.stop_id = s_x1.stop_id
        JOIN stops s_x2 ON st_x2.stop_id = s_x2.stop_id
        JOIN trips t ON st_x1.trip_id = t.trip_id
        JOIN routes r ON t.route_id = r.route_id
        WHERE st_x1.stop_id IN ({x1_ph})
          AND st_x2.stop_id IN ({x2_ph})
        GROUP BY st_x1.stop_id, st_x2.stop_id, r.route_short_name, t.trip_headsign
        ORDER BY trip_count2 DESC
        LIMIT 20
    """, x1_ids + x2_ids)
    mid_rows = cur.fetchall()

    if not mid_rows:
        conn.close()
        return []

    x1_to_orig = {}
    for r in x1_rows:
        x1_to_orig.setdefault(r["x1_id"], []).append(r["orig_stop_id"])

    x2_to_dest = {}
    for r in x2_rows:
        x2_to_dest.setdefault(r["x2_id"], []).append(r["dest_stop_id"])

    candidates = []
    seen_combos = set()

    for m in mid_rows:
        x1_id = m["x1_id"]
        x2_id = m["x2_id"]
        orig_candidate_ids = x1_to_orig.get(x1_id, [])
        if not orig_candidate_ids:
            continue
        orig_id = orig_candidate_ids[0]
        if orig_id not in orig_stop_map:
            continue

        combo_key = (orig_id, m["x1_name"], m["x2_name"])
        if combo_key in seen_combos:
            continue
        seen_combos.add(combo_key)

        # Leg 1 routes: orig_id -> x1_id
        cur.execute("""
            SELECT r.route_short_name, r.route_long_name, t.trip_headsign, t.direction_id,
                   COUNT(DISTINCT t.trip_id) as trip_count,
                   AVG(st2.stop_sequence - st1.stop_sequence) as avg_stops
            FROM stop_times st1
            JOIN stop_times st2 ON st1.trip_id = st2.trip_id AND st2.stop_sequence > st1.stop_sequence
            JOIN trips t ON st1.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE st1.stop_id = ? AND st2.stop_id = ?
            GROUP BY r.route_short_name, t.trip_headsign
            ORDER BY trip_count DESC LIMIT 4
        """, (orig_id, x1_id))
        l1_res = cur.fetchall()
        if not l1_res:
            continue

        # Leg 3 routes: x2_id -> destination stops
        dest_candidate_ids = x2_to_dest.get(x2_id, [])
        if not dest_candidate_ids:
            continue
        dest_id = dest_candidate_ids[0]
        cur.execute("""
            SELECT r.route_short_name, r.route_long_name, t.trip_headsign, t.direction_id,
                   s_dest.stop_name as dest_name,
                   COUNT(DISTINCT t.trip_id) as trip_count,
                   AVG(st2.stop_sequence - st1.stop_sequence) as avg_stops
            FROM stop_times st1
            JOIN stop_times st2 ON st1.trip_id = st2.trip_id AND st2.stop_sequence > st1.stop_sequence
            JOIN stops s_dest ON st2.stop_id = s_dest.stop_id
            JOIN trips t ON st1.trip_id = t.trip_id
            JOIN routes r ON t.route_id = r.route_id
            WHERE st1.stop_id = ? AND st2.stop_id = ?
            GROUP BY r.route_short_name, t.trip_headsign
            ORDER BY trip_count DESC LIMIT 4
        """, (x2_id, dest_id))
        l3_res = cur.fetchall()
        if not l3_res:
            continue

        leg1_routes = [
            ViableRouteOption(
                route_short_name=r["route_short_name"],
                route_long_name=r["route_long_name"],
                trip_headsign=r["trip_headsign"],
                direction_id=str(r["direction_id"]),
                destination_stop_name=m["x1_name"],
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
                destination_stop_name=m["x2_name"],
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
        transfer_penalty = 28.0
        frequency_bonus = min(25.0, math.log2(1.0 + total_trips) * 3.0)
        composite_score = max(0.0, min(100.0, 50.0 - walk_penalty - transfer_penalty + frequency_bonus))

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
                "base_score": 50.0,
                "walk_penalty": -round(walk_penalty, 2),
                "transfer_penalty": -transfer_penalty,
                "frequency_bonus": round(frequency_bonus, 2),
                "total_trips_per_day": total_trips,
                "transfers": 2,
                "transfer1_hub": m["x1_name"],
                "transfer2_hub": m["x2_name"],
            },
            is_direct=False,
            transfers_count=2,
            transfer_stop_name=m["x1_name"],
            transfer_stop_desc=m["x1_desc"] or "Change to Bus 2",
            transfer2_stop_name=m["x2_name"],
            transfer2_stop_desc=m["x2_desc"] or "Change to Bus 3 towards destination",
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
    Supports Direct routes and Multi-Leg Transfer fallback (1-transfer and 2-transfer).
    """
    def find_viable_routes(w_radius, d_radius):
        o_stops = find_nearby_stops(origin_lat, origin_lon, radius_meters=w_radius)
        d_stops = find_nearby_stops(dest_lat, dest_lon, radius_meters=d_radius)
        if not o_stops or not d_stops:
            return o_stops, d_stops, {}

        o_map = {s.stop_id: (s, dist) for s, dist in o_stops}
        d_ids = [s.stop_id for s, _ in d_stops]
        o_ids = list(o_map.keys())

        conn = get_db_connection(readonly=True)
        cur = conn.cursor()
        orig_placeholders = ",".join(["?"] * len(o_ids))
        dest_placeholders = ",".join(["?"] * len(d_ids))

        query = f"""
            SELECT 
                st1.stop_id as orig_stop_id,
                s2.stop_name as dest_stop_name,
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
        return o_stops, d_stops, s_routes

    # 1. Initial direct search
    origin_stops, dest_stops, stop_routes = find_viable_routes(walk_radius_m, dest_radius_m)

    # 2. Progressive radius expansion if no direct routes found initially
    if not stop_routes and (walk_radius_m < 1200.0 or dest_radius_m < 2000.0):
        expanded_walk = max(walk_radius_m, 1200.0)
        expanded_dest = max(dest_radius_m, 2000.0)
        origin_stops, dest_stops, stop_routes = find_viable_routes(expanded_walk, expanded_dest)

    orig_stop_map = {s.stop_id: (s, dist) for s, dist in origin_stops}

    # 3. If NO direct routes found, run Transfer Graph Search
    if not stop_routes:
        # 3a. Try 1-Transfer
        transfer_candidates = find_transfer_candidates(origin_stops, dest_stops, orig_stop_map)
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

        # 3b. Try 2-Transfer (3-Leg Path)
        two_transfer_candidates = find_two_transfer_candidates(origin_stops, dest_stops, orig_stop_map)
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

        # 3c. Progressive radius retry for outer rural / sparse stops
        if walk_radius_m < 1600.0 or dest_radius_m < 2500.0:
            exp_o = find_nearby_stops(origin_lat, origin_lon, radius_meters=1800.0)
            exp_d = find_nearby_stops(dest_lat, dest_lon, radius_meters=3000.0)
            if exp_o and exp_d:
                exp_map = {s.stop_id: (s, dist) for s, dist in exp_o}
                cands = find_transfer_candidates(exp_o, exp_d, exp_map) or find_two_transfer_candidates(exp_o, exp_d, exp_map)
                if cands:
                    primary = cands[0]
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
                        message=f"Found journey via {primary.transfer_stop_name}.",
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

    # 4. Direct Routes Scoring
    candidates: List[CandidateBoardingPoint] = []
    for sid, routes in stop_routes.items():
        stop, h_dist = orig_stop_map[sid]
        est_walk_m = h_dist * STREET_WALK_FACTOR
        walk_min = max(1, math.ceil(est_walk_m / (WALKING_SPEED_MPS * 60.0)))
        total_trips = sum(ro.trip_count for ro in routes)
        route_count = len(routes)

        walk_penalty = est_walk_m * 0.05
        frequency_bonus = min(30.0, math.log2(1.0 + total_trips) * 4.0)
        route_variety_bonus = min(10.0, route_count * 2.0)

        composite_score = 60.0 - walk_penalty + frequency_bonus + route_variety_bonus
        final_score = max(0.0, min(100.0, composite_score))

        score_breakdown = {
            "base_score": 60.0,
            "walk_penalty": -round(walk_penalty, 2),
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
    primary = candidates[0] if candidates else None

    return JourneyRecommendation(
        origin_name=origin_name,
        origin_lat=origin_lat,
        origin_lon=origin_lon,
        dest_name=dest_name,
        dest_lat=dest_lat,
        dest_lon=dest_lon,
        primary_candidate=primary,
        ranked_candidates=candidates,
        status="OK",
        message="Found viable direct boarding points.",
    )
