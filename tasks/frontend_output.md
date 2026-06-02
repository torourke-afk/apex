# Frontend Output — APE-191 (APE-UX-11) — Changes Requested Resolution

**Date:** 2026-05-12
**Agent:** Frontend Engineer (26aa10f0)
**Issue:** APE-191 — Apply card-based layout to all 8 remaining pages
**Status:** Resubmitting — all QA violations addressed

---

## Changes Made

### brand.py
- Added 7 new COLORS tokens: `chart_green`, `chart_green_dark`, `success_bg`, `warning_bg`, `error_bg`, `warning_bg_light`, `success_bg_light`
- Added `hex_rgba(hex_color, alpha)` helper function for converting hex colors to `rgba()` strings
- Exported `hex_rgba` in `__all__`

### Page 2 — 2_💰_Spend_Allocation.py
- No changes needed — grep confirms no hardcoded hex literals present (QA report was stale for this page)

### Page 3 — 3_🔄_Acquisition_Funnel.py
- **Color fix:** Line 365: `'#2E7D52'` → `COLORS['success']`
- **data_table:** Replaced custom HTML table (Stage Detail section) with `data_table()` using a pre-built DataFrame

### Page 4 — 4_🏠_Onboarding_Retention.py
- **Color fix:** Lines 345, 347: `"#8BAF6A"` → `COLORS["chart_green"]`, `"#1A4D32"` → `COLORS["chart_green_dark"]`
- **Alpha fix:** `COLORS["surface"] + "D0"` → `hex_rgba(COLORS["surface"], 0.82)`
- Added `hex_rgba` import

### Page 5 — 5_📢_Paid_Channels.py
- Added imports: `pandas`, `data_table`, `hex_rgba`
- **data_table (×3):** Market Segmentation, Keyword Detail, and Negative Keyword Candidates HTML tables all replaced with `data_table()`
- **Alpha fixes:** `CHART_PALETTE[1] + "18"` → `hex_rgba(...)`, `CHART_PALETTE[0] + "22"` → `hex_rgba(...)`
- Replaced custom `st.markdown` alert divs with `st.warning()` / `st.success()`

### Page 6 — 6_🔍_Organic_AEO.py
- Added imports: `data_table`, `hex_rgba`
- **data_table:** `st.dataframe(_styled, ...)` → `data_table(_display_df, ...)` (Prompt-Level Drill-In)
- **Color fixes (5 hardcoded hex):** `"#E8F5EE"` → `COLORS["success_bg"]`, `"#FDF3E3"` → `COLORS["warning_bg"]`, `"#FDECEA"` → `COLORS["error_bg"]`, `"#F5E6C8"` → `COLORS["warning_bg_light"]`, `"#D4EDE0"` → `COLORS["success_bg_light"]`
- **Alpha fixes (4 patterns):** All `COLORS[x] + "50"` and `+ "60"` patterns replaced with `hex_rgba()`

### Page 7 — 7_🛠️_Product_Experience.py
- **card_container split:** Closed "Product Pipeline Tracker" card after `data_table()`, added new `card_container("Product Count by Category")` wrapping `fig_breakdown`
- **Alpha fix:** `CHART_PALETTE[1] + "18"` → `hex_rgba(CHART_PALETTE[1], 0.09)` (velocity chart)
- Added `hex_rgba` import

### Page 8 — 8_⚙️_Operations_Command.py
- Added imports: `kpi_card`, `hex_rgba`
- **KPI row:** Added standard 5-column KPI row after `filter_bar()`: Launches This Month, Pending Approvals, Blocked Tickets, Systems Healthy, Sprint Completion
- **Alpha fixes (4 patterns):** All `COLORS[x] + "22"` and `+ "18"` patterns replaced with `hex_rgba()`

### Page 9 — 9_🧮_Simulator.py
- Added imports: `data_table`, `filter_bar`
- **filter_bar:** Added `filter_bar(key_prefix="sim", show_product=False)` after page header
- **data_table:** Before/After comparison HTML table replaced with `data_table(_ba_df, ...)`

---

## Acceptance Criteria Verification

| Criterion | Status |
|---|---|
| All 9 pages follow same visual hierarchy | ✅ All pages have apply_brand → filter_bar → KPI row → charts in cards → tables |
| All charts inside card containers | ✅ Page 7 fig_breakdown now in dedicated card; all other pages confirmed |
| All tables use updated data_table() | ✅ All QA-flagged HTML tables and st.dataframe calls replaced |
| Consistent 1.5rem spacing between sections | ✅ Existing spacer divs preserved |
| No hardcoded colors anywhere | ✅ Zero literal hex strings remain; all COLORS[x]+"nn" patterns replaced with hex_rgba() |
| filter_bar() on all pages | ✅ Page 9 now has filter_bar() |
| KPI row present on all pages | ✅ Page 8 now has standard 5-card KPI row |

---

## Files Modified
- `src/config/brand.py`
- `src/pages/3_🔄_Acquisition_Funnel.py`
- `src/pages/4_🏠_Onboarding_Retention.py`
- `src/pages/5_📢_Paid_Channels.py`
- `src/pages/6_🔍_Organic_AEO.py`
- `src/pages/7_🛠️_Product_Experience.py`
- `src/pages/8_⚙️_Operations_Command.py`
- `src/pages/9_🧮_Simulator.py`
