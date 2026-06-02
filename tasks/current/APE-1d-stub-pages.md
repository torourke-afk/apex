# APE-1d: 9 Stub Pages

**Parent:** APE-1  
**Priority:** High  
**Assignee:** Developer agent  
**Depends on:** APE-1a, APE-1b, APE-1c

## Summary

Create the 9 numbered page files in `src/pages/`. Each is a minimal stub that proves navigation works and brand is applied.

## Requirements

Create these files, each following the same template pattern:

1. `src/pages/01_Overview.py`
2. `src/pages/02_Market_Intelligence.py`
3. `src/pages/03_Campaign_Performance.py`
4. `src/pages/04_Competitor_Analysis.py`
5. `src/pages/05_Channel_Analytics.py`
6. `src/pages/06_Content_Performance.py`
7. `src/pages/07_Lead_Pipeline.py`
8. `src/pages/08_Budget_Allocation.py`
9. `src/pages/09_Executive_Summary.py`

Each stub page must:
- Import and call `apply_brand()` (or import brand tokens)
- Set a page-specific title via `st.title()` using the module name
- Display a placeholder message: "Module coming soon — Phase 2"
- Use brand colors for any styled elements
- **No pure black or white**

## Acceptance

- All 9 pages appear in Streamlit sidebar in numeric order
- Clicking each page renders the stub with correct title
- Brand colors applied on every page
