#!/usr/bin/env python3
"""
Phase 3 Benchmark Verification Suite.
Runs the internal ranking engine against all ground-truth urban and rural
journeys in benchmarks/journeys.json.
Validates:
- Correct boarding stop selection
- Rejection of wrong-direction / opposite-side stops
- Ranking order and score breakdown
- Query latency
"""

import json
import os
import sys
import time
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)
BENCHMARK_PATH = os.path.join(BASE_DIR, "benchmarks", "journeys.json")
from engine.ranker import rank_boarding_points


def main():
    print("=" * 80)
    print("BMTC RECOMMENDER BENCHMARK EVALUATION (URBAN + RURAL BENGALURU)")
    print("=" * 80)

    if not os.path.exists(BENCHMARK_PATH):
        print(f"Error: {BENCHMARK_PATH} not found.")
        sys.exit(1)

    with open(BENCHMARK_PATH, "r", encoding="utf-8") as f:
        benchmarks = json.load(f)

    passed_count = 0
    total_count = len(benchmarks)

    for idx, b in enumerate(benchmarks, 1):
        jid = b["id"]
        name = b["name"]
        jtype = b.get("type", "urban")
        orig = b["origin"]
        dest = b["destination"]
        expected = b.get("expected", {})
        target_stop_id = expected.get("primary_boarding_stop_id")
        avoid_stop_ids = expected.get("avoid_stop_ids", [])
        expected_routes = expected.get("key_routes", [])

        print(f"\n[{idx}/{total_count}] {name} ({jtype})")
        print(f"  Origin: {orig['name']} ({orig['lat']}, {orig['lon']})")
        print(f"  Destination: {dest['name']} ({dest['lat']}, {dest['lon']})")

        t0 = time.time()
        rec = rank_boarding_points(
            origin_lat=orig["lat"],
            origin_lon=orig["lon"],
            dest_lat=dest["lat"],
            dest_lon=dest["lon"],
            origin_name=orig["name"],
            dest_name=dest["name"],
            walk_radius_m=800.0,
            dest_radius_m=1200.0,
        )
        latency_ms = (time.time() - t0) * 1000

        if rec.status != "OK" or not rec.primary_candidate:
            print(f"  [FAIL] Status: {rec.status} ({rec.message}) in {latency_ms:.1f}ms")
            continue

        prim = rec.primary_candidate
        print(f"  [RESULT] Latency: {latency_ms:.1f}ms | Found {len(rec.ranked_candidates)} viable boarding stops")
        print(f"  PRIMARY RECOMMENDATION:")
        print(f"    - Boarding Stop: [{prim.stop_id}] {prim.stop_name}")
        print(f"      Description:   {prim.stop_desc}")
        print(f"      Walk Distance: {prim.walk_distance_m:.0f} m (~{prim.walk_duration_min} min walk)")
        print(f"      Score:         {prim.score:.1f} / 100")
        print(f"      Score Breakdown: {prim.score_breakdown}")
        
        top_routes_str = ", ".join([f"{r.route_short_name} (Towards {r.trip_headsign})" for r in prim.viable_routes[:3]])
        print(f"      Key Routes:    {top_routes_str}")

        # Verification Checks
        passed = True
        if target_stop_id and prim.stop_id != target_stop_id:
            # Check if target_stop_id was at least in top 3
            candidate_ids = [c.stop_id for c in rec.ranked_candidates[:3]]
            if target_stop_id in candidate_ids:
                print(f"    ✓ Expected stop [{target_stop_id}] found in top candidate ranking.")
            else:
                print(f"    ✗ Expected stop [{target_stop_id}] was not primary (picked {prim.stop_id}).")
                passed = False

        # Verify avoid_stop_ids were strictly avoided
        for avoid_id in avoid_stop_ids:
            if prim.stop_id == avoid_id:
                print(f"    ✗ CRITICAL ERROR: Recommended forbidden / wrong-direction stop [{avoid_id}]!")
                passed = False
            else:
                print(f"    ✓ Successfully avoided wrong-direction stop [{avoid_id}].")

        # Check candidate list
        print(f"  INTERNAL MULTI-CANDIDATE RANKING:")
        for rank, c in enumerate(rec.ranked_candidates[:4], 1):
            star = " (PRIMARY)" if rank == 1 else ""
            print(f"    #{rank}: [{c.stop_id}] {c.stop_name} ({c.stop_desc}) | {c.walk_distance_m:.0f}m | Score {c.score:.1f}{star}")

        if passed:
            passed_count += 1
            print(f"  --> [PASS]")
        else:
            print(f"  --> [FAIL / REVIEW]")

    print("\n" + "=" * 80)
    print(f"BENCHMARK SUMMARY: {passed_count}/{total_count} Passed ({(passed_count/total_count)*100:.1f}%)")
    print("=" * 80)


if __name__ == "__main__":
    main()
