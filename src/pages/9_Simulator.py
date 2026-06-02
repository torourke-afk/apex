import streamlit as st
import plotly.graph_objects as go
import numpy as np

from src.components.filter_bar import get_global_filters
from src.components.card_container import card_container, card_container_end
from src.components.kpi_card import kpi_card
from src.components.chart_wrapper import branded_chart
from src.components.scenario_compare import scenario_comparison
from src.config.brand import COLORS, GRADIENTS, TYPOGRAPHY, BORDER_RADIUS
from src.simulator.simulation_engine import run_simulation, ASSUMPTION_DEFAULTS, ASSUMPTION_RANGES
from src.components.page_chrome import page_chrome
from src.components.chat_drawer import render_chat_drawer

_FUNNEL_STAGES = ["Impressions", "Clicks", "App Started", "App Submitted", "Approved", "Funded", "Active (90d)"]
_FUNNEL_RATES = [0.048, 0.19, 0.70, 0.82, 0.77, 0.65]
_BENCH_RATES   = [0.055, 0.22, 0.75, 0.84, 0.80, 0.70]
_SS = "sim_"

ff = TYPOGRAPHY["font_family"]

# ---------------------------------------------------------------------------
# Read Settings overrides from session_state (set by Settings page)
# ---------------------------------------------------------------------------
def _get_settings_overrides() -> dict:
    """Collect all Settings-page overrides into a dict suitable for run_simulation()."""
    overrides = {}

    # Media coefficients
    # Keys stored as percentages (0-100) in Settings need scaling back to fractions
    _PCT_KEYS = {"sem_nonbranded_share", "default_sem_pct", "default_social_pct"}
    for k in ("brand_cpm", "impression_visit_rate", "sem_nonbranded_share",
              "default_sem_pct", "default_social_pct"):
        val = st.session_state.get(f"media_{k}")
        if val is not None:
            overrides[k] = val * 0.01 if k in _PCT_KEYS else val

    # Funnel rate overrides (bench_0..bench_5)
    funnel_rates = []
    for i in range(6):
        val = st.session_state.get(f"bench_{i}")
        if val is not None:
            funnel_rates.append(val)
    if len(funnel_rates) == 6:
        overrides["funnel_rates"] = funnel_rates

    # Channel efficiency overrides
    eff = {}
    for ch_key in ("brand_media", "performance_sem", "paid_social",
                   "seo_aeo", "hv_overlay", "conversion_cro"):
        val = st.session_state.get(f"eff_{ch_key}")
        if val is not None:
            eff[ch_key] = val
    if eff:
        overrides["channel_efficiency"] = eff

    return overrides

_settings = _get_settings_overrides()

# ---------------------------------------------------------------------------
# NBD Channel config — reads efficiency + bounds from Settings
# ---------------------------------------------------------------------------
_NBD_CHANNEL_DEFS = [
    {"key": "brand_media",     "label": "Brand Media",     "icon": "📺", "color": COLORS["secondary"],  "default_eff": 0.6,  "default_min": 0.05, "default_max": 0.50},
    {"key": "performance_sem", "label": "Performance SEM", "icon": "🔍", "color": COLORS["accent"],     "default_eff": 1.8,  "default_min": 0.10, "default_max": 0.60},
    {"key": "paid_social",     "label": "Paid Social",     "icon": "📱", "color": "#7B61FF",             "default_eff": 1.1,  "default_min": 0.05, "default_max": 0.40},
    {"key": "seo_aeo",         "label": "SEO / AEO",       "icon": "🌐", "color": COLORS["success"],    "default_eff": 1.4,  "default_min": 0.03, "default_max": 0.20},
    {"key": "hv_overlay",      "label": "HV Overlay",      "icon": "🎯", "color": COLORS["warning"],    "default_eff": 1.5,  "default_min": 0.02, "default_max": 0.25},
    {"key": "conversion_cro",  "label": "Conversion / CRO","icon": "⚡", "color": "#FF6B6B",             "default_eff": 2.0,  "default_min": 0.02, "default_max": 0.15},
]

# Build live NBD_CHANNELS by reading Settings overrides
_NBD_CHANNELS = []
for ch in _NBD_CHANNEL_DEFS:
    _NBD_CHANNELS.append({
        "key":        ch["key"],
        "label":      ch["label"],
        "icon":       ch["icon"],
        "color":      ch["color"],
        "efficiency": st.session_state.get(f"eff_{ch['key']}", ch["default_eff"]),
        "min_pct":    st.session_state.get(f"nbd_min_pct_{ch['key']}", ch["default_min"]),
        "max_pct":    st.session_state.get(f"nbd_max_pct_{ch['key']}", ch["default_max"]),
    })


def _init():
    for k, v in ASSUMPTION_DEFAULTS.items():
        if f"{_SS}{k}" not in st.session_state:
            st.session_state[f"{_SS}{k}"] = v
    if f"{_SS}annual_media_spend_m" not in st.session_state:
        st.session_state[f"{_SS}annual_media_spend_m"] = st.session_state.get(f"{_SS}annual_media_spend", 5_000_000) / 1_000_000
    if "simulator_scenarios" not in st.session_state:
        st.session_state["simulator_scenarios"] = []
    # NBD state
    if "nbd_budget" not in st.session_state:
        st.session_state["nbd_budget"] = 5_000_000
    if "nbd_objective" not in st.session_state:
        st.session_state["nbd_objective"] = "Maximize Funded Accounts"
    # Mode defaults
    if "apex_mode" not in st.session_state:
        st.session_state["apex_mode"] = "BD Mode"

_init()

page_chrome(title="Simulator")
filters = get_global_filters()

# ---------------------------------------------------------------------------
# Mode indicator
# ---------------------------------------------------------------------------
is_bd = st.session_state.get("apex_mode", "BD Mode") == "BD Mode"
mode_color = COLORS["secondary"] if is_bd else COLORS["success"]
mode_label = "BD Mode" if is_bd else "Client Mode"
mode_icon = "🏢" if is_bd else "📊"

st.markdown(f"""
<div style="
    display:inline-flex; align-items:center; gap:8px;
    background: {mode_color}12; border:1px solid {mode_color}40;
    border-radius:{BORDER_RADIUS['full']}; padding:4px 14px 4px 10px;
    margin-bottom:0.75rem;
">
    <span style="font-size:14px;">{mode_icon}</span>
    <span style="color:{mode_color};font-size:0.75rem;font-weight:600;letter-spacing:0.03em;">{mode_label}</span>
</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Tab selector: Full-Funnel Simulator | NBD Optimizer
# ---------------------------------------------------------------------------
sim_tab, nbd_tab = st.tabs(["Full-Funnel Simulator", "NBD Optimizer"])

# ═══════════════════════════════════════════════════════════════════════════
# TAB 1: Full-Funnel Simulator (existing)
# ═══════════════════════════════════════════════════════════════════════════
with sim_tab:
    left, right = st.columns([4, 6])

    with left:
        card_container(title="Inputs", subtitle="BD Mode uses industry benchmarks · Client Mode uses configured data")

        if is_bd:
            with st.expander("Institution Profile", expanded=True):
                st.text_input("Institution Name", value="First Regional Bank", key="sim_institution_name")
                c1, c2 = st.columns(2)
                c1.number_input("Branch Count", min_value=1, value=85, key="sim_branch_count")
                c2.number_input("Current Media Spend ($M)", min_value=0.1, value=5.0, step=0.5, key="sim_current_spend_m")
                st.selectbox("Growth Objective", ["HH Growth", "Deposit Growth", "Lending", "Full Relationship"], key="sim_growth_objective")
                st.selectbox("Competitive Position", ["Market Leader", "Challenger", "New Entrant"], index=1, key="sim_competitive_position")
        else:
            # Client mode — show locked indicator
            st.markdown(f"""
            <div style="
                background:{COLORS['glass_bg']}; border:1px solid {COLORS['glass_border']};
                border-radius:{BORDER_RADIUS['md']}; padding:0.75rem 1rem; margin-bottom:0.75rem;
            ">
                <div style="color:{COLORS['success']};font-size:0.8rem;font-weight:600;margin-bottom:4px;">
                    <i class="fas fa-lock"></i>&nbsp; Client Data Active
                </div>
                <div style="color:{COLORS['text_secondary']};font-size:0.72rem;">
                    Simulator is using configured client benchmarks. Override sliders below to model adjustments.
                </div>
            </div>
            """, unsafe_allow_html=True)

        r = ASSUMPTION_RANGES
        st.slider("Annual Media Spend ($M)", min_value=0.5, max_value=50.0,
                  step=0.5, key=f"{_SS}annual_media_spend_m", format="$%.1fM")
        st.session_state[f"{_SS}annual_media_spend"] = st.session_state[f"{_SS}annual_media_spend_m"] * 1_000_000
        st.slider("Brand Media %", min_value=r["brand_media_pct"]["min"], max_value=r["brand_media_pct"]["max"],
                  step=r["brand_media_pct"]["step"], key=f"{_SS}brand_media_pct")
        st.slider("MOB6 Retention Rate", min_value=r["mob6_retention_rate"]["min"], max_value=r["mob6_retention_rate"]["max"],
                  step=r["mob6_retention_rate"]["step"], key=f"{_SS}mob6_retention_rate")
        st.slider("Base LTV per HH ($)", min_value=r["base_ltv_per_hh"]["min"], max_value=r["base_ltv_per_hh"]["max"],
                  step=r["base_ltv_per_hh"]["step"], key=f"{_SS}base_ltv_per_hh", format="$%.0f")

        with st.expander("Funnel Conversion"):
            st.slider("Visit → Lead Rate", min_value=r["visit_lead_rate"]["min"], max_value=r["visit_lead_rate"]["max"],
                      step=r["visit_lead_rate"]["step"], key=f"{_SS}visit_lead_rate")
            st.slider("PFI Conversion Rate", min_value=r["pfi_conversion_rate"]["min"], max_value=r["pfi_conversion_rate"]["max"],
                      step=r["pfi_conversion_rate"]["step"], key=f"{_SS}pfi_conversion_rate")

        with st.expander("Channel CPCs"):
            st.slider("SEM CPC Non-Branded ($)", min_value=r["sem_cpc_nonbranded"]["min"], max_value=r["sem_cpc_nonbranded"]["max"],
                      step=r["sem_cpc_nonbranded"]["step"], key=f"{_SS}sem_cpc_nonbranded", format="$%.2f")
            st.slider("Social CPL ($)", min_value=r["social_cpl"]["min"], max_value=r["social_cpl"]["max"],
                      step=r["social_cpl"]["step"], key=f"{_SS}social_cpl", format="$%.0f")

        col_save, col_clear = st.columns(2)
        if col_save.button("💾 Save Scenario", use_container_width=True):
            inputs_snap = {k: st.session_state.get(f"{_SS}{k}", v) for k, v in ASSUMPTION_DEFAULTS.items()}
            inputs_snap.update(_settings)
            results_snap = run_simulation(inputs_snap)
            name = st.session_state.get("sim_institution_name", f"Scenario {len(st.session_state['simulator_scenarios'])+1}")[:20]
            entry = {"name": name, **results_snap}
            scenarios = st.session_state["simulator_scenarios"]
            if len(scenarios) >= 3:
                scenarios.pop(0)
            scenarios.append(entry)
            st.success(f'Saved as "{name}"')
        if col_clear.button("🗑 Clear", use_container_width=True):
            st.session_state["simulator_scenarios"] = []

        card_container_end()

    with right:
        inputs = {k: st.session_state.get(f"{_SS}{k}", v) for k, v in ASSUMPTION_DEFAULTS.items()}
        inputs.update(_settings)
        results = run_simulation(inputs)

        card_container(title="Simulation Results")
        r1, r2, r3 = st.columns(3)
        with r1:
            kpi_card("Total Spend", results["Total Spend"], format_type="currency")
        with r2:
            kpi_card("Funded Accounts", results["Funded Accounts"], format_type="number")
        with r3:
            kpi_card("Retained HH (MOB6)", results["Retained HH"], format_type="number")
        r4, r5, r6 = st.columns(3)
        with r4:
            kpi_card("PFI Households", results["PFI HH"], format_type="number")
        with r5:
            kpi_card("Portfolio LTV", results["Portfolio LTV"], format_type="currency")
        with r6:
            kpi_card("CPIHH", results["CPIHH"], format_type="currency", invert_delta=True)
        card_container_end()

        funded = results["Funded Accounts"]
        total_rate = 1.0
        for rate in _FUNNEL_RATES:
            total_rate *= rate
        top_volume = funded / total_rate if total_rate > 0 else 100_000
        funnel_values = [top_volume]
        for rate in _FUNNEL_RATES:
            funnel_values.append(funnel_values[-1] * rate)
        bench_values = [top_volume]
        for rate in _BENCH_RATES:
            bench_values.append(bench_values[-1] * rate)

        card_container(title="Funnel Waterfall", subtitle="Projected volume vs industry benchmark")
        fig_f = go.Figure()
        fig_f.add_trace(go.Bar(name="Benchmark", x=bench_values, y=_FUNNEL_STAGES, orientation="h",
                               marker_color=COLORS["border"], opacity=0.45))
        fig_f.add_trace(go.Bar(name="Projected", x=funnel_values, y=_FUNNEL_STAGES, orientation="h",
                               marker_color=[COLORS["success"] if a >= b else COLORS["error"] for a, b in zip(funnel_values, bench_values)],
                               text=[f"{v:,.0f}" for v in funnel_values], textposition="outside"))
        fig_f.update_layout(barmode="overlay", height=300)
        branded_chart(fig_f, height=300, key="sim_funnel")
        card_container_end()

        scenarios = st.session_state.get("simulator_scenarios", [])
        if len(scenarios) >= 2:
            card_container(title="Scenario Comparison")
            scenario_comparison(
                scenarios=scenarios,
                metrics=["Total Spend", "Funded Accounts", "Retained HH", "PFI HH", "Portfolio LTV", "CPIHH", "ROI"],
                invert_metrics=["CPIHH"],
            )
            card_container_end()

        with st.expander("Sensitivity Analysis"):
            sweep_var = st.selectbox("Sweep variable", list(ASSUMPTION_DEFAULTS.keys()), key="sim_sweep_var")
            rng = ASSUMPTION_RANGES[sweep_var]
            sweep_vals = np.linspace(rng["min"], rng["max"], 10)
            retained_hhs = []
            for val in sweep_vals:
                sweep_inputs = dict(inputs)
                sweep_inputs[sweep_var] = val
                sweep_inputs.update(_settings)
                retained_hhs.append(run_simulation(sweep_inputs)["Retained HH"])
            fig_s = go.Figure(go.Scatter(
                x=list(sweep_vals), y=retained_hhs, mode="lines+markers",
                line=dict(color=COLORS["primary"], width=2), marker=dict(size=6),
            ))
            fig_s.update_layout(xaxis_title=sweep_var.replace("_", " ").title(), yaxis_title="Retained HH", height=260)
            branded_chart(fig_s, height=260, key="sim_sensitivity")


# ═══════════════════════════════════════════════════════════════════════════
# TAB 2: NBD Optimizer
# ═══════════════════════════════════════════════════════════════════════════
with nbd_tab:
    nbd_left, nbd_right = st.columns([4, 6])

    with nbd_left:
        card_container(title="Budget & Objective", subtitle="Define total budget and optimization goal")

        st.number_input(
            "Total Annual Budget ($)",
            min_value=100_000,
            max_value=100_000_000,
            step=100_000,
            key="nbd_budget",
            format="%d",
        )
        budget = st.session_state["nbd_budget"]

        st.selectbox(
            "Optimization Objective",
            ["Maximize Funded Accounts", "Maximize ROI", "Maximize Impression Share", "Minimize CPIHH"],
            key="nbd_objective",
        )
        objective = st.session_state["nbd_objective"]

        st.markdown(f"""
        <div style="
            background:{COLORS['glass_bg']}; border:1px solid {COLORS['glass_border']};
            border-radius:{BORDER_RADIUS['md']}; padding:0.75rem 1rem; margin:0.5rem 0;
        ">
            <div style="color:{COLORS['text_secondary']};font-size:0.72rem;margin-bottom:4px;">
                <i class="fas fa-lightbulb" style="color:{COLORS['warning']};"></i>&nbsp;
                The optimizer uses channel efficiency scores and diminishing-returns curves to suggest
                the allocation that best fits your objective.
            </div>
        </div>
        """, unsafe_allow_html=True)

        card_container_end()

        # ── Channel Constraints (from Settings) ─────────────────────────────
        card_container(title="Channel Constraints", subtitle="Bounds configured in Settings · NBD Bounds tab")

        for ch in _NBD_CHANNELS:
            min_display = f"{ch['min_pct']*100:.0f}%"
            max_display = f"{ch['max_pct']*100:.0f}%"
            st.markdown(f'<div style="display:flex;justify-content:space-between;align-items:center;padding:0.3rem 0;border-bottom:1px solid {COLORS["glass_border"]};"><span style="color:{COLORS["text_primary"]};font-size:0.8rem;font-weight:500;">{ch["icon"]} {ch["label"]}</span><span style="color:{COLORS["text_secondary"]};font-size:0.75rem;">{min_display} – {max_display}</span></div>', unsafe_allow_html=True)

        st.markdown(f'<div style="margin-top:0.5rem;"><a href="/Settings" target="_self" style="color:{COLORS["accent"]};font-size:0.72rem;text-decoration:none;"><i class="fas fa-cog"></i>&nbsp; Edit bounds in Settings</a></div>', unsafe_allow_html=True)

        card_container_end()

    # ── RIGHT: Optimization Results ─────────────────────────────────────────
    with nbd_right:
        # Run the optimizer (diminishing returns model)
        def _optimize_allocation(budget: float, objective: str, channels: list) -> list[dict]:
            """
            Simple optimizer using efficiency-weighted allocation with
            diminishing returns (square-root scaling).

            Returns list of dicts with: key, label, icon, color, pct, dollars, impact_score
            """
            # Weight by efficiency and apply diminishing returns
            total_eff = sum(c["efficiency"] for c in channels)
            raw_pcts = []
            for c in channels:
                # Base allocation proportional to efficiency
                base = c["efficiency"] / total_eff
                # Apply diminishing returns — higher efficiency channels get more
                # but with sqrt dampening to prevent over-concentration
                adj = np.sqrt(c["efficiency"]) / sum(np.sqrt(ch["efficiency"]) for ch in channels)
                # Blend base and adjusted
                pct = 0.3 * base + 0.7 * adj
                # Clamp to constraints (already pulled from Settings via _NBD_CHANNELS)
                min_pct = c["min_pct"]
                max_pct = c["max_pct"]
                pct = max(min_pct, min(max_pct, pct))
                raw_pcts.append(pct)

            # Normalize to sum to 1.0
            total_pct = sum(raw_pcts)
            norm_pcts = [p / total_pct for p in raw_pcts] if total_pct > 0 else [1/len(channels)] * len(channels)

            # Objective-specific adjustments
            if "ROI" in objective:
                # Boost high-efficiency channels
                for i, c in enumerate(channels):
                    if c["efficiency"] >= 1.5:
                        norm_pcts[i] *= 1.15
                total_pct = sum(norm_pcts)
                norm_pcts = [p / total_pct for p in norm_pcts]
            elif "Impression" in objective:
                # Boost brand and social
                for i, c in enumerate(channels):
                    if c["key"] in ("brand_media", "paid_social"):
                        norm_pcts[i] *= 1.3
                total_pct = sum(norm_pcts)
                norm_pcts = [p / total_pct for p in norm_pcts]
            elif "CPIHH" in objective:
                # Boost conversion and SEM
                for i, c in enumerate(channels):
                    if c["key"] in ("conversion_cro", "performance_sem"):
                        norm_pcts[i] *= 1.2
                total_pct = sum(norm_pcts)
                norm_pcts = [p / total_pct for p in norm_pcts]

            results = []
            for i, c in enumerate(channels):
                dollars = budget * norm_pcts[i]
                # Impact score: efficiency × sqrt(dollars) normalized
                impact = c["efficiency"] * np.sqrt(dollars / 1_000_000)
                results.append({
                    **c,
                    "pct": norm_pcts[i],
                    "dollars": dollars,
                    "impact_score": impact,
                })
            return results

        alloc = _optimize_allocation(budget, objective, _NBD_CHANNELS)
        total_impact = sum(a["impact_score"] for a in alloc)

        # ── KPI row ─────────────────────────────────────────────────────────
        card_container(title="Optimal Allocation", subtitle=f"Objective: {objective}")
        k1, k2, k3 = st.columns(3)
        with k1:
            kpi_card("Total Budget", budget, format_type="currency")
        with k2:
            top_channel = max(alloc, key=lambda a: a["pct"])
            # Custom HTML card for string value (kpi_card expects float)
            st.markdown(f"""<div style="
                background:{COLORS['glass_bg']};border:1px solid {COLORS['glass_border']};
                border-radius:{BORDER_RADIUS['xl']};padding:1.25rem 1.5rem 1rem;
                backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);
            "><span style="color:{COLORS['text_secondary']};font-size:0.65rem;font-weight:600;
                text-transform:uppercase;letter-spacing:0.07em;">TOP CHANNEL</span>
            <div style="color:{COLORS['text_primary']};font-size:1.5rem;font-weight:700;
                line-height:1.15;margin-top:0.35rem;">{top_channel['icon']} {top_channel['label']}</div>
            </div>""", unsafe_allow_html=True)
        with k3:
            kpi_card("Channels Active", len([a for a in alloc if a["pct"] > 0.01]), format_type="number")
        card_container_end()

        # ── Allocation bars ─────────────────────────────────────────────────
        card_container(title="Channel Breakdown", subtitle="Recommended $ allocation per channel")

        # Sort by dollars descending
        alloc_sorted = sorted(alloc, key=lambda a: a["dollars"], reverse=True)
        max_dollars = alloc_sorted[0]["dollars"] if alloc_sorted else 1

        for a in alloc_sorted:
            bar_width = (a["dollars"] / max_dollars * 100) if max_dollars > 0 else 0
            pct_display = f"{a['pct']*100:.1f}%"
            dollar_display = f"${a['dollars']:,.0f}"

            st.markdown(f"""
            <div style="margin-bottom:12px;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="color:{COLORS['text_primary']};font-size:0.82rem;font-weight:600;">
                        {a['icon']} {a['label']}
                    </span>
                    <span style="color:{COLORS['text_secondary']};font-size:0.78rem;font-weight:500;">
                        {dollar_display} <span style="color:{a['color']};font-weight:700;">({pct_display})</span>
                    </span>
                </div>
                <div style="
                    background:{COLORS['glass_bg']};
                    border-radius:{BORDER_RADIUS['full']};
                    height:8px;
                    overflow:hidden;
                    border:1px solid {COLORS['glass_border']};
                ">
                    <div style="
                        width:{bar_width}%;
                        height:100%;
                        background:linear-gradient(90deg, {a['color']}CC, {a['color']});
                        border-radius:{BORDER_RADIUS['full']};
                        transition: width 0.3s ease;
                    "></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        card_container_end()

        # ── Donut chart ─────────────────────────────────────────────────────
        card_container(title="Allocation Mix", subtitle="Visual distribution of recommended spend")
        fig_donut = go.Figure(go.Pie(
            labels=[a["label"] for a in alloc_sorted],
            values=[a["dollars"] for a in alloc_sorted],
            hole=0.55,
            marker=dict(colors=[a["color"] for a in alloc_sorted]),
            textinfo="label+percent",
            textfont=dict(size=11, color=COLORS["text_primary"]),
            hovertemplate="<b>%{label}</b><br>$%{value:,.0f}<br>%{percent}<extra></extra>",
        ))
        fig_donut.update_layout(
            height=320,
            showlegend=False,
            annotations=[dict(
                text=f"${budget/1_000_000:.1f}M",
                x=0.5, y=0.5, font_size=18, showarrow=False,
                font=dict(color=COLORS["text_primary"], family=ff, weight=700),
            )],
        )
        branded_chart(fig_donut, height=320, key="nbd_donut")
        card_container_end()

        # ── Impact scores ───────────────────────────────────────────────────
        with st.expander("Channel Impact Scores"):
            st.markdown(f"""
            <div style="color:{COLORS['text_secondary']};font-size:0.72rem;margin-bottom:0.5rem;">
                Impact score = channel efficiency × √(allocated spend in $M). Higher means more expected return per dollar.
            </div>
            """, unsafe_allow_html=True)

            for a in alloc_sorted:
                norm_impact = (a["impact_score"] / total_impact * 100) if total_impact > 0 else 0
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:0.3rem 0;">
                    <span style="width:140px;color:{COLORS['text_primary']};font-size:0.8rem;font-weight:500;">
                        {a['icon']} {a['label']}
                    </span>
                    <div style="flex:1;background:{COLORS['glass_bg']};border-radius:4px;height:6px;overflow:hidden;">
                        <div style="width:{norm_impact}%;height:100%;background:{a['color']};border-radius:4px;"></div>
                    </div>
                    <span style="color:{a['color']};font-size:0.75rem;font-weight:700;width:45px;text-align:right;">
                        {a['impact_score']:.1f}
                    </span>
                </div>
                """, unsafe_allow_html=True)

        # ── Apply to Simulator button ───────────────────────────────────────
        st.markdown("<div style='height:0.5rem;'></div>", unsafe_allow_html=True)
        if st.button("🔄 Apply Allocation to Simulator", use_container_width=True, type="primary"):
            st.session_state[f"{_SS}annual_media_spend"] = budget
            st.session_state[f"{_SS}annual_media_spend_m"] = budget / 1_000_000
            # Set brand media pct from NBD result
            brand_alloc = next((a for a in alloc if a["key"] == "brand_media"), None)
            if brand_alloc:
                st.session_state[f"{_SS}brand_media_pct"] = round(brand_alloc["pct"], 2)
            st.success("Applied NBD allocation to Full-Funnel Simulator inputs")

render_chat_drawer(page_key="simulator")
