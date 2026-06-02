# APE-1f: DuckDB Initialization

**Parent:** APE-1  
**Priority:** Medium  
**Assignee:** Developer agent  
**Depends on:** APE-1b (settings for DB_PATH)

## Summary

Create `src/data/init_db.py` that initializes the local DuckDB database with schema stubs for each module.

## Requirements

1. Create `data/` directory if it doesn't exist.
2. Connect to DuckDB at the path from `settings.DB_PATH`.
3. Create stub tables (can be empty, just schema):
   - `kpi_metrics` — id, name, value, period, updated_at
   - `campaigns` — id, name, channel, status, spend, revenue, start_date, end_date
   - `competitors` — id, name, segment, notes
   - `leads` — id, source, stage, score, created_at
4. Make the script idempotent (`CREATE TABLE IF NOT EXISTS`).
5. Runnable standalone: `python -m src.data.init_db`

## Acceptance

- Running the script creates `data/apex.duckdb`
- Tables exist and are queryable
- Running it twice doesn't error (idempotent)
