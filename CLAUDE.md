# CLAUDE.md — Apex

Apex is the RVGT marketing-intelligence platform. This file is the entry point for any agent working in this repo.

## Read-first

- **`DESIGN.md`** (repo root) — the design system ("Signal Deck"): how the UI must look. **Read before any UI work; style must not drift from it.**
- **`AGENTS.md`** (repo root) — how to build Apex (stack, hard rules, workflow).
- **`design/`** — the full design + architecture spec set:
  - `Apex-Design-Memo-Combined.md` — the design *system* (tokens, primitives, theming, motion). **The design source of truth referenced by all UI work.**
  - `Apex-Feature-Components-Screen-Spec.md` — screen-by-screen composition for all 12 surfaces + BFF build-order map.
  - `Apex-Unified-Microservice-Architecture.md` — service boundaries, metric layer, BFF.
  - `Apex-React-Frontend-Scaffold-Prompt.md` — master front-end build prompt.
  - `mockups/Executive-Scorecard.dc.html` — delivered visual reference / token source of truth.
  - `reference/RV-Reference-Capabilities.md` — capabilities absorbed from the RV demo repos **velocity-sites** (Velocity Overdrive launch pipeline) and **fitb-acquisition-engine-demo** (Next-Best-Dollar allocator). These feed the Acquisition Engine + Launch Pipeline surfaces and services 11–15 in the architecture.

## What Apex is

A CMO-grade marketing-intelligence console across 7 domains (Executive Scorecard, Spend, Channels [Brand/Performance/SEO/AEO], Funnel, Product & Ops, Simulator, Retention) + Settings, plus an agentic **Directive** layer (Kamino) with a human-in-the-loop approval queue.

## Architecture

**React (Vite) + TypeScript + Tailwind** thin client (`web/`) over a **FastAPI BFF** (`src/api/`) that wraps the existing Python data layer (DuckDB + SQLAlchemy + seed data). All 13 surfaces are built and routing live. The BFF exposes 16 routers with typed JSON endpoints; the React app consumes them via a custom `useQuery<T>` hook layer (`web/src/api/`). Legacy Streamlit app (`app.py`, `src/pages/`) still runs but is frozen — all new work is React.

## Non-negotiable UI rules (full list in DESIGN.md)

- Read `DESIGN.md` before any UI. No hardcoded hex — semantic tokens / Tailwind aliases only.
- Fonts: **Space Grotesk** (UI) + **JetBrains Mono** (numerals, `tabular-nums`).
- Accent: **teal** (`#34E1D4` dark / `#0C998D` light). **Red = critical/destructive only.**
- Light/dark via `data-theme`; WCAG AA enforced (contrast lint); full `prefers-reduced-motion` support.
- Account changes route through the **Directive approval queue with a diff** — never instant writes. Agent proposes, human confirms, action is audit-logged.
- Run the **pre-merge checklist (DESIGN.md §8)** before shipping UI.

## Front end

The React front end lives in **`web/`** — a Vite + React 19 + TypeScript + Tailwind app. All 13 surfaces are built: Scorecard, Spend, Media, Creative, Audience, Brand Awareness, Product, Funnel, Retention, Operations (interactive approval queue), Simulator (interactive budget sliders), Modeling, and Settings. The shell layer provides the app chrome (atmosphere, rail, context bar, filter bar, agent console). See `AGENTS.md` for the full file tree and running instructions.

## Running locally

```bash
# Terminal 1 — BFF on port 8000
uvicorn src.api:app --reload --port 8000

# Terminal 2 — React on port 5173
cd web && npm install && npm run dev
```
