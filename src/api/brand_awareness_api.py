"""Brand Awareness Tracker API endpoints.

GET /api/brand-awareness/share-of-search — Share of Search time-series for configured peer set
GET /api/brand-awareness/peer-comparison — peer comparison table (latest period)
"""

from __future__ import annotations

import logging

import pandas as pd
from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/brand-awareness", tags=["brand-awareness"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _df_to_records(df: pd.DataFrame) -> list[dict]:
    if df is None or df.empty:
        return []
    records = df.to_dict(orient="records")
    # Convert date/Timestamp objects to ISO strings for JSON serialization
    for rec in records:
        for key, val in rec.items():
            if hasattr(val, "isoformat"):
                rec[key] = val.isoformat()
    return records


def _call_cached(fn, *args, **kwargs):
    """Call a function that may be wrapped with @st.cache_data."""
    try:
        return fn(*args, **kwargs)
    except Exception:
        underlying = getattr(fn, "__wrapped__", None)
        if underlying is not None:
            return underlying(*args, **kwargs)
        raise


def _get_default_config_json() -> str:
    """Return the default FITB tracker config as JSON string."""
    from src.data.brand_awareness import default_fitb_config, config_to_json

    return config_to_json(default_fitb_config())


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/share-of-search")
def share_of_search(
    geo: str = Query(default="US", description="Geography scope: US or DMA code"),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return Share of Search time-series for the configured peer set."""
    try:
        from src.data.brand_awareness import load_share_of_search

        config_json = _get_default_config_json()
        df = _call_cached(load_share_of_search, config_json, geo)
        return {"share_of_search": _df_to_records(df)}
    except Exception as exc:
        logger.warning("share_of_search fallback: %s", exc)
        return {"share_of_search": []}


@router.get("/peer-comparison")
def peer_comparison(
    geo: str = Query(default="US", description="Geography scope"),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return peer comparison table for the latest available period."""
    try:
        from src.data.brand_awareness import (
            load_msv_data,
            compute_peer_comparison,
        )

        config_json = _get_default_config_json()
        msv_df = _call_cached(load_msv_data, config_json)
        comparison_df = compute_peer_comparison(msv_df, geo=geo)
        return {"peer_comparison": _df_to_records(comparison_df)}
    except Exception as exc:
        logger.warning("peer_comparison fallback: %s", exc)
        return {"peer_comparison": []}
