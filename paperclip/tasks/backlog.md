# Apex — Development Backlog

> Maintained by Tech Lead. Items are ordered by priority (top = highest).
> Status: `TODO` | `IN PROGRESS` | `IN REVIEW` | `DONE`

---

## Phase 1 — Foundation (Weeks 1–3)

### 1.1 Project Scaffolding & Brand System
**Status:** TODO
**Agents:** Frontend, Backend
**Description:** Create the Streamlit multi-page app skeleton, RVGT brand config (colors, fonts, chart palettes), shared CSS injection, and the base layout (sidebar nav, header strip, footer). Set up FastAPI skeleton for the Kamino directive bus. Configure DuckDB for local dev.
**Acceptance:** `streamlit run src/app.py` launches with branded sidebar, all 9 page stubs load without error, FastAPI healthcheck returns 200.

### 1.2 Database Schema & Models
**Status:** TODO
**Agents:** Backend, Data Engineer
**Description:** Define all Pydantic models in src/models/ and create the initial database schema: campaigns, funnel_events, cohorts, offers, alerts, budgets, scenarios, directives. Set up Alembic migrations. Create DuckDB initialization script.
**Acceptance:** All models importable, `alembic upgrade head` runs clean, empty tables queryable.

### 1.3 Seed Data Generation — Core
**Status:** TODO
**Agents:** Data Engineer
**Description:** Generate realistic demo datasets for the first 4 modules: campaign performance across 20+ DMAs, funnel events at each of 6 stages, onboarding cohorts with MOB6/MOB12 retention curves, and KPI summary data. Use Faker for names/dates, numpy for realistic distributions.
**Acceptance:** Seed script runs in <30s, produces ≥10,000 rows per table, distributions pass pandera validation, data visible in DuckDB queries.

### 1.4 Reusable Component Library
**Status:** TODO
**Agents:** Frontend
**Description:** Build the shared Streamlit component library: KPI card (value + delta + sparkline), branded chart wrapper (Plotly with RVGT colors), filter bar (date range + DMA + channel), alert badge, metric strip, section header. All in src/components/.
**Acceptance:** Each component renders correctly in a test page, brand colors verified, responsive at common widths.

---

## Phase 2 — Core Dashboards (Weeks 3–6)

### 2.1 Executive Scorecard
**Status:** TODO
**Agents:** Frontend, Backend
**Description:** Build the CMO landing page: top-line KPI cards (spend, applications, funded accounts, CPA, ROAS, NIM contribution), alert feed showing active alerts, financial summary strip, and 30/60/90-day trend sparklines. Pulls data from the backend API layer.
**Acceptance:** All KPI cards populate from seed data, sparklines render, alert feed shows sample alerts, page loads in <3s.

### 2.2 Spend Allocation Dashboard
**Status:** TODO
**Agents:** Frontend, Backend
**Description:** Channel mix visualization with interactive sliders for budget reallocation, DMA performance matrix (heatmap with drill-in), scenario comparison view (current vs. proposed), and pacing indicators. Backend endpoints for budget data and scenario persistence.
**Acceptance:** Sliders update projections in real time, DMA heatmap is interactive, scenarios save and load from session state.

### 2.3 Acquisition Funnel
**Status:** TODO
**Agents:** Frontend, Backend, Data Engineer
**Description:** 6-stage waterfall visualization (Impressions → Clicks → Visits → Starts → Submits → Funded), drop-off analysis between each stage, filter controls (by channel, DMA, time period). Backend aggregation queries for funnel data.
**Acceptance:** Waterfall chart renders with correct arithmetic (in × rate = out), filters update all charts, conversion rates displayed at each stage.

### 2.4 Onboarding & Retention
**Status:** TODO
**Agents:** Frontend, Backend, Data Engineer
**Description:** PFI milestone dashboard (5 milestone completion rates), cohort heatmaps (retention by acquisition month × MOB), BEI composite score visualization, LTV projection display. Data layer for cohort builder and BEI calculation engine.
**Acceptance:** Heatmap renders with realistic retention curves, PFI milestones show completion %, BEI score calculates from 5 weighted components.

---

## Phase 3 — Channel Intelligence (Weeks 6–9)

### 3.1 Paid Channels — SEM
**Status:** TODO
**Agents:** Frontend, Backend, Data Engineer
**Description:** SEM performance dashboard: keyword group performance, quality score trends, CPC/CPA tracking, impression share, competitive benchmark comparisons. Seed data for SEM metrics.
**Acceptance:** All SEM metrics render from seed data, benchmark comparisons display, time-series charts work with date filters.

### 3.2 Paid Channels — Social & Brand Media
**Status:** TODO
**Agents:** Frontend, Backend, Data Engineer
**Description:** Social media performance (Meta, LinkedIn) and brand media (display, video, connected TV) dashboards. Reach/frequency metrics, creative performance, brand lift proxies. Seed data for social/brand channels.
**Acceptance:** Channel sub-tabs navigate correctly, all metrics populated, creative performance table sortable.

### 3.3 Organic & AEO Module
**Status:** TODO
**Agents:** Frontend, Backend, Data Engineer
**Description:** LLM Visibility Score tracking across 5 platforms (ChatGPT, Perplexity, Gemini, Copilot, Claude), competitive benchmarking tables, prompt coverage analysis (50+ prompts), SEO performance overlay. Seed data for LLM visibility scores.
**Acceptance:** Score charts render per platform, competitive comparison table functional, prompt-level drill-in works.

### 3.4 Seed Data Generation — Channels
**Status:** TODO
**Agents:** Data Engineer
**Description:** Generate realistic seed data for all channel-specific modules: SEM keywords/bids/quality scores, social media campaigns/creatives, brand media flights, LLM visibility scores across platforms and prompts. Must align with funnel data from Phase 1.
**Acceptance:** All channel dashboards can render without errors using seed data, cross-channel totals reconcile with executive scorecard.

---

## Phase 4 — Operations & Simulator (Weeks 9–13)

### 4.1 Product & Experience Module
**Status:** TODO
**Agents:** Frontend, Backend
**Description:** Transformation pipeline tracker (initiative status board), testing velocity dashboard (A/B test count, statistical significance tracking), product roadmap visualization. Kamino integration status indicators.
**Acceptance:** Pipeline tracker shows initiative statuses, test velocity chart renders, roadmap timeline interactive.

### 4.2 Operations Command Center
**Status:** TODO
**Agents:** Frontend, Backend, Data Engineer
**Description:** Launch calendar (campaign and initiative scheduling), capacity heatmap (team workload by week), approval queue (pending directives), system health cards (API status, data freshness, pipeline health). Alert rule engine in backend.
**Acceptance:** Calendar shows scheduled items, capacity heatmap interactive, approval queue processes mock directives, health cards show green/yellow/red.

### 4.3 Alert Engine
**Status:** TODO
**Agents:** Backend, Data Engineer
**Description:** Background alert evaluation engine: define alert rules (threshold-based, trend-based, anomaly-based), evaluate against current metrics on a schedule, write alerts to database with severity levels, surface in Executive Scorecard feed.
**Acceptance:** Alert rules fire correctly when test data crosses thresholds, alerts appear in feed within one evaluation cycle, severity levels render correctly.

### 4.4 Full-Funnel Simulator — Calculation Engine
**Status:** TODO
**Agents:** Backend, Data Engineer
**Description:** Build the 5-stage waterfall calculation engine in src/simulator/engine.py: Traffic Generation → Funnel Conversion → Retention & Deepening → LTV Projection → Efficiency Metrics. Pure Python module with no UI dependencies. Benchmark data tables and preset scenario templates.
**Acceptance:** Engine produces correct outputs for all 5 preset scenarios, unit tests cover each stage independently, benchmark data loaded from src/data/benchmarks/.

### 4.5 Full-Funnel Simulator — UI
**Status:** TODO
**Agents:** Frontend
**Description:** Simulator Streamlit page with layered input controls (Layer 1: 6 major budget buckets with sliders; Layer 2: sub-tactic drill-in panels), funnel waterfall output visualization, scenario comparison (side-by-side), sensitivity curves, BD/Client mode toggle, preset scenario selector.
**Acceptance:** All input controls functional, waterfall chart updates on slider change, BD mode hides internal metrics, scenarios saveable to session state, sensitivity curves render for each input variable.

---

## Phase 5 — Integration & Polish (Weeks 13–16)

### 5.1 Kamino Directive Bus
**Status:** TODO
**Agents:** Backend
**Description:** FastAPI endpoints for the Apex → Kamino directive pipeline: submit directive, check status, cancel directive, list active directives. Directive types: budget reallocation, bid adjustment, campaign pause/resume, alert acknowledgment. Redis pub/sub for real-time status updates.
**Acceptance:** All CRUD endpoints functional, directive status updates propagate, integration tests pass.

### 5.2 Cross-Page State & Navigation
**Status:** TODO
**Agents:** Frontend, QA
**Description:** Verify and polish st.session_state usage across all 9 modules. Scenarios saved in Simulator visible in Scorecard and Spend Allocation. Alert acknowledgments persist. Filter selections carry across pages where appropriate.
**Acceptance:** QA verifies all cross-page state scenarios in qa_results.md, no orphaned state keys, no session state collisions.

### 5.3 Performance Optimization
**Status:** TODO
**Agents:** Frontend, Backend
**Description:** Add st.cache_data and st.cache_resource decorators to all data-fetching functions. Implement query result caching in the API layer. Lazy-load heavy visualizations. Target: every page loads in <3 seconds with seed data.
**Acceptance:** Lighthouse-style timing check on each page, all under 3s threshold, cache hit rates logged.

### 5.4 Comprehensive QA Pass
**Status:** TODO
**Agents:** QA
**Description:** Full regression test across all 9 modules: brand compliance audit, data contract verification, simulator math validation, cross-page state testing, alert engine testing, accessibility basics. Document all findings in tasks/qa_results.md.
**Acceptance:** All tests pass or have documented fix tickets, brand compliance 100%, simulator math verified independently.
