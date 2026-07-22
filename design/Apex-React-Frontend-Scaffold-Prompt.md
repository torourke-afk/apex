# Apex Front-End Build — Master Scaffold Prompt (React + Tailwind)

> Copy-paste this to Claude Code / Claude design in the Apex repo.
> **Stack decision:** the Apex front end is a **React (Next.js, App Router) + TypeScript + Tailwind CSS** application — a *thin client* over the unified microservice **Gateway/BFF** (GraphQL/REST). SQL stays in the data layer; the BFF returns JSON; React renders the **Signal Deck** aesthetic. This is the **architecture-first** path: the React app talks to BFF contracts, not to Streamlit or to data loaders.
> **Design source of truth:** `Apex-Design-Memo-Combined.md` ("Signal Deck") + `DESIGN.md` (authored in Task 3). **Type: Satoshi (UI) + JetBrains Mono (numerals, tabular-nums).** Theming: token-driven, light/dark via `data-theme` class, WCAG-AA enforced, violet/cyan ground, RVGT red = critical only. Mission-Control feedback layer (celebration on real wins only, progressive-reward streaks, mission tracker, agent console).

---

## Stack & conventions (apply to all tasks)

- **Framework:** Next.js 14+ (App Router) · TypeScript · React 18.
- **Styling:** **Tailwind CSS** with a **token-driven config** — Tailwind theme values reference CSS custom properties (the semantic tokens), so light/dark and future themes swap via `data-theme` with zero component changes. **No hardcoded hex in components — Tailwind/semantic classes only.**
- **Server state:** TanStack Query against the BFF. **UI state:** Zustand. **No data fetching in components** — go through a typed BFF client/hooks layer.
- **Charts:** Recharts (or visx for the gauge/curves). **Drag/DnD:** dnd-kit. **Icons:** lucide-react. **Motion:** Framer Motion (gated by `prefers-reduced-motion`).
- **Fonts:** Satoshi via Fontshare (`@font-face` or `next/font` local), JetBrains Mono via `next/font/google`. System fallback if blocked.
- **Mocking:** until BFF endpoints exist, mock with **MSW** against the documented BFF contracts (OpenAPI) so the UI is buildable in parallel with services.
- **Boundary rule:** components consume BFF JSON only; they never know SQL exists. Numbers come pre-computed from the metric layer.

For **every** task: write yourself a new end-to-end `/goal` that completes the whole plan — architecture, implementation, tests, review, and final result meeting the standard — not just the next step. Split the goal into independent pieces, spawn as many parallel agents as needed to do it better and faster, and give each agent its own dedicated `/goal` that includes its expected deliverable, its verification method, and its completion standard. Dispatch them concurrently, track progress in the right place, synthesize results as they return, resolve conflicts, continue implementation, run real-time validation after important steps, and finish with a review skill, submission/commit when appropriate, and a final summary. Validation must cover the real end-to-end path — browser/computer use, clicks, keyboard actions, and any necessary operation. Do not stop after partial progress unless blocked by missing credentials, destructive ambiguity, or conflicting requirements.

Execute the three tasks **in order: 3 → 1 → 2.**

---

## 3. Give it a DESIGN.md first  *(do this first — everything reads it)*

**Task:** Author `DESIGN.md` at the repo root — a plain-text design system (the Google Stitch concept: **AGENTS.md says how to build it, DESIGN.md says how it should look**). Every UI build reads DESIGN.md before writing a component, so style stops drifting. Codify the Signal Deck spec as enforceable rules expressed for **React + Tailwind**:

- **Color:** three-tier tokens (primitive → semantic → component) as **CSS custom properties** under `:root`, `[data-theme="dark"]` (default), `[data-theme="light"]`; document every semantic token + hex in both themes and the **WCAG-AA contrast contract** (≥4.5:1 body, ≥3:1 large/UI) with the exact passing pairings. Show the **Tailwind mapping** (e.g., `colors: { canvas: 'var(--color-bg-canvas)', accent: 'var(--color-accent)', critical: 'var(--color-critical)' }`). RVGT red = critical/destructive only.
- **Type:** Satoshi + JetBrains Mono; weights; rem scale (xs .75 → 3xl 2.75); `tabular-nums` mandatory on all numerals (a `.num` / `font-mono tabular-nums` utility); uppercase HUD label rule.
- **Spacing / radius / shadow / motion** tokens, mapped to Tailwind theme extensions and Framer Motion presets (`--ease`, `--t-fast/--t/--t-slow`).
- **Component rules:** composition rules for KPICard, Alert/AlertWire, Button, Console (agent/directive input), Chip, MissionTracker, Gauge, DataTable, FilterBar, CardContainer, SectionHeader; the "AI/agent surface = violet" rule; the "celebration only on rare real wins, ≤600ms, never blocking, max one on screen, reduced-motion gated" rule.
- **Do/Don't** examples and a pre-merge checklist any agent runs before shipping UI.

Set up the Next.js + Tailwind project so the Tailwind config + a `globals.css` token sheet are the literal source DESIGN.md documents (single source of truth). Add/update `AGENTS.md`: *read DESIGN.md before any UI work; no hardcoded hex; numerals = JetBrains Mono tabular-nums.* End with a review skill that verifies DESIGN.md is complete, internally consistent, and contrast-valid (run a token-pair contrast check).

*(Apply the end-to-end `/goal` + parallel-agent + validation protocol above.)*

---

## 1. Design System — build the React component library  *(start in a worktree)*

**Task:** Build **one unified Design System** as a reusable, maintainable **React + Tailwind component library** that conforms to `DESIGN.md`, and wire the Apex pages onto it. Because the production UI is being (re)built in React over the BFF, this means: stand up the component library as the canonical UI source, port the existing Apex surfaces (the 7 domains: Executive Scorecard, Spend, Channels [Brand/Performance/SEO/AEO], Funnel, Product & Ops, Simulator, Retention + Settings) to library components, and **route all UI through the library with no bypassing** (no raw hex, no off-library one-off markup, no inline styles outside the library). Build the Signal Deck primitives as typed React components:

- `KPICard` (value/delta/sparkline/target-ring), `Alert` + `AlertWire`, `Button`, `Console` (agent/directive input with caret), `Chip`, `MissionTracker`, `Gauge` (radial), `DataTable`, `FilterBar`, `CardContainer`, `SectionHeader`, plus theme provider + `useTheme` toggle.
- Each component: typed props, Tailwind/semantic classes only, light/dark correct, `prefers-reduced-motion` honored, Storybook story, and a unit/interaction test.
- Data comes from the typed BFF hooks (mocked via MSW against the OpenAPI contracts until services land). Keep the SQL/metric layer untouched — components render JSON.

**This is a refactor/rebuild of the presentation tier, so start in a git worktree.** Add a review skill at the end that fails on any bypass (hardcoded color, off-library UI, untokenized spacing) and confirms every page renders through the library in both themes.

*(Apply the end-to-end `/goal` + parallel-agent + validation protocol. Validation must include `next dev`, visiting each ported surface in the browser, and confirming light + dark via the `data-theme` toggle.)*

---

## 2. Accessibility & responsive pass

**Task:** Ensure regular, low-vision, keyboard-only, and different-device users can all reliably complete the **core actions** (view scorecard, filter, read a chart/table, run a simulation, submit and approve a directive). Run the Next.js app locally from the current commit; walk the core paths at **desktop / tablet / phone** breakpoints (Tailwind `sm/md/lg/xl`); fix responsive issues (overlap / overflow / truncation / horizontal scroll), contrast, font scaling (rem + zoom to 200%), keyboard (Tab / Enter / Space / Esc; focus trapping in dialogs/console), focus states (signal-cyan ring, AA-visible both themes), and a11y semantics of images / icon buttons / forms / status — `alt`, `aria-label` on icon buttons, `<label>` on inputs, `role="status"` / `aria-live` for the alert wire and async sim/directive results, accessible names for the gauge/charts. Verify reduced-motion disables celebrations/sweeps/count-ups. Record issues found, fixes applied, and remaining risks. Add a review skill at the end (axe + keyboard-only walkthrough + viewport screenshots).

*(Apply the end-to-end `/goal` + parallel-agent + validation protocol. Validation must cover the real end-to-end path at all three viewports, including keyboard-only completion of submit→approve directive and screen-reader/axe semantics checks.)*

---

### Standing rules for all three tasks
- Read `DESIGN.md` before writing any UI.
- React + Tailwind; **no hardcoded colors** — semantic tokens / Tailwind theme only; RVGT red = critical/destructive only.
- All numerals use JetBrains Mono with `tabular-nums`.
- Components consume BFF JSON via typed hooks — **never** query SQL or embed data logic.
- Every interactive element keyboard-reachable with a visible focus state; everything works with `prefers-reduced-motion`.
- Work on a worktree/branch with clear commits; finish each task with its review skill, then a final summary of what changed, what was validated (and how), and remaining risks.
