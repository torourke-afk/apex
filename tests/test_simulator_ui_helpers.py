"""Unit tests for src/simulator/ui_helpers.py — APE-122 / APE-24c.

Tests run without Streamlit by patching st.session_state via a lightweight mock.
All assertions focus on the build_scenario_input() contract: correct rate
conversions, proper CPC/CPL blending, and full ScenarioInput field coverage.
"""

from __future__ import annotations

import sys
import types
from typing import Any, Dict

import pytest

from src.simulator.engine import ChannelConfig, ScenarioInput, SimulatorMode, run_simulation
from src.simulator.ui_helpers import (
    SLIDER_DEFAULTS,
    _DEFAULT_CHANNEL_MIX,
    _DIRECT_MAIL_CPL,
    _DISPLAY_CPC,
    _SEM_BRANDED_BUDGET_SHARE,
    _SOCIAL_NATIVE_SHARE,
    build_scenario_input,
    init_simulator_state,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _make_mock_st(sim_state: Dict[str, Any]) -> types.ModuleType:
    """Return a minimal streamlit mock with session_state set to sim_state."""
    mock_st = types.ModuleType("streamlit")
    mock_st.session_state = {"simulator": sim_state}
    return mock_st


def _patch_st(sim_state: Dict[str, Any]) -> Dict[str, Any]:
    """Patch sys.modules['streamlit'] with the given simulator state dict."""
    sys.modules["streamlit"] = _make_mock_st(sim_state)
    return sim_state


def _default_sim_state() -> Dict[str, Any]:
    return {
        "mode": SimulatorMode.BD.value,
        "total_spend": 500_000.0,
        "scenario_name": "Test Scenario",
        "channel_mix": dict(_DEFAULT_CHANNEL_MIX),
        "conversion_assumptions": dict(SLIDER_DEFAULTS),
        "current_result": None,
    }


# ---------------------------------------------------------------------------
# TestSliderDefaults
# ---------------------------------------------------------------------------


class TestSliderDefaults:
    """SLIDER_DEFAULTS must match industry.py midpoints × 100 for funnel rates."""

    def test_funnel_rates_loaded_from_industry_py(self) -> None:
        from src.data.benchmarks.industry import FUNNEL_RATES

        mapping = {
            "visit_to_app_start": FUNNEL_RATES["page_visit_to_app_start"],
            "app_start_to_apply": FUNNEL_RATES["app_start_to_form_complete"],
            "apply_to_approve": FUNNEL_RATES["form_complete_to_kyc_pass"],
            "approve_to_open": FUNNEL_RATES["kyc_pass_to_approval"],
            "open_to_fund": FUNNEL_RATES["approval_to_funded"],
            "funded_to_active_90d": FUNNEL_RATES["funded_to_active_90d"],
        }
        for key, stage in mapping.items():
            expected = round(stage.industry_avg.default * 100, 1)
            assert SLIDER_DEFAULTS[key] == expected, (
                f"{key}: expected {expected}%, got {SLIDER_DEFAULTS[key]}%"
            )

    def test_retention_defaults_match_spec(self) -> None:
        assert SLIDER_DEFAULTS["mob6_rate"] == 77.5
        assert SLIDER_DEFAULTS["mob12_rate"] == 72.5
        assert SLIDER_DEFAULTS["pfi_conversion"] == 50.0

    def test_ltv_defaults_match_spec(self) -> None:
        assert SLIDER_DEFAULTS["ltv_per_hh"] == 3000.0
        assert SLIDER_DEFAULTS["pfi_ltv_multiplier"] == 5.0

    def test_traffic_generation_defaults(self) -> None:
        assert SLIDER_DEFAULTS["brand_lift_pct"] == 20.0
        assert SLIDER_DEFAULTS["organic_share"] == 37.0
        assert SLIDER_DEFAULTS["aeo_share"] == 3.5
        assert SLIDER_DEFAULTS["life_event_cvr_mult"] == 2.5
        assert SLIDER_DEFAULTS["mover_propensity_mult"] == 4.0

    def test_all_rate_defaults_are_valid_step_values(self) -> None:
        """All % defaults should be representable with 0.5% precision (step floors)."""
        rate_keys = [
            "brand_lift_pct",
            "sem_ctr",
            "organic_share",
            "aeo_share",
            "visit_to_app_start",
            "app_start_to_apply",
            "apply_to_approve",
            "approve_to_open",
            "open_to_fund",
            "funded_to_active_90d",
            "mob6_rate",
            "mob12_rate",
            "pfi_conversion",
        ]
        for k in rate_keys:
            v = SLIDER_DEFAULTS[k]
            # Must be representable as a multiple of 0.5 (the finest step used)
            assert v % 0.5 == 0.0, f"{k}={v} is not a valid 0.5-step value"


# ---------------------------------------------------------------------------
# TestBuildScenarioInput — rate conversion
# ---------------------------------------------------------------------------


class TestBuildScenarioInput:
    """build_scenario_input() must correctly convert % → fraction for engine fields."""

    def setup_method(self) -> None:
        _patch_st(_default_sim_state())

    def test_organic_multiplier_divided_by_100(self) -> None:
        inputs = build_scenario_input()
        assert abs(inputs.organic_multiplier - 0.37) < 1e-9

    def test_aeo_rate_divided_by_100(self) -> None:
        inputs = build_scenario_input()
        assert abs(inputs.aeo_rate - 0.035) < 1e-9

    def test_funnel_rates_divided_by_100(self) -> None:
        inputs = build_scenario_input()
        assert abs(inputs.visit_to_app_start - 0.50) < 1e-9
        assert abs(inputs.app_start_to_apply - 0.63) < 1e-9
        assert abs(inputs.apply_to_approve - 0.75) < 1e-9
        assert abs(inputs.approve_to_open - 0.84) < 1e-9
        assert abs(inputs.open_to_fund - 0.72) < 1e-9

    def test_retention_rates_divided_by_100(self) -> None:
        inputs = build_scenario_input()
        assert abs(inputs.mob6_rate - 0.775) < 1e-9
        assert abs(inputs.mob12_rate - 0.725) < 1e-9
        assert abs(inputs.pfi_conversion_rate - 0.50) < 1e-9

    def test_ltv_values_not_divided(self) -> None:
        inputs = build_scenario_input()
        assert inputs.ltv_per_hh == 3000.0
        assert inputs.pfi_ltv_multiplier == 5.0

    def test_total_spend_passthrough(self) -> None:
        _patch_st({**_default_sim_state(), "total_spend": 1_000_000.0})
        inputs = build_scenario_input()
        assert inputs.total_spend == 1_000_000.0

    def test_mode_bd(self) -> None:
        inputs = build_scenario_input()
        assert inputs.mode == SimulatorMode.BD

    def test_mode_client(self) -> None:
        state = _default_sim_state()
        state["mode"] = SimulatorMode.CLIENT.value
        _patch_st(state)
        inputs = build_scenario_input()
        assert inputs.mode == SimulatorMode.CLIENT

    def test_scenario_name_passthrough(self) -> None:
        state = _default_sim_state()
        state["scenario_name"] = "FITB Pitch"
        _patch_st(state)
        inputs = build_scenario_input()
        assert inputs.name == "FITB Pitch"

    def test_brand_lift_pct_applied_to_sem_channel(self) -> None:
        inputs = build_scenario_input()
        # SLIDER_DEFAULTS["brand_lift_pct"] = 20.0 → engine expects 0.20
        assert abs(inputs.channels["sem"].brand_lift_pct - 0.20) < 1e-9

    def test_override_funnel_rate(self) -> None:
        state = _default_sim_state()
        state["conversion_assumptions"]["visit_to_app_start"] = 65.0  # 65%
        _patch_st(state)
        inputs = build_scenario_input()
        assert abs(inputs.visit_to_app_start - 0.65) < 1e-9


# ---------------------------------------------------------------------------
# TestSemCpcBlending
# ---------------------------------------------------------------------------


class TestSemCpcBlending:
    """SEM CPC harmonic-mean blending must preserve traffic-volume math."""

    def setup_method(self) -> None:
        _patch_st(_default_sim_state())

    def test_sem_cpc_is_harmonic_mean(self) -> None:
        inputs = build_scenario_input()
        branded_cpc = SLIDER_DEFAULTS["sem_cpc_branded"]
        non_branded_cpc = SLIDER_DEFAULTS["sem_cpc_non_branded"]
        expected = 1.0 / (
            _SEM_BRANDED_BUDGET_SHARE / branded_cpc
            + (1.0 - _SEM_BRANDED_BUDGET_SHARE) / non_branded_cpc
        )
        assert abs(inputs.channels["sem"].cpc - expected) < 1e-9

    def test_sem_cpc_is_not_arithmetic_mean(self) -> None:
        inputs = build_scenario_input()
        arith_mean = (
            _SEM_BRANDED_BUDGET_SHARE * SLIDER_DEFAULTS["sem_cpc_branded"]
            + (1.0 - _SEM_BRANDED_BUDGET_SHARE) * SLIDER_DEFAULTS["sem_cpc_non_branded"]
        )
        # Harmonic mean < arithmetic mean for positive values
        assert inputs.channels["sem"].cpc < arith_mean

    def test_sem_channel_uses_cpc_model(self) -> None:
        inputs = build_scenario_input()
        assert inputs.channels["sem"].use_cpl is False

    def test_higher_branded_cpc_raises_blended_cpc(self) -> None:
        state = _default_sim_state()
        state["conversion_assumptions"]["sem_cpc_branded"] = 5.00
        _patch_st(state)
        inputs_high = build_scenario_input()

        _patch_st(_default_sim_state())
        inputs_default = build_scenario_input()

        assert inputs_high.channels["sem"].cpc > inputs_default.channels["sem"].cpc


# ---------------------------------------------------------------------------
# TestSocialCplBlending
# ---------------------------------------------------------------------------


class TestSocialCplBlending:
    """Social CPL must be a weighted average of native and landing-page CPLs."""

    def setup_method(self) -> None:
        _patch_st(_default_sim_state())

    def test_social_cpl_weighted_average(self) -> None:
        inputs = build_scenario_input()
        native_cpl = SLIDER_DEFAULTS["social_cpl_native"]
        landing_cpl = SLIDER_DEFAULTS["social_cpl_landing"]
        expected = (
            _SOCIAL_NATIVE_SHARE * native_cpl
            + (1.0 - _SOCIAL_NATIVE_SHARE) * landing_cpl
        )
        assert abs(inputs.channels["social"].cpl - expected) < 1e-9

    def test_social_channel_uses_cpl_model(self) -> None:
        inputs = build_scenario_input()
        assert inputs.channels["social"].use_cpl is True

    def test_social_cpl_bounded_between_native_and_landing(self) -> None:
        inputs = build_scenario_input()
        blended = inputs.channels["social"].cpl
        assert SLIDER_DEFAULTS["social_cpl_native"] <= blended <= SLIDER_DEFAULTS["social_cpl_landing"]


# ---------------------------------------------------------------------------
# TestChannelConfig
# ---------------------------------------------------------------------------


class TestChannelConfig:
    """Channel configs must use fixed benchmarks for display and direct_mail."""

    def setup_method(self) -> None:
        _patch_st(_default_sim_state())

    def test_display_uses_fixed_cpc(self) -> None:
        inputs = build_scenario_input()
        assert inputs.channels["display"].cpc == _DISPLAY_CPC
        assert inputs.channels["display"].use_cpl is False

    def test_direct_mail_uses_fixed_cpl(self) -> None:
        inputs = build_scenario_input()
        assert inputs.channels["direct_mail"].cpl == _DIRECT_MAIL_CPL
        assert inputs.channels["direct_mail"].use_cpl is True

    def test_channel_spend_pcts_sum_to_one(self) -> None:
        inputs = build_scenario_input()
        total = sum(ch.spend_pct for ch in inputs.channels.values())
        assert abs(total - 1.0) < 1e-9

    def test_custom_channel_mix(self) -> None:
        state = _default_sim_state()
        state["channel_mix"] = {"sem": 0.60, "social": 0.20, "display": 0.10, "direct_mail": 0.10}
        _patch_st(state)
        inputs = build_scenario_input()
        assert abs(inputs.channels["sem"].spend_pct - 0.60) < 1e-9


# ---------------------------------------------------------------------------
# TestEngineRoundtrip
# ---------------------------------------------------------------------------


class TestEngineRoundtrip:
    """build_scenario_input() → run_simulation() must produce valid results."""

    def setup_method(self) -> None:
        _patch_st(_default_sim_state())

    def test_simulation_runs_without_error(self) -> None:
        inputs = build_scenario_input()
        result = run_simulation(inputs)
        assert result is not None

    def test_simulation_result_has_positive_traffic(self) -> None:
        inputs = build_scenario_input()
        result = run_simulation(inputs)
        assert result.traffic.total_traffic > 0

    def test_simulation_result_has_positive_funded_accounts(self) -> None:
        inputs = build_scenario_input()
        result = run_simulation(inputs)
        assert result.funnel.funded_accounts > 0

    def test_simulation_result_has_positive_ltv(self) -> None:
        inputs = build_scenario_input()
        result = run_simulation(inputs)
        assert result.ltv.total_ltv > 0

    def test_higher_spend_yields_more_funded_accounts(self) -> None:
        _patch_st({**_default_sim_state(), "total_spend": 1_000_000.0})
        result_high = run_simulation(build_scenario_input())

        _patch_st({**_default_sim_state(), "total_spend": 250_000.0})
        result_low = run_simulation(build_scenario_input())

        assert result_high.funnel.funded_accounts > result_low.funnel.funded_accounts

    def test_better_funnel_yields_lower_cpihh(self) -> None:
        state_good = _default_sim_state()
        state_good["conversion_assumptions"]["visit_to_app_start"] = 80.0  # 80%
        _patch_st(state_good)
        result_good = run_simulation(build_scenario_input())

        state_poor = _default_sim_state()
        state_poor["conversion_assumptions"]["visit_to_app_start"] = 20.0  # 20%
        _patch_st(state_poor)
        result_poor = run_simulation(build_scenario_input())

        assert result_good.efficiency.cpihh < result_poor.efficiency.cpihh

    def test_higher_ltv_per_hh_raises_total_ltv(self) -> None:
        state_high = _default_sim_state()
        state_high["conversion_assumptions"]["ltv_per_hh"] = 9000.0
        _patch_st(state_high)
        result_high = run_simulation(build_scenario_input())

        _patch_st(_default_sim_state())
        result_default = run_simulation(build_scenario_input())

        assert result_high.ltv.total_ltv > result_default.ltv.total_ltv


# ---------------------------------------------------------------------------
# TestInitSimulatorState
# ---------------------------------------------------------------------------


class TestInitSimulatorState:
    """init_simulator_state() must bootstrap without overwriting existing values."""

    def test_creates_simulator_key_if_missing(self) -> None:
        mock_st = types.ModuleType("streamlit")
        mock_st.session_state = {}
        sys.modules["streamlit"] = mock_st

        init_simulator_state()

        assert "simulator" in mock_st.session_state
        sim = mock_st.session_state["simulator"]
        assert "mode" in sim
        assert "total_spend" in sim
        assert "conversion_assumptions" in sim

    def test_does_not_overwrite_existing_mode(self) -> None:
        mock_st = types.ModuleType("streamlit")
        mock_st.session_state = {"simulator": {"mode": SimulatorMode.CLIENT.value}}
        sys.modules["streamlit"] = mock_st

        init_simulator_state()

        assert mock_st.session_state["simulator"]["mode"] == SimulatorMode.CLIENT.value

    def test_does_not_overwrite_existing_assumptions(self) -> None:
        custom_ca = {**SLIDER_DEFAULTS, "mob6_rate": 90.0}
        mock_st = types.ModuleType("streamlit")
        mock_st.session_state = {"simulator": {"conversion_assumptions": custom_ca}}
        sys.modules["streamlit"] = mock_st

        init_simulator_state()

        assert mock_st.session_state["simulator"]["conversion_assumptions"]["mob6_rate"] == 90.0

    def test_conversion_assumptions_defaults_match_slider_defaults(self) -> None:
        mock_st = types.ModuleType("streamlit")
        mock_st.session_state = {}
        sys.modules["streamlit"] = mock_st

        init_simulator_state()

        ca = mock_st.session_state["simulator"]["conversion_assumptions"]
        for key, expected in SLIDER_DEFAULTS.items():
            assert ca[key] == expected, f"{key}: expected {expected}, got {ca[key]}"
