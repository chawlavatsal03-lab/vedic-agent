# calculator.py
# -------------------------------------------------------------------
# Vedic Astrology Chart Calculator
# Uses Swiss Ephemeris via swisseph-ffi.
#
# Astrological choices (documented for reproducibility):
#   - Ayanamsa:     Lahiri (SE_SIDM_LAHIRI), the official Indian standard.
#   - Zodiac:       Sidereal (SEFLG_SIDEREAL).
#   - Houses:       Whole-sign ('W' / ord('W') = 87).
#   - Nodes:        Mean Node (SE_MEAN_NODE) — matches classical Vedic
#                   convention. Switch to SE_TRUE_NODE to match AstroSage
#                   and other modern software.
#   - Planet set:   Sun, Moon, Mars, Mercury, Jupiter, Venus, Saturn,
#                   Rahu (mean node), Ketu (Rahu + 180°).
#   - Time base:    Julian Day computed from UTC.
# -------------------------------------------------------------------

from swisseph_ffi import (
    SwissEph, SE_GREG_CAL,
    SE_SUN, SE_MOON, SE_MARS, SE_MERCURY, SE_JUPITER, SE_VENUS, SE_SATURN,
    SE_MEAN_NODE,
    SEFLG_SIDEREAL, SEFLG_SPEED, SE_SIDM_LAHIRI,
    c_double, create_string_buffer,
)
from geopy.geocoders import Nominatim, Photon
from timezonefinder import TimezoneFinder
import pytz
import time
from datetime import datetime

# -------------------------------------------------------------------
# Swiss Ephemeris setup
# -------------------------------------------------------------------
swe = SwissEph()
swe.swe_set_sid_mode(SE_SIDM_LAHIRI, 0, 0)

SIGNS = [
    "Aries", "Taurus", "Gemini", "Cancer", "Leo", "Virgo",
    "Libra", "Scorpio", "Sagittarius", "Capricorn", "Aquarius", "Pisces"
]
SIGNS_VEDIC = [
    "Mesha", "Vrishabha", "Mithuna", "Karka", "Simha", "Kanya",
    "Tula", "Vrischika", "Dhanu", "Makara", "Kumbha", "Meena"
]
NAKSHATRAS = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati"
]

PLANETS = {
    "Sun":     SE_SUN,
    "Moon":    SE_MOON,
    "Mars":    SE_MARS,
    "Mercury": SE_MERCURY,
    "Jupiter": SE_JUPITER,
    "Venus":   SE_VENUS,
    "Saturn":  SE_SATURN,
    "Rahu":    SE_MEAN_NODE,
}

# User agent: Nominatim's usage policy requires a real contact identifier.
# Replace the email with your own before going commercial.
NOMINATIM_USER_AGENT = "vedic_agent_v1 (vatsal@yourdomain.com)"

# -------------------------------------------------------------------
# Geocoding and timezone
# -------------------------------------------------------------------
def geocode_place(place_name, retries=3):
    """Geocode a place name to (lat, lon), trying Photon first, then Nominatim."""
    # --- Try Photon first (faster, no rate limit issues) ---
    try:
        photon = Photon(user_agent="vedic_agent_v1")
        location = photon.geocode(place_name, timeout=15)
        if location is not None:
            return location.latitude, location.longitude
    except Exception:
        pass  # fall through to Nominatim

    # --- Fallback to Nominatim (with retries) ---
    geolocator = Nominatim(user_agent=NOMINATIM_USER_AGENT)
    last_error = None
    for attempt in range(retries):
        try:
            location = geolocator.geocode(place_name, timeout=15)
            if location is not None:
                return location.latitude, location.longitude
        except Exception as e:
            last_error = e
        time.sleep(1)

    if last_error is not None:
        raise ValueError(
            f"Could not geocode place: '{place_name}' after {retries} attempts. "
            f"Last error: {last_error}"
        )
    raise ValueError(
        f"Could not geocode place: '{place_name}'. "
        "Try adding a country, e.g. 'Mumbai, India'."
    )


def get_timezone(lat, lon):
    tf = TimezoneFinder()
    tz_name = tf.timezone_at(lat=lat, lng=lon)
    if tz_name is None:
        raise ValueError(
            f"Could not determine timezone for coordinates "
            f"lat={lat}, lon={lon}."
        )
    return tz_name


def to_julian_day(date_str, time_str, tz_name):
    """Convert local date/time to Julian Day in UT."""
    time_str = time_str.strip()
    if time_str.count(":") == 2:
        fmt = "%Y-%m-%d %H:%M:%S"
    else:
        fmt = "%Y-%m-%d %H:%M"

    try:
        local_dt = datetime.strptime(f"{date_str} {time_str}", fmt)
    except ValueError:
        raise ValueError(
            f"Invalid date/time. Use date YYYY-MM-DD and time HH:MM or HH:MM:SS. "
            f"You entered date='{date_str}' time='{time_str}'."
        )

    tz = pytz.timezone(tz_name)
    local_dt = tz.localize(local_dt)
    utc_dt = local_dt.astimezone(pytz.utc)

    hour_decimal = utc_dt.hour + utc_dt.minute / 60.0 + utc_dt.second / 3600.0
    jd = swe.swe_julday(utc_dt.year, utc_dt.month, utc_dt.day, hour_decimal, SE_GREG_CAL)
    return jd, utc_dt


# -------------------------------------------------------------------
# Astrology helpers
# -------------------------------------------------------------------
def get_sign(longitude):
    idx = int(longitude / 30) % 12
    return idx, SIGNS[idx], SIGNS_VEDIC[idx]


def get_nakshatra(longitude):
    idx = int(longitude / (360 / 27)) % 27
    return idx, NAKSHATRAS[idx]


def get_house(longitude, asc_sign_index):
    """Whole-sign house: house 1 = ascendant's sign, house 2 = next sign, etc."""
    sign_idx = int(longitude / 30) % 12
    return ((sign_idx - asc_sign_index) % 12) + 1


def calc_planet(jd, planet_id):
    """
    Return (longitude, latitude, distance, speed) in the sidereal zodiac.
    Raises RuntimeError if Swiss Ephemeris reports an error.
    """
    xx = (c_double * 6)()
    serr = create_string_buffer(256)
    flags = SEFLG_SIDEREAL | SEFLG_SPEED

    ret = swe.swe_calc_ut(jd, planet_id, flags, xx, serr)
    if ret < 0:
        msg = serr.value.decode(errors="ignore") if serr.value else "unknown error"
        raise RuntimeError(f"Swiss Ephemeris planet calculation failed: {msg}")

    return xx[0], xx[1], xx[2], xx[3]


def calc_houses(jd, lat, lon):
    """
    Return (cusps, ascmc) for whole-sign houses in the sidereal zodiac.
    Raises RuntimeError if Swiss Ephemeris reports an error.
    """
    cusps = (c_double * 13)()
    ascmc = (c_double * 10)()

    ret = swe.swe_houses_ex(jd, SEFLG_SIDEREAL, lat, lon, ord('W'), cusps, ascmc)
    if ret < 0:
        raise RuntimeError("Swiss Ephemeris houses calculation failed.")

    return cusps, ascmc


# -------------------------------------------------------------------
# Main chart calculation
# -------------------------------------------------------------------
def calculate_chart(name, date_str, time_str, place_name):
    lat, lon = geocode_place(place_name)
    tz_name = get_timezone(lat, lon)
    jd, utc_dt = to_julian_day(date_str, time_str, tz_name)

    cusps, ascmc = calc_houses(jd, lat, lon)
    asc_longitude = ascmc[0]
    asc_sign_idx, asc_sign, asc_sign_vedic = get_sign(asc_longitude)
    _, asc_nak = get_nakshatra(asc_longitude)

    results = {
        "name": name,
        "place": place_name,
        "latitude": lat,
        "longitude": lon,
        "timezone": tz_name,
        "local_time": f"{date_str} {time_str}",
        "utc_time": utc_dt.strftime("%Y-%m-%d %H:%M:%S"),
        "julian_day": jd,
        "ascendant": {
            "longitude": asc_longitude,
            "sign": asc_sign,
            "sign_vedic": asc_sign_vedic,
            "nakshatra": asc_nak,
        },
        "planets": {},
    }

    for pname, pid in PLANETS.items():
        plon, plat, pdist, pspeed = calc_planet(jd, pid)
        _, sign, sign_vedic = get_sign(plon)
        _, nak = get_nakshatra(plon)
        house = get_house(plon, asc_sign_idx)

        results["planets"][pname] = {
            "longitude": plon,
            "latitude": plat,
            "speed": pspeed,
            "sign": sign,
            "sign_vedic": sign_vedic,
            "house": house,
            "nakshatra": nak,
        }

        # Ketu is always 180° opposite Rahu, same speed.
        if pname == "Rahu":
            ketu_lon = (plon + 180.0) % 360.0
            _, k_sign, k_sign_vedic = get_sign(ketu_lon)
            _, k_nak = get_nakshatra(ketu_lon)
            k_house = get_house(ketu_lon, asc_sign_idx)
            results["planets"]["Ketu"] = {
                "longitude": ketu_lon,
                "latitude": -plat,
                "speed": pspeed,
                "sign": k_sign,
                "sign_vedic": k_sign_vedic,
                "house": k_house,
                "nakshatra": k_nak,
            }

    return results


# -------------------------------------------------------------------
# Pretty printing
# -------------------------------------------------------------------
PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


def print_chart(chart):
    print("\n" + "=" * 78)
    print(f"Vedic Birth Chart for {chart['name']}")
    print("=" * 78)
    print(f"Place     : {chart['place']}  (Lat {chart['latitude']:.4f}, Lon {chart['longitude']:.4f})")
    print(f"Timezone  : {chart['timezone']}")
    print(f"Local time: {chart['local_time']}")
    print(f"UTC time  : {chart['utc_time']}")
    print(f"Julian Day: {chart['julian_day']:.6f}")
    print("-" * 78)

    asc = chart["ascendant"]
    print(f"Ascendant : {asc['longitude']:.4f}°  {asc['sign_vedic']} ({asc['sign']})  Nakshatra: {asc['nakshatra']}")
    print("-" * 78)
    print(f"{'Planet':<10} {'Longitude':>11} {'Sign (Vedic)':<16} {'House':>6} {'Nakshatra':<20}")
    print("-" * 78)

    for pname in PLANET_ORDER:
        d = chart["planets"].get(pname)
        if not d:
            continue
        print(f"{pname:<10} {d['longitude']:>11.4f} {d['sign_vedic']:<16} {d['house']:>6} {d['nakshatra']:<20}")

    print("=" * 78)


# -------------------------------------------------------------------
# CLI entry
# -------------------------------------------------------------------
if __name__ == "__main__":
    print("Vedic Astrology Chart Calculator")
    print("--------------------------------")
    name = input("Enter name: ").strip()
    date_str = input("Enter date of birth (YYYY-MM-DD): ").strip()
    time_str = input("Enter time of birth (HH:MM 24h): ").strip()
    place_name = input("Enter place of birth: ").strip()

    chart = calculate_chart(name, date_str, time_str, place_name)
    print_chart(chart)