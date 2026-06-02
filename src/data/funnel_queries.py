"""
funnel_queries.py
-----------------
Data layer for the Acquisition Funnel page.

Attempts to query the DuckDB database for funnel data; falls back to
deterministic seeded synthetic data so the UI is never empty in dev/demo mode.

Public API
----------
get_funnel_data(filters: dict | None = None) → dict
    Returns a dict with:
    - stages       : list[str]   — 8 stage labels
    - values       : list[float] — absolute counts per stage
    - benchmarks   : list[float] — benchmark counts (ideal at each stage)
    - rates        : list[float] — step-to-step conversion rates (7 values)
    - bench_rates  : list[float] — benchmark step rates (7 values)
    - avg_account_ltv : float   — avg LTV per funded account ($)
"""

from __future__ import annotations

import random

import streamlit as st

# ---------------------------------------------------------------------------
# Funnel stage definitions
# ---------------------------------------------------------------------------

FUNNEL_STAGES: list[str] = [
    "Brand UOI",
    "Brand Capture",
    "App Started",
    "App Submitted",
    "Approved",
    "Funded",
    "Active (90d)",
]

# Benchmark conversion rates between consecutive stages (6 transitions)
# UOI→Brand Capture, Capture→App Started,
# Started→Submitted, Submitted→Approved, Approved→Funded, Funded→Active(90d)
BENCH_RATES: list[float] = [0.30, 0.005, 0.65, 0.75, 0.87, 0.72]

# Actual performance rates (computed from recalibrated synthetic data)
_ACTUAL_RATES: list[float] = [0.27623, 0.00443, 0.60376, 0.71803, 0.84948, 0.65]

# Benchmark absolute values given the Brand UOI base
_UOI_BASE: float = 6_840.0  # ~520k impressions × 1.317% visit rate


# Segment base proportions for drop-off analysis (dimension → {label: share})
_SEGMENT_PROPORTIONS: dict[str, dict[str, float]] = {
    "channel": {
        "SEM Branded": 0.18,
        "SEM Non-Branded": 0.15,
        "Paid Social": 0.14,
        "CTV": 0.08,
        "Organic": 0.22,
        "Direct": 0.13,
        "Referral": 0.10,
    },
    "market": {
        "Chicago, IL": 0.15,
        "Atlanta, GA": 0.12,
        "Dallas-Fort Worth, TX": 0.11,
        "Houston, TX": 0.10,
        "Columbus, OH": 0.09,
        "Charlotte, NC": 0.08,
        "Detroit, MI": 0.08,
        "Cincinnati, OH": 0.07,
        "Nashville, TN": 0.07,
        "Cleveland, OH": 0.06,
        "Other": 0.07,
    },
    "product": {
        "Checking": 0.32,
        "Credit Card": 0.22,
        "Savings": 0.18,
        "Mortgage": 0.10,
        "Auto Loan": 0.09,
        "Personal Loan": 0.06,
        "CD": 0.03,
    },
    "device": {
        "Mobile": 0.55,
        "Desktop": 0.38,
        "Tablet": 0.07,
    },
    "personalization": {
        "Personalized": 0.40,
        "Control": 0.35,
        "None": 0.25,
    },
}


def _build_stage_values(
    base: float,
    step_rates: list[float],
) -> list[float]:
    """Compute absolute values for each stage from a base value + step rates."""
    vals = [base]
    for r in step_rates:
        vals.append(round(vals[-1] * r))
    return vals


# ---------------------------------------------------------------------------
# Seed data builder
# ---------------------------------------------------------------------------

def _seed_funnel(rng_seed: int = 42) -> dict:
    rng = random.Random(rng_seed)

    # Slight jitter on UOI base to vary by filter selection
    uoi_base = _UOI_BASE + rng.uniform(-500, 500)

    actual_values = _build_stage_values(uoi_base, _ACTUAL_RATES)
    bench_values = _build_stage_values(uoi_base, BENCH_RATES)

    return {
        "stages": FUNNEL_STAGES,
        "values": [round(v) for v in actual_values],
        "benchmarks": [round(v) for v in bench_values],
        "rates": _ACTUAL_RATES,
        "bench_rates": BENCH_RATES,
        "avg_account_ltv": 4_800.0,  # avg LTV per funded account
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300, show_spinner=False)
def get_funnel_data(filters: dict | None = None) -> dict:
    """
    Return 8-stage acquisition funnel data.

    Queries DuckDB when a ``funnel_summary_daily`` table is present;
    falls back to deterministic seed data otherwise.

    Parameters
    ----------
    filters : dict, optional
        Keys: date_start, date_end, dma, channel, product, segment, campaign.
        Used to filter DB results; ignored in seed fallback (demo mode).

    Returns
    -------
    dict
        stages, values, benchmarks, rates, bench_rates, avg_account_ltv
    """
    try:
        import os
        import duckdb  # noqa: F401

        db_path = os.environ.get("APEX_DB_PATH", "apex_clean.duckdb")
        con = duckdb.connect(db_path, read_only=True)
        tables = {r[0] for r in con.execute("SHOW TABLES").fetchall()}

        # Prefer funnel_summary_daily (synthetic dataset) over funnel_metrics (old schema)
        if "funnel_summary_daily" not in tables and "funnel_metrics" not in tables:
            raise ValueError("No funnel table found — using seed data")

        # Build WHERE clause for date/DMA filters
        where_clauses = []
        params: list = []
        if filters:
            if filters.get("date_start"):
                where_clauses.append("date >= ?")
                params.append(str(filters["date_start"]))
            if filters.get("date_end"):
                where_clauses.append("date <= ?")
                params.append(str(filters["date_end"]))
            if filters.get("dma"):
                placeholders = ", ".join("?" * len(filters["dma"]))
                where_clauses.append(f"dma_name IN ({placeholders})")
                params.extend(filters["dma"])

        where_sql = f"WHERE {' AND '.join(where_clauses)}" if where_clauses else ""

        if "funnel_summary_daily" in tables:
            # Query from synthetic funnel_summary_daily (no impressions — start at Brand UOI)
            query = f"""
                SELECT
                    SUM(brand_interactions),
                    SUM(applications_started),
                    SUM(applications_submitted),
                    SUM(applications_approved),
                    SUM(accounts_funded)
                FROM funnel_summary_daily
                {where_sql}
            """
            row = con.execute(query, params).fetchone()

            # Build WHERE clause for sem_daily (same date/dma filters)
            sem_where_clauses = list(where_clauses)
            sem_params = list(params)
            sem_where_sql = f"WHERE {' AND '.join(sem_where_clauses)} " if sem_where_clauses else ""
            sem_brand_query = f"""
                SELECT COALESCE(SUM(clicks), 0) FROM sem_daily
                {sem_where_sql}{'AND ' if sem_where_sql else 'WHERE '}campaign_type = 'brand'
            """
            sem_brand_row = con.execute(sem_brand_query, sem_params).fetchone()
            sem_brand_clicks = float(sem_brand_row[0] or 0) if sem_brand_row else 0.0
        else:
            query = f"""
                SELECT
                    SUM(clicks), SUM(app_started),
                    SUM(app_submitted), SUM(approved), SUM(funded)
                FROM funnel_metrics
                {where_sql}
            """
            row = con.execute(query, params).fetchone()
            sem_brand_clicks = 0.0

        con.close()

        if row and row[0]:
            if "funnel_summary_daily" in tables:
                brand_interactions = float(row[0] or 0)
                app_started = float(row[1] or 0)
                app_submitted = float(row[2] or 0)
                approved = float(row[3] or 0)
                funded = float(row[4] or 0)
                active_90d = round(funded * 0.65)
                values = [brand_interactions, sem_brand_clicks,
                          app_started, app_submitted, approved, funded, active_90d]
            else:
                values = [float(v or 0) for v in row]
                # Add Active (90d) as ~65% of Funded
                funded = values[-1]
                active_90d = round(funded * 0.65)
                values.append(active_90d)
            # Compute step rates from actual data
            rates = []
            for i in range(len(values) - 1):
                rates.append(values[i + 1] / values[i] if values[i] else 0.0)
            # Benchmarks use fixed rates applied to actual UOI base
            benchmarks = _build_stage_values(values[0], BENCH_RATES)
            return {
                "stages": FUNNEL_STAGES,
                "values": [round(v) for v in values],
                "benchmarks": [round(v) for v in benchmarks],
                "rates": rates,
                "bench_rates": BENCH_RATES,
                "avg_account_ltv": 4_800.0,
            }
    except Exception:
        pass

    # Vary seed by filter hash so different filter combos produce different data
    seed = hash(str(filters)) % 1000 if filters else 42
    return _seed_funnel(rng_seed=seed)


@st.cache_data(ttl=300, show_spinner=False)
def get_dropoff_by_segment(
    stage_idx: int,
    dimension: str,
    filters: dict | None = None,
) -> dict:
    """
    Return drop-off volume broken down by segment for a given stage transition.

    Parameters
    ----------
    stage_idx : int
        0–4 index of the transition (0 = Impressions→Clicks, …, 4 = Approved→Funded).
    dimension : str
        One of: "channel", "market", "product", "device", "personalization".
    filters : dict, optional
        Same filter keys as get_funnel_data — passed through for consistency.

    Returns
    -------
    dict
        labels: list[str], dropoff: list[float], total_dropoff: float
    """
    funnel = get_funnel_data(filters)
    values = funnel["values"]
    total_dropoff = max(0.0, float(values[stage_idx] - values[stage_idx + 1]))

    proportions = _SEGMENT_PROPORTIONS.get(dimension, _SEGMENT_PROPORTIONS["channel"])
    seed = abs(hash((stage_idx, dimension, str(filters)))) % 9_999
    rng = random.Random(seed)

    labels = list(proportions.keys())
    base_props = list(proportions.values())

    # Apply ±20% noise so different stage/filter combos show distinct patterns
    noisy = [max(0.01, p * (1.0 + rng.uniform(-0.20, 0.20))) for p in base_props]
    total_noisy = sum(noisy)
    normalized = [p / total_noisy for p in noisy]

    dropoff_vals = [round(total_dropoff * p) for p in normalized]

    return {
        "labels": labels,
        "dropoff": dropoff_vals,
        "total_dropoff": total_dropoff,
    }
