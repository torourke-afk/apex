"""
Filter Bar Component
--------------------
Compact horizontal filter strip: date-preset chips, DMA / channel / product
selectors, compare toggle, and Export / Refresh actions.

All selections are persisted in ``st.session_state`` with namespaced keys so
multiple filter bars on the same app don't collide.
"""

from __future__ import annotations

import datetime
import streamlit as st

from src.config.brand import COLORS, TYPOGRAPHY, BORDER_RADIUS, MOTION, inject_brand_css
from src.state import get_global, set_global
from src.data.data_range import (
    get_data_date_range,
    get_available_dmas,
    get_available_channels,
    get_available_products,
    compute_prior_period,
)

# ---------------------------------------------------------------------------
# Dynamic data-driven options (auto-detected from DuckDB at startup)
# ---------------------------------------------------------------------------

_DMA_OPTIONS: list[str] = []
_CHANNEL_OPTIONS: list[str] = []
_PRODUCT_OPTIONS: list[str] = []
_DATA_END_DATE: datetime.date | None = None
_DATA_START_DATE: datetime.date | None = None
_OPTIONS_LOADED: bool = False


def _ensure_options() -> None:
    """Load filter options from the database once per session."""
    global _DMA_OPTIONS, _CHANNEL_OPTIONS, _PRODUCT_OPTIONS
    global _DATA_END_DATE, _DATA_START_DATE, _OPTIONS_LOADED
    if _OPTIONS_LOADED:
        return
    _DATA_START_DATE, _DATA_END_DATE = get_data_date_range()
    _DMA_OPTIONS[:] = get_available_dmas() or [
        "Cincinnati, OH", "Columbus, OH", "Chicago, IL",
        "Nashville, TN", "Indianapolis, IN", "Atlanta, GA",
        "Dayton, OH", "Tampa, FL", "Orlando, FL", "Lexington, KY",
    ]
    _CHANNEL_OPTIONS[:] = get_available_channels() or [
        "SEM", "SOCIAL", "DISPLAY", "EMAIL", "DIRECT_MAIL",
        "SEO_BRAND", "SEO_NONBRAND", "DIRECT", "AEO_REFERRAL",
    ]
    _PRODUCT_OPTIONS[:] = get_available_products() or [
        "Momentum Checking", "Goal Saver", "Money Market Account",
        "Certificate of Deposit",
    ]
    _OPTIONS_LOADED = True


# Full preset names (used internally and returned in the filter dict)
_DATE_PRESETS: list[str] = ["Last 30 days", "Last 60 days", "Last 90 days", "Custom"]

# Short chip display labels — maps 1:1 to _DATE_PRESETS by index
_CHIP_LABELS: list[str] = ["30d", "60d", "90d", "Custom"]

# Bidirectional lookup
_CHIP_TO_PRESET: dict[str, str] = dict(zip(_CHIP_LABELS, _DATE_PRESETS))
_PRESET_TO_CHIP: dict[str, str] = dict(zip(_DATE_PRESETS, _CHIP_LABELS))


# ---------------------------------------------------------------------------
# CSS — injected at page level so it targets Streamlit widgets globally.
# The old .filter-bar-container approach doesn't work because st.markdown
# <div> tags don't actually wrap Streamlit widgets in the DOM.
# ---------------------------------------------------------------------------

_ff = TYPOGRAPHY["font_family"]
_ts = COLORS["text_secondary"]
_tp = COLORS["text_primary"]
_gb = COLORS["glass_border"]
_blue = COLORS["secondary"]
_dur = MOTION["duration_fast"]
_ease = MOTION["ease_out"]

_FILTER_CSS = f"""
<style>
  /* ── Scope all filter-bar rules to any stVerticalBlock containing
       the .filter-strip-row marker injected by filter_bar(). Using
       CSS :has() avoids relying on a JS-added class. ───────────────────── */

  /* ── Compact filter-bar: tighten the horizontal block gaps ────────────── */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stHorizontalBlock"] {{
    gap: 0.4rem !important;
    align-items: center !important;
  }}

  /* ── Date preset chips (st.radio → pill buttons) ────────────────────── */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stRadio"] > [data-testid="stWidgetLabel"] {{
    display: none !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stRadio"] > [role="radiogroup"] {{
    display: flex !important;
    flex-direction: row !important;
    gap: 4px !important;
    flex-wrap: nowrap !important;
    align-items: center !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stRadio"] [role="radiogroup"] > label {{
    display: inline-flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 3px 12px !important;
    border-radius: {BORDER_RADIUS['full']} !important;
    border: 1px solid {_gb} !important;
    background: transparent !important;
    color: {_ts} !important;
    font-family: {_ff} !important;
    font-size: 0.6875rem !important;
    font-weight: 500 !important;
    cursor: pointer !important;
    margin: 0 !important;
    transition: all {_dur} {_ease} !important;
    white-space: nowrap !important;
    height: 28px !important;
    min-height: 28px !important;
    line-height: 1 !important;
    gap: 0 !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stRadio"] [role="radiogroup"] > label:hover {{
    border-color: rgba(0,117,255,0.35) !important;
    color: {_tp} !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stRadio"] [role="radiogroup"] > label > div:first-child {{
    display: none !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stRadio"] [role="radiogroup"] > label > input {{
    position: absolute !important;
    opacity: 0 !important;
    width: 0 !important;
    height: 0 !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stRadio"] [role="radiogroup"] > label:has(input:checked) {{
    background: rgba(0,117,255,0.15) !important;
    border-color: {_blue} !important;
    color: {_tp} !important;
    font-weight: 600 !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stRadio"] [role="radiogroup"] > label p {{
    font-size: 0.6875rem !important;
    margin: 0 !important;
    white-space: nowrap !important;
  }}

  /* ── Multiselect compact sizing ──────────────────────────────────────── */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stMultiSelect"] {{
    min-height: 0 !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stMultiSelect"] [data-baseweb="select"] {{
    min-height: 28px !important;
    font-size: 0.75rem !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stMultiSelect"] [data-baseweb="select"] > div {{
    min-height: 28px !important;
    padding: 0 8px !important;
    font-size: 0.75rem !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stMultiSelect"] input {{
    font-size: 0.75rem !important;
  }}

  /* ── Compare toggle — smaller ────────────────────────────────────────── */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stToggle"] label {{
    font-size: 0.6875rem !important;
    color: {_ts} !important;
    white-space: nowrap !important;
  }}

  /* ── Action buttons — ghost style ────────────────────────────────────── */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) .stButton > button {{
    padding: 3px 10px !important;
    border-radius: {BORDER_RADIUS['md']} !important;
    border: 1px solid {_gb} !important;
    background: transparent !important;
    color: {_ts} !important;
    font-family: {_ff} !important;
    font-size: 0.6875rem !important;
    font-weight: 500 !important;
    height: 28px !important;
    min-height: 28px !important;
    line-height: 1 !important;
    transition: all {_dur} {_ease} !important;
    box-shadow: none !important;
    width: 100% !important;
    white-space: nowrap !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) .stButton > button:hover {{
    border-color: rgba(0,117,255,0.35) !important;
    color: {_tp} !important;
    background: rgba(0,117,255,0.06) !important;
    box-shadow: none !important;
  }}


  /* ── Tighten vertical gaps inside each column ───────────────────────── */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stVerticalBlock"] {{
    gap: 0.15rem !important;
  }}
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stVerticalBlock"] > div {{
    padding-top: 0 !important;
    padding-bottom: 0 !important;
  }}
  /* Hide native widget labels — filter identity comes from placeholder text */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stMultiSelect"] > [data-testid="stWidgetLabel"],
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stToggle"] > [data-testid="stWidgetLabel"] {{
    display: none !important;
  }}
  /* Style the compare toggle label (renders inline to the right of the knob) */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stToggle"] > label {{
    font-size: 0.6875rem !important;
    color: {_ts} !important;
    font-weight: 500 !important;
    white-space: nowrap !important;
  }}
</style>
"""


def _inject_css() -> None:
    """Inject filter bar CSS once per render."""
    st.markdown(_FILTER_CSS, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------

def _state_key(key_prefix: str, field: str) -> str:
    return f"{key_prefix}_filter_{field}"


def _init_state(key_prefix: str) -> None:
    """Populate session_state defaults if keys are absent or stale."""
    _ensure_options()
    anchor = _DATA_END_DATE or datetime.date.today()
    data_min = _DATA_START_DATE or (anchor - datetime.timedelta(days=365))
    _global_dma = get_global("dma_filter") or []

    k_start = _state_key(key_prefix, "date_start")
    k_end = _state_key(key_prefix, "date_end")

    if k_end in st.session_state:
        stored_end = st.session_state[k_end]
        if isinstance(stored_end, datetime.date) and stored_end > anchor:
            st.session_state[k_start] = anchor - datetime.timedelta(days=30)
            st.session_state[k_end] = anchor
            st.session_state[_state_key(key_prefix, "date_preset")] = _DATE_PRESETS[0]
    if k_start in st.session_state:
        stored_start = st.session_state[k_start]
        if isinstance(stored_start, datetime.date) and stored_start < data_min:
            st.session_state[k_start] = data_min

    defaults = {
        _state_key(key_prefix, "date_preset"): _DATE_PRESETS[0],
        k_start: anchor - datetime.timedelta(days=30),
        k_end: anchor,
        _state_key(key_prefix, "dma"): _global_dma,
        _state_key(key_prefix, "channel"): [],
        _state_key(key_prefix, "product"): [],
        _state_key(key_prefix, "compare"): False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def filter_bar(
    key_prefix: str = "default",
    show_date: bool = True,
    show_dma: bool = True,
    show_channel: bool = True,
    show_product: bool = True,
) -> dict:
    """Render a compact horizontal filter bar and return current selections."""
    inject_brand_css()
    _inject_css()
    _init_state(key_prefix)

    k_preset = _state_key(key_prefix, "date_preset")
    k_start = _state_key(key_prefix, "date_start")
    k_end = _state_key(key_prefix, "date_end")
    k_dma = _state_key(key_prefix, "dma")
    k_channel = _state_key(key_prefix, "channel")
    k_product = _state_key(key_prefix, "product")
    k_compare = _state_key(key_prefix, "compare")

    visible_filters = [show_date, show_dma, show_channel, show_product]
    if not any(visible_filters):
        return {
            "date_preset": st.session_state[k_preset],
            "date_start": st.session_state[k_start],
            "date_end": st.session_state[k_end],
            "dma": st.session_state[k_dma],
            "channel": st.session_state[k_channel],
            "product": st.session_state[k_product],
            "compare": st.session_state.get(k_compare, False),
        }

    _ensure_options()
    anchor = _DATA_END_DATE or datetime.date.today()
    data_min = _DATA_START_DATE or (anchor - datetime.timedelta(days=365))

    # ── Layout: compact column ratios ─────────────────────────────────────
    col_specs: list[float] = []
    if show_date:
        col_specs.append(3.0)     # date chips (4 pills need room)
    if show_dma:
        col_specs.append(2.0)
    if show_channel:
        col_specs.append(2.0)
    if show_product:
        col_specs.append(2.0)
    col_specs.append(1.5)         # compare toggle
    col_specs.append(1.1)         # export button
    col_specs.append(1.1)         # refresh button

    # Marker class for CSS scoping — the st.container wraps everything
    # and the sticky JS targets this container's stLayoutWrapper
    st.markdown(
        '<div class="filter-strip-row" style="display:contents;"></div>',
        unsafe_allow_html=True,
    )

    cols = st.columns(col_specs)
    col_idx = 0

    # ── Date preset chips ─────────────────────────────────────────────────
    if show_date:
        with cols[col_idx]:
            current_preset = st.session_state[k_preset]
            current_chip = _PRESET_TO_CHIP.get(current_preset, _CHIP_LABELS[0])
            current_chip_idx = _CHIP_LABELS.index(current_chip) if current_chip in _CHIP_LABELS else 0

            selected_chip = st.radio(
                label="Date Range",
                options=_CHIP_LABELS,
                index=current_chip_idx,
                horizontal=True,
                label_visibility="collapsed",
                key=f"_widget_{k_preset}",
            )

            new_preset = _CHIP_TO_PRESET.get(selected_chip, current_preset)
            st.session_state[k_preset] = new_preset

            if new_preset == "Last 30 days":
                st.session_state[k_start] = anchor - datetime.timedelta(days=30)
                st.session_state[k_end] = anchor
            elif new_preset == "Last 60 days":
                st.session_state[k_start] = anchor - datetime.timedelta(days=60)
                st.session_state[k_end] = anchor
            elif new_preset == "Last 90 days":
                st.session_state[k_start] = anchor - datetime.timedelta(days=90)
                st.session_state[k_end] = anchor
            else:
                sub_start, sub_end = st.columns(2)
                with sub_start:
                    date_start = st.date_input(
                        label="Start",
                        value=st.session_state[k_start],
                        min_value=data_min,
                        max_value=st.session_state[k_end],
                        label_visibility="collapsed",
                        key=f"_widget_{k_start}",
                    )
                with sub_end:
                    date_end = st.date_input(
                        label="End",
                        value=st.session_state[k_end],
                        min_value=date_start,
                        max_value=anchor,
                        label_visibility="collapsed",
                        key=f"_widget_{k_end}",
                    )
                st.session_state[k_start] = date_start
                st.session_state[k_end] = date_end

        col_idx += 1

    # ── DMA selector ──────────────────────────────────────────────────────
    if show_dma:
        with cols[col_idx]:
            selected_dma = st.multiselect(
                label="DMA",
                options=_DMA_OPTIONS,
                default=st.session_state[k_dma],
                placeholder="All DMAs",
                label_visibility="collapsed",
                key=f"_widget_{k_dma}",
            )
            st.session_state[k_dma] = selected_dma
            set_global("dma_filter", selected_dma)
        col_idx += 1

    # ── Channel selector ──────────────────────────────────────────────────
    if show_channel:
        with cols[col_idx]:
            selected_channel = st.multiselect(
                label="Channel",
                options=_CHANNEL_OPTIONS,
                default=st.session_state[k_channel],
                placeholder="All Channels",
                label_visibility="collapsed",
                key=f"_widget_{k_channel}",
            )
            st.session_state[k_channel] = selected_channel
        col_idx += 1

    # ── Product selector ──────────────────────────────────────────────────
    if show_product:
        with cols[col_idx]:
            selected_product = st.multiselect(
                label="Product",
                options=_PRODUCT_OPTIONS,
                default=st.session_state[k_product],
                placeholder="All Products",
                label_visibility="collapsed",
                key=f"_widget_{k_product}",
            )
            st.session_state[k_product] = selected_product
        col_idx += 1

    # ── Compare toggle ────────────────────────────────────────────────────
    with cols[col_idx]:
        compare = st.toggle(
            label="Compare",
            value=st.session_state.get(k_compare, False),
            label_visibility="visible",
            key=f"_widget_{k_compare}",
        )
        st.session_state[k_compare] = compare
    col_idx += 1

    # ── Export ──────────────────────────────────────────────────────────
    with cols[col_idx]:
        st.button("Export", key=f"_btn_export_{key_prefix}", use_container_width=True)
    col_idx += 1

    # ── Refresh ──────────────────────────────────────────────────────────
    with cols[col_idx]:
        if st.button("Refresh", key=f"_btn_refresh_{key_prefix}", use_container_width=True):
            st.rerun()

    # ── Build result ──────────────────────────────────────────────────────
    _compare = st.session_state.get(k_compare, False)
    _start = st.session_state[k_start]
    _end = st.session_state[k_end]

    result = {
        "date_preset": st.session_state[k_preset],
        "date_start": _start,
        "date_end": _end,
        "dma": st.session_state[k_dma],
        "channel": st.session_state[k_channel],
        "product": st.session_state[k_product],
        "compare": _compare,
        "prior_start": None,
        "prior_end": None,
    }

    if _compare and _start and _end:
        prior_start, prior_end = compute_prior_period(_start, _end)
        result["prior_start"] = prior_start
        result["prior_end"] = prior_end

    return result


# ---------------------------------------------------------------------------
# Global filter reader (for pages that use the persistent top nav)
# ---------------------------------------------------------------------------

def get_global_filters() -> dict:
    """Read filters from global session state keys (set by the app-level filter bar)."""
    return {
        "date_preset": st.session_state.get("global_filter_date_preset", "Last 30 days"),
        "date_start": st.session_state.get("global_filter_date_start"),
        "date_end": st.session_state.get("global_filter_date_end"),
        "dma": st.session_state.get("global_filter_dma", []),
        "channel": st.session_state.get("global_filter_channel", []),
        "product": st.session_state.get("global_filter_product", []),
        "compare": st.session_state.get("global_filter_compare", False),
        "prior_start": st.session_state.get("global_filter_prior_start"),
        "prior_end": st.session_state.get("global_filter_prior_end"),
    }
