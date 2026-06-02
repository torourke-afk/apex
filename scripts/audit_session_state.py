#!/usr/bin/env python3
"""
scripts/audit_session_state.py — Static audit of st.session_state usage.

Scans all .py files in src/ for st.session_state references, cross-references
against the STATE_KEYS registry, and reports:
  - Unregistered keys  (used in code, absent from STATE_KEYS)
  - Orphaned keys      (in STATE_KEYS, never referenced in src/)
  - Write-only keys    (assigned but never read in src/)
  - Read-only keys     (read but never assigned in src/)
  - Collision candidates (keys from different namespace owners sharing a prefix)

Exit codes:
  0 — all checks pass (unregistered / orphaned counts are 0)
  1 — one or more issues found
"""

from __future__ import annotations

import ast
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ---------------------------------------------------------------------------
# Workspace paths
# ---------------------------------------------------------------------------

SCRIPT_DIR = Path(__file__).resolve().parent
WORKSPACE_ROOT = SCRIPT_DIR.parent
SRC_DIR = WORKSPACE_ROOT / "src"

if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

# ---------------------------------------------------------------------------
# Load STATE_KEYS from the registry (with a minimal streamlit stub)
# ---------------------------------------------------------------------------

import types as _types

_st_stub = _types.ModuleType("streamlit")
_st_stub.session_state = {}
sys.modules.setdefault("streamlit", _st_stub)

from src.state import STATE_KEYS, NS_GLOBAL  # noqa: E402

REGISTERED_KEYS: set[str] = set(STATE_KEYS.keys())
PLACEHOLDER_KEYS: set[str] = {k for k, v in STATE_KEYS.items() if v.get("placeholder")}
VALID_PREFIXES: set[str] = {
    "global_", "scorecard_", "spend_", "funnel_", "onboarding_",
    "channels_", "organic_", "product_", "ops_", "simulator_",
}

# ---------------------------------------------------------------------------
# Regex patterns for session_state key extraction
# ---------------------------------------------------------------------------

# st.session_state["key"] or st.session_state['key']
_SUBSCRIPT_RE = re.compile(
    r'st\.session_state\s*\[\s*[\'"]([^\'"]+)[\'"]\s*\]'
)
# st.session_state.get("key") or .get('key')
_GET_RE = re.compile(
    r'st\.session_state\.get\s*\(\s*[\'"]([^\'"]+)[\'"]\s*[,\)]'
)
# "key" in st.session_state
_IN_RE = re.compile(
    r'[\'"]([^\'"]+)[\'"]\s+in\s+st\.session_state'
)
# st.session_state.pop("key")
_POP_RE = re.compile(
    r'st\.session_state\.pop\s*\(\s*[\'"]([^\'"]+)[\'"]\s*[,\)]'
)

# Write patterns: st.session_state["key"] = ...
_WRITE_RE = re.compile(
    r'st\.session_state\s*\[\s*[\'"]([^\'"]+)[\'"]\s*\]\s*='
)

# Typed accessor patterns — these construct full keys implicitly:
#   get_global("suffix")   → "global_<suffix>"
#   set_global("suffix")   → "global_<suffix>"
_GLOBAL_ACCESSOR_RE = re.compile(
    r'(?:get_global|set_global)\s*\(\s*[\'"]([^\'"]+)[\'"]'
)
#   get_module("module", "suffix")  → "<module>_<suffix>"
#   set_module("module", "suffix")  → "<module>_<suffix>"
_MODULE_ACCESSOR_RE = re.compile(
    r'(?:get_module|set_module)\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]'
)


def _expand_accessor_keys(source: str) -> set[str]:
    """Reconstruct full registry keys from typed-accessor call sites."""
    keys: set[str] = set()
    for m in _GLOBAL_ACCESSOR_RE.finditer(source):
        keys.add(f"global_{m.group(1)}")
    for m in _MODULE_ACCESSOR_RE.finditer(source):
        keys.add(f"{m.group(1)}_{m.group(2)}")
    return keys


def _extract_keys_from_source(
    source: str,
) -> tuple[set[str], set[str]]:
    """Return (all_keys, write_keys) found in source text.

    Includes both direct st.session_state["key"] access and
    indirect access via the typed accessor helpers.
    """
    all_keys: set[str] = set()
    write_keys: set[str] = set()

    for pattern in (_SUBSCRIPT_RE, _GET_RE, _IN_RE, _POP_RE):
        for m in pattern.finditer(source):
            all_keys.add(m.group(1))

    for m in _WRITE_RE.finditer(source):
        write_keys.add(m.group(1))
        all_keys.add(m.group(1))

    # Reconstruct keys from typed accessor calls
    accessor_keys = _expand_accessor_keys(source)
    all_keys |= accessor_keys
    # Treat set_global / set_module calls as writes
    for m in re.finditer(r'set_global\s*\(\s*[\'"]([^\'"]+)[\'"]', source):
        write_keys.add(f"global_{m.group(1)}")
    for m in re.finditer(
        r'set_module\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]', source
    ):
        write_keys.add(f"{m.group(1)}_{m.group(2)}")

    return all_keys, write_keys


# ---------------------------------------------------------------------------
# Walk src/
# ---------------------------------------------------------------------------

used_keys: set[str] = set()           # any reference
written_keys: set[str] = set()        # assigned
file_key_map: dict[str, set[str]] = defaultdict(set)  # file → keys used

py_files = sorted(SRC_DIR.rglob("*.py"))
for py_file in py_files:
    try:
        source = py_file.read_text(encoding="utf-8")
    except OSError:
        continue
    file_keys, file_writes = _extract_keys_from_source(source)
    used_keys |= file_keys
    written_keys |= file_writes
    if file_keys:
        rel = py_file.relative_to(WORKSPACE_ROOT)
        file_key_map[str(rel)] |= file_keys

read_keys = used_keys - written_keys   # referenced but never assigned

# ---------------------------------------------------------------------------
# Compute findings
# ---------------------------------------------------------------------------

unregistered = used_keys - REGISTERED_KEYS
orphaned = (REGISTERED_KEYS - used_keys) - PLACEHOLDER_KEYS
write_only = written_keys - (used_keys - written_keys) - (REGISTERED_KEYS - used_keys)
# write_only: written in code, never appear in a read pattern
# Recompute cleanly:
read_pattern_keys = set()
for py_file in py_files:
    try:
        source = py_file.read_text(encoding="utf-8")
    except OSError:
        continue
    for pattern in (_SUBSCRIPT_RE, _GET_RE, _IN_RE, _POP_RE):
        for m in pattern.finditer(source):
            read_pattern_keys.add(m.group(1))
    # Writes also count as "reads" if they appear in a get/in/pop pattern
    # (assignment can be to a key that is also read elsewhere)

# Also capture get_global / get_module as read accesses
for py_file in py_files:
    try:
        source = py_file.read_text(encoding="utf-8")
    except OSError:
        continue
    for m in re.finditer(r'get_global\s*\(\s*[\'"]([^\'"]+)[\'"]', source):
        read_pattern_keys.add(f"global_{m.group(1)}")
    for m in re.finditer(
        r'get_module\s*\(\s*[\'"]([^\'"]+)[\'"]\s*,\s*[\'"]([^\'"]+)[\'"]', source
    ):
        read_pattern_keys.add(f"{m.group(1)}_{m.group(2)}")

actual_write_only = written_keys - read_pattern_keys   # assigned, never read
actual_read_only = read_pattern_keys - written_keys    # read, never assigned

# Collision candidates: keys from different files claiming the same effective suffix
# (same key referenced under multiple namespace-less names)
# Simple heuristic: find registered keys whose suffix (after the prefix) appears
# under more than one namespace prefix in STATE_KEYS.
suffix_owners: dict[str, list[str]] = defaultdict(list)
for key, meta in STATE_KEYS.items():
    owner = meta["owner"]  # e.g. "scorecard_"
    suffix = key[len(owner):]
    suffix_owners[suffix].append(owner)

collision_candidates = {
    suffix: owners
    for suffix, owners in suffix_owners.items()
    if len(owners) > 1
}

# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

SEPARATOR = "─" * 72
issues: list[str] = []


def _section(title: str, items: set | dict, detail_fn=None) -> None:
    print(f"\n{SEPARATOR}")
    print(f"  {title}  ({len(items)})")
    print(SEPARATOR)
    if not items:
        print("  (none)")
        return
    if isinstance(items, dict):
        for k, v in sorted(items.items()):
            print(f"  {k!r:40s} owners: {v}")
    else:
        for k in sorted(items):
            if detail_fn:
                print(f"  {k!r:40s} {detail_fn(k)}")
            else:
                print(f"  {k!r}")


def _files_using(key: str) -> str:
    files = [f for f, keys in file_key_map.items() if key in keys]
    return f"in: {', '.join(files)}" if files else ""


print("\n" + "=" * 72)
print("  Apex Session State Audit")
print(f"  Source: {SRC_DIR}")
print(f"  Registered keys: {len(REGISTERED_KEYS)}")
print(f"  Keys found in src/: {len(used_keys)}")
print("=" * 72)

_section("UNREGISTERED KEYS (used in code, absent from STATE_KEYS)", unregistered, _files_using)
if unregistered:
    issues.append(f"{len(unregistered)} unregistered key(s)")

_section("ORPHANED KEYS (in STATE_KEYS, never referenced in src/)", orphaned)
if orphaned:
    issues.append(f"{len(orphaned)} orphaned key(s)")

_section("WRITE-ONLY KEYS (assigned but never read)", actual_write_only, _files_using)

_section("READ-ONLY KEYS (read but never assigned)", actual_read_only, _files_using)

_section("COLLISION CANDIDATES (same suffix, multiple namespace owners)", collision_candidates)

# ---------------------------------------------------------------------------
# Summary & exit
# ---------------------------------------------------------------------------

print(f"\n{SEPARATOR}")
if issues:
    print(f"  RESULT: FAIL — {'; '.join(issues)}")
    print(SEPARATOR + "\n")
    sys.exit(1)
else:
    print("  RESULT: PASS — no unregistered or orphaned keys found")
    print(SEPARATOR + "\n")
    sys.exit(0)
