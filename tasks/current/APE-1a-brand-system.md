# APE-1a: RVGT Brand System

**Parent:** APE-1  
**Priority:** High — blocks all other tickets  
**Assignee:** Developer agent

## Summary

Create `src/config/brand.py` with the complete RVGT brand token set. This is the foundation every page and component imports.

## Requirements

1. Define a `COLORS` dict with at minimum:
   - `primary`, `secondary`, `accent` — RVGT brand colors
   - `background` — near-white (NOT `#FFFFFF`)
   - `surface` — card/panel background
   - `text_primary` — near-black (NOT `#000000`)
   - `text_secondary` — muted text
   - `success`, `warning`, `error` — semantic colors
   - `border` — subtle dividers

2. Define a `TYPOGRAPHY` dict:
   - `font_family` — sans-serif stack
   - `heading_font` — if different from body
   - `sizes` — `sm`, `md`, `lg`, `xl`, `xxl`

3. Define a `SPACING` dict:
   - `xs`, `sm`, `md`, `lg`, `xl` — consistent spacing scale

4. Export a `apply_brand(st)` function that:
   - Sets `st.set_page_config()` defaults (page title, icon, layout)
   - Injects custom CSS via `st.markdown()` to apply brand colors, fonts, hide Streamlit chrome as needed

5. **Hard constraint:** No `#000000` or `#FFFFFF` anywhere. Use near-black/near-white equivalents.

## Acceptance

- `from src.config.brand import COLORS, TYPOGRAPHY, SPACING, apply_brand` works
- Visual inspection: brand colors render correctly in Streamlit
- Grep for `#000000` and `#FFFFFF` returns zero hits across the project

## Reference

See RVGT brand guidelines (`rvgt-brand` skill) for official color palette.
