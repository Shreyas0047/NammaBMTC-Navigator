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


def classify_route_service(route_short_name: str, stops_count: int = 10) -> tuple:
    """
    Classifies a BMTC route into service category and estimates official fare in INR:
    - AIRPORT_AC: 'KIA-' prefix (Vayu Vajra luxury airport express)
    - VAJRA_AC: 'V-' prefix (Volvo Vajra air-conditioned city express)
    - ORDINARY: All regular non-AC services (Sarige / Suvarna / Pushpak / Feeder)
    """
    name = (route_short_name or "").strip().upper()
    if name.startswith("KIA-"):
        if stops_count <= 8:
            fare = 150
        elif stops_count <= 16:
            fare = 220
        elif stops_count <= 25:
            fare = 260
        else:
            fare = 280
        return "AIRPORT_AC", fare
    elif name.startswith("V-"):
        if stops_count <= 4:
            fare = 20
        elif stops_count <= 8:
            fare = 35
        elif stops_count <= 14:
            fare = 50
        elif stops_count <= 20:
            fare = 65
        elif stops_count <= 28:
            fare = 80
        else:
            fare = 95
        return "VAJRA_AC", fare
    else:
        if stops_count <= 3:
            fare = 5
        elif stops_count <= 6:
            fare = 10
        elif stops_count <= 10:
            fare = 15
        elif stops_count <= 15:
            fare = 20
        elif stops_count <= 22:
            fare = 25
        else:
            fare = 30
        return "ORDINARY", fare


from engine.stop_resolver import clean_stop_display_name


@dataclass(frozen=True)
class ViableRouteOption:
    route_short_name: str
    route_long_name: str
    trip_headsign: str
    direction_id: str
    destination_stop_name: str
    trip_count: int
    transit_stops_count: int
    service_type: str = ""
    estimated_fare: int = 0
    enroute_milestones: List[str] = field(default_factory=list)
    estimated_ride_min: int = 0

    def __post_init__(self):
        if not self.service_type or self.estimated_fare == 0:
            stype, fare = classify_route_service(self.route_short_name, self.transit_stops_count)
            object.__setattr__(self, "service_type", stype)
            object.__setattr__(self, "estimated_fare", fare)
        if self.estimated_ride_min == 0:
            r_min = max(5, int(round(self.transit_stops_count * 2.2))) if self.transit_stops_count > 0 else 10
            object.__setattr__(self, "estimated_ride_min", r_min)


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
        all_routes = self.viable_routes or (self.leg1_routes + self.leg2_routes + self.leg3_routes)
        has_ac = any(r.service_type in ("VAJRA_AC", "AIRPORT_AC") for r in all_routes)
        has_non_ac = any(r.service_type == "ORDINARY" for r in all_routes)
        fares = [r.estimated_fare for r in all_routes if r.estimated_fare > 0]
        min_fare = min(fares) if fares else 15
        max_fare = max(fares) if fares else 25

        if has_ac and has_non_ac:
            fare_range_str = f"₹{min_fare} - ₹{max_fare}"
            service_tag = "Mixed (AC & Non-AC)"
            pass_info = "₹70 BMTC Ordinary (Shakti Scheme) / ₹140 Vajra Pass Valid"
        elif has_ac:
            fare_range_str = f"₹{min_fare} - ₹{max_fare}"
            service_tag = "AC Vajra / Vayu Vajra"
            pass_info = "₹140 Vajra Gold Day Pass Valid"
        else:
            fare_range_str = f"₹{min_fare} - ₹{max_fare}"
            service_tag = "Non-AC Ordinary"
            pass_info = "₹70 BMTC Day Pass Valid • Shakti Scheme Eligible"

        # Calculate ETA and commute duration breakdown
        if self.is_direct:
            primary_route = self.viable_routes[0] if self.viable_routes else None
            ride_time_min = primary_route.estimated_ride_min if primary_route else 20
            total_trips = sum(r.trip_count for r in self.viable_routes)
            transfer_wait_min = 0
        else:
            r1 = self.leg1_routes[0] if self.leg1_routes else None
            r2 = self.leg2_routes[0] if self.leg2_routes else None
            r3 = self.leg3_routes[0] if (self.transfers_count == 2 and self.leg3_routes) else None
            ride_time_min = (r1.estimated_ride_min if r1 else 15) + (r2.estimated_ride_min if r2 else 15) + (r3.estimated_ride_min if r3 else 0)
            total_trips = sum(r.trip_count for r in self.leg1_routes)
            transfer_wait_min = 8 if self.transfers_count == 1 else 16

        # Headway estimation based on daily frequency
        if total_trips >= 70:
            wait_headway_min = 4
            headway_desc = "Every ~4–7 mins (High Frequency)"
        elif total_trips >= 30:
            wait_headway_min = 7
            headway_desc = "Every ~8–12 mins (Good Frequency)"
        elif total_trips >= 15:
            wait_headway_min = 12
            headway_desc = "Every ~15–20 mins (Moderate Frequency)"
        else:
            wait_headway_min = 20
            headway_desc = "Every ~25–35 mins (Standard Schedule)"

        total_journey_min = self.walk_duration_min + wait_headway_min + ride_time_min + transfer_wait_min

        # Aggregate key milestones from primary route
        key_milestones = []
        if self.viable_routes and self.viable_routes[0].enroute_milestones:
            key_milestones = self.viable_routes[0].enroute_milestones
        elif self.leg1_routes and self.leg1_routes[0].enroute_milestones:
            key_milestones = self.leg1_routes[0].enroute_milestones

        def _format_route(r: ViableRouteOption) -> Dict[str, Any]:
            return {
                "route": r.route_short_name,
                "towards": r.trip_headsign,
                "destination_stop": clean_stop_display_name(r.destination_stop_name),
                "trips_per_day": r.trip_count,
                "stops_away": r.transit_stops_count,
                "service_type": r.service_type,
                "estimated_fare": r.estimated_fare,
                "fare_text": f"₹{r.estimated_fare}",
                "is_ac": r.service_type in ("VAJRA_AC", "AIRPORT_AC"),
                "estimated_ride_min": r.estimated_ride_min,
                "enroute_milestones": r.enroute_milestones,
                "shakti_eligible": r.service_type == "ORDINARY",
            }

        return {
            "stop_id": self.stop_id,
            "stop_name": clean_stop_display_name(self.stop_name),
            "stop_desc": clean_stop_display_name(self.stop_desc),
            "lat": self.lat,
            "lon": self.lon,
            "walk_distance_m": round(self.walk_distance_m),
            "walk_duration_min": self.walk_duration_min,
            "score": round(self.score, 2),
            "score_breakdown": self.score_breakdown,
            "is_direct": self.is_direct,
            "transfers_count": self.transfers_count,
            "transfer_stop_name": clean_stop_display_name(self.transfer_stop_name),
            "transfer_stop_desc": self.transfer_stop_desc,
            "transfer2_stop_name": clean_stop_display_name(self.transfer2_stop_name),
            "transfer2_stop_desc": self.transfer2_stop_desc,
            "fare_range_str": fare_range_str,
            "min_fare": min_fare,
            "max_fare": max_fare,
            "has_ac": has_ac,
            "has_non_ac": has_non_ac,
            "service_tag": service_tag,
            "pass_info": pass_info,
            "journey_breakdown": {
                "walk_time_min": self.walk_duration_min,
                "ride_time_min": ride_time_min,
                "wait_headway_min": wait_headway_min,
                "transfer_wait_min": transfer_wait_min,
                "total_journey_min": total_journey_min,
                "headway_desc": headway_desc,
                "shakti_scheme_eligible": has_non_ac,
                "pass_info": pass_info,
                "key_milestones": key_milestones,
            },
            "routes": [_format_route(r) for r in self.viable_routes],
            "leg1_routes": [_format_route(r) for r in self.leg1_routes],
            "leg2_routes": [_format_route(r) for r in self.leg2_routes],
            "leg3_routes": [_format_route(r) for r in self.leg3_routes],
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
