"""
Full-Funnel Simulation Engine
------------------------------
APE-24c/APE-24d — Core run_simulation() function.

Takes a flat dict of inputs (budget + conversion assumptions) and returns
headline metric results used by the results panel, scenario comparison,
and sensitivity sweep.
"""

from __future__ import annotations

from src.data.benchmarks.industry import STAGE_RATES as _BENCHMARK_RATES


# ---------------------------------------------------------------------------
# Conversion assumption defaults (also used as slider seed values)
# ---------------------------------------------------------------------------

ASSUMPTION_DEFAULTS: dict[str, float] = {
    "annual_media_spend": 5_000_000,
    "brand_media_pct": 0.40,
    "sem_cpc_nonbranded": 3.50,
    "social_cpl": 45.0,
    "visit_lead_rate": 0.08,
    "mob6_retention_rate": 0.75,
    "pfi_conversion_rate": 0.35,
    "base_ltv_per_hh": 1_200.0,
}

# Slider ranges per assumption (used by APE-24c sliders & sensitivity sweep)
ASSUMPTION_RANGES: dict[str, dict] = {
    "annual_media_spend": {"min": 500_000, "max": 50_000_000, "step": 100_000},
    "brand_media_pct":    {"min": 0.10,    "max": 0.70,       "step": 0.01},
    "sem_cpc_nonbranded": {"min": 1.00,    "max": 12.00,      "step": 0.25},
    "social_cpl":         {"min": 15.0,    "max": 150.0,      "step": 5.0},
    "visit_lead_rate":    {"min": 0.02,    "max": 0.25,       "step": 0.005},
    "mob6_retention_rate":{"min": 0.40,    "max": 0.95,       "step": 0.01},
    "pfi_conversion_rate":{"min": 0.10,    "max": 0.70,       "step": 0.01},
    "base_ltv_per_hh":    {"min": 400.0,   "max": 3_000.0,    "step": 50.0},
}


def run_simulation(inputs: dict) -> dict:
    """
    Run the full-funnel simulation with the given inputs.

    Parameters
    ----------
    inputs : dict
        Keys from ASSUMPTION_DEFAULTS (plus optional ``budget_buckets`` and
        ``sub_tactics`` from session state). Unknown keys are ignored.

    Returns
    -------
    dict with headline metrics:
        - "Total Spend"      (float, dollars)
        - "Funded Accounts"  (int)
        - "Retained HH"      (int)
        - "PFI HH"           (int)
        - "Portfolio LTV"    (float, dollars)
        - "CPIHH"            (float, dollars — cost per interested HH)
        - "ROI"              (float, ratio — e.g. 2.4 → 2.4x)
    """
    # --- Pull inputs with defaults -------------------------------------------
    spend              = float(inputs.get("annual_media_spend",  ASSUMPTION_DEFAULTS["annual_media_spend"]))
    brand_pct          = float(inputs.get("brand_media_pct",     ASSUMPTION_DEFAULTS["brand_media_pct"]))
    sem_cpc            = float(inputs.get("sem_cpc_nonbranded",  ASSUMPTION_DEFAULTS["sem_cpc_nonbranded"]))
    social_cpl         = float(inputs.get("social_cpl",          ASSUMPTION_DEFAULTS["social_cpl"]))
    visit_lead_rate    = float(inputs.get("visit_lead_rate",     ASSUMPTION_DEFAULTS["visit_lead_rate"]))
    mob6_retention     = float(inputs.get("mob6_retention_rate", ASSUMPTION_DEFAULTS["mob6_retention_rate"]))
    pfi_conv           = float(inputs.get("pfi_conversion_rate", ASSUMPTION_DEFAULTS["pfi_conversion_rate"]))
    base_ltv           = float(inputs.get("base_ltv_per_hh",     ASSUMPTION_DEFAULTS["base_ltv_per_hh"]))

    # --- Media coefficients (overridable from Settings) -----------------------
    brand_cpm            = float(inputs.get("brand_cpm",             18.0))
    visit_rate           = float(inputs.get("impression_visit_rate", 0.005))
    sem_nonbranded_share = float(inputs.get("sem_nonbranded_share",  0.45))
    default_sem_pct      = float(inputs.get("default_sem_pct",       0.25))
    default_social_pct   = float(inputs.get("default_social_pct",    0.15))

    # Derive SEM / Social spend from budget_buckets if available
    buckets  = inputs.get("budget_buckets", {})
    sem_pct  = buckets.get("performance_sem", spend * default_sem_pct) / spend if spend > 0 else default_sem_pct
    social_spend_raw = buckets.get("paid_social", spend * default_social_pct)

    # --- Brand media → impressions → visits ----------------------------------
    brand_spend  = spend * brand_pct
    impressions  = (brand_spend / brand_cpm) * 1_000
    brand_visits = impressions * visit_rate

    # --- Performance SEM → clicks --------------------------------------------
    sem_spend            = spend * sem_pct
    sem_nonbranded_spend = sem_spend * sem_nonbranded_share
    sem_clicks           = sem_nonbranded_spend / sem_cpc if sem_cpc > 0 else 0

    # --- Total site visits → leads -------------------------------------------
    total_visits  = brand_visits + sem_clicks
    funnel_leads  = total_visits * visit_lead_rate

    # --- Paid Social → leads (direct CPL) ------------------------------------
    social_leads  = social_spend_raw / social_cpl if social_cpl > 0 else 0

    total_leads   = funnel_leads + social_leads

    # --- Leads → funded accounts (benchmark multi-stage pipeline) ------------
    # Funnel rates overridable from Settings via inputs["funnel_rates"]
    _fr = inputs.get("funnel_rates", None)
    _rates = _fr if (_fr and len(_fr) == 6) else _BENCHMARK_RATES
    mid_funnel_rate = (
        _rates[1]
        * _rates[2]
        * _rates[3]
        * _rates[4]
        * _rates[5]
    )
    funded_accounts = int(total_leads * mid_funnel_rate)

    # --- Retained HH (MOB6) --------------------------------------------------
    retained_hh = int(funded_accounts * mob6_retention)

    # --- PFI (Primary Financial Institution) ---------------------------------
    pfi_hh = int(retained_hh * pfi_conv)

    # --- Portfolio LTV -------------------------------------------------------
    portfolio_ltv = retained_hh * base_ltv

    # --- CPIHH ---------------------------------------------------------------
    cpihh = spend / retained_hh if retained_hh > 0 else 0.0

    # --- Blended CPL ---------------------------------------------------------
    blended_cpl = spend / total_leads if total_leads > 0 else 0.0

    # --- ROI (LTV revenue vs media spend) ------------------------------------
    roi = (portfolio_ltv - spend) / spend if spend > 0 else 0.0

    # --- Stage volumes (7 stages for waterfall chart) ------------------------
    # Work through the (possibly overridden) funnel rates from total_leads downward
    mql_stage        = int(total_leads * _rates[1])
    app_start_stage  = int(mql_stage   * _rates[2])
    app_comp_stage   = int(app_start_stage  * _rates[3])
    approved_stage   = int(app_comp_stage   * _rates[4])

    stage_volumes: list[int] = [
        int(total_visits),   # Visits
        int(total_leads),    # Leads
        mql_stage,           # MQL
        app_start_stage,     # App Started
        app_comp_stage,      # App Completed
        approved_stage,      # Approved
        funded_accounts,     # Funded
    ]

    # --- Actual stage-to-stage conversion rates (for color logic) -----------
    stage_rates_actual: list[float] = []
    for i in range(len(stage_volumes) - 1):
        denom = stage_volumes[i]
        stage_rates_actual.append(stage_volumes[i + 1] / denom if denom > 0 else 0.0)

    # --- Channel contributions (visit-weighted with quality multiplier) ------
    # Per-channel efficiency relative to a $1 of spend driving funded accounts
    # Overridable via inputs["channel_efficiency"] dict from Settings
    _eff_overrides = inputs.get("channel_efficiency", {})
    _CHANNEL_EFFICIENCY: dict[str, float] = {
        "brand_media":     float(_eff_overrides.get("brand_media",     1.0)),
        "performance_sem": float(_eff_overrides.get("performance_sem", 1.8)),
        "paid_social":     float(_eff_overrides.get("paid_social",     1.1)),
        "hv_overlay":      float(_eff_overrides.get("hv_overlay",      1.5)),
        "seo_aeo":         float(_eff_overrides.get("seo_aeo",         1.2)),
        "conversion":      float(_eff_overrides.get("conversion_cro",  0.0)),
    }
    _weights = {
        k: buckets.get(k, 0) * eff
        for k, eff in _CHANNEL_EFFICIENCY.items()
    }
    _total_weight = sum(_weights.values())
    channel_contributions: dict[str, int] = {
        k: int(funded_accounts * w / _total_weight) if _total_weight > 0 else 0
        for k, w in _weights.items()
    }
    # Ensure total matches funded_accounts (distribute rounding remainder to top channel)
    _contrib_sum = sum(channel_contributions.values())
    _remainder = funded_accounts - _contrib_sum
    if _remainder != 0 and _total_weight > 0:
        top_channel = max(
            (k for k in channel_contributions if _CHANNEL_EFFICIENCY.get(k, 0) > 0),
            key=lambda k: _weights.get(k, 0),
            default=None,
        )
        if top_channel:
            channel_contributions[top_channel] += _remainder

    return {
        "Total Spend":          spend,
        "Funded Accounts":      funded_accounts,
        "Retained HH":          retained_hh,
        "PFI HH":               pfi_hh,
        "Portfolio LTV":        portfolio_ltv,
        "CPIHH":                cpihh,
        "Blended CPL":          blended_cpl,
        "ROI":                  roi,
        # Extended fields for APE-123 output panels
        "stage_volumes":        stage_volumes,
        "stage_rates":          stage_rates_actual,
        "channel_contributions": channel_contributions,
    }


def build_inputs_from_session(sim: dict) -> dict:
    """
    Build a flat inputs dict from the simulator session_state payload.

    Parameters
    ----------
    sim : dict
        ``st.session_state["simulator"]``

    Returns
    -------
    dict suitable for run_simulation()
    """
    assumptions = sim.get("conversion_assumptions", {})
    institution  = sim.get("institution", {})
    buckets      = sim.get("budget_buckets", {})

    inputs: dict = {**ASSUMPTION_DEFAULTS}
    inputs["annual_media_spend"] = float(
        institution.get("annual_media_spend", ASSUMPTION_DEFAULTS["annual_media_spend"])
    )
    inputs["budget_buckets"] = buckets

    # Overlay any user-set assumptions
    for k in ASSUMPTION_DEFAULTS:
        if k in assumptions:
            inputs[k] = float(assumptions[k])

    return inputs
