"""Product & Experience query functions.

Provides seed-data backed query layer for the three Product & Experience
endpoints. Seed data represents a realistic mid-cycle bank product portfolio.
Each function returns safe defaults (empty containers / zero values) when no
live data exists, so callers never see 500s in dev/demo mode.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Literal

import streamlit as st

from src.config.settings import APEX_DATA_REFRESH_INTERVAL_SECONDS, APEX_DEBUG_MODE
from src.data import cache_metrics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Seed data — product pipeline
# ---------------------------------------------------------------------------

_PIPELINE_SEED: list[dict] = [
    {
        "id": "pipe-001",
        "name": "AI-Powered Savings Nudge",
        "product_line": "savings",
        "stage": "development",
        "owner": "Product - Core Banking",
        "target_date": "2026-07-15",
        "priority": "high",
        "confidence_score": 0.82,
        "description": "ML-driven push notifications that surface personalized savings opportunities.",
    },
    {
        "id": "pipe-002",
        "name": "Instant Account Opening v2",
        "product_line": "checking",
        "stage": "testing",
        "owner": "Product - Digital Onboarding",
        "target_date": "2026-06-01",
        "priority": "critical",
        "confidence_score": 0.91,
        "description": "Sub-3-minute account opening with biometric identity verification.",
    },
    {
        "id": "pipe-003",
        "name": "PFI Cross-Sell Engine",
        "product_line": "investments",
        "stage": "discovery",
        "owner": "Product - Wealth",
        "target_date": "2026-10-01",
        "priority": "medium",
        "confidence_score": 0.55,
        "description": "Rule-based cross-sell trigger model for primary financial institution conversion.",
    },
    {
        "id": "pipe-004",
        "name": "HELOC Digital Close",
        "product_line": "lending",
        "stage": "ideation",
        "owner": "Product - Lending",
        "target_date": "2026-12-01",
        "priority": "low",
        "confidence_score": 0.38,
        "description": "Fully digital closing flow for home equity lines of credit.",
    },
    {
        "id": "pipe-005",
        "name": "Rewards Wallet Integration",
        "product_line": "cards",
        "stage": "launched",
        "owner": "Product - Cards",
        "target_date": "2026-04-01",
        "priority": "high",
        "confidence_score": 1.0,
        "description": "Unified rewards wallet across credit card and checking products.",
    },
    {
        "id": "pipe-006",
        "name": "Voice Banking Assistant",
        "product_line": "digital",
        "stage": "development",
        "owner": "Product - Digital Experience",
        "target_date": "2026-08-15",
        "priority": "medium",
        "confidence_score": 0.70,
        "description": "Alexa/Google voice banking with balance, transfer, and bill-pay support.",
    },
    {
        "id": "pipe-007",
        "name": "Student Checking Acquisition",
        "product_line": "checking",
        "stage": "testing",
        "owner": "Product - Segments",
        "target_date": "2026-06-30",
        "priority": "high",
        "confidence_score": 0.88,
        "description": "Campus-targeted checking product with fee waivers and financial literacy tools.",
    },
    {
        "id": "pipe-008",
        "name": "Business Banking Dashboard",
        "product_line": "business",
        "stage": "discovery",
        "owner": "Product - SMB",
        "target_date": "2026-11-01",
        "priority": "medium",
        "confidence_score": 0.61,
        "description": "Unified cash flow dashboard for small business owners with AP/AR insights.",
    },
]

_VALID_STAGES = {"ideation", "discovery", "development", "testing", "launched"}
_VALID_PRODUCT_LINES = {"savings", "checking", "lending", "investments", "cards", "digital", "business"}


# ---------------------------------------------------------------------------
# Seed data — product roadmap
# ---------------------------------------------------------------------------

_ROADMAP_SEED: list[dict] = [
    {
        "id": "road-001",
        "initiative": "Digital Onboarding Overhaul",
        "product_line": "checking",
        "quarter": "Q2-2026",
        "status": "in_progress",
        "priority": "critical",
        "theme": "acquisition",
        "owner": "Product - Digital Onboarding",
        "dependencies": ["Identity Verification API", "Core Banking Upgrade"],
        "kpi_target": "App completion rate +8 pp",
        "effort_weeks": 14,
    },
    {
        "id": "road-002",
        "initiative": "PFI Activation Campaign Suite",
        "product_line": "investments",
        "quarter": "Q3-2026",
        "status": "planned",
        "priority": "high",
        "theme": "retention",
        "owner": "Product - Wealth",
        "dependencies": ["CRM Integration", "Behavioral Event Streaming"],
        "kpi_target": "PFI conversion +3 pp",
        "effort_weeks": 10,
    },
    {
        "id": "road-003",
        "initiative": "AI Personalization Engine",
        "product_line": "digital",
        "quarter": "Q3-2026",
        "status": "planned",
        "priority": "high",
        "theme": "engagement",
        "owner": "Product - Digital Experience",
        "dependencies": ["ML Platform", "Data Lake Phase 2"],
        "kpi_target": "Engagement index +15%",
        "effort_weeks": 18,
    },
    {
        "id": "road-004",
        "initiative": "HELOC Digital Close",
        "product_line": "lending",
        "quarter": "Q4-2026",
        "status": "planned",
        "priority": "medium",
        "theme": "acquisition",
        "owner": "Product - Lending",
        "dependencies": ["E-Signature v3", "Title Insurance API"],
        "kpi_target": "Lending funnel CVR +5 pp",
        "effort_weeks": 20,
    },
    {
        "id": "road-005",
        "initiative": "Instant Account Opening v2",
        "product_line": "checking",
        "quarter": "Q2-2026",
        "status": "in_progress",
        "priority": "critical",
        "theme": "acquisition",
        "owner": "Product - Digital Onboarding",
        "dependencies": ["Biometric SDK"],
        "kpi_target": "Time-to-fund < 3 min",
        "effort_weeks": 8,
    },
    {
        "id": "road-006",
        "initiative": "Student Segment Launch",
        "product_line": "checking",
        "quarter": "Q2-2026",
        "status": "in_progress",
        "priority": "high",
        "theme": "acquisition",
        "owner": "Product - Segments",
        "dependencies": ["Campus Partnership Agreements"],
        "kpi_target": "18-24 HH share +2 pp",
        "effort_weeks": 6,
    },
    {
        "id": "road-007",
        "initiative": "Voice Banking MVP",
        "product_line": "digital",
        "quarter": "Q3-2026",
        "status": "planned",
        "priority": "medium",
        "theme": "engagement",
        "owner": "Product - Digital Experience",
        "dependencies": ["NLP Platform", "Core Banking API v3"],
        "kpi_target": "Digital NPS +4 points",
        "effort_weeks": 12,
    },
    {
        "id": "road-008",
        "initiative": "SMB Cash Flow Dashboard",
        "product_line": "business",
        "quarter": "Q4-2026",
        "status": "planned",
        "priority": "medium",
        "theme": "retention",
        "owner": "Product - SMB",
        "dependencies": ["QuickBooks Integration", "Plaid v3"],
        "kpi_target": "SMB retention +4 pp",
        "effort_weeks": 16,
    },
]

_VALID_QUARTERS = {"Q1-2026", "Q2-2026", "Q3-2026", "Q4-2026"}
_VALID_THEMES = {"acquisition", "retention", "engagement"}


# ---------------------------------------------------------------------------
# Seed data — testing velocity
# ---------------------------------------------------------------------------

_TESTING_VELOCITY_SEED: dict = {
    "30d": {
        "tests_run": 12,
        "tests_won": 5,
        "tests_inconclusive": 3,
        "tests_lost": 4,
        "avg_lift_pct": 8.4,
        "avg_duration_days": 18.2,
        "top_winning_test": "Homepage CTA Color — +22% CVR",
        "top_channel": "digital",
    },
    "60d": {
        "tests_run": 24,
        "tests_won": 10,
        "tests_inconclusive": 7,
        "tests_lost": 7,
        "avg_lift_pct": 7.1,
        "avg_duration_days": 19.8,
        "top_winning_test": "Offer Personalization Variant B — +18% activation",
        "top_channel": "digital",
    },
    "90d": {
        "tests_run": 38,
        "tests_won": 15,
        "tests_inconclusive": 12,
        "tests_lost": 11,
        "avg_lift_pct": 6.8,
        "avg_duration_days": 20.5,
        "top_winning_test": "Streamlined App Form — +15% completion",
        "top_channel": "sem",
    },
}

# Baseline: rolling 90d average from prior period (6 months ago)
_TESTING_VELOCITY_BASELINE: dict = {
    "30d": {"tests_run": 8, "win_rate": 0.33, "avg_lift_pct": 5.2},
    "60d": {"tests_run": 16, "win_rate": 0.35, "avg_lift_pct": 5.8},
    "90d": {"tests_run": 28, "win_rate": 0.36, "avg_lift_pct": 6.1},
}


# ---------------------------------------------------------------------------
# Query functions
# ---------------------------------------------------------------------------

def get_product_pipeline(
    stage: str | None = None,
    product_line: str | None = None,
) -> dict:
    """Return product pipeline items, optionally filtered by stage and product_line."""
    items = list(_PIPELINE_SEED)

    if stage:
        items = [i for i in items if i["stage"] == stage]
    if product_line:
        items = [i for i in items if i["product_line"] == product_line]

    stage_counts: dict[str, int] = {s: 0 for s in _VALID_STAGES}
    for item in _PIPELINE_SEED:
        if item["stage"] in stage_counts:
            stage_counts[item["stage"]] += 1

    return {
        "items": items,
        "total": len(items),
        "stage_counts": stage_counts,
        "as_of": datetime.utcnow(),
    }


def get_product_roadmap(
    quarter: str | None = None,
    product_line: str | None = None,
    theme: str | None = None,
) -> dict:
    """Return roadmap initiatives, optionally filtered by quarter, product_line, or theme."""
    items = list(_ROADMAP_SEED)

    if quarter:
        items = [i for i in items if i["quarter"] == quarter]
    if product_line:
        items = [i for i in items if i["product_line"] == product_line]
    if theme:
        items = [i for i in items if i["theme"] == theme]

    by_quarter: dict[str, list[str]] = {}
    for item in items:
        by_quarter.setdefault(item["quarter"], []).append(item["initiative"])

    total_effort = sum(i["effort_weeks"] for i in items)

    return {
        "items": items,
        "total": len(items),
        "by_quarter": by_quarter,
        "total_effort_weeks": total_effort,
        "as_of": datetime.utcnow(),
    }


def get_testing_velocity(
    period: Literal["30d", "60d", "90d"] = "30d",
) -> dict:
    """Return A/B testing velocity metrics with baseline comparison.

    Computes win_rate and delta vs baseline for the requested period window.
    """
    data = _TESTING_VELOCITY_SEED.get(period, _TESTING_VELOCITY_SEED["30d"])
    baseline = _TESTING_VELOCITY_BASELINE.get(period, _TESTING_VELOCITY_BASELINE["30d"])

    tests_run = data["tests_run"]
    tests_won = data["tests_won"]
    win_rate = tests_won / tests_run if tests_run > 0 else 0.0

    baseline_tests = baseline["tests_run"]
    baseline_win_rate = baseline["win_rate"]
    baseline_lift = baseline["avg_lift_pct"]

    tests_run_delta = tests_run - baseline_tests
    tests_run_delta_pct = (tests_run_delta / baseline_tests * 100) if baseline_tests > 0 else 0.0
    win_rate_delta = win_rate - baseline_win_rate
    lift_delta = data["avg_lift_pct"] - baseline_lift

    return {
        "period": period,
        "tests_run": tests_run,
        "tests_won": tests_won,
        "tests_inconclusive": data["tests_inconclusive"],
        "tests_lost": data["tests_lost"],
        "win_rate": round(win_rate, 4),
        "avg_lift_pct": data["avg_lift_pct"],
        "avg_duration_days": data["avg_duration_days"],
        "top_winning_test": data["top_winning_test"],
        "top_channel": data["top_channel"],
        # Baseline comparison
        "baseline_tests_run": baseline_tests,
        "baseline_win_rate": baseline_win_rate,
        "baseline_avg_lift_pct": baseline_lift,
        "tests_run_delta": tests_run_delta,
        "tests_run_delta_pct": round(tests_run_delta_pct, 1),
        "win_rate_delta": round(win_rate_delta, 4),
        "lift_delta": round(lift_delta, 2),
        "as_of": datetime.utcnow(),
    }


# ---------------------------------------------------------------------------
# Streamlit-cached wrappers  (load_*)
#
# Each wrapper follows the two-function pattern required for cache_metrics:
#   outer function (load_*)         — records every call (hit + miss)
#   inner function (_load_*_cached) — runs only on miss; records the miss
# ---------------------------------------------------------------------------

def load_product_pipeline(
    stage: str | None = None,
    product_line: str | None = None,
) -> dict:
    """Cached wrapper for get_product_pipeline."""
    cache_metrics.record_call("load_product_pipeline")
    return _load_product_pipeline_cached(stage, product_line)


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_product_pipeline_cached(stage: str | None, product_line: str | None) -> dict:
    cache_metrics.record_miss("load_product_pipeline")
    return get_product_pipeline(stage=stage, product_line=product_line)


# Preserve .clear so callers can still invalidate the cache.
load_product_pipeline.clear = _load_product_pipeline_cached.clear  # type: ignore[attr-defined]


def load_product_roadmap(
    quarter: str | None = None,
    product_line: str | None = None,
    theme: str | None = None,
) -> dict:
    """Cached wrapper for get_product_roadmap."""
    cache_metrics.record_call("load_product_roadmap")
    return _load_product_roadmap_cached(quarter, product_line, theme)


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_product_roadmap_cached(
    quarter: str | None,
    product_line: str | None,
    theme: str | None,
) -> dict:
    cache_metrics.record_miss("load_product_roadmap")
    return get_product_roadmap(quarter=quarter, product_line=product_line, theme=theme)


load_product_roadmap.clear = _load_product_roadmap_cached.clear  # type: ignore[attr-defined]


def load_testing_velocity(period: Literal["30d", "60d", "90d"] = "30d") -> dict:
    """Cached wrapper for get_testing_velocity."""
    cache_metrics.record_call("load_testing_velocity")
    return _load_testing_velocity_cached(period)


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_testing_velocity_cached(period: Literal["30d", "60d", "90d"]) -> dict:
    cache_metrics.record_miss("load_testing_velocity")
    return get_testing_velocity(period=period)


load_testing_velocity.clear = _load_testing_velocity_cached.clear  # type: ignore[attr-defined]
