"""SEM query functions (APE-89 deliverable, consumed by APE-93 API).

All functions query sem_keyword_groups JOIN sem_daily_performance and return
plain dicts suitable for Pydantic model construction. They return safe
zero/empty defaults when no data is present so callers never see 500s.

Tables (see seed_sem.py / test DDL):
  sem_keyword_groups    — id, keyword_group, match_type, intent_type,
                          market_segment, quality_score, is_active
  sem_daily_performance — id, keyword_group_id, date, impressions, clicks,
                          conversions, spend, cpc, ctr, cvr, cpl,
                          impression_share, vbb_margin_signal, quality_score
"""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_PERIOD_DAYS: dict[str, int] = {"7d": 7, "30d": 30, "60d": 60, "90d": 90}

_SORT_COLUMN_MAP: dict[str, str] = {
    "spend": "SUM(p.spend)",
    "conversions": "SUM(p.conversions)",
    "cpa": "CASE WHEN SUM(p.conversions) > 0 THEN SUM(p.spend) / SUM(p.conversions) ELSE 0 END",
    "cpc": "CASE WHEN SUM(p.clicks) > 0 THEN SUM(p.spend) / SUM(p.clicks) ELSE 0 END",
    "ctr": "CASE WHEN SUM(p.impressions) > 0 THEN CAST(SUM(p.clicks) AS DOUBLE) / SUM(p.impressions) ELSE 0 END",
    "cvr": "CASE WHEN SUM(p.clicks) > 0 THEN CAST(SUM(p.conversions) AS DOUBLE) / SUM(p.clicks) ELSE 0 END",
    "quality_score": "AVG(p.quality_score)",
}

# Metric column mapping for trends
_METRIC_COLUMN: dict[str, str] = {
    "cpc": "CASE WHEN SUM(p.clicks) > 0 THEN SUM(p.spend) / SUM(p.clicks) ELSE 0 END",
    "ctr": "CASE WHEN SUM(p.impressions) > 0 THEN CAST(SUM(p.clicks) AS DOUBLE) / SUM(p.impressions) ELSE 0 END",
    "cvr": "CASE WHEN SUM(p.clicks) > 0 THEN CAST(SUM(p.conversions) AS DOUBLE) / SUM(p.clicks) ELSE 0 END",
    "cpl": "CASE WHEN SUM(p.conversions) > 0 THEN SUM(p.spend) / SUM(p.conversions) ELSE 0 END",
    "quality_score": "AVG(p.quality_score)",
    "impression_share": "AVG(p.impression_share)",
    "vbb_margin_signal": "AVG(p.vbb_margin_signal)",
    "spend": "SUM(p.spend)",
}


def _date_clauses(
    params: dict[str, Any],
    start_date: str | None,
    end_date: str | None,
    alias: str = "p",
) -> str:
    clauses = ""
    if start_date:
        clauses += f" AND {alias}.date >= :start_date"
        params["start_date"] = start_date
    if end_date:
        clauses += f" AND {alias}.date <= :end_date"
        params["end_date"] = end_date
    return clauses


# ---------------------------------------------------------------------------
# Overview
# ---------------------------------------------------------------------------

def get_sem_overview(
    db: Session,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return aggregated SEM overview metrics.

    Returns a dict with keys: avg_cpc, avg_ctr, avg_cvr, avg_cpl,
    avg_quality_score, impression_share_branded, vbb_margin_signal,
    negative_keyword_score. All values are floats; defaults to 0.0.
    """
    params: dict[str, Any] = {}
    date_sql = _date_clauses(params, start_date, end_date)

    # Aggregate all performance across all groups
    agg_sql = text(f"""
        SELECT
            COALESCE(AVG(p.cpc), 0.0) AS avg_cpc,
            COALESCE(AVG(p.ctr), 0.0) AS avg_ctr,
            COALESCE(AVG(p.cvr), 0.0) AS avg_cvr,
            COALESCE(AVG(p.cpl), 0.0) AS avg_cpl,
            COALESCE(AVG(p.quality_score), 0.0) AS avg_quality_score,
            COALESCE(AVG(p.vbb_margin_signal), 0.0) AS vbb_margin_signal
        FROM sem_daily_performance p
        JOIN sem_keyword_groups g ON g.id = p.keyword_group_id
        WHERE 1=1{date_sql}
    """)

    # Branded impression share (only branded groups)
    branded_sql = text(f"""
        SELECT COALESCE(AVG(p.impression_share), 0.0) AS impression_share_branded
        FROM sem_daily_performance p
        JOIN sem_keyword_groups g ON g.id = p.keyword_group_id
        WHERE g.intent_type = 'branded'{date_sql}
    """)

    # Negative keyword score: ratio of active groups, used as a proxy
    neg_sql = text("""
        SELECT
            CASE WHEN COUNT(*) > 0
                THEN CAST(SUM(CASE WHEN is_active THEN 1 ELSE 0 END) AS DOUBLE) / COUNT(*)
                ELSE 0.0
            END AS negative_keyword_score
        FROM sem_keyword_groups
    """)

    try:
        agg_row = db.execute(agg_sql, params).fetchone()
        branded_row = db.execute(branded_sql, params).fetchone()
        neg_row = db.execute(neg_sql).fetchone()
        # Commit the read transaction so DuckDB releases its MVCC snapshot.
        # This prevents "Conflict on tuple deletion" when the caller's session
        # later runs DELETE statements within the same connection.
        db.commit()
    except Exception:
        db.rollback()
        return {
            "avg_cpc": 0.0, "avg_ctr": 0.0, "avg_cvr": 0.0, "avg_cpl": 0.0,
            "avg_quality_score": 0.0, "impression_share_branded": 0.0,
            "vbb_margin_signal": 0.0, "negative_keyword_score": 0.0,
        }

    return {
        "avg_cpc": float(agg_row[0]) if agg_row else 0.0,
        "avg_ctr": float(agg_row[1]) if agg_row else 0.0,
        "avg_cvr": float(agg_row[2]) if agg_row else 0.0,
        "avg_cpl": float(agg_row[3]) if agg_row else 0.0,
        "avg_quality_score": float(agg_row[4]) if agg_row else 0.0,
        "vbb_margin_signal": float(agg_row[5]) if agg_row else 0.0,
        "impression_share_branded": float(branded_row[0]) if branded_row else 0.0,
        "negative_keyword_score": float(neg_row[0]) if neg_row else 0.0,
    }


# ---------------------------------------------------------------------------
# Keywords
# ---------------------------------------------------------------------------

def get_sem_keywords(
    db: Session,
    *,
    sort: str = "spend",
    filters: dict[str, Any] | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = 1,
    page_size: int = 50,
) -> dict:
    """Return keyword group performance rows, sorted and paginated.

    Returns: {"groups": [...], "total": int}
    """
    filters = filters or {}
    params: dict[str, Any] = {}

    where_parts = ["1=1"]
    if "intent_type" in filters:
        where_parts.append("g.intent_type = :intent_type")
        params["intent_type"] = filters["intent_type"]
    if "match_type" in filters:
        where_parts.append("g.match_type = :match_type")
        params["match_type"] = filters["match_type"]
    if "market_segment" in filters:
        where_parts.append("g.market_segment = :market_segment")
        params["market_segment"] = filters["market_segment"]
    if "is_active" in filters:
        where_parts.append("g.is_active = :is_active")
        params["is_active"] = filters["is_active"]

    date_sql = _date_clauses(params, start_date, end_date)
    where_sql = " AND ".join(where_parts)
    sort_expr = _SORT_COLUMN_MAP.get(sort, "SUM(p.spend)")
    offset = (page - 1) * page_size

    base_sql = f"""
        FROM sem_keyword_groups g
        JOIN sem_daily_performance p ON p.keyword_group_id = g.id
            AND 1=1{date_sql}
        WHERE {where_sql}
        GROUP BY g.id, g.keyword_group, g.match_type, g.intent_type,
                 g.market_segment, g.quality_score, g.is_active
    """

    count_sql = text(f"SELECT COUNT(*) FROM (SELECT g.id {base_sql}) t")

    data_sql = text(f"""
        SELECT
            g.keyword_group,
            g.match_type,
            g.intent_type,
            g.market_segment,
            CAST(AVG(p.quality_score) AS INTEGER) AS quality_score,
            COALESCE(SUM(p.spend), 0.0) AS spend,
            CAST(COALESCE(SUM(p.clicks), 0) AS INTEGER) AS clicks,
            CAST(COALESCE(SUM(p.impressions), 0) AS INTEGER) AS impressions,
            CAST(COALESCE(SUM(p.conversions), 0) AS INTEGER) AS conversions,
            CASE WHEN SUM(p.clicks) > 0 THEN SUM(p.spend) / SUM(p.clicks) ELSE 0.0 END AS cpc,
            CASE WHEN SUM(p.impressions) > 0 THEN CAST(SUM(p.clicks) AS DOUBLE) / SUM(p.impressions) ELSE 0.0 END AS ctr,
            CASE WHEN SUM(p.clicks) > 0 THEN CAST(SUM(p.conversions) AS DOUBLE) / SUM(p.clicks) ELSE 0.0 END AS cvr,
            CASE WHEN SUM(p.conversions) > 0 THEN SUM(p.spend) / SUM(p.conversions) ELSE 0.0 END AS cpl,
            COALESCE(AVG(p.impression_share), 0.0) AS impression_share,
            g.is_active
        {base_sql}
        ORDER BY {sort_expr} DESC
        LIMIT :limit OFFSET :offset
    """)
    params["limit"] = page_size
    params["offset"] = offset

    try:
        total = db.execute(count_sql, params).scalar() or 0
        rows = db.execute(data_sql, params).fetchall()
        db.commit()
    except Exception:
        db.rollback()
        return {"groups": [], "total": 0}

    groups = []
    for row in rows:
        groups.append({
            "keyword_group": row[0],
            "match_type": row[1],
            "intent_type": row[2],
            "market_segment": row[3],
            "quality_score": int(row[4]) if row[4] is not None else 0,
            "spend": float(row[5]),
            "clicks": int(row[6]),
            "impressions": int(row[7]),
            "conversions": int(row[8]),
            "cpc": float(row[9]),
            "ctr": float(row[10]),
            "cvr": float(row[11]),
            "cpl": float(row[12]),
            "impression_share": float(row[13]),
            "is_active": bool(row[14]),
        })

    return {"groups": groups, "total": int(total)}


# ---------------------------------------------------------------------------
# Trends
# ---------------------------------------------------------------------------

def get_sem_trends(
    db: Session,
    *,
    metric: str = "cpc",
    period: str = "30d",
    intent_type: str | None = None,
    market_segment: str | None = None,
) -> dict:
    """Return daily time-series for a single SEM metric within the period window.

    Returns: {"points": [{"date": "YYYY-MM-DD", "value": float}, ...]}
    """
    days = _PERIOD_DAYS.get(period, 30)
    cutoff = date.today() - timedelta(days=days)
    metric_expr = _METRIC_COLUMN.get(metric, "SUM(p.spend)")

    params: dict[str, Any] = {"cutoff": cutoff}
    where_parts = ["p.date >= :cutoff"]

    if intent_type:
        where_parts.append("g.intent_type = :intent_type")
        params["intent_type"] = intent_type
    if market_segment:
        where_parts.append("g.market_segment = :market_segment")
        params["market_segment"] = market_segment

    where_sql = " AND ".join(where_parts)

    sql = text(f"""
        SELECT
            CAST(p.date AS VARCHAR) AS day,
            {metric_expr} AS metric_value
        FROM sem_daily_performance p
        JOIN sem_keyword_groups g ON g.id = p.keyword_group_id
        WHERE {where_sql}
        GROUP BY p.date
        ORDER BY p.date ASC
    """)

    try:
        rows = db.execute(sql, params).fetchall()
        db.commit()
    except Exception:
        db.rollback()
        return {"points": []}

    return {
        "points": [{"date": str(row[0]), "value": float(row[1])} for row in rows]
    }


# ---------------------------------------------------------------------------
# Match Types
# ---------------------------------------------------------------------------

def get_sem_match_types(
    db: Session,
    *,
    start_date: str | None = None,
    end_date: str | None = None,
) -> dict:
    """Return per-match-type aggregated performance.

    Returns: {"match_types": [{match_type, spend, clicks, impressions,
              conversions, cpc, ctr, cvr, cpl}, ...]}
    """
    params: dict[str, Any] = {}
    date_sql = _date_clauses(params, start_date, end_date)

    sql = text(f"""
        SELECT
            g.match_type,
            COALESCE(SUM(p.spend), 0.0) AS spend,
            CAST(COALESCE(SUM(p.clicks), 0) AS INTEGER) AS clicks,
            CAST(COALESCE(SUM(p.impressions), 0) AS INTEGER) AS impressions,
            CAST(COALESCE(SUM(p.conversions), 0) AS INTEGER) AS conversions,
            CASE WHEN SUM(p.clicks) > 0 THEN SUM(p.spend) / SUM(p.clicks) ELSE 0.0 END AS cpc,
            CASE WHEN SUM(p.impressions) > 0 THEN CAST(SUM(p.clicks) AS DOUBLE) / SUM(p.impressions) ELSE 0.0 END AS ctr,
            CASE WHEN SUM(p.clicks) > 0 THEN CAST(SUM(p.conversions) AS DOUBLE) / SUM(p.clicks) ELSE 0.0 END AS cvr,
            CASE WHEN SUM(p.conversions) > 0 THEN SUM(p.spend) / SUM(p.conversions) ELSE 0.0 END AS cpl
        FROM sem_keyword_groups g
        JOIN sem_daily_performance p ON p.keyword_group_id = g.id
            AND 1=1{date_sql}
        GROUP BY g.match_type
        ORDER BY SUM(p.spend) DESC NULLS LAST
    """)

    try:
        rows = db.execute(sql, params).fetchall()
        db.commit()
    except Exception:
        db.rollback()
        return {"match_types": []}

    match_types = []
    for row in rows:
        match_types.append({
            "match_type": row[0],
            "spend": float(row[1]),
            "clicks": int(row[2]),
            "impressions": int(row[3]),
            "conversions": int(row[4]),
            "cpc": float(row[5]),
            "ctr": float(row[6]),
            "cvr": float(row[7]),
            "cpl": float(row[8]),
        })

    return {"match_types": match_types}
