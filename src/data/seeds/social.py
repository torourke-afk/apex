"""Seed: Paid Social Channel Data (APE-98)

Three tables:
  - social_paid_daily      — 4 platforms × 90 days = 360 rows
  - social_paid_creatives  — 56 creatives across platforms (14 per platform)
  - social_paid_audiences  — 16 first-party audience segments

Budget constraint:
  Total social spend = 15% of total_media_budget ($15,000,000) = $2,250,000
  Platform split (by spend):
    Meta (Facebook/Instagram):  70%  → $1,575,000
    TikTok:                     15%  →   $337,500
    LinkedIn:                   10%  →   $225,000
    Other (Pinterest/Snapchat):  5%  →   $112,500

CVR ranges:
  Native lead form:  10–16% (Meta highest, LinkedIn lowest)
  Landing page:       3–6%

Idempotent: DELETE + INSERT on all three tables.

Run:
    python -m src.data.seeds.social
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, timedelta
from typing import List

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
# RNG + temporal window (trailing 90 days, aligned with seed_campaigns)
# ---------------------------------------------------------------------------
SEED = 42
rng = np.random.default_rng(SEED)

DATES: List[date] = [DAY_0 + timedelta(days=i) for i in range(90)]

# ---------------------------------------------------------------------------
# Budget constants
# ---------------------------------------------------------------------------
TOTAL_MEDIA_BUDGET = 15_000_000.0       # from budgets.py annual total
TOTAL_SOCIAL_SPEND = TOTAL_MEDIA_BUDGET * 0.15  # $2,250,000

PLATFORMS = ["Meta", "TikTok", "LinkedIn", "Other"]
PLATFORM_SHARE = {"Meta": 0.70, "TikTok": 0.15, "LinkedIn": 0.10, "Other": 0.05}

# ---------------------------------------------------------------------------
# Platform performance parameters
# ---------------------------------------------------------------------------

# Native lead form CVR: 10–16% (Meta highest, LinkedIn lowest)
# Landing page CVR: 3–6%
PLATFORM_PARAMS = {
    "Meta": {
        "cvr_native":  (0.140, 0.160),
        "cvr_landing": (0.048, 0.060),
        "cpm":         (12.0, 22.0),
        "ctr":         (0.010, 0.030),
    },
    "TikTok": {
        "cvr_native":  (0.110, 0.130),
        "cvr_landing": (0.038, 0.052),
        "cpm":         (8.0, 16.0),
        "ctr":         (0.012, 0.032),
    },
    "LinkedIn": {
        "cvr_native":  (0.100, 0.110),
        "cvr_landing": (0.030, 0.045),
        "cpm":         (28.0, 55.0),   # LinkedIn CPMs are significantly higher
        "ctr":         (0.006, 0.016),
    },
    "Other": {
        "cvr_native":  (0.110, 0.125),
        "cvr_landing": (0.035, 0.050),
        "cpm":         (6.0, 14.0),
        "ctr":         (0.008, 0.022),
    },
}

# Day-of-week seasonality: (weekday_mult, weekend_mult)
PLATFORM_WEEKDAY_MULT = {
    "Meta":     (1.05, 0.90),   # slightly stronger on weekdays
    "TikTok":   (1.00, 1.00),   # even across week
    "LinkedIn": (1.25, 0.50),   # B2B: heavy weekday, near-zero weekends
    "Other":    (0.95, 1.10),   # lifestyle: stronger weekends
}

# Monthly seasonality index (calendar months): social tends to peak Q4 + summer
_MONTH_SEASONALITY = {
    1: 0.95, 2: 0.90, 3: 0.92,   # Q1: slightly soft
    4: 0.98, 5: 1.05, 6: 1.08,   # Q2–summer ramp
    7: 1.10, 8: 1.08, 9: 1.05,   # summer peak
    10: 1.10, 11: 1.15, 12: 1.20, # Q4 holiday surge
}

# ---------------------------------------------------------------------------
# Creative definitions
# ---------------------------------------------------------------------------
CREATIVE_FORMATS = ["video", "static", "carousel"]
CAMPAIGN_TYPES = ["awareness", "consideration", "conversion", "retargeting"]
CREATIVE_STATUSES = ["active", "paused", "completed"]
N_CREATIVES = 56   # 14 per platform — satisfies ≥50 requirement

# Platform-specific CTR medians for creative generation
CREATIVE_CTR_MEDIAN = {"Meta": 0.018, "TikTok": 0.022, "LinkedIn": 0.010, "Other": 0.014}
CREATIVE_CVR_MEDIAN = {"Meta": 0.150, "TikTok": 0.120, "LinkedIn": 0.105, "Other": 0.115}

# ---------------------------------------------------------------------------
# Audience definitions
# ---------------------------------------------------------------------------
N_AUDIENCES = 16

AUDIENCE_TYPES = [
    "custom_list", "lookalike", "interest", "retargeting",
    "crm_match", "behavioral", "demographic",
]

AUDIENCE_TEMPLATES = [
    ("Existing Customers – Meta",        "Meta",     "crm_match",   (85_000, 210_000),  (0.70, 0.85)),
    ("High-Intent Lookalike 1% – Meta",  "Meta",     "lookalike",   (1_200_000, 3_500_000), (0.55, 0.70)),
    ("Retargeting – Site Visitors – Meta","Meta",    "retargeting", (45_000, 120_000),  (0.65, 0.80)),
    ("New Mover Audience – Meta",        "Meta",     "behavioral",  (90_000, 250_000),  (0.55, 0.70)),
    ("Homeowners 35-54 – Meta",          "Meta",     "demographic", (500_000, 1_800_000), (0.40, 0.60)),
    ("TikTok CRM Upload",                "TikTok",   "crm_match",   (72_000, 180_000),  (0.60, 0.80)),
    ("TikTok Lookalike – Funded Acct",   "TikTok",   "lookalike",   (800_000, 2_200_000), (0.45, 0.65)),
    ("TikTok 18-34 High HHI",            "TikTok",   "demographic", (400_000, 1_100_000), (0.38, 0.55)),
    ("TikTok Retargeting – Video Views", "TikTok",   "retargeting", (30_000, 90_000),   (0.60, 0.78)),
    ("LinkedIn Decision Makers",         "LinkedIn", "demographic", (150_000, 420_000), (0.35, 0.55)),
    ("LinkedIn CRM Match",               "LinkedIn", "crm_match",   (40_000, 110_000),  (0.65, 0.82)),
    ("LinkedIn Job Changers",            "LinkedIn", "behavioral",  (80_000, 200_000),  (0.42, 0.62)),
    ("LinkedIn Retargeting – Engagers",  "LinkedIn", "retargeting", (15_000, 45_000),   (0.68, 0.84)),
    ("Pinterest Home Finance",           "Other",    "interest",    (250_000, 700_000), (0.38, 0.55)),
    ("Snapchat 25-40 Homeowners",        "Other",    "demographic", (180_000, 520_000), (0.36, 0.52)),
    ("Other Retargeting Pool",           "Other",    "retargeting", (22_000, 65_000),   (0.62, 0.78)),
]
assert len(AUDIENCE_TEMPLATES) == N_AUDIENCES

# Performance lift vs. no audience (1.0 = baseline, >1.0 = lift)
AUDIENCE_LIFT_PARAMS = {
    "crm_match":   (2.0, 3.2),
    "lookalike":   (1.4, 2.2),
    "retargeting": (1.8, 2.8),
    "behavioral":  (1.3, 2.0),
    "interest":    (1.1, 1.6),
    "demographic": (1.0, 1.5),
    "custom_list": (1.5, 2.5),
}


# ---------------------------------------------------------------------------
# Builder: platform_daily
# ---------------------------------------------------------------------------

def build_platform_daily() -> pd.DataFrame:
    """Generate 360 daily rows (4 platforms × 90 days) with spend exactly
    reconciling to 15% of total_media_budget ($2,250,000).

    Strategy: generate raw spend shares with log-normal noise + weekday/month
    seasonality, then rescale each platform's total to hit its target.
    """
    rows: list = []
    now = pd.Timestamp.now()

    for platform in PLATFORMS:
        params = PLATFORM_PARAMS[platform]
        wd_mult, we_mult = PLATFORM_WEEKDAY_MULT[platform]
        target_spend = TOTAL_SOCIAL_SPEND * PLATFORM_SHARE[platform]
        daily_base = target_spend / 90.0

        # Generate raw spends with seasonality + noise
        raw_spends: list[float] = []
        for d in DATES:
            is_weekend = d.weekday() >= 5
            day_mult = we_mult if is_weekend else wd_mult
            month_mult = _MONTH_SEASONALITY[d.month]
            noise = float(rng.lognormal(0.0, 0.12))
            raw_spends.append(daily_base * day_mult * month_mult * noise)

        # Rescale so sum = target_spend exactly
        raw_total = sum(raw_spends)
        scale = target_spend / raw_total
        spends = [round(s * scale, 4) for s in raw_spends]

        for i, d in enumerate(DATES):
            spend = max(1.0, spends[i])
            is_weekend = d.weekday() >= 5

            # Impressions via CPM
            cpm = float(rng.uniform(*params["cpm"]))
            impressions = max(100, int(spend / cpm * 1000.0))

            # CTR + clicks
            ctr = float(rng.uniform(*params["ctr"]))
            clicks = max(0, int(impressions * ctr))

            # CVRs
            cvr_native = round(
                float(np.clip(rng.uniform(*params["cvr_native"]), 0.08, 0.20)), 6
            )
            cvr_landing = round(
                float(np.clip(rng.uniform(*params["cvr_landing"]), 0.025, 0.065)), 6
            )

            # Leads via each conversion path
            leads_native = max(0, int(clicks * cvr_native))
            leads_landing = max(0, int(clicks * cvr_landing))
            total_leads = leads_native + leads_landing

            cpa_native = round(spend / max(leads_native, 1), 4)
            cpa_landing = round(spend / max(leads_landing, 1), 4)

            rows.append({
                "id":            str(uuid.uuid4()),
                "platform":      platform,
                "record_date":   d,
                "spend":         round(spend, 4),
                "impressions":   impressions,
                "clicks":        clicks,
                "ctr":           round(ctr, 6),
                "cvr_native":    cvr_native,
                "cvr_landing":   cvr_landing,
                "leads_native":  leads_native,
                "leads_landing": leads_landing,
                "total_leads":   total_leads,
                "cpa_native":    cpa_native,
                "cpa_landing":   cpa_landing,
                "created_at":    now,
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Builder: creatives
# ---------------------------------------------------------------------------

def build_creatives() -> pd.DataFrame:
    """Generate 56 creative performance records (14 per platform)."""
    rows: list = []
    now = pd.Timestamp.now()
    creative_num = 1

    for platform in PLATFORMS:
        ctr_med = CREATIVE_CTR_MEDIAN[platform]
        cvr_med = CREATIVE_CVR_MEDIAN[platform]

        for i in range(N_CREATIVES // len(PLATFORMS)):
            fmt = str(rng.choice(CREATIVE_FORMATS))
            camp_type = str(rng.choice(CAMPAIGN_TYPES))

            ctr = round(
                float(np.clip(rng.normal(ctr_med, ctr_med * 0.30), 0.002, 0.06)), 6
            )
            # CVR for creatives uses native lead-form range (10–16%)
            cvr = round(
                float(np.clip(rng.normal(cvr_med, cvr_med * 0.12), 0.08, 0.20)), 6
            )

            spend = round(float(rng.uniform(8_000, 120_000)), 2)
            cpm = float(rng.uniform(*PLATFORM_PARAMS[platform]["cpm"]))
            impressions = max(100, int(spend / cpm * 1000.0))
            clicks = max(0, int(impressions * ctr))
            conversions = max(0, int(clicks * cvr))

            # Weight statuses: mostly active, some paused/completed
            status = str(rng.choice(
                CREATIVE_STATUSES, p=[0.55, 0.20, 0.25]
            ))

            rows.append({
                "id":            str(uuid.uuid4()),
                "creative_id":   f"SC-{creative_num:04d}",
                "platform":      platform,
                "format":        fmt,
                "campaign_type": camp_type,
                "ctr":           ctr,
                "cvr":           cvr,
                "spend":         spend,
                "impressions":   impressions,
                "clicks":        clicks,
                "conversions":   conversions,
                "status":        status,
                "created_at":    now,
            })
            creative_num += 1

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Builder: audiences
# ---------------------------------------------------------------------------

def build_audiences() -> pd.DataFrame:
    """Generate 16 first-party audience segment records."""
    rows: list = []
    now = pd.Timestamp.now()

    for i, (name, platform, seg_type, size_range, match_range) in enumerate(
        AUDIENCE_TEMPLATES
    ):
        size = int(rng.integers(*size_range))
        match_rate = round(float(rng.uniform(*match_range)), 4)
        lift_lo, lift_hi = AUDIENCE_LIFT_PARAMS[seg_type]
        performance_lift = round(float(rng.uniform(lift_lo, lift_hi)), 4)
        status = "active" if i < 14 else "paused"   # 14 active, 2 paused

        rows.append({
            "id":               str(uuid.uuid4()),
            "audience_name":    name,
            "platform":         platform,
            "segment_type":     seg_type,
            "size":             size,
            "match_rate":       match_rate,
            "performance_lift": performance_lift,
            "status":           status,
            "created_at":       now,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pandera schemas (local — also registered in validation.py)
# ---------------------------------------------------------------------------

SOCIAL_PAID_DAILY_SCHEMA = DataFrameSchema(
    {
        "id":            Column(str,   nullable=False),
        "platform":      Column(str,   Check.isin(PLATFORMS)),
        "record_date":   Column("object", nullable=False),
        "spend":         Column(float, Check.greater_than(0)),
        "impressions":   Column(int,   Check.greater_than_or_equal_to(0)),
        "clicks":        Column(int,   Check.greater_than_or_equal_to(0)),
        "ctr":           Column(float, Check.in_range(0.0, 0.20)),
        "cvr_native":    Column(float, Check.in_range(0.08, 0.22)),
        "cvr_landing":   Column(float, Check.in_range(0.02, 0.07)),
        "leads_native":  Column(int,   Check.greater_than_or_equal_to(0)),
        "leads_landing": Column(int,   Check.greater_than_or_equal_to(0)),
        "total_leads":   Column(int,   Check.greater_than_or_equal_to(0)),
        "cpa_native":    Column(float, Check.greater_than(0)),
        "cpa_landing":   Column(float, Check.greater_than(0)),
    },
    checks=[
        Check(
            lambda df: len(df) == 360,
            error="social_paid_daily: expected 360 rows (4 platforms × 90 days)",
        ),
        Check(
            lambda df: df["platform"].nunique() == 4,
            error="social_paid_daily: must have all 4 platforms",
        ),
        Check(
            lambda df: abs(df["spend"].sum() - TOTAL_SOCIAL_SPEND) < 1.0,
            error=f"social_paid_daily: total spend must be ${TOTAL_SOCIAL_SPEND:,.0f} (±$1)",
        ),
        Check(
            lambda df: (
                df[df["platform"] == "Meta"]["spend"].sum() /
                df["spend"].sum()
            ).round(2) >= 0.68,
            error="social_paid_daily: Meta spend share must be ≥68%",
        ),
    ],
    coerce=True,
)

SOCIAL_PAID_CREATIVES_SCHEMA = DataFrameSchema(
    {
        "id":            Column(str,   nullable=False),
        "creative_id":   Column(str,   nullable=False),
        "platform":      Column(str,   Check.isin(PLATFORMS)),
        "format":        Column(str,   Check.isin(CREATIVE_FORMATS)),
        "campaign_type": Column(str,   Check.isin(CAMPAIGN_TYPES)),
        "ctr":           Column(float, Check.in_range(0.0, 0.10)),
        "cvr":           Column(float, Check.in_range(0.08, 0.22)),
        "spend":         Column(float, Check.greater_than(0)),
        "impressions":   Column(int,   Check.greater_than(0)),
        "clicks":        Column(int,   Check.greater_than_or_equal_to(0)),
        "conversions":   Column(int,   Check.greater_than_or_equal_to(0)),
        "status":        Column(str,   Check.isin(CREATIVE_STATUSES)),
    },
    checks=[
        Check(
            lambda df: len(df) >= 50,
            error="social_paid_creatives: must have >= 50 rows",
        ),
        Check(
            lambda df: df["platform"].nunique() == 4,
            error="social_paid_creatives: must represent all 4 platforms",
        ),
        Check(
            lambda df: df["format"].nunique() >= 2,
            error="social_paid_creatives: must have >= 2 creative formats",
        ),
    ],
    coerce=True,
)

SOCIAL_PAID_AUDIENCES_SCHEMA = DataFrameSchema(
    {
        "id":               Column(str,   nullable=False),
        "audience_name":    Column(str,   nullable=False),
        "platform":         Column(str,   Check.isin(PLATFORMS)),
        "segment_type":     Column(str,   Check.isin(AUDIENCE_TYPES)),
        "size":             Column(int,   Check.greater_than(0)),
        "match_rate":       Column(float, Check.in_range(0.30, 0.90)),
        "performance_lift": Column(float, Check.greater_than_or_equal_to(1.0)),
        "status":           Column(str,   Check.isin(["active", "paused"])),
    },
    checks=[
        Check(
            lambda df: len(df).between(12, 20) if hasattr(len(df), "between") else 12 <= len(df) <= 20,
            error="social_paid_audiences: must have 12–20 segments",
        ),
        Check(
            lambda df: (df["status"] == "active").sum() >= 12,
            error="social_paid_audiences: must have >= 12 active segments",
        ),
        Check(
            lambda df: df["performance_lift"].gt(1.0).any(),
            error="social_paid_audiences: at least one segment must show >1.0 lift",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# DDL — new social tables
# ---------------------------------------------------------------------------

_DDL_SOCIAL_PAID_DAILY = """
CREATE TABLE IF NOT EXISTS social_paid_daily (
    id            VARCHAR PRIMARY KEY,
    platform      VARCHAR NOT NULL,
    record_date   DATE    NOT NULL,
    spend         DECIMAL(18, 4) NOT NULL,
    impressions   INTEGER NOT NULL,
    clicks        INTEGER NOT NULL,
    ctr           DECIMAL(10, 6) NOT NULL,
    cvr_native    DECIMAL(10, 6) NOT NULL,
    cvr_landing   DECIMAL(10, 6) NOT NULL,
    leads_native  INTEGER NOT NULL,
    leads_landing INTEGER NOT NULL,
    total_leads   INTEGER NOT NULL,
    cpa_native    DECIMAL(18, 4) NOT NULL,
    cpa_landing   DECIMAL(18, 4) NOT NULL,
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_DDL_SOCIAL_PAID_CREATIVES = """
CREATE TABLE IF NOT EXISTS social_paid_creatives (
    id            VARCHAR PRIMARY KEY,
    creative_id   VARCHAR NOT NULL UNIQUE,
    platform      VARCHAR NOT NULL,
    format        VARCHAR NOT NULL,
    campaign_type VARCHAR NOT NULL,
    ctr           DECIMAL(10, 6) NOT NULL,
    cvr           DECIMAL(10, 6) NOT NULL,
    spend         DECIMAL(18, 2) NOT NULL,
    impressions   INTEGER NOT NULL,
    clicks        INTEGER NOT NULL,
    conversions   INTEGER NOT NULL,
    status        VARCHAR NOT NULL DEFAULT 'active',
    created_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_DDL_SOCIAL_PAID_AUDIENCES = """
CREATE TABLE IF NOT EXISTS social_paid_audiences (
    id               VARCHAR PRIMARY KEY,
    audience_name    VARCHAR NOT NULL,
    platform         VARCHAR NOT NULL,
    segment_type     VARCHAR NOT NULL,
    size             INTEGER NOT NULL,
    match_rate       DECIMAL(6, 4) NOT NULL,
    performance_lift DECIMAL(8, 4) NOT NULL,
    status           VARCHAR NOT NULL DEFAULT 'active',
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

def generate_social_data(verbose: bool = True) -> dict[str, pd.DataFrame]:
    """Build and insert paid social seed data.

    Creates three tables:
      - social_paid_daily      (360 rows — 4 platforms × 90 days)
      - social_paid_creatives  (56 rows)
      - social_paid_audiences  (16 rows)

    Returns a dict of DataFrames keyed by table name.
    """
    df_daily = build_platform_daily()
    df_creatives = build_creatives()
    df_audiences = build_audiences()

    # Type coercions
    for col in ("spend", "ctr", "cvr_native", "cvr_landing", "cpa_native", "cpa_landing"):
        df_daily[col] = df_daily[col].astype(float)
    for col in ("impressions", "clicks", "leads_native", "leads_landing", "total_leads"):
        df_daily[col] = df_daily[col].astype(int)

    for col in ("ctr", "cvr", "spend"):
        df_creatives[col] = df_creatives[col].astype(float)
    for col in ("impressions", "clicks", "conversions"):
        df_creatives[col] = df_creatives[col].astype(int)

    df_audiences["match_rate"] = df_audiences["match_rate"].astype(float)
    df_audiences["performance_lift"] = df_audiences["performance_lift"].astype(float)
    df_audiences["size"] = df_audiences["size"].astype(int)

    # Pandera validation
    SOCIAL_PAID_DAILY_SCHEMA.validate(df_daily)
    SOCIAL_PAID_CREATIVES_SCHEMA.validate(df_creatives)
    SOCIAL_PAID_AUDIENCES_SCHEMA.validate(df_audiences)

    conn = get_connection()
    try:
        # Ensure tables exist
        for ddl in (_DDL_SOCIAL_PAID_DAILY, _DDL_SOCIAL_PAID_CREATIVES, _DDL_SOCIAL_PAID_AUDIENCES):
            conn.execute(ddl)

        # social_paid_daily
        conn.execute("DELETE FROM social_paid_daily")
        conn.register("_spd", df_daily)
        conn.execute("""
            INSERT INTO social_paid_daily
                (id, platform, record_date, spend, impressions, clicks, ctr,
                 cvr_native, cvr_landing, leads_native, leads_landing,
                 total_leads, cpa_native, cpa_landing, created_at)
            SELECT id, platform, record_date, spend, impressions, clicks, ctr,
                   cvr_native, cvr_landing, leads_native, leads_landing,
                   total_leads, cpa_native, cpa_landing, created_at
            FROM _spd
        """)

        # social_paid_creatives
        conn.execute("DELETE FROM social_paid_creatives")
        conn.register("_spc", df_creatives)
        conn.execute("""
            INSERT INTO social_paid_creatives
                (id, creative_id, platform, format, campaign_type,
                 ctr, cvr, spend, impressions, clicks, conversions,
                 status, created_at)
            SELECT id, creative_id, platform, format, campaign_type,
                   ctr, cvr, spend, impressions, clicks, conversions,
                   status, created_at
            FROM _spc
        """)

        # social_paid_audiences
        conn.execute("DELETE FROM social_paid_audiences")
        conn.register("_spa", df_audiences)
        conn.execute("""
            INSERT INTO social_paid_audiences
                (id, audience_name, platform, segment_type, size,
                 match_rate, performance_lift, status, created_at)
            SELECT id, audience_name, platform, segment_type, size,
                   match_rate, performance_lift, status, created_at
            FROM _spa
        """)

        conn.commit()

    finally:
        for name in ("_spd", "_spc", "_spa"):
            try:
                conn.unregister(name)
            except Exception:
                pass
        conn.close()

    if verbose:
        total_spend = df_daily["spend"].sum()
        budget_pct = total_spend / TOTAL_MEDIA_BUDGET * 100

        print(f"[social] social_paid_daily: {len(df_daily):,} rows")
        print(f"  Date range:   {df_daily['record_date'].min()} → {df_daily['record_date'].max()}")
        print(f"  Total spend:  ${total_spend:,.2f}  ({budget_pct:.1f}% of total media budget)")
        print()
        print("  Platform breakdown:")
        by_platform = (
            df_daily.groupby("platform")
            .agg(spend=("spend", "sum"), leads=("total_leads", "sum"))
        )
        for plat, row in by_platform.iterrows():
            share = row["spend"] / total_spend * 100
            print(f"    {plat:<12}  spend=${row['spend']:>12,.0f}  ({share:.0f}%)  leads={row['leads']:,}")
        print()

        print(f"[social] social_paid_creatives: {len(df_creatives):,} rows")
        status_counts = df_creatives["status"].value_counts().to_dict()
        format_counts = df_creatives["format"].value_counts().to_dict()
        print(f"  Statuses: {status_counts}")
        print(f"  Formats:  {format_counts}")
        print(f"  Avg CVR:  {df_creatives['cvr'].mean():.2%}")
        print()

        print(f"[social] social_paid_audiences: {len(df_audiences):,} rows")
        active = (df_audiences["status"] == "active").sum()
        avg_lift = df_audiences["performance_lift"].mean()
        avg_match = df_audiences["match_rate"].mean()
        print(f"  Active segments: {active}")
        print(f"  Avg match rate:  {avg_match:.1%}")
        print(f"  Avg lift:        {avg_lift:.2f}×")

        # Budget reconciliation confirmation
        print()
        print(f"  Budget check: ${total_spend:,.2f} / ${TOTAL_MEDIA_BUDGET:,.0f} = {budget_pct:.2f}%  (target: 15.00%)")
        if abs(total_spend - TOTAL_SOCIAL_SPEND) < 1.0:
            print("  ✓ Spend reconciles to within $1 of target")
        else:
            delta = total_spend - TOTAL_SOCIAL_SPEND
            print(f"  ⚠ Spend delta: ${delta:+,.2f}")

    return {
        "platform_daily": df_daily,
        "creatives":       df_creatives,
        "audiences":       df_audiences,
    }


# Back-compat alias so run_all.py can call seed() uniformly
def seed(verbose: bool = True) -> pd.DataFrame:
    """Seed wrapper — calls generate_social_data() and returns platform_daily."""
    dfs = generate_social_data(verbose=verbose)
    return dfs["platform_daily"]


if __name__ == "__main__":
    dfs = generate_social_data(verbose=True)
    total_rows = sum(len(v) for v in dfs.values())
    print(f"\nTotal rows seeded: {total_rows}")
