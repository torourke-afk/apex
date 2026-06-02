# APE-28 Fix: Caching Settings & get_engine (C-1 Blocker)

## Problem

`tests/test_caching.py` has 25 failures due to two missing implementations:

### 1. Missing `APEX_DATA_REFRESH_INTERVAL_MINUTES` in settings.py

**File:** `src/config/settings.py`

The test suite expects:
- `APEX_DATA_REFRESH_INTERVAL_MINUTES` — integer, default 15, driven by env var `APEX_DATA_REFRESH_INTERVAL_MINUTES`
- `APEX_DATA_REFRESH_INTERVAL_SECONDS` — derived as `MINUTES * 60` (currently hardcoded to 300)

**Current state (lines 24-26):**
```python
APEX_DATA_REFRESH_INTERVAL_SECONDS: int = int(
    os.environ.get("APEX_DATA_REFRESH_INTERVAL_SECONDS", "300")
)
```

**Required change:**
```python
APEX_DATA_REFRESH_INTERVAL_MINUTES: int = int(
    os.environ.get("APEX_DATA_REFRESH_INTERVAL_MINUTES", "15")
)
APEX_DATA_REFRESH_INTERVAL_SECONDS: int = APEX_DATA_REFRESH_INTERVAL_MINUTES * 60
```

### 2. Missing `get_engine()` in init_db.py

**File:** `src/data/init_db.py`

Tests expect `get_engine()` decorated with `@st.cache_resource` that returns a `sqlalchemy.engine.Engine`.

**Current state:** Only `get_connection()` exists (returns DuckDB connection). No SQLAlchemy engine.

**Required additions:**
- Import `streamlit as st` and `sqlalchemy.create_engine`
- Add `get_engine()` function decorated with `@st.cache_resource`
- For dev mode: create engine from `sqlite:///` or DuckDB-compatible URI
- For prod mode: create engine from `DB_URL`
- Export `get_engine` from module

## Verification

Run `pytest tests/test_caching.py -v` — all 25 failures must resolve to 0.
