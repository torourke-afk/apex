# Apex web/ — QA Report

**Date:** June 24, 2026 · **Build:** FULL build per `BUILD-WORK-ORDER.md` (11 routes, 14 surfaces) · **Verified by:** typecheck, lint, contrast lint, production build, runtime route probes, content markers, design-system + governance invariants.

## Final QA gate

| Check | Result | Detail |
|---|---|---|
| TypeScript (`tsc --noEmit`) | ✅ PASS | 0 errors |
| ESLint (`next lint`, incl. jsx-a11y) | ✅ PASS | 0 warnings / 0 errors (now configured) |
| Contrast lint (WCAG AA, both themes) | ✅ PASS | all token pairings ≥ AA; caught + fixed 2 light-mode failures during the build |
| Production build (`next build`) | ✅ PASS | all 11 routes compile (static) |
| Runtime route probes | ✅ PASS | all 11 routes HTTP 200 |
| Content markers | ✅ PASS | every screen renders its signature content |
| No hardcoded hex (app/components) | ✅ PASS | 0 (color only via tokens) |
| `aria-live` regions | ✅ PASS | approvals decisions, alert wire, simulator run |
| `prefers-reduced-motion` | ✅ PASS | global disable rule |
| `error.tsx` + `loading.tsx` | ✅ PASS | app-level boundaries (no blank routes) |
| Governance: no instant writes | ✅ PASS | 5 screens route commit/approve through Directive + approval queue |
| First-party guardrail (Launch) | ✅ PASS | Member FDIC / first-party language enforced |

## Surfaces built (14)

**Full screens:** Executive Scorecard · Spend Allocation · Channels (Performance/Social/SEO/AEO tabs) · Acquisition Funnel · Product & Ops · Retention (draggable observation date) · Settings · Approvals (diff + high-impact confirm + reject/undo + aria-live) · Simulator (inputs → run progress → results → waterfall → commit) · **Acquisition Engine** (Next-Best-Dollar: response curves, waste-gap headline, top moves, 30-day rollout, geo money-flow, commit→directive) · **Launch Pipeline / Site Factory** (operator-paced stage rail, delivery board, compliance + QA scans with evidence, A/B with z-test confidence, launch + first-party guardrail).

## Foundation

Next.js 14 + TS + Tailwind · token system (both themes, AA-enforced) · TanStack Query + Zustand · ESLint + jsx-a11y + Prettier · contrast-lint script · `npm run check` (tsc + lint + contrast) gate · full typed BFF contract layer (`lib/bff.ts` + `lib/bff-extended.ts`) for all 14 surfaces, ready to swap fixtures for live `fetch()`.

## UX-audit P1 fixes applied

Reject feedback + undo · nav labels (expandable rail) · high-impact approve confirmation · simulator run progress + aria-live · app-level error/empty/loading everywhere.

## Known limitations (not defects)

- **Data is fixture-backed**, not wired to a live BFF/MSW service worker — the typed contract layer is the documented swap-in seam.
- **Charts are inline SVG** (sparkline, bar, line, response curve, survival, funnel) rather than Recharts/visx — lighter and dependency-free; can be upgraded later.
- **Browser screenshots not captured here** — the dev server runs in the sandbox and Claude-in-Chrome runs on the user's machine, so visual verification was done via served-HTML content markers + invariant greps. To eyeball: `cd web && npm run dev`.
- Launch pipeline proofing/factory/preview stages are represented as workspace descriptions (the real static-HTML build + revise-to-v2 loop are server-side capabilities per the reference repos, out of scope for the mock front end).

## Live API wiring (added)

- **CORS** added to `src/api/__init__.py` (`APEX_CORS_ORIGINS`, defaults to localhost:3000) so the browser can call the routers.
- **Adapter layer** (`src/lib/api.ts`) maps the real FastAPI shapes → the UI view-models: scorecard KPIs (`{name,value,target,delta_pct,sparkline_data,…}` → `KPICard` model, with CPL/CPIHH/CAC auto-flagged lower-is-better), alerts, and directives (status → proposed/approved/executed/rejected).
- **Live/mock switch** via `NEXT_PUBLIC_API_BASE` (`web/.env.example`). Unset = typed fixtures; set = live routers, with a try/catch fallback to mock so the UI never hard-breaks.
- **Adapter validated** deterministically against a real-shaped scorecard payload (Node harness): KPI formatting, lower-is-better inversion (CPIHH 312 ≤ 320 → target met), delta direction, and goal % all correct. ✅
- **Live HTTP round-trip not captured in-sandbox:** booting uvicorn against the 350 MB DuckDB exceeds the sandbox's 45s/call limit and background processes don't persist across isolated bash calls, so a live curl against `:8000` couldn't complete here. The integration risk (shape mapping) is covered by the adapter validation above; to verify the full round-trip locally: `uvicorn src.api:app --port 8000` then `NEXT_PUBLIC_API_BASE=http://localhost:8000 npm run dev`.

## Charts upgraded to Recharts

`BarChart`, `LineChart`, and `Sparkline` rebuilt on **Recharts** (responsive, tooltips, token-driven colors). `ResponseCurveChart`, the funnel bars, and the survival curve remain custom SVG (bespoke shapes Recharts doesn't model well). Bundle grew to ~190–217 kB/route (expected for Recharts); build clean.

## Design-system refresh (new full Signal Deck, June 24)

Applied the updated design system delivered in `Apex feature components & screen specs-5200f0c8.zip`:
- **DESIGN.md** replaced with the new full "Signal Deck" system (12 surfaces, atmosphere spec, expanded component specs); new mockup + screenshots saved to `design/mockups/`.
- **Tokens re-synced verbatim** from the delivered Design Component into `web/src/styles/tokens.css` and `src/config/brand.py` — both themes, including the AAA-tuned light palette (`--bg #DDE2EA`, `--cyan #0B897E`, `--text #0A0E16`, …) and new atmosphere tokens (`--dot`, `--dot-star`, `--header-bg`, `--aura1/2/3`). Contrast lint re-run: **PASS both themes** (muted now 4.31:1, accent 11.85:1 — stronger than before).
- **Atmosphere layer added** (`components/Atmosphere.tsx` + globals.css): three drifting aura blobs + a **stable 450-dot starfield** (generated once via useMemo so re-renders don't restart it) with **cursor-repel** (single mousemove→rAF handler, R=130/MAX=40), `twinkle`, float drift, and a vignette. Mounted behind a `z-1` content column in AppShell. **Fully gated by `prefers-reduced-motion`.**
- Verified: new tokens + atmosphere keyframes compiled into the CSS bundle; rendered HTML contains the dot field, auras, and vignette; all routes still 200.

## Verdict

**Green.** The full surface set builds, typechecks, lints, passes the AA contrast gate (both themes), serves every route, and holds the design-system + governance invariants. The new full Signal Deck design system (refreshed tokens + atmosphere) is applied and verified. Live API wiring is in place behind an adapter layer (validated against real shapes) and switched by env; charts are on Recharts. The only thing not demonstrated in-sandbox is a live uvicorn round-trip + pixel screenshots of the running app, due to sandbox process/time limits — runnable locally with `npm run dev`.
