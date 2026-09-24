# agent.py
# -------------------------------------------------------------------
# Vedic Reading Generator — Format B (planet-by-planet)
# with enriched Vedic data (dignity, lordships, friendship, etc.)
# -------------------------------------------------------------------

import json
import os
from calculator import calculate_chart
from enrich import enrich_chart
from dasha import format_dasha_markdown

KB_PATH = os.path.join("data", "interpretations.json")

PLANET_ORDER = ["Sun", "Moon", "Mars", "Mercury", "Jupiter", "Venus", "Saturn", "Rahu", "Ketu"]


# -------------------------------------------------------------------
# Load knowledge base
# -------------------------------------------------------------------
def load_knowledge_base():
    if not os.path.exists(KB_PATH):
        raise FileNotFoundError(
            f"Knowledge base not found at '{KB_PATH}'. "
            "Please create data/interpretations.json."
        )
    with open(KB_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


# -------------------------------------------------------------------
# Header block
# -------------------------------------------------------------------
def build_header(chart):
    asc = chart["ascendant"]
    lines = []
    lines.append(f"# Vedic Reading for {chart['name']}")
    lines.append("")
    lines.append(f"**Birth:** {chart['local_time']} ({chart['timezone']})")
    lines.append(f"**Place:** {chart['place']} (Lat {chart['latitude']:.4f}, Lon {chart['longitude']:.4f})")
    lines.append(f"**UTC:** {chart['utc_time']}")
    lines.append("")
    lines.append(
        f"**Lagna (Ascendant):** {asc['sign_vedic']} ({asc['sign']}) — "
        f"{asc['deg_in_sign_dms']} — Nakshatra: {asc['nakshatra']} (pada {asc['nakshatra_pada']})"
    )
    lines.append(
        f"**Lagna Lord:** {asc['sign_lord']} placed in "
        f"{asc.get('lagna_lord_sign', '?')} (House {asc.get('lagna_lord_house', '?')})"
    )
    lines.append("")
    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# -------------------------------------------------------------------
# Position data block for a planet
# -------------------------------------------------------------------
def format_position_data(p):
    """Return a compact 'Position data' block for a planet."""
    qualities = p.get("sign_qualities", {})
    element = qualities.get("element", "?")
    gender = qualities.get("gender", "?")
    mobility = qualities.get("mobility", "?")

    from enrich import ordinal
    functional = p.get("functional_lordships", [])
    func_str = ", ".join(ordinal(h) for h in functional) if functional else "—"

    retro = "Yes" if p.get("retrograde") else "No"
    combust = "Yes" if p.get("combust") else "No"

    lines = [
        "**Position data**",
        f"- Longitude: {p['longitude']:.4f}°  ({p['deg_in_sign_dms']} in {p['sign_vedic']})",
        f"- Sign: {p['sign_vedic']} ({p['sign']}) — {element}, {gender}, {mobility}",
        f"- House: {p['house']}",
        f"- Nakshatra: {p['nakshatra']} pada {p['nakshatra_pada']} (lord: {p['nakshatra_lord']})",
        f"- Sign lord: {p['sign_lord']} — {p['sign_relationship']}",
        f"- Dignity: {p['dignity']}",
        f"- Functional lordship (this Lagna): {func_str}",
        f"- Retrograde: {retro}  |  Combust: {combust}",
    ]
    return "\n".join(lines)


# -------------------------------------------------------------------
# Ascendant section
# -------------------------------------------------------------------
def build_ascendant_section(chart, kb):
    asc = chart["ascendant"]
    sign_v = asc["sign_vedic"]
    nak = asc["nakshatra"]

    lines = []
    lines.append(f"## Lagna — {sign_v} ({asc['sign']})")
    lines.append("")

    # Position data
    qualities = asc.get("sign_qualities", {})
    lines.append("**Position data**")
    lines.append(f"- Longitude: {asc['longitude']:.4f}°  ({asc['deg_in_sign_dms']} in {sign_v})")
    lines.append(
        f"- Sign: {sign_v} ({asc['sign']}) — "
        f"{qualities.get('element', '?')}, "
        f"{qualities.get('gender', '?')}, "
        f"{qualities.get('mobility', '?')}"
    )
    lines.append(f"- Nakshatra: {nak} pada {asc['nakshatra_pada']} (lord: {asc['nakshatra_lord']})")
    lines.append(f"- Lagna lord: {asc['sign_lord']}")
    lines.append("")

    # Interpretation
    asc_rule = kb.get("ascendant_in_sign", {}).get(sign_v)
    if asc_rule:
        lines.append(asc_rule)
        lines.append("")

    nak_rule = kb.get("nakshatra", {}).get(nak)
    if nak_rule:
        lines.append(f"The Lagna falls in **{nak}** nakshatra. {nak_rule}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# -------------------------------------------------------------------
# One planet section
# -------------------------------------------------------------------
def build_planet_section(pname, p, kb):
    sign_v = p["sign_vedic"]
    sign = p["sign"]
    house = p["house"]
    nak = p["nakshatra"]

    lines = []
    lines.append(f"## {pname} — {sign_v} ({sign}), House {house}, {nak} pada {p['nakshatra_pada']}")
    lines.append("")

    # Enriched position block
    lines.append(format_position_data(p))
    lines.append("")

    # Interpretation lines
    sign_rule = kb.get("planet_in_sign", {}).get(pname, {}).get(sign_v)
    if sign_rule:
        lines.append(sign_rule)
        lines.append("")

    house_rule = kb.get("planet_in_house", {}).get(pname, {}).get(str(house))
    if house_rule:
        lines.append(house_rule)
        lines.append("")

    nak_rule = kb.get("nakshatra", {}).get(nak)
    if nak_rule:
        lines.append(f"Nakshatra: {nak_rule}")
        lines.append("")

    lines.append("---")
    lines.append("")
    return "\n".join(lines)


# -------------------------------------------------------------------
# Summary block
# -------------------------------------------------------------------
def build_summary(chart, kb):
    asc = chart["ascendant"]
    moon = chart["planets"]["Moon"]
    sun = chart["planets"]["Sun"]

    lines = []
    lines.append("## Summary — The Big Three")
    lines.append("")

    asc_rule = kb.get("ascendant_in_sign", {}).get(asc["sign_vedic"])
    if asc_rule:
        lines.append(f"**Lagna ({asc['sign_vedic']}):** {asc_rule}")
        lines.append("")

    for label, p in [("Sun", sun), ("Moon", moon)]:
        sign_rule = kb.get("planet_in_sign", {}).get(label, {}).get(p["sign_vedic"])
        if sign_rule:
            lines.append(f"**{label} in {p['sign_vedic']}, House {p['house']}:** {sign_rule}")
            lines.append("")

    return "\n".join(lines)


# -------------------------------------------------------------------
# Full reading
# -------------------------------------------------------------------
def build_reading(chart, kb):
    parts = []
    parts.append(build_header(chart))
    parts.append(build_ascendant_section(chart, kb))

    for pname in PLANET_ORDER:
        p = chart["planets"].get(pname)
        if not p:
            continue
        parts.append(build_planet_section(pname, p, kb))

    parts.append(build_summary(chart, kb))

    # Add Vimshottari Dasha section
    parts.append(format_dasha_markdown(chart))

    parts.append("---")
    parts.append("")
    parts.append(
        "*This reading is generated for educational purposes. "
        "It is based on classical Vedic astrology principles and "
        "is not a substitute for consultation with a qualified astrologer.*"
    )

    return "\n".join(parts)


# -------------------------------------------------------------------
# Main entry
# -------------------------------------------------------------------
def predict(name, date_str, time_str, place_name):
    print("Calculating chart...")
    chart = calculate_chart(name, date_str, time_str, place_name)

    print("Enriching with Vedic dignity data...")
    chart = enrich_chart(chart)

    print("Loading knowledge base...")
    kb = load_knowledge_base()

    print("Building reading...")
    reading = build_reading(chart, kb)

    return chart, reading


if __name__ == "__main__":
    print("Vedic Astrology Agent (Format B — Enriched)")
    print("------------------------------------------")
    name = input("Enter name: ").strip()
    date_str = input("Enter date of birth (YYYY-MM-DD): ").strip()
    time_str = input("Enter time of birth (HH:MM or HH:MM:SS): ").strip()
    place_name = input("Enter place of birth: ").strip()

    chart, reading = predict(name, date_str, time_str, place_name)

    print("\n" + "=" * 78)
    print("CHART SUMMARY")
    print("=" * 78)
    from calculator import print_chart
    print_chart(chart)

    out_name = f"reading_{name.replace(' ', '_')}.md"
    with open(out_name, "w", encoding="utf-8") as f:
        f.write(reading)
    print(f"\nReading saved to: {out_name}")

    print("\n" + "=" * 78)
    print("VEDIC READING")
    print("=" * 78)
    print(reading)
    print("=" * 78)