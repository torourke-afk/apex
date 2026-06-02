"""
QA tests for APE-139 — Navigation Polish & Sidebar

Verifies:
  - PAGES registry completeness and schema
  - new STATE_KEYS (global_current_page, global_alert_context)
  - _KPI_PAGE_MAP coverage on known KPIs
  - brand.py active-nav CSS selector present
"""

from __future__ import annotations

import os
import sys
import types

# ── Path setup ────────────────────────────────────────────────────────────────

EXECUTOR_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..")
)
if EXECUTOR_ROOT not in sys.path:
    sys.path.insert(0, EXECUTOR_ROOT)

# Minimal Streamlit stub (no live session needed)
_st_stub = types.ModuleType("streamlit")
_st_stub.session_state = {}

def _noop(*a, **kw): pass
_st_stub.set_page_config = _noop
_st_stub.markdown = _noop
sys.modules.setdefault("streamlit", _st_stub)

# ── Imports ───────────────────────────────────────────────────────────────────

import pytest

from src.config.settings import PAGES
from src.config.brand import COLORS, _brand_css
from src.state import STATE_KEYS


# ── PAGES registry ────────────────────────────────────────────────────────────

class TestPagesRegistry:
    EXPECTED_MODULES = [
        ("executive_scorecard", "📊", "Executive Scorecard"),
        ("spend_allocation",    "💰", "Spend Allocation"),
        ("acquisition_funnel",  "🔻", "Acquisition Funnel"),
        ("onboarding_retention","🤝", "Onboarding & Retention"),
        ("paid_channels",       "📢", "Paid Channels"),
        ("organic_aeo",         "🔍", "Organic & AEO"),
        ("product_experience",  "🚀", "Product & Experience"),
        ("operations_command",  "⚙️",  "Operations Command"),
        ("simulator",           "🧪", "Full-Funnel Simulator"),
    ]

    def test_exactly_9_pages(self):
        assert len(PAGES) == 9, f"Expected 9 pages, got {len(PAGES)}"

    @pytest.mark.parametrize("idx,expected", enumerate(EXPECTED_MODULES))
    def test_page_order_and_identity(self, idx, expected):
        page_id, icon, title = expected
        page = PAGES[idx]
        assert page["id"] == page_id, f"PAGES[{idx}] id mismatch"
        assert page["icon"] == icon, f"PAGES[{idx}] icon mismatch"
        assert page["title"] == title, f"PAGES[{idx}] title mismatch"

    def test_all_pages_have_description(self):
        for page in PAGES:
            desc = page.get("description", "")
            assert desc, f"Page '{page['id']}' has no description"
            assert len(desc) >= 20, f"Page '{page['id']}' description too short: {desc!r}"

    def test_no_duplicate_ids(self):
        ids = [p["id"] for p in PAGES]
        assert len(ids) == len(set(ids)), "Duplicate page IDs in PAGES"

    def test_no_duplicate_icons(self):
        icons = [p["icon"] for p in PAGES]
        assert len(icons) == len(set(icons)), "Duplicate icons in PAGES"


# ── STATE_KEYS — APE-139 new keys ─────────────────────────────────────────────

class TestStateKeysAPE139:
    def test_global_current_page_registered(self):
        assert "global_current_page" in STATE_KEYS, (
            "global_current_page missing from STATE_KEYS registry"
        )

    def test_global_alert_context_registered(self):
        assert "global_alert_context" in STATE_KEYS, (
            "global_alert_context missing from STATE_KEYS registry"
        )

    def test_global_current_page_defaults_to_none(self):
        assert STATE_KEYS["global_current_page"]["default"] is None

    def test_global_alert_context_defaults_to_none(self):
        assert STATE_KEYS["global_alert_context"]["default"] is None

    def test_global_current_page_owned_by_global_ns(self):
        assert STATE_KEYS["global_current_page"]["owner"] == "global_"

    def test_global_alert_context_owned_by_global_ns(self):
        assert STATE_KEYS["global_alert_context"]["owner"] == "global_"


# ── brand.py — active nav CSS ─────────────────────────────────────────────────

class TestActiveNavCSS:
    def test_sidebar_nav_link_selector_present(self):
        css = _brand_css()
        assert 'stSidebarNavLink' in css, (
            "brand.py CSS missing stSidebarNavLink selector for active-page highlight"
        )

    def test_active_nav_uses_rvgt_red(self):
        css = _brand_css()
        red = COLORS["primary"]  # #FF0016
        assert red in css, (
            f"Active nav highlight must reference COLORS['primary'] ({red})"
        )

    def test_active_nav_has_border_left(self):
        css = _brand_css()
        assert "border-left" in css, (
            "Active nav CSS should include a left-border accent"
        )

    def test_active_nav_aria_current_page(self):
        css = _brand_css()
        assert 'aria-current="page"' in css, (
            "Active nav CSS should target aria-current='page' attribute"
        )


# ── KPI page map spot-check (via importing scorecard module vars) ──────────────

class TestKPIPageMap:
    """Import _KPI_PAGE_MAP from the scorecard page and verify key mappings."""

    @pytest.fixture(scope="class", autouse=True)
    def import_map(self):
        """
        The scorecard page calls apply_brand/init_state at import time.
        Stub them out so we can extract _KPI_PAGE_MAP without a live session.
        """
        import importlib

        # Stub out apply_brand so set_page_config isn't called
        brand_mod = sys.modules.get("src.config.brand")
        if brand_mod:
            brand_mod.apply_brand = lambda *a, **kw: None

        # Stub out data queries to avoid DB dependency
        stub_queries = types.ModuleType("src.data.scorecard_queries")
        stub_queries.get_kpi_summary = lambda: []
        stub_queries.get_financial_summary = lambda: []
        stub_queries.get_recent_alerts = lambda **kw: []
        sys.modules["src.data.scorecard_queries"] = stub_queries

        # Stub out components
        for mod_name in [
            "src.components",
            "src.components.alert_badge",
        ]:
            if mod_name not in sys.modules:
                stub = types.ModuleType(mod_name)
                stub.kpi_card = _noop
                stub.metric_strip = _noop
                stub.section_header = _noop
                stub.badge_html = lambda **kw: ""
                sys.modules[mod_name] = stub

        # Prevent re-execution of st.set_page_config
        _st_stub.set_page_config = _noop

        # Re-import with stubs
        if "src.pages.1_Executive_Scorecard" in sys.modules:
            del sys.modules["src.pages.1_Executive_Scorecard"]

        # We can't cleanly exec the page module (top-level st calls), so
        # validate the map by reading the source directly.
        scorecard_path = os.path.join(
            EXECUTOR_ROOT, "src/pages/1_Executive_Scorecard.py"
        )
        self.__class__._scorecard_src = open(scorecard_path).read()

    def test_kpi_page_map_defined(self):
        assert "_KPI_PAGE_MAP" in self._scorecard_src

    def test_kpi_page_map_covers_all_known_kpis(self):
        known_kpis = [
            "App Completion Rate",
            "Brand Capture Rate",
            "CPIHH",
            "LLM Visibility Score",
            "MOB6 Retention Rate",
            "Total Media Spend",
        ]
        for kpi in known_kpis:
            assert kpi in self._scorecard_src, (
                f"_KPI_PAGE_MAP missing entry for KPI: {kpi!r}"
            )

    def test_view_details_sets_alert_context(self):
        assert "alert_context" in self._scorecard_src, (
            "Scorecard must write global_alert_context before st.switch_page()"
        )

    def test_switch_page_used_for_deep_link(self):
        assert "st.switch_page" in self._scorecard_src, (
            "Scorecard must use st.switch_page() for alert deep links"
        )

    def test_deep_link_writes_context_before_switch(self):
        """Context write must appear before st.switch_page in source order."""
        ctx_idx = self._scorecard_src.find("global_alert_context")
        switch_idx = self._scorecard_src.find("st.switch_page")
        assert ctx_idx < switch_idx, (
            "global_alert_context must be set before st.switch_page() is called"
        )
