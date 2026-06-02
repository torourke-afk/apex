"""Tests for Product & Experience data loaders (APE-112 / APE-20b).

Coverage:
  - load_product_pipeline: columns, row count, status filter, invalid status raises,
      on_track and is_overdue computed fields present and boolean
  - load_roadmap: columns, quarter filter, is_overdue computed field present
  - load_ab_tests: columns, status filter, invalid status raises,
      is_significant derived from p_value for running tests
  - load_testing_velocity: columns, weeks limit, invalid weeks raises
  - get_pipeline_summary: required keys, launched_count, on_track_count numeric
  - get_velocity_baseline: required keys, winner_rate_trend is float,
      empty result shape for unknown team

Strategy: monkeypatch `src.data.load_product.get_connection` to return an
in-memory DuckDB pre-loaded with controlled fixture rows.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import duckdb
import pandas as pd
import pytest

import src.data.load_product as loaders

# ---------------------------------------------------------------------------
# Fixture DDL
# ---------------------------------------------------------------------------

_DDL_INITIATIVES = """
CREATE TABLE IF NOT EXISTS product_initiatives (
    id                  VARCHAR PRIMARY KEY,
    title               VARCHAR NOT NULL,
    description         VARCHAR NOT NULL,
    status              VARCHAR NOT NULL,
    priority            VARCHAR NOT NULL,
    product_area        VARCHAR NOT NULL,
    owner               VARCHAR NOT NULL,
    target_launch_date  DATE NOT NULL,
    actual_launch_date  DATE,
    hypothesis          VARCHAR NOT NULL,
    success_metric      VARCHAR NOT NULL,
    baseline_value      DECIMAL(18,4) NOT NULL,
    target_value        DECIMAL(18,4) NOT NULL,
    actual_value        DECIMAL(18,4),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_DDL_ROADMAP = """
CREATE TABLE IF NOT EXISTS roadmap_items (
    id              VARCHAR PRIMARY KEY,
    initiative_id   VARCHAR NOT NULL,
    quarter         VARCHAR(7) NOT NULL,
    title           VARCHAR NOT NULL,
    status          VARCHAR NOT NULL,
    team            VARCHAR NOT NULL,
    effort_points   INTEGER NOT NULL,
    priority        VARCHAR NOT NULL,
    milestone       VARCHAR,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_DDL_ABTESTS = """
CREATE TABLE IF NOT EXISTS ab_tests (
    id                      VARCHAR PRIMARY KEY,
    test_name               VARCHAR NOT NULL,
    hypothesis              VARCHAR NOT NULL,
    product_area            VARCHAR NOT NULL,
    status                  VARCHAR NOT NULL,
    variant_count           INTEGER NOT NULL,
    start_date              DATE NOT NULL,
    end_date                DATE,
    sample_size             INTEGER NOT NULL DEFAULT 0,
    traffic_allocation_pct  DECIMAL(6,4) NOT NULL,
    primary_metric          VARCHAR NOT NULL,
    control_rate            DECIMAL(10,6) NOT NULL,
    treatment_rate          DECIMAL(10,6),
    lift_pct                DECIMAL(10,4),
    p_value                 DECIMAL(10,6),
    is_significant          BOOLEAN,
    winner                  VARCHAR,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_DDL_VELOCITY = """
CREATE TABLE IF NOT EXISTS testing_velocity (
    id                      VARCHAR PRIMARY KEY,
    week_start              DATE NOT NULL,
    team                    VARCHAR NOT NULL,
    tests_launched          INTEGER NOT NULL DEFAULT 0,
    tests_completed         INTEGER NOT NULL DEFAULT 0,
    tests_running           INTEGER NOT NULL DEFAULT 0,
    winner_rate             DECIMAL(6,4) NOT NULL,
    avg_test_duration_days  INTEGER NOT NULL DEFAULT 0,
    total_sample_size       INTEGER NOT NULL DEFAULT 0,
    created_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at              TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


def _make_conn() -> duckdb.DuckDBPyConnection:
    """Return an in-memory DuckDB with all product tables and fixture rows."""
    conn = duckdb.connect(":memory:")
    conn.execute(_DDL_INITIATIVES)
    conn.execute(_DDL_ROADMAP)
    conn.execute(_DDL_ABTESTS)
    conn.execute(_DDL_VELOCITY)

    # --- product_initiatives fixture ---
    conn.execute("""
        INSERT INTO product_initiatives VALUES
        -- launched, on-track (actual >= target)
        ('i-001', 'Digital Acct Opening v3', 'Redesign flow', 'launched', 'p0',
         'checking', 'Sarah Chen', '2026-02-01', '2026-02-14', 'Hypothesis A',
         'application_completion_rate', 0.4200, 0.5100, 0.5340,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        -- launched, NOT on-track (actual < target)
        ('i-002', 'Spend Analytics v2', 'Better cats', 'launched', 'p2',
         'digital_banking', 'Mia Foster', '2025-11-01', '2025-11-08', 'Hypothesis B',
         'cross_sell_click_rate', 0.0310, 0.0430, 0.0410,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        -- in_progress, not overdue (target future)
        ('i-003', 'Personalized Onboarding', 'Dynamic content', 'in_progress', 'p0',
         'digital_banking', 'Priya Nair', '2026-06-01', NULL, 'Hypothesis C',
         'pfi_30d_completion_rate', 0.5800, 0.6700, NULL,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        -- in_progress, overdue (target in past)
        ('i-004', 'Business Banking Beta', 'SMB dashboard', 'paused', 'p1',
         'business_banking', 'Carlos Reyes', '2026-04-01', NULL, 'Hypothesis D',
         'smb_nps_score', 32.0, 42.0, NULL,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        -- cancelled
        ('i-005', 'Cross-sell Modal', 'Sequenced prompts', 'cancelled', 'p2',
         'digital_banking', 'Noah Wright', '2026-03-15', NULL, 'Hypothesis E',
         'cross_sell_conversion_rate', 0.0220, 0.0300, NULL,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """)

    # --- roadmap_items fixture ---
    conn.execute("""
        INSERT INTO roadmap_items VALUES
        -- complete, Q1 (past) — not overdue
        ('r-001', 'i-001', '2026-Q1', 'Form Simplification', 'complete',
         'Product Engineering', 8, 'must_have', 'MVP',
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        -- in_flight, Q2 (current quarter, not past) — not overdue
        ('r-002', 'i-003', '2026-Q2', 'Segment Tagging', 'in_flight',
         'Data Platform', 5, 'must_have', 'Beta',
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        -- planned, Q1 (past) — IS overdue
        ('r-003', 'i-004', '2026-Q1', 'SMB Auth Flow', 'planned',
         'Product Engineering', 13, 'must_have', NULL,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """)

    # --- ab_tests fixture ---
    conn.execute("""
        INSERT INTO ab_tests VALUES
        -- complete, significant (p < 0.05, flag TRUE)
        ('a-001', 'DAOv3 Short Form', 'Shorter form reduces drop-off', 'checking',
         'complete', 2, '2026-01-15', '2026-02-14', 42000, 0.5000,
         'application_completion_rate', 0.420000, 0.512000, 0.2190, 0.001200,
         TRUE, 'treatment_a', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        -- complete, NOT significant (p >= 0.05)
        ('a-002', 'CC Hero Image Test', 'Lifestyle imagery outperforms', 'credit_card',
         'complete', 2, '2026-02-01', '2026-03-01', 18500, 0.5000,
         'apply_ctr', 0.031000, 0.033800, 0.0903, 0.041000,
         FALSE, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        -- running, no result yet (is_significant NULL — must derive from p_value=NULL)
        ('a-003', 'Onboarding Progress Bar', 'Steps reduce drop-off', 'digital_banking',
         'running', 2, '2026-04-01', NULL, 28000, 0.5000,
         'onboarding_completion_rate', 0.620000, NULL, NULL, NULL,
         NULL, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        -- running, interim p_value present (< 0.05) but flag NULL — derive significant
        ('a-004', 'Push Timing AM vs PM', 'Morning open rate lift', 'digital_banking',
         'running', 2, '2026-02-14', NULL, 55000, 0.5000,
         'notification_open_rate', 0.120000, NULL, NULL, 0.000300,
         NULL, NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """)

    # --- testing_velocity fixture ---
    conn.execute("""
        INSERT INTO testing_velocity VALUES
        ('v-001', '2026-02-09', 'Product Growth', 1, 0, 3, 0.0, 21, 12000,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('v-002', '2026-02-16', 'Product Growth', 2, 1, 4, 0.5, 19, 18400,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('v-003', '2026-02-23', 'Product Growth', 0, 1, 3, 1.0, 22, 14100,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('v-004', '2026-03-02', 'Product Growth', 1, 2, 2, 0.5, 20, 24800,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('v-005', '2026-03-09', 'Product Growth', 2, 1, 3, 0.0, 18, 21300,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('v-006', '2026-03-16', 'Product Growth', 1, 1, 3, 1.0, 21, 17600,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('v-007', '2026-03-23', 'Product Growth', 2, 2, 3, 1.0, 22, 31200,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('v-008', '2026-03-30', 'Product Growth', 1, 1, 4, 1.0, 20, 28500,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('v-009', '2026-04-06', 'Product Growth', 3, 2, 5, 0.5, 19, 42100,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('v-010', '2026-04-13', 'Product Growth', 1, 2, 4, 0.5, 21, 35700,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('v-011', '2026-04-20', 'Product Growth', 2, 1, 5, 1.0, 22, 29000,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP),
        ('v-012', '2026-04-27', 'Product Growth', 2, 2, 5, 0.5, 20, 38900,
         CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
    """)

    return conn


@pytest.fixture(autouse=True)
def mock_conn(monkeypatch):
    """Patch get_connection in the loaders module to use the in-memory fixture DB."""
    monkeypatch.setattr(loaders, "get_connection", _make_conn)


# ---------------------------------------------------------------------------
# load_product_pipeline
# ---------------------------------------------------------------------------

class TestLoadProductPipeline:
    def test_returns_dataframe(self):
        df = loaders.load_product_pipeline()
        assert isinstance(df, pd.DataFrame)

    def test_expected_row_count(self):
        df = loaders.load_product_pipeline()
        assert len(df) == 5

    def test_required_columns(self):
        df = loaders.load_product_pipeline()
        for col in ("id", "title", "status", "priority", "product_area",
                    "on_track", "is_overdue"):
            assert col in df.columns, f"Missing column: {col}"

    def test_on_track_is_bool(self):
        df = loaders.load_product_pipeline()
        assert df["on_track"].dtype == bool or df["on_track"].dtype == object
        # All values must be bool-like
        assert df["on_track"].isin([True, False]).all()

    def test_is_overdue_is_bool(self):
        df = loaders.load_product_pipeline()
        assert df["is_overdue"].isin([True, False]).all()

    def test_launched_on_track_logic(self):
        df = loaders.load_product_pipeline()
        # i-001: actual=0.534 >= target=0.51 → on_track True
        row_on = df[df["id"] == "i-001"].iloc[0]
        assert row_on["on_track"] is True or row_on["on_track"] == True  # noqa: E712
        # i-002: actual=0.041 < target=0.043 → on_track False
        row_off = df[df["id"] == "i-002"].iloc[0]
        assert row_off["on_track"] is False or row_off["on_track"] == False  # noqa: E712

    def test_overdue_logic(self):
        df = loaders.load_product_pipeline()
        # i-004: paused, target 2026-04-01 < today (2026-05-08) → overdue
        row = df[df["id"] == "i-004"].iloc[0]
        assert row["is_overdue"] is True or row["is_overdue"] == True  # noqa: E712
        # i-003: in_progress, target 2026-06-01 > today → not overdue
        row2 = df[df["id"] == "i-003"].iloc[0]
        assert row2["is_overdue"] is False or row2["is_overdue"] == False  # noqa: E712

    def test_status_filter(self):
        df = loaders.load_product_pipeline(status="launched")
        assert len(df) == 2
        assert (df["status"] == "launched").all()

    def test_product_area_filter(self):
        df = loaders.load_product_pipeline(product_area="checking")
        assert len(df) == 1
        assert df.iloc[0]["product_area"] == "checking"

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="status must be one of"):
            loaders.load_product_pipeline(status="bad_status")

    def test_invalid_priority_raises(self):
        with pytest.raises(ValueError, match="priority must be one of"):
            loaders.load_product_pipeline(priority="p9")


# ---------------------------------------------------------------------------
# load_roadmap
# ---------------------------------------------------------------------------

class TestLoadRoadmap:
    def test_returns_dataframe(self):
        df = loaders.load_roadmap()
        assert isinstance(df, pd.DataFrame)

    def test_required_columns(self):
        df = loaders.load_roadmap()
        for col in ("id", "initiative_id", "initiative_title", "quarter",
                    "status", "team", "effort_points", "is_overdue"):
            assert col in df.columns, f"Missing column: {col}"

    def test_quarter_filter(self):
        df = loaders.load_roadmap(quarter="2026-Q2")
        assert len(df) == 1
        assert (df["quarter"] == "2026-Q2").all()

    def test_is_overdue_logic(self):
        df = loaders.load_roadmap()
        # r-003: planned in 2026-Q1 (ended 2026-03-31) → overdue
        overdue = df[df["id"] == "r-003"].iloc[0]
        assert overdue["is_overdue"] is True or overdue["is_overdue"] == True  # noqa: E712
        # r-001: complete — not overdue even though Q1 is past
        complete = df[df["id"] == "r-001"].iloc[0]
        assert complete["is_overdue"] is False or complete["is_overdue"] == False  # noqa: E712

    def test_initiative_title_joined(self):
        df = loaders.load_roadmap()
        assert df["initiative_title"].notna().any()

    def test_status_filter(self):
        df = loaders.load_roadmap(status="complete")
        assert len(df) == 1
        assert df.iloc[0]["status"] == "complete"

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="status must be one of"):
            loaders.load_roadmap(status="not_a_status")


# ---------------------------------------------------------------------------
# load_ab_tests
# ---------------------------------------------------------------------------

class TestLoadABTests:
    def test_returns_dataframe(self):
        df = loaders.load_ab_tests()
        assert isinstance(df, pd.DataFrame)

    def test_required_columns(self):
        df = loaders.load_ab_tests()
        for col in ("id", "test_name", "status", "is_significant",
                    "control_rate", "p_value"):
            assert col in df.columns, f"Missing column: {col}"

    def test_is_significant_bool(self):
        df = loaders.load_ab_tests()
        assert df["is_significant"].isin([True, False]).all()

    def test_is_significant_from_flag(self):
        df = loaders.load_ab_tests()
        # a-001: flag TRUE → significant
        assert df[df["id"] == "a-001"].iloc[0]["is_significant"] == True  # noqa: E712
        # a-002: flag FALSE → not significant
        assert df[df["id"] == "a-002"].iloc[0]["is_significant"] == False  # noqa: E712

    def test_is_significant_derived_from_p_value(self):
        df = loaders.load_ab_tests()
        # a-004: flag NULL but p_value=0.0003 < 0.05 → derived significant
        assert df[df["id"] == "a-004"].iloc[0]["is_significant"] == True  # noqa: E712
        # a-003: flag NULL and p_value=NULL → not significant
        assert df[df["id"] == "a-003"].iloc[0]["is_significant"] == False  # noqa: E712

    def test_status_filter(self):
        df = loaders.load_ab_tests(status="running")
        assert len(df) == 2
        assert (df["status"] == "running").all()

    def test_product_area_filter(self):
        df = loaders.load_ab_tests(product_area="checking")
        assert len(df) == 1

    def test_invalid_status_raises(self):
        with pytest.raises(ValueError, match="status must be one of"):
            loaders.load_ab_tests(status="invalid")


# ---------------------------------------------------------------------------
# load_testing_velocity
# ---------------------------------------------------------------------------

class TestLoadTestingVelocity:
    def test_returns_dataframe(self):
        df = loaders.load_testing_velocity()
        assert isinstance(df, pd.DataFrame)

    def test_all_12_rows(self):
        df = loaders.load_testing_velocity()
        assert len(df) == 12

    def test_weeks_limit(self):
        df = loaders.load_testing_velocity(weeks=4)
        assert len(df) == 4

    def test_team_filter(self):
        df = loaders.load_testing_velocity(team="Product Growth")
        assert len(df) == 12

    def test_team_filter_no_match(self):
        df = loaders.load_testing_velocity(team="Nonexistent Team")
        assert len(df) == 0

    def test_invalid_weeks_raises(self):
        with pytest.raises(ValueError, match="weeks must be a positive integer"):
            loaders.load_testing_velocity(weeks=0)

    def test_required_columns(self):
        df = loaders.load_testing_velocity()
        for col in ("id", "week_start", "team", "tests_launched", "tests_completed",
                    "tests_running", "winner_rate", "avg_test_duration_days",
                    "total_sample_size"):
            assert col in df.columns, f"Missing column: {col}"

    def test_most_recent_first(self):
        df = loaders.load_testing_velocity()
        dates = pd.to_datetime(df["week_start"])
        assert dates.is_monotonic_decreasing


# ---------------------------------------------------------------------------
# get_pipeline_summary
# ---------------------------------------------------------------------------

class TestGetPipelineSummary:
    def test_returns_dict(self):
        result = loaders.get_pipeline_summary()
        assert isinstance(result, dict)

    def test_required_keys(self):
        result = loaders.get_pipeline_summary()
        for key in ("total_initiatives", "by_status", "by_priority",
                    "by_product_area", "launched_count", "on_track_count",
                    "overdue_count", "avg_target_value", "avg_actual_value",
                    "total_effort_points", "roadmap_by_status",
                    "ab_tests_running", "ab_tests_significant"):
            assert key in result, f"Missing key: {key}"

    def test_launched_count(self):
        result = loaders.get_pipeline_summary()
        assert result["launched_count"] == 2

    def test_on_track_count_positive(self):
        result = loaders.get_pipeline_summary()
        # i-001 is launched + on_track; i-003 is in_progress + future target
        assert result["on_track_count"] >= 1

    def test_overdue_count(self):
        result = loaders.get_pipeline_summary()
        # i-004 (paused, target past) is overdue
        assert result["overdue_count"] >= 1

    def test_total_effort_points_positive(self):
        result = loaders.get_pipeline_summary()
        assert result["total_effort_points"] == 8 + 5 + 13

    def test_ab_tests_running(self):
        result = loaders.get_pipeline_summary()
        assert result["ab_tests_running"] == 2

    def test_ab_tests_significant(self):
        result = loaders.get_pipeline_summary()
        # a-001 is complete + significant; a-002 is complete + not significant
        assert result["ab_tests_significant"] == 1


# ---------------------------------------------------------------------------
# get_velocity_baseline
# ---------------------------------------------------------------------------

class TestGetVelocityBaseline:
    def test_returns_dict(self):
        result = loaders.get_velocity_baseline()
        assert isinstance(result, dict)

    def test_required_keys(self):
        result = loaders.get_velocity_baseline()
        for key in ("team", "weeks_included", "avg_tests_launched",
                    "avg_tests_completed", "avg_tests_running", "avg_winner_rate",
                    "avg_test_duration_days", "avg_total_sample_size",
                    "total_tests_launched", "total_tests_completed",
                    "winner_rate_trend"):
            assert key in result, f"Missing key: {key}"

    def test_weeks_included_12(self):
        result = loaders.get_velocity_baseline()
        assert result["weeks_included"] == 12

    def test_weeks_limit(self):
        result = loaders.get_velocity_baseline(weeks=4)
        assert result["weeks_included"] == 4

    def test_winner_rate_trend_is_float(self):
        result = loaders.get_velocity_baseline()
        assert isinstance(result["winner_rate_trend"], float)

    def test_total_tests_launched(self):
        result = loaders.get_velocity_baseline()
        # sum from fixture: 1+2+0+1+2+1+2+1+3+1+2+2 = 18
        assert result["total_tests_launched"] == 18

    def test_empty_result_for_unknown_team(self):
        result = loaders.get_velocity_baseline(team="Ghost Team")
        assert result["weeks_included"] == 0
        assert result["avg_tests_launched"] == 0.0
        assert result["winner_rate_trend"] == 0.0

    def test_team_scoped_baseline(self):
        result = loaders.get_velocity_baseline(team="Product Growth")
        assert result["weeks_included"] == 12
