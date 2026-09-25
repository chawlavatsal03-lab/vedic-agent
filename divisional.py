# divisional.py
# -------------------------------------------------------------------
# Divisional charts (Varga) computed from the exact birth longitudes.
#
# Supported:
#   D-1  Rashi      (identity — same as birth chart)
#   D-9  Navamsa    (marriage, dharma, inner strength)
#   D-10 Dasamsa    (career, profession, status)
#
# All formulas operate on sidereal longitudes from calculator.py.
# Nothing here invents values — every placement derives from the
# planet's exact degree.
# -------------------------------------------------------------------

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]
SIGNS_VEDIC = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"
]

PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]

import json
import os

_RULES_PATH = os.path.join("data", "planet_rules.json")


def _load_rules():
    with open(_RULES_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


_RULES = _load_rules()

# -------------------------------------------------------------------
# Element-based starting sign for Navamsa
# -------------------------------------------------------------------
def _navamsa_start_sign(sign_index):
    """
    Return the starting sign index for the Navamsa of the given sign.
    sign_index: 0=Aries, 1=Taurus, ..., 11=Pisces.
    """
    element = sign_index % 4  # 0=fire, 1=earth, 2=air, 3=water (natural order)
    return [0, 9, 6, 3][element]  # Aries=0, Capricorn=9, Libra=6, Cancer=3


def _d9_sign_index(longitude):
    """Compute the D-9 (Navamsa) sign index from sidereal longitude."""
    sign_index = int(longitude / 30) % 12
    deg_in_sign = longitude % 30
    part = int(deg_in_sign / (30.0 / 9.0))   # 0..8
    start = _navamsa_start_sign(sign_index)
    return (start + part) % 12


# -------------------------------------------------------------------
# Dasamsa (D-10)
# -------------------------------------------------------------------
def _d10_sign_index(longitude):
    """
    Compute the D-10 (Dasamsa) sign index from sidereal longitude.
    Odd sign:  count forward from the sign itself.
    Even sign: count forward from the 9th sign from it.
    """
    sign_index = int(longitude / 30) % 12
    deg_in_sign = longitude % 30
    part = int(deg_in_sign / 3.0)  # 0..9

    if sign_index % 2 == 0:  # odd sign (Aries, Gemini, ...)
        return (sign_index + part) % 12
    else:                    # even sign (Taurus, Cancer, ...)
        return (sign_index + 8 + part) % 12


# -------------------------------------------------------------------
# Compute one divisional chart
# -------------------------------------------------------------------
def _compute_chart(chart, division):
    """
    Return a divisional chart dict:
      {
        "division": <int>,
        "asc_sign_index": int,
        "asc_sign_vedic": str,
        "planets": {
            "<Planet>": {"sign_index": int, "sign_vedic": str, "house": int},
            ...
        }
      }
    """
    asc = chart["ascendant"]

    if division == 1:
        asc_sign_index = int(asc["longitude"] / 30) % 12
        planet_signs = {
            p: int(d["longitude"] / 30) % 12
            for p, d in chart["planets"].items()
        }
    elif division == 9:
        asc_sign_index = _d9_sign_index(asc["longitude"])
        planet_signs = {
            p: _d9_sign_index(d["longitude"])
            for p, d in chart["planets"].items()
        }
    elif division == 10:
        asc_sign_index = _d10_sign_index(asc["longitude"])
        planet_signs = {
            p: _d10_sign_index(d["longitude"])
            for p, d in chart["planets"].items()
        }
    else:
        raise ValueError(f"Unsupported division D-{division}")

    planets = {}
    for p, sign_idx in planet_signs.items():
        house = ((sign_idx - asc_sign_index) % 12) + 1
        planets[p] = {
            "sign_index": sign_idx,
            "sign_vedic": SIGNS_VEDIC[sign_idx],
            "sign": SIGNS[sign_idx],
            "house": house,
        }

    return {
        "division": division,
        "asc_sign_index": asc_sign_index,
        "asc_sign_vedic": SIGNS_VEDIC[asc_sign_index],
        "asc_sign": SIGNS[asc_sign_index],
        "planets": planets,
    }

def _relationship(planet, other):
    """Return 'Friend', 'Neutral', 'Self', or 'Enemy' from planet's perspective."""
    if planet == other:
        return "Self"
    rel = _RULES["natural_friendship"].get(planet, {})
    if other in rel.get("friends", []):
        return "Friend"
    if other in rel.get("enemies", []):
        return "Enemy"
    return "Neutral"


def _dignity(planet, sign_vedic, deg_in_sign):
    """Return dignity label for a planet in a sign at a given degree in that sign."""
    ex = _RULES["exaltation"].get(planet, {})
    if ex.get("sign") == sign_vedic:
        return "Exalted"

    deb = _RULES["debilitation"].get(planet, {})
    if deb.get("sign") == sign_vedic:
        return "Debilitated"

    mt = _RULES["moolatrikona"].get(planet)
    if mt and mt.get("sign") == sign_vedic and mt.get("start") <= deg_in_sign <= mt.get("end"):
        return "Moolatrikona"

    if sign_vedic in _RULES["own_signs"].get(planet, []):
        return "Own Sign"

    sign_lord = _RULES["sign_lords"][sign_vedic]
    rel = _relationship(planet, sign_lord)
    if rel == "Friend":
        return "Friendly Sign"
    if rel == "Enemy":
        return "Enemy Sign"
    return "Neutral Sign"


def compute_divisional_dignity(dchart, chart):
    """
    For a divisional chart, compute each planet's dignity based on the
    sign it occupies IN THAT CHART.

    Note: the moolatrikona range check uses the planet's D-1 degree-within-sign,
    since divisional charts don't carry their own sub-degree. This is standard.
    """
    dignity = {}
    for p, d in dchart["planets"].items():
        birth_deg = chart["planets"][p].get("deg_in_sign", 0.0)
        dignity[p] = _dignity(p, d["sign_vedic"], birth_deg)
    return dignity

# -------------------------------------------------------------------
# Public API
# -------------------------------------------------------------------
def compute_d1(chart):
    return _compute_chart(chart, 1)


def compute_d9(chart):
    return _compute_chart(chart, 9)


def compute_d10(chart):
    return _compute_chart(chart, 10)


def compute_all(chart, divisions=(1, 9, 10)):
    """Return dict: {division: divisional_chart}."""
    return {d: _compute_chart(chart, d) for d in divisions}


# -------------------------------------------------------------------
# Pretty printing for debugging
# -------------------------------------------------------------------
def print_divisional(dchart):
    print(f"\n=== D-{dchart['division']} Chart ===")
    print(f"Ascendant: {dchart['asc_sign_vedic']} ({dchart['asc_sign']})")
    print(f"{'Planet':<10} {'Sign':<15} {'House':>6}")
    print("-" * 40)
    for p in PLANET_ORDER:
        d = dchart["planets"].get(p)
        if not d:
            continue
        print(f"{p:<10} {d['sign_vedic']:<15} {d['house']:>6}")


# -------------------------------------------------------------------
# Self-test
# -------------------------------------------------------------------
if __name__ == "__main__":
    from calculator import calculate_chart
    from enrich import enrich_chart

    chart = calculate_chart("Test", "2000-03-03", "15:00", "New Delhi, India")
    chart = enrich_chart(chart)

    for div in (1, 9, 10):
        dchart = compute_all(chart, divisions=[div])[div]
        print_divisional(dchart)
        print("Dignity:", compute_divisional_dignity(dchart, chart))