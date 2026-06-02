import streamlit as st
import plotly.graph_objects as go

from src.components.filter_bar import get_global_filters
from src.components.card_container import card_container, card_container_end
from src.components.kpi_card import kpi_card
from src.components.chart_wrapper import branded_chart
from src.config.brand import COLORS
from src.components.page_chrome import page_chrome
from src.data.retention import (
    get_pfi_milestones,
    get_milestone_kpis,
    get_behavioral_triggers,
    load_cohort_heatmap,
)

page_chrome(title="Onboarding & Retention")
filters = get_global_filters()

ret_filters = {
    "channel": filters["channel"][0] if filters["channel"] else None,
    "quality_band": None,
}

milestones = get_pfi_milestones()
milestone_kpis = get_milestone_kpis()

card_container(title="PFI Flywheel", subtitle="Six milestones that lock in primary banking status")
fly_cols = st.columns(3)
for i, m in enumerate(milestones):
    actual_pct = m["actual"]  # percentage 0-100
    target_pct = m["target"]  # benchmark percentage
    bar_color = COLORS["success"] if actual_pct >= target_pct else (COLORS["warning"] if actual_pct >= target_pct * 0.85 else COLORS["error"])
    with fly_cols[i % 3]:
        st.markdown(
            f"""<div style="padding:0.5rem 0 0.75rem;">
            <div style="font-size:0.78rem;font-weight:700;color:{COLORS['text_primary']};margin-bottom:0.1rem;">{m['milestone']}</div>
            <div style="font-size:0.68rem;color:{COLORS['text_secondary']};margin-bottom:0.5rem;">Target {target_pct:.0f}% by Day {m['window_d']}</div>
            <div style="position:relative;background:{COLORS['border']};border-radius:4px;height:7px;width:100%;margin-bottom:0.35rem;">
                <div style="background:{bar_color};border-radius:4px;height:7px;width:{min(actual_pct, 100):.1f}%;"></div>
                <div style="position:absolute;top:-3px;left:{target_pct:.1f}%;width:2px;height:13px;background:{COLORS['text_secondary']};border-radius:1px;"></div>
            </div>
            <div style="display:flex;justify-content:space-between;">
                <span style="font-size:0.8rem;font-weight:700;color:{bar_color};">{actual_pct:.1f}%</span>
                <span style="font-size:0.7rem;color:{COLORS['text_secondary']};">vs {target_pct:.0f}% target</span>
            </div>
            </div>""",
            unsafe_allow_html=True,
        )
card_container_end()

card_container(title="90-Day Milestone Dashboard")
mk_cols = st.columns(len(milestone_kpis))
for col, kpi in zip(mk_cols, milestone_kpis):
    with col:
        is_below = kpi["value"] < kpi["threshold"]
        alert_text = kpi.get("kamino_text") if is_below else None
        # Wrap each card in a min-height container so all tiles align
        st.markdown('<div style="min-height:180px;">', unsafe_allow_html=True)
        kpi_card(
            title=kpi["title"],
            value=kpi["value"],
            format_type="percent",
            alert_status="warning" if is_below else "success",
            alert_text=alert_text,
        )
        st.markdown('</div>', unsafe_allow_html=True)
card_container_end()

card_container(title="Retention Cohort Heatmap", subtitle="MOB retention rate by acquisition cohort")
heatmap_df = load_cohort_heatmap(ret_filters)
if not heatmap_df.empty:
    # Values are 0-1 scale; convert to percentage for display
    heatmap_df = heatmap_df * 100
    z_vals = heatmap_df.values.tolist()
    fig = go.Figure(go.Heatmap(
        z=z_vals,
        x=list(heatmap_df.columns),
        y=list(heatmap_df.index),
        colorscale=[[0.0, COLORS["error"]], [0.5, COLORS["warning"]], [1.0, COLORS["success"]]],
        zmin=60,
        zmax=95,
        text=[[f"{v:.1f}%" for v in row] for row in z_vals],
        texttemplate="%{text}",
        textfont={"size": 9},
    ))
    fig.update_layout(xaxis_title="Acquisition Cohort", yaxis_title="Month on Book", height=360)
    branded_chart(fig, height=360, key="cohort_heatmap")
else:
    st.info("No cohort data for current filters.")
card_container_end()

card_container(title="Behavioral Trigger Monitor", subtitle="Automated Kamino sequences — volume and conversion rate")
triggers_df = get_behavioral_triggers()
if not triggers_df.empty:
    st.dataframe(triggers_df, use_container_width=True, hide_index=True)
card_container_end()
