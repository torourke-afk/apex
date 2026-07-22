"""Audience API endpoints.

GET /api/audience/segments    — audience segments with share, tags, and notes
GET /api/audience/top-markets — top DMA markets ranked by ROAS
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

audience_router = APIRouter(prefix="/api/audience", tags=["audience"])


# ---------------------------------------------------------------------------
# Seed / fallback data
# ---------------------------------------------------------------------------

_SEGMENTS = [
    {
        "name": "Young Professionals",
        "share": 0.34,
        "tag": "HIGH VALUE",
        "tag_color": "var(--green)",
        "note": "Checking + savings bundle",
    },
    {
        "name": "Families 30–45",
        "share": 0.28,
        "tag": "GROWING",
        "tag_color": "var(--cyan)",
        "note": "Mortgage cross-sell opportunity",
    },
    {
        "name": "Retirees 55+",
        "share": 0.22,
        "tag": "STABLE",
        "tag_color": "var(--text2)",
        "note": "CD + wealth management",
    },
    {
        "name": "Small Business",
        "share": 0.16,
        "tag": "EMERGING",
        "tag_color": "var(--amber)",
        "note": "Business checking pipeline",
    },
]

_TOP_MARKETS = [
    {"rank": 1, "name": "Cincinnati", "code": "DMA 515", "roas": 5.2, "funded": 2840},
    {"rank": 2, "name": "Chicago", "code": "DMA 602", "roas": 4.8, "funded": 3120},
    {"rank": 3, "name": "Columbus", "code": "DMA 535", "roas": 4.6, "funded": 1960},
    {"rank": 4, "name": "Indianapolis", "code": "DMA 527", "roas": 4.3, "funded": 1640},
    {"rank": 5, "name": "Detroit", "code": "DMA 505", "roas": 4.1, "funded": 1480},
    {"rank": 6, "name": "Louisville", "code": "DMA 529", "roas": 3.9, "funded": 1220},
]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@audience_router.get("/segments")
def audience_segments():
    """Return audience segments with share breakdown, tags, and notes."""
    try:
        return {"segments": _SEGMENTS, "count": len(_SEGMENTS)}
    except Exception as exc:
        logger.warning("audience_segments fallback: %s", exc)
        return {"segments": [], "count": 0}


@audience_router.get("/top-markets")
def audience_top_markets(
    dma: str | None = Query(default=None, description="Filter by DMA code, e.g. 'DMA 515'"),
):
    """Return top DMA markets ranked by ROAS."""
    try:
        markets = list(_TOP_MARKETS)

        if dma:
            dma_upper = dma.strip().upper()
            markets = [m for m in markets if dma_upper in m["code"].upper()]

        return {"markets": markets, "count": len(markets)}
    except Exception as exc:
        logger.warning("audience_top_markets fallback: %s", exc)
        return {"markets": [], "count": 0}
