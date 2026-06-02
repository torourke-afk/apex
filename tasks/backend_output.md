# APE-196 — Fix Caching Settings & get_engine

## Status: COMPLETE

## What Was Fixed

### 1. `APEX_DATA_REFRESH_INTERVAL_MINUTES` in settings.py
Already in place before this heartbeat (line 24–27). No change needed.

### 2. `get_engine()` in init_db.py
Already in place before this heartbeat (lines 92–97). No change needed.

### 3. conftest.py — Root cause of 23 test failures

**Root cause:** `_restore_streamlit_module` was saving ALL `streamlit.*` submodules and popping newly loaded ones after each test. This caused `CachedResult` class-identity mismatches in pickle when `@st.cache_data` decorated functions ran across test boundaries.

**Fix (already applied before this heartbeat):**
- Added `_preload_streamlit` session-scoped fixture that imports streamlit once before any test runs
- Simplified `_restore_streamlit_module` to only restore `sys.modules["streamlit"]` if a test REPLACED it (never pops submodules)
- This prevents the class-identity mismatch in pickle while still handling `test_simulator_ui_helpers.py`'s fake-streamlit pattern

## Test Results

```
pytest tests/test_caching.py -v
30 passed, 0 failed (12 warnings)
```

## Pre-existing Issues (not in scope)

15 test files have collection errors caused by setting `sys.modules["streamlit"]` to a fake at module level before importing code that needs real streamlit (`st_aggrid` → `streamlit.components.v1`). These are frontend test files (test_alert_badge.py, test_cross_page_state.py, etc.) and pre-date this heartbeat.

## Next Action

APE-28 QA Pass can now proceed — unblock APE-196, mark it done, notify Tech Lead.
