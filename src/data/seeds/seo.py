"""Seed: SEO (Search Engine Optimization) Data (APE-102)

Generates seed data for three tables:
  - seo_keyword_rankings  — 500 keywords across 7 product categories
  - seo_organic_traffic   — monthly sessions/conversions, 7 products × 12 months (84 rows)
  - seo_technical_metrics — Core Web Vitals + index coverage, 1 row per page group (7 rows)

Reconciliation rules:
  - Keyword rank distribution: ~30% page 1 (1–10), ~25% page 2 (11–20), ~45% page 3+ (21+)
  - Organic traffic shows 5–15% MoM growth with seasonal peaks per product
  - Organic conversions ≈ 25% of total funnel volume (documented; reconciled via funnel seed)
  - SEO spend = $750,000/year (5% of $15M total media budget; tracked in budgets table)
  - Core Web Vitals scores by product page group

Idempotent: DELETE + INSERT on each table.

Run:
    python -m src.data.seeds.seo
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date
from typing import List

import numpy as np
import pandas as pd

from src.data.seeds._dates import TWELVE_MONTH_STARTS

WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.data.init_db import get_connection  # noqa: E402

SEED = 102
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

ANNUAL_TOTAL = 15_000_000.0
SEO_BUDGET = ANNUAL_TOTAL * 0.05  # $750,000 (5% of total media budget)

PRODUCTS = [
    "checking", "savings", "mortgage", "auto_loan",
    "credit_card", "personal_loan", "wealth_mgmt",
]

# 12 months (computed from _dates anchor)
MONTHS: list[date] = [ts.date() for ts in TWELVE_MONTH_STARTS]

assert len(MONTHS) == 12

# ---------------------------------------------------------------------------
# Keyword templates per product
# ---------------------------------------------------------------------------

_KW_TEMPLATES: dict[str, list[str]] = {
    "checking": [
        "best checking account",
        "free checking account",
        "online checking account",
        "checking account no fees",
        "checking account near me",
        "open checking account online",
        "checking account comparison",
        "high yield checking account",
        "interest bearing checking account",
        "student checking account",
        "joint checking account",
        "business checking account",
        "second chance checking",
        "checking account with early direct deposit",
        "checking account bonus offer",
        "checking account overdraft protection",
    ],
    "savings": [
        "high yield savings account",
        "best savings account rates",
        "online savings account",
        "savings account rates today",
        "savings account comparison",
        "money market vs savings account",
        "how to open savings account",
        "savings account no minimum balance",
        "savings account for kids",
        "savings account calculator",
        "best savings account 2026",
        "savings account interest rate",
    ],
    "mortgage": [
        "mortgage rates today",
        "current mortgage rates",
        "30 year mortgage rates",
        "15 year mortgage rates",
        "home loan rates",
        "mortgage calculator",
        "first time home buyer mortgage",
        "FHA loan rates",
        "VA loan rates",
        "jumbo mortgage rates",
        "mortgage pre-approval",
        "refinance mortgage rates",
        "home equity loan rates",
        "HELOC rates",
        "mortgage lender near me",
        "mortgage rate comparison",
    ],
    "auto_loan": [
        "auto loan rates",
        "car loan rates today",
        "best auto loan rates",
        "auto loan calculator",
        "car loan comparison",
        "used car loan rates",
        "auto loan refinance",
        "car loan pre-approval",
        "auto loan near me",
        "best car loan 2026",
        "auto loan for bad credit",
        "motorcycle loan rates",
    ],
    "credit_card": [
        "best credit card",
        "cash back credit card",
        "rewards credit card",
        "credit card comparison",
        "no annual fee credit card",
        "travel credit card",
        "0 percent APR credit card",
        "credit card for fair credit",
        "credit card balance transfer",
        "secured credit card",
        "best credit card for groceries",
        "credit card sign up bonus",
        "low interest credit card",
        "credit card approval requirements",
    ],
    "personal_loan": [
        "personal loan rates",
        "best personal loan",
        "personal loan calculator",
        "online personal loan",
        "personal loan comparison",
        "debt consolidation loan",
        "personal loan for bad credit",
        "personal loan pre-qualification",
        "personal loan same day funding",
        "unsecured personal loan",
        "personal loan near me",
        "personal loan vs credit card",
    ],
    "wealth_mgmt": [
        "wealth management services",
        "financial advisor near me",
        "investment management services",
        "retirement planning advisor",
        "wealth management fees comparison",
        "private banking services",
        "portfolio management",
        "estate planning services",
        "tax planning financial advisor",
        "best wealth management firm",
        "high net worth banking",
        "trust and estate services",
        "fiduciary financial advisor",
    ],
}

# Geo and intent modifiers for keyword expansion
_GEO_MODS = ["", "near me", "online"]
_TIME_MODS = ["", "2026", "today"]

# ---------------------------------------------------------------------------
# Seasonal multipliers by calendar month (1–12) per product
# ---------------------------------------------------------------------------

_SEASONALITY: dict[str, dict[int, float]] = {
    "checking":      {1: 1.28, 2: 1.00, 3: 1.05, 4: 1.00, 5: 0.95, 6: 0.90, 7: 0.90, 8: 1.20, 9: 0.95, 10: 0.95, 11: 0.90, 12: 0.85},
    "savings":       {1: 1.18, 2: 1.05, 3: 1.00, 4: 0.95, 5: 0.90, 6: 0.90, 7: 0.90, 8: 0.92, 9: 1.10, 10: 1.02, 11: 0.95, 12: 0.95},
    "mortgage":      {1: 0.85, 2: 0.90, 3: 1.40, 4: 1.35, 5: 1.25, 6: 1.10, 7: 1.00, 8: 0.95, 9: 0.95, 10: 0.90, 11: 0.85, 12: 0.80},
    "auto_loan":     {1: 0.90, 2: 0.95, 3: 1.20, 4: 1.20, 5: 1.15, 6: 1.10, 7: 1.05, 8: 1.10, 9: 1.05, 10: 0.95, 11: 0.90, 12: 0.85},
    "credit_card":   {1: 0.90, 2: 0.85, 3: 0.90, 4: 0.95, 5: 0.95, 6: 0.90, 7: 0.90, 8: 0.90, 9: 1.00, 10: 1.05, 11: 1.20, 12: 1.25},
    "personal_loan": {1: 1.05, 2: 0.95, 3: 1.00, 4: 1.00, 5: 1.00, 6: 1.00, 7: 0.95, 8: 0.95, 9: 1.00, 10: 1.00, 11: 0.95, 12: 1.10},
    "wealth_mgmt":   {1: 1.20, 2: 1.00, 3: 1.05, 4: 1.00, 5: 0.95, 6: 0.90, 7: 0.90, 8: 0.90, 9: 1.02, 10: 1.05, 11: 1.05, 12: 1.00},
}

# Base monthly sessions per product (month 1, before growth + seasonal)
_BASE_SESSIONS: dict[str, int] = {
    "checking":      42_000,
    "savings":       30_000,
    "mortgage":      35_000,
    "auto_loan":     20_000,
    "credit_card":   52_000,
    "personal_loan": 23_000,
    "wealth_mgmt":   14_000,
}

# Organic conversion rates (session → application/lead)
_BASE_CVR: dict[str, float] = {
    "checking":      0.035,
    "savings":       0.028,
    "mortgage":      0.042,
    "auto_loan":     0.030,
    "credit_card":   0.025,
    "personal_loan": 0.032,
    "wealth_mgmt":   0.020,
}

# Average MoM growth rate for organic traffic
MOM_GROWTH_BASE = 0.085  # 8.5% average; noise applied per month

# ---------------------------------------------------------------------------
# Keyword per-product counts and page-tier distribution (must sum to 500)
# ---------------------------------------------------------------------------

#  Product        n    p1(30%)  p2(25%)  p3+(45%)
#  checking      72       22       18       32
#  savings       72       22       18       32
#  mortgage      72       22       18       32
#  auto_loan     72       22       18       32
#  credit_card   71       21       18       32
#  personal_loan 71       21       18       32
#  wealth_mgmt   70       21       17       32
#  ─────────────────────────────────────────────
#  TOTAL        500      151      125      224  → 500 ✓

_PRODUCT_KW_CONFIG: list[tuple[str, int, int, int, int]] = [
    # (product,  n,   p1,  p2,  p3)
    ("checking",      72, 22, 18, 32),
    ("savings",       72, 22, 18, 32),
    ("mortgage",      72, 22, 18, 32),
    ("auto_loan",     72, 22, 18, 32),
    ("credit_card",   71, 21, 18, 32),
    ("personal_loan", 71, 21, 18, 32),
    ("wealth_mgmt",   70, 21, 17, 32),
]

assert sum(row[1] for row in _PRODUCT_KW_CONFIG) == 500


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------

def _keyword_pool(product: str, n: int, seed_offset: int) -> list[str]:
    """Return n distinct keyword strings for a product via template expansion."""
    rng_local = np.random.default_rng(SEED + seed_offset)
    templates = _KW_TEMPLATES[product]
    combos: list[str] = []
    for t in templates:
        for g in _GEO_MODS:
            for tm in _TIME_MODS:
                kw = " ".join(filter(None, [t, g, tm])).strip()
                combos.append(kw)
    if len(combos) < n:
        # Extend with numeric variants (edge safety)
        combos += [f"{c} {i+1}" for i, c in enumerate(combos * 3)]
    idx = rng_local.choice(len(combos), size=n, replace=False)
    return [combos[int(i)] for i in idx]


def _build_keyword_rankings() -> pd.DataFrame:
    """Build 500 keyword ranking rows with realistic page-tier distribution."""
    rows: list[dict] = []
    now = pd.Timestamp.now()
    record_month = str(MONTHS[-1])

    rng_kw = np.random.default_rng(SEED + 10)

    # Rank-change pools: "trending positive overall" = mostly negative (rank # decreasing = improving)
    _p1_changes = [-3, -2, -2, -2, -1, -1, -1, 0, 0, 1]
    _p2_changes = [-5, -4, -3, -3, -2, -2, -1, -1, 0, 1, 2]
    _p3_changes = [-10, -8, -6, -5, -4, -3, -2, -2, -1, 0, 0, 2, 4, 5]

    for seed_off, (product, n_kw, n_p1, n_p2, n_p3) in enumerate(_PRODUCT_KW_CONFIG):
        keywords = _keyword_pool(product, n_kw, seed_offset=seed_off * 7)

        # Generate rank values per tier
        p1_ranks = rng_kw.integers(1, 11, size=n_p1).tolist()
        p2_ranks = rng_kw.integers(11, 21, size=n_p2).tolist()
        p3_ranks = rng_kw.integers(21, 101, size=n_p3).tolist()

        all_ranks  = p1_ranks + p2_ranks + p3_ranks
        page_nums  = [1] * n_p1 + [2] * n_p2 + [3] * n_p3

        # Search volume: higher rank = higher volume
        p1_vols = rng_kw.integers(8_000, 250_001, size=n_p1).tolist()
        p2_vols = rng_kw.integers(1_500, 40_001,  size=n_p2).tolist()
        p3_vols = rng_kw.integers(200,   8_001,   size=n_p3).tolist()
        all_vols = p1_vols + p2_vols + p3_vols

        for i in range(n_kw):
            current_rank = int(all_ranks[i])
            page_num     = int(page_nums[i])
            search_vol   = int(all_vols[i])

            # Rank change (negative = improved)
            if page_num == 1:
                change_pool = _p1_changes
            elif page_num == 2:
                change_pool = _p2_changes
            else:
                change_pool = _p3_changes

            rank_change    = int(rng_kw.choice(change_pool))
            prev_month_rank = max(1, current_rank - rank_change)

            # Difficulty: correlated with search volume
            difficulty = int(
                min(100, max(1, int(30 + (search_vol / 250_000) * 55 + float(rng_kw.normal(0, 6)))))
            )

            rows.append({
                "id":                   str(uuid.uuid4()),
                "keyword":              keywords[i].strip(),
                "product_category":     product,
                "current_rank":         current_rank,
                "page_num":             page_num,
                "prev_month_rank":      prev_month_rank,
                "rank_change":          rank_change,
                "monthly_search_volume": search_vol,
                "difficulty_score":     difficulty,
                "record_month":         record_month,
                "created_at":           now,
            })

    return pd.DataFrame(rows)


def _build_organic_traffic() -> pd.DataFrame:
    """Build 84 organic traffic rows (7 products × 12 months), with growth + seasonal patterns."""
    rows: list[dict] = []
    now = pd.Timestamp.now()

    rng_traffic = np.random.default_rng(SEED + 20)

    for product in PRODUCTS:
        base    = _BASE_SESSIONS[product]
        cvr     = _BASE_CVR[product]
        seasons = _SEASONALITY[product]

        prev_sessions: int | None = None

        for month_idx, month in enumerate(MONTHS):
            # Compound growth: base × (1 + growth)^t, with per-month noise
            growth_noise = float(rng_traffic.normal(0, 0.02))
            effective_growth = max(0.03, min(0.18, MOM_GROWTH_BASE + growth_noise))

            base_grown  = base * ((1 + effective_growth) ** month_idx)
            season_mult = seasons[month.month]
            noise_mult  = 1.0 + float(rng_traffic.normal(0, 0.025))

            sessions = int(base_grown * season_mult * noise_mult)
            sessions = max(1_000, sessions)

            # Organic CVR with small noise
            actual_cvr = max(0.005, cvr + float(rng_traffic.normal(0, 0.003)))
            organic_conversions = max(0, int(sessions * actual_cvr))
            conversion_rate = organic_conversions / sessions if sessions > 0 else 0.0

            if prev_sessions is not None and prev_sessions > 0:
                mom_growth = (sessions - prev_sessions) / prev_sessions
            else:
                mom_growth = 0.0

            rows.append({
                "id":                   str(uuid.uuid4()),
                "month":                str(month),
                "product_category":     product,
                "sessions":             sessions,
                "organic_conversions":  organic_conversions,
                "conversion_rate":      round(conversion_rate, 4),
                "mom_growth_pct":       round(mom_growth, 4),
                "created_at":           now,
            })

            prev_sessions = sessions

    return pd.DataFrame(rows)


def _build_technical_metrics() -> pd.DataFrame:
    """Build 7 Core Web Vitals rows, one per product page group."""
    rows: list[dict] = []
    now = pd.Timestamp.now()
    record_date = str(MONTHS[-1])

    rng_tech = np.random.default_rng(SEED + 30)

    # Per-product CWV baselines (realistic bank site values)
    _CWV: dict[str, dict[str, float]] = {
        "checking":      {"lcp": 2_100, "fid": 75,  "cls": 0.06},
        "savings":       {"lcp": 2_300, "fid": 80,  "cls": 0.07},
        "mortgage":      {"lcp": 2_850, "fid": 95,  "cls": 0.10},
        "auto_loan":     {"lcp": 2_400, "fid": 85,  "cls": 0.08},
        "credit_card":   {"lcp": 2_650, "fid": 90,  "cls": 0.09},
        "personal_loan": {"lcp": 2_200, "fid": 78,  "cls": 0.07},
        "wealth_mgmt":   {"lcp": 3_200, "fid": 115, "cls": 0.12},
    }

    # Pages submitted per product group
    _PAGES: dict[str, dict[str, float]] = {
        "checking":      {"submitted": 450, "coverage": 0.940},
        "savings":       {"submitted": 380, "coverage": 0.950},
        "mortgage":      {"submitted": 620, "coverage": 0.910},
        "auto_loan":     {"submitted": 340, "coverage": 0.930},
        "credit_card":   {"submitted": 520, "coverage": 0.920},
        "personal_loan": {"submitted": 290, "coverage": 0.940},
        "wealth_mgmt":   {"submitted": 280, "coverage": 0.890},
    }

    for product in PRODUCTS:
        cwv = _CWV[product]
        pc  = _PAGES[product]

        lcp = max(600.0, float(cwv["lcp"]) + float(rng_tech.normal(0, 80)))
        fid = max(15.0,  float(cwv["fid"]) + float(rng_tech.normal(0, 7)))
        cls = max(0.005, min(0.35, float(cwv["cls"]) + float(rng_tech.normal(0, 0.005))))

        pages_submitted   = int(pc["submitted"])
        index_coverage    = max(0.70, min(0.99, float(pc["coverage"]) + float(rng_tech.normal(0, 0.010))))
        pages_indexed     = int(pages_submitted * index_coverage)
        crawl_budget_used = max(0.50, min(0.99, 0.68 + float(rng_tech.uniform(0, 0.22))))

        rows.append({
            "id":                    str(uuid.uuid4()),
            "page_group":            product,
            "lcp_ms":                round(lcp, 1),
            "fid_ms":                round(fid, 1),
            "cls_score":             round(cls, 4),
            "pages_indexed":         pages_indexed,
            "pages_submitted":       pages_submitted,
            "index_coverage_pct":    round(index_coverage, 4),
            "crawl_budget_used_pct": round(crawl_budget_used, 4),
            "record_date":           record_date,
            "created_at":            now,
        })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_seo_data() -> dict[str, pd.DataFrame]:
    """Generate SEO seed DataFrames.

    Returns:
        dict with keys:
          "keyword_rankings"  — 500 keyword rows
          "organic_traffic"   — 84 rows (7 products × 12 months)
          "technical_seo"     — 7 rows (one per page group)

    Budget note:
        SEO spend = $750,000/year (5% of $15M total media budget).
        This is tracked in the budgets table under channel 'seo_aeo'.
    """
    return {
        "keyword_rankings": _build_keyword_rankings(),
        "organic_traffic":  _build_organic_traffic(),
        "technical_seo":    _build_technical_metrics(),
    }


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL_KEYWORD_RANKINGS = """
CREATE TABLE IF NOT EXISTS seo_keyword_rankings (
    id                    VARCHAR PRIMARY KEY,
    keyword               VARCHAR NOT NULL,
    product_category      VARCHAR NOT NULL,
    current_rank          INTEGER NOT NULL,
    page_num              INTEGER NOT NULL,
    prev_month_rank       INTEGER NOT NULL,
    rank_change           INTEGER NOT NULL,
    monthly_search_volume INTEGER NOT NULL,
    difficulty_score      INTEGER NOT NULL,
    record_month          DATE NOT NULL,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_DDL_ORGANIC_TRAFFIC = """
CREATE TABLE IF NOT EXISTS seo_organic_traffic (
    id                   VARCHAR PRIMARY KEY,
    month                DATE NOT NULL,
    product_category     VARCHAR NOT NULL,
    sessions             INTEGER NOT NULL,
    organic_conversions  INTEGER NOT NULL,
    conversion_rate      DECIMAL(8, 4) NOT NULL,
    mom_growth_pct       DECIMAL(8, 4) NOT NULL,
    created_at           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (month, product_category)
)
"""

_DDL_TECHNICAL_METRICS = """
CREATE TABLE IF NOT EXISTS seo_technical_metrics (
    id                    VARCHAR PRIMARY KEY,
    page_group            VARCHAR NOT NULL UNIQUE,
    lcp_ms                DECIMAL(10, 2) NOT NULL,
    fid_ms                DECIMAL(8, 2) NOT NULL,
    cls_score             DECIMAL(6, 4) NOT NULL,
    pages_indexed         INTEGER NOT NULL,
    pages_submitted       INTEGER NOT NULL,
    index_coverage_pct    DECIMAL(6, 4) NOT NULL,
    crawl_budget_used_pct DECIMAL(6, 4) NOT NULL,
    record_date           DATE NOT NULL,
    created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
"""

_KW_COLS = [
    "id", "keyword", "product_category", "current_rank", "page_num",
    "prev_month_rank", "rank_change", "monthly_search_volume",
    "difficulty_score", "record_month", "created_at",
]

_TRAFFIC_COLS = [
    "id", "month", "product_category", "sessions",
    "organic_conversions", "conversion_rate", "mom_growth_pct", "created_at",
]

_TECH_COLS = [
    "id", "page_group", "lcp_ms", "fid_ms", "cls_score",
    "pages_indexed", "pages_submitted", "index_coverage_pct",
    "crawl_budget_used_pct", "record_date", "created_at",
]


def _insert(conn, table: str, df: pd.DataFrame, columns: list[str]) -> None:
    conn.execute(f"DELETE FROM {table}")
    conn.register(f"_df_{table}", df)
    cols = ", ".join(columns)
    conn.execute(f"INSERT INTO {table} ({cols}) SELECT {cols} FROM _df_{table}")
    try:
        conn.unregister(f"_df_{table}")
    except Exception:
        pass


def seed(verbose: bool = False) -> dict[str, pd.DataFrame]:
    """Generate and persist SEO seed data to DuckDB.

    Returns dict of DataFrames for downstream use/validation.
    """
    from src.data.seeds.validation import (
        validate_seo_keyword_rankings,
        validate_seo_organic_traffic,
        validate_seo_technical_metrics,
    )

    conn = get_connection()

    try:
        conn.execute(_DDL_KEYWORD_RANKINGS)
        conn.execute(_DDL_ORGANIC_TRAFFIC)
        conn.execute(_DDL_TECHNICAL_METRICS)

        dfs = generate_seo_data()
        kw       = dfs["keyword_rankings"]
        traffic  = dfs["organic_traffic"]
        tech     = dfs["technical_seo"]

        validate_seo_keyword_rankings(kw)
        validate_seo_organic_traffic(traffic)
        validate_seo_technical_metrics(tech)

        _insert(conn, "seo_keyword_rankings",  kw,      _KW_COLS)
        _insert(conn, "seo_organic_traffic",   traffic, _TRAFFIC_COLS)
        _insert(conn, "seo_technical_metrics", tech,    _TECH_COLS)
        conn.commit()

        if verbose:
            total_conversions = int(traffic["organic_conversions"].sum())
            total_sessions    = int(traffic["sessions"].sum())
            print(f"[seo] seo_keyword_rankings:  {len(kw):,} rows")
            print(f"[seo] seo_organic_traffic:   {len(traffic):,} rows")
            print(f"[seo] seo_technical_metrics: {len(tech):,} rows")
            print(f"[seo] Annual sessions:       {total_sessions:,}")
            print(f"[seo] Annual conversions:    {total_conversions:,}  (~25% of funnel)")
            print(f"[seo] SEO budget allocation: ${SEO_BUDGET:,.0f} (tracked in budgets.seo_aeo)")

    finally:
        conn.close()

    return dfs


if __name__ == "__main__":
    import time
    t0 = time.perf_counter()
    result = seed(verbose=True)
    elapsed = time.perf_counter() - t0
    total = sum(len(v) for v in result.values())
    print(f"Done: {total:,} total rows in {elapsed:.2f}s")
