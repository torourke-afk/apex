import streamlit as st
import plotly.graph_objects as go
import plotly.express as px

from src.components.filter_bar import get_global_filters
from src.components.card_container import card_container, card_container_end
from src.components.chart_wrapper import branded_chart
from src.components.channel_mix_sliders import channel_mix_sliders as render_channel_mix_sliders
from src.config.brand import COLORS, CHART_PALETTE_EXTENDED
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer
from src.data.spend_queries import (
    get_budget_overview,
    get_channel_spend_breakdown,
    get_market_allocation,
)

_TIER_COLORS = {"T1": COLORS["primary"], "T2": COLORS["warning"], "T3": COLORS["iron"]}

# Lat/lon for DMA bubble map
_DMA_COORDS: dict[str, tuple[float, float]] = {
    "Cincinnati, OH": (39.1031, -84.5120),
    "Columbus, OH": (39.9612, -82.9988),
    "Chicago, IL": (41.8781, -87.6298),
    "Atlanta, GA": (33.7490, -84.3880),
    "Nashville, TN": (36.1627, -86.7816),
    "Dallas-Fort Worth, TX": (32.7767, -96.7970),
    "Houston, TX": (29.7604, -95.3698),
    "Indianapolis, IN": (39.7684, -86.1581),
    "Charlotte, NC": (35.2271, -80.8431),
    "Detroit, MI": (42.3314, -83.0458),
    "Cleveland, OH": (41.4993, -81.6944),
    "Tampa, FL": (27.9506, -82.4572),
    "Orlando, FL": (28.5383, -81.3792),
    "Dayton, OH": (39.7589, -84.1916),
    "Lexington, KY": (38.0406, -84.5037),
    "Louisville, KY": (38.2527, -85.7585),
    "Pittsburgh, PA": (40.4406, -79.9959),
    "Grand Rapids, MI": (42.9634, -85.6681),
    "Toledo, OH": (41.6528, -83.5379),
    "Knoxville, TN": (35.9606, -83.9207),
    "Raleigh-Durham, NC": (35.7796, -78.6382),
}

_TIER_MAP_COLORS = {"T1": COLORS["primary"], "T2": COLORS["warning"], "T3": COLORS["iron"]}


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

def _fmt_currency(val: float) -> str:
    if abs(val) >= 1_000_000:
        return f"${val / 1_000_000:.2f}M"
    if abs(val) >= 1_000:
        return f"${val / 1_000:.0f}K"
    return f"${val:,.0f}"


def _fmt_delta(metric: dict) -> str:
    d = metric.get("delta", 0)
    fmt = metric.get("format", "currency")
    if fmt == "percent":
        sign = "+" if d > 0 else ""
        return f"{sign}{d:+.1f} pts"
    elif fmt == "currency":
        if abs(d) >= 1_000_000:
            return f"{'+' if d > 0 else '-'}${abs(d) / 1_000_000:.2f}M vs prior"
        if abs(d) >= 1_000:
            return f"{'+' if d > 0 else '-'}${abs(d) / 1_000:.0f}K vs prior"
        return f"{'+' if d > 0 else '-'}${abs(d):,.0f} vs prior"
    return f"{d:+.1f}"


def _fmt_value(metric: dict) -> str:
    v = metric.get("value", 0)
    fmt = metric.get("format", "currency")
    if fmt == "percent":
        return f"{v:.1f}%"
    if fmt == "currency":
        return _fmt_currency(v)
    return f"{v:,.0f}"


# ---------------------------------------------------------------------------
# Page layout
# ---------------------------------------------------------------------------

page_chrome(title="Spend Allocation")
filters = get_global_filters()

# ── Budget Overview strip ─────────────────────────────────────────────────
budget_metrics = get_budget_overview(filters)

card_container(title="Budget Overview")
cols = st.columns(4)
for i, m in enumerate(budget_metrics):
    label = m["label"]
    delta = m.get("delta", 0)
    if "CPIHH" in label:
        delta_color = COLORS["success"] if delta <= 0 else COLORS["warning"]
    elif "Pacing" in label:
        delta_color = COLORS["success"] if delta >= 0 else COLORS["warning"]
    else:
        delta_color = COLORS["success"] if delta >= 0 else COLORS["warning"]

    with cols[i]:
        st.markdown(
            f"""<div style="padding:0.75rem 0;">
            <div style="font-size:0.65rem;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;color:{COLORS['text_secondary']};margin-bottom:0.3rem;">{label}</div>
            <div style="font-size:1.8rem;font-weight:700;color:{COLORS['text_primary']};line-height:1.1;">{_fmt_value(m)}</div>
            <div style="font-size:0.75rem;color:{delta_color};margin-top:0.2rem;">{_fmt_delta(m)}</div>
            </div>""",
            unsafe_allow_html=True,
        )
card_container_end()

# ── Pacing & Burn Rate chart (moved to top) ──────────────────────────────
channel_data = get_channel_spend_breakdown(filters)

card_container(title="Pacing & Burn Rate by Channel", subtitle="Actual spend vs plan — filtered period")
fig = go.Figure()
fig.add_trace(go.Bar(
    name="Plan",
    x=channel_data["plan"],
    y=channel_data["categories"],
    orientation="h",
    marker_color=COLORS["border"],
    opacity=0.6,
))
fig.add_trace(go.Bar(
    name="Actual",
    x=channel_data["actual"],
    y=channel_data["categories"],
    orientation="h",
    marker_color=COLORS["primary"],
    text=[f"${v/1e6:.2f}M" for v in channel_data["actual"]],
    textposition="outside",
))
fig.update_layout(barmode="overlay", xaxis_title="Spend ($)", height=300)
branded_chart(fig, height=300, key="budget_pacing")
card_container_end()

# ── DMA Section: Table + Map ─────────────────────────────────────────────
markets = get_market_allocation(filters)

card_container(title="DMA Spend Distribution", subtitle="Geographic market allocation by tier with spend map")

left_col, right_col = st.columns([1.1, 1], gap="medium")

# --- Left: DMA table ---
with left_col:
    _ts = COLORS["text_secondary"]
    _tp = COLORS["text_primary"]
    _bd = COLORS["border"]

    hdr = st.columns([3, 1, 1.5, 1.2, 1.2])
    for col, h in zip(hdr, ["Market", "Tier", "Monthly Spend", "Funded", "CPIHH"]):
        col.markdown(
            f"<span style='font-size:0.65rem;font-weight:600;text-transform:uppercase;"
            f"letter-spacing:0.07em;color:{_ts};'>{h}</span>",
            unsafe_allow_html=True,
        )
    st.markdown(
        f"<hr style='border-color:{_bd};margin:0.3rem 0 0.2rem;'/>",
        unsafe_allow_html=True,
    )
    for row in markets:
        rc = st.columns([3, 1, 1.5, 1.2, 1.2])
        tc = _TIER_COLORS.get(row["Tier"], COLORS["iron"])
        rc[0].markdown(f"<span style='font-size:0.82rem;color:{_tp};'>{row['Market']}</span>", unsafe_allow_html=True)
        rc[1].markdown(f"<span style='font-size:0.8rem;font-weight:600;color:{tc};'>{row['Tier']}</span>", unsafe_allow_html=True)
        rc[2].markdown(f"<span style='font-size:0.8rem;color:{_tp};'>{_fmt_currency(row['Monthly Spend'])}</span>", unsafe_allow_html=True)
        rc[3].markdown(f"<span style='font-size:0.8rem;color:{_tp};'>{row['Funded']:,}</span>", unsafe_allow_html=True)
        rc[4].markdown(f"<span style='font-size:0.8rem;color:{_tp};'>{_fmt_currency(row['CPIHH'])}</span>", unsafe_allow_html=True)

# --- Right: DMA bubble map ---
with right_col:
    # Build map data from markets
    map_lats = []
    map_lons = []
    map_labels = []
    map_spend = []
    map_tiers = []
    map_funded = []
    map_cpihh = []

    for row in markets:
        coords = _DMA_COORDS.get(row["Market"])
        if coords:
            map_lats.append(coords[0])
            map_lons.append(coords[1])
            map_labels.append(row["Market"])
            map_spend.append(row["Monthly Spend"])
            map_tiers.append(row["Tier"])
            map_funded.append(row.get("Funded", 0))
            map_cpihh.append(row.get("CPIHH", 0))

    if map_lats:
        # Scale bubble sizes: sqrt-scale for visual balance, min 12px
        max_spend = max(map_spend) if map_spend else 1
        bubble_sizes = [max(12, 50 * (s / max_spend) ** 0.5) for s in map_spend]

        # Color by tier
        tier_color_map = {"T1": COLORS["primary"], "T2": COLORS["warning"], "T3": COLORS["iron"]}
        bubble_colors = [tier_color_map.get(t, COLORS["iron"]) for t in map_tiers]

        # Build hover text
        hover_texts = [
            f"<b>{lbl}</b><br>"
            f"Tier: {tier}<br>"
            f"Spend: {_fmt_currency(sp)}<br>"
            f"Funded: {fd:,}<br>"
            f"CPIHH: {_fmt_currency(cp)}"
            for lbl, tier, sp, fd, cp in zip(map_labels, map_tiers, map_spend, map_funded, map_cpihh)
        ]

        map_fig = go.Figure()
        map_fig.add_trace(go.Scattergeo(
            lat=map_lats,
            lon=map_lons,
            text=hover_texts,
            hoverinfo="text",
            marker=dict(
                size=bubble_sizes,
                color=bubble_colors,
                opacity=0.75,
                line=dict(width=1, color="rgba(255,255,255,0.3)"),
                sizemode="diameter",
            ),
        ))

        map_fig.update_geos(
            scope="usa",
            showland=True,
            landcolor="rgba(30, 35, 60, 0.6)",
            showlakes=False,
            showcountries=False,
            showsubunits=True,
            subunitcolor="rgba(255,255,255,0.08)",
            bgcolor="rgba(0,0,0,0)",
            framecolor="rgba(255,255,255,0.05)",
            coastlinecolor="rgba(255,255,255,0.1)",
            lakecolor="rgba(0,0,0,0)",
            projection_type="albers usa",
            lonaxis_range=[-105, -72],
            lataxis_range=[25, 47],
        )

        map_fig.update_layout(
            height=340,
            margin=dict(l=0, r=0, t=0, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            geo=dict(bgcolor="rgba(0,0,0,0)"),
            showlegend=False,
        )

        st.plotly_chart(map_fig, use_container_width=True, key="dma_spend_map")

        # Legend
        st.markdown(
            f"<div style='display:flex;gap:1rem;justify-content:center;margin-top:0.25rem;'>"
            f"<span style='font-size:0.7rem;color:{COLORS['primary']};'>● T1 Markets</span>"
            f"<span style='font-size:0.7rem;color:{COLORS['warning']};'>● T2 Markets</span>"
            f"<span style='font-size:0.7rem;color:{COLORS['iron']};'>● T3 Markets</span>"
            f"</div>"
            f"<div style='text-align:center;font-size:0.6rem;color:{COLORS['text_secondary']};margin-top:0.15rem;'>Bubble size = relative spend</div>",
            unsafe_allow_html=True,
        )

card_container_end()

# ── Channel Mix Simulator (moved to bottom) ──────────────────────────────
card_container(title="Channel Mix Control", subtitle="Brand media allocation within approved strategic bands")
render_channel_mix_sliders()
card_container_end()

render_chat_drawer(page_key="spend_alloc")
