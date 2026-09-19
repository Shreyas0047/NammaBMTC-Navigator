"""
BMTC Boarding Point Recommender - Web Backend Server.
Lightweight FastAPI application providing transit search, candidate ranking API,
and static frontend serving.
"""

import os
import sys
from typing import Optional
from fastapi import FastAPI, Query, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from engine.db import get_db_connection
from engine.ranker import rank_boarding_points
from engine.spatial_index import haversine
from engine.live_tracker import get_live_route_telemetry
from engine.intermodal import find_intermodal_route
from data.metro_network import METRO_LINES, get_all_lines_polylines

app = FastAPI(
    title="NammaBMTC Navigator API",
    description="Destination-aware BMTC transit boarding and multi-transfer routing recommendations for Bengaluru Urban & Rural",
    version="1.0.0",
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class RecommendRequest(BaseModel):
    origin_lat: float
    origin_lon: float
    dest_lat: float
    dest_lon: float
    origin_name: Optional[str] = "Current Location"
    dest_name: Optional[str] = "Destination"
    service_filter: Optional[str] = "ALL"


@app.api_route("/health", methods=["GET", "HEAD"])
@app.api_route("/api/health", methods=["GET", "HEAD"])
def health():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM stops")
        count = cur.fetchone()["count"]
        conn.close()
        return {
            "status": "healthy",
            "service": "NammaBMTC Navigator",
            "version": "1.0.0",
            "stops_indexed": count
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


from engine.stop_resolver import (
    resolve_search_term,
    clean_stop_display_name,
    LANDMARK_ALIASES,
)


@app.get("/api/stops/search")
def search_stops(
    q: str = Query(..., min_length=2),
    user_lat: Optional[float] = Query(None),
    user_lon: Optional[float] = Query(None),
    limit: int = 8,
):
    """
    Fast, landmark-aware & phonetic search for stops across Bengaluru Urban and Rural.
    Resolves popular tech parks, colloquial landmarks, hospitals, malls, and Kannada/English variants.
    Provides clean display names and real-time distance from user.
    """
    term = q.strip()
    if not term:
        return []

    norm = term.lower()
    primary, candidates = resolve_search_term(norm)

    # Build SQL search patterns for verbatim query, landmark resolution, and phonetic candidates
    patterns = []
    for c in candidates:
        patterns.append(f"%{c}%")
    if f"%{norm}%" not in patterns:
        patterns.append(f"%{norm}%")

    where_clauses = " OR ".join(["stop_name LIKE ?" for _ in patterns])

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        f"""
        SELECT stop_id, stop_name, stop_desc, stop_lat, stop_lon
        FROM stops
        WHERE {where_clauses}
        LIMIT 45
        """,
        patterns,
    )
    rows = cur.fetchall()
    conn.close()

    results = []
    seen = set()
    ranked = []

    for r in rows:
        raw_name = r["stop_name"].strip()
        clean_name = clean_stop_display_name(raw_name)
        if clean_name in seen:
            continue
        seen.add(clean_name)

        dist_km = None
        if isinstance(user_lat, (int, float)) and isinstance(user_lon, (int, float)):
            dist_km = round(haversine(user_lat, user_lon, r["stop_lat"], r["stop_lon"]) / 1000.0, 1)

        # Relevance scoring
        c_lower = clean_name.lower()
        p_lower = primary.lower()
        if c_lower == p_lower:
            priority = 0
        elif c_lower.startswith(p_lower):
            priority = 1
        elif p_lower in c_lower:
            priority = 2
        elif c_lower.startswith(norm):
            priority = 3
        elif norm in c_lower:
            priority = 4
        else:
            priority = 5

        dist_tiebreaker = dist_km if dist_km is not None else 999.0
        ranked.append((priority, dist_tiebreaker, len(clean_name), {
            "stop_id": r["stop_id"],
            "stop_name": clean_name,
            "raw_stop_name": raw_name,
            "stop_desc": clean_stop_display_name(r["stop_desc"] or ""),
            "lat": r["stop_lat"],
            "lon": r["stop_lon"],
            "dist_km": dist_km,
        }))

    ranked.sort(key=lambda x: (x[0], x[1], x[2]))
    return [item[3] for item in ranked[:limit]]


@app.post("/api/recommend")
def recommend(req: RecommendRequest):
    """
    Evaluates candidate stops and returns destination-aware ranked boarding recommendations.
    """
    print(f"RECOMMEND REQUEST: origin=({req.origin_lat}, {req.origin_lon}, '{req.origin_name}') dest=({req.dest_lat}, {req.dest_lon}, '{req.dest_name}')")
    try:
        rec = rank_boarding_points(
            origin_lat=req.origin_lat,
            origin_lon=req.origin_lon,
            dest_lat=req.dest_lat,
            dest_lon=req.dest_lon,
            origin_name=req.origin_name or "Current Location",
            dest_name=req.dest_name or "Destination",
            service_filter=req.service_filter or "ALL",
        )

        # Calculate estimated bus travel time for intermodal comparison
        bus_mins = None
        if rec.primary_candidate:
            walk_min = rec.primary_candidate.walk_duration_min
            stops_count = 15
            if rec.primary_candidate.viable_routes:
                stops_count = rec.primary_candidate.viable_routes[0].transit_stops_count
            elif rec.primary_candidate.leg1_routes and rec.primary_candidate.leg2_routes:
                stops_count = rec.primary_candidate.leg1_routes[0].transit_stops_count + rec.primary_candidate.leg2_routes[0].transit_stops_count
            transfer_penalty = 12 if not rec.primary_candidate.is_direct else 0
            bus_mins = walk_min + int(stops_count * 2.8) + transfer_penalty

        # Check for Namma Metro (BMRCL) intermodal transit option
        metro_opt = find_intermodal_route(
            origin_lat=req.origin_lat,
            origin_lon=req.origin_lon,
            dest_lat=req.dest_lat,
            dest_lon=req.dest_lon,
            bus_travel_time_mins=bus_mins,
        )

        return {
            "status": rec.status,
            "message": rec.message,
            "origin": {
                "name": rec.origin_name,
                "lat": rec.origin_lat,
                "lon": rec.origin_lon,
            },
            "destination": {
                "name": rec.dest_name,
                "lat": rec.dest_lat,
                "lon": rec.dest_lon,
            },
            "primary": rec.primary_candidate.to_dict() if rec.primary_candidate else None,
            "alternatives": [c.to_dict() for c in rec.ranked_candidates[1:5]],
            "total_viable_stops": len(rec.ranked_candidates),
            "metro_option": metro_opt,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/metro/network")
def metro_network():
    """Returns metadata and polyline coordinates for all Namma Metro lines."""
    return {
        "lines": METRO_LINES,
        "polylines": get_all_lines_polylines(),
    }


@app.get("/api/live-bus")
def live_bus_telemetry(
    route: str = Query(..., description="BMTC route number e.g. 365, 500-D, KIA-8"),
    orig_lat: float = Query(..., description="Boarding stop latitude"),
    orig_lon: float = Query(..., description="Boarding stop longitude"),
    dest_lat: Optional[float] = Query(None, description="Alighting stop latitude"),
    dest_lon: Optional[float] = Query(None, description="Alighting stop longitude"),
):
    """
    Returns real-time GPS telemetry from BMTC's Vehicle Tracking and Monitoring System (VTMS).
    Locates active buses, determines approaching vehicles, and calculates ETAs.
    """
    try:
        data = get_live_route_telemetry(
            route_no=route,
            orig_lat=orig_lat,
            orig_lon=orig_lon,
            dest_lat=dest_lat,
            dest_lon=dest_lon,
        )
        return data
    except Exception as e:
        return {
            "live": False,
            "route": route,
            "reason": f"Live telemetry lookup error: {str(e)}",
            "approaching_count": 0,
            "nearest_bus": None,
            "approaching_buses": [],
            "all_active_buses": [],
        }


# Mount static frontend
frontend_dir = os.path.join(BASE_DIR, "frontend")
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
