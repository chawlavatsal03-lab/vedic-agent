# enrich.py
# -------------------------------------------------------------------
# Enrich a raw chart (from calculator.py) with Vedic dignity,
# lordships, friendship, combustion, retrograde, pada, DMS, and
# vargottama data.
#
# Reads fixed rules from data/planet_rules.json.
# Does NOT modify the chart's raw longitudes — only adds fields.
# -------------------------------------------------------------------

import json
import os

RULES_PATH = os.path.join("data", "planet_rules.json")


def _load_rules():
    with open(RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_RULES = _load_rules()


# -------------------------------------------------------------------
# Helpers
# -------------------------------------------------------------------
def ordinal(n):
    """Return 1st, 2nd, 3rd, 4th, ... 11th, 12th."""
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"


def to_dms(deg_in_sign):
    """Convert a 0–30 degree value in a sign to 'DD°MM'SS\"' format."""
    d = int(deg_in_sign)
    rem = (deg_in_sign - d) * 60
    m = int(rem)
    s = int((rem - m) * 60)
    return f"{d:02d}°{m:02d}'{s:02d}\""


def get_pada(longitude):
    """Return 1–4 for the pada within the nakshatra."""
    nak_span = 360.0 / 27.0
    pos_in_nak = longitude % nak_span
    pada = int(pos_in_nak / (nak_span / 4.0)) + 1
    return min(pada, 4)


def relationship(planet, other):
    """Return 'Friend', 'Neutral', or 'Enemy' from the planet's perspective."""
    if planet == other:
        return "Self"
    rel = _RULES["natural_friendship"].get(planet, {})
    if other in rel.get("friends", []):
        return "Friend"
    if other in rel.get("enemies", []):
        return "Enemy"
    return "Neutral"


def get_dignity(planet, sign_vedic, deg_in_sign):
    """Return dignity label for a planet in a sign at a given degree in that sign."""
    # Exaltation
    ex = _RULES["exaltation"].get(planet, {})
    if ex.get("sign") == sign_vedic:
        return "Exalted"

    # Debilitation
    deb = _RULES["debilitation"].get(planet, {})
    if deb.get("sign") == sign_vedic:
        return "Debilitated"

    # Moolatrikona (has priority over own sign)
    mt = _RULES["moolatrikona"].get(planet)
    if mt and mt.get("sign") == sign_vedic and mt.get("start") <= deg_in_sign <= mt.get("end"):
        return "Moolatrikona"

    # Own sign
    if sign_vedic in _RULES["own_signs"].get(planet, []):
        return "Own Sign"

    # Friendly / Neutral / Enemy based on the sign's lord
    sign_lord = _RULES["sign_lords"][sign_vedic]
    rel = relationship(planet, sign_lord)
    if rel == "Friend":
        return "Friendly Sign"
    if rel == "Enemy":
        return "Enemy Sign"
    return "Neutral Sign"


def is_combust(planet, planet_lon, sun_lon):
    """Return True if planet is within the classical combustion orb from the Sun."""
    if planet in ("Sun",):
        return False
    orb = _RULES["combustion_orb"].get(planet)
    if orb is None:
        return False
    diff = abs((planet_lon - sun_lon + 180) % 360 - 180)  # 0–180°
    return diff <= orb


def functional_lordships(planet, asc_sign_vedic):
    """
    Return list of house numbers (1–12) ruled by planet for the given Lagna.
    House 1 = the ascendant sign. House N = the sign N-1 steps forward.
    """
    signs = list(_RULES["sign_lords"].keys())
    asc_idx = signs.index(asc_sign_vedic)
    houses = []
    for i, sign in enumerate(signs):
        lord = _RULES["sign_lords"][sign]
        if lord == planet:
            house_num = ((i - asc_idx) % 12) + 1
            houses.append(house_num)
    return sorted(houses)


def compute_sign_lord(sign_vedic):
    return _RULES["sign_lords"][sign_vedic]


def compute_nakshatra_lord(nakshatra):
    return _RULES["nakshatra_lords"].get(nakshatra)


def compute_sign_qualities(sign_vedic):
    return _RULES["sign_qualities"].get(sign_vedic, {})


def compute_vargottama(longitude, sign_vedic):
    """
    Placeholder: vargottama means same sign in D-1 and D-9.
    Full Navamsa computation will be added when we do divisional charts.
    For now, return None.
    """
    return None


# -------------------------------------------------------------------
# Main entry: enrich a chart
# -------------------------------------------------------------------
def enrich_chart(chart):
    """
    Add computed Vedic fields to each planet and to the ascendant.
    Returns the same chart dict, mutated in place, for convenience.
    """
    asc = chart["ascendant"]
    asc_sign_vedic = asc["sign_vedic"]

    # --- Ascendant enrichment ---
    asc["deg_in_sign"] = asc["longitude"] % 30
    asc["deg_in_sign_dms"] = to_dms(asc["deg_in_sign"])
    asc["nakshatra_pada"] = get_pada(asc["longitude"])
    asc["sign_lord"] = compute_sign_lord(asc_sign_vedic)
    asc["nakshatra_lord"] = compute_nakshatra_lord(asc["nakshatra"])
    asc["sign_qualities"] = compute_sign_qualities(asc_sign_vedic)

    # --- Planets enrichment ---
    sun_lon = chart["planets"]["Sun"]["longitude"]

    for pname, p in chart["planets"].items():
        p["deg_in_sign"] = p["longitude"] % 30
        p["deg_in_sign_dms"] = to_dms(p["deg_in_sign"])
        p["nakshatra_pada"] = get_pada(p["longitude"])
        p["sign_lord"] = compute_sign_lord(p["sign_vedic"])
        p["sign_relationship"] = relationship(pname, p["sign_lord"])
        p["nakshatra_lord"] = compute_nakshatra_lord(p["nakshatra"])
        p["dignity"] = get_dignity(pname, p["sign_vedic"], p["deg_in_sign"])
        p["combust"] = is_combust(pname, p["longitude"], sun_lon)
        p["retrograde"] = p.get("speed", 0) < 0
        p["functional_lordships"] = functional_lordships(pname, asc_sign_vedic)
        p["sign_qualities"] = compute_sign_qualities(p["sign_vedic"])
        p["vargottama"] = compute_vargottama(p["longitude"], p["sign_vedic"])

    # --- Add Lagna lord placement ---
    lagna_lord_name = asc["sign_lord"]
    lagna_lord = chart["planets"].get(lagna_lord_name)
    if lagna_lord:
        asc["lagna_lord_house"] = lagna_lord["house"]
        asc["lagna_lord_sign"] = lagna_lord["sign_vedic"]
    else:
        asc["lagna_lord_house"] = None
        asc["lagna_lord_sign"] = None

    return chart


if __name__ == "__main__":
    # Self-test with Vatsal's chart
    from calculator import calculate_chart
    import json as _json

    chart = calculate_chart("Test", "2000-03-03", "15:00", "New Delhi, India")
    enrich_chart(chart)
    print(_json.dumps(chart["planets"]["Sun"], indent=2, default=str))