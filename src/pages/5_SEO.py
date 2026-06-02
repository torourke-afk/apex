"""
SEO — Organic search rankings, traffic, and keyword performance
"""

import streamlit as st
import plotly.graph_objects as go

from src.components.filter_bar import get_global_filters
from src.components.card_container import card_container, card_container_end
from src.components.chart_wrapper import branded_chart
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer
from src.config.brand import COLORS, CHART_PALETTE

page_chrome(title="SEO")
filters = get_global_filters()

# ---------------------------------------------------------------------------
# Seed data (will be replaced with live connectors)
# ---------------------------------------------------------------------------

_ORGANIC_KPI = [
    ("Organic Sessions", "1.42M", "+8.3%", True),
    ("Non-Brand Clicks", "312K", "+12.1%", True),
    ("Avg Position", "14.2", "-1.8", True),
    ("Click-Through Rate", "3.8%", "+0.4 pts", True),
    ("Indexed Pages", "24.8K", "+1.2K", True),
    ("Core Web Vitals Pass", "87%", "+3 pts", True),
]

_KEYWORD_RANKINGS = [
    {"Keyword": "best checking account", "Position": 4, "Change": -2, "Volume": 18_100, "Page": "/checking"},
    {"Keyword": "high yield savings", "Position": 8, "Change": 1, "Volume": 33_100, "Page": "/savings/high-yield"},
    {"Keyword": "free checking account near me", "Position": 6, "Change": -3, "Volume": 12_400, "Page": "/checking/free"},
    {"Keyword": "cd rates today", "Position": 12, "Change": 0, "Volume": 49_500, "Page": "/cd-rates"},
    {"Keyword": "student checking account", "Position": 3, "Change": -1, "Volume": 8_100, "Page": "/checking/student"},
    {"Keyword": "money market rates", "Position": 15, "Change": 2, "Volume": 27_100, "Page": "/money-market"},
    {"Keyword": "bank near me", "Position": 7, "Change": -1, "Volume": 90_500, "Page": "/locations"},
    {"Keyword": "mobile banking app", "Position": 11, "Change": -4, "Volume": 14_800, "Page": "/mobile"},
    {"Keyword": "home equity loan rates", "Position": 18, "Change": 3, "Volume": 22_200, "Page": "/home-equity"},
    {"Keyword": "online savings account", "Position": 9, "Change": -2, "Volume": 40_500, "Page": "/savings/online"},
]

_ORGANIC_TRAFFIC_WEEKS = list(range(1, 13))
_ORGANIC_TRAFFIC_SESSIONS = [118_000, 121_000, 115_000, 128_000, 132_000, 125_000,
                              138_000, 141_000, 135_000, 148_000, 152_000, 142_000]
_ORGANIC_TRAFFIC_BRAND = [42_000, 43_000, 41_000, 45_000, 46_000, 44_000,
                           48_000, 49_000, 47_000, 52_000, 53_000, 50_000]
_ORGANIC_TRAFFIC_NONBRAND = [s - b for s, b in zip(_ORGANIC_TRAFFIC_SESSIONS, _ORGANIC_TRAFFIC_BRAND)]

_TOP_PAGES = [
    {"Page": "/checking", "Sessions": 245_000, "Bounce Rate": "32%", "Avg Time": "2:45", "Conversions": 4_120},
    {"Page": "/savings/high-yield", "Sessions": 198_000, "Bounce Rate": "28%", "Avg Time": "3:12", "Conversions": 3_580},
    {"Page": "/cd-rates", "Sessions": 156_000, "Bounce Rate": "35%", "Avg Time": "2:18", "Conversions": 2_210},
    {"Page": "/locations", "Sessions": 142_000, "Bounce Rate": "45%", "Avg Time": "1:32", "Conversions": 890},
    {"Page": "/mobile", "Sessions": 118_000, "Bounce Rate": "38%", "Avg Time": "2:55", "Conversions": 1_650},
]


# ── KPI Strip ─────────────────────────────────────────────────────────────
card_container(title="Organic Search Overview", subtitle="Last 30 days — Google Search Console + GA4")
kpi_cols = st.columns(6)
for col, (label, value, delta, is_good) in zip(kpi_cols, _ORGANIC_KPI):
    color = COLORS["success"] if is_good else COLORS["error"]
    with col:
        st.markdown(
            f"""<div style="padding:0.6rem 0;">
            <div style="font-size:0.6rem;font-weight:600;text-transform:uppercase;color:{COLORS['text_secondary']};margin-bottom:0.25rem;">{label}</div>
            <div style="font-size:1.4rem;font-weight:700;color:{COLORS['text_primary']};">{value}</div>
            <div style="font-size:0.7rem;color:{color};">{delta}</div>
            </div>""",
            unsafe_allow_html=True,
        )
card_container_end()

# ── Organic Traffic Trend ─────────────────────────────────────────────────
card_container(title="Organic Traffic Trend", subtitle="Weekly sessions — Brand vs Non-Brand")
fig = go.Figure()
fig.add_trace(go.Scatter(
    x=_ORGANIC_TRAFFIC_WEEKS, y=_ORGANIC_TRAFFIC_NONBRAND,
    name="Non-Brand", fill="tozeroy",
    line=dict(color=COLORS["primary"], width=2),
    fillcolor="rgba(0, 117, 255, 0.15)",
))
fig.add_trace(go.Scatter(
    x=_ORGANIC_TRAFFIC_WEEKS, y=_ORGANIC_TRAFFIC_BRAND,
    name="Brand", fill="tozeroy",
    line=dict(color=COLORS["secondary"], width=2),
    fillcolor="rgba(0, 210, 255, 0.10)",
))
fig.update_layout(
    height=300,
    xaxis_title="Week",
    yaxis_title="Sessions",
    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
)
branded_chart(fig, height=300, key="seo_traffic_trend")
card_container_end()

# ── Keyword Rankings ──────────────────────────────────────────────────────
card_container(title="Keyword Rankings", subtitle="Top tracked keywords — position changes vs prior period")
import pandas as pd
kw_df = pd.DataFrame(_KEYWORD_RANKINGS)
# Add visual change indicator
kw_df["Δ"] = kw_df["Change"].apply(lambda c: f"▲ {abs(c)}" if c < 0 else (f"▼ {abs(c)}" if c > 0 else "—"))
kw_df["Volume"] = kw_df["Volume"].apply(lambda v: f"{v:,}")
display_kw = kw_df[["Keyword", "Position", "Δ", "Volume", "Page"]]
st.dataframe(display_kw, use_container_width=True, hide_index=True, height=360)
card_container_end()

# ── Top Pages by Organic Traffic ──────────────────────────────────────────
card_container(title="Top Landing Pages", subtitle="Highest organic traffic pages with conversion data")
pages_df = pd.DataFrame(_TOP_PAGES)
pages_df["Sessions"] = pages_df["Sessions"].apply(lambda v: f"{v:,}")
pages_df["Conversions"] = pages_df["Conversions"].apply(lambda v: f"{v:,}")
st.dataframe(pages_df, use_container_width=True, hide_index=True)
card_container_end()

# ── Content Gap Callout ───────────────────────────────────────────────────
st.markdown(
    f"""<div style="background:{COLORS['surface_sunken']};border-left:3px solid {COLORS['warning']};border-radius:0 6px 6px 0;padding:0.65rem 0.9rem;margin-top:0.5rem;font-size:0.78rem;color:{COLORS['text_secondary']};">
    <strong style="color:{COLORS['text_primary']};">Content Gap Alert:</strong>&nbsp;
    12 high-volume keywords (10K+ monthly searches) have no dedicated landing page. Top opportunity:
    <strong style="color:{COLORS['warning']};">"no fee checking account"</strong> (22K searches/mo, currently ranking position 34).
    Creating a targeted page could capture an estimated 2,800 additional monthly visits.
    </div>""",
    unsafe_allow_html=True,
)

render_chat_drawer(page_key="seo")
