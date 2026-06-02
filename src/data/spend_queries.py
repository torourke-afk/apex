"""
spend_queries.py
----------------
Data layer for the Spend Allocation page.

Queries the synthetic dataset table ``funnel_summary_daily`` for spend
aggregations by channel, market, and budget overview metrics.  Falls back
to deterministic seed data so the UI is never empty in dev/demo mode.

Public API
----------
get_budget_overview(filters)          -> list[dict]  — 4 budget KPI cards
get_channel_spend_breakdown(filters)  -> dict        — channel pacing data
get_market_allocation(filters)        -> list[dict]  — per-DMA spend table
"""

from __future__ import annotations

import calendar
import datetime
import os

import duckdb
import streamlit as st


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_db_path() -> str:
    return os.environ.get("APEX_DB_PATH", "apex_clean.duckdb")


def _build_where(
    filters: dict | None,
    date_col: str = "date",
    dma_col: str = "dma_name",
) -> tuple[str, list]:
    """Build a WHERE clause from the filter dict.  Returns (sql, params)."""
    clauses: list[str] = []
    params: list = []
    if not filters:
        return "", params
    if filters.get("date_start"):
        clauses.append(f"{date_col} >= ?")
        params.append(str(filters["date_start"]))
    if filters.get("date_end"):
        clauses.append(f"{date_col} <= ?")
        params.append(str(filters["date_end"]))
    if filters.get("dma"):
        ph = ", ".join("?" * len(filters["dma"]))
        clauses.append(f"{dma_col} IN ({ph})")
        params.extend(filters["dma"])
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


# ---------------------------------------------------------------------------
# Tier assignment
# ---------------------------------------------------------------------------

_TIER_MAP: dict[str, str] = {
    "Cincinnati, OH": "T1",
    "Columbus, OH": "T1",
    "Chicago, IL": "T1",
    "Atlanta, GA": "T2",
    "Nashville, TN": "T2",
    "Dallas-Fort Worth, TX": "T2",
    "Houston, TX": "T2",
    "Indianapolis, IN": "T2",
    "Charlotte, NC": "T3",
    "Detroit, MI": "T3",
    "Cleveland, OH": "T3",
}


def _tier_for(dma_name: str) -> str:
    return _TIER_MAP.get(dma_name, "T3")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data(ttl=120, show_spinner=False)
def get_budget_overview(filters: dict | None = None) -> list[dict]:
    """Return 4 budget KPI cards computed from funnel_summary_daily."""
    try:
        con = duckdb.connect(_get_db_path(), read_only=True)
    except Exception:
        return _fallback_budget_overview()

    try:
        f = dict(filters or {})
        where, params = _build_where(f)

        row = con.execute(f"""
            SELECT
                SUM(brand_spend + sem_spend + social_spend + display_spend),
                SUM(brand_spend),
                SUM(accounts_funded)
            FROM funnel_summary_daily
            {where}
        """, params).fetchone()

        total_spend = float(row[0] or 0)
        brand_spend = float(row[1] or 0)
        funded = int(row[2] or 0)

        # --- MTD spend (current month based on date_end) ---
        end_date = f.get("date_end")
        if end_date:
            end_d = end_date if isinstance(end_date, datetime.date) else datetime.date.fromisoformat(str(end_date))
        else:
            end_d = datetime.date.today()

        mtd_start = end_d.replace(day=1)
        mtd_where, mtd_params = _build_where(
            dict(f, date_start=mtd_start, date_end=end_d)
        )
        mtd_row = con.execute(f"""
            SELECT SUM(brand_spend + sem_spend + social_spend + display_spend)
            FROM funnel_summary_daily {mtd_where}
        """, mtd_params).fetchone()
        mtd_spend = float(mtd_row[0] or 0)

        # Previous month MTD for delta
        prev_end = mtd_start - datetime.timedelta(days=1)
        prev_start = prev_end.replace(day=1)
        # Same number of elapsed days in prior month
        elapsed_days = (end_d - mtd_start).days + 1
        prev_compare_end = min(prev_start + datetime.timedelta(days=elapsed_days - 1), prev_end)
        pmtd_where, pmtd_params = _build_where(
            dict(f, date_start=prev_start, date_end=prev_compare_end)
        )
        pmtd_row = con.execute(f"""
            SELECT SUM(brand_spend + sem_spend + social_spend + display_spend)
            FROM funnel_summary_daily {pmtd_where}
        """, pmtd_params).fetchone()
        prev_mtd_spend = float(pmtd_row[0] or 0)
        mtd_delta = mtd_spend - prev_mtd_spend

        # --- QTD Pacing ---
        q_month = ((end_d.month - 1) // 3) * 3 + 1
        qtd_start = end_d.replace(month=q_month, day=1)
        q_end_month = q_month + 2
        days_in_quarter_end = calendar.monthrange(end_d.year, q_end_month)[1]
        quarter_end = end_d.replace(month=q_end_month, day=days_in_quarter_end)
        days_elapsed = (end_d - qtd_start).days + 1
        days_in_quarter = (quarter_end - qtd_start).days + 1

        qtd_where, qtd_params = _build_where(
            dict(f, date_start=qtd_start, date_end=end_d)
        )
        qtd_row = con.execute(f"""
            SELECT SUM(brand_spend + sem_spend + social_spend + display_spend)
            FROM funnel_summary_daily {qtd_where}
        """, qtd_params).fetchone()
        qtd_actual = float(qtd_row[0] or 0)

        # Full quarter spend (for plan estimation): extrapolate from daily average
        full_q_where, full_q_params = _build_where(
            dict(f, date_start=qtd_start, date_end=quarter_end)
        )
        full_q_row = con.execute(f"""
            SELECT SUM(brand_spend + sem_spend + social_spend + display_spend)
            FROM funnel_summary_daily {full_q_where}
        """, full_q_params).fetchone()
        full_q_spend = float(full_q_row[0] or 0)

        # Plan = full quarter spend (the plan is "what we'd spend at uniform daily rate")
        # Pacing = actual / expected-at-this-point
        expected_at_point = full_q_spend * (days_elapsed / days_in_quarter) if days_in_quarter else 0
        qtd_pacing = (qtd_actual / expected_at_point * 100) if expected_at_point else 0.0

        # Prior quarter pacing for delta
        prev_q_start = qtd_start - datetime.timedelta(days=1)
        prev_q_start = prev_q_start.replace(day=1)
        prev_q_start = prev_q_start.replace(month=((prev_q_start.month - 1) // 3) * 3 + 1, day=1)
        pq_where, pq_params = _build_where(
            dict(f, date_start=prev_q_start, date_end=prev_q_start + datetime.timedelta(days=days_elapsed - 1))
        )
        pq_row = con.execute(f"""
            SELECT SUM(brand_spend + sem_spend + social_spend + display_spend)
            FROM funnel_summary_daily {pq_where}
        """, pq_params).fetchone()
        prev_qtd = float(pq_row[0] or 0)

        prev_full_q_end_month = prev_q_start.month + 2
        prev_full_q_end_day = calendar.monthrange(prev_q_start.year, prev_full_q_end_month)[1]
        prev_quarter_end = prev_q_start.replace(month=prev_full_q_end_month, day=prev_full_q_end_day)
        prev_full_where, prev_full_params = _build_where(
            dict(f, date_start=prev_q_start, date_end=prev_quarter_end)
        )
        prev_full_row = con.execute(f"""
            SELECT SUM(brand_spend + sem_spend + social_spend + display_spend)
            FROM funnel_summary_daily {prev_full_where}
        """, prev_full_params).fetchone()
        prev_full_q = float(prev_full_row[0] or 0)
        prev_days_in_q = (prev_quarter_end - prev_q_start).days + 1
        prev_expected = prev_full_q * (days_elapsed / prev_days_in_q) if prev_days_in_q else 0
        prev_pacing = (prev_qtd / prev_expected * 100) if prev_expected else 0
        pacing_delta = qtd_pacing - prev_pacing

        # --- Brand portion ---
        brand_pct = (brand_spend / total_spend * 100) if total_spend else 0.0

        # --- Blended CPIHH ---
        cpihh = (total_spend / funded) if funded else 0.0

        # Prior period CPIHH for delta
        if f.get("date_start") and f.get("date_end"):
            start_d = f["date_start"] if isinstance(f["date_start"], datetime.date) else datetime.date.fromisoformat(str(f["date_start"]))
            period_days = (end_d - start_d).days
            prior_end = start_d - datetime.timedelta(days=1)
            prior_start = prior_end - datetime.timedelta(days=period_days)
            prior_where, prior_params = _build_where(
                dict(f, date_start=prior_start, date_end=prior_end)
            )
            prior_row = con.execute(f"""
                SELECT
                    SUM(brand_spend + sem_spend + social_spend + display_spend),
                    SUM(accounts_funded)
                FROM funnel_summary_daily {prior_where}
            """, prior_params).fetchone()
            prior_spend = float(prior_row[0] or 0)
            prior_funded = int(prior_row[1] or 0)
            prior_cpihh = (prior_spend / prior_funded) if prior_funded else 0
            cpihh_delta = cpihh - prior_cpihh
        else:
            cpihh_delta = 0.0

        con.close()

        return [
            {
                "label": "Total Spend MTD",
                "value": mtd_spend,
                "delta": mtd_delta,
                "format": "currency",
            },
            {
                "label": "QTD Pacing",
                "value": qtd_pacing,
                "delta": pacing_delta,
                "format": "percent",
            },
            {
                "label": "Brand Burn Rate",
                "value": brand_pct,
                "delta": 0.0,
                "format": "percent",
            },
            {
                "label": "Blended CPIHH",
                "value": cpihh,
                "delta": cpihh_delta,
                "format": "currency",
            },
        ]
    except Exception:
        try:
            con.close()
        except Exception:
            pass
        return _fallback_budget_overview()


@st.cache_data(ttl=120, show_spinner=False)
def get_channel_spend_breakdown(filters: dict | None = None) -> dict:
    """Return spend by channel category with plan comparison."""
    try:
        con = duckdb.connect(_get_db_path(), read_only=True)
    except Exception:
        return _fallback_channel_breakdown()

    try:
        where, params = _build_where(filters)

        row = con.execute(f"""
            SELECT
                SUM(brand_spend)   AS brand_media,
                SUM(sem_spend)     AS sem,
                SUM(social_spend)  AS social,
                SUM(display_spend) AS display
            FROM funnel_summary_daily
            {where}
        """, params).fetchone()

        brand_media = float(row[0] or 0)
        sem = float(row[1] or 0)
        social = float(row[2] or 0)
        display = float(row[3] or 0)

        # SEO and Email are not tracked in funnel_summary_daily — estimate
        # as small constant fractions of total tracked spend
        tracked_total = brand_media + sem + social + display
        seo = tracked_total * 0.028       # ~2.8% allocation
        email = tracked_total * 0.033     # ~3.3% allocation

        categories = [
            "Brand Media",
            "Performance SEM",
            "Paid Social",
            "HV Segment Overlay",
            "SEO / AEO",
            "Conversion & Testing",
        ]
        actual = [brand_media, sem, social, display, seo, email]

        # Plan = slight over-plan vs actual (varies by channel maturity)
        plan_multipliers = [1.12, 1.10, 1.08, 1.15, 1.10, 1.07]
        plan = [a * m for a, m in zip(actual, plan_multipliers)]

        con.close()

        return {
            "categories": categories,
            "actual": actual,
            "plan": plan,
        }
    except Exception:
        try:
            con.close()
        except Exception:
            pass
        return _fallback_channel_breakdown()


@st.cache_data(ttl=120, show_spinner=False)
def get_market_allocation(filters: dict | None = None) -> list[dict]:
    """Return per-DMA spend breakdown with CPIHH."""
    try:
        con = duckdb.connect(_get_db_path(), read_only=True)
    except Exception:
        return _fallback_markets()

    try:
        where, params = _build_where(filters)

        rows = con.execute(f"""
            SELECT
                dma_name,
                SUM(brand_spend + sem_spend + social_spend + display_spend) AS total_spend,
                SUM(accounts_funded) AS funded
            FROM funnel_summary_daily
            {where}
            GROUP BY dma_name
            ORDER BY total_spend DESC
        """, params).fetchall()

        con.close()

        markets: list[dict] = []
        for r in rows:
            dma = r[0]
            spend = float(r[1] or 0)
            funded = int(r[2] or 0)
            cpihh = spend / funded if funded else 0.0
            markets.append({
                "Market": dma,
                "Tier": _tier_for(dma),
                "Monthly Spend": spend,
                "CPIHH": cpihh,
                "Funded": funded,
            })

        return markets if markets else _fallback_markets()
    except Exception:
        try:
            con.close()
        except Exception:
            pass
        return _fallback_markets()


# ---------------------------------------------------------------------------
# Fallbacks
# ---------------------------------------------------------------------------

def _fallback_budget_overview() -> list[dict]:
    return [
        {"label": "Total Spend MTD", "value": 4_820_000, "delta": -180_000, "format": "currency"},
        {"label": "QTD Pacing", "value": 94.2, "delta": -2.1, "format": "percent"},
        {"label": "Brand Burn Rate", "value": 67.3, "delta": 2.1, "format": "percent"},
        {"label": "Blended CPIHH", "value": 312, "delta": -18.50, "format": "currency"},
    ]


def _fallback_channel_breakdown() -> dict:
    return {
        "categories": ["Brand Media", "Performance SEM", "Paid Social", "HV Segment Overlay", "SEO / AEO", "Conversion & Testing"],
        "actual": [8_090_000, 2_175_000, 1_870_000, 2_845_000, 445_000, 524_000],
        "plan": [12_000_000, 3_750_000, 3_000_000, 4_000_000, 1_000_000, 1_000_000],
    }


def _fallback_markets() -> list[dict]:
    return [
        {"Market": "Cincinnati, OH", "Tier": "T1", "Monthly Spend": 820_000, "CPIHH": 298, "Funded": 2752},
        {"Market": "Chicago, IL", "Tier": "T1", "Monthly Spend": 640_000, "CPIHH": 312, "Funded": 2051},
        {"Market": "Columbus, OH", "Tier": "T1", "Monthly Spend": 520_000, "CPIHH": 305, "Funded": 1705},
        {"Market": "Atlanta, GA", "Tier": "T2", "Monthly Spend": 390_000, "CPIHH": 321, "Funded": 1215},
        {"Market": "Nashville, TN", "Tier": "T2", "Monthly Spend": 310_000, "CPIHH": 334, "Funded": 928},
    ]
