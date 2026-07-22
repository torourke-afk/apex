# Apex Codebase Audit — July 2026

Goal: Identify every gap between the current state and connecting to real accounts. Prioritized by what blocks real-data connectivity.

---

## Executive Summary

The UI shell and all 13 surfaces are built and rendering. The BFF has 16 routers with 40+ endpoints, and about 40% of those hit real DuckDB queries. But the frontend and backend are barely connected — only 2 of 14 React hooks actually call the BFF. The rest return hardcoded inline data. There are zero external API integrations (Google Ads, Meta, GA4, Snowflake, Salesforce are all listed in Settings but none are wired). There is no authentication, no deployment config, and no tests. A dead Next.js codebase coexists with the active Vite app, and the live-API switch is broken because it reads a Next.js env var that Vite never sets.

**Shortest path to real accounts:** Fix the API client → wire hooks to live BFF → build integration layer → add auth.

---

## 1. CRITICAL — Blocks Any Real Data

### 1.1 Dead live-API switch (lib/api.ts line 13)

The `isLive()` function checks `process.env.NEXT_PUBLIC_API_BASE`. This is a Vite project — `process.env` is always `undefined`. The live code path in `bff.ts` is permanently unreachable. Meanwhile, `api/client.ts` correctly uses `import.meta.env.VITE_API_URL` but is imported by nothing.

**Fix:** Delete `lib/api.ts`. Rewire `api/hooks.ts` to use `api/client.ts` (`apiFetch<T>()`) for all BFF calls. One-file change, unlocks everything downstream.

### 1.2 Frontend hooks are all hardcoded stubs

14 hooks in `web/src/api/hooks.ts`. Current state:

| Hook | Calls BFF? | BFF endpoint exists? |
|------|-----------|---------------------|
| useScoreboardKPIs | Via broken lib/api.ts | Yes — `/api/scorecard/kpis` |
| useFinancialSummary | No (inline stub) | Yes — `/api/scorecard/financial-summary` |
| useAlerts | Via broken lib/api.ts | Yes — `/api/scorecard/alerts` |
| useSpendOverview | No (mock fn) | Yes — `/api/spend/overview` |
| useSpendPacing | No (mock fn) | Yes — `/api/spend/pacing` |
| useSpendDMA | No (mock fn) | Yes — `/api/spend/dma` |
| useFunnelStages | No (mock fn) | Yes — `/api/funnel/stages` |
| useSEMOverview | No (inline stub) | Yes — `/api/channels/sem/overview` |
| useBrandAwareness | No (inline stub) | Yes — `/api/brand-awareness/share-of-search` |
| useApprovals | No (inline stub) | Yes — `/api/ops/approvals` |
| useProductPipeline | No (inline stub) | Yes — `/api/product/pipeline` |
| useTestingVelocity | No (inline stub) | Yes — `/api/product/testing-velocity` |
| useRetentionCurves | No (inline stub) | Yes — `/api/retention/curves` |
| useBenchmarks | No (inline stub) | Yes — `/api/settings/benchmarks` |

**Every BFF endpoint already exists.** The hooks just need to call `apiFetch` instead of returning inline objects.

### 1.3 Two competing HTTP clients

- `api/client.ts` — Vite-correct (`import.meta.env.VITE_API_URL`), type-safe `apiFetch<T>()`. **Not imported by any hook.**
- `lib/api.ts` — Next.js-era (`process.env.NEXT_PUBLIC_API_BASE`), broken `get<T>()`. **Used by bff.ts for the 2 hooks that attempt live calls.**

**Fix:** Consolidate on `api/client.ts`. Delete `lib/api.ts`, `lib/bff.ts`, `lib/bff-extended.ts`.

### 1.4 Zero external API integrations

Settings shows connector cards for: Google Ads, Microsoft Advertising, Meta, GA4, Snowflake, Salesforce. `src/integrations/__init__.py` is empty. There are no API clients, no OAuth flows, no webhook receivers, no ETL pipelines. All data is DuckDB seed tables.

Partial exception: `src/data/brand_awareness.py` reads `SEMRUSH_API_KEY` and makes real HTTP calls to SEMrush. This is the only external integration in the entire codebase.

---

## 2. HIGH — Required for Production

### 2.1 Zero authentication on BFF

Every endpoint is public. `POST /api/directives` creates approval-queue items with no identity verification. `PATCH /api/alerts/{id}/acknowledge` acknowledges alerts for anyone. CORS is localhost-only (dev) which provides zero security against direct HTTP calls.

**Needed:** JWT or OAuth2 middleware on FastAPI, user session management, role-based access for the directive approval queue.

### 2.2 Dead Next.js code still in tree

Files that import `next/link`, `next/navigation`, or use `"use client"` directives:
- `web/src/app/` (entire directory — App Router pages)
- `web/src/components/AppShell.tsx`
- `web/src/lib/theme.tsx`, `lib/providers.tsx`, `lib/api.ts`, `lib/bff.ts`, `lib/bff-extended.ts`
- `web/src/lib/hooks.ts` line 1 (`"use client"`)

`next` is NOT in `package.json`. The dead code is excluded from `tsconfig.json` `include` so it doesn't cause build errors, but it creates a maintenance trap. The active hooks in `api/hooks.ts` import from `lib/bff.ts` and `lib/bff-extended.ts` — creating a real dependency on the dead code.

**Fix:** Delete `web/src/app/`, `web/src/components/`, `web/src/lib/` entirely. Move any still-needed mock data into `api/hooks.ts` fallbacks. Delete `web/next.config.mjs`, update `.eslintrc.json` to remove `next/core-web-vitals`.

### 2.3 requirements.txt is for Streamlit, not BFF

Current `requirements.txt` lists: streamlit, plotly, altair, streamlit-aggrid, pandas, numpy, scipy. Missing the BFF's actual runtime deps: fastapi, uvicorn, pydantic, httpx, apscheduler, duckdb-engine, cachetools.

**Fix:** Create `pyproject.toml` with proper BFF dependencies. Keep legacy `requirements-streamlit.txt` if the frozen Streamlit app needs to stay runnable.

### 2.4 BFF monkey-patches Streamlit at import time

`src/api/__init__.py` imports `streamlit as _st` and replaces `st.cache_data` / `st.cache_resource` with `cachetools` wrappers. The data layer modules use `@st.cache_data` decorators, coupling them to Streamlit's runtime. A Streamlit version upgrade could break the BFF.

**Fix:** Replace `@st.cache_data` in data modules with `@functools.lru_cache` or `cachetools.TTLCache`. Remove the Streamlit shim from `__init__.py`.

### 2.5 No deployment infrastructure

Missing: Dockerfile, docker-compose.yml, CI config (.github/workflows/), production nginx config, health check endpoint, Procfile/fly.toml/cloud manifests.

### 2.6 No tests

Frontend: zero test files, no test runner in `package.json`. Backend: 34 test files exist but are entangled with Streamlit module shims. The router-level tests (scorecard, SEM, alerts, directives, ops, product) may still be runnable but the test infrastructure needs modernization.

### 2.7 Global FilterBar is disconnected

The FilterBar updates ShellProvider state (dateRange, products, dmas, channels), but no data hook reads those values. Filter selections have zero effect on any surface's displayed data. (Note: the Awareness surface correctly uses its own local filter — that one works.)

### 2.8 Silent error swallowing in 8 BFF routers

Spend, funnel, channels (brand/SEO/AEO/social), retention, and brand_awareness routers all use `try: ... except Exception: return <fallback>`. Every error returns 200 OK with placeholder data. Production debugging would be extremely difficult.

---

## 3. MEDIUM — Quality & Maintainability

### 3.1 ~85 hardcoded color values violate design system

The "no hardcoded hex" rule (DESIGN.md) is violated across 15 files. The dominant pattern is `rgba(52,225,212,...)` (teal accent decomposed into RGB at various opacities). Should use CSS custom properties with opacity modifiers.

Worst offenders: SettingsView.tsx (11 values), Creative.tsx (6 gradient pairs), searchTrends.ts (10 brand colors — arguably intentional), ContextBar.tsx (gradient hex).

### 3.2 Non-functional UI elements

| Element | File | Issue |
|---------|------|-------|
| Agent Console SEND button | shell/AgentConsole.tsx | No onClick handler |
| Agent Console input | shell/AgentConsole.tsx | No submit mechanism |
| ACK button (Scorecard alerts) | surfaces/Scorecard.tsx | No onClick handler |
| APPROVE/REJECT/DEFER buttons | surfaces/Operations.tsx | No onClick handlers |
| CLEAR CACHE button | surfaces/SettingsView.tsx | No onClick handler |
| BD/Client toggle (ContextBar) | shell/ContextBar.tsx | Sets state, nothing reads it |
| "SYNCED · 2m AGO" label | shell/ContextBar.tsx | Hardcoded, never updates |
| Tool chips (AgentConsole) | shell/AgentConsole.tsx | Decorative only |

### 3.3 ContextBar entirely hardcoded

Client name "Fifth Third", sync status "SYNCED · 2m AGO", "+ 2 RV VALIDATION", gradient colors — all static strings. Should be driven by BFF settings/session data.

### 3.4 Inconsistent database access patterns

Two patterns coexist in the BFF:
1. Raw DuckDB (`duckdb.connect()`) — in scorecard_queries.py, spend_queries.py, funnel_queries.py
2. SQLAlchemy ORM — in sem.py, alerts.py, ops.py, directives.py

Should consolidate on SQLAlchemy for consistency and connection management.

### 3.5 Fabricated benchmark in hooks.ts

Line 172: `benchmark: convRate * 0.95` — guarantees the company always outperforms the benchmark by 5%. This would be misleading with real data.

### 3.6 Simulator uses only client-side math

Simulator surface does all calculations with hardcoded constants in the browser. The BFF has `POST /api/simulate/` with a proper simulation engine, but the surface doesn't call it.

### 3.7 DuckDB files are ~700MB

`apex_clean.duckdb` (350MB) and `apex_dev.duckdb` (349MB) plus WAL files. `.gitignore` excludes them now but they may exist in git history.

### 3.8 Alembic migrations potentially stale

`alembic/` directory exists with config pointing to `apex_dev.duckdb`. Unclear if migrations match the current 14 ORM models in `src/data/orm.py`.

---

## 4. Surface-by-Surface Readiness

| # | Surface | Frontend Data | BFF Router | External API Needed | Readiness |
|---|---------|--------------|------------|--------------------:|-----------|
| 1 | Scorecard | 2 hooks via broken api.ts; inline fallbacks | Real DB (4 tables) | GA4, Google Ads aggregates | 30% |
| 2 | Spend | Mock functions | Real DB (funnel_summary_daily) | Google Ads, Meta spend feeds | 15% |
| 3 | Media | Hardcoded MEDIA_ROWS | Real DB (sem_daily + sem_keywords) | Google Ads, Meta, Microsoft Ads | 10% |
| 4 | Creative | 100% hardcoded, no hooks | **No router** | Creative asset API (Meta, Google) | 0% |
| 5 | Audience | Hardcoded segments | Mock (reuses spend DMA) | GA4 audiences, CRM segments | 5% |
| 6 | Awareness | Local searchTrends.ts (226KB real data) | Real DB (brand_awareness) | Google Ads Keyword Planner | 70% |
| 7 | Funnel | Mock via bff-extended.ts | Real DB + synthetic jitter | GA4 funnel, CRM conversion events | 15% |
| 8 | Product | Hooks exist but data discarded | Hardcoded seed (pipeline, roadmap) | Jira/project management API | 5% |
| 9 | Retention | Hardcoded 5 datasets | Synthetic 250K-account model | Core banking data, CRM | 10% |
| 10 | Operations | Inline stub | Real DB (directives table) | Internal approval system | 25% |
| 11 | Simulator | 100% client-side | Full simulation engine exists | None (model-driven) | 40% |
| 12 | Modeling | 100% hardcoded | **No router** | MMM/attribution model outputs | 0% |
| 13 | Settings | Inline stub | Hardcoded benchmarks | Account settings, OAuth flows | 5% |

---

## 5. Recommended Execution Order

### Phase 1: Unblock the pipe (1-2 days)
1. **Fix the API client** — delete `lib/api.ts`, rewire hooks to `api/client.ts`
2. **Wire all 14 hooks to live BFF endpoints** — every endpoint already exists
3. **Delete dead Next.js code** — `web/src/app/`, `web/src/components/`, `web/src/lib/`
4. **Fix requirements.txt** — create `pyproject.toml` with actual BFF deps

### Phase 2: Make it real (3-5 days)
5. **Wire FilterBar to hooks** — pass filter state as query params to BFF endpoints
6. **Wire Operations buttons** — APPROVE/REJECT/DEFER → POST `/api/ops/approvals/{id}/approve|reject`
7. **Wire Simulator to BFF engine** — replace client-side math with `POST /api/simulate/`
8. **Remove Streamlit coupling** — replace `@st.cache_data` with `functools.lru_cache`
9. **Fix error handling** — replace catch-all swallowing with proper HTTP error responses
10. **Build Creative and Modeling routers** — the 2 surfaces with no backend at all

### Phase 3: Connect external data (1-2 weeks)
11. **Google Ads API integration** — spend, keywords, SEM performance
12. **Meta Ads API integration** — social spend, creative performance
13. **GA4 integration** — funnel events, audience segments, traffic
14. **OAuth flow for Settings connectors** — so users can connect their own accounts

### Phase 4: Production-ready (1 week)
15. **Add JWT authentication** — FastAPI security middleware
16. **Dockerize** — BFF + frontend containers
17. **CI pipeline** — lint, typecheck, test on every push
18. **Clean up hardcoded colors** — replace ~85 hex/rgba values with CSS variables

---

## 6. Quick Wins (< 1 hour each)

- Delete `web/next.config.mjs` and update `.eslintrc.json`
- Remove `"use client"` from `lib/hooks.ts` line 1
- Fix fabricated benchmark (hooks.ts line 172)
- Add `onClick` to Operations APPROVE/REJECT/DEFER buttons
- Add `onClick` to Agent Console SEND button (even if just a placeholder)
- Replace hardcoded "SYNCED · 2m AGO" with a relative-time component
- Add `.env` to `.gitignore` (verify it's not tracked in git history)
