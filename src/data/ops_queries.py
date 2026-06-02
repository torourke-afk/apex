"""Ops query functions.

Provides seed-data backed query layer for the Ops endpoints:
  - get_ops_calendar   — marketing operations calendar
  - get_ops_capacity   — team / resource capacity by channel
  - get_ops_health     — system health status
  - get_competitive_feed — latest competitive intelligence items

Approval queries are handled directly in the router via Directive ORM.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

import streamlit as st

from src.config.settings import APEX_DATA_REFRESH_INTERVAL_SECONDS, APEX_DEBUG_MODE
from src.data import cache_metrics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Seed data — ops calendar
# ---------------------------------------------------------------------------

_CALENDAR_SEED: list[dict] = [
    {
        "id": "cal-001",
        "title": "Q2 SEM Campaign Launch",
        "event_type": "campaign_launch",
        "date": "2026-05-12",
        "channel": "sem",
        "owner": "Media - Paid Search",
        "status": "scheduled",
        "description": "Spring checking account acquisition push across all Google & Bing markets.",
    },
    {
        "id": "cal-002",
        "title": "Creative Asset Review — Mortgage",
        "event_type": "creative_review",
        "date": "2026-05-09",
        "channel": "display",
        "owner": "Creative - Lending",
        "status": "scheduled",
        "description": "Final stakeholder review of Q2 mortgage display creatives before trafficking.",
    },
    {
        "id": "cal-003",
        "title": "Budget Reallocation Deadline",
        "event_type": "deadline",
        "date": "2026-05-15",
        "channel": "all",
        "owner": "Finance - Marketing",
        "status": "scheduled",
        "description": "Last day to submit Q2 channel budget reallocations before system freeze.",
    },
    {
        "id": "cal-004",
        "title": "Monthly Performance Review",
        "event_type": "review",
        "date": "2026-05-20",
        "channel": "all",
        "owner": "Analytics",
        "status": "scheduled",
        "description": "Cross-channel April performance retrospective with channel leads.",
    },
    {
        "id": "cal-005",
        "title": "SEO Content Sprint Kickoff",
        "event_type": "planning",
        "date": "2026-05-13",
        "channel": "seo",
        "owner": "Content - SEO",
        "status": "scheduled",
        "description": "Q3 organic content planning session — 40 articles across savings & checking.",
    },
    {
        "id": "cal-006",
        "title": "Paid Social A/B Test Launch",
        "event_type": "campaign_launch",
        "date": "2026-05-14",
        "channel": "paid_social",
        "owner": "Media - Paid Social",
        "status": "scheduled",
        "description": "Three-cell creative test: static vs. carousel vs. video for checking product.",
    },
    {
        "id": "cal-007",
        "title": "LLM Visibility Audit",
        "event_type": "review",
        "date": "2026-05-22",
        "channel": "llm",
        "owner": "Digital - AI Strategy",
        "status": "scheduled",
        "description": "Bi-monthly LLM mention scoring across GPT, Gemini, and Perplexity surfaces.",
    },
    {
        "id": "cal-008",
        "title": "Q2 Campaign Post-Launch QA",
        "event_type": "review",
        "date": "2026-05-16",
        "channel": "sem",
        "owner": "Media - Paid Search",
        "status": "completed",
        "description": "Pixel verification, landing page QA, and initial spend pacing check.",
    },
]


def get_ops_calendar(
    *,
    month: str | None = None,
    channel: str | None = None,
    event_type: str | None = None,
) -> dict:
    """Return marketing ops calendar filtered by optional month/channel/event_type."""
    items = list(_CALENDAR_SEED)

    if month:
        items = [i for i in items if i["date"].startswith(month)]
    if channel and channel != "all":
        items = [i for i in items if i["channel"] == channel or i["channel"] == "all"]
    if event_type:
        items = [i for i in items if i["event_type"] == event_type]

    return {
        "items": items,
        "total": len(items),
        "as_of": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# Seed data — capacity
# ---------------------------------------------------------------------------

_CAPACITY_SEED: list[dict] = [
    {
        "id": "cap-001",
        "team": "Media - Paid Search",
        "channel": "sem",
        "period": "2026-05",
        "allocated_hours": 160,
        "used_hours": 112,
        "available_hours": 48,
        "utilization_pct": 0.70,
        "projects": ["Q2 SEM Launch", "Keyword Expansion", "Quality Score Optimization"],
    },
    {
        "id": "cap-002",
        "team": "Media - Paid Social",
        "channel": "paid_social",
        "period": "2026-05",
        "allocated_hours": 140,
        "used_hours": 126,
        "available_hours": 14,
        "utilization_pct": 0.90,
        "projects": ["A/B Test Launch", "Audience Refresh", "Creative Rotation"],
    },
    {
        "id": "cap-003",
        "team": "Content - SEO",
        "channel": "seo",
        "period": "2026-05",
        "allocated_hours": 200,
        "used_hours": 80,
        "available_hours": 120,
        "utilization_pct": 0.40,
        "projects": ["Q3 Content Sprint", "Backlink Outreach"],
    },
    {
        "id": "cap-004",
        "team": "Creative - Display",
        "channel": "display",
        "period": "2026-05",
        "allocated_hours": 120,
        "used_hours": 108,
        "available_hours": 12,
        "utilization_pct": 0.90,
        "projects": ["Mortgage Creative Review", "Brand Refresh Banners"],
    },
    {
        "id": "cap-005",
        "team": "Analytics",
        "channel": "all",
        "period": "2026-05",
        "allocated_hours": 180,
        "used_hours": 90,
        "available_hours": 90,
        "utilization_pct": 0.50,
        "projects": ["Monthly Performance Review", "Attribution Modeling", "Dashboard Updates"],
    },
    {
        "id": "cap-006",
        "team": "Digital - AI Strategy",
        "channel": "llm",
        "period": "2026-05",
        "allocated_hours": 80,
        "used_hours": 32,
        "available_hours": 48,
        "utilization_pct": 0.40,
        "projects": ["LLM Visibility Audit", "Prompt Optimization"],
    },
]


def get_ops_capacity(
    *,
    period: str | None = None,
    channel: str | None = None,
    team: str | None = None,
) -> dict:
    """Return team capacity filtered by optional period/channel/team."""
    items = list(_CAPACITY_SEED)

    if period:
        items = [i for i in items if i["period"] == period]
    if channel and channel != "all":
        items = [i for i in items if i["channel"] == channel or i["channel"] == "all"]
    if team:
        low = team.lower()
        items = [i for i in items if low in i["team"].lower()]

    total_allocated = sum(i["allocated_hours"] for i in items)
    total_used = sum(i["used_hours"] for i in items)
    avg_utilization = (total_used / total_allocated) if total_allocated > 0 else 0.0

    return {
        "items": items,
        "total": len(items),
        "total_allocated_hours": total_allocated,
        "total_used_hours": total_used,
        "avg_utilization_pct": round(avg_utilization, 4),
        "as_of": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# Seed data — health
# ---------------------------------------------------------------------------

_HEALTH_SEED: list[dict] = [
    {
        "name": "Database",
        "status": "healthy",
        "last_checked": "2026-05-08T10:00:00Z",
        "message": "All queries responding within SLA (p99 < 50ms).",
    },
    {
        "name": "Alert Engine",
        "status": "healthy",
        "last_checked": "2026-05-08T09:55:00Z",
        "message": "Last evaluation cycle completed in 1.2s. 0 rule errors.",
    },
    {
        "name": "SEM Data Pipeline",
        "status": "healthy",
        "last_checked": "2026-05-08T09:50:00Z",
        "message": "Google Ads & Bing feeds current. Last sync: 09:45 UTC.",
    },
    {
        "name": "Competitive Feed",
        "status": "healthy",
        "last_checked": "2026-05-08T09:45:00Z",
        "message": "12 new signals ingested in last 24h.",
    },
    {
        "name": "Simulator Engine",
        "status": "healthy",
        "last_checked": "2026-05-08T09:40:00Z",
        "message": "Idle. Last scenario run 4h ago.",
    },
    {
        "name": "Scheduler (APScheduler)",
        "status": "healthy",
        "last_checked": "2026-05-08T10:00:00Z",
        "message": "All 3 background jobs running on schedule.",
    },
]


def get_ops_health() -> dict:
    """Return system health status across all components."""
    components = list(_HEALTH_SEED)

    # Derive overall status: unhealthy > degraded > healthy
    statuses = {c["status"] for c in components}
    if "unhealthy" in statuses:
        overall = "unhealthy"
    elif "degraded" in statuses:
        overall = "degraded"
    else:
        overall = "healthy"

    return {
        "overall_status": overall,
        "components": components,
        "component_count": len(components),
        "as_of": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# Seed data — competitive feed
# ---------------------------------------------------------------------------

_COMPETITIVE_FEED_SEED: list[dict] = [
    {
        "id": "cf-001",
        "competitor": "Chase",
        "category": "promotion",
        "headline": "Chase launches $900 checking bonus for new customers",
        "summary": (
            "Chase increased its checking account welcome bonus to $900 (from $700) "
            "for new customers who complete qualifying direct deposits. "
            "Likely response to KeyBank's $400 offer expansion."
        ),
        "source": "chase.com",
        "detected_at": "2026-05-07T14:22:00Z",
        "impact": "high",
        "tags": ["checking", "acquisition", "bonus", "direct-deposit"],
    },
    {
        "id": "cf-002",
        "competitor": "Huntington",
        "category": "product",
        "headline": "Huntington introduces 'Standby Cash' expansion to 21 new markets",
        "summary": (
            "Huntington expanded its Standby Cash small-dollar credit product to 21 additional "
            "markets, directly competing with Fifth Third's retail banking footprint in the Midwest."
        ),
        "source": "huntington.com",
        "detected_at": "2026-05-06T09:10:00Z",
        "impact": "high",
        "tags": ["product", "credit", "expansion", "midwest"],
    },
    {
        "id": "cf-003",
        "competitor": "KeyBank",
        "category": "campaign",
        "headline": "KeyBank ramps up YouTube pre-roll for home equity messaging",
        "summary": (
            "KeyBank increased YouTube spend by an estimated 35% MoM targeting home equity "
            "search and content audiences — a direct play against Fifth Third's HELOC pipeline."
        ),
        "source": "pathmatics",
        "detected_at": "2026-05-05T16:45:00Z",
        "impact": "medium",
        "tags": ["campaign", "video", "heloc", "youtube"],
    },
    {
        "id": "cf-004",
        "competitor": "PNC",
        "category": "pricing",
        "headline": "PNC raises HYSA rate to 4.60% APY",
        "summary": (
            "PNC's High Yield Savings Account rate increased from 4.35% to 4.60% APY, "
            "narrowing the gap vs. online-only banks and intensifying rate competition "
            "in the mass-affluent segment."
        ),
        "source": "pnc.com",
        "detected_at": "2026-05-04T11:30:00Z",
        "impact": "medium",
        "tags": ["savings", "pricing", "rate", "hysa"],
    },
    {
        "id": "cf-005",
        "competitor": "Ally",
        "category": "channel",
        "headline": "Ally increases paid search investment in non-branded checking terms",
        "summary": (
            "Ally Bank's share of voice in 'best checking account' and 'free checking' "
            "terms rose 12 pp in April, according to SpyFu data — likely testing acquisition "
            "efficiency ahead of a product refresh."
        ),
        "source": "spyfu",
        "detected_at": "2026-05-03T08:00:00Z",
        "impact": "medium",
        "tags": ["sem", "checking", "share-of-voice", "competitive-bidding"],
    },
    {
        "id": "cf-006",
        "competitor": "US Bancorp",
        "category": "product",
        "headline": "US Bank Smartly Checking adds 4% APY on balances up to $5K",
        "summary": (
            "US Bank's Smartly Checking now earns 4.0% APY on balances up to $5,000 "
            "when paired with a US Bank credit card — a compelling bundle for mass-market customers."
        ),
        "source": "usbank.com",
        "detected_at": "2026-05-02T13:15:00Z",
        "impact": "high",
        "tags": ["checking", "product", "interest-bearing", "bundle"],
    },
    {
        "id": "cf-007",
        "competitor": "Wells Fargo",
        "category": "campaign",
        "headline": "Wells Fargo reactivates TV spend for 'Life Moments' brand campaign",
        "summary": (
            "Wells Fargo resumed national TV advertising with a new lifecycle-focused brand "
            "campaign after a 6-month hiatus following regulatory settlements. "
            "Linear TV share of voice up 8 pp in May."
        ),
        "source": "ispot.tv",
        "detected_at": "2026-05-01T17:50:00Z",
        "impact": "low",
        "tags": ["brand", "tv", "campaign", "lifecycle"],
    },
]


def get_competitive_feed(
    *,
    competitor: str | None = None,
    category: str | None = None,
    impact: str | None = None,
    limit: int = 20,
) -> dict:
    """Return competitive feed items filtered by optional competitor/category/impact."""
    items = list(_COMPETITIVE_FEED_SEED)

    if competitor:
        low = competitor.lower()
        items = [i for i in items if low in i["competitor"].lower()]
    if category:
        items = [i for i in items if i["category"] == category]
    if impact:
        items = [i for i in items if i["impact"] == impact]

    items = items[:limit]

    return {
        "items": items,
        "total": len(items),
        "as_of": datetime.now(timezone.utc),
    }


# ---------------------------------------------------------------------------
# Streamlit-cached wrappers  (load_*)
# ---------------------------------------------------------------------------

def load_ops_calendar(
    *,
    month: str | None = None,
    channel: str | None = None,
    event_type: str | None = None,
) -> dict:
    """Cached wrapper for get_ops_calendar."""
    cache_metrics.record_call("load_ops_calendar")
    return _load_ops_calendar_cached(month, channel, event_type)


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_ops_calendar_cached(
    month: str | None,
    channel: str | None,
    event_type: str | None,
) -> dict:
    cache_metrics.record_miss("load_ops_calendar")
    return get_ops_calendar(month=month, channel=channel, event_type=event_type)


load_ops_calendar.clear = _load_ops_calendar_cached.clear  # type: ignore[attr-defined]


def load_ops_capacity(
    *,
    period: str | None = None,
    channel: str | None = None,
    team: str | None = None,
) -> dict:
    """Cached wrapper for get_ops_capacity."""
    cache_metrics.record_call("load_ops_capacity")
    return _load_ops_capacity_cached(period, channel, team)


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_ops_capacity_cached(
    period: str | None,
    channel: str | None,
    team: str | None,
) -> dict:
    cache_metrics.record_miss("load_ops_capacity")
    return get_ops_capacity(period=period, channel=channel, team=team)


load_ops_capacity.clear = _load_ops_capacity_cached.clear  # type: ignore[attr-defined]


def load_ops_health() -> dict:
    """Cached wrapper for get_ops_health."""
    cache_metrics.record_call("load_ops_health")
    return _load_ops_health_cached()


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_ops_health_cached() -> dict:
    cache_metrics.record_miss("load_ops_health")
    return get_ops_health()


load_ops_health.clear = _load_ops_health_cached.clear  # type: ignore[attr-defined]


def load_competitive_feed(
    *,
    competitor: str | None = None,
    category: str | None = None,
    impact: str | None = None,
    limit: int = 20,
) -> dict:
    """Cached wrapper for get_competitive_feed."""
    cache_metrics.record_call("load_competitive_feed")
    return _load_competitive_feed_cached(competitor, category, impact, limit)


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_competitive_feed_cached(
    competitor: str | None,
    category: str | None,
    impact: str | None,
    limit: int,
) -> dict:
    cache_metrics.record_miss("load_competitive_feed")
    return get_competitive_feed(competitor=competitor, category=category, impact=impact, limit=limit)


load_competitive_feed.clear = _load_competitive_feed_cached.clear  # type: ignore[attr-defined]
