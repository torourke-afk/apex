"""Seed: LLM Visibility Scores (APE-84 / APE-18b)

Generates seed data for the ``llm_visibility`` table.

  6 platforms × 50 prompts × 12 weeks × 6 brands = 21,600 rows
  Brands: Fifth Third Bank (client, trending up) + 5 competitors (flat)
  Platforms: Google AI Overviews (highest) → Copilot (lowest)
  22 DMAs; each prompt is pinned to one DMA so geographic variety is present.

Idempotent: DELETE + INSERT on the table.

Run:
    python -m src.data.seeds.seed_llm_visibility
"""

from __future__ import annotations

import os
import sys
import uuid
from datetime import date, timedelta

import numpy as np
import pandas as pd

from src.data.seeds._dates import TWELVE_WEEK_START

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

_START = TWELVE_WEEK_START
WEEKS: list[date] = [_START + timedelta(weeks=i) for i in range(12)]

# Platforms ordered highest → lowest baseline mention rate
PLATFORMS = [
    "google_ai_overviews",
    "chatgpt",
    "perplexity",
    "gemini",
    "claude",
    "copilot",
]

# Baseline mention rates per platform (Google AI Overviews highest, Copilot lowest)
PLATFORM_MENTION_BASE = {
    "google_ai_overviews": 0.48,
    "chatgpt":             0.42,
    "perplexity":          0.38,
    "gemini":              0.33,
    "claude":              0.29,
    "copilot":             0.22,
}

PLATFORM_VOLATILITY = {
    "google_ai_overviews": 0.04,
    "chatgpt":             0.03,
    "perplexity":          0.03,
    "gemini":              0.04,
    "claude":              0.05,
    "copilot":             0.04,
}

# 50 prompts across 6 product categories
PROMPTS: list[tuple[str, str]] = [
    # checking (10)
    ("best checking account",                         "checking"),
    ("free checking account no minimum balance",      "checking"),
    ("bank with early direct deposit",                "checking"),
    ("checking account with overdraft protection",    "checking"),
    ("online checking account no fees",               "checking"),
    ("best bank for direct deposit bonus",            "checking"),
    ("joint checking account",                        "checking"),
    ("student checking account",                      "checking"),
    ("second chance checking account",                "checking"),
    ("bank with best mobile app",                     "checking"),
    # savings (8)
    ("best savings account interest rate",            "savings"),
    ("high yield savings account",                    "savings"),
    ("money market account rates",                    "savings"),
    ("best CD rates",                                 "savings"),
    ("how to set up automatic savings",               "savings"),
    ("best bank for high interest savings",           "savings"),
    ("bank account for bad credit",                   "savings"),
    ("what is APY",                                   "savings"),
    # mortgage (9)
    ("mortgage rates near me",                        "mortgage"),
    ("how to get a mortgage",                         "mortgage"),
    ("refinance mortgage rates",                      "mortgage"),
    ("best bank for first home buyers",               "mortgage"),
    ("how to negotiate mortgage rate",                "mortgage"),
    ("home equity loan rates",                        "mortgage"),
    ("home equity line of credit rates",              "mortgage"),
    ("FHA loan requirements",                         "mortgage"),
    ("mortgage pre-approval process",                 "mortgage"),
    # credit card (7)
    ("best credit card for cash back",                "credit_card"),
    ("best credit card for travel rewards",           "credit_card"),
    ("best bank for travel rewards",                  "credit_card"),
    ("how to build credit with a bank",               "credit_card"),
    ("best credit card no annual fee",                "credit_card"),
    ("credit card with 0 APR intro offer",            "credit_card"),
    ("best rewards credit card for groceries",        "credit_card"),
    # auto loan (8)
    ("auto loan rates",                               "auto_loan"),
    ("best auto loan rates",                          "auto_loan"),
    ("refinance auto loan",                           "auto_loan"),
    ("car loan calculator",                           "auto_loan"),
    ("used car loan rates",                           "auto_loan"),
    ("best bank for car loan",                        "auto_loan"),
    ("auto loan preapproval online",                  "auto_loan"),
    ("gap insurance for auto loan",                   "auto_loan"),
    # personal loan (8)
    ("personal loan rates",                           "personal_loan"),
    ("best personal loan for debt consolidation",     "personal_loan"),
    ("personal loan no credit check",                 "personal_loan"),
    ("best bank personal loan",                       "personal_loan"),
    ("how to get a small business loan",              "personal_loan"),
    ("personal loan same day funding",                "personal_loan"),
    ("home improvement loan rates",                   "personal_loan"),
    ("personal loan vs credit card",                  "personal_loan"),
]

assert len(PROMPTS) == 50, f"Expected 50 prompts, got {len(PROMPTS)}"

# 22 DMAs — Fifth Third footprint
DMAS: list[str] = [
    "Cincinnati",
    "Indianapolis",
    "Chicago",
    "Detroit",
    "Cleveland-Akron",
    "Columbus",
    "Nashville",
    "Charlotte",
    "Atlanta",
    "Tampa-St. Pete",
    "Miami-Fort Lauderdale",
    "Philadelphia",
    "Boston",
    "New York",
    "Minneapolis-Saint Paul",
    "Denver",
    "Dallas-Fort Worth",
    "Houston",
    "Phoenix",
    "Seattle-Tacoma",
    "San Francisco-Oakland",
    "Los Angeles",
]

assert len(DMAS) == 22, f"Expected 22 DMAs, got {len(DMAS)}"

# Assign each prompt a DMA (cycle through list so all 22 appear)
PROMPT_DMA: dict[str, str] = {
    prompt: DMAS[i % len(DMAS)]
    for i, (prompt, _) in enumerate(PROMPTS)
}

# 6 brands: Fifth Third (client) + 5 competitors
CLIENT_BRAND = "Fifth Third Bank"
COMPETITOR_BRANDS = [
    "National Bank A",
    "Regional Bank B",
    "Digital Bank C",
    "Credit Union D",
    "National Bank E",
]
ALL_BRANDS = [CLIENT_BRAND] + COMPETITOR_BRANDS

# Competitor baseline mention-rate offsets (relative to platform base)
COMPETITOR_OFFSETS = {
    "National Bank A":  +0.04,
    "Regional Bank B":  -0.05,
    "Digital Bank C":   +0.02,
    "Credit Union D":   -0.09,
    "National Bank E":  +0.01,
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clip(val: float, lo: float, hi: float) -> float:
    return float(np.clip(val, lo, hi))


# ---------------------------------------------------------------------------
# Row builders
# ---------------------------------------------------------------------------

def _build_rows() -> pd.DataFrame:
    """Build 21,600 rows (6 brands × 6 platforms × 50 prompts × 12 weeks)."""
    rows: list[dict] = []
    now = pd.Timestamp.now()

    for brand in ALL_BRANDS:
        is_client = brand == CLIENT_BRAND

        for week_idx, week in enumerate(WEEKS):
            # Client improves ~7 pp total over 12 weeks; competitors flat
            improvement = week_idx * 0.006 if is_client else 0.0

            for platform in PLATFORMS:
                base_mention = PLATFORM_MENTION_BASE[platform]
                vol = PLATFORM_VOLATILITY[platform]

                if not is_client:
                    base_mention += COMPETITOR_OFFSETS[brand]

                for prompt_text, prompt_category in PROMPTS:
                    market_dma = PROMPT_DMA[prompt_text]

                    noise_mention   = float(rng.normal(0, vol))
                    noise_position  = float(rng.normal(0, 0.18))
                    noise_sentiment = float(rng.normal(0, 0.04))
                    noise_citation  = float(rng.normal(0, vol * 0.5))

                    mention_rate   = _clip(base_mention + improvement + noise_mention, 0.15, 0.60)
                    avg_position   = _clip(3.2 - improvement * 2.5 + noise_position, 1.0, 5.0)
                    sentiment_score = _clip(0.50 + improvement * 0.35 + noise_sentiment, 0.20, 0.80)
                    citation_rate  = _clip(0.20 + improvement * 0.55 + noise_citation, 0.10, 0.40)

                    # Boolean mentioned: True when mention_rate > 0.25 + noise
                    mentioned = bool(mention_rate > 0.25)
                    position  = int(round(avg_position)) if mentioned else None

                    rows.append({
                        "id":               str(uuid.uuid4()),
                        "week_start":       str(week),
                        "platform":         platform,
                        "prompt_text":      prompt_text,
                        "prompt_category":  prompt_category,
                        "market_dma":       market_dma,
                        "brand":            brand,
                        "mentioned":        mentioned,
                        "position":         position,
                        "mention_rate":     round(mention_rate, 4),
                        "sentiment_score":  round(sentiment_score, 4),
                        "citation_rate":    round(citation_rate, 4),
                        "created_at":       now,
                        "updated_at":       now,
                    })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_llm_visibility_data() -> pd.DataFrame:
    """Return a DataFrame of 21,600 LLM visibility rows (unsaved)."""
    return _build_rows()


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS llm_visibility (
    id               VARCHAR PRIMARY KEY,
    week_start       DATE NOT NULL,
    platform         VARCHAR NOT NULL,
    prompt_text      VARCHAR NOT NULL,
    prompt_category  VARCHAR NOT NULL,
    market_dma       VARCHAR NOT NULL,
    brand            VARCHAR NOT NULL,
    mentioned        BOOLEAN NOT NULL,
    position         INTEGER,
    mention_rate     DECIMAL(6, 4) NOT NULL,
    sentiment_score  DECIMAL(6, 4) NOT NULL,
    citation_rate    DECIMAL(6, 4) NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP,
    UNIQUE (week_start, platform, prompt_text, brand)
)
"""

_COLS = [
    "id", "week_start", "platform", "prompt_text", "prompt_category",
    "market_dma", "brand", "mentioned", "position",
    "mention_rate", "sentiment_score", "citation_rate",
    "created_at", "updated_at",
]


def seed(verbose: bool = False) -> pd.DataFrame:
    """Generate and persist LLM visibility seed data to DuckDB."""
    from src.data.seeds.validation import validate_llm_visibility

    conn = get_connection()
    try:
        conn.execute(_DDL)
        df = generate_llm_visibility_data()
        validate_llm_visibility(df)

        conn.execute("DELETE FROM llm_visibility")
        conn.register("_df_llm", df)
        cols = ", ".join(_COLS)
        conn.execute(f"INSERT INTO llm_visibility ({cols}) SELECT {cols} FROM _df_llm")
        try:
            conn.unregister("_df_llm")
        except Exception:
            pass
        conn.commit()

        if verbose:
            print(f"[llm_visibility] {len(df):,} rows  "
                  f"({df['brand'].nunique()} brands × "
                  f"{df['platform'].nunique()} platforms × "
                  f"{df['prompt_text'].nunique()} prompts × "
                  f"{df['week_start'].nunique()} weeks)")
    finally:
        conn.close()

    return df


if __name__ == "__main__":
    import time
    t0 = time.perf_counter()
    result = seed(verbose=True)
    print(f"Done: {len(result):,} rows in {time.perf_counter() - t0:.2f}s")
