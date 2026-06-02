import streamlit as st

from src.components.filter_bar import get_global_filters
from src.components.card_container import card_container, card_container_end
from src.components.kpi_card import kpi_card
from src.config.brand import COLORS
from src.data.product_queries import get_product_pipeline, get_testing_velocity
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

_STAGE_ORDER = ["ideation", "discovery", "development", "testing", "launched"]
_STAGE_LABELS = {"ideation": "Ideation", "discovery": "Discovery", "development": "Development", "testing": "Testing", "launched": "Launched"}
_STAGE_COLORS = {
    "ideation": COLORS["iron"],
    "discovery": COLORS["warning"],
    "development": COLORS["primary"],
    "testing": COLORS["secondary"],
    "launched": COLORS["success"],
}
_PRIORITY_COLORS = {"critical": COLORS["error"], "high": COLORS["warning"], "medium": COLORS["iron"], "low": COLORS["alloy"]}
_STATUS_COLORS = {"in_progress": COLORS["primary"], "planned": COLORS["warning"], "completed": COLORS["success"], "at_risk": COLORS["error"]}

_WAVES = [
    {
        "name": "Wave 1 — Foundation",
        "status": "completed",
        "subtitle": "Stabilize core journeys",
        "deliverables": ["Baseline analytics instrumentation", "Core funnel friction reduction", "Mobile UX audit + fixes", "KYC flow optimization"],
    },
    {
        "name": "Wave 2 — Scale",
        "status": "in_progress",
        "subtitle": "Personalization & funnel integration",
        "deliverables": ["Personalization engine go-live", "A/B test velocity program", "CRM-triggered in-app messaging", "Real-time funnel alerting"],
    },
    {
        "name": "Wave 3 — Transform",
        "status": "planned",
        "subtitle": "AI-first conversational experience",
        "deliverables": ["Conversational onboarding (LLM)", "Real-time offer decisioning", "Predictive abandonment recovery", "Agentic customer service"],
    },
]

page_chrome(title="Product & Experience")
filters = get_global_filters()

pipeline_data = get_product_pipeline()
items = pipeline_data.get("items", [])

card_container(title="Product Pipeline", subtitle="Initiatives by development stage")
stage_cols = st.columns(len(_STAGE_ORDER))
for col, stage_key in zip(stage_cols, _STAGE_ORDER):
    stage_items = [i for i in items if i.get("stage") == stage_key]
    label = _STAGE_LABELS[stage_key]
    color = _STAGE_COLORS[stage_key]
    with col:
        st.markdown(
            f"""<div style="background:{COLORS['surface_sunken']};border-radius:6px;padding:0.4rem 0.6rem;margin-bottom:0.5rem;">
            <span style="font-size:0.62rem;font-weight:700;text-transform:uppercase;letter-spacing:0.06em;color:{color};">{label}</span>
            <span style="font-size:0.62rem;color:{COLORS['iron']};float:right;">{len(stage_items)}</span>
            </div>""",
            unsafe_allow_html=True,
        )
        for item in stage_items:
            prio_color = _PRIORITY_COLORS.get(item.get("priority", "medium"), COLORS["iron"])
            conf = item.get("confidence_score", 0.5)
            conf_pct = int(conf * 100)
            conf_color = COLORS["success"] if conf >= 0.8 else (COLORS["warning"] if conf >= 0.6 else COLORS["error"])
            st.markdown(
                f"""<div style="border:0.5px solid {COLORS['border']};border-left:3px solid {prio_color};border-radius:0 6px 6px 0;padding:0.6rem 0.7rem;margin-bottom:0.4rem;">
                <div style="font-size:0.76rem;font-weight:600;color:{COLORS['text_primary']};margin-bottom:0.15rem;">{item['name']}</div>
                <div style="font-size:0.66rem;color:{COLORS['text_secondary']};margin-bottom:0.3rem;">{item.get('owner','')}</div>
                <div style="font-size:0.65rem;color:{COLORS['iron']};">Due: {item.get('target_date','')[:7]}</div>
                <div style="display:flex;align-items:center;gap:0.35rem;margin-top:0.3rem;">
                    <div style="flex:1;background:{COLORS['border']};border-radius:3px;height:4px;">
                        <div style="background:{conf_color};border-radius:3px;height:4px;width:{conf_pct}%;"></div>
                    </div>
                    <span style="font-size:0.63rem;color:{conf_color};">{conf_pct}%</span>
                </div>
                </div>""",
                unsafe_allow_html=True,
            )
card_container_end()

card_container(title="Digital Experience Transformation Roadmap", subtitle="Three-wave delivery model")
wave_cols = st.columns(3)
for col, wave in zip(wave_cols, _WAVES):
    s = wave["status"]
    sc = _STATUS_COLORS.get(s, COLORS["iron"])
    with col:
        st.markdown(
            f"""<div style="border-top:3px solid {sc};border-radius:0 0 8px 8px;padding:0.9rem 0.75rem;">
            <div style="font-size:0.84rem;font-weight:700;color:{COLORS['text_primary']};margin-bottom:0.15rem;">{wave['name']}</div>
            <div style="font-size:0.7rem;color:{COLORS['text_secondary']};margin-bottom:0.5rem;">{wave['subtitle']}</div>
            <span style="font-size:0.6rem;font-weight:700;text-transform:uppercase;padding:0.15rem 0.5rem;border-radius:9999px;background:{sc}22;color:{sc};">{s.replace('_',' ').title()}</span>
            <ul style="margin:0.65rem 0 0 0;padding-left:1rem;">
                {''.join(f'<li style="font-size:0.73rem;color:{COLORS["text_secondary"]};margin-bottom:0.2rem;">{d}</li>' for d in wave['deliverables'])}
            </ul>
            </div>""",
            unsafe_allow_html=True,
        )
card_container_end()

card_container(title="Testing Velocity Tracker", subtitle="A/B and multivariate test cadence — last 30 days")
tv = get_testing_velocity("30d")
tv_cols = st.columns(4)
tv_metrics = [
    ("Tests Running", tv.get("tests_run", 0), None, "number"),
    ("Win Rate", tv.get("win_rate", 0) * 100, None, "percent"),
    ("Avg Lift", tv.get("avg_lift_pct", 0), None, "percent"),
    ("Tests Won", tv.get("tests_won", 0), None, "number"),
]
for col, (title, val, delta, fmt) in zip(tv_cols, tv_metrics):
    with col:
        kpi_card(title=title, value=val, delta=delta, format_type=fmt)
card_container_end()

render_chat_drawer(page_key="product_exp")
