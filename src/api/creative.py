"""Creative Performance API endpoints.

GET /api/creative/overview — creative asset performance summary (top creative units)
GET /api/creative/assets   — list of creative assets with metrics
GET /api/creative/themes   — message theme resonance scores
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/creative", tags=["creative"])


# ---------------------------------------------------------------------------
# Seed / fallback data
# ---------------------------------------------------------------------------

_CREATIVE_ASSETS = [
    {
        "name": "Summer Freedom",
        "theme": "Lifestyle · Aspirational",
        "format": "VIDEO 15s",
        "fatigue": "FRESH",
        "ctr": 0.032,
        "cvr": 0.041,
        "spend": 820_000,
        "impressions": 25_625_000,
        "clicks": 820_000,
        "conversions": 33_620,
        "thumb_gradient": "linear-gradient(135deg, #1a3a4a, #0d7d6a)",
    },
    {
        "name": "Rate Lock Hero",
        "theme": "Product · Rate",
        "format": "STATIC",
        "fatigue": "FRESH",
        "ctr": 0.028,
        "cvr": 0.038,
        "spend": 640_000,
        "impressions": 22_857_143,
        "clicks": 640_000,
        "conversions": 24_320,
        "thumb_gradient": "linear-gradient(135deg, #2a1a4a, #6a0d7d)",
    },
    {
        "name": "Family Moments",
        "theme": "Life Event · Family",
        "format": "VIDEO 30s",
        "fatigue": "WATCH",
        "ctr": 0.024,
        "cvr": 0.032,
        "spend": 1_100_000,
        "impressions": 45_833_333,
        "clicks": 1_100_000,
        "conversions": 35_200,
        "thumb_gradient": "linear-gradient(135deg, #4a3a1a, #7d6a0d)",
    },
    {
        "name": "Mobile First",
        "theme": "Digital · App",
        "format": "CAROUSEL",
        "fatigue": "FRESH",
        "ctr": 0.021,
        "cvr": 0.029,
        "spend": 420_000,
        "impressions": 20_000_000,
        "clicks": 420_000,
        "conversions": 12_180,
        "thumb_gradient": "linear-gradient(135deg, #1a2a4a, #0d3a7d)",
    },
    {
        "name": "Community Roots",
        "theme": "Brand · Local",
        "format": "STATIC",
        "fatigue": "TIRED",
        "ctr": 0.016,
        "cvr": 0.021,
        "spend": 380_000,
        "impressions": 23_750_000,
        "clicks": 380_000,
        "conversions": 7_980,
        "thumb_gradient": "linear-gradient(135deg, #4a1a2a, #7d0d3a)",
    },
    {
        "name": "Smart Savings",
        "theme": "Product · Savings",
        "format": "VIDEO 15s",
        "fatigue": "WATCH",
        "ctr": 0.014,
        "cvr": 0.018,
        "spend": 290_000,
        "impressions": 20_714_286,
        "clicks": 290_000,
        "conversions": 5_220,
        "thumb_gradient": "linear-gradient(135deg, #2a4a1a, #3a7d0d)",
    },
]

_MESSAGE_THEMES = [
    {"name": "Rate Competitiveness", "score": 92},
    {"name": "Digital Convenience", "score": 87},
    {"name": "Local Community", "score": 76},
    {"name": "Financial Wellness", "score": 71},
    {"name": "Life Stage Triggers", "score": 68},
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/overview")
def creative_overview(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return creative asset performance summary — top creative units by CTR."""
    try:
        assets = _CREATIVE_ASSETS
        total_spend = sum(a["spend"] for a in assets)
        total_impressions = sum(a["impressions"] for a in assets)
        total_clicks = sum(a["clicks"] for a in assets)
        total_conversions = sum(a["conversions"] for a in assets)
        blended_ctr = total_clicks / total_impressions if total_impressions else 0
        blended_cvr = total_conversions / total_clicks if total_clicks else 0

        return {
            "total_assets": len(assets),
            "total_spend": total_spend,
            "blended_ctr": round(blended_ctr, 4),
            "blended_cvr": round(blended_cvr, 4),
            "total_impressions": total_impressions,
            "total_conversions": total_conversions,
            "assets": assets,
        }
    except Exception as exc:
        logger.warning("creative_overview fallback: %s", exc)
        return {
            "total_assets": 0,
            "total_spend": 0,
            "blended_ctr": 0,
            "blended_cvr": 0,
            "total_impressions": 0,
            "total_conversions": 0,
            "assets": [],
        }


@router.get("/assets")
def creative_assets(
    sort_by: str = Query(default="ctr", description="Sort field: ctr, cvr, spend"),
    fatigue: str | None = Query(default=None, description="Filter by fatigue: FRESH, WATCH, TIRED"),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return list of creative assets with performance metrics."""
    try:
        assets = list(_CREATIVE_ASSETS)

        # Apply fatigue filter
        if fatigue:
            fatigue_values = [f.strip().upper() for f in fatigue.split(",")]
            assets = [a for a in assets if a["fatigue"] in fatigue_values]

        # Sort
        if sort_by in ("ctr", "cvr", "spend"):
            assets = sorted(assets, key=lambda a: a[sort_by], reverse=True)

        return {"assets": assets, "count": len(assets)}
    except Exception as exc:
        logger.warning("creative_assets fallback: %s", exc)
        return {"assets": [], "count": 0}


@router.get("/themes")
def creative_themes(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return message theme resonance scores."""
    try:
        return {"themes": _MESSAGE_THEMES}
    except Exception as exc:
        logger.warning("creative_themes fallback: %s", exc)
        return {"themes": []}
