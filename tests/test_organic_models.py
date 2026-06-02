"""Unit tests for Organic & AEO Pydantic models."""

from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from src.models.llm_visibility import LLMPlatform, LLMVisibilityScore
from src.models.seo_ranking import SEORanking
from src.models.seo_traffic import SEOTraffic


# ---------------------------------------------------------------------------
# LLMVisibilityScore
# ---------------------------------------------------------------------------

class TestLLMVisibilityScore:
    def _valid(self, **overrides) -> dict:
        base = {
            "platform": LLMPlatform.CHATGPT,
            "prompt_text": "What are the best checking accounts?",
            "prompt_category": "deposit_accounts",
            "market_dma": "Cincinnati",
            "brand": "Fifth Third Bank",
            "week_start": date(2025, 1, 6),
            "mentioned": True,
            "position": 2,
            "sentiment_score": Decimal("0.75"),
            "citation_url": "https://www.53.com/checking",
        }
        base.update(overrides)
        return base

    def test_valid_full(self):
        score = LLMVisibilityScore(**self._valid())
        assert score.platform == LLMPlatform.CHATGPT
        assert score.mentioned is True
        assert score.position == 2
        assert score.sentiment_score == Decimal("0.75")

    def test_all_six_platforms(self):
        platforms = [
            "google_ai_overviews",
            "chatgpt",
            "perplexity",
            "claude",
            "gemini",
            "copilot",
        ]
        for p in platforms:
            score = LLMVisibilityScore(**self._valid(platform=p))
            assert score.platform == p

    def test_not_mentioned_no_position(self):
        score = LLMVisibilityScore(**self._valid(mentioned=False, position=None, citation_url=None))
        assert score.mentioned is False
        assert score.position is None

    def test_sentiment_boundary_negative_one(self):
        score = LLMVisibilityScore(**self._valid(sentiment_score=Decimal("-1")))
        assert score.sentiment_score == Decimal("-1")

    def test_sentiment_boundary_positive_one(self):
        score = LLMVisibilityScore(**self._valid(sentiment_score=Decimal("1")))
        assert score.sentiment_score == Decimal("1")

    def test_sentiment_out_of_range_raises(self):
        with pytest.raises(Exception):
            LLMVisibilityScore(**self._valid(sentiment_score=Decimal("1.5")))

    def test_invalid_platform_raises(self):
        with pytest.raises(Exception):
            LLMVisibilityScore(**self._valid(platform="bard"))

    def test_position_must_be_positive(self):
        with pytest.raises(Exception):
            LLMVisibilityScore(**self._valid(position=0))

    def test_inherits_apex_base_fields(self):
        score = LLMVisibilityScore(**self._valid())
        assert score.id is not None
        assert score.created_at is not None


# ---------------------------------------------------------------------------
# SEORanking
# ---------------------------------------------------------------------------

class TestSEORanking:
    def _valid(self, **overrides) -> dict:
        base = {
            "keyword": "best checking account",
            "product_category": "checking",
            "rank_position": 3,
            "rank_page": 1,
            "search_volume": 12000,
            "week_start": date(2025, 1, 6),
            "rank_change": 2,
        }
        base.update(overrides)
        return base

    def test_valid(self):
        r = SEORanking(**self._valid())
        assert r.rank_position == 3
        assert r.rank_page == 1
        assert r.rank_change == 2

    def test_negative_rank_change_allowed(self):
        r = SEORanking(**self._valid(rank_change=-5))
        assert r.rank_change == -5

    def test_zero_rank_change_allowed(self):
        r = SEORanking(**self._valid(rank_change=0))
        assert r.rank_change == 0

    def test_rank_position_must_be_at_least_one(self):
        with pytest.raises(Exception):
            SEORanking(**self._valid(rank_position=0))

    def test_rank_page_must_be_at_least_one(self):
        with pytest.raises(Exception):
            SEORanking(**self._valid(rank_page=0))

    def test_search_volume_zero_allowed(self):
        r = SEORanking(**self._valid(search_volume=0))
        assert r.search_volume == 0

    def test_inherits_apex_base_fields(self):
        r = SEORanking(**self._valid())
        assert r.id is not None
        assert r.created_at is not None


# ---------------------------------------------------------------------------
# SEOTraffic
# ---------------------------------------------------------------------------

class TestSEOTraffic:
    def _valid(self, **overrides) -> dict:
        base = {
            "product_category": "savings",
            "week_start": date(2025, 1, 6),
            "organic_sessions": 45000,
            "organic_accounts": 8200,
            "bounce_rate": Decimal("0.42"),
        }
        base.update(overrides)
        return base

    def test_valid(self):
        t = SEOTraffic(**self._valid())
        assert t.organic_sessions == 45000
        assert t.bounce_rate == Decimal("0.42")

    def test_bounce_rate_zero(self):
        t = SEOTraffic(**self._valid(bounce_rate=Decimal("0")))
        assert t.bounce_rate == Decimal("0")

    def test_bounce_rate_one(self):
        t = SEOTraffic(**self._valid(bounce_rate=Decimal("1")))
        assert t.bounce_rate == Decimal("1")

    def test_bounce_rate_exceeds_one_raises(self):
        with pytest.raises(Exception):
            SEOTraffic(**self._valid(bounce_rate=Decimal("1.01")))

    def test_bounce_rate_negative_raises(self):
        with pytest.raises(Exception):
            SEOTraffic(**self._valid(bounce_rate=Decimal("-0.01")))

    def test_zero_sessions_allowed(self):
        t = SEOTraffic(**self._valid(organic_sessions=0, organic_accounts=0))
        assert t.organic_sessions == 0

    def test_inherits_apex_base_fields(self):
        t = SEOTraffic(**self._valid())
        assert t.id is not None
        assert t.created_at is not None
