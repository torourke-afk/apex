"""Seed: SEM Keyword Groups & Daily Performance  (APE-88)

Generates:
  - 220 keyword groups spanning branded, non-branded, and pmax intent
    across 7 product categories and 3 match types.
  - 90-day daily performance records for all groups.

Keyword group breakdown:
  Branded      88  (~40%)  — CPC $0.40–2.00, CTR 8–18%, QS 7–10
  Non-branded  99  (~45%)  — CPC $2.00–5.00, CTR 4–10%, QS 5–8
  PMax         33  (~15%)  — CPC $1.00–3.00, CTR 6–12%, QS 5–9
  ─────────────────
  Total       220

Match type allocation: broad 30%, exact 45%, phrase 25%.
Market segment distribution: established 50%, growth 30%, new 20%.
Daily rows: 220 groups × 90 days = 19,800 rows.
VBB margin signal: float [0, 1], higher = stronger margin signal.

Idempotent: DROP + CREATE + INSERT on both tables.

Run:
    python -m src.data.seeds.seed_sem
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
from pandera.pandas import Check, Column, DataFrameSchema

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
# RNG & temporal window
# ---------------------------------------------------------------------------
SEED = 99
rng = np.random.default_rng(SEED)

DATES: List[date] = [DAY_0 + timedelta(days=i) for i in range(90)]

# ---------------------------------------------------------------------------
# Product categories
# ---------------------------------------------------------------------------
PRODUCT_CATEGORIES: List[str] = [
    "checking",
    "savings",
    "credit_card",
    "mortgage",
    "auto_loan",
    "heloc",
    "personal_loan",
]

PRODUCT_LABELS: dict = {
    "checking":      "checking account",
    "savings":       "savings account",
    "credit_card":   "credit card",
    "mortgage":      "mortgage",
    "auto_loan":     "auto loan",
    "heloc":         "home equity line of credit",
    "personal_loan": "personal loan",
}

# ---------------------------------------------------------------------------
# Market segments
# ---------------------------------------------------------------------------
MARKET_SEGMENTS: List[str] = ["established", "growth", "new"]
MARKET_SEGMENT_WEIGHTS: List[float] = [0.50, 0.30, 0.20]

# ---------------------------------------------------------------------------
# Branded keyword templates  (13 × 7 = 91 → sample 88)
# ---------------------------------------------------------------------------
BRANDED_TEMPLATES: List[str] = [
    "fifth third {product}",
    "fifth third bank {product}",
    "fifth 3rd {product}",
    "53 bank {product}",
    "fifth third {product} account",
    "fifth third {product} online",
    "fifth third {product} near me",
    "fifth third {product} rates",
    "fifth third bank {product} review",
    "53 {product}",
    "fifth third {product} apply",
    "fifth third {product} login",
    "fifth third {product} offer",
]

# ---------------------------------------------------------------------------
# Non-branded keyword templates  (7 × 17 + 7 extra = 126 → sample 99)
# ---------------------------------------------------------------------------
_NB_SHARED: List[str] = [
    "best {product} near me",
    "best {product} rates",
    "open {product} online",
    "{product} with no monthly fee",
    "compare {product} offers",
    "top {product} banks {year}",
    "{product} sign up bonus",
    "high yield {product}",
    "low rate {product}",
    "{product} for bad credit",
    "{product} requirements",
    "how to get a {product}",
    "{product} application",
    "{product} approval odds",
    "bank {product} reviews",
    "online {product} account",
    "instant approval {product}",
]

_NB_CATEGORY_EXTRAS: dict = {
    "checking":      "{product} with cashback rewards",
    "savings":       "high interest {product} account",
    "credit_card":   "{product} travel rewards",
    "mortgage":      "fixed rate {product} lender",
    "auto_loan":     "{product} refinance rates",
    "heloc":         "{product} draw period rules",
    "personal_loan": "unsecured {product} same day",
}

# ---------------------------------------------------------------------------
# PMax campaign templates  (5 × 7 = 35 → sample 33)
# ---------------------------------------------------------------------------
PMAX_TEMPLATES: List[str] = [
    "PMax - {product} - New Movers",
    "PMax - {product} - Life Events",
    "PMax - {product} - High Value",
    "PMax - {product} - Cross Sell",
    "PMax - {product} - Reactivation",
]

# ---------------------------------------------------------------------------
# Match type distribution and CPC ranges
# ---------------------------------------------------------------------------
MATCH_TYPES: List[str] = ["broad", "exact", "phrase"]
MATCH_WEIGHTS: List[float] = [0.30, 0.45, 0.25]

# max_cpc by (intent, match_type)
MAX_CPC_RANGES: dict = {
    ("branded",     "broad"):  (0.40, 1.50),
    ("branded",     "phrase"): (0.50, 1.80),
    ("branded",     "exact"):  (0.60, 2.00),
    ("non_branded", "broad"):  (2.00, 3.50),
    ("non_branded", "phrase"): (2.50, 4.00),
    ("non_branded", "exact"):  (3.00, 5.00),
    ("pmax",        "broad"):  (1.00, 2.00),
    ("pmax",        "phrase"): (1.20, 2.50),
    ("pmax",        "exact"):  (1.50, 3.00),
}

# Actual avg cpc is 70–90% of max_cpc
CPC_REALISATION = (0.70, 0.90)

# Monthly search volume ranges by intent
MONTHLY_VOL_RANGES: dict = {
    "branded":     (5_000,  80_000),
    "non_branded": (2_000, 150_000),
    "pmax":        (10_000, 200_000),
}

# Quality score distributions by intent (mean, std — clipped to 3–10)
QS_PARAMS: dict = {
    "branded":     (8.5, 1.0),
    "non_branded": (6.5, 1.2),
    "pmax":        (7.0, 1.0),
}

# Impression share by intent
IS_RANGES: dict = {
    "branded":     (0.85, 0.97),
    "non_branded": (0.20, 0.60),
    "pmax":        (0.40, 0.75),
}

# CTR ranges by intent
CTR_RANGES: dict = {
    "branded":     (0.08, 0.18),
    "non_branded": (0.04, 0.10),
    "pmax":        (0.06, 0.12),
}

# Conversion rate ranges by intent
CVR_RANGES: dict = {
    "branded":     (0.04, 0.12),
    "non_branded": (0.02, 0.07),
    "pmax":        (0.03, 0.09),
}

# VBB margin signal ranges by intent [0, 1]
VBB_RANGES: dict = {
    "branded":     (0.30, 0.80),
    "non_branded": (0.10, 0.60),
    "pmax":        (0.20, 0.70),
}

# Avg position ranges by intent
POS_RANGES: dict = {
    "branded":     (1.0, 2.5),
    "non_branded": (1.5, 4.5),
    "pmax":        (1.0, 2.0),
}

# Weekday/weekend multiplier
WEEKDAY_MULT = 1.10
WEEKEND_MULT = 0.80


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick_match_type() -> str:
    return str(rng.choice(MATCH_TYPES, p=MATCH_WEIGHTS))


def _pick_market_segment() -> str:
    return str(rng.choice(MARKET_SEGMENTS, p=MARKET_SEGMENT_WEIGHTS))


def _quality_score(intent: str) -> int:
    mu, sigma = QS_PARAMS[intent]
    return int(np.clip(round(rng.normal(mu, sigma)), 3, 10))


def _max_cpc(intent: str, match_type: str) -> float:
    lo, hi = MAX_CPC_RANGES[(intent, match_type)]
    return round(float(rng.uniform(lo, hi)), 2)


def _monthly_volume(intent: str) -> int:
    lo, hi = MONTHLY_VOL_RANGES[intent]
    mu = np.log((lo + hi) / 2)
    val = int(np.clip(rng.lognormal(mu, 0.6), lo, hi))
    return max(lo, round(val / 100) * 100)


# ---------------------------------------------------------------------------
# Build keyword groups
# ---------------------------------------------------------------------------

def build_keyword_groups() -> pd.DataFrame:
    """Return DataFrame of 220 SEM keyword groups.

    Distribution: ~40% branded, ~45% non_branded, ~15% pmax.
    Match types: broad 30%, exact 45%, phrase 25%.
    Market segments: established 50%, growth 30%, new 20%.
    """
    rows: list = []
    now = pd.Timestamp.now()
    rng_sample = np.random.default_rng(SEED + 1)

    # ── Branded (88 = sample from 13 templates × 7 categories = 91) ─────────
    branded_candidates: List[dict] = []
    for cat in PRODUCT_CATEGORIES:
        label = PRODUCT_LABELS[cat]
        for tmpl in BRANDED_TEMPLATES:
            mt = _pick_match_type()
            branded_candidates.append({
                "id":                       str(uuid.uuid4()),
                "name":                     tmpl.format(product=label),
                "product_category":         cat,
                "intent_type":              "branded",
                "match_type":               mt,
                "market_segment":           _pick_market_segment(),
                "max_cpc":                  _max_cpc("branded", mt),
                "quality_score":            _quality_score("branded"),
                "estimated_monthly_volume": _monthly_volume("branded"),
                "is_active":                True,
                "dma":                      None,
                "created_at":               now,
                "updated_at":               now,
            })
    idx = rng_sample.choice(len(branded_candidates), size=88, replace=False)
    rows.extend([branded_candidates[i] for i in sorted(idx)])

    # ── Non-branded (99 = sample from 18 × 7 = 126 candidates) ─────────────
    nb_candidates: List[dict] = []
    for cat in PRODUCT_CATEGORIES:
        label = PRODUCT_LABELS[cat]
        templates = _NB_SHARED + [_NB_CATEGORY_EXTRAS[cat]]
        for tmpl in templates:
            mt = _pick_match_type()
            nb_candidates.append({
                "id":                       str(uuid.uuid4()),
                "name":                     tmpl.format(product=label, year="2026"),
                "product_category":         cat,
                "intent_type":              "non_branded",
                "match_type":               mt,
                "market_segment":           _pick_market_segment(),
                "max_cpc":                  _max_cpc("non_branded", mt),
                "quality_score":            _quality_score("non_branded"),
                "estimated_monthly_volume": _monthly_volume("non_branded"),
                "is_active":                bool(rng.random() > 0.10),
                "dma":                      None,
                "created_at":               now,
                "updated_at":               now,
            })
    idx = rng_sample.choice(len(nb_candidates), size=99, replace=False)
    rows.extend([nb_candidates[i] for i in sorted(idx)])

    # ── PMax (33 = sample from 5 × 7 = 35 candidates) ──────────────────────
    pmax_candidates: List[dict] = []
    for cat in PRODUCT_CATEGORIES:
        label = PRODUCT_LABELS[cat]
        for tmpl in PMAX_TEMPLATES:
            mt = _pick_match_type()
            pmax_candidates.append({
                "id":                       str(uuid.uuid4()),
                "name":                     tmpl.format(product=label.title()),
                "product_category":         cat,
                "intent_type":              "pmax",
                "match_type":               mt,
                "market_segment":           _pick_market_segment(),
                "max_cpc":                  _max_cpc("pmax", mt),
                "quality_score":            _quality_score("pmax"),
                "estimated_monthly_volume": _monthly_volume("pmax"),
                "is_active":                True,
                "dma":                      None,
                "created_at":               now,
                "updated_at":               now,
            })
    idx = rng_sample.choice(len(pmax_candidates), size=33, replace=False)
    rows.extend([pmax_candidates[i] for i in sorted(idx)])

    df = pd.DataFrame(rows)
    assert len(df) >= 200, f"Expected >= 200 keyword groups, got {len(df)}"
    return df


# ---------------------------------------------------------------------------
# Build daily performance
# ---------------------------------------------------------------------------

def build_daily_performance(df_groups: pd.DataFrame) -> pd.DataFrame:
    """Return 220 × 90 = 19,800 daily SEM performance rows."""
    rows: list = []

    for _, grp in df_groups.iterrows():
        intent: str = grp["intent_type"]
        qs_base: int = int(grp["quality_score"])
        max_cpc: float = float(grp["max_cpc"])
        monthly_vol: int = int(grp["estimated_monthly_volume"])
        is_active: bool = bool(grp["is_active"])

        ctr_lo, ctr_hi = CTR_RANGES[intent]
        cvr_lo, cvr_hi = CVR_RANGES[intent]
        pos_lo, pos_hi = POS_RANGES[intent]
        is_lo, is_hi = IS_RANGES[intent]
        vbb_lo, vbb_hi = VBB_RANGES[intent]

        daily_imp_base = monthly_vol / 30.0
        activity_scale = 1.0 if is_active else 0.20

        for d in DATES:
            is_weekend = d.weekday() >= 5
            day_mult = WEEKEND_MULT if is_weekend else WEEKDAY_MULT

            noise = float(rng.lognormal(0.0, 0.25))
            impressions = max(0, int(daily_imp_base * day_mult * noise * activity_scale))

            ctr = float(rng.uniform(ctr_lo, ctr_hi))
            clicks = max(0, int(impressions * ctr))

            realise = float(rng.uniform(*CPC_REALISATION))
            cpc = round(max_cpc * realise * float(rng.lognormal(0.0, 0.08)), 4)

            spend = round(clicks * cpc, 4)

            avg_position = round(float(rng.uniform(pos_lo, pos_hi)), 2)
            impression_share = round(float(rng.uniform(is_lo, is_hi)), 4)

            # Quality score: slight daily jitter ±1 around base, clamped 3–10
            qs_day = int(np.clip(qs_base + rng.integers(-1, 2), 3, 10))

            cvr = float(rng.uniform(cvr_lo, cvr_hi))
            conversions = max(0, int(clicks * cvr))
            cvr_realized = round(conversions / max(clicks, 1), 6)
            cpl = round(spend / max(conversions, 1), 4)

            # VBB margin signal: base from intent range + small daily noise
            vbb_base = float(rng.uniform(vbb_lo, vbb_hi))
            vbb = float(np.clip(vbb_base + rng.normal(0.0, 0.03), 0.0, 1.0))

            rows.append({
                "id":                str(uuid.uuid4()),
                "keyword_group_id":  grp["id"],
                "date":              d,
                "impressions":       impressions,
                "clicks":            clicks,
                "ctr":               round(ctr, 6),
                "cpc":               cpc,
                "spend":             spend,
                "avg_position":      avg_position,
                "impression_share":  impression_share,
                "quality_score":     qs_day,
                "conversions":       conversions,
                "cvr":               cvr_realized,
                "cpl":               cpl,
                "vbb_margin_signal": round(vbb, 6),
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Pandera schemas
# ---------------------------------------------------------------------------

GROUPS_SCHEMA = DataFrameSchema(
    {
        "id":                       Column(str,   nullable=False),
        "name":                     Column(str,   nullable=False),
        "product_category":         Column(str,   Check.isin(PRODUCT_CATEGORIES)),
        "intent_type":              Column(str,   Check.isin(["branded", "non_branded", "pmax"])),
        "match_type":               Column(str,   Check.isin(MATCH_TYPES)),
        "market_segment":           Column(str,   Check.isin(MARKET_SEGMENTS)),
        "max_cpc":                  Column(float, Check.greater_than(0)),
        "quality_score":            Column(int,   Check.in_range(3, 10)),
        "estimated_monthly_volume": Column(int,   Check.greater_than_or_equal_to(0)),
        "is_active":                Column(bool,  nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 200, error="Expected >= 200 keyword groups"),
        Check(lambda df: df["intent_type"].nunique() == 3, error="All 3 intent types required"),
        Check(lambda df: df["product_category"].nunique() == 7, error="All 7 product categories required"),
        Check(
            lambda df: abs(df[df["intent_type"] == "branded"].shape[0] / len(df) - 0.40) < 0.06,
            error="Branded share must be ~40% (±6%)",
        ),
        Check(
            lambda df: abs(df[df["intent_type"] == "non_branded"].shape[0] / len(df) - 0.45) < 0.06,
            error="Non-branded share must be ~45% (±6%)",
        ),
        Check(
            lambda df: abs(df["match_type"].value_counts(normalize=True).get("exact", 0) - 0.45) < 0.08,
            error="Exact match share must be ~45% (±8%)",
        ),
    ],
    coerce=True,
)

PERF_SCHEMA = DataFrameSchema(
    {
        "id":                Column(str,   nullable=False),
        "keyword_group_id":  Column(str,   nullable=False),
        "date":              Column("object", nullable=False),
        "impressions":       Column(int,   Check.greater_than_or_equal_to(0)),
        "clicks":            Column(int,   Check.greater_than_or_equal_to(0)),
        "ctr":               Column(float, Check.in_range(0.0, 1.0)),
        "cpc":               Column(float, Check.greater_than_or_equal_to(0)),
        "spend":             Column(float, Check.greater_than_or_equal_to(0)),
        "avg_position":      Column(float, Check.in_range(1.0, 10.0)),
        "impression_share":  Column(float, Check.in_range(0.0, 1.0)),
        "quality_score":     Column(int,   Check.in_range(3, 10)),
        "conversions":       Column(int,   Check.greater_than_or_equal_to(0)),
        "cvr":               Column(float, Check.in_range(0.0, 1.0)),
        "cpl":               Column(float, Check.greater_than_or_equal_to(0)),
        "vbb_margin_signal": Column(float, Check.in_range(0.0, 1.0)),
    },
    checks=[
        Check(lambda df: len(df) >= 19_000, error="Expected >= 19,000 daily rows"),
        Check(lambda df: df["date"].nunique() == 90, error="Expected 90 distinct dates"),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL_GROUPS = """
CREATE TABLE IF NOT EXISTS sem_keyword_groups (
    id                        VARCHAR PRIMARY KEY,
    name                      VARCHAR NOT NULL,
    product_category          VARCHAR NOT NULL,
    intent_type               VARCHAR NOT NULL,
    match_type                VARCHAR NOT NULL,
    market_segment            VARCHAR NOT NULL DEFAULT 'established',
    max_cpc                   DECIMAL(10, 2) NOT NULL,
    quality_score             INTEGER NOT NULL,
    estimated_monthly_volume  INTEGER NOT NULL,
    is_active                 BOOLEAN NOT NULL DEFAULT TRUE,
    dma                       VARCHAR,
    created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at                TIMESTAMP
)
"""

_DDL_PERF = """
CREATE TABLE IF NOT EXISTS sem_daily_performance (
    id                    VARCHAR PRIMARY KEY,
    keyword_group_id      VARCHAR NOT NULL,
    date                  DATE NOT NULL,
    impressions           INTEGER NOT NULL,
    clicks                INTEGER NOT NULL,
    ctr                   DECIMAL(10, 6) NOT NULL,
    cpc                   DECIMAL(10, 4) NOT NULL,
    spend                 DECIMAL(18, 4) NOT NULL,
    avg_position          DECIMAL(5, 2) NOT NULL,
    impression_share      DECIMAL(8, 4) NOT NULL,
    quality_score         INTEGER NOT NULL,
    conversions           INTEGER NOT NULL,
    cvr                   DECIMAL(10, 6) NOT NULL,
    cpl                   DECIMAL(18, 4) NOT NULL,
    vbb_margin_signal     DECIMAL(8, 6) NOT NULL,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""


# ---------------------------------------------------------------------------
# Seed entrypoint
# ---------------------------------------------------------------------------

def seed(verbose: bool = True) -> pd.DataFrame:
    """Build and insert SEM keyword groups and daily performance data.

    Returns the keyword groups DataFrame.
    """
    df_groups = build_keyword_groups()
    df_perf = build_daily_performance(df_groups)

    # Type coercions before validation
    df_groups["max_cpc"] = df_groups["max_cpc"].astype(float)
    df_groups["quality_score"] = df_groups["quality_score"].astype(int)
    df_groups["estimated_monthly_volume"] = df_groups["estimated_monthly_volume"].astype(int)
    df_groups["is_active"] = df_groups["is_active"].astype(bool)

    df_perf["impressions"] = df_perf["impressions"].astype(int)
    df_perf["clicks"] = df_perf["clicks"].astype(int)
    df_perf["ctr"] = df_perf["ctr"].astype(float)
    df_perf["cpc"] = df_perf["cpc"].astype(float)
    df_perf["spend"] = df_perf["spend"].astype(float)
    df_perf["avg_position"] = df_perf["avg_position"].astype(float)
    df_perf["impression_share"] = df_perf["impression_share"].astype(float)
    df_perf["quality_score"] = df_perf["quality_score"].astype(int)
    df_perf["conversions"] = df_perf["conversions"].astype(int)
    df_perf["cvr"] = df_perf["cvr"].astype(float)
    df_perf["cpl"] = df_perf["cpl"].astype(float)
    df_perf["vbb_margin_signal"] = df_perf["vbb_margin_signal"].astype(float)

    # Pandera validation
    GROUPS_SCHEMA.validate(df_groups)
    PERF_SCHEMA.validate(df_perf)

    conn = get_connection()
    try:
        # Ensure tables exist (with new schema — recreate if columns differ)
        conn.execute("DROP TABLE IF EXISTS sem_daily_performance")
        conn.execute("DROP TABLE IF EXISTS sem_keyword_groups")
        conn.execute(_DDL_GROUPS)
        conn.execute(_DDL_PERF)

        # Insert keyword groups
        conn.register("grp_df", df_groups)
        conn.execute("""
            INSERT INTO sem_keyword_groups
                (id, name, product_category, intent_type, match_type,
                 market_segment, max_cpc, quality_score, estimated_monthly_volume,
                 is_active, dma, created_at, updated_at)
            SELECT id, name, product_category, intent_type, match_type,
                   market_segment, max_cpc, quality_score, estimated_monthly_volume,
                   is_active, dma, created_at, updated_at
            FROM grp_df
        """)

        # Insert daily performance
        conn.register("perf_df", df_perf)
        conn.execute("""
            INSERT INTO sem_daily_performance
                (id, keyword_group_id, date, impressions, clicks,
                 ctr, cpc, spend, avg_position, impression_share,
                 quality_score, conversions, cvr, cpl, vbb_margin_signal)
            SELECT id, keyword_group_id, date, impressions, clicks,
                   ctr, cpc, spend, avg_position, impression_share,
                   quality_score, conversions, cvr, cpl, vbb_margin_signal
            FROM perf_df
        """)

        conn.commit()
    finally:
        for name in ("grp_df", "perf_df"):
            try:
                conn.unregister(name)
            except Exception:
                pass
        conn.close()

    if verbose:
        print(f"[seed_sem] Inserted {len(df_groups):,} rows into sem_keyword_groups")
        print(f"  Intent types:    {df_groups['intent_type'].value_counts().to_dict()}")
        print(f"  Match types:     {df_groups['match_type'].value_counts().to_dict()}")
        print(f"  Market segments: {df_groups['market_segment'].value_counts().to_dict()}")
        print(f"  Categories:      {df_groups['product_category'].value_counts().to_dict()}")
        print(f"  Active groups:   {df_groups['is_active'].sum()} / {len(df_groups)}")
        print(f"  QS range:        {df_groups['quality_score'].min()}–"
              f"{df_groups['quality_score'].max()} "
              f"(median {df_groups['quality_score'].median():.1f})")
        print(f"  Max CPC:         ${df_groups['max_cpc'].min():.2f} – "
              f"${df_groups['max_cpc'].max():.2f}  "
              f"(median ${df_groups['max_cpc'].median():.2f})")
        print()
        print(f"[seed_sem] Inserted {len(df_perf):,} rows into sem_daily_performance")
        print(f"  Date range:      {df_perf['date'].min()} → {df_perf['date'].max()}")
        print(f"  Total spend:     ${df_perf['spend'].sum():,.0f}")
        print(f"  Total clicks:    {df_perf['clicks'].sum():,}")
        print(f"  Avg CTR:         {df_perf['ctr'].mean():.2%}")
        print(f"  Avg CVR:         {df_perf['cvr'].mean():.2%}")
        print(f"  Avg VBB signal:  {df_perf['vbb_margin_signal'].mean():.3f}")
        print(f"  Avg position:    {df_perf['avg_position'].mean():.2f}")

        spend_by_intent = (
            df_perf.merge(df_groups[["id", "intent_type"]], left_on="keyword_group_id", right_on="id")
            .groupby("intent_type")["spend"]
            .sum()
        )
        total_spend = spend_by_intent.sum()
        print()
        print("  Spend by intent:")
        for intent, amt in spend_by_intent.sort_values(ascending=False).items():
            print(f"    {intent:<15} {amt / total_spend:>5.1%}  (${amt:,.0f})")

    return df_groups


if __name__ == "__main__":
    seed()
