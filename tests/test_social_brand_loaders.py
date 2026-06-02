"""Tests for Social & Brand Media data loaders (APE-81).

Fixtures create an isolated in-memory / temp-file DuckDB seeded with the
build_* functions from seed_social_brand.py, then monkeypatch get_connection
in the loaders module so each test queries reproducible data.

Coverage target: 7 loaders × at least 3 tests each = 21+ tests.
"""

from __future__ import annotations

import duckdb
import pandas as pd
import pytest

import src.data.social_brand_loaders as loaders_mod
from src.data.seeds.seed_social_brand import (
    BEI_WEIGHTS,
    GEOS,
    LIFE_EVENTS,
    _insert,
    build_brand_market_bei,
    build_life_event_campaigns,
    build_mover_marketing,
    build_social_creatives,
    build_social_platform_metrics,
)

# ---------------------------------------------------------------------------
# Module-scoped fixture: isolated seeded DuckDB
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def _db_path(tmp_path_factory):
    """Create a temp-file DuckDB seeded with all social & brand tables."""
    from src.data import init_db as _init_mod

    db_file = str(tmp_path_factory.mktemp("apex") / "test.duckdb")
    conn = duckdb.connect(db_file)

    # Create all tables using the production DDL (idempotent)
    for stmt in _init_mod._DDL:
        conn.execute(stmt)

    # --- social_platform_metrics ---
    df = build_social_platform_metrics()
    for col in ("spend", "cpl", "cvr_native", "cvr_landing", "cpa_ai", "cpa_manual"):
        df[col] = df[col].astype(float)
    _insert(conn, "social_platform_metrics", df, [
        "id", "platform", "period", "spend", "impressions", "clicks",
        "leads", "cpl", "cvr_native", "cvr_landing", "cpa_ai", "cpa_manual",
        "first_party_audiences", "created_at", "updated_at",
    ])

    # --- social_creatives ---
    df = build_social_creatives()
    for col in ("ctr", "cvr", "spend"):
        df[col] = df[col].astype(float)
    _insert(conn, "social_creatives", df, [
        "id", "creative_id", "platform", "name", "format",
        "ctr", "cvr", "spend", "impressions", "is_underperformer",
        "created_at", "updated_at",
    ])

    # --- brand_market_bei ---
    df = build_brand_market_bei()
    for col in (
        "awareness_score", "branded_search_score", "direct_traffic_score",
        "branch_visits_score", "social_engagement_score", "bei_score",
        "frequency_compliance", "ctv_completion_rate",
        "olv_completion_rate", "audio_listen_through_rate",
    ):
        df[col] = df[col].astype(float)
    _insert(conn, "brand_market_bei", df, [
        "id", "market_name", "market_tier", "week_ending",
        "awareness_score", "branded_search_score", "direct_traffic_score",
        "branch_visits_score", "social_engagement_score", "bei_score",
        "frequency_compliance", "ctv_completion_rate", "olv_completion_rate",
        "audio_listen_through_rate", "is_active_market", "incrementality_lift",
        "created_at", "updated_at",
    ])

    # --- life_event_campaigns ---
    df = build_life_event_campaigns()
    for col in ("cvr", "mass_market_cvr", "cvr_multiplier"):
        df[col] = df[col].astype(float)
    _insert(conn, "life_event_campaigns", df, [
        "id", "event_type", "period", "status", "cvr", "mass_market_cvr",
        "cvr_multiplier", "segment_size", "segment_parameters",
        "created_at", "updated_at",
    ])

    # --- mover_marketing ---
    df = build_mover_marketing()
    for col in (
        "pipeline_quality_score", "mover_to_account_cvr",
        "propensity_benchmark", "high_income_subset_cvr",
    ):
        df[col] = df[col].astype(float)
    _insert(conn, "mover_marketing", df, [
        "id", "geo", "period", "pipeline_volume", "pipeline_quality_score",
        "mover_to_account_cvr", "propensity_benchmark", "is_expansion_geo",
        "high_income_subset_cvr", "high_income_subset_volume",
        "created_at", "updated_at",
    ])

    conn.commit()
    conn.close()
    return db_file


@pytest.fixture
def db(monkeypatch, _db_path):
    """Patch loaders.get_connection to use the isolated test database."""
    monkeypatch.setattr(loaders_mod, "get_connection", lambda: duckdb.connect(_db_path))


# ---------------------------------------------------------------------------
# load_social_overview
# ---------------------------------------------------------------------------


class TestLoadSocialOverview:
    def test_returns_dict(self, db):
        assert isinstance(loaders_mod.load_social_overview(), dict)

    def test_has_all_required_keys(self, db):
        result = loaders_mod.load_social_overview()
        expected = {
            "total_spend",
            "total_leads",
            "blended_cpl",
            "blended_cvr",
            "ai_vs_manual_cpa_delta",
            "active_first_party_audience_count",
            "alert_flags",
        }
        assert set(result.keys()) == expected

    def test_positive_spend_and_leads(self, db):
        result = loaders_mod.load_social_overview()
        assert result["total_spend"] > 0
        assert result["total_leads"] > 0

    def test_blended_cvr_is_fraction(self, db):
        result = loaders_mod.load_social_overview()
        assert 0 < result["blended_cvr"] < 1

    def test_alert_flags_is_list(self, db):
        result = loaders_mod.load_social_overview()
        assert isinstance(result["alert_flags"], list)

    def test_cpl_alert_fires_when_benchmark_very_low(self, db, monkeypatch):
        """Setting benchmark to $0.01 forces a CPL alert."""
        monkeypatch.setattr(loaders_mod, "_SEM_CPL_BENCHMARK", 0.01)
        result = loaders_mod.load_social_overview()
        assert any("CPL" in flag for flag in result["alert_flags"])

    def test_cvr_alert_fires_when_threshold_impossibly_high(self, db, monkeypatch):
        """Setting CVR threshold to 999 forces a CVR alert."""
        monkeypatch.setattr(loaders_mod, "_CVR_ALERT_THRESHOLD", 999.0)
        result = loaders_mod.load_social_overview()
        assert any("CVR" in flag for flag in result["alert_flags"])


# ---------------------------------------------------------------------------
# load_social_platforms
# ---------------------------------------------------------------------------


class TestLoadSocialPlatforms:
    _EXPECTED_COLS = frozenset(
        {"platform", "spend", "spend_pct", "leads", "cpl", "cvr_native", "cvr_landing", "volume"}
    )

    def test_returns_dataframe(self, db):
        assert isinstance(loaders_mod.load_social_platforms(), pd.DataFrame)

    def test_expected_columns(self, db):
        df = loaders_mod.load_social_platforms()
        assert set(df.columns) == self._EXPECTED_COLS

    def test_four_platforms_returned(self, db):
        df = loaders_mod.load_social_platforms()
        assert len(df) == 4

    def test_spend_pct_sums_to_one(self, db):
        df = loaders_mod.load_social_platforms()
        assert abs(df["spend_pct"].sum() - 1.0) < 1e-4

    def test_period_filter_returns_rows(self, db):
        df_filtered = loaders_mod.load_social_platforms(period="2025-05-05")
        assert len(df_filtered) > 0
        assert len(df_filtered) <= 4  # at most one row per platform


# ---------------------------------------------------------------------------
# load_social_creatives
# ---------------------------------------------------------------------------


class TestLoadSocialCreatives:
    _EXPECTED_COLS = frozenset(
        {
            "creative_id", "platform", "name", "format",
            "ctr", "cvr", "spend", "impressions", "is_underperformer",
        }
    )

    def test_returns_dataframe(self, db):
        assert isinstance(loaders_mod.load_social_creatives(), pd.DataFrame)

    def test_expected_columns(self, db):
        df = loaders_mod.load_social_creatives()
        assert set(df.columns) == self._EXPECTED_COLS

    def test_default_sort_ctr_descending(self, db):
        df = loaders_mod.load_social_creatives()
        assert df["ctr"].iloc[0] >= df["ctr"].iloc[-1]

    def test_sort_by_spend_ascending(self, db):
        df = loaders_mod.load_social_creatives(sort_by="spend", ascending=True)
        assert df["spend"].is_monotonic_increasing

    def test_sort_by_cvr_descending(self, db):
        df = loaders_mod.load_social_creatives(sort_by="cvr", ascending=False)
        assert df["cvr"].iloc[0] >= df["cvr"].iloc[-1]

    def test_invalid_sort_raises_value_error(self, db):
        with pytest.raises(ValueError, match="sort_by"):
            loaders_mod.load_social_creatives(sort_by="impressions")

    def test_underperformer_flag_is_bool_dtype(self, db):
        df = loaders_mod.load_social_creatives()
        assert df["is_underperformer"].dtype == bool

    def test_some_creatives_flagged_as_underperformers(self, db):
        df = loaders_mod.load_social_creatives()
        assert df["is_underperformer"].any()


# ---------------------------------------------------------------------------
# load_brand_bei
# ---------------------------------------------------------------------------


class TestLoadBrandBei:
    _BEI_COMPONENT_COLS = frozenset(
        {
            "awareness_score", "branded_search_score", "direct_traffic_score",
            "branch_visits_score", "social_engagement_score",
        }
    )

    def test_returns_dataframe(self, db):
        assert isinstance(loaders_mod.load_brand_bei(), pd.DataFrame)

    def test_has_all_bei_component_columns(self, db):
        df = loaders_mod.load_brand_bei()
        assert self._BEI_COMPONENT_COLS.issubset(df.columns)

    def test_has_bei_trend_slope_column(self, db):
        df = loaders_mod.load_brand_bei()
        assert "bei_trend_slope" in df.columns

    def test_total_rows_15_markets_x_12_weeks(self, db):
        df = loaders_mod.load_brand_bei()
        assert len(df) == 180  # 15 markets × 12 weeks

    def test_tier_filter_restricts_to_tier(self, db):
        df = loaders_mod.load_brand_bei(market_tier="Tier1")
        assert len(df) > 0
        assert (df["market_tier"] == "Tier1").all()

    def test_tier_filter_reduces_row_count(self, db):
        df_all = loaders_mod.load_brand_bei()
        df_t2 = loaders_mod.load_brand_bei(market_tier="Tier2")
        assert len(df_t2) < len(df_all)

    def test_invalid_tier_raises_value_error(self, db):
        with pytest.raises(ValueError, match="market_tier"):
            loaders_mod.load_brand_bei(market_tier="TierX")

    def test_bei_composite_matches_seed_formula(self, db):
        """Verify stored bei_score ≈ 0.25×A + 0.25×BS + 0.20×DT + 0.20×BV + 0.10×SE."""
        df = loaders_mod.load_brand_bei()
        # Cast to float — DuckDB may return Decimal objects for DECIMAL columns
        score_cols = [
            "awareness_score", "branded_search_score", "direct_traffic_score",
            "branch_visits_score", "social_engagement_score", "bei_score",
        ]
        for col in score_cols:
            df[col] = df[col].astype(float)

        computed = (
            df["awareness_score"]           * BEI_WEIGHTS["awareness_score"]
            + df["branded_search_score"]    * BEI_WEIGHTS["branded_search_score"]
            + df["direct_traffic_score"]    * BEI_WEIGHTS["direct_traffic_score"]
            + df["branch_visits_score"]     * BEI_WEIGHTS["branch_visits_score"]
            + df["social_engagement_score"] * BEI_WEIGHTS["social_engagement_score"]
        )
        # Allow ±0.05 for intermediate rounding in the seed
        assert ((computed - df["bei_score"]).abs() < 0.05).all()


# ---------------------------------------------------------------------------
# load_brand_frequency
# ---------------------------------------------------------------------------


class TestLoadBrandFrequency:
    def test_returns_dict(self, db):
        assert isinstance(loaders_mod.load_brand_frequency(), dict)

    def test_has_required_keys(self, db):
        result = loaders_mod.load_brand_frequency()
        assert set(result.keys()) == {
            "pct_at_threshold", "ctv_completion", "olv_completion", "audio_listen_through"
        }

    def test_all_values_in_0_1_range(self, db):
        result = loaders_mod.load_brand_frequency()
        for key, val in result.items():
            assert 0.0 <= val <= 1.0, f"{key}={val} out of [0, 1]"


# ---------------------------------------------------------------------------
# load_life_events
# ---------------------------------------------------------------------------


class TestLoadLifeEvents:
    _EXPECTED_COLS = frozenset(
        {"event_type", "status", "cvr", "mass_market_cvr", "cvr_multiplier", "segment_size"}
    )

    def test_returns_dataframe(self, db):
        assert isinstance(loaders_mod.load_life_events(), pd.DataFrame)

    def test_expected_columns(self, db):
        df = loaders_mod.load_life_events()
        assert set(df.columns) == self._EXPECTED_COLS

    def test_exactly_eight_event_types(self, db):
        df = loaders_mod.load_life_events()
        assert len(df) == 8
        assert set(df["event_type"]) == set(LIFE_EVENTS)

    def test_cvr_multiplier_exceeds_one(self, db):
        """Life-event CVR must exceed mass-market CVR (multiplier > 1)."""
        df = loaders_mod.load_life_events()
        assert (df["cvr_multiplier"] > 1.0).all()

    def test_segment_size_positive(self, db):
        df = loaders_mod.load_life_events()
        assert (df["segment_size"] > 0).all()


# ---------------------------------------------------------------------------
# load_movers
# ---------------------------------------------------------------------------


class TestLoadMovers:
    _EXPECTED_COLS = frozenset(
        {
            "geo", "period", "pipeline_volume", "pipeline_quality_score",
            "mover_to_account_cvr", "propensity_benchmark", "is_expansion_geo",
            "high_income_subset_cvr", "high_income_subset_volume",
        }
    )

    def test_returns_dataframe(self, db):
        assert isinstance(loaders_mod.load_movers(), pd.DataFrame)

    def test_expected_columns(self, db):
        df = loaders_mod.load_movers()
        assert set(df.columns) == self._EXPECTED_COLS

    def test_all_geos_present(self, db):
        df = loaders_mod.load_movers()
        assert set(df["geo"]) == set(GEOS)

    def test_geo_filter_restricts_rows(self, db):
        df_filtered = loaders_mod.load_movers(geo="Charlotte, NC")
        assert len(df_filtered) > 0
        assert (df_filtered["geo"] == "Charlotte, NC").all()

    def test_geo_filter_fewer_rows_than_unfiltered(self, db):
        df_all = loaders_mod.load_movers()
        df_one = loaders_mod.load_movers(geo="Atlanta, GA")
        assert len(df_one) < len(df_all)

    def test_is_expansion_geo_is_bool_dtype(self, db):
        df = loaders_mod.load_movers()
        assert df["is_expansion_geo"].dtype == bool

    def test_pipeline_volume_positive(self, db):
        df = loaders_mod.load_movers()
        assert (df["pipeline_volume"] > 0).all()
