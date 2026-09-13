#!/usr/bin/env python3
"""
Phase 1: Empirical Walking Evaluation Script.
Compares:
1. Straight-line Haversine distance (baseline).
2. Manhattan / Grid distance approximation.
3. Real walking route via OpenStreetMap Public Routing API (OSRM Foot profile).

Measures walk distance, walk time estimate, and routing reliability across sample
Bengaluru boarding stop walk pairs.
"""

import json
import math
import os
import sys
import time
import urllib.parse
import urllib.request

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BENCHMARK_PATH = os.path.join(BASE_DIR, "benchmarks", "journeys.json")
WALKING_SPEED_MPS = 1.2  # 1.2 m/s = ~4.3 km/h (standard human walking speed)


def haversine_distance(lat1, lon1, lat2, lon2):
    R = 6371000  # meters
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2.0) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2.0) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def query_osrm_foot(lat1, lon1, lat2, lon2):
    """
    Queries public OSRM foot demo server to test pedestrian network routing in Bengaluru.
    Returns (distance_meters, duration_seconds) or (None, None) if unreachable.
    """
    url = f"https://routing.openstreetmap.de/routed-foot/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=false"
    req = urllib.request.Request(url, headers={"User-Agent": "BMTC-Recommender-WalkAudit/1.0"})
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if data.get("code") == "Ok" and "routes" in data and len(data["routes"]) > 0:
                route = data["routes"][0]
                return route["distance"], route["duration"]
    except Exception as e:
        return None, None
    return None, None


def main():
    print("=" * 70)
    print("PHASE 1: EMPIRICAL WALKING DISTANCE EVALUATION (BENGALURU)")
    print("=" * 70)

    if not os.path.exists(BENCHMARK_PATH):
        print(f"Benchmark file {BENCHMARK_PATH} not found.")
        sys.exit(1)

    with open(BENCHMARK_PATH, "r") as f:
        benchmarks = json.load(f)

    # Load stops
    stops_file = os.path.join(BASE_DIR, "data", "gtfs", "stops.txt")
    stops = {}
    with open(stops_file, "r", encoding="utf-8") as f:
        import csv
        for row in csv.DictReader(f):
            stops[row["stop_id"]] = {
                "name": row["stop_name"],
                "desc": row.get("stop_desc", ""),
                "lat": float(row["stop_lat"]),
                "lon": float(row["stop_lon"]),
            }

    results = []
    print(f"{'Journey ID':<32} | {'Stop Name':<28} | {'Haversine':<10} | {'OSM Foot':<10} | {'Ratio (OSM/Hav)'}")
    print("-" * 105)

    for b in benchmarks:
        jid = b["id"]
        origin = b["origin"]
        target_stop_id = b["expected"].get("primary_boarding_stop_id")
        if not target_stop_id or target_stop_id not in stops:
            continue

        stop = stops[target_stop_id]
        h_dist = haversine_distance(origin["lat"], origin["lon"], stop["lat"], stop["lon"])
        h_time = h_dist / WALKING_SPEED_MPS

        # Query OSRM foot API
        osm_dist, osm_time = query_osrm_foot(origin["lat"], origin["lon"], stop["lat"], stop["lon"])
        time.sleep(0.5)  # respectful rate limit

        ratio_str = f"{osm_dist / h_dist:.2f}x" if (osm_dist and h_dist > 0) else "N/A"
        osm_dist_str = f"{osm_dist:.0f} m" if osm_dist else "Timeout/Err"
        
        print(f"{jid:<32} | {stop['name'][:26]:<28} | {h_dist:.0f} m      | {osm_dist_str:<10} | {ratio_str}")
        results.append({
            "journey": jid,
            "haversine_m": h_dist,
            "osrm_m": osm_dist,
            "ratio": (osm_dist / h_dist) if (osm_dist and h_dist > 0) else None
        })

    valid_ratios = [r["ratio"] for r in results if r["ratio"] is not None]
    if valid_ratios:
        avg_ratio = sum(valid_ratios) / len(valid_ratios)
        print("-" * 105)
        print(f"Empirical Detour Multiplier for Bengaluru walking: ~{avg_ratio:.2f}x Haversine distance.")
        print(f"Recommendation for Walking Model:")
        print(f"  - Using straight-line Haversine with empirical street factor ({avg_ratio:.2f}x) gives")
        print(f"    a robust, zero-latency walk estimation (~4.3 km/h walking speed).")
        print(f"  - When high-confidence road network data is available, OSM Foot can refine it,")
        print(f"    but Haversine x {avg_ratio:.2f} provides a zero-downtime, fully offline fallback.")
    print("=" * 70)


if __name__ == "__main__":
    main()
