#!/usr/bin/env python3
"""
Comprehensive Pre-Deployment Verification Script for NammaBMTC Navigator.
Tests all endpoints, routing across diverse corridors, live telemetry, search aliases, and static assets.
"""

import sys
import os
import json
import time
import urllib.request
import urllib.parse

BASE_URL = "http://localhost:8000"

def get(path):
    url = f"{BASE_URL}{path}"
    req = urllib.request.Request(url, headers={"User-Agent": "NammaBMTC-Verifier/1.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read()
        if "text" in content_type or "json" in content_type or "xml" in content_type or "javascript" in content_type:
            return resp.status, raw.decode("utf-8")
        return resp.status, raw

def post_json(path, data):
    url = f"{BASE_URL}{path}"
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", "User-Agent": "NammaBMTC-Verifier/1.0"}
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return resp.status, json.loads(resp.read().decode("utf-8"))

def main():
    print("=" * 70)
    print("🚀 NAMMABMTC NAVIGATOR - PRE-DEPLOYMENT VERIFICATION TEST")
    print("=" * 70)
    
    passed_tests = 0
    total_tests = 0

    def assert_test(name, condition, detail=""):
        nonlocal passed_tests, total_tests
        total_tests += 1
        if condition:
            passed_tests += 1
            print(f"  ✅ [PASS] {name} {f'({detail})' if detail else ''}")
        else:
            print(f"  ❌ [FAIL] {name} {f'({detail})' if detail else ''}")

    # 1. Health Checks
    print("\n--- 1. Health & Server Endpoints ---")
    try:
        status, body = get("/health")
        data = json.loads(body)
        assert_test("GET /health", status == 200 and data.get("status") == "healthy", f"{data.get('stops_indexed')} stops")
    except Exception as e:
        assert_test("GET /health", False, str(e))

    try:
        status, body = get("/api/health")
        data = json.loads(body)
        assert_test("GET /api/health", status == 200 and data.get("status") == "healthy")
    except Exception as e:
        assert_test("GET /api/health", False, str(e))

    # 2. Search & Aliases
    print("\n--- 2. Stop Search & Smart Aliases ---")
    alias_queries = [
        ("majestic", ["KEMPEGOWDA", "KBS", "MAJESTIC"]),
        ("kbs", ["KEMPEGOWDA", "KBS"]),
        ("airport", ["AIRPORT"]),
        ("silk board", ["SILK BOARD"]),
        ("itpl", ["ITPL"]),
        ("ecity", ["ELECTRONIC CITY"]),
        ("whitefield", ["WHITE FIELD", "WHITEFIELD"]),
        ("kr market", ["MARKET", "KR MARKET"])
    ]
    for q, expected_keywords in alias_queries:
        try:
            status, body = get(f"/api/stops/search?q={urllib.parse.quote(q)}")
            data = json.loads(body)
            has_match = any(any(kw in s["stop_name"].upper() for kw in expected_keywords) for s in data)
            assert_test(f"Alias search '{q}'", status == 200 and has_match, f"{len(data)} results, top: {data[0]['stop_name'] if data else 'none'}")
        except Exception as e:
            assert_test(f"Alias search '{q}'", False, str(e))

    # Distance relative to user lat/lon
    try:
        status, body = get("/api/stops/search?q=metro&user_lat=12.9716&user_lon=77.5946")
        data = json.loads(body)
        has_dist = len(data) > 0 and "dist_km" in data[0] and data[0]["dist_km"] is not None
        assert_test("Search with GPS distance badges", has_dist, f"Nearest: {data[0]['stop_name']} ({data[0].get('dist_km')} km)")
    except Exception as e:
        assert_test("Search with GPS distance badges", False, str(e))

    # 3. Route Recommendation Use Cases Across Corridors
    print("\n--- 3. Diverse Transit Corridors & Routing ---")
    corridors = [
        {
            "name": "Central to IT Hub: Majestic to Electronic City",
            "origin_lat": 12.9774, "origin_lon": 77.5708, "origin_name": "Kempegowda Bus Station (Majestic)",
            "dest_lat": 12.8452, "dest_lon": 77.6602, "dest_name": "Electronic City",
        },
        {
            "name": "Peri-Urban Arterial: BTL College to Anekal",
            "origin_lat": 12.8258, "origin_lon": 77.6760, "origin_name": "BTL Institute of Technology",
            "dest_lat": 12.7107, "dest_lon": 77.6974, "dest_name": "Anekal Bus Stand",
        },
        {
            "name": "ORR Express: Central Silk Board to Hebbal",
            "origin_lat": 12.9176, "origin_lon": 77.6238, "origin_name": "Central Silk Board",
            "dest_lat": 13.0358, "dest_lon": 77.5970, "dest_name": "Hebbal Flyover",
        },
        {
            "name": "Airport Vayu Vajra: Majestic to Kempegowda Intl Airport",
            "origin_lat": 12.9774, "origin_lon": 77.5708, "origin_name": "Majestic",
            "dest_lat": 13.1986, "dest_lon": 77.7066, "dest_name": "Kempegowda International Airport",
        },
        {
            "name": "Tech Corridor: Whitefield / ITPL to Majestic",
            "origin_lat": 12.9863, "origin_lon": 77.7378, "origin_name": "ITPL Main Gate",
            "dest_lat": 12.9774, "dest_lon": 77.5708, "dest_name": "Kempegowda Bus Station",
        },
        {
            "name": "South to North: Banashankari to Yelahanka",
            "origin_lat": 12.9155, "origin_lon": 77.5736, "origin_name": "Banashankari TTMC",
            "dest_lat": 13.1007, "dest_lon": 77.5963, "dest_name": "Yelahanka Old Town",
        },
        {
            "name": "West to East: Kengeri to ITPL",
            "origin_lat": 12.9081, "origin_lon": 77.4880, "origin_name": "Kengeri TTMC",
            "dest_lat": 12.9863, "dest_lon": 77.7378, "dest_name": "ITPL",
        },
        {
            "name": "Rural Fringe: Hoskote to Majestic",
            "origin_lat": 13.0712, "origin_lon": 77.7981, "origin_name": "Hoskote Bus Stand",
            "dest_lat": 12.9774, "dest_lon": 77.5708, "dest_name": "Majestic",
        },
        {
            "name": "Short City Hop: Indiranagar to MG Road",
            "origin_lat": 12.9784, "origin_lon": 77.6408, "origin_name": "Indiranagar 100ft Rd",
            "dest_lat": 12.9756, "dest_lon": 77.6066, "dest_name": "MG Road Metro",
        },
        {
            "name": "Industrial Belt: Jigani to Electronic City",
            "origin_lat": 12.7836, "origin_lon": 77.6420, "origin_name": "Jigani APC Circle",
            "dest_lat": 12.8452, "dest_lon": 77.6602, "dest_name": "Electronic City",
        }
    ]

    for corr in corridors:
        try:
            status, res = post_json("/api/recommend", corr)
            primary = res.get("primary")
            has_rec = primary is not None
            if has_rec:
                stop_name = primary.get("stop_name", "Unknown Stop")
                direct = primary.get("is_direct", False)
                if direct:
                    routes = primary.get("routes", [])
                    route_str = ", ".join([r.get("route", "") for r in routes[:3]])
                    ttype = "Direct"
                else:
                    transfer_stop = primary.get("transfer_stop_name", "Transfer Hub")
                    routes = primary.get("leg1_routes", [])
                    l2_routes = primary.get("leg2_routes", [])
                    route_str = f"Leg1: {', '.join([r.get('route', '') for r in routes[:2]])} -> Leg2: {', '.join([r.get('route', '') for r in l2_routes[:2]])}"
                    ttype = f"Transfer via {transfer_stop}"
                assert_test(corr["name"], True, f"{ttype} at '{stop_name}' | {route_str}")
            else:
                assert_test(corr["name"], False, "No recommendation found")
        except Exception as e:
            assert_test(corr["name"], False, str(e))

    # 4. Live VTMS Telemetry API
    print("\n--- 4. Live BMTC VTMS Telemetry ---")
    telemetry_tests = [
        ("Single route 500-D (ORR)", "500-D", 12.9176, 77.6238, 13.0358, 77.5970),
        ("Single route 365 (Bannerghatta)", "365", 12.9774, 77.5708, 12.7107, 77.6974),
        ("Multi-route comma separated (365, 365-P, 366)", "365, 365-P, 366", 12.9774, 77.5708, 12.7107, 77.6974),
        ("Airport Route KIA-9", "KIA-9", 12.9774, 77.5708, 13.1986, 77.7066),
    ]

    for label, route, olat, olon, dlat, dlon in telemetry_tests:
        try:
            status, body = get(f"/api/live-bus?route={urllib.parse.quote(route)}&orig_lat={olat}&orig_lon={olon}&dest_lat={dlat}&dest_lon={dlon}")
            data = json.loads(body)
            # Response should always be structured even if live API is temporarily empty
            is_valid = "live" in data and "approaching_count" in data and "all_active_buses" in data
            buses_found = len(data.get("all_active_buses", []))
            nearest = data.get("nearest_bus")
            detail = f"{buses_found} buses active, nearest ETA: {nearest.get('eta_mins')}m" if nearest else f"{buses_found} active buses"
            assert_test(f"VTMS {label}", is_valid, detail)
        except Exception as e:
            assert_test(f"VTMS {label}", False, str(e))

    # 5. Static Assets & PWA
    print("\n--- 5. Static Assets & Frontend Integrity ---")
    static_files = [
        ("/", 200, "text/html"),
        ("/index.html", 200, "text/html"),
        ("/style.css", 200, "text/css"),
        ("/app.js", 200, "javascript"),
        ("/manifest.json", 200, "json"),
        ("/robots.txt", 200, "text/plain"),
        ("/sitemap.xml", 200, "xml"),
        ("/assets/logo.svg", 200, "image/svg+xml"),
        ("/assets/app-icon.jpg", 200, "image/jpeg"),
    ]

    for path, expected_status, expected_mime in static_files:
        try:
            status, body = get(path)
            assert_test(f"Static file: {path}", status == expected_status, f"HTTP {status}")
        except Exception as e:
            assert_test(f"Static file: {path}", False, str(e))

    # Verify Popular Hubs removed from HTML
    try:
        _, html = get("/")
        has_popular_hubs = "popular-hubs" in html or "Popular Hubs" in html
        assert_test("Popular Hubs completely removed from DOM", not has_popular_hubs)
    except Exception as e:
        assert_test("Popular Hubs completely removed from DOM", False, str(e))

    # 6. Namma Metro (BMRCL) Intermodal Routing & API
    print("\n--- 6. Namma Metro (BMRCL) Intermodal Transit ---")
    try:
        status, body = get("/api/metro/network")
        data = json.loads(body)
        has_lines = all(k in data.get("lines", {}) for k in ["PURPLE", "GREEN", "YELLOW"])
        has_poly = len(data.get("polylines", {}).get("PURPLE", [])) == 37
        assert_test("Metro Network API (/api/metro/network)", status == 200 and has_lines and has_poly, f"Purple: {len(data.get('polylines', {}).get('PURPLE', []))} stations, Green: {len(data.get('polylines', {}).get('GREEN', []))}, Yellow: {len(data.get('polylines', {}).get('YELLOW', []))}")
    except Exception as e:
        assert_test("Metro Network API (/api/metro/network)", False, str(e))

    metro_corridors = [
        {
            "label": "Purple Line East-West: Majestic to ITPL",
            "req": {"origin_lat": 12.9757, "origin_lon": 77.5728, "dest_lat": 12.9863, "dest_lon": 77.7479, "origin_name": "Majestic", "dest_name": "ITPL"},
            "expected_line": "PURPLE",
            "min_stations": 15,
        },
        {
            "label": "Green Line South-North: Banashankari to Yeshwanthpur",
            "req": {"origin_lat": 12.9152, "origin_lon": 77.5736, "dest_lat": 13.0231, "dest_lon": 77.5501, "origin_name": "Banashankari", "dest_name": "Yeshwanthpur"},
            "expected_line": "GREEN",
            "min_stations": 12,
        },
        {
            "label": "Yellow Line South Tech: Silk Board to Electronic City",
            "req": {"origin_lat": 12.9176, "origin_lon": 77.6227, "dest_lat": 12.8468, "dest_lon": 77.6758, "origin_name": "Central Silk Board", "dest_name": "Electronic City"},
            "expected_line": "YELLOW",
            "min_stations": 6,
        },
        {
            "label": "West to East Full Corridor: Kengeri to ITPL",
            "req": {"origin_lat": 12.9079, "origin_lon": 77.4787, "dest_lat": 12.9863, "dest_lon": 77.7479, "origin_name": "Kengeri", "dest_name": "ITPL"},
            "expected_line": "PURPLE",
            "min_stations": 30,
        },
    ]

    for mc in metro_corridors:
        try:
            status, res = post_json("/api/recommend", mc["req"])
            mo = res.get("metro_option")
            is_valid = (
                mo is not None
                and mo.get("available") is True
                and mo.get("primary_line") == mc["expected_line"]
                and mo.get("total_stations", 0) >= mc["min_stations"]
                and len(mo.get("steps", [])) >= 3
            )
            detail = f"{mo.get('primary_line')} Line, {mo.get('total_stations')} stations, saves ~{mo.get('time_saved_mins')}m, fare ₹{mo.get('fare')}" if mo else "No metro option"
            assert_test(f"Intermodal: {mc['label']}", is_valid, detail)
        except Exception as e:
            assert_test(f"Intermodal: {mc['label']}", False, str(e))

    # 7. AC vs Non-AC Bus Service Filtering & Fare Indicators
    print("\n--- 7. AC vs Non-AC Bus Service Filter & Fare Indicators ---")
    filter_tests = [
        {
            "name": "Non-AC Ordinary Filter (ITPL -> Majestic)",
            "req": {"origin_lat": 12.9863, "origin_lon": 77.7378, "dest_lat": 12.9774, "dest_lon": 77.5708, "service_filter": "NON_AC"},
            "check": lambda p: (
                p.get("service_tag") == "Non-AC Ordinary"
                and p.get("has_ac") is False
                and all(not r.get("is_ac") for r in (p.get("routes") or []))
                and "₹" in p.get("fare_range_str", "")
            ),
        },
        {
            "name": "AC Vajra Volvo Filter (ITPL -> Majestic)",
            "req": {"origin_lat": 12.9863, "origin_lon": 77.7378, "dest_lat": 12.9774, "dest_lon": 77.5708, "service_filter": "AC"},
            "check": lambda p: (
                p.get("service_tag") == "AC Vajra / Vayu Vajra"
                and p.get("has_ac") is True
                and any(r.get("is_ac") for r in (p.get("routes") or []))
                and p.get("min_fare", 0) >= 50
            ),
        },
        {
            "name": "Airport Vayu Vajra AC (Majestic -> Airport)",
            "req": {"origin_lat": 12.9774, "origin_lon": 77.5708, "dest_lat": 13.1986, "dest_lon": 77.7066, "service_filter": "AC"},
            "check": lambda p: (
                p.get("has_ac") is True
                and any(r.get("route", "").startswith("KIA-") for r in (p.get("routes") or []))
                and p.get("min_fare", 0) >= 150
            ),
        },
        {
            "name": "Unfiltered All Services with Fare Range (Majestic -> Silk Board)",
            "req": {"origin_lat": 12.9774, "origin_lon": 77.5708, "dest_lat": 12.9176, "dest_lon": 77.6238, "service_filter": "ALL"},
            "check": lambda p: (
                "fare_range_str" in p
                and "min_fare" in p
                and "max_fare" in p
                and len(p.get("routes", [])) > 0
                and "fare_text" in p.get("routes", [])[0]
            ),
        },
    ]

    for ft in filter_tests:
        try:
            status, res = post_json("/api/recommend", ft["req"])
            primary = res.get("primary")
            is_valid = primary is not None and ft["check"](primary)
            routes = [r.get("route") for r in (primary.get("routes", []) if primary else [])]
            detail = f"Fare: {primary.get('fare_range_str')}, Tag: {primary.get('service_tag')}, Routes: {routes[:2]}" if primary else "No primary"
            assert_test(ft["name"], is_valid, detail)
        except Exception as e:
            assert_test(ft["name"], False, str(e))

    print("\n" + "=" * 70)
    print(f"📊 VERIFICATION SUMMARY: {passed_tests}/{total_tests} tests passed ({round(passed_tests/total_tests*100, 1)}%)")
    print("=" * 70)

    if passed_tests == total_tests:
        print("🎉 ALL SYSTEMS GO! Ready for 100% Free Production Deployment.")
        return 0
    else:
        print("⚠️ Some tests failed. Please inspect logs above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
