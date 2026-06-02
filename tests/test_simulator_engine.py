"""Unit tests for src/simulator/engine.py — 5-stage waterfall simulator.

Coverage:
- All 5 presets load and produce plausible numeric outputs
- run_simulation: stage outputs are internally consistent
- Sensitivity: single-input change → proportional output change
- Before/After: apply_rvgt_improvements + run_comparison produce positive deltas
- Edge cases: zero traffic, extreme spend
- Runs in < 1 second (no I/O during simulation — benchmarks loaded once)
"""

import math
import time

import pytest

from src.simulator.engine import (
    ChannelConfig,
    ScenarioInput,
    SimulatorMode,
    WaterfallEngine,
    apply_rvgt_improvements,
    load_preset,
    run_comparison,
    run_simulation,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reference_preset() -> ScenarioInput:
    return load_preset("regional_growth")


def _simple_scenario(spend: float = 100_000.0) -> ScenarioInput:
    """Minimal two-channel scenario for deterministic arithmetic checks."""
    return ScenarioInput(
        name="test_simple",
        mode=SimulatorMode.BD,
        total_spend=spend,
        channels={
            "sem": ChannelConfig(spend_pct=0.60, cpc=6.0, cpl=0.0, use_cpl=False, brand_lift_pct=0.05),
            "social": ChannelConfig(spend_pct=0.40, cpc=0.0, cpl=20.0, use_cpl=True, brand_lift_pct=0.03),
        },
        organic_multiplier=0.10,
        aeo_rate=0.02,
        visit_to_app_start=0.06,
        app_start_to_apply=0.70,
        apply_to_approve=0.50,
        approve_to_open=0.90,
        open_to_fund=0.75,
        mob6_rate=0.80,
        mob12_rate=0.65,
        pfi_conversion_rate=0.25,
        ltv_per_hh=900.0,
        pfi_ltv_multiplier=3.0,
    )


# ---------------------------------------------------------------------------
# Preset tests
# ---------------------------------------------------------------------------


_PRESET_NAMES = [
    "regional_growth",
    "top_20",
    "community",
    "de_novo",
    "acquisition_integration",
]


class TestPresets:
    @pytest.mark.parametrize("name", _PRESET_NAMES)
    def test_preset_loads(self, name):
        preset = load_preset(name)
        assert preset.name == name
        assert preset.total_spend > 0

    @pytest.mark.parametrize("name", _PRESET_NAMES)
    def test_preset_produces_positive_outputs(self, name):
        result = run_simulation(load_preset(name))
        assert result.funnel.funded_accounts > 0
        assert result.ltv.total_ltv > 0
        assert result.efficiency.cpihh > 0

    @pytest.mark.parametrize("name", _PRESET_NAMES)
    def test_preset_channel_spend_pcts_sum_to_one(self, name):
        preset = load_preset(name)
        total = sum(ch.spend_pct for ch in preset.channels.values())
        assert math.isclose(total, 1.0, abs_tol=1e-9)

    def test_unknown_preset_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            load_preset("nonexistent")

    def test_top20_more_funded_than_community(self):
        top20 = run_simulation(load_preset("top_20"))
        comm = run_simulation(load_preset("community"))
        # top_20 spends 62× more — should produce far more funded accounts
        assert top20.funnel.funded_accounts > comm.funnel.funded_accounts

    def test_de_novo_more_funded_than_community(self):
        deno = run_simulation(load_preset("de_novo"))
        comm = run_simulation(load_preset("community"))
        # de_novo spends ~7× more than community
        assert deno.funnel.funded_accounts > comm.funnel.funded_accounts


# ---------------------------------------------------------------------------
# Stage arithmetic correctness
# ---------------------------------------------------------------------------


class TestStageArithmetic:
    def test_stage1_sem_cpc_model(self):
        s = _simple_scenario(100_000.0)
        result = run_simulation(s)
        # SEM: 60k spend / $6 CPC = 10,000 clicks
        assert math.isclose(result.traffic.paid_traffic_by_channel["sem"], 10_000.0, rel_tol=1e-9)

    def test_stage1_social_cpl_model(self):
        s = _simple_scenario(100_000.0)
        result = run_simulation(s)
        # Social: 40k spend / $20 CPL = 2,000 leads
        assert math.isclose(result.traffic.paid_traffic_by_channel["social"], 2_000.0, rel_tol=1e-9)

    def test_stage1_total_paid_traffic(self):
        s = _simple_scenario(100_000.0)
        result = run_simulation(s)
        assert math.isclose(result.traffic.total_paid_traffic, 12_000.0, rel_tol=1e-9)

    def test_stage1_brand_lift(self):
        s = _simple_scenario(100_000.0)
        result = run_simulation(s)
        # brand_lift = 10_000 * 0.05 + 2_000 * 0.03 = 500 + 60 = 560
        assert math.isclose(result.traffic.brand_lift_traffic, 560.0, rel_tol=1e-9)

    def test_stage1_organic_traffic(self):
        s = _simple_scenario(100_000.0)
        result = run_simulation(s)
        # organic = 12_000 * 0.10 = 1_200
        assert math.isclose(result.traffic.organic_traffic, 1_200.0, rel_tol=1e-9)

    def test_stage1_aeo_traffic(self):
        s = _simple_scenario(100_000.0)
        result = run_simulation(s)
        # aeo = 12_000 * 0.02 = 240
        assert math.isclose(result.traffic.aeo_traffic, 240.0, rel_tol=1e-9)

    def test_stage1_total_traffic_sum(self):
        s = _simple_scenario(100_000.0)
        result = run_simulation(s)
        expected = (
            result.traffic.total_paid_traffic
            + result.traffic.organic_traffic
            + result.traffic.brand_lift_traffic
            + result.traffic.aeo_traffic
        )
        assert math.isclose(result.traffic.total_traffic, expected, rel_tol=1e-9)

    def test_stage2_waterfall_chain(self):
        s = _simple_scenario(100_000.0)
        r = run_simulation(s)
        f = r.funnel
        assert math.isclose(f.app_starts, f.visits * s.visit_to_app_start, rel_tol=1e-9)
        assert math.isclose(f.applications, f.app_starts * s.app_start_to_apply, rel_tol=1e-9)
        assert math.isclose(f.approvals, f.applications * s.apply_to_approve, rel_tol=1e-9)
        assert math.isclose(f.account_opens, f.approvals * s.approve_to_open, rel_tol=1e-9)
        assert math.isclose(f.funded_accounts, f.account_opens * s.open_to_fund, rel_tol=1e-9)

    def test_stage2_drop_offs_are_non_negative(self):
        r = run_simulation(_simple_scenario())
        f = r.funnel
        assert f.drop_visit_to_app_start >= 0
        assert f.drop_app_start_to_apply >= 0
        assert f.drop_apply_to_approve >= 0
        assert f.drop_approve_to_open >= 0
        assert f.drop_open_to_fund >= 0

    def test_stage2_drop_offs_sum_to_funnel_loss(self):
        r = run_simulation(_simple_scenario())
        f = r.funnel
        assert math.isclose(f.drop_visit_to_app_start, f.visits - f.app_starts, rel_tol=1e-9)
        assert math.isclose(f.drop_open_to_fund, f.account_opens - f.funded_accounts, rel_tol=1e-9)

    def test_stage3_mob6_gt_mob12(self):
        r = run_simulation(_simple_scenario())
        # MOB6 rate > MOB12 rate in all presets → MOB6 retained > MOB12 retained
        assert r.retention.mob6_retained > r.retention.mob12_retained

    def test_stage3_pfi_le_mob12(self):
        r = run_simulation(_simple_scenario())
        assert r.retention.pfi_converted <= r.retention.mob12_retained + 1e-6

    def test_stage4_ltv_components(self):
        s = _simple_scenario()
        r = run_simulation(s)
        ret = r.retention
        non_pfi = ret.mob12_retained - ret.pfi_converted
        expected_base = non_pfi * s.ltv_per_hh
        expected_pfi = ret.pfi_converted * s.ltv_per_hh * s.pfi_ltv_multiplier
        assert math.isclose(r.ltv.base_ltv, expected_base, rel_tol=1e-9)
        assert math.isclose(r.ltv.pfi_ltv, expected_pfi, rel_tol=1e-9)
        assert math.isclose(r.ltv.total_ltv, expected_base + expected_pfi, rel_tol=1e-9)

    def test_stage5_cpihh(self):
        s = _simple_scenario()
        r = run_simulation(s)
        expected = s.total_spend / r.funnel.funded_accounts
        assert math.isclose(r.efficiency.cpihh, expected, rel_tol=1e-9)

    def test_stage5_blended_cpl(self):
        s = _simple_scenario()
        r = run_simulation(s)
        expected = s.total_spend / r.funnel.applications
        assert math.isclose(r.efficiency.blended_cpl, expected, rel_tol=1e-9)

    def test_stage5_roi_formula(self):
        s = _simple_scenario()
        r = run_simulation(s)
        expected_roi = (r.ltv.total_ltv - s.total_spend) / s.total_spend
        assert math.isclose(r.efficiency.roi, expected_roi, rel_tol=1e-9)

    def test_stage5_revenue_per_dollar(self):
        s = _simple_scenario()
        r = run_simulation(s)
        expected = r.ltv.total_ltv / s.total_spend
        assert math.isclose(r.efficiency.revenue_per_dollar, expected, rel_tol=1e-9)

    def test_stage5_payback_months_positive(self):
        r = run_simulation(_simple_scenario())
        assert r.efficiency.payback_months > 0


# ---------------------------------------------------------------------------
# Sensitivity tests — proportional output change
# ---------------------------------------------------------------------------


class TestSensitivity:
    def test_double_spend_doubles_traffic(self):
        r1 = run_simulation(_simple_scenario(100_000.0))
        r2 = run_simulation(_simple_scenario(200_000.0))
        # Traffic scales linearly with spend (CPC/CPL models are linear)
        assert math.isclose(r2.traffic.total_traffic, r1.traffic.total_traffic * 2, rel_tol=1e-6)

    def test_double_spend_doubles_funded_accounts(self):
        r1 = run_simulation(_simple_scenario(100_000.0))
        r2 = run_simulation(_simple_scenario(200_000.0))
        assert math.isclose(r2.funnel.funded_accounts, r1.funnel.funded_accounts * 2, rel_tol=1e-6)

    def test_higher_visit_to_app_start_increases_funnel(self):
        s1 = _simple_scenario()
        s2 = _simple_scenario()
        s2.visit_to_app_start = s1.visit_to_app_start * 1.25
        r1 = run_simulation(s1)
        r2 = run_simulation(s2)
        assert r2.funnel.funded_accounts > r1.funnel.funded_accounts
        # Proportional: 25% lift in visit_to_app_start → 25% more funded
        assert math.isclose(
            r2.funnel.funded_accounts / r1.funnel.funded_accounts, 1.25, rel_tol=1e-6
        )

    def test_higher_mob12_rate_increases_ltv(self):
        s1 = _simple_scenario()
        s2 = _simple_scenario()
        s2.mob12_rate = s1.mob12_rate * 1.10  # 10% lift
        r1 = run_simulation(s1)
        r2 = run_simulation(s2)
        assert r2.ltv.total_ltv > r1.ltv.total_ltv

    def test_lower_cpc_increases_traffic(self):
        s1 = _simple_scenario()
        s2 = _simple_scenario()
        # Halve SEM CPC → double SEM traffic
        s2.channels["sem"] = ChannelConfig(
            spend_pct=0.60, cpc=3.0, cpl=0.0, use_cpl=False, brand_lift_pct=0.05
        )
        r1 = run_simulation(s1)
        r2 = run_simulation(s2)
        assert r2.traffic.paid_traffic_by_channel["sem"] > r1.traffic.paid_traffic_by_channel["sem"]

    def test_cpihh_decreases_with_better_funnel(self):
        s1 = _simple_scenario()
        s2 = _simple_scenario()
        s2.visit_to_app_start = 0.10  # much better conversion
        r1 = run_simulation(s1)
        r2 = run_simulation(s2)
        assert r2.efficiency.cpihh < r1.efficiency.cpihh

    def test_pfi_multiplier_increases_ltv(self):
        s1 = _simple_scenario()
        s2 = _simple_scenario()
        s2.pfi_ltv_multiplier = s1.pfi_ltv_multiplier * 1.5
        r1 = run_simulation(s1)
        r2 = run_simulation(s2)
        assert r2.ltv.total_ltv > r1.ltv.total_ltv


# ---------------------------------------------------------------------------
# Before / After (RVGT improvements)
# ---------------------------------------------------------------------------


class TestRVGTImprovements:
    def test_apply_rvgt_improvements_returns_new_object(self):
        original = _reference_preset()
        improved = apply_rvgt_improvements(original)
        assert improved is not original
        assert original.name != improved.name

    def test_apply_rvgt_does_not_mutate_original(self):
        original = _reference_preset()
        original_cpc = original.channels["sem"].cpc
        apply_rvgt_improvements(original)
        assert original.channels["sem"].cpc == original_cpc

    def test_rvgt_lowers_cpc(self):
        original = _reference_preset()
        improved = apply_rvgt_improvements(original)
        assert improved.channels["sem"].cpc < original.channels["sem"].cpc

    def test_rvgt_lowers_cpl(self):
        original = _reference_preset()
        improved = apply_rvgt_improvements(original)
        assert improved.channels["social"].cpl < original.channels["social"].cpl

    def test_rvgt_lifts_funnel_rates(self):
        original = _reference_preset()
        improved = apply_rvgt_improvements(original)
        assert improved.visit_to_app_start > original.visit_to_app_start
        assert improved.apply_to_approve > original.apply_to_approve

    def test_rvgt_lifts_retention_rates(self):
        original = _reference_preset()
        improved = apply_rvgt_improvements(original)
        assert improved.mob6_rate >= original.mob6_rate
        assert improved.mob12_rate >= original.mob12_rate

    def test_rvgt_rates_capped_at_1(self):
        """Improvement lifts must not push rates above 100%."""
        # Build a scenario already near ceiling
        s = _simple_scenario()
        s.visit_to_app_start = 0.99
        s.mob6_rate = 0.99
        improved = apply_rvgt_improvements(s)
        assert improved.visit_to_app_start <= 1.0
        assert improved.mob6_rate <= 1.0

    def test_run_comparison_after_beats_before_on_funded_accounts(self):
        result = run_comparison(_reference_preset())
        assert result.after.funnel.funded_accounts > result.before.funnel.funded_accounts

    def test_run_comparison_delta_sign_on_cpihh(self):
        """RVGT improvements should reduce cost per incremental household."""
        result = run_comparison(_reference_preset())
        assert result.delta["cpihh"] < 0

    def test_run_comparison_pct_change_funded_accounts_positive(self):
        result = run_comparison(_reference_preset())
        assert result.pct_change["funded_accounts"] > 0

    def test_run_comparison_pct_change_roi_positive(self):
        result = run_comparison(_reference_preset())
        assert result.pct_change["roi"] > 0

    def test_run_comparison_all_keys_present(self):
        result = run_comparison(_reference_preset())
        required_keys = {
            "total_traffic",
            "funded_accounts",
            "applications",
            "mob6_retained",
            "mob12_retained",
            "pfi_converted",
            "total_ltv",
            "cpihh",
            "blended_cpl",
            "roi",
            "payback_months",
            "revenue_per_dollar",
        }
        assert required_keys.issubset(result.delta.keys())
        assert required_keys.issubset(result.pct_change.keys())


# ---------------------------------------------------------------------------
# WaterfallEngine class wrapper
# ---------------------------------------------------------------------------


class TestWaterfallEngine:
    def test_engine_simulate_returns_result(self):
        engine = WaterfallEngine()
        result = engine.simulate(_simple_scenario())
        assert result.funnel.funded_accounts > 0

    def test_engine_compare_returns_comparison(self):
        engine = WaterfallEngine()
        result = engine.compare(_reference_preset())
        assert "funded_accounts" in result.delta

    def test_engine_preset_returns_scenario(self):
        engine = WaterfallEngine()
        preset = engine.preset("regional_growth")
        assert preset.name == "regional_growth"


# ---------------------------------------------------------------------------
# Performance
# ---------------------------------------------------------------------------


class TestPerformance:
    def test_run_simulation_under_one_second(self):
        s = _reference_preset()
        start = time.perf_counter()
        run_simulation(s)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"run_simulation took {elapsed:.3f}s — expected <1s"

    def test_run_comparison_under_one_second(self):
        s = _reference_preset()
        start = time.perf_counter()
        run_comparison(s)
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"run_comparison took {elapsed:.3f}s — expected <1s"

    def test_all_presets_under_one_second(self):
        start = time.perf_counter()
        for name in _PRESET_NAMES:
            run_simulation(load_preset(name))
        elapsed = time.perf_counter() - start
        assert elapsed < 1.0, f"All preset simulations took {elapsed:.3f}s — expected <1s"


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


class TestEdgeCases:
    def test_zero_spend_gives_zero_traffic(self):
        s = _simple_scenario(spend=0.0)
        r = run_simulation(s)
        assert r.traffic.total_paid_traffic == 0.0
        assert r.traffic.total_traffic == 0.0
        assert r.funnel.funded_accounts == 0.0

    def test_zero_funded_cpihh_is_inf(self):
        s = _simple_scenario(spend=0.0)
        r = run_simulation(s)
        assert math.isinf(r.efficiency.cpihh)

    def test_scenario_name_preserved(self):
        s = _simple_scenario()
        s.name = "my_custom_scenario"
        r = run_simulation(s)
        assert r.scenario_name == "my_custom_scenario"

    def test_bd_mode_preserved(self):
        s = _simple_scenario()
        s.mode = SimulatorMode.BD
        r = run_simulation(s)
        assert r.mode == SimulatorMode.BD

    def test_client_mode_preserved(self):
        s = _simple_scenario()
        s.mode = SimulatorMode.CLIENT
        r = run_simulation(s)
        assert r.mode == SimulatorMode.CLIENT

    def test_total_spend_preserved_in_result(self):
        s = _simple_scenario(250_000.0)
        r = run_simulation(s)
        assert r.total_spend == 250_000.0
