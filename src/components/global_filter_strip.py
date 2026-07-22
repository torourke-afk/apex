"""
Global filter strip — Signal Deck Design System
------------------------------------------------
Renders a persistent sticky filter bar at the top of each page.
Call ``render_global_filters()`` once in app.py before nav.run().
The filter values are stored in ``st.session_state["global_filter_*"]`` keys
and read by ``get_global_filters()``.

Styling follows the Signal Deck reference mockup: the filter bar sits below
the context bar as a full-width flex row with --bg2 background and a
1px --line border-bottom.  Sticky positioning is achieved via CSS targeting
the stLayoutWrapper that contains the .sticky-filter-marker div.
"""

import streamlit as st

from src.components.filter_bar import filter_bar as _render_filter_bar

# ---------------------------------------------------------------------------
# Signal Deck sticky strip CSS
# ---------------------------------------------------------------------------

_STRIP_CSS = """
<style>
  /* ── Remove Streamlit header ─────────────────────────────────────────── */
  header[data-testid="stHeader"] {
    display: none !important;
  }
  .stApp,
  [data-testid="stAppViewContainer"],
  section.main {
    padding-top: 0 !important;
  }

  /* ── Prevent horizontal scrollbar ───────────────────────────────────── */
  body {
    overflow-x: clip !important;
  }

  /* ── Content padding clears the fixed bar ───────────────────────────── */
  .block-container {
    max-width: 100% !important;
    padding-top: 4rem !important;
  }

  /* ── Fixed filter bar — pinned to top of content area ───────────────── */
  /* Uses Signal Deck tokens: --bg2 background, --line border */
  [data-testid="stLayoutWrapper"]:has(.sticky-filter-marker) {
    position: fixed !important;
    top: 0 !important;
    left: 260px !important;
    width: calc(100vw - 260px) !important;
    z-index: 999 !important;
    background: var(--bg2) !important;
    border-bottom: 1px solid var(--line) !important;
    padding: 0 !important;
    box-sizing: border-box !important;
  }

  /* ── Collapsed sidebar: shift left edge to match 64px rail ──────────── */
  .stApp:has(section[data-testid="stSidebar"][aria-expanded="false"]) [data-testid="stLayoutWrapper"]:has(.sticky-filter-marker) {
    left: 64px !important;
    width: calc(100vw - 64px) !important;
  }
</style>
"""


def render_global_filters() -> dict:
    """Render the global filter bar as a persistent sticky strip.

    Returns the filter dict (same shape as ``get_global_filters()``).
    """
    st.markdown(_STRIP_CSS, unsafe_allow_html=True)

    with st.container():
        # Hidden marker -- CSS :has(.sticky-filter-marker) scopes sticky styles
        # to exactly this container's stLayoutWrapper.
        st.markdown(
            '<div class="sticky-filter-marker" style="display:none;"></div>',
            unsafe_allow_html=True,
        )
        filters = _render_filter_bar(key_prefix="global")

    # Persist to session state for pages that call get_global_filters()
    st.session_state["global_filter_date_preset"] = filters["date_preset"]
    st.session_state["global_filter_date_start"] = filters["date_start"]
    st.session_state["global_filter_date_end"] = filters["date_end"]
    st.session_state["global_filter_dma"] = filters["dma"]
    st.session_state["global_filter_channel"] = filters["channel"]
    st.session_state["global_filter_product"] = filters["product"]
    st.session_state["global_filter_compare"] = filters["compare"]
    st.session_state["global_filter_prior_start"] = filters.get("prior_start")
    st.session_state["global_filter_prior_end"] = filters.get("prior_end")

    return filters
