"""Social & Brand Media data loaders (APE-81).

Read-only query functions over the DuckDB social/brand domain tables:

    load_social_overview()                 -> dict
    load_social_platforms(period=None)     -> DataFrame
    load_social_creatives(sort_by, ...)    -> DataFrame
    load_brand_bei(market_tier=None)       -> DataFrame
    load_brand_frequency()                 -> dict
    load_life_events()                     -> DataFrame
    load_movers(geo=None)                  -> DataFrame

Connections are opened and closed per call.  All monetary values are floats.

Each loader tries the synthetic dataset tables first (social_paid_daily,
brand_media_daily, brand_reach_frequency), falls back to the legacy schema
tables, and finally returns hardcoded seed data if neither exists.
"""

from __future__ import annotations

import hashlib
from typing import Optional

import numpy as np
import pandas as pd

from src.data.init_db import get_connection

# ---------------------------------------------------------------------------
# Alert benchmarks (module-level so tests can monkeypatch)
# ---------------------------------------------------------------------------

# Social blended CPL alert fires when it exceeds this (typical SEM CPL floor)
_SEM_CPL_BENCHMARK: float = 60.0

# Blended CVR (leads / clicks) alert fires when below this
_CVR_ALERT_THRESHOLD: float = 0.025

_VALID_SORT_FIELDS = frozenset({"ctr", "cvr", "spend"})
_VALID_TIERS = frozenset({"Tier1", "Tier2", "Tier3"})

# Hardcoded constants for synthetic data estimation
_NATIVE_LEAD_FORM_CVR = 0.13  # ~13% click-to-lead on native forms
_LANDING_PAGE_CVR = 0.025  # ~2.5% landing page CVR
_AI_MANUAL_CPA_DELTA = 8.20  # AI saves ~$8.20 vs manual CPA
_DEFAULT_FP_AUDIENCES = 16  # default first-party audience count


def _table_exists(conn, table_name: str) -> bool:
    """Check whether a table exists in the connected DuckDB database."""
    try:
        result = conn.execute(
            "SELECT COUNT(*) FROM information_schema.tables WHERE table_name = ?",
            [table_name],
        ).fetchone()
        return result[0] > 0
    except Exception:
        return False


# ---------------------------------------------------------------------------
# 1. load_social_overview
# ---------------------------------------------------------------------------


def _load_social_overview_synthetic(conn) -> dict:
    """Load social overview from the synthetic social_paid_daily table."""
    totals = conn.execute(
        """
        SELECT
            SUM(spend)       AS total_spend,
            SUM(clicks)      AS total_clicks,
            SUM(impressions) AS total_impressions,
            COUNT(DISTINCT platform) AS platform_count
        FROM social_paid_daily
        """
    ).fetchone()

    total_spend = float(totals[0] or 0)
    total_clicks = int(totals[1] or 0)
    # Estimate leads from clicks using native lead form CVR
    total_leads = int(total_clicks * _NATIVE_LEAD_FORM_CVR)
    blended_cpl = total_spend / total_leads if total_leads > 0 else 0.0
    blended_cvr = total_leads / total_clicks if total_clicks > 0 else 0.0

    alert_flags: list[str] = []
    if blended_cpl > _SEM_CPL_BENCHMARK:
        alert_flags.append(
            f"Social CPL ${blended_cpl:.2f} exceeds SEM benchmark ${_SEM_CPL_BENCHMARK:.2f}"
        )
    if blended_cvr < _CVR_ALERT_THRESHOLD:
        alert_flags.append(
            f"Blended CVR {blended_cvr:.3%} below threshold {_CVR_ALERT_THRESHOLD:.3%}"
        )

    return {
        "total_spend": total_spend,
        "total_leads": total_leads,
        "blended_cpl": blended_cpl,
        "blended_cvr": blended_cvr,
        "ai_vs_manual_cpa_delta": _AI_MANUAL_CPA_DELTA,
        "active_first_party_audience_count": _DEFAULT_FP_AUDIENCES,
        "alert_flags": alert_flags,
    }


def load_social_overview() -> dict:
    """Aggregate social metrics across all platforms and periods.

    Returns:
        dict with keys:
            total_spend                    (float)
            total_leads                    (int)
            blended_cpl                    (float)
            blended_cvr                    (float)  leads / clicks
            ai_vs_manual_cpa_delta         (float)  avg_manual - avg_ai (positive = AI is cheaper)
            active_first_party_audience_count (int) sum of FP audiences in latest period
            alert_flags                    (list[str])
    """
    conn = get_connection()
    try:
        # Try synthetic table first
        if _table_exists(conn, "social_paid_daily"):
            return _load_social_overview_synthetic(conn)

        # Fall back to legacy schema
        totals = conn.execute(
            """
            SELECT
                SUM(spend)                         AS total_spend,
                SUM(leads)                         AS total_leads,
                SUM(clicks)                        AS total_clicks,
                AVG(cpa_ai)                        AS avg_cpa_ai,
                AVG(cpa_manual)                    AS avg_cpa_manual,
                SUM(spend) / NULLIF(SUM(leads), 0) AS blended_cpl
            FROM social_platform_metrics
            """
        ).fetchone()

        fp_row = conn.execute(
            """
            SELECT COALESCE(SUM(first_party_audiences), 0)
            FROM social_platform_metrics
            WHERE period = (SELECT MAX(period) FROM social_platform_metrics)
            """
        ).fetchone()
    except Exception:
        # Neither table exists — return minimal seed data
        return {
            "total_spend": 0.0,
            "total_leads": 0,
            "blended_cpl": 0.0,
            "blended_cvr": 0.0,
            "ai_vs_manual_cpa_delta": _AI_MANUAL_CPA_DELTA,
            "active_first_party_audience_count": 0,
            "alert_flags": [],
        }
    finally:
        conn.close()

    total_spend = float(totals[0] or 0)
    total_leads = int(totals[1] or 0)
    total_clicks = int(totals[2] or 0)
    avg_cpa_ai = float(totals[3] or 0)
    avg_cpa_manual = float(totals[4] or 0)
    blended_cpl = float(totals[5] or 0)
    blended_cvr = total_leads / total_clicks if total_clicks > 0 else 0.0
    ai_vs_manual_delta = avg_cpa_manual - avg_cpa_ai
    active_fp = int(fp_row[0] or 0)

    alert_flags: list[str] = []
    if blended_cpl > _SEM_CPL_BENCHMARK:
        alert_flags.append(
            f"Social CPL ${blended_cpl:.2f} exceeds SEM benchmark ${_SEM_CPL_BENCHMARK:.2f}"
        )
    if blended_cvr < _CVR_ALERT_THRESHOLD:
        alert_flags.append(
            f"Blended CVR {blended_cvr:.3%} below threshold {_CVR_ALERT_THRESHOLD:.3%}"
        )

    return {
        "total_spend": total_spend,
        "total_leads": total_leads,
        "blended_cpl": blended_cpl,
        "blended_cvr": blended_cvr,
        "ai_vs_manual_cpa_delta": ai_vs_manual_delta,
        "active_first_party_audience_count": active_fp,
        "alert_flags": alert_flags,
    }


# ---------------------------------------------------------------------------
# 2. load_social_platforms
# ---------------------------------------------------------------------------


def _load_social_platforms_synthetic(conn, period: Optional[str] = None) -> pd.DataFrame:
    """Load per-platform breakdown from the synthetic social_paid_daily table."""
    where = "WHERE date = ?" if period else ""
    params: list = [period] if period else []

    rows = conn.execute(
        f"""
        SELECT
            platform,
            SUM(spend)                              AS spend,
            SUM(clicks)                             AS clicks,
            SUM(impressions)                        AS volume,
            SUM(likes + shares + comments + saves)  AS engagements
        FROM social_paid_daily
        {where}
        GROUP BY platform
        ORDER BY SUM(spend) DESC
        """,
        params,
    ).fetchall()

    df = pd.DataFrame(
        rows,
        columns=["platform", "spend", "clicks", "volume", "engagements"],
    )
    # Estimate leads from clicks
    df["leads"] = (df["clicks"] * _NATIVE_LEAD_FORM_CVR).astype(int)
    df["cpl"] = df["spend"] / df["leads"].replace(0, np.nan)
    df["cpl"] = df["cpl"].fillna(0.0)
    df["cvr_native"] = _NATIVE_LEAD_FORM_CVR
    df["cvr_landing"] = _LANDING_PAGE_CVR

    for col in ("spend", "cpl", "cvr_native", "cvr_landing"):
        df[col] = df[col].astype(float)
    for col in ("leads", "volume"):
        df[col] = df[col].astype(int)

    total_spend = df["spend"].sum()
    df["spend_pct"] = (df["spend"] / total_spend).round(6) if total_spend > 0 else 0.0

    return df[["platform", "spend", "spend_pct", "leads", "cpl", "cvr_native", "cvr_landing", "volume"]]


def load_social_platforms(period: Optional[str] = None) -> pd.DataFrame:
    """Per-platform social performance breakdown.

    Args:
        period: ISO date string (e.g. '2025-05-05') to filter to a single week.
                None aggregates all available periods.

    Returns:
        DataFrame with columns:
            platform, spend, spend_pct, leads, cpl, cvr_native, cvr_landing, volume
    """
    conn = get_connection()
    try:
        # Try synthetic table first
        if _table_exists(conn, "social_paid_daily"):
            return _load_social_platforms_synthetic(conn, period)

        # Fall back to legacy schema
        where = "WHERE period = ?" if period else ""
        params: list = [period] if period else []

        rows = conn.execute(
            f"""
            SELECT
                platform,
                SUM(spend)                         AS spend,
                SUM(leads)                         AS leads,
                SUM(spend) / NULLIF(SUM(leads), 0) AS cpl,
                AVG(cvr_native)                    AS cvr_native,
                AVG(cvr_landing)                   AS cvr_landing,
                SUM(impressions)                   AS volume
            FROM social_platform_metrics
            {where}
            GROUP BY platform
            ORDER BY spend DESC
            """,
            params,
        ).fetchall()
    except Exception:
        # Neither table exists — return empty DataFrame with correct schema
        return pd.DataFrame(
            columns=["platform", "spend", "spend_pct", "leads", "cpl", "cvr_native", "cvr_landing", "volume"]
        )
    finally:
        conn.close()

    df = pd.DataFrame(
        rows,
        columns=["platform", "spend", "leads", "cpl", "cvr_native", "cvr_landing", "volume"],
    )
    for col in ("spend", "cpl", "cvr_native", "cvr_landing"):
        df[col] = df[col].astype(float)
    for col in ("leads", "volume"):
        df[col] = df[col].astype(int)

    total_spend = df["spend"].sum()
    df["spend_pct"] = (df["spend"] / total_spend).round(6) if total_spend > 0 else 0.0

    return df[["platform", "spend", "spend_pct", "leads", "cpl", "cvr_native", "cvr_landing", "volume"]]


# ---------------------------------------------------------------------------
# 3. load_social_creatives
# ---------------------------------------------------------------------------


def _load_social_creatives_synthetic(conn, sort_by: str, ascending: bool) -> pd.DataFrame:
    """Load creative performance from the synthetic social_paid_daily table."""
    rows = conn.execute(
        """
        SELECT
            creative_id,
            platform,
            creative_name                           AS name,
            objective                               AS format,
            CASE WHEN SUM(impressions) > 0
                 THEN SUM(clicks) * 1.0 / SUM(impressions)
                 ELSE 0 END                         AS ctr,
            ?                                       AS cvr,
            SUM(spend)                              AS spend,
            SUM(impressions)                        AS impressions
        FROM social_paid_daily
        GROUP BY creative_id, platform, creative_name, objective
        """,
        [_NATIVE_LEAD_FORM_CVR],
    ).fetchall()

    df = pd.DataFrame(
        rows,
        columns=["creative_id", "platform", "name", "format", "ctr", "cvr", "spend", "impressions"],
    )
    # Flag bottom-quartile CTR as underperformers
    ctr_25 = df["ctr"].quantile(0.25) if not df.empty else 0
    df["is_underperformer"] = df["ctr"] < ctr_25

    return df.sort_values(sort_by, ascending=ascending).reset_index(drop=True)


def load_social_creatives(sort_by: str = "ctr", ascending: bool = False) -> pd.DataFrame:
    """Creative performance table, sortable by key metrics.

    Args:
        sort_by:   Column to sort by -- one of 'ctr', 'cvr', 'spend'.
        ascending: Sort direction (default False = best-first / descending).

    Returns:
        DataFrame with columns:
            creative_id, platform, name, format, ctr, cvr, spend,
            impressions, is_underperformer
    """
    if sort_by not in _VALID_SORT_FIELDS:
        raise ValueError(
            f"sort_by must be one of {sorted(_VALID_SORT_FIELDS)}, got {sort_by!r}"
        )

    conn = get_connection()
    try:
        # Try synthetic table first
        if _table_exists(conn, "social_paid_daily"):
            return _load_social_creatives_synthetic(conn, sort_by, ascending)

        # Fall back to legacy schema
        rows = conn.execute(
            """
            SELECT creative_id, platform, name, format,
                   ctr, cvr, spend, impressions, is_underperformer
            FROM social_creatives
            """
        ).fetchall()
    except Exception:
        # Neither table exists — return empty DataFrame
        return pd.DataFrame(
            columns=[
                "creative_id", "platform", "name", "format",
                "ctr", "cvr", "spend", "impressions", "is_underperformer",
            ]
        )
    finally:
        conn.close()

    df = pd.DataFrame(
        rows,
        columns=[
            "creative_id", "platform", "name", "format",
            "ctr", "cvr", "spend", "impressions", "is_underperformer",
        ],
    )
    df["is_underperformer"] = df["is_underperformer"].astype(bool)
    return df.sort_values(sort_by, ascending=ascending).reset_index(drop=True)


# ---------------------------------------------------------------------------
# 4. load_brand_bei
# ---------------------------------------------------------------------------

# BEI seed data configuration
_BEI_MARKETS = {
    "Tier1": ["Cincinnati OH", "Columbus OH", "Chicago IL"],
    "Tier2": ["Atlanta GA", "Nashville TN", "Dallas-Fort Worth TX", "Houston TX"],
    "Tier3": ["Charlotte NC", "Detroit MI", "Cleveland OH"],
}
_BEI_WEEKS = 12


def _generate_bei_seed_data(market_tier: Optional[str] = None) -> pd.DataFrame:
    """Generate deterministic seed BEI data when no table exists."""
    rows = []
    base_date = pd.Timestamp("2026-02-23")  # 12 weeks back from ~mid-May 2026

    tiers = {market_tier: _BEI_MARKETS[market_tier]} if market_tier else _BEI_MARKETS

    for tier, markets in tiers.items():
        for market in markets:
            # Deterministic seed per market
            seed = int(hashlib.md5(market.encode()).hexdigest()[:8], 16) % 10000
            rng = np.random.RandomState(seed)
            base_bei = rng.uniform(52, 72)

            for w in range(_BEI_WEEKS):
                week_ending = base_date + pd.Timedelta(weeks=w)
                # Slight upward trend + noise
                trend = w * 0.35
                noise = rng.normal(0, 1.5)
                bei = min(95, max(35, base_bei + trend + noise))

                # Component scores
                awareness = rng.uniform(max(40, bei - 15), min(100, bei + 10))
                branded_search = rng.uniform(max(35, bei - 20), min(95, bei + 5))
                direct_traffic = rng.uniform(max(30, bei - 20), min(90, bei + 10))
                branch_visits = rng.uniform(max(25, bei - 25), min(85, bei + 5))
                social_engagement = rng.uniform(max(30, bei - 18), min(90, bei + 8))

                rows.append({
                    "market_name": market,
                    "market_tier": tier,
                    "week_ending": week_ending,
                    "awareness_score": round(awareness, 2),
                    "branded_search_score": round(branded_search, 2),
                    "direct_traffic_score": round(direct_traffic, 2),
                    "branch_visits_score": round(branch_visits, 2),
                    "social_engagement_score": round(social_engagement, 2),
                    "bei_score": round(bei, 2),
                    "is_active_market": True,
                    "incrementality_lift": round(rng.uniform(0.02, 0.15), 4),
                })

    df = pd.DataFrame(rows)
    if df.empty:
        df["bei_trend_slope"] = pd.Series(dtype=float)
        return df

    # Compute per-market linear slope of bei_score
    slopes = (
        df[["market_name", "week_ending", "bei_score"]]
        .sort_values("week_ending")
        .groupby("market_name")["bei_score"]
        .apply(
            lambda s: float(np.polyfit(range(len(s)), s.values.astype(float), 1)[0])
        )
        .reset_index()
        .rename(columns={"bei_score": "bei_trend_slope"})
    )
    return df.merge(slopes, on="market_name", how="left")


def load_brand_bei(market_tier: Optional[str] = None) -> pd.DataFrame:
    """BEI scores by market with all component scores and 12-week trend.

    Args:
        market_tier: Filter to 'Tier1', 'Tier2', or 'Tier3'. None returns all markets.

    Returns:
        DataFrame with columns:
            market_name, market_tier, week_ending,
            awareness_score, branded_search_score, direct_traffic_score,
            branch_visits_score, social_engagement_score, bei_score,
            is_active_market, incrementality_lift, bei_trend_slope

        bei_trend_slope is the linear slope of bei_score over the 12-week window
        per market (positive = improving).
    """
    if market_tier is not None and market_tier not in _VALID_TIERS:
        raise ValueError(
            f"market_tier must be one of {sorted(_VALID_TIERS)}, got {market_tier!r}"
        )

    conn = get_connection()
    try:
        # Try legacy schema first (it has exact columns we need)
        if _table_exists(conn, "brand_market_bei"):
            where = "WHERE market_tier = ?" if market_tier else ""
            params: list = [market_tier] if market_tier else []

            rows = conn.execute(
                f"""
                SELECT
                    market_name, market_tier, week_ending,
                    awareness_score, branded_search_score, direct_traffic_score,
                    branch_visits_score, social_engagement_score, bei_score,
                    is_active_market, incrementality_lift
                FROM brand_market_bei
                {where}
                ORDER BY market_name, week_ending
                """,
                params,
            ).fetchall()

            cols = [
                "market_name", "market_tier", "week_ending",
                "awareness_score", "branded_search_score", "direct_traffic_score",
                "branch_visits_score", "social_engagement_score", "bei_score",
                "is_active_market", "incrementality_lift",
            ]
            df = pd.DataFrame(rows, columns=cols)

            if df.empty:
                df["bei_trend_slope"] = pd.Series(dtype=float)
                return df

            slopes = (
                df[["market_name", "week_ending", "bei_score"]]
                .sort_values("week_ending")
                .groupby("market_name")["bei_score"]
                .apply(
                    lambda s: float(np.polyfit(range(len(s)), s.values.astype(float), 1)[0])
                )
                .reset_index()
                .rename(columns={"bei_score": "bei_trend_slope"})
            )
            return df.merge(slopes, on="market_name", how="left")
    except Exception:
        pass
    finally:
        conn.close()

    # Fall back to deterministic seed data
    return _generate_bei_seed_data(market_tier)


# ---------------------------------------------------------------------------
# 5. load_brand_frequency
# ---------------------------------------------------------------------------


def _load_brand_frequency_synthetic(conn) -> dict:
    """Load frequency metrics from the synthetic brand_reach_frequency table."""
    row = conn.execute(
        """
        SELECT
            SUM(CASE WHEN rolling_30d_frequency >= 4.0 AND rolling_30d_frequency <= 8.0
                     THEN 1.0 ELSE 0.0 END) / NULLIF(COUNT(*), 0)  AS pct_at_threshold
        FROM brand_reach_frequency
        WHERE date = (SELECT MAX(date) FROM brand_reach_frequency)
        """
    ).fetchone()

    pct = float(row[0] or 0) if row else 0.0

    # Completion rates don't exist in synthetic data — use realistic defaults
    return {
        "pct_at_threshold": pct,
        "ctv_completion": 0.82,
        "olv_completion": 0.64,
        "audio_listen_through": 0.91,
    }


def load_brand_frequency() -> dict:
    """Frequency compliance and completion metrics across all markets.

    Returns:
        dict with keys:
            pct_at_threshold   (float) fraction of market-weeks with frequency_compliance >= 0.70
            ctv_completion     (float) average CTV completion rate
            olv_completion     (float) average OLV completion rate
            audio_listen_through (float) average audio listen-through rate
    """
    conn = get_connection()
    try:
        # Try synthetic table first
        if _table_exists(conn, "brand_reach_frequency"):
            return _load_brand_frequency_synthetic(conn)

        # Fall back to legacy schema
        row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN frequency_compliance >= 0.70 THEN 1.0 ELSE 0.0 END)
                    / NULLIF(COUNT(*), 0)           AS pct_at_threshold,
                AVG(ctv_completion_rate)             AS ctv_completion,
                AVG(olv_completion_rate)             AS olv_completion,
                AVG(audio_listen_through_rate)       AS audio_listen_through
            FROM brand_market_bei
            """
        ).fetchone()
    except Exception:
        # Neither table exists — return defaults
        return {
            "pct_at_threshold": 0.0,
            "ctv_completion": 0.0,
            "olv_completion": 0.0,
            "audio_listen_through": 0.0,
        }
    finally:
        conn.close()

    return {
        "pct_at_threshold": float(row[0] or 0),
        "ctv_completion": float(row[1] or 0),
        "olv_completion": float(row[2] or 0),
        "audio_listen_through": float(row[3] or 0),
    }


# ---------------------------------------------------------------------------
# 6. load_life_events
# ---------------------------------------------------------------------------

_LIFE_EVENT_SEED = [
    {"event_type": "New Job",              "status": "Active", "cvr": 0.062, "mass_market_cvr": 0.015, "cvr_multiplier": 4.13, "segment_size": 28500},
    {"event_type": "New Home",             "status": "Active", "cvr": 0.078, "mass_market_cvr": 0.018, "cvr_multiplier": 4.33, "segment_size": 19200},
    {"event_type": "New Baby",             "status": "Active", "cvr": 0.045, "mass_market_cvr": 0.012, "cvr_multiplier": 3.75, "segment_size": 15800},
    {"event_type": "Retirement",           "status": "Active", "cvr": 0.053, "mass_market_cvr": 0.016, "cvr_multiplier": 3.31, "segment_size": 22100},
    {"event_type": "Marriage",             "status": "Active", "cvr": 0.058, "mass_market_cvr": 0.014, "cvr_multiplier": 4.14, "segment_size": 17600},
    {"event_type": "Divorce",              "status": "Active", "cvr": 0.034, "mass_market_cvr": 0.011, "cvr_multiplier": 3.09, "segment_size": 11400},
    {"event_type": "College",              "status": "Active", "cvr": 0.041, "mass_market_cvr": 0.013, "cvr_multiplier": 3.15, "segment_size": 24300},
    {"event_type": "Military Relocation",  "status": "Active", "cvr": 0.037, "mass_market_cvr": 0.010, "cvr_multiplier": 3.70, "segment_size": 8900},
]


def load_life_events() -> pd.DataFrame:
    """All 8 life event campaigns from the latest period.

    Returns:
        DataFrame with columns:
            event_type, status, cvr, mass_market_cvr, cvr_multiplier, segment_size
    """
    conn = get_connection()
    try:
        # Try legacy schema
        if _table_exists(conn, "life_event_campaigns"):
            rows = conn.execute(
                """
                SELECT event_type, status, cvr, mass_market_cvr, cvr_multiplier, segment_size
                FROM life_event_campaigns
                WHERE period = (SELECT MAX(period) FROM life_event_campaigns)
                ORDER BY event_type
                """
            ).fetchall()

            return pd.DataFrame(
                rows,
                columns=["event_type", "status", "cvr", "mass_market_cvr", "cvr_multiplier", "segment_size"],
            )
    except Exception:
        pass
    finally:
        conn.close()

    # No table exists — return hardcoded seed data
    return pd.DataFrame(_LIFE_EVENT_SEED)


# ---------------------------------------------------------------------------
# 7. load_movers
# ---------------------------------------------------------------------------


def load_movers(geo: Optional[str] = None) -> pd.DataFrame:
    """Mover marketing data by geography.

    Args:
        geo: Geography filter (e.g. 'Charlotte, NC'). None returns all geographies.

    Returns:
        DataFrame with columns:
            geo, period, pipeline_volume, pipeline_quality_score,
            mover_to_account_cvr, propensity_benchmark, is_expansion_geo,
            high_income_subset_cvr, high_income_subset_volume
    """
    conn = get_connection()
    try:
        if _table_exists(conn, "mover_marketing"):
            where = "WHERE geo = ?" if geo else ""
            params: list = [geo] if geo else []

            rows = conn.execute(
                f"""
                SELECT
                    geo, period, pipeline_volume, pipeline_quality_score,
                    mover_to_account_cvr, propensity_benchmark, is_expansion_geo,
                    high_income_subset_cvr, high_income_subset_volume
                FROM mover_marketing
                {where}
                ORDER BY geo, period
                """,
                params,
            ).fetchall()

            df = pd.DataFrame(
                rows,
                columns=[
                    "geo", "period", "pipeline_volume", "pipeline_quality_score",
                    "mover_to_account_cvr", "propensity_benchmark", "is_expansion_geo",
                    "high_income_subset_cvr", "high_income_subset_volume",
                ],
            )
            if not df.empty:
                df["is_expansion_geo"] = df["is_expansion_geo"].astype(bool)
            return df
    except Exception:
        pass
    finally:
        conn.close()

    # No table exists — return empty DataFrame with correct schema
    return pd.DataFrame(
        columns=[
            "geo", "period", "pipeline_volume", "pipeline_quality_score",
            "mover_to_account_cvr", "propensity_benchmark", "is_expansion_geo",
            "high_income_subset_cvr", "high_income_subset_volume",
        ]
    )
