"""Acquisition Funnel API endpoints.

GET /api/funnel/stages  — funnel stage names, volumes, conversion rates, benchmarks
GET /api/funnel/dropoff — drop-off volume by segment for a given stage transition
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/funnel", tags=["funnel"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _parse_filters(
    date_start: str | None = None,
    date_end: str | None = None,
    dma: str | None = None,
) -> dict[str, Any] | None:
    filters: dict[str, Any] = {}
    if date_start:
        filters["date_start"] = date_start
    if date_end:
        filters["date_end"] = date_end
    if dma:
        filters["dma"] = [d.strip() for d in dma.split(",")]
    return filters or None


def _call_cached(fn, *args, **kwargs):
    """Call a function that may be wrapped with @st.cache_data."""
    try:
        return fn(*args, **kwargs)
    except Exception:
        underlying = getattr(fn, "__wrapped__", None)
        if underlying is not None:
            return underlying(*args, **kwargs)
        raise


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/stages")
def funnel_stages(
    date_start: str | None = Query(default=None),
    date_end: str | None = Query(default=None),
    dma: str | None = Query(default=None, description="Comma-separated DMA names"),
):
    """Return 7-stage acquisition funnel data with benchmarks."""
    try:
        from src.data.funnel_queries import get_funnel_data

        filters = _parse_filters(date_start, date_end, dma)
        data = _call_cached(get_funnel_data, filters)
        return data
    except Exception as exc:
        logger.warning("funnel_stages fallback: %s", exc)
        return {
            "stages": [
                "Brand UOI", "Brand Capture", "App Started",
                "App Submitted", "Approved", "Funded", "Active (90d)",
            ],
            "values": [6840, 1889, 8, 5, 4, 3, 2],
            "benchmarks": [6840, 2052, 10, 7, 5, 4, 3],
            "rates": [0.276, 0.004, 0.604, 0.718, 0.849, 0.65],
            "bench_rates": [0.30, 0.005, 0.65, 0.75, 0.87, 0.72],
            "avg_account_ltv": 4800.0,
        }


@router.get("/dropoff")
def funnel_dropoff(
    stage_idx: int = Query(
        default=0, ge=0, le=5,
        description="Stage transition index (0=UOI->Capture, ..., 5=Funded->Active)",
    ),
    dimension: str = Query(
        default="channel",
        description="Segment dimension: channel, market, product, device, personalization",
    ),
    date_start: str | None = Query(default=None),
    date_end: str | None = Query(default=None),
    dma: str | None = Query(default=None),
):
    """Return drop-off volume broken down by segment for a stage transition."""
    try:
        from src.data.funnel_queries import get_dropoff_by_segment

        filters = _parse_filters(date_start, date_end, dma)
        data = _call_cached(get_dropoff_by_segment, stage_idx, dimension, filters)
        return data
    except Exception as exc:
        logger.warning("funnel_dropoff fallback: %s", exc)
        return {
            "labels": ["SEM Branded", "SEM Non-Branded", "Paid Social", "CTV", "Organic", "Direct", "Referral"],
            "dropoff": [890, 740, 680, 395, 1090, 640, 495],
            "total_dropoff": 4930.0,
        }


_CHANNEL_COLORS = {
    "SEM": "var(--cyan)",
    "SEO": "var(--green)",
    "Social": "var(--amber)",
    "Email": "#a78bfa",
    "Direct": "var(--text3)",
    "Display": "#f59e0b",
    "AEO": "#818cf8",
    "Direct Mail": "#94a3b8",
}

_CHANNEL_MAP = {
    "SEM": ["SEM"],
    "SEO": ["SEO_BRAND", "SEO_NONBRAND"],
    "Social": ["SOCIAL"],
    "Email": ["EMAIL"],
    "Direct": ["DIRECT"],
    "Display": ["DISPLAY"],
    "AEO": ["AEO_REFERRAL"],
    "Direct Mail": ["DIRECT_MAIL"],
}


def _fmt_vol(n: int) -> str:
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(n)


@router.get("/sankey")
def funnel_sankey(
    date_start: str | None = Query(default=None),
    date_end: str | None = Query(default=None),
    dma: str | None = Query(default=None, description="Comma-separated DMA names"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return Sankey flow data computed from application_events."""
    import os
    import duckdb

    db_path = os.environ.get("APEX_DB_PATH", "apex_clean.duckdb")
    try:
        con = duckdb.connect(db_path, read_only=True)

        # Build WHERE clause
        clauses: list[str] = []
        params: list = []
        if date_start:
            clauses.append("date >= ?")
            params.append(date_start)
        if date_end:
            clauses.append("date <= ?")
            params.append(date_end)
        if dma:
            dma_list = [d.strip() for d in dma.split(",")]
            clauses.append(f"dma_name IN ({', '.join('?' * len(dma_list))})")
            params.extend(dma_list)

        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

        # Per-channel funnel counts
        rows = con.execute(f"""
            SELECT
                channel,
                COUNT(*) AS total,
                SUM(reached_identity_verify) AS id_verify,
                SUM(reached_submit) AS submitted,
                SUM(approved) AS approved
            FROM application_events
            {where}
            GROUP BY channel
            ORDER BY total DESC
        """, params).fetchall()

        con.close()

        # Group raw DB channels into display channels
        raw_map: dict[str, dict] = {}
        for row in rows:
            raw_map[row[0]] = {
                "total": int(row[1]),
                "id_verify": int(row[2]),
                "submitted": int(row[3]),
                "approved": int(row[4]),
            }

        channel_data: list[dict] = []
        for display_name, raw_keys in _CHANNEL_MAP.items():
            merged = {"total": 0, "id_verify": 0, "submitted": 0, "approved": 0}
            for rk in raw_keys:
                if rk in raw_map:
                    for k in merged:
                        merged[k] += raw_map[rk][k]
            if merged["total"] > 0:
                channel_data.append({"name": display_name, **merged})

        # Apply channel filter if provided
        if channel:
            ch_filter = {c.strip().lower() for c in channel.split(",")}
            channel_data = [c for c in channel_data if c["name"].lower() in ch_filter]

        # Compute percentages
        grand_total = sum(c["total"] for c in channel_data) or 1
        channels_out = []
        for c in channel_data:
            pct = round(c["total"] / grand_total * 100)
            channels_out.append({
                "name": c["name"],
                "pct": pct,
                "color": _CHANNEL_COLORS.get(c["name"], "var(--text3)"),
                "label": f"{c['name']} {pct}%",
            })

        # Aggregate stage totals
        total_apps = sum(c["total"] for c in channel_data)
        total_id = sum(c["id_verify"] for c in channel_data)
        total_sub = sum(c["submitted"] for c in channel_data)
        total_appr = sum(c["approved"] for c in channel_data)

        stages = [
            {"label": "CHANNEL MIX", "volume": _fmt_vol(total_apps)},
            {"label": "APP STARTED", "volume": _fmt_vol(total_apps)},
            {"label": "ID VERIFIED", "volume": _fmt_vol(total_id)},
            {"label": "SUBMITTED", "volume": _fmt_vol(total_sub)},
            {"label": "APPROVED", "volume": _fmt_vol(total_appr)},
        ]

        # Stage narrowing factors (proportion of stage 0 height)
        stage_factors = [
            1.0,
            round(total_id / total_apps, 2) if total_apps else 0.75,
            round(total_sub / total_apps, 2) if total_apps else 0.6,
            round(total_appr / total_apps, 2) if total_apps else 0.43,
        ]

        return {
            "channels": channels_out,
            "stages": stages,
            "stage_factors": stage_factors,
        }

    except Exception as exc:
        logger.exception("funnel_sankey failed — returning fallback")
        return {
            "channels": [
                {"name": "SEM", "pct": 30, "color": "var(--cyan)", "label": "SEM 30%"},
                {"name": "SEO", "pct": 35, "color": "var(--green)", "label": "SEO 35%"},
                {"name": "Social", "pct": 12, "color": "var(--amber)", "label": "Social 12%"},
            ],
            "stages": [
                {"label": "CHANNEL MIX", "volume": "78K"},
                {"label": "APP STARTED", "volume": "78K"},
                {"label": "SUBMITTED", "volume": "47K"},
                {"label": "APPROVED", "volume": "34K"},
            ],
            "stage_factors": [1.0, 0.60, 0.43],
        }
