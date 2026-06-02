# APE-1e: Requirements File

**Parent:** APE-1  
**Priority:** High  
**Assignee:** Developer agent

## Summary

Create `requirements.txt` with pinned versions for all Phase 1 dependencies.

## Requirements

Include at minimum:
```
streamlit>=1.30.0
pandas>=2.1.0
plotly>=5.18.0
altair>=5.2.0
duckdb>=0.9.0
python-dotenv>=1.0.0
pytest>=7.4.0
```

Pin to minimum versions (use `>=`), not exact pins, for flexibility in dev.

## Acceptance

- `pip install -r requirements.txt` succeeds in a clean venv
- All imports used by app.py and pages resolve without error
