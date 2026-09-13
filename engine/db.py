"""
GTFS Database Builder and Manager.
Compiles raw GTFS CSV files into a high-performance, indexed SQLite database.
"""

import csv
import os
import sqlite3
import time

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GTFS_DIR = os.path.join(BASE_DIR, "data", "gtfs")
DB_PATH = os.path.join(BASE_DIR, "data", "bmtc.db")


def get_db_connection(readonly=True) -> sqlite3.Connection:
    if not os.path.exists(DB_PATH):
        raise FileNotFoundError(f"Database not found at {DB_PATH}. Run build_db() first.")
    if readonly:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    else:
        conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def build_db(force: bool = False):
    if os.path.exists(DB_PATH) and not force:
        print(f"Database already exists at {DB_PATH}. Skipping build.")
        return

    print(f"Building SQLite database from GTFS at {DB_PATH} ...")
    start_time = time.time()

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # SQLite performance pragmas for initial bulk load
    cur.execute("PRAGMA synchronous = OFF;")
    cur.execute("PRAGMA journal_mode = MEMORY;")
    cur.execute("PRAGMA cache_size = 100000;")

    # 1. Stops table
    print("  Creating stops table...")
    cur.execute("""
        CREATE TABLE stops (
            stop_id TEXT PRIMARY KEY,
            stop_name TEXT NOT NULL,
            cluster_name TEXT,
            stop_desc TEXT,
            stop_lat REAL NOT NULL,
            stop_lon REAL NOT NULL,
            zone_id TEXT
        );
    """)
    import re

    def compute_cluster(name: str) -> str:
        n = name.strip()
        n = re.sub(r'^CS-', '', n)
        n = re.sub(r'\s*-\s*Platform\s*[0-9A-Za-z.\s]+', '', n, flags=re.IGNORECASE)
        m = re.sub(r'\s*\([^)]*\)', '', n).strip()
        if m:
            n = m
        n = re.sub(r'\bK\.R\.Market\b', 'KR Market', n, flags=re.IGNORECASE)
        n = re.sub(r'\bYeshawanthapura\b', 'Yeshwanthpur', n, flags=re.IGNORECASE)
        return n.strip()

    stops_file = os.path.join(GTFS_DIR, "stops.txt")
    with open(stops_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        stop_rows = [
            (
                r["stop_id"].strip(),
                r["stop_name"].strip(),
                compute_cluster(r["stop_name"]),
                r.get("stop_desc", "").strip(),
                float(r["stop_lat"]),
                float(r["stop_lon"]),
                r.get("zone_id", "").strip(),
            )
            for r in reader
            if r.get("stop_lat") and r.get("stop_lon")
        ]
        cur.executemany("INSERT INTO stops VALUES (?, ?, ?, ?, ?, ?, ?);", stop_rows)
    print(f"  Inserted {len(stop_rows):,} stops.")

    # 2. Routes table
    print("  Creating routes table...")
    cur.execute("""
        CREATE TABLE routes (
            route_id TEXT PRIMARY KEY,
            route_short_name TEXT NOT NULL,
            route_long_name TEXT NOT NULL,
            route_type INTEGER
        );
    """)
    routes_file = os.path.join(GTFS_DIR, "routes.txt")
    with open(routes_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        route_rows = [
            (
                r["route_id"].strip(),
                r.get("route_short_name", "").strip(),
                r.get("route_long_name", "").strip(),
                int(r.get("route_type", 3)),
            )
            for r in reader
        ]
        cur.executemany("INSERT INTO routes VALUES (?, ?, ?, ?);", route_rows)
    print(f"  Inserted {len(route_rows):,} routes.")

    # 3. Trips table
    print("  Creating trips table...")
    cur.execute("""
        CREATE TABLE trips (
            trip_id TEXT PRIMARY KEY,
            route_id TEXT NOT NULL,
            service_id TEXT,
            trip_headsign TEXT NOT NULL,
            direction_id INTEGER NOT NULL
        );
    """)
    trips_file = os.path.join(GTFS_DIR, "trips.txt")
    with open(trips_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        trip_rows = [
            (
                r["trip_id"].strip(),
                r["route_id"].strip(),
                r.get("service_id", "").strip(),
                r.get("trip_headsign", "").strip(),
                int(r.get("direction_id", 0)),
            )
            for r in reader
        ]
        cur.executemany("INSERT INTO trips VALUES (?, ?, ?, ?, ?);", trip_rows)
    print(f"  Inserted {len(trip_rows):,} trips.")

    # 4. Stop Times table
    print("  Creating stop_times table...")
    cur.execute("""
        CREATE TABLE stop_times (
            trip_id TEXT NOT NULL,
            stop_id TEXT NOT NULL,
            stop_sequence INTEGER NOT NULL
        );
    """)
    st_file = os.path.join(GTFS_DIR, "stop_times.txt")
    with open(st_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        st_rows = [
            (
                r["trip_id"].strip(),
                r["stop_id"].strip(),
                int(r["stop_sequence"]),
            )
            for r in reader
        ]
        cur.executemany("INSERT INTO stop_times VALUES (?, ?, ?);", st_rows)
    print(f"  Inserted {len(st_rows):,} stop_times.")

    # 5. Create Indexes
    print("  Creating indices for fast lookups...")
    cur.execute("CREATE INDEX idx_stops_lat_lon ON stops (stop_lat, stop_lon);")
    cur.execute("CREATE INDEX idx_stops_cluster ON stops (cluster_name);")
    cur.execute("CREATE INDEX idx_trips_route ON trips (route_id);")
    cur.execute("CREATE INDEX idx_st_stop_trip ON stop_times (stop_id, trip_id);")
    cur.execute("CREATE INDEX idx_st_trip_seq ON stop_times (trip_id, stop_sequence);")

    conn.commit()
    conn.close()

    elapsed = time.time() - start_time
    size_mb = os.path.getsize(DB_PATH) / (1024 * 1024)
    print(f"Database built successfully in {elapsed:.2f}s! Size: {size_mb:.1f} MB")


if __name__ == "__main__":
    import sys
    force_rebuild = "--force" in sys.argv
    build_db(force=force_rebuild)
