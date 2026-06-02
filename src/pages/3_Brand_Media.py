"""
Brand Media — Brand awareness, reach/frequency, BEI, and life events
"""

import os

import duckdb
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from src.components.filter_bar import get_global_filters
from src.components.card_container import card_container, card_container_end
from src.components.chart_wrapper import branded_chart
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer
from src.config.brand import COLORS
from src.data.social_brand_loaders import load_brand_bei, load_life_events


# ---------------------------------------------------------------------------
# DB helpers (shared with Performance Media)
# ---------------------------------------------------------------------------

def _query_db(sql, params=None):
    db_path = os.environ.get("APEX_DB_PATH", "apex_clean.duckdb")
    try:
        con = duckdb.connect(db_path, read_only=True)
        result = con.execute(sql, params or []).fetchdf()
        con.close()
        return result
    except Exception:
        return pd.DataFrame()


def _build_filters(filters, date_col="date", dma_col="dma_name"):
    clauses, params = [], []
    if filters.get("date_start"):
        clauses.append(f"{date_col} >= ?")
        params.append(str(filters["date_start"]))
    if filters.get("date_end"):
        clauses.append(f"{date_col} <= ?")
        params.append(str(filters["date_end"]))
    if filters.get("dma"):
        ph = ", ".join("?" * len(filters["dma"]))
        clauses.append(f"{dma_col} IN ({ph})")
        params.extend(filters["dma"])
    where = " WHERE " + " AND ".join(clauses) if clauses else ""
    return where, params


# ---------------------------------------------------------------------------
# Page setup
# ---------------------------------------------------------------------------

page_chrome(title="Brand Media")
filters = get_global_filters()

brand_where, brand_params = _build_filters(filters)

# ── Brand Media Overview KPIs ─────────────────────────────────────────────
rf_sql = f"""
    SELECT
        SUM(daily_impressions)        AS total_impressions,
        AVG(rolling_30d_reach)        AS avg_30d_reach,
        AVG(rolling_30d_frequency)    AS avg_30d_frequency
    FROM brand_reach_frequency
    {brand_where}
"""
rf_kpi_df = _query_db(rf_sql, brand_params)

card_container(title="Brand Media Overview")
brand_kpi_cols = st.columns(3)
if not rf_kpi_df.empty:
    row = rf_kpi_df.iloc[0]
    total_imp = row.get("total_impressions", 0)
    avg_reach = row.get("avg_30d_reach", 0)
    avg_freq = row.get("avg_30d_frequency", 0)
else:
    total_imp = avg_reach = avg_freq = 0

brand_kpi_items = [
    ("Total Impressions", f"{int(total_imp):,}" if pd.notna(total_imp) else "—"),
    ("Avg 30d Reach", f"{int(avg_reach):,}" if pd.notna(avg_reach) else "—"),
    ("Avg 30d Frequency", f"{avg_freq:.2f}x" if pd.notna(avg_freq) and avg_freq else "—"),
]
for col, (label, val) in zip(brand_kpi_cols, brand_kpi_items):
    with col:
        st.markdown(
            f"""<div style="padding:0.6rem 0;">
            <div style="font-size:0.62rem;font-weight:600;text-transform:uppercase;color:{COLORS['text_secondary']};margin-bottom:0.25rem;">{label}</div>
            <div style="font-size:1.6rem;font-weight:700;color:{COLORS['text_primary']};">{val}</div>
            </div>""",
            unsafe_allow_html=True,
        )
card_container_end()

# ── Impressions by Channel — horizontal bar ───────────────────────────────
ch_sql = f"""
    SELECT
        channel_name,
        SUM(impressions) AS impressions
    FROM brand_media_daily
    {brand_where}
    GROUP BY channel_name
    ORDER BY impressions ASC
"""
ch_df = _query_db(ch_sql, brand_params)

if not ch_df.empty:
    channel_palette = [
        COLORS["primary"], COLORS["secondary"], COLORS["warning"],
        COLORS["success"], COLORS["error"], COLORS.get("iron", "#808080"),
        COLORS["primary"], COLORS["secondary"],
    ]
    ch_colors = [channel_palette[i % len(channel_palette)] for i in range(len(ch_df))]
    card_container(title="Impressions by Channel")
    fig = go.Figure(go.Bar(
        x=ch_df["impressions"],
        y=ch_df["channel_name"],
        orientation="h",
        marker_color=ch_colors,
        text=[f"{v:,.0f}" for v in ch_df["impressions"]],
        textposition="outside",
    ))
    fig.update_layout(
        height=340,
        xaxis_title="Impressions",
        yaxis_title="Channel",
        margin=dict(l=10, r=100, t=20, b=40),
    )
    branded_chart(fig, height=340, key="brand_impressions_by_channel")
    card_container_end()

# ── Reach & Frequency by DMA — table ─────────────────────────────────────
dma_sql = f"""
    SELECT
        dma_name                        AS "DMA",
        SUM(daily_impressions)          AS "Impressions",
        AVG(rolling_30d_reach)          AS "30d Reach",
        AVG(rolling_30d_frequency)      AS "30d Frequency"
    FROM brand_reach_frequency
    {brand_where}
    GROUP BY dma_name
    ORDER BY SUM(daily_impressions) DESC
"""
dma_df = _query_db(dma_sql, brand_params)

if not dma_df.empty:
    card_container(title="Reach & Frequency by DMA")
    display_dma = dma_df.copy()
    if "Impressions" in display_dma.columns:
        display_dma["Impressions"] = display_dma["Impressions"].map("{:,.0f}".format)
    if "30d Reach" in display_dma.columns:
        display_dma["30d Reach"] = display_dma["30d Reach"].map("{:,.0f}".format)
    if "30d Frequency" in display_dma.columns:
        display_dma["30d Frequency"] = display_dma["30d Frequency"].map("{:.2f}x".format)
    st.dataframe(display_dma, use_container_width=True, hide_index=True)
    card_container_end()

# ── Campaign Breakdown by Creative ────────────────────────────────────────
creative_sql = f"""
    SELECT
        creative_name               AS "Creative",
        channel_name                AS "Channel",
        SUM(impressions)            AS "Impressions",
        SUM(interactions)           AS "Interactions",
        SUM(spend)                  AS "Spend"
    FROM brand_media_daily
    {brand_where}
    GROUP BY creative_name, channel_name
    ORDER BY SUM(spend) DESC
"""
creative_df = _query_db(creative_sql, brand_params)

if not creative_df.empty:
    card_container(title="Campaign Breakdown by Creative")
    display_creative = creative_df.copy()
    if "Impressions" in display_creative.columns:
        display_creative["Impressions"] = display_creative["Impressions"].map("{:,.0f}".format)
    if "Interactions" in display_creative.columns:
        display_creative["Interactions"] = display_creative["Interactions"].map("{:,.0f}".format)
    if "Spend" in display_creative.columns:
        display_creative["Spend"] = display_creative["Spend"].map("${:,.0f}".format)
    st.dataframe(display_creative, use_container_width=True, hide_index=True)
    card_container_end()

# ── Life Event Campaigns ──────────────────────────────────────────────────
events_df = load_life_events()
if not events_df.empty:
    card_container(title="Life Event Campaigns", subtitle="8 always-on segments · Target 2–3× mass market CVR")
    st.dataframe(events_df, use_container_width=True, hide_index=True)
    card_container_end()

render_chat_drawer(page_key="brand_media")
