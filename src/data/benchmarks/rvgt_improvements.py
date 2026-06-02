"""
RVGT Improvement Benchmarks
----------------------------
Defines the improvement factors RVGT partnerships deliver to prospect
conversion assumptions. Used by run_comparison() to generate Before/After
simulation pairs for the BD before/after toggle.

Public API
----------
RVGT_IMPROVEMENT_FACTORS : dict[str, float]
    Multiplicative factors applied to each assumption key.
ComparisonResult         : NamedTuple with .before and .after dicts
run_comparison(inputs)   : returns ComparisonResult(before, after)
"""

from __future__ import annotations

from typing import NamedTuple

from src.simulator.simulation_engine import run_simulation


# ---------------------------------------------------------------------------
# Multiplicative improvement factors applied to key conversion assumptions.
# Represent median performance improvements observed across RVGT engagements.
# ---------------------------------------------------------------------------
RVGT_IMPROVEMENT_FACTORS: dict[str, float] = {
    "sem_cpc_nonbranded":   0.85,   # 15% CPC reduction via bid strategy
    "social_cpl":           0.80,   # 20% CPL reduction via creative optimization
    "visit_lead_rate":      1.20,   # 20% higher visit→lead conversion
    "mob6_retention_rate":  1.10,   # 10% better 6-month retention
    "pfi_conversion_rate":  1.15,   # 15% higher primary relationship conversion
    "base_ltv_per_hh":      1.08,   # 8% LTV lift through relationship deepening
}


class ComparisonResult(NamedTuple):
    """Container for a Before/After simulation pair."""

    before: dict
    after: dict


def run_comparison(inputs: dict) -> ComparisonResult:
    """
    Run a Before/After simulation pair.

    'before' uses the prospect's inputs as-is.
    'after' applies RVGT_IMPROVEMENT_FACTORS to key assumptions,
    representing the projected performance With RVGT Partnership.

    Parameters
    ----------
    inputs : dict
        Flat inputs dict as returned by build_inputs_from_session().

    Returns
    -------
    ComparisonResult(before=dict, after=dict)
    """
    from src.simulator.simulation_engine import ASSUMPTION_DEFAULTS

    before = run_simulation(inputs)

    improved: dict = {**inputs}
    for key, factor in RVGT_IMPROVEMENT_FACTORS.items():
        base_val = float(improved.get(key, ASSUMPTION_DEFAULTS.get(key, 1.0)))
        improved[key] = base_val * factor

    after = run_simulation(improved)
    return ComparisonResult(before=before, after=after)
