"""Tests for SEM data loaders (APE-89).

Coverage:
  - load_sem_overview: keys present, avg_cpc float, vbb_margin_trend float,
      date_range filtering reduces total_spend
  - load_sem_keywords: unfiltered shape, intent_type filter, invalid sort_by raises,
      invalid intent_type raises, date_range filtering
  - load_sem_trends: metric param, group_by day vs week, invalid metric raises,
      date_range filtering returns subset
  - load_sem_match_types: columns present, spend_pct sums to 1, date_range filter
  - load_sem_market_segments: benchmark columns present, date_range filter
  - load_sem_campaign_types: benchmark columns, budget_share mapped, date_range filter
  - load_sem_negative_keyword_score: returns dict, keys present, date_range filter,
      empty result structure, high qs_threshold returns all groups

Strategy: monkeypatch `src.data.sem_loaders.get_connection` to return an
in-memory DuckDB pre-loaded with controlled fixture rows.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import duckdb
import pandas as pd
import pytest

import src.data.sem_loaders as loaders

# ---------------------------------------------------------------------------
# Fixture DDL & data
# ---------------------------------------------------------------------------

_DDL_GROUPS = """
CREATE TABLE IF NOT EXISTS sem_keyword_groups (
    id               VARCHAR PRIMARY KEY,
    name             VARCHAR NOT NULL,
    product_category VARCHAR NOT NULL,
    intent_type      VARCHAR NOT NULL,
    match_type       VARCHAR NOT NULL,
    max_cpc          DECIMAL(10,2) NOT NULL,
    quality_score    INTEGER NOT NULL,
    estimated_monthly_volume INTEGER NOT NULL,
    market_segment   VARCHAR NOT NULL,
    is_active        BOOLEAN NOT NULL DEFAULT TRUE,
    dma              VARCHAR,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP
)
"""

_DDL_PERF = """
CREATE TABLE IF NOT EXISTS sem_daily_performance (
    id               VARCHAR PRIMARY KEY,
    keyword_group_id VARCHAR NOT NULL,
    "date"           DATE NOT NULL,
    impressions      INTEGER NOT NULL,
    clicks           INTEGER NOT NULL,
    ctr              DECIMAL(10,6) NOT NULL,
    cpc              DECIMAL(10,4) NOT NULL,
    spend            DECIMAL(18,4) NOT NULL,
    avg_position     DECIMAL(5,2) NOT NULL,
    impression_share DECIMAL(8,4) NOT NULL,
    quality_score    INTEGER NOT NULL,
    conversions      INTEGER NOT NULL,
    cvr              DECIMAL(10,6) NOT NULL,
    cpl              DECIMAL(18,4) NOT NULL,
    vbb_margin_signal DECIMAL(8,6) NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

# 3 keyword groups: 2 branded, 1 non_branded
_GROUPS = [
    ("kg1", "Fifth Third Checking – Branded", "checking", "branded",   "exact",  1.25, 8, 50000, "established", True,  None),
    ("kg2", "Fifth Third Mortgage – Branded", "mortgage",  "branded",   "phrase", 1.00, 7, 30000, "growth",      True,  None),
    ("kg3", "Checking Account Rates",         "checking", "non_branded","broad",  3.50, 5, 20000, "new",         True,  None),
]

# Performance rows: 4 days × 3 groups = 12 rows
# Two date bands for filter tests: early (Jan) and late (Feb)
_PERF = [
    # kg1 — high QS / established
    ("p1",  "kg1", date(2026,1,5),  10000, 1200, 0.12, 1.10, 1320.0, 1.5, 0.88, 8, 36,  0.030, 36.67, 0.72),
    ("p2",  "kg1", date(2026,1,12), 10500, 1260, 0.12, 1.12, 1411.2, 1.5, 0.87, 8, 38,  0.030, 37.14, 0.73),
    ("p3",  "kg1", date(2026,2,2),  11000, 1320, 0.12, 1.15, 1518.0, 1.4, 0.89, 8, 40,  0.030, 37.95, 0.74),
    ("p4",  "kg1", date(2026,2,9),  11500, 1380, 0.12, 1.18, 1628.4, 1.4, 0.90, 8, 41,  0.030, 39.72, 0.75),
    # kg2 — medium QS / growth
    ("p5",  "kg2", date(2026,1,5),   8000,  640, 0.08, 1.00,  640.0, 2.0, 0.70, 7, 13,  0.020, 49.23, 0.55),
    ("p6",  "kg2", date(2026,1,12),  8200,  656, 0.08, 1.01,  662.6, 2.0, 0.71, 7, 13,  0.020, 50.97, 0.56),
    ("p7",  "kg2", date(2026,2,2),   8400,  672, 0.08, 1.02,  685.4, 1.9, 0.72, 7, 14,  0.021, 48.96, 0.57),
    ("p8",  "kg2", date(2026,2,9),   8600,  688, 0.08, 1.03,  708.6, 1.9, 0.73, 7, 14,  0.020, 50.61, 0.58),
    # kg3 — low QS / new (negative keyword candidate)
    ("p9",  "kg3", date(2026,1,5),   5000,  150, 0.03, 3.20,  480.0, 3.5, 0.40, 5,  3,  0.020,160.00, 0.30),
    ("p10", "kg3", date(2026,1,12),  5200,  156, 0.03, 3.25,  507.0, 3.5, 0.41, 5,  3,  0.019,169.00, 0.31),
    ("p11", "kg3", date(2026,2,2),   5400,  162, 0.03, 3.30,  534.6, 3.4, 0.42, 5,  3,  0.019,178.20, 0.32),
    ("p12", "kg3", date(2026,2,9),   5600,  168, 0.03, 3.35,  562.8, 3.4, 0.43, 5,  4,  0.024,140.70, 0.33),
]


class _NoCloseConn:
    """Wraps a DuckDB connection and makes close() a no-op.

    Production loaders call conn.close() in their finally blocks.  When tests
    monkeypatch get_connection to return a shared in-memory connection, that
    first close() destroys the fixture for all subsequent calls in the same
    test.  This wrapper prevents that without changing production code.
    """

    def __init__(self, conn: duckdb.DuckDBPyConnection) -> None:
        self._conn = conn

    def execute(self, *args, **kwargs):
        return self._conn.execute(*args, **kwargs)

    def executemany(self, *args, **kwargs):
        return self._conn.executemany(*args, **kwargs)

    def commit(self):
        pass

    def close(self):
        pass  # intentionally suppressed in test context


def _make_conn() -> _NoCloseConn:
    conn = duckdb.connect(":memory:")
    conn.execute(_DDL_GROUPS)
    conn.execute(_DDL_PERF)
    conn.executemany(
        "INSERT INTO sem_keyword_groups VALUES (?,?,?,?,?,?,?,?,?,?,?,NOW(),NULL)",
        _GROUPS,
    )
    conn.executemany(
        "INSERT INTO sem_daily_performance VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NOW())",
        _PERF,
    )
    return _NoCloseConn(conn)


@pytest.fixture
def mock_conn(monkeypatch):
    conn = _make_conn()
    monkeypatch.setattr(loaders, "get_connection", lambda: conn)
    yield conn


# ---------------------------------------------------------------------------
# load_sem_overview
# ---------------------------------------------------------------------------


class TestLoadSemOverview:

    def test_required_keys_present(self, mock_conn):
        result = loaders.load_sem_overview()
        expected_keys = {
            "total_spend", "total_clicks", "total_impressions", "total_conversions",
            "blended_ctr", "blended_cvr", "blended_cpl",
            "avg_quality_score", "avg_impression_share", "avg_vbb_margin_signal",
            "avg_cpc", "vbb_margin_trend",
            "active_keyword_groups", "alert_flags",
        }
        assert expected_keys.issubset(result.keys())

    def test_avg_cpc_is_float(self, mock_conn):
        result = loaders.load_sem_overview()
        assert isinstance(result["avg_cpc"], float)
        assert result["avg_cpc"] > 0

    def test_vbb_margin_trend_is_float(self, mock_conn):
        result = loaders.load_sem_overview()
        assert isinstance(result["vbb_margin_trend"], float)

    def test_alert_flags_is_list(self, mock_conn):
        result = loaders.load_sem_overview()
        assert isinstance(result["alert_flags"], list)

    def test_date_range_reduces_spend(self, mock_conn):
        full = loaders.load_sem_overview()
        jan_only = loaders.load_sem_overview(date_range=(date(2026,1,1), date(2026,1,31)))
        assert jan_only["total_spend"] < full["total_spend"]

    def test_total_clicks_integer(self, mock_conn):
        result = loaders.load_sem_overview()
        assert isinstance(result["total_clicks"], int)

    def test_active_keyword_groups_count(self, mock_conn):
        result = loaders.load_sem_overview()
        assert result["active_keyword_groups"] == 3


# ---------------------------------------------------------------------------
# load_sem_keywords
# ---------------------------------------------------------------------------


class TestLoadSemKeywords:

    def test_returns_all_groups_unfiltered(self, mock_conn):
        df = loaders.load_sem_keywords()
        assert len(df) == 3

    def test_filter_by_intent_type_branded(self, mock_conn):
        df = loaders.load_sem_keywords(intent_type="branded")
        assert len(df) == 2
        assert (df["intent_type"] == "branded").all()

    def test_filter_by_product_category(self, mock_conn):
        df = loaders.load_sem_keywords(product_category="checking")
        assert len(df) == 2
        assert (df["product_category"] == "checking").all()

    def test_date_range_filtering(self, mock_conn):
        jan = loaders.load_sem_keywords(date_range=(date(2026,1,1), date(2026,1,31)))
        feb = loaders.load_sem_keywords(date_range=(date(2026,2,1), date(2026,2,28)))
        assert jan.iloc[0]["spend"] != feb.iloc[0]["spend"]

    def test_invalid_sort_by_raises(self, mock_conn):
        with pytest.raises(ValueError, match="sort_by must be one of"):
            loaders.load_sem_keywords(sort_by="invalid_col")

    def test_invalid_intent_type_raises(self, mock_conn):
        with pytest.raises(ValueError, match="intent_type must be one of"):
            loaders.load_sem_keywords(intent_type="competitor")

    def test_limit_respected(self, mock_conn):
        df = loaders.load_sem_keywords(limit=1)
        assert len(df) == 1

    def test_required_columns_present(self, mock_conn):
        df = loaders.load_sem_keywords()
        required = {"keyword_group_id", "name", "spend", "ctr", "cvr", "cpl",
                    "avg_quality_score", "avg_vbb_margin_signal"}
        assert required.issubset(set(df.columns))

    def test_spend_is_float(self, mock_conn):
        df = loaders.load_sem_keywords()
        assert df["spend"].dtype == float


# ---------------------------------------------------------------------------
# load_sem_trends
# ---------------------------------------------------------------------------


class TestLoadSemTrends:

    def test_default_metric_spend_weekly(self, mock_conn):
        df = loaders.load_sem_trends()
        assert list(df.columns) == ["period", "value"]
        assert df["value"].dtype == float
        # 4 dates in 3 distinct ISO weeks (Jan 5, Jan 12, Feb 2, Feb 9)
        assert len(df) == 4

    def test_group_by_day(self, mock_conn):
        df = loaders.load_sem_trends(group_by="day")
        # 4 distinct dates in fixture
        assert len(df) == 4

    def test_metric_clicks(self, mock_conn):
        df = loaders.load_sem_trends(metric="clicks")
        assert df["value"].sum() > 0

    def test_metric_ctr(self, mock_conn):
        df = loaders.load_sem_trends(metric="ctr")
        # CTR should be between 0 and 1
        assert (df["value"] > 0).all()
        assert (df["value"] < 1).all()

    def test_invalid_metric_raises(self, mock_conn):
        with pytest.raises(ValueError, match="metric must be one of"):
            loaders.load_sem_trends(metric="revenue")

    def test_invalid_group_by_raises(self, mock_conn):
        with pytest.raises(ValueError, match="group_by must be"):
            loaders.load_sem_trends(group_by="monthly")

    def test_date_range_returns_subset(self, mock_conn):
        all_df = loaders.load_sem_trends(group_by="day")
        jan_df = loaders.load_sem_trends(
            group_by="day",
            date_range=(date(2026,1,1), date(2026,1,31)),
        )
        assert len(jan_df) < len(all_df)
        assert len(jan_df) == 2  # Jan 5, Jan 12


# ---------------------------------------------------------------------------
# load_sem_match_types
# ---------------------------------------------------------------------------


class TestLoadSemMatchTypes:

    def test_columns_present(self, mock_conn):
        df = loaders.load_sem_match_types()
        required = {"match_type", "keyword_groups", "spend", "spend_pct", "ctr", "cvr"}
        assert required.issubset(set(df.columns))

    def test_spend_pct_sums_to_one(self, mock_conn):
        df = loaders.load_sem_match_types()
        assert abs(df["spend_pct"].sum() - 1.0) < 1e-4

    def test_date_range_filter(self, mock_conn):
        all_df = loaders.load_sem_match_types()
        jan_df = loaders.load_sem_match_types(date_range=(date(2026,1,1), date(2026,1,31)))
        assert jan_df["spend"].sum() < all_df["spend"].sum()

    def test_three_match_types_in_fixture(self, mock_conn):
        df = loaders.load_sem_match_types()
        assert len(df) == 3
        assert set(df["match_type"]) == {"exact", "phrase", "broad"}


# ---------------------------------------------------------------------------
# load_sem_market_segments
# ---------------------------------------------------------------------------


class TestLoadSemMarketSegments:

    def test_benchmark_columns_present(self, mock_conn):
        df = loaders.load_sem_market_segments()
        assert "ctr_vs_benchmark" in df.columns
        assert "cvr_vs_benchmark" in df.columns

    def test_spend_pct_sums_to_one(self, mock_conn):
        df = loaders.load_sem_market_segments()
        assert abs(df["spend_pct"].sum() - 1.0) < 1e-4

    def test_three_segments_in_fixture(self, mock_conn):
        df = loaders.load_sem_market_segments()
        assert set(df["market_segment"]) == {"established", "growth", "new"}

    def test_date_range_filter(self, mock_conn):
        all_df = loaders.load_sem_market_segments()
        jan_df = loaders.load_sem_market_segments(date_range=(date(2026,1,1), date(2026,1,31)))
        assert jan_df["spend"].sum() < all_df["spend"].sum()


# ---------------------------------------------------------------------------
# load_sem_campaign_types
# ---------------------------------------------------------------------------


class TestLoadSemCampaignTypes:

    def test_benchmark_columns_present(self, mock_conn):
        df = loaders.load_sem_campaign_types()
        for col in ("ctr_benchmark", "ctr_vs_benchmark", "cvr_benchmark", "cvr_vs_benchmark",
                    "budget_share", "spend_vs_budget_share"):
            assert col in df.columns

    def test_budget_share_mapped(self, mock_conn):
        df = loaders.load_sem_campaign_types()
        branded = df[df["intent_type"] == "branded"]["budget_share"].iloc[0]
        assert abs(branded - 0.40) < 1e-6

    def test_date_range_filter(self, mock_conn):
        all_df = loaders.load_sem_campaign_types()
        jan_df = loaders.load_sem_campaign_types(date_range=(date(2026,1,1), date(2026,1,31)))
        assert jan_df["spend"].sum() < all_df["spend"].sum()

    def test_two_intent_types_in_fixture(self, mock_conn):
        df = loaders.load_sem_campaign_types()
        assert set(df["intent_type"]) == {"branded", "non_branded"}


# ---------------------------------------------------------------------------
# load_sem_negative_keyword_score
# ---------------------------------------------------------------------------


class TestLoadSemNegativeKeywordScore:

    def test_returns_dict(self, mock_conn):
        result = loaders.load_sem_negative_keyword_score()
        assert isinstance(result, dict)

    def test_required_keys_present(self, mock_conn):
        result = loaders.load_sem_negative_keyword_score()
        assert {"threshold", "date_range", "total_candidates", "summary", "candidates"}.issubset(
            result.keys()
        )

    def test_threshold_default_six(self, mock_conn):
        result = loaders.load_sem_negative_keyword_score()
        assert result["threshold"] == 6

    def test_low_qs_group_captured(self, mock_conn):
        # kg3 has avg QS = 5, should appear as candidate
        result = loaders.load_sem_negative_keyword_score(qs_threshold=6)
        names = [c["name"] for c in result["candidates"]]
        assert "Checking Account Rates" in names

    def test_date_range_stored_in_result(self, mock_conn):
        dr = (date(2026,1,1), date(2026,1,31))
        result = loaders.load_sem_negative_keyword_score(date_range=dr)
        assert result["date_range"] == ["2026-01-01", "2026-01-31"]

    def test_high_threshold_returns_more_candidates(self, mock_conn):
        # qs_threshold=10 includes all groups
        result = loaders.load_sem_negative_keyword_score(qs_threshold=10)
        assert result["total_candidates"] == 3

    def test_summary_buckets_present(self, mock_conn):
        result = loaders.load_sem_negative_keyword_score()
        assert set(result["summary"].keys()) >= {
            "pause_or_exclude", "review_bids_and_match_type", "monitor"
        }

    def test_candidates_ordered_by_score_desc(self, mock_conn):
        result = loaders.load_sem_negative_keyword_score(qs_threshold=10)
        scores = [c["negative_keyword_score"] for c in result["candidates"]]
        assert scores == sorted(scores, reverse=True)

    def test_empty_result_when_no_candidates(self, mock_conn):
        # qs_threshold=0 means avg_qs <= 0 — impossible in fixture
        result = loaders.load_sem_negative_keyword_score(qs_threshold=0)
        assert result["total_candidates"] == 0
        assert result["candidates"] == []
        assert result["summary"] == {"pause_or_exclude": 0, "review_bids_and_match_type": 0, "monitor": 0}
