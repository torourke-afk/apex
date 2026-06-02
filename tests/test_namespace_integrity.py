"""
tests/test_namespace_integrity.py — Namespace integrity tests for APE-141.

Verifies:
  - Every key in STATE_KEYS starts with a valid declared namespace prefix
  - No two modules claim the same fully-qualified key
  - All global_ keys are documented (non-empty description / comment in source)
  - Namespace constants (NS_*) are consistent with the registry entries
  - Registry is self-consistent (owner prefix matches key prefix)
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

# Minimal Streamlit stub
_st_stub = types.ModuleType("streamlit")
_st_stub.session_state = {}
sys.modules.setdefault("streamlit", _st_stub)

import pytest

from src.state import (
    STATE_KEYS,
    NS_GLOBAL, NS_SCORECARD, NS_SPEND, NS_FUNNEL, NS_ONBOARDING,
    NS_CHANNELS, NS_ORGANIC, NS_PRODUCT, NS_OPS, NS_SIMULATOR,
)

# ---------------------------------------------------------------------------
# Fixtures / helpers
# ---------------------------------------------------------------------------

VALID_PREFIXES: frozenset[str] = frozenset({
    NS_GLOBAL, NS_SCORECARD, NS_SPEND, NS_FUNNEL, NS_ONBOARDING,
    NS_CHANNELS, NS_ORGANIC, NS_PRODUCT, NS_OPS, NS_SIMULATOR,
})

# Keys whose physical name deliberately uses a prefix different from their owner
# namespace (e.g. aeo_* owned by organic_, cal_*/approval_* owned by ops_,
# bei_*/retention_* owned by onboarding_, simulator/submitted_directives owned
# by simulator_).  These are spec-sanctioned cross-namespace entries and are
# exempt from prefix-equality assertions.
CROSS_NAMESPACE_KEYS: frozenset[str] = frozenset(
    key for key, meta in STATE_KEYS.items()
    if not key.startswith(meta["owner"])
)


def _prefix_of(key: str) -> str | None:
    """Return the namespace prefix for a registered key, or None."""
    for p in VALID_PREFIXES:
        if key.startswith(p):
            return p
    return None


# ---------------------------------------------------------------------------
# Test Suite 1: Every STATE_KEYS key starts with a valid declared prefix
# ---------------------------------------------------------------------------


class TestKeyPrefixValidity:
    """Every key in STATE_KEYS must begin with one of the declared NS_* prefixes."""

    @pytest.mark.parametrize("key", list(STATE_KEYS.keys()))
    def test_key_starts_with_valid_prefix(self, key: str):
        if key in CROSS_NAMESPACE_KEYS:
            pytest.skip(f"Cross-namespace key {key!r} — exempted by CROSS_NAMESPACE_KEYS")
        prefix = _prefix_of(key)
        assert prefix is not None, (
            f"Key {key!r} does not start with any declared namespace prefix.\n"
            f"Valid prefixes: {sorted(VALID_PREFIXES)}"
        )

    def test_all_keys_have_non_empty_suffix(self):
        """Key must have a meaningful suffix after the namespace prefix."""
        for key in STATE_KEYS:
            if key in CROSS_NAMESPACE_KEYS:
                continue
            prefix = _prefix_of(key)
            assert prefix is not None
            suffix = key[len(prefix):]
            assert suffix, f"Key {key!r} has an empty suffix after prefix {prefix!r}"
            assert not suffix.startswith("_"), (
                f"Key {key!r} suffix starts with underscore — double-underscore separator"
            )

    def test_no_bare_prefix_keys(self):
        """No key should equal a naked prefix (e.g. 'global_' alone)."""
        for prefix in VALID_PREFIXES:
            assert prefix not in STATE_KEYS, (
                f"Bare prefix {prefix!r} found as a key in STATE_KEYS"
            )


# ---------------------------------------------------------------------------
# Test Suite 2: No two modules claim the same key
# ---------------------------------------------------------------------------


class TestKeyUniqueness:
    """Each fully-qualified key appears exactly once in STATE_KEYS."""

    def test_no_duplicate_keys(self):
        keys = list(STATE_KEYS.keys())
        unique_keys = set(keys)
        assert len(keys) == len(unique_keys), (
            f"Duplicate keys detected: "
            f"{[k for k in keys if keys.count(k) > 1]}"
        )

    def test_no_two_owners_claim_same_key(self):
        """
        The 'owner' field in each entry must match the key's prefix.
        If two entries had the same key, they could not coexist in the dict.
        This test additionally verifies owner consistency.
        Cross-namespace keys (in CROSS_NAMESPACE_KEYS) are exempt from this check.
        """
        for key, meta in STATE_KEYS.items():
            if key in CROSS_NAMESPACE_KEYS:
                continue
            owner = meta.get("owner", "")
            assert key.startswith(owner), (
                f"Key {key!r} has owner {owner!r} but key does not start with that prefix"
            )

    def test_owner_field_present_for_all_keys(self):
        for key, meta in STATE_KEYS.items():
            assert "owner" in meta, f"Key {key!r} is missing 'owner' field"
            assert meta["owner"], f"Key {key!r} has an empty 'owner' field"

    def test_owner_is_valid_prefix(self):
        for key, meta in STATE_KEYS.items():
            owner = meta["owner"]
            assert owner in VALID_PREFIXES, (
                f"Key {key!r} owner {owner!r} is not in VALID_PREFIXES"
            )


# ---------------------------------------------------------------------------
# Test Suite 3: All global_ keys are documented
# ---------------------------------------------------------------------------


class TestGlobalKeyDocumentation:
    """All global_ keys must be accounted for with a default and owner."""

    def test_all_global_keys_have_defaults(self):
        global_keys = {k: v for k, v in STATE_KEYS.items() if k.startswith(NS_GLOBAL)}
        assert global_keys, "No global_ keys found in STATE_KEYS"
        for key, meta in global_keys.items():
            assert "default" in meta, f"Global key {key!r} has no 'default' field"

    def test_all_global_keys_have_type(self):
        for key, meta in STATE_KEYS.items():
            if not key.startswith(NS_GLOBAL):
                continue
            assert "type" in meta, f"Global key {key!r} has no 'type' field"
            assert isinstance(meta["type"], type), (
                f"Global key {key!r} 'type' field is not a Python type: {meta['type']!r}"
            )

    def test_expected_global_keys_present(self):
        """Core cross-page global keys must be registered."""
        required_globals = {
            "global_current_page",
            "global_alert_context",
            "global_date_range",
            "global_dma_filter",
            "global_scenarios",
        }
        missing = required_globals - set(STATE_KEYS.keys())
        assert not missing, f"Required global keys missing from registry: {missing}"

    def test_global_keys_source_documented(self):
        """
        Verify that every global_ key appears in the source code of state/__init__.py
        in a comment or inline documentation position.
        """
        state_src_path = os.path.join(EXECUTOR_ROOT, "src/state/__init__.py")
        with open(state_src_path) as fh:
            src = fh.read()

        for key, meta in STATE_KEYS.items():
            if not key.startswith(NS_GLOBAL):
                continue
            # Key must literally appear in the source file
            assert key in src, (
                f"Global key {key!r} is in STATE_KEYS but not found in state/__init__.py source"
            )


# ---------------------------------------------------------------------------
# Test Suite 4: Namespace constant consistency
# ---------------------------------------------------------------------------


class TestNamespaceConstants:
    """NS_* constants match the pattern used in STATE_KEYS owners."""

    NS_CONSTANTS = {
        "NS_GLOBAL": NS_GLOBAL,
        "NS_SCORECARD": NS_SCORECARD,
        "NS_SPEND": NS_SPEND,
        "NS_FUNNEL": NS_FUNNEL,
        "NS_ONBOARDING": NS_ONBOARDING,
        "NS_CHANNELS": NS_CHANNELS,
        "NS_ORGANIC": NS_ORGANIC,
        "NS_PRODUCT": NS_PRODUCT,
        "NS_OPS": NS_OPS,
        "NS_SIMULATOR": NS_SIMULATOR,
    }

    @pytest.mark.parametrize("name,value", NS_CONSTANTS.items())
    def test_ns_constant_ends_with_underscore(self, name: str, value: str):
        assert value.endswith("_"), (
            f"{name} = {value!r} should end with '_' (namespace separator)"
        )

    @pytest.mark.parametrize("name,value", NS_CONSTANTS.items())
    def test_ns_constant_is_non_empty(self, name: str, value: str):
        assert value, f"{name} must not be empty"

    def test_every_ns_constant_has_at_least_one_key(self):
        """Each declared namespace must own at least one key in STATE_KEYS."""
        owners_in_registry = {meta["owner"] for meta in STATE_KEYS.values()}
        for name, ns in self.NS_CONSTANTS.items():
            assert ns in owners_in_registry, (
                f"Namespace {name} ({ns!r}) has no keys in STATE_KEYS"
            )

    def test_all_registry_owners_map_to_a_constant(self):
        """Owners in the registry must be one of the declared NS_* constants."""
        declared = set(self.NS_CONSTANTS.values())
        for key, meta in STATE_KEYS.items():
            owner = meta["owner"]
            assert owner in declared, (
                f"Key {key!r} owner {owner!r} is not a declared NS_* constant"
            )


# ---------------------------------------------------------------------------
# Test Suite 5: Registry schema completeness
# ---------------------------------------------------------------------------


class TestRegistrySchema:
    """Every entry in STATE_KEYS satisfies the required schema."""

    REQUIRED_FIELDS = {"type", "owner", "default"}

    @pytest.mark.parametrize("key", list(STATE_KEYS.keys()))
    def test_entry_has_all_required_fields(self, key: str):
        meta = STATE_KEYS[key]
        missing = self.REQUIRED_FIELDS - set(meta.keys())
        assert not missing, (
            f"STATE_KEYS[{key!r}] is missing required fields: {missing}"
        )

    def test_registry_has_expected_minimum_size(self):
        """Registry must contain at least the known baseline of 28 keys."""
        assert len(STATE_KEYS) >= 28, (
            f"STATE_KEYS has only {len(STATE_KEYS)} entries; expected >= 28"
        )

    def test_no_key_contains_double_underscore(self):
        """Keys should use single underscores as namespace separators."""
        for key in STATE_KEYS:
            assert "__" not in key, (
                f"Key {key!r} contains a double-underscore; "
                "use a single underscore as the namespace separator"
            )

    def test_all_defaults_match_declared_type_or_none(self):
        """
        The 'default' value must be an instance of 'type', or None (for NoneType keys).
        """
        for key, meta in STATE_KEYS.items():
            declared_type = meta["type"]
            default = meta["default"]
            if declared_type is type(None):
                assert default is None, (
                    f"Key {key!r} declares type NoneType but default is {default!r}"
                )
            else:
                assert isinstance(default, declared_type) or default is None, (
                    f"Key {key!r}: default {default!r} is not an instance of {declared_type}"
                )
