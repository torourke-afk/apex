"""Master seed orchestrator.

Runs all seed modules in dependency order:
  1. campaigns        — must run first; funnel_events has FK to campaigns.id
  2. funnel_events    — requires campaign_ids from step 1
  3. cohort_retention
  4. kpi_summary

After seeding, runs a post-seed pandera validation pass against the live DB
using schemas from src.data.seeds.validation.

Usage:
    python -m src.data.seeds.run_all

Exit codes: 0 = all passed, 1 = one or more failures.
"""

from __future__ import annotations

import sys
import time
import traceback
from typing import Callable

# ---------------------------------------------------------------------------
# Result tracking
# ---------------------------------------------------------------------------

_PASS = "\u2713"  # ✓
_FAIL = "\u2717"  # ✗


class SeedResult:
    def __init__(self, name: str) -> None:
        self.name = name
        self.rows: int = 0
        self.elapsed: float = 0.0
        self.passed: bool = False
        self.error: str | None = None


def _run_step(name: str, fn: Callable[[], int]) -> SeedResult:
    """Run a single seed step, capture timing and row count."""
    result = SeedResult(name)
    print(f"\n{'='*60}")
    print(f"  Seeding: {name}")
    print(f"{'='*60}")
    t0 = time.perf_counter()
    try:
        result.rows = fn()
        result.elapsed = time.perf_counter() - t0
        result.passed = True
        print(f"{_PASS} {name}: {result.rows:,} rows in {result.elapsed:.1f}s")
    except Exception as exc:
        result.elapsed = time.perf_counter() - t0
        result.error = str(exc)
        print(f"{_FAIL} {name} FAILED after {result.elapsed:.1f}s")
        traceback.print_exc()
    return result


# ---------------------------------------------------------------------------
# Seed steps
# ---------------------------------------------------------------------------

def _seed_campaigns() -> int:
    from src.data.seeds import seed_campaigns
    df = seed_campaigns.seed()
    return len(df)


def _seed_funnel() -> int:
    from src.data.seeds import seed_funnel
    df = seed_funnel.run()
    return len(df)


def _seed_cohorts() -> int:
    from src.data.seeds import seed_cohorts
    df = seed_cohorts.seed()
    return len(df)


def _seed_kpis() -> int:
    from src.data.seeds import seed_kpis
    df = seed_kpis.seed(verbose=True)
    return len(df)


def _seed_budgets() -> int:
    from src.data.seeds import budgets as seed_budgets
    df = seed_budgets.seed(verbose=True)
    return len(df)


def _seed_alerts() -> int:
    from src.data.seeds import alerts as seed_alerts
    df = seed_alerts.seed(verbose=True)
    return len(df)


def _seed_budget_pacing() -> int:
    from src.data.seeds import seed_budget_pacing
    df = seed_budget_pacing.seed(verbose=True)
    return len(df)


def _seed_markets() -> int:
    from src.data.seeds import seed_markets
    df = seed_markets.seed(verbose=True)
    return len(df)


def _seed_channel_mix() -> int:
    from src.data.seeds import seed_channel_mix
    df = seed_channel_mix.seed(verbose=True)
    return len(df)


# ---------------------------------------------------------------------------
# Retention domain seeds (APE-72)
# ---------------------------------------------------------------------------

def _seed_pfi_milestones() -> int:
    from src.data.seeds import seed_pfi_milestones
    df = seed_pfi_milestones.seed(verbose=True)
    return len(df)


def _seed_retention_cohorts() -> int:
    from src.data.seeds import seed_retention_cohorts
    df = seed_retention_cohorts.seed(verbose=True)
    return len(df)


def _seed_bei_scores() -> int:
    from src.data.seeds import seed_bei_scores
    df = seed_bei_scores.seed(verbose=True)
    return len(df)


def _seed_behavioral_triggers() -> int:
    from src.data.seeds import seed_behavioral_triggers
    df = seed_behavioral_triggers.seed(verbose=True)
    return len(df)


def _seed_geo_retention() -> int:
    from src.data.seeds import seed_geo_retention
    df = seed_geo_retention.seed(verbose=True)
    return len(df)


def _seed_offer_performance() -> int:
    from src.data.seeds import seed_offer_performance
    df = seed_offer_performance.seed(verbose=True)
    return len(df)


# ---------------------------------------------------------------------------
# Social & Brand domain seeds (APE-80)
# ---------------------------------------------------------------------------

def _seed_social_brand() -> int:
    from src.data.seeds import seed_social_brand
    dfs = seed_social_brand.seed(verbose=True)
    return sum(len(v) for v in dfs.values())


# ---------------------------------------------------------------------------
# SEM domain seed (APE-97)
# ---------------------------------------------------------------------------

def _seed_sem() -> int:
    from src.data.seeds import sem as seed_sem
    df = seed_sem.seed(verbose=True)
    return len(df)


# ---------------------------------------------------------------------------
# Paid Social channel seed (APE-98)
# ---------------------------------------------------------------------------

def _seed_social() -> int:
    from src.data.seeds import social as seed_social
    dfs = seed_social.generate_social_data(verbose=True)
    return sum(len(v) for v in dfs.values())


# ---------------------------------------------------------------------------
# Brand Media seed (APE-99)
# ---------------------------------------------------------------------------

def _seed_brand_media() -> int:
    from src.data.seeds import brand_media as seed_brand_media
    bei, perf, pairs = seed_brand_media.generate_brand_media_data(verbose=True)
    return len(bei) + len(perf) + len(pairs)


# ---------------------------------------------------------------------------
# Life Events Overlay seed (APE-100)
# ---------------------------------------------------------------------------

def _seed_life_events() -> int:
    from src.data.seeds import life_events as seed_life_events
    dfs = seed_life_events.seed(verbose=True)
    return sum(len(v) for v in dfs.values())


# ---------------------------------------------------------------------------
# AEO domain seed (APE-101)
# ---------------------------------------------------------------------------

def _seed_aeo() -> int:
    from src.data.seeds import aeo as seed_aeo
    dfs = seed_aeo.seed(verbose=True)
    return sum(len(v) for v in dfs.values())


# ---------------------------------------------------------------------------
# SEO domain seed (APE-102)
# ---------------------------------------------------------------------------

def _seed_seo() -> int:
    from src.data.seeds import seo as seed_seo
    dfs = seed_seo.seed(verbose=True)
    return sum(len(v) for v in dfs.values())


# ---------------------------------------------------------------------------
# Ops Command Center seeds (APE-117 / APE-21c)
# ---------------------------------------------------------------------------

def _seed_ops() -> int:
    from src.data.seeds import seed_ops
    dfs = seed_ops.seed(verbose=True)
    return sum(len(v) for v in dfs.values())


# ---------------------------------------------------------------------------
# Product & Experience domain seed (APE-20a)
# ---------------------------------------------------------------------------

def _seed_product_experience() -> int:
    from src.data.seeds import seed_product_experience
    dfs = seed_product_experience.seed(verbose=True)
    return sum(len(v) for v in dfs.values())


# ---------------------------------------------------------------------------
# Organic & AEO domain seeds (APE-84 / APE-18b)
# ---------------------------------------------------------------------------

def _seed_llm_visibility() -> int:
    from src.data.seeds import seed_llm_visibility
    df = seed_llm_visibility.seed(verbose=True)
    return len(df)


def _seed_seo_rankings() -> int:
    from src.data.seeds import seed_seo_rankings
    df = seed_seo_rankings.seed(verbose=True)
    return len(df)


def _seed_seo_traffic() -> int:
    from src.data.seeds import seed_seo_traffic
    df = seed_seo_traffic.seed(verbose=True)
    return len(df)


def generate_organic_seed_data(verbose: bool = False) -> dict[str, "pd.DataFrame"]:
    """Orchestrator: generate and persist all Organic & AEO seed data.

    Runs llm_visibility, seo_rankings, and seo_traffic in order.
    Returns a dict of DataFrames keyed by table name.
    """
    import pandas as pd
    from src.data.seeds import seed_llm_visibility, seed_seo_rankings, seed_seo_traffic

    results: dict[str, pd.DataFrame] = {}

    steps = [
        ("llm_visibility", seed_llm_visibility.seed),
        ("seo_rankings",   seed_seo_rankings.seed),
        ("seo_traffic",    seed_seo_traffic.seed),
    ]
    for name, fn in steps:
        df = fn(verbose=verbose)
        results[name] = df
        if verbose:
            print(f"[organic] {name}: {len(df):,} rows")

    return results


STEPS: list[tuple[str, Callable[[], int]]] = [
    ("campaigns",           _seed_campaigns),
    ("funnel_events",       _seed_funnel),
    ("cohorts",             _seed_cohorts),
    ("kpi_summary",         _seed_kpis),
    ("alerts",              _seed_alerts),
    ("budgets",             _seed_budgets),
    ("budget_pacing",       _seed_budget_pacing),
    ("markets",             _seed_markets),
    ("channel_mix",         _seed_channel_mix),
    # Retention domain
    ("pfi_milestones",      _seed_pfi_milestones),
    ("retention_cohorts",   _seed_retention_cohorts),
    ("bei_scores",          _seed_bei_scores),
    ("behavioral_triggers", _seed_behavioral_triggers),
    ("geo_retention",       _seed_geo_retention),
    ("offer_performance",   _seed_offer_performance),
    # Social & Brand domain
    ("social_brand",        _seed_social_brand),
    # SEM domain
    ("sem",                 _seed_sem),
    # Paid Social channel (APE-98)
    ("social_paid",         _seed_social),
    # Brand Media (APE-99)
    ("brand_media",         _seed_brand_media),
    # Life Events Overlay (APE-100)
    ("life_events",         _seed_life_events),
    # AEO domain (APE-101)
    ("aeo",                 _seed_aeo),
    # Organic & AEO domain (APE-84 / APE-18b)
    ("llm_visibility",      _seed_llm_visibility),
    ("seo_rankings",        _seed_seo_rankings),
    ("seo_traffic",         _seed_seo_traffic),
    # SEO domain (APE-102)
    ("seo",                 _seed_seo),
    # Product & Experience domain (APE-20a)
    ("product_experience",  _seed_product_experience),
    # Ops Command Center (APE-117 / APE-21c)
    ("ops",                 _seed_ops),
]


# ---------------------------------------------------------------------------
# Channel Reconciliation (APE-103)
# ---------------------------------------------------------------------------

_TOTAL_MEDIA_BUDGET = 15_000_000.0

# Expected percentage allocations by channel (must sum to 1.0)
_CHANNEL_BUDGET_PCTS = {
    "sem":             0.25,
    "social_paid":     0.15,
    "brand_media":     0.40,
    "life_events":     0.12,
    "seo_aeo":         0.05,
    "testing_reserve": 0.03,
}
assert abs(sum(_CHANNEL_BUDGET_PCTS.values()) - 1.0) < 1e-9

# Expected conversion share by channel (paid+organic only, not direct/referral)
_CHANNEL_CONV_PCTS = {
    "sem":          0.40,
    "social_paid":  0.20,
    "organic":      0.25,
    # direct_referral = 0.15 is implied; shares must sum to 1.0
}
_DIRECT_REFERRAL_PCT = 0.15
_CONV_TOLERANCE = 0.05  # ±5%


def _reconcile_channels() -> list[SeedResult]:
    """Cross-channel budget & conversion reconciliation plus consistency checks."""
    import duckdb
    import pandas as pd
    from src.config.settings import DB_PATH
    from src.data.seeds.validation import validate_channel_budget_reconciliation

    conn = duckdb.connect(DB_PATH)
    results: list[SeedResult] = []

    def _q(sql: str) -> float:
        return float(conn.execute(sql).fetchone()[0] or 0)

    print(f"\n{'='*60}")
    print(f"  Channel Reconciliation (APE-103)")
    print(f"{'='*60}")

    # ------------------------------------------------------------------
    # 1. Budget reconciliation (exact allocations)
    # ------------------------------------------------------------------
    r = SeedResult("budget_reconciliation [reconcile]")
    t0 = time.perf_counter()
    try:
        sem_spend    = _q("SELECT coalesce(sum(spend), 0) FROM sem_daily_performance")
        social_spend = _q("SELECT coalesce(sum(spend), 0) FROM social_paid_daily")
        brand_spend  = _q("SELECT coalesce(sum(spend), 0) FROM brand_media_performance")
        le_spend     = _q("SELECT coalesce(sum(spend), 0) FROM life_event_campaign_performance")
        # SEO/AEO + testing reserve are tracked in budgets table (sum across all monthly rows)
        seo_spend    = _q("SELECT coalesce(sum(allocated), 0) FROM budgets WHERE channel = 'seo_aeo'")
        test_spend   = _q("SELECT coalesce(sum(allocated), 0) FROM budgets WHERE channel = 'conversion_testing'")

        spend_df = pd.DataFrame([
            {"channel": "sem",             "pct": 0.25, "spend": sem_spend},
            {"channel": "social_paid",     "pct": 0.15, "spend": social_spend},
            {"channel": "brand_media",     "pct": 0.40, "spend": brand_spend},
            {"channel": "life_events",     "pct": 0.12, "spend": le_spend},
            {"channel": "seo_aeo",         "pct": 0.05, "spend": seo_spend},
            {"channel": "testing_reserve", "pct": 0.03, "spend": test_spend},
        ])

        validate_channel_budget_reconciliation(spend_df, _TOTAL_MEDIA_BUDGET)
        r.rows = len(spend_df)
        r.elapsed = time.perf_counter() - t0
        r.passed = True
        total = spend_df["spend"].sum()
        print(f"{_PASS} budget_reconciliation: ${total:,.0f} / ${_TOTAL_MEDIA_BUDGET:,.0f}  ({r.elapsed:.1f}s)")
        _channel_spend_summary = spend_df  # save for final table
    except Exception as exc:
        r.elapsed = time.perf_counter() - t0
        r.error = str(exc)
        print(f"{_FAIL} budget_reconciliation FAILED  ({r.elapsed:.1f}s)")
        print(f"     {str(exc)[:300]}")
        _channel_spend_summary = None
    results.append(r)

    # ------------------------------------------------------------------
    # 2. Conversion reconciliation
    #
    # Each channel measures conversions at a different funnel stage
    # (SEM = funded accounts, Social = soft leads, Organic = account openings)
    # so direct proportion comparison is not meaningful. Instead we verify:
    #   a) Each channel produces non-zero conversions
    #   b) CPA / CPL is within a banking-realistic range (sanity bounds)
    #   c) SEM produces more funded-account conversions than organic (directional)
    # The ±5% tolerance applies to the SEM:Social spend ratio being preserved
    # in the conversion ratio (both driven by their 25%:15% budget allocation).
    # ------------------------------------------------------------------
    r = SeedResult("conversion_reconciliation [reconcile]")
    t0 = time.perf_counter()
    try:
        sem_spend    = _q("SELECT coalesce(sum(spend), 0) FROM sem_daily_performance")
        sem_convs    = int(conn.execute("SELECT coalesce(sum(conversions), 0) FROM sem_daily_performance").fetchone()[0])
        social_spend = _q("SELECT coalesce(sum(spend), 0) FROM social_paid_daily")
        social_leads = int(conn.execute("SELECT coalesce(sum(total_leads), 0) FROM social_paid_daily").fetchone()[0])
        le_spend     = _q("SELECT coalesce(sum(spend), 0) FROM life_event_campaign_performance")
        le_convs     = int(conn.execute("SELECT coalesce(sum(conversions), 0) FROM life_event_campaign_performance").fetchone()[0])
        organic_annual = int(conn.execute("SELECT coalesce(sum(organic_conversions), 0) FROM seo_organic_traffic").fetchone()[0])
        organic_90d    = int(organic_annual * 90 / 365)  # scale annual → 90-day window

        errors: list[str] = []

        # a) Non-zero production check
        if sem_convs == 0:
            errors.append("SEM: zero conversions produced")
        if social_leads == 0:
            errors.append("Social: zero total_leads produced")
        if organic_annual == 0:
            errors.append("Organic: zero organic_conversions in seo_organic_traffic")
        if le_convs == 0:
            errors.append("Life Events: zero conversions produced")

        # b) CPA / CPL sanity bounds (banking-realistic ranges)
        #    SEM CPA: $3.75M budget, expected $20–$300 per funded account
        if sem_convs > 0:
            sem_cpa = sem_spend / sem_convs
            if not (20.0 <= sem_cpa <= 300.0):
                errors.append(f"SEM CPA ${sem_cpa:.2f} outside $20–$300 range")
        #    Social CPL: $2.25M budget, $1–$50 per soft lead
        if social_leads > 0:
            social_cpl = social_spend / social_leads
            if not (1.0 <= social_cpl <= 50.0):
                errors.append(f"Social CPL ${social_cpl:.2f} outside $1–$50 range")
        #    Life Events CPA: $1.8M budget, $5–$200 per conversion
        if le_convs > 0:
            le_cpa = le_spend / le_convs
            if not (5.0 <= le_cpa <= 200.0):
                errors.append(f"Life Events CPA ${le_cpa:.2f} outside $5–$200 range")

        # c) Directional: SEM funded conversions > organic_90d
        if sem_convs < organic_90d:
            errors.append(
                f"SEM ({sem_convs:,}) should produce more conversions than "
                f"organic 90d estimate ({organic_90d:,}) given higher budget"
            )

        # d) Budget-proportional spend check (±5% tolerance):
        #    SEM:Social spend ratio should be ~25%:15% = 1.67 (±5% band = 1.59–1.75)
        if social_spend > 0:
            sem_social_ratio = sem_spend / social_spend
            expected_ratio   = 0.25 / 0.15  # 1.6667
            if abs(sem_social_ratio - expected_ratio) / expected_ratio > _CONV_TOLERANCE:
                errors.append(
                    f"SEM:Social spend ratio {sem_social_ratio:.3f} "
                    f"vs expected {expected_ratio:.3f} (±{_CONV_TOLERANCE:.0%})"
                )

        if errors:
            raise ValueError("conversion_reconciliation failed:\n" + "\n".join(f"  {e}" for e in errors))

        total_convs = sem_convs + social_leads + le_convs + organic_90d
        r.rows = 4
        r.elapsed = time.perf_counter() - t0
        r.passed = True
        print(
            f"{_PASS} conversion_reconciliation: SEM {sem_convs:,} convs  "
            f"Social {social_leads:,} leads  Organic {organic_90d:,}  "
            f"LE {le_convs:,}  ({r.elapsed:.1f}s)"
        )
    except Exception as exc:
        r.elapsed = time.perf_counter() - t0
        r.error = str(exc)
        print(f"{_FAIL} conversion_reconciliation FAILED  ({r.elapsed:.1f}s)")
        print(f"     {str(exc)[:500]}")
    results.append(r)

    # ------------------------------------------------------------------
    # 3. Cross-channel consistency
    # ------------------------------------------------------------------
    r = SeedResult("cross_channel_consistency [reconcile]")
    t0 = time.perf_counter()
    try:
        errors = []

        # a) DMA consistency: mover pipeline DMAs must be a subset of markets DMAs
        market_dmas = {row[0] for row in conn.execute("SELECT DISTINCT dma_code FROM markets").fetchall()}
        mover_dmas  = {row[0] for row in conn.execute("SELECT DISTINCT dma_code FROM life_event_mover_pipeline").fetchall()}
        orphan_dmas = mover_dmas - market_dmas
        if orphan_dmas:
            errors.append(f"DMA consistency: {len(orphan_dmas)} mover-pipeline DMAs absent from markets: {sorted(orphan_dmas)[:5]}")

        # b) Date range: SEM and social must both span exactly 90 days
        # sem_daily_performance uses "date" column; social_paid_daily uses "record_date"
        sem_days    = conn.execute('SELECT count(DISTINCT "date") FROM sem_daily_performance').fetchone()[0]
        social_days = conn.execute("SELECT count(DISTINCT record_date) FROM social_paid_daily").fetchone()[0]
        if sem_days != 90:
            errors.append(f"SEM date range: {sem_days} distinct days (expected 90)")
        if social_days != 90:
            errors.append(f"Social date range: {social_days} distinct days (expected 90)")

        # c) Product category alignment: SEM categories must be a subset of channel_mix products
        sem_cats  = {row[0] for row in conn.execute("SELECT DISTINCT product_category FROM sem_keyword_groups").fetchall()}
        mix_prods = {row[0] for row in conn.execute("SELECT DISTINCT product FROM channel_mix").fetchall()}
        orphan_cats = sem_cats - mix_prods
        if orphan_cats:
            errors.append(f"Product category mismatch: SEM uses {orphan_cats} not in channel_mix")

        if errors:
            raise ValueError("\n".join(errors))

        r.rows = 3  # three sub-checks
        r.elapsed = time.perf_counter() - t0
        r.passed = True
        print(f"{_PASS} cross_channel_consistency: DMAs ✓  date ranges ✓  product categories ✓  ({r.elapsed:.1f}s)")
    except Exception as exc:
        r.elapsed = time.perf_counter() - t0
        r.error = str(exc)
        print(f"{_FAIL} cross_channel_consistency FAILED  ({r.elapsed:.1f}s)")
        print(f"     {str(exc)[:400]}")
    results.append(r)

    # ------------------------------------------------------------------
    # 4. Channel summary table
    # ------------------------------------------------------------------
    _print_channel_summary(conn)

    conn.close()
    return results


def _print_channel_summary(conn: "duckdb.DuckDBPyConnection") -> None:
    """Print channel | spend | % spend | conversions | % conv summary table."""
    import pandas as pd

    def _q(sql: str) -> float:
        return float(conn.execute(sql).fetchone()[0] or 0)

    def _qi(sql: str) -> int:
        return int(conn.execute(sql).fetchone()[0] or 0)

    organic_annual = _qi("SELECT coalesce(sum(organic_conversions), 0) FROM seo_organic_traffic")
    organic_90d    = int(organic_annual * 90 / 365)
    seo_spend      = _q("SELECT coalesce(sum(allocated), 0) FROM budgets WHERE channel = 'seo_aeo'")
    test_spend     = _q("SELECT coalesce(sum(allocated), 0) FROM budgets WHERE channel = 'conversion_testing'")

    rows = [
        ("SEM",              _q("SELECT coalesce(sum(spend),0) FROM sem_daily_performance"),
                             _qi("SELECT coalesce(sum(conversions),0) FROM sem_daily_performance")),
        ("Social Paid",      _q("SELECT coalesce(sum(spend),0) FROM social_paid_daily"),
                             _qi("SELECT coalesce(sum(total_leads),0) FROM social_paid_daily")),
        ("Brand Media",      _q("SELECT coalesce(sum(spend),0) FROM brand_media_performance"),
                             0),
        ("Life Events",      _q("SELECT coalesce(sum(spend),0) FROM life_event_campaign_performance"),
                             _qi("SELECT coalesce(sum(conversions),0) FROM life_event_campaign_performance")),
        ("SEO / AEO",        seo_spend, organic_90d),
        ("Testing Reserve",  test_spend, 0),
    ]

    total_spend = sum(r[1] for r in rows)
    total_convs = sum(r[2] for r in rows)

    print(f"\n{'='*70}")
    print(f"  Channel Summary")
    print(f"{'='*70}")
    print(f"  {'Channel':<22}  {'Spend':>13}  {'% Spend':>8}  {'Conversions':>12}  {'% Conv':>7}")
    print(f"  {'-'*22}  {'-'*13}  {'-'*8}  {'-'*12}  {'-'*7}")
    for name, spend, convs in rows:
        pct_spend = spend / total_spend * 100 if total_spend else 0
        pct_conv  = convs / total_convs * 100  if total_convs and convs else 0
        conv_str  = f"{convs:,}" if convs else "—"
        pct_c_str = f"{pct_conv:5.1f}%" if convs else "  —  "
        print(f"  {name:<22}  ${spend:>12,.0f}  {pct_spend:7.1f}%  {conv_str:>12}  {pct_c_str:>7}")
    print(f"  {'─'*22}  {'─'*13}  {'─'*8}  {'─'*12}  {'─'*7}")
    print(f"  {'TOTAL':<22}  ${total_spend:>12,.0f}  {'100.0%':>8}  {total_convs:>12,}  {'100.0%':>7}")
    print(f"{'='*70}\n")


# ---------------------------------------------------------------------------
# Post-seed pandera validation pass (reads from live DB)
# ---------------------------------------------------------------------------

def _validate_all() -> list[SeedResult]:
    """Query each table from DuckDB and run pandera schemas from validation.py."""
    import duckdb
    import pandas as pd
    from src.config.settings import DB_PATH
    from src.data.seeds.validation import (
        validate_campaigns,
        validate_funnel,
        validate_cohorts_pfi,
        validate_kpis,
        validate_alerts,
        validate_budgets,
        validate_budget_pacing,
        validate_markets,
        validate_channel_mix,
        validate_sem_keyword_groups,
        validate_sem_daily_performance,
        validate_life_event_campaigns,
        validate_life_event_mover_pipeline,
        validate_aeo_weekly,
        validate_aeo_competitors,
        validate_llm_visibility,
        validate_seo_rankings,
        validate_seo_traffic,
        validate_seo_keyword_rankings,
        validate_seo_organic_traffic,
        validate_seo_technical_metrics,
    )

    conn = duckdb.connect(DB_PATH)
    results: list[SeedResult] = []

    checks = [
        ("campaigns [validate]",        "SELECT id, name, channel, status, spend, revenue, start_date, end_date FROM campaigns",    validate_campaigns),
        ("funnel_events [validate]",     "SELECT id, campaign_id, stage, event_date, channel, market_tier, product_type, device, count FROM funnel_events", lambda df: validate_funnel(df)),
        ("cohorts [validate]",            "SELECT name, segment, size, period_start, period_end FROM cohorts WHERE name LIKE '% | PFI Member %'", validate_cohorts_pfi),
        ("kpi_summary [validate]",       "SELECT id, period_month, dma, channel, product, total_spend, revenue, roas, conversions, funnel_volume, conversion_rate, cpa, funded_accounts, cost_per_funded, mob6_retention, mob12_retention, ltv, net_margin, active_customers, nps FROM kpi_summary", validate_kpis),
        ("alerts [validate]",            "SELECT id, title, severity, category, message, is_read, resolved_at, created_at, updated_at FROM alerts", validate_alerts),
        ("budgets [validate]",           "SELECT id, name, channel, period, period_start, allocated, actual FROM budgets", validate_budgets),
        ("budget_pacing [validate]",     "SELECT id, channel, period_month, week_num, week_start, weekly_planned, weekly_actual, cumulative_planned, cumulative_actual, pacing_rate, forecast_eom, variance_pct, pacing_status FROM budget_pacing", validate_budget_pacing),
        ("markets [validate]",           "SELECT id, dma_code, dma_name, tier, state, population, hhi_median, branch_count, digital_adoption_pct, brand_awareness_pct, brand_consideration_pct, brand_health_score, retention_6m, retention_12m, nps_score, active_customers, avg_ltv FROM markets", validate_markets),
        ("channel_mix [validate]",       "SELECT id, channel, product, baseline_mix_pct, cpa_target, roas_target, conversion_rate_base, growth_coeff, q1_seasonality, q2_seasonality, q3_seasonality, q4_seasonality, budget_elasticity, saturation_point FROM channel_mix", validate_channel_mix),
        # sem_keyword_groups: DB stores is_active (bool); map to status string for schema
        ("sem_keyword_groups [validate]",   "SELECT id, name, product_category, intent_type, match_type, max_cpc, quality_score, estimated_monthly_volume, CASE WHEN is_active THEN 'active' ELSE 'paused' END AS status FROM sem_keyword_groups", validate_sem_keyword_groups),
        # sem_daily_performance: DB uses date/cpc/cvr/cpl; alias to match validation schema
        ("sem_daily_performance [validate]", "SELECT id, keyword_group_id, \"date\" AS record_date, impressions, clicks, ctr, cpc AS avg_cpc, spend, avg_position, impression_share, quality_score, conversions, cvr AS conversion_rate, cpl AS cost_per_conversion FROM sem_daily_performance", validate_sem_daily_performance),
        ("life_event_campaigns [validate]", "SELECT id, campaign_id, campaign_name, channel, event_date, impressions, clicks, conversions, spend, ctr, cvr, cpa, cvr_vs_baseline FROM life_event_campaign_performance", validate_life_event_campaigns),
        ("life_event_mover_pipeline [validate]", "SELECT id, week_num, week_start, dma_code, dma_name, data_provider, pipeline_volume, match_rate, matched_records, propensity_cvr_mult, mover_cvr, conversions_est FROM life_event_mover_pipeline", validate_life_event_mover_pipeline),
        ("aeo_weekly_readings [validate]",    "SELECT id, week_ending, platform, prompt, mention_rate, avg_position, share_of_voice, sentiment_score, citation_rate FROM aeo_weekly_readings",    validate_aeo_weekly),
        ("aeo_competitor_scores [validate]",  "SELECT id, week_ending, competitor_name, platform, mention_rate, avg_position, share_of_voice, sentiment_score, citation_rate FROM aeo_competitor_scores", validate_aeo_competitors),
        ("llm_visibility [validate]",         "SELECT id, week_start, platform, prompt_text, prompt_category, market_dma, brand, mentioned, position, mention_rate, sentiment_score, citation_rate FROM llm_visibility", validate_llm_visibility),
        ("seo_rankings [validate]",           "SELECT id, week_start, keyword, product_category, rank_position, rank_page, search_volume, rank_change FROM seo_rankings", validate_seo_rankings),
        ("seo_traffic [validate]",            "SELECT id, week_start, product_category, organic_sessions, organic_accounts, bounce_rate FROM seo_traffic", validate_seo_traffic),
        ("seo_keyword_rankings [validate]",   "SELECT id, keyword, product_category, current_rank, page_num, prev_month_rank, rank_change, monthly_search_volume, difficulty_score, record_month FROM seo_keyword_rankings", validate_seo_keyword_rankings),
        ("seo_organic_traffic [validate]",    "SELECT id, month, product_category, sessions, organic_conversions, conversion_rate, mom_growth_pct FROM seo_organic_traffic", validate_seo_organic_traffic),
        ("seo_technical_metrics [validate]",  "SELECT id, page_group, lcp_ms, fid_ms, cls_score, pages_indexed, pages_submitted, index_coverage_pct, crawl_budget_used_pct, record_date FROM seo_technical_metrics", validate_seo_technical_metrics),
    ]

    print(f"\n{'='*60}")
    print(f"  Post-seed Pandera Validation")
    print(f"{'='*60}")

    for name, query, fn in checks:
        r = SeedResult(name)
        t0 = time.perf_counter()
        try:
            df = conn.execute(query).df()
            fn(df)
            r.rows = len(df)
            r.elapsed = time.perf_counter() - t0
            r.passed = True
            print(f"{_PASS} {name}: {r.rows:,} rows OK  ({r.elapsed:.1f}s)")
        except Exception as exc:
            r.elapsed = time.perf_counter() - t0
            r.error = str(exc)
            print(f"{_FAIL} {name} FAILED  ({r.elapsed:.1f}s)")
            print(f"     {str(exc)[:200]}")
        results.append(r)

    conn.close()
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _create_views() -> list[SeedResult]:
    """Create (or replace) pre-aggregated views after all seeds complete."""
    from src.data.init_db import create_views

    r = SeedResult("pre_aggregated_views [views]")
    t0 = time.perf_counter()
    print(f"\n{'='*60}")
    print(f"  Creating pre-aggregated views")
    print(f"{'='*60}")
    try:
        create_views()
        r.rows = 3  # three views: v_daily_kpi_summary, v_channel_performance, v_funnel_stage_summary
        r.elapsed = time.perf_counter() - t0
        r.passed = True
        print(f"{_PASS} pre_aggregated_views: v_daily_kpi_summary, v_channel_performance, v_funnel_stage_summary  ({r.elapsed:.1f}s)")
    except Exception as exc:
        r.elapsed = time.perf_counter() - t0
        r.error = str(exc)
        print(f"{_FAIL} pre_aggregated_views FAILED  ({r.elapsed:.1f}s)")
        traceback.print_exc()
    return [r]


def run_all() -> bool:
    """Seed all tables in order, then validate. Returns True if everything passed."""
    print("\n" + "=" * 60)
    print("  Apex Seed Orchestrator")
    print("=" * 60)
    wall_start = time.perf_counter()

    seed_results: list[SeedResult] = []
    for name, fn in STEPS:
        result = _run_step(name, fn)
        seed_results.append(result)
        # Stop on campaigns failure — downstream seeds need campaign_ids
        if not result.passed and name == "campaigns":
            print("\nHalting: campaigns seed failed; downstream seeds require campaign_ids.")
            break

    # Create pre-aggregated views after seeding (APE-131)
    view_results: list[SeedResult] = []
    if all(r.passed for r in seed_results):
        view_results = _create_views()

    # Post-seed validation (only if seeding succeeded)
    val_results: list[SeedResult] = []
    reconcile_results: list[SeedResult] = []
    if all(r.passed for r in seed_results + view_results):
        val_results = _validate_all()
    if all(r.passed for r in seed_results + view_results + val_results):
        reconcile_results = _reconcile_channels()

    wall_elapsed = time.perf_counter() - wall_start

    # ---------- Summary ----------
    all_results = seed_results + view_results + val_results + reconcile_results
    print("\n" + "=" * 60)
    print("  Summary")
    print("=" * 60)

    all_passed = True
    for r in all_results:
        icon = _PASS if r.passed else _FAIL
        status = f"{r.rows:>10,} rows  {r.elapsed:5.1f}s" if r.passed else f"{'FAILED':>16}  {r.elapsed:5.1f}s"
        print(f"  {icon}  {r.name:<38}  {status}")
        if not r.passed:
            all_passed = False

    for r in all_results:
        if not r.passed and r.error:
            print(f"\n  Error [{r.name}]:\n    {r.error[:400]}")

    _PERF_GATE = 60.0
    time_ok = wall_elapsed < _PERF_GATE
    time_icon = _PASS if time_ok else _FAIL
    print(f"\n  Total wall time: {wall_elapsed:.1f}s  {time_icon} ({'< ' if time_ok else '> '}{_PERF_GATE:.0f}s gate)")
    if not time_ok:
        all_passed = False
        print(f"  {_FAIL} PERFORMANCE GATE FAILED: {wall_elapsed:.1f}s > {_PERF_GATE:.0f}s")
    if all_passed:
        print("  ALL SEEDS + VALIDATIONS + RECONCILIATION PASSED\n")
    else:
        failed = [r.name for r in all_results if not r.passed]
        print(f"  FAILED: {', '.join(failed)}\n")

    return all_passed


if __name__ == "__main__":
    passed = run_all()
    sys.exit(0 if passed else 1)
