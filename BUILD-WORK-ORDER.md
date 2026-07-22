# Apex — Build Work Order (Claude Code)

**Purpose:** the complete, sequenced set of changes to take the current `web/` vertical slice up to the full guide spec, ready to hand to Claude Code. **Date:** June 24, 2026.

> **Read first (every task):** `DESIGN.md`, `AGENTS.md`, `design/Apex-Design-Memo-Combined.md` (system), `design/Apex-Feature-Components-Screen-Spec.md` (screens + BFF build-order map), `design/Apex-Unified-Microservice-Architecture.md` (15 services), `design/reference/RV-Reference-Capabilities.md` (velocity-sites + fitb-acquisition-engine capabilities). Build React + Tailwind over the BFF; mock until services are live. No hardcoded hex; Space Grotesk + JetBrains Mono; teal accent; red = critical only; every account change routes through the Directive approval queue.

## Current state (verified — see `web/QA-REPORT.md`)

✅ Next.js 14 + TS + Tailwind scaffold in `web/`; token system (both themes), theme toggle, AppShell, AgentConsole. ✅ Component library: KPICard, Gauge, Sparkline, Alert/AlertWire, MissionTracker, DiffView, Button, StatusPill, Skeleton/Empty/Error, CardContainer. ✅ Full screens: Scorecard, Approvals, Simulator. ✅ Typed fixture BFF (`lib/bff.ts`) + `useQuery` hook. ✅ Builds, typechecks, boots, all 8 routes 200. ⚠️ Stubs only: Spend, Channels, Funnel, Product, Retention. ❌ Not built: Acquisition Engine, Launch Pipeline, AEO, channel detail, Settings, real Retention, NL→SQL Lens, MSW, ESLint, tests.

---

## How to run this work order

Write yourself an end-to-end `/goal` covering the whole order, not just the next step. Split into the workstreams below; spawn parallel agents where independent (data/mocks, components, screens can parallelize once the foundation tasks land). Each agent gets its own `/goal` with deliverable + verification + completion standard. Track progress, synthesize, resolve conflicts, run real-time validation after each task (typecheck + build + boot + browser walk in both themes), and finish with the review skill + the QA gate in the last section. Don't stop on partial progress unless blocked by missing credentials, destructive ambiguity, or conflicting requirements.

**Dependency order:** Foundation (1–3) → then Screens (4–10) and Data (each screen depends on its mock from task 2) in parallel → Polish/UX-fixes (11) → QA gate (12).

---

## Workstream 1 — Foundation & tooling

### 1.1 Configure ESLint + Prettier (P0 tooling)
- `next lint` currently drops to an interactive prompt (no config). Add `.eslintrc.json` with `next/core-web-vitals`, plus `eslint-plugin-jsx-a11y` (recommended) and Prettier. Add `"lint": "next lint"` (already present) and `"format"`. **Verify:** `npm run lint` exits 0 non-interactively.

### 1.2 Add a contrast-lint script (DESIGN.md contract)
- Script that parses the semantic token pairs from `src/styles/tokens.css` and asserts WCAG AA (≥4.5:1 body, ≥3:1 large/UI) for every `--color-text-*` on its background and `accent-contrast` on `accent`, **per theme** (remember light accent is the darkened teal). Wire into CI/`npm run check`. **Verify:** script passes for both themes; fails if a token is edited below AA.

### 1.3 State + data libraries (align to spec)
- Add **TanStack Query** (replace the hand-rolled `useQuery` seam) and **Zustand** for UI state. Keep the `lib/bff.ts` contract; swap `useQuery` internals to TanStack. **Verify:** Scorecard/Approvals/Simulator still load through the new query layer; build clean.

---

## Workstream 2 — MSW + full BFF contracts

### 2.1 Wire MSW
- Add `msw`, create `src/mocks/handlers.ts` + browser/server worker. Move the `lib/bff.ts` fixtures behind real HTTP handlers matching the **BFF endpoint readiness map** in the screen spec. **Verify:** network tab shows mocked requests; app runs identically.

### 2.2 Implement every BFF contract used by the screens (typed)
Mock these to realistic fixtures (shapes per screen spec), each with **loading/empty/error** paths exercised:
- Existing-router contracts: `/api/scorecard/*`, `/api/channels/sem/*`, `/api/ops/*`, `/api/directives/*`, `/api/product/*`, `/api/alerts/*`.
- New-service contracts: `/api/spend/*`, `/api/channels/{brand,social,seo,aeo}/*`, `/api/funnel/*`, `/api/retention/*`, `POST /api/simulate`, **`GET /api/allocate?objective&budget&period`** (Next-Best-Dollar), **Lens `POST /ask`** (NL→SQL), **Launch/Audit/Experiments** contracts.
**Verify:** typed client + handler for each; a fixture for empty + error per endpoint.

---

## Workstream 3 — Complete the design-system component library

Build the remaining feature components from the screen-spec inventory as typed, themed, reduced-motion-safe, Storybook-storied (optional) components. Group:
- **Charts/data:** `ResponseCurveChart`, `FunnelSankey`, `FunnelWaterfall`, `SurvivalCurveChart`, `DMASpendMap`/`GeoMap`, `GeoMoneyFlowMap`, `LLMVisibilityScore`, `CompetitiveAEOBenchmark`, `DataTable` (sortable, conditional badges). Use Recharts/visx; gauge/curves may be SVG.
- **Controls:** `ChannelMixSliders`, `InputSlider` (have a basic one — promote), `ABTestSetup`, `SegmentFilterPanel`, `ConnectorCard`, `BenchmarkEditor`, `ThemeToggle` (have — extract).
- **Composites:** `TopMovesTable`, `WasteGapStrip`, `MoneyLeftHeadline`, `RolloutSimulator`, `LensDataAnswer`, `DeliveryBoard`, `ProofingPanel`+`CreativeViewer`, `SiteFactoryPanel`+`LivePreview`, `ComplianceScanResults`, `QAScanResults`, `ExperimentLive`, `LaunchRegistry`, `ProductPipeline`(kanban), `TransformationRoadmap`(timeline), `LaunchCalendar`, `TeamCapacity`, `CompetitiveIntelFeed`, `AbandonmentRecoveryTracker`, `LifeEventCampaigns`, `OperatingStreak`.
**Verify:** each renders in both themes, keyboard-reachable, no hardcoded hex, reduced-motion safe.

---

## Workstream 4–10 — Build the screens to full depth

Each screen: build per its section in `design/Apex-Feature-Components-Screen-Spec.md`; wire to its MSW contract; implement all states (loading/empty/error/populated/stale; agentic proposed→queued→approved→executed where relevant).

- **4 · Spend Allocation** — BudgetOverviewKPIs, PacingBurnChart, **DMASpendMap**, **ChannelMixSliders** (commit → `channel_mix_adjustment` Directive).
- **5 · Channels** — tabs/sub-routes: Brand (impressions, reach/freq, **LifeEventCampaigns**), Performance (SEM + **GoogleVsBing** + Social), SEO (rankings, traffic), **AEO** (**LLMVisibilityScore**, mention rate, **CompetitiveAEOBenchmark**).
- **6 · Acquisition Funnel** — **FunnelSankey** (red = drop-off), **DropoffAnalysis** ($/stage), **AbandonmentRecoveryTracker**.
- **7 · Product & Ops** — **ProductPipeline**, **TransformationRoadmap**, TestingVelocity, **LaunchCalendar**, **TeamCapacity**, **ApprovalQueue** surface, SystemHealth, **CompetitiveIntelFeed**.
- **8 · Retention** — **SegmentFilterPanel**, **SurvivalCurveChart** with **draggable observation-date**, RetentionKPIs.
- **9 · Settings** — ApplicationModeToggle (BD/Client), AppearancePanel (theme), IntegrationsGrid (**ConnectorCard**), **BenchmarkEditor** (5 tabs).
- **10 · NEW — Acquisition Engine (`/acquisition-engine`)** — the Next-Best-Dollar flow: `EngineInputs` (Profit/Volume + Budget), `TodayGap`, **`ResponseCurveChart`** (dot below curve = waste, optimal ring), **`WasteGapStrip`** + **`MoneyLeftHeadline`** (count-up), **`TopMovesTable`** (role-tagged, 0.4×–2.0×), **`RolloutSimulator`** + **`GeoMoneyFlowMap`** (30-day, ≤20%/wk), **`AgentDefense`**; **Commit → `budget_reallocation` Directive**. Wire to `GET /api/allocate`.
- **10b · NEW — Launch Pipeline / Site Factory (`/launch`)** — operator-paced stage rail with human gates: `LensPromptPlan` → `DeliveryBoard` (all-Done gate) → `ProofingPanel`/`CreativeViewer` (revise-to-v2, approve gate) → `SiteFactoryPanel`/`LivePreview` → **`ComplianceScanResults`** (evidence) → **`QAScanResults`** → `ApproveGate` → **`ABTestSetup`**/`ExperimentLive` → `LaunchRegistry` (feeds back to Lens). Enforce **first-party guardrail** (DESIGN.md §7). Add both to the AppShell nav.

---

## Workstream 11 — Apply the UX-audit P1 fixes (`web/UX-AUDIT.md`)

1. **Reject feedback + undo** (Approvals) — terminal "Rejected" state, optional reason, toast w/ Undo, `aria-live`.
2. **Nav labels** — expandable rail with icon+label (or focus flyout), not `title`-only.
3. **Confirm high-impact approve** — two-stage/confirm popover for `impact:"high"`; one-click stays for low.
4. **Run progress** (Simulator) — scan-line "computing" + disable inputs + headline count-up on result.
5. **Actionable alerts** — per-alert Acknowledge + Investigate (deep-link / pre-fill console).
6. **Error/empty everywhere** — app-level `error.tsx`+`loading.tsx`; every data region renders one of {loading, empty, error, populated}.
(Then P2s #7–12 as capacity allows.)

---

## Workstream 12 — QA gate (run before "done")

Run and keep green:
1. `npx tsc --noEmit` → 0 errors.
2. `npm run lint` → 0 errors (non-interactive).
3. `npm run build` → all routes compile.
4. **Contrast lint** (1.2) → AA both themes.
5. Boot + **browser walk every route** in **dark and light** at desktop/tablet/phone widths; confirm no overlap/overflow/horizontal scroll.
6. **Keyboard-only** completion of the core path: filter → open a directive → approve (with confirm) → see executed; Tab/Enter/Space/Esc all work; focus ring visible.
7. **Reduced-motion**: celebrations/sweeps/count-ups disabled.
8. **axe** (or jsx-a11y) clean on each route; icon buttons labeled, inputs labeled, `aria-live` on alert wire + async results.
9. Governance: no live write without a Directive + approval; first-party guardrail holds on Launch.
10. Update `web/QA-REPORT.md` with results; write a final summary (changed / validated / remaining risks).

**Definition of done:** all 14 surfaces built to spec and wired to mocked BFF contracts, the component library complete, the UX-audit P1s fixed, and the full QA gate green in both themes with keyboard-only + reduced-motion paths verified.
