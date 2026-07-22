"""
Apex — RVGT Marketing Intelligence Platform
Entry point: streamlit run app.py
"""

import datetime

import streamlit as st

from src.config.brand import apply_brand, COLORS, TYPOGRAPHY, BORDER_RADIUS, MOTION, inject_brand_css
from src.config.settings import APP_NAME, APP_VERSION, APP_DESCRIPTION, PAGES
from src.state import init_state
from src.components.global_filter_strip import render_global_filters
from src.components.app_chrome import (
    inject_chrome_css,
    render_sidebar_branding,
    render_sidebar_collapse_label,
    render_agent_console,
)

# ---------------------------------------------------------------------------
# Brand (must be first st call)
# ---------------------------------------------------------------------------

apply_brand(
    st,
    page_title="Apex | RVGT Marketing Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Session state initialisation
# ---------------------------------------------------------------------------

init_state()

# ---------------------------------------------------------------------------
# Shared chrome — sidebar branding, icon tiles, agent console CSS
# ---------------------------------------------------------------------------

inject_chrome_css()

# Sidebar branding (APEX logo + wordmark above nav) + collapse label at bottom
with st.sidebar:
    render_sidebar_branding()
    render_sidebar_collapse_label()

# ---------------------------------------------------------------------------
# Persistent global filter bar — renders above all pages
# ---------------------------------------------------------------------------

render_global_filters()

# ---------------------------------------------------------------------------
# Multi-page navigation via st.navigation()
# ---------------------------------------------------------------------------

_PAGE_FILES = [
    "src/pages/1_Executive_Scorecard.py",
    "src/pages/2_Spend_Allocation.py",
    "src/pages/3_Brand_Media.py",
    "src/pages/4_Performance_Media.py",
    "src/pages/5_SEO.py",
    "src/pages/6_Organic_AEO.py",
    "src/pages/3_Acquisition_Funnel.py",
    "src/pages/7_Product_Experience.py",
    "src/pages/8_Operations_Command.py",
    "src/pages/10_Retention_Forecast.py",
    "src/pages/12_Brand_Awareness.py",
    "src/pages/11_Settings.py",
]

# Build st.Page objects from the registry + file list (zipped by position)
_pages = [
    st.Page(
        path,
        title=meta["title"],
        icon=meta["icon"],
    )
    for path, meta in zip(_PAGE_FILES, PAGES)
]

nav = st.navigation(_pages)

# ---------------------------------------------------------------------------
# Run selected page
# ---------------------------------------------------------------------------
# NOTE: st.navigation() owns the sidebar in Streamlit 1.57+.
# Global filter bar is rendered above (persistent across all pages).
# Chat drawer is rendered inside each page: src/components/chat_drawer.py

nav.run()

# ---------------------------------------------------------------------------
# Agent console — persistent bottom command bar
# ---------------------------------------------------------------------------

render_agent_console()
