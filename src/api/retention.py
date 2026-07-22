"""Retention Forecast API endpoints.

GET /api/retention/curves — survival curve arrays per segment + portfolio blend
GET /api/retention/kpis   — retention KPI cards (MOB6, LTV, churn, payback)
GET /api/retention/ltv    — LTV accrual curve with CPIHH breakeven
"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Query

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/retention", tags=["retention"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
# Helpers — compute KPIs and LTV from real data
# ---------------------------------------------------------------------------

def _compute_retention_kpis() -> list[dict]:
    """Compute retention KPIs from survival curves and DuckDB data."""
    import os
    import duckdb

    # Get survival curves
    from src.data.retention_forecast import load_fits, get_survival_curves

    seg_fits, pooled = load_fits("ORIGINATION")
    curves = get_survival_curves(seg_fits, pooled, horizon_days=400)
    portfolio = curves.get("Portfolio (blended)", [])

    if len(portfolio) < 181:
        raise ValueError("Not enough survival data")

    mob6_ret = float(portfolio[180]) * 100  # S(180) as percentage
    churn_90 = (1 - float(portfolio[90])) * 100  # 1 - S(90)

    # CPIHH from spend data
    db_path = os.environ.get("APEX_DB_PATH", "apex_clean.duckdb")
    con = duckdb.connect(db_path, read_only=True)
    row = con.execute("""
        SELECT
            SUM(brand_spend + sem_spend + social_spend + display_spend),
            SUM(accounts_funded)
        FROM funnel_summary_daily
    """).fetchone()
    total_spend = float(row[0] or 0)
    total_funded = int(row[1] or 1)
    cpihh = total_spend / max(1, total_funded)

    # Avg deposit (proxy for LTV base)
    dep_row = con.execute("SELECT AVG(initial_deposit) FROM customer_conversions").fetchone()
    avg_deposit = float(dep_row[0] or 0)
    con.close()

    # LTV at 12 months: cumulative retained value
    ltv_12m = 0.0
    for mo in range(1, 13):
        day = mo * 30
        s = float(portfolio[min(day, len(portfolio) - 1)])
        ltv_12m += avg_deposit * s / 12

    # Payback period: first month where cumulative LTV > CPIHH
    cum_ltv = 0.0
    payback_mo = 12
    for mo in range(1, 13):
        day = mo * 30
        s = float(portfolio[min(day, len(portfolio) - 1)])
        cum_ltv += avg_deposit * s / 12
        if cum_ltv >= cpihh:
            payback_mo = mo
            break

    mob6_target = 74.0
    mob6_delta = mob6_ret - mob6_target
    mob6_positive = mob6_delta >= 0

    return [
        {
            "label": "MOB6 RETENTION",
            "value": f"{mob6_ret:.1f}%",
            "value_suffix": None,
            "delta": f"{'↑' if mob6_positive else '↓'} {abs(mob6_delta):.1f} vs target {mob6_target:.0f}%",
            "color": "text-positive" if mob6_positive else "text-warning",
        },
        {
            "label": "AVG PORTFOLIO LTV",
            "value": f"${ltv_12m:,.0f}",
            "value_suffix": None,
            "delta": f"12-mo accrual · avg deposit ${avg_deposit:,.0f}",
            "color": "text-positive",
        },
        {
            "label": "90-DAY CHURN",
            "value": f"{churn_90:.1f}%",
            "value_suffix": None,
            "delta": f"1 − S(90) survival",
            "color": "text-positive" if churn_90 < 25 else "text-warning",
        },
        {
            "label": "PAYBACK PERIOD",
            "value": str(payback_mo),
            "value_suffix": "mo",
            "delta": f"CPIHH ${cpihh:,.0f} / LTV curve",
            "color": "text-fg2",
        },
    ]


def _compute_ltv_accrual() -> dict:
    """Compute LTV accrual curve from survival curves and avg deposit."""
    import os
    import duckdb

    from src.data.retention_forecast import load_fits, get_survival_curves

    seg_fits, pooled = load_fits("ORIGINATION")
    curves = get_survival_curves(seg_fits, pooled, horizon_days=400)
    portfolio = curves.get("Portfolio (blended)", [])

    db_path = os.environ.get("APEX_DB_PATH", "apex_clean.duckdb")
    con = duckdb.connect(db_path, read_only=True)

    dep_row = con.execute("SELECT AVG(initial_deposit) FROM customer_conversions").fetchone()
    avg_deposit = float(dep_row[0] or 0)

    spend_row = con.execute("""
        SELECT
            SUM(brand_spend + sem_spend + social_spend + display_spend),
            SUM(accounts_funded)
        FROM funnel_summary_daily
    """).fetchone()
    total_spend = float(spend_row[0] or 0)
    total_funded = int(spend_row[1] or 1)
    cpihh = total_spend / max(1, total_funded)

    con.close()

    # Build LTV points
    points = [{"mo": 0, "ltv": 0}]
    cum_ltv = 0.0
    breakeven_mob = 12
    found_breakeven = False
    for mo in range(1, 13):
        day = mo * 30
        s = float(portfolio[min(day, len(portfolio) - 1)])
        cum_ltv += avg_deposit * s / 12
        points.append({"mo": mo, "ltv": round(cum_ltv)})
        if not found_breakeven and cum_ltv >= cpihh:
            breakeven_mob = mo
            found_breakeven = True

    return {
        "points": points,
        "cpihh": round(cpihh),
        "breakeven_mob": breakeven_mob,
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/curves")
def retention_curves(
    segment_col: str = Query(
        default="ORIGINATION",
        description="Segmentation column: CHANNEL, ORIGINATION, AUDIENCE, DEVICE_TYPE",
    ),
    horizon_days: int = Query(default=940, ge=30, le=3650),
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return survival curve arrays per segment + portfolio blend.

    Each segment maps to a list of S(t) values from t=0 to t=horizon_days.
    """
    try:
        from src.data.retention_forecast import load_fits, get_survival_curves

        seg_fits, pooled = _call_cached(load_fits, segment_col)
        curves_raw = get_survival_curves(seg_fits, pooled, horizon_days=horizon_days)

        # Convert numpy arrays to lists for JSON serialization
        curves: dict[str, list[float]] = {}
        for name, arr in curves_raw.items():
            curves[name] = [round(float(v), 6) for v in arr]

        return {
            "segment_col": segment_col,
            "horizon_days": horizon_days,
            "curves": curves,
        }
    except Exception as exc:
        logger.warning("retention_curves fallback: %s", exc)
        return {
            "segment_col": segment_col,
            "horizon_days": horizon_days,
            "curves": {},
        }


@router.get("/kpis")
def retention_kpis(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return retention KPI cards computed from survival curves + DuckDB data."""
    try:
        kpis = _call_cached(_compute_retention_kpis)
        return {"kpis": kpis}
    except Exception as exc:
        logger.exception("retention_kpis failed — returning fallback")
        return {"kpis": [
            {"label": "MOB6 RETENTION", "value": "—", "value_suffix": None, "delta": "Data unavailable", "color": "text-fg3"},
            {"label": "AVG PORTFOLIO LTV", "value": "—", "value_suffix": None, "delta": "Data unavailable", "color": "text-fg3"},
            {"label": "90-DAY CHURN", "value": "—", "value_suffix": None, "delta": "Data unavailable", "color": "text-fg3"},
            {"label": "PAYBACK PERIOD", "value": "—", "value_suffix": "mo", "delta": "Data unavailable", "color": "text-fg3"},
        ]}


@router.get("/ltv")
def retention_ltv(
    date_start: str | None = Query(default=None, description="ISO date start filter"),
    date_end: str | None = Query(default=None, description="ISO date end filter"),
    product: str | None = Query(default=None, description="Comma-separated product filter"),
    dma: str | None = Query(default=None, description="Comma-separated DMA filter"),
    channel: str | None = Query(default=None, description="Comma-separated channel filter"),
):
    """Return LTV accrual curve with CPIHH breakeven month, computed from real data."""
    try:
        return _call_cached(_compute_ltv_accrual)
    except Exception as exc:
        logger.exception("retention_ltv failed — returning fallback")
        return {"points": [{"mo": 0, "ltv": 0}], "cpihh": 0, "breakeven_mob": 12}
