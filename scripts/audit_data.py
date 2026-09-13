#!/usr/bin/env python3
"""
Audit script for BMTC GTFS feed.
Evaluates:
1. Geographic bounding box (validates Bengaluru Urban + Bengaluru Rural coverage).
2. Key rural/suburban satellite hubs (Nelamangala, Doddaballapura, Devanahalli, Hosakote, Attibele, Bidadi, Harohalli).
3. Stop, Route, Trip, StopTimes inventory.
4. Direction fidelity (direction_id and trip_headsign coverage).
5. Stop sequence monotonicity.
6. Licensing & Provenance.
"""

import csv
import os
import sys

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GTFS_DIR = os.path.join(BASE_DIR, "data", "gtfs")

# Target satellite areas for Bengaluru Rural / Peri-Urban audit
RURAL_HUBS = {
    "Nelamangala": {"lat_min": 13.07, "lat_max": 13.15, "lon_min": 77.35, "lon_max": 77.44},
    "Doddaballapura": {"lat_min": 13.25, "lat_max": 13.35, "lon_min": 77.50, "lon_max": 77.58},
    "Devanahalli / Airport": {"lat_min": 13.18, "lat_max": 13.28, "lon_min": 77.67, "lon_max": 77.76},
    "Hosakote": {"lat_min": 13.04, "lat_max": 13.12, "lon_min": 77.76, "lon_max": 77.85},
    "Attibele / Anekal": {"lat_min": 12.75, "lat_max": 12.82, "lon_min": 77.73, "lon_max": 77.81},
    "Bidadi": {"lat_min": 12.77, "lat_max": 12.85, "lon_min": 77.36, "lon_max": 77.43},
    "Harohalli": {"lat_min": 12.63, "lat_max": 12.72, "lon_min": 77.46, "lon_max": 77.54},
    "Sarjapura": {"lat_min": 12.84, "lat_max": 12.90, "lon_min": 77.76, "lon_max": 77.82},
}


def audit_stops():
    path = os.path.join(GTFS_DIR, "stops.txt")
    if not os.path.exists(path):
        print(f"ERROR: {path} not found.")
        return None

    total_stops = 0
    missing_coords = 0
    min_lat, max_lat = 90.0, -90.0
    min_lon, max_lon = 180.0, -180.0
    hub_counts = {name: 0 for name in RURAL_HUBS}
    named_stops = []

    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_stops += 1
            lat_str = row.get("stop_lat", "").strip()
            lon_str = row.get("stop_lon", "").strip()
            name = row.get("stop_name", "").strip()

            if not lat_str or not lon_str:
                missing_coords += 1
                continue

            try:
                lat = float(lat_str)
                lon = float(lon_str)
            except ValueError:
                missing_coords += 1
                continue

            if lat < min_lat: min_lat = lat
            if lat > max_lat: max_lat = lat
            if lon < min_lon: min_lon = lon
            if lon > max_lon: max_lon = lon

            # Check coverage of key rural hubs
            for hub, b in RURAL_HUBS.items():
                if b["lat_min"] <= lat <= b["lat_max"] and b["lon_min"] <= lon <= b["lon_max"]:
                    hub_counts[hub] += 1

    return {
        "total_stops": total_stops,
        "missing_coords": missing_coords,
        "lat_range": (min_lat, max_lat),
        "lon_range": (min_lon, max_lon),
        "hub_counts": hub_counts,
    }


def audit_routes():
    path = os.path.join(GTFS_DIR, "routes.txt")
    if not os.path.exists(path):
        return None
    total_routes = 0
    route_types = {}
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_routes += 1
            rtype = row.get("route_type", "unknown")
            route_types[rtype] = route_types.get(rtype, 0) + 1
    return {"total_routes": total_routes, "route_types": route_types}


def audit_trips():
    path = os.path.join(GTFS_DIR, "trips.txt")
    if not os.path.exists(path):
        return None
    total_trips = 0
    with_direction = 0
    with_headsign = 0
    directions = {}
    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_trips += 1
            d = row.get("direction_id", "").strip()
            if d in ("0", "1"):
                with_direction += 1
                directions[d] = directions.get(d, 0) + 1
            h = row.get("trip_headsign", "").strip()
            if h:
                with_headsign += 1
    return {
        "total_trips": total_trips,
        "with_direction": with_direction,
        "with_headsign": with_headsign,
        "directions": directions,
    }


def audit_stop_times():
    path = os.path.join(GTFS_DIR, "stop_times.txt")
    if not os.path.exists(path):
        return None
    total_records = 0
    last_trip = None
    last_seq = -1
    seq_violations = 0

    with open(path, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            total_records += 1
            trip_id = row.get("trip_id")
            try:
                seq = int(row.get("stop_sequence", 0))
            except ValueError:
                seq_violations += 1
                continue

            if trip_id == last_trip:
                if seq <= last_seq:
                    seq_violations += 1
            else:
                last_trip = trip_id
            last_seq = seq

    return {
        "total_stop_times": total_records,
        "seq_violations": seq_violations,
    }


def main():
    print("=" * 60)
    print("BMTC GTFS DATASET AUDIT (Urban + Rural Bengaluru)")
    print("=" * 60)

    if not os.path.exists(GTFS_DIR):
        print(f"GTFS directory not found at {GTFS_DIR}. Run fetch_data.py first.")
        sys.exit(1)

    print("\n1. AUDITING STOPS...")
    stops_info = audit_stops()
    if stops_info:
        print(f"  Total stops: {stops_info['total_stops']:,}")
        print(f"  Stops with missing coordinates: {stops_info['missing_coords']}")
        print(f"  Latitude Range:  {stops_info['lat_range'][0]:.4f} to {stops_info['lat_range'][1]:.4f}")
        print(f"  Longitude Range: {stops_info['lon_range'][0]:.4f} to {stops_info['lon_range'][1]:.4f}")
        print("\n  Rural & Satellite Hub Coverage:")
        for hub, count in stops_info["hub_counts"].items():
            status = "✓ COVERED" if count > 0 else "✗ MISSING"
            print(f"    - {hub:<22}: {count:>4} stops  [{status}]")

    print("\n2. AUDITING ROUTES...")
    routes_info = audit_routes()
    if routes_info:
        print(f"  Total distinct routes: {routes_info['total_routes']:,}")
        print(f"  Route types: {routes_info['route_types']}")

    print("\n3. AUDITING TRIPS & DIRECTION FIDELITY...")
    trips_info = audit_trips()
    if trips_info:
        tot = trips_info["total_trips"]
        dir_pct = (trips_info["with_direction"] / tot * 100) if tot else 0
        head_pct = (trips_info["with_headsign"] / tot * 100) if tot else 0
        print(f"  Total trips: {tot:,}")
        print(f"  Trips with valid direction_id (0/1): {trips_info['with_direction']:,} ({dir_pct:.1f}%)")
        print(f"  Trips with non-empty headsign:       {trips_info['with_headsign']:,} ({head_pct:.1f}%)")

    print("\n4. AUDITING STOP TIMES & SEQUENCES...")
    st_info = audit_stop_times()
    if st_info:
        print(f"  Total stop_time entries: {st_info['total_stop_times']:,}")
        print(f"  Stop sequence monotonicity violations: {st_info['seq_violations']}")

    print("\n5. LICENSING & PROVENANCE SUMMARY:")
    print("  - Dataset Source: Sourced via Namma BMTC official app / Vonter bmtc-gtfs")
    print("  - License: Open Data Commons Open Database License (ODbL 1.0)")
    print("  - Copyright Note: Underlying proprietary transit schedule info copyrighted by BMTC")
    print("  - Commercial/Public Constraint: ODbL Share-Alike & Attribution required")
    print("=" * 60)


if __name__ == "__main__":
    main()
