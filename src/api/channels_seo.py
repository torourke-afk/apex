"""SEO channel API endpoints.

GET /api/channels/seo/rankings — keyword ranking table (filterable by category/period)
GET /api/channels/seo/traffic  — organic traffic by product category over time
"""

from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/channels/seo", tags=["channels-seo"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _df_to_records(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    return df.to_dict(orient="records")


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/rankings")
def seo_rankings(
    category: str | None = Query(
        default=None,
        description="Product category filter: checking, savings, mortgage, credit_card, auto_loan, personal_loan",
    ),
    period: str | None = Query(default=None, description="ISO week_start date"),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return SEO keyword rankings, optionally filtered by category and week."""
    try:
        from src.data.organic_loaders import load_seo_rankings

        df = load_seo_rankings(category=category, period=period)
        return {"rankings": _df_to_records(df)}
    except Exception as exc:
        logger.warning("seo_rankings fallback: %s", exc)
        return {"rankings": []}


@router.get("/traffic")
def seo_traffic(
    period: str | None = Query(default=None, description="ISO week_start date"),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return organic traffic by product category over time."""
    try:
        from src.data.organic_loaders import load_seo_traffic

        df = load_seo_traffic(period=period)
        return {"traffic": _df_to_records(df)}
    except Exception as exc:
        logger.warning("seo_traffic fallback: %s", exc)
        return {"traffic": []}
