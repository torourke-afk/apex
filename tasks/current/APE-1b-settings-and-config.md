# APE-1b: Settings & Configuration

**Parent:** APE-1  
**Priority:** High — blocks page stubs  
**Assignee:** Developer agent  
**Depends on:** APE-1a (brand system)

## Summary

Create `src/config/settings.py` with app-wide configuration and environment handling.

## Requirements

1. Define app metadata:
   - `APP_NAME = "Apex"`
   - `APP_VERSION = "0.1.0"`
   - `APP_DESCRIPTION` — one-liner for the platform

2. Database config:
   - `DB_PATH` — path to DuckDB file (default: `data/apex.duckdb`)
   - `DB_URL` — PostgreSQL connection string (from env var, optional)
   - Helper to detect dev vs prod mode

3. Page registry — ordered list of the 9 modules with:
   - `id`, `title`, `icon` (emoji), `description`
   - Used by the sidebar and overview page

4. Feature flags dict (empty for now, structure in place).

5. Use `os.environ.get()` for any secrets or env-specific values. No hardcoded credentials.

## Acceptance

- `from src.config.settings import APP_NAME, PAGES, DB_PATH` works
- Settings load without error in both dev (no env vars) and prod (env vars set)
