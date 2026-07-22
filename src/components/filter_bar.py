"""
Filter Bar Component — Signal Deck Design System
-------------------------------------------------
Compact horizontal filter strip matching the reference mockup
(Executive-Scorecard.dc.html lines 122-151).

Renders a pure-HTML flex row styled to the Signal Deck tokens, with
hidden Streamlit widgets underneath that drive actual filter state via
``st.session_state``.  Each filter chip shows the current selection
summary; clicking uses the hidden Streamlit widgets for selection.

All selections are persisted in ``st.session_state`` with namespaced keys
so multiple filter bars on the same app don't collide.
"""

from __future__ import annotations

import datetime
import streamlit as st

from src.config.brand import inject_brand_css
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


# Date presets
_DATE_PRESETS: list[str] = ["Last 30 days", "Last 60 days", "Last 90 days", "Custom"]
_DATE_PRESET_LABELS: dict[str, str] = {
    "Last 30 days": "Last 30d",
    "Last 60 days": "Last 60d",
    "Last 90 days": "Last 90d",
    "Custom": "Custom",
}


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
# Signal Deck filter bar CSS
# ---------------------------------------------------------------------------

_FILTER_BAR_CSS = """
<style>
  /* ── Signal Deck filter bar — pure HTML chip row ──────────────────────── */

  .sd-filter-bar {
    flex: none;
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 11px 22px;
    border-bottom: 1px solid var(--line);
    background: var(--bg2);
    font-family: 'Space Grotesk', system-ui, sans-serif;
  }

  .sd-filter-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    letter-spacing: .18em;
    color: var(--text3);
    margin-right: 2px;
    text-transform: uppercase;
    user-select: none;
  }

  .sd-filter-chip {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 8px 13px;
    border-radius: 9px;
    border: 1px solid var(--line);
    background: var(--panel);
    color: var(--text);
    cursor: pointer;
    font-family: 'Space Grotesk', system-ui, sans-serif;
    font-size: 12.5px;
    line-height: 1;
    white-space: nowrap;
    transition: border-color 150ms cubic-bezier(0.0, 0.0, 0.2, 1);
  }
  .sd-filter-chip:hover {
    border-color: var(--cyan);
  }

  .sd-filter-chip .chip-label {
    color: var(--text3);
    font-family: 'JetBrains Mono', monospace;
    font-size: 9px;
    letter-spacing: .1em;
    text-transform: uppercase;
  }

  .sd-filter-chip .chip-value {
    font-weight: 500;
  }

  .sd-filter-chip .chip-arrow {
    color: var(--text3);
    font-size: 10px;
  }

  .sd-filter-spacer {
    flex: 1;
  }

  .sd-filter-reset {
    display: flex;
    align-items: center;
    gap: 7px;
    padding: 8px 13px;
    border-radius: 9px;
    border: 1px dashed var(--line2);
    background: none;
    color: var(--text2);
    cursor: pointer;
    font-family: 'JetBrains Mono', monospace;
    font-size: 10px;
    letter-spacing: .06em;
    text-transform: uppercase;
    white-space: nowrap;
    line-height: 1;
    transition: color 150ms cubic-bezier(0.0, 0.0, 0.2, 1),
                border-color 150ms cubic-bezier(0.0, 0.0, 0.2, 1);
  }
  .sd-filter-reset:hover {
    color: var(--text);
    border-color: var(--text2);
  }

  /* ── Hide the Streamlit widgets used for actual filter input ──────────── */
  .sd-hidden-widgets {
    position: absolute;
    left: -9999px;
    width: 1px;
    height: 1px;
    overflow: hidden;
    opacity: 0;
    pointer-events: none;
  }

  /* ── Tighten Streamlit vertical gaps inside filter columns ────────────── */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) {
    gap: 0 !important;
  }
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stHorizontalBlock"] {
    gap: 0.4rem !important;
    align-items: center !important;
  }
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stVerticalBlock"] {
    gap: 0.15rem !important;
  }
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stVerticalBlock"] > div {
    padding-top: 0 !important;
    padding-bottom: 0 !important;
  }

  /* ── Hide native widget labels in filter bar ─────────────────────────── */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stWidgetLabel"] {
    display: none !important;
  }

  /* ── Compact Streamlit selectbox/multiselect inside filter bar ────────── */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stSelectbox"],
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-testid="stMultiSelect"] {
    min-height: 0 !important;
  }
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-baseweb="select"] {
    min-height: 34px !important;
    font-size: 0.75rem !important;
    border: 1px solid var(--line) !important;
    border-radius: 9px !important;
    background: var(--panel) !important;
  }
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-baseweb="select"] > div {
    min-height: 34px !important;
    padding: 0 12px !important;
    font-size: 0.75rem !important;
    border-color: var(--line) !important;
    border-radius: 9px !important;
    background: var(--panel) !important;
    font-family: 'JetBrains Mono', monospace !important;
  }
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-baseweb="select"] input {
    font-size: 0.75rem !important;
    font-family: 'JetBrains Mono', monospace !important;
  }
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) [data-baseweb="select"]:hover {
    border-color: var(--cyan) !important;
  }

  /* ── Filter bar action buttons ───────────────────────────────────────── */
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) .stButton > button {
    padding: 6px 13px !important;
    border-radius: 9px !important;
    border: 1px dashed var(--line2) !important;
    background: none !important;
    color: var(--text2) !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 10px !important;
    font-weight: 500 !important;
    letter-spacing: .06em !important;
    text-transform: uppercase !important;
    height: auto !important;
    min-height: 0 !important;
    line-height: 1 !important;
    white-space: nowrap !important;
    box-shadow: none !important;
    transition: color 150ms cubic-bezier(0.0, 0.0, 0.2, 1),
                border-color 150ms cubic-bezier(0.0, 0.0, 0.2, 1) !important;
  }
  [data-testid="stVerticalBlock"]:has(> [data-testid="stElementContainer"] .filter-strip-row) .stButton > button:hover {
    color: var(--text) !important;
    border-color: var(--text2) !important;
    background: none !important;
    box-shadow: none !important;
  }

  @media (prefers-reduced-motion: reduce) {
    .sd-filter-chip,
    .sd-filter-reset {
      transition: none !important;
    }
  }
</style>
"""


def _inject_css() -> None:
    """Inject Signal Deck filter bar CSS once per render."""
    st.markdown(_FILTER_BAR_CSS, unsafe_allow_html=True)


def _summarize_selection(selected: list[str], all_label: str, count: int | None = None) -> str:
    """Build the chip value summary text."""
    if not selected:
        suffix = f" · {count}" if count is not None else ""
        return f"All {all_label}{suffix}"
    if len(selected) == 1:
        return selected[0]
    return f"{len(selected)} selected"


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
    """Render a Signal Deck filter bar and return current selections.

    The visual bar is a pure-HTML flex row matching the design mockup.
    Actual filter selections use Streamlit widgets rendered below.
    """
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

    # ── Build the visual chip row (pure HTML) ────────────────────────────
    date_label = _DATE_PRESET_LABELS.get(
        st.session_state[k_preset], st.session_state[k_preset]
    )
    product_summary = _summarize_selection(st.session_state[k_product], "products")
    dma_summary = _summarize_selection(
        st.session_state[k_dma], "markets", count=len(_DMA_OPTIONS)
    )
    channel_summary = _summarize_selection(st.session_state[k_channel], "channels")

    # Marker for CSS scoping (used by global_filter_strip sticky positioning)
    st.markdown(
        '<div class="filter-strip-row" style="display:contents;"></div>',
        unsafe_allow_html=True,
    )

    # Build chip HTML fragments
    chips_html = ""

    if show_date:
        chips_html += (
            '<div class="sd-filter-chip">'
            '<span class="chip-label">RANGE</span>'
            f'<span class="chip-value">{date_label}</span>'
            '<span class="chip-arrow">▾</span>'
            '</div>'
        )

    if show_product:
        chips_html += (
            '<div class="sd-filter-chip">'
            '<span class="chip-label">PRODUCT</span>'
            f'<span class="chip-value">{product_summary}</span>'
            '<span class="chip-arrow">▾</span>'
            '</div>'
        )

    if show_dma:
        chips_html += (
            '<div class="sd-filter-chip">'
            '<span class="chip-label">DMA</span>'
            f'<span class="chip-value">{dma_summary}</span>'
            '<span class="chip-arrow">▾</span>'
            '</div>'
        )

    if show_channel:
        chips_html += (
            '<div class="sd-filter-chip">'
            '<span class="chip-label">CHANNEL</span>'
            f'<span class="chip-value">{channel_summary}</span>'
            '<span class="chip-arrow">▾</span>'
            '</div>'
        )

    bar_html = f"""
    <div class="sd-filter-bar">
      <span class="sd-filter-label">FILTER</span>
      {chips_html}
      <div class="sd-filter-spacer"></div>
    </div>
    """
    st.markdown(bar_html, unsafe_allow_html=True)

    # ── Streamlit widgets for actual interaction ─────────────────────────
    # These drive the session_state; the HTML bar above is the visual layer.

    # Build column layout for interactive widgets
    col_specs: list[float] = []
    if show_date:
        col_specs.append(2.0)
    if show_product:
        col_specs.append(2.0)
    if show_dma:
        col_specs.append(2.0)
    if show_channel:
        col_specs.append(2.0)
    col_specs.append(1.0)  # reset button

    cols = st.columns(col_specs)
    col_idx = 0

    # ── Date preset selector ─────────────────────────────────────────────
    if show_date:
        with cols[col_idx]:
            current_preset = st.session_state[k_preset]
            current_idx = _DATE_PRESETS.index(current_preset) if current_preset in _DATE_PRESETS else 0

            selected_preset = st.selectbox(
                label="Date Range",
                options=_DATE_PRESETS,
                index=current_idx,
                label_visibility="collapsed",
                key=f"_widget_{k_preset}",
            )

            st.session_state[k_preset] = selected_preset

            if selected_preset == "Last 30 days":
                st.session_state[k_start] = anchor - datetime.timedelta(days=30)
                st.session_state[k_end] = anchor
            elif selected_preset == "Last 60 days":
                st.session_state[k_start] = anchor - datetime.timedelta(days=60)
                st.session_state[k_end] = anchor
            elif selected_preset == "Last 90 days":
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

    # ── Product selector ─────────────────────────────────────────────────
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

    # ── DMA selector ─────────────────────────────────────────────────────
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

    # ── Channel selector ─────────────────────────────────────────────────
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

    # ── Reset button ─────────────────────────────────────────────────────
    with cols[col_idx]:
        if st.button("↺ RESET", key=f"_btn_reset_{key_prefix}", use_container_width=True):
            st.rerun()

    # ── Build result ─────────────────────────────────────────────────────
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
