"""
Simulator Engine — 5-Stage Waterfall Calculation Engine

Dual-mode: BD (business development pitches) vs Client (active engagement tracking).
Five pipeline stages:
  1. Traffic Generation   — spend → visits by channel (CPC/CPL), brand lift, organic/AEO
  2. Funnel Conversion    — 6-step waterfall: visit → app_start → apply → approve → open → fund
  3. Retention/Activation — MOB6/MOB12 retention rates, PFI (Primary Financial Institution) conversion
  4. LTV Projection       — retained HH × LTV per segment, PFI multiplier
  5. Efficiency Metrics   — CPIHH, ROI, payback months, blended CPL

Public API:
  run_simulation(inputs: ScenarioInput) -> SimulationResult
  run_comparison(inputs: ScenarioInput) -> ComparisonResult
  load_preset(name: str) -> ScenarioInput
  apply_rvgt_improvements(scenario: ScenarioInput) -> ScenarioInput
"""

from __future__ import annotations

import json
import math
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Optional

# ---------------------------------------------------------------------------
# Benchmarks loader
# ---------------------------------------------------------------------------

_BENCHMARKS_PATH = Path(__file__).parent.parent / "data" / "benchmarks" / "simulator.json"


def _load_benchmarks() -> dict:
    with open(_BENCHMARKS_PATH) as fh:
        return json.load(fh)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class SimulatorMode(str, Enum):
    BD = "bd"        # Business Development: show improvement potential to prospects
    CLIENT = "client"  # Client: track actual performance vs. goals


# ---------------------------------------------------------------------------
# Input dataclasses
# ---------------------------------------------------------------------------


@dataclass
class ChannelConfig:
    """Per-channel configuration. Either CPC or CPL model (not both)."""

    spend_pct: float          # Fraction of total budget allocated (0–1)
    cpc: float                # Cost-per-click (used when use_cpl=False)
    cpl: float                # Cost-per-lead (used when use_cpl=True)
    use_cpl: bool             # True → CPL model; False → CPC model
    brand_lift_pct: float = 0.0  # Incremental organic traffic as fraction of paid traffic


@dataclass
class ScenarioInput:
    """All parameters required to run a simulation."""

    name: str
    mode: SimulatorMode = SimulatorMode.BD

    # Budget
    total_spend: float = 500_000.0

    # Channel mix (must sum to ≤1.0; remainder treated as unspent)
    channels: Dict[str, ChannelConfig] = field(default_factory=dict)

    # Organic / AEO traffic multipliers applied to total paid traffic
    organic_multiplier: float = 0.12   # organic as fraction of paid total
    aeo_rate: float = 0.04             # AEO incremental traffic as fraction of paid total

    # Funnel conversion rates (6-step waterfall)
    visit_to_app_start: float = 0.06
    app_start_to_apply: float = 0.68
    apply_to_approve: float = 0.52
    approve_to_open: float = 0.91
    open_to_fund: float = 0.72

    # Retention
    mob6_rate: float = 0.78      # % of funded HH still active at Month-on-Book 6
    mob12_rate: float = 0.65     # % of funded HH still active at Month-on-Book 12
    pfi_conversion_rate: float = 0.22  # % of MOB12 HH who become PFI customers

    # LTV
    ltv_per_hh: float = 950.0        # Base LTV per retained household (annual)
    pfi_ltv_multiplier: float = 2.9  # LTV multiplier for PFI customers


# ---------------------------------------------------------------------------
# Output dataclasses (one per stage + top-level wrapper)
# ---------------------------------------------------------------------------


@dataclass
class StageTraffic:
    """Stage 1 — Traffic Generation outputs."""

    paid_traffic_by_channel: Dict[str, float]  # channel → raw paid visits/leads
    total_paid_traffic: float
    organic_traffic: float
    brand_lift_traffic: float
    aeo_traffic: float
    total_traffic: float
    spend_by_channel: Dict[str, float]         # channel → spend dollars


@dataclass
class StageFunnel:
    """Stage 2 — Funnel Conversion outputs (6-step waterfall)."""

    visits: float
    app_starts: float
    applications: float
    approvals: float
    account_opens: float
    funded_accounts: float

    # Drop-off at each step (absolute)
    drop_visit_to_app_start: float
    drop_app_start_to_apply: float
    drop_apply_to_approve: float
    drop_approve_to_open: float
    drop_open_to_fund: float


@dataclass
class StageRetention:
    """Stage 3 — Retention & Activation outputs."""

    mob6_retained: float
    mob12_retained: float
    pfi_converted: float
    mob6_churn: float
    mob12_churn: float


@dataclass
class StageLTV:
    """Stage 4 — LTV Projection outputs."""

    base_ltv: float       # LTV from MOB12 non-PFI retained HH
    pfi_ltv: float        # LTV from PFI-converted HH
    total_ltv: float


@dataclass
class StageEfficiency:
    """Stage 5 — Efficiency Metrics outputs."""

    cpihh: float          # Cost per incremental household (funded)
    blended_cpl: float    # Total spend / applications
    roi: float            # (total_ltv - total_spend) / total_spend
    payback_months: float  # months to recoup spend at LTV/12 monthly run-rate
    revenue_per_dollar: float  # total_ltv / total_spend


@dataclass
class SimulationResult:
    """Full result from a single simulation run."""

    scenario_name: str
    mode: SimulatorMode
    total_spend: float
    traffic: StageTraffic
    funnel: StageFunnel
    retention: StageRetention
    ltv: StageLTV
    efficiency: StageEfficiency


@dataclass
class SimulatorInput:
    """Alias kept for backwards-compat with __init__.py stub."""

    scenario: ScenarioInput


@dataclass
class ComparisonResult:
    """Before/After comparison — baseline vs. RVGT-improved scenario."""

    before: SimulationResult
    after: SimulationResult
    delta: Dict[str, float]      # key → (after - before)
    pct_change: Dict[str, float]  # key → (after - before) / before (0-safe)


# ---------------------------------------------------------------------------
# WaterfallEngine class (thin class wrapper around module-level functions)
# ---------------------------------------------------------------------------


class WaterfallEngine:
    """Thin class wrapper for callers that prefer OOP style."""

    def simulate(self, inputs: ScenarioInput) -> SimulationResult:
        return run_simulation(inputs)

    def compare(self, inputs: ScenarioInput) -> ComparisonResult:
        return run_comparison(inputs)

    def preset(self, name: str) -> ScenarioInput:
        return load_preset(name)

    def improve(self, scenario: ScenarioInput) -> ScenarioInput:
        return apply_rvgt_improvements(scenario)


# ---------------------------------------------------------------------------
# Stage calculations
# ---------------------------------------------------------------------------


def _stage_traffic(inputs: ScenarioInput) -> StageTraffic:
    """Stage 1: convert spend → traffic visits/leads per channel."""
    paid_by_channel: Dict[str, float] = {}
    spend_by_channel: Dict[str, float] = {}
    brand_lift_total = 0.0

    for ch_name, ch in inputs.channels.items():
        ch_spend = inputs.total_spend * ch.spend_pct
        spend_by_channel[ch_name] = ch_spend

        if ch.use_cpl:
            # CPL model: spend / CPL = number of leads delivered directly to funnel
            paid_by_channel[ch_name] = ch_spend / ch.cpl if ch.cpl > 0 else 0.0
        else:
            # CPC model: spend / CPC = number of clicks (site visits)
            paid_by_channel[ch_name] = ch_spend / ch.cpc if ch.cpc > 0 else 0.0

        brand_lift_total += paid_by_channel[ch_name] * ch.brand_lift_pct

    total_paid = sum(paid_by_channel.values())
    organic = total_paid * inputs.organic_multiplier
    aeo = total_paid * inputs.aeo_rate
    total = total_paid + organic + brand_lift_total + aeo

    return StageTraffic(
        paid_traffic_by_channel=paid_by_channel,
        total_paid_traffic=total_paid,
        organic_traffic=organic,
        brand_lift_traffic=brand_lift_total,
        aeo_traffic=aeo,
        total_traffic=total,
        spend_by_channel=spend_by_channel,
    )


def _stage_funnel(inputs: ScenarioInput, traffic: StageTraffic) -> StageFunnel:
    """Stage 2: run visits through 6-step conversion waterfall."""
    visits = traffic.total_traffic
    app_starts = visits * inputs.visit_to_app_start
    applications = app_starts * inputs.app_start_to_apply
    approvals = applications * inputs.apply_to_approve
    opens = approvals * inputs.approve_to_open
    funded = opens * inputs.open_to_fund

    return StageFunnel(
        visits=visits,
        app_starts=app_starts,
        applications=applications,
        approvals=approvals,
        account_opens=opens,
        funded_accounts=funded,
        drop_visit_to_app_start=visits - app_starts,
        drop_app_start_to_apply=app_starts - applications,
        drop_apply_to_approve=applications - approvals,
        drop_approve_to_open=approvals - opens,
        drop_open_to_fund=opens - funded,
    )


def _stage_retention(inputs: ScenarioInput, funnel: StageFunnel) -> StageRetention:
    """Stage 3: apply MOB6/MOB12 retention and PFI conversion."""
    mob6 = funnel.funded_accounts * inputs.mob6_rate
    mob12 = funnel.funded_accounts * inputs.mob12_rate
    pfi = mob12 * inputs.pfi_conversion_rate

    return StageRetention(
        mob6_retained=mob6,
        mob12_retained=mob12,
        pfi_converted=pfi,
        mob6_churn=funnel.funded_accounts - mob6,
        mob12_churn=funnel.funded_accounts - mob12,
    )


def _stage_ltv(inputs: ScenarioInput, retention: StageRetention) -> StageLTV:
    """Stage 4: project LTV from retained and PFI households."""
    non_pfi_mob12 = retention.mob12_retained - retention.pfi_converted
    base_ltv = non_pfi_mob12 * inputs.ltv_per_hh
    pfi_ltv = retention.pfi_converted * inputs.ltv_per_hh * inputs.pfi_ltv_multiplier
    total_ltv = base_ltv + pfi_ltv

    return StageLTV(
        base_ltv=base_ltv,
        pfi_ltv=pfi_ltv,
        total_ltv=total_ltv,
    )


def _stage_efficiency(
    inputs: ScenarioInput,
    funnel: StageFunnel,
    ltv: StageLTV,
) -> StageEfficiency:
    """Stage 5: compute cost efficiency and return metrics."""
    funded = funnel.funded_accounts
    applications = funnel.applications
    spend = inputs.total_spend
    total_ltv = ltv.total_ltv

    cpihh = spend / funded if funded > 0 else float("inf")
    blended_cpl = spend / applications if applications > 0 else float("inf")
    roi = (total_ltv - spend) / spend if spend > 0 else 0.0
    monthly_ltv_run_rate = total_ltv / 12.0
    payback_months = spend / monthly_ltv_run_rate if monthly_ltv_run_rate > 0 else float("inf")
    revenue_per_dollar = total_ltv / spend if spend > 0 else 0.0

    return StageEfficiency(
        cpihh=cpihh,
        blended_cpl=blended_cpl,
        roi=roi,
        payback_months=payback_months,
        revenue_per_dollar=revenue_per_dollar,
    )


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def run_simulation(inputs: ScenarioInput) -> SimulationResult:
    """Run the full 5-stage waterfall for a single scenario.

    Pure calculation — no I/O, no DB access. Runs in well under 1 second.
    """
    traffic = _stage_traffic(inputs)
    funnel = _stage_funnel(inputs, traffic)
    retention = _stage_retention(inputs, funnel)
    ltv = _stage_ltv(inputs, retention)
    efficiency = _stage_efficiency(inputs, funnel, ltv)

    return SimulationResult(
        scenario_name=inputs.name,
        mode=inputs.mode,
        total_spend=inputs.total_spend,
        traffic=traffic,
        funnel=funnel,
        retention=retention,
        ltv=ltv,
        efficiency=efficiency,
    )


def run_comparison(inputs: ScenarioInput) -> ComparisonResult:
    """Run before/after comparison.

    'before' = inputs as provided (baseline).
    'after'  = inputs with RVGT improvements applied.
    Returns deltas and percent-change for all key metrics.
    """
    before_result = run_simulation(inputs)
    after_inputs = apply_rvgt_improvements(inputs)
    after_result = run_simulation(after_inputs)

    before_kpis = _extract_kpis(before_result)
    after_kpis = _extract_kpis(after_result)

    delta: Dict[str, float] = {}
    pct_change: Dict[str, float] = {}
    for key in before_kpis:
        b = before_kpis[key]
        a = after_kpis[key]
        delta[key] = a - b
        pct_change[key] = (a - b) / b if b != 0 else 0.0

    return ComparisonResult(
        before=before_result,
        after=after_result,
        delta=delta,
        pct_change=pct_change,
    )


def _extract_kpis(result: SimulationResult) -> Dict[str, float]:
    """Flatten key metrics from a SimulationResult for comparison."""
    return {
        "total_traffic": result.traffic.total_traffic,
        "funded_accounts": result.funnel.funded_accounts,
        "applications": result.funnel.applications,
        "mob6_retained": result.retention.mob6_retained,
        "mob12_retained": result.retention.mob12_retained,
        "pfi_converted": result.retention.pfi_converted,
        "total_ltv": result.ltv.total_ltv,
        "cpihh": result.efficiency.cpihh,
        "blended_cpl": result.efficiency.blended_cpl,
        "roi": result.efficiency.roi,
        "payback_months": result.efficiency.payback_months,
        "revenue_per_dollar": result.efficiency.revenue_per_dollar,
    }


def load_preset(name: str) -> ScenarioInput:
    """Return a named preset ScenarioInput.

    Preset names match the APE-23a contract (src/data/benchmarks/presets.py):
      - regional_growth         Mid-size regional bank, organic growth strategy
      - top_20                  Large national bank, efficiency-focused
      - community               Small community bank, relationship-driven
      - de_novo                 New digital-first bank, high CAC / fast funnel
      - acquisition_integration Post-acquisition bank, retention-focused
    """
    presets = {
        "regional_growth": _preset_regional_growth,
        "top_20": _preset_top_20,
        "community": _preset_community,
        "de_novo": _preset_de_novo,
        "acquisition_integration": _preset_acquisition_integration,
    }
    if name not in presets:
        raise ValueError(
            f"Unknown preset '{name}'. Available: {sorted(presets.keys())}"
        )
    return presets[name]()


def apply_rvgt_improvements(scenario: ScenarioInput) -> ScenarioInput:
    """Apply RVGT improvement deltas to a scenario and return a new ScenarioInput.

    Improvement magnitudes are loaded from src/data/benchmarks/simulator.json
    so they can be tuned without code changes.

    Does NOT mutate the input — returns a new object.
    """
    bm = _load_benchmarks()
    imp = bm["rvgt_improvements"]

    # Copy channel configs with reduced CPCs/CPLs
    new_channels: Dict[str, ChannelConfig] = {}
    for ch_name, ch in scenario.channels.items():
        new_channels[ch_name] = ChannelConfig(
            spend_pct=ch.spend_pct,
            cpc=ch.cpc * (1.0 - imp["cpc_reduction_pct"]) if not ch.use_cpl else ch.cpc,
            cpl=ch.cpl * (1.0 - imp["cpl_reduction_pct"]) if ch.use_cpl else ch.cpl,
            use_cpl=ch.use_cpl,
            brand_lift_pct=ch.brand_lift_pct,
        )

    def _lift(base: float, lift_pct: float) -> float:
        """Apply a percentage lift, capped at 1.0 for rates."""
        return min(1.0, base * (1.0 + lift_pct))

    return ScenarioInput(
        name=f"{scenario.name} (RVGT)",
        mode=scenario.mode,
        total_spend=scenario.total_spend,
        channels=new_channels,
        organic_multiplier=scenario.organic_multiplier * (1.0 + imp["organic_multiplier_lift"]),
        aeo_rate=scenario.aeo_rate,
        visit_to_app_start=_lift(scenario.visit_to_app_start, imp["visit_to_app_start_lift"]),
        app_start_to_apply=_lift(scenario.app_start_to_apply, imp["app_start_to_apply_lift"]),
        apply_to_approve=_lift(scenario.apply_to_approve, imp["apply_to_approve_lift"]),
        approve_to_open=_lift(scenario.approve_to_open, imp["approve_to_open_lift"]),
        open_to_fund=_lift(scenario.open_to_fund, imp["open_to_fund_lift"]),
        mob6_rate=_lift(scenario.mob6_rate, imp["mob6_rate_lift"]),
        mob12_rate=_lift(scenario.mob12_rate, imp["mob12_rate_lift"]),
        pfi_conversion_rate=_lift(scenario.pfi_conversion_rate, imp["pfi_conversion_lift"]),
        ltv_per_hh=scenario.ltv_per_hh,
        pfi_ltv_multiplier=scenario.pfi_ltv_multiplier,
    )


# ---------------------------------------------------------------------------
# Preset factory functions
# ---------------------------------------------------------------------------


def _default_channels_from_benchmarks(bm: dict, overrides: Optional[dict] = None) -> Dict[str, ChannelConfig]:
    """Build channel configs from benchmark defaults with optional spend_pct overrides."""
    default_spend_pcts = {
        "sem": 0.40,
        "social": 0.30,
        "display": 0.20,
        "direct_mail": 0.10,
    }
    if overrides:
        default_spend_pcts.update(overrides)

    channels: Dict[str, ChannelConfig] = {}
    for ch_name, ch_bm in bm["channels"].items():
        channels[ch_name] = ChannelConfig(
            spend_pct=default_spend_pcts.get(ch_name, 0.0),
            cpc=ch_bm["cpc"] or 0.0,
            cpl=ch_bm["cpl"] or 0.0,
            use_cpl=ch_bm["use_cpl"],
            brand_lift_pct=ch_bm["brand_lift_pct"],
        )
    return channels


def _preset_regional_growth() -> ScenarioInput:
    """Mid-size regional bank ($15–25B assets), organic growth strategy.

    APE-23a archetype: regional_growth. Full RVGT engagement.
    SEM-heavy mix (56%), strong direct mail / email block.
    """
    bm = _load_benchmarks()
    # Consolidate APE-23a 8-channel mix into engine's 4 channels:
    #   sem          = paid_search_branded(0.18) + paid_search_non_branded(0.38)
    #   social       = paid_social(0.20)
    #   display      = display(0.08)
    #   direct_mail  = direct_mail(0.07) + email(0.06) + referral(0.03)
    channels = _default_channels_from_benchmarks(
        bm, {"sem": 0.56, "social": 0.20, "display": 0.08, "direct_mail": 0.16}
    )
    return ScenarioInput(
        name="regional_growth",
        mode=SimulatorMode.CLIENT,
        total_spend=1_250_000.0,      # annual_media_budget / 12 months
        channels=channels,
        organic_multiplier=0.14,
        aeo_rate=bm["organic"]["aeo_rate"],
        visit_to_app_start=0.50,      # page_visit_to_app_start
        app_start_to_apply=0.63,      # app_start_to_form_complete
        apply_to_approve=0.75,        # form_complete_to_kyc_pass
        approve_to_open=0.84,         # kyc_pass_to_approval
        open_to_fund=0.72,            # approval_to_funded
        mob6_rate=0.85,               # checking_90d proxy
        mob12_rate=0.74,              # checking_1yr
        pfi_conversion_rate=0.68,     # product_activation_30d
        ltv_per_hh=933.0,             # ltv_3yr_blended(2800) / 3
        pfi_ltv_multiplier=bm["ltv"]["pfi_ltv_multiplier"],
    )


def _preset_top_20() -> ScenarioInput:
    """Large national bank ($100B+ assets), efficiency and personalization at scale.

    APE-23a archetype: top_20. Full RVGT engagement.
    Balanced multi-channel mix, high funnel conversion, best-in-class retention.
    """
    bm = _load_benchmarks()
    # sem = 0.20 + 0.30 = 0.50, social = 0.22, display = 0.12,
    # direct_mail = 0.05 + 0.08 + 0.03 = 0.16
    channels = _default_channels_from_benchmarks(
        bm, {"sem": 0.50, "social": 0.22, "display": 0.12, "direct_mail": 0.16}
    )
    return ScenarioInput(
        name="top_20",
        mode=SimulatorMode.CLIENT,
        total_spend=6_250_000.0,      # annual_media_budget(75MM) / 12
        channels=channels,
        organic_multiplier=0.20,
        aeo_rate=bm["organic"]["aeo_rate"],
        visit_to_app_start=0.58,
        app_start_to_apply=0.72,
        apply_to_approve=0.84,
        approve_to_open=0.90,
        open_to_fund=0.82,
        mob6_rate=0.90,
        mob12_rate=0.82,
        pfi_conversion_rate=0.76,
        ltv_per_hh=1_400.0,          # ltv_3yr_blended(4200) / 3
        pfi_ltv_multiplier=bm["ltv"]["pfi_ltv_multiplier"],
    )


def _preset_community() -> ScenarioInput:
    """Small community bank (<$2B assets), relationship-driven, heavy direct mail.

    APE-23a archetype: community. Pilot RVGT engagement — high growth ceiling.
    Low media budget, direct mail dominant (47% of mix).
    """
    bm = _load_benchmarks()
    # sem = 0.12 + 0.18 = 0.30, social = 0.18, display = 0.05,
    # direct_mail = 0.28 + 0.08 + 0.11 = 0.47
    channels = _default_channels_from_benchmarks(
        bm, {"sem": 0.30, "social": 0.18, "display": 0.05, "direct_mail": 0.47}
    )
    return ScenarioInput(
        name="community",
        mode=SimulatorMode.CLIENT,
        total_spend=100_000.0,        # annual_media_budget(1.2MM) / 12
        channels=channels,
        organic_multiplier=0.10,
        aeo_rate=bm["organic"]["aeo_rate"],
        visit_to_app_start=0.44,
        app_start_to_apply=0.58,
        apply_to_approve=0.72,
        approve_to_open=0.82,
        open_to_fund=0.68,
        mob6_rate=0.84,
        mob12_rate=0.76,
        pfi_conversion_rate=0.60,
        ltv_per_hh=633.0,            # ltv_3yr_blended(1900) / 3
        pfi_ltv_multiplier=bm["ltv"]["pfi_ltv_multiplier"],
    )


def _preset_de_novo() -> ScenarioInput:
    """New digital-first bank, no branches, high CAC, fast digital funnel.

    APE-23a archetype: de_novo. Prospect RVGT engagement stage.
    Performance marketing heavy, Year 1–3 breakeven horizon 18–24 months.
    """
    bm = _load_benchmarks()
    # sem = 0.08 + 0.35 = 0.43, social = 0.32, display = 0.10,
    # direct_mail = 0.02 + 0.08 + 0.05 = 0.15
    channels = _default_channels_from_benchmarks(
        bm, {"sem": 0.43, "social": 0.32, "display": 0.10, "direct_mail": 0.15}
    )
    return ScenarioInput(
        name="de_novo",
        mode=SimulatorMode.BD,
        total_spend=708_333.0,        # annual_media_budget(8.5MM) / 12
        channels=channels,
        organic_multiplier=0.08,      # early organic footprint
        aeo_rate=bm["organic"]["aeo_rate"],
        visit_to_app_start=0.55,
        app_start_to_apply=0.75,
        apply_to_approve=0.82,
        approve_to_open=0.88,
        open_to_fund=0.78,
        mob6_rate=0.76,               # checking_90d
        mob12_rate=0.60,              # checking_1yr — higher churn early
        pfi_conversion_rate=0.74,     # product_activation_30d — high (fully digital)
        ltv_per_hh=533.0,            # ltv_3yr_blended(1600) / 3
        pfi_ltv_multiplier=bm["ltv"]["pfi_ltv_multiplier"],
    )


def _preset_acquisition_integration() -> ScenarioInput:
    """Post-acquisition bank (12–18 months), dual-brand, elevated churn risk.

    APE-23a archetype: acquisition_integration. Full RVGT engagement.
    Marketing bridges two brands; focus on cross-sell, loyalty, churn prevention.
    """
    bm = _load_benchmarks()
    # sem = 0.22 + 0.28 = 0.50, social = 0.18, display = 0.07,
    # direct_mail = 0.10 + 0.12 + 0.03 = 0.25
    channels = _default_channels_from_benchmarks(
        bm, {"sem": 0.50, "social": 0.18, "display": 0.07, "direct_mail": 0.25}
    )
    return ScenarioInput(
        name="acquisition_integration",
        mode=SimulatorMode.CLIENT,
        total_spend=1_833_333.0,      # annual_media_budget(22MM) / 12
        channels=channels,
        organic_multiplier=0.12,
        aeo_rate=bm["organic"]["aeo_rate"],
        visit_to_app_start=0.46,      # degraded — brand confusion post-acquisition
        app_start_to_apply=0.60,
        apply_to_approve=0.74,
        approve_to_open=0.83,
        open_to_fund=0.70,
        mob6_rate=0.80,               # checking_90d — elevated churn from acquired HH
        mob12_rate=0.68,              # checking_1yr
        pfi_conversion_rate=0.58,     # product_activation_30d — disrupted by migration
        ltv_per_hh=800.0,            # ltv_3yr_blended(2400) / 3
        pfi_ltv_multiplier=bm["ltv"]["pfi_ltv_multiplier"],
    )
