"""Tests for src/data/retention.py loader functions.

Uses an in-memory DuckDB database with seed data so no live DB is required.
The shared `engine` in the retention module is monkeypatched with a fresh
in-memory engine for each test session.
"""

from __future__ import annotations

import uuid
from datetime import datetime

import pytest
from sqlalchemy import create_engine, text

import src.data.retention as retention_module
from src.data.retention import (
    get_bei_scores,
    get_behavioral_triggers,
    get_cohort_heatmap,
    get_geo_retention,
    get_offer_performance,
    get_pfi_milestones,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def mem_engine():
    """In-memory DuckDB engine with all retention tables created and seeded."""
    eng = create_engine("duckdb:///:memory:", echo=False)
    now = datetime.utcnow()

    with eng.begin() as conn:
        # cohorts (required for FK targets)
        conn.execute(text("""
            CREATE TABLE cohorts (
                id UUID PRIMARY KEY,
                name VARCHAR NOT NULL,
                segment VARCHAR NOT NULL,
                criteria JSON NOT NULL,
                size INTEGER NOT NULL DEFAULT 0,
                period_start DATE NOT NULL,
                period_end DATE NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
        cohort_id = str(uuid.uuid4())
        conn.execute(text("""
            INSERT INTO cohorts VALUES (
                :id, 'Test Cohort', 'new', '{}', 100,
                '2024-01-01', '2024-12-31', :now, :now
            )
        """), {"id": cohort_id, "now": now})

        # pfi_milestones
        conn.execute(text("""
            CREATE TABLE pfi_milestones (
                id UUID PRIMARY KEY,
                cohort_id UUID,
                milestone_type VARCHAR NOT NULL,
                target_pct DECIMAL(6,4) NOT NULL,
                actual_pct DECIMAL(6,4) NOT NULL,
                target_days INTEGER NOT NULL,
                switching_cost DECIMAL(18,4) NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
        for mtype, tpct, apct, tdays, scost in [
            ("Direct Deposit", 0.60, 0.54, 30, 450.00),
            ("Bill Pay", 0.40, 0.38, 45, 280.00),
            ("Debit Card", 0.70, 0.72, 14, 150.00),
        ]:
            conn.execute(text("""
                INSERT INTO pfi_milestones VALUES (
                    :id, :cid, :mtype, :tpct, :apct, :tdays, :scost, :now, :now
                )
            """), {"id": str(uuid.uuid4()), "cid": cohort_id,
                   "mtype": mtype, "tpct": tpct, "apct": apct,
                   "tdays": tdays, "scost": scost, "now": now})

        # cohort_retention_heatmap
        conn.execute(text("""
            CREATE TABLE cohort_retention_heatmap (
                id UUID PRIMARY KEY,
                cohort_id UUID,
                acquisition_month VARCHAR NOT NULL,
                mob INTEGER NOT NULL,
                retention_rate DECIMAL(6,4) NOT NULL,
                channel VARCHAR NOT NULL,
                quality_score_band VARCHAR NOT NULL,
                market VARCHAR NOT NULL,
                offer_type VARCHAR NOT NULL,
                product_mix VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
        heatmap_rows = [
            ("2024-01", 1, 0.92, "Digital", "High", "Midwest", "Cash Back", "Checking"),
            ("2024-01", 3, 0.85, "Digital", "High", "Midwest", "Cash Back", "Checking"),
            ("2024-01", 6, 0.78, "Digital", "High", "Midwest", "Cash Back", "Checking"),
            ("2024-02", 1, 0.91, "Branch", "Medium", "South", "APY Boost", "Savings"),
            ("2024-02", 3, 0.83, "Branch", "Medium", "South", "APY Boost", "Savings"),
            ("2024-02", 6, 0.75, "Branch", "Medium", "South", "APY Boost", "Savings"),
        ]
        for acq_month, mob, rr, ch, qsb, mkt, ot, pm in heatmap_rows:
            conn.execute(text("""
                INSERT INTO cohort_retention_heatmap VALUES (
                    :id, :cid, :acq, :mob, :rr, :ch, :qsb, :mkt, :ot, :pm, :now, :now
                )
            """), {"id": str(uuid.uuid4()), "cid": cohort_id, "acq": acq_month,
                   "mob": mob, "rr": rr, "ch": ch, "qsb": qsb, "mkt": mkt,
                   "ot": ot, "pm": pm, "now": now})

        # bei_scores
        conn.execute(text("""
            CREATE TABLE bei_scores (
                id UUID PRIMARY KEY,
                market_tier VARCHAR NOT NULL,
                period VARCHAR NOT NULL,
                ease_of_banking DECIMAL(6,4) NOT NULL,
                trust DECIMAL(6,4) NOT NULL,
                value_perception DECIMAL(6,4) NOT NULL,
                digital_experience DECIMAL(6,4) NOT NULL,
                service_quality DECIMAL(6,4) NOT NULL,
                composite_score DECIMAL(6,4) NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
        for tier, period, eob, trust, vp, de, sq, comp in [
            ("Tier 1", "Q1 2024", 0.82, 0.79, 0.75, 0.88, 0.81, 0.81),
            ("Tier 1", "Q2 2024", 0.84, 0.80, 0.76, 0.89, 0.82, 0.82),
            ("Tier 2", "Q1 2024", 0.74, 0.71, 0.68, 0.79, 0.72, 0.73),
        ]:
            conn.execute(text("""
                INSERT INTO bei_scores VALUES (
                    :id, :tier, :period, :eob, :trust, :vp, :de, :sq, :comp, :now, :now
                )
            """), {"id": str(uuid.uuid4()), "tier": tier, "period": period,
                   "eob": eob, "trust": trust, "vp": vp, "de": de,
                   "sq": sq, "comp": comp, "now": now})

        # behavioral_triggers
        conn.execute(text("""
            CREATE TABLE behavioral_triggers (
                id UUID PRIMARY KEY,
                trigger_name VARCHAR NOT NULL,
                condition VARCHAR NOT NULL,
                action VARCHAR NOT NULL,
                volume_per_week INTEGER NOT NULL,
                conversion_rate DECIMAL(6,4) NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
        for tname, cond, act, vpw, cr in [
            ("Low Balance Alert", "balance < $100", "Send push + offer", 4200, 0.18),
            ("No Debit 30d", "no debit transaction in 30 days", "Email reactivation", 1800, 0.12),
            ("DD Miss", "expected direct deposit not received", "Branch follow-up", 950, 0.23),
        ]:
            conn.execute(text("""
                INSERT INTO behavioral_triggers VALUES (
                    :id, :tn, :cond, :act, :vpw, :cr, :now, :now
                )
            """), {"id": str(uuid.uuid4()), "tn": tname, "cond": cond,
                   "act": act, "vpw": vpw, "cr": cr, "now": now})

        # geo_retention
        conn.execute(text("""
            CREATE TABLE geo_retention (
                id UUID PRIMARY KEY,
                geography VARCHAR NOT NULL,
                lat DECIMAL(9,6) NOT NULL,
                lon DECIMAL(9,6) NOT NULL,
                retention_90d DECIMAL(6,4) NOT NULL,
                market_tier VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
        for geo, lat, lon, r90, mt in [
            ("Cincinnati, OH", 39.1031, -84.5120, 0.88, "Tier 1"),
            ("Nashville, TN", 36.1627, -86.7816, 0.82, "Tier 2"),
            ("Atlanta, GA", 33.7490, -84.3880, 0.79, "Tier 2"),
        ]:
            conn.execute(text("""
                INSERT INTO geo_retention VALUES (
                    :id, :geo, :lat, :lon, :r90, :mt, :now, :now
                )
            """), {"id": str(uuid.uuid4()), "geo": geo, "lat": lat,
                   "lon": lon, "r90": r90, "mt": mt, "now": now})

        # offer_performance
        conn.execute(text("""
            CREATE TABLE offer_performance (
                id UUID PRIMARY KEY,
                offer_name VARCHAR NOT NULL,
                eligibility_rate DECIMAL(6,4) NOT NULL,
                activation_rate DECIMAL(6,4) NOT NULL,
                fulfillment_rate DECIMAL(6,4) NOT NULL,
                day_30_impact DECIMAL(6,4) NOT NULL,
                day_90_impact DECIMAL(6,4) NOT NULL,
                period VARCHAR NOT NULL,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """))
        for oname, er, ar, fr, d30, d90, period in [
            ("$300 Welcome Bonus", 0.65, 0.48, 0.92, 0.05, 0.12, "Q1 2024"),
            ("$300 Welcome Bonus", 0.67, 0.50, 0.93, 0.06, 0.13, "Q2 2024"),
            ("4.5% APY Savings", 0.80, 0.61, 0.95, 0.08, 0.18, "Q1 2024"),
        ]:
            conn.execute(text("""
                INSERT INTO offer_performance VALUES (
                    :id, :on, :er, :ar, :fr, :d30, :d90, :period, :now, :now
                )
            """), {"id": str(uuid.uuid4()), "on": oname, "er": er, "ar": ar,
                   "fr": fr, "d30": d30, "d90": d90, "period": period, "now": now})

    return eng, cohort_id


@pytest.fixture(autouse=True)
def patch_engine(mem_engine, monkeypatch):
    """Redirect all loader calls to the in-memory engine."""
    eng, _ = mem_engine
    monkeypatch.setattr(retention_module, "engine", eng)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestGetPfiMilestones:
    def test_returns_all_rows_without_filter(self, mem_engine):
        df = get_pfi_milestones()
        assert len(df) == 3
        assert list(df.columns) == [
            "milestone_type", "target_pct", "actual_pct", "target_days", "switching_cost"
        ]

    def test_filters_by_cohort_id(self, mem_engine):
        _, cohort_id = mem_engine
        df = get_pfi_milestones(cohort_id=cohort_id)
        assert len(df) == 3

    def test_unknown_cohort_returns_empty(self):
        df = get_pfi_milestones(cohort_id=str(uuid.uuid4()))
        assert df.empty

    def test_ordered_by_milestone_type(self):
        df = get_pfi_milestones()
        assert list(df["milestone_type"]) == sorted(df["milestone_type"].tolist())


class TestGetCohortHeatmap:
    def test_returns_pivoted_dataframe(self):
        df = get_cohort_heatmap()
        assert "acquisition_month" in df.columns
        # MOB columns should be integers
        mob_cols = [c for c in df.columns if c != "acquisition_month"]
        assert all(isinstance(c, int) for c in mob_cols)

    def test_pivot_shape(self):
        df = get_cohort_heatmap()
        assert len(df) == 2  # 2024-01 and 2024-02
        assert 1 in df.columns and 3 in df.columns and 6 in df.columns

    def test_empty_filters_returns_all_data(self):
        df_no_filter = get_cohort_heatmap()
        df_empty_filter = get_cohort_heatmap({})
        assert len(df_no_filter) == len(df_empty_filter)

    def test_filter_by_channel(self):
        df = get_cohort_heatmap({"channel": "Digital"})
        assert len(df) == 1
        assert df["acquisition_month"].iloc[0] == "2024-01"

    def test_filter_by_unknown_value_returns_empty(self):
        df = get_cohort_heatmap({"channel": "NonexistentChannel"})
        assert df.empty

    def test_none_filter_values_are_ignored(self):
        df = get_cohort_heatmap({"channel": None, "market": None})
        assert len(df) == 2


class TestGetBeiScores:
    def test_returns_all_rows_without_filter(self):
        df = get_bei_scores()
        assert len(df) == 3
        expected_cols = [
            "market_tier", "period", "ease_of_banking", "trust",
            "value_perception", "digital_experience", "service_quality",
            "composite_score",
        ]
        assert list(df.columns) == expected_cols

    def test_filters_by_market_tier(self):
        df = get_bei_scores(market_tier="Tier 1")
        assert len(df) == 2
        assert all(df["market_tier"] == "Tier 1")

    def test_unknown_tier_returns_empty(self):
        df = get_bei_scores(market_tier="Tier 99")
        assert df.empty


class TestGetBehavioralTriggers:
    def test_returns_all_rows(self):
        df = get_behavioral_triggers()
        assert len(df) == 3
        assert list(df.columns) == [
            "trigger_name", "condition", "action", "volume_per_week", "conversion_rate"
        ]

    def test_ordered_by_trigger_name(self):
        df = get_behavioral_triggers()
        assert list(df["trigger_name"]) == sorted(df["trigger_name"].tolist())


class TestGetGeoRetention:
    def test_returns_all_rows(self):
        df = get_geo_retention()
        assert len(df) == 3
        assert list(df.columns) == [
            "geography", "lat", "lon", "retention_90d", "market_tier"
        ]

    def test_has_numeric_coordinates(self):
        df = get_geo_retention()
        assert df["lat"].dtype.kind in ("f", "O")  # float or Decimal
        assert df["lon"].dtype.kind in ("f", "O")


class TestGetOfferPerformance:
    def test_returns_all_rows(self):
        df = get_offer_performance()
        assert len(df) == 3
        assert list(df.columns) == [
            "offer_name", "eligibility_rate", "activation_rate",
            "fulfillment_rate", "day_30_impact", "day_90_impact", "period",
        ]

    def test_ordered_by_offer_then_period(self):
        df = get_offer_performance()
        welcome_rows = df[df["offer_name"] == "$300 Welcome Bonus"]
        assert list(welcome_rows["period"]) == ["Q1 2024", "Q2 2024"]
