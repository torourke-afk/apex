"""SEM data loaders (APE-89).

Read-only query functions over the DuckDB SEM domain tables:

    load_sem_overview(date_range)                                      → dict
    load_sem_keywords(date_range, intent_type, product_category, ...)  → DataFrame
    load_sem_trends(metric, date_range, group_by)                      → DataFrame
    load_sem_match_types(date_range)                                   → DataFrame
    load_sem_market_segments(date_range)                               → DataFrame
    load_sem_campaign_types(date_range)                                → DataFrame
    load_sem_negative_keyword_score(date_range, qs_threshold)          → dict

All monetary values are floats.
Connections are opened and closed per call (no connection reuse across requests).

Tables queried:
    sem_keyword_groups      — 210 group definitions (intent_type, match_type, market_segment, …)
    sem_daily_performance   — 18,900 daily metric rows (spend, clicks, CTR, CVR, QS, VBB, …)
"""

from __future__ import annotations

from datetime import date
from typing import Optional, Tuple

import numpy as np
import pandas as pd

from src.data.init_db import get_connection
from src.data.sem_benchmarks import (
    SEM_BUDGET_SHARE,
    SEM_CTR_BENCHMARK,
    SEM_CVR_BENCHMARK,
    SEM_CPC_BENCHMARK,
    SEM_IS_BENCHMARK,
    SEM_QS_ALERT,
    SEM_QS_NEGATIVE_DEFAULT,
)

# Re-export so callers who import from this module still work
__all__ = [
    "load_sem_overview",
    "load_sem_keywords",
    "load_sem_trends",
    "load_sem_match_types",
    "load_sem_market_segments",
    "load_sem_campaign_types",
    "load_sem_negative_keyword_score",
    # benchmarks (re-exported for convenience)
    "SEM_BUDGET_SHARE",
    "SEM_CTR_BENCHMARK",
    "SEM_CVR_BENCHMARK",
    "SEM_CPC_BENCHMARK",
    "SEM_IS_BENCHMARK",
    "SEM_QS_ALERT",
    "SEM_QS_NEGATIVE_DEFAULT",
]

DateRange = Tuple[date, date]


def _load_sem_overview_synthetic(filters: dict) -> Optional[dict]:
    """Query the synthetic sem_daily table when it exists."""
    import os
    import duckdb
    db_path = os.environ.get("APEX_DB_PATH", "apex_clean.duckdb")
    con = duckdb.connect(db_path, read_only=True)
    try:
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}
        if "sem_daily" not in tables:
            return None

        clauses = []
        params: list = []
        if filters.get("date_start"):
            clauses.append("date >= ?")
            params.append(str(filters["date_start"]))
        if filters.get("date_end"):
            clauses.append("date <= ?")
            params.append(str(filters["date_end"]))
        if filters.get("dma"):
            ph = ", ".join("?" * len(filters["dma"]))
            clauses.append(f"dma_name IN ({ph})")
            params.extend(filters["dma"])
        where = ("WHERE " + " AND ".join(clauses)) if clauses else ""

        row = con.execute(f"""
            SELECT
                SUM(spend), SUM(clicks), SUM(impressions), SUM(conversions),
                SUM(clicks)*1.0/NULLIF(SUM(impressions),0),
                SUM(conversions)*1.0/NULLIF(SUM(clicks),0),
                SUM(spend)/NULLIF(SUM(conversions),0),
                AVG(quality_score), AVG(impression_share), AVG(avg_cpc)
            FROM sem_daily {where}
        """, params).fetchone()

        if not row or row[0] is None:
            return None

        total_spend = float(row[0] or 0)
        blended_ctr = float(row[4] or 0)
        avg_qs = float(row[7] or 0)

        alert_flags: list[str] = []
        blended_ctr_bench = sum(SEM_CTR_BENCHMARK.values()) / len(SEM_CTR_BENCHMARK)
        if blended_ctr < blended_ctr_bench * 0.80:
            alert_flags.append(f"Blended CTR {blended_ctr:.3%} is >20% below benchmark {blended_ctr_bench:.3%}")
        if avg_qs < SEM_QS_ALERT:
            alert_flags.append(f"Average quality score {avg_qs:.1f} below alert threshold {SEM_QS_ALERT}")

        return {
            "total_spend": total_spend,
            "total_clicks": int(row[1] or 0),
            "total_impressions": int(row[2] or 0),
            "total_conversions": int(row[3] or 0),
            "blended_ctr": blended_ctr,
            "blended_cvr": float(row[5] or 0),
            "blended_cpl": float(row[6] or 0),
            "avg_quality_score": avg_qs,
            "avg_impression_share": float(row[8] or 0),
            "avg_vbb_margin_signal": 0.0,
            "avg_cpc": float(row[9] or 0),
            "vbb_margin_trend": 0.0,
            "active_keyword_groups": 0,
            "alert_flags": alert_flags,
        }
    finally:
        con.close()


_VALID_SORT_FIELDS = frozenset({"spend", "clicks", "ctr", "cvr", "cpl", "quality_score", "vbb_margin_signal"})
_VALID_INTENT_TYPES = frozenset({"branded", "non_branded", "pmax"})
_VALID_METRICS = frozenset({"spend", "clicks", "impressions", "conversions", "ctr", "cvr", "cpl",
                             "avg_quality_score", "avg_vbb_margin_signal", "avg_impression_share"})
_VALID_GROUP_BY = frozenset({"day", "week"})


def _date_filter(alias: str = "p") -> str:
    """Return a parameterised WHERE/AND clause fragment for date range filtering."""
    return f'{alias}."date" BETWEEN ? AND ?'


# ---------------------------------------------------------------------------
# 1. load_sem_overview
# ---------------------------------------------------------------------------


def load_sem_overview(
    date_range: Optional[DateRange] = None,
    filters: Optional[dict] = None,
) -> dict:
    """Aggregate SEM performance across all keyword groups within a date window.

    Args:
        date_range: (start, end) inclusive. None returns all available dates.
        filters: Optional filter dict from filter_bar (date_start, date_end, dma, etc.)

    Returns:
        dict with keys: total_spend, total_clicks, total_impressions, total_conversions,
        blended_ctr, blended_cvr, blended_cpl, avg_quality_score, avg_impression_share,
        avg_vbb_margin_signal, avg_cpc, vbb_margin_trend, active_keyword_groups, alert_flags
    """
    # ── Try synthetic sem_daily table first ──────────────────────────────
    try:
        result = _load_sem_overview_synthetic(filters or {})
        if result is not None:
            return result
    except Exception:
        pass

    # ── Fall through to original sem_keyword_groups / sem_daily_performance ──
    params: list = []
    where = ""
    if date_range is not None:
        where = f"WHERE {_date_filter()}"
        params.extend([date_range[0], date_range[1]])

    conn = get_connection()
    try:
        totals = conn.execute(
            f"""
            SELECT
                SUM(p.spend)                                        AS total_spend,
                SUM(p.clicks)                                       AS total_clicks,
                SUM(p.impressions)                                  AS total_impressions,
                SUM(p.conversions)                                  AS total_conversions,
                SUM(p.clicks) * 1.0 / NULLIF(SUM(p.impressions), 0) AS blended_ctr,
                SUM(p.conversions) * 1.0 / NULLIF(SUM(p.clicks), 0) AS blended_cvr,
                SUM(p.spend) / NULLIF(SUM(p.conversions), 0)        AS blended_cpl,
                AVG(p.quality_score)                                AS avg_qs,
                AVG(p.impression_share)                             AS avg_is,
                AVG(p.vbb_margin_signal)                            AS avg_vbb,
                AVG(p.cpc)                                          AS avg_cpc
            FROM sem_daily_performance p
            {where}
            """,
            params,
        ).fetchone()

        active_count = conn.execute(
            "SELECT COUNT(*) FROM sem_keyword_groups WHERE is_active = TRUE"
        ).fetchone()[0]

        # Fetch daily vbb_margin_signal time series for slope calculation
        vbb_params: list = []
        vbb_where = ""
        if date_range is not None:
            vbb_where = f"WHERE {_date_filter()}"
            vbb_params.extend([date_range[0], date_range[1]])

        vbb_rows = conn.execute(
            f"""
            SELECT p."date", AVG(p.vbb_margin_signal) AS avg_vbb
            FROM sem_daily_performance p
            {vbb_where}
            GROUP BY p."date"
            ORDER BY p."date"
            """,
            vbb_params,
        ).fetchall()
    finally:
        conn.close()

    total_spend = float(totals[0] or 0)
    total_clicks = int(totals[1] or 0)
    total_impressions = int(totals[2] or 0)
    total_conversions = int(totals[3] or 0)
    blended_ctr = float(totals[4] or 0)
    blended_cvr = float(totals[5] or 0)
    blended_cpl = float(totals[6] or 0)
    avg_qs = float(totals[7] or 0)
    avg_is = float(totals[8] or 0)
    avg_vbb = float(totals[9] or 0)
    avg_cpc = float(totals[10] or 0)

    # Linear slope of daily avg vbb_margin_signal (units: signal/day)
    vbb_margin_trend = 0.0
    if len(vbb_rows) >= 2:
        xs = np.arange(len(vbb_rows), dtype=float)
        ys = np.array([float(r[1]) for r in vbb_rows], dtype=float)
        slope, _ = np.polyfit(xs, ys, 1)
        vbb_margin_trend = float(round(slope, 8))

    alert_flags: list[str] = []
    blended_ctr_benchmark = sum(SEM_CTR_BENCHMARK.values()) / len(SEM_CTR_BENCHMARK)
    if blended_ctr < blended_ctr_benchmark * 0.80:
        alert_flags.append(
            f"Blended CTR {blended_ctr:.3%} is >20% below benchmark {blended_ctr_benchmark:.3%}"
        )
    if avg_qs < SEM_QS_ALERT:
        alert_flags.append(
            f"Average quality score {avg_qs:.1f} is below alert threshold {SEM_QS_ALERT}"
        )
    if avg_is < 0.50:
        alert_flags.append(
            f"Average impression share {avg_is:.1%} is below 50% — budget or bid pressure"
        )

    return {
        "total_spend": total_spend,
        "total_clicks": total_clicks,
        "total_impressions": total_impressions,
        "total_conversions": total_conversions,
        "blended_ctr": blended_ctr,
        "blended_cvr": blended_cvr,
        "blended_cpl": blended_cpl,
        "avg_quality_score": avg_qs,
        "avg_impression_share": avg_is,
        "avg_vbb_margin_signal": avg_vbb,
        "avg_cpc": avg_cpc,
        "vbb_margin_trend": vbb_margin_trend,
        "active_keyword_groups": int(active_count),
        "alert_flags": alert_flags,
    }


# ---------------------------------------------------------------------------
# 2. load_sem_keywords
# ---------------------------------------------------------------------------


def load_sem_keywords(
    date_range: Optional[DateRange] = None,
    intent_type: Optional[str] = None,
    product_category: Optional[str] = None,
    sort_by: str = "spend",
    limit: Optional[int] = None,
) -> pd.DataFrame:
    """Keyword group performance — aggregated over the specified date range.

    Args:
        date_range:       (start, end) inclusive. None aggregates all available dates.
        intent_type:      Filter by intent — 'branded', 'non_branded', or 'pmax'.
        product_category: Filter by product (e.g. 'checking', 'mortgage').
        sort_by:          Column to rank by. One of: spend, clicks, ctr, cvr, cpl,
                          quality_score, vbb_margin_signal.
        limit:            Cap number of rows returned. None returns all.

    Returns:
        DataFrame with columns:
            keyword_group_id, name, product_category, intent_type, match_type,
            market_segment, max_cpc, quality_score_group,
            spend, clicks, impressions, conversions,
            ctr, cvr, cpl, avg_position, impression_share,
            avg_quality_score, avg_vbb_margin_signal
    """
    if sort_by not in _VALID_SORT_FIELDS:
        raise ValueError(f"sort_by must be one of {sorted(_VALID_SORT_FIELDS)}, got {sort_by!r}")
    if intent_type is not None and intent_type not in _VALID_INTENT_TYPES:
        raise ValueError(f"intent_type must be one of {sorted(_VALID_INTENT_TYPES)}, got {intent_type!r}")

    filters: list[str] = []
    params: list = []
    if date_range is not None:
        filters.append(_date_filter())
        params.extend([date_range[0], date_range[1]])
    if intent_type is not None:
        filters.append("g.intent_type = ?")
        params.append(intent_type)
    if product_category is not None:
        filters.append("g.product_category = ?")
        params.append(product_category)
    where = ("WHERE " + " AND ".join(filters)) if filters else ""

    limit_clause = f"LIMIT {int(limit)}" if limit is not None else ""

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                g.id                         AS keyword_group_id,
                g.name,
                g.product_category,
                g.intent_type,
                g.match_type,
                g.market_segment,
                g.max_cpc,
                g.quality_score              AS quality_score_group,
                SUM(p.spend)                 AS spend,
                SUM(p.clicks)                AS clicks,
                SUM(p.impressions)           AS impressions,
                SUM(p.conversions)           AS conversions,
                SUM(p.clicks) * 1.0 / NULLIF(SUM(p.impressions), 0) AS ctr,
                SUM(p.conversions) * 1.0 / NULLIF(SUM(p.clicks), 0) AS cvr,
                SUM(p.spend) / NULLIF(SUM(p.conversions), 0)         AS cpl,
                AVG(p.avg_position)          AS avg_position,
                AVG(p.impression_share)      AS impression_share,
                AVG(p.quality_score)         AS avg_quality_score,
                AVG(p.vbb_margin_signal)     AS avg_vbb_margin_signal
            FROM sem_keyword_groups g
            JOIN sem_daily_performance p ON p.keyword_group_id = g.id
            {where}
            GROUP BY
                g.id, g.name, g.product_category, g.intent_type,
                g.match_type, g.market_segment, g.max_cpc, g.quality_score
            ORDER BY {sort_by} DESC
            {limit_clause}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "keyword_group_id", "name", "product_category", "intent_type",
        "match_type", "market_segment", "max_cpc", "quality_score_group",
        "spend", "clicks", "impressions", "conversions",
        "ctr", "cvr", "cpl", "avg_position", "impression_share",
        "avg_quality_score", "avg_vbb_margin_signal",
    ]
    df = pd.DataFrame(rows, columns=cols)
    for col in ("spend", "ctr", "cvr", "cpl", "avg_position", "impression_share",
                "avg_quality_score", "avg_vbb_margin_signal", "max_cpc"):
        df[col] = df[col].astype(float)
    for col in ("clicks", "impressions", "conversions", "quality_score_group"):
        df[col] = df[col].astype(int)
    return df


# ---------------------------------------------------------------------------
# 3. load_sem_trends
# ---------------------------------------------------------------------------


def load_sem_trends(
    metric: str = "spend",
    date_range: Optional[DateRange] = None,
    group_by: str = "week",
) -> pd.DataFrame:
    """Time-series for a single SEM metric at daily or weekly grain.

    Args:
        metric:     Metric column to trend. One of: spend, clicks, impressions,
                    conversions, ctr, cvr, cpl, avg_quality_score,
                    avg_vbb_margin_signal.
        date_range: (start, end) inclusive. None returns all available dates.
        group_by:   Temporal grain — 'day' or 'week' (ISO week start, Monday).

    Returns:
        DataFrame with columns:
            period   — DATE (daily) or DATE (Monday of ISO week)
            value    — float, the requested metric aggregated over the period
    """
    if metric not in _VALID_METRICS:
        raise ValueError(f"metric must be one of {sorted(_VALID_METRICS)}, got {metric!r}")
    if group_by not in _VALID_GROUP_BY:
        raise ValueError(f"group_by must be 'day' or 'week', got {group_by!r}")

    params: list = []
    where = ""
    if date_range is not None:
        where = f"WHERE {_date_filter()}"
        params.extend([date_range[0], date_range[1]])

    if group_by == "day":
        period_expr = 'p."date"'
    else:
        period_expr = "DATE_TRUNC('week', p.\"date\")"

    # Map metric to the correct SQL aggregate expression
    _agg: dict[str, str] = {
        "spend": "SUM(p.spend)",
        "clicks": "SUM(p.clicks)",
        "impressions": "SUM(p.impressions)",
        "conversions": "SUM(p.conversions)",
        "ctr": "SUM(p.clicks) * 1.0 / NULLIF(SUM(p.impressions), 0)",
        "cvr": "SUM(p.conversions) * 1.0 / NULLIF(SUM(p.clicks), 0)",
        "cpl": "SUM(p.spend) / NULLIF(SUM(p.conversions), 0)",
        "avg_quality_score": "AVG(p.quality_score)",
        "avg_vbb_margin_signal": "AVG(p.vbb_margin_signal)",
        "avg_impression_share": "AVG(p.impression_share)",
    }

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                {period_expr}     AS period,
                {_agg[metric]}    AS value
            FROM sem_daily_performance p
            {where}
            GROUP BY {period_expr}
            ORDER BY {period_expr}
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    df = pd.DataFrame(rows, columns=["period", "value"])
    df["value"] = df["value"].astype(float)
    return df


# ---------------------------------------------------------------------------
# 4. load_sem_match_types
# ---------------------------------------------------------------------------


def load_sem_match_types(
    date_range: Optional[DateRange] = None,
) -> pd.DataFrame:
    """Aggregate performance broken down by Google Ads match type.

    Args:
        date_range: (start, end) inclusive. None aggregates all available dates.

    Returns:
        DataFrame with columns:
            match_type, keyword_groups, spend, spend_pct,
            clicks, impressions, conversions,
            ctr, cvr, cpl,
            avg_quality_score, avg_impression_share, avg_vbb_margin_signal
    """
    params: list = []
    where = ""
    if date_range is not None:
        where = f"WHERE {_date_filter()}"
        params.extend([date_range[0], date_range[1]])

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                g.match_type,
                COUNT(DISTINCT g.id)                                      AS keyword_groups,
                SUM(p.spend)                                              AS spend,
                SUM(p.clicks)                                             AS clicks,
                SUM(p.impressions)                                        AS impressions,
                SUM(p.conversions)                                        AS conversions,
                SUM(p.clicks) * 1.0 / NULLIF(SUM(p.impressions), 0)      AS ctr,
                SUM(p.conversions) * 1.0 / NULLIF(SUM(p.clicks), 0)      AS cvr,
                SUM(p.spend) / NULLIF(SUM(p.conversions), 0)              AS cpl,
                AVG(p.quality_score)                                      AS avg_quality_score,
                AVG(p.impression_share)                                   AS avg_impression_share,
                AVG(p.vbb_margin_signal)                                  AS avg_vbb_margin_signal
            FROM sem_keyword_groups g
            JOIN sem_daily_performance p ON p.keyword_group_id = g.id
            {where}
            GROUP BY g.match_type
            ORDER BY spend DESC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "match_type", "keyword_groups", "spend",
        "clicks", "impressions", "conversions",
        "ctr", "cvr", "cpl",
        "avg_quality_score", "avg_impression_share", "avg_vbb_margin_signal",
    ]
    df = pd.DataFrame(rows, columns=cols)
    for col in ("spend", "ctr", "cvr", "cpl", "avg_quality_score",
                "avg_impression_share", "avg_vbb_margin_signal"):
        df[col] = df[col].astype(float)
    for col in ("keyword_groups", "clicks", "impressions", "conversions"):
        df[col] = df[col].astype(int)

    total_spend = df["spend"].sum()
    df["spend_pct"] = (df["spend"] / total_spend).round(6) if total_spend > 0 else 0.0
    return df[["match_type", "keyword_groups", "spend", "spend_pct",
               "clicks", "impressions", "conversions",
               "ctr", "cvr", "cpl",
               "avg_quality_score", "avg_impression_share", "avg_vbb_margin_signal"]]


# ---------------------------------------------------------------------------
# 5. load_sem_market_segments
# ---------------------------------------------------------------------------


def load_sem_market_segments(
    date_range: Optional[DateRange] = None,
) -> pd.DataFrame:
    """Aggregate performance broken down by market maturity segment.

    Market segments: established (40%), growth (40%), new (20%).

    Args:
        date_range: (start, end) inclusive. None aggregates all available dates.

    Returns:
        DataFrame with columns:
            market_segment, keyword_groups, spend, spend_pct,
            clicks, impressions, conversions,
            ctr, cvr, cpl,
            avg_quality_score, avg_vbb_margin_signal,
            ctr_vs_benchmark, cvr_vs_benchmark
    """
    _blended_ctr = sum(
        SEM_CTR_BENCHMARK[it] * SEM_BUDGET_SHARE[it] for it in SEM_BUDGET_SHARE
    )
    _blended_cvr = sum(
        SEM_CVR_BENCHMARK[it] * SEM_BUDGET_SHARE[it] for it in SEM_BUDGET_SHARE
    )

    params: list = []
    where = ""
    if date_range is not None:
        where = f"WHERE {_date_filter()}"
        params.extend([date_range[0], date_range[1]])

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                g.market_segment,
                COUNT(DISTINCT g.id)                                      AS keyword_groups,
                SUM(p.spend)                                              AS spend,
                SUM(p.clicks)                                             AS clicks,
                SUM(p.impressions)                                        AS impressions,
                SUM(p.conversions)                                        AS conversions,
                SUM(p.clicks) * 1.0 / NULLIF(SUM(p.impressions), 0)      AS ctr,
                SUM(p.conversions) * 1.0 / NULLIF(SUM(p.clicks), 0)      AS cvr,
                SUM(p.spend) / NULLIF(SUM(p.conversions), 0)              AS cpl,
                AVG(p.quality_score)                                      AS avg_quality_score,
                AVG(p.vbb_margin_signal)                                  AS avg_vbb_margin_signal
            FROM sem_keyword_groups g
            JOIN sem_daily_performance p ON p.keyword_group_id = g.id
            {where}
            GROUP BY g.market_segment
            ORDER BY spend DESC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "market_segment", "keyword_groups", "spend",
        "clicks", "impressions", "conversions",
        "ctr", "cvr", "cpl",
        "avg_quality_score", "avg_vbb_margin_signal",
    ]
    df = pd.DataFrame(rows, columns=cols)
    for col in ("spend", "ctr", "cvr", "cpl", "avg_quality_score", "avg_vbb_margin_signal"):
        df[col] = df[col].astype(float)
    for col in ("keyword_groups", "clicks", "impressions", "conversions"):
        df[col] = df[col].astype(int)

    total_spend = df["spend"].sum()
    df["spend_pct"] = (df["spend"] / total_spend).round(6) if total_spend > 0 else 0.0
    df["ctr_vs_benchmark"] = (df["ctr"] - _blended_ctr).round(6)
    df["cvr_vs_benchmark"] = (df["cvr"] - _blended_cvr).round(6)

    return df[["market_segment", "keyword_groups", "spend", "spend_pct",
               "clicks", "impressions", "conversions",
               "ctr", "cvr", "cpl",
               "avg_quality_score", "avg_vbb_margin_signal",
               "ctr_vs_benchmark", "cvr_vs_benchmark"]]


# ---------------------------------------------------------------------------
# 6. load_sem_campaign_types
# ---------------------------------------------------------------------------


def load_sem_campaign_types(
    date_range: Optional[DateRange] = None,
) -> pd.DataFrame:
    """Aggregate performance broken down by campaign/intent type.

    Intent types: branded (40% budget share), non_branded (45%), pmax (15%).

    Args:
        date_range: (start, end) inclusive. None aggregates all available dates.

    Returns:
        DataFrame with columns:
            intent_type, keyword_groups, budget_share,
            spend, spend_pct, spend_vs_budget_share,
            clicks, impressions, conversions,
            ctr, ctr_benchmark, ctr_vs_benchmark,
            cvr, cvr_benchmark, cvr_vs_benchmark,
            cpl, avg_cpc, avg_impression_share,
            avg_quality_score, avg_vbb_margin_signal
    """
    params: list = []
    where = ""
    if date_range is not None:
        where = f"WHERE {_date_filter()}"
        params.extend([date_range[0], date_range[1]])

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                g.intent_type,
                COUNT(DISTINCT g.id)                                      AS keyword_groups,
                SUM(p.spend)                                              AS spend,
                SUM(p.clicks)                                             AS clicks,
                SUM(p.impressions)                                        AS impressions,
                SUM(p.conversions)                                        AS conversions,
                SUM(p.clicks) * 1.0 / NULLIF(SUM(p.impressions), 0)      AS ctr,
                SUM(p.conversions) * 1.0 / NULLIF(SUM(p.clicks), 0)      AS cvr,
                SUM(p.spend) / NULLIF(SUM(p.conversions), 0)              AS cpl,
                AVG(p.cpc)                                                AS avg_cpc,
                AVG(p.impression_share)                                   AS avg_impression_share,
                AVG(p.quality_score)                                      AS avg_quality_score,
                AVG(p.vbb_margin_signal)                                  AS avg_vbb_margin_signal
            FROM sem_keyword_groups g
            JOIN sem_daily_performance p ON p.keyword_group_id = g.id
            {where}
            GROUP BY g.intent_type
            ORDER BY spend DESC
            """,
            params,
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "intent_type", "keyword_groups", "spend",
        "clicks", "impressions", "conversions",
        "ctr", "cvr", "cpl", "avg_cpc",
        "avg_impression_share", "avg_quality_score", "avg_vbb_margin_signal",
    ]
    df = pd.DataFrame(rows, columns=cols)
    for col in ("spend", "ctr", "cvr", "cpl", "avg_cpc",
                "avg_impression_share", "avg_quality_score", "avg_vbb_margin_signal"):
        df[col] = df[col].astype(float)
    for col in ("keyword_groups", "clicks", "impressions", "conversions"):
        df[col] = df[col].astype(int)

    total_spend = df["spend"].sum()
    df["spend_pct"] = (df["spend"] / total_spend).round(6) if total_spend > 0 else 0.0
    df["budget_share"] = df["intent_type"].map(SEM_BUDGET_SHARE)
    df["spend_vs_budget_share"] = (df["spend_pct"] - df["budget_share"]).round(6)
    df["ctr_benchmark"] = df["intent_type"].map(SEM_CTR_BENCHMARK)
    df["ctr_vs_benchmark"] = (df["ctr"] - df["ctr_benchmark"]).round(6)
    df["cvr_benchmark"] = df["intent_type"].map(SEM_CVR_BENCHMARK)
    df["cvr_vs_benchmark"] = (df["cvr"] - df["cvr_benchmark"]).round(6)
    df["roas_proxy"] = (df["conversions"] / df["spend"].replace(0, float("nan"))).round(6)

    return df[[
        "intent_type", "keyword_groups", "budget_share",
        "spend", "spend_pct", "spend_vs_budget_share",
        "clicks", "impressions", "conversions",
        "ctr", "ctr_benchmark", "ctr_vs_benchmark",
        "cvr", "cvr_benchmark", "cvr_vs_benchmark",
        "cpl", "avg_cpc", "avg_impression_share",
        "avg_quality_score", "avg_vbb_margin_signal",
        "roas_proxy",
    ]]


# ---------------------------------------------------------------------------
# 7. load_sem_negative_keyword_score
# ---------------------------------------------------------------------------


def load_sem_negative_keyword_score(
    date_range: Optional[DateRange] = None,
    qs_threshold: int = SEM_QS_NEGATIVE_DEFAULT,
) -> dict:
    """Identify keyword groups that are candidates for negative keyword action.

    A group is a candidate when its average quality score (within the date range)
    is at or below ``qs_threshold``.  The composite ``negative_keyword_score``
    (0–100) combines quality score weakness, impression share loss, and CPL
    inefficiency into a single actionability signal — higher = stronger candidate
    for negative action.

    Score components (equally weighted, each 0–33.3):
        - qs_component:   max(0, (threshold - avg_qs) / threshold) × 33.3
        - is_component:   max(0, (benchmark_is - avg_is) / benchmark_is) × 33.3
        - cpl_component:  max(0, (avg_cpl - median_cpl) / median_cpl) × 33.3

    Args:
        date_range:   (start, end) inclusive. None aggregates all available dates.
        qs_threshold: Groups with avg_quality_score ≤ this value are included.
                      Default 6 (one below healthy threshold of 7).

    Returns:
        dict with keys:
            threshold         (int)       qs_threshold used
            date_range        (list[str]) [start, end] ISO strings, or null
            total_candidates  (int)       number of flagged groups
            summary           (dict)      counts per recommendation bucket
            candidates        (list[dict]) ordered by negative_keyword_score desc
    """
    params: list = []
    where = ""
    if date_range is not None:
        where = f"WHERE {_date_filter()}"
        params.extend([date_range[0], date_range[1]])

    conn = get_connection()
    try:
        rows = conn.execute(
            f"""
            SELECT
                g.id                                                      AS keyword_group_id,
                g.name,
                g.product_category,
                g.intent_type,
                g.match_type,
                g.market_segment,
                AVG(p.quality_score)                                      AS avg_quality_score,
                AVG(p.impression_share)                                   AS avg_impression_share,
                SUM(p.spend)                                              AS spend,
                SUM(p.clicks)                                             AS clicks,
                SUM(p.conversions)                                        AS conversions,
                SUM(p.spend) / NULLIF(SUM(p.conversions), 0)              AS cpl
            FROM sem_keyword_groups g
            JOIN sem_daily_performance p ON p.keyword_group_id = g.id
            {where}
            GROUP BY g.id, g.name, g.product_category, g.intent_type, g.match_type, g.market_segment
            HAVING AVG(p.quality_score) <= ?
            ORDER BY avg_quality_score ASC
            """,
            params + [qs_threshold],
        ).fetchall()
    finally:
        conn.close()

    cols = [
        "keyword_group_id", "name", "product_category", "intent_type",
        "match_type", "market_segment",
        "avg_quality_score", "avg_impression_share",
        "spend", "clicks", "conversions", "cpl",
    ]
    df = pd.DataFrame(rows, columns=cols)

    if df.empty:
        return {
            "threshold": qs_threshold,
            "date_range": [str(date_range[0]), str(date_range[1])] if date_range else None,
            "total_candidates": 0,
            "summary": {"pause_or_exclude": 0, "review_bids_and_match_type": 0, "monitor": 0},
            "candidates": [],
        }

    for col in ("avg_quality_score", "avg_impression_share", "spend", "cpl"):
        df[col] = df[col].astype(float)
    for col in ("clicks", "conversions"):
        df[col] = df[col].astype(int)

    # --- Score components ---
    df["qs_component"] = (
        np.clip((qs_threshold - df["avg_quality_score"]) / qs_threshold, 0, 1) * 33.3
    ).round(2)

    blended_is_benchmark = sum(
        SEM_IS_BENCHMARK[it] * SEM_BUDGET_SHARE[it] for it in SEM_BUDGET_SHARE
    )
    df["is_component"] = (
        np.clip(
            (blended_is_benchmark - df["avg_impression_share"]) / blended_is_benchmark,
            0, 1
        ) * 33.3
    ).round(2)

    valid_cpl = df["cpl"].replace([np.inf, np.nan], np.nan).dropna()
    benchmark_cpl = float(valid_cpl.median()) if not valid_cpl.empty else 1.0
    df["cpl_component"] = (
        np.clip(
            (df["cpl"].replace([np.inf, np.nan], benchmark_cpl * 2) - benchmark_cpl)
            / benchmark_cpl,
            0, 1
        ) * 33.3
    ).round(2)

    df["negative_keyword_score"] = (
        df["qs_component"] + df["is_component"] + df["cpl_component"]
    ).round(2)

    def _recommend(row: pd.Series) -> str:
        if row["negative_keyword_score"] >= 66:
            return "pause_or_exclude"
        if row["negative_keyword_score"] >= 33:
            return "review_bids_and_match_type"
        return "monitor"

    df["recommendation"] = df.apply(_recommend, axis=1)
    df = df.sort_values("negative_keyword_score", ascending=False).reset_index(drop=True)

    summary = df["recommendation"].value_counts().to_dict()
    for bucket in ("pause_or_exclude", "review_bids_and_match_type", "monitor"):
        summary.setdefault(bucket, 0)

    candidates = df.to_dict(orient="records")

    return {
        "threshold": qs_threshold,
        "date_range": [str(date_range[0]), str(date_range[1])] if date_range else None,
        "total_candidates": len(candidates),
        "summary": summary,
        "candidates": candidates,
    }
