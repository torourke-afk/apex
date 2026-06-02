"""UI helper layer for the Full-Funnel Simulator Streamlit page.

Provides:
  - SLIDER_DEFAULTS: canonical defaults for all UI sliders, loaded from industry.py midpoints.
  - init_simulator_state(): idempotent session_state bootstrap.
  - build_scenario_input(): maps st.session_state["simulator"] → ScenarioInput for the engine.

Rate conventions:
  Rates are stored in session_state at percentage scale (0-100), e.g. 20.0 means 20%.
  build_scenario_input() divides by 100 before passing to the engine.
  Dollar values and multipliers are stored at face value.

Data flow:
  UI sliders → session_state["simulator"]["conversion_assumptions"]
  → build_scenario_input() → ScenarioInput → run_simulation() → SimulationResult
"""

from __future__ import annotations

from typing import Any, Dict

from src.data.benchmarks.industry import FUNNEL_RATES
from src.simulator.engine import ChannelConfig, ScenarioInput, SimulatorMode

# ---------------------------------------------------------------------------
# Slider defaults — rates in % (0-100) scale; $ and multipliers at face value
# ---------------------------------------------------------------------------

_FR = FUNNEL_RATES  # shorthand

SLIDER_DEFAULTS: Dict[str, Any] = {
    # --- Traffic Generation ---
    # brand_lift_pct: incremental organic traffic driven by brand ads as % of paid
    "brand_lift_pct": 20.0,          # %, range 5-50, step 1
    "sem_cpc_branded": 1.25,         # $, range 0.10-5.00, step 0.05
    "sem_cpc_non_branded": 3.50,     # $, range 1.00-10.00, step 0.10 (spec ~$3.46, rounded to step)
    "sem_ctr": 8.5,                  # %, range 2-20, step 0.5 (spec ~8.3%, rounded to step)
    "social_cpl_native": 65.0,       # $, range 20-150, step 5
    "social_cpl_landing": 100.0,     # $, range 40-200, step 5
    "organic_share": 37.0,           # %, range 10-60, step 1
    "aeo_share": 3.5,                # %, range 0-15, step 0.5
    "life_event_cvr_mult": 2.5,      # x, range 1.0-5.0, step 0.1
    "mover_propensity_mult": 4.0,    # x, range 1.0-8.0, step 0.5
    # --- Funnel Conversion (6-stage) — industry_avg midpoints from industry.py × 100 ---
    "visit_to_app_start": round(_FR["page_visit_to_app_start"].industry_avg.default * 100, 1),
    "app_start_to_apply": round(_FR["app_start_to_form_complete"].industry_avg.default * 100, 1),
    "apply_to_approve": round(_FR["form_complete_to_kyc_pass"].industry_avg.default * 100, 1),
    "approve_to_open": round(_FR["kyc_pass_to_approval"].industry_avg.default * 100, 1),
    "open_to_fund": round(_FR["approval_to_funded"].industry_avg.default * 100, 1),
    "funded_to_active_90d": round(_FR["funded_to_active_90d"].industry_avg.default * 100, 1),
    # --- Retention & Activation ---
    "mob6_rate": 77.5,               # %, range 50-95, step 0.5
    "mob12_rate": 72.5,              # %, range 50-95, step 0.5
    "pfi_conversion": 50.0,          # %, range 20-80, step 1
    # --- LTV ---
    "ltv_per_hh": 3000.0,            # $, range 1000-10000, step 100
    "pfi_ltv_multiplier": 5.0,       # x, range 2.0-10.0, step 0.5
}

# Default channel spend allocation (must sum to 1.0)
_DEFAULT_CHANNEL_MIX: Dict[str, float] = {
    "sem": 0.40,
    "social": 0.30,
    "display": 0.20,
    "direct_mail": 0.10,
}

# SEM budget split: 30% branded keywords, 70% non-branded
_SEM_BRANDED_BUDGET_SHARE = 0.30

# Social budget split: 40% native placements, 60% landing-page campaigns
_SOCIAL_NATIVE_SHARE = 0.40

# Fixed benchmark CPC/CPL for channels not exposed in the assumptions panel
_DISPLAY_CPC = 1.10       # display CPC from simulator.json benchmarks
_DIRECT_MAIL_CPL = 80.0   # direct_mail CPL from industry.py benchmarks


# ---------------------------------------------------------------------------
# Session state management
# ---------------------------------------------------------------------------


def init_simulator_state() -> None:
    """Idempotently bootstrap st.session_state["simulator"].

    Safe to call on every Streamlit page load — does not overwrite user-modified
    values once the state is established.
    """
    import streamlit as st  # deferred so this module is importable without Streamlit

    if "simulator" not in st.session_state:
        st.session_state["simulator"] = {}

    sim = st.session_state["simulator"]

    if "mode" not in sim:
        sim["mode"] = SimulatorMode.BD.value
    if "total_spend" not in sim:
        sim["total_spend"] = 500_000.0
    if "scenario_name" not in sim:
        sim["scenario_name"] = "Custom Scenario"
    if "channel_mix" not in sim:
        sim["channel_mix"] = dict(_DEFAULT_CHANNEL_MIX)
    if "conversion_assumptions" not in sim:
        sim["conversion_assumptions"] = dict(SLIDER_DEFAULTS)
    if "current_result" not in sim:
        sim["current_result"] = None


# ---------------------------------------------------------------------------
# ScenarioInput assembly
# ---------------------------------------------------------------------------


def build_scenario_input() -> ScenarioInput:
    """Assemble a ScenarioInput from the current simulator session state.

    Key translations applied here:
    - Rate fields (stored as %, 0-100) are divided by 100 before the engine sees them.
    - SEM CPC is blended from branded/non-branded CPCs using a harmonic mean weighted
      by budget share.  This formula preserves the traffic math:
        total_clicks = sem_spend × (branded_share/branded_cpc + non_branded_share/non_branded_cpc)
        blended_cpc  = 1 / (branded_share/branded_cpc + non_branded_share/non_branded_cpc)
    - Social CPL is a budget-share-weighted arithmetic average of native and landing-page CPLs.
    - sem_ctr, life_event_cvr_mult, mover_propensity_mult: stored for display/annotation
      but not consumed by the engine (they affect audience quality, not bulk CVR).
    - funded_to_active_90d: 6th funnel-stage slider stored in session_state for display;
      the engine uses MOB6/MOB12 for retention (separately configurable in the panel).
    """
    import streamlit as st

    sim = st.session_state.get("simulator", {})
    ca: Dict[str, Any] = sim.get("conversion_assumptions", dict(SLIDER_DEFAULTS))
    channel_mix: Dict[str, float] = sim.get("channel_mix", dict(_DEFAULT_CHANNEL_MIX))

    # --- Blend SEM CPC (harmonic mean by budget share) ---
    sem_branded_cpc = float(ca["sem_cpc_branded"])
    sem_non_branded_cpc = float(ca["sem_cpc_non_branded"])
    sem_cpc = 1.0 / (
        _SEM_BRANDED_BUDGET_SHARE / sem_branded_cpc
        + (1.0 - _SEM_BRANDED_BUDGET_SHARE) / sem_non_branded_cpc
    )

    # --- Blend social CPL (weighted average) ---
    social_cpl = (
        _SOCIAL_NATIVE_SHARE * float(ca["social_cpl_native"])
        + (1.0 - _SOCIAL_NATIVE_SHARE) * float(ca["social_cpl_landing"])
    )

    channels: Dict[str, ChannelConfig] = {
        "sem": ChannelConfig(
            spend_pct=channel_mix.get("sem", 0.40),
            cpc=sem_cpc,
            cpl=0.0,
            use_cpl=False,
            brand_lift_pct=float(ca["brand_lift_pct"]) / 100.0,
        ),
        "social": ChannelConfig(
            spend_pct=channel_mix.get("social", 0.30),
            cpc=0.0,
            cpl=social_cpl,
            use_cpl=True,
            brand_lift_pct=0.05,
        ),
        "display": ChannelConfig(
            spend_pct=channel_mix.get("display", 0.20),
            cpc=_DISPLAY_CPC,
            cpl=0.0,
            use_cpl=False,
            brand_lift_pct=0.03,
        ),
        "direct_mail": ChannelConfig(
            spend_pct=channel_mix.get("direct_mail", 0.10),
            cpc=0.0,
            cpl=_DIRECT_MAIL_CPL,
            use_cpl=True,
            brand_lift_pct=0.02,
        ),
    }

    mode_val = sim.get("mode", SimulatorMode.BD.value)
    mode = SimulatorMode(mode_val) if isinstance(mode_val, str) else mode_val

    return ScenarioInput(
        name=sim.get("scenario_name", "Custom Scenario"),
        mode=mode,
        total_spend=float(sim.get("total_spend", 500_000.0)),
        channels=channels,
        organic_multiplier=float(ca["organic_share"]) / 100.0,
        aeo_rate=float(ca["aeo_share"]) / 100.0,
        visit_to_app_start=float(ca["visit_to_app_start"]) / 100.0,
        app_start_to_apply=float(ca["app_start_to_apply"]) / 100.0,
        apply_to_approve=float(ca["apply_to_approve"]) / 100.0,
        approve_to_open=float(ca["approve_to_open"]) / 100.0,
        open_to_fund=float(ca["open_to_fund"]) / 100.0,
        mob6_rate=float(ca["mob6_rate"]) / 100.0,
        mob12_rate=float(ca["mob12_rate"]) / 100.0,
        pfi_conversion_rate=float(ca["pfi_conversion"]) / 100.0,
        ltv_per_hh=float(ca["ltv_per_hh"]),
        pfi_ltv_multiplier=float(ca["pfi_ltv_multiplier"]),
    )
