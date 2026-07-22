"""Modeling & Attribution API endpoints.

GET /api/modeling/attribution    — channel attribution results (modeled contribution)
GET /api/modeling/registry       — model registry (trained models, dates, accuracy)
GET /api/modeling/incrementality — incrementality test results
"""

from __future__ import annotations

import logging
from datetime import date, timedelta

from fastapi import APIRouter, Query

from src.data.seeds._dates import YESTERDAY

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/modeling", tags=["modeling"])

# Shift all hardcoded dates relative to the original anchor date
_ORIG_ANCHOR = date(2026, 7, 16)
_SHIFT = timedelta(days=(YESTERDAY - _ORIG_ANCHOR).days)


def _shift_date_str(iso_str: str) -> str:
    """Shift an ISO date string by _SHIFT days."""
    d = date.fromisoformat(iso_str) + _SHIFT
    return d.isoformat()


# ---------------------------------------------------------------------------
# Seed / fallback data
# ---------------------------------------------------------------------------

_ATTRIBUTION_BARS = [
    {"name": "SEM", "value": 0.41, "color": "var(--cyan)"},
    {"name": "BRAND", "value": 0.24, "color": "var(--green)"},
    {"name": "SOCIAL", "value": 0.18, "color": "var(--amber)"},
    {"name": "EMAIL", "value": 0.09, "color": "#7C8BFF"},
    {"name": "DIRECT", "value": 0.05, "color": "var(--text3)"},
    {"name": "AFFIL", "value": 0.03, "color": "var(--text3)"},
]

_MODEL_REGISTRY = [
    {
        "name": "MMM – National",
        "model_type": "Bayesian MMM",
        "r_squared": 0.94,
        "status": "LIVE",
        "trained_ago": "2 weeks ago",
        "last_trained": _shift_date_str("2026-07-02"),
        "version": "3.2.1",
    },
    {
        "name": "MTA – Digital",
        "model_type": "Shapley MTA",
        "r_squared": 0.91,
        "status": "LIVE",
        "trained_ago": "3 days ago",
        "last_trained": _shift_date_str("2026-07-13"),
        "version": "2.1.0",
    },
    {
        "name": "Geo Lift – DMA",
        "model_type": "Causal Impact",
        "r_squared": 0.88,
        "status": "LIVE",
        "trained_ago": "1 week ago",
        "last_trained": _shift_date_str("2026-07-09"),
        "version": "1.4.3",
    },
    {
        "name": "Saturation Response",
        "model_type": "Hill Function",
        "r_squared": 0.92,
        "status": "LIVE",
        "trained_ago": "5 days ago",
        "last_trained": _shift_date_str("2026-07-11"),
        "version": "2.0.0",
    },
    {
        "name": "Creative Scoring",
        "model_type": "Multi-armed",
        "r_squared": 0.85,
        "status": "LIVE",
        "trained_ago": "1 day ago",
        "last_trained": _shift_date_str("2026-07-15"),
        "version": "1.1.2",
    },
    {
        "name": "Retention Hazard",
        "model_type": "Cox PH",
        "r_squared": 0.89,
        "status": "LIVE",
        "trained_ago": "4 days ago",
        "last_trained": _shift_date_str("2026-07-12"),
        "version": "1.3.0",
    },
]

_INCREMENTALITY_TESTS = [
    {
        "name": "SEM Brand Holdout",
        "lift": 0.124,
        "method": "Geo randomized",
        "p_value": 0.003,
        "status": "COMPLETE",
        "start_date": _shift_date_str("2026-06-01"),
        "end_date": _shift_date_str("2026-06-30"),
    },
    {
        "name": "Social Video Uplift",
        "lift": 0.081,
        "method": "Ghost ads",
        "p_value": 0.012,
        "status": "COMPLETE",
        "start_date": _shift_date_str("2026-06-15"),
        "end_date": _shift_date_str("2026-07-10"),
    },
    {
        "name": "DM Reactivation",
        "lift": 0.067,
        "method": "RCT holdout",
        "p_value": 0.008,
        "status": "COMPLETE",
        "start_date": _shift_date_str("2026-05-20"),
        "end_date": _shift_date_str("2026-06-20"),
    },
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/attribution")
def modeling_attribution(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return channel attribution results (modeled incremental contribution)."""
    try:
        return {
            "channels": _ATTRIBUTION_BARS,
            "model_type": "Bayesian MMM + Shapley",
            "last_updated": YESTERDAY.isoformat(),
        }
    except Exception as exc:
        logger.warning("modeling_attribution fallback: %s", exc)
        return {"channels": [], "model_type": "", "last_updated": ""}


@router.get("/registry")
def modeling_registry(
    status: str | None = Query(default=None, description="Filter by status: LIVE, TRAINING, RETIRED"),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
):
    """Return model registry — trained models, dates, accuracy (R^2)."""
    try:
        models = list(_MODEL_REGISTRY)

        if status:
            status_values = [s.strip().upper() for s in status.split(",")]
            models = [m for m in models if m["status"] in status_values]

        return {"models": models, "count": len(models)}
    except Exception as exc:
        logger.warning("modeling_registry fallback: %s", exc)
        return {"models": [], "count": 0}


@router.get("/incrementality")
def modeling_incrementality(
    status: str | None = Query(default=None, description="Filter by status: COMPLETE, RUNNING, PLANNED"),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
):
    """Return incrementality test results."""
    try:
        tests = list(_INCREMENTALITY_TESTS)

        if status:
            status_values = [s.strip().upper() for s in status.split(",")]
            tests = [t for t in tests if t["status"] in status_values]

        return {"tests": tests, "count": len(tests)}
    except Exception as exc:
        logger.warning("modeling_incrementality fallback: %s", exc)
        return {"tests": [], "count": 0}
