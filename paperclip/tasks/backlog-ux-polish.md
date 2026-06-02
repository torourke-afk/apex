# Apex UX/UI Polish — Phase 7 Backlog

> **Epic:** Phase 7 — UX Polish, Missing Features & Bug Fixes
> **Owner:** Distributed across Frontend Engineer, Backend Engineer, QA Engineer
> **Design reference:** `docs/ux-redesign-mockup-reference.html`
> **Gap analysis source:** Mockup-vs-live audit completed 2026-05-12
> **Hard rule:** All colors MUST come from `src/config/brand.py`. No hardcoded hex values anywhere.
> **QA gate:** Every ticket in this phase auto-routes to QA Engineer on completion. QA uses the updated acceptance matrix (APE-P7-QA) to validate.

---

## APE-P7-01: Expand brand.py color palette for UI richness

**Assignee:** Frontend Engineer
**Priority:** High — blocks all cosmetic tickets
**Blocks:** APE-P7-02, APE-P7-03, APE-P7-04, APE-P7-05, APE-P7-06, APE-P7-07, APE-P7-08
**Files to modify:** `src/config/brand.py`

### Context
The current RVGT brand palette (Red, Onyx, Platinum, Scarlet, Mahogany, Iron, Alloy) is structurally sound but visually monotone for a data-dense dashboard. The gap analysis scored charts and data tables lower because the limited palette makes it hard to distinguish 4+ data series or encode semantic states richly. This ticket expands the palette with complementary accent colors that harmonize with the RVGT brand while adding the visual variety needed for a professional CMO dashboard.

### Requirements

1. **Add UI accent colors** to the `COLORS` dict — these extend (not replace) the brand primaries:
   ```python
   # UI accent palette — complementary to RVGT brand
   "accent_blue": "#2563EB",       # Data series, links, info states
   "accent_blue_light": "#DBEAFE", # Blue badge backgrounds
   "accent_teal": "#0D9488",       # Secondary positive, channel highlights
   "accent_teal_light": "#CCFBF1", # Teal badge backgrounds
   "accent_amber": "#D97706",      # Caution states, pending indicators
   "accent_amber_light": "#FEF3C7",# Amber badge backgrounds
   "accent_purple": "#7C3AED",     # AI/agent features, innovation
   "accent_purple_light": "#EDE9FE",# Purple badge backgrounds
   "accent_indigo": "#4F46E5",     # Interactive highlights, focus rings
   "accent_indigo_light": "#E0E7FF",# Indigo badge backgrounds
   ```

2. **Replace the chart palette** with a perceptually distinct sequence:
   ```python
   CHART_PALETTE: list[str] = [
       _MAHOGANY,       # #800000 — primary series
       "#2563EB",       # accent_blue — second series
       _ONYX,           # #303A42 — third series
       "#0D9488",       # accent_teal — fourth series
       "#D97706",       # accent_amber — fifth series
   ]

   CHART_PALETTE_EXTENDED: list[str] = [
       _MAHOGANY,       # #800000
       "#2563EB",       # accent_blue
       _ONYX,           # #303A42
       "#0D9488",       # accent_teal
       "#D97706",       # accent_amber
       _RED,            # #FF0016
       "#7C3AED",       # accent_purple
       _IRON,           # #9BA6B1
       "#4F46E5",       # accent_indigo
       _ALLOY,          # #D4DBE0
   ]
   ```

3. **Add dark mode color overrides** as a parallel dict:
   ```python
   COLORS_DARK: dict[str, str] = {
       "background": "#0F1117",
       "surface": "#1A1D2E",
       "surface_raised": "#242838",
       "surface_sunken": "#0A0C14",
       "surface_overlay": "rgba(10, 12, 20, 0.8)",
       "text_primary": "#E2E8F0",
       "text_secondary": "#94A3B8",
       "border": "#2D3348",
       "success": "#34D399",
       "warning": "#FBBF24",
       "error": "#F87171",
       "success_bg": "rgba(16, 185, 129, 0.15)",
       "warning_bg": "rgba(251, 191, 36, 0.15)",
       "error_bg": "rgba(248, 113, 113, 0.15)",
   }
   ```

4. **Add a `get_colors(dark: bool = False)` helper** function:
   ```python
   def get_colors(dark: bool = False) -> dict[str, str]:
       """Return the appropriate color dict based on theme."""
       if dark:
           merged = {**COLORS, **COLORS_DARK}
           return merged
       return COLORS
   ```

5. **Update `_brand_css()`** to emit CSS custom properties for all new accent colors.

6. **Update `__all__`** to export: `COLORS_DARK`, `get_colors`, and any new dicts.

### Sub-steps
- [ ] Add all accent color entries to COLORS dict
- [ ] Replace CHART_PALETTE and CHART_PALETTE_EXTENDED
- [ ] Create COLORS_DARK dict
- [ ] Add get_colors() helper
- [ ] Update _brand_css() to include new CSS custom properties
- [ ] Update __all__ exports
- [ ] Run `python -c "from src.config.brand import *"` to verify no import errors
- [ ] Verify no hardcoded hex values leaked: `grep -rn '#[0-9a-fA-F]\{6\}' src/components/ src/pages/`

### Acceptance criteria
- `from src.config.brand import COLORS, COLORS_DARK, CHART_PALETTE, CHART_PALETTE_EXTENDED, get_colors` works
- `len(CHART_PALETTE) == 5` and all 5 colors are perceptually distinct (no two adjacent in same hue family)
- `len(CHART_PALETTE_EXTENDED) == 10`
- `get_colors(dark=True)["background"]` returns `"#0F1117"`
- All existing pages still render without errors
- New CSS custom properties `--color-accent-blue`, `--color-accent-teal`, etc. visible in browser dev tools

### Does NOT include
- Implementing dark mode toggle (separate ticket APE-P7-07)
- Changing any existing component or page files (subsequent tickets reference these tokens)

---

## APE-P7-02: Upgrade filter bar to chip-style design

**Assignee:** Frontend Engineer
**Priority:** Medium
**Depends on:** APE-P7-01
**Files to modify:** `src/components/filter_bar.py`

### Context
The gap analysis scored the filter bar 6/10. The mockup shows chip-style pill buttons with leading icons and dropdown carets. The live app uses native Streamlit radio buttons and multiselects, which are functional but visually inconsistent with the card-based design language.

### Requirements

1. **Replace date range radio buttons** with chip-style HTML pills:
   - Each chip: `height: 32px`, `padding: 0 14px`, `border-radius: 8px` (BORDER_RADIUS["md"])
   - Background: `COLORS["surface_sunken"]` (inactive), `hex_rgba(COLORS["accent_indigo"], 0.1)` (active)
   - Border: `0.5px solid COLORS["border"]` (inactive), `COLORS["accent_indigo"]` (active)
   - Text: `COLORS["text_primary"]` (inactive), `COLORS["accent_indigo"]` (active)
   - Render via `st.markdown()` with `unsafe_allow_html=True` + JavaScript click handlers that write to `st.session_state`

2. **Style the DMA/Channel/Product selects** with custom CSS targeting Streamlit's `[data-baseweb="select"]`:
   - Rounded corners matching BORDER_RADIUS["md"]
   - Border color from COLORS["border"], focus ring using accent_indigo
   - Label text in TYPOGRAPHY["sizes"]["sm"], uppercase, COLORS["text_secondary"]

3. **Add filter chip icons** using Unicode or st.markdown icon spans:
   - Date: 📅, DMA: 📍, Channel: 📡, Product: 📦

4. **Make the filter bar sticky** by wrapping in a `st.container()` with custom CSS:
   ```css
   [data-testid="stVerticalBlockBorderWrapper"]:has(.apex-filter-bar) {
       position: sticky;
       top: 0;
       z-index: 100;
       background: var(--color-background);
   }
   ```

### Sub-steps
- [ ] Create `_chip_html()` helper that generates a single chip pill
- [ ] Replace `st.radio` for date range with chip pills rendered via st.markdown
- [ ] Add CSS targeting to style Streamlit native selects
- [ ] Add icon prefixes to all filter labels
- [ ] Add sticky positioning CSS to _brand_css() or as local injection
- [ ] Test that filter state persists correctly in session_state after chip clicks
- [ ] Verify on Executive Scorecard and 2+ inner pages

### Acceptance criteria
- Date range shows as horizontal pill chips, not radio buttons
- Active chip has accent_indigo background tint and border
- All selects have rounded corners and brand-consistent styling
- Filter bar sticks to top on scroll
- Filter state changes propagate correctly to page data

### Does NOT include
- Compare toggle styling (covered by APE-P7-06)
- Export/Refresh button redesign (minor, leave as-is)

---

## APE-P7-03: Build custom topbar component

**Assignee:** Frontend Engineer
**Priority:** Medium
**Depends on:** APE-P7-01
**Files to create:** `src/components/topbar.py`
**Files to modify:** `src/config/brand.py` (CSS additions), each page file

### Context
The mockup has a 48px sticky topbar with page title, search input, theme toggle, notification bell with red dot, and user avatar. The live app has no topbar — the filter bar is the first element. This is the most visually prominent gap (scored 2/10).

### Requirements

1. **Create `src/components/topbar.py`** with a `render_topbar()` function:
   ```python
   def render_topbar(
       page_title: str,
       show_search: bool = True,
       show_notifications: bool = True,
       user_initials: str = "TO",
   ) -> None:
   ```

2. **Topbar layout** (rendered as a single `st.markdown()` HTML block):
   - Height: 48px, sticky at top (`position: sticky; top: 0; z-index: 200`)
   - Background: `COLORS["surface"]` with `border-bottom: 0.5px solid COLORS["border"]`
   - Left: page title in `TYPOGRAPHY["sizes"]["lg"]`, weight 500
   - Right: search input (decorative — placeholder "Search metrics..."), notification bell icon, user avatar circle
   - Avatar: 28px circle, `COLORS["accent_indigo"]` background, white initials

3. **Search input** is decorative for now (renders as styled div, not functional):
   - 200px wide, `COLORS["surface_sunken"]` background, `BORDER_RADIUS["md"]`, search icon + placeholder text

4. **Notification bell** shows a 6px red dot when there are active alerts:
   ```python
   def render_topbar(page_title: str, alert_count: int = 0, ...):
   ```

5. **Add topbar call** to every page file, right after the filter bar import. The topbar renders ABOVE the filter bar.

### Sub-steps
- [ ] Create `src/components/topbar.py` with render_topbar() function
- [ ] Build HTML template with page title, search, bell, avatar
- [ ] Add sticky positioning CSS
- [ ] Add notification dot logic (red dot when alert_count > 0)
- [ ] Import and call render_topbar() in `1_Executive_Scorecard.py`
- [ ] Import and call render_topbar() in all 8 remaining page files
- [ ] Update `src/components/__init__.py` to export render_topbar
- [ ] Verify topbar appears above filter bar on all pages

### Acceptance criteria
- Topbar renders on all 9 pages with correct page titles
- Topbar is sticky and stays above the filter bar on scroll
- Avatar shows "TO" initials in accent_indigo circle
- Notification bell shows red dot when alert_count > 0
- Search input is visually present (functionality deferred)

### Does NOT include
- Functional search (future phase)
- Theme toggle button (handled by APE-P7-07)

---

## APE-P7-04: Add charts row to Executive Scorecard

**Assignee:** Frontend Engineer
**Priority:** Medium
**Depends on:** APE-P7-01
**Files to modify:** `src/pages/1_Executive_Scorecard.py`, `src/components/chart_wrapper.py`

### Context
The mockup shows a 2:1 grid below the KPIs with a stacked area chart ("Funded account trend by channel") and a donut chart ("Channel mix"). The live app skipped this and goes straight to Financial Summary. This is a key visual element for the CMO landing page.

### Requirements

1. **Add a charts section** between the KPI cards and Financial Summary on the Executive Scorecard page.

2. **Left chart (2/3 width):** Stacked area chart
   - Title: "Funded account trend" (rendered via `card_container()`)
   - Subtitle: "Last 6 months, stacked by channel"
   - Chart type: Plotly filled area chart with `stackgroup='one'`
   - Series: Digital, Direct Mail, Branch, Call Center (use first 4 colors from CHART_PALETTE)
   - Data: Pull from existing `get_funded_account_data()` or mock with realistic numbers
   - Custom legend below chart (not Plotly default)

3. **Right chart (1/3 width):** Donut chart
   - Title: "Channel mix" (rendered via `card_container()`)
   - Subtitle: "Funded account attribution %"
   - Chart type: Plotly donut with `hole=0.65`
   - Same 4 channels, same 4 colors
   - Legend items below with percentage labels

4. **Layout:** Use `st.columns([2, 1])` to create the 2:1 grid.

5. **Both charts wrapped** in `card_container()` / `card_container_end()` pairs.

### Sub-steps
- [ ] Add import for chart_wrapper and card_container in Executive Scorecard
- [ ] Create the 2:1 column layout below KPI section
- [ ] Build stacked area chart using Plotly with CHART_PALETTE colors
- [ ] Build donut chart using Plotly with CHART_PALETTE colors and hole=0.65
- [ ] Add custom legend HTML below each chart
- [ ] Wrap both in card_container
- [ ] Verify visual alignment matches mockup proportion
- [ ] Test that charts render without errors with seed data

### Acceptance criteria
- Two charts visible below KPI cards on Executive Scorecard
- Area chart is stacked and shows 4 channel series
- Donut chart shows channel mix with percentages
- Both charts use CHART_PALETTE colors (no hardcoded hex)
- Both wrapped in card_container with title and subtitle
- Charts are responsive and don't overflow on standard 1080p+ screens

### Does NOT include
- Interactive drill-down on chart click
- Time range filtering on charts (uses same global filter)

---

## APE-P7-05: Add campaign performance table to Executive Scorecard

**Assignee:** Frontend Engineer
**Priority:** Medium
**Depends on:** APE-P7-01
**Files to modify:** `src/pages/1_Executive_Scorecard.py`, `src/components/data_table.py`

### Context
The mockup shows a campaign performance table below the charts with columns: Campaign, Status, Spend, Revenue, ROAS (color-coded badges), Funded, Budget pace (inline progress bar). The `data_table.py` component already has badge and progress bar renderers but the table isn't on the Executive Scorecard.

### Requirements

1. **Add a "Campaign performance" section** below the charts row on Executive Scorecard.

2. **Table columns:**
   | Column | Type | Renderer |
   |--------|------|----------|
   | Campaign | text, bold | Default |
   | Status | badge | Status dot (green=Active, amber=Paused, red=Ended) |
   | Spend | currency | Format as $XXK or $X.XM |
   | Revenue | currency | Format as $XXK or $X.XM |
   | ROAS | badge | Green badge if ≥3.0x, amber if 1.0-2.99x, red if <1.0x |
   | Funded | number | Comma-formatted |
   | Budget pace | progress bar | Inline bar, green <80%, amber 80-95%, red >95% |

3. **Use the existing `data_table.py` component** — call its render function with the campaign data and column config.

4. **Data source:** Pull from `get_campaign_summary()` in the data layer, or create mock data if the function doesn't exist:
   ```python
   MOCK_CAMPAIGNS = [
       {"campaign": "Q2 checking acquisition", "status": "Active", "spend": 1200000, "revenue": 5700000, "roas": 4.75, "funded": 2841, "budget_pct": 72},
       {"campaign": "Savings rate promo", "status": "Active", "spend": 680000, "revenue": 2400000, "roas": 3.53, "funded": 1204, "budget_pct": 88},
       {"campaign": "Brand awareness — national", "status": "Active", "spend": 890000, "revenue": 1100000, "roas": 1.24, "funded": 412, "budget_pct": 95},
       {"campaign": "Mortgage refinance retarget", "status": "Paused", "spend": 340000, "revenue": 204000, "roas": 0.60, "funded": 87, "budget_pct": 100},
   ]
   ```

5. **Wrap in `card_container()`** with title "Campaign performance" and subtitle "Top campaigns by ROAS".

### Sub-steps
- [ ] Create or locate campaign data source function
- [ ] Build column configuration dict for data_table component
- [ ] Add ROAS badge renderer (green/amber/red thresholds)
- [ ] Add budget pace progress bar renderer
- [ ] Add status dot renderer
- [ ] Place table in card_container below charts row
- [ ] Test rendering with mock data
- [ ] Verify badge colors come from brand.py tokens

### Acceptance criteria
- Campaign table visible on Executive Scorecard below charts
- ROAS column shows colored badges (green ≥3x, amber 1-3x, red <1x)
- Budget pace column shows inline colored progress bars
- Status column shows colored dots
- All colors from brand.py, no hardcoded hex
- Table wrapped in card_container with title/subtitle

### Does NOT include
- Sorting or filtering within the table
- Click-through to campaign detail pages

---

## APE-P7-06: Redesign sidebar to icon-rail style

**Assignee:** Frontend Engineer
**Priority:** Low
**Depends on:** APE-P7-01
**Files to modify:** `src/config/brand.py` (CSS), `src/app.py`

### Context
The mockup shows a 56px icon-only sidebar rail with tooltip labels. The live app has a 220px text sidebar with emoji prefixes. This is a significant visual difference but lower priority because the text sidebar is fully functional. Streamlit's sidebar is notoriously hard to override, so this ticket may require creative CSS hacking.

### Requirements

1. **Narrow the sidebar to 64px** (wider than mockup's 56px to accommodate Streamlit's padding):
   ```css
   section[data-testid="stSidebar"] {
       width: 64px !important;
       min-width: 64px !important;
   }
   section[data-testid="stSidebar"] > div {
       width: 64px !important;
       padding: 8px !important;
   }
   ```

2. **Hide nav link text, show only emojis** — the page files already have emoji prefixes (📊, 💰, etc.). Use CSS to:
   ```css
   [data-testid="stSidebarNavLink"] span {
       font-size: 0;          /* hide text */
       line-height: 0;
   }
   [data-testid="stSidebarNavLink"] span::first-letter {
       font-size: 18px;       /* show only emoji */
       line-height: 36px;
   }
   ```

3. **Add tooltip on hover** showing the full page name:
   ```css
   [data-testid="stSidebarNavLink"]:hover::after {
       content: attr(data-label);
       position: absolute;
       left: 72px;
       top: 50%;
       transform: translateY(-50%);
       /* styled tooltip */
   }
   ```
   Note: Streamlit may not support `data-label` attributes natively. If `::after` approach doesn't work, fall back to a narrower 120px sidebar that shows abbreviated page names.

4. **Move APEX branding block** — replace the text "APEX / MARKETING INTELLIGENCE" with a centered "A" logo pill:
   - 36px × 36px rounded square, `COLORS["primary"]` background, white "A" letter
   - Positioned at top of sidebar

5. **Hide the module guide expander** in icon-rail mode (too wide).

### Sub-steps
- [ ] Add CSS to narrow sidebar to 64px
- [ ] Add CSS to hide link text and enlarge emoji
- [ ] Test tooltip approach — try ::after first, fall back to narrower sidebar if needed
- [ ] Replace APEX text block with logo pill
- [ ] Hide module guide expander via CSS
- [ ] Test on all 9 pages — ensure active page highlight still works
- [ ] Test sidebar collapse/expand behavior
- [ ] Fall back gracefully if Streamlit version doesn't support the CSS selectors

### Acceptance criteria
- Sidebar is 64px wide (or 120px fallback with abbreviated names)
- Only emoji icons visible in default state
- Active page has red left-border highlight
- APEX logo pill at top
- No layout overflow or clipping issues

### Does NOT include
- Settings icon at sidebar bottom (future)
- Animated expand/collapse on hover

---

## APE-P7-07: Implement dark mode toggle and theme system

**Assignee:** Frontend Engineer
**Priority:** Medium
**Depends on:** APE-P7-01, APE-P7-03 (topbar must exist to host the toggle)
**Files to modify:** `src/config/brand.py`, `src/components/topbar.py`, all page files

### Context
The mockup has a dark/light theme toggle in the topbar. `brand.py` now has a `COLORS_DARK` dict (from APE-P7-01) but no mechanism to switch between themes at runtime. Streamlit has native dark mode support via `config.toml` and user system preferences, but we need the toggle to be in our topbar.

### Requirements

1. **Add a theme toggle button** to the topbar (modify `render_topbar()`):
   - Moon icon (🌙) when in light mode, sun icon (☀️) when in dark mode
   - Clicking toggles `st.session_state["apex_theme"]` between "light" and "dark"
   - Button uses `st.button()` with custom CSS, placed in topbar's right section

2. **Create `inject_theme_css(dark: bool)` function** in brand.py:
   - When `dark=True`, override all CSS custom properties with COLORS_DARK values
   - When `dark=False`, use standard COLORS values
   - Handle chart background, table background, card surface, text colors

3. **Update `_brand_css()`** to read `st.session_state.get("apex_theme", "light")` and conditionally apply dark styles.

4. **Update Plotly chart templates** in `chart_wrapper.py`:
   - `branded_chart_card()` should detect theme and apply appropriate `plot_bgcolor`, `paper_bgcolor`, `font.color`

5. **Update topbar, filter bar, card_container** to respect theme state.

### Sub-steps
- [ ] Add theme toggle button to topbar.py
- [ ] Create inject_theme_css() in brand.py
- [ ] Update _brand_css() to conditionally apply dark mode overrides
- [ ] Update chart_wrapper.py to detect and apply dark theme to Plotly figures
- [ ] Update card_container.py background colors for dark mode
- [ ] Update filter_bar.py chip/select colors for dark mode
- [ ] Test light ↔ dark toggle on Executive Scorecard
- [ ] Test on 2+ inner pages
- [ ] Verify all text remains readable in dark mode (contrast ratio ≥4.5:1)

### Acceptance criteria
- Theme toggle visible in topbar
- Clicking toggle switches between light and dark themes
- All text readable in both themes (WCAG AA contrast)
- Charts update colors when theme changes
- Cards, filters, sidebar all respect theme
- Theme preference persists within session (session_state)

### Does NOT include
- System preference detection (OS dark mode auto-switch)
- Per-user theme persistence across sessions

---

## APE-P7-08: Fix DuckDB CatalogException on Paid Channels page

**Assignee:** Backend Engineer
**Priority:** High — this is a runtime error visible to users
**Files to modify:** `src/pages/5_Paid_Channels.py`, `src/data/` (schema/seed files)

### Context
The Paid Channels page throws a DuckDB `CatalogException` at the bottom:
```
_duckdb.CatalogException: Catalog Error: Table with name social_platform_metrics does not exist! 
Did you mean "sqlite_temp_master"? LINE 9: FROM social_platform_metrics ^
```
This is visible to the user as a red error traceback on the page.

### Requirements

1. **Identify where `social_platform_metrics` is referenced** in the Paid Channels page:
   ```bash
   grep -rn "social_platform_metrics" src/
   ```

2. **Option A — Create the missing table:** If the schema is defined elsewhere (check `src/data/schema.sql`, `src/data/seed.py`, or similar):
   - Add the `social_platform_metrics` table to the schema
   - Add seed data matching the expected columns
   - Verify the query runs successfully

3. **Option B — Add graceful error handling:** If the table is intentionally deferred:
   ```python
   try:
       df = conn.execute("SELECT ... FROM social_platform_metrics").fetchdf()
   except duckdb.CatalogException:
       st.info("Social platform metrics data is not yet available.")
       df = pd.DataFrame()  # empty fallback
   ```

4. **Prefer Option A** (create the table). Only use Option B if the data source genuinely doesn't exist yet.

5. **Verify no other missing tables** across all pages:
   ```bash
   # Run each page's data queries and catch CatalogExceptions
   python -c "from src.data import get_engine; ..."
   ```

### Sub-steps
- [ ] grep for social_platform_metrics across entire src/ directory
- [ ] Check schema files for table definition
- [ ] If missing: create table in schema and add seed data
- [ ] If deferred: add try/except with user-friendly message
- [ ] Test Paid Channels page renders without errors
- [ ] Run all 9 pages and check for any other CatalogExceptions
- [ ] Fix any additional missing tables found

### Acceptance criteria
- Paid Channels page loads without any red error tracebacks
- All data sections on the page render (even if with empty/placeholder data)
- No CatalogException errors on any of the 9 pages
- Error handling is graceful — user sees an info message, not a stack trace

### Does NOT include
- Real production data integration
- Social platform API connections

---

## APE-P7-09: Fix REDIS_URL missing from settings.py

**Assignee:** Backend Engineer
**Priority:** Medium — blocks alert engine integration
**Files to modify:** `src/config/settings.py`
**Related:** APE-175 (existing bug)

### Context
APE-175 was filed earlier: `REDIS_URL` is missing from `src/config/settings.py`, which blocks `test_alerts_api.py`. This is the only open bug from the original Phase 1-5 work.

### Requirements

1. **Add REDIS_URL** to `src/config/settings.py`:
   ```python
   REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/0")
   ```

2. **Add a fallback** for environments without Redis:
   ```python
   REDIS_AVAILABLE: bool = True
   try:
       import redis
       _r = redis.from_url(REDIS_URL)
       _r.ping()
   except Exception:
       REDIS_AVAILABLE = False
   ```

3. **Update any code that imports REDIS_URL** to check `REDIS_AVAILABLE` first.

4. **Update test_alerts_api.py** to skip Redis-dependent tests when `REDIS_AVAILABLE is False`:
   ```python
   @pytest.mark.skipif(not settings.REDIS_AVAILABLE, reason="Redis not available")
   ```

### Sub-steps
- [ ] Add REDIS_URL to settings.py with env var fallback
- [ ] Add REDIS_AVAILABLE bool with connection check
- [ ] grep for all REDIS_URL imports and update to check availability
- [ ] Update test_alerts_api.py with skip decorators
- [ ] Run tests to verify they pass (or skip gracefully)
- [ ] Verify alert engine still works when Redis IS available

### Acceptance criteria
- `from src.config.settings import REDIS_URL, REDIS_AVAILABLE` works
- App starts without errors even when Redis is not running
- test_alerts_api.py passes (or skips cleanly) in both Redis/no-Redis environments
- Alert engine functions normally when Redis is available

### Does NOT include
- Alert engine refactoring
- Redis deployment or Docker compose changes

---

## APE-P7-10: Scan all pages for runtime errors and missing data

**Assignee:** Backend Engineer
**Priority:** High
**Depends on:** APE-P7-08, APE-P7-09

### Context
The DuckDB error on Paid Channels suggests there may be other runtime errors lurking on pages we haven't visited. This ticket is a systematic sweep of all 9 pages to find and fix any remaining errors.

### Requirements

1. **Visit each of the 9 pages programmatically** and capture any errors:
   - 1_Executive_Scorecard.py
   - 2_Spend_Allocation.py
   - 3_Acquisition_Funnel.py
   - 4_Onboarding_Retention.py
   - 5_Paid_Channels.py
   - 6_Organic_AEO.py
   - 7_Product_Experience.py
   - 8_Operations_Command.py
   - 9_Simulator.py

2. **For each page, check:**
   - Does it load without Python exceptions?
   - Are all data queries resolving (no CatalogException, no KeyError)?
   - Are all component imports working?
   - Are charts rendering (no empty figure errors)?

3. **Fix each error found** with either:
   - Adding missing table/data (preferred)
   - Adding graceful error handling with st.info() fallback

4. **Document findings** — create a brief report of what was found and fixed.

### Sub-steps
- [ ] Create a test script that imports and validates each page's data functions
- [ ] Run against all 9 pages
- [ ] Catalog all errors with page, line number, error type
- [ ] Fix each error (create missing tables or add error handling)
- [ ] Re-run validation to confirm zero errors
- [ ] Document all fixes

### Acceptance criteria
- All 9 pages load without any red error tracebacks
- All data sections render (even with placeholder data)
- A summary of fixes is documented in the issue

### Does NOT include
- Performance optimization
- Data accuracy validation

---

## APE-P7-QA: Phase 7 comprehensive QA acceptance matrix

**Assignee:** QA Engineer
**Priority:** Critical — all other Phase 7 tickets route here on completion
**Blocked by:** All APE-P7-01 through APE-P7-10

### Context
This is the QA gate for Phase 7. It incorporates all 10 dimensions from the mockup-vs-live gap analysis plus new requirements from the expanded brand palette and bug fixes. Every ticket in this phase must pass this QA matrix before the phase is marked complete.

### QA acceptance matrix

#### A. Brand & tokens (from APE-P7-01)
- [ ] `COLORS` dict includes all accent colors (blue, teal, amber, purple, indigo) with light variants
- [ ] `CHART_PALETTE` has 5 perceptually distinct colors
- [ ] `CHART_PALETTE_EXTENDED` has 10 colors
- [ ] `COLORS_DARK` dict exists with all dark mode overrides
- [ ] `get_colors(dark=True)` returns dark palette
- [ ] `grep -rn '#[0-9a-fA-F]\{6\}' src/components/ src/pages/` — ZERO matches outside brand.py
- [ ] All CSS custom properties present in browser dev tools (including --color-accent-*)

#### B. Filter bar (from APE-P7-02)
- [ ] Date range renders as chip-style pills (not radio buttons)
- [ ] Active chip has accent color tint and border
- [ ] DMA/Channel/Product selects have rounded corners and brand styling
- [ ] Filter bar sticks to top on scroll
- [ ] Filter selections persist across page navigation

#### C. Topbar (from APE-P7-03)
- [ ] Topbar visible on all 9 pages with correct page title
- [ ] Search input present (decorative is OK)
- [ ] Notification bell with red dot when alerts > 0
- [ ] User avatar with "TO" initials
- [ ] Topbar is sticky above filter bar

#### D. Charts on Executive Scorecard (from APE-P7-04)
- [ ] Stacked area chart visible below KPIs showing 4 channel series
- [ ] Donut chart visible next to area chart showing channel mix percentages
- [ ] Both charts use CHART_PALETTE colors
- [ ] Both wrapped in card_container with title/subtitle
- [ ] Charts are responsive (no overflow)

#### E. Campaign table on Executive Scorecard (from APE-P7-05)
- [ ] Campaign performance table visible below charts
- [ ] ROAS badges: green (≥3x), amber (1-3x), red (<1x)
- [ ] Budget pace shows inline progress bars with color coding
- [ ] Status column shows colored dots
- [ ] Table wrapped in card_container

#### F. Sidebar (from APE-P7-06)
- [ ] Sidebar is narrower than current 220px (64px ideal, 120px acceptable)
- [ ] Only icons/emojis visible (full text hidden or abbreviated)
- [ ] Active page has red highlight
- [ ] APEX branding present (logo pill or abbreviated)
- [ ] No layout overflow or clipping

#### G. Dark mode (from APE-P7-07)
- [ ] Theme toggle in topbar
- [ ] Clicking toggle switches all colors
- [ ] Text readable in both themes (contrast ≥4.5:1)
- [ ] Charts update to dark theme
- [ ] Cards, filters, sidebar all respect theme

#### H. Runtime stability (from APE-P7-08, APE-P7-09, APE-P7-10)
- [ ] All 9 pages load without red error tracebacks
- [ ] No CatalogException on any page
- [ ] REDIS_URL in settings.py with graceful fallback
- [ ] Paid Channels page specifically: no social_platform_metrics error
- [ ] App starts without errors even without Redis

#### I. Cross-cutting checks
- [ ] All colors sourced from brand.py (grep audit passes)
- [ ] Libre Franklin font loads and renders on all text
- [ ] No pure #000000 or #FFFFFF anywhere (brand constraint)
- [ ] Card hover transitions (shadow + translateY) work on metric cards
- [ ] Scrollbars use brand styling (thin, iron-colored)
- [ ] Streamlit default chrome (hamburger menu, footer) hidden
- [ ] Version label (v0.1.0) visible in sidebar

#### J. Regression checks
- [ ] All Phase 1-5 functionality still works (navigation, data loading, filtering)
- [ ] No new console errors in browser dev tools
- [ ] Page load time ≤3 seconds for Executive Scorecard
- [ ] All 9 pages accessible via sidebar navigation

### Test procedure
1. Start the app: `streamlit run src/app.py`
2. Navigate to each of the 9 pages via sidebar
3. On each page: check for errors, verify filters work, verify brand consistency
4. Run the grep audit for hardcoded hex values
5. Test dark mode toggle on 3+ pages
6. Test browser resize to 1024px width for responsive check
7. Document pass/fail for each checkbox above

### Acceptance criteria
- ALL checkboxes above pass (100% pass rate required for phase sign-off)
- Written QA report with pass/fail for each item
- Screenshots of Executive Scorecard in both light and dark mode
- Screenshot of any remaining issues (if waived with justification)

---
