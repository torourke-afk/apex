"""Seed KPI data for the executive scorecard.

Table 1 — kpi_summary (backward-compat)
  Generic marketing KPIs across DMA × channel × product × month. >= 10,000 rows.

Table 2 — kpi_sparklines (APE-10 sparkline spec)
  7 specific KPIs with 12-week weekly granularity across DMA × customer_segment.
  >= 10,000 rows.  Exact value ranges, trend classifications, and alert statuses
  per the APE-49 spec.

Both tables are idempotent (truncate-before-insert, create-if-not-exists).

Run directly:
    python -m src.data.seeds.seed_kpis
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

from src.data.init_db import get_connection

# ---------------------------------------------------------------------------
# Shared dimension constants
# ---------------------------------------------------------------------------

DMAS = [
    "New York", "Los Angeles", "Chicago", "Dallas", "Houston",
    "Philadelphia", "Washington DC", "Miami", "Atlanta", "Boston",
    "Phoenix", "Seattle", "Minneapolis", "Denver", "San Diego",
    "Tampa", "Portland", "Detroit", "St. Louis", "Baltimore",
]

DMA_WEIGHT = {
    "New York": 2.0, "Los Angeles": 1.8, "Chicago": 1.5,
    "Dallas": 1.3, "Houston": 1.2, "Philadelphia": 1.1,
    "Washington DC": 1.2, "Miami": 1.1, "Atlanta": 1.0,
    "Boston": 1.0, "Phoenix": 0.9, "Seattle": 0.9,
    "Minneapolis": 0.8, "Denver": 0.8, "San Diego": 0.7,
    "Tampa": 0.7, "Portland": 0.6, "Detroit": 0.7,
    "St. Louis": 0.6, "Baltimore": 0.6,
}

# ---------------------------------------------------------------------------
# kpi_summary constants (legacy schema — do not change)
# ---------------------------------------------------------------------------

CHANNELS = [
    "paid_search", "paid_social", "display",
    "email", "direct_mail", "affiliate", "organic",
]

PRODUCTS = [
    "checking", "savings", "credit_card", "mortgage",
    "auto_loan", "personal_loan", "cd", "money_market",
]

MONTHS = pd.date_range("2025-01-01", periods=12, freq="MS")

SEASONALITY = np.array([
    0.90, 0.88, 1.05, 1.08, 1.06, 1.00,
    0.95, 0.97, 1.02, 1.04, 1.07, 1.15,
])

CHANNEL_SPEND_SCALE = {
    "paid_search": 1.4, "paid_social": 1.2, "display": 0.8,
    "email": 0.3, "direct_mail": 0.5, "affiliate": 0.7, "organic": 0.1,
}

CHANNEL_ROAS_BASE = {
    "paid_search": 4.2, "paid_social": 3.1, "display": 2.0,
    "email": 6.5, "direct_mail": 3.8, "affiliate": 3.5, "organic": 8.0,
}

PRODUCT_FUNNEL_SCALE = {
    "checking": 1.6, "savings": 1.4, "credit_card": 1.8,
    "mortgage": 0.6, "auto_loan": 0.9, "personal_loan": 1.0,
    "cd": 0.7, "money_market": 0.8,
}

PRODUCT_LTV_BASE = {
    "checking": 850, "savings": 620, "credit_card": 480,
    "mortgage": 12000, "auto_loan": 3200, "personal_loan": 1400,
    "cd": 900, "money_market": 750,
}

# ---------------------------------------------------------------------------
# kpi_sparklines constants (APE-10 spec)
# ---------------------------------------------------------------------------

# 12 Monday-based week starts ending near 2026-05-04
WEEKS = pd.date_range("2026-02-09", periods=12, freq="W-MON")

CUSTOMER_SEGMENTS = [
    "new_customers", "existing_customers", "reactivated",
    "cross_sell", "high_value", "digital_only",
    "branch_primary", "mobile_first", "young_adults", "seniors",
]

# Segment scaling factors applied to base KPI values
SEGMENT_SCALE = {
    "new_customers":     1.05,
    "existing_customers": 1.10,
    "reactivated":       0.92,
    "cross_sell":        1.08,
    "high_value":        1.15,
    "digital_only":      1.03,
    "branch_primary":    0.95,
    "mobile_first":      1.07,
    "young_adults":      0.98,
    "seniors":           0.90,
}

# KPI spec definitions
# For pct KPIs: range_min/max are 0-100 scale (stored as 0-100, not 0-1).
# For count KPIs: absolute counts.
# For currency KPIs: dollar amounts.
# trend_dir: "up" = improving when rising, "down" = improving when falling.
# trend_pct: fractional change over 12 weeks (e.g. 0.06 = +6% from week 1→12).
# noise_std: std dev of weekly noise as fraction of base_value.
KPI_SPECS = [
    {
        "kpi_name": "net_hh_growth",
        "kpi_label": "Net HH Growth",
        "unit": "count",
        "base_value": 195.0,          # baseline weekly new HH
        "range_min": 160.0,
        "range_max": 250.0,
        "target_value": 240.0,
        "trend": "improving",
        "trend_dir": "up",
        "trend_pct": 0.08,            # +8% over 12 weeks
        "noise_std": 0.02,            # ~2% weekly variation per spec
        "alert_green": lambda v: v >= 200,
        "alert_yellow": lambda v: v >= 170,
    },
    {
        "kpi_name": "mob6_retention",
        "kpi_label": "MOB6 Retention",
        "unit": "pct",
        "base_value": 73.5,           # starts at low end 72-78 range
        "range_min": 72.0,
        "range_max": 78.0,
        "target_value": 78.0,
        "trend": "improving",
        "trend_dir": "up",
        "trend_pct": 0.04,            # slight improvement ~+3pp over 12 weeks
        "noise_std": 0.015,
        "alert_green": lambda v: v >= 76.0,
        "alert_yellow": lambda v: v >= 73.0,
    },
    {
        "kpi_name": "brand_capture_rate",
        "kpi_label": "Brand Capture Rate",
        "unit": "pct",
        "base_value": 50.0,           # midpoint of 45-55 range
        "range_min": 45.0,
        "range_max": 55.0,
        "target_value": 55.0,
        "trend": "stable",
        "trend_dir": "up",
        "trend_pct": 0.0,             # flat with seasonal dips
        "noise_std": 0.03,
        "seasonal_dip_weeks": {3, 7},  # apply -4% dip at these week indices
        "alert_green": lambda v: v >= 50.0,
        "alert_yellow": lambda v: v >= 46.0,
    },
    {
        "kpi_name": "cpihh",
        "kpi_label": "CPIHH",
        "unit": "currency",
        "base_value": 215.0,          # starts near top of $180-220 range
        "range_min": 180.0,
        "range_max": 220.0,
        "target_value": 185.0,        # lower is better
        "trend": "improving",
        "trend_dir": "down",
        "trend_pct": -0.07,           # declining ~$15 over 12 weeks
        "noise_std": 0.02,
        "alert_green": lambda v: v <= 195.0,
        "alert_yellow": lambda v: v <= 212.0,
    },
    {
        "kpi_name": "llm_visibility_score",
        "kpi_label": "LLM Visibility Score",
        "unit": "score",
        "base_value": 37.0,           # starts at lower end of 35-50 range
        "range_min": 35.0,
        "range_max": 50.0,
        "target_value": 50.0,
        "trend": "improving",
        "trend_dir": "up",
        "trend_pct": 0.12,            # increasing trend
        "noise_std": 0.025,
        "alert_green": lambda v: v >= 44.0,
        "alert_yellow": lambda v: v >= 38.0,
    },
    {
        "kpi_name": "app_completion_rate",
        "kpi_label": "App Completion Rate",
        "unit": "pct",
        "base_value": 49.5,           # starts just below midpoint 48-54
        "range_min": 48.0,
        "range_max": 54.0,
        "target_value": 54.0,
        "trend": "improving",
        "trend_dir": "up",
        "trend_pct": 0.05,
        "noise_std": 0.018,
        "alert_green": lambda v: v >= 52.0,
        "alert_yellow": lambda v: v >= 49.5,
    },
    {
        "kpi_name": "onboarding_activation_day30",
        "kpi_label": "Onboarding Activation Day 30",
        "unit": "pct",
        "base_value": 48.0,
        "range_min": 46.0,
        "range_max": 52.0,
        "target_value": 52.0,
        "trend": "improving",
        "trend_dir": "up",
        "trend_pct": 0.04,
        "noise_std": 0.02,
        "alert_green": lambda v: v >= 50.0,
        "alert_yellow": lambda v: v >= 47.5,
    },
]

RNG = np.random.default_rng(42)


# ---------------------------------------------------------------------------
# kpi_summary helpers (legacy)
# ---------------------------------------------------------------------------

def _ts_signal(base: float, trend_pct: float, season_idx: int, noise_pct: float = 0.05) -> float:
    trend = 1.0 + trend_pct * (season_idx / 11)
    season = SEASONALITY[season_idx % 12]
    noise = 1.0 + RNG.normal(0, noise_pct)
    return max(0.0, base * trend * season * noise)


def _build_summary_rows() -> list[dict]:
    rows = []
    for dma in DMAS:
        dma_w = DMA_WEIGHT[dma]
        for channel in CHANNELS:
            ch_spend = CHANNEL_SPEND_SCALE[channel]
            ch_roas = CHANNEL_ROAS_BASE[channel]
            for product in PRODUCTS:
                prod_funnel = PRODUCT_FUNNEL_SCALE[product]
                prod_ltv = PRODUCT_LTV_BASE[product]
                for m_idx, period in enumerate(MONTHS):
                    spend_base = 5_000 * dma_w * ch_spend
                    total_spend = _ts_signal(spend_base, 0.12, m_idx, 0.06)

                    roas_val = max(0.5, _ts_signal(ch_roas, 0.04, m_idx, 0.07))
                    revenue = total_spend * roas_val

                    funnel_base = 2_000 * dma_w * prod_funnel
                    funnel_volume = max(10, int(_ts_signal(funnel_base, 0.08, m_idx, 0.08)))

                    cvr_base = RNG.uniform(0.04, 0.15) * (1.0 / ch_spend if ch_spend > 0 else 0.08)
                    cvr_base = np.clip(cvr_base, 0.03, 0.20)
                    conversion_rate = float(np.clip(_ts_signal(cvr_base, 0.05, m_idx, 0.07), 0.01, 0.45))
                    conversions = max(1, int(funnel_volume * conversion_rate))

                    funded_rate = RNG.uniform(0.50, 0.80)
                    funded_accounts = max(1, int(conversions * funded_rate))

                    cpa = total_spend / conversions
                    cost_per_funded = total_spend / funded_accounts

                    mob6_base = 0.88 if product in ("checking", "savings", "cd", "money_market") else 0.72
                    mob12_base = mob6_base * 0.92
                    mob6_retention = float(np.clip(_ts_signal(mob6_base, 0.01, m_idx, 0.03), 0.40, 0.99))
                    mob12_retention = float(np.clip(_ts_signal(mob12_base, 0.01, m_idx, 0.03), 0.30, 0.98))

                    ltv = float(_ts_signal(prod_ltv * dma_w, 0.06, m_idx, 0.06))
                    net_margin = float(np.clip((revenue - total_spend) / revenue if revenue > 0 else 0, -0.5, 0.9))

                    active_base = 800 * dma_w * prod_funnel
                    active_customers = max(1, int(_ts_signal(active_base, 0.10, m_idx, 0.05)))

                    nps_base = RNG.uniform(25, 55)
                    nps = float(np.clip(_ts_signal(nps_base, 0.02, m_idx, 0.08), -20, 90))

                    rows.append({
                        "id": str(uuid.uuid4()),
                        "period_month": period.date(),
                        "dma": dma,
                        "channel": channel,
                        "product": product,
                        "total_spend": round(total_spend, 4),
                        "revenue": round(revenue, 4),
                        "roas": round(roas_val, 4),
                        "conversions": conversions,
                        "funnel_volume": funnel_volume,
                        "conversion_rate": round(conversion_rate, 6),
                        "cpa": round(cpa, 4),
                        "funded_accounts": funded_accounts,
                        "cost_per_funded": round(cost_per_funded, 4),
                        "mob6_retention": round(mob6_retention, 6),
                        "mob12_retention": round(mob12_retention, 6),
                        "ltv": round(ltv, 4),
                        "net_margin": round(net_margin, 6),
                        "active_customers": active_customers,
                        "nps": round(nps, 2),
                        "created_at": datetime.now(timezone.utc),
                    })
    return rows


# ---------------------------------------------------------------------------
# kpi_sparklines builder (APE-10 spec)
# ---------------------------------------------------------------------------

def _alert_status(spec: dict, value: float) -> str:
    if spec["alert_green"](value):
        return "green"
    if spec["alert_yellow"](value):
        return "yellow"
    return "red"


def _build_sparkline_rows() -> list[dict]:
    """Build 7-KPI × 12-week × 20-DMA × 10-segment sparkline rows.

    Row count: 7 × 12 × 20 × 10 = 16,800.
    """
    rows = []
    now = datetime.now(timezone.utc)

    for spec in KPI_SPECS:
        kpi_name = spec["kpi_name"]
        kpi_label = spec["kpi_label"]
        base = spec["base_value"]
        trend_pct = spec["trend_pct"]
        noise_std = spec["noise_std"]
        range_min = spec["range_min"]
        range_max = spec["range_max"]
        seasonal_dip_weeks: set[int] = spec.get("seasonal_dip_weeks", set())

        for dma in DMAS:
            dma_w = DMA_WEIGHT[dma]
            # Scale base by DMA weight (counts scale with population;
            # pct/score/currency get a smaller DMA-level adjustment)
            if spec["unit"] == "count":
                dma_base = base * dma_w
                dma_target = spec["target_value"] * dma_w
            else:
                # For pct/score/currency: ±10% max DMA shift, normalized to mean
                mean_w = sum(DMA_WEIGHT.values()) / len(DMA_WEIGHT)
                dma_adj = 1.0 + 0.10 * (dma_w - mean_w) / mean_w
                dma_base = base * dma_adj
                dma_target = spec["target_value"] * dma_adj

            for segment in CUSTOMER_SEGMENTS:
                seg_scale = SEGMENT_SCALE[segment]

                # Compute 12 weekly values for this DMA × segment × KPI
                weekly_values: list[float] = []
                for w_idx in range(12):
                    # Linear trend: 0 at week 0, trend_pct at week 11
                    trend_factor = 1.0 + trend_pct * (w_idx / 11) if w_idx > 0 else 1.0
                    v = dma_base * seg_scale * trend_factor
                    # Seasonal dip at specified weeks
                    if w_idx in seasonal_dip_weeks:
                        v *= 0.96
                    # Weekly noise
                    v *= (1.0 + RNG.normal(0, noise_std))
                    # Clamp to spec range (with DMA/segment scaling)
                    if spec["unit"] == "count":
                        clamp_min = range_min * dma_w * seg_scale * 0.8
                        clamp_max = range_max * dma_w * seg_scale * 1.2
                    else:
                        clamp_min = range_min * 0.95
                        clamp_max = range_max * 1.05
                    v = float(np.clip(v, clamp_min, clamp_max))
                    weekly_values.append(round(v, 4))

                # current_value is the week-12 value
                current_value = weekly_values[-1]

                for w_idx, (week_start, value) in enumerate(zip(WEEKS, weekly_values)):
                    rows.append({
                        "id": str(uuid.uuid4()),
                        "kpi_name": kpi_name,
                        "kpi_label": kpi_label,
                        "week_start_date": week_start.date(),
                        "week_num": w_idx + 1,  # 1-based
                        "dma": dma,
                        "customer_segment": segment,
                        "value": value,
                        "current_value": round(current_value, 4),
                        "target_value": round(dma_target * seg_scale, 4),
                        "trend": spec["trend"],
                        "alert_status": _alert_status(spec, current_value),
                        "created_at": now,
                    })

    return rows


# ---------------------------------------------------------------------------
# Pandera schemas
# ---------------------------------------------------------------------------

KPI_SCHEMA = DataFrameSchema(
    {
        "id": Column(str, nullable=False),
        "period_month": Column("object", nullable=False),
        "dma": Column(str, Check.isin(DMAS)),
        "channel": Column(str, Check.isin(CHANNELS)),
        "product": Column(str, Check.isin(PRODUCTS)),
        "total_spend": Column(float, Check.greater_than(0)),
        "revenue": Column(float, Check.greater_than(0)),
        "roas": Column(float, Check.greater_than(0)),
        "conversions": Column(int, Check.greater_than(0)),
        "funnel_volume": Column(int, Check.greater_than(0)),
        "conversion_rate": Column(float, [Check.in_range(0.0, 1.0)]),
        "cpa": Column(float, Check.greater_than(0)),
        "funded_accounts": Column(int, Check.greater_than(0)),
        "cost_per_funded": Column(float, Check.greater_than(0)),
        "mob6_retention": Column(float, [Check.in_range(0.0, 1.0)]),
        "mob12_retention": Column(float, [Check.in_range(0.0, 1.0)]),
        "ltv": Column(float, Check.greater_than(0)),
        "net_margin": Column(float, [Check.in_range(-1.0, 1.0)]),
        "active_customers": Column(int, Check.greater_than(0)),
        "nps": Column(float, [Check.in_range(-100, 100)]),
    },
    checks=[
        Check(lambda df: len(df) >= 10_000, error="Must have >= 10,000 rows"),
    ],
)

SPARKLINE_KPI_NAMES = [s["kpi_name"] for s in KPI_SPECS]
SPARKLINE_TRENDS = ["improving", "declining", "stable"]
SPARKLINE_ALERTS = ["green", "yellow", "red"]

SPARKLINES_SCHEMA = DataFrameSchema(
    {
        "id": Column(str, nullable=False),
        "kpi_name": Column(str, Check.isin(SPARKLINE_KPI_NAMES), nullable=False),
        "kpi_label": Column(str, nullable=False),
        "week_start_date": Column("object", nullable=False),
        "week_num": Column(int, Check.in_range(1, 12), nullable=False),
        "dma": Column(str, Check.isin(DMAS), nullable=False),
        "customer_segment": Column(str, Check.isin(CUSTOMER_SEGMENTS), nullable=False),
        "value": Column(float, nullable=False),
        "current_value": Column(float, nullable=False),
        "target_value": Column(float, Check.greater_than(0), nullable=False),
        "trend": Column(str, Check.isin(SPARKLINE_TRENDS), nullable=False),
        "alert_status": Column(str, Check.isin(SPARKLINE_ALERTS), nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 10_000, error="kpi_sparklines: must have >= 10,000 rows"),
        Check(
            lambda df: df["kpi_name"].nunique() == 7,
            error="kpi_sparklines: must have exactly 7 distinct KPIs",
        ),
        Check(
            lambda df: df["week_num"].nunique() == 12,
            error="kpi_sparklines: must have exactly 12 weeks",
        ),
        Check(
            lambda df: df["dma"].nunique() == 20,
            error="kpi_sparklines: must span all 20 DMAs",
        ),
    ],
)


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL_KPI_SUMMARY = """
CREATE TABLE IF NOT EXISTS kpi_summary (
    id               VARCHAR PRIMARY KEY,
    period_month     DATE NOT NULL,
    dma              VARCHAR NOT NULL,
    channel          VARCHAR NOT NULL,
    product          VARCHAR NOT NULL,
    total_spend      DECIMAL(18, 4),
    revenue          DECIMAL(18, 4),
    roas             DECIMAL(10, 4),
    conversions      INTEGER,
    funnel_volume    INTEGER,
    conversion_rate  DECIMAL(10, 6),
    cpa              DECIMAL(18, 4),
    funded_accounts  INTEGER,
    cost_per_funded  DECIMAL(18, 4),
    mob6_retention   DECIMAL(10, 6),
    mob12_retention  DECIMAL(10, 6),
    ltv              DECIMAL(18, 4),
    net_margin       DECIMAL(10, 6),
    active_customers INTEGER,
    nps              DECIMAL(8, 2),
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_DDL_KPI_SPARKLINES = """
CREATE TABLE IF NOT EXISTS kpi_sparklines (
    id               VARCHAR PRIMARY KEY,
    kpi_name         VARCHAR NOT NULL,
    kpi_label        VARCHAR NOT NULL,
    week_start_date  DATE NOT NULL,
    week_num         INTEGER NOT NULL,
    dma              VARCHAR NOT NULL,
    customer_segment VARCHAR NOT NULL,
    value            DECIMAL(18, 4),
    current_value    DECIMAL(18, 4),
    target_value     DECIMAL(18, 4),
    trend            VARCHAR NOT NULL,
    alert_status     VARCHAR NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


# ---------------------------------------------------------------------------
# Public seed functions
# ---------------------------------------------------------------------------

def seed_sparklines(verbose: bool = True) -> pd.DataFrame:
    """Build and insert kpi_sparklines seed data. Returns the DataFrame."""
    rows = _build_sparkline_rows()
    df = pd.DataFrame(rows)

    df["value"] = df["value"].astype(float)
    df["current_value"] = df["current_value"].astype(float)
    df["target_value"] = df["target_value"].astype(float)
    df["week_num"] = df["week_num"].astype(int)

    SPARKLINES_SCHEMA.validate(df)

    conn = get_connection()
    try:
        conn.execute(_DDL_KPI_SPARKLINES)
        conn.execute("DELETE FROM kpi_sparklines")
        conn.register("sparklines_df", df)
        conn.execute("INSERT INTO kpi_sparklines SELECT * FROM sparklines_df")
        conn.commit()
    finally:
        conn.unregister("sparklines_df")
        conn.close()

    if verbose:
        print(f"[seed_kpis] Inserted {len(df):,} rows into kpi_sparklines")
        print(f"  KPIs:     {df['kpi_name'].nunique()} ({', '.join(df['kpi_name'].unique())})")
        print(f"  Weeks:    {df['week_num'].nunique()} ({df['week_start_date'].min()} → {df['week_start_date'].max()})")
        print(f"  DMAs:     {df['dma'].nunique()}, Segments: {df['customer_segment'].nunique()}")
        print(f"  Alerts:   {dict(df.groupby('alert_status')['id'].count())}")
        for kpi in df['kpi_name'].unique():
            sub = df[df['kpi_name'] == kpi]
            print(
                f"  {kpi:<35} value range: "
                f"{sub['value'].min():.2f} – {sub['value'].max():.2f}  "
                f"target: {sub['target_value'].mean():.2f}"
            )

    return df


def seed(verbose: bool = True) -> pd.DataFrame:
    """Build and insert both kpi_summary and kpi_sparklines. Returns kpi_summary DataFrame."""
    # --- kpi_summary (legacy schema, required by run_all validation) ---
    rows = _build_summary_rows()
    df = pd.DataFrame(rows)

    df["conversions"] = df["conversions"].astype(int)
    df["funnel_volume"] = df["funnel_volume"].astype(int)
    df["funded_accounts"] = df["funded_accounts"].astype(int)
    df["active_customers"] = df["active_customers"].astype(int)
    df["total_spend"] = df["total_spend"].astype(float)
    df["revenue"] = df["revenue"].astype(float)
    df["roas"] = df["roas"].astype(float)
    df["conversion_rate"] = df["conversion_rate"].astype(float)
    df["cpa"] = df["cpa"].astype(float)
    df["cost_per_funded"] = df["cost_per_funded"].astype(float)
    df["mob6_retention"] = df["mob6_retention"].astype(float)
    df["mob12_retention"] = df["mob12_retention"].astype(float)
    df["ltv"] = df["ltv"].astype(float)
    df["net_margin"] = df["net_margin"].astype(float)
    df["nps"] = df["nps"].astype(float)

    KPI_SCHEMA.validate(df)

    conn = get_connection()
    try:
        conn.execute(_DDL_KPI_SUMMARY)
        conn.execute("DELETE FROM kpi_summary")
        conn.register("kpi_df", df)
        conn.execute("INSERT INTO kpi_summary SELECT * FROM kpi_df")
        conn.commit()
    finally:
        conn.unregister("kpi_df")
        conn.close()

    if verbose:
        print(f"[seed_kpis] Inserted {len(df):,} rows into kpi_summary")
        print(f"  Period: {df['period_month'].min()} → {df['period_month'].max()}")
        print(f"  DMAs: {df['dma'].nunique()}, Channels: {df['channel'].nunique()}, Products: {df['product'].nunique()}")

    # --- kpi_sparklines (APE-10 spec) ---
    seed_sparklines(verbose=verbose)

    return df


if __name__ == "__main__":
    seed()
