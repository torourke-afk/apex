# APE-1g: Directory Scaffold & __init__ Files

**Parent:** APE-1  
**Priority:** High — do this first  
**Assignee:** Developer agent

## Summary

Create the full project directory structure with `__init__.py` files so all imports resolve.

## Requirements

Create these directories and empty `__init__.py` files:

```
src/__init__.py
src/config/__init__.py
src/pages/__init__.py       (may not be needed for Streamlit, but include for imports)
src/components/__init__.py
src/data/__init__.py
src/simulator/__init__.py
tests/__init__.py
data/                        (no __init__, just the directory for DuckDB)
```

Also create:
- `.gitignore` with Python defaults + `data/*.duckdb`, `.env`, `__pycache__/`, `.streamlit/`
- `.streamlit/config.toml` with theme overrides pointing to RVGT brand colors

## Acceptance

- `python -c "import src; import src.config; import src.data"` works
- `.gitignore` covers standard Python artifacts and DuckDB file
- Streamlit config exists and references brand colors

## Note

This ticket should be executed FIRST — it creates the skeleton that all other tickets build on.
