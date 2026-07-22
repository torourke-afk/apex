"""Seed: SEM Channel Daily Performance Data (APE-88)

Generates 210 keyword groups × 90 days = 18,900 daily records.
Total SEM spend reconciles exactly to 25% of total media budget ($3,750,000).

Tables:
    sem_keyword_groups    — 210 keyword group definitions
    sem_daily_performance — 18,900 daily metric rows

Intent type breakdown (spec: ~40/45/15%):
    Branded:        84 groups  (40.0%) — CPC $0.50–1.50, CTR 10–15%, QS 7–10
    Non-branded:    95 groups  (45.2%) — CPC $2.00–5.00, CTR  6–10%, QS 4– 7
    PMax/AI:        31 groups  (14.8%) — CPC $1.00–3.00, CTR  8–12%, QS 5– 8

Match type allocation per group: exact 45%, broad 30%, phrase 25%.
Market segment distribution: established 40%, growth 40%, new 20%.
Quality score range: 3–10 (spec minimum is 3).
Impression share: branded 85–95%, non-branded 40–70%.

VBB margin signal: float in [0, 1] — higher value = higher margin product intent.

Budget reconciliation:
    Total spend = 25% of ANNUAL_TOTAL ($15,000,000) = $3,750,000 (exact match).

Run:
    python -m src.data.seeds.sem
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
from src.data.seeds._dates import YESTERDAY as END_DATE, TRAILING_90D_START as START_DATE

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
SEED = 97
rng = np.random.default_rng(SEED)

# From budgets.py: ANNUAL_TOTAL = $15,000,000; Performance SEM = 25%
ANNUAL_TOTAL = 15_000_000.0
SEM_BUDGET = ANNUAL_TOTAL * 0.25  # $3,750,000.00 — must match exactly

DAYS = 90

PRODUCTS = [
    "checking", "savings", "credit_card", "mortgage",
    "auto_loan", "personal_loan", "cd", "money_market",
]

MATCH_TYPES = ["broad", "exact", "phrase"]
MATCH_TYPE_PROBS = [0.30, 0.45, 0.25]  # broad 30%, exact 45%, phrase 25%

MARKET_SEGMENTS = ["established", "growth", "new"]
MARKET_SEGMENT_PROBS = [0.40, 0.40, 0.20]  # established 40%, growth 40%, new 20%

# Intent type configuration (spec: ~40/45/15% branded/non-branded/pmax)
INTENT_CONFIG = {
    "branded": {
        "count": 84,
        "cpc_lo": 0.50,  "cpc_hi": 1.50,
        "ctr_lo": 0.10,  "ctr_hi": 0.15,
        "qs_lo":  7,     "qs_hi":  10,
        "is_lo":  0.85,  "is_hi":  0.95,
        "cvr_lo": 0.025, "cvr_hi": 0.040,
        "pos_lo": 1.0,   "pos_hi": 2.5,
        "budget_share": 0.40,
        "vol_lo": 10_000, "vol_hi": 100_000,
        "vbb_lo": 0.55,  "vbb_hi": 0.85,
    },
    "non_branded": {
        "count": 95,
        "cpc_lo": 2.00,  "cpc_hi": 5.00,
        "ctr_lo": 0.06,  "ctr_hi": 0.10,
        "qs_lo":  4,     "qs_hi":  7,
        "is_lo":  0.40,  "is_hi":  0.70,
        "cvr_lo": 0.015, "cvr_hi": 0.030,
        "pos_lo": 2.0,   "pos_hi": 4.5,
        "budget_share": 0.45,
        "vol_lo": 5_000,  "vol_hi": 50_000,
        "vbb_lo": 0.30,  "vbb_hi": 0.65,
    },
    "pmax": {
        "count": 31,
        "cpc_lo": 1.00,  "cpc_hi": 3.00,
        "ctr_lo": 0.08,  "ctr_hi": 0.12,
        "qs_lo":  5,     "qs_hi":  8,
        "is_lo":  0.50,  "is_hi":  0.75,
        "cvr_lo": 0.018, "cvr_hi": 0.035,
        "pos_lo": 1.0,   "pos_hi": 2.0,
        "budget_share": 0.15,
        "vol_lo": 20_000, "vol_hi": 200_000,
        "vbb_lo": 0.40,  "vbb_hi": 0.75,
    },
}
# Verify counts and budget shares
_total_groups = sum(c["count"] for c in INTENT_CONFIG.values())
assert _total_groups == 210, f"Expected 210 groups, got {_total_groups}"
assert abs(sum(c["budget_share"] for c in INTENT_CONFIG.values()) - 1.0) < 1e-9

# ---------------------------------------------------------------------------
# Keyword name generators
# ---------------------------------------------------------------------------

_BANK_NAME = "Fifth Third"

_BRANDED_MODIFIERS = [
    "account", "online banking", "near me", "bank", "open account",
    "rates", "review", "login", "mobile app", "promo", "sign up",
    "customer service", "phone number", "routing number",
]

_NB_INTENT_PREFIXES = [
    "best", "top", "no fee", "high yield", "low rate", "online",
    "easy", "instant approval", "free", "compare", "local", "affordable",
]

_NB_SUFFIXES = [
    "account", "accounts", "rates", "near me", "online", "options",
    "deals", "bank", "2026",
]

_PMAX_AUDIENCES = [
    "new movers", "life events", "high value", "cross sell",
    "reactivation", "mass market", "premium segment",
]


def _make_branded_names(count: int) -> List[str]:
    """Generate 'count' branded keyword group names."""
    product_map = {
        "checking": "Checking",
        "savings": "Savings",
        "credit_card": "Credit Card",
        "mortgage": "Mortgage",
        "auto_loan": "Auto Loan",
        "personal_loan": "Personal Loan",
        "cd": "CD",
        "money_market": "Money Market",
    }
    combos = [
        f"{_BANK_NAME} {product_map[p]} {mod}"
        for p in PRODUCTS
        for mod in _BRANDED_MODIFIERS
    ]
    rng_local = np.random.default_rng(SEED + 1)
    idx = rng_local.permutation(len(combos))[:count]
    return [combos[i] for i in idx]


def _make_nonbranded_names(count: int) -> List[str]:
    """Generate 'count' non-branded keyword group names."""
    combos = [
        f"{pfx} {p.replace('_', ' ')} {sfx}"
        for pfx in _NB_INTENT_PREFIXES
        for p in PRODUCTS
        for sfx in _NB_SUFFIXES
    ]
    rng_local = np.random.default_rng(SEED + 2)
    idx = rng_local.permutation(len(combos))[:count]
    return [combos[i] for i in idx]


def _make_pmax_names(count: int) -> List[str]:
    """Generate 'count' PMax campaign names."""
    combos = [
        f"PMax - {p.replace('_', ' ').title()} - {aud.title()}"
        for p in PRODUCTS
        for aud in _PMAX_AUDIENCES
    ]
    rng_local = np.random.default_rng(SEED + 3)
    idx = rng_local.permutation(len(combos))[:count]
    return [combos[i] for i in idx]


# ---------------------------------------------------------------------------
# Keyword group builder
# ---------------------------------------------------------------------------

def _build_keyword_groups() -> pd.DataFrame:
    """Build 210 keyword group rows across 3 intent types."""
    rows: List[dict] = []
    now = pd.Timestamp.now()

    name_builders = {
        "branded":     _make_branded_names,
        "non_branded": _make_nonbranded_names,
        "pmax":        _make_pmax_names,
    }

    rng_mt = np.random.default_rng(SEED + 10)
    rng_ms = np.random.default_rng(SEED + 11)

    for intent_type, cfg in INTENT_CONFIG.items():
        n = cfg["count"]
        names = name_builders[intent_type](n)

        # Match types: exact 45%, broad 30%, phrase 25%
        n_broad  = round(n * MATCH_TYPE_PROBS[0])
        n_exact  = round(n * MATCH_TYPE_PROBS[1])
        n_phrase = n - n_broad - n_exact
        match_arr = (
            ["broad"]  * n_broad +
            ["exact"]  * n_exact +
            ["phrase"] * n_phrase
        )
        match_arr = [match_arr[i] for i in rng_mt.permutation(len(match_arr))]

        # Market segments: established 40%, growth 40%, new 20%
        n_estab  = round(n * MARKET_SEGMENT_PROBS[0])
        n_growth = round(n * MARKET_SEGMENT_PROBS[1])
        n_new    = n - n_estab - n_growth
        seg_arr = (
            ["established"] * n_estab +
            ["growth"]      * n_growth +
            ["new"]         * n_new
        )
        seg_arr = [seg_arr[i] for i in rng_ms.permutation(len(seg_arr))]

        # Product categories distributed proportionally
        base_products = (PRODUCTS * ((n // len(PRODUCTS)) + 1))[:n]
        product_arr = [base_products[i] for i in rng_mt.permutation(n)]

        for i in range(n):
            max_cpc = float(rng.uniform(cfg["cpc_lo"], cfg["cpc_hi"]))
            qs      = int(rng.integers(cfg["qs_lo"], cfg["qs_hi"] + 1))
            vol     = int(rng.integers(cfg["vol_lo"], cfg["vol_hi"]))

            rows.append({
                "id":                       str(uuid.uuid4()),
                "name":                     names[i],
                "product_category":         product_arr[i],
                "intent_type":              intent_type,
                "match_type":               match_arr[i],
                "max_cpc":                  round(max_cpc, 2),
                "quality_score":            qs,
                "estimated_monthly_volume": vol,
                "market_segment":           seg_arr[i],
                "is_active":                True,
                "dma":                      None,
                "created_at":               now,
                "updated_at":               now,
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Daily performance generator
# ---------------------------------------------------------------------------

def generate_sem_data() -> pd.DataFrame:
    """Generate 210 keyword groups × 90 days of SEM daily performance.

    Total spend across all rows is reconciled to exactly $3,750,000
    (25% of total media budget from budgets.py).

    Returns
    -------
    pd.DataFrame
        Daily performance records (18,900 rows).
        Also sets module-level ``_groups_df`` for seed() to persist.
    """
    global _groups_df  # noqa: PLW0603

    groups_df = _build_keyword_groups()
    _groups_df = groups_df

    n_groups = len(groups_df)  # 210
    n_days   = DAYS             # 90

    dates = pd.date_range(start=START_DATE, periods=n_days, freq="D")
    intent_types = groups_df["intent_type"].tolist()

    # Per-group base metrics (n_groups,)
    avg_cpc = np.array([
        float(rng.uniform(INTENT_CONFIG[it]["cpc_lo"], INTENT_CONFIG[it]["cpc_hi"]))
        for it in intent_types
    ], dtype=np.float64)

    avg_ctr = np.array([
        float(rng.uniform(INTENT_CONFIG[it]["ctr_lo"], INTENT_CONFIG[it]["ctr_hi"]))
        for it in intent_types
    ], dtype=np.float64)

    avg_cvr = np.array([
        float(rng.uniform(INTENT_CONFIG[it]["cvr_lo"], INTENT_CONFIG[it]["cvr_hi"]))
        for it in intent_types
    ], dtype=np.float64)

    avg_pos = np.array([
        float(rng.uniform(INTENT_CONFIG[it]["pos_lo"], INTENT_CONFIG[it]["pos_hi"]))
        for it in intent_types
    ], dtype=np.float64)

    imp_share = np.array([
        float(rng.uniform(INTENT_CONFIG[it]["is_lo"], INTENT_CONFIG[it]["is_hi"]))
        for it in intent_types
    ], dtype=np.float64)

    qs_daily = np.array([
        INTENT_CONFIG[it]["qs_lo"] +
        float(rng.uniform(0, INTENT_CONFIG[it]["qs_hi"] - INTENT_CONFIG[it]["qs_lo"]))
        for it in intent_types
    ], dtype=np.float64)

    # VBB margin signal per group, stable across days with small daily noise
    vbb_base = np.array([
        float(rng.uniform(INTENT_CONFIG[it]["vbb_lo"], INTENT_CONFIG[it]["vbb_hi"]))
        for it in intent_types
    ], dtype=np.float64)

    # Budget allocation per group (90-day total)
    group_90d_budget = np.zeros(n_groups, dtype=np.float64)
    for intent_type, cfg in INTENT_CONFIG.items():
        mask = np.array([it == intent_type for it in intent_types])
        n_in_type = mask.sum()
        type_budget = SEM_BUDGET * cfg["budget_share"]
        group_90d_budget[mask] = type_budget / n_in_type

    group_daily_base = group_90d_budget / n_days  # (n_groups,)

    # Day-level multipliers: weekday traffic pattern + gentle trend
    weekday_mult = np.where(
        np.array([d.dayofweek for d in dates]) < 5,
        1.20, 0.62
    ).astype(np.float64)
    trend_mult = np.linspace(0.88, 1.12, n_days, dtype=np.float64)
    day_mult = weekday_mult * trend_mult  # (n_days,)

    # Raw spend matrix: (n_groups, n_days)
    noise = rng.uniform(0.85, 1.15, size=(n_groups, n_days)).astype(np.float64)
    raw_spend = (
        group_daily_base[:, np.newaxis]
        * day_mult[np.newaxis, :]
        * noise
    )

    # Exact budget reconciliation: scale to SEM_BUDGET
    scale = SEM_BUDGET / raw_spend.sum()
    spend = raw_spend * scale  # (210, 90), sum == SEM_BUDGET

    # Derive clicks, impressions, conversions
    clicks_f      = spend / avg_cpc[:, np.newaxis]
    clicks        = np.maximum(np.round(clicks_f).astype(int), 1)
    impressions_f = clicks_f / avg_ctr[:, np.newaxis]
    impressions   = np.maximum(np.round(impressions_f).astype(int), 1)
    conversions_f = clicks_f * avg_cvr[:, np.newaxis]
    conversions   = np.maximum(np.round(conversions_f).astype(int), 0)

    # Realized rates from integer values
    ctr_realized = np.where(impressions > 0, clicks / impressions, 0.0)
    cvr_realized = np.where(clicks > 0, conversions / clicks, 0.0)
    cpl_realized = spend / np.maximum(conversions, 1)

    # VBB margin signal: base ± small daily noise, clamped to [0, 1]
    vbb_noise = rng.uniform(-0.05, 0.05, size=(n_groups, n_days)).astype(np.float64)
    vbb_matrix = np.clip(vbb_base[:, np.newaxis] + vbb_noise, 0.0, 1.0)

    # Flatten in C order: (group0/day0, group0/day1, ..., group1/day0, ...)
    group_ids  = np.repeat(groups_df["id"].values, n_days)
    date_arr   = np.tile(dates.date, n_groups)

    perf_df = pd.DataFrame({
        "id":                  [str(uuid.uuid4()) for _ in range(n_groups * n_days)],
        "keyword_group_id":    group_ids,
        "date":                date_arr,
        "impressions":         impressions.ravel().astype(int),
        "clicks":              clicks.ravel().astype(int),
        "ctr":                 ctr_realized.ravel().round(6),
        "cpc":                 np.repeat(avg_cpc, n_days).round(4),
        "spend":               spend.ravel().round(4),
        "avg_position":        np.repeat(avg_pos, n_days).round(2),
        "impression_share":    np.repeat(imp_share, n_days).round(4),
        "quality_score":       np.repeat(qs_daily.astype(int), n_days),
        "conversions":         conversions.ravel().astype(int),
        "cvr":                 cvr_realized.ravel().round(6),
        "cpl":                 cpl_realized.ravel().round(4),
        "vbb_margin_signal":   vbb_matrix.ravel().round(6),
    })

    return perf_df


# Module-level storage so seed() can access groups built during generate_sem_data()
_groups_df: pd.DataFrame | None = None


# ---------------------------------------------------------------------------
# Pandera schemas
# ---------------------------------------------------------------------------

VALID_INTENT_TYPES  = ["branded", "non_branded", "pmax"]
VALID_MATCH_TYPES   = ["broad", "exact", "phrase"]
VALID_MARKET_SEGS   = ["established", "growth", "new"]
VALID_PRODUCTS      = PRODUCTS

SEM_GROUPS_SCHEMA = DataFrameSchema(
    {
        "id":                       Column(str, nullable=False),
        "name":                     Column(str, nullable=False),
        "product_category":         Column(str, Check.isin(VALID_PRODUCTS), nullable=False),
        "intent_type":              Column(str, Check.isin(VALID_INTENT_TYPES), nullable=False),
        "match_type":               Column(str, Check.isin(VALID_MATCH_TYPES), nullable=False),
        "max_cpc":                  Column(float, Check.in_range(0.50, 5.00), nullable=False),
        "quality_score":            Column(int, Check.in_range(3, 10), nullable=False),
        "estimated_monthly_volume": Column(int, Check.greater_than(0), nullable=False),
        "market_segment":           Column(str, Check.isin(VALID_MARKET_SEGS), nullable=False),
        "is_active":                Column(bool, nullable=False),
    },
    checks=[
        Check(lambda df: len(df) >= 200,
              error="sem_keyword_groups: must have >= 200 groups"),
        Check(
            lambda df: abs(
                df[df["intent_type"] == "branded"].shape[0] / len(df) - 0.40
            ) < 0.05,
            error="sem_keyword_groups: branded share must be ~40% (±5%)",
        ),
        Check(
            lambda df: abs(
                df[df["intent_type"] == "non_branded"].shape[0] / len(df) - 0.45
            ) < 0.05,
            error="sem_keyword_groups: non_branded share must be ~45% (±5%)",
        ),
        Check(
            lambda df: abs(
                df[df["intent_type"] == "pmax"].shape[0] / len(df) - 0.15
            ) < 0.05,
            error="sem_keyword_groups: pmax share must be ~15% (±5%)",
        ),
        Check(
            lambda df: abs(
                df["match_type"].value_counts(normalize=True).get("exact", 0) - 0.45
            ) < 0.06,
            error="sem_keyword_groups: exact match must be ~45% (±6%)",
        ),
    ],
    coerce=True,
)

SEM_DAILY_SCHEMA = DataFrameSchema(
    {
        "id":                  Column(str, nullable=False),
        "keyword_group_id":    Column(str, nullable=False),
        "date":                Column("object", nullable=False),
        "impressions":         Column(int, Check.greater_than(0), nullable=False),
        "clicks":              Column(int, Check.greater_than(0), nullable=False),
        "ctr":                 Column(float, Check.in_range(0.0, 0.50), nullable=False),
        "cpc":                 Column(float, Check.in_range(0.40, 6.00), nullable=False),
        "spend":               Column(float, Check.greater_than(0), nullable=False),
        "avg_position":        Column(float, Check.in_range(1.0, 8.0), nullable=False),
        "impression_share":    Column(float, Check.in_range(0.0, 1.0), nullable=False),
        "quality_score":       Column(int, Check.in_range(3, 10), nullable=False),
        "conversions":         Column(int, Check.greater_than_or_equal_to(0), nullable=False),
        "cvr":                 Column(float, Check.in_range(0.0, 0.20), nullable=False),
        "cpl":                 Column(float, Check.greater_than(0), nullable=False),
        "vbb_margin_signal":   Column(float, Check.in_range(0.0, 1.0), nullable=False),
    },
    checks=[
        Check(
            lambda df: len(df) >= 200 * 90,
            error="sem_daily_performance: must have >= 18,000 rows (200 groups × 90 days)",
        ),
        Check(
            lambda df: abs(df["spend"].sum() - SEM_BUDGET) < 1.0,
            error=f"sem_daily_performance: total spend must equal ${SEM_BUDGET:,.2f} (±$1)",
        ),
        Check(
            lambda df: (df["clicks"] <= df["impressions"]).all(),
            error="sem_daily_performance: clicks must not exceed impressions",
        ),
        Check(
            lambda df: df["keyword_group_id"].nunique() >= 200,
            error="sem_daily_performance: must have >= 200 distinct keyword groups",
        ),
    ],
    coerce=True,
)


# ---------------------------------------------------------------------------
# Schema migration helper
# ---------------------------------------------------------------------------

def _recreate_sem_tables(conn) -> None:
    """Drop and recreate SEM tables with the current spec schema."""
    conn.execute("DROP TABLE IF EXISTS sem_daily_performance")
    conn.execute("DROP TABLE IF EXISTS sem_keyword_groups")
    conn.execute("""
        CREATE TABLE sem_keyword_groups (
            id                        VARCHAR PRIMARY KEY,
            name                      VARCHAR NOT NULL,
            product_category          VARCHAR NOT NULL,
            intent_type               VARCHAR NOT NULL,
            match_type                VARCHAR NOT NULL,
            max_cpc                   DECIMAL(10, 2) NOT NULL,
            quality_score             INTEGER NOT NULL,
            estimated_monthly_volume  INTEGER NOT NULL,
            market_segment            VARCHAR NOT NULL,
            is_active                 BOOLEAN NOT NULL DEFAULT TRUE,
            dma                       VARCHAR,
            created_at                TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at                TIMESTAMP
        )
    """)
    conn.execute("""
        CREATE TABLE sem_daily_performance (
            id                    VARCHAR PRIMARY KEY,
            keyword_group_id      VARCHAR NOT NULL,
            "date"                DATE NOT NULL,
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
    """)


# ---------------------------------------------------------------------------
# Seed function (writes to DuckDB)
# ---------------------------------------------------------------------------

def seed(verbose: bool = True) -> pd.DataFrame:
    """Build and insert SEM seed data into DuckDB.

    Idempotent — drops SEM tables and reinserts from scratch on every run.

    Returns
    -------
    pd.DataFrame
        Daily performance DataFrame (18,900 rows).
    """
    perf_df = generate_sem_data()

    global _groups_df
    if _groups_df is None:
        raise RuntimeError("_groups_df was not populated by generate_sem_data()")

    groups_df = _groups_df.copy()

    # Coerce types for pandera
    groups_df["max_cpc"]                   = groups_df["max_cpc"].astype(float)
    groups_df["quality_score"]             = groups_df["quality_score"].astype(int)
    groups_df["estimated_monthly_volume"]  = groups_df["estimated_monthly_volume"].astype(int)
    groups_df["is_active"]                 = groups_df["is_active"].astype(bool)

    perf_df["impressions"]       = perf_df["impressions"].astype(int)
    perf_df["clicks"]            = perf_df["clicks"].astype(int)
    perf_df["quality_score"]     = perf_df["quality_score"].astype(int)
    perf_df["conversions"]       = perf_df["conversions"].astype(int)
    perf_df["ctr"]               = perf_df["ctr"].astype(float)
    perf_df["cpc"]               = perf_df["cpc"].astype(float)
    perf_df["spend"]             = perf_df["spend"].astype(float)
    perf_df["avg_position"]      = perf_df["avg_position"].astype(float)
    perf_df["impression_share"]  = perf_df["impression_share"].astype(float)
    perf_df["cvr"]               = perf_df["cvr"].astype(float)
    perf_df["cpl"]               = perf_df["cpl"].astype(float)
    perf_df["vbb_margin_signal"] = perf_df["vbb_margin_signal"].astype(float)

    # Validate
    SEM_GROUPS_SCHEMA.validate(groups_df)
    SEM_DAILY_SCHEMA.validate(perf_df)

    conn = get_connection()
    try:
        _recreate_sem_tables(conn)

        # Insert keyword groups
        conn.register("sem_groups_df", groups_df)
        conn.execute("""
            INSERT INTO sem_keyword_groups
                (id, name, product_category, intent_type, match_type,
                 max_cpc, quality_score, estimated_monthly_volume,
                 market_segment, is_active, dma, created_at, updated_at)
            SELECT id, name, product_category, intent_type, match_type,
                   max_cpc, quality_score, estimated_monthly_volume,
                   market_segment, is_active, dma, created_at, updated_at
            FROM sem_groups_df
        """)
        conn.unregister("sem_groups_df")

        # Insert daily performance
        conn.register("sem_perf_df", perf_df)
        conn.execute("""
            INSERT INTO sem_daily_performance
                (id, keyword_group_id, "date", impressions, clicks,
                 ctr, cpc, spend, avg_position, impression_share,
                 quality_score, conversions, cvr, cpl, vbb_margin_signal)
            SELECT id, keyword_group_id, "date", impressions, clicks,
                   ctr, cpc, spend, avg_position, impression_share,
                   quality_score, conversions, cvr, cpl, vbb_margin_signal
            FROM sem_perf_df
        """)
        conn.unregister("sem_perf_df")
        conn.commit()
    finally:
        conn.close()

    if verbose:
        total_spend  = perf_df["spend"].sum()
        total_clicks = perf_df["clicks"].sum()
        total_imps   = perf_df["impressions"].sum()
        total_convs  = perf_df["conversions"].sum()
        overall_ctr  = total_clicks / max(total_imps, 1)
        overall_cvr  = total_convs / max(total_clicks, 1)

        print(f"[seed_sem] Inserted {len(groups_df)} keyword groups into sem_keyword_groups")
        print(f"[seed_sem] Inserted {len(perf_df):,} rows into sem_daily_performance")
        print(f"  Date range:        {START_DATE} → {END_DATE} ({DAYS} days)")
        print(f"  Total spend:       ${total_spend:>14,.2f}  (target: ${SEM_BUDGET:,.2f})")
        print(f"  Variance from tgt: ${total_spend - SEM_BUDGET:+.4f}")
        print(f"  Total clicks:      {total_clicks:>14,}")
        print(f"  Total impressions: {total_imps:>14,}")
        print(f"  Total conversions: {total_convs:>14,}")
        print(f"  Overall CTR:       {overall_ctr:.3%}")
        print(f"  Overall CVR:       {overall_cvr:.3%}")
        print(f"  Avg VBB signal:    {perf_df['vbb_margin_signal'].mean():.4f}")
        print(f"\n  By intent type:")
        type_summary = (
            perf_df
            .merge(groups_df[["id", "intent_type"]], left_on="keyword_group_id", right_on="id")
            .groupby("intent_type")
            .agg(
                groups=("keyword_group_id", "nunique"),
                spend=("spend", "sum"),
                clicks=("clicks", "sum"),
            )
            .sort_values("spend", ascending=False)
        )
        for it, row in type_summary.iterrows():
            pct = row["spend"] / total_spend * 100
            print(f"    {it:<15}  {row['groups']:>3} groups  "
                  f"${row['spend']:>12,.0f}  ({pct:.1f}%)  "
                  f"{row['clicks']:>9,} clicks")

        print(f"\n  Match type distribution (keyword groups):")
        mt_counts = groups_df["match_type"].value_counts()
        for mt, cnt in mt_counts.items():
            print(f"    {mt:<10}  {cnt:>3}  ({cnt / len(groups_df):.1%})")

        print(f"\n  Market segment distribution (keyword groups):")
        ms_counts = groups_df["market_segment"].value_counts()
        for ms, cnt in ms_counts.items():
            print(f"    {ms:<15}  {cnt:>3}  ({cnt / len(groups_df):.1%})")
        print()

    return perf_df


if __name__ == "__main__":
    seed()
