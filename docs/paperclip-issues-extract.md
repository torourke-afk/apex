# Apex — Paperclip Issues Extract

> **Source:** http://localhost:3100/APE/issues
> **Extracted:** 2026-05-12
> **Total Issues:** 179
> **Project:** Apex — RVGT Marketing Intelligence & Operations Platform
> **Agents:** Tech Lead, Backend Engineer, Data Engineer, Frontend Engineer, QA Engineer

---

## Project Summary

Apex is a 9-module Streamlit CMO dashboard built across 5 major phases. All 179 issues are currently in **Done** status with QA approval, except for one open bug (APE-175). The project spans: scaffolding & brand system, database & models, seed data, reusable components, 9 dashboard modules, a calculation engine, alert engine, Kamino directive bus, performance optimization, cross-page state management, and comprehensive QA.

---

## Phase 1 — Foundation

### APE-1: Phase 1.1 — Project Scaffolding & Brand System
**Status:** Done | **Sub-issues:** 7/7 done

**Objective:** Set up the complete Apex project scaffold and establish the RVGT brand system as the foundation for all 9 dashboard modules.

**Deliverables:**
- Project directory structure
- `brand.py` — RVGT color tokens, typography, spacing, CSS injection
- `settings.py` — app configuration
- `app.py` — Streamlit entry point
- 9 stub pages (numbered `1_` through `9_`)
- `requirements.txt`
- DuckDB initialization

**Acceptance Criteria:**
- `streamlit run src/app.py` works
- All pages navigable via sidebar
- RVGT brand applied (Libre Franklin, Red #FF0016, Onyx #303A42, Platinum #F1F4F7)
- No pure black (#000000) or pure white (#FFFFFF) anywhere

**Architecture Decisions:**
- Streamlit multi-page with numbered files
- Brand-first approach — every page imports `apply_brand()`
- DuckDB for dev / PostgreSQL for prod
- `.streamlit/config.toml` with RVGT theme

**Child Issues:** APE-2 through APE-8

---

### APE-9: Phase 1.2 — Database Schema & Models
**Status:** Done | **Sub-issues:** 3/3 done

**Objective:** Define all Pydantic data models and database schema that serve as the shared contract between frontend, backend, and data layers.

**Requirements:**
- 10+ model files: `campaign.py`, `funnel.py`, `cohort.py`, `offer.py`, `alert.py`, `budget.py`, `directive.py`, `simulator.py`, `kpi.py`, `channel.py`
- `db.py` connection layer
- Alembic migration infrastructure
- Full detailed schema for each model with enums, fields, and relationships

**Acceptance Criteria:**
- All models importable: `from src.models import Campaign, FunnelEvent, Cohort, ...`
- `alembic upgrade head` runs clean against DuckDB
- Empty tables queryable via SQLAlchemy
- Pydantic validation works (invalid data → ValidationError)
- Every enum value matches the build spec exactly

**Child Issues:** APE-29 (Pydantic Models), APE-30 (Alembic), APE-31 (DuckDB Init)

**Note:** `simulator.py`, `kpi.py`, `channel.py` deferred to their owning phases.

---

### APE-10: Phase 1.3 — Seed Data Generation (Core)
**Status:** Done | **Sub-issues:** 12/12 done

**Objective:** Generate realistic demo datasets powering the first 4 modules. Every chart, KPI card, and table must have plausible data to render against.

**Requirements:**
- 7 seed files:
  - `campaigns.py` — 200+ campaigns, 22 DMAs, 90 days daily, power-law distributions
  - `funnel.py` — 50,000+ events, 6 stages
  - `cohorts.py` — 5,000+ members, MOB6 70-80%, PFI milestones
  - `kpis.py` — 12-week sparklines for 7 KPIs
  - `alerts.py` — 30+ alerts with severity mix
  - `budgets.py` — $15M total, 6 categories
  - `run_all.py` — orchestrator

**Data Quality Standards:**
- Numpy distributions (not uniform random)
- Power-law campaign spend
- Exponential decay retention
- Geographic variation by market tier
- Weekday/weekend patterns

**Acceptance Criteria:**
- `run_all.py` completes in <30 seconds
- ≥10,000 rows per major table
- Pandera validation passes
- Data queryable with plausible results
- KPI sparklines show realistic trends
- All 22 DMAs represented

**Final Data Volumes:** Campaigns 33,660 rows, funnel 45,990-53,655, cohorts 5,600, kpis 10k+, alerts 35, budgets 72.

**Child Issues:** APE-38–41, APE-43–50

---

### APE-11: Phase 1.4 — Reusable Component Library
**Status:** Done | **Sub-issues:** 12/12 done

**Objective:** Build the shared Streamlit component library used by all 9 modules. Enforce RVGT brand consistency and eliminate duplicate code.

**Components (10 files):**

| # | File | Function | Description |
|---|------|----------|-------------|
| 1 | `kpi_card.py` | `kpi_card(title, value, delta, delta_pct, sparkline_data, alert_status)` | Trend-colored sparklines, delta arrows |
| 2 | `chart_wrapper.py` | `branded_plotly(fig)`, `branded_altair(chart)`, `waterfall_chart(stages, values, rates)` | RVGT-branded chart wrappers |
| 3 | `filter_bar.py` | `filter_bar(show_date, show_dma, show_channel, show_product)` | Session state persistence, 22 DMAs |
| 4 | `alert_badge.py` | `alert_badge(severity, count)` | Critical/Warning/Info styling |
| 5 | `metric_strip.py` | `metric_strip(metrics)` | Horizontal row of metrics |
| 6 | `section_header.py` | `section_header(title, subtitle, icon)` | Branded H2 with red left border |
| 7 | `data_table.py` | `data_table(df, sortable, filterable, paginated)` | Branded AgGrid wrapper |
| 8 | `heatmap.py` | `geo_heatmap()` | Geographic heat map |
| 9 | `scenario_compare.py` | `scenario_comparison()` | Side-by-side scenario comparison |
| 10 | `__init__.py` | — | Re-exports all components |

**Brand Rules:**
- Colors from `brand.py` only (NEVER hardcode hex)
- Libre Franklin font
- No pure black/white
- CHART_PALETTE order: Mahogany → Red → Onyx → Iron → Alloy
- 12px card corners, 16px padding

**Acceptance Criteria:**
- Each component renders correctly standalone
- All components use COLORS constants (grep for hardcoded hex = fail)
- Filter bar persists selections across `st.rerun()`
- KPI card sparklines render with correct trend coloring
- Components work in 2/3/4 column layouts

**Child Issues:** APE-32–37, APE-42, APE-51–55

---

## Phase 2 — Core Modules (1–4)

### APE-12: Phase 2.1 — Executive Scorecard (Module 1)
**Status:** Done | **Sub-issues:** 6/6 done

**Objective:** CMO landing page. Shows where the engagement stands against contractual KPIs with green/yellow/red status, 12-week sparklines, financial summary, and alert feed.

**Requirements:**
- **Primary KPI Panel (7 KPIs):** Net HH Growth, MOB6 Retention, Brand Capture Rate, CPIHH, LLM Visibility Score, App Completion Rate, Onboarding Activation Day 30 — each with large value, delta arrow, 12-week sparkline (green=improving, red=declining)
- **Financial Summary Strip:** Spend MTD/QTD/YTD vs plan, Blended CPL, CPIHH, Revenue attribution, Brand burn rate
- **Alert Feed:** 10 most recent, categorized by severity, filterable, linking to relevant module
- **Backend:** `GET /api/scorecard/kpis`, `/financial-summary`, `/alerts`

**Acceptance Criteria:**
- All 7 KPI cards populate from seed data
- Sparklines render with correct color coding
- Financial strip shows MTD/QTD/YTD with delta vs plan
- Alert feed shows 10 most recent, correctly categorized
- Page loads in <3 seconds
- All colors from COLORS constants
- Libre Franklin font applied globally

**Child Issues:** APE-58, APE-61, APE-68, APE-69, APE-78, APE-79

---

### APE-13: Phase 2.2 — Spend Allocation Dashboard (Module 2)
**Status:** Done | **Sub-issues:** 6/6 done

**Objective:** The CMO's primary operational control surface. Budget decisions happen here.

**Requirements:**
- **Budget Overview Panel:** 6 categories with progress bars, burn rate, projected landing. Flag >5% off pace.
- **Channel Mix Sliders:** Interactive sliders constrained to strategic ranges (CTV 30-50%, Social 25-50%, Audio 5-20%). Exceeding range triggers `st.warning()`. Real-time recalculation.
- **Geographic Market Matrix:** DMA table with tier, spend, brand health, retention, CPIHH. `geo_heatmap()` overlay. Tier reassignment with budget impact preview.
- **Scenario Modeling:** Save/compare up to 3 scenarios. Variables: shift between channels, add/remove markets, toggle life events, adjust SEM split.
- **Pacing & Burn Rate:** Line charts per category with confidence intervals, projected landing.
- **Backend:** `GET /api/budgets`, `/budgets/markets`, `POST /api/scenarios`, `GET /api/scenarios`, `POST /api/directives`

**Acceptance Criteria:**
- Channel mix sliders update projections in real time (<500ms)
- DMA heatmap is interactive
- Scenarios save and reload correctly from session state
- Budget pacing flags trigger >5% off plan
- Directive submission creates record in directives table

**Child Issues:** APE-62–67

---

### APE-14: Phase 2.3 — Acquisition Funnel (Module 3)
**Status:** Done | **Sub-issues:** 5/5 done

**Objective:** Visual representation of the entire acquisition journey from first impression to funded account. Each stage shows volume, conversion rate, cost metrics, and drop-off.

**Requirements:**
- **6-Stage Funnel Waterfall** using `waterfall_chart()`:
  - Page Visit → App Start (55%/65%)
  - App Start → Form Complete (65%/75%)
  - Form Complete → KYC Pass (75%/85%)
  - KYC Pass → Approval (85%/90%)
  - Approval → Funded (73%/87%)
  - Funded → Active 90d (70%/85%)
- **Drop-off Analysis:** Per-stage drop-off volume segmented by channel source (7 types), market tier, product type (7), device (3), personalization segment, time period
- **Abandonment Recovery Tracker:** 5 windows (0-2hr through 7-14 days)
- **Landing Page Performance, Personalization Monitor**
- **Backend:** 4 API endpoints under `/api/funnel/`

**Acceptance Criteria:**
- Waterfall arithmetic correct (`volume_in × conversion_rate = volume_out`)
- All filter dimensions update all charts simultaneously
- Drop-off dollar impact = `drop_off_volume × configured_ltv`
- Recovery tracker shows realistic metrics
- Charts use CHART_PALETTE colors with green/yellow/red benchmarking

**Child Issues:** APE-56, APE-57, APE-59, APE-60, APE-85

---

### APE-15: Phase 2.4 — Onboarding & Retention (Module 4)
**Status:** Done | **Sub-issues:** 8/8 done

**Objective:** Track every customer from funded account through PFI status. Monitor behavioral triggers and milestone completions that predict long-term retention.

**Requirements:**
- **PFI Flywheel Tracker:** Circular/radial chart showing 6 PFI milestones (Direct Deposit, Bill Pay, Debit Card, Digital Wallet, P2P Payments, Cross-sell) with completion rates and targets
- **90-Day Milestone Dashboard:** Day 7 funded rate (80%+), Day 30 DD enrolled (50%+), Day 90 2nd product (25%+), Day 90 retention (90%+) with Kamino interventions
- **Cohort Heatmaps:** X=acquisition month, Y=MOB, color=retention rate with exponential decay
- **BEI Composite Score:** Formula: `(0.25 × Awareness) + (0.25 × Branded Search) + (0.20 × Direct Traffic) + (0.20 × Branch Visits) + (0.10 × Social Engagement)`
- **Behavioral Trigger Monitor, Geo-Retention Heat Map, Offer Engine Performance**
- **Backend:** 5 API endpoints under `/api/retention/`

**Acceptance Criteria:**
- PFI flywheel shows completion rates from seed cohort data
- Cohort heatmap renders with realistic exponential decay (MOB1 96.6% → MOB6 79.1% → MOB18 73.3%)
- BEI calculates correctly from 5 weighted components
- All milestone alerts fire at correct thresholds
- Retention curves vary by channel quality (SEM 80.5% > Social 78.4% > Display 74.2%)

**Child Issues:** APE-70–77

---

## Phase 3 — Channel Modules (5–6)

### APE-16: Phase 3.1 — Paid Channels: SEM (Module 5 — SEM Tab)
**Status:** Done | **Sub-issues:** 4/4 done

**Objective:** Build the SEM performance sub-dashboard within Module 5.

**Requirements:**
- **SEM Metrics:** CPC ($3.46 benchmark), CTR (8.3%), CVR (2.55%), CPL ($83.93), Quality Score (7+ target), Impression Share (90%+ branded), VBB margin signal
- **Sub-Views:** Market segmentation (established/growth/new), match type allocation (broad 30%/exact 45%/phrase 25%), AI-powered PMax vs standard comparison, negative keyword hygiene score, keyword group table (sortable), QS trend, IS trend
- **Backend:** 4 API endpoints
- **Seed Data:** 220 keyword groups, 19,800 daily rows, QS 3-10

**Child Issues:** APE-88, APE-89, APE-92, APE-93

---

### APE-17: Phase 3.2 — Paid Channels: Social & Brand Media (Module 5 — Social/Brand Tabs)
**Status:** Done | **Sub-issues:** 6/6 done

**Objective:** Build Social and Brand Media sub-dashboards within Module 5.

**Requirements:**
- **Social Tab:** CPL, Native CVR 13%, LP CVR 4.02%, AI CPA, first-party audiences 15+. Platform breakdown: Meta 70%, TikTok 15%, LinkedIn 10%, Other 5%. Creative performance table sortable by CTR/CVR/spend.
- **Brand Media Tab:** BEI Score by market tier with 12-week trend line. Frequency compliance. CTV/OLV completion rates. Streaming audio listen-through. Active/Control incrementality.
- **Life Event Campaigns:** 8 always-on campaigns (Home Purchase, Marriage, New Child, College, Inheritance, Job Change, Divorce, Retirement) with 2-3x CVR target
- **Mover Marketing:** Pipeline volume/quality, 3-5x propensity benchmark
- **Backend:** 7 API endpoints

**Child Issues:** APE-80, APE-81, APE-83, APE-87, APE-91, APE-95

---

### APE-18: Phase 3.3 — Organic & AEO Intelligence (Module 6)
**Status:** Done | **Sub-issues:** 6/6 done

**Objective:** Monitor SEO, AEO (Answer Engine Optimization), and GEO (Generative Engine Optimization). Track RVGT's most distinctive capability: measuring and improving a bank's visibility in AI-generated answers.

**Requirements:**
- **LLM Visibility Score Dashboard:** 6 platforms (Google AI Overviews, ChatGPT, Perplexity, Claude, Gemini, Copilot), 100-150 prompts per client, 22 DMAs, weekly refresh
- **Metrics per RVGT 12-Layer Testing Methodology:** Mention Rate, Average Position, Share of Voice, Sentiment Score, Citation Rate
- **Competitive AEO Benchmarking:** Competitor comparison table
- **SEO Performance:** Organic volume, keyword ranking distribution, traffic by product, rank change alerts
- **Seed Data:** 6 platforms × 50+ prompts × 12 weeks = 3,600+ records, 5 competitors (actual: 24,072 records)

**Child Issues:** APE-82, APE-84, APE-86, APE-90, APE-94, APE-96

---

### APE-19: Phase 3.4 — Seed Data Generation (Channels)
**Status:** Done | **Sub-issues:** 7/7 done

**Objective:** Generate realistic seed data for all channel-specific modules. Cross-channel totals must reconcile with Executive Scorecard.

**Requirements:**
- `sem.py` — 200+ keyword groups, 90 days daily, CPC $0.50-5.00, QS 3-10
- `social.py` — Meta 70%, TikTok 15%, LinkedIn 10%, Other 5%. 50+ creatives.
- `brand_media.py` — BEI components per market per week, CTV/OLV 85-95%
- `life_events.py` — 8 campaigns, CVR 2-4x multiplier
- `aeo.py` — 6 platforms × 50 prompts × 12 weeks, 5 competitors
- `seo.py` — 500+ keywords, page 1/2/3+ distribution
- **Reconciliation:** Total spend = $15M budget, attribution plausible (SEM 40%, Social 20%, Organic 25%, Direct 15%)

**Child Issues:** APE-97–103

---

## Phase 4 — Advanced Modules (7–9)

### APE-20: Phase 4.1 — Product & Experience Module (Module 7)
**Status:** Done | **Sub-issues:** 4/4 done

**Objective:** Track product innovation pipeline and digital experience transformation.

**Requirements:**
- **Product Pipeline Tracker:** Initiative name, status (Concept/In Design/In Build/In Market), key success metric, funnel connection. Uses `data_table()` with status badges.
- **Digital Experience Transformation Roadmap:** Three-wave tracker (Foundation, Scale, Transform) with Gantt-style Plotly chart
- **Testing Velocity Tracker:** Active tests, avg duration, winning variant deployment speed, cumulative lift, velocity drop alert
- **Seed Data:** 15 product initiatives, 10 active A/B tests, 12-week testing velocity history

**Child Issues:** APE-111–114

---

### APE-21: Phase 4.2 — Operations Command Center (Module 8)
**Status:** Done | **Sub-issues:** 5/5 done

**Objective:** Team management, approval workflows, launch calendars, system health. Keeps CMO informed on execution.

**Requirements:**
- **Launch Calendar:** Campaign launches, content deployments, test start/stop, product releases tagged by workstream with approval status
- **Team Capacity & Velocity:** Sprint burndown, resource utilization heatmap, ticket aging, blocked ticket alerts
- **Approval Queue:** Budget reallocations, campaign launches, creative sign-offs, market tier changes with approve/reject buttons
- **System Health Monitor:** 6 categories (Behavioral Data, Offer Management, AI/Analytics, CMS, Personalization, Attribution) with green/yellow/red status
- **Competitive Intelligence Feed:** Auto-curated feed with ad spend shifts, SEO alerts, earnings highlights, hiring signals
- **Seed Data:** 30+ calendar events, 10 approval items, health checks for 6 categories, 20 competitive intel items

**Child Issues:** APE-115–119

---

### APE-22: Phase 4.3 — Alert Engine
**Status:** Done | **Sub-issues:** 3/3 done

**Objective:** Background evaluation engine that monitors KPIs against rules and generates alerts surfaced in the Executive Scorecard feed.

**Requirements:**
- **AlertRule class** with threshold, trend, and anomaly condition types
- **9 Standard Alert Rules:**
  1. Net HH Growth <95% pace → Critical
  2. MOB6 Retention -2pts → Critical
  3. Brand Capture -5pts MoM → Warning
  4. CPIHH +10% QoQ → Warning
  5. LLM Visibility -5pts MoM → Warning
  6. App Completion -3pts WoW → Warning
  7. SEM CPC >$5.00 → Warning
  8. SEM QS <5 → Info
  9. Impression Share <85% → Warning
- **API Endpoints:** `GET /api/alerts`, `POST /api/alerts/evaluate`, `PATCH /api/alerts/:id/acknowledge`
- **APScheduler** integration (default 5 min interval)

**Child Issues:** APE-104–106

---

### APE-23: Phase 4.4 — Full-Funnel Simulator: Calculation Engine (Module 9 Backend)
**Status:** Done | **Sub-issues:** 4/4 done

**Objective:** Build the 5-stage waterfall calculation engine — the most strategically important module. Pure Python, no UI dependencies.

**Requirements:**
- **Dual-Mode Architecture:** BD Mode (industry benchmarks) vs Client Mode (live data). Mode determines data source, NOT calculation logic.
- **Stage 1 — Traffic Generation:** Spend → traffic via CPL/CPC. Brand media branded search lift (15-25%/30-40%). Organic/AEO share.
- **Stage 2 — Funnel Conversion:** 6-stage waterfall with spec rates.
- **Stage 3 — Retention & Activation:** MOB6 (70-85%), MOB12 (65-80%), PFI conversion (35-65%).
- **Stage 4 — LTV Projection:** Retained HHs × LTV ($2,500-3,500). PFI multiplier (3-7x).
- **Stage 5 — Efficiency Metrics:** CPIHH, ROI, payback months, blended CPL.
- **5 Preset Scenarios:** Regional Growth, Top-20 Optimization, Community Digital Entry, De Novo/Neobank, Acquisition Integration
- **BD Before/After Toggle:** RVGT improvement assumptions (brand capture +30-40 pp, site CVR +3-5%, testing velocity 3x, onboarding 2.2x, MOB6 +2-4 pts, SEO +2,000/yr)
- **Benchmark data** in `src/data/benchmarks/industry.py`

**Child Issues:** APE-107, APE-109, APE-110

---

### APE-24: Phase 4.5 — Full-Funnel Simulator: UI (Module 9 Frontend)
**Status:** Done | **Sub-issues:** 8/8 done

**Objective:** Build the Simulator Streamlit page with layered input controls, waterfall output, scenario comparison, and BD/Client mode toggle. Designed for live walkthroughs in BD meetings.

**Requirements:**
- **Mode Toggle:** BD Mode (benchmarks) / Client Mode (live data)
- **Institution Profile (BD only):** 8 fields (name, branches, DMAs, media spend, digital volume, retention rate, growth objective, competitive position)
- **Layer 1 — Budget Buckets:** 6 sliders (Brand 40%, SEM 25%, Social 15%, HV Overlay 12%, SEO/AEO 5%, Conversion 3%)
- **Layer 2 — Sub-tactic drill-in:** Per-bucket expanders
- **Conversion Assumptions Panel:** All engine parameters as sliders
- **Output Panels:** Headline KPI cards, funnel waterfall, channel contribution stacked bar, scenario comparison (up to 3), sensitivity analysis curves
- **BD Before/After Toggle, 5 Preset Selector**

**Child Issues:** APE-120–127

---

## Phase 5 — Integration & QA

### APE-25: Phase 5.1 — Kamino Directive Bus
**Status:** Done | **Sub-issues:** 8/8 done

**Objective:** Build the FastAPI integration layer between Apex and Kamino. When CMO makes decisions in Apex, structured directives flow to Kamino for execution.

**Requirements:**
- **Directive Types:** Budget Reallocation, Market Tier Change, Channel Mix Adjustment, Life Event Toggle, Test Launch, Recovery Update, Offer Strategy
- **Files:** `src/kamino/models.py`, `src/kamino/client.py`, `src/api/directives.py`
- **Endpoints:** `POST /api/directives`, `GET /api/directives` (with filters), `GET /api/directives/:id`, `PATCH /api/directives/:id/cancel`, `GET /api/directives/:id/status`
- **Redis pub/sub** for real-time UI updates
- **Status transitions:** pending → approved → in_progress → completed/failed

**Child Issues:** APE-128, APE-133–137, APE-142, APE-143

---

### APE-26: Phase 5.2 — Cross-Page State & Navigation
**Status:** Done | **Sub-issues:** 31/31 done

**Objective:** Polish `st.session_state` usage across all 9 modules. Ensure data flows correctly between pages.

**Requirements:**
- **Cross-page state contracts:** Scenarios saved in Simulator (Module 9) visible in Scorecard (Module 1) and Spend Allocation (Module 2). Alert acknowledgments persist. Filter selections carry. Budget changes reflected.
- **Session state namespacing:** Each module prefixes keys (`scorecard_`, `spend_`, `funnel_`, `onboarding_`, `channels_`, `organic_`, `product_`, `ops_`, `simulator_`). Shared keys use `global_` prefix. No key collisions.
- **Navigation polish:** Sidebar shows all 9 modules with icons. Current page highlighted in COLORS.RED.

**Child Issues:** APE-138–141, APE-144–170

---

### APE-27: Phase 5.3 — Performance Optimization
**Status:** Done | **Sub-issues:** 4/4 done

**Objective:** Every page loads in <3 seconds with seed data. Add caching, lazy loading, and query optimization.

**Requirements:**
- `@st.cache_data` on all data-fetching functions (TTL = configurable)
- `@st.cache_resource` on DB connections
- Lazy loading with `st.spinner()` on heavy visualizations
- Batch queries, pre-aggregate common views, index DuckDB on hot columns
- Architecture decision: no Redis — Streamlit built-in caching sufficient for single-process DuckDB app

**Results:** Worst page load: Home 0.219s. Scorecard queries consolidated from 11 to 6. 492 tests passing.

**Child Issues:** APE-129–132

---

### APE-28: Phase 5.4 — Comprehensive QA Pass
**Status:** In Progress | **Sub-issues:** 7/9 done, 1 blocked

**Objective:** Full regression test across all 9 modules. Final quality gate before demo-ready.

**Test Categories:**

1. **Brand Compliance Audit:** Grep all `.py` for hardcoded hex (should be ZERO), Libre Franklin on every page, no pure black/white, chart palette order, rounded corners (12px cards, 8px buttons)

2. **Data Contract Verification:** Frontend uses Pydantic models from `src/models/`, API responses match schemas, seed data passes pandera validation

3. **Simulator Math Validation:** `volume_in × rate = volume_out` at each stage, `LTV = retained_hh × ltv × pfi_multiplier`, `CPIHH = total_spend / retained_hh`, sensitivity curves monotonic

4. **Cross-Page State:** Simulator scenario → Scorecard, filters persist across nav, alert acks persist, budget changes → Scorecard strip

5. **Alert Engine:** Each alert type fires at threshold, alerts appear in feed, acknowledge flow works

6. **Performance:** Each page <3s load, simulator slider <500ms, no unnecessary re-renders

7. **Accessibility:** Alt text on images, not color-only indicators, tab navigation

**Deliverable:** `tasks/qa_results.md` — `## [Module] — PASSED/FAILED`, failures with file/line/repro.

**Acceptance Criteria:**
- Brand compliance 100%
- Simulator math independently verified
- Zero critical bugs, <5 medium

**Child Issues:**
- APE-171: Brand Compliance & Accessibility (categories #1, #7) — Done
- APE-172: Data Contracts & Simulator Math (categories #2, #3) — Done
- APE-173: Cross-Page State & Alert Engine (categories #4, #5) — Blocked by APE-175
- APE-174: Performance Regression & Full Test Suite (category #6) — Done
- APE-175: **Bug: REDIS_URL missing** — In Review (see below)
- APE-176–179: Productivity reviews — Done

---

## Open Bug

### APE-175: Bug: REDIS_URL missing from src/config/settings.py — blocks test_alerts_api.py
**Status:** In Review | **Blocks:** APE-173

**Description:**
`src/kamino/events.py:23` imports `REDIS_URL` from `src.config.settings`, but `REDIS_URL` is not defined in that module. This causes an `ImportError` at collection time that blocks all 22 tests in `tests/test_alerts_api.py`.

**Import Chain:**
```
tests/test_alerts_api.py
→ src/api/__init__.py:14 (from .directives import router)
→ src/api/directives.py:22 (from src.kamino.events import ...)
→ src/kamino/events.py:23 (from src.config.settings import REDIS_URL) ← MISSING
```

**Fix:**
Add to `src/config/settings.py`:
```python
REDIS_URL = os.environ.get("APEX_REDIS_URL", "redis://localhost:6379")
```
(`os` is already imported at line 5 — no additional import needed.)

**Impact:** Blocks APE-173 alert engine checks 2 and 3 (alert feed visibility and acknowledge flow via API).

**Repro:**
```bash
python3 -m pytest tests/test_alerts_api.py -v
# ERROR collecting tests/test_alerts_api.py
# ImportError: cannot import name REDIS_URL from src.config.settings
```

---

## Full Issue Index (179 issues)

### Phase 1 — Foundation
| ID | Title | Status |
|----|-------|--------|
| APE-1 | Phase 1.1 — Project Scaffolding & Brand System | Done |
| APE-2–8 | (Child scaffolding issues) | Done |
| APE-9 | Phase 1.2 — Database Schema & Models | Done |
| APE-29–31 | (Child schema issues) | Done |
| APE-10 | Phase 1.3 — Seed Data Generation (Core) | Done |
| APE-38–50 | (Child seed data issues) | Done |
| APE-11 | Phase 1.4 — Reusable Component Library | Done |
| APE-32–37, 42, 51–55 | (Child component issues) | Done |

### Phase 2 — Core Modules
| ID | Title | Status |
|----|-------|--------|
| APE-12 | Phase 2.1 — Executive Scorecard (Module 1) | Done |
| APE-58, 61, 68, 69, 78, 79 | (Child issues) | Done |
| APE-13 | Phase 2.2 — Spend Allocation (Module 2) | Done |
| APE-62–67 | (Child issues) | Done |
| APE-14 | Phase 2.3 — Acquisition Funnel (Module 3) | Done |
| APE-56, 57, 59, 60, 85 | (Child issues) | Done |
| APE-15 | Phase 2.4 — Onboarding & Retention (Module 4) | Done |
| APE-70–77 | (Child issues) | Done |

### Phase 3 — Channel Modules
| ID | Title | Status |
|----|-------|--------|
| APE-16 | Phase 3.1 — Paid Channels: SEM | Done |
| APE-88, 89, 92, 93 | (Child issues) | Done |
| APE-17 | Phase 3.2 — Paid Channels: Social & Brand Media | Done |
| APE-80, 81, 83, 87, 91, 95 | (Child issues) | Done |
| APE-18 | Phase 3.3 — Organic & AEO Module | Done |
| APE-82, 84, 86, 90, 94, 96 | (Child issues) | Done |
| APE-19 | Phase 3.4 — Seed Data Generation (Channels) | Done |
| APE-97–103 | (Child issues) | Done |

### Phase 4 — Advanced Modules
| ID | Title | Status |
|----|-------|--------|
| APE-20 | Phase 4.1 — Product & Experience (Module 7) | Done |
| APE-111–114 | (Child issues) | Done |
| APE-21 | Phase 4.2 — Operations Command (Module 8) | Done |
| APE-115–119 | (Child issues) | Done |
| APE-22 | Phase 4.3 — Alert Engine | Done |
| APE-104–106 | (Child issues) | Done |
| APE-23 | Phase 4.4 — Simulator: Calculation Engine | Done |
| APE-107, 109, 110 | (Child issues) | Done |
| APE-24 | Phase 4.5 — Simulator: UI | Done |
| APE-120–127 | (Child issues) | Done |

### Phase 5 — Integration & QA
| ID | Title | Status |
|----|-------|--------|
| APE-25 | Phase 5.1 — Kamino Directive Bus | Done |
| APE-128, 133–137, 142, 143 | (Child issues) | Done |
| APE-26 | Phase 5.2 — Cross-Page State & Navigation | Done |
| APE-138–141, 144–170 | (Child issues) | Done |
| APE-27 | Phase 5.3 — Performance Optimization | Done |
| APE-129–132 | (Child issues) | Done |
| APE-28 | Phase 5.4 — Comprehensive QA Pass | **In Progress** |
| APE-171–174 | (QA child issues) | Done (173 blocked) |
| APE-175 | **Bug: REDIS_URL missing** | **In Review** |
| APE-176–179 | (Productivity reviews) | Done |
