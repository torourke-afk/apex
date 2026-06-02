# Apex UX/UI Redesign — Frontend Backlog

> **Epic:** APE-UX — Modernize all 9 Apex dashboard modules to match the CMO Marketing Dashboard design system.
> **Owner:** Frontend Engineer agent
> **Design reference:** `docs/ux-redesign-mockup-reference.html` (open in browser for visual target)
> **Design system spec:** `CMO Marketing Dashboard — Design System & Build Skill.md` (in second-brain)
> **Priority:** Execute in order — each ticket builds on the prior one.
> **Hard rule:** All colors MUST come from `src/config/brand.py`. No hardcoded hex values anywhere.

---

## How to use this document

Each ticket below is a self-contained unit of work for the Frontend Engineer agent. The Tech Lead should copy individual tickets into `tasks/current/frontend-ux-*.md` files in execution order. Each ticket lists:

- **What to change** — exact files and functions
- **What it should look like** — mapped to the design reference
- **Acceptance criteria** — testable conditions
- **Does NOT include** — scope boundaries to prevent drift

---

## APE-UX-01: Modernize brand.py design token system

**Status:** TODO
**Blocks:** All other APE-UX tickets
**Files to modify:** `src/config/brand.py`

### Context
The current `brand.py` has a solid foundation (COLORS dict, TYPOGRAPHY dict, SPACING dict, CSS injection). This ticket extends it with modern dashboard tokens needed by all subsequent tickets — specifically elevated surface colors, a richer spacing scale, motion tokens, and dark mode readiness.

### Requirements

1. **Add surface hierarchy tokens** to the `COLORS` dict:
   ```python
   "surface_raised": "#FFFFFF",     # Cards that sit above the background
   "surface_sunken": "#E8ECEF",     # Recessed areas (filter bar bg, input fields)
   "surface_overlay": "#FFFFFF",    # Modals, dropdowns, tooltips
   ```

2. **Add chart accent palette** (extend `CHART_PALETTE` with a secondary set for when >5 series are needed):
   ```python
   CHART_PALETTE_EXTENDED: list[str] = [
       _MAHOGANY, _RED, _ONYX, _IRON, _ALLOY,
       "#2E7D52",   # success green
       "#C97B1A",   # warning amber
       "#4A6FA5",   # steel blue
   ]
   ```

3. **Extend SPACING** with `xxs` (2px) and `xxxl` (64px) tokens.

4. **Add BORDER_RADIUS dict**:
   ```python
   BORDER_RADIUS: dict[str, str] = {
       "sm": "6px",
       "md": "8px",
       "lg": "12px",
       "xl": "16px",
       "full": "9999px",
   }
   ```

5. **Add MOTION dict** for transition tokens:
   ```python
   MOTION: dict[str, str] = {
       "duration_fast": "150ms",
       "duration_normal": "250ms",
       "duration_slow": "400ms",
       "ease_out": "cubic-bezier(0.16, 1, 0.3, 1)",
       "ease_in_out": "cubic-bezier(0.45, 0, 0.55, 1)",
   }
   ```

6. **Update `_brand_css()` function** to include:
   - CSS custom properties (`:root { --rvgt-bg: ...; }`) for all tokens so components can reference them in inline HTML
   - Increased `.block-container` max-width to `1600px` with `padding: 1.5rem 2rem`
   - Card hover transition: `transition: box-shadow 150ms ease, transform 150ms ease;`
   - Updated border-radius on `[data-testid="metric-container"]` from `6px` to `12px`

7. **Export all new dicts** from the module and update `__all__` if present.

### Acceptance criteria
- `from src.config.brand import COLORS, TYPOGRAPHY, SPACING, BORDER_RADIUS, MOTION, CHART_PALETTE_EXTENDED` works
- All existing pages still render without errors (no breaking changes to existing COLORS/TYPOGRAPHY/SPACING keys)
- `grep -rn '#[0-9a-fA-F]\{6\}' src/components/ src/pages/` shows zero matches outside of `brand.py`
- New CSS custom properties visible in browser dev tools when Streamlit runs

### Does NOT include
- Dark mode implementation (future ticket)
- Changes to any page files or component files (those come in subsequent tickets)

---

## APE-UX-02: Redesign KPI card component

**Status:** TODO
**Blocks:** APE-UX-05 (Scorecard page)
**Depends on:** APE-UX-01
**Files to modify:** `src/components/kpi_card.py`

### Context
The current `kpi_card()` function works but looks dated compared to the design reference. The mockup shows cards with: icon in the label row, larger value font with tighter letter-spacing, a colored delta with directional arrow, and an integrated sparkline with gradient fill that flows into the card bottom.

### Requirements

1. **Update card HTML template** in `kpi_card()`:
   - Border-radius: use `BORDER_RADIUS["lg"]` (12px) — already partially done, keep consistent
   - Add subtle box-shadow on hover (via CSS class, not inline): `box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07); transform: translateY(-1px);`
   - Value font size: increase from `1.9rem` to `2.2rem`
   - Add `letter-spacing: -0.02em` to the value
   - Label: keep uppercase, but reduce font-size to `0.65rem` and add a leading icon slot

2. **Add `icon` parameter** to `kpi_card()`:
   ```python
   def kpi_card(
       title: str,
       value: float,
       delta: float = None,
       delta_pct: float = None,
       sparkline_data: list = None,
       format_type: str = "number",
       alert_status: str | None = None,
       alert_text: str | None = None,
       icon: str | None = None,          # NEW — emoji or HTML icon string
       invert_delta: bool = False,        # NEW — True for metrics where increase = bad (CPA, CPIHH)
   ) -> None:
   ```

3. **Implement `invert_delta` logic**: When `True`, positive delta renders in `COLORS["error"]` (red) and negative delta renders in `COLORS["success"]` (green). This is critical for cost metrics like CPIHH and CAC where going up is bad.

4. **Update sparkline rendering**: Move the sparkline `<div>` inside the card container (currently it's a separate `st.markdown` + `st.plotly_chart` call which creates a visual gap). Render it as part of the same HTML block by embedding a small inline SVG or keep Plotly but reduce margin to zero.

5. **Add hover interaction CSS** in the `_brand_css()` output or as a component-level style block:
   ```css
   .apex-kpi-card {
     transition: box-shadow 150ms ease, transform 150ms ease;
     cursor: pointer;
   }
   .apex-kpi-card:hover {
     box-shadow: 0 4px 6px -1px rgba(0,0,0,0.07), 0 2px 4px -2px rgba(0,0,0,0.05);
     transform: translateY(-1px);
   }
   ```

### Acceptance criteria
- `kpi_card(title="CPIHH", value=677, delta=32, invert_delta=True)` renders with red delta (increase is bad)
- `kpi_card(title="Revenue", value=2400000, format_type="currency", icon="💰")` shows icon before label
- Cards have visible hover lift effect in browser
- Sparkline integrates seamlessly into card bottom (no gap)
- All existing callers in `1_Executive_Scorecard.py` still work (backward compatible — new params are optional)

### Does NOT include
- Click-to-drill-down behavior (future ticket)
- Dark mode styling (handled by APE-UX-01 CSS variables)

---

## APE-UX-03: Redesign filter bar component

**Status:** TODO
**Depends on:** APE-UX-01
**Files to modify:** `src/components/filter_bar.py`

### Context
The current filter bar uses Streamlit's default `st.selectbox` and `st.multiselect` in columns. The design reference shows a more compact, chip-style filter bar with pill-shaped controls that sits sticky below the top bar.

### Requirements

1. **Update the `_FILTER_CSS` string** with modern styling:
   - Container: `background: {COLORS['surface_sunken']}`; `border-radius: {BORDER_RADIUS["lg"]}`; `padding: 0.625rem 1rem`
   - Remove the current `border: 1px solid` — use subtle background differentiation instead
   - Add sticky positioning hint (note: Streamlit doesn't natively support sticky, but CSS can help):
     ```css
     .filter-bar-container {
       position: sticky;
       top: 0;
       z-index: 100;
     }
     ```

2. **Add date preset chips** — render the date presets (Last 30d, 60d, 90d, Custom) as chip-style buttons instead of a selectbox. Use `st.columns` with tight spacing and `st.button` styled via CSS to look like pills:
   ```css
   .filter-chip {
     display: inline-flex;
     align-items: center;
     gap: 4px;
     padding: 4px 12px;
     border-radius: 8px;
     border: 0.5px solid {COLORS['border']};
     background: {COLORS['surface']};
     font-size: 0.75rem;
     cursor: pointer;
   }
   .filter-chip.active {
     background: rgba(255, 0, 22, 0.08);  /* RVGT Red at 8% */
     border-color: {COLORS['primary']};
     color: {COLORS['primary']};
   }
   ```

3. **Add a "Compare" toggle** — a simple `st.toggle` or checkbox that enables period-over-period comparison mode. Store in session state as `{key_prefix}_filter_compare`.

4. **Add Export and Refresh buttons** at the right end of the filter bar using `st.button` styled as small outlined buttons.

5. **Return `compare` key** in the filter dict:
   ```python
   return {
       ...existing keys...,
       "compare": st.session_state.get(f"{key_prefix}_filter_compare", False),
   }
   ```

### Acceptance criteria
- Filter bar renders as a single horizontal strip with chip-style controls
- Active date preset is visually highlighted with RVGT Red accent
- Compare toggle returns boolean in filter dict
- All existing callers (`1_Executive_Scorecard.py`, `2_Spend_Allocation.py`, etc.) still work — new features are additive
- Filter bar sticks to top when scrolling (best effort within Streamlit constraints)

### Does NOT include
- Actual comparison data logic (that's a backend/data ticket)
- Mobile-specific filter sheet (Streamlit handles responsive layout)

---

## APE-UX-04: Redesign section header and card container components

**Status:** TODO
**Depends on:** APE-UX-01
**Files to modify:** `src/components/section_header.py`, NEW: `src/components/card_container.py`

### Context
The design reference uses consistent card containers for every chart and table section. The section headers are simpler (no HR divider) with just a title + subtitle. We need a reusable card wrapper.

### Requirements

1. **Simplify `section_header()`**:
   - Remove the `<hr>` divider — the design reference uses whitespace and cards to create visual separation
   - Increase title font size to `TYPOGRAPHY["sizes"]["xl"]` (already there)
   - Make subtitle optional and lighter: `font-size: 0.8125rem; color: {COLORS["text_secondary"]}`
   - Add optional `action` parameter for a right-aligned button/link:
     ```python
     def section_header(title: str, subtitle: str = None, icon: str = None, action: str = None) -> None:
     ```
     When `action` is set, render a small text link on the right side of the header row.

2. **Create `src/components/card_container.py`** — a reusable card wrapper:
   ```python
   def card_container(
       title: str = None,
       subtitle: str = None,
       actions: list[dict] = None,  # [{"label": "Monthly", "active": True}, {"label": "Weekly"}]
   ) -> None:
   ```
   This function:
   - Opens a `<div>` with card styling: `background: {COLORS['surface']}; border: 0.5px solid {COLORS['border']}; border-radius: {BORDER_RADIUS['lg']}; padding: 1rem 1.25rem;`
   - Renders the optional header row (title left, action buttons right)
   - Does NOT close the div — the caller adds chart/table content after, then calls `card_container_end()`

   Also provide:
   ```python
   def card_container_end() -> None:
       st.markdown("</div>", unsafe_allow_html=True)
   ```

   **Alternative approach** (if nested HTML is flaky in Streamlit): Use `st.container()` with CSS class injection:
   ```python
   def card(title=None, subtitle=None):
       """Returns a context manager that wraps content in a styled card."""
       # Implementation using st.container + st.markdown for header
   ```

3. **Register in `src/components/__init__.py`**:
   ```python
   from src.components.card_container import card_container, card_container_end
   ```

### Acceptance criteria
- `section_header("Executive KPIs", icon="📊")` renders without the HR divider
- `section_header("Campaign Performance", action="View All →")` shows the action link
- `card_container(title="Revenue trend", subtitle="Last 6 months")` creates a styled card wrapper
- Existing pages render without errors

### Does NOT include
- Collapsible/expandable card state
- Drag-and-drop card reordering

---

## APE-UX-05: Redesign Executive Scorecard page

**Status:** TODO
**Depends on:** APE-UX-01, APE-UX-02, APE-UX-03, APE-UX-04
**Files to modify:** `src/pages/1_Executive_Scorecard.py`

### Context
This is the CMO landing page and the most important view. The design reference shows a clear vertical hierarchy: filter bar → KPI row (5 cards) → primary chart (trend line) → secondary charts (2-up) → alert feed. The current page has KPIs, financial strip, scenarios, and alerts but lacks the chart visualizations and modern layout flow.

### Requirements

1. **Replace the page header** with a simpler format matching the mockup:
   ```python
   st.markdown(
       f"""<div style="margin-bottom: 1rem;">
         <h1 style="color:{COLORS['secondary']};font-family:{ff};font-size:1.75rem;
                     font-weight:700;margin-bottom:0.15rem;line-height:1.2;">
           Executive Scorecard</h1>
         <p style="color:{COLORS['text_secondary']};font-family:{ff};font-size:0.8125rem;margin:0;">
           CMO Dashboard · {datetime.datetime.now().strftime('%B %d, %Y')}</p>
       </div>""",
       unsafe_allow_html=True,
   )
   ```

2. **Add filter bar** at the top:
   ```python
   from src.components import filter_bar
   filters = filter_bar(key_prefix="scorecard", show_product=False)
   ```

3. **Reorganize KPI row to 5-across** (currently 4+3). Use the design reference layout:
   ```python
   kpi_cols = st.columns(5)
   ```
   Map the 7 existing KPIs to 5 hero metrics: Total Media Spend, Applications, Funded Accounts, CPIHH (with `invert_delta=True`), ROAS. Move the remaining 2 KPIs into the financial summary strip.

4. **Add primary chart section** — a stacked area chart showing funded accounts by channel over time. Use `branded_chart()` from `chart_wrapper.py`:
   ```python
   import plotly.graph_objects as go
   from src.components import branded_chart, card_container, card_container_end

   card_container(title="Funded account trend by channel", subtitle="Last 6 months")
   fig = go.Figure()
   # Add traces per channel from data layer
   for channel, data in channel_trends.items():
       fig.add_trace(go.Scatter(
           x=data["months"], y=data["funded"],
           name=channel, fill="tonexty",
           line=dict(width=1.5),
       ))
   branded_chart(fig, height=300)
   card_container_end()
   ```

5. **Add secondary charts row** — 2 columns:
   - Left: Channel mix donut chart using `go.Pie` with `hole=0.7`
   - Right: Keep the financial summary strip (from `metric_strip`)

6. **Restyle alert feed**: Keep the existing alert feed logic but wrap it in a `card_container()` and update the individual alert row styling to match the mockup (softer backgrounds, larger gap between badge and text).

7. **Remove the saved scenarios section** from this page (it belongs in Simulator or can stay but move below alerts).

### Layout hierarchy (top to bottom)
```
1. Page header (title + date)
2. Filter bar (date, DMA, channel)
3. KPI row (5 cards, single row)
4. Primary chart card (funded account trend, full width)
5. Two-column row:
   a. Channel mix donut (card)
   b. Financial summary strip (card)
6. Alert feed (card)
```

### Acceptance criteria
- Page follows the mockup's vertical hierarchy exactly
- 5 KPI cards render in a single row
- CPIHH card shows red delta (cost metric going up = bad)
- Area chart renders with RVGT brand colors via `branded_chart()`
- Donut chart shows channel mix with center text
- Filter bar is functional and date changes re-query data
- Alert feed retains all existing functionality (filter, acknowledge, view details)
- Page loads in < 3 seconds with seed data

### Does NOT include
- Real-time data updates (stays as page-load queries)
- Agent command bar (future phase)
- Compare mode data (just the toggle UI)

---

## APE-UX-06: Redesign data table component

**Status:** TODO
**Depends on:** APE-UX-01
**Files to modify:** `src/components/data_table.py`

### Context
The current `data_table()` wraps `streamlit-aggrid` with RVGT styling. The design reference shows a cleaner table with: lighter header (not dark Onyx), inline progress bars, ROAS badges with conditional coloring, and status dots.

### Requirements

1. **Lighten the header row**: Change from Onyx background to Platinum:
   ```python
   header_bg = COLORS["background"]     # Platinum #F1F4F7 (was Onyx)
   header_text = COLORS["text_primary"]  # Onyx (was Platinum)
   ```

2. **Add helper functions** for inline cell renderers:

   ```python
   def badge_cell_renderer(thresholds: dict = None) -> JsCode:
       """Returns a JsCode cell renderer that shows a colored badge.

       Parameters
       ----------
       thresholds : dict
           {"green": 3.0, "amber": 1.5}
           Values >= green threshold get green badge,
           >= amber get amber, below get red.
       """
       # Return JsCode that renders <span class="badge green/amber/red">value</span>
   ```

   ```python
   def progress_bar_renderer(max_value: float = 100) -> JsCode:
       """Returns a JsCode cell renderer that shows an inline progress bar."""
       # Return JsCode rendering a small bar with color based on fill %
       # <80% = green, 80-95% = amber, >95% = red
   ```

   ```python
   def status_dot_renderer() -> JsCode:
       """Returns a JsCode renderer for status column (Active/Paused/Stopped)."""
       # Renders a colored dot + text
   ```

3. **Update default grid options**:
   - Row height: `40px` (was 36px) for more breathing room
   - Header height: `44px` (was 40px)
   - Remove cell right-border: `"border-right": "none"` in `.ag-cell`
   - Add alternating row colors using lighter shades
   - Row hover: use `rgba(255, 0, 22, 0.04)` (very subtle RVGT Red) instead of Alloy

4. **Add column configuration helpers**:
   ```python
   def configure_campaign_table(gb: GridOptionsBuilder) -> None:
       """Pre-configures columns for the standard campaign performance table."""
       gb.configure_column("Campaign", pinned="left", width=200)
       gb.configure_column("Status", cellRenderer=status_dot_renderer(), width=100)
       gb.configure_column("ROAS", cellRenderer=badge_cell_renderer({"green": 3.0, "amber": 1.5}), width=100)
       gb.configure_column("Budget Pace", cellRenderer=progress_bar_renderer(), width=140)
   ```

### Acceptance criteria
- Table header is light (Platinum bg, dark text) — not dark Onyx
- ROAS column shows colored badges (green ≥3x, amber ≥1.5x, red <1.5x)
- Budget pace column shows inline progress bars with color coding
- Status column shows colored dots (green=Active, amber=Paused, red=Stopped)
- Table renders correctly with seed data from any page that uses `data_table()`
- No regressions in existing table usage (backward compatible)

### Does NOT include
- Row selection / batch actions
- Inline editing
- Export to CSV (handled by Streamlit's built-in)

---

## APE-UX-07: Redesign chart wrapper with card integration

**Status:** TODO
**Depends on:** APE-UX-01, APE-UX-04
**Files to modify:** `src/components/chart_wrapper.py`

### Context
The current `branded_chart()` applies colors and renders. The design reference shows charts always inside card containers with a header row (title, subtitle, optional toggle buttons). We need the chart wrapper to integrate with the card container.

### Requirements

1. **Add `branded_chart_card()` convenience function** that wraps a Plotly figure in a card:
   ```python
   def branded_chart_card(
       fig: go.Figure,
       title: str,
       subtitle: str = None,
       height: int = 300,
       toggles: list[str] = None,  # ["Monthly", "Weekly"] — style as pill buttons
       key: str = None,
   ) -> None:
       """Renders a Plotly chart inside a styled card container with header."""
   ```
   This function:
   - Renders the card container `<div>` with header row
   - Applies brand styling to the figure
   - Calls `st.plotly_chart()` inside the card
   - Closes the card div

2. **Update chart background**: Change `paper_bgcolor` and `plot_bgcolor` from `surface` to `"rgba(0,0,0,0)"` (transparent) so the card container background shows through cleanly.

3. **Add donut chart helper**:
   ```python
   def branded_donut(
       labels: list[str],
       values: list[float],
       title: str = None,
       center_text: str = None,  # e.g., "$2.4M" displayed in the donut hole
       height: int = 300,
       key: str = None,
   ) -> None:
       """Renders a branded donut chart (pie with hole=0.7) inside a card."""
   ```

4. **Update `waterfall_chart()`**: Change `paper_bgcolor` from `COLORS["platinum"]` to transparent, and update the bar styling to use softer rounded corners.

### Acceptance criteria
- `branded_chart_card(fig, title="Revenue trend", subtitle="Last 6 months", toggles=["Monthly", "Weekly"])` renders a complete card with chart
- `branded_donut(labels, values, center_text="$2.4M")` renders donut with center text
- Charts have transparent backgrounds (card provides the background)
- All existing `branded_chart()` callers still work (new functions are additive)

### Does NOT include
- Chart animation tokens (Plotly handles its own animations)
- Custom tooltip templates

---

## APE-UX-08: Redesign metric strip component

**Status:** TODO
**Depends on:** APE-UX-01
**Files to modify:** `src/components/metric_strip.py`

### Context
The metric strip shows 3–6 financial summary metrics in a horizontal row. The design reference shows these as smaller, more compact cards with the value prominent and the label above in small caps.

### Requirements

1. **Update card styling**:
   - Border-radius: `BORDER_RADIUS["lg"]` (12px)
   - Padding: `1rem 1.25rem` (tighter than current)
   - Label: `font-size: 0.65rem` (smaller), add `letter-spacing: 0.08em`
   - Value: `font-size: 1.5rem` (was `xxl` / 1.75rem), `font-weight: 700`

2. **Add delta percentage display** alongside absolute delta:
   ```python
   def metric_strip(metrics: list[dict]) -> None:
       """
       metrics: list of dicts with keys:
         - label: str
         - value: str | float
         - delta: float (optional)
         - delta_pct: float (optional)  # NEW
         - format: str (optional)
       """
   ```

3. **Support `name` key as alias for `label`** — the scorecard data layer returns dicts with `name` not `label`. Add: `label = str(m.get("label", m.get("name", "")))` to handle both.

### Acceptance criteria
- Metric strip renders with updated sizing
- Both `label` and `name` keys work in the metric dict
- Delta percentage shows when provided
- Financial summary on Executive Scorecard page still renders correctly

---

## APE-UX-09: Redesign sidebar navigation

**Status:** TODO
**Depends on:** APE-UX-01
**Files to modify:** `src/app.py`, `src/config/brand.py` (CSS section)

### Context
The design reference shows a narrow icon sidebar (56px collapsed) with icons for each module. Streamlit's native sidebar is wider and text-based. We can't fully replicate the mockup's sidebar, but we can modernize the Streamlit sidebar significantly.

### Requirements

1. **Update sidebar CSS in `_brand_css()`**:
   - Reduce sidebar width: `section[data-testid="stSidebar"] { width: 220px !important; min-width: 220px !important; }`
   - Add module icons before each nav link using `::before` pseudo-elements or update the page filenames to include emoji prefixes
   - Improve active state: brighter RVGT Red background, thicker left border (4px)
   - Add subtle hover effect on nav links:
     ```css
     [data-testid="stSidebarNavLink"]:hover {
       background-color: rgba(255, 0, 22, 0.06) !important;
       transition: background-color 150ms ease;
     }
     ```

2. **Update `src/app.py` sidebar header**:
   - Increase "APEX" logo text size to 32px
   - Add a version number or "v2.0" badge below
   - Add the current user context (e.g., "RVGT · CMO Dashboard")

3. **Rename page files** to include emoji icons for the sidebar:
   ```
   src/pages/1_📊_Executive_Scorecard.py
   src/pages/2_💰_Spend_Allocation.py
   src/pages/3_🔄_Acquisition_Funnel.py
   src/pages/4_🏠_Onboarding_Retention.py
   src/pages/5_📢_Paid_Channels.py
   src/pages/6_🔍_Organic_AEO.py
   src/pages/7_🛠️_Product_Experience.py
   src/pages/8_⚙️_Operations_Command.py
   src/pages/9_🧮_Simulator.py
   ```
   **IMPORTANT:** After renaming, update ALL `st.switch_page()` calls across all pages (currently in `1_Executive_Scorecard.py` at line 237 in `_KPI_PAGE_MAP`). Search for every `src/pages/` reference in the codebase.

4. **Add a collapsible sidebar toggle** hint:
   ```python
   st.sidebar.markdown(
       f"<div style='text-align:center;padding:0.5rem;font-size:11px;color:{COLORS['iron']};'>"
       "Press [ to collapse sidebar"
       "</div>",
       unsafe_allow_html=True,
   )
   ```

### Acceptance criteria
- Sidebar is narrower (220px) with icons before each module name
- Active page has a prominent RVGT Red indicator
- All `st.switch_page()` calls work after file renames
- `streamlit run src/app.py` launches with updated sidebar

### Does NOT include
- Collapsible icon-only mode (Streamlit doesn't support this natively)
- Custom sidebar widgets beyond navigation

---

## APE-UX-10: Modernize app.py landing page

**Status:** TODO
**Depends on:** APE-UX-01, APE-UX-09
**Files to modify:** `src/app.py`

### Context
The current landing page shows a grid of 9 module cards. The design reference suggests this should either redirect to the Executive Scorecard immediately OR show a more polished module picker.

### Requirements

1. **Auto-redirect to Executive Scorecard** if the user has visited before:
   ```python
   if st.session_state.get("has_visited", False):
       st.switch_page("src/pages/1_📊_Executive_Scorecard.py")
   st.session_state["has_visited"] = True
   ```

2. **Redesign the module cards** with the updated card styling:
   - Use `BORDER_RADIUS["lg"]` (12px)
   - Add hover effect (subtle shadow lift)
   - Larger icon (32px)
   - Module name in `font-weight: 600; font-size: 0.9375rem`
   - Description in `font-size: 0.8125rem; color: {COLORS['text_secondary']}`
   - Add a subtle "→" arrow on hover

3. **Add a welcome header** with user context:
   ```
   Welcome back, Tyler
   Select a module to get started.
   ```

### Acceptance criteria
- First visit shows the module picker
- Subsequent visits auto-redirect to Executive Scorecard
- Module cards have hover effects
- All 9 module links work (point to renamed page files from APE-UX-09)

---

## APE-UX-11: Apply card-based layout to all 8 remaining pages

**Status:** TODO
**Depends on:** APE-UX-01 through APE-UX-07
**Files to modify:** All files in `src/pages/` (2 through 9)

### Context
After the Executive Scorecard is redesigned, all other pages need the same treatment: filter bar at top, KPI row, charts in card containers, tables with updated styling.

### Requirements

For **each page** (2–9), apply this standard layout pattern:

```python
# 1. Brand + page config
apply_brand(st, page_title="RVGT | {Module Name}")

# 2. Page header
st.markdown(f"""<div style="margin-bottom:1rem;">
  <h1 style="...">{Module Name}</h1>
  <p style="...">{subtitle} · {date}</p>
</div>""", unsafe_allow_html=True)

# 3. Filter bar (with page-specific filters)
filters = filter_bar(key_prefix="{module_key}", show_dma=True, show_channel=True)

# 4. KPI row (3-5 cards, page-specific metrics)
cols = st.columns(N)
for i, kpi in enumerate(kpis):
    with cols[i]:
        kpi_card(...)

# 5. Charts in card containers
branded_chart_card(fig, title="...", subtitle="...")

# 6. Data tables (if applicable)
card_container(title="Campaign Performance")
data_table(df)
card_container_end()
```

**Page-specific notes:**

| Page | Key layout change |
|------|-------------------|
| 2 — Spend Allocation | Channel mix sliders stay, but wrap in card containers. DMA heatmap in a card. |
| 3 — Acquisition Funnel | Waterfall chart gets a card wrapper. Drop-off analysis below. |
| 4 — Onboarding & Retention | Cohort heatmap in card. PFI milestones as styled KPI cards. |
| 5 — Paid Channels | Sub-tabs (SEM, Social, Brand) stay. Each sub-dashboard gets card layout. |
| 6 — Organic & AEO | LLM Visibility chart in card. Competitive table uses updated `data_table()`. |
| 7 — Product Experience | Pipeline tracker in card. Testing velocity chart in card. |
| 8 — Operations Command | Calendar in card. Capacity heatmap in card. Health cards as KPI row. |
| 9 — Simulator | Input controls in card. Output waterfall in card. Scenario comparison uses card layout. |

### Acceptance criteria
- All 9 pages follow the same visual hierarchy: header → filters → KPIs → charts → tables
- All charts are inside card containers
- All tables use the updated `data_table()` component
- Consistent spacing between sections (`margin-top: 1.5rem` between major sections)
- No hardcoded colors — everything from `brand.py`

### Does NOT include
- New data features (just UI reorganization of existing content)
- Mobile-specific layouts

---

## APE-UX-12: Add global CSS polish and micro-interactions

**Status:** TODO
**Depends on:** All prior APE-UX tickets
**Files to modify:** `src/config/brand.py` (CSS section)

### Context
Final polish pass to add subtle micro-interactions and consistent transitions across the entire app.

### Requirements

1. **Add global transition rules** in `_brand_css()`:
   ```css
   /* Smooth transitions on all interactive elements */
   .stButton > button,
   [data-testid="stSidebarNavLink"],
   .stSelectbox,
   .stMultiSelect {
     transition: all 150ms ease;
   }
   ```

2. **Add number formatting CSS** for metric values:
   ```css
   .apex-metric-value {
     font-variant-numeric: tabular-nums;
     letter-spacing: -0.02em;
   }
   ```

3. **Improve scrollbar styling**:
   ```css
   ::-webkit-scrollbar { width: 6px; height: 6px; }
   ::-webkit-scrollbar-track { background: transparent; }
   ::-webkit-scrollbar-thumb { background: {COLORS['iron']}; border-radius: 3px; }
   ::-webkit-scrollbar-thumb:hover { background: {COLORS['secondary']}; }
   ```

4. **Add loading skeleton CSS class** (for future use):
   ```css
   .apex-skeleton {
     background: linear-gradient(90deg, {COLORS['background']} 25%, {COLORS['surface_sunken']} 50%, {COLORS['background']} 75%);
     background-size: 200% 100%;
     animation: shimmer 1.5s infinite;
     border-radius: {BORDER_RADIUS['md']};
   }
   @keyframes shimmer {
     0% { background-position: 200% 0; }
     100% { background-position: -200% 0; }
   }
   ```

5. **Add tooltip refinement**:
   ```css
   [data-baseweb="tooltip"] {
     background-color: {COLORS['secondary']} !important;
     color: {COLORS['platinum']} !important;
     border-radius: {BORDER_RADIUS['sm']} !important;
     font-size: 0.75rem !important;
     padding: 0.35rem 0.65rem !important;
   }
   ```

### Acceptance criteria
- All buttons and interactive elements have smooth hover transitions
- Metric values use tabular number formatting
- Scrollbars are thin and brand-colored
- Loading skeleton class is available for future components
- No visual regressions on any page

---

## APE-UX-13: QA — Full visual regression and brand compliance audit

**Status:** TODO
**Depends on:** All APE-UX tickets
**Agents:** QA
**Files to modify:** `tasks/qa_results.md`

### Requirements

1. **Launch the app** with `streamlit run src/app.py` and visit all 9 pages.

2. **For each page, verify:**
   - [ ] Page loads without Python errors
   - [ ] All KPI cards render with correct formatting and deltas
   - [ ] Charts render inside card containers with brand colors
   - [ ] Tables show updated styling (light header, badges, progress bars)
   - [ ] Filter bar is functional and updates page content
   - [ ] Consistent spacing between sections
   - [ ] No hardcoded hex values (run `grep -rn '#[0-9a-fA-F]\{6\}' src/components/ src/pages/`)

3. **Brand compliance checks:**
   - [ ] No `#000000` or `#FFFFFF` anywhere in rendered output
   - [ ] Chart colors follow CHART_PALETTE order
   - [ ] Libre Franklin font loads correctly
   - [ ] Border radius is consistent (12px on cards, 8px on chips/badges)

4. **Cross-page state:**
   - [ ] Filter selections persist when navigating between pages
   - [ ] Alert acknowledgments persist
   - [ ] Scenario saves from Simulator appear in Scorecard

5. **Write results** to `tasks/qa_results.md` with PASS/FAIL per check.

### Acceptance criteria
- All checks documented in `tasks/qa_results.md`
- Zero FAIL items for brand compliance
- Any functional FAIL items have follow-up tickets created
