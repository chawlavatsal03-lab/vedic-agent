# chart_image.py
# -------------------------------------------------------------------
# North Indian (diamond) chart renderer.
#
# Regions are defined as polygons. Sign numbers and planet rows are
# placed at the polygon's CENTROID, nudged toward the chart center
# so labels always sit inside the region.
# -------------------------------------------------------------------

ABBR = {
    "Sun": "Su", "Moon": "Mo", "Mars": "Ma", "Mercury": "Me",
    "Jupiter": "Ju", "Venus": "Ve", "Saturn": "Sa",
    "Rahu": "Ra", "Ketu": "Ke",
}

SIZE = 620
MARGIN = 40
INNER = SIZE - 2 * MARGIN

# 12 regions. Coordinates in normalized units: (-1..1) on both axes,
# with (0,0) at chart center. Outer square corners: (±1, ±1).
REGIONS = {
    1:  [(0, -1), (0.5, -0.5), (0, 0), (-0.5, -0.5)],       # top diamond
    2:  [(-1, -1), (0, -1), (-0.5, -0.5)],                    # top-left tri
    3:  [(-1, -1), (-1, 0), (-0.5, -0.5)],                    # left-upper tri
    4:  [(-1, 0), (-1, 1), (-0.5, 0.5), (-0.5, -0.5)],        # left diamond
    5:  [(-1, 0), (-1, 1), (-0.5, 0.5)],                      # left-lower tri -- actually bottom-left-upper
    6:  [(-1, 1), (0, 1), (-0.5, 0.5)],                       # bottom-left tri
    7:  [(0, 1), (0.5, 0.5), (0, 0), (-0.5, 0.5)],            # bottom diamond
    8:  [(1, 1), (0, 1), (0.5, 0.5)],                         # bottom-right tri
    9:  [(1, 0), (1, 1), (0.5, 0.5)],                         # right-lower tri -- actually bottom-right-upper
    10: [(1, 0), (1, -1), (0.5, -0.5), (0.5, 0.5)],           # right diamond
    11: [(1, -1), (1, 0), (0.5, -0.5)],                       # upper-right tri
    12: [(1, -1), (0, -1), (0.5, -0.5)],                      # top-right tri
}

# Wait — the "left diamond" is not H4 alone. Let me get the standard
# arrangement right. In a North Indian chart:
#   H1 = top diamond (top-center)
#   H2 = top-left triangle
#   H3 = upper-left triangle (side)
#   H4 = left diamond (left-center)
#   H5 = lower-left triangle (side)
#   H6 = bottom-left triangle
#   H7 = bottom diamond (bottom-center)
#   H8 = bottom-right triangle
#   H9 = lower-right triangle (side)
#   H10 = right diamond (right-center)
#   H11 = upper-right triangle (side)
#   H12 = top-right triangle
#
# The "left diamond" H4 is actually formed by:
#   (-1,-1),(-1,1),(0,1),(0,-1)  -- no, that's the whole left half.
#
# Correct: the left "diamond" is bounded by (-1,0),(0,0),(-0.5,-0.5),(-0.5,0.5)?
# No. Look at the shape. The left diamond has vertices:
#   (-1,-1)? No.
# Let me just use the mathematically correct decomposition.

REGIONS = {
    # Top diamond (H1): between the top edge and the inner diamond
    1:  [(0, -1), (0.5, -0.5), (0, 0), (-0.5, -0.5)],

    # Top-left triangle (H2): bounded by top edge, left edge, and diagonal
    2:  [(-1, -1), (0, -1), (-0.5, -0.5)],

    # Left-upper side triangle (H3): bounded by left edge, diagonal, and inner diamond
    3:  [(-1, -1), (-0.5, -0.5), (-1, 0)],

    # Left diamond (H4): the small diamond to the left of center
    4:  [(-1, 0), (-0.5, -0.5), (0, 0), (-0.5, 0.5)],

    # Left-lower side triangle (H5): bounded by left edge, inner diamond, and diagonal
    5:  [(-1, 0), (-0.5, 0.5), (-1, 1)],

    # Bottom-left triangle (H6): bounded by bottom edge, left edge, and diagonal
    6:  [(-1, 1), (0, 1), (-0.5, 0.5)],

    # Bottom diamond (H7)
    7:  [(0, 1), (0.5, 0.5), (0, 0), (-0.5, 0.5)],

    # Bottom-right triangle (H8)
    8:  [(1, 1), (0, 1), (0.5, 0.5)],

    # Right-lower side triangle (H9)
    9:  [(1, 0), (1, 1), (0.5, 0.5)],

    # Right diamond (H10)
    10: [(1, 0), (0.5, 0.5), (0, 0), (0.5, -0.5)],

    # Right-upper side triangle (H11)
    11: [(1, -1), (1, 0), (0.5, -0.5)],

    # Top-right triangle (H12)
    12: [(1, -1), (0, -1), (0.5, -0.5)],
}


def _centroid(verts):
    """Return (x, y) centroid of a polygon."""
    xs = [v[0] for v in verts]
    ys = [v[1] for v in verts]
    return sum(xs) / len(xs), sum(ys) / len(ys)


def _nudge_toward_center(cx, cy, factor=0.15):
    """Move a point toward (0,0) by the given factor of its distance."""
    return cx * (1 - factor), cy * (1 - factor)


COLORS = {
    1:  "#B3E5FC", 2:  "#FFF9C4", 3:  "#C8E6C9", 4:  "#E1BEE7",
    5:  "#FFCCBC", 6:  "#FFE0B2", 7:  "#FFF59D", 8:  "#F8BBD0",
    9:  "#B2DFDB", 10: "#FFECB3", 11: "#D1C4E9", 12: "#CFD8DC",
}


def _escape(s):
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _dignity_color(dignity):
    if dignity == "Exalted":
        return "#1565C0"
    if dignity == "Debilitated":
        return "#C62828"
    if dignity == "Moolatrikona":
        return "#2E7D32"
    if dignity == "Own Sign":
        return "#6A1B9A"
    return "#000000"


def render_north_indian(dchart, title=None, dignity_lookup=None):
    asc = dchart["asc_sign_index"]

    planets_by_house = {h: [] for h in range(1, 13)}
    for p, d in dchart["planets"].items():
        planets_by_house[d["house"]].append((p, d))

    cx = SIZE / 2
    cy = SIZE / 2
    half = INNER / 2

    def P(xn, yn):
        return (cx + xn * half, cy + yn * half)

    parts = []
    parts.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {SIZE} {SIZE}" width="{SIZE}" height="{SIZE}">'
    )
    parts.append(f'<rect width="{SIZE}" height="{SIZE}" fill="#FFFFFF"/>')

    if title:
        parts.append(
            f'<text x="{cx}" y="24" font-family="Georgia, serif" '
            f'font-size="18" font-weight="bold" text-anchor="middle" '
            f'fill="#333">{_escape(title)}</text>'
        )

    # --- Fill regions ---
    for house, verts in REGIONS.items():
        pts = " ".join(f"{P(x, y)[0]:.2f},{P(x, y)[1]:.2f}" for x, y in verts)
        fill = COLORS.get(house, "#EEEEEE")
        parts.append(f'<polygon points="{pts}" fill="{fill}" stroke="none"/>')

    # --- Grid lines ---
    x0, y0 = P(-1, -1)
    x1, y1 = P(1, 1)
    xm, yt = P(0, -1)
    xr, ym = P(1, 0)
    xm2, yb = P(0, 1)
    xl, ym2 = P(-1, 0)

    parts.append(
        f'<rect x="{x0:.2f}" y="{y0:.2f}" width="{(x1 - x0):.2f}" '
        f'height="{(y1 - y0):.2f}" fill="none" stroke="#000" stroke-width="1.5"/>'
    )
    parts.append(f'<line x1="{x0:.2f}" y1="{y0:.2f}" x2="{x1:.2f}" y2="{y1:.2f}" stroke="#000" stroke-width="1.2"/>')
    parts.append(f'<line x1="{x1:.2f}" y1="{y0:.2f}" x2="{x0:.2f}" y2="{y1:.2f}" stroke="#000" stroke-width="1.2"/>')
    parts.append(f'<line x1="{xm:.2f}" y1="{yt:.2f}" x2="{xr:.2f}" y2="{ym:.2f}" stroke="#000" stroke-width="1.2"/>')
    parts.append(f'<line x1="{xr:.2f}" y1="{ym:.2f}" x2="{xm2:.2f}" y2="{yb:.2f}" stroke="#000" stroke-width="1.2"/>')
    parts.append(f'<line x1="{xm2:.2f}" y1="{yb:.2f}" x2="{xl:.2f}" y2="{ym2:.2f}" stroke="#000" stroke-width="1.2"/>')
    parts.append(f'<line x1="{xl:.2f}" y1="{ym2:.2f}" x2="{xm:.2f}" y2="{yt:.2f}" stroke="#000" stroke-width="1.2"/>')

    # --- Text ---
    for house in range(1, 13):
        verts = REGIONS[house]
        cx_n, cy_n = _centroid(verts)
        # Nudge toward chart center so text sits comfortably inside
        tx_n, ty_n = _nudge_toward_center(cx_n, cy_n, factor=0.12)
        tx, ty = P(tx_n, ty_n)

        # Slight vertical offset for sign number vs planets
        # Sign number is placed ABOVE planets (or below, depending on region).
        # Use a small vertical gap (in pixels).
        gap_px = 18

        # Determine direction: sign number above, planets below (in chart-Y terms).
        # In chart coords, -1 is top, +1 is bottom. So "above" = smaller y.
        # We want sign number always closer to the outer corner.
        # For top-regions (H1, H2, H12): outer is up (smaller y) → sign above planets.
        # For bottom-regions (H6, H7, H8): outer is down (larger y) → sign below planets.
        # For left (H3, H4, H5): outer is left; but text reads left-to-right, so keep sign above.
        # Simpler: always put sign above planets.
        sign_y = ty - gap_px / 2
        planet_y = ty + gap_px / 2 + 6

        sign_idx = ((house - 1) + asc) % 12
        sign_num = sign_idx + 1

        if house == 1:
            parts.append(
                f'<text x="{tx:.1f}" y="{sign_y - 22:.1f}" '
                f'font-family="Georgia, serif" font-size="12" '
                f'font-weight="bold" text-anchor="middle" fill="#000">'
                f'Lagna</text>'
            )

        parts.append(
            f'<text x="{tx:.1f}" y="{sign_y:.1f}" '
            f'font-family="Georgia, serif" font-size="16" '
            f'font-weight="bold" text-anchor="middle" '
            f'fill="#C62828">{sign_num}</text>'
        )

        planets_here = planets_by_house[house]
        if not planets_here:
            continue
        planets_here.sort(key=lambda x: x[0])

        labels = []
        for p, d in planets_here:
            lbl = ABBR.get(p, p[:2])
            if d.get("retrograde"):
                lbl += "\u1D3F"
            if d.get("combust"):
                lbl += "\u1D9C"
            color = "#000"
            if dignity_lookup and p in dignity_lookup:
                color = _dignity_color(dignity_lookup[p])
            labels.append((lbl, color))

        n = len(labels)
        slot_px = 34
        total_width = n * slot_px
        start_x = tx - total_width / 2 + slot_px / 2

        for i, (lbl, color) in enumerate(labels):
            px = start_x + i * slot_px
            parts.append(
                f'<text x="{px:.1f}" y="{planet_y:.1f}" '
                f'font-family="Georgia, serif" font-size="14" '
                f'font-weight="bold" text-anchor="middle" fill="{color}">'
                f'{lbl}</text>'
            )

    parts.append("</svg>")
    return "".join(parts)


if __name__ == "__main__":
    from calculator import calculate_chart
    from enrich import enrich_chart
    from divisional import compute_d1, compute_d9, compute_d10

    chart = calculate_chart("Test", "2000-03-03", "15:00", "New Delhi, India")
    chart = enrich_chart(chart)
    dignity = {p: d["dignity"] for p, d in chart["planets"].items()}

    for label, compute, division in [
        ("D-1", compute_d1, "Rashi"),
        ("D-9", compute_d9, "Navamsa"),
        ("D-10", compute_d10, "Dasamsa"),
    ]:
        dchart = compute(chart)
        svg = render_north_indian(
            dchart,
            title=f"{dchart['asc_sign_vedic']} Lagna ({label} {division})",
            dignity_lookup=dignity,
        )
        fname = f"chart_{label.lower().replace('-','')}.svg"
        with open(fname, "w", encoding="utf-8") as f:
            f.write(svg)
        print(f"Wrote {fname}")