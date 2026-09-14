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


@app.get("/api/health")
def health():
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) as count FROM stops")
        count = cur.fetchone()["count"]
        conn.close()
        return {"status": "ok", "stops_indexed": count}
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/api/stops/search")
def search_stops(q: str = Query(..., min_length=2), limit: int = 8):
    """
    Fast substring and prefix search for stops across Bengaluru Urban and Rural.
    """
    term = q.strip()
    if not term:
        return []

    conn = get_db_connection()
    cur = conn.cursor()
    # Prioritize prefix match, then substring match
    cur.execute(
        """
        SELECT stop_id, stop_name, stop_desc, stop_lat, stop_lon
        FROM stops
        WHERE stop_name LIKE ? OR stop_desc LIKE ?
        ORDER BY 
            CASE 
                WHEN stop_name LIKE ? THEN 1
                WHEN stop_desc LIKE ? THEN 2
                ELSE 3
            END,
            stop_name ASC
        LIMIT ?
        """,
        (f"%{term}%", f"%{term}%", f"{term}%", f"{term}%", limit),
    )
    rows = cur.fetchall()
    conn.close()

    results = []
    seen = set()
    for r in rows:
        key = (r["stop_name"], round(r["stop_lat"], 4), round(r["stop_lon"], 4))
        if key in seen:
            continue
        seen.add(key)
        results.append({
            "stop_id": r["stop_id"],
            "stop_name": r["stop_name"],
            "stop_desc": r["stop_desc"] or "",
            "lat": r["stop_lat"],
            "lon": r["stop_lon"],
        })
    return results


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
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Mount static frontend
frontend_dir = os.path.join(BASE_DIR, "frontend")
os.makedirs(frontend_dir, exist_ok=True)
app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
