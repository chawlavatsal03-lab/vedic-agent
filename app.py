# app.py
# -------------------------------------------------------------------
# Streamlit UI for the Vedic Astrology Agent
#
# Usage:
#   streamlit run app.py
#
# Then open the URL shown in the terminal (usually http://localhost:8501)
# -------------------------------------------------------------------

import streamlit as st
from datetime import date, time, datetime

from calculator import calculate_chart
from enrich import enrich_chart, ordinal
from agent import load_knowledge_base, build_reading, PLANET_ORDER
from dasha import (
    compute_mahadashas,
    find_current_dasha_chain,
    _format_date,
    _format_datetime,
    _format_duration,
)

# -------------------------------------------------------------------
# Page config
# -------------------------------------------------------------------
st.set_page_config(
    page_title="Vedic Astrology Agent",
    page_icon="🪔",
    layout="wide",
)


# -------------------------------------------------------------------
# Custom CSS (small polish)
# -------------------------------------------------------------------
st.markdown(
    """
    <style>
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #8B4513;
        margin-bottom: 0.2rem;
    }
    .subtitle {
        color: #666;
        margin-bottom: 1.5rem;
    }
    .small-note {
        color: #888;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Header
# -------------------------------------------------------------------
st.markdown('<div class="main-title">🪔 Vedic Astrology Agent</div>', unsafe_allow_html=True)
st.markdown(
    '<div class="subtitle">Compute a Vedic birth chart with Lahiri ayanamsa, '
    'sidereal zodiac, whole-sign houses, and generate a classical reading.</div>',
    unsafe_allow_html=True,
)


# -------------------------------------------------------------------
# Input form
# -------------------------------------------------------------------
with st.form("birth_form"):
    col1, col2 = st.columns(2)

    with col1:
        name = st.text_input("Full name", value="", placeholder="e.g. Vatsal Chawla")
        date_input = st.date_input(
            "Date of birth",
            value=date(2000, 3, 3),
            min_value=date(1900, 1, 1),
            max_value=date.today(),
        )

    with col2:
        time_input = st.time_input(
            "Time of birth (24h)",
            value=time(15, 0),
        )
        place = st.text_input(
            "Place of birth",
            value="",
            placeholder="e.g. New Delhi, India",
            help="Include the country for best geocoding accuracy.",
        )

    submitted = st.form_submit_button("Calculate Reading", use_container_width=True)


# -------------------------------------------------------------------
# Process
# -------------------------------------------------------------------
if submitted:
    # Validate
    errors = []
    if not name.strip():
        errors.append("Please enter a name.")
    if not place.strip():
        errors.append("Please enter a place of birth.")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    # Convert inputs to strings that calculator.py expects
    date_str = date_input.strftime("%Y-%m-%d")
    time_str = time_input.strftime("%H:%M")

    # Run the pipeline
    try:
        with st.spinner("Calculating chart..."):
            chart = calculate_chart(name, date_str, time_str, place)

        with st.spinner("Enriching with Vedic dignity data..."):
            chart = enrich_chart(chart)

        with st.spinner("Loading knowledge base and building reading..."):
            kb = load_knowledge_base()
            reading = build_reading(chart, kb)

    except Exception as e:
        st.error(f"Error: {e}")
        st.stop()

    # -------------------------------------------------------------------
    # Store in session so tabs persist
    # -------------------------------------------------------------------
    st.session_state["chart"] = chart
    st.session_state["reading"] = reading


# -------------------------------------------------------------------
# Display results (if we have them)
# -------------------------------------------------------------------
if "chart" in st.session_state and "reading" in st.session_state:
    chart = st.session_state["chart"]
    reading = st.session_state["reading"]
    asc = chart["ascendant"]

    st.success(f"Chart calculated for **{chart['name']}** — {chart['place']}")

    # Top summary cards
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Lagna", f"{asc['sign_vedic']} ({asc['sign']})")
    c2.metric("Lagna Lord", asc["sign_lord"])
    c3.metric("Sun", f"{chart['planets']['Sun']['sign_vedic']} · House {chart['planets']['Sun']['house']}")
    c4.metric("Moon", f"{chart['planets']['Moon']['sign_vedic']} · House {chart['planets']['Moon']['house']}")

    # Tabs
    tab_reading, tab_chart, tab_position, tab_dasha, tab_raw = st.tabs(
        ["📖 Reading", "📊 Chart", "🔬 Position Data", "🕉 Dasha", "📄 Raw Markdown"]
    )

    # --- Reading tab ---
    with tab_reading:
        st.markdown(reading, unsafe_allow_html=False)

        st.download_button(
            label="⬇️ Download reading as Markdown",
            data=reading,
            file_name=f"reading_{chart['name'].replace(' ', '_')}.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # --- Chart tab ---
    with tab_chart:
        rows = []
        for pname in PLANET_ORDER:
            p = chart["planets"].get(pname)
            if not p:
                continue
            rows.append({
                "Planet": pname,
                "Longitude": f"{p['longitude']:.4f}°",
                "Sign (Vedic)": p["sign_vedic"],
                "Sign (English)": p["sign"],
                "House": p["house"],
                "Nakshatra": p["nakshatra"],
                "Pada": p["nakshatra_pada"],
                "Deg in sign": p["deg_in_sign_dms"],
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

    # --- Position Data tab ---
    with tab_position:
        rows = []
        for pname in PLANET_ORDER:
            p = chart["planets"].get(pname)
            if not p:
                continue
            func = ", ".join(ordinal(h) for h in p.get("functional_lordships", [])) or "—"
            rows.append({
                "Planet": pname,
                "Sign": p["sign_vedic"],
                "House": p["house"],
                "DMS": p["deg_in_sign_dms"],
                "Nakshatra": f"{p['nakshatra']} p{p['nakshatra_pada']}",
                "Nak Lord": p["nakshatra_lord"],
                "Sign Lord": p["sign_lord"],
                "Relation": p["sign_relationship"],
                "Dignity": p["dignity"],
                "Functional": func,
                "R": "Yes" if p["retrograde"] else "—",
                "C": "Yes" if p["combust"] else "—",
            })
        st.dataframe(rows, use_container_width=True, hide_index=True)

        st.caption(
            "R = Retrograde, C = Combust. "
            "Functional lordships are for the given Lagna. "
            "Dignity labels follow classical Parashari rules."
        )
    # --- Dasha tab ---
    with tab_dasha:
        try:
            md_data = compute_mahadashas(chart)
            current = find_current_dasha_chain(chart)

            st.subheader("Current 6-Level Dasha Chain")
            if current and current["chain"]:
                rows = []
                labels = [
                    ("1. Mahadasha", "Mahadasha"),
                    ("2. Antardasha", "Antardasha"),
                    ("3. Pratyantardasha", "Pratyantardasha"),
                    ("4. Sookshmadasha", "Sookshmadasha"),
                    ("5. Pranadasha", "Pranadasha"),
                    ("6. Dehadasha", "Dehadasha"),
                ]
                for label, key in labels:
                    p = current["chain"].get(key)
                    if p is None:
                        continue
                    rows.append({
                        "Level": label,
                        "Name": p.get("name", p["lord"]),
                        "Start": _format_datetime(p["start"]),
                        "End": _format_datetime(p["end"]),
                        "Duration": _format_duration(p["years"]),
                    })
                st.dataframe(rows, use_container_width=True, hide_index=True)
                st.caption(f"As of {_format_datetime(current['as_of'])} UTC")
            else:
                st.info("No active dasha found for today's date.")

            st.subheader("Mahadasha Timeline")
            md_rows = []
            for i, md in enumerate(md_data["mahadashas"], 1):
                dur = _format_duration(md["years"])
                if md.get("is_balance"):
                    dur += " (balance)"
                md_rows.append({
                    "#": i,
                    "Mahadasha": md["lord"],
                    "Start": _format_date(md["start"]),
                    "End": _format_date(md["end"]),
                    "Duration": dur,
                })
            st.dataframe(md_rows, use_container_width=True, hide_index=True)

            st.subheader("Antardashas in Current Mahadasha")
            if current and current.get("antardasha_list"):
                ad_rows = []
                md_lord = current["chain"]["Mahadasha"]["lord"]
                for i, ad in enumerate(current["antardasha_list"], 1):
                    ad_rows.append({
                        "#": i,
                        "Antardasha": f"{md_lord}-{ad['lord']}",
                        "Start": _format_date(ad["start"]),
                        "End": _format_date(ad["end"]),
                        "Duration": _format_duration(ad["years"]),
                    })
                st.dataframe(ad_rows, use_container_width=True, hide_index=True)

            st.caption(
                "Vimshottari Dasha based on the Moon's nakshatra at birth. "
                "Six levels: Mahadasha → Antardasha → Pratyantardasha → "
                "Sookshmadasha → Pranadasha → Dehadasha."
            )
        except Exception as e:
            st.error(f"Dasha calculation error: {e}")

    # --- Raw markdown tab ---
    with tab_raw:
        st.code(reading, language="markdown")


# -------------------------------------------------------------------
# Footer
# -------------------------------------------------------------------
st.markdown("---")
st.markdown(
    '<div class="small-note">For educational purposes only. '
    'This reading is generated from classical Vedic astrology principles '
    'and is not a substitute for consultation with a qualified astrologer.</div>',
    unsafe_allow_html=True,
)