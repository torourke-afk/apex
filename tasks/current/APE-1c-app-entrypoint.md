# APE-1c: App Entry Point

**Parent:** APE-1  
**Priority:** High  
**Assignee:** Developer agent  
**Depends on:** APE-1a, APE-1b

## Summary

Create `app.py` — the Streamlit entry point that boots the application, applies brand, and sets up navigation.

## Requirements

1. Import and call `apply_brand()` from `src/config/brand.py`.
2. Set up the Streamlit multi-page app structure.
3. Display app title and a minimal landing/redirect to the Overview page.
4. Initialize `st.session_state` keys needed across pages (empty dict placeholders are fine for now).
5. The app must be runnable with `streamlit run app.py`.

## Acceptance

- `streamlit run app.py` launches without error
- Browser shows branded page with sidebar listing all 9 pages
- RVGT colors visible in header/sidebar
