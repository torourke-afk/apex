"""
tests/test_state.py — Unit tests for src/state/__init__.py
"""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers — mock st.session_state as a plain dict for all tests
# ---------------------------------------------------------------------------


def make_mock_st(initial: dict | None = None) -> MagicMock:
    """Return a mock streamlit module whose session_state behaves like a dict."""
    mock_st = MagicMock()
    store: dict = dict(initial or {})

    # Proxy attribute access to the underlying dict
    mock_st.session_state = store
    return mock_st, store


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def patch_streamlit():
    """Patch streamlit in the state module for every test."""
    store: dict = {}
    with patch("src.state.st") as mock_st:
        mock_st.session_state = store
        yield mock_st, store


# ---------------------------------------------------------------------------
# init_state — basic initialisation
# ---------------------------------------------------------------------------


class TestInitState:
    def test_all_keys_initialised(self, patch_streamlit):
        from src.state import init_state, STATE_KEYS

        mock_st, store = patch_streamlit
        init_state()

        for key in STATE_KEYS:
            assert key in store, f"Key '{key}' was not initialised by init_state()"

    def test_idempotent_does_not_overwrite(self, patch_streamlit):
        """Calling init_state() twice must not overwrite already-set keys."""
        from src.state import init_state

        mock_st, store = patch_streamlit
        init_state()

        # Mutate a key after first init
        store["global_date_range"] = "2024-01-01:2024-12-31"

        init_state()  # second call

        assert store["global_date_range"] == "2024-01-01:2024-12-31"

    def test_mutable_defaults_are_independent_copies(self, patch_streamlit):
        """List defaults must be independent copies, not shared references."""
        from src.state import init_state, STATE_KEYS

        mock_st, store = patch_streamlit
        init_state()

        # Grab a list-typed key
        list_keys = [k for k, v in STATE_KEYS.items() if v["default"] == []]
        assert list_keys, "Expected at least one list-typed key"

        key = list_keys[0]
        store[key].append("sentinel")

        # Re-init a fresh store — the default should still be []
        fresh_store: dict = {}
        mock_st.session_state = fresh_store
        init_state()
        assert fresh_store[key] == [], "List default was mutated across init_state calls"


# ---------------------------------------------------------------------------
# get_global / set_global
# ---------------------------------------------------------------------------


class TestGlobalAccessors:
    def test_set_then_get_roundtrip(self, patch_streamlit):
        from src.state import init_state, get_global, set_global

        mock_st, store = patch_streamlit
        init_state()

        set_global("date_range", "2025-01-01:2025-03-31")
        assert get_global("date_range") == "2025-01-01:2025-03-31"

    def test_prefix_prepended_automatically(self, patch_streamlit):
        from src.state import init_state, set_global

        mock_st, store = patch_streamlit
        init_state()

        set_global("date_range", "value")
        assert "global_date_range" in store
        assert store["global_date_range"] == "value"

    def test_get_missing_key_returns_none(self, patch_streamlit):
        from src.state import get_global

        mock_st, store = patch_streamlit
        result = get_global("nonexistent_key")
        assert result is None

    def test_get_global_reads_from_session_state(self, patch_streamlit):
        from src.state import get_global

        mock_st, store = patch_streamlit
        store["global_dma_filter"] = ["TX", "CA"]
        assert get_global("dma_filter") == ["TX", "CA"]


# ---------------------------------------------------------------------------
# get_module / set_module
# ---------------------------------------------------------------------------


class TestModuleAccessors:
    def test_set_then_get_roundtrip(self, patch_streamlit):
        from src.state import init_state, get_module, set_module

        mock_st, store = patch_streamlit
        init_state()

        set_module("scorecard", "selected_metric", "CAC")
        assert get_module("scorecard", "selected_metric") == "CAC"

    def test_prefix_prepended_automatically(self, patch_streamlit):
        from src.state import init_state, set_module

        mock_st, store = patch_streamlit
        init_state()

        set_module("spend", "selected_channels", ["paid_search"])
        assert "spend_selected_channels" in store
        assert store["spend_selected_channels"] == ["paid_search"]

    def test_get_missing_key_returns_none(self, patch_streamlit):
        from src.state import get_module

        mock_st, store = patch_streamlit
        result = get_module("simulator", "nonexistent")
        assert result is None

    def test_module_namespaces_are_isolated(self, patch_streamlit):
        """Keys with the same bare name in different modules must not collide."""
        from src.state import init_state, set_module, get_module

        mock_st, store = patch_streamlit
        init_state()

        set_module("channels", "active_tab", "paid")
        set_module("organic", "active_tab", "seo")

        assert get_module("channels", "active_tab") == "paid"
        assert get_module("organic", "active_tab") == "seo"


# ---------------------------------------------------------------------------
# Namespace constants
# ---------------------------------------------------------------------------


class TestNamespaceConstants:
    def test_all_namespace_constants_defined(self):
        import src.state as state_module

        expected = [
            "NS_GLOBAL",
            "NS_SCORECARD",
            "NS_SPEND",
            "NS_FUNNEL",
            "NS_ONBOARDING",
            "NS_CHANNELS",
            "NS_ORGANIC",
            "NS_PRODUCT",
            "NS_OPS",
            "NS_SIMULATOR",
        ]
        for name in expected:
            assert hasattr(state_module, name), f"Missing namespace constant: {name}"

    def test_global_prefix_value(self):
        from src.state import NS_GLOBAL

        assert NS_GLOBAL == "global_"

    def test_all_constants_end_with_underscore(self):
        import src.state as state_module

        ns_constants = [v for k, v in vars(state_module).items() if k.startswith("NS_")]
        for ns in ns_constants:
            assert ns.endswith("_"), f"Namespace '{ns}' does not end with '_'"


# ---------------------------------------------------------------------------
# STATE_KEYS registry
# ---------------------------------------------------------------------------


class TestStateKeysRegistry:
    def test_registry_has_required_fields(self):
        from src.state import STATE_KEYS

        for key, meta in STATE_KEYS.items():
            assert "type" in meta, f"STATE_KEYS['{key}'] missing 'type'"
            assert "owner" in meta, f"STATE_KEYS['{key}'] missing 'owner'"
            assert "default" in meta, f"STATE_KEYS['{key}'] missing 'default'"

    def test_global_keys_present(self):
        from src.state import STATE_KEYS

        assert "global_dma_filter" in STATE_KEYS
        assert "global_scenarios" in STATE_KEYS

    def test_all_namespaces_represented(self):
        from src.state import STATE_KEYS

        owners = {meta["owner"] for meta in STATE_KEYS.values()}
        # channels_ and product_ namespaces have no registered keys after
        # orphaned-entry cleanup (APE-145).
        expected_owners = {
            "global_",
            "scorecard_",
            "spend_",
            "funnel_",
            "onboarding_",
            "organic_",
            "ops_",
            "simulator_",
        }
        missing = expected_owners - owners
        assert not missing, f"No STATE_KEYS entries for namespaces: {missing}"
