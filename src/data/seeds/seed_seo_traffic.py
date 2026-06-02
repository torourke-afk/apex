"""Seed: SEO Traffic (APE-84 / APE-18b)

Generates seed data for the ``seo_traffic`` table.

  6 categories × 12 weeks = 72 rows
  Categories: checking, savings, mortgage, credit_card, auto_loan, personal_loan
  Sessions: 5k–50k/week per category
  Organic accounts: 50–500/week per category
  Bounce rate: 30–65%
  Slight week-over-week upward trend in sessions and accounts.

Idempotent: DELETE + INSERT on the table.

Run:
    python -m src.data.seeds.seed_seo_traffic
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

CATEGORIES = [
    "checking",
    "savings",
    "mortgage",
    "credit_card",
    "auto_loan",
    "personal_loan",
]

# Baseline weekly sessions, accounts, and bounce rate per category
# (sessions, accounts, bounce_rate_base)
CATEGORY_BASELINES: dict[str, dict] = {
    "checking":      {"sessions": 38_000, "accounts": 380, "bounce": 0.42},
    "savings":       {"sessions": 28_000, "accounts": 290, "bounce": 0.45},
    "mortgage":      {"sessions": 22_000, "accounts": 180, "bounce": 0.38},
    "credit_card":   {"sessions": 18_000, "accounts": 150, "bounce": 0.50},
    "auto_loan":     {"sessions": 14_000, "accounts": 120, "bounce": 0.48},
    "personal_loan": {"sessions": 10_000, "accounts":  90, "bounce": 0.55},
}


# ---------------------------------------------------------------------------
# Row builder
# ---------------------------------------------------------------------------

def _build_rows() -> pd.DataFrame:
    rows: list[dict] = []
    now = pd.Timestamp.now()

    for category in CATEGORIES:
        base = CATEGORY_BASELINES[category]

        for week_idx, week in enumerate(WEEKS):
            # Gradual organic growth: ~1.5% uplift per week
            growth = 1.0 + week_idx * 0.015

            # Weekly noise
            session_noise   = float(rng.normal(0, base["sessions"] * 0.06))
            account_noise   = float(rng.normal(0, base["accounts"] * 0.07))
            bounce_noise    = float(rng.normal(0, 0.025))

            organic_sessions = int(np.clip(
                round(base["sessions"] * growth + session_noise),
                5_000, 50_000,
            ))
            organic_accounts = int(np.clip(
                round(base["accounts"] * growth + account_noise),
                50, 500,
            ))
            bounce_rate = float(np.clip(
                base["bounce"] + bounce_noise,
                0.30, 0.65,
            ))

            rows.append({
                "id":               str(uuid.uuid4()),
                "week_start":       str(week),
                "product_category": category,
                "organic_sessions": organic_sessions,
                "organic_accounts": organic_accounts,
                "bounce_rate":      round(bounce_rate, 4),
                "created_at":       now,
                "updated_at":       now,
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def generate_seo_traffic_data() -> pd.DataFrame:
    """Return DataFrame of 72 SEO traffic rows (unsaved)."""
    return _build_rows()


# ---------------------------------------------------------------------------
# DDL
# ---------------------------------------------------------------------------

_DDL = """
CREATE TABLE IF NOT EXISTS seo_traffic (
    id               VARCHAR PRIMARY KEY,
    week_start       DATE NOT NULL,
    product_category VARCHAR NOT NULL,
    organic_sessions INTEGER NOT NULL,
    organic_accounts INTEGER NOT NULL,
    bounce_rate      DECIMAL(6, 4) NOT NULL,
    created_at       TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at       TIMESTAMP,
    UNIQUE (week_start, product_category)
)
"""

_COLS = [
    "id", "week_start", "product_category",
    "organic_sessions", "organic_accounts", "bounce_rate",
    "created_at", "updated_at",
]


def seed(verbose: bool = False) -> pd.DataFrame:
    """Generate and persist SEO traffic seed data to DuckDB."""
    from src.data.seeds.validation import validate_seo_traffic

    conn = get_connection()
    try:
        conn.execute(_DDL)
        df = generate_seo_traffic_data()
        validate_seo_traffic(df)

        conn.execute("DELETE FROM seo_traffic")
        conn.register("_df_seo_traffic", df)
        cols = ", ".join(_COLS)
        conn.execute(f"INSERT INTO seo_traffic ({cols}) SELECT {cols} FROM _df_seo_traffic")
        try:
            conn.unregister("_df_seo_traffic")
        except Exception:
            pass
        conn.commit()

        if verbose:
            print(f"[seo_traffic] {len(df):,} rows  "
                  f"({df['product_category'].nunique()} categories × "
                  f"{df['week_start'].nunique()} weeks)")
            for cat in CATEGORIES:
                cat_df = df[df["product_category"] == cat]
                print(f"  {cat:<14}  sessions={cat_df['organic_sessions'].mean():,.0f} avg  "
                      f"bounce={cat_df['bounce_rate'].mean():.1%}")
    finally:
        conn.close()

    return df


if __name__ == "__main__":
    import time
    t0 = time.perf_counter()
    result = seed(verbose=True)
    print(f"Done: {len(result):,} rows in {time.perf_counter() - t0:.2f}s")
