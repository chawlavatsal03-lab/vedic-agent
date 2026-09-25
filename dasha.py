# force-redeploy 2026-09-26
# dasha.py
# -------------------------------------------------------------------
# Vimshottari Dasha — full 6-level hierarchy
#
# Level 1: Mahadasha        (years)
# Level 2: Antardasha       (months to years)
# Level 3: Pratyantardasha  (weeks to months)
# Level 4: Sookshmadasha    (days to weeks)
# Level 5: Pranadasha       (hours to days)
# Level 6: Dehadasha        (minutes to hours)
#
# Sequence always starts with the parent's lord and cycles through
# the standard Vimshottari sequence.
#
# Reference: Parashara Hora Shastra, Ch. 46–47.
# -------------------------------------------------------------------

from datetime import datetime, timedelta

# -------------------------------------------------------------------
# Fixed Vimshottari rules
# -------------------------------------------------------------------
DASHA_SEQUENCE = ["Ketu", "Venus", "Sun", "Moon", "Mars", "Rahu", "Jupiter", "Saturn", "Mercury"]
DASHA_YEARS = {
    "Ketu":    7,
    "Venus":  20,
    "Sun":     6,
    "Moon":   10,
    "Mars":    7,
    "Rahu":   18,
    "Jupiter": 16,
    "Saturn":  19,
    "Mercury": 17,
}
TOTAL_YEARS = sum(DASHA_YEARS.values())  # 120

# 27 nakshatras in order
NAKSHATRA_ORDER = [
    "Ashwini", "Bharani", "Krittika", "Rohini", "Mrigashira", "Ardra",
    "Punarvasu", "Pushya", "Ashlesha", "Magha", "Purva Phalguni", "Uttara Phalguni",
    "Hasta", "Chitra", "Swati", "Vishakha", "Anuradha", "Jyeshtha",
    "Mula", "Purva Ashadha", "Uttara Ashadha", "Shravana", "Dhanishta", "Shatabhisha",
    "Purva Bhadrapada", "Uttara Bhadrapada", "Revati",
]

# The nakshatra lord cycles through these 9 planets, in this order.
NAKSHATRA_LORD_CYCLE = DASHA_SEQUENCE  # starts with Ketu


# -------------------------------------------------------------------
# Time utilities
# -------------------------------------------------------------------
def _add_years(dt, years):
    """Add a fractional number of years (Julian year = 365.2425 days)."""
    return dt + timedelta(days=years * 365.2425)


def _add_days(dt, days):
    return dt + timedelta(days=days)


def _format_date(dt):
    return dt.strftime("%Y-%m-%d")


def _format_datetime(dt):
    return dt.strftime("%Y-%m-%d %H:%M")


def _format_duration(years):
    """Format a duration in years as 'Xy Ym Zd'."""
    if years >= 1.0:
        y = int(years)
        rem_months = (years - y) * 12
        m = int(rem_months)
        d = int((rem_months - m) * 30)
        return f"{y}y {m}m {d}d"
    elif years * 365.2425 >= 1:
        days = years * 365.2425
        d = int(days)
        h = int((days - d) * 24)
        return f"{d}d {h}h"
    else:
        hours = years * 365.2425 * 24
        h = int(hours)
        m = int((hours - h) * 60)
        return f"{h}h {m}m"


# -------------------------------------------------------------------
# Nakshatra helpers
# -------------------------------------------------------------------
def _starting_lord(moon_longitude):
    """Vimshottari starting lord from the Moon's nakshatra."""
    nak_span = 360.0 / 27.0
    nak_idx = int(moon_longitude / nak_span) % 27
    return NAKSHATRA_LORD_CYCLE[nak_idx % 9]


def _balance_fraction(moon_longitude):
    """Fraction of the Moon's nakshatra still remaining at birth."""
    nak_span = 360.0 / 27.0
    pos_in_nak = moon_longitude % nak_span
    return 1.0 - (pos_in_nak / nak_span)


# -------------------------------------------------------------------
# Core: build a dasha tree recursively
# -------------------------------------------------------------------
def _build_sub_periods(parent_lord, parent_start, parent_end):
    """
    Given a parent period (lord + start + end), build its 9 sub-periods
    using the proportional Vimshottari rule.
    """
    total_seconds = (parent_end - parent_start).total_seconds()
    parent_years = total_seconds / (365.2425 * 86400)

    seq_idx = DASHA_SEQUENCE.index(parent_lord)
    sub_periods = []
    cursor = parent_start

    for i in range(9):
        planet = DASHA_SEQUENCE[(seq_idx + i) % 9]
        frac = DASHA_YEARS[planet] / TOTAL_YEARS
        sub_years = parent_years * frac
        sub_end = cursor + timedelta(seconds=sub_years * 365.2425 * 86400)

        sub_periods.append({
            "lord": planet,
            "start": cursor,
            "end": sub_end,
            "years": sub_years,
        })
        cursor = sub_end

    return sub_periods


def _find_sub_at(periods, when):
    """Find which sub-period contains the given datetime."""
    for p in periods:
        if p["start"] <= when < p["end"]:
            return p
    return None


# -------------------------------------------------------------------
# Main calculation
# -------------------------------------------------------------------
def compute_mahadashas(chart, num_periods=9):
    """Compute the Mahadasha timeline from birth."""
    moon = chart["planets"]["Moon"]
    moon_lon = moon["longitude"]

    starting_lord = _starting_lord(moon_lon)
    balance_frac = _balance_fraction(moon_lon)
    balance_years = DASHA_YEARS[starting_lord] * balance_frac

    birth_dt = datetime.strptime(chart["utc_time"], "%Y-%m-%d %H:%M:%S")

    seq_idx = DASHA_SEQUENCE.index(starting_lord)
    periods = []
    cursor = birth_dt

    # First period: the balance of the starting dasha
    first_end = _add_years(cursor, balance_years)
    periods.append({
        "lord": starting_lord,
        "start": cursor,
        "end": first_end,
        "years": balance_years,
        "is_balance": True,
    })
    cursor = first_end

    # Full periods after the first
    for i in range(1, num_periods):
        planet = DASHA_SEQUENCE[(seq_idx + i) % 9]
        years = DASHA_YEARS[planet]
        end = _add_years(cursor, years)
        periods.append({
            "lord": planet,
            "start": cursor,
            "end": end,
            "years": years,
            "is_balance": False,
        })
        cursor = end

    return {
        "moon_longitude": moon_lon,
        "moon_nakshatra": moon["nakshatra"],
        "starting_lord": starting_lord,
        "balance_years": balance_years,
        "mahadashas": periods,
    }


def find_current_dasha_chain(chart, as_of=None):
    """
    Return the full 6-level dasha chain active at the given datetime.
    If as_of is None, use current UTC time.
    """
    if as_of is None:
        from datetime import timezone
        as_of = datetime.now(timezone.utc).replace(tzinfo=None)

    md_data = compute_mahadashas(chart)

    # Find Mahadasha
    md = None
    for p in md_data["mahadashas"]:
        if p["start"] <= as_of < p["end"]:
            md = p
            break
    if md is None:
        return None

    # Level 2: Antardasha
    ad_list = _build_sub_periods(md["lord"], md["start"], md["end"])
    ad = _find_sub_at(ad_list, as_of)
    if ad is None:
        return {"as_of": as_of, "chain": [md], "mahadasha_data": md_data}
    ad["name"] = f"{md['lord']}-{ad['lord']}"

    # Level 3: Pratyantardasha
    pd_list = _build_sub_periods(ad["lord"], ad["start"], ad["end"])
    pd = _find_sub_at(pd_list, as_of)
    if pd:
        pd["name"] = f"{md['lord']}-{ad['lord']}-{pd['lord']}"

    # Level 4: Sookshmadasha
    sd_list = _build_sub_periods(pd["lord"], pd["start"], pd["end"]) if pd else []
    sd = _find_sub_at(sd_list, as_of) if sd_list else None
    if sd:
        sd["name"] = f"{md['lord']}-{ad['lord']}-{pd['lord']}-{sd['lord']}"

    # Level 5: Pranadasha
    prd_list = _build_sub_periods(sd["lord"], sd["start"], sd["end"]) if sd else []
    prd = _find_sub_at(prd_list, as_of) if prd_list else None
    if prd:
        prd["name"] = f"{md['lord']}-{ad['lord']}-{pd['lord']}-{sd['lord']}-{prd['lord']}"

    # Level 6: Dehadasha
    dd_list = _build_sub_periods(prd["lord"], prd["start"], prd["end"]) if prd else []
    dd = _find_sub_at(dd_list, as_of) if dd_list else None
    if dd:
        dd["name"] = f"{md['lord']}-{ad['lord']}-{pd['lord']}-{sd['lord']}-{prd['lord']}-{dd['lord']}"

    chain = {
        "Mahadasha": md,
        "Antardasha": ad,
        "Pratyantardasha": pd,
        "Sookshmadasha": sd,
        "Pranadasha": prd,
        "Dehadasha": dd,
    }

    return {
        "as_of": as_of,
        "chain": chain,
        "mahadasha_data": md_data,
        "antardasha_list": ad_list,
    }


# -------------------------------------------------------------------
# Markdown output
# -------------------------------------------------------------------
def format_dasha_markdown(chart):
    md_data = compute_mahadashas(chart)
    lines = []

    lines.append("## Vimshottari Dasha")
    lines.append("")
    lines.append(
        f"**Moon at birth:** {md_data['moon_longitude']:.4f}° "
        f"({md_data['moon_nakshatra']} nakshatra)"
    )
    lines.append(f"**Starting Dasha:** {md_data['starting_lord']}")
    lines.append(
        f"**Balance at birth:** {_format_duration(md_data['balance_years'])}"
    )
    lines.append("")

    # --- Mahadasha timeline ---
    lines.append("### Mahadasha Timeline")
    lines.append("")
    lines.append("| # | Mahadasha | Start | End | Duration |")
    lines.append("|---|-----------|-------|-----|----------|")
    for i, md in enumerate(md_data["mahadashas"], 1):
        dur = _format_duration(md["years"])
        if md["is_balance"]:
            dur += " (balance)"
        lines.append(
            f"| {i} | {md['lord']} | {_format_date(md['start'])} "
            f"| {_format_date(md['end'])} | {dur} |"
        )
    lines.append("")

    # --- Current 6-level chain ---
    current = find_current_dasha_chain(chart)
    if not current:
        lines.append("*No active dasha found for current date.*")
        return "\n".join(lines)

    lines.append(f"### Current Dasha Chain (as of {_format_datetime(current['as_of'])} UTC)")
    lines.append("")
    lines.append("| Level | Name | Lord | Start | End | Duration |")
    lines.append("|-------|------|------|-------|-----|----------|")
    labels = ["1. Mahadasha", "2. Antardasha", "3. Pratyantardasha",
              "4. Sookshmadasha", "5. Pranadasha", "6. Dehadasha"]
    keys = ["Mahadasha", "Antardasha", "Pratyantardasha",
            "Sookshmadasha", "Pranadasha", "Dehadasha"]
    for label, key in zip(labels, keys):
        p = current["chain"][key]
        if p is None:
            continue
        name = p.get("name", p["lord"])
        lines.append(
            f"| {label} | {name} | {p['lord']} | "
            f"{_format_datetime(p['start'])} | {_format_datetime(p['end'])} | "
            f"{_format_duration(p['years'])} |"
        )
    lines.append("")

    # --- Antardasha table for the current Mahadasha ---
    md = current["chain"]["Mahadasha"]
    ad_list = _build_sub_periods(md["lord"], md["start"], md["end"])
    lines.append(f"### Antardashas within {md['lord']} Mahadasha")
    lines.append("")
    lines.append("| # | Antardasha | Start | End | Duration |")
    lines.append("|---|------------|-------|-----|----------|")
    for i, ad in enumerate(ad_list, 1):
        lines.append(
            f"| {i} | {md['lord']}-{ad['lord']} | {_format_date(ad['start'])} "
            f"| {_format_date(ad['end'])} | {_format_duration(ad['years'])} |"
        )
    lines.append("")

    return "\n".join(lines)


# -------------------------------------------------------------------
# Self-test
# -------------------------------------------------------------------
if __name__ == "__main__":
    from calculator import calculate_chart
    from enrich import enrich_chart

    chart = calculate_chart("Test", "2000-03-03", "15:00", "New Delhi, India")
    chart = enrich_chart(chart)
    print(format_dasha_markdown(chart))