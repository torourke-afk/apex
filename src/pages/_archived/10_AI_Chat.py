"""
AI Chat — Conversational interface for dashboard data
------------------------------------------------------
Chat with the dashboard: ask questions about funnel performance,
spend allocation, simulator results, and benchmarks.
Uses session-state data context to provide informed answers.
"""

import streamlit as st

from src.components.page_chrome import page_chrome
from src.components.card_container import card_container, card_container_end
from src.config.brand import COLORS, GRADIENTS, TYPOGRAPHY, BORDER_RADIUS

page_chrome(title="AI Chat", breadcrumb="Pages / AI Chat")

ff = TYPOGRAPHY["font_family"]

# ── Initialize chat state ──────────────────────────────────────────────────
if "chat_messages" not in st.session_state:
    st.session_state["chat_messages"] = [
        {
            "role": "assistant",
            "content": (
                "Hey! I'm your Apex data assistant. I can help you explore "
                "dashboard metrics, funnel performance, spend allocation, and "
                "simulator results.\n\n"
                "Try asking things like:\n"
                "- *What's the current funnel conversion rate?*\n"
                "- *Summarize my spend allocation*\n"
                "- *What are the simulator defaults?*\n"
                "- *Compare my efficiency scores*"
            ),
        }
    ]


# ── Data context builder ──────────────────────────────────────────────────
def _build_data_context() -> str:
    """Gather relevant dashboard data from session state for chat context."""
    ctx_parts = []

    # Mode
    mode = st.session_state.get("apex_mode", "BD Mode")
    theme = st.session_state.get("apex_theme", "Dark")
    ctx_parts.append(f"Current mode: {mode} | Theme: {theme}")

    # Funnel benchmarks
    from src.data.benchmarks.industry import STAGE_TRANSITION_LABELS, STAGE_RATES
    bench_lines = []
    for i, label in enumerate(STAGE_TRANSITION_LABELS):
        current = st.session_state.get(f"bench_{i}", STAGE_RATES[i])
        bench_lines.append(f"  {label}: {current:.3f} (industry default: {STAGE_RATES[i]:.3f})")
    ctx_parts.append("Funnel Conversion Rates:\n" + "\n".join(bench_lines))

    # Simulator defaults
    from src.simulator.simulation_engine import ASSUMPTION_DEFAULTS
    sim_lines = []
    for k, v in ASSUMPTION_DEFAULTS.items():
        current = st.session_state.get(f"settings_{k}", v)
        label = k.replace("_", " ").title()
        sim_lines.append(f"  {label}: {current}")
    ctx_parts.append("Simulator Assumptions:\n" + "\n".join(sim_lines))

    # Efficiency scores
    eff_labels = {
        "brand_media": "Brand Media",
        "performance_sem": "Performance SEM",
        "paid_social": "Paid Social",
        "seo_aeo": "SEO / AEO",
        "hv_overlay": "HV Overlay",
        "conversion_cro": "Conversion / CRO",
    }
    eff_lines = []
    for k, label in eff_labels.items():
        score = st.session_state.get(f"eff_{k}", 1.0)
        eff_lines.append(f"  {label}: {score:.1f}")
    ctx_parts.append("Channel Efficiency Scores:\n" + "\n".join(eff_lines))

    # Media coefficients
    media_keys = {
        "brand_cpm": ("Brand CPM", "$"),
        "impression_visit_rate": ("Impression → Visit Rate", ""),
        "sem_nonbranded_share": ("SEM Non-Branded Share", "%"),
        "default_sem_pct": ("Default SEM %", "%"),
        "default_social_pct": ("Default Social %", "%"),
    }
    media_lines = []
    for k, (label, unit) in media_keys.items():
        val = st.session_state.get(f"media_{k}")
        if val is not None:
            media_lines.append(f"  {label}: {val}{unit}")
    if media_lines:
        ctx_parts.append("Media Coefficients:\n" + "\n".join(media_lines))

    # Connectors
    connectors = ["Google Ads", "Meta Ads", "Profound", "Google Analytics", "Salesforce", "DuckDB"]
    conn_status = []
    for name in connectors:
        key = f"connector_{name.lower().replace(' ', '_')}"
        status = "Connected" if st.session_state.get(key) else "Not Connected"
        conn_status.append(f"  {name}: {status}")
    ctx_parts.append("Connector Status:\n" + "\n".join(conn_status))

    # Funnel data (if available)
    try:
        from src.data.funnel_queries import get_funnel_data
        funnel = get_funnel_data(None)
        stages = funnel["stages"]
        values = funnel["values"]
        funnel_lines = [f"  {s}: {v:,.0f}" for s, v in zip(stages, values)]
        ctx_parts.append("Current Funnel Volumes:\n" + "\n".join(funnel_lines))
    except Exception:
        pass

    return "\n\n".join(ctx_parts)


# ── Simple response engine ────────────────────────────────────────────────
def _generate_response(user_msg: str) -> str:
    """
    Generate an intelligent response based on dashboard data context.
    Uses keyword matching + data context to provide helpful answers.
    In a production environment, this would call an LLM API.
    """
    msg_lower = user_msg.lower()
    ctx = _build_data_context()

    # Funnel questions
    if any(w in msg_lower for w in ["funnel", "conversion", "rate", "stage", "drop"]):
        from src.data.benchmarks.industry import STAGE_TRANSITION_LABELS, STAGE_RATES
        from src.data.funnel_queries import get_funnel_data

        lines = ["Here's the current funnel state:\n"]

        # Current volumes
        try:
            funnel = get_funnel_data(None)
            stages = funnel["stages"]
            values = funnel["values"]
            rates = funnel["rates"]
            for i, (s, v) in enumerate(zip(stages, values)):
                rate_str = f" → {rates[i]*100:.1f}% conversion" if i < len(rates) else ""
                lines.append(f"**{s}**: {v:,.0f}{rate_str}")
        except Exception:
            pass

        # Benchmark comparison
        lines.append("\n**Benchmark Comparison:**")
        for i, label in enumerate(STAGE_TRANSITION_LABELS):
            current = st.session_state.get(f"bench_{i}", STAGE_RATES[i])
            default = STAGE_RATES[i]
            delta = current - default
            direction = "above" if delta > 0 else "below" if delta < 0 else "at"
            lines.append(f"- {label}: {current:.3f} ({direction} industry benchmark of {default:.3f})")

        return "\n".join(lines)

    # Spend / budget questions
    if any(w in msg_lower for w in ["spend", "budget", "allocation", "cost", "cpm", "cpc", "cpl"]):
        spend = st.session_state.get("settings_annual_media_spend", 5_000_000)
        brand_pct = st.session_state.get("settings_brand_media_pct", 0.40)
        cpm = st.session_state.get("media_brand_cpm", 18.0)
        sem_cpc = st.session_state.get("settings_sem_cpc_nonbranded", 3.50)
        social_cpl = st.session_state.get("settings_social_cpl", 45.0)

        brand_spend = spend * brand_pct
        perf_spend = spend * (1 - brand_pct)

        return (
            f"**Spend Overview:**\n\n"
            f"- **Total Annual Budget**: ${spend:,.0f}\n"
            f"- **Brand Media** ({brand_pct*100:.0f}%): ${brand_spend:,.0f}\n"
            f"- **Performance** ({(1-brand_pct)*100:.0f}%): ${perf_spend:,.0f}\n\n"
            f"**Unit Costs:**\n"
            f"- Brand CPM: ${cpm:.1f}\n"
            f"- SEM CPC (non-branded): ${sem_cpc:.2f}\n"
            f"- Social CPL: ${social_cpl:.0f}\n\n"
            f"At a ${cpm:.1f} CPM, your brand budget buys ~{brand_spend / cpm * 1000:,.0f} impressions."
        )

    # Efficiency questions
    if any(w in msg_lower for w in ["efficiency", "channel", "score", "perform"]):
        eff_data = {
            "Brand Media": st.session_state.get("eff_brand_media", 0.6),
            "Performance SEM": st.session_state.get("eff_performance_sem", 1.8),
            "Paid Social": st.session_state.get("eff_paid_social", 1.1),
            "SEO / AEO": st.session_state.get("eff_seo_aeo", 1.4),
            "HV Overlay": st.session_state.get("eff_hv_overlay", 1.5),
            "Conversion / CRO": st.session_state.get("eff_conversion_cro", 2.0),
        }
        sorted_eff = sorted(eff_data.items(), key=lambda x: x[1], reverse=True)

        lines = ["**Channel Efficiency Scores** (1.0 = baseline):\n"]
        for name, score in sorted_eff:
            bar_len = int(score * 10)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"- **{name}**: {score:.1f}  `{bar}`")

        lines.append(f"\n**Top performer**: {sorted_eff[0][0]} at {sorted_eff[0][1]:.1f}x baseline")
        lines.append(f"**Lowest**: {sorted_eff[-1][0]} at {sorted_eff[-1][1]:.1f}x")

        return "\n".join(lines)

    # Simulator questions
    if any(w in msg_lower for w in ["simulator", "simulation", "default", "assumption", "ltv", "retention"]):
        from src.simulator.simulation_engine import ASSUMPTION_DEFAULTS

        lines = ["**Current Simulator Settings:**\n"]
        display_map = {
            "annual_media_spend": ("Annual Media Spend", "${:,.0f}"),
            "brand_media_pct": ("Brand Media %", "{:.0%}"),
            "sem_cpc_nonbranded": ("SEM CPC Non-Branded", "${:.2f}"),
            "social_cpl": ("Social CPL", "${:.0f}"),
            "visit_lead_rate": ("Visit → Lead Rate", "{:.1%}"),
            "mob6_retention_rate": ("MOB6 Retention", "{:.0%}"),
            "pfi_conversion_rate": ("PFI Conversion", "{:.0%}"),
            "base_ltv_per_hh": ("Base LTV per HH", "${:,.0f}"),
        }
        for k, (label, fmt) in display_map.items():
            current = st.session_state.get(f"settings_{k}", ASSUMPTION_DEFAULTS[k])
            default = ASSUMPTION_DEFAULTS[k]
            changed = " *(modified)*" if current != default else ""
            lines.append(f"- **{label}**: {fmt.format(current)}{changed}")

        return "\n".join(lines)

    # Connectors
    if any(w in msg_lower for w in ["connector", "connect", "integration", "data source"]):
        connectors = [
            ("Google Ads", "google_ads"),
            ("Meta Ads", "meta_ads"),
            ("Profound", "profound"),
            ("Google Analytics", "google_analytics"),
            ("Salesforce", "salesforce"),
            ("DuckDB", "duckdb"),
        ]
        connected = []
        disconnected = []
        for name, key in connectors:
            if st.session_state.get(f"connector_{key}"):
                connected.append(name)
            else:
                disconnected.append(name)

        lines = ["**Connector Status:**\n"]
        if connected:
            lines.append(f"✅ **Connected** ({len(connected)}): " + ", ".join(connected))
        if disconnected:
            lines.append(f"⚪ **Not Connected** ({len(disconnected)}): " + ", ".join(disconnected))
        lines.append(f"\nGo to **Settings → Connectors** to manage integrations.")

        return "\n".join(lines)

    # Mode questions
    if any(w in msg_lower for w in ["mode", "bd ", "client"]):
        mode = st.session_state.get("apex_mode", "BD Mode")
        if mode == "BD Mode":
            return (
                f"You're currently in **BD Mode** 🏢\n\n"
                "This mode uses industry benchmarks and allows full override "
                "of all simulator parameters. Great for prospecting and "
                "competitive analysis.\n\n"
                "Switch to **Client Mode** in Settings → Mode & Appearance "
                "to lock the simulator to client-specific data."
            )
        else:
            return (
                f"You're currently in **Client Mode** 📊\n\n"
                "The simulator is locked to client data and configured benchmarks. "
                "This ensures all projections reflect actual client performance.\n\n"
                "Switch to **BD Mode** in Settings → Mode & Appearance "
                "for full override capability."
            )

    # Summary / overview
    if any(w in msg_lower for w in ["summary", "overview", "status", "dashboard", "tell me"]):
        mode = st.session_state.get("apex_mode", "BD Mode")
        spend = st.session_state.get("settings_annual_media_spend", 5_000_000)
        brand_pct = st.session_state.get("settings_brand_media_pct", 0.40)

        try:
            from src.data.funnel_queries import get_funnel_data
            funnel = get_funnel_data(None)
            funded = funnel["values"][-2] if len(funnel["values"]) > 1 else 0
            active = funnel["values"][-1]
        except Exception:
            funded, active = 0, 0

        return (
            f"**Dashboard Overview:**\n\n"
            f"- **Mode**: {mode}\n"
            f"- **Annual Budget**: ${spend:,.0f} ({brand_pct*100:.0f}% brand / {(1-brand_pct)*100:.0f}% performance)\n"
            f"- **Funded Accounts**: {funded:,.0f}\n"
            f"- **Active (90d)**: {active:,.0f}\n\n"
            "Ask me about specific areas — funnel rates, spend breakdown, "
            "efficiency scores, simulator settings, or connector status."
        )

    # Default fallback
    return (
        "I can help with questions about:\n\n"
        "- **Funnel performance** — conversion rates, volumes, benchmarks\n"
        "- **Spend allocation** — budget breakdown, unit costs, impressions\n"
        "- **Channel efficiency** — score comparisons and rankings\n"
        "- **Simulator settings** — current assumptions and defaults\n"
        "- **Connectors** — integration status\n"
        "- **Dashboard overview** — high-level summary\n\n"
        "Try asking a specific question about any of these topics!"
    )


# ── Chat UI ───────────────────────────────────────────────────────────────

# Quick-action chips
st.markdown(f"""<div style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:1rem;">
    <span style="display:inline-flex;align-items:center;padding:5px 12px;border-radius:9999px;background:{COLORS['glass_bg']};border:1px solid {COLORS['glass_border']};color:{COLORS['text_secondary']};font-size:0.72rem;cursor:pointer;font-family:{ff};">📊 Dashboard overview</span>
    <span style="display:inline-flex;align-items:center;padding:5px 12px;border-radius:9999px;background:{COLORS['glass_bg']};border:1px solid {COLORS['glass_border']};color:{COLORS['text_secondary']};font-size:0.72rem;cursor:pointer;font-family:{ff};">🔻 Funnel performance</span>
    <span style="display:inline-flex;align-items:center;padding:5px 12px;border-radius:9999px;background:{COLORS['glass_bg']};border:1px solid {COLORS['glass_border']};color:{COLORS['text_secondary']};font-size:0.72rem;cursor:pointer;font-family:{ff};">💰 Spend breakdown</span>
    <span style="display:inline-flex;align-items:center;padding:5px 12px;border-radius:9999px;background:{COLORS['glass_bg']};border:1px solid {COLORS['glass_border']};color:{COLORS['text_secondary']};font-size:0.72rem;cursor:pointer;font-family:{ff};">⚡ Efficiency scores</span>
</div>""", unsafe_allow_html=True)

# Quick action buttons (these actually work, unlike the visual chips)
qa1, qa2, qa3, qa4 = st.columns(4)
with qa1:
    if st.button("📊 Overview", key="qa_overview", use_container_width=True):
        st.session_state["chat_messages"].append({"role": "user", "content": "Give me a dashboard overview"})
        st.session_state["chat_messages"].append({"role": "assistant", "content": _generate_response("Give me a dashboard overview")})
        st.rerun()
with qa2:
    if st.button("🔻 Funnel", key="qa_funnel", use_container_width=True):
        st.session_state["chat_messages"].append({"role": "user", "content": "What's the funnel performance?"})
        st.session_state["chat_messages"].append({"role": "assistant", "content": _generate_response("What's the funnel performance?")})
        st.rerun()
with qa3:
    if st.button("💰 Spend", key="qa_spend", use_container_width=True):
        st.session_state["chat_messages"].append({"role": "user", "content": "Summarize spend allocation"})
        st.session_state["chat_messages"].append({"role": "assistant", "content": _generate_response("Summarize spend allocation")})
        st.rerun()
with qa4:
    if st.button("⚡ Efficiency", key="qa_eff", use_container_width=True):
        st.session_state["chat_messages"].append({"role": "user", "content": "Compare channel efficiency scores"})
        st.session_state["chat_messages"].append({"role": "assistant", "content": _generate_response("Compare channel efficiency scores")})
        st.rerun()

_gb = COLORS["glass_border"]
st.markdown(f"<hr style='border-color:{_gb};margin:0.5rem 0 1rem;'/>", unsafe_allow_html=True)

# Render message history
for msg in st.session_state["chat_messages"]:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# Chat input
if prompt := st.chat_input("Ask about your dashboard data..."):
    # Add user message
    st.session_state["chat_messages"].append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Generate and display response
    response = _generate_response(prompt)
    st.session_state["chat_messages"].append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)

# Clear chat button
st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
c1, c2, c3 = st.columns([2, 2, 6])
with c1:
    if st.button("🗑️ Clear Chat", key="clear_chat", use_container_width=True):
        st.session_state["chat_messages"] = [st.session_state["chat_messages"][0]]
        st.rerun()
