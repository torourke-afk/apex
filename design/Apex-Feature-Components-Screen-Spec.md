# Apex — Feature Components & Screen Specs

**The hand-off companion to `Apex-Design-Memo-Combined.md` (Signal Deck).** Where the memo defines the *system* (tokens, primitives, theming, motion), this defines the *screens* — what each of the 12 surfaces is made of, how it's laid out, its states, and the BFF data it consumes. Grounded in the real Apex pages (`src/pages/`), components (`src/components/`), API routers (`src/api/`), and the Kamino directive model.

> **For Claude design:** read `DESIGN.md` and the combined memo first. Build in React + Tailwind over the BFF. Every screen below lists: **Purpose · Layout · Feature components · Primitives used · States · BFF data.** "Primitives" = the system kit (KPICard, Gauge, DataTable, etc.). "Feature components" = domain-specific composites unique to that screen.

> **This is the NEW build.** The React app is a thin client over the unified microservice Gateway/BFF — it consumes JSON via typed hooks and never touches SQL/Streamlit. The *feature content* of each screen (KPIs, charts, tables, flows) is taken from the working current app so nothing is lost; the *delivery* is the new architecture. The screen content does not depend on which services exist yet — build the UI against the BFF contracts and **mock with MSW** until each service is live (see build-order map below).

---

## BFF endpoint readiness (build order for the new architecture)

Which target contracts already exist as FastAPI routers vs. still need extraction from Streamlit data loaders into their service. The React UI is built against all of them via MSW mocks; flip mock→live as each lands.

| Domain / screen | Target BFF contract | Status today | Action |
|---|---|---|---|
| Scorecard (1) | `/api/scorecard/*` | **Exists** (`api/scorecard.py`) | Wrap in BFF; wire live |
| Performance Media — SEM (4) | `/api/channels/sem/*` | **Exists** (`api/sem.py`) | Wire live |
| Operations — approvals/calendar/etc (9) | `/api/ops/*` | **Exists** (`api/ops.py`) | Wire live |
| Directives / Approval Queue (9, Spend, Simulator) | `/api/directives/*` | **Exists** (`api/directives.py`, Kamino model) | Wire live |
| Product & Experience (8) | `/api/product/*` | **Exists** (`api/product.py`) | Wire live |
| Alerts / Alert Wire (1, 9) | `/api/alerts/*` | **Exists** (`api/alerts.py`) | Wire live |
| Spend Allocation (2) | `/api/spend/*` (overview, pacing, dma, mix-bands) | **Extract** — in `data/spend_queries.py`, `load_budget_pacing` | New Spend service |
| Brand Media (3) | `/api/channels/brand/*` | **Extract** — `social_brand_loaders`, `load_brand_bei`, `life_event_campaign` | Into Channels service |
| Performance — Social (4) | `/api/channels/social/*` | **Extract** — `social_platform_metric`, `social_creative` | Into Channels service |
| SEO (5) | `/api/channels/seo/*` | **Extract** — `organic_loaders`, `seo_ranking`, `seo_traffic` | Into Channels service |
| AEO (6) | `/api/channels/aeo/*` | **Extract** — `organic_aeo`, `llm_visibility` | Into Channels service |
| Acquisition Funnel (7) | `/api/funnel/*` | **Extract** — `funnel_queries`, `funnel_event`, `cohort` | New Funnel service |
| Simulator (10) | `POST /api/simulate` (async job) | **Extract** — `simulator/*` engines | New Simulation service (async via Kamino) |
| Retention (11) | `/api/retention/*` | **Extract** — `retention_*`, `geo_retention` | New Retention service (async) |
| Settings / context / benchmarks (12) | Gateway context + Metric Layer | **Partial** — `config/settings.py`, brand, benchmark seeds | Gateway/BFF + Metric Layer |

**Implication for the front-end agent:** all 12 surfaces can be built immediately against MSW mocks of these contracts; six wire to live endpoints almost right away, the rest wire up as the Spend / Channels / Funnel / Simulation / Retention services are extracted per `Apex-Unified-Microservice-Architecture.md`.

---

## 0. Shared chrome (every screen)

- **AppShell** — left icon rail (collapsible, 7 domains + Settings), top context bar (page title, status/freshness, account switcher [Fifth Third + RV validation accounts], theme toggle, BD/Client mode), main canvas.
- **GlobalFilterBar** — sticky chip-style filters: **date range, product, DMA, channel**. Emits a shared filter context; every data hook takes it as params (replaces today's `st.session_state` global filter). Maps to current `global_filter_strip`.
- **AgentConsole** — docked bottom command line (the directive/chat entry), JetBrains Mono, blinking signal-cyan caret, agent tool-chips inline (`query_metrics`, `simulate_geo`, `propose_action`). Maps to current `chat_drawer`. Any proposed account change becomes a Directive in the approval queue — never an instant write.
- **Standard states** every data region must implement: **loading** (skeleton shimmer), **empty** (no data for filter → guidance), **error** (retry), **stale** (freshness badge when data is older than refresh interval), **populated**.

---

## 1. Executive Scorecard  *(`1_Executive_Scorecard.py`, `api/scorecard.py`)*

**Purpose:** CMO morning glance — contractual KPIs vs. target, financial summary, top campaigns, live alerts.

**Layout:** HUD status ribbon → hero gauge + Primary KPI row → 2-col (Financial Summary | Campaign performance) → Alert wire.

**Feature components:**
- `PrimaryKPIDeck` — the contractual-target KPIs on a 12-week trajectory; each is a `KPICard` with value, delta vs. target, sparkline, and a **target ring** (Gauge-mini) that completes + celebrates when target is crossed (consequence feedback).
- `FinancialSummaryStrip` — `MetricStrip` of spend/revenue/efficiency roll-ups.
- `CampaignLeaderboard` — `DataTable`, top campaigns by ROAS, conditional ROAS badges (critical if < target).
- `AlertWire` — last 10 threshold breaches, newest slides in from top, criticals get one attention pulse then quiet; each row → acknowledge.
- `OperatingStreak` — subtle "on-pace N weeks / alerts cleared N days" momentum chip (progressive reward).

**Primitives:** Gauge, KPICard, MetricStrip, DataTable, Alert/AlertWire, CardContainer, SectionHeader.

**BFF data:** `GET /api/scorecard/kpis` (KPI summary: name, value, target, delta, trend[]), `/financial-summary`, `/api/scorecard/alerts` (or `/api/alerts`).

---

## 2. Spend Allocation  *(`2_Spend_Allocation.py`, `api/sem.py` + spend queries)*

**Purpose:** where budget goes across channels/campaigns/lines; pacing vs. plan; geographic allocation; channel-mix control within approved bands.

**Layout:** Budget Overview KPIs → Pacing & Burn (grouped bar, actual vs plan) → DMA Spend Map → Channel Mix Control.

**Feature components:**
- `BudgetOverviewKPIs` — `KPICard` row: total budget, spent, pacing %, remaining.
- `PacingBurnChart` — grouped bar, actual spend vs plan by channel, over/under flagged in warning/critical.
- `DMASpendMap` — **geographic choropleth** of spend by DMA tier (the geo map) + tier legend; hover = spend + KPI per market. (Key Acquisition-pillar feature.)
- `ChannelMixControl` — `ChannelMixSliders` (maps to `channel_mix_sliders`): drag allocation **within approved strategic bands**; rebalancing re-projects in real time; **"Commit plan"** stages a `channel_mix_adjustment` Directive (not an instant write) → approval queue + mission-tracker tick.

**Primitives:** KPICard, ChartWrapper (bar), GeoMap, ChannelMixSliders, MissionTracker, Button, CardContainer.

**BFF data:** spend overview, pacing-by-channel, spend-by-DMA(tier), channel-mix bands; commit → `POST /api/directives` (type `channel_mix_adjustment`).

---

## 3. Brand Media  *(`3_Brand_Media.py`)*

**Purpose:** brand-awareness campaigns — reach/frequency/impressions by channel, BEI, life-event segments.

**Layout:** Brand Media Overview KPIs → 2-col (Impressions by Channel bar | Reach & Frequency by DMA) → Campaign-by-Creative breakdown → Life Event Campaigns.

**Feature components:**
- `BrandOverviewKPIs` — impressions, reach, frequency, BEI (Brand Equity Index).
- `ImpressionsByChannel` — bar (ChartWrapper).
- `ReachFrequencyByDMA` — table/heatmap by market.
- `CreativeBreakdown` — `DataTable` of campaigns by creative.
- `LifeEventCampaigns` — feature card: **8 always-on segments**, target 2–3× mass-market CVR; each segment row shows status + lift; toggling a segment stages a `life_event_toggle` Directive.

**Primitives:** KPICard, ChartWrapper, Heatmap, DataTable, CardContainer; Directive on toggle.

**BFF data:** brand overview, impressions-by-channel, reach/freq-by-DMA, creative breakdown, life-event segments (`life_event_campaign`, `brand_market_bei`).

---

## 4. Performance Media  *(`4_Performance_Media.py`, `api/sem.py`)*

**Purpose:** paid search + paid social performance. **Two tabs.**

**Layout:** Tabs → **Paid Search (SEM)** | **Paid Social**.

**Feature components — SEM tab:**
- `SEMOverviewKPIs` — CPL, ROAS, quality score, spend.
- `SpendByIntent` — bar by intent type (branded/non-branded).
- `GoogleVsBing` — engine split (the multi-engine view — Google/Microsoft).
- `SEMCampaignTable` — top 10 by spend (`DataTable`).
- `SEMWeeklyTrend` — dual-axis spend & clicks.
- `QualityScoreByType` — bar.

**Feature components — Paid Social tab:**
- `SocialOverviewKPIs`, `PlatformBreakdown` (table), `PlatformSpendDistribution` (bar), `SocialEngagementMetrics`, `SocialWeeklyTrend`.

**Primitives:** Tabs, KPICard, ChartWrapper (bar/dual-axis), DataTable, CardContainer.

**BFF data:** `GET /api/channels/sem/overview|keywords|trends|match-types`; social equivalents (`social_platform_metric`, `social_creative`).

---

## 5. SEO  *(`5_SEO.py`, organic loaders)*

**Purpose:** organic search — GSC/GA4 overview, traffic trend, keyword rankings, top landing pages.

**Layout:** Organic Overview KPIs → Organic Traffic Trend (Brand vs Non-Brand) → Keyword Rankings table → Top Landing Pages table.

**Feature components:**
- `OrganicOverviewKPIs` — sessions, clicks, avg position, CTR (last 30 days).
- `OrganicTrafficTrend` — weekly sessions, Brand vs Non-Brand series.
- `KeywordRankingsTable` — tracked keywords with **position-change deltas** vs prior period (up/down arrows, color-coded).
- `TopLandingPages` — `DataTable` with conversion data.

**Primitives:** KPICard, ChartWrapper (line), DataTable, CardContainer.

**BFF data:** organic overview, traffic-trend, keyword rankings (`seo_ranking`), landing pages (`seo_traffic`).

---

## 6. AEO — AI Engine Optimization  *(`6_Organic_AEO.py`, `llm_visibility`)*

**Purpose:** how often the brand appears in AI-generated answers — the agentic-search readiness surface.

**Layout:** LLM Visibility Score (hero) → Mention Rate by Platform → Prompt Results → Competitive AEO Benchmarking.

**Feature components:**
- `LLMVisibilityScore` — hero `KPICard`/Gauge: the headline AEO score with trend.
- `MentionRateByPlatform` — line, mention rate per AI platform over N weeks (week selector).
- `PromptResultsTable` — per-query AI visibility (which prompts surface the brand).
- `CompetitiveAEOBenchmark` — bar: LLM Visibility Score vs tracked competitors.

**Primitives:** Gauge/KPICard, ChartWrapper (line/bar), DataTable, CardContainer, week selector.

**BFF data:** LLM visibility score + trend, mention-rate-by-platform, prompt-level results, competitor benchmark (`llm_visibility`).

---

## 7. Acquisition Funnel  *(`3_Acquisition_Funnel.py`, funnel queries, Kamino)*

**Purpose:** flow from Brand UOI → Active accounts, by product/DMA; where dollars leak; recovery.

**Layout:** Funnel Sankey (full width) → Drop-off Analysis → Abandonment Recovery Tracker.

**Feature components:**
- `FunnelSankey` — **Sankey diagram**: width = relative conversion, **red flows = drop-off**. The signature funnel visual. Segmentable by product/DMA via the global filter.
- `DropoffAnalysis` — **dollar impact of friction at each step** (`DataTable` + bar): quantifies $ lost per stage.
- `AbandonmentRecoveryTracker` — automated **Kamino sequences** by recovery window; shows active recovery flows, their window, and recovered volume; ties to `recovery_update` Directive.

**Primitives:** Sankey (ChartWrapper variant), DataTable, ChartWrapper (bar), CardContainer, MissionTracker (recovery status).

**BFF data:** funnel stages + conversion (`funnel_event`, `cohort`), drop-off $ by stage, recovery sequences.

---

## 8. Product & Experience  *(`7_Product_Experience.py`, `api/product.py`)*

**Purpose:** digital product delivery — pipeline by stage, transformation roadmap, testing velocity.

**Layout:** Product Pipeline (by stage) → Digital Experience Transformation Roadmap (3-wave) → Testing Velocity Tracker.

**Feature components:**
- `ProductPipeline` — initiatives grouped by **development stage** (kanban-style columns or stacked status), each card = initiative + status.
- `TransformationRoadmap` — **three-wave delivery model** timeline (roadmap_item) — horizontal waves with milestones.
- `TestingVelocityTracker` — `KPICard` row (tests live, win rate, avg lift, cadence) + trend; last-30-day A/B + multivariate cadence.

**Primitives:** KPICard, Kanban/StatusBoard (feature), Timeline (feature), ChartWrapper, CardContainer.

**BFF data:** `GET /api/product/pipeline|roadmap|testing-velocity`.

---

## 9. Operations Command  *(`8_Operations_Command.py`, `api/ops.py`, `api/directives.py`)*

**Purpose:** run-the-business ops — launches, capacity, **approval queue**, system health, competitive intel. **Five tabs.**

**Layout:** Operations Overview KPIs (Launches this month · Pending approvals · Systems healthy · Competitive signals) → Tabs: **Calendar · Capacity · Approvals · Health · Intel**.

**Feature components:**
- `OpsOverviewKPIs` — the 4-KPI row; Pending Approvals badge drives the rail badge.
- `LaunchCalendar` — marketing launch calendar (month grid of events).
- `TeamCapacity` — resource utilization bar by team/person.
- **`ApprovalQueue`** — the human-in-the-loop centerpiece. Each item = a Directive (`budget_reallocation`, `channel_mix_adjustment`, `test_launch`, `life_event_toggle`, `recovery_update`, `offer_strategy`, `market_tier_change`) with a **DiffView** (current vs proposed) + agent rationale; **Approve / Reject / Edit&approve**; decision writes to audit log; on approve, the row plays the success sweep and the directive advances its state-machine status.
- `SystemHealthMonitor` — service/integration health pills (synced/syncing/error).
- `CompetitiveIntelFeed` — incoming competitive signals (wire-style).

**Primitives:** KPICard, Tabs, Calendar (feature), ChartWrapper (bar), DiffView (feature), Button, HealthPill, AlertWire/Feed, MissionTracker.

**BFF data:** `GET /api/ops/calendar|capacity|approvals|health|competitive-feed`; `POST /api/ops/approvals/{id}/approve|reject`; directive lifecycle via `api/directives`.

---

## 10. Full-Funnel Simulator  *(`9_Simulator.py`, `simulator/*`)*

**Purpose:** scenario modeling — forecast marketing-mix impact across the full funnel; NBD budget optimizer. **Two tabs.** Heaviest compute → runs async via Kamino job.

**Layout:** Tabs → **Full-Funnel Simulator** | **NBD Optimizer**.

**Feature components — Simulator tab:**
- `SimulatorInputPanel` — `InputSlider` set: Annual Media Spend ($M), Brand Media %, MOB6 Retention Rate, Base LTV/HH, Visit→Lead, PFI Conversion, SEM CPC non-branded, Social CPL. **BD Mode** uses industry benchmarks; **Client Mode** uses configured data (banner indicates which). Advanced levers progressively disclosed.
- `SimulationResults` — `KPICard` grid: Total Spend, Funded Accounts, Retained HH (MOB6), PFI HH, Portfolio LTV, **CPIHH** (inverted delta — lower is better).
- `FunnelWaterfall` — projected volume vs industry benchmark per stage.
- `ScenarioComparison` — `ScenarioCompare` (maps to `scenario_compare`): A/B scenarios overlaid; **Mission Debrief** treatment — run = scan-line compute (≤900ms) → headline delta count-up with over-shoot when beating plan.

**Feature components — NBD Optimizer tab:**
- `BudgetObjectivePanel` — total budget + optimization goal (CAC / funded accounts / LTV) within NBD allocation bounds.
- `OptimizerResult` — recommended channel allocation + projected outcome; **"Commit"** stages a `budget_reallocation` Directive.

**Primitives:** Tabs, InputSlider, KPICard, ChartWrapper (waterfall/scatter), ScenarioCompare, MissionTracker, Button. Long run → async job with progress (scan-line) state.

**BFF data:** `POST /api/simulate` (scenario spec → projection, async job id), optimizer endpoint; benchmark config from Settings/metric layer.

---

## 11. Retention Forecast  *(`10_Retention_Forecast.py`, retention model)*

**Purpose:** parametric **survival-curve** modeler with segment filters and a draggable observation date. Async compute.

**Layout:** Segment Filters → Survival Curve (with movable observation-date slider) → Segment KPI cards.

**Feature components:**
- `SegmentFilterPanel` — multi-select segments to overlay on the curve.
- `SurvivalCurveChart` — the survival/retention curves per segment; **draggable observation-date slider** that recomputes retained-at-date live (Mission Debrief feel on recompute).
- `RetentionKPIs` — `KPICard` per segment: retention at MOBn, decay rate, projected retained HH.

**Primitives:** MultiSelect, ChartWrapper (survival curves), Slider (observation date), KPICard, CardContainer. Recompute → async/cached.

**BFF data:** retention curves by segment (`retention_cohort`, `geo_retention`), observation-date recompute endpoint.

---

## 12. Settings  *(`11_Settings.py`)*

**Purpose:** mode, appearance, integrations, and **all simulator/benchmark configuration** (the values the metric layer + simulator read).

**Layout:** Sections → Application Mode · Appearance · Data & Export · Data Source Integrations → benchmark Tabs (Funnel · Media · Defaults · Efficiency · NBD).

**Feature components:**
- `ApplicationModeToggle` — **BD vs Client mode** (drives data sources + simulator behavior platform-wide).
- `AppearancePanel` — **theme toggle** (light/dark; future themes) + density.
- `DataExportPanel` — cache + export preferences.
- `IntegrationsGrid` — connect external platforms (Google/Microsoft/Meta/GA4/Snowflake/…), each with **health status** + 2-click connect (maps to the Connector service).
- `BenchmarkEditor` (tabbed) — `InputSlider` sets for **Funnel conversion rates, Media coefficients, Simulator defaults, Channel efficiency scores, NBD allocation bounds**. These are the governed inputs the Metric Layer + Simulation service consume.

**Primitives:** Toggle, ThemeToggle, ConnectorCard (feature), Tabs, InputSlider, CardContainer, SectionHeader.

**BFF data:** settings/mode (Gateway context), connector list + health, benchmark config (Metric Layer).

---

## Feature-component inventory (the net-new composites beyond primitives)

These are the domain pieces a Claude design agent must build *in addition to* the system primitives:

| Feature component | Screen(s) | Notes |
|---|---|---|
| `DMASpendMap` / `GeoMap` | Spend, (Brand) | choropleth by DMA tier |
| `ChannelMixSliders` | Spend | drag within approved bands → Directive |
| `FunnelSankey` | Funnel | width = conversion, red = drop-off |
| `DropoffAnalysis` | Funnel | $ impact per stage |
| `AbandonmentRecoveryTracker` | Funnel | Kamino recovery sequences |
| `ApprovalQueue` + `DiffView` | Ops | HITL centerpiece, directive state machine |
| `LaunchCalendar` | Ops | month grid |
| `TeamCapacity` | Ops | utilization bars |
| `CompetitiveIntelFeed` | Ops, Scorecard | wire feed |
| `ProductPipeline` (Kanban) | Product | by stage |
| `TransformationRoadmap` (Timeline) | Product | 3-wave |
| `SimulatorInputPanel` + `SimulationResults` | Simulator | BD/Client modes |
| `FunnelWaterfall` | Simulator | vs benchmark |
| `ScenarioCompare` | Simulator | Mission Debrief |
| `SurvivalCurveChart` + observation slider | Retention | draggable date |
| `LLMVisibilityScore` + `CompetitiveAEOBenchmark` | AEO | agentic-search |
| `LifeEventCampaigns` | Brand | 8 always-on segments |
| `GoogleVsBing` engine split | Performance | multi-engine |
| `ConnectorCard` + `BenchmarkEditor` | Settings | governed inputs |
| `AgentConsole` + `OperatingStreak` | global / Scorecard | Mission-Control layer |

## States checklist (apply to every feature component)

For each: **loading** (skeleton), **empty** (filter yields nothing → guidance), **error** (retry), **populated**, **stale** (freshness badge), and where agentic: **proposed → queued → approved → executed** (with audit). Reduced-motion must fully disable celebrations/sweeps/count-ups. Every interactive element keyboard-reachable with a visible signal-cyan focus ring.

---

*Hand-off set = this spec + `Apex-Design-Memo-Combined.md` (system) + `DESIGN.md` (rules, authored in Task 3) + `Apex-React-Frontend-Scaffold-Prompt.md` (build instructions). Together they let a Claude design agent build every Apex surface without improvising.*
