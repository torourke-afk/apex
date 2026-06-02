"""Tests for organic & AEO data loaders (APE-86 / APE-18c).

Coverage:
  - load_llm_visibility: unfiltered, platform filter, period filter, market filter,
    invalid platform raises ValueError
  - load_competitive_aeo: unfiltered, competitor filter, period filter, empty result
  - load_prompt_drilldown: unfiltered, platform filter, prompt_category filter
  - load_seo_rankings: unfiltered, category filter, period filter, invalid category raises
  - load_seo_traffic: unfiltered, period filter, empty result
  - load_rank_change_alerts: default threshold, custom threshold, invalid threshold raises
  - compute_mention_rate: known inputs, empty df
  - compute_avg_position: 'avg_position' column, 'position' column, empty df
  - compute_share_of_voice: known split, missing brand, empty df
  - compute_citation_rate: known inputs, empty df

Strategy: monkeypatch `src.data.organic_loaders.get_connection` to return an
in-memory DuckDB populated with controlled fixture rows.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import patch

import duckdb
import pandas as pd
import pytest

import src.data.organic_loaders as loaders

# ---------------------------------------------------------------------------
# Shared DDL for fixture tables
# ---------------------------------------------------------------------------

_DDL_LLM = """
CREATE TABLE IF NOT EXISTS llm_visibility (
    id               VARCHAR PRIMARY KEY,
    week_start       DATE,
    platform         VARCHAR,
    prompt_text      VARCHAR,
    prompt_category  VARCHAR,
    market_dma       VARCHAR,
    brand            VARCHAR,
    mentioned        BOOLEAN,
    position         INTEGER,
    mention_rate     DOUBLE,
    sentiment_score  DOUBLE,
    citation_rate    DOUBLE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP
)
"""

_DDL_AEO_WEEKLY = """
CREATE TABLE IF NOT EXISTS aeo_weekly_readings (
    id              VARCHAR PRIMARY KEY,
    week_ending     DATE,
    platform        VARCHAR,
    prompt          VARCHAR,
    mention_rate    DOUBLE,
    avg_position    DOUBLE,
    share_of_voice  DOUBLE,
    sentiment_score DOUBLE,
    citation_rate   DOUBLE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP
)
"""

_DDL_AEO_COMP = """
CREATE TABLE IF NOT EXISTS aeo_competitor_scores (
    id              VARCHAR PRIMARY KEY,
    week_ending     DATE,
    competitor_name VARCHAR,
    platform        VARCHAR,
    mention_rate    DOUBLE,
    avg_position    DOUBLE,
    share_of_voice  DOUBLE,
    sentiment_score DOUBLE,
    citation_rate   DOUBLE,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP
)
"""

_DDL_SEO_RANK = """
CREATE TABLE IF NOT EXISTS seo_rankings (
    id               VARCHAR PRIMARY KEY,
    week_start       DATE,
    keyword          VARCHAR,
    product_category VARCHAR,
    rank_position    INTEGER,
    rank_page        INTEGER,
    search_volume    INTEGER,
    rank_change      INTEGER,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP
)
"""

_DDL_SEO_TRAFFIC = """
CREATE TABLE IF NOT EXISTS seo_traffic (
    id               VARCHAR PRIMARY KEY,
    week_start       DATE,
    product_category VARCHAR,
    organic_sessions INTEGER,
    organic_accounts INTEGER,
    bounce_rate      DOUBLE,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP
)
"""


def _make_conn() -> duckdb.DuckDBPyConnection:
    """Return an in-memory DuckDB connection pre-loaded with fixture rows."""
    conn = duckdb.connect(":memory:")

    conn.execute(_DDL_LLM)
    conn.execute(_DDL_AEO_WEEKLY)
    conn.execute(_DDL_AEO_COMP)
    conn.execute(_DDL_SEO_RANK)
    conn.execute(_DDL_SEO_TRAFFIC)

    # llm_visibility — 4 rows: 2 platforms × 2 brands
    conn.executemany(
        """
        INSERT INTO llm_visibility VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), NULL)
        """,
        [
            ("id1", date(2025, 5, 5), "chatgpt", "best checking account",
             "checking", "Cincinnati", "Fifth Third Bank",
             True, 2, 0.42, 0.60, 0.25),
            ("id2", date(2025, 5, 5), "chatgpt", "best checking account",
             "checking", "Cincinnati", "National Bank A",
             True, 1, 0.38, 0.55, 0.23),
            ("id3", date(2025, 5, 12), "perplexity", "mortgage rates near me",
             "mortgage", "Detroit", "Fifth Third Bank",
             True, 3, 0.35, 0.58, 0.22),
            ("id4", date(2025, 5, 12), "perplexity", "mortgage rates near me",
             "mortgage", "Detroit", "National Bank A",
             False, None, 0.20, 0.45, 0.15),
        ],
    )

    # aeo_weekly_readings — 4 rows
    conn.executemany(
        """
        INSERT INTO aeo_weekly_readings VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), NULL)
        """,
        [
            ("ar1", date(2025, 5, 5), "ChatGPT", "best checking account",
             0.42, 2.10, 0.15, 0.60, 0.25),
            ("ar2", date(2025, 5, 5), "ChatGPT", "high yield savings account",
             0.38, 2.50, 0.13, 0.55, 0.22),
            ("ar3", date(2025, 5, 12), "Perplexity", "best checking account",
             0.36, 2.30, 0.12, 0.52, 0.20),
            ("ar4", date(2025, 5, 12), "Perplexity", "mortgage rates near me",
             0.30, 2.80, 0.10, 0.48, 0.18),
        ],
    )

    # aeo_competitor_scores — 4 rows
    conn.executemany(
        """
        INSERT INTO aeo_competitor_scores VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), NULL)
        """,
        [
            ("ac1", date(2025, 5, 5), "National Bank A", "ChatGPT",
             0.38, 2.10, 0.18, 0.55, 0.26),
            ("ac2", date(2025, 5, 5), "Regional Bank B", "ChatGPT",
             0.29, 2.80, 0.12, 0.48, 0.19),
            ("ac3", date(2025, 5, 12), "National Bank A", "Perplexity",
             0.35, 2.20, 0.16, 0.53, 0.24),
            ("ac4", date(2025, 5, 12), "Regional Bank B", "Perplexity",
             0.27, 2.90, 0.11, 0.46, 0.18),
        ],
    )

    # seo_rankings — 5 rows across two categories with varying rank_change
    conn.executemany(
        """
        INSERT INTO seo_rankings VALUES (?, ?, ?, ?, ?, ?, ?, ?, NOW(), NULL)
        """,
        [
            ("sr1", date(2025, 5, 5), "best checking account", "checking", 5, 1, 22000, 0),
            ("sr2", date(2025, 5, 12), "best checking account", "checking", 3, 1, 22000, -2),
            ("sr3", date(2025, 5, 5), "mortgage rates today", "mortgage", 15, 2, 45000, 0),
            ("sr4", date(2025, 5, 12), "mortgage rates today", "mortgage", 22, 3, 45000, 7),
            ("sr5", date(2025, 5, 12), "high yield savings account", "savings", 8, 1, 24000, -6),
        ],
    )

    # seo_traffic — 4 rows
    conn.executemany(
        """
        INSERT INTO seo_traffic VALUES (?, ?, ?, ?, ?, ?, NOW(), NULL)
        """,
        [
            ("st1", date(2025, 5, 5), "checking", 38000, 380, 0.42),
            ("st2", date(2025, 5, 5), "savings", 28000, 290, 0.45),
            ("st3", date(2025, 5, 12), "checking", 39000, 395, 0.41),
            ("st4", date(2025, 5, 12), "savings", 29000, 305, 0.44),
        ],
    )

    return conn


@pytest.fixture
def mock_conn(monkeypatch):
    """Monkeypatch get_connection to return a fresh in-memory fixture DB."""
    conn = _make_conn()
    monkeypatch.setattr(loaders, "get_connection", lambda: conn)
    yield conn


# ---------------------------------------------------------------------------
# load_llm_visibility
# ---------------------------------------------------------------------------


class TestLoadLlmVisibility:

    def test_returns_all_rows_unfiltered(self, mock_conn):
        df = loaders.load_llm_visibility()
        assert len(df) == 4
        assert set(df.columns) >= {
            "week_start", "platform", "prompt_text", "prompt_category",
            "market_dma", "brand", "mentioned", "position",
            "mention_rate", "sentiment_score", "citation_rate",
        }

    def test_filter_by_platform(self, mock_conn):
        df = loaders.load_llm_visibility(platform="chatgpt")
        assert len(df) == 2
        assert (df["platform"] == "chatgpt").all()

    def test_filter_by_period(self, mock_conn):
        df = loaders.load_llm_visibility(period="2025-05-05")
        assert len(df) == 2
        assert (df["week_start"].astype(str) == "2025-05-05").all()

    def test_filter_by_market(self, mock_conn):
        df = loaders.load_llm_visibility(market="Cincinnati")
        assert len(df) == 2
        assert (df["market_dma"] == "Cincinnati").all()

    def test_combined_filters(self, mock_conn):
        df = loaders.load_llm_visibility(platform="chatgpt", period="2025-05-05")
        assert len(df) == 2

    def test_invalid_platform_raises(self, mock_conn):
        with pytest.raises(ValueError, match="platform must be one of"):
            loaders.load_llm_visibility(platform="unknown_llm")

    def test_empty_result_returns_empty_df(self, mock_conn):
        df = loaders.load_llm_visibility(period="1900-01-01")
        assert df.empty
        assert isinstance(df, pd.DataFrame)

    def test_mention_rate_is_float(self, mock_conn):
        df = loaders.load_llm_visibility()
        assert df["mention_rate"].dtype == float

    def test_mentioned_is_bool(self, mock_conn):
        df = loaders.load_llm_visibility()
        assert df["mentioned"].dtype == bool


# ---------------------------------------------------------------------------
# load_competitive_aeo
# ---------------------------------------------------------------------------


class TestLoadCompetitiveAeo:

    def test_returns_all_rows_unfiltered(self, mock_conn):
        df = loaders.load_competitive_aeo()
        assert len(df) == 4

    def test_filter_by_competitor(self, mock_conn):
        df = loaders.load_competitive_aeo(competitors=["National Bank A"])
        assert len(df) == 2
        assert (df["competitor_name"] == "National Bank A").all()

    def test_filter_multiple_competitors(self, mock_conn):
        df = loaders.load_competitive_aeo(competitors=["National Bank A", "Regional Bank B"])
        assert len(df) == 4

    def test_filter_by_period(self, mock_conn):
        df = loaders.load_competitive_aeo(period="2025-05-05")
        assert len(df) == 2

    def test_empty_competitors_list_returns_all(self, mock_conn):
        df = loaders.load_competitive_aeo(competitors=[])
        assert len(df) == 4

    def test_metrics_are_float(self, mock_conn):
        df = loaders.load_competitive_aeo()
        for col in ("mention_rate", "avg_position", "share_of_voice", "citation_rate"):
            assert df[col].dtype == float


# ---------------------------------------------------------------------------
# load_prompt_drilldown
# ---------------------------------------------------------------------------


class TestLoadPromptDrilldown:

    def test_returns_all_rows_unfiltered(self, mock_conn):
        df = loaders.load_prompt_drilldown()
        assert len(df) == 4

    def test_filter_by_platform(self, mock_conn):
        df = loaders.load_prompt_drilldown(platform="ChatGPT")
        assert len(df) == 2
        assert (df["platform"] == "ChatGPT").all()

    def test_filter_by_period(self, mock_conn):
        df = loaders.load_prompt_drilldown(period="2025-05-05")
        assert len(df) == 2

    def test_prompt_category_filter_checking(self, mock_conn):
        df = loaders.load_prompt_drilldown(prompt_category="checking")
        # "best checking account" appears twice in the fixture
        assert len(df) >= 2
        assert df["prompt"].str.contains("checking", case=False).all()

    def test_unknown_category_returns_empty(self, mock_conn):
        df = loaders.load_prompt_drilldown(prompt_category="not_a_category")
        assert df.empty

    def test_metrics_are_float(self, mock_conn):
        df = loaders.load_prompt_drilldown()
        for col in ("mention_rate", "avg_position", "citation_rate"):
            assert df[col].dtype == float


# ---------------------------------------------------------------------------
# load_seo_rankings
# ---------------------------------------------------------------------------


class TestLoadSeoRankings:

    def test_returns_all_rows_unfiltered(self, mock_conn):
        df = loaders.load_seo_rankings()
        assert len(df) == 5

    def test_filter_by_category(self, mock_conn):
        df = loaders.load_seo_rankings(category="checking")
        assert len(df) == 2
        assert (df["product_category"] == "checking").all()

    def test_filter_by_period(self, mock_conn):
        df = loaders.load_seo_rankings(period="2025-05-05")
        assert len(df) == 2

    def test_invalid_category_raises(self, mock_conn):
        with pytest.raises(ValueError, match="category must be one of"):
            loaders.load_seo_rankings(category="bad_category")

    def test_rank_position_is_int(self, mock_conn):
        df = loaders.load_seo_rankings()
        assert df["rank_position"].dtype in (int, "int64", "int32")

    def test_empty_result_is_dataframe(self, mock_conn):
        df = loaders.load_seo_rankings(period="1900-01-01")
        assert df.empty and isinstance(df, pd.DataFrame)


# ---------------------------------------------------------------------------
# load_seo_traffic
# ---------------------------------------------------------------------------


class TestLoadSeoTraffic:

    def test_returns_all_rows_unfiltered(self, mock_conn):
        df = loaders.load_seo_traffic()
        assert len(df) == 4

    def test_filter_by_period(self, mock_conn):
        df = loaders.load_seo_traffic(period="2025-05-05")
        assert len(df) == 2

    def test_bounce_rate_is_float(self, mock_conn):
        df = loaders.load_seo_traffic()
        assert df["bounce_rate"].dtype == float

    def test_empty_result_graceful(self, mock_conn):
        df = loaders.load_seo_traffic(period="1900-01-01")
        assert df.empty and isinstance(df, pd.DataFrame)


# ---------------------------------------------------------------------------
# load_rank_change_alerts
# ---------------------------------------------------------------------------


class TestLoadRankChangeAlerts:

    def test_default_threshold_five(self, mock_conn):
        # Only rows with |rank_change| >= 5: sr4 (7), sr5 (-6)
        df = loaders.load_rank_change_alerts()
        assert len(df) == 2

    def test_custom_threshold_two(self, mock_conn):
        # |rank_change| >= 2: sr2 (-2), sr4 (7), sr5 (-6)
        df = loaders.load_rank_change_alerts(threshold=2)
        assert len(df) == 3

    def test_direction_column_present(self, mock_conn):
        df = loaders.load_rank_change_alerts(threshold=2)
        assert "direction" in df.columns
        assert set(df["direction"].unique()).issubset({"improved", "dropped"})

    def test_dropped_has_positive_rank_change(self, mock_conn):
        df = loaders.load_rank_change_alerts(threshold=2)
        dropped = df[df["direction"] == "dropped"]
        assert (dropped["rank_change"] > 0).all()

    def test_improved_has_negative_rank_change(self, mock_conn):
        df = loaders.load_rank_change_alerts(threshold=2)
        improved = df[df["direction"] == "improved"]
        assert (improved["rank_change"] < 0).all()

    def test_threshold_zero_raises(self, mock_conn):
        with pytest.raises(ValueError, match="threshold must be >= 1"):
            loaders.load_rank_change_alerts(threshold=0)

    def test_high_threshold_returns_empty(self, mock_conn):
        df = loaders.load_rank_change_alerts(threshold=999)
        assert df.empty and isinstance(df, pd.DataFrame)
        assert "direction" in df.columns


# ---------------------------------------------------------------------------
# Aggregation helpers
# ---------------------------------------------------------------------------


class TestComputeMentionRate:

    def test_known_values(self):
        df = pd.DataFrame({"mention_rate": [0.4, 0.6, 0.5]})
        result = loaders.compute_mention_rate(df)
        assert abs(result - 0.5) < 1e-9

    def test_empty_df_returns_zero(self):
        assert loaders.compute_mention_rate(pd.DataFrame()) == 0.0

    def test_missing_column_returns_zero(self):
        df = pd.DataFrame({"other": [1, 2, 3]})
        assert loaders.compute_mention_rate(df) == 0.0


class TestComputeAvgPosition:

    def test_avg_position_column(self):
        df = pd.DataFrame({"avg_position": [2.0, 3.0, 4.0]})
        assert abs(loaders.compute_avg_position(df) - 3.0) < 1e-9

    def test_position_column_fallback(self):
        df = pd.DataFrame({"position": [1.0, 2.0, 3.0]})
        assert abs(loaders.compute_avg_position(df) - 2.0) < 1e-9

    def test_ignores_null_positions(self):
        df = pd.DataFrame({"position": [1.0, None, 3.0]})
        assert abs(loaders.compute_avg_position(df) - 2.0) < 1e-9

    def test_empty_df_returns_zero(self):
        assert loaders.compute_avg_position(pd.DataFrame()) == 0.0

    def test_no_position_column_returns_zero(self):
        df = pd.DataFrame({"other": [1, 2]})
        assert loaders.compute_avg_position(df) == 0.0


class TestComputeShareOfVoice:

    def test_known_split(self):
        df = pd.DataFrame({
            "brand": ["Fifth Third Bank", "National Bank A", "Regional Bank B"],
            "mention_rate": [0.40, 0.35, 0.25],
        })
        sov = loaders.compute_share_of_voice(df, "Fifth Third Bank")
        assert abs(sov - 0.40) < 1e-9

    def test_missing_brand_returns_zero(self):
        df = pd.DataFrame({
            "brand": ["National Bank A"],
            "mention_rate": [0.40],
        })
        assert loaders.compute_share_of_voice(df, "Fifth Third Bank") == 0.0

    def test_empty_df_returns_zero(self):
        assert loaders.compute_share_of_voice(pd.DataFrame(), "Fifth Third Bank") == 0.0

    def test_zero_total_returns_zero(self):
        df = pd.DataFrame({"brand": ["Foo"], "mention_rate": [0.0]})
        assert loaders.compute_share_of_voice(df, "Foo") == 0.0


class TestComputeCitationRate:

    def test_known_values(self):
        df = pd.DataFrame({"citation_rate": [0.20, 0.30, 0.40]})
        assert abs(loaders.compute_citation_rate(df) - 0.30) < 1e-9

    def test_empty_df_returns_zero(self):
        assert loaders.compute_citation_rate(pd.DataFrame()) == 0.0

    def test_missing_column_returns_zero(self):
        df = pd.DataFrame({"other": [1, 2, 3]})
        assert loaders.compute_citation_rate(df) == 0.0
