"""
Route Details Provider for BMTC Routes.
Provides comprehensive route information, stop sequences, staged fares,
operating schedules, and passenger boarding stop alignment.
"""

import math
import sqlite3
from typing import Any, Dict, List, Optional
from engine.db import get_db_connection
from engine.models import classify_route_service


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


def get_route_details(
    route_name: str,
    orig_lat: Optional[float] = None,
    orig_lon: Optional[float] = None,
    dest_lat: Optional[float] = None,
    dest_lon: Optional[float] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetches full metadata, service classification, staged fare, and complete
    stop sequence for a given route (e.g. '378-P', '500-D', 'KIA-9').
    Highlights the passenger's origin and destination stops within the sequence.
    """
    clean_name = route_name.strip()
    conn = get_db_connection()
    c = conn.cursor()

    # Exact match first, then prefix match
    c.execute(
        "SELECT route_id, route_short_name, route_long_name, route_type FROM routes WHERE route_short_name = ? LIMIT 1",
        (clean_name,),
    )
    row = c.fetchone()
    if not row:
        c.execute(
            "SELECT route_id, route_short_name, route_long_name, route_type FROM routes WHERE route_short_name LIKE ? LIMIT 1",
            (clean_name + "%",),
        )
        row = c.fetchone()

    if not row:
        conn.close()
        return None

    route_id = row["route_id"]
    sname = row["route_short_name"]
    lname = row["route_long_name"]

    # Retrieve all trips associated with this route to pick the best direction
    c.execute(
        "SELECT trip_id, trip_headsign, direction_id FROM trips WHERE route_id = ?",
        (route_id,),
    )
    trips = c.fetchall()
    if not trips:
        conn.close()
        return None

    best_trip_id = trips[0]["trip_id"]
    best_headsign = trips[0]["trip_headsign"] or ""
    best_stops = []
    best_orig_idx = -1
    best_dest_idx = -1

    for tr in trips:
        tid = tr["trip_id"]
        c.execute(
            """
            SELECT st.stop_sequence, s.stop_id, s.stop_name, s.stop_desc, s.stop_lat, s.stop_lon
            FROM stop_times st
            JOIN stops s ON st.stop_id = s.stop_id
            WHERE st.trip_id = ?
            ORDER BY st.stop_sequence
            """,
            (tid,),
        )
        cur_stops = c.fetchall()
        if not cur_stops:
            continue

        if orig_lat is not None and orig_lon is not None:
            o_idx = min(
                range(len(cur_stops)),
                key=lambda i: _haversine(orig_lat, orig_lon, cur_stops[i]["stop_lat"], cur_stops[i]["stop_lon"]),
            )
            if dest_lat is not None and dest_lon is not None:
                d_idx = min(
                    range(len(cur_stops)),
                    key=lambda i: _haversine(dest_lat, dest_lon, cur_stops[i]["stop_lat"], cur_stops[i]["stop_lon"]),
                )
                if o_idx <= d_idx:
                    best_trip_id = tid
                    best_headsign = tr["trip_headsign"] or ""
                    best_stops = cur_stops
                    best_orig_idx = o_idx
                    best_dest_idx = d_idx
                    break
            else:
                best_trip_id = tid
                best_headsign = tr["trip_headsign"] or ""
                best_stops = cur_stops
                best_orig_idx = o_idx
                break

    if not best_stops and trips:
        # Fallback to first trip
        c.execute(
            """
            SELECT st.stop_sequence, s.stop_id, s.stop_name, s.stop_desc, s.stop_lat, s.stop_lon
            FROM stop_times st
            JOIN stops s ON st.stop_id = s.stop_id
            WHERE st.trip_id = ?
            ORDER BY st.stop_sequence
            """,
            (trips[0]["trip_id"],),
        )
        best_stops = c.fetchall()

    conn.close()

    total_stops = len(best_stops)
    service_type, fare = classify_route_service(sname, total_stops)

    if service_type == "VAJRA_AC":
        service_label = "AC Vajra (Volvo Express)"
        fare_text = f"₹{fare}"
        pass_text = "₹140 Vajra Gold Day Pass Valid"
        shakti_eligible = False
    elif service_type == "AIRPORT_AC":
        service_label = "Vayu Vajra (Airport Express)"
        fare_text = f"₹{fare}"
        pass_text = "Standard airport fare applies"
        shakti_eligible = False
    else:
        service_label = "Non-AC Ordinary (Sarige)"
        fare_text = f"₹{fare}"
        pass_text = "₹70 BMTC Day Pass Valid"
        shakti_eligible = True

    # Compute total route length in kilometers
    total_distance_km = 0.0
    for i in range(len(best_stops) - 1):
        s1 = best_stops[i]
        s2 = best_stops[i + 1]
        total_distance_km += _haversine(s1["stop_lat"], s1["stop_lon"], s2["stop_lat"], s2["stop_lon"])

    estimated_duration_min = max(12, int(round(total_stops * 2.2)))

    # Mark stops for passenger
    stops_payload: List[Dict[str, Any]] = []
    for idx, s in enumerate(best_stops):
        is_boarding = idx == best_orig_idx
        is_alighting = idx == best_dest_idx
        stops_payload.append({
            "seq": s["stop_sequence"],
            "sequence": s["stop_sequence"],
            "stop_id": s["stop_id"],
            "stop_name": s["stop_name"],
            "stop_desc": s["stop_desc"] or "",
            "lat": s["stop_lat"],
            "lon": s["stop_lon"],
            "is_boarding_stop": is_boarding,
            "is_alighting_stop": is_alighting,
        })

    origin_term = best_stops[0]["stop_name"] if best_stops else "Origin Terminus"
    dest_term = best_stops[-1]["stop_name"] if best_stops else "Destination Terminus"

    daily_trips = max(12, len(trips) * 8)
    if daily_trips >= 60:
        headway = "Every ~5–8 mins (High Frequency)"
    elif daily_trips >= 30:
        headway = "Every ~10–15 mins (Standard Frequency)"
    else:
        headway = "Every ~20–30 mins (Scheduled Service)"

    fare_non_ac = 25 if total_stops >= 20 else (15 if total_stops >= 10 else 10)
    fare_ac = 60 if total_stops >= 20 else 40

    return {
        "route": sname,
        "route_short_name": sname,
        "route_long_name": lname,
        "trip_headsign": best_headsign,
        "service_type": service_label,
        "service_type_code": service_type,
        "service_type_name": service_label,
        "origin": origin_term,
        "origin_terminus": origin_term,
        "destination": dest_term,
        "destination_terminus": dest_term,
        "total_stops": total_stops,
        "distance_km": round(total_distance_km, 1),
        "estimated_duration_min": estimated_duration_min,
        "trips_per_day": daily_trips,
        "operating_hours": "05:00 AM – 11:15 PM",
        "headway_desc": headway,
        "fare_str": fare_text,
        "fares": {
            "non_ac": fare_non_ac,
            "ac_vajra": fare_ac,
            "shakti_free": shakti_eligible,
            "daily_pass_accepted": (service_type != "VAJRA_AC" and service_type != "AIRPORT_AC"),
        },
        "schedule": {
            "first_bus": "05:15 AM",
            "last_bus": "11:00 PM",
        },
        "shakti_eligible": shakti_eligible,
        "pass_info": pass_text,
        "stops": stops_payload,
    }
