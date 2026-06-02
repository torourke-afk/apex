"""
Performance Media — SEM, Paid Social, and HV Segment Overlay
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
from src.data.sem_loaders import load_sem_overview
from src.data.social_brand_loaders import load_social_overview, load_social_platforms


# ---------------------------------------------------------------------------
# DB helpers
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

page_chrome(title="Performance Media")
filters = get_global_filters()

tab_sem, tab_social = st.tabs(["Paid Search (SEM)", "Paid Social"])

# ===========================================================================
# SEM Tab
# ===========================================================================
with tab_sem:
    sem = load_sem_overview(filters=filters)

    _SEM_ITEMS = [
        ("Avg CPC", sem.get("avg_cpc", 1.15), 1.15, "currency", True),
        ("CTR", sem.get("blended_ctr", 0.155) * 100, 15.5, "percent", False),
        ("CVR", sem.get("blended_cvr", 0.055) * 100, 5.5, "percent", False),
        ("CPL", sem.get("blended_cpl", 20.91), 20.91, "currency", True),
        ("Avg Quality Score", sem.get("avg_quality_score", 7.5), 7.0, "number", False),
        ("Impression Share", sem.get("avg_impression_share", 0.65) * 100, 65.0, "percent", False),
    ]

    card_container(title="SEM Performance Overview")
    kpi_cols = st.columns(3)
    for i, (label, val, bench, fmt, invert) in enumerate(_SEM_ITEMS):
        pct_diff = ((val - bench) / bench) * 100 if bench else 0
        is_good = pct_diff <= 0 if invert else pct_diff >= 0
        color = COLORS["success"] if is_good else COLORS["error"]
        fmt_val = f"${val:.2f}" if fmt == "currency" else (f"{val:.1f}%" if fmt == "percent" else f"{val:.1f}")
        bench_str = f"${bench:.2f}" if fmt == "currency" else (f"{bench:.1f}%" if fmt == "percent" else f"{bench:.1f}")
        with kpi_cols[i % 3]:
            st.markdown(
                f"""<div style="padding:0.6rem 0;">
                <div style="font-size:0.62rem;font-weight:600;text-transform:uppercase;color:{COLORS['text_secondary']};margin-bottom:0.25rem;">{label}</div>
                <div style="font-size:1.6rem;font-weight:700;color:{COLORS['text_primary']};">{fmt_val}</div>
                <div style="font-size:0.7rem;color:{color};">Bench: {bench_str}</div>
                </div>""",
                unsafe_allow_html=True,
            )
    card_container_end()

    type_color_map = {
        "brand": COLORS["primary"],
        "non-brand": COLORS["secondary"],
        "pmax": COLORS["warning"],
    }

    # SEM Spend by Intent Type
    intent_where, intent_params = _build_filters(filters)
    intent_sql = f"""
        SELECT campaign_type, SUM(spend) AS spend
        FROM sem_daily {intent_where}
        GROUP BY campaign_type
        ORDER BY spend DESC
    """
    intent_df = _query_db(intent_sql, intent_params)

    card_container(title="SEM Spend by Intent Type")
    if not intent_df.empty:
        total_sem_spend = intent_df["spend"].sum()
        _label_map = {"brand": "Branded", "non-brand": "Non-Branded", "pmax": "PMax"}
        intent_labels = [_label_map.get(t, t) for t in intent_df["campaign_type"]]
        intent_pcts = [f"{s/total_sem_spend:.0%}" for s in intent_df["spend"]]
        fig = go.Figure(go.Bar(
            x=intent_labels,
            y=intent_df["spend"].tolist(),
            marker_color=[type_color_map.get(t, COLORS["iron"]) for t in intent_df["campaign_type"]],
            text=intent_pcts,
            textposition="outside",
        ))
    else:
        fig = go.Figure(go.Bar(
            x=["Branded", "Non-Branded", "PMax"],
            y=[sem.get("total_spend", 26_000_000) * p for p in [0.30, 0.53, 0.17]],
            marker_color=[COLORS["primary"], COLORS["secondary"], COLORS["warning"]],
            text=["30%", "53%", "17%"],
            textposition="outside",
        ))
    fig.update_layout(yaxis_title="Spend ($)", height=280)
    branded_chart(fig, height=280, key="sem_intent")
    card_container_end()

    # Google vs Bing
    eng_sql = f"""
        SELECT search_engine, SUM(spend) AS spend, SUM(clicks) AS clicks,
               SUM(impressions) AS impressions
        FROM sem_daily {intent_where}
        GROUP BY search_engine ORDER BY spend DESC
    """
    eng_df = _query_db(eng_sql, intent_params)

    if not eng_df.empty and len(eng_df) > 1:
        card_container(title="Google vs Bing", subtitle="Spend split by search engine")
        eng_cols = st.columns(2)
        for col_ui, (_, row) in zip(eng_cols, eng_df.iterrows()):
            eng_name = str(row["search_engine"]).capitalize()
            with col_ui:
                st.markdown(
                    f"""<div style="padding:0.6rem 0;">
                    <div style="font-size:0.62rem;font-weight:600;text-transform:uppercase;color:{COLORS['text_secondary']};margin-bottom:0.25rem;">{eng_name}</div>
                    <div style="font-size:1.4rem;font-weight:700;color:{COLORS['text_primary']};">${row['spend']:,.0f}</div>
                    <div style="font-size:0.7rem;color:{COLORS['iron']};">{int(row['clicks']):,} clicks · {int(row['impressions']):,} imps</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        card_container_end()

    # SEM Campaign Performance Table
    where, params = _build_filters(filters)
    camp_sql = f"""
        SELECT
            campaign_name                            AS "Campaign",
            search_engine                            AS "Engine",
            campaign_type                            AS "Type",
            SUM(spend)                               AS "Spend",
            SUM(clicks)                              AS "Clicks",
            AVG(ctr)                                 AS "CTR",
            AVG(avg_cpc)                             AS "CPC",
            SUM(conversions)                         AS "Conversions",
            CASE WHEN SUM(clicks) > 0
                 THEN SUM(conversions) / SUM(clicks)
                 ELSE 0 END                          AS "CVR"
        FROM sem_daily
        {where}
        GROUP BY campaign_name, search_engine, campaign_type
        ORDER BY SUM(spend) DESC
        LIMIT 10
    """
    camp_df = _query_db(camp_sql, params)

    if not camp_df.empty:
        card_container(title="SEM Campaign Performance", subtitle="Top 10 by Spend")
        display_df = camp_df.copy()
        if "Spend" in display_df.columns:
            display_df["Spend"] = display_df["Spend"].map("${:,.0f}".format)
        if "CPC" in display_df.columns:
            display_df["CPC"] = display_df["CPC"].map("${:.2f}".format)
        if "CTR" in display_df.columns:
            display_df["CTR"] = display_df["CTR"].map("{:.1%}".format)
        if "CVR" in display_df.columns:
            display_df["CVR"] = display_df["CVR"].map("{:.1%}".format)
        if "Conversions" in display_df.columns:
            display_df["Conversions"] = display_df["Conversions"].map("{:,.0f}".format)
        if "Clicks" in display_df.columns:
            display_df["Clicks"] = display_df["Clicks"].map("{:,.0f}".format)
        st.dataframe(display_df, use_container_width=True, hide_index=True)
        card_container_end()

    # SEM Weekly Trend
    trend_sql = f"""
        SELECT
            DATE_TRUNC('week', date::DATE) AS week,
            SUM(spend)                     AS spend,
            SUM(clicks)                    AS clicks
        FROM sem_daily
        {where}
        GROUP BY 1
        ORDER BY 1
    """
    trend_df = _query_db(trend_sql, params)

    if not trend_df.empty:
        card_container(title="SEM Weekly Trend", subtitle="Spend & Clicks over time")
        fig2 = go.Figure()
        fig2.add_trace(go.Scatter(
            x=trend_df["week"], y=trend_df["spend"],
            name="Spend ($)", line=dict(color=COLORS["primary"], width=2), yaxis="y1",
        ))
        fig2.add_trace(go.Scatter(
            x=trend_df["week"], y=trend_df["clicks"],
            name="Clicks", line=dict(color=COLORS["secondary"], width=2, dash="dot"), yaxis="y2",
        ))
        fig2.update_layout(
            height=300,
            yaxis=dict(title="Spend ($)", title_font=dict(color=COLORS["primary"]),
                       tickfont=dict(color=COLORS["primary"])),
            yaxis2=dict(title="Clicks", title_font=dict(color=COLORS["secondary"]),
                        tickfont=dict(color=COLORS["secondary"]),
                        overlaying="y", side="right"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        branded_chart(fig2, height=300, key="sem_weekly_trend")
        card_container_end()

    # Quality Score by Campaign Type
    qs_sql = f"""
        SELECT campaign_type AS "Campaign Type", AVG(quality_score) AS "Avg Quality Score"
        FROM sem_daily {where}
        GROUP BY campaign_type ORDER BY campaign_type
    """
    qs_df = _query_db(qs_sql, params)

    if not qs_df.empty:
        bar_colors = [type_color_map.get(str(t).lower(), COLORS["iron"]) for t in qs_df["Campaign Type"]]
        card_container(title="Quality Score by Campaign Type")
        fig3 = go.Figure(go.Bar(
            x=qs_df["Campaign Type"], y=qs_df["Avg Quality Score"],
            marker_color=bar_colors,
            text=[f"{v:.1f}" for v in qs_df["Avg Quality Score"]],
            textposition="outside",
        ))
        fig3.update_layout(height=280, yaxis=dict(title="Avg Quality Score", range=[0, 10]), xaxis_title="Campaign Type")
        branded_chart(fig3, height=280, key="sem_quality_score")
        card_container_end()

# ===========================================================================
# Social Tab
# ===========================================================================
with tab_social:
    social = load_social_overview()
    platforms_df = load_social_platforms()

    card_container(title="Paid Social Performance Overview")
    soc_cols = st.columns(4)
    soc_items = [
        ("CPL — Native Forms", f"${social.get('blended_cpl', 52.40):.2f}", "Bench: $50–80"),
        ("Native Lead CVR", f"{social.get('blended_cvr', 0.13)*100:.1f}%", "Bench: 13%"),
        ("AI vs Manual CPA Lift", f"${social.get('ai_vs_manual_cpa_delta', 8.20):.2f}", "AI cheaper"),
        ("1st-Party Audiences", f"{social.get('active_first_party_audience_count', 16)}", "Bench: 15+"),
    ]
    for col, (label, val, note) in zip(soc_cols, soc_items):
        with col:
            st.markdown(
                f"""<div style="padding:0.6rem 0;">
                <div style="font-size:0.62rem;font-weight:600;text-transform:uppercase;color:{COLORS['text_secondary']};margin-bottom:0.25rem;">{label}</div>
                <div style="font-size:1.5rem;font-weight:700;color:{COLORS['text_primary']};">{val}</div>
                <div style="font-size:0.7rem;color:{COLORS['iron']};">{note}</div>
                </div>""",
                unsafe_allow_html=True,
            )
    card_container_end()

    if not platforms_df.empty:
        card_container(title="Platform Breakdown")
        st.dataframe(platforms_df, use_container_width=True, hide_index=True)
        card_container_end()

    # Platform Spend Distribution
    soc_where, soc_params = _build_filters(filters)
    plat_sql = f"""
        SELECT platform, SUM(spend) AS spend
        FROM social_paid_daily {soc_where}
        GROUP BY platform ORDER BY spend ASC
    """
    plat_spend_df = _query_db(plat_sql, soc_params)

    if not plat_spend_df.empty:
        platform_palette = [COLORS["primary"], COLORS["secondary"], COLORS["warning"],
                            COLORS["success"], COLORS["error"], COLORS.get("iron", "#808080")]
        bar_colors_plat = [platform_palette[i % len(platform_palette)] for i in range(len(plat_spend_df))]
        card_container(title="Platform Spend Distribution")
        fig4 = go.Figure(go.Bar(
            x=plat_spend_df["spend"], y=plat_spend_df["platform"], orientation="h",
            marker_color=bar_colors_plat,
            text=[f"${v:,.0f}" for v in plat_spend_df["spend"]], textposition="outside",
        ))
        fig4.update_layout(height=300, xaxis_title="Spend ($)", margin=dict(l=10, r=80, t=20, b=40))
        branded_chart(fig4, height=300, key="social_platform_spend")
        card_container_end()

    # Social Engagement Metrics
    eng_sql = f"""
        SELECT SUM(likes) AS total_likes, SUM(shares) AS total_shares,
               SUM(comments) AS total_comments, SUM(video_views) AS total_video_views
        FROM social_paid_daily {soc_where}
    """
    eng_df = _query_db(eng_sql, soc_params)

    if not eng_df.empty:
        row = eng_df.iloc[0]
        eng_items = [
            ("Total Likes", row.get("total_likes", 0)),
            ("Total Shares", row.get("total_shares", 0)),
            ("Total Comments", row.get("total_comments", 0)),
            ("Total Video Views", row.get("total_video_views", 0)),
        ]
        card_container(title="Social Engagement Metrics")
        eng_cols = st.columns(4)
        for col, (label, val) in zip(eng_cols, eng_items):
            with col:
                display_val = f"{int(val):,}" if pd.notna(val) else "—"
                st.markdown(
                    f"""<div style="padding:0.6rem 0;">
                    <div style="font-size:0.62rem;font-weight:600;text-transform:uppercase;color:{COLORS['text_secondary']};margin-bottom:0.25rem;">{label}</div>
                    <div style="font-size:1.5rem;font-weight:700;color:{COLORS['text_primary']};">{display_val}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
        card_container_end()

    # Social Weekly Trend
    soc_trend_sql = f"""
        SELECT DATE_TRUNC('week', date::DATE) AS week, SUM(spend) AS spend, SUM(clicks) AS clicks
        FROM social_paid_daily {soc_where}
        GROUP BY 1 ORDER BY 1
    """
    soc_trend_df = _query_db(soc_trend_sql, soc_params)

    if not soc_trend_df.empty:
        card_container(title="Social Weekly Trend", subtitle="Spend & Clicks over time")
        fig5 = go.Figure()
        fig5.add_trace(go.Scatter(
            x=soc_trend_df["week"], y=soc_trend_df["spend"],
            name="Spend ($)", line=dict(color=COLORS["primary"], width=2), yaxis="y1",
        ))
        fig5.add_trace(go.Scatter(
            x=soc_trend_df["week"], y=soc_trend_df["clicks"],
            name="Clicks", line=dict(color=COLORS["secondary"], width=2, dash="dot"), yaxis="y2",
        ))
        fig5.update_layout(
            height=300,
            yaxis=dict(title="Spend ($)", title_font=dict(color=COLORS["primary"]),
                       tickfont=dict(color=COLORS["primary"])),
            yaxis2=dict(title="Clicks", title_font=dict(color=COLORS["secondary"]),
                        tickfont=dict(color=COLORS["secondary"]),
                        overlaying="y", side="right"),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        )
        branded_chart(fig5, height=300, key="social_weekly_trend")
        card_container_end()

render_chat_drawer(page_key="perf_media")
