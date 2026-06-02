import streamlit as st
import plotly.graph_objects as go

from src.components.filter_bar import get_global_filters
from src.components.card_container import card_container, card_container_end
from src.components.kpi_card import kpi_card
from src.components.chart_wrapper import branded_chart
from src.config.brand import COLORS
from src.data.ops_queries import get_ops_calendar, get_ops_health, get_competitive_feed, get_ops_capacity
from src.data.submit_directive import get_submitted_directives
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

_STATUS_COLORS = {"scheduled": COLORS["primary"], "launched": COLORS["success"], "completed": COLORS["success"], "paused": COLORS["warning"], "cancelled": COLORS["iron"]}
_HEALTH_COLORS = {"healthy": COLORS["success"], "degraded": COLORS["warning"], "unhealthy": COLORS["error"]}
_IMPACT_COLORS = {"high": COLORS["error"], "medium": COLORS["warning"], "low": COLORS["iron"]}

page_chrome(title="Operations Command")
filters = get_global_filters()

cal_data = get_ops_calendar()
cal_items = cal_data.get("items", []) if isinstance(cal_data, dict) else []
health = get_ops_health()
feed_data = get_competitive_feed()
feed_items = feed_data.get("items", []) if isinstance(feed_data, dict) else []
directives = get_submitted_directives()
cap_data = get_ops_capacity()
items_cap = cap_data.get("items", []) if isinstance(cap_data, dict) else []

_num_scheduled = sum(1 for i in cal_items if i.get("status") == "scheduled")
_num_pending = len(directives)
_num_healthy = sum(1 for c in health.get("components", []) if c.get("status") == "healthy")
_num_total = len(health.get("components", []))

card_container(title="Operations Overview")
ov_cols = st.columns(4)
with ov_cols[0]:
    kpi_card("Launches This Month", _num_scheduled, format_type="number", icon="🚀")
with ov_cols[1]:
    kpi_card("Pending Approvals", _num_pending, format_type="number", icon="📋",
             alert_status="warning" if _num_pending > 0 else None)
with ov_cols[2]:
    kpi_card("Systems Healthy", _num_healthy, format_type="number", icon="✅",
             alert_status="success" if _num_healthy == _num_total else "warning")
with ov_cols[3]:
    kpi_card("Competitive Signals", len(feed_items), format_type="number", icon="📡")
card_container_end()

tab_cal, tab_cap, tab_approvals, tab_health, tab_intel = st.tabs([
    "Launch Calendar", "Team Capacity", "Approval Queue", "System Health", "Competitive Intel"
])

with tab_cal:
    card_container(title="Marketing Launch Calendar")
    hdr = st.columns([1.2, 3, 1.5, 2, 1.5])
    for col, h in zip(hdr, ["Date", "Title", "Channel", "Owner", "Status"]):
        col.markdown(f"<span style='font-size:0.65rem;font-weight:600;text-transform:uppercase;letter-spacing:0.07em;color:{COLORS['text_secondary']};'>{h}</span>", unsafe_allow_html=True)
    st.markdown(f"<hr style='border-color:{COLORS['border']};margin:0.3rem 0;'/>", unsafe_allow_html=True)
    for item in cal_items:
        rc = st.columns([1.2, 3, 1.5, 2, 1.5])
        status = item.get("status", "scheduled")
        sc = _STATUS_COLORS.get(status, COLORS["iron"])
        rc[0].markdown(f"<span style='font-size:0.78rem;color:{COLORS['text_secondary']};'>{item.get('date','')}</span>", unsafe_allow_html=True)
        rc[1].markdown(f"<span style='font-size:0.8rem;color:{COLORS['text_primary']};font-weight:500;'>{item.get('title','')}</span>", unsafe_allow_html=True)
        rc[2].markdown(f"<span style='font-size:0.76rem;color:{COLORS['text_secondary']};'>{item.get('channel','').upper()}</span>", unsafe_allow_html=True)
        rc[3].markdown(f"<span style='font-size:0.74rem;color:{COLORS['text_secondary']};'>{item.get('owner','')}</span>", unsafe_allow_html=True)
        rc[4].markdown(f"<span style='background:{sc}22;color:{sc};font-size:0.63rem;font-weight:700;text-transform:uppercase;padding:0.15rem 0.5rem;border-radius:9999px;'>{status}</span>", unsafe_allow_html=True)
    card_container_end()

with tab_cap:
    card_container(title="Team Resource Utilization")
    if items_cap:
        teams = [i.get("channel") or i.get("team", "") for i in items_cap]
        utilization = [i.get("utilization_pct", 0.70) * 100 for i in items_cap]
        bar_colors = [COLORS["error"] if u > 90 else (COLORS["warning"] if u > 75 else COLORS["success"]) for u in utilization]
        fig = go.Figure(go.Bar(
            x=utilization, y=teams, orientation="h",
            marker_color=bar_colors,
            text=[f"{u:.0f}%" for u in utilization], textposition="outside",
        ))
        fig.update_layout(xaxis_range=[0, 110], xaxis_title="Utilization %", height=300)
        branded_chart(fig, height=300, key="team_utilization")
    else:
        st.info("Capacity data not available.")
    card_container_end()

with tab_approvals:
    card_container(title="Approval Queue")
    if not directives:
        st.markdown(
            f"<div style='text-align:center;padding:2rem;color:{COLORS['text_secondary']};font-size:0.85rem;'>No items pending approval.</div>",
            unsafe_allow_html=True,
        )
    else:
        for d in directives:
            left, right = st.columns([5, 1])
            with left:
                st.markdown(
                    f"""<div style="border-left:3px solid {COLORS['primary']};border-radius:0 6px 6px 0;padding:0.65rem 0.9rem;margin-bottom:0.5rem;">
                    <div style="font-size:0.82rem;font-weight:700;color:{COLORS['text_primary']};margin-bottom:0.1rem;">{d.get('scenario_name','Directive')}</div>
                    <div style="font-size:0.72rem;color:{COLORS['text_secondary']};">{d.get('note','')}</div>
                    </div>""",
                    unsafe_allow_html=True,
                )
            with right:
                if st.button("✓", key=f"approve_{d.get('id','')}", type="primary"):
                    st.success("Approved")
                if st.button("✗", key=f"reject_{d.get('id','')}"):
                    st.warning("Rejected")
    card_container_end()

with tab_health:
    card_container(title="System Health Monitor")
    overall = health.get("overall_status", "healthy")
    overall_color = _HEALTH_COLORS.get(overall, COLORS["iron"])
    st.markdown(
        f"""<div style="background:{overall_color}22;border:0.5px solid {overall_color};border-radius:8px;padding:0.55rem 0.9rem;margin-bottom:1rem;display:flex;align-items:center;gap:0.5rem;">
        <span style="width:8px;height:8px;border-radius:50%;background:{overall_color};display:inline-block;"></span>
        <span style="font-size:0.82rem;font-weight:600;color:{overall_color};">Overall: {overall.title()}</span>
        </div>""",
        unsafe_allow_html=True,
    )
    for comp in health.get("components", []):
        s = comp.get("status", "healthy")
        sc = _HEALTH_COLORS.get(s, COLORS["iron"])
        st.markdown(
            f"""<div style="display:flex;align-items:center;gap:0.75rem;padding:0.45rem 0;border-bottom:0.5px solid {COLORS['border']};">
            <span style="width:7px;height:7px;border-radius:50%;background:{sc};flex-shrink:0;display:inline-block;"></span>
            <span style="font-size:0.82rem;font-weight:500;color:{COLORS['text_primary']};flex:1;">{comp.get('name','')}</span>
            <span style="font-size:0.7rem;color:{sc};font-weight:600;">{s.title()}</span>
            </div>""",
            unsafe_allow_html=True,
        )
    card_container_end()

with tab_intel:
    card_container(title="Competitive Intelligence Feed")
    for item in feed_items[:15]:
        impact = item.get("impact", "medium")
        ic = _IMPACT_COLORS.get(impact, COLORS["iron"])
        st.markdown(
            f"""<div style="border-left:3px solid {ic};border-radius:0 6px 6px 0;padding:0.6rem 0.9rem;margin-bottom:0.4rem;background:rgba(0,0,0,0.01);">
            <div style="display:flex;align-items:center;gap:0.5rem;margin-bottom:0.2rem;">
                <span style="font-size:0.62rem;font-weight:700;text-transform:uppercase;background:{ic}22;color:{ic};padding:0.1rem 0.4rem;border-radius:4px;">{impact}</span>
                <span style="font-size:0.68rem;color:{COLORS['text_secondary']};">{item.get('competitor','')} · {item.get('date','')}</span>
            </div>
            <div style="font-size:0.82rem;color:{COLORS['text_primary']};">{item.get('headline','')}</div>
            </div>""",
            unsafe_allow_html=True,
        )
    card_container_end()

render_chat_drawer(page_key="ops_cmd")
