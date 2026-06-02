"""
Organic AEO / LLM Visibility Data Module — APE-90
---------------------------------------------------
Provides deterministic seed data for the LLM Visibility Score dashboard:

  - PLATFORMS               : list of 6 AI platforms
  - PROMPT_CATEGORIES       : list of prompt query categories
  - DMA_MARKETS             : list of DMA market names (subset from retention)

  - get_llm_visibility_summary(filters) → dict of per-metric KPI dicts
  - get_llm_visibility_trends(filters) → dict of metric → wide DataFrame
  - get_prompt_results(filters)        → DataFrame of per-prompt records

All data is seeded at 42 and shifts deterministically with filter parameters
so charts update reactively when filters change.
"""

from __future__ import annotations

import math
import random
from datetime import date, timedelta
from typing import Any

import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLATFORMS: list[str] = [
    "ChatGPT",
    "Claude",
    "Gemini",
    "Perplexity",
    "Copilot",
    "Meta AI",
]

PROMPT_CATEGORIES: list[str] = [
    "Account Opening",
    "Mortgage",
    "Credit Cards",
    "Personal Loans",
    "Savings",
    "Financial Planning",
]

DMA_MARKETS: list[str] = [
    "New York",
    "Chicago",
    "Dallas",
    "Atlanta",
    "Philadelphia",
    "Boston",
    "Houston",
    "Phoenix",
    "Detroit",
    "Tampa",
    "Minneapolis",
    "Denver",
]

# 12 weekly periods ending on today (2026-05-08)
_TODAY = date(2026, 5, 8)
_WEEKS: list[str] = [
    (_TODAY - timedelta(weeks=11 - i)).strftime("%b %d")
    for i in range(12)
]

# Per-platform baseline rates — realistic spread across 6 AI assistants
_PLATFORM_BASELINES: dict[str, dict[str, float]] = {
    "ChatGPT":    {"mention_rate": 0.68, "avg_position": 2.1, "sov": 0.34, "sentiment": 78, "citation_rate": 0.52},
    "Claude":     {"mention_rate": 0.54, "avg_position": 2.8, "sov": 0.27, "sentiment": 82, "citation_rate": 0.44},
    "Gemini":     {"mention_rate": 0.48, "avg_position": 3.2, "sov": 0.24, "sentiment": 74, "citation_rate": 0.38},
    "Perplexity": {"mention_rate": 0.61, "avg_position": 2.4, "sov": 0.31, "sentiment": 76, "citation_rate": 0.58},
    "Copilot":    {"mention_rate": 0.39, "avg_position": 3.9, "sov": 0.19, "sentiment": 71, "citation_rate": 0.32},
    "Meta AI":    {"mention_rate": 0.31, "avg_position": 4.6, "sov": 0.15, "sentiment": 68, "citation_rate": 0.26},
}

# Trend direction per platform per metric (+1 improving, -1 declining)
_PLATFORM_TRENDS: dict[str, dict[str, int]] = {
    "ChatGPT":    {"mention_rate":  1, "avg_position": -1, "sov":  1, "sentiment":  1, "citation_rate":  1},
    "Claude":     {"mention_rate":  1, "avg_position": -1, "sov":  1, "sentiment":  1, "citation_rate":  1},
    "Gemini":     {"mention_rate":  1, "avg_position": -1, "sov":  1, "sentiment": -1, "citation_rate":  1},
    "Perplexity": {"mention_rate": -1, "avg_position":  1, "sov": -1, "sentiment":  1, "citation_rate": -1},
    "Copilot":    {"mention_rate": -1, "avg_position":  1, "sov": -1, "sentiment": -1, "citation_rate": -1},
    "Meta AI":    {"mention_rate":  1, "avg_position": -1, "sov":  1, "sentiment":  1, "citation_rate":  1},
}

# Metric weekly drift magnitude
_METRIC_DRIFT: dict[str, float] = {
    "mention_rate":  0.006,
    "avg_position":  0.04,
    "sov":           0.004,
    "sentiment":     0.5,
    "citation_rate": 0.008,
}

# Clamp ranges
_METRIC_CLAMPS: dict[str, tuple[float, float]] = {
    "mention_rate":  (0.10, 0.95),
    "avg_position":  (1.0, 6.5),
    "sov":           (0.05, 0.55),
    "sentiment":     (50.0, 95.0),
    "citation_rate": (0.05, 0.85),
}

# Sample prompt texts per category
_PROMPT_TEMPLATES: dict[str, list[str]] = {
    "Account Opening": [
        "What is the best bank for a new checking account?",
        "How do I open a savings account online?",
        "Which banks offer the easiest account opening process?",
        "Compare top banks for opening a first checking account.",
        "What should I look for when opening a bank account?",
    ],
    "Mortgage": [
        "What are current mortgage rates at Fifth Third Bank?",
        "How do I get pre-approved for a mortgage?",
        "Which banks offer the best 30-year fixed mortgage rates?",
        "What documents do I need for a mortgage application?",
        "Explain the mortgage approval process for first-time buyers.",
    ],
    "Credit Cards": [
        "Which bank offers the best cash back credit card?",
        "Compare Fifth Third credit cards with Chase and Bank of America.",
        "What is a good credit card for someone building credit?",
        "Best credit cards with no annual fee in 2026.",
        "How do I choose between a rewards card and cash back card?",
    ],
    "Personal Loans": [
        "Where can I get a personal loan with good rates?",
        "Compare personal loan rates across major banks.",
        "Is Fifth Third a good option for a personal loan?",
        "What credit score do I need for a personal loan?",
        "How fast can I get a personal loan approved?",
    ],
    "Savings": [
        "Which bank has the highest savings account interest rate?",
        "Compare high-yield savings accounts in 2026.",
        "Is it worth switching banks for a higher savings rate?",
        "Fifth Third Bank savings account vs online banks.",
        "How much should I keep in a savings account?",
    ],
    "Financial Planning": [
        "Which banks offer the best financial planning services?",
        "Does Fifth Third have financial advisors?",
        "How do I create a financial plan with my bank?",
        "Best banks for investment and financial planning tools.",
        "What budgeting tools does Fifth Third offer?",
    ],
}


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _filter_hash(filters: dict[str, Any]) -> int:
    """Produce a deterministic integer seed from active filter values."""
    parts = []
    for k in sorted(filters.keys()):
        v = filters[k]
        if isinstance(v, list):
            parts.append(f"{k}={'|'.join(sorted(str(x) for x in v))}")
        else:
            parts.append(f"{k}={v}")
    return hash("|".join(parts)) % (2**31)


def _apply_filter_shift(baseline: float, metric: str, filters: dict[str, Any]) -> float:
    """Shift baseline by a small deterministic amount based on active filters."""
    seed = _filter_hash(filters)
    rng = random.Random(seed)
    shift = rng.uniform(-0.04, 0.04)
    val = baseline + shift
    lo, hi = _METRIC_CLAMPS[metric]
    return max(lo, min(hi, val))


def _weekly_series(platform: str, metric: str, filters: dict[str, Any], n_weeks: int = 12) -> list[float]:
    """Generate a weekly time series for one platform/metric combination."""
    base = _filter_hash(filters)
    rng = random.Random(base + hash(platform) + hash(metric))
    adjusted_base = _apply_filter_shift(_PLATFORM_BASELINES[platform][metric], metric, filters)
    drift = _METRIC_DRIFT[metric] * _PLATFORM_TRENDS[platform][metric]
    lo, hi = _METRIC_CLAMPS[metric]

    # Walk backward from the current baseline
    series = [adjusted_base]
    for i in range(n_weeks - 1):
        noise = rng.gauss(0, _METRIC_DRIFT[metric] * 0.4)
        prev = series[-1] - drift + noise  # -drift because we walk backward
        series.append(max(lo, min(hi, prev)))

    series.reverse()
    return series


def _trim_weeks(series: list[float], n_weeks: int) -> list[float]:
    return series[-n_weeks:]


def _active_platforms(filters: dict[str, Any]) -> list[str]:
    sel = filters.get("platforms", [])
    return sel if sel else PLATFORMS


def _active_categories(filters: dict[str, Any]) -> list[str]:
    sel = filters.get("prompt_categories", [])
    return sel if sel else PROMPT_CATEGORIES


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def get_llm_visibility_summary(filters: dict[str, Any]) -> dict[str, dict]:
    """
    Return per-metric summary KPIs aggregated across selected platforms.

    Returns
    -------
    dict with keys: mention_rate, avg_position, sov, sentiment, citation_rate
    Each value is a dict with:
      - value        : current period aggregate (float)
      - prev_value   : prior period aggregate (float)
      - delta        : value - prev_value
      - sparkline    : list[float] — 12 weekly values (avg across platforms)
      - label        : human-readable metric name
      - format_type  : "percent" | "number" | "score"
      - higher_better: bool
    """
    n_weeks = filters.get("n_weeks", 12)
    platforms = _active_platforms(filters)

    metrics = {
        "mention_rate":  {"label": "Mention Rate",      "format_type": "percent",  "higher_better": True},
        "avg_position":  {"label": "Avg Position",      "format_type": "position", "higher_better": False},
        "sov":           {"label": "Share of Voice",    "format_type": "percent",  "higher_better": True},
        "sentiment":     {"label": "Sentiment Score",   "format_type": "score",    "higher_better": True},
        "citation_rate": {"label": "Citation Rate",     "format_type": "percent",  "higher_better": True},
    }

    result = {}
    for m, meta in metrics.items():
        all_series = [_trim_weeks(_weekly_series(p, m, filters), n_weeks) for p in platforms]
        # Average across platforms per week
        avg_series = [
            sum(s[i] for s in all_series) / len(all_series)
            for i in range(n_weeks)
        ]
        current = avg_series[-1]
        prev = avg_series[-2] if len(avg_series) >= 2 else current
        result[m] = {
            **meta,
            "value": current,
            "prev_value": prev,
            "delta": current - prev,
            "sparkline": avg_series,
        }

    return result


def get_llm_visibility_trends(filters: dict[str, Any]) -> dict[str, pd.DataFrame]:
    """
    Return a dict mapping metric name → wide DataFrame.

    Each DataFrame has:
      - index: week labels (str)
      - columns: one per active platform
      - values: weekly metric value
    """
    n_weeks = filters.get("n_weeks", 12)
    platforms = _active_platforms(filters)
    weeks = _WEEKS[-n_weeks:]

    metrics = ["mention_rate", "avg_position", "sov", "sentiment", "citation_rate"]
    result = {}
    for m in metrics:
        data = {}
        for p in platforms:
            series = _trim_weeks(_weekly_series(p, m, filters), n_weeks)
            data[p] = series
        result[m] = pd.DataFrame(data, index=weeks)

    return result


def get_prompt_results(filters: dict[str, Any]) -> pd.DataFrame:
    """
    Return a per-prompt results DataFrame.

    Columns:
      - prompt_text    : str
      - category       : str
      - platform       : str
      - mentioned      : bool
      - position       : int (1–10 or NaN if not mentioned)
      - sentiment      : float (0–100)
      - citation       : bool

    Row count: len(active_categories) * prompts_per_category * len(active_platforms)
    """
    platforms = _active_platforms(filters)
    categories = _active_categories(filters)

    seed = _filter_hash(filters)
    rng = random.Random(seed)

    rows: list[dict] = []
    for cat in categories:
        prompts = _PROMPT_TEMPLATES.get(cat, [f"Sample prompt for {cat}"])
        for prompt in prompts:
            for platform in platforms:
                base = _PLATFORM_BASELINES[platform]
                # Mention determination
                mention_p = base["mention_rate"] + rng.uniform(-0.05, 0.05)
                mentioned = rng.random() < max(0.1, min(0.95, mention_p))

                position = None
                if mentioned:
                    # Position: normally distributed around platform baseline
                    raw_pos = base["avg_position"] + rng.gauss(0, 0.8)
                    position = max(1, min(8, round(raw_pos, 1)))

                sentiment_val = base["sentiment"] + rng.gauss(0, 5)
                sentiment_val = max(50, min(98, round(sentiment_val, 1)))

                citation_p = base["citation_rate"] + rng.uniform(-0.05, 0.05)
                citation = mentioned and rng.random() < max(0.05, min(0.95, citation_p))

                rows.append({
                    "Prompt": prompt,
                    "Category": cat,
                    "Platform": platform,
                    "Mentioned": "Yes" if mentioned else "No",
                    "Position": position if mentioned else "—",
                    "Sentiment": sentiment_val,
                    "Citation": "Yes" if citation else "No",
                })

    return pd.DataFrame(rows)
