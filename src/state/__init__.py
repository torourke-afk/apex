"""
src/state/__init__.py — Session State Registry & Namespace Module

Central session state management for Apex.  All cross-page and per-module
keys live here; callers use the typed getters/setters rather than touching
st.session_state directly.
"""

from __future__ import annotations

from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Namespace prefix constants
# ---------------------------------------------------------------------------

NS_GLOBAL = "global_"
NS_SCORECARD = "scorecard_"
NS_SPEND = "spend_"
NS_FUNNEL = "funnel_"
NS_ONBOARDING = "onboarding_"
NS_CHANNELS = "channels_"
NS_ORGANIC = "organic_"
NS_PRODUCT = "product_"
NS_OPS = "ops_"
NS_SIMULATOR = "simulator_"

# ---------------------------------------------------------------------------
# STATE_KEYS registry
# Each entry: { "type": <python type>, "owner": <namespace>, "default": <value> }
# ---------------------------------------------------------------------------

STATE_KEYS: dict[str, dict[str, Any]] = {
    # ── Global shared keys ───────────────────────────────────────────────────
    "global_current_page": {
        "type": str,
        "owner": NS_GLOBAL,
        "default": None,
        "placeholder": True,
    },
    "global_date_range": {
        "type": tuple,
        "owner": NS_GLOBAL,
        "default": (),
        "placeholder": True,
    },
    "global_alert_context": {
        "type": type(None),
        "owner": NS_GLOBAL,
        "default": None,
    },
    "global_dma_filter": {
        "type": list,
        "owner": NS_GLOBAL,
        "default": [],
    },
    "global_scenarios": {
        "type": list,
        "owner": NS_GLOBAL,
        "default": [],
    },
    # ── Scorecard ────────────────────────────────────────────────────────────
    "scorecard_acknowledged_alerts": {
        "type": list,
        "owner": NS_SCORECARD,
        "default": [],
    },
    # ── Spend ────────────────────────────────────────────────────────────────
    "spend_current_budget": {
        "type": dict,
        "owner": NS_SPEND,
        "default": {},
    },
    "channel_mix_budget_m": {
        "type": float,
        "owner": NS_SPEND,
        "default": 5.0,
    },
    "channel_overrides": {
        "type": dict,
        "owner": NS_SPEND,
        "default": {},
    },
    "market_tier_overrides": {
        "type": dict,
        "owner": NS_SPEND,
        "default": {},
    },
    # ── Funnel ───────────────────────────────────────────────────────────────
    "funnel_filter_date_preset": {
        "type": str,
        "owner": NS_FUNNEL,
        "default": "Last 30 days",
    },
    "funnel_filter_date_start": {
        "type": type(None),
        "owner": NS_FUNNEL,
        "default": None,
    },
    "funnel_filter_date_end": {
        "type": type(None),
        "owner": NS_FUNNEL,
        "default": None,
    },
    "funnel_filter_dma": {
        "type": list,
        "owner": NS_FUNNEL,
        "default": [],
    },
    "funnel_filter_channel": {
        "type": list,
        "owner": NS_FUNNEL,
        "default": [],
    },
    "funnel_filter_product": {
        "type": list,
        "owner": NS_FUNNEL,
        "default": [],
    },
    "funnel_filter_segment": {
        "type": str,
        "owner": NS_FUNNEL,
        "default": "All Segments",
    },
    "funnel_filter_campaign": {
        "type": str,
        "owner": NS_FUNNEL,
        "default": "All Campaigns",
    },
    "funnel_dropoff_stage_idx": {
        "type": int,
        "owner": NS_FUNNEL,
        "default": 0,
    },
    "funnel_dropoff_dimension": {
        "type": str,
        "owner": NS_FUNNEL,
        "default": "channel",
    },
    "funnel_dropoff_ltv": {
        "type": int,
        "owner": NS_FUNNEL,
        "default": 3200,
    },
    # ── Onboarding / Retention ───────────────────────────────────────────────
    "bei_market_tier": {
        "type": str,
        "owner": NS_ONBOARDING,
        "default": "All",
    },
    "retention_channel": {
        "type": list,
        "owner": NS_ONBOARDING,
        "default": [],
    },
    "retention_market": {
        "type": list,
        "owner": NS_ONBOARDING,
        "default": [],
    },
    "retention_quality_band": {
        "type": list,
        "owner": NS_ONBOARDING,
        "default": [],
    },
    "retention_offer_type": {
        "type": list,
        "owner": NS_ONBOARDING,
        "default": [],
    },
    "retention_cohort_range": {
        "type": int,
        "owner": NS_ONBOARDING,
        "default": 18,
    },
    # ── Organic / AEO ────────────────────────────────────────────────────────
    "aeo_platforms": {
        "type": list,
        "owner": NS_ORGANIC,
        "default": [],
    },
    "aeo_n_weeks": {
        "type": int,
        "owner": NS_ORGANIC,
        "default": 12,
    },
    "aeo_dma_markets": {
        "type": list,
        "owner": NS_ORGANIC,
        "default": [],
    },
    "aeo_prompt_categories": {
        "type": list,
        "owner": NS_ORGANIC,
        "default": [],
    },
    # ── Channels ─────────────────────────────────────────────────────────────
    "channels_selected": {
        "type": list,
        "owner": NS_CHANNELS,
        "default": [],
        "placeholder": True,
    },
    # ── Product ──────────────────────────────────────────────────────────────
    "product_selected_line": {
        "type": str,
        "owner": NS_PRODUCT,
        "default": "All",
        "placeholder": True,
    },
    # ── Ops ──────────────────────────────────────────────────────────────────
    "approval_queue": {
        "type": list,
        "owner": NS_OPS,
        "default": [],
    },
    "approval_log": {
        "type": list,
        "owner": NS_OPS,
        "default": [],
    },
    "cal_year": {
        "type": int,
        "owner": NS_OPS,
        "default": 2026,
    },
    "cal_month": {
        "type": int,
        "owner": NS_OPS,
        "default": 1,
    },
    # ── Simulator ────────────────────────────────────────────────────────────
    "simulator": {
        "type": dict,
        "owner": NS_SIMULATOR,
        "default": {},
    },
    "submitted_directives": {
        "type": list,
        "owner": NS_SIMULATOR,
        "default": [],
    },
}

# ---------------------------------------------------------------------------
# init_state — idempotent cold-start initialisation
# ---------------------------------------------------------------------------


def init_state() -> None:
    """Initialise all registered session-state keys with their defaults.

    Safe to call multiple times; already-set keys are left untouched.
    """
    for key, meta in STATE_KEYS.items():
        if key not in st.session_state:
            # Use a copy for mutable defaults so pages don't share references.
            default = meta["default"]
            if isinstance(default, list):
                st.session_state[key] = list(default)
            elif isinstance(default, dict):
                st.session_state[key] = dict(default)
            else:
                st.session_state[key] = default


# ---------------------------------------------------------------------------
# Typed accessors — global namespace
# ---------------------------------------------------------------------------


def get_global(key: str) -> Any:
    """Return a global-namespace value.

    ``key`` must NOT include the ``global_`` prefix; it is prepended
    automatically.
    """
    full_key = f"{NS_GLOBAL}{key}"
    return st.session_state.get(full_key)


def set_global(key: str, value: Any) -> None:
    """Set a global-namespace key.

    ``key`` must NOT include the ``global_`` prefix.
    """
    full_key = f"{NS_GLOBAL}{key}"
    st.session_state[full_key] = value


# ---------------------------------------------------------------------------
# Typed accessors — module namespace
# ---------------------------------------------------------------------------


def get_module(module: str, key: str) -> Any:
    """Return a module-scoped value.

    ``module`` should be one of the NS_* constants *without* the trailing
    underscore, e.g. ``"scorecard"``.  The prefix is prepended automatically.
    ``key`` must NOT include the namespace prefix.
    """
    full_key = f"{module}_{key}"
    return st.session_state.get(full_key)


def set_module(module: str, key: str, value: Any) -> None:
    """Set a module-scoped key.

    ``module`` should be one of the NS_* constants *without* the trailing
    underscore.  The prefix is prepended automatically.
    """
    full_key = f"{module}_{key}"
    st.session_state[full_key] = value
