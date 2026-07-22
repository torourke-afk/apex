"""Seed: Campaign Performance Data  (APE-46 — revised spec)

Generates daily campaign performance records for a trailing 90-day window:
  - 10 channel types (sem_branded, sem_nonbranded, paid_social_meta,
    paid_social_tiktok, paid_social_linkedin, ctv_olv, streaming_audio,
    ooh_print, life_event [8 subtypes], mover)
  - Exact 22 DMAs per spec
  - Daily granularity with weekday/weekend multipliers
  - Power-law spend distribution across campaigns
  - CPC: branded $0.50–2.00, non-branded $3.00–5.00
  - CTR: 6–12% (SEM/social), CPL: $50–120
  - Spend allocation: Brand Media 40%, SEM 25%, Paid Social 15%,
    HV Overlay 12%, other 8%

Produces:
  - `campaigns`            – 374 campaign rows (1 per channel×DMA)
  - `campaign_performance` – 33,660 daily rows (374 campaigns × 90 days)

Idempotent: DELETE + INSERT on both tables.

Run:
    python -m src.data.seeds.seed_campaigns
"""

from __future__ import annotations

import sys
import os
import uuid
from datetime import date, timedelta
from typing import List, Optional, Tuple

import numpy as np
import pandas as pd
import pandera.pandas as pa
from pandera.pandas import Column, DataFrameSchema, Check

# ---------------------------------------------------------------------------
# Path bootstrap
# ---------------------------------------------------------------------------
WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.data.init_db import get_connection  # noqa: E402
from src.data.seeds._dates import YESTERDAY as TODAY, TRAILING_90D_START as DAY_0

# ---------------------------------------------------------------------------
# RNG
# ---------------------------------------------------------------------------
SEED = 42
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Temporal window — trailing 90 days
# ---------------------------------------------------------------------------
DATES: List[date] = [DAY_0 + timedelta(days=i) for i in range(90)]

# ---------------------------------------------------------------------------
# DMAs — exact 22 per spec
# ---------------------------------------------------------------------------
DMAS: List[str] = [
    "New York", "Los Angeles", "Chicago", "Houston", "Phoenix",
    "Philadelphia", "San Antonio", "San Diego", "Dallas", "Austin",
    "Jacksonville", "Columbus", "Charlotte", "Indianapolis", "San Francisco",
    "Seattle", "Denver", "Nashville", "Oklahoma City", "Louisville",
    "Memphis", "Richmond",
]
assert len(DMAS) == 22

# Population-proportional DMA weights
DMA_WEIGHTS = np.array([
    2.0, 1.8, 1.5, 1.2, 0.9,   # NY, LA, CHI, HOU, PHX
    1.1, 0.7, 0.8, 1.3, 0.6,   # PHI, SA, SD, DAL, AUS
    0.5, 0.5, 0.8, 0.6, 1.1,   # JAX, COL, CLT, IND, SFO
    0.9, 0.8, 0.6, 0.4, 0.4,   # SEA, DEN, NSH, OKC, LOU
    0.4, 0.3,                   # MEM, RIC
], dtype=float)
DMA_WEIGHTS /= DMA_WEIGHTS.sum()
DMA_IDX: dict = {dma: i for i, dma in enumerate(DMAS)}

# ---------------------------------------------------------------------------
# Channel definitions
# ---------------------------------------------------------------------------
BASE_CHANNELS: List[str] = [
    "sem_branded", "sem_nonbranded",
    "paid_social_meta", "paid_social_tiktok", "paid_social_linkedin",
    "ctv_olv", "streaming_audio", "ooh_print",
    "mover",
]
LIFE_EVENT_SUBTYPES: List[str] = [
    "home_purchase", "marriage", "new_child", "college",
    "inheritance", "job_change", "divorce", "retirement",
]
ALL_CHANNELS: List[str] = BASE_CHANNELS + ["life_event"]

# ---------------------------------------------------------------------------
# Spend allocation weights (normalised to 1.0)
# Brand Media 40%:  ctv_olv + streaming_audio + ooh_print
# SEM 25%:          sem_branded + sem_nonbranded
# Paid Social 15%:  paid_social_meta + paid_social_tiktok + paid_social_linkedin
# HV Overlay 12%:   life_event (÷8 subtypes) + mover
# ---------------------------------------------------------------------------
_RAW_SPEND_SHARE: dict = {
    "ctv_olv":              0.150,
    "streaming_audio":      0.120,
    "ooh_print":            0.130,
    "sem_branded":          0.100,
    "sem_nonbranded":       0.150,
    "paid_social_meta":     0.065,
    "paid_social_tiktok":   0.050,
    "paid_social_linkedin": 0.035,
    "life_event":           0.070,   # will be divided across 8 subtypes
    "mover":                0.050,
}
_raw_total = sum(_RAW_SPEND_SHARE.values())
CHANNEL_SPEND_SHARE: dict = {k: v / _raw_total for k, v in _RAW_SPEND_SHARE.items()}

# Daily budget pool across all DMAs — used to size per-campaign budgets
DAILY_BUDGET_POOL: float = 500_000.0   # $500k/day

# ---------------------------------------------------------------------------
# Channel performance parameters
# ---------------------------------------------------------------------------

# CTR ranges (fraction)
CHANNEL_CTR: dict = {
    "sem_branded":          (0.08, 0.12),
    "sem_nonbranded":       (0.06, 0.12),
    "paid_social_meta":     (0.06, 0.10),
    "paid_social_tiktok":   (0.06, 0.10),
    "paid_social_linkedin": (0.04, 0.08),
    "ctv_olv":              (0.01, 0.04),
    "streaming_audio":      (0.005, 0.02),
    "ooh_print":            (0.001, 0.008),
    "life_event":           (0.07, 0.12),
    "mover":                (0.06, 0.11),
}

# CPC ranges (dollars) — None = CPM-based channel
CHANNEL_CPC: dict = {
    "sem_branded":          (0.50, 2.00),
    "sem_nonbranded":       (3.00, 5.00),
    "paid_social_meta":     (0.80, 2.50),
    "paid_social_tiktok":   (0.50, 1.80),
    "paid_social_linkedin": (4.00, 12.00),
    "ctv_olv":              None,
    "streaming_audio":      None,
    "ooh_print":            None,
    "life_event":           (1.50, 4.00),
    "mover":                (1.00, 3.50),
}

# CPM for CPM-based channels (dollars per thousand)
CHANNEL_CPM: dict = {
    "ctv_olv":         25.0,
    "streaming_audio": 12.0,
    "ooh_print":        8.0,
}

# CPL range for lead-gen channels
CPL_LO, CPL_HI = 50.0, 120.0

# Weekday (Mon–Fri) and weekend (Sat–Sun) spend multipliers
WEEKDAY_MULT: dict = {
    "sem_branded":          (1.10, 0.80),
    "sem_nonbranded":       (1.12, 0.76),
    "paid_social_meta":     (1.05, 0.90),
    "paid_social_tiktok":   (1.00, 1.00),
    "paid_social_linkedin": (1.20, 0.60),   # B2B: heavy weekday
    "ctv_olv":              (0.95, 1.10),   # streaming higher weekends
    "streaming_audio":      (0.92, 1.16),
    "ooh_print":            (1.00, 1.00),
    "life_event":           (1.08, 0.84),
    "mover":                (1.05, 0.90),
}

STATUSES: List[str] = ["active", "paused", "completed"]
STATUS_WEIGHTS: List[float] = [0.50, 0.20, 0.30]


# ---------------------------------------------------------------------------
# Name generator
# ---------------------------------------------------------------------------
_CHANNEL_LABELS: dict = {
    "sem_branded":          "SEM Brand",
    "sem_nonbranded":       "SEM NBrand",
    "paid_social_meta":     "Meta Social",
    "paid_social_tiktok":   "TikTok Social",
    "paid_social_linkedin": "LinkedIn Social",
    "ctv_olv":              "CTV/OLV",
    "streaming_audio":      "Streaming Audio",
    "ooh_print":            "OOH/Print",
    "life_event":           "Life Event",
    "mover":                "Mover",
}
_SUBTYPE_LABELS: dict = {
    "home_purchase": "Home Purchase",
    "marriage":      "Marriage",
    "new_child":     "New Child",
    "college":       "College",
    "inheritance":   "Inheritance",
    "job_change":    "Job Change",
    "divorce":       "Divorce",
    "retirement":    "Retirement",
}


def _campaign_name(channel: str, subtype: Optional[str], dma: str) -> str:
    ch_label = _CHANNEL_LABELS.get(channel, channel)
    sub_label = f" – {_SUBTYPE_LABELS[subtype]}" if subtype else ""
    return f"{ch_label}{sub_label} | {dma} | 2026"


# ---------------------------------------------------------------------------
# Campaign builder
# ---------------------------------------------------------------------------

def build_campaigns() -> pd.DataFrame:
    """One campaign per (channel_key, dma).

    Base channels: 9 × 22 = 198 campaigns
    Life event:    8 × 22 = 176 campaigns
    Total:              374 campaigns
    """
    n_total = len(BASE_CHANNELS) * len(DMAS) + len(LIFE_EVENT_SUBTYPES) * len(DMAS)

    # Power-law (Pareto) budget multipliers — produces long-tail spend distribution
    pareto_alpha = 1.5
    power_mult = rng.pareto(pareto_alpha, size=n_total) + 1.0
    power_mult /= power_mult.mean()

    rows: list = []
    now = pd.Timestamp.now()
    idx = 0

    for channel in BASE_CHANNELS:
        share = CHANNEL_SPEND_SHARE[channel]
        wd_mult, _ = WEEKDAY_MULT[channel]
        for dma in DMAS:
            dma_w = float(DMA_WEIGHTS[DMA_IDX[dma]])
            budget = DAILY_BUDGET_POOL * share * dma_w * 90 * float(power_mult[idx])
            rows.append({
                "id":              str(uuid.uuid4()),
                "name":            _campaign_name(channel, None, dma),
                "channel":         channel,
                "channel_subtype": None,
                "dma":             dma,
                "status":          str(rng.choice(STATUSES, p=STATUS_WEIGHTS)),
                "budget":          round(budget, 2),
                "start_date":      DAY_0,
                "end_date":        TODAY,
                "created_at":      now,
                "updated_at":      now,
            })
            idx += 1

    subtype_share = CHANNEL_SPEND_SHARE["life_event"] / len(LIFE_EVENT_SUBTYPES)
    for subtype in LIFE_EVENT_SUBTYPES:
        for dma in DMAS:
            dma_w = float(DMA_WEIGHTS[DMA_IDX[dma]])
            budget = DAILY_BUDGET_POOL * subtype_share * dma_w * 90 * float(power_mult[idx])
            rows.append({
                "id":              str(uuid.uuid4()),
                "name":            _campaign_name("life_event", subtype, dma),
                "channel":         "life_event",
                "channel_subtype": subtype,
                "dma":             dma,
                "status":          str(rng.choice(STATUSES, p=STATUS_WEIGHTS)),
                "budget":          round(budget, 2),
                "start_date":      DAY_0,
                "end_date":        TODAY,
                "created_at":      now,
                "updated_at":      now,
            })
            idx += 1

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Daily performance builder
# ---------------------------------------------------------------------------

def build_daily_performance(df_camps: pd.DataFrame) -> pd.DataFrame:
    """Generate one daily record per (campaign, date).

    374 campaigns × 90 days = 33,660 rows.
    """
    rows: list = []

    for _, camp in df_camps.iterrows():
        channel: str = camp["channel"]
        subtype: Optional[str] = camp["channel_subtype"] if pd.notna(camp["channel_subtype"]) else None
        dma: str = camp["dma"]
        budget: float = float(camp["budget"])
        daily_base: float = budget / 90.0

        ctr_lo, ctr_hi = CHANNEL_CTR[channel]
        cpc_range: Optional[Tuple[float, float]] = CHANNEL_CPC[channel]
        wd_mult, we_mult = WEEKDAY_MULT[channel]

        for d in DATES:
            is_weekend: bool = d.weekday() >= 5

            # Daily spend: base × weekday pattern × log-normal noise
            day_mult = we_mult if is_weekend else wd_mult
            noise = float(rng.lognormal(0.0, 0.20))
            spend = max(1.0, daily_base * day_mult * noise)

            if cpc_range is not None:
                # CPC-based (SEM, paid social, life_event, mover)
                cpc = float(rng.uniform(*cpc_range))
                clicks = max(1, int(spend / cpc))
                ctr = float(rng.uniform(ctr_lo, ctr_hi))
                impressions = max(clicks, int(round(clicks / ctr)))
                actual_cpc = spend / clicks
            else:
                # CPM-based (ctv_olv, streaming_audio, ooh_print)
                cpm = CHANNEL_CPM[channel]
                impressions = max(100, int(spend / cpm * 1000.0))
                ctr = float(rng.uniform(ctr_lo, ctr_hi))
                clicks = max(0, int(impressions * ctr))
                actual_cpc = spend / max(clicks, 1)

            # Leads — CPL in $50–120 range
            cpl = float(rng.uniform(CPL_LO, CPL_HI))
            leads = max(0, int(spend / cpl))

            rows.append({
                "id":              str(uuid.uuid4()),
                "campaign_id":     camp["id"],
                "record_date":     d,
                "channel":         channel,
                "channel_subtype": subtype,
                "dma":             dma,
                "is_weekend":      is_weekend,
                "spend":           round(spend, 4),
                "impressions":     impressions,
                "clicks":          clicks,
                "ctr":             round(ctr, 6),
                "leads":           leads,
                "cpl":             round(cpl, 4),
                "cpc":             round(actual_cpc, 4),
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pandera schemas
# ---------------------------------------------------------------------------

CAMPAIGNS_SCHEMA = DataFrameSchema(
    {
        "id":              Column(str,    nullable=False),
        "name":            Column(str,    nullable=False),
        "channel":         Column(str,    Check.isin(ALL_CHANNELS)),
        "dma":             Column(str,    Check.isin(DMAS)),
        "status":          Column(str,    Check.isin(STATUSES)),
        "budget":          Column(float,  Check.greater_than(0)),
        "start_date":      Column("object", nullable=False),
        "end_date":        Column("object", nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 370, error="Expected >= 370 campaign rows"),
        Check(lambda df: df["dma"].nunique() == 22, error="Expected exactly 22 DMAs"),
        Check(lambda df: df["channel"].nunique() == len(ALL_CHANNELS),
              error="Expected all channel types represented"),
    ],
    coerce=True,
)

PERF_SCHEMA = DataFrameSchema(
    {
        "id":          Column(str,   nullable=False),
        "campaign_id": Column(str,   nullable=False),
        "record_date": Column("object", nullable=False),
        "channel":     Column(str,   Check.isin(ALL_CHANNELS)),
        "dma":         Column(str,   Check.isin(DMAS)),
        "spend":       Column(float, Check.greater_than(0)),
        "impressions": Column(int,   Check.greater_than_or_equal_to(0)),
        "clicks":      Column(int,   Check.greater_than_or_equal_to(0)),
        "ctr":         Column(float, Check.in_range(0.0, 0.20)),
        "leads":       Column(int,   Check.greater_than_or_equal_to(0)),
        "cpl":         Column(float, Check.in_range(CPL_LO, CPL_HI)),
        "cpc":         Column(float, Check.greater_than(0)),
    },
    checks=[
        Check(lambda df: len(df) >= 10_000, error="Expected >= 10,000 daily rows"),
        Check(lambda df: df["dma"].nunique() == 22, error="Expected all 22 DMAs"),
        Check(lambda df: df["channel"].nunique() == len(ALL_CHANNELS),
              error="Expected all channel types in daily data"),
    ],
    coerce=True,
)

# ---------------------------------------------------------------------------
# DDL — campaign_performance (daily, revised schema)
# ---------------------------------------------------------------------------
_DDL_PERF = """
CREATE TABLE IF NOT EXISTS campaign_performance (
    id               VARCHAR PRIMARY KEY,
    campaign_id      VARCHAR NOT NULL,
    record_date      DATE    NOT NULL,
    channel          VARCHAR NOT NULL,
    channel_subtype  VARCHAR,
    dma              VARCHAR NOT NULL,
    is_weekend       BOOLEAN NOT NULL DEFAULT FALSE,
    spend            DECIMAL(18, 4),
    impressions      INTEGER,
    clicks           INTEGER,
    ctr              DECIMAL(10, 6),
    leads            INTEGER,
    cpl              DECIMAL(10, 4),
    cpc              DECIMAL(10, 4),
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

def seed(verbose: bool = True) -> pd.DataFrame:
    """Build and insert campaign seed data.

    1. Migrates `campaigns`: adds channel_subtype, budget columns if missing.
    2. Drops and recreates `campaign_performance` (daily schema).
    3. Inserts 374 campaigns and 33,660 daily performance rows.

    Returns the campaigns DataFrame.
    """
    df_camps = build_campaigns()
    df_perf = build_daily_performance(df_camps)

    # Type coercions
    df_camps["budget"] = df_camps["budget"].astype(float)
    df_perf["spend"] = df_perf["spend"].astype(float)
    df_perf["ctr"] = df_perf["ctr"].astype(float)
    df_perf["cpl"] = df_perf["cpl"].astype(float)
    df_perf["cpc"] = df_perf["cpc"].astype(float)
    for col in ("impressions", "clicks", "leads"):
        df_perf[col] = df_perf[col].astype(int)

    # Pandera validation
    CAMPAIGNS_SCHEMA.validate(df_camps)
    PERF_SCHEMA.validate(df_perf)

    conn = get_connection()
    try:
        # ------------------------------------------------------------------ #
        # Migration: add new columns to campaigns if missing                  #
        # ------------------------------------------------------------------ #
        existing_cols = {
            row[0].lower()
            for row in conn.execute(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'campaigns'"
            ).fetchall()
        }
        if "dma" not in existing_cols:
            conn.execute("ALTER TABLE campaigns ADD COLUMN dma VARCHAR")
            if verbose:
                print("[seed_campaigns] Migration: added dma column")
        if "channel_subtype" not in existing_cols:
            conn.execute("ALTER TABLE campaigns ADD COLUMN channel_subtype VARCHAR")
            if verbose:
                print("[seed_campaigns] Migration: added channel_subtype column")
        if "budget" not in existing_cols:
            conn.execute("ALTER TABLE campaigns ADD COLUMN budget DECIMAL(18,4)")
            if verbose:
                print("[seed_campaigns] Migration: added budget column")

        # ------------------------------------------------------------------ #
        # Seed campaigns                                                       #
        # Clear funnel_events first (FK on campaigns.id)                      #
        # ------------------------------------------------------------------ #
        conn.execute("DELETE FROM funnel_events")
        conn.execute("DELETE FROM campaigns")
        conn.register("camp_df", df_camps)
        conn.execute("""
            INSERT INTO campaigns
                (id, name, channel, channel_subtype, status,
                 dma, budget, start_date, end_date, created_at, updated_at)
            SELECT id, name, channel, channel_subtype, status,
                   dma, budget, start_date, end_date, created_at, updated_at
            FROM camp_df
        """)

        # ------------------------------------------------------------------ #
        # campaign_performance — drop & recreate (schema changed)             #
        # ------------------------------------------------------------------ #
        conn.execute("DROP TABLE IF EXISTS campaign_performance")
        conn.execute(_DDL_PERF)
        conn.register("perf_df", df_perf)
        conn.execute("""
            INSERT INTO campaign_performance
                (id, campaign_id, record_date, channel, channel_subtype,
                 dma, is_weekend, spend, impressions, clicks,
                 ctr, leads, cpl, cpc)
            SELECT id, campaign_id, record_date, channel, channel_subtype,
                   dma, is_weekend, spend, impressions, clicks,
                   ctr, leads, cpl, cpc
            FROM perf_df
        """)

        conn.commit()
    finally:
        for name in ("camp_df", "perf_df"):
            try:
                conn.unregister(name)
            except Exception:
                pass
        conn.close()

    if verbose:
        print(f"[seed_campaigns] Inserted {len(df_camps):,} rows into campaigns")
        print(f"  DMAs:     {df_camps['dma'].nunique()} unique markets")
        print(f"  Channels: {df_camps['channel'].value_counts().to_dict()}")
        print(f"  Statuses: {df_camps['status'].value_counts().to_dict()}")
        print(f"  Budget:   ${df_camps['budget'].min():,.0f} – "
              f"${df_camps['budget'].max():,.0f}  "
              f"(median ${df_camps['budget'].median():,.0f})")
        print()
        print(f"[seed_campaigns] Inserted {len(df_perf):,} rows into campaign_performance")
        print(f"  Date range: {df_perf['record_date'].min()} → {df_perf['record_date'].max()}")
        print(f"  DMAs:       {df_perf['dma'].nunique()} unique")
        print(f"  Channels:   {df_perf['channel'].nunique()} unique")
        print(f"  Weekends:   {df_perf['is_weekend'].sum():,} rows "
              f"({df_perf['is_weekend'].mean():.1%})")

        # Spend distribution summary
        spend_by_bucket = (
            df_perf.assign(bucket=df_perf["channel"].map({
                "ctv_olv": "Brand Media", "streaming_audio": "Brand Media",
                "ooh_print": "Brand Media",
                "sem_branded": "SEM", "sem_nonbranded": "SEM",
                "paid_social_meta": "Paid Social",
                "paid_social_tiktok": "Paid Social",
                "paid_social_linkedin": "Paid Social",
                "life_event": "HV Overlay", "mover": "HV Overlay",
            }))
            .groupby("bucket")["spend"]
            .sum()
        )
        total_spend = spend_by_bucket.sum()
        print()
        print("  Spend allocation:")
        for bucket, amt in spend_by_bucket.sort_values(ascending=False).items():
            print(f"    {bucket:<14} {amt / total_spend:>5.1%}  (${amt:,.0f})")

    return df_camps


if __name__ == "__main__":
    seed()
