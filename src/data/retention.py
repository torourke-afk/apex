"""
Retention Data Module — APE-75
-------------------------------
Provides mock data for the Onboarding & Retention page:
  - get_cohort_heatmap(filters) → retention rate matrix (MOB × acquisition month)
  - get_bei_scores(market_tier) → BEI composite + component scores over time

Both functions return deterministic data seeded at 42, so charts are stable
across reruns. Filters shift baseline values to simulate realistic filter-driven
variance without a live DB.
"""

from __future__ import annotations

import math
import random
from typing import Any

import pandas as pd
import streamlit as st

from src.config.settings import APEX_DATA_REFRESH_INTERVAL_SECONDS
from src.data import cache_metrics

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHANNELS = ["SEM", "Social", "Display", "Direct Mail", "Branch"]
QUALITY_BANDS = ["A", "B", "C", "D"]
MARKETS = [
    "New York", "Chicago", "Dallas", "Atlanta", "Philadelphia",
    "Boston", "Houston", "Phoenix", "Detroit", "Tampa",
    "Minneapolis", "Denver", "Seattle", "Baltimore", "Cincinnati",
]
OFFER_TYPES = ["Cash Back", "Rate Special", "Fee Waiver", "Bundle", "None"]
PRODUCT_MIX = ["Checking", "Savings", "CD", "Credit Card", "Mortgage"]

MARKET_TIERS = {"Tier 1": 1, "Tier 2": 2, "Tier 3": 3, "All": 0}

# BEI formula weights
BEI_WEIGHTS = {
    "Awareness": 0.25,
    "Branded Search": 0.25,
    "Direct Traffic": 0.20,
    "Branch Visits": 0.20,
    "Social Engagement": 0.10,
}

# Acquisition months: 18 months ending ~May 2025
_ACQ_MONTHS = pd.date_range(end="2025-05-01", periods=18, freq="MS")
_ACQ_LABELS = [d.strftime("%b %Y") for d in _ACQ_MONTHS]

# ---------------------------------------------------------------------------
# Cohort Retention Heatmap
# ---------------------------------------------------------------------------

def _base_retention(mob: int, channel: str | None = None, band: str | None = None) -> float:
    """
    Asymptotic exponential decay retention at month-on-book `mob`.

    retention(mob) = floor + (start - floor) * exp(-k * (mob - 1))

    MOB 1 starts near 95%, decays sharply through MOB 6, then flattens toward
    a long-run floor (~72% for average cohort). This produces the classic
    S-curve visible in bank product retention data.

    Channel and quality band shift both the start and the floor.
    """
    # Channel modifiers — SEM retains best, Display worst
    channel_delta = {
        "SEM": 0.04,
        "Social": 0.01,
        "Display": -0.05,
        "Direct Mail": 0.02,
        "Branch": 0.05,
    }.get(channel or "", 0.0)

    # Quality band modifiers — A retains best
    band_delta = {"A": 0.06, "B": 0.02, "C": -0.04, "D": -0.10}.get(band or "", 0.0)

    shift = channel_delta + band_delta

    # Asymptotic parameters
    start = 0.95 + shift          # retention at MOB 1
    floor = 0.72 + shift * 0.6   # long-run retention floor (flatter than start shift)
    k = 0.28                      # decay rate — controls how fast early drop is

    # Clamp floor below start
    floor = max(0.10, min(start - 0.05, floor))

    retention = floor + (start - floor) * math.exp(-k * (mob - 1))
    return max(0.05, min(0.99, retention))


def get_cohort_heatmap(filters: dict[str, Any] | None = None) -> pd.DataFrame:
    """
    Return a DataFrame suitable for a Plotly heatmap.

    Shape: rows = MOB 1–18 (index), columns = acquisition month labels.
    Values: retention rate (0.0–1.0).

    Parameters
    ----------
    filters : dict, optional
        Keys: ``channel`` (list[str]), ``quality_score_band`` (list[str]),
        ``market`` (list[str]), ``offer_type`` (list[str]),
        ``product_mix`` (list[str]).

    Returns
    -------
    pd.DataFrame
        Index: int (MOB 1–18), Columns: str (acquisition month labels),
        Values: float (retention rate 0–1).
    """
    filters = filters or {}
    rng = random.Random(42)

    # Determine effective channel/band for baseline shift
    channels = filters.get("channel") or []
    bands = filters.get("quality_score_band") or []

    # Pick representative modifiers (first selected or None = all)
    channel = channels[0] if len(channels) == 1 else None
    band = bands[0] if len(bands) == 1 else None

    # Market & offer type add minor noise shifts
    markets = filters.get("market") or []
    offers = filters.get("offer_type") or []
    market_seed = sum(ord(c) for m in markets for c in m) if markets else 0
    offer_seed = sum(ord(c) for o in offers for c in o) if offers else 0
    noise_scale = 0.015 + (0.005 * (len(bands) > 1))

    records: dict[str, list[float]] = {}
    for col_idx, acq_label in enumerate(_ACQ_LABELS):
        col_rates: list[float] = []
        for mob in range(1, 19):
            rate = _base_retention(mob, channel, band)
            # Add small deterministic noise per cohort
            seed = 42 + col_idx * 100 + mob + market_seed + offer_seed
            rng = random.Random(seed)
            noise = rng.uniform(-noise_scale, noise_scale)
            # Slightly more recent cohorts trend slightly better (recency improvement)
            recency_boost = col_idx * 0.0015
            rate = max(0.05, min(0.99, rate + noise + recency_boost))
            col_rates.append(round(rate, 4))
        records[acq_label] = col_rates

    df = pd.DataFrame(records, index=range(1, 19))
    df.index.name = "MOB"
    return df


def get_cohort_active_accounts(filters: dict[str, Any] | None = None) -> pd.DataFrame:
    """
    Return active account counts matching the heatmap dimensions.
    Used for heatmap hover text.
    """
    rng = random.Random(99)
    filters = filters or {}

    records: dict[str, list[int]] = {}
    for col_idx, acq_label in enumerate(_ACQ_LABELS):
        # Starting cohort size decreases with recency (older cohorts fully ramped)
        cohort_size = 8000 - col_idx * 250 + rng.randint(-200, 200)
        cohort_size = max(1500, cohort_size)
        col_accounts: list[int] = []
        for mob in range(1, 19):
            seed = 99 + col_idx * 50 + mob
            rng2 = random.Random(seed)
            # Apply exponential decay to account count
            decay_factor = math.exp(-0.08 * (mob - 1))
            accounts = int(cohort_size * decay_factor * (0.92 + rng2.uniform(-0.03, 0.03)))
            col_accounts.append(max(50, accounts))
        records[acq_label] = col_accounts

    df = pd.DataFrame(records, index=range(1, 19))
    df.index.name = "MOB"
    return df


# ---------------------------------------------------------------------------
# BEI Composite Score
# ---------------------------------------------------------------------------

_BEI_MONTHS = pd.date_range(end="2025-05-01", periods=12, freq="MS")
_BEI_LABELS = [d.strftime("%b %Y") for d in _BEI_MONTHS]

# Tier baselines for each BEI component (0–100 scale)
_TIER_BASELINES: dict[int, dict[str, float]] = {
    1: {"Awareness": 72, "Branded Search": 68, "Direct Traffic": 65, "Branch Visits": 71, "Social Engagement": 58},
    2: {"Awareness": 61, "Branded Search": 55, "Direct Traffic": 53, "Branch Visits": 60, "Social Engagement": 49},
    3: {"Awareness": 48, "Branded Search": 41, "Direct Traffic": 40, "Branch Visits": 45, "Social Engagement": 36},
}


def _tier_label(tier_int: int) -> str:
    return {1: "Tier 1", 2: "Tier 2", 3: "Tier 3"}.get(tier_int, f"Tier {tier_int}")


def get_bei_scores(market_tier: str = "All") -> dict[str, Any]:
    """
    Return BEI composite and component scores for each market tier over 12 months.

    Parameters
    ----------
    market_tier : str
        One of "Tier 1", "Tier 2", "Tier 3", "All".
        When "All", all three tiers are returned for comparison.

    Returns
    -------
    dict with keys:
        ``composite_df``   pd.DataFrame   Columns: month_label, tier, bei_composite
        ``components_df``  pd.DataFrame   Columns: tier, component, value (latest period)
        ``months``         list[str]      12 month labels
        ``tiers``          list[str]      Tiers included in this result
    """
    tier_int = MARKET_TIERS.get(market_tier, 0)
    tiers_to_include = [1, 2, 3] if tier_int == 0 else [tier_int]

    composite_rows: list[dict] = []
    component_rows: list[dict] = []

    for t in tiers_to_include:
        baselines = _TIER_BASELINES[t]
        tier_label = _tier_label(t)

        for m_idx, month in enumerate(_BEI_LABELS):
            components: dict[str, float] = {}
            rng = random.Random(t * 1000 + m_idx)
            for comp, base in baselines.items():
                # Gentle upward trend with noise
                trend = m_idx * 0.4
                noise = rng.uniform(-2.0, 2.5)
                value = max(10.0, min(99.0, base + trend + noise))
                components[comp] = round(value, 1)

            # BEI composite = weighted sum
            bei = sum(BEI_WEIGHTS[c] * v for c, v in components.items())
            composite_rows.append({
                "month": month,
                "tier": tier_label,
                "bei_composite": round(bei, 2),
            })

            # Latest period components for stacked bar
            if m_idx == len(_BEI_LABELS) - 1:
                for comp, val in components.items():
                    component_rows.append({
                        "tier": tier_label,
                        "component": comp,
                        "value": val,
                        "weight": BEI_WEIGHTS[comp],
                        "weighted_value": round(val * BEI_WEIGHTS[comp], 2),
                    })

    composite_df = pd.DataFrame(composite_rows)
    components_df = pd.DataFrame(component_rows)

    return {
        "composite_df": composite_df,
        "components_df": components_df,
        "months": _BEI_LABELS,
        "tiers": [_tier_label(t) for t in tiers_to_include],
    }


# ---------------------------------------------------------------------------
# APE-76 — Behavioral Triggers
# ---------------------------------------------------------------------------

def get_behavioral_triggers() -> pd.DataFrame:
    """
    Returns Kamino behavioral trigger definitions with volume and CVR metrics.

    Columns: Trigger Condition, Action, Volume/Week, CVR (%), Signal, Status
    Sorted by Volume/Week descending.
    """
    rows = [
        {"Trigger Condition": "No transaction 7d",  "Action": "Email",               "Volume/Week": 4_820, "CVR (%)": 11.4, "Status": "Active"},
        {"Trigger Condition": "No app download 7d", "Action": "SMS",                 "Volume/Week": 3_610, "CVR (%)": 8.7,  "Status": "Active"},
        {"Trigger Condition": "No DD 14d",          "Action": "Guided Switching",    "Volume/Week": 2_940, "CVR (%)": 6.2,  "Status": "Active"},
        {"Trigger Condition": "Large deposit",      "Action": "CD Comparison",       "Volume/Week": 1_755, "CVR (%)": 14.8, "Status": "Active"},
        {"Trigger Condition": "Rent >$2K",          "Action": "Mortgage Pre-Qual",   "Volume/Week": 1_320, "CVR (%)": 4.1,  "Status": "Testing"},
        {"Trigger Condition": "Unfunded 7d",        "Action": "Push + Banker Email", "Volume/Week": 5_490, "CVR (%)": 3.6,  "Status": "Active"},
    ]
    df = pd.DataFrame(rows).sort_values("Volume/Week", ascending=False).reset_index(drop=True)

    def _signal(cvr: float) -> str:
        if cvr > 10:
            return "🟢 High"
        if cvr >= 5:
            return "🟡 Mid"
        return "🔴 Low"

    df["Signal"] = df["CVR (%)"].apply(_signal)
    return df[["Trigger Condition", "Action", "Volume/Week", "CVR (%)", "Signal", "Status"]]


# ---------------------------------------------------------------------------
# APE-76 — Geo-Retention Heat Map
# ---------------------------------------------------------------------------

def get_geo_retention() -> pd.DataFrame:
    """
    Returns MSA-level 90-day retention data for the geo scatter map.

    Columns: MSA, lat, lon, Volume, Retention_90d (%), Tier
    """
    msas = [
        # Top-tier markets
        {"MSA": "New York, NY",      "lat": 40.71, "lon": -74.01,  "Volume": 48_200, "Retention_90d": 94.8, "Tier": "Top"},
        {"MSA": "Los Angeles, CA",   "lat": 34.05, "lon": -118.24, "Volume": 36_500, "Retention_90d": 91.3, "Tier": "Top"},
        {"MSA": "Chicago, IL",       "lat": 41.88, "lon": -87.63,  "Volume": 29_100, "Retention_90d": 88.7, "Tier": "Top"},
        {"MSA": "Houston, TX",       "lat": 29.76, "lon": -95.37,  "Volume": 22_400, "Retention_90d": 86.4, "Tier": "Top"},
        {"MSA": "Phoenix, AZ",       "lat": 33.45, "lon": -112.07, "Volume": 18_700, "Retention_90d": 92.1, "Tier": "Top"},
        {"MSA": "Philadelphia, PA",  "lat": 39.95, "lon": -75.17,  "Volume": 17_900, "Retention_90d": 89.5, "Tier": "Top"},
        # Mid-tier markets
        {"MSA": "Dallas, TX",        "lat": 32.78, "lon": -96.80,  "Volume": 14_600, "Retention_90d": 87.2, "Tier": "Mid"},
        {"MSA": "San Antonio, TX",   "lat": 29.43, "lon": -98.49,  "Volume": 11_200, "Retention_90d": 83.9, "Tier": "Mid"},
        {"MSA": "San Diego, CA",     "lat": 32.72, "lon": -117.16, "Volume": 12_800, "Retention_90d": 93.4, "Tier": "Mid"},
        {"MSA": "Jacksonville, FL",  "lat": 30.33, "lon": -81.66,  "Volume": 9_400,  "Retention_90d": 84.7, "Tier": "Mid"},
        {"MSA": "Columbus, OH",      "lat": 39.96, "lon": -82.99,  "Volume": 8_700,  "Retention_90d": 90.2, "Tier": "Mid"},
        {"MSA": "Charlotte, NC",     "lat": 35.23, "lon": -80.84,  "Volume": 10_100, "Retention_90d": 91.8, "Tier": "Mid"},
        {"MSA": "Indianapolis, IN",  "lat": 39.77, "lon": -86.16,  "Volume": 7_900,  "Retention_90d": 85.6, "Tier": "Mid"},
        {"MSA": "Seattle, WA",       "lat": 47.61, "lon": -122.33, "Volume": 16_300, "Retention_90d": 95.2, "Tier": "Mid"},
        {"MSA": "Denver, CO",        "lat": 39.74, "lon": -104.98, "Volume": 13_500, "Retention_90d": 93.7, "Tier": "Mid"},
        # Emerging markets
        {"MSA": "Nashville, TN",     "lat": 36.16, "lon": -86.78,  "Volume": 6_200,  "Retention_90d": 88.4, "Tier": "Emerging"},
        {"MSA": "Louisville, KY",    "lat": 38.25, "lon": -85.76,  "Volume": 4_800,  "Retention_90d": 82.1, "Tier": "Emerging"},
        {"MSA": "Oklahoma City, OK", "lat": 35.47, "lon": -97.52,  "Volume": 4_100,  "Retention_90d": 81.3, "Tier": "Emerging"},
        {"MSA": "Raleigh, NC",       "lat": 35.78, "lon": -78.64,  "Volume": 5_600,  "Retention_90d": 92.6, "Tier": "Emerging"},
        {"MSA": "Minneapolis, MN",   "lat": 44.98, "lon": -93.27,  "Volume": 9_800,  "Retention_90d": 90.9, "Tier": "Emerging"},
    ]
    return pd.DataFrame(msas)


# ---------------------------------------------------------------------------
# APE-76 — Offer Engine Performance
# ---------------------------------------------------------------------------

def get_offer_performance() -> dict:
    """
    Returns offer engine performance data.

    Returns
    -------
    dict with keys:
        kpis : dict
            eligibility_rate, activation_rate, fulfillment_rate (%)
        activation_time_series : pd.DataFrame
            Columns: Month, Offer Type, Activations
        impact_table : pd.DataFrame
            Columns: Offer Type, Day 30 Impact (%), Day 90 Impact (%)
            Sorted by Day 90 desc.
    """
    kpis = {
        "eligibility_rate": 68.4,
        "activation_rate": 31.7,
        "fulfillment_rate": 84.2,
    }

    months = ["Nov", "Dec", "Jan", "Feb", "Mar", "Apr"]
    base_activations = {
        "CD Rate Bonus":     [820, 910, 860, 930, 990, 1_040],
        "Mortgage Pre-Qual": [310, 280, 320, 350, 390,   420],
        "Cash Back Rewards": [640, 710, 680, 720, 780,   850],
        "Savings Boost":     [430, 470, 510, 540, 580,   620],
        "Referral Bonus":    [190, 210, 230, 250, 270,   295],
    }

    rows = []
    for offer_type, counts in base_activations.items():
        for month, count in zip(months, counts):
            rows.append({"Month": month, "Offer Type": offer_type, "Activations": count})
    activation_ts = pd.DataFrame(rows)
    activation_ts["Month"] = pd.Categorical(activation_ts["Month"], categories=months, ordered=True)

    impact_df = (
        pd.DataFrame([
            {"Offer Type": "CD Rate Bonus",     "Day 30 Impact (%)": 8.4,  "Day 90 Impact (%)": 14.2},
            {"Offer Type": "Mortgage Pre-Qual", "Day 30 Impact (%)": 5.1,  "Day 90 Impact (%)": 11.7},
            {"Offer Type": "Cash Back Rewards", "Day 30 Impact (%)": 7.8,  "Day 90 Impact (%)": 9.3},
            {"Offer Type": "Savings Boost",     "Day 30 Impact (%)": 6.2,  "Day 90 Impact (%)": 8.6},
            {"Offer Type": "Referral Bonus",    "Day 30 Impact (%)": 4.3,  "Day 90 Impact (%)": 7.1},
        ])
        .sort_values("Day 90 Impact (%)", ascending=False)
        .reset_index(drop=True)
    )

    return {
        "kpis": kpis,
        "activation_time_series": activation_ts,
        "impact_table": impact_df,
    }


# ---------------------------------------------------------------------------
# APE-74 — PFI Flywheel Milestones
# ---------------------------------------------------------------------------

def get_pfi_milestones() -> list[dict]:
    """
    Returns PFI milestone data for the Flywheel Tracker.

    Each dict has keys:
        milestone : str   — milestone name
        target    : float — target completion % (0–100)
        actual    : float — actual completion % (0–100)
        window_d  : int   — time window in days
    """
    return [
        {"milestone": "Direct Deposit", "target": 50.0, "actual": 47.0, "window_d": 30},
        {"milestone": "Bill Pay",       "target": 30.0, "actual": 21.0, "window_d": 60},
        {"milestone": "Debit Card",     "target": 70.0, "actual": 73.0, "window_d": 14},
        {"milestone": "Digital Wallet", "target": 25.0, "actual": 27.0, "window_d": 30},
        {"milestone": "P2P",            "target": 20.0, "actual": 14.0, "window_d": 60},
        {"milestone": "Cross-sell",     "target": 25.0, "actual": 23.0, "window_d": 90},
    ]


def get_milestone_kpis() -> list[dict]:
    """
    Returns 90-day milestone KPI data for the Milestone Dashboard.

    Each dict has keys:
        title        : str   — KPI label
        value        : float — current observed value (%)
        threshold    : float — alert threshold (%)
        kamino_text  : str   — Kamino intervention text shown on alert
    """
    return [
        {
            "title": "Day 7 Funded",
            "value": 78.4,
            "threshold": 75.0,
            "kamino_text": "Kamino: Send funding nudge sequence",
        },
        {
            "title": "Day 30 Direct Deposit",
            "value": 43.1,
            "threshold": 45.0,
            "kamino_text": "Kamino: Trigger DD activation flow",
        },
        {
            "title": "Day 90 2nd Product",
            "value": 18.6,
            "threshold": 20.0,
            "kamino_text": "Kamino: Cross-sell outreach eligible",
        },
        {
            "title": "Day 90 Retention",
            "value": 91.2,
            "threshold": 85.0,
            "kamino_text": "Kamino: Retention pathway active",
        },
    ]


# ---------------------------------------------------------------------------
# Streamlit-cached wrappers  (load_*)
# ---------------------------------------------------------------------------

def load_pfi_milestones() -> list[dict]:
    """Cached wrapper for get_pfi_milestones."""
    cache_metrics.record_call("load_pfi_milestones")
    return _load_pfi_milestones_cached()


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_pfi_milestones_cached() -> list[dict]:
    cache_metrics.record_miss("load_pfi_milestones")
    return get_pfi_milestones()


load_pfi_milestones.clear = _load_pfi_milestones_cached.clear  # type: ignore[attr-defined]


def load_cohort_heatmap(filters: dict[str, Any] | None = None) -> "pd.DataFrame":
    """Cached wrapper for get_cohort_heatmap."""
    cache_metrics.record_call("load_cohort_heatmap")
    import json
    key = json.dumps(filters, sort_keys=True) if filters else None
    return _load_cohort_heatmap_cached(key)


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_cohort_heatmap_cached(filters_key: str | None) -> "pd.DataFrame":
    cache_metrics.record_miss("load_cohort_heatmap")
    import json
    filters = json.loads(filters_key) if filters_key else None
    return get_cohort_heatmap(filters)


load_cohort_heatmap.clear = _load_cohort_heatmap_cached.clear  # type: ignore[attr-defined]


def load_bei_scores(market_tier: str = "All") -> dict:
    """Cached wrapper for get_bei_scores."""
    cache_metrics.record_call("load_bei_scores")
    return _load_bei_scores_cached(market_tier)


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_bei_scores_cached(market_tier: str) -> dict:
    cache_metrics.record_miss("load_bei_scores")
    return get_bei_scores(market_tier)


load_bei_scores.clear = _load_bei_scores_cached.clear  # type: ignore[attr-defined]


def load_behavioral_triggers() -> "pd.DataFrame":
    """Cached wrapper for get_behavioral_triggers."""
    cache_metrics.record_call("load_behavioral_triggers")
    return _load_behavioral_triggers_cached()


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_behavioral_triggers_cached() -> "pd.DataFrame":
    cache_metrics.record_miss("load_behavioral_triggers")
    return get_behavioral_triggers()


load_behavioral_triggers.clear = _load_behavioral_triggers_cached.clear  # type: ignore[attr-defined]


def load_geo_retention() -> "pd.DataFrame":
    """Cached wrapper for get_geo_retention."""
    cache_metrics.record_call("load_geo_retention")
    return _load_geo_retention_cached()


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_geo_retention_cached() -> "pd.DataFrame":
    cache_metrics.record_miss("load_geo_retention")
    return get_geo_retention()


load_geo_retention.clear = _load_geo_retention_cached.clear  # type: ignore[attr-defined]


def load_offer_performance() -> dict:
    """Cached wrapper for get_offer_performance."""
    cache_metrics.record_call("load_offer_performance")
    return _load_offer_performance_cached()


@st.cache_data(ttl=APEX_DATA_REFRESH_INTERVAL_SECONDS)
def _load_offer_performance_cached() -> dict:
    cache_metrics.record_miss("load_offer_performance")
    return get_offer_performance()


load_offer_performance.clear = _load_offer_performance_cached.clear  # type: ignore[attr-defined]
