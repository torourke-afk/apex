"""
tests/test_state_contracts.py — Integration tests for APE-140 cross-page state contracts.

Each test exercises a full producer→consumer round-trip through the state registry,
mirroring the real page code without importing Streamlit pages (which have top-level
side-effects).  st.session_state is mocked as a plain dict, matching the pattern
established in tests/test_state.py.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Fixture — shared mock session_state for every test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_streamlit():
    """Patch streamlit in the state module so session_state is a plain dict."""
    store: dict = {}
    with patch("src.state.st") as mock_st:
        mock_st.session_state = store
        yield mock_st, store


# ---------------------------------------------------------------------------
# Contract 1: Simulator Scenarios → Scorecard + Spend Allocation
#
# Producer  : Module 9 (Simulator) calls set_global("scenarios", [...])
# Consumers : Module 1 (Scorecard) reads get_global("scenarios")
#             Module 2 (Spend Allocation) reads get_global("scenarios")
# ---------------------------------------------------------------------------


class TestContract1SimulatorScenarios:
    """Scenarios saved in Simulator are visible in Scorecard and Spend Allocation."""

    def test_scenario_written_by_simulator_readable_by_scorecard(self, patch_streamlit):
        from src.state import init_state, set_global, get_global

        _, store = patch_streamlit
        init_state()

        # Simulator produces a scenario list
        scenarios = [
            {"name": "Q3 Aggressive", "budget": {"paid_search": 50_000, "display": 20_000}},
            {"name": "Q3 Conservative", "budget": {"paid_search": 30_000, "display": 10_000}},
        ]
        set_global("scenarios", scenarios)

        # Scorecard consumer reads the same list
        result = get_global("scenarios")
        assert result == scenarios, "Scorecard did not receive scenarios written by Simulator"

    def test_scenario_written_by_simulator_readable_by_spend_allocation(self, patch_streamlit):
        from src.state import init_state, set_global, get_global

        _, store = patch_streamlit
        init_state()

        scenarios = [{"name": "Base Case", "budget": {"paid_search": 40_000}}]
        set_global("scenarios", scenarios)

        # Spend Allocation consumer reads and picks the latest (last) scenario
        all_scenarios = get_global("scenarios")
        assert all_scenarios, "Spend Allocation received an empty scenarios list"
        latest = all_scenarios[-1]
        assert latest["budget"]["paid_search"] == 40_000

    def test_key_stored_with_global_prefix(self, patch_streamlit):
        """Confirm raw key in session_state has the global_ prefix."""
        from src.state import init_state, set_global

        _, store = patch_streamlit
        init_state()

        set_global("scenarios", [{"name": "Test"}])
        assert "global_scenarios" in store, "global_scenarios key missing from session_state"


# ---------------------------------------------------------------------------
# Contract 2: Scorecard Alert Acknowledgments Persist
#
# Producer  : Module 1 (Scorecard) calls set_module("scorecard", "acknowledged_alerts", [...])
# Contract  : Value must survive a simulated navigation-away-and-back cycle
#             (i.e. reading the same session_state without re-initialising it)
# ---------------------------------------------------------------------------


class TestContract2AlertAcknowledgments:
    """Alert acknowledgments written by Scorecard persist across navigation."""

    def test_acknowledged_alerts_survive_navigation(self, patch_streamlit):
        from src.state import init_state, set_module, get_module

        _, store = patch_streamlit
        init_state()

        # User acknowledges two alerts on the Scorecard page
        acked = ["alert_001", "alert_002"]
        set_module("scorecard", "acknowledged_alerts", acked)

        # Simulate navigation away — session_state is not cleared
        # (no re-init; store persists)

        # Navigate back — read the acked set
        result = get_module("scorecard", "acknowledged_alerts")
        assert result == acked, "Acknowledged alerts were lost after navigation"

    def test_incremental_acknowledgment_accumulates(self, patch_streamlit):
        from src.state import init_state, set_module, get_module

        _, store = patch_streamlit
        init_state()

        set_module("scorecard", "acknowledged_alerts", ["alert_001"])

        # User acknowledges a second alert without clearing the first
        current = get_module("scorecard", "acknowledged_alerts") or []
        current = list(current)
        current.append("alert_002")
        set_module("scorecard", "acknowledged_alerts", current)

        result = get_module("scorecard", "acknowledged_alerts")
        assert "alert_001" in result
        assert "alert_002" in result

    def test_key_stored_with_scorecard_prefix(self, patch_streamlit):
        from src.state import init_state, set_module

        _, store = patch_streamlit
        init_state()

        set_module("scorecard", "acknowledged_alerts", ["alert_x"])
        assert "scorecard_acknowledged_alerts" in store


# ---------------------------------------------------------------------------
# Contract 3: DMA Filter Carry-Over (bidirectional)
#
# Direction A: Module 3 (Funnel) filter_bar() writes → Module 4 (Onboarding) reads
# Direction B: Module 4 can update the filter; Module 3 reads the updated value
# ---------------------------------------------------------------------------


class TestContract3DmaFilterCarryOver:
    """DMA filter written by Funnel is applied as default in Onboarding (and vice-versa)."""

    def test_funnel_writes_dma_filter_onboarding_reads(self, patch_streamlit):
        from src.state import init_state, set_global, get_global

        _, store = patch_streamlit
        init_state()

        # Funnel filter_bar writes the DMA filter
        dma_selection = ["TX", "CA", "FL"]
        set_global("dma_filter", dma_selection)

        # Onboarding reads it as the default
        result = get_global("dma_filter")
        assert result == dma_selection, "Onboarding did not receive DMA filter set by Funnel"

    def test_onboarding_updates_dma_filter_funnel_reads(self, patch_streamlit):
        from src.state import init_state, set_global, get_global

        _, store = patch_streamlit
        init_state()

        # Funnel sets an initial filter
        set_global("dma_filter", ["TX"])

        # Onboarding narrows or changes the filter (bidirectional)
        set_global("dma_filter", ["TX", "NY"])

        # Funnel re-reads after Onboarding update
        result = get_global("dma_filter")
        assert result == ["TX", "NY"], "Funnel did not see the DMA filter update from Onboarding"

    def test_dma_filter_key_stored_with_global_prefix(self, patch_streamlit):
        from src.state import init_state, set_global

        _, store = patch_streamlit
        init_state()

        set_global("dma_filter", ["GA"])
        assert "global_dma_filter" in store


# ---------------------------------------------------------------------------
# Contract 4: Spend Allocation → Scorecard Financial Strip
#
# Producer  : Module 2 (Spend Allocation) writes spend_current_budget (channel → amount)
# Consumer  : Module 1 (Scorecard) financial strip reads live budget figures
# ---------------------------------------------------------------------------


class TestContract4SpendToScorecardFinancialStrip:
    """Budget dict written by Spend Allocation is read by Scorecard financial strip."""

    def test_spend_budget_readable_by_scorecard(self, patch_streamlit):
        from src.state import init_state, set_module, get_module

        _, store = patch_streamlit
        init_state()

        # Spend Allocation writes the current budget
        budget = {
            "paid_search": 45_000,
            "display": 15_000,
            "social": 20_000,
            "email": 5_000,
        }
        set_module("spend", "current_budget", budget)

        # Scorecard financial strip reads it
        result = get_module("spend", "current_budget")
        assert result == budget, "Scorecard financial strip did not receive budget from Spend Allocation"

    def test_budget_update_reflected_immediately(self, patch_streamlit):
        """A budget change in Spend Allocation is immediately visible to Scorecard."""
        from src.state import init_state, set_module, get_module

        _, store = patch_streamlit
        init_state()

        set_module("spend", "current_budget", {"paid_search": 40_000})

        # User adjusts a slider — Spend Allocation writes an updated dict
        set_module("spend", "current_budget", {"paid_search": 55_000, "display": 10_000})

        result = get_module("spend", "current_budget")
        assert result["paid_search"] == 55_000
        assert result["display"] == 10_000

    def test_total_budget_calculation_from_registry(self, patch_streamlit):
        """Consumer can derive a total from the channel dict without raw session_state access."""
        from src.state import init_state, set_module, get_module

        _, store = patch_streamlit
        init_state()

        budget = {"paid_search": 50_000, "display": 20_000, "social": 30_000}
        set_module("spend", "current_budget", budget)

        retrieved = get_module("spend", "current_budget")
        total = sum(retrieved.values())
        assert total == 100_000

    def test_key_stored_with_spend_prefix(self, patch_streamlit):
        from src.state import init_state, set_module

        _, store = patch_streamlit
        init_state()

        set_module("spend", "current_budget", {"email": 5_000})
        assert "spend_current_budget" in store
