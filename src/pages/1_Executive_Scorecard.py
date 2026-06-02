import pandas as pd
import streamlit as st

from src.components.filter_bar import get_global_filters
from src.components.card_container import card_container, card_container_end
from src.components.kpi_card import kpi_card
from src.components.metric_strip import metric_strip
from src.components.section_header import section_header
from src.components.alert_badge import badge_html
from src.components.data_table import render_campaign_table
from src.config.brand import COLORS
from src.data.scorecard_queries import get_kpi_summary, get_financial_summary, get_recent_alerts, get_campaign_performance
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

_SEVERITY_COLORS = {
    "error": COLORS["error"],
    "warning": COLORS["warning"],
    "info": COLORS["primary"],
    "success": COLORS["success"],
}
_INVERT_DELTA = {"CPIHH", "Cost Per Incremental HH"}


def _fmt_currency(val: float) -> str:
    if val >= 1_000_000:
        return f"${val / 1_000_000:.1f}M"
    return f"${val / 1_000:.0f}K"


def _get_campaign_df(filters):
    raw = get_campaign_performance(filters)
    df = pd.DataFrame(raw)
    if df.empty:
        return df
    df["Spend"] = df["Spend"].apply(_fmt_currency)
    df["Revenue"] = df["Revenue"].apply(_fmt_currency)
    df["Funded"] = df["Funded"].apply(lambda x: f"{x:,}")
    return df


page_chrome(title="Executive Scorecard")

# Clear stale caches on first load so we always hit real data
if "cache_cleared" not in st.session_state:
    st.cache_data.clear()
    st.session_state["cache_cleared"] = True

filters = get_global_filters()

kpis = get_kpi_summary(filters)
financials = get_financial_summary(filters)
alerts = get_recent_alerts(filters, limit=10)

card_container(title="Primary KPIs", subtitle="Contractual targets · 12-week trajectory")
cols_a = st.columns(4)
for i, kpi in enumerate(kpis[:4]):
    with cols_a[i]:
        kpi_card(
            title=kpi["name"],
            value=kpi["value"],
            delta=kpi.get("delta"),
            delta_pct=kpi.get("delta_pct"),
            sparkline_data=kpi.get("sparkline_data"),
            format_type=kpi.get("format_type", "number"),
            alert_status=kpi.get("alert_status"),
            invert_delta=kpi["name"] in _INVERT_DELTA,
        )
cols_b = st.columns(3)
for i, kpi in enumerate(kpis[4:7]):
    with cols_b[i]:
        kpi_card(
            title=kpi["name"],
            value=kpi["value"],
            delta=kpi.get("delta"),
            delta_pct=kpi.get("delta_pct"),
            sparkline_data=kpi.get("sparkline_data"),
            format_type=kpi.get("format_type", "number"),
            alert_status=kpi.get("alert_status"),
            invert_delta=kpi["name"] in _INVERT_DELTA,
        )
card_container_end()

card_container(title="Financial Summary")
metric_strip(
    metrics=[
        {"label": m["label"], "value": m["value"], "delta": m.get("delta"), "format": m.get("format")}
        for m in financials
    ]
)
card_container_end()

card_container(title="Campaign performance", subtitle="Top campaigns by ROAS")
_df_campaigns = _get_campaign_df(filters)
render_campaign_table(_df_campaigns, key="scorecard_campaigns")
card_container_end()

card_container(title="Alert Feed", subtitle="Last 10 threshold breaches")
for alert in alerts:
    sev = alert["severity"]
    color = _SEVERITY_COLORS.get(sev, COLORS["iron"])
    badge = badge_html(text=sev.upper(), severity=sev)
    st.markdown(
        f"""<div style="display:flex;align-items:flex-start;gap:0.75rem;
            border-left:3px solid {color};border-radius:0 4px 4px 0;
            padding:0.6rem 0.9rem;margin-bottom:0.4rem;
            background:rgba(0,0,0,0.02);">
            <div style="flex:1;">
                <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem;">
                    {badge}
                    <span style="font-size:0.8rem;font-weight:600;color:{COLORS['text_primary']};">{alert['kpi']}</span>
                </div>
                <span style="font-size:0.75rem;color:{COLORS['text_secondary']};">{alert['desc']}</span>
            </div>
            <span style="font-size:0.7rem;color:{COLORS['iron']};white-space:nowrap;">{alert['ts']}</span>
        </div>""",
        unsafe_allow_html=True,
    )
card_container_end()

render_chat_drawer(page_key="exec_scorecard")
