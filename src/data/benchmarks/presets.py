"""
Simulator Presets
-----------------
Pre-defined scenario configurations for the Full-Funnel Simulator.
Each preset returns a dict that maps onto st.session_state["simulator"].

Public API
----------
load_preset(name: str) -> dict   — returns a merged state patch for the named preset
PRESET_NAMES: list[str]          — ordered list of non-Custom preset names
"""

from __future__ import annotations

from typing import Any

PRESET_NAMES: list[str] = [
    "Regional Growth",
    "Top-20 Optimization",
    "Community Digital Entry",
    "De Novo / Neobank",
    "Acquisition Integration",
]

_PRESETS: dict[str, dict[str, Any]] = {
    "Regional Growth": {
        "institution": {
            "name": "Regional Growth Bank",
            "branch_count": 250,
            "dmas": 12,
            "annual_media_spend": 12_000_000,
            "digital_account_volume": 35_000,
            "retention_rate": 78,
            "growth_objective": "HH Growth",
            "competitive_position": "Challenger",
        },
        "budget_buckets": {
            "brand_media": 0.35,
            "performance_sem": 0.28,
            "paid_social": 0.17,
            "hv_overlay": 0.10,
            "seo_aeo": 0.06,
            "conversion": 0.04,
        },
        "conversion_assumptions": {
            "brand_media_pct": 0.35,
            "sem_cpc_nonbranded": 3.20,
            "social_cpl": 42.0,
            "visit_lead_rate": 0.09,
            "mob6_retention_rate": 0.78,
            "pfi_conversion_rate": 0.36,
            "base_ltv_per_hh": 1_250.0,
        },
    },
    "Top-20 Optimization": {
        "institution": {
            "name": "Top-20 Bank",
            "branch_count": 1_200,
            "dmas": 45,
            "annual_media_spend": 80_000_000,
            "digital_account_volume": 250_000,
            "retention_rate": 83,
            "growth_objective": "Deposit Growth",
            "competitive_position": "Leader",
        },
        "budget_buckets": {
            "brand_media": 0.42,
            "performance_sem": 0.22,
            "paid_social": 0.14,
            "hv_overlay": 0.12,
            "seo_aeo": 0.06,
            "conversion": 0.04,
        },
        "conversion_assumptions": {
            "brand_media_pct": 0.42,
            "sem_cpc_nonbranded": 2.80,
            "social_cpl": 38.0,
            "visit_lead_rate": 0.10,
            "mob6_retention_rate": 0.83,
            "pfi_conversion_rate": 0.42,
            "base_ltv_per_hh": 1_600.0,
        },
    },
    "Community Digital Entry": {
        "institution": {
            "name": "Community Digital Bank",
            "branch_count": 35,
            "dmas": 3,
            "annual_media_spend": 1_500_000,
            "digital_account_volume": 5_000,
            "retention_rate": 70,
            "growth_objective": "HH Growth",
            "competitive_position": "Challenger",
        },
        "budget_buckets": {
            "brand_media": 0.20,
            "performance_sem": 0.30,
            "paid_social": 0.25,
            "hv_overlay": 0.08,
            "seo_aeo": 0.10,
            "conversion": 0.07,
        },
        "conversion_assumptions": {
            "brand_media_pct": 0.20,
            "sem_cpc_nonbranded": 4.20,
            "social_cpl": 52.0,
            "visit_lead_rate": 0.07,
            "mob6_retention_rate": 0.70,
            "pfi_conversion_rate": 0.28,
            "base_ltv_per_hh": 900.0,
        },
    },
    "De Novo / Neobank": {
        "institution": {
            "name": "De Novo Neobank",
            "branch_count": 1,
            "dmas": 1,
            "annual_media_spend": 3_000_000,
            "digital_account_volume": 20_000,
            "retention_rate": 65,
            "growth_objective": "HH Growth",
            "competitive_position": "New Entrant",
        },
        "budget_buckets": {
            "brand_media": 0.15,
            "performance_sem": 0.25,
            "paid_social": 0.35,
            "hv_overlay": 0.05,
            "seo_aeo": 0.12,
            "conversion": 0.08,
        },
        "conversion_assumptions": {
            "brand_media_pct": 0.15,
            "sem_cpc_nonbranded": 2.50,
            "social_cpl": 35.0,
            "visit_lead_rate": 0.12,
            "mob6_retention_rate": 0.65,
            "pfi_conversion_rate": 0.25,
            "base_ltv_per_hh": 750.0,
        },
    },
    "Acquisition Integration": {
        "institution": {
            "name": "Acquisition Integration Bank",
            "branch_count": 600,
            "dmas": 25,
            "annual_media_spend": 30_000_000,
            "digital_account_volume": 90_000,
            "retention_rate": 76,
            "growth_objective": "Full Relationship",
            "competitive_position": "Leader",
        },
        "budget_buckets": {
            "brand_media": 0.45,
            "performance_sem": 0.20,
            "paid_social": 0.12,
            "hv_overlay": 0.15,
            "seo_aeo": 0.05,
            "conversion": 0.03,
        },
        "conversion_assumptions": {
            "brand_media_pct": 0.45,
            "sem_cpc_nonbranded": 3.50,
            "social_cpl": 48.0,
            "visit_lead_rate": 0.08,
            "mob6_retention_rate": 0.76,
            "pfi_conversion_rate": 0.33,
            "base_ltv_per_hh": 1_400.0,
        },
    },
}


def load_preset(name: str) -> dict[str, Any]:
    """
    Return a state patch dict for the named preset.

    The caller should merge this into st.session_state["simulator"]:
        patch = load_preset(name)
        st.session_state["simulator"].update(patch)

    Raises KeyError if `name` is not a known preset.
    """
    if name not in _PRESETS:
        raise KeyError(f"Unknown preset: {name!r}. Valid options: {PRESET_NAMES}")
    preset = _PRESETS[name]
    total_spend = preset["institution"]["annual_media_spend"]
    # Convert fractional allocations to dollar amounts matching the slider widget type
    budget_dollars = {
        k: int(v * total_spend) for k, v in preset["budget_buckets"].items()
    }
    return {
        "institution": {**preset["institution"]},
        "budget_buckets": budget_dollars,
        "conversion_assumptions": {**preset.get("conversion_assumptions", {})},
        "selected_preset": name,
    }
