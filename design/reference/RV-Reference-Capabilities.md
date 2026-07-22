# RV Reference Capabilities — velocity-sites & fitb-acquisition-engine-demo

**Captured June 24, 2026** from the two RedVentures repos (via README + ARCHITECTURE.md + AGENTS.md). These are existing RV demo builds whose capabilities must be reflected in the new Apex build guide. This doc is the source; the architecture and screen specs reference it.

> Both are operator-paced, demo-grade, near-zero-dependency builds that run locally with deterministic fallbacks and (optionally) the Claude CLI for agentic paths. Apex should absorb their *capabilities and patterns*, rebuilt on the Apex microservice + React/Tailwind foundation.

---

## A. velocity-sites — "Velocity Overdrive" (autonomous website-launch platform)

**What it is:** you chat with **Velocity Lens**, name a customer persona, and it turns the prompt into recommendations + tickets for a first-party **Fifth Third Momentum® Checking** offer page ($350 new-customer offer on 53.com), then drives the entire launch pipeline through interactive human gates — really building the site as static HTML, running real compliance/QA scans and A/B experiments, and feeding live performance back into Lens to plan the next iteration.

### The pipeline (12 stages, operator-paced with human gates)
```
Velocity Lens → Recommendations → Tickets → JIRA → Creative Proofing (Workfront)
→ Site Factory → Live Preview → Compliance → QA → Approve → A/B Test Setup → Launch → (feedback loop)
```
- **Does not auto-play.** Each stage runs/awaits, then the operator advances. Interactive gates: move JIRA tickets to Done (unlocks proofing), review/approve Workfront proofs (with a *real* revise-to-v2 feedback loop), the **Approve** human launch gate, and A/B setup (pick metric, toggle variants, set traffic split).
- **First-party, not affiliate** — 53.com pages, "Open an Account" CTAs, Member FDIC / Equal Housing Lender, real offer T&Cs.
- Post-launch performance (funded accounts, account-open CTR, CPA, winning variant) feeds back into Lens, which recommends the next persona — closing the loop.

### Backend: a 10-service Node mesh (gateway + domain services)
| Service | Port | Owns |
|---|---|---|
| gateway | 6100 | reverse proxy, health aggregation, service manifest, **event bus (SSE fan-out, exact replay)** |
| lens | 6110 | warehouse + **agentic NL→SQL** (Velocity Lens) |
| delivery | 6120 | issues / JIRA workflow + real ticket-work execution |
| proofing | 6130 | creative proofs, threaded comments, revisions (Workfront) |
| factory | 6140 | full site authoring + **real static-HTML builds** (AEM) |
| dam | 6150 | asset library |
| audit | 6160 | **compliance + QA scans** of built sites, reviewer memos |
| experiments | 6170 | **live A/B experiments** — ticking traffic, real statistics |
| analytics | 6180 | launch registry + performance time-series |
| agents | 6190 | agent runs on the local claude CLI |

Each service owns its own SQLite DB; services talk only over HTTP + the persisted event bus. Pattern: **every client bridge is defensive — a failed call returns null and the engine applies a deterministic in-engine fallback**, so a down mesh degrades gracefully.

### Computed subsystems (real, local, no external APIs) — the capabilities to absorb
- **Intelligence (`intel.js`)** — blends a seed keyword corpus + persona + funnel model into **opportunity score, monthly demand, avg CPC, target CPA, 90-day projected funded accounts** per persona; ranks the persona portfolio to recommend the next iteration.
- **Site production (`buildSpec.js` + `renderHtml.js`)** — assembles a multi-page site from recommendations (route + content blocks + schema.org JSON-LD per page), then renders to **real static HTML on disk** (doctype, meta/OG, JSON-LD, disclosures, a working JS calculator, a real `/apply` page, sitemap.xml, robots.txt).
- **Compliance (`compliance.js`)** — scans the built spec for **Member FDIC, Equal Housing Lender, Reg DD rate/fee terms, $350 offer T&Cs, 1099-INT note, UDAAP "free"/"no fee" claims, comparative-claim substantiation, axe-like a11y** → honest pass/warn/fail **with evidence** (a missing disclosure genuinely fails).
- **QA (`qa.js`)** — Lighthouse-ish score from the real block inventory (Core Web Vitals estimates), offer-accuracy reconcile vs source-of-record, CTA + link crawl, schema validation, responsive heuristics.
- **Experimentation (`experiment.js`)** — seeded marketing-funnel simulation (search → clicks → visits → apply → funded) + **two-proportion A/B z-test → CTR, CPA, ROI, winning variant, lift, honest statistical confidence** (underpowered scenarios read <95%; O'Brien-Fleming sequential testing).
- **Delivery (`delivery.js`)** — derives the JIRA backlog (points from effort × keyword difficulty, types, labels, acceptance criteria, epic/sprint) and Workfront proofs (legal markup from required disclosures).
- **Proof revision (`revise.js`)** — deterministic creative revision (parses feedback, clamps lengths, re-applies Member FDIC + offer T&Cs, scrubs UDAAP claims).
- **Agentic compliance/QA reviewers** — autonomous agents verifying one assertion at a time, only advancing when green, filing real reviewer memos.
- **Lens warehouse** — in-memory `node:sqlite` warehouse over the seed corpus + live launches, with a **semantic ontology, SELECT-only/allowlist guards, SQL gen → execute → repair (≤2 retries) → table + SVG chart + NL summary**.

### Validation discipline (a pattern Apex should adopt)
Two headless harnesses kept green: `validate-pipeline.mjs` (551 checks — SPA + engine realism + a **hard design-fidelity gate**: exact kit palette/type/layout on built pages) and `validate-platform.mjs --strict` (130 checks — boots the whole mesh with the CLI disabled, exercises every service contract).

### Stack
React + Vite + Tailwind v4; **node built-ins only** for the backend (`node:http`, `node:sqlite`, `node:crypto`, `node:child_process`…); optional local `claude` CLI for agentic paths with deterministic fallbacks; **no runtime network calls**.

---

## B. fitb-acquisition-engine-demo — "Acquisition Engine" (autonomous paid-media reallocation)

**What it is:** a standalone, executive-grade demo of an **autonomous paid-media reallocation agent** wrapping a **"Next Best Dollar" diminishing-returns allocator** (fitted response curves per campaign × geo). It dramatizes how much money is left on the table by misallocated ad spend, then shows the agent closing that gap automatically. Story runs on an energy retailer's Texas paid-media portfolio (synthetic data shaped to mirror real RV energy CSVs so production data swaps in with no UI change). **The wow is the gap, not the AI.**

### The allocator (the core capability)
- **Next Best Dollar marginal allocator** over fitted **response curves**: `accounts = k · ln(1 + spend/S_REF)` per combo (10 campaigns × 6 TX metros = 60 combos, 52 weeks).
- **Bounded reallocation**: each combo clamped to **[0.4× – 2.0×] current** — exactly what a **30-day, ≤20%/week rollout** can physically reach (0.8⁴≈0.41, 1.2⁴≈2.07). Guarantees the result beats current and is reachable.
- **Objectives:** Profit (contribution margin = accounts×value − spend) or Volume (ALL_ACCOUNTS). Budget is an input.
- **Role segments** in campaign names — Scale / Defend / Maintain / Experiment — drive the defend/scale map + frontier coloring.
- **Curve refinement over the rollout**: each move has day-0 and day-30 curve samples; the drawn curve lerps as the agent "learns" the true response.
- Headline (seed 42, CM, $1.43M/wk): ~5,600 accounts @ ~$247 CAC, ~−$32K/wk margin **→** 7,500 accounts @ ~$190 CAC, ~+$410K/wk = **+33% accounts, ~$23M/yr left on the table, same budget.**

### The experience (5 screens)
1. **Intro** — cursor-reactive hero landing → CTA.
2. **Today** — the gap laid bare: today's CAC / margin / accounts / spend, a **campaign × metro scatter** (dots only, no curves), a scrollable table of all 60 combos; set **Objective (Profit/Volume) + Budget**.
3. **Building** — animated "building your optimal plan."
4. **Optimal Plan** — **per-campaign response curves with each dot sitting below its curve** (dashed waste-gap connector) + its own optimal-spend ring; KPI gap strip; top-moves table; the headline **$ left on the table / yr** (counts up).
5. **Simulate** — animates the 30-day rollout: dots travel onto their curves, curves drift day-0→day-30, **money flows across a Texas map** (donor → recipient metros), KPIs tick up; **chat with the agent throughout — it defends every move with the numbers.**

### Stack
**Frontend** — Vite + React + TypeScript + **Tailwind + Framer Motion + visx** (near-black "Profound-style" UI; hand-built SVG TX map). **Backend** — **FastAPI** wrapping the allocator pipeline + LLM chat skills: `GET /api/scenario?objective&budget&period`, streamed `POST /api/chat`. **Data** — synthetic energy CSVs (`generate_energy_data.py`), structured so real RV energy data drops in cleanly. Allocator = DePei's `paid_media_budget_recommender.py` with a `--weekly-csv` branch.

---

## C. What Apex must absorb (mapping)

| Capability (from repos) | Apex home | Status in current guide |
|---|---|---|
| **Next-Best-Dollar marginal allocator + fitted response curves** | Optimization Service + Simulator/Spend screens | **NEW — add** (the math behind reallocation) |
| **Bounded reallocation (0.4×–2.0×, ≤20%/week, 30-day reachable)** | Optimization Service; directive guardrails | **NEW — add** |
| **Waste-gap visualization** (dots below curves, $ left on the table) | Spend / Simulator screens | **NEW — add** |
| **Live rollout simulation** (dots→curves, curves drift, geo money-flow map, KPIs tick) | Simulator (Mission Debrief) | Partially (Simulator exists; add curves + geo-flow + rollout) |
| **Agent defends each move with the numbers** | Agent console / directive rationale | Partially (rationale exists; add per-move defense) |
| **Autonomous website-launch pipeline** (Lens→…→Launch w/ human gates) | NEW **Launch pipeline** surface + services | **NEW — add as a domain** |
| **Velocity Lens NL→SQL** (ontology → SQL → repair → table+chart+summary) | Lens / Analysis agent + warehouse | Partially (chat exists; add NL→SQL + ontology + guards) |
| **Recommendations engine** (opportunity, demand, CPC, target CPA, projected funded) | Channels/Spend + Optimization | Partially |
| **Real static-HTML Site Factory** (multi-page spec, JSON-LD, sitemap, calculator) | NEW **Site Factory** service | **NEW — add** |
| **Agentic compliance scans** (FDIC/EHL/Reg DD/T&Cs/UDAAP/a11y, evidence) | NEW **Compliance** capability in Audit/Policy | **NEW — add** |
| **Agentic QA scans** (Lighthouse-ish, offer reconcile, link/schema crawl) | NEW **QA** capability in Audit | **NEW — add** |
| **A/B experiment engine** (funnel sim + two-proportion z-test, power, O'Brien-Fleming) | NEW **Experiments** service | **NEW — add** |
| **Creative proofing + real revise-to-v2 loop** | Channels/Creative + proofing | Partially (creative phase exists; add proof loop) |
| **JIRA-like delivery / ticket work** | Product & Ops | Partially (approvals exist; add delivery/tickets) |
| **Launch registry + performance feedback loop** | Analytics + Scorecard | **NEW — add the closed loop** |
| **Event bus (SSE fan-out, exact replay) + defensive client fallbacks** | Gateway/BFF + all services | Reinforce in architecture |
| **Headless validation harnesses + design-fidelity gate** | Build/CI discipline | **NEW — adopt the pattern** |
| **first-party-only guardrail** (53.com, FDIC/EHL, no affiliate/competitor) | DESIGN.md / content rules | **NEW — add to governance** |
| **Real-data-swap-in design** (synthetic shaped to match prod CSVs) | Data layer / connectors | Reinforce |

These map cleanly onto the four RV 2.0 pillars: the **Acquisition Engine = Acquisition pillar** (the agentic paid-media engine already scoped), and **Velocity Overdrive = Conversion pillar** ("Site Factory" — the autonomous landing-page launch loop). Apex is the unified console over both.
