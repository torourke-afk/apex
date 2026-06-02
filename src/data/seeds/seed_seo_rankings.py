"""Seed: SEO Keyword Rankings (APE-84 / APE-18b)

Generates seed data for the ``seo_rankings`` table.

  200 keywords × 12 weeks = 2,400 rows
  Categories: checking, savings, mortgage, credit_card, auto_loan, personal_loan
  Rank distribution: ~30% page 1, ~25% page 2, ~45% page 3+
  Fifth Third Bank improves 2–3 positions over the 12-week window.

Idempotent: DELETE + INSERT on the table.

Run:
    python -m src.data.seeds.seed_seo_rankings
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, timedelta

import numpy as np
import pandas as pd

WORKSPACE = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)
if WORKSPACE not in sys.path:
    sys.path.insert(0, WORKSPACE)

from src.data.init_db import get_connection  # noqa: E402

SEED = 42
rng = np.random.default_rng(SEED)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_START = date(2025, 5, 5)
WEEKS: list[date] = [_START + timedelta(weeks=i) for i in range(12)]

# 200 keywords, ~33-34 per category
# Format: (keyword, search_volume_base)
_KEYWORDS_BY_CAT: dict[str, list[tuple[str, int]]] = {
    "checking": [
        ("best checking account",                     22_000),
        ("free checking account",                     18_500),
        ("online checking account",                   15_000),
        ("checking account no fees",                  12_000),
        ("checking account with high interest",        8_500),
        ("best bank for checking account",            10_000),
        ("joint checking account",                     6_800),
        ("student checking account",                   9_200),
        ("second chance checking account",             5_500),
        ("checking account with overdraft protection", 7_200),
        ("bank account no minimum balance",            8_800),
        ("free business checking account",             6_200),
        ("bank with early direct deposit",            11_000),
        ("best bank mobile app",                      14_500),
        ("checking account instant approval",          5_800),
        ("checkings accounts near me",                 4_500),
        ("online bank account open instantly",         9_000),
        ("bank account bonus offer",                   7_600),
        ("best national bank checking",                6_100),
        ("direct deposit bonus bank",                  5_300),
        ("checking account for bad credit",            4_800),
        ("bank with no overdraft fees",                8_200),
        ("digital bank checking account",              7_400),
        ("checking account interest rate",             6_600),
        ("best bank for millennials",                  5_100),
        ("checking account switch bonus",              4_200),
        ("business checking account fees",             5_900),
        ("teen checking account",                      6_400),
        ("bank with cashback checking",                4_700),
        ("premium checking account benefits",          3_900),
        ("virtual checking account",                   5_200),
        ("checking account fdic insured",              3_600),
        ("how to open a bank account online",         13_000),
        ("best bank no monthly fees",                  8_400),
    ],
    "savings": [
        ("best savings account interest rate",        19_000),
        ("high yield savings account",                24_000),
        ("savings account rates",                     16_500),
        ("best online savings account",               14_000),
        ("money market account",                      11_500),
        ("CD rates best",                             10_200),
        ("best CD rates today",                        9_500),
        ("savings account vs money market",            7_800),
        ("high interest savings account",             12_000),
        ("savings account APY comparison",             8_200),
        ("best savings account for kids",              6_400),
        ("online savings account no minimum",          7_100),
        ("how to grow savings fast",                   5_900),
        ("savings account interest calculator",        6_800),
        ("best bank for savings",                     10_800),
        ("emergency fund savings account",             7_500),
        ("1 year CD rates",                            6_200),
        ("18 month CD rates",                          4_800),
        ("5 year CD rates",                            5_500),
        ("savings account federal insurance",          3_900),
        ("automatic savings account",                  5_200),
        ("round up savings feature",                   4_600),
        ("savings account for minors",                 4_100),
        ("joint savings account rates",                3_800),
        ("best savings account bonus",                 5_000),
        ("what is APY savings",                        8_900),
        ("savings account compound interest",          6_100),
        ("best savings account no fees",               7_300),
        ("mobile savings app bank",                    5_700),
        ("savings account open online same day",       5_100),
        ("savings ladder strategy",                    3_400),
        ("best bank for retirement savings",           8_100),
        ("savings account tax implications",           4_300),
        ("best savings account for college fund",      5_800),
    ],
    "mortgage": [
        ("mortgage rates today",                      45_000),
        ("current mortgage rates",                    38_000),
        ("30 year fixed mortgage rate",               32_000),
        ("15 year mortgage rate",                     18_000),
        ("mortgage rate calculator",                  28_000),
        ("best mortgage rates",                       22_000),
        ("FHA loan rates",                            16_000),
        ("VA loan rates",                             14_500),
        ("refinance mortgage rates",                  20_000),
        ("home equity loan rates",                    12_500),
        ("HELOC rates",                               11_000),
        ("jumbo mortgage rates",                       8_200),
        ("ARM mortgage rates",                         7_600),
        ("mortgage pre-approval",                     15_000),
        ("how to get a mortgage",                     13_000),
        ("first-time homebuyer loan",                 11_500),
        ("mortgage points explained",                  6_800),
        ("closing costs calculator",                   9_200),
        ("down payment assistance",                    8_900),
        ("mortgage lender comparison",                 7_400),
        ("best bank for mortgage",                    10_500),
        ("online mortgage application",                8_100),
        ("mortgage approval process",                  7_200),
        ("investment property mortgage rate",          5_800),
        ("construction loan rates",                    4_900),
        ("home improvement loan",                      8_700),
        ("bridge loan real estate",                    4_200),
        ("reverse mortgage rates",                     6_100),
        ("mortgage forbearance options",               5_300),
        ("how to negotiate mortgage rate",             6_700),
        ("mortgage broker vs bank",                    7_800),
        ("PMI removal mortgage",                       5_600),
        ("mortgage rate lock period",                  4_700),
    ],
    "credit_card": [
        ("best cash back credit card",                30_000),
        ("best travel rewards credit card",           26_000),
        ("best no annual fee credit card",            22_000),
        ("0 APR credit card",                         19_500),
        ("best credit card for groceries",            14_000),
        ("balance transfer credit card",              16_000),
        ("secured credit card",                       12_000),
        ("credit card for bad credit",                10_500),
        ("best credit card signup bonus",             18_000),
        ("credit card with lounge access",             8_200),
        ("business credit card rewards",               9_800),
        ("credit card foreign transaction fee",        7_600),
        ("best credit card for gas",                  11_000),
        ("credit card interest rate comparison",       9_200),
        ("how to build credit credit card",           13_000),
        ("student credit card",                       10_800),
        ("credit card points vs cash back",            7_400),
        ("visa vs mastercard credit card",             6_800),
        ("best hotel rewards credit card",             9_100),
        ("credit card fraud protection",               8_500),
        ("credit card with cell phone insurance",      5_900),
        ("no deposit secured card",                    6_200),
        ("credit union credit card rates",             7_100),
        ("best flat rate cash back card",              8_800),
        ("credit card annual fee worth it",            6_500),
        ("how to lower credit card interest",          7_900),
        ("2 percent cash back credit card",           11_500),
        ("credit card for fair credit",                6_800),
        ("rotating category credit card",              5_400),
        ("metal credit card",                          4_900),
        ("credit card purchase protection",            5_700),
        ("best credit card for dining",                8_300),
        ("apply credit card online instant approval", 12_000),
    ],
    "auto_loan": [
        ("auto loan rates",                           24_000),
        ("best auto loan rates",                      18_500),
        ("car loan calculator",                       32_000),
        ("refinance auto loan",                       15_000),
        ("used car loan rates",                       12_000),
        ("auto loan preapproval",                     10_500),
        ("how to get a car loan",                      8_800),
        ("auto loan interest rate",                   11_000),
        ("new car loan rates",                        14_500),
        ("car loan with bad credit",                   9_200),
        ("credit union auto loan rate",               10_200),
        ("bank vs dealer auto loan",                   7_600),
        ("auto loan for first time buyer",             8_100),
        ("auto loan payoff calculator",                9_500),
        ("72 month auto loan rate",                    6_800),
        ("auto loan 84 months",                        5_900),
        ("low income car loan",                        6_200),
        ("auto loan cosigner",                         5_400),
        ("gap insurance auto loan",                    7_200),
        ("auto loan down payment amount",              6_600),
        ("refinance auto loan lower payment",          8_400),
        ("underwater on car loan options",             5_100),
        ("auto loan approval odds",                    6_900),
        ("classic car loan rates",                     4_800),
        ("electric vehicle loan rates",                7_800),
        ("auto loan 1.9 APR",                          5_600),
        ("best bank for car loan",                     9_800),
        ("auto loan transfer to another bank",         4_200),
        ("is my car loan rate good",                   6_100),
        ("auto loan deferred payment",                 4_900),
        ("military auto loan rates",                   5_300),
        ("auto loan comparison tool",                  6_700),
        ("paying off auto loan early",                 7_400),
    ],
    "personal_loan": [
        ("personal loan rates",                       21_000),
        ("best personal loan",                        18_000),
        ("personal loan calculator",                  24_000),
        ("debt consolidation loan",                   19_500),
        ("personal loan for bad credit",              14_000),
        ("personal loan same day funding",            10_500),
        ("personal loan no credit check",              8_800),
        ("how to get a personal loan",                12_000),
        ("personal loan comparison",                  11_000),
        ("secured personal loan",                      7_600),
        ("unsecured personal loan",                    8_200),
        ("credit union personal loan rates",           9_500),
        ("personal loan vs credit card",               9_200),
        ("personal loan approval odds",                7_400),
        ("personal loan for home improvement",         8_900),
        ("emergency personal loan",                    6_800),
        ("small personal loan 1000",                   6_400),
        ("personal loan 5000",                         7_100),
        ("personal loan 10000",                        8_500),
        ("low interest personal loan",                10_200),
        ("personal loan online apply",                11_500),
        ("bank vs online lender personal loan",        6_200),
        ("personal loan for vacation",                 5_900),
        ("medical loan",                               7_800),
        ("personal loan interest rate calculator",     8_100),
        ("personal loan payoff calculator",            6_600),
        ("personal loan origination fee",              5_500),
        ("best bank personal loan",                    9_800),
        ("personal loan for wedding",                  5_200),
        ("personal loan deferred payments",            4_900),
        ("how long to get personal loan",              6_300),
        ("personal loan for car repair",               5_700),
        ("personal loan credit score requirements",    7_900),
    ],
}

# Flatten to list of (keyword, category, search_volume_base)
ALL_KEYWORDS: list[tuple[str, str, int]] = [
    (kw, cat, vol)
    for cat, kws in _KEYWORDS_BY_CAT.items()
    for kw, vol in kws
]

assert len(ALL_KEYWORDS) == 200, f"Expected 200 keywords, got {len(ALL_KEYWORDS)}"

# Rank distribution targets: ~30% page 1, ~25% page 2, ~45% page 3+
# Page 1 = positions 1-10, page 2 = 11-20, page 3+ = 21+
# Baseline: skewed toward page 3+; client improves over time
_PAGE_WEIGHTS = [0.30, 0.25, 0.45]  # p1, p2, p3+


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _rank_to_page(pos: int) -> int:
    if pos <= 10:
        return 1
    elif pos <= 20:
        return 2
    return 3


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def _build_rows() -> pd.DataFrame:
    rows: list[dict] = []
    now = pd.Timestamp.now()

    for week_idx, week in enumerate(WEEKS):
        # Client trends up: reduce rank by ~0.25/week on average
        rank_improvement = week_idx * 0.25

        for keyword, category, vol_base in ALL_KEYWORDS:
            noise_rank = float(rng.normal(0, 3.5))
            noise_vol  = int(rng.integers(-vol_base // 10, vol_base // 10))

            # Starting position sampled from page-weighted distribution
            page_draw = rng.choice([1, 2, 3], p=_PAGE_WEIGHTS)
            if page_draw == 1:
                start_pos = int(rng.integers(1, 11))
            elif page_draw == 2:
                start_pos = int(rng.integers(11, 21))
            else:
                start_pos = int(rng.integers(21, 61))

            pos = int(np.clip(round(start_pos - rank_improvement + noise_rank), 1, 100))
            page = _rank_to_page(pos)
            search_volume = max(0, vol_base + noise_vol)

            # week-over-week rank change (negative = improved, positive = dropped)
            if week_idx == 0:
                rank_change = 0
            else:
                rank_change = int(round(float(rng.normal(-0.5, 2.5))))

            rows.append({
                "id":               str(uuid.uuid4()),
                "week_start":       str(week),
                "keyword":          keyword,
                "product_category": category,
                "rank_position":    pos,
                "rank_page":        page,
                "search_volume":    search_volume,
                "rank_change":      rank_change,
                "created_at":       now,
                "updated_at":       now,
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_seo_rankings_data() -> pd.DataFrame:
    """Return DataFrame of 2,400 SEO keyword ranking rows (unsaved)."""
    return _build_rows()


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS seo_rankings (
    id               VARCHAR PRIMARY KEY,
    week_start       DATE NOT NULL,
    keyword          VARCHAR NOT NULL,
    product_category VARCHAR NOT NULL,
    rank_position    INTEGER NOT NULL,
    rank_page        INTEGER NOT NULL,
    search_volume    INTEGER NOT NULL,
    rank_change      INTEGER NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP,
    UNIQUE (week_start, keyword)
)
"""

_COLS = [
    "id", "week_start", "keyword", "product_category",
    "rank_position", "rank_page", "search_volume", "rank_change",
    "created_at", "updated_at",
]


def seed(verbose: bool = False) -> pd.DataFrame:
    """Generate and persist SEO rankings seed data to DuckDB."""
    from src.data.seeds.validation import validate_seo_rankings

    conn = get_connection()
    try:
        conn.execute(_DDL)
        df = generate_seo_rankings_data()
        validate_seo_rankings(df)

        conn.execute("DELETE FROM seo_rankings")
        conn.register("_df_seo_rank", df)
        cols = ", ".join(_COLS)
        conn.execute(f"INSERT INTO seo_rankings ({cols}) SELECT {cols} FROM _df_seo_rank")
        try:
            conn.unregister("_df_seo_rank")
        except Exception:
            pass
        conn.commit()

        if verbose:
            p1 = (df["rank_page"] == 1).mean()
            p2 = (df["rank_page"] == 2).mean()
            p3 = (df["rank_page"] >= 3).mean()
            print(f"[seo_rankings] {len(df):,} rows  "
                  f"page1={p1:.0%} page2={p2:.0%} page3+={p3:.0%}")
    finally:
        conn.close()

    return df


if __name__ == "__main__":
    import time
    t0 = time.perf_counter()
    result = seed(verbose=True)
    print(f"Done: {len(result):,} rows in {time.perf_counter() - t0:.2f}s")
