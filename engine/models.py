"""
Data models for the BMTC Boarding Point Recommender.
Supports Direct and Multi-Leg Transfer Journeys.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Optional, Any


@dataclass(frozen=True)
class Stop:
    stop_id: str
    stop_name: str
    stop_desc: str
    lat: float
    lon: float
    zone_id: str = ""


@dataclass(frozen=True)
class Route:
    route_id: str
    route_short_name: str
    route_long_name: str


@dataclass(frozen=True)
class ViableRouteOption:
    route_short_name: str
    route_long_name: str
    trip_headsign: str
    direction_id: str
    destination_stop_name: str
    trip_count: int
    transit_stops_count: int


@dataclass
class CandidateBoardingPoint:
    stop_id: str
    stop_name: str
    stop_desc: str
    lat: float
    lon: float
    walk_distance_m: float
    walk_duration_min: int
    viable_routes: List[ViableRouteOption] = field(default_factory=list)
    score: float = 0.0
    score_breakdown: Dict[str, Any] = field(default_factory=dict)
    is_direct: bool = True
    transfers_count: int = 0
    transfer_stop_name: str = ""
    transfer_stop_desc: str = ""
    transfer2_stop_name: str = ""
    transfer2_stop_desc: str = ""
    leg1_routes: List[ViableRouteOption] = field(default_factory=list)
    leg2_routes: List[ViableRouteOption] = field(default_factory=list)
    leg3_routes: List[ViableRouteOption] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "stop_id": self.stop_id,
            "stop_name": self.stop_name,
            "stop_desc": self.stop_desc,
            "lat": self.lat,
            "lon": self.lon,
            "walk_distance_m": round(self.walk_distance_m),
            "walk_duration_min": self.walk_duration_min,
            "score": round(self.score, 2),
            "score_breakdown": self.score_breakdown,
            "is_direct": self.is_direct,
            "transfers_count": self.transfers_count,
            "transfer_stop_name": self.transfer_stop_name,
            "transfer_stop_desc": self.transfer_stop_desc,
            "transfer2_stop_name": self.transfer2_stop_name,
            "transfer2_stop_desc": self.transfer2_stop_desc,
            "routes": [
                {
                    "route": r.route_short_name,
                    "towards": r.trip_headsign,
                    "destination_stop": r.destination_stop_name,
                    "trips_per_day": r.trip_count,
                    "stops_away": r.transit_stops_count,
                }
                for r in self.viable_routes
            ],
            "leg1_routes": [
                {
                    "route": r.route_short_name,
                    "towards": r.trip_headsign,
                    "destination_stop": r.destination_stop_name,
                    "trips_per_day": r.trip_count,
                    "stops_away": r.transit_stops_count,
                }
                for r in self.leg1_routes
            ],
            "leg2_routes": [
                {
                    "route": r.route_short_name,
                    "towards": r.trip_headsign,
                    "destination_stop": r.destination_stop_name,
                    "trips_per_day": r.trip_count,
                    "stops_away": r.transit_stops_count,
                }
                for r in self.leg2_routes
            ],
            "leg3_routes": [
                {
                    "route": r.route_short_name,
                    "towards": r.trip_headsign,
                    "destination_stop": r.destination_stop_name,
                    "trips_per_day": r.trip_count,
                    "stops_away": r.transit_stops_count,
                }
                for r in self.leg3_routes
            ],
        }


@dataclass
class JourneyRecommendation:
    origin_name: str
    origin_lat: float
    origin_lon: float
    dest_name: str
    dest_lat: float
    dest_lon: float
    primary_candidate: Optional[CandidateBoardingPoint]
    ranked_candidates: List[CandidateBoardingPoint] = field(default_factory=list)
    status: str = "OK"
    message: str = ""
