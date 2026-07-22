# Apex — Unified Microservice Architecture

**A clean, consolidated services architecture derived from the existing Apex codebase.**

Version 1.0 · June 24, 2026 · For RVGT / Apex Marketing Intelligence Platform

---

## 1. What Apex is today (evaluation of current code)

Apex is an **RVGT marketing-intelligence platform** built as a **Streamlit multi-page monolith** in Python, backed by DuckDB (dev) / PostgreSQL (prod), with a partially-extracted **FastAPI service layer** and an async job/event subsystem called **Kamino**. The codebase is well-structured for a monolith but mixes presentation, business logic, and data access in ways that block independent scaling and reuse.

### 1.1 Current structure (as observed in `src/`)

| Layer | What's there | Notes |
|---|---|---|
| **Entry / shell** | `app.py` — `st.navigation()` over 12 pages, persistent global filter strip, brand CSS injection | Single process; pages run in-process |
| **Pages (12)** | Executive Scorecard, Spend Allocation, Brand Media, Performance Media, SEO, AEO, Acquisition Funnel, Product & Experience, Operations Command, Full-Funnel Simulator, Retention Forecast, Settings | `src/pages/`; registry in `src/config/settings.py:PAGES` |
| **Components** | `kpi_card`, `chart_wrapper`, `data_table`, `filter_bar`, `global_filter_strip`, `metric_strip`, `card_container`, `section_header`, `heatmap`, `channel_mix_sliders`, `scenario_compare`, `alert_badge`, `chat_drawer`, `page_chrome` | `src/components/` — a real, reusable design-component set |
| **API (FastAPI)** | Routers: `scorecard`, `sem`, `alerts`, `directives`, `ops`, `product` | `src/api/` — already a service seam, but co-deployed |
| **Simulator** | `engine`, `scenario_engine`, `simulation_engine`, `channel_projections`, `ui_helpers` | `src/simulator/` — heavy compute, full-funnel modeling |
| **Data** | Loaders/queries per domain (sem, organic, product, ops, retention, scorecard, spend, funnel), `alert_engine`, `database`, `orm`, ETL + seeds + benchmarks | `src/data/` — domain-segmented but directly imported by pages |
| **Kamino (jobs/events)** | `client` (HTTP client w/ retries), `models` (Directive, DirectiveType, DirectiveStatus state machine), `events` (Redis pub/sub) | `src/kamino/` — the agentic "directive" backbone |
| **Domain models** | ~40 SQLAlchemy models (campaign, budget, sem_daily_performance, seo_ranking, llm_visibility, retention_cohort, ops_*, directive, scenario, life_event_campaign, bei_score, …) | `src/models/` |
| **State** | `STATE_KEYS` registry, global vs. module-scoped session state, ownership rules | `src/state/` — cross-page contract |
| **Migrations** | Alembic (initial schema, retention domain, ops models) | `alembic/` |
| **Front end** | Next.js + TS + Tailwind app (Signal Deck design system) | `web/` — thin client over the BFF |

### 1.2 The seven functional domains (what the 12 pages actually do)

The pages collapse into **seven coherent capability domains**, which become the basis for services:

1. **Executive / Scorecard** — CMO KPI rollup, financial summary, live alert feed.
2. **Spend & Allocation** — budget distribution across channels/campaigns/business lines, optimization signals, pacing.
3. **Acquisition Channels** — Brand Media, Performance Media (SEM/paid social/programmatic), SEO, AEO (LLM visibility) — distinct surfaces, one "channel performance" family.
4. **Acquisition Funnel** — Brand UOI → Active accounts, by product and DMA.
5. **Product & Operations** — digital product metrics + launch calendar, team velocity, **approval queue**, system health, competitive intel.
6. **Simulation** — full-funnel scenario modeling (the heaviest compute).
7. **Retention** — parametric survival-curve forecasting with segment filters.

Cross-cutting: **Alerts**, **Directives (agentic actions)**, **Settings/benchmarks/mode (BD vs Client)**, **the chat drawer**, and the **global filter** (date range, product, DMA, channel) shared across every page.

### 1.3 Problems to fix in the merge

- **Presentation and logic are fused.** Pages import data loaders and simulator engines directly; there is no stable internal API boundary for most domains (only ~6 routers exist).
- **Two databases, ad hoc access.** DuckDB/Postgres chosen via env; `orm.py` + per-domain query modules but no single data-access contract.
- **Compute and UI share a process.** The simulator (expensive) runs in the Streamlit worker, so a heavy scenario blocks the UI.
- **Kamino is half-wired.** A directive state machine + Redis events exist, but execution/approval is not a clean, separately-deployable service.
- **State coupling.** `st.session_state` carries cross-page contracts that a service split must replace with explicit API params.

---

## 2. Target architecture — principles

1. **Separate the shell from the services.** The Streamlit app becomes a **thin presentation client** (later optionally replaced/augmented by a React front end per the design memos) that talks only to internal APIs — never to loaders or the DB directly.
2. **One service per capability domain**, each owning its data access and exposing a versioned REST/gRPC contract. The existing FastAPI routers are the seed.
3. **Heavy compute is its own service.** The simulator and retention modeler run as async workers behind Kamino, so the UI never blocks.
4. **Kamino becomes the action + job backbone.** All agentic "directives" (budget reallocation, channel-mix change, test launch, etc.) flow through one governed service with the existing state machine + approval queue.
5. **One semantic metric layer.** KPIs (CPL, ROAS, CPIHH, funded-accounts-per-media-$, BEI, LLM visibility) are defined once and read by every service — no page recomputes its own.
6. **Stateless services, explicit context.** Global filter (date/product/DMA/channel) and mode (BD/Client) travel as request parameters, not hidden session state.

---

## 3. Service map (the clean target)

Services + shared infrastructure. Services 1–10 map to existing Apex code; services 11–15 absorb capabilities from the two RV reference builds (`design/reference/RV-Reference-Capabilities.md`) — the **fitb-acquisition-engine-demo** (Next-Best-Dollar allocator) and **velocity-sites / Velocity Overdrive** (autonomous launch pipeline).

| # | Service | Absorbs (current code / reference repo) | Owns |
|---|---|---|---|
| 1 | **Gateway / BFF** | `app.py` shell wiring, `global_filter_strip`, auth | Routing, auth, request context (filter + mode), aggregation, **event bus with SSE fan-out + exact replay** (pattern from velocity-sites gateway) |
| 2 | **Scorecard Service** | `api/scorecard.py`, `data/scorecard_queries.py` | Executive KPIs, financial summary, alert feed read |
| 3 | **Channels Service** | `api/sem.py`, `data/sem_*`, `organic_*`, `social_brand_loaders`, `load_brand_bei`, `llm_visibility` | Brand/Performance media, SEM, SEO, AEO metrics + benchmarks |
| 4 | **Funnel Service** | `data/funnel_queries.py`, `funnel_event`, `cohort` | Acquisition funnel (Brand UOI → Active) by product/DMA |
| 5 | **Spend Service** | `data/spend_queries.py`, `load_budget_pacing`, `budget`, `mover_marketing` | Budget allocation, pacing, optimization signals |
| 6 | **Product & Ops Service** | `api/product.py`, `api/ops.py`, `data/product_*`, `ops_*` | Pipeline, roadmap, testing velocity, calendar, capacity, system health, competitive intel |
| 7 | **Simulation Service** | `simulator/*` + **Acquisition Engine allocator** | Full-funnel scenario modeling **and the Next-Best-Dollar allocator + rollout simulation** (async) |
| 8 | **Retention Service** | `data/retention*`, `account_retention_core`, `retention_cohort`, `geo_retention` | Survival-curve forecasting (async) |
| 9 | **Directive / Kamino Service** | `kamino/*`, `api/directives.py`, `api/ops.py` approvals, `directive` model | Agentic actions, state machine, approval queue, job execution, events |
| 10 | **Alerts Service** | `api/alerts.py`, `data/alert_engine.py`, `bei_score` thresholds | Threshold evaluation, alert lifecycle (ack), notifications |
| 11 | **Allocation / Optimization Service** | fitb-acquisition-engine `paid_media_budget_recommender.py` (Next-Best-Dollar) | **Fitted response curves per campaign×geo**, bounded marginal reallocation (0.4×–2.0×, ≤20%/wk), objective (Profit/Volume), waste-gap + "$ left on the table", 30-day rollout projection with curve refinement. Emits **proposed reallocations as Directives** (never auto-writes). |
| 12 | **Lens / NL→SQL Service** | velocity-sites `lens` + Apex `chat_drawer` | Connected-context chat **and** ask-the-data: semantic ontology → SQL gen → execute (SELECT-only/allowlist guards) → repair (≤2) → table + chart + NL summary, over the warehouse. |
| 13 | **Launch / Site Factory Service** | velocity-sites `factory` + `delivery` + `proofing` | Recommendation→tickets→proof→**real static-HTML build** (multi-page spec, JSON-LD, sitemap, calculator)→live preview→launch registry. The Conversion-pillar "Site Factory". |
| 14 | **Audit Service (Compliance + QA)** | velocity-sites `audit` | **Agentic compliance scans** (Member FDIC, EHL, Reg DD, offer T&Cs, UDAAP, comparative-claim, a11y) and **QA scans** (Lighthouse-ish, offer reconcile, link/CTA/schema crawl) — honest pass/warn/fail **with evidence**, reviewer memos. |
| 15 | **Experiments Service** | velocity-sites `experiments` | Seeded funnel simulation + **two-proportion A/B z-test, CI, power, O'Brien-Fleming sequential testing**; per-arm live ticks; winning variant + lift + honest confidence. |

Shared infra: **Metric Layer** (semantic definitions), **Data Access layer** (Postgres/Snowflake prod · DuckDB dev behind one contract), **Event Bus** (Redis pub/sub + SSE fan-out with exact replay), **Job Workers** (sim/retention/allocation/launch/directives), **Cache** (Redis), **Object/artifact store** (built sites, reports, scenarios), **AuthN/Z + RBAC**, **Observability**.

**Two cross-cutting patterns adopted from the reference builds:**
1. **Defensive client bridges** — every UI→service call has a deterministic in-engine fallback; a down service degrades gracefully instead of breaking the experience (velocity-sites `src/platform/client.js`).
2. **Real-data-swap-in** — synthetic seed data is shaped to mirror production CSVs (energy paid-media, keyword corpus, funnel benchmarks) so live data drops in with no UI change.

### 3.1 Diagram (text)

```
   Streamlit shell (thin)  ──┐                       ┌── React shell (per design memos, optional)
   global filter + mode      │                       │
                             ▼                       ▼
                    ┌──────────────────────────────────────┐
                    │     Gateway / BFF  (request context)  │
                    └───┬───────┬───────┬───────┬───────────┘
            ┌───────────┘       │       │       └─────────────┐
       Scorecard            Channels  Funnel    Spend     Product & Ops
            │                   │       │         │             │
            └──────────┬────────┴───────┴────┬────┴──────┬──────┘
                       ▼                      ▼           ▼
                 Metric Layer  ◄────  Data Access (PG/DuckDB)   Alerts ──► notify
                       ▲                      ▲
        Simulation ────┘        Retention ────┘    (async via Job Workers)
                       │                      │
                       └──────► Directive / Kamino Service ──► Event Bus (Redis)
                                   (state machine + approval queue + execution)
```

---

## 4. Service detail (extraction plan from current code)

**1. Gateway / BFF.** Wraps the current `app.py` wiring. Resolves the **request context** — the global filter (`date_range`, `product`, `dma`, `channel`) and **mode** (`BD` vs `Client`) that today live in `st.session_state` — and passes them as explicit params to downstream services. Hosts auth and RBAC. Aggregates multi-service responses for the Scorecard page.

**2. Scorecard Service.** Promote `api/scorecard.py` to standalone. Endpoints already exist: `/kpis`, `/financial-summary`, `/alerts`. Reads through the Metric Layer; never recomputes KPIs locally.

**3. Channels Service.** Consolidate the four channel pages (Brand, Performance, SEO, AEO) behind one service. `api/sem.py` is the template (`/overview`, `/keywords`, `/trends`, `/match-types`). Add `/brand`, `/seo`, `/aeo` sub-resources backed by the existing organic/social/BEI/LLM-visibility loaders.

**4. Funnel Service.** Extract `funnel_queries.py`; expose funnel stages, conversion rates, and segment drill-downs (product, DMA). Shares stage-rate benchmarks with the Simulation Service.

**5. Spend Service.** Extract `spend_queries.py` + budget pacing. Exposes allocation by channel/campaign/line, pacing vs. plan, and **optimization signals** that can be turned into Directives.

**6. Product & Ops Service.** Merge `api/product.py` and `api/ops.py` — they're closely related (delivery + operations). Owns pipeline, roadmap, testing velocity, launch calendar, team capacity, **approval queue surface**, system health, competitive feed.

**7. Simulation Service.** Extract `simulator/*` and run it **off the UI thread** as a Kamino job. Input: scenario spec (channel mix, spend, benchmarks). Output: full-funnel projection + before/after comparison artifact. The current `ui_helpers.py` logic moves to the BFF/front end; the math stays server-side.

**8. Retention Service.** Extract the retention modeler (`retention_model_core`, `retention_forecast`, `account_retention_core`). Parametric survival curves with segment filters and a movable observation date, computed async and cached.

**9. Directive / Kamino Service.** The agentic backbone. Already has the right primitives: `DirectiveType` (budget_reallocation, market_tier_change, channel_mix_adjustment, life_event_toggle, test_launch, recovery_update, offer_strategy), a `DirectiveStatus` state machine (pending → approved → in_progress → completed/failed/cancelled) with guarded transitions, a retrying HTTP `client`, and Redis `events`. Promote to a full service: submit → classify → **approval queue** (from `api/ops.py` approvals) → execute → emit events. This is where human-in-the-loop governance lives.

**10. Alerts Service.** Extract `alert_engine.py` + `api/alerts.py`. Periodically evaluates metrics against thresholds (`/evaluate`), persists alerts, supports acknowledge, and pushes to the notification channel + the Scorecard feed.

### 4.1 Shared: Metric Layer

The single most valuable cleanup. Today KPIs are computed inside per-domain query modules. Extract a **metric definition module** (name → SQL/expression → grain) covering: CPL, ROAS, CPM, quality score, BEI, LLM visibility score, funnel stage rates, CPIHH, funded-accounts-per-media-dollar, retention/survival. Every service reads metrics from here so "ROAS" means one thing platform-wide.

### 4.2 Shared: Data Access

One contract over **PostgreSQL (prod) / DuckDB (dev)** — formalize what `orm.py` + `database.py` start. Services depend on the contract, not on a driver. Alembic remains the migration source of truth; the ~40 existing models are partitioned by service ownership (e.g., `sem_*`, `seo_*`, `llm_visibility` → Channels; `retention_*`, `geo_retention` → Retention; `ops_*`, `directive` → Product&Ops / Kamino).

### 4.3 Reference-build capabilities (from velocity-sites & fitb-acquisition-engine-demo)

Source: `design/reference/RV-Reference-Capabilities.md`. These are the concrete capabilities the two RV demo repos contribute; they live in the new services 11–15.

**(a) Next-Best-Dollar allocator — Allocation/Optimization Service (#11).** The Acquisition pillar's optimization core.
- Fits a **diminishing-returns response curve per campaign×geo combo**: `accounts = k · ln(1 + spend / S_REF)`. Combos = campaign × geo (e.g., 10 campaigns × 6 metros).
- **Bounded marginal reallocation**: each combo clamped to **[0.4× – 2.0×] of current spend** — what a **30-day, ≤20%/week** rollout can physically reach. Guarantees the optimized plan beats current and is reachable.
- **Objective**: Profit (contribution margin = accounts×value − spend) or Volume (accounts), under a fixed **Budget**.
- Produces: the **waste gap** (today's actual sits below the efficient curve), per-combo **optimal-spend target**, **top moves**, and the headline **"$ left on the table / year"** at constant budget.
- **Rollout simulation**: curve refinement day-0 → day-30 (the agent "learns" the true response); per-combo spend travels toward its optimal; donor→recipient money-flow across the geo map.
- **Governance**: the optimizer never writes — it emits a `budget_reallocation` / `channel_mix_adjustment` **Directive** for the approval queue, and the agent **defends each move with the numbers**.

**(b) Autonomous launch pipeline — Launch/Site Factory (#13) + Audit (#14) + Experiments (#15).** The Conversion pillar's "Site Factory".
```
Lens (persona prompt) → Recommendations → Tickets → Delivery board (gate: all Done)
→ Creative Proofing (review + real revise-to-v2, gate: approve) → Site Factory (real static-HTML build)
→ Live Preview → Compliance scan (evidence) → QA scan (evidence) → Approve (human gate)
→ A/B Test Setup (metric/variants/split) → Launch (registry) → performance feeds back into Lens → next persona
```
- **Operator-paced with human gates** — does not auto-play; each stage runs/awaits then advances. Interactive gates: move tickets, approve proofs, **Approve** launch, start experiment.
- **Real artifacts**: the factory renders a multi-page spec to **real static HTML** (routes, schema.org JSON-LD, disclosures, working calculator, sitemap/robots); compliance & QA **scan the built spec** and return honest pass/warn/fail **with evidence**; experiments run a **two-proportion z-test** (CI, power, O'Brien-Fleming) on a seeded funnel sim.
- **First-party guardrail**: launched pages are the client's own (e.g., 53.com) — Member FDIC / EHL, real offer T&Cs, no affiliate links or competitor comparisons. (Also recorded in `DESIGN.md` governance.)

**(c) Lens NL→SQL — Lens Service (#12).** Ask-the-data: **semantic ontology → SQL generation → execute (SELECT-only / allowlist guards) → repair (≤2 retries) → result table + chart + natural-language summary**, over the metric-layer warehouse, with deterministic fallbacks at every step.

---

## 5. Recommended deployment & stack (minimal change from today)

| Concern | Choice | Rationale |
|---|---|---|
| Service language | **Python (FastAPI)** | Reuse 100% of existing routers, models, engines |
| Presentation | **Streamlit (now)** → optional **React/Next** (design memos) | Thin client either way; talks only to BFF |
| Async jobs | **Kamino + Redis** (already present) + a worker pool (Celery/RQ/Arq) | Sim/retention/directives off the UI thread |
| Data | **PostgreSQL (prod)**, DuckDB (dev) behind one DAL | No rewrite; formalize the seam |
| Events | **Redis pub/sub** (already used by Kamino) | Directive lifecycle, alert fan-out |
| Metric layer | Python module (start) → dbt/semantic layer (scale) | One definition of every KPI |
| Packaging | One container image per service, **Docker Compose** (dev) → **Kubernetes** (prod) | Independent scaling: Simulation/Retention scale separately from UI |
| Contracts | OpenAPI per service (FastAPI gives this free) | Stable seams; enables the React front end |

---

## 6. Migration sequence (low-risk, incremental)

1. **Freeze contracts.** Define OpenAPI for the 6 existing routers; add request-context params (filter + mode) so nothing depends on `st.session_state`.
2. **Introduce the BFF.** Point the Streamlit pages at the BFF instead of importing loaders directly — page by page, starting with Scorecard (already API-backed).
3. **Extract the Metric Layer.** Move KPI definitions out of query modules; repoint services at it.
4. **Carve out heavy compute.** Move the Simulator and Retention modeler behind Kamino jobs (biggest UX win — UI stops blocking).
5. **Promote Kamino to a service.** Wire submit → approval queue → execute → events end-to-end; this unlocks the agentic/directive features cleanly.
6. **Split remaining domains** (Channels, Funnel, Spend, Product&Ops, Alerts) behind their contracts.
7. **Containerize + orchestrate.** One image per service; Compose → K8s.
8. *(Optional)* **Swap the shell.** With stable BFF contracts, a React front end (per the chosen design memo) can replace or run alongside Streamlit without touching services.

---

## 7. Feature → service traceability

| Current page / feature | Target service |
|---|---|
| Executive Scorecard | Scorecard (+ Alerts feed) |
| Spend Allocation | Spend |
| Brand Media / Performance Media / SEO / AEO | Channels |
| Acquisition Funnel | Funnel |
| Product & Experience | Product & Ops |
| Operations Command (calendar, capacity, approvals, health, intel) | Product & Ops (+ Directive for approvals) |
| Full-Funnel Simulator | Simulation (async) |
| Retention Forecast | Retention (async) |
| Settings (theme, benchmarks, connectors, BD/Client mode) | Gateway/BFF (context) + Metric Layer (benchmarks) |
| Chat drawer / directives | Directive / Kamino |
| Alert badge / alert engine | Alerts |
| Global filter strip | Gateway/BFF (request context) |

---

*This architecture preserves every existing feature and component while giving Apex clean service boundaries, off-thread compute, a single metric definition, and a governed agentic-action backbone — and it leaves the door open to the React front end designed in the accompanying UX/UI memos.*
