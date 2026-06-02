"""
Tests for the Full-Funnel Simulator
-------------------------------------
APE-127 — covers run_simulation(), build_inputs_from_session(),
run_comparison(), and preset loading.

All imports from src/simulator/simulation_engine.py (the module
that 9_Simulator.py actually uses).
"""

from __future__ import annotations

import math
import pytest

from src.simulator.simulation_engine import (
    ASSUMPTION_DEFAULTS,
    ASSUMPTION_RANGES,
    run_simulation,
    build_inputs_from_session,
)
from src.data.benchmarks.rvgt_improvements import (
    RVGT_IMPROVEMENT_FACTORS,
    ComparisonResult,
    run_comparison,
)
from src.data.benchmarks.presets import (
    PRESET_NAMES,
    load_preset,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

REQUIRED_OUTPUT_KEYS = {
    "Total Spend",
    "Funded Accounts",
    "Retained HH",
    "PFI HH",
    "Portfolio LTV",
    "CPIHH",
    "Blended CPL",
    "ROI",
    "stage_volumes",
    "stage_rates",
    "channel_contributions",
}

REQUIRED_ASSUMPTION_KEYS = {
    "annual_media_spend",
    "brand_media_pct",
    "sem_cpc_nonbranded",
    "social_cpl",
    "visit_lead_rate",
    "mob6_retention_rate",
    "pfi_conversion_rate",
    "base_ltv_per_hh",
}


def default_inputs() -> dict:
    return dict(ASSUMPTION_DEFAULTS)


# ===========================================================================
# 1. run_simulation — output structure
# ===========================================================================


class TestRunSimulationOutputStructure:
    """run_simulation() returns all required keys with correct types."""

    def test_all_required_keys_present(self):
        result = run_simulation(default_inputs())
        assert REQUIRED_OUTPUT_KEYS.issubset(result.keys())

    def test_total_spend_matches_input(self):
        inputs = default_inputs()
        result = run_simulation(inputs)
        assert result["Total Spend"] == inputs["annual_media_spend"]

    def test_funded_accounts_is_int(self):
        result = run_simulation(default_inputs())
        assert isinstance(result["Funded Accounts"], int)

    def test_retained_hh_is_int(self):
        result = run_simulation(default_inputs())
        assert isinstance(result["Retained HH"], int)

    def test_pfi_hh_is_int(self):
        result = run_simulation(default_inputs())
        assert isinstance(result["PFI HH"], int)

    def test_portfolio_ltv_is_float(self):
        result = run_simulation(default_inputs())
        assert isinstance(result["Portfolio LTV"], float)

    def test_stage_volumes_has_seven_elements(self):
        result = run_simulation(default_inputs())
        assert len(result["stage_volumes"]) == 7

    def test_stage_rates_has_six_elements(self):
        result = run_simulation(default_inputs())
        assert len(result["stage_rates"]) == 6

    def test_channel_contributions_is_dict(self):
        result = run_simulation(default_inputs())
        assert isinstance(result["channel_contributions"], dict)


# ===========================================================================
# 2. run_simulation — happy-path numerics
# ===========================================================================


class TestRunSimulationHappyPath:
    """Sanity-check numeric relationships on default inputs."""

    def test_funded_accounts_positive(self):
        result = run_simulation(default_inputs())
        assert result["Funded Accounts"] > 0

    def test_retained_hh_le_funded_accounts(self):
        result = run_simulation(default_inputs())
        assert result["Retained HH"] <= result["Funded Accounts"]

    def test_pfi_hh_le_retained_hh(self):
        result = run_simulation(default_inputs())
        assert result["PFI HH"] <= result["Retained HH"]

    def test_cpihh_positive_when_retained_hh_gt_zero(self):
        result = run_simulation(default_inputs())
        if result["Retained HH"] > 0:
            assert result["CPIHH"] > 0

    def test_stage_volumes_monotonically_decreasing(self):
        result = run_simulation(default_inputs())
        vols = result["stage_volumes"]
        for i in range(len(vols) - 1):
            assert vols[i] >= vols[i + 1], (
                f"stage_volumes[{i}]={vols[i]} < stage_volumes[{i+1}]={vols[i+1]}"
            )

    def test_stage_rates_all_between_zero_and_one(self):
        result = run_simulation(default_inputs())
        for rate in result["stage_rates"]:
            assert 0.0 <= rate <= 1.0, f"stage rate out of range: {rate}"

    def test_roi_is_finite(self):
        result = run_simulation(default_inputs())
        assert math.isfinite(result["ROI"])

    def test_blended_cpl_positive(self):
        result = run_simulation(default_inputs())
        assert result["Blended CPL"] > 0

    def test_higher_spend_yields_more_funded_accounts(self):
        low = run_simulation({**default_inputs(), "annual_media_spend": 1_000_000})
        high = run_simulation({**default_inputs(), "annual_media_spend": 20_000_000})
        assert high["Funded Accounts"] > low["Funded Accounts"]


# ===========================================================================
# 3. run_simulation — edge cases
# ===========================================================================


class TestRunSimulationEdgeCases:
    """Boundary/degenerate inputs should not raise exceptions."""

    def test_zero_spend_returns_zero_funded(self):
        result = run_simulation({**default_inputs(), "annual_media_spend": 0})
        assert result["Funded Accounts"] == 0

    def test_zero_sem_cpc_handled(self):
        """Division-by-zero guard in sem_clicks calculation."""
        result = run_simulation({**default_inputs(), "sem_cpc_nonbranded": 0})
        assert result["Total Spend"] == ASSUMPTION_DEFAULTS["annual_media_spend"]

    def test_zero_social_cpl_handled(self):
        """Division-by-zero guard in social_leads calculation."""
        result = run_simulation({**default_inputs(), "social_cpl": 0})
        assert REQUIRED_OUTPUT_KEYS.issubset(result.keys())

    def test_unknown_keys_are_ignored(self):
        inputs = {**default_inputs(), "nonexistent_key": 99999}
        result = run_simulation(inputs)
        assert REQUIRED_OUTPUT_KEYS.issubset(result.keys())

    def test_empty_inputs_uses_all_defaults(self):
        result = run_simulation({})
        assert result["Total Spend"] == ASSUMPTION_DEFAULTS["annual_media_spend"]

    def test_cpihh_zero_when_retained_hh_zero(self):
        result = run_simulation({
            **default_inputs(),
            "mob6_retention_rate": 0.0,
        })
        assert result["CPIHH"] == 0.0

    def test_budget_buckets_override_sem_spend(self):
        """Explicit budget_buckets should route through sem channel path."""
        inputs = {
            **default_inputs(),
            "budget_buckets": {
                "performance_sem": 500_000,
                "paid_social": 250_000,
            },
        }
        result = run_simulation(inputs)
        assert REQUIRED_OUTPUT_KEYS.issubset(result.keys())


# ===========================================================================
# 4. build_inputs_from_session
# ===========================================================================


class TestBuildInputsFromSession:
    """build_inputs_from_session() maps st.session_state['simulator'] correctly."""

    def _base_sim(self) -> dict:
        return {
            "institution": {"annual_media_spend": 8_000_000},
            "budget_buckets": {"performance_sem": 2_000_000, "paid_social": 1_200_000},
            "conversion_assumptions": {
                "sem_cpc_nonbranded": 2.75,
                "social_cpl": 40.0,
            },
        }

    def test_returns_required_assumption_keys(self):
        inputs = build_inputs_from_session(self._base_sim())
        assert REQUIRED_ASSUMPTION_KEYS.issubset(inputs.keys())

    def test_annual_media_spend_from_institution(self):
        inputs = build_inputs_from_session(self._base_sim())
        assert inputs["annual_media_spend"] == 8_000_000.0

    def test_assumption_overrides_applied(self):
        inputs = build_inputs_from_session(self._base_sim())
        assert inputs["sem_cpc_nonbranded"] == 2.75
        assert inputs["social_cpl"] == 40.0

    def test_defaults_fill_missing_assumptions(self):
        inputs = build_inputs_from_session(self._base_sim())
        # keys NOT in conversion_assumptions should fall back to ASSUMPTION_DEFAULTS
        assert inputs["visit_lead_rate"] == ASSUMPTION_DEFAULTS["visit_lead_rate"]

    def test_budget_buckets_passed_through(self):
        inputs = build_inputs_from_session(self._base_sim())
        assert inputs["budget_buckets"]["performance_sem"] == 2_000_000

    def test_empty_sim_uses_defaults(self):
        inputs = build_inputs_from_session({})
        assert inputs["annual_media_spend"] == ASSUMPTION_DEFAULTS["annual_media_spend"]

    def test_all_assumption_values_are_float(self):
        inputs = build_inputs_from_session(self._base_sim())
        for k in REQUIRED_ASSUMPTION_KEYS:
            assert isinstance(inputs[k], float), f"{k} is not float"

    def test_result_feeds_run_simulation_without_error(self):
        sim = self._base_sim()
        inputs = build_inputs_from_session(sim)
        result = run_simulation(inputs)
        assert REQUIRED_OUTPUT_KEYS.issubset(result.keys())


# ===========================================================================
# 5. run_comparison
# ===========================================================================


class TestRunComparison:
    """run_comparison() returns a valid ComparisonResult with before/after dicts."""

    def test_returns_comparison_result_namedtuple(self):
        result = run_comparison(default_inputs())
        assert isinstance(result, ComparisonResult)

    def test_before_has_required_keys(self):
        result = run_comparison(default_inputs())
        assert REQUIRED_OUTPUT_KEYS.issubset(result.before.keys())

    def test_after_has_required_keys(self):
        result = run_comparison(default_inputs())
        assert REQUIRED_OUTPUT_KEYS.issubset(result.after.keys())

    def test_after_funded_ge_before_funded(self):
        """RVGT improvements should not reduce funded accounts."""
        result = run_comparison(default_inputs())
        assert result.after["Funded Accounts"] >= result.before["Funded Accounts"]

    def test_after_retained_ge_before_retained(self):
        result = run_comparison(default_inputs())
        assert result.after["Retained HH"] >= result.before["Retained HH"]

    def test_after_ltv_ge_before_ltv(self):
        result = run_comparison(default_inputs())
        assert result.after["Portfolio LTV"] >= result.before["Portfolio LTV"]

    def test_before_spend_equals_after_spend(self):
        """Spend should be the same; RVGT improves efficiency, not budget."""
        result = run_comparison(default_inputs())
        assert result.before["Total Spend"] == result.after["Total Spend"]

    def test_improvement_factors_applied(self):
        """Manually applying all RVGT factors should reproduce the 'after' result."""
        inputs = default_inputs()
        # Apply every factor exactly as run_comparison does
        improved = {**inputs}
        for key, factor in RVGT_IMPROVEMENT_FACTORS.items():
            base_val = float(improved.get(key, ASSUMPTION_DEFAULTS.get(key, 1.0)))
            improved[key] = base_val * factor
        manual_after = run_simulation(improved)
        automated = run_comparison(inputs)
        assert automated.after["Funded Accounts"] == manual_after["Funded Accounts"]


# ===========================================================================
# 6. Preset loading
# ===========================================================================


class TestPresetLoading:
    """All 5 presets load without error and populate required session fields."""

    REQUIRED_SESSION_KEYS = {"institution", "budget_buckets", "conversion_assumptions", "selected_preset"}
    BUDGET_CHANNELS = {"brand_media", "performance_sem", "paid_social", "hv_overlay", "seo_aeo", "conversion"}

    @pytest.mark.parametrize("name", PRESET_NAMES)
    def test_preset_loads_without_error(self, name):
        patch = load_preset(name)
        assert patch is not None

    @pytest.mark.parametrize("name", PRESET_NAMES)
    def test_preset_has_required_session_keys(self, name):
        patch = load_preset(name)
        assert self.REQUIRED_SESSION_KEYS.issubset(patch.keys())

    @pytest.mark.parametrize("name", PRESET_NAMES)
    def test_preset_budget_buckets_are_dollars(self, name):
        patch = load_preset(name)
        for channel, amount in patch["budget_buckets"].items():
            assert isinstance(amount, int), f"{name}/{channel} is not int"
            assert amount >= 0, f"{name}/{channel} amount negative"

    @pytest.mark.parametrize("name", PRESET_NAMES)
    def test_preset_budget_channels_present(self, name):
        patch = load_preset(name)
        assert self.BUDGET_CHANNELS.issubset(patch["budget_buckets"].keys())

    @pytest.mark.parametrize("name", PRESET_NAMES)
    def test_preset_conversion_assumptions_present(self, name):
        patch = load_preset(name)
        assert len(patch["conversion_assumptions"]) > 0

    @pytest.mark.parametrize("name", PRESET_NAMES)
    def test_preset_feeds_simulation_without_error(self, name):
        patch = load_preset(name)
        sim = {
            "institution": patch["institution"],
            "budget_buckets": patch["budget_buckets"],
            "conversion_assumptions": patch["conversion_assumptions"],
        }
        inputs = build_inputs_from_session(sim)
        result = run_simulation(inputs)
        assert REQUIRED_OUTPUT_KEYS.issubset(result.keys())
        assert result["Funded Accounts"] >= 0

    def test_unknown_preset_raises_key_error(self):
        with pytest.raises(KeyError):
            load_preset("Nonexistent Preset")

    def test_preset_selected_preset_field_matches_name(self):
        for name in PRESET_NAMES:
            patch = load_preset(name)
            assert patch["selected_preset"] == name

    def test_five_presets_defined(self):
        assert len(PRESET_NAMES) == 5
