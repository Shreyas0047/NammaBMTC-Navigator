"""
Spatial index and proximity functions for BMTC stops.
"""

import math
from typing import List, Tuple
from engine.db import get_db_connection
from engine.models import Stop

# Average conversion factors near Bengaluru (~12.97 deg N)
# 1 degree latitude ~= 110,574 meters
# 1 degree longitude ~= 111,320 * cos(12.97 deg) ~= 108,480 meters
LAT_DEG_TO_METERS = 110574.0
LON_DEG_TO_METERS = 108480.0


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371000.0  # Earth radius in meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2.0 * R * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))


def find_nearby_stops(lat: float, lon: float, radius_meters: float = 800.0) -> List[Tuple[Stop, float]]:
    """
    Finds all BMTC stops within radius_meters of (lat, lon).
    Returns a list of (Stop, distance_in_meters) sorted by distance ascending.
    """
    dlat = radius_meters / LAT_DEG_TO_METERS
    dlon = radius_meters / LON_DEG_TO_METERS

    min_lat, max_lat = lat - dlat, lat + dlat
    min_lon, max_lon = lon - dlon, lon + dlon

    conn = get_db_connection(readonly=True)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT stop_id, stop_name, stop_desc, stop_lat, stop_lon, zone_id
        FROM stops
        WHERE stop_lat BETWEEN ? AND ?
          AND stop_lon BETWEEN ? AND ?
        """,
        (min_lat, max_lat, min_lon, max_lon),
    )
    rows = cur.fetchall()
    conn.close()

    results = []
    for r in rows:
        slat = r["stop_lat"]
        slon = r["stop_lon"]
        dist = haversine(lat, lon, slat, slon)
        if dist <= radius_meters:
            s = Stop(
                stop_id=r["stop_id"],
                stop_name=r["stop_name"],
                stop_desc=r["stop_desc"] or "",
                lat=slat,
                lon=slon,
                zone_id=r["zone_id"] or "",
            )
            results.append((s, dist))

    results.sort(key=lambda x: x[1])
    return results
