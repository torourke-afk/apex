"""
tests/test_cross_page_state.py — Integration tests for APE-141 cross-page state contracts.

Verifies the four cross-page state contracts plus idempotency and navigation-preservation
requirements. Each test exercises a full producer→consumer round-trip through the state
registry without importing Streamlit pages.

Contracts under test:
  1. Simulator → Scorecard: save scenario → read back match
  2. Scorecard alert acknowledgment → re-read feed → alert filtered out
  3. DMA filter in Funnel → read from Onboarding → values match
  4. Budget in Spend Allocation → Scorecard strip → values match
  5. init_state() idempotency — call twice, no data loss
  6. Navigate away/back simulation — state preserved
"""

from __future__ import annotations

import os
import sys
import types

# ── Path setup ────────────────────────────────────────────────────────────────

EXECUTOR_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__),
                 "../../26aa10f0-519d-418d-a1cc-d66c6319f47d")
)
if EXECUTOR_ROOT not in sys.path:
    sys.path.insert(0, EXECUTOR_ROOT)

# Minimal Streamlit stub — session_state must be patchable per-test
_st_mod = types.ModuleType("streamlit")
_st_mod.session_state = {}
sys.modules["streamlit"] = _st_mod

import pytest
from unittest.mock import patch


# ---------------------------------------------------------------------------
# Shared fixture — fresh isolated session_state for every test
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def fresh_state():
    """Provide a clean dict as session_state for every test."""
    store: dict = {}
    with patch("src.state.st") as mock_st:
        mock_st.session_state = store
        yield mock_st, store


# ---------------------------------------------------------------------------
# Contract 1: Simulator → Scorecard
#
# Producer  : Simulator writes simulator_active_scenario + set_global("scenarios", [...])
# Consumer  : Scorecard reads get_global("scenarios") and verifies round-trip
# ---------------------------------------------------------------------------


class TestContract1SimulatorToScorecard:
    """Scenario saved in Simulator state is readable by Scorecard."""

    def test_scenario_round_trip(self, fresh_state):
        from src.state import init_state, set_global, get_global

        _, store = fresh_state
        init_state()

        scenario = {
            "name": "Q3 Aggressive",
            "budget": {"paid_search": 50_000, "display": 20_000},
            "projected_leads": 4_200,
        }
        # Simulator writes
        set_global("scenarios", [scenario])

        # Scorecard reads
        result = get_global("scenarios")
        assert result == [scenario], "Scorecard did not receive the scenario written by Simulator"

    def test_simulator_active_scenario_key_present(self, fresh_state):
        """simulator_active_scenario key is initialized and writable."""
        from src.state import init_state, get_module, set_module

        _, store = fresh_state
        init_state()

        set_module("simulator", "active_scenario", {"name": "Base"})
        assert get_module("simulator", "active_scenario") == {"name": "Base"}

    def test_multiple_scenarios_preserved(self, fresh_state):
        from src.state import init_state, set_global, get_global

        _, store = fresh_state
        init_state()

        scenarios = [
            {"name": "Conservative", "budget": {"paid_search": 30_000}},
            {"name": "Aggressive", "budget": {"paid_search": 60_000}},
        ]
        set_global("scenarios", scenarios)

        retrieved = get_global("scenarios")
        assert len(retrieved) == 2
        assert retrieved[1]["name"] == "Aggressive"

    def test_global_scenarios_key_stored_with_prefix(self, fresh_state):
        from src.state import init_state, set_global

        _, store = fresh_state
        init_state()

        set_global("scenarios", [{"name": "Test"}])
        assert "global_scenarios" in store


# ---------------------------------------------------------------------------
# Contract 2: Scorecard alert acknowledgment → feed re-read → alert absent
#
# Producer  : Scorecard sets scorecard_acknowledged_alerts
# Consumer  : Alert feed filters out acknowledged IDs before display
# ---------------------------------------------------------------------------


class TestContract2AlertAcknowledgmentFiltering:
    """An acknowledged alert is absent from the feed when re-read."""

    def test_acknowledged_alert_not_in_unacked_list(self, fresh_state):
        from src.state import init_state, set_module, get_module

        _, store = fresh_state
        init_state()

        # Simulate feed of 3 alerts
        feed = ["alert_cpl_high", "alert_cer_low", "alert_retention_drop"]

        # User acknowledges the first alert
        set_module("scorecard", "acknowledged_alerts", ["alert_cpl_high"])

        # Consumer computes unacknowledged set
        acked = get_module("scorecard", "acknowledged_alerts") or []
        unacked = [a for a in feed if a not in acked]

        assert "alert_cpl_high" not in unacked
        assert "alert_cer_low" in unacked
        assert "alert_retention_drop" in unacked

    def test_incremental_acknowledgment_accumulates(self, fresh_state):
        from src.state import init_state, set_module, get_module

        _, store = fresh_state
        init_state()

        set_module("scorecard", "acknowledged_alerts", ["alert_001"])

        current = list(get_module("scorecard", "acknowledged_alerts") or [])
        current.append("alert_002")
        set_module("scorecard", "acknowledged_alerts", current)

        result = get_module("scorecard", "acknowledged_alerts")
        assert "alert_001" in result
        assert "alert_002" in result

    def test_acknowledged_alerts_survive_navigation(self, fresh_state):
        """Acked set is preserved without calling init_state a second time."""
        from src.state import init_state, set_module, get_module

        _, store = fresh_state
        init_state()

        set_module("scorecard", "acknowledged_alerts", ["alert_nav_test"])

        # Simulate navigation away — no re-init; store persists in real Streamlit
        result = get_module("scorecard", "acknowledged_alerts")
        assert result == ["alert_nav_test"]

    def test_key_stored_with_scorecard_prefix(self, fresh_state):
        from src.state import init_state, set_module

        _, store = fresh_state
        init_state()

        set_module("scorecard", "acknowledged_alerts", ["x"])
        assert "scorecard_acknowledged_alerts" in store


# ---------------------------------------------------------------------------
# Contract 3: DMA filter in Funnel → read from Onboarding → values match
#
# Producer  : Funnel filter_bar() writes global_dma_filter
# Consumer  : Onboarding reads global_dma_filter as default selection
# ---------------------------------------------------------------------------


class TestContract3DmaFunnelToOnboarding:
    """DMA filter set in Funnel is visible as the default in Onboarding."""

    def test_funnel_writes_onboarding_reads(self, fresh_state):
        from src.state import init_state, set_global, get_global

        _, store = fresh_state
        init_state()

        dma = ["TX", "CA", "FL"]
        set_global("dma_filter", dma)

        result = get_global("dma_filter")
        assert result == dma, "Onboarding did not receive DMA filter set by Funnel"

    def test_onboarding_update_visible_to_funnel(self, fresh_state):
        """Bidirectional: Onboarding update is picked up by Funnel."""
        from src.state import init_state, set_global, get_global

        _, store = fresh_state
        init_state()

        set_global("dma_filter", ["TX"])
        set_global("dma_filter", ["TX", "NY"])

        result = get_global("dma_filter")
        assert result == ["TX", "NY"]

    def test_empty_dma_filter_initializes_as_list(self, fresh_state):
        from src.state import init_state, get_global

        _, store = fresh_state
        init_state()

        result = get_global("dma_filter")
        assert isinstance(result, list)

    def test_dma_filter_key_stored_with_global_prefix(self, fresh_state):
        from src.state import init_state, set_global

        _, store = fresh_state
        init_state()

        set_global("dma_filter", ["GA"])
        assert "global_dma_filter" in store


# ---------------------------------------------------------------------------
# Contract 4: Budget in Spend Allocation → Scorecard financial strip
#
# Producer  : Spend Allocation writes spend_current_budget
# Consumer  : Scorecard financial strip reads live budget figures
# ---------------------------------------------------------------------------


class TestContract4SpendToScorecardStrip:
    """Budget dict written by Spend Allocation is read by Scorecard financial strip."""

    def test_budget_round_trip(self, fresh_state):
        from src.state import init_state, set_module, get_module

        _, store = fresh_state
        init_state()

        budget = {
            "paid_search": 45_000,
            "display": 15_000,
            "social": 20_000,
            "email": 5_000,
        }
        set_module("spend", "current_budget", budget)

        result = get_module("spend", "current_budget")
        assert result == budget

    def test_budget_update_reflected_immediately(self, fresh_state):
        from src.state import init_state, set_module, get_module

        _, store = fresh_state
        init_state()

        set_module("spend", "current_budget", {"paid_search": 40_000})
        set_module("spend", "current_budget", {"paid_search": 55_000, "display": 10_000})

        result = get_module("spend", "current_budget")
        assert result["paid_search"] == 55_000
        assert result["display"] == 10_000

    def test_scorecard_strip_total_calculation(self, fresh_state):
        """Consumer derives total spend from channel dict without raw session_state access."""
        from src.state import init_state, set_module, get_module

        _, store = fresh_state
        init_state()

        budget = {"paid_search": 50_000, "display": 20_000, "social": 30_000}
        set_module("spend", "current_budget", budget)

        retrieved = get_module("spend", "current_budget")
        assert sum(retrieved.values()) == 100_000

    def test_key_stored_with_spend_prefix(self, fresh_state):
        from src.state import init_state, set_module

        _, store = fresh_state
        init_state()

        set_module("spend", "current_budget", {"email": 5_000})
        assert "spend_current_budget" in store


# ---------------------------------------------------------------------------
# Contract 5: init_state() idempotency
#
# Calling init_state() twice must not overwrite already-set values.
# ---------------------------------------------------------------------------


class TestInitStateIdempotency:
    """init_state() called twice does not reset values set between calls."""

    def test_double_init_preserves_written_values(self, fresh_state):
        from src.state import init_state, set_global, get_global

        _, store = fresh_state
        init_state()

        # Set a value after first init
        set_global("dma_filter", ["TX", "FL"])

        # Second init must not reset it
        init_state()

        result = get_global("dma_filter")
        assert result == ["TX", "FL"], (
            "init_state() reset global_dma_filter on second call"
        )

    def test_double_init_preserves_all_registered_values(self, fresh_state):
        from src.state import init_state, set_module, get_module

        _, store = fresh_state
        init_state()

        set_module("scorecard", "comparison_period", "prior_year")
        set_module("spend", "budget_view", "quarterly")
        set_module("simulator", "running", True)

        init_state()

        assert get_module("scorecard", "comparison_period") == "prior_year"
        assert get_module("spend", "budget_view") == "quarterly"
        assert get_module("simulator", "running") is True

    def test_double_init_all_keys_present(self, fresh_state):
        from src.state import init_state, STATE_KEYS

        _, store = fresh_state
        init_state()
        init_state()

        for key in STATE_KEYS:
            assert key in store, f"Key {key!r} missing from session_state after double init"

    def test_mutable_defaults_are_independent_copies(self, fresh_state):
        """Two calls to init_state() should not share mutable default references."""
        from src.state import init_state, STATE_KEYS

        _, store1 = fresh_state
        init_state()

        list_keys = [k for k, v in STATE_KEYS.items() if v["type"] is list]
        assert list_keys, "Expected at least one list-typed key in STATE_KEYS"

        key = list_keys[0]
        store1[key].append("sentinel_value")
        # Defaults in STATE_KEYS should not be mutated
        assert "sentinel_value" not in STATE_KEYS[key]["default"], (
            f"Mutation of store[{key!r}] leaked into STATE_KEYS default"
        )


# ---------------------------------------------------------------------------
# Contract 6: Navigate away / back — state preserved
#
# Simulates a user navigating from Page A → Page B → back to Page A.
# Session state must be fully intact; no re-initialisation clears values.
# ---------------------------------------------------------------------------


class TestNavigationStatePreservation:
    """Session state is preserved across simulated page navigation."""

    def test_state_survives_page_change(self, fresh_state):
        from src.state import init_state, set_global, set_module, get_global, get_module

        _, store = fresh_state
        init_state()

        # Page A (Funnel) sets DMA filter
        set_global("dma_filter", ["TX", "CA"])
        # Page A (Scorecard) acknowledges an alert
        set_module("scorecard", "acknowledged_alerts", ["alert_abc"])
        # Page A (Simulator) saves a scenario
        set_global("scenarios", [{"name": "Q4 Plan", "budget": {}}])

        # ── "Navigate" to another page ─────────────────────────────────────
        # In Streamlit, navigation does NOT clear session_state.
        # We simulate by reading without calling init_state() again.
        # ──────────────────────────────────────────────────────────────────

        assert get_global("dma_filter") == ["TX", "CA"]
        assert get_module("scorecard", "acknowledged_alerts") == ["alert_abc"]
        assert get_global("scenarios")[0]["name"] == "Q4 Plan"

    def test_init_state_on_new_page_does_not_clear_existing(self, fresh_state):
        """A new page calling init_state() as part of its boot must not clear prior data."""
        from src.state import init_state, set_module, get_module

        _, store = fresh_state
        init_state()  # Page A boot

        set_module("spend", "current_budget", {"paid_search": 40_000})

        init_state()  # Page B boot — idempotent; must leave budget intact

        budget = get_module("spend", "current_budget")
        assert budget == {"paid_search": 40_000}, (
            "Page B's init_state() cleared Spend Allocation's budget"
        )

    def test_global_current_page_tracks_navigation(self, fresh_state):
        """global_current_page can be updated to track the active page."""
        from src.state import init_state, set_global, get_global

        _, store = fresh_state
        init_state()

        set_global("current_page", "executive_scorecard")
        assert get_global("current_page") == "executive_scorecard"

        set_global("current_page", "spend_allocation")
        assert get_global("current_page") == "spend_allocation"

    def test_module_state_isolated_across_pages(self, fresh_state):
        """Different module namespaces do not interfere with each other."""
        from src.state import init_state, set_module, get_module

        _, store = fresh_state
        init_state()

        set_module("funnel", "stage_filter", ["awareness", "consideration"])
        set_module("onboarding", "step", 3)

        # Funnel state unaffected by onboarding writes
        assert get_module("funnel", "stage_filter") == ["awareness", "consideration"]
        assert get_module("onboarding", "step") == 3
