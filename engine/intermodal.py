"""
Intermodal Routing Engine: BMTC Bus + BMRCL Namma Metro
Evaluates multimodal shortcuts across Bengaluru, computing time savings against
peak-traffic bus routes, interchange walking penalties, and step-by-step transit cards.
"""

from typing import Dict, Any, Optional, List, Tuple
from data.metro_network import (
    METRO_LINES,
    METRO_STATIONS,
    find_nearest_metro_station,
    get_stations_for_line,
    haversine_km,
)


def calculate_metro_fare(station_count: int) -> int:
    """Calculates official BMRCL token fare based on station count."""
    if station_count <= 2:
        return 10
    elif station_count <= 5:
        return 20
    elif station_count <= 10:
        return 30
    elif station_count <= 15:
        return 40
    elif station_count <= 20:
        return 50
    else:
        return 60


def route_single_line(start_stn: Dict[str, Any], end_stn: Dict[str, Any]) -> Dict[str, Any]:
    """Generates direct metro routing along the same line."""
    line = start_stn["line"]
    meta = METRO_LINES[line]
    line_stations = get_stations_for_line(line)
    
    s_idx = start_stn["seq"] - 1
    e_idx = end_stn["seq"] - 1
    
    if s_idx < e_idx:
        stations_path = line_stations[s_idx:e_idx + 1]
        direction_headsign = meta["terminals"][1]
    else:
        stations_path = list(reversed(line_stations[e_idx:s_idx + 1]))
        direction_headsign = meta["terminals"][0]
        
    num_stations = len(stations_path) - 1
    # 2.1 mins run + 0.5 mins dwell = ~2.6 mins per station interval
    metro_ride_time = int(round(num_stations * 2.6))
    fare = calculate_metro_fare(num_stations)
    
    polyline = [[s["lat"], s["lon"]] for s in stations_path]
    
    return {
        "legs": [
            {
                "line": line,
                "line_name": meta["name"],
                "line_color": meta["color"],
                "headsign": direction_headsign,
                "start_station": start_stn["name"],
                "end_station": end_stn["name"],
                "station_count": num_stations,
                "duration_mins": metro_ride_time,
                "stations": [s["name"] for s in stations_path],
                "polyline": polyline
            }
        ],
        "interchange": None,
        "total_metro_ride_mins": metro_ride_time,
        "total_metro_stations": num_stations,
        "total_fare": fare,
        "full_polyline": polyline
    }


def route_with_interchange(start_stn: Dict[str, Any], end_stn: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Routes between two different lines with 1 transfer:
    - Purple <-> Green via Majestic (Kempegowda)
    - Green <-> Yellow via RV Road
    - Purple <-> Yellow via Majestic and RV Road (2 transfers)
    """
    l1 = start_stn["line"]
    l2 = end_stn["line"]
    
    transfer_pairs = []
    if (l1 == "PURPLE" and l2 == "GREEN") or (l1 == "GREEN" and l2 == "PURPLE"):
        transfer_pairs.append(("Nadaprabhu Kempegowda Station (Majestic)", 5)) # 5 min transfer
    elif (l1 == "GREEN" and l2 == "YELLOW") or (l1 == "YELLOW" and l2 == "GREEN"):
        transfer_pairs.append(("Rashtreeya Vidyalaya Road (RV Road)", 4)) # 4 min cross-platform transfer
    elif (l1 == "PURPLE" and l2 == "YELLOW"):
        # Purple to Yellow via Majestic and RV Road
        # Leg 1: Purple -> Majestic
        # Leg 2: Majestic -> RV Road (Green)
        # Leg 3: RV Road -> Yellow
        majestic_p = next(s for s in METRO_STATIONS if s["id"] == "P15")
        majestic_g = next(s for s in METRO_STATIONS if s["id"] == "G17")
        rv_road_g = next(s for s in METRO_STATIONS if s["id"] == "G24")
        rv_road_y = next(s for s in METRO_STATIONS if s["id"] == "Y01")
        
        leg1 = route_single_line(start_stn, majestic_p)["legs"][0]
        leg2 = route_single_line(majestic_g, rv_road_g)["legs"][0]
        leg3 = route_single_line(rv_road_y, end_stn)["legs"][0]
        
        total_time = leg1["duration_mins"] + 5 + leg2["duration_mins"] + 4 + leg3["duration_mins"]
        total_stns = leg1["station_count"] + leg2["station_count"] + leg3["station_count"]
        
        return {
            "legs": [leg1, leg2, leg3],
            "interchange": {
                "count": 2,
                "hubs": ["Majestic (Kempegowda)", "RV Road"]
            },
            "total_metro_ride_mins": total_time,
            "total_metro_stations": total_stns,
            "total_fare": calculate_metro_fare(total_stns),
            "full_polyline": leg1["polyline"] + leg2["polyline"] + leg3["polyline"]
        }
    elif (l1 == "YELLOW" and l2 == "PURPLE"):
        rv_road_y = next(s for s in METRO_STATIONS if s["id"] == "Y01")
        rv_road_g = next(s for s in METRO_STATIONS if s["id"] == "G24")
        majestic_g = next(s for s in METRO_STATIONS if s["id"] == "G17")
        majestic_p = next(s for s in METRO_STATIONS if s["id"] == "P15")
        
        leg1 = route_single_line(start_stn, rv_road_y)["legs"][0]
        leg2 = route_single_line(rv_road_g, majestic_g)["legs"][0]
        leg3 = route_single_line(majestic_p, end_stn)["legs"][0]
        
        total_time = leg1["duration_mins"] + 4 + leg2["duration_mins"] + 5 + leg3["duration_mins"]
        total_stns = leg1["station_count"] + leg2["station_count"] + leg3["station_count"]
        
        return {
            "legs": [leg1, leg2, leg3],
            "interchange": {
                "count": 2,
                "hubs": ["RV Road", "Majestic (Kempegowda)"]
            },
            "total_metro_ride_mins": total_time,
            "total_metro_stations": total_stns,
            "total_fare": calculate_metro_fare(total_stns),
            "full_polyline": leg1["polyline"] + leg2["polyline"] + leg3["polyline"]
        }
        
    # Single transfer: Purple <-> Green or Green <-> Yellow
    transfer_hub_name, transfer_walk_time = transfer_pairs[0]
    hub_stn1 = next(s for s in METRO_STATIONS if s["name"] == transfer_hub_name and s["line"] == l1)
    hub_stn2 = next(s for s in METRO_STATIONS if s["name"] == transfer_hub_name and s["line"] == l2)
    
    leg1 = route_single_line(start_stn, hub_stn1)["legs"][0]
    leg2 = route_single_line(hub_stn2, end_stn)["legs"][0]
    
    total_time = leg1["duration_mins"] + transfer_walk_time + leg2["duration_mins"]
    total_stns = leg1["station_count"] + leg2["station_count"]
    
    return {
        "legs": [leg1, leg2],
        "interchange": {
            "count": 1,
            "station": transfer_hub_name,
            "walk_time_mins": transfer_walk_time
        },
        "total_metro_ride_mins": total_time,
        "total_metro_stations": total_stns,
        "total_fare": calculate_metro_fare(total_stns),
        "full_polyline": leg1["polyline"] + leg2["polyline"]
    }


def find_intermodal_route(
    origin_lat: float,
    origin_lon: float,
    dest_lat: float,
    dest_lon: float,
    bus_travel_time_mins: Optional[int] = None,
    bus_fare: Optional[int] = None,
    max_station_access_km: float = 2.5
) -> Optional[Dict[str, Any]]:
    """
    Evaluates whether an intermodal (Walk/Feeder + Namma Metro) route is viable,
    calculates travel time savings over road bus traffic, and returns a detailed itinerary.
    """
    origin_metro = find_nearest_metro_station(origin_lat, origin_lon, max_distance_km=max_station_access_km)
    dest_metro = find_nearest_metro_station(dest_lat, dest_lon, max_distance_km=max_station_access_km)
    
    if not origin_metro or not dest_metro:
        return None
        
    # Same station doesn't warrant a metro ride
    if origin_metro["name"] == dest_metro["name"]:
        return None

    # Determine metro routing
    if origin_metro["line"] == dest_metro["line"]:
        metro_plan = route_single_line(origin_metro, dest_metro)
    else:
        metro_plan = route_with_interchange(origin_metro, dest_metro)
        
    if not metro_plan:
        return None

    # Walking / first & last mile access (75 m/min = 4.5 km/h)
    access_walk_mins = max(1, int(round(origin_metro["distance_m"] / 75.0)))
    egress_walk_mins = max(1, int(round(dest_metro["distance_m"] / 75.0)))
    
    total_hybrid_time = access_walk_mins + metro_plan["total_metro_ride_mins"] + egress_walk_mins
    
    # Estimate bus travel time if not provided (assume 16 km/h road traffic in Bangalore)
    straight_dist_km = haversine_km(origin_lat, origin_lon, dest_lat, dest_lon)
    if bus_travel_time_mins is None or bus_travel_time_mins <= 0:
        # Bangalore road distance ~ 1.35x straight line, 16 km/h avg speed + 10 min waiting
        road_km = straight_dist_km * 1.35
        est_bus_mins = int(round((road_km / 16.0) * 60)) + 10
    else:
        est_bus_mins = bus_travel_time_mins
        
    time_saved_mins = est_bus_mins - total_hybrid_time
    is_faster = time_saved_mins > 0
    is_substantially_faster = time_saved_mins >= 15

    # Human-readable step-by-step itinerary
    steps = []
    
    # Step 1: Access
    if origin_metro["distance_m"] > 30:
        steps.append({
            "type": "walk",
            "icon": "🚶",
            "title": f"Walk {origin_metro['distance_m']}m to {origin_metro['name']}",
            "subtitle": f"Approx {access_walk_mins} min walk to Metro Station entrance",
            "duration_mins": access_walk_mins
        })
    else:
        steps.append({
            "type": "board",
            "icon": "🚇",
            "title": f"Enter {origin_metro['name']} Metro Station",
            "subtitle": "Direct access",
            "duration_mins": 1
        })
        
    # Step 2: Metro legs
    for idx, leg in enumerate(metro_plan["legs"]):
        steps.append({
            "type": "metro",
            "icon": "🚇",
            "line": leg["line"],
            "line_color": leg["line_color"],
            "title": f"Board {leg['line_name']} towards {leg['headsign']}",
            "subtitle": f"Ride {leg['station_count']} stations ({leg['duration_mins']} mins) from {leg['start_station']} to {leg['end_station']}",
            "station_count": leg["station_count"],
            "duration_mins": leg["duration_mins"]
        })
        if idx < len(metro_plan["legs"]) - 1:
            # Transfer step
            interchange_stn = leg["end_station"]
            steps.append({
                "type": "interchange",
                "icon": "🔄",
                "title": f"Interchange at {interchange_stn}",
                "subtitle": f"Follow signs to {metro_plan['legs'][idx + 1]['line_name']} platform",
                "duration_mins": 5
            })
            
    # Step 3: Egress
    if dest_metro["distance_m"] > 30:
        steps.append({
            "type": "walk",
            "icon": "🚶",
            "title": f"Exit {dest_metro['name']} and walk {dest_metro['distance_m']}m",
            "subtitle": f"Approx {egress_walk_mins} min walk to final destination",
            "duration_mins": egress_walk_mins
        })
    else:
        steps.append({
            "type": "arrive",
            "icon": "📍",
            "title": f"Arrive at {dest_metro['name']}",
            "subtitle": "Destination reached",
            "duration_mins": 0
        })

    # Primary line info for UI badge
    primary_line = metro_plan["legs"][0]["line"]
    primary_color = metro_plan["legs"][0]["line_color"]

    return {
        "available": True,
        "is_faster": is_faster,
        "is_substantially_faster": is_substantially_faster,
        "time_saved_mins": time_saved_mins if time_saved_mins > 0 else 0,
        "total_travel_time_mins": total_hybrid_time,
        "metro_ride_time_mins": metro_plan["total_metro_ride_mins"],
        "access_walk_mins": access_walk_mins,
        "egress_walk_mins": egress_walk_mins,
        "total_stations": metro_plan["total_metro_stations"],
        "fare": metro_plan["total_fare"],
        "origin_station": origin_metro,
        "dest_station": dest_metro,
        "lines_used": list(dict.fromkeys(leg["line"] for leg in metro_plan["legs"])),
        "primary_line": primary_line,
        "primary_color": primary_color,
        "has_interchange": metro_plan["interchange"] is not None,
        "interchange_info": metro_plan["interchange"],
        "steps": steps,
        "polyline": metro_plan["full_polyline"]
    }
