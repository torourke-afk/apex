"""Media / Channel Performance API endpoints.

GET /api/media/channels    — channel performance data for all 6 media channels
GET /api/media/saturation  — saturation curve parameters per channel
GET /api/media/efficiency  — efficiency frontier bubble chart data
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

media_router = APIRouter(prefix="/api/media", tags=["media"])


# ---------------------------------------------------------------------------
# Seed / fallback data
# ---------------------------------------------------------------------------

_CHANNELS = [
    {
        "name": "SEM",
        "color": "var(--color-sem)",
        "spend": 4_200_000,
        "cpihh": 286,
        "cvr": 0.048,
        "roas": 4.6,
        "trend": [3.8, 4.0, 4.1, 4.3, 4.2, 4.5, 4.4, 4.6],
    },
    {
        "name": "Brand TV",
        "color": "var(--color-brand-tv)",
        "spend": 5_600_000,
        "cpihh": 420,
        "cvr": 0.012,
        "roas": 2.8,
        "trend": [2.2, 2.4, 2.5, 2.6, 2.7, 2.6, 2.9, 2.8],
    },
    {
        "name": "Social",
        "color": "var(--color-social)",
        "spend": 2_100_000,
        "cpihh": 312,
        "cvr": 0.031,
        "roas": 3.7,
        "trend": [3.0, 3.2, 3.1, 3.4, 3.3, 3.5, 3.6, 3.7],
    },
    {
        "name": "Display",
        "color": "var(--color-display)",
        "spend": 1_800_000,
        "cpihh": 298,
        "cvr": 0.039,
        "roas": 3.9,
        "trend": [3.2, 3.4, 3.5, 3.6, 3.7, 3.8, 3.8, 3.9],
    },
    {
        "name": "Direct Mail",
        "color": "var(--color-direct-mail)",
        "spend": 3_400_000,
        "cpihh": 345,
        "cvr": 0.024,
        "roas": 3.5,
        "trend": [3.0, 3.1, 3.2, 3.3, 3.4, 3.3, 3.5, 3.5],
    },
    {
        "name": "Affiliate",
        "color": "var(--color-affiliate)",
        "spend": 900_000,
        "cpihh": 380,
        "cvr": 0.018,
        "roas": 2.1,
        "trend": [1.8, 1.9, 2.0, 1.9, 2.0, 2.1, 2.0, 2.1],
    },
]

_SATURATION_CURVES = [
    {"label": "SEM", "color": "var(--color-sem)", "k": 3.2, "max_y": 0.92, "dot_x": 0.55},
    {"label": "Social", "color": "var(--color-social)", "k": 2.6, "max_y": 0.85, "dot_x": 0.40},
    {"label": "Brand", "color": "var(--color-brand-tv)", "k": 1.8, "max_y": 0.78, "dot_x": 0.70},
]

_EFFICIENCY_BUBBLES = [
    {"label": "SEM", "x": 0.24, "y": 4.6, "r": 22, "color": "var(--color-sem)"},
    {"label": "Brand", "x": 0.32, "y": 2.8, "r": 28, "color": "var(--color-brand-tv)"},
    {"label": "Social", "x": 0.12, "y": 3.7, "r": 18, "color": "var(--color-social)"},
    {"label": "Mail", "x": 0.20, "y": 3.5, "r": 14, "color": "var(--color-direct-mail)"},
    {"label": "Display", "x": 0.10, "y": 3.9, "r": 12, "color": "var(--color-display)"},
    {"label": "Affiliate", "x": 0.05, "y": 2.1, "r": 10, "color": "var(--color-affiliate)"},
]

_PORTFOLIO_AVG_ROAS = 3.5


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@media_router.get("/channels")
def media_channels(
    channel: str | None = Query(default=None, description="Channel name filter"),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
):
    """Return channel performance data for all 6 media channels."""
    try:
        channels = list(_CHANNELS)

        # Apply channel name filter
        if channel:
            filter_values = [c.strip().lower() for c in channel.split(",")]
            channels = [
                ch for ch in channels if ch["name"].lower() in filter_values
            ]

        total_spend = sum(ch["spend"] for ch in channels)

        return {
            "channels": channels,
            "count": len(channels),
            "total_spend": total_spend,
        }
    except Exception as exc:
        logger.warning("media_channels fallback: %s", exc)
        return {"channels": [], "count": 0, "total_spend": 0}


@media_router.get("/saturation")
def media_saturation(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
):
    """Return saturation curve parameters for each channel."""
    try:
        return {"curves": _SATURATION_CURVES}
    except Exception as exc:
        logger.warning("media_saturation fallback: %s", exc)
        return {"curves": []}


@media_router.get("/efficiency")
def media_efficiency(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
):
    """Return efficiency frontier bubble chart data."""
    try:
        return {
            "bubbles": _EFFICIENCY_BUBBLES,
            "portfolio_avg_roas": _PORTFOLIO_AVG_ROAS,
        }
    except Exception as exc:
        logger.warning("media_efficiency fallback: %s", exc)
        return {"bubbles": [], "portfolio_avg_roas": 0}
