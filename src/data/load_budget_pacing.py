"""
load_budget_pacing.py
---------------------
Generates budget pacing data for the Spend Allocation page.

Returns per-category DataFrames with:
  - Daily planned vs. actual cumulative spend
  - Projected landing + 80% confidence interval
  - Pacing flags (>5% over → "over", >5% under → "under", else "on_track")

All data is synthetic (seeded for reproducibility). Replace the
``_generate_raw_actuals`` function with a real DB query when available.
"""

from __future__ import annotations

import datetime
import random

import numpy as np
import pandas as pd
import streamlit as st

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CATEGORIES: list[str] = [
    "Paid Search",
    "Paid Social",
    "Content & SEO",
    "Display & Programmatic",
    "Events & Sponsorships",
    "Email & CRM",
]

# Annual budget per category (USD)
_ANNUAL_BUDGETS: dict[str, float] = {
    "Paid Search": 1_200_000,
    "Paid Social": 850_000,
    "Content & SEO": 420_000,
    "Display & Programmatic": 600_000,
    "Events & Sponsorships": 380_000,
    "Email & CRM": 150_000,
}

# Simulated pacing scenarios per category (over / under / on_track)
_PACING_SCENARIOS: dict[str, str] = {
    "Paid Search": "on_track",
    "Paid Social": "over",
    "Content & SEO": "under",
    "Display & Programmatic": "on_track",
    "Events & Sponsorships": "under",
    "Email & CRM": "over",
}

_OVER_FACTOR = 1.10   # 10% over budget pace
_UNDER_FACTOR = 0.88  # 12% under budget pace


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_period() -> tuple[datetime.date, datetime.date, datetime.date]:
    """Return (period_start, today, period_end) for the current fiscal month."""
    today = datetime.date.today()
    start = today.replace(day=1)
    # Last day of the month
    if today.month == 12:
        end = today.replace(year=today.year + 1, month=1, day=1) - datetime.timedelta(days=1)
    else:
        end = today.replace(month=today.month + 1, day=1) - datetime.timedelta(days=1)
    return start, today, end


def _daily_planned(annual_budget: float, days_in_month: int) -> np.ndarray:
    """Return an array of daily planned spend (evenly distributed)."""
    monthly = annual_budget / 12
    return np.full(days_in_month, monthly / days_in_month)


def _daily_actuals(
    daily_plan: np.ndarray,
    elapsed_days: int,
    scenario: str,
    seed: int,
) -> np.ndarray:
    """Simulate daily actual spend with noise around a pacing scenario."""
    rng = np.random.default_rng(seed)
    n = elapsed_days

    if scenario == "over":
        factor = _OVER_FACTOR
    elif scenario == "under":
        factor = _UNDER_FACTOR
    else:
        factor = 1.0

    noise = rng.normal(loc=0, scale=0.05, size=n)
    actuals = daily_plan[:n] * factor * (1 + noise)
    return np.maximum(actuals, 0)  # no negative spend


def _project_landing(
    cumulative_actual: np.ndarray,
    elapsed_days: int,
    days_in_month: int,
    seed: int,
) -> tuple[float, float, float]:
    """
    Project end-of-month cumulative spend with 80% CI.

    Returns (projected, lower_80, upper_80).
    """
    if elapsed_days == 0:
        return 0.0, 0.0, 0.0

    daily_avg = cumulative_actual[-1] / elapsed_days
    remaining = days_in_month - elapsed_days
    projected = cumulative_actual[-1] + daily_avg * remaining

    # Uncertainty grows with remaining days
    rng = np.random.default_rng(seed + 99)
    std = daily_avg * 0.08 * np.sqrt(remaining)
    lower = projected - 1.28 * std  # ~80% CI
    upper = projected + 1.28 * std
    return float(projected), float(max(lower, 0)), float(upper)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data(ttl=300)
def load_budget_pacing() -> dict[str, dict]:
    """
    Return pacing data for all budget categories.

    Returns
    -------
    dict keyed by category name, each value is a dict with:
      - ``df`` : pd.DataFrame with columns
            date, planned_daily, actual_daily,
            planned_cumulative, actual_cumulative
        (rows for elapsed days only; planned_cumulative covers full month)
      - ``budget_monthly`` : float — monthly budget allocation
      - ``projected`` : float — projected end-of-month spend
      - ``projected_lower`` : float — 80% CI lower
      - ``projected_upper`` : float — 80% CI upper
      - ``pacing_pct`` : float — (actual_cumulative / planned_cumulative) - 1
      - ``pacing_flag`` : str — "over", "under", or "on_track"
      - ``days_elapsed`` : int
      - ``days_in_month`` : int
    """
    start, today, end = _get_period()
    days_in_month = (end - start).days + 1
    elapsed_days = (today - start).days + 1  # today counts

    result: dict[str, dict] = {}

    for i, cat in enumerate(CATEGORIES):
        annual = _ANNUAL_BUDGETS[cat]
        monthly = annual / 12
        scenario = _PACING_SCENARIOS[cat]

        daily_plan = _daily_planned(annual, days_in_month)
        daily_act = _daily_actuals(daily_plan, elapsed_days, scenario, seed=i * 17)

        cumplan = np.cumsum(daily_plan)
        cumact = np.concatenate([np.cumsum(daily_act), np.full(days_in_month - elapsed_days, np.nan)])

        dates = [start + datetime.timedelta(days=d) for d in range(days_in_month)]

        df = pd.DataFrame(
            {
                "date": dates,
                "planned_daily": daily_plan,
                "actual_daily": np.concatenate([daily_act, np.full(days_in_month - elapsed_days, np.nan)]),
                "planned_cumulative": cumplan,
                "actual_cumulative": cumact,
            }
        )

        proj, proj_lo, proj_hi = _project_landing(
            np.cumsum(daily_act), elapsed_days, days_in_month, seed=i
        )

        # Pacing: compare cumulative actual vs planned at today's day
        plan_to_date = cumplan[elapsed_days - 1]
        act_to_date = float(np.sum(daily_act))
        pacing_pct = (act_to_date / plan_to_date - 1) if plan_to_date > 0 else 0.0

        if pacing_pct > 0.05:
            flag = "over"
        elif pacing_pct < -0.05:
            flag = "under"
        else:
            flag = "on_track"

        result[cat] = {
            "df": df,
            "budget_monthly": monthly,
            "projected": proj,
            "projected_lower": proj_lo,
            "projected_upper": proj_hi,
            "pacing_pct": pacing_pct,
            "pacing_flag": flag,
            "actual_to_date": act_to_date,
            "plan_to_date": plan_to_date,
            "days_elapsed": elapsed_days,
            "days_in_month": days_in_month,
        }

    return result


def pacing_summary(data: dict[str, dict]) -> dict:
    """
    Aggregate summary across all categories.

    Returns a dict with:
      - total_budget_monthly
      - total_actual_to_date
      - total_plan_to_date
      - total_projected
      - over_count, under_count, on_track_count
      - overall_pacing_pct
    """
    total_budget = sum(v["budget_monthly"] for v in data.values())
    total_actual = sum(v["actual_to_date"] for v in data.values())
    total_plan = sum(v["plan_to_date"] for v in data.values())
    total_proj = sum(v["projected"] for v in data.values())

    flags = [v["pacing_flag"] for v in data.values()]
    overall_pct = (total_actual / total_plan - 1) if total_plan > 0 else 0.0

    return {
        "total_budget_monthly": total_budget,
        "total_actual_to_date": total_actual,
        "total_plan_to_date": total_plan,
        "total_projected": total_proj,
        "over_count": flags.count("over"),
        "under_count": flags.count("under"),
        "on_track_count": flags.count("on_track"),
        "overall_pacing_pct": overall_pct,
    }
