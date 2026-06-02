"""
Persistent AI Chat drawer — call render_chat_drawer() at the bottom of each page.
"""

import streamlit as st
from src.config.brand import COLORS


def _chat_respond(user_msg: str) -> str:
    """Generate a response based on dashboard state. Keyword-based stub."""
    msg_lower = user_msg.lower()

    if any(w in msg_lower for w in ["funnel", "conversion", "rate", "stage", "drop"]):
        try:
            from src.data.benchmarks.industry import STAGE_TRANSITION_LABELS, STAGE_RATES
            from src.data.funnel_queries import get_funnel_data
            lines = ["Here's the current funnel state:\n"]
            funnel = get_funnel_data(None)
            for i, (s, v) in enumerate(zip(funnel["stages"], funnel["values"])):
                rate_str = f" → {funnel['rates'][i]*100:.1f}% conversion" if i < len(funnel["rates"]) else ""
                lines.append(f"**{s}**: {v:,.0f}{rate_str}")
            lines.append("\n**Benchmark Comparison:**")
            for i, label in enumerate(STAGE_TRANSITION_LABELS):
                cur = st.session_state.get(f"bench_{i}", STAGE_RATES[i])
                d = "above" if cur > STAGE_RATES[i] else "below" if cur < STAGE_RATES[i] else "at"
                lines.append(f"- {label}: {cur:.3f} ({d} industry benchmark of {STAGE_RATES[i]:.3f})")
            return "\n".join(lines)
        except Exception:
            return "Funnel data is currently loading. Try again in a moment."

    if any(w in msg_lower for w in ["spend", "budget", "allocation", "cost", "cpm", "cpc", "cpl"]):
        spend = st.session_state.get("settings_annual_media_spend", 5_000_000)
        bp = st.session_state.get("settings_brand_media_pct", 0.40)
        cpm = st.session_state.get("media_brand_cpm", 18.0)
        return (
            f"**Spend Overview:**\n\n"
            f"- **Total Annual Budget**: ${spend:,.0f}\n"
            f"- **Brand Media** ({bp*100:.0f}%): ${spend*bp:,.0f}\n"
            f"- **Performance** ({(1-bp)*100:.0f}%): ${spend*(1-bp):,.0f}\n\n"
            f"At ${cpm:.1f} CPM, brand budget buys ~{spend*bp/cpm*1000:,.0f} impressions."
        )

    if any(w in msg_lower for w in ["efficiency", "channel", "score", "perform"]):
        eff = {
            "Brand Media": st.session_state.get("eff_brand_media", 0.6),
            "Performance SEM": st.session_state.get("eff_performance_sem", 1.8),
            "Paid Social": st.session_state.get("eff_paid_social", 1.1),
            "SEO / AEO": st.session_state.get("eff_seo_aeo", 1.4),
            "HV Overlay": st.session_state.get("eff_hv_overlay", 1.5),
            "Conversion / CRO": st.session_state.get("eff_conversion_cro", 2.0),
        }
        ranked = sorted(eff.items(), key=lambda x: x[1], reverse=True)
        lines = ["**Channel Efficiency Scores** (1.0 = baseline):\n"]
        for name, s in ranked:
            lines.append(f"- **{name}**: {s:.1f}  `{'█'*int(s*10)}{'░'*(20-int(s*10))}`")
        lines.append(f"\n**Top**: {ranked[0][0]} at {ranked[0][1]:.1f}x")
        return "\n".join(lines)

    if any(w in msg_lower for w in ["simulator", "simulation", "default", "assumption", "ltv"]):
        try:
            from src.simulator.simulation_engine import ASSUMPTION_DEFAULTS
            dm = {"annual_media_spend": ("Annual Media Spend", "${:,.0f}"),
                  "brand_media_pct": ("Brand %", "{:.0%}"), "sem_cpc_nonbranded": ("SEM CPC", "${:.2f}"),
                  "social_cpl": ("Social CPL", "${:.0f}"), "visit_lead_rate": ("Visit→Lead", "{:.1%}"),
                  "mob6_retention_rate": ("MOB6 Retention", "{:.0%}"), "base_ltv_per_hh": ("LTV/HH", "${:,.0f}")}
            lines = ["**Simulator Settings:**\n"]
            for k, (l, f) in dm.items():
                lines.append(f"- **{l}**: {f.format(st.session_state.get(f'settings_{k}', ASSUMPTION_DEFAULTS.get(k, 0)))}")
            return "\n".join(lines)
        except Exception:
            return "Simulator defaults are loading."

    if any(w in msg_lower for w in ["summary", "overview", "status", "dashboard", "tell me"]):
        mode = st.session_state.get("apex_mode", "BD Mode")
        spend = st.session_state.get("settings_annual_media_spend", 5_000_000)
        bp = st.session_state.get("settings_brand_media_pct", 0.40)
        try:
            from src.data.funnel_queries import get_funnel_data
            fv = get_funnel_data(None)["values"]
            funded, active = (fv[-2], fv[-1]) if len(fv) > 1 else (0, 0)
        except Exception:
            funded, active = 0, 0
        return (
            f"**Dashboard Overview:**\n\n- **Mode**: {mode}\n"
            f"- **Annual Budget**: ${spend:,.0f} ({bp*100:.0f}% brand / {(1-bp)*100:.0f}% performance)\n"
            f"- **Funded**: {funded:,.0f} · **Active (90d)**: {active:,.0f}\n\n"
            "Ask about funnel rates, spend, efficiency, or simulator settings."
        )

    return (
        "I can help with:\n\n"
        "- **Funnel** — conversion rates, volumes\n- **Spend** — budget breakdown\n"
        "- **Efficiency** — channel scores\n- **Simulator** — assumptions\n"
        "- **Overview** — high-level summary"
    )


def render_chat_drawer(page_key: str = "default"):
    """Render the persistent AI chat drawer at the bottom of a page.

    Args:
        page_key: Unique key prefix to avoid widget ID collisions across pages.
    """
    if "chat_messages" not in st.session_state:
        st.session_state["chat_messages"] = []

    _gb = COLORS["glass_border"]
    _tp = COLORS["text_primary"]
    _ts = COLORS["text_secondary"]
    st.markdown(
        f"<hr style='border-color:{_gb};margin:2rem 0 0.5rem;'/>"
        f"<div style='font-size:0.75rem;font-weight:600;text-transform:uppercase;"
        f"letter-spacing:0.07em;color:{_ts};margin-bottom:0.5rem;'>"
        f"💬 Apex AI Assistant</div>",
        unsafe_allow_html=True,
    )

    qa1, qa2, qa3, qa4, qa_clear = st.columns([1, 1, 1, 1, 0.6])
    with qa1:
        if st.button("📊 Overview", key=f"chat_qa_overview_{page_key}", use_container_width=True):
            st.session_state["chat_messages"].append({"role": "user", "content": "Give me a dashboard overview"})
            st.session_state["chat_messages"].append({"role": "assistant", "content": _chat_respond("Give me a dashboard overview")})
            st.rerun()
    with qa2:
        if st.button("🔻 Funnel", key=f"chat_qa_funnel_{page_key}", use_container_width=True):
            st.session_state["chat_messages"].append({"role": "user", "content": "What's the funnel performance?"})
            st.session_state["chat_messages"].append({"role": "assistant", "content": _chat_respond("What's the funnel performance?")})
            st.rerun()
    with qa3:
        if st.button("💰 Spend", key=f"chat_qa_spend_{page_key}", use_container_width=True):
            st.session_state["chat_messages"].append({"role": "user", "content": "Summarize spend allocation"})
            st.session_state["chat_messages"].append({"role": "assistant", "content": _chat_respond("Summarize spend allocation")})
            st.rerun()
    with qa4:
        if st.button("⚡ Efficiency", key=f"chat_qa_eff_{page_key}", use_container_width=True):
            st.session_state["chat_messages"].append({"role": "user", "content": "Compare channel efficiency scores"})
            st.session_state["chat_messages"].append({"role": "assistant", "content": _chat_respond("Compare channel efficiency scores")})
            st.rerun()
    with qa_clear:
        if st.button("🗑️ Clear", key=f"chat_clear_{page_key}", use_container_width=True):
            st.session_state["chat_messages"] = []
            st.rerun()

    for msg in st.session_state["chat_messages"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if prompt := st.chat_input("Ask about your dashboard data...", key=f"chat_input_{page_key}"):
        st.session_state["chat_messages"].append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        response = _chat_respond(prompt)
        st.session_state["chat_messages"].append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)
