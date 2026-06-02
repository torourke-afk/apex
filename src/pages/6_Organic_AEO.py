import streamlit as st
import plotly.graph_objects as go

from src.components.card_container import card_container, card_container_end
from src.components.kpi_card import kpi_card
from src.components.chart_wrapper import branded_chart
from src.config.brand import COLORS, CHART_PALETTE
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer
from src.data.organic_aeo import (
    get_llm_visibility_summary,
    get_llm_visibility_trends,
    get_prompt_results,
    PLATFORMS,
    PROMPT_CATEGORIES,
)

_COMPETITOR_SCORES = [
    {"name": "Competitor C", "score": 48.3, "is_client": False},
    {"name": "Competitor B", "score": 54.8, "is_client": False},
    {"name": "Client", "score": 62.4, "is_client": True},
    {"name": "Competitor A", "score": 71.2, "is_client": False},
]

page_chrome(title="AEO")

with st.expander("AEO Filters", expanded=False):
    fc = st.columns(3)
    sel_platforms = fc[0].multiselect("Platforms", PLATFORMS, default=PLATFORMS, key="aeo_platforms")
    sel_category = fc[1].selectbox("Prompt Category", ["All"] + PROMPT_CATEGORIES, key="aeo_category")
    sel_weeks = fc[2].slider("Weeks of history", 4, 24, 12, key="aeo_weeks")

aeo_filters = {
    "platforms": sel_platforms or PLATFORMS,
    "category": sel_category if sel_category != "All" else None,
    "weeks": sel_weeks,
}

summary = get_llm_visibility_summary(aeo_filters)

_METRIC_CONFIG = [
    ("mention_rate",   "Mention Rate",    "percent", "📣", False),
    ("avg_position",   "Avg Position",    "number",  "🥇", True),
    ("sov",            "Share of Voice",  "percent", "📢", False),
    ("sentiment",      "Sentiment Score", "number",  "😊", False),
    ("citation_rate",  "Citation Rate",   "percent", "🔗", False),
]

card_container(title="LLM Visibility Score", subtitle="How often the brand appears in AI-generated answers")
vis_cols = st.columns(len(_METRIC_CONFIG))
for col, (key, label, fmt, icon, invert) in zip(vis_cols, _METRIC_CONFIG):
    if key in summary:
        m = summary[key]
        with col:
            kpi_card(
                title=label,
                value=m.get("value", 0),
                delta=m.get("delta"),
                delta_pct=m.get("delta_pct"),
                sparkline_data=m.get("sparkline"),
                format_type=fmt,
                icon=icon,
                invert_delta=invert,
            )
card_container_end()

trends = get_llm_visibility_trends(aeo_filters)
if "mention_rate" in trends:
    trend_df = trends["mention_rate"]
    card_container(title="Mention Rate by Platform", subtitle=f"Last {sel_weeks} weeks")
    fig = go.Figure()
    palette = list(CHART_PALETTE)
    for i, col in enumerate(trend_df.columns):
        if col != "week":
            fig.add_trace(go.Scatter(
                x=list(range(len(trend_df))),
                y=trend_df[col],
                name=col,
                mode="lines+markers",
                line=dict(color=palette[i % len(palette)], width=2),
                marker=dict(size=5),
            ))
    fig.update_layout(xaxis_title="Week", yaxis_title="Mention Rate (%)", legend_title="Platform", height=300)
    branded_chart(fig, height=300, key="aeo_trends")
    card_container_end()

prompts_df = get_prompt_results(aeo_filters)
if not prompts_df.empty:
    card_container(title="Prompt Results", subtitle="Per-query AI visibility")
    search_term = st.text_input("Filter prompts", placeholder="Search...", key="aeo_search", label_visibility="collapsed")
    if search_term:
        mask = prompts_df.apply(lambda row: row.astype(str).str.contains(search_term, case=False).any(), axis=1)
        prompts_df = prompts_df[mask]
    st.dataframe(prompts_df, use_container_width=True, hide_index=True, height=280)
    card_container_end()

card_container(title="Competitive AEO Benchmarking", subtitle="LLM Visibility Score vs tracked competitors")
fig = go.Figure(go.Bar(
    x=[c["score"] for c in _COMPETITOR_SCORES],
    y=[c["name"] for c in _COMPETITOR_SCORES],
    orientation="h",
    marker_color=[COLORS["primary"] if c["is_client"] else COLORS["border"] for c in _COMPETITOR_SCORES],
    text=[f"{c['score']:.1f}" for c in _COMPETITOR_SCORES],
    textposition="outside",
))
fig.update_layout(xaxis_range=[0, 100], xaxis_title="LLM Visibility Score", height=240)
branded_chart(fig, height=240, key="aeo_competitive")
st.markdown(
    f"""<div style="background:{COLORS['surface_sunken']};border-left:3px solid {COLORS['primary']};border-radius:0 6px 6px 0;padding:0.65rem 0.9rem;margin-top:0.5rem;font-size:0.78rem;color:{COLORS['text_secondary']};">
    <strong style="color:{COLORS['text_primary']};">BD Talking Point:</strong>&nbsp;
    When a consumer asks ChatGPT for the best checking account near them, does your bank appear in the answer?
    Client currently appears in <strong style="color:{COLORS['text_primary']};">62.4%</strong> of relevant queries — above 2 of 3 tracked competitors.
    </div>""",
    unsafe_allow_html=True,
)
card_container_end()

render_chat_drawer(page_key="aeo")
