# AGENTS.md — How to build Apex

> **AGENTS.md = how to build it. `DESIGN.md` = how it should look.** Read both before touching UI.

Apex is the RVGT marketing-intelligence platform. The front end is a **React (Vite) + TypeScript + Tailwind** thin client over a **FastAPI BFF** that wraps the existing Python data layer (DuckDB + SQLAlchemy + seed data). SQL/metrics live in the data + metric layers; the UI consumes BFF JSON via typed hooks and never queries SQL directly.

## Read-first (every session, before any UI work)

1. **`DESIGN.md`** (repo root) — the design system: tokens, type, spacing, motion, component + governance rules. **Style must not drift from it.**
2. **`design/Apex-Design-Memo-Combined.md`** — the system rationale + full component/motion spec ("Signal Deck").
3. **`design/Apex-Feature-Components-Screen-Spec.md`** — screen-by-screen composition for all 12 surfaces + the BFF endpoint readiness / build-order map.
4. **`design/Apex-Unified-Microservice-Architecture.md`** — service boundaries, the metric layer, and how the BFF is assembled.
5. **`design/Apex-React-Frontend-Scaffold-Prompt.md`** — the master build prompt (DESIGN.md → component library → a11y/responsive pass).
6. Visual reference: **`design/mockups/Executive-Scorecard.dc.html`** — the delivered mockup; the design source of truth for tokens, font, and palette.

## Hard rules

- **No hardcoded colors.** Use the semantic tokens / Tailwind aliases defined in `DESIGN.md`. Red (`--color-critical`) is for critical/destructive only.
- **Fonts:** Space Grotesk (UI) + JetBrains Mono (all numerals, `tabular-nums`).
- **Theming:** light/dark via `data-theme`; new themes are token blocks, never component edits.
- **Accessibility:** every interactive element keyboard-reachable with a visible signal focus ring; WCAG AA contrast (CI lint); full support for `prefers-reduced-motion`.
- **Data boundary:** React components consume BFF JSON via typed hooks (TanStack Query). No SQL, no Streamlit, no data logic in components. Mock with MSW against BFF contracts until a service is live (see build-order map in the screen spec).
- **Governance:** any account-changing action is a **Directive** routed through the approval queue with a diff — never an instant write. Agent proposes, human confirms, action is audit-logged.
- **Motion/feedback:** celebrations only on rare real wins, ≤600ms, never blocking, max one at a time; reduced-motion disables them.
- Run the **pre-merge checklist in `DESIGN.md` §8** before shipping any UI.

## Stack

React (Vite 6) · TypeScript · Tailwind 4 (tokens aliased to CSS vars) · lucide-react (icons). Custom `useQuery<T>` hook for server state (no external dependency). All charts are hand-drawn SVG (no Recharts/visx dependency). Backend: FastAPI (uvicorn) + DuckDB (dev/seed) behind the data-access layer. Kamino directive engine for the approval queue.

## Front-end architecture (`web/`)

```
web/
├── src/
│   ├── main.tsx            # StrictMode → ShellProvider → AppShell
│   ├── nav.ts              # 13-surface NavEntry[] table
│   ├── globals.css          # CSS custom properties + keyframes
│   ├── api/                 # BFF client layer
│   │   ├── client.ts        # apiFetch<T>() wrapper (VITE_API_URL)
│   │   ├── types.ts         # 25 TypeScript interfaces for BFF responses
│   │   ├── hooks.ts         # Generic useQuery<T> + 22 domain hooks
│   │   └── index.ts         # Barrel export
│   ├── shell/               # App chrome
│   │   ├── ShellProvider.tsx # Context: theme, mode, autopilot, view, rail, accent
│   │   ├── AppShell.tsx     # Root layout: Atmosphere + Rail + ContextBar + FilterBar + SurfaceRouter + AgentConsole
│   │   ├── Rail.tsx         # Collapsible icon rail (218px ↔ 64px)
│   │   ├── ContextBar.tsx   # Breadcrumb, sync pill, BD/CLIENT toggle
│   │   ├── FilterBar.tsx    # RANGE/PRODUCT/DMA/CHANNEL chips
│   │   ├── AgentConsole.tsx # Footer command prompt
│   │   └── Atmosphere.tsx   # 3 aura blobs + 450-dot cursor-repel field
│   ├── surfaces/            # 13 feature surfaces + router
│   │   ├── SurfaceRouter.tsx
│   │   ├── Scorecard.tsx    # Executive Scorecard (hero gauge + KPI deck + financials + alerts)
│   │   ├── Spend.tsx        # Budget pacing + allocation + reallocation ledger
│   │   ├── Media.tsx        # Channel performance table + saturation + efficiency frontier
│   │   ├── Creative.tsx     # Creative units grid + message resonance bars
│   │   ├── Audience.tsx     # DMA heatmap + top markets + audience segments
│   │   ├── BrandAwareness.tsx # Share of search + peer comparison
│   │   ├── Product.tsx      # Product line table + conversion funnels
│   │   ├── Funnel.tsx       # SVG Sankey (channel → funded) + stage rate cards
│   │   ├── Retention.tsx    # Cohort heatmap + LTV accrual chart
│   │   ├── Operations.tsx   # Approval queue + directive review (interactive)
│   │   ├── Simulator.tsx    # Budget sliders + projected outcome (interactive)
│   │   ├── Modeling.tsx     # Attribution bars + model registry + incrementality tests
│   │   └── SettingsView.tsx # Mode/appearance/data/integrations/benchmarks
│   └── ui/                  # Design system primitives
│       ├── Card.tsx, SectionHeader.tsx, Pill.tsx, Segmented.tsx
│       ├── MiniRing.tsx, Sparkline.tsx
│       └── index.ts
├── package.json             # Vite + React 19 + TS + Tailwind + lucide-react
├── vite.config.ts           # Port 5173, @ alias
├── tailwind.config.ts       # Signal Deck tokens mapped to Tailwind
└── tsconfig.json            # Strict, ESNext, bundler resolution
```

## Back-end architecture (`src/api/`)

FastAPI app at `src.api:app`, 16 routers:

| Router | Prefix | Endpoints |
|--------|--------|-----------|
| scorecard | `/api/scorecard` | kpis, financial-summary, alerts |
| sem | `/api/channels/sem` | overview, keywords |
| spend | `/api/spend` | overview, pacing, dma |
| funnel | `/api/funnel` | stages, dropoff |
| channels_brand | `/api/channels/brand` | overview, platforms, bei, life-events |
| channels_seo | `/api/channels/seo` | rankings, traffic |
| channels_aeo | `/api/channels/aeo` | summary, trends, prompts |
| channels_social | `/api/channels/social` | overview, platforms |
| retention | `/api/retention` | curves, kpis |
| brand_awareness | `/api/brand-awareness` | share-of-search, peer-comparison |
| simulate | `/api/simulate` | POST /, GET /presets |
| settings | `/api/settings` | benchmarks, mode |
| product | `/api/product` | pipeline, roadmap, testing-velocity |
| ops | `/api/ops` | approvals, calendar, health |
| alerts | `/api/alerts` | evaluate, list |
| directives | `/api/directives` | list, create, approve, reject |

CORS allows `localhost:3000`, `localhost:5173`, and `127.0.0.1` variants.

## Running locally

```bash
# Terminal 1 — BFF
cd Apex
uvicorn src.api:app --reload --port 8000

# Terminal 2 — React
cd Apex/web
npm install
npm run dev        # → http://localhost:5173
```

## Legacy note

The Streamlit app (`app.py`, `src/pages/`, `src/components/`, `src/config/brand.py`) still runs but is frozen. `brand.py` has been synced to the new tokens. New UI is React only; do not add Streamlit pages.

## Workflow

1. Read the read-first set. 2. Confirm which BFF endpoints exist vs. need mocking. 3. Build against `DESIGN.md`. 4. Validate in a browser (both themes, keyboard-only). 5. Run the pre-merge checklist (`DESIGN.md` §8). 6. Commit with a clear message.
