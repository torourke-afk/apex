"""Unit tests for SEM Pydantic models (APE-88).

Covers SEMKeywordGroup and SEMDailyPerformance spec compliance:
  - field presence and constraints
  - enum values (intent_type, match_type, market_segment)
  - quality_score range 3–10
  - vbb_margin_signal range 0–1
  - model_validator invariants (clicks ≤ impressions, conversions ≤ clicks)
  - is_active field semantics
  - ApexBase inheritance
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from src.models.sem_keyword_group import SEMIntentType, SEMKeywordGroup
from src.models.sem_daily_performance import SEMDailyPerformance


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _valid_group(**overrides) -> dict:
    base = {
        "name": "Fifth Third Checking Account",
        "product_category": "checking",
        "intent_type": SEMIntentType.BRANDED,
        "match_type": "exact",
        "max_cpc": Decimal("1.25"),
        "quality_score": 8,
        "estimated_monthly_volume": 50_000,
        "market_segment": "established",
        "is_active": True,
    }
    base.update(overrides)
    return base


def _valid_perf(**overrides) -> dict:
    base = {
        "keyword_group_id": uuid4(),
        "date": date(2026, 3, 1),
        "impressions": 10_000,
        "clicks": 500,
        "ctr": Decimal("0.050000"),
        "cpc": Decimal("1.2500"),
        "spend": Decimal("625.0000"),
        "avg_position": Decimal("1.50"),
        "impression_share": Decimal("0.8500"),
        "quality_score": 7,
        "conversions": 15,
        "cvr": Decimal("0.030000"),
        "cpl": Decimal("41.6667"),
        "vbb_margin_signal": 0.72,
    }
    base.update(overrides)
    return base


# ---------------------------------------------------------------------------
# SEMKeywordGroup
# ---------------------------------------------------------------------------

class TestSEMKeywordGroup:

    def test_valid_branded_group(self):
        g = SEMKeywordGroup(**_valid_group())
        assert g.intent_type == "branded"
        assert g.market_segment == "established"
        assert g.is_active is True
        assert g.quality_score == 8

    def test_all_three_intent_types_accepted(self):
        for it in ("branded", "non_branded", "pmax"):
            g = SEMKeywordGroup(**_valid_group(intent_type=it))
            assert g.intent_type == it

    def test_competitor_intent_type_rejected(self):
        """'competitor' was in old model; spec removed it — must raise."""
        with pytest.raises(Exception):
            SEMKeywordGroup(**_valid_group(intent_type="competitor"))

    def test_market_segment_required(self):
        data = _valid_group()
        del data["market_segment"]
        with pytest.raises(Exception):
            SEMKeywordGroup(**data)

    def test_market_segment_all_values(self):
        for seg in ("established", "growth", "new"):
            g = SEMKeywordGroup(**_valid_group(market_segment=seg))
            assert g.market_segment == seg

    def test_market_segment_invalid_raises(self):
        with pytest.raises(Exception):
            SEMKeywordGroup(**_valid_group(market_segment="premium"))

    def test_is_active_field_exists_and_defaults_true(self):
        g = SEMKeywordGroup(**_valid_group())
        assert g.is_active is True

    def test_is_active_can_be_false(self):
        g = SEMKeywordGroup(**_valid_group(is_active=False))
        assert g.is_active is False

    def test_quality_score_minimum_is_3(self):
        with pytest.raises(Exception):
            SEMKeywordGroup(**_valid_group(quality_score=2))

    def test_quality_score_3_accepted(self):
        g = SEMKeywordGroup(**_valid_group(quality_score=3))
        assert g.quality_score == 3

    def test_quality_score_10_accepted(self):
        g = SEMKeywordGroup(**_valid_group(quality_score=10))
        assert g.quality_score == 10

    def test_quality_score_above_10_rejected(self):
        with pytest.raises(Exception):
            SEMKeywordGroup(**_valid_group(quality_score=11))

    def test_inherits_apex_base_fields(self):
        g = SEMKeywordGroup(**_valid_group())
        assert g.id is not None
        assert g.created_at is not None

    def test_all_match_types_accepted(self):
        for mt in ("exact", "broad", "phrase"):
            g = SEMKeywordGroup(**_valid_group(match_type=mt))
            assert g.match_type == mt


# ---------------------------------------------------------------------------
# SEMDailyPerformance
# ---------------------------------------------------------------------------

class TestSEMDailyPerformance:

    def test_valid_record(self):
        p = SEMDailyPerformance(**_valid_perf())
        assert p.clicks == 500
        assert p.vbb_margin_signal == pytest.approx(0.72)

    def test_date_field_name(self):
        """Field must be named 'date' (not 'record_date')."""
        p = SEMDailyPerformance(**_valid_perf())
        assert hasattr(p, "date")
        assert not hasattr(p, "record_date")

    def test_cpc_field_name(self):
        """Field must be named 'cpc' (not 'avg_cpc')."""
        p = SEMDailyPerformance(**_valid_perf())
        assert hasattr(p, "cpc")
        assert not hasattr(p, "avg_cpc")

    def test_cvr_field_name(self):
        """Field must be named 'cvr' (not 'conversion_rate')."""
        p = SEMDailyPerformance(**_valid_perf())
        assert hasattr(p, "cvr")
        assert not hasattr(p, "conversion_rate")

    def test_cpl_field_name(self):
        """Field must be named 'cpl' (not 'cost_per_conversion')."""
        p = SEMDailyPerformance(**_valid_perf())
        assert hasattr(p, "cpl")
        assert not hasattr(p, "cost_per_conversion")

    def test_vbb_margin_signal_required(self):
        data = _valid_perf()
        del data["vbb_margin_signal"]
        with pytest.raises(Exception):
            SEMDailyPerformance(**data)

    def test_vbb_margin_signal_range(self):
        SEMDailyPerformance(**_valid_perf(vbb_margin_signal=0.0))
        SEMDailyPerformance(**_valid_perf(vbb_margin_signal=1.0))

    def test_vbb_margin_signal_above_1_rejected(self):
        with pytest.raises(Exception):
            SEMDailyPerformance(**_valid_perf(vbb_margin_signal=1.01))

    def test_vbb_margin_signal_below_0_rejected(self):
        with pytest.raises(Exception):
            SEMDailyPerformance(**_valid_perf(vbb_margin_signal=-0.01))

    def test_quality_score_minimum_is_3(self):
        with pytest.raises(Exception):
            SEMDailyPerformance(**_valid_perf(quality_score=2))

    def test_quality_score_3_accepted(self):
        p = SEMDailyPerformance(**_valid_perf(quality_score=3))
        assert p.quality_score == 3

    def test_clicks_cannot_exceed_impressions(self):
        with pytest.raises(Exception):
            SEMDailyPerformance(**_valid_perf(impressions=100, clicks=200))

    def test_conversions_cannot_exceed_clicks(self):
        with pytest.raises(Exception):
            SEMDailyPerformance(**_valid_perf(clicks=10, conversions=50))

    def test_zero_conversions_allowed(self):
        p = SEMDailyPerformance(**_valid_perf(conversions=0, cvr=Decimal("0")))
        assert p.conversions == 0

    def test_inherits_apex_base_fields(self):
        p = SEMDailyPerformance(**_valid_perf())
        assert p.id is not None
        assert p.created_at is not None
