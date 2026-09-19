"""
Namma Metro (BMRCL) Network Dataset
Covers Purple Line (37 stations), Green Line (32 stations), and Yellow Line (16 stations).
Includes station sequences, geographic coordinates, interchange hubs, and routing utilities.
"""

from typing import List, Dict, Any, Optional, Tuple
import math

# Color specifications for UI and Leaflet overlays
METRO_LINES = {
    "PURPLE": {
        "name": "Purple Line",
        "color": "#7C3AED",
        "bg_class": "bg-purple-600",
        "text_color": "#ffffff",
        "terminals": ("Challaghatta", "Whitefield (Kadugodi)"),
    },
    "GREEN": {
        "name": "Green Line",
        "color": "#059669",
        "bg_class": "bg-emerald-600",
        "text_color": "#ffffff",
        "terminals": ("Madavara", "Silk Institute"),
    },
    "YELLOW": {
        "name": "Yellow Line",
        "color": "#D97706",
        "bg_class": "bg-amber-600",
        "text_color": "#ffffff",
        "terminals": ("RV Road", "Bommasandra"),
    }
}

# All 85 BMRCL Stations across the 3 lines
# Seq numbers indicate order along the line from start terminal to end terminal
METRO_STATIONS = [
    # ==========================================
    # PURPLE LINE (Challaghatta <-> Whitefield)
    # ==========================================
    {"id": "P01", "name": "Challaghatta", "line": "PURPLE", "seq": 1, "lat": 12.8942, "lon": 77.4660, "aliases": ["challaghatta", "kengeri west"]},
    {"id": "P02", "name": "Kengeri", "line": "PURPLE", "seq": 2, "lat": 12.9079, "lon": 77.4787, "aliases": ["kengeri", "kengeri railway station"]},
    {"id": "P03", "name": "Kengeri Bus Terminal", "line": "PURPLE", "seq": 3, "lat": 12.9152, "lon": 77.4839, "aliases": ["kengeri bus stand", "kengeri ttms", "kengeri bus terminal"]},
    {"id": "P04", "name": "Pattanagere", "line": "PURPLE", "seq": 4, "lat": 12.9238, "lon": 77.4984, "aliases": ["pattanagere", "rvce", "rv college"]},
    {"id": "P05", "name": "Jnanabharathi", "line": "PURPLE", "seq": 5, "lat": 12.9304, "lon": 77.5054, "aliases": ["jnanabharathi", "bangalore university", "bu campus"]},
    {"id": "P06", "name": "Rajarajeshwari Nagar", "line": "PURPLE", "seq": 6, "lat": 12.9377, "lon": 77.5147, "aliases": ["rajarajeshwari nagar", "rr nagar", "rr nagar arch"]},
    {"id": "P07", "name": "Nayandahalli", "line": "PURPLE", "seq": 7, "lat": 12.9439, "lon": 77.5222, "aliases": ["nayandahalli", "mysore road junction"]},
    {"id": "P08", "name": "Mysore Road", "line": "PURPLE", "seq": 8, "lat": 12.9467, "lon": 77.5303, "aliases": ["mysore road", "mysore road satellite bus stand", "bapuji nagar"]},
    {"id": "P09", "name": "Deepanjali Nagar", "line": "PURPLE", "seq": 9, "lat": 12.9519, "lon": 77.5372, "aliases": ["deepanjali nagar"]},
    {"id": "P10", "name": "Attiguppe", "line": "PURPLE", "seq": 10, "lat": 12.9618, "lon": 77.5338, "aliases": ["attiguppe"]},
    {"id": "P11", "name": "Vijayanagar", "line": "PURPLE", "seq": 11, "lat": 12.9696, "lon": 77.5375, "aliases": ["vijayanagar", "vijayanagara"]},
    {"id": "P12", "name": "Hosahalli", "line": "PURPLE", "seq": 12, "lat": 12.9745, "lon": 77.5457, "aliases": ["hosahalli", "balagangadharanatha swamiji", "chord road"]},
    {"id": "P13", "name": "Magadi Road", "line": "PURPLE", "seq": 13, "lat": 12.9756, "lon": 77.5552, "aliases": ["magadi road", "toll gate"]},
    {"id": "P14", "name": "Krantivira Sangolli Rayanna (City Railway Station)", "line": "PURPLE", "seq": 14, "lat": 12.9781, "lon": 77.5663, "aliases": ["ksr", "city railway station", "bangalore city station"]},
    {"id": "P15", "name": "Nadaprabhu Kempegowda Station (Majestic)", "line": "PURPLE", "seq": 15, "lat": 12.9757, "lon": 77.5728, "aliases": ["majestic", "kempegowda", "kbs", "majestic metro", "kempegowda bus station"], "is_interchange": True, "interchange_lines": ["GREEN"]},
    {"id": "P16", "name": "Sir M. Visveshwaraya (Central College)", "line": "PURPLE", "seq": 16, "lat": 12.9739, "lon": 77.5835, "aliases": ["central college", "sir m visveshwaraya", "kr circle"]},
    {"id": "P17", "name": "Dr. B.R. Ambedkar (Vidhana Soudha)", "line": "PURPLE", "seq": 17, "lat": 12.9797, "lon": 77.5927, "aliases": ["vidhana soudha", "vikasa soudha", "high court"]},
    {"id": "P18", "name": "Cubbon Park", "line": "PURPLE", "seq": 18, "lat": 12.9810, "lon": 77.5995, "aliases": ["cubbon park", "chinnaswamy stadium", "gpo"]},
    {"id": "P19", "name": "Mahatma Gandhi Road", "line": "PURPLE", "seq": 19, "lat": 12.9756, "lon": 77.6066, "aliases": ["mg road", "brigade road", "church street"]},
    {"id": "P20", "name": "Trinity", "line": "PURPLE", "seq": 20, "lat": 12.9727, "lon": 77.6169, "aliases": ["trinity", "trinity circle", "victoria layout"]},
    {"id": "P21", "name": "Halasuru", "line": "PURPLE", "seq": 21, "lat": 12.9757, "lon": 77.6268, "aliases": ["halasuru", "ulsoor", "ulsoor lake"]},
    {"id": "P22", "name": "Indiranagar", "line": "PURPLE", "seq": 22, "lat": 12.9783, "lon": 77.6386, "aliases": ["indiranagar", "indiranagara", "100ft road", "cmh road"]},
    {"id": "P23", "name": "Swami Vivekananda Road", "line": "PURPLE", "seq": 23, "lat": 12.9860, "lon": 77.6444, "aliases": ["sv road", "swami vivekananda road", "old madras road"]},
    {"id": "P24", "name": "Baiyappanahalli", "line": "PURPLE", "seq": 24, "lat": 12.9912, "lon": 77.6521, "aliases": ["baiyappanahalli", "byappanahalli", "smvt railway station"]},
    {"id": "P25", "name": "Benniganahalli", "line": "PURPLE", "seq": 25, "lat": 12.9944, "lon": 77.6620, "aliases": ["benniganahalli", "tin factory", "kasturi nagar"]},
    {"id": "P26", "name": "Krishnarajapura (KR Pura)", "line": "PURPLE", "seq": 26, "lat": 12.9984, "lon": 77.6755, "aliases": ["kr puram", "krishnarajapura", "kr puram railway station"]},
    {"id": "P27", "name": "Singayyanapalya", "line": "PURPLE", "seq": 27, "lat": 12.9961, "lon": 77.6888, "aliases": ["singayyanapalya", "mahadevapura", "phoenix marketcity"]},
    {"id": "P28", "name": "Garudacharpalya", "line": "PURPLE", "seq": 28, "lat": 12.9930, "lon": 77.7011, "aliases": ["garudacharpalya", "decathlon brigade"]},
    {"id": "P29", "name": "Hoodi", "line": "PURPLE", "seq": 29, "lat": 12.9918, "lon": 77.7126, "aliases": ["hoodi", "hoodi junction"]},
    {"id": "P30", "name": "Seetharampalya", "line": "PURPLE", "seq": 30, "lat": 12.9868, "lon": 77.7212, "aliases": ["seetharampalya", "itpl road"]},
    {"id": "P31", "name": "Kundalahalli", "line": "PURPLE", "seq": 31, "lat": 12.9818, "lon": 77.7275, "aliases": ["kundalahalli", "kundalahalli gate", "brookefield"]},
    {"id": "P32", "name": "Nallurhalli", "line": "PURPLE", "seq": 32, "lat": 12.9774, "lon": 77.7371, "aliases": ["nallurhalli", "siddapura"]},
    {"id": "P33", "name": "Sri Sathya Sai Hospital", "line": "PURPLE", "seq": 33, "lat": 12.9786, "lon": 77.7441, "aliases": ["sri sathya sai hospital", "satya sai hospital", "itpl back gate"]},
    {"id": "P34", "name": "Pattandur Agrahara (ITPL)", "line": "PURPLE", "seq": 34, "lat": 12.9863, "lon": 77.7479, "aliases": ["itpl", "pattandur agrahara", "international tech park"]},
    {"id": "P35", "name": "Kadugodi Tree Park", "line": "PURPLE", "seq": 35, "lat": 12.9953, "lon": 77.7533, "aliases": ["kadugodi tree park", "tree park"]},
    {"id": "P36", "name": "Hopefarm Channasandra", "line": "PURPLE", "seq": 36, "lat": 13.0035, "lon": 77.7588, "aliases": ["hopefarm", "hopefarm junction", "channasandra"]},
    {"id": "P37", "name": "Whitefield (Kadugodi)", "line": "PURPLE", "seq": 37, "lat": 13.0084, "lon": 77.7609, "aliases": ["whitefield", "kadugodi", "whitefield railway station", "whitefield metro"]},

    # ==========================================
    # GREEN LINE (Madavara <-> Silk Institute)
    # ==========================================
    {"id": "G01", "name": "Madavara (BIEC)", "line": "GREEN", "seq": 1, "lat": 13.0645, "lon": 77.4770, "aliases": ["madavara", "biec", "bangalore exhibition centre"]},
    {"id": "G02", "name": "Chikkabidarakallu", "line": "GREEN", "seq": 2, "lat": 13.0531, "lon": 77.4892, "aliases": ["chikkabidarakallu", "jindal"]},
    {"id": "G03", "name": "Manjunath Nagar", "line": "GREEN", "seq": 3, "lat": 13.0425, "lon": 77.4983, "aliases": ["manjunath nagar"]},
    {"id": "G04", "name": "Nagasandra", "line": "GREEN", "seq": 4, "lat": 13.0335, "lon": 77.5028, "aliases": ["nagasandra"]},
    {"id": "G05", "name": "Dasarahalli", "line": "GREEN", "seq": 5, "lat": 13.0270, "lon": 77.5132, "aliases": ["dasarahalli", "t dasarahalli"]},
    {"id": "G06", "name": "Jalahalli", "line": "GREEN", "seq": 6, "lat": 13.0232, "lon": 77.5204, "aliases": ["jalahalli", "jalahalli cross"]},
    {"id": "G07", "name": "Peenya Industry", "line": "GREEN", "seq": 7, "lat": 13.0189, "lon": 77.5273, "aliases": ["peenya industry", "peenya 1st stage"]},
    {"id": "G08", "name": "Peenya", "line": "GREEN", "seq": 8, "lat": 13.0142, "lon": 77.5342, "aliases": ["peenya"]},
    {"id": "G09", "name": "Goraguntepalya", "line": "GREEN", "seq": 9, "lat": 13.0169, "lon": 77.5458, "aliases": ["goraguntepalya", "taj yeshwantpur", "outer ring road peenya"]},
    {"id": "G10", "name": "Yeshwanthpur", "line": "GREEN", "seq": 10, "lat": 13.0231, "lon": 77.5501, "aliases": ["yeshwanthpur", "yeshvantpur", "yeshwanthpur railway station", "yeshwanthpur ttms"]},
    {"id": "G11", "name": "Sandal Soap Factory", "line": "GREEN", "seq": 11, "lat": 13.0149, "lon": 77.5539, "aliases": ["sandal soap factory", "soap factory"]},
    {"id": "G12", "name": "Mahalakshmi", "line": "GREEN", "seq": 12, "lat": 13.0076, "lon": 77.5494, "aliases": ["mahalakshmi", "mahalakshmi layout", "iskcon"]},
    {"id": "G13", "name": "Rajajinagar", "line": "GREEN", "seq": 13, "lat": 12.9989, "lon": 77.5558, "aliases": ["rajajinagar", "rajajinagara", "1st block rajajinagar"]},
    {"id": "G14", "name": "Kuvempu Road", "line": "GREEN", "seq": 14, "lat": 12.9936, "lon": 77.5601, "aliases": ["kuvempu road", "navrang"]},
    {"id": "G15", "name": "Srirampura", "line": "GREEN", "seq": 15, "lat": 12.9882, "lon": 77.5636, "aliases": ["srirampura", "harishchandra ghat"]},
    {"id": "G16", "name": "Mantri Square Sampige Road", "line": "GREEN", "seq": 16, "lat": 12.9831, "lon": 77.5701, "aliases": ["sampige road", "mantri square", "malleswaram"]},
    {"id": "G17", "name": "Nadaprabhu Kempegowda Station (Majestic)", "line": "GREEN", "seq": 17, "lat": 12.9757, "lon": 77.5728, "aliases": ["majestic", "kempegowda", "kbs", "majestic metro"], "is_interchange": True, "interchange_lines": ["PURPLE"]},
    {"id": "G18", "name": "Chickpet", "line": "GREEN", "seq": 18, "lat": 12.9678, "lon": 77.5746, "aliases": ["chickpet", "balepet", "cottonpet"]},
    {"id": "G19", "name": "Krishna Rajendra Market (KR Market)", "line": "GREEN", "seq": 19, "lat": 12.9609, "lon": 77.5746, "aliases": ["kr market", "kr market metro", "city market", "kalasipalya"]},
    {"id": "G20", "name": "National College", "line": "GREEN", "seq": 20, "lat": 12.9501, "lon": 77.5729, "aliases": ["national college", "basavanagudi"]},
    {"id": "G21", "name": "Lalbagh", "line": "GREEN", "seq": 21, "lat": 12.9427, "lon": 77.5799, "aliases": ["lalbagh", "lalbagh west gate", "mavalli"]},
    {"id": "G22", "name": "South End Circle", "line": "GREEN", "seq": 22, "lat": 12.9372, "lon": 77.5802, "aliases": ["south end circle", "surana college"]},
    {"id": "G23", "name": "Jayanagar", "line": "GREEN", "seq": 23, "lat": 12.9295, "lon": 77.5801, "aliases": ["jayanagar", "jayanagar 4th block", "jayanagar ttms"]},
    {"id": "G24", "name": "Rashtreeya Vidyalaya Road (RV Road)", "line": "GREEN", "seq": 24, "lat": 12.9213, "lon": 77.5800, "aliases": ["rv road", "rashtreeya vidyalaya road"], "is_interchange": True, "interchange_lines": ["YELLOW"]},
    {"id": "G25", "name": "Banashankari", "line": "GREEN", "seq": 25, "lat": 12.9152, "lon": 77.5736, "aliases": ["banashankari", "banashankari ttms", "bsk"]},
    {"id": "G26", "name": "Jaya Prakash Nagar (JP Nagar)", "line": "GREEN", "seq": 26, "lat": 12.9073, "lon": 77.5734, "aliases": ["jp nagar", "jaya prakash nagar", "sarakki"]},
    {"id": "G27", "name": "Yelachenahalli", "line": "GREEN", "seq": 27, "lat": 12.8958, "lon": 77.5701, "aliases": ["yelachenahalli", "puttenahalli"]},
    {"id": "G28", "name": "Konanakunte Cross", "line": "GREEN", "seq": 28, "lat": 12.8856, "lon": 77.5684, "aliases": ["konanakunte cross", "forum south bangalore"]},
    {"id": "G29", "name": "Doddakallasandra", "line": "GREEN", "seq": 29, "lat": 12.8753, "lon": 77.5615, "aliases": ["doddakallasandra"]},
    {"id": "G30", "name": "Vajarahalli", "line": "GREEN", "seq": 30, "lat": 12.8665, "lon": 77.5539, "aliases": ["vajarahalli"]},
    {"id": "G31", "name": "Thalaghattapura", "line": "GREEN", "seq": 31, "lat": 12.8577, "lon": 77.5451, "aliases": ["thalaghattapura", "kanakapura road"]},
    {"id": "G32", "name": "Silk Institute", "line": "GREEN", "seq": 32, "lat": 12.8465, "lon": 77.5369, "aliases": ["silk institute", "anajanapura"]},

    # ==========================================
    # YELLOW LINE (RV Road <-> Bommasandra)
    # ==========================================
    {"id": "Y01", "name": "Rashtreeya Vidyalaya Road (RV Road)", "line": "YELLOW", "seq": 1, "lat": 12.9213, "lon": 77.5800, "aliases": ["rv road", "rashtreeya vidyalaya road"], "is_interchange": True, "interchange_lines": ["GREEN"]},
    {"id": "Y02", "name": "Ragigudda", "line": "YELLOW", "seq": 2, "lat": 12.9168, "lon": 77.5910, "aliases": ["ragigudda", "jayanagar 9th block"]},
    {"id": "Y03", "name": "Jayadeva Hospital", "line": "YELLOW", "seq": 3, "lat": 12.9175, "lon": 77.6015, "aliases": ["jayadeva", "jayadeva hospital", "bannerghatta road metro"]},
    {"id": "Y04", "name": "BTM Layout", "line": "YELLOW", "seq": 4, "lat": 12.9163, "lon": 77.6117, "aliases": ["btm layout", "btm", "btm 2nd stage"]},
    {"id": "Y05", "name": "Central Silk Board", "line": "YELLOW", "seq": 5, "lat": 12.9176, "lon": 77.6227, "aliases": ["central silk board", "silk board", "silkboard", "csb"]},
    {"id": "Y06", "name": "Bommanahalli", "line": "YELLOW", "seq": 6, "lat": 12.9090, "lon": 77.6300, "aliases": ["bommanahalli", "roopena agrahara"]},
    {"id": "Y07", "name": "Hongasandra", "line": "YELLOW", "seq": 7, "lat": 12.8984, "lon": 77.6360, "aliases": ["hongasandra", "garebhavipalya"]},
    {"id": "Y08", "name": "Kudlu Gate", "line": "YELLOW", "seq": 8, "lat": 12.8887, "lon": 77.6436, "aliases": ["kudlu gate", "kudlu"]},
    {"id": "Y09", "name": "Singasandra", "line": "YELLOW", "seq": 9, "lat": 12.8798, "lon": 77.6521, "aliases": ["singasandra"]},
    {"id": "Y10", "name": "Hosa Road", "line": "YELLOW", "seq": 10, "lat": 12.8703, "lon": 77.6608, "aliases": ["hosa road", "jail road junction"]},
    {"id": "Y11", "name": "Beratena Agrahara", "line": "YELLOW", "seq": 11, "lat": 12.8612, "lon": 77.6685, "aliases": ["beratena agrahara"]},
    {"id": "Y12", "name": "Electronic City", "line": "YELLOW", "seq": 12, "lat": 12.8468, "lon": 77.6758, "aliases": ["electronic city", "ecity", "electronic city phase 1", "wipro electronic city"]},
    {"id": "Y13", "name": "Infosys Foundation Konappana Agrahara", "line": "YELLOW", "seq": 13, "lat": 12.8368, "lon": 77.6792, "aliases": ["konappana agrahara", "infosys", "electronic city phase 2"]},
    {"id": "Y14", "name": "Huskur Road", "line": "YELLOW", "seq": 14, "lat": 12.8256, "lon": 77.6834, "aliases": ["huskur road", "veerasandra"]},
    {"id": "Y15", "name": "Hebbagodi", "line": "YELLOW", "seq": 15, "lat": 12.8152, "lon": 77.6872, "aliases": ["hebbagodi", "biocon"]},
    {"id": "Y16", "name": "Bommasandra", "line": "YELLOW", "seq": 16, "lat": 12.8025, "lon": 77.6912, "aliases": ["bommasandra", "narayana hrudayalaya"]},
]


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculates great-circle distance between two GPS coordinates in kilometers."""
    R = 6371.0
    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (math.sin(d_lat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(d_lon / 2) ** 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


def find_nearest_metro_station(lat: float, lon: float, max_distance_km: float = 2.5) -> Optional[Dict[str, Any]]:
    """
    Finds the closest Namma Metro station within max_distance_km.
    Returns dictionary with station details and distance in meters, or None.
    """
    closest = None
    min_dist = float("inf")
    
    for s in METRO_STATIONS:
        d = haversine_km(lat, lon, s["lat"], s["lon"])
        if d < min_dist and d <= max_distance_km:
            min_dist = d
            closest = dict(s)
            closest["distance_km"] = round(d, 2)
            closest["distance_m"] = int(d * 1000)
            
    return closest


def find_metro_station_by_name(query: str) -> Optional[Dict[str, Any]]:
    """
    Matches a query string to a metro station by name or alias.
    """
    q = query.strip().lower()
    for s in METRO_STATIONS:
        if q == s["name"].lower() or any(q == a or a in q for a in s.get("aliases", [])):
            return dict(s)
    # Secondary substring search
    for s in METRO_STATIONS:
        if q in s["name"].lower():
            return dict(s)
    return None


def get_stations_for_line(line_name: str) -> List[Dict[str, Any]]:
    """Returns sorted stations along a given metro line."""
    return sorted(
        [s for s in METRO_STATIONS if s["line"] == line_name.upper()],
        key=lambda x: x["seq"]
    )


def get_all_lines_polylines() -> Dict[str, List[List[float]]]:
    """
    Returns coordinate pairs [[lat, lon], ...] for each line for Leaflet polyline rendering.
    """
    result = {}
    for line_name in METRO_LINES:
        stations = get_stations_for_line(line_name)
        result[line_name] = [[s["lat"], s["lon"]] for s in stations]
    return result
