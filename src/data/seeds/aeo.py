"""Seed: AEO (AI Engine Optimization) Data (APE-101)

Generates seed data for two tables:
  - aeo_weekly_readings     — 6 platforms × 50 prompts × 12 weeks = 3,600 rows
  - aeo_competitor_scores   — 5 competitors × 6 platforms × 12 weeks = 360 rows

Client bank shows gradual improvement over 12 weeks.
Competitors hold flat with minor noise.
Platform variation: newer platforms (Claude, Meta AI) show more volatility.

Idempotent: DELETE + INSERT on each table.

Run:
    python -m src.data.seeds.aeo
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

# 12 weekly periods starting 2025-05-05 (Mondays)
_START = date(2025, 5, 5)
WEEKS: list[date] = [_START + timedelta(weeks=i) for i in range(12)]

PLATFORMS = ["ChatGPT", "Perplexity", "Gemini", "Claude", "Copilot", "Meta AI"]

# Newer platforms have higher volatility multiplier
PLATFORM_VOLATILITY = {
    "ChatGPT":   0.03,
    "Perplexity": 0.03,
    "Gemini":    0.04,
    "Claude":    0.06,
    "Copilot":   0.04,
    "Meta AI":   0.06,
}

# ChatGPT/Perplexity skew higher on mention rate
PLATFORM_MENTION_BASE = {
    "ChatGPT":    0.42,
    "Perplexity": 0.40,
    "Gemini":     0.32,
    "Claude":     0.28,
    "Copilot":    0.30,
    "Meta AI":    0.26,
}

BANKING_PROMPTS: list[str] = [
    "best checking account",
    "mortgage rates near me",
    "best savings account interest rate",
    "how to open a bank account online",
    "best bank for small business",
    "compare checking accounts",
    "best CD rates",
    "bank with no fees",
    "home equity loan rates",
    "best online bank",
    "auto loan rates",
    "personal loan rates",
    "best credit card for cash back",
    "how to get a mortgage",
    "refinance mortgage rates",
    "high yield savings account",
    "money market account rates",
    "best bank for millennials",
    "bank with highest interest rate",
    "online checking account no minimum balance",
    "best bank for first home buyers",
    "student checking account",
    "joint checking account",
    "best bank near me",
    "bank overdraft protection",
    "best bank for direct deposit bonus",
    "how to build credit with a bank",
    "bank with best mobile app",
    "free checking account",
    "what is APY",
    "best bank for seniors",
    "second chance checking account",
    "how to dispute a bank charge",
    "bank wire transfer fees",
    "best bank for travel rewards",
    "how to switch banks",
    "best bank for teenagers",
    "how to set up automatic savings",
    "bank with early direct deposit",
    "best bank for self employed",
    "how to get a small business loan",
    "bank with best ATM network",
    "best bank for international transfers",
    "how does compound interest work",
    "best bank for retirement savings",
    "bank account for bad credit",
    "digital banking vs traditional banking",
    "best bank for home improvement loan",
    "bank with no foreign transaction fees",
    "how to negotiate mortgage rate",
]

COMPETITORS = [
    "National Bank A",
    "Regional Bank B",
    "Digital Bank C",
    "Credit Union D",
    "National Bank E",
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _clip(val: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, val))


def _build_weekly_readings() -> pd.DataFrame:
    """Build 3,600 rows: 6 platforms × 50 prompts × 12 weeks."""
    rows = []
    now = pd.Timestamp.now()

    for week_idx, week in enumerate(WEEKS):
        # Client bank improves +5–10 pp total over 12 weeks → ~0.5–0.8 pp/week
        improvement = week_idx * 0.007  # ~8.4 pp over 12 weeks

        for platform in PLATFORMS:
            vol = PLATFORM_VOLATILITY[platform]
            mention_base = PLATFORM_MENTION_BASE[platform]

            for prompt in BANKING_PROMPTS:
                # Deterministic noise from rng (seeded)
                noise_mention = float(rng.normal(0, vol))
                noise_position = float(rng.normal(0, 0.15))
                noise_sov = float(rng.normal(0, vol * 0.6))
                noise_sentiment = float(rng.normal(0, 0.03))
                noise_citation = float(rng.normal(0, vol * 0.5))

                mention_rate = _clip(mention_base + improvement + noise_mention, 0.15, 0.60)
                avg_position = _clip(3.0 - improvement * 2 + noise_position, 1.0, 5.0)
                share_of_voice = _clip(0.14 + improvement * 0.8 + noise_sov, 0.05, 0.25)
                sentiment_score = _clip(0.52 + improvement * 0.3 + noise_sentiment, 0.20, 0.80)
                citation_rate = _clip(0.22 + improvement * 0.6 + noise_citation, 0.10, 0.40)

                rows.append({
                    "id": str(uuid.uuid4()),
                    "week_ending": str(week),
                    "platform": platform,
                    "prompt": prompt,
                    "mention_rate": round(mention_rate, 4),
                    "avg_position": round(avg_position, 2),
                    "share_of_voice": round(share_of_voice, 4),
                    "sentiment_score": round(sentiment_score, 4),
                    "citation_rate": round(citation_rate, 4),
                    "created_at": now,
                    "updated_at": now,
                })

    return pd.DataFrame(rows)


def _build_competitor_scores() -> pd.DataFrame:
    """Build 360 rows: 5 competitors × 6 platforms × 12 weeks (flat with noise)."""
    rows = []
    now = pd.Timestamp.now()

    # Baseline mention rates per competitor (stable, varied)
    competitor_baselines = {
        "National Bank A":  {"mention": 0.38, "position": 2.1, "sov": 0.18, "sentiment": 0.55, "citation": 0.26},
        "Regional Bank B":  {"mention": 0.29, "position": 2.8, "sov": 0.12, "sentiment": 0.48, "citation": 0.19},
        "Digital Bank C":   {"mention": 0.35, "position": 2.3, "sov": 0.16, "sentiment": 0.62, "citation": 0.28},
        "Credit Union D":   {"mention": 0.24, "position": 3.2, "sov": 0.09, "sentiment": 0.58, "citation": 0.17},
        "National Bank E":  {"mention": 0.33, "position": 2.5, "sov": 0.14, "sentiment": 0.51, "citation": 0.23},
    }

    for week_idx, week in enumerate(WEEKS):
        for competitor, base in competitor_baselines.items():
            for platform in PLATFORMS:
                vol = PLATFORM_VOLATILITY[platform] * 0.8  # slightly less volatile for competitors

                mention_rate = _clip(base["mention"] + float(rng.normal(0, vol)), 0.15, 0.60)
                avg_position = _clip(base["position"] + float(rng.normal(0, 0.12)), 1.0, 5.0)
                share_of_voice = _clip(base["sov"] + float(rng.normal(0, vol * 0.5)), 0.05, 0.25)
                sentiment_score = _clip(base["sentiment"] + float(rng.normal(0, 0.025)), 0.20, 0.80)
                citation_rate = _clip(base["citation"] + float(rng.normal(0, vol * 0.4)), 0.10, 0.40)

                rows.append({
                    "id": str(uuid.uuid4()),
                    "week_ending": str(week),
                    "competitor_name": competitor,
                    "platform": platform,
                    "mention_rate": round(mention_rate, 4),
                    "avg_position": round(avg_position, 2),
                    "share_of_voice": round(share_of_voice, 4),
                    "sentiment_score": round(sentiment_score, 4),
                    "citation_rate": round(citation_rate, 4),
                    "created_at": now,
                    "updated_at": now,
                })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_aeo_data() -> dict[str, pd.DataFrame]:
    """Generate AEO seed DataFrames.

    Returns:
        dict with keys:
          "weekly_readings"     — 3,600 rows (6 platforms × 50 prompts × 12 weeks)
          "competitor_comparison" — 360 rows (5 competitors × 6 platforms × 12 weeks)
    """
    return {
        "weekly_readings": _build_weekly_readings(),
        "competitor_comparison": _build_competitor_scores(),
    }


_DDL_WEEKLY_READINGS = """
CREATE TABLE IF NOT EXISTS aeo_weekly_readings (
    id              VARCHAR PRIMARY KEY,
    week_ending     DATE NOT NULL,
    platform        VARCHAR NOT NULL,
    prompt          VARCHAR NOT NULL,
    mention_rate    DECIMAL(6, 4) NOT NULL,
    avg_position    DECIMAL(5, 2) NOT NULL,
    share_of_voice  DECIMAL(6, 4) NOT NULL,
    sentiment_score DECIMAL(6, 4) NOT NULL,
    citation_rate   DECIMAL(6, 4) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP,
    UNIQUE (week_ending, platform, prompt)
)
"""

_DDL_COMPETITOR_SCORES = """
CREATE TABLE IF NOT EXISTS aeo_competitor_scores (
    id              VARCHAR PRIMARY KEY,
    week_ending     DATE NOT NULL,
    competitor_name VARCHAR NOT NULL,
    platform        VARCHAR NOT NULL,
    mention_rate    DECIMAL(6, 4) NOT NULL,
    avg_position    DECIMAL(5, 2) NOT NULL,
    share_of_voice  DECIMAL(6, 4) NOT NULL,
    sentiment_score DECIMAL(6, 4) NOT NULL,
    citation_rate   DECIMAL(6, 4) NOT NULL,
    created_at      TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at      TIMESTAMP,
    UNIQUE (week_ending, competitor_name, platform)
)
"""


_WEEKLY_COLS = [
    "id", "week_ending", "platform", "prompt",
    "mention_rate", "avg_position", "share_of_voice",
    "sentiment_score", "citation_rate", "created_at", "updated_at",
]

_COMPETITOR_COLS = [
    "id", "week_ending", "competitor_name", "platform",
    "mention_rate", "avg_position", "share_of_voice",
    "sentiment_score", "citation_rate", "created_at", "updated_at",
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
    """Generate and persist AEO seed data to DuckDB.

    Returns dict of DataFrames for downstream use/validation.
    """
    from src.data.seeds.validation import validate_aeo_weekly, validate_aeo_competitors

    conn = get_connection()

    try:
        conn.execute(_DDL_WEEKLY_READINGS)
        conn.execute(_DDL_COMPETITOR_SCORES)

        dfs = generate_aeo_data()
        weekly = dfs["weekly_readings"]
        competitors = dfs["competitor_comparison"]

        validate_aeo_weekly(weekly)
        validate_aeo_competitors(competitors)

        _insert(conn, "aeo_weekly_readings", weekly, _WEEKLY_COLS)
        _insert(conn, "aeo_competitor_scores", competitors, _COMPETITOR_COLS)
        conn.commit()

        if verbose:
            print(f"[aeo] aeo_weekly_readings:   {len(weekly):,} rows")
            print(f"[aeo] aeo_competitor_scores: {len(competitors):,} rows")

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
