"""
BMTC Smart Stop Resolver & Transliteration Normalizer
Resolves colloquial names, tech parks, hospitals, malls, colleges,
and handles Kannada/English transliteration differences across Bengaluru.
"""

import re
from typing import List, Dict, Any, Optional, Tuple

# Comprehensive curated landmarks, tech parks, colleges, hospitals, malls, and hubs
LANDMARK_ALIASES = {
    # --- Major Transit Hubs ---
    "majestic": "Kempegowda Bus Station",
    "kbs": "Kempegowda Bus Station",
    "city railway station": "Kempegowda Bus Station",
    "ksr": "Kempegowda Bus Station",
    "sangolli rayanna": "Kempegowda Bus Station",
    "silk board": "Central Silk Board",
    "silkboard": "Central Silk Board",
    "csb": "Central Silk Board",
    "central silk board": "Central Silk Board",
    "airport": "Kempegowda International Airport",
    "kia": "Kempegowda International Airport",
    "bial": "Kempegowda International Airport",
    "bangalore airport": "Kempegowda International Airport",
    "kempegowda airport": "Kempegowda International Airport",
    "kr market": "Krishna Rajendra Market",
    "krmarket": "Krishna Rajendra Market",
    "city market": "Krishna Rajendra Market",
    "market": "Krishna Rajendra Market",
    "kalasipalya": "Krishna Rajendra Market (Kalasipalya)",
    "shivajinagar": "Shivajinagara Bus Station",
    "shanthinagar": "Shanthinagara TTMC",
    "shantinagar": "Shanthinagara TTMC",
    "banashankari": "Banashankari Bus Station",
    "bsk": "Banashankari Bus Station",
    "yeshwanthpur": "Yeshwanthpura TTMC",
    "yeshwantpur": "Yeshwanthpura TTMC",
    "ypr": "Yeshwanthpura TTMC",
    "yeshwanthpur railway station": "Yeshwanthpura Railway Station",
    "cantonment": "Bangalore Cantonment Railway Station",
    "cantonment railway station": "Bangalore Cantonment Railway Station",
    "kr puram": "KR Puram Railway Station",
    "krishnarajapura": "KR Puram Railway Station",
    "tin factory": "Tin Factory",
    "tinfactory": "Tin Factory",
    "baiyappanahalli": "Baiyappanahalli Metro Station",
    "smvt": "Baiyappanahalli Railway Station",
    "kengeri": "Kengeri TTMC",
    "kengeri bus stand": "Kengeri TTMC",
    "kengeri satellite town": "Kengeri Satellite Town",

    # --- Tech Parks & IT Corridors ---
    "manyata": "Manyatha Tech Park",
    "manyata tech park": "Manyatha Tech Park",
    "manyatha": "Manyatha Tech Park",
    "manyatha tech park": "Manyatha Tech Park",
    "nagavara": "Nagawara Junction",
    "nagawara": "Nagawara Junction",
    "ecospace": "Eco Space",
    "eco space": "Eco Space",
    "rmz ecospace": "Eco Space",
    "rmz ecoworld": "Devarabisanahalli Ring Road",
    "ecoworld": "Devarabisanahalli Ring Road",
    "embassy tech village": "Embassy Tech Village",
    "etv": "Embassy Tech Village",
    "bellandur": "Bellanduru Gate",
    "bellanduru": "Bellanduru Gate",
    "itpl": "ITPL",
    "itpl main gate": "ITPL",
    "international tech park": "ITPL",
    "whitefield": "White Field Post Office",
    "white field": "White Field Post Office",
    "kadugodi": "Kadugodi Bapuji Circle",
    "bagmane": "CV Raman Nagar",
    "bagmane tech park": "CV Raman Nagar",
    "bagmane constellation": "Karthik Nagara",
    "global village": "Rajarajeshwari Nagar",
    "global village tech park": "Rajarajeshwari Nagar",
    "prestige tech park": "Kadu bisanahalli",
    "cessna": "New Horizon College",
    "cessna business park": "New Horizon College",
    "marathahalli": "Marathahalli Bridge",
    "marathalli": "Marathahalli Bridge",
    "electronic city": "Electronic City",
    "ecity": "Electronic City",
    "e-city": "Electronic City",
    "electronic city phase 1": "Electronic City",
    "electronic city phase 2": "Konappana Agrahara",
    "wipro gate electronic city": "Electronic City",
    "infosys electronic city": "Konappana Agrahara",
    "wipro sarjapur": "Kaikondrahalli",

    # --- Major Suburbs & Localities ---
    "malleswaram": "Malleshwara",
    "malleshwaram": "Malleshwara",
    "malleshwara": "Malleshwara",
    "indiranagar": "Indiranagara 12th Main",
    "indiranagara": "Indiranagara 12th Main",
    "100ft road indiranagar": "Double Road Indiranagara",
    "koramangala": "BDA Complex Koramangala",
    "koramangala bda": "BDA Complex Koramangala",
    "sony world": "Airtel office Koramangala",
    "sony world signal": "Airtel office Koramangala",
    "koramangala sony world": "Airtel office Koramangala",
    "hsr": "HSR Layout BDA Complex",
    "hsr layout": "HSR Layout BDA Complex",
    "btm": "BTM Layout Water Tank",
    "btm layout": "BTM Layout Water Tank",
    "jayanagar": "Jayanagara 4th Block",
    "jayanagara": "Jayanagara 4th Block",
    "jp nagar": "JP Nagara 6th Phase",
    "jaya prakash nagar": "JP Nagara 6th Phase",
    "rajajinagar": "Rajajinagara 1st Block",
    "rajajinagara": "Rajajinagara 1st Block",
    "vijayanagar": "Vijayanagar Bus Station",
    "vijayanagara": "Vijayanagar Bus Station",
    "basavanagudi": "Basavanagudi Police Station",
    "basaveshwaranagar": "Basaveshwaranagara BDA Complex",
    "basaveshwarnagar": "Basaveshwaranagara BDA Complex",
    "domlur": "Domluru TTMC",
    "domluru": "Domluru TTMC",
    "hebbal": "Hebbala Bridge",
    "hebbala": "Hebbala Bridge",
    "yelahanka": "Yelahanka Old Town",
    "yelahanka new town": "4th Phase Yelahanka New Town Iyengar Bakery",
    "brookefield": "Kundalahalli Gate",
    "brookfield": "Kundalahalli Gate",
    "kundalahalli": "Kundalahalli Gate",
    "kundalahalli gate": "Kundalahalli Gate",
    "aecs layout": "AECS Layout Cross",
    "beml layout": "BEML Layout Gate",
    "sarjapur": "Abbaiah Circle Sarjapura",
    "sarjapura": "Abbaiah Circle Sarjapura",
    "sarjapur road": "Crystal Apartment Sarjapura Road",
    "hoodi": "Hoodi",
    "hoodi junction": "Hoodi",
    "peenya": "CS-Peenya 2nd Stage",
    "peenya 2nd stage": "CS-Peenya 2nd Stage",
    "jigani": "Jigani APC Circle",
    "bommasandra": "Bommasandra",
    "anekal": "Anekal Bus Stand",
    "hoskote": "Hoskote Bus Stand",
    "doddaballapur": "Doddaballapura Bus Stand",
    "nelamangala": "Nelamangala Bus Station",

    # --- Malls & Commercial Hubs ---
    "orion mall": "Sandal Soap Factory",
    "orion": "Sandal Soap Factory",
    "phoenix marketcity": "Singaianapalya Phoenix",
    "phoenix mall": "Singaianapalya Phoenix",
    "singayyanapalya": "Singaianapalya Phoenix",
    "mantri square": "Malleshwara 8th Cross (Sampige Road)",
    "mantri mall": "Malleshwara 8th Cross (Sampige Road)",
    "nexus koramangala": "BDA Complex Koramangala",
    "forum koramangala": "BDA Complex Koramangala",
    "forum mall": "BDA Complex Koramangala",
    "forum south": "Konanakunte Cross",
    "vega city": "BTM Layout Water Tank",
    "vega city mall": "BTM Layout Water Tank",
    "lulu mall": "Sujatha Theatre",
    "mg road": "MG Road Metro Station",
    "brigade road": "Mayo Hall",
    "commercial street": "Shivajinagara Bus Station",
    "church street": "MG Road Metro Station",
    "cubbon park": "Cubbon Park",
    "vidhana soudha": "Vidhana Soudha",
    "high court": "High Court",

    # --- Hospitals ---
    "jayadeva": "East End Jayanagara",
    "jayadeva hospital": "East End Jayanagara",
    "nimhans": "NIMHANS Hospital",
    "nimhans hospital": "NIMHANS Hospital",
    "victoria hospital": "Victoria Hospital",
    "bowring hospital": "Bowring Hospital",
    "manipal hospital": "Manipal Hospital HAL Road",
    "manipal old airport road": "Manipal Hospital HAL Road",
    "narayana hrudayalaya": "Narayana Hrudayalaya",
    "kidwai": "Kidwai Hospital",
    "st johns": "St. Johns Hospital",
    "st johns hospital": "St. Johns Hospital",

    # --- Colleges & Universities ---
    "christ university": "Dairy Circle",
    "christ college": "Dairy Circle",
    "pes university": "PES College",
    "pes college": "PES College",
    "pesit": "PES College",
    "rvce": "Pattanagere",
    "rv college": "Pattanagere",
    "bmsce": "National College",
    "bms college": "National College",
    "ms ramaiah": "M.S.Ramaiah College",
    "ramaiah": "M.S.Ramaiah College",
    "bangalore university": "Jnanabharathi Metro Station",
    "jnanabharathi": "Jnanabharathi Metro Station",
    "mount carmel": "Mount Carmel College",
    "national college": "National College",
}


def clean_stop_display_name(raw_name: str) -> str:
    """
    Cleans up BMTC raw GTFS naming anomalies:
    - Strips 'CS-' prefix (e.g. 'CS-Kempegowda Bus Station' -> 'Kempegowda Bus Station')
    - Cleans duplicate whitespace
    """
    if not raw_name:
        return ""
    name = raw_name.strip()
    if name.startswith("CS-"):
        name = name[3:].strip()
    name = re.sub(r"\s+", " ", name)
    return name


def normalize_kannada_english_transliteration(term: str) -> List[str]:
    """
    Generates realistic Bengaluru phonetics and transliteration variants:
    e.g. 'malleswaram' -> ['malleshwara', 'malleswara', 'malleshwaram']
         'manyata' -> ['manyatha', 'manyata']
         'nagar' -> ['nagara', 'nagar']
         'pur' -> ['pura', 'pur']
    """
    t = term.lower().strip()
    variants = [t]

    # Specific phonetic substitutions
    if "shw" in t:
        variants.append(t.replace("shw", "sw"))
    elif "sw" in t:
        variants.append(t.replace("sw", "shw"))

    if "sh" in t:
        variants.append(t.replace("sh", "s"))
    elif "s" in t and "sh" not in t:
        variants.append(t.replace("s", "sh"))

    if "th" in t:
        variants.append(t.replace("th", "t"))
    elif "t" in t and "th" not in t:
        variants.append(t.replace("t", "th"))

    if "w" in t:
        variants.append(t.replace("w", "v"))
    elif "v" in t:
        variants.append(t.replace("v", "w"))

    # Suffixes
    for var in list(variants):
        if var.endswith("am"):
            variants.append(var[:-2] + "a")
            variants.append(var[:-2])
        if var.endswith("nagar"):
            variants.append(var + "a")
        elif var.endswith("nagara"):
            variants.append(var[:-1])
            
        if var.endswith("pur"):
            variants.append(var + "a")
        elif var.endswith("pura"):
            variants.append(var[:-1])

        if var.endswith("ur"):
            variants.append(var + "u")
        elif var.endswith("uru"):
            variants.append(var[:-1])

    # Remove duplicates preserving order
    return list(dict.fromkeys(variants))


def resolve_search_term(raw_term: str) -> Tuple[str, List[str]]:
    """
    Resolves user search input against the landmark dictionary and transliteration variants.
    Returns (primary_expanded_term, list_of_all_candidate_search_strings).
    """
    norm = raw_term.lower().strip()
    norm = re.sub(r"\s+", " ", norm)

    expanded = LANDMARK_ALIASES.get(norm)
    if expanded:
        return expanded, [expanded, norm]

    # Check partial phrases in LANDMARK_ALIASES
    for k, v in LANDMARK_ALIASES.items():
        if k in norm or norm in k:
            return v, [v, norm]

    # Generate transliteration variants
    variants = normalize_kannada_english_transliteration(norm)
    return variants[0], variants
