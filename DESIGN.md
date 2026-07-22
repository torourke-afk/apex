# Apex — Signal Deck Design System

Visual system as implemented in `Executive Scorecard.dc.html` — a single Design Component that routes all **12 Apex surfaces** behind the shared AppShell chrome. Dark-first "mission-control" aesthetic: deep atmospheric base, a single signal-cyan accent, monospace data accents over a grotesk display/body face. Merge these tokens + component specs into the Apex React + Tailwind app (BFF unchanged).

**Build status:** all 12 screens implemented and routing live (rail = router, `state.view` drives the active surface). Operations (approval queue) and the Simulator (live scenario model) are interactive; the rest render representative sample data.

---

## 1. Design tokens

All theme values are CSS custom properties on the root, swapped by `[data-theme="light"]`. Port these verbatim into your Tailwind theme (`:root` / `.dark` or a `data-theme` selector).

### Dark (default)
```
--bg:       #06080C   /* app base */
--bg2:      #0A0E14   /* raised base / filter bar */
--panel:    #0D1118   /* card surface */
--panel2:   #10151E   /* inset / segmented control track */
--elev:     #151B26   /* popovers, rail tiles */
--line:     rgba(255,255,255,.07)   /* hairline borders */
--line2:    rgba(255,255,255,.13)   /* stronger borders */
--text:     #E8ECF4
--text2:    #A4ADBF
--text3:    #6B7587
--cyan:     #34E1D4   /* THE signal accent (single, deliberate) */
--cyanInk:  #04100F   /* ink on cyan fills */
--green:    #4FD89B   /* positive / on-pace */
--amber:    #F2B14C   /* warning / over-target */
--red:      #FF5C72   /* critical */
--dot:      rgba(170,205,230,.26)  /* ambient starfield dot */
--dotStar:  rgba(190,215,235,.7)   /* brighter drifting dot */
--headerBg: rgba(10,13,19,.55)
--aura1/2/3: low-alpha cyan / blue / violet radial glows
```

### Light (AAA-tuned contrast)
```
--bg:#DDE2EA  --bg2:#EAEEF4  --panel:#FFF  --panel2:#F4F6FA  --elev:#FFF
--line:rgba(12,18,28,.13)  --line2:rgba(12,18,28,.24)
--text:#0A0E16  --text2:#414B5C  --text3:#4E5567
--cyan:#0B897E  --cyanInk:#FFF  --green:#0F7A4D  --amber:#8A5E0A  --red:#C92F47
--dot:rgba(40,70,110,.22)  --dotStar:rgba(50,80,120,.6)
--headerBg:rgba(255,255,255,.7)
```
> Accent/positive/warn/critical are darkened in light mode so all foreground/background pairings clear WCAG AAA.

---

## 2. Typography

- **Display + body:** `Space Grotesk` (400/500/600/700). Tight tracking on large numerals (`letter-spacing:-.02em`).
- **Data / labels / system chrome:** `JetBrains Mono` (400/500/700). ALL-CAPS micro-labels at 9–10px with `letter-spacing:.1–.2em`.
- Scale in use: KPI value 30px · hero numeral 58px · section title 14px · micro-label 9–10px.

---

## 3. Motion

| Keyframe | Use |
|---|---|
| `ringhero` / `ringkpi` | gauge ring reveal (neutralized to opacity-only for live re-render safety) |
| `pulseonce` | one-shot inset glow on new critical alerts |
| `blink` | console caret |
| `aura1/2/3` | slow 26–38s drift of background glow blobs |
| `floatA–floatF` | six drift vectors for the ambient dot field |
| `twinkle` | per-dot opacity flicker (5–11s, randomized phase) |

`@media (prefers-reduced-motion: reduce)` kills all animation + transition.

---

## 4. Atmosphere (the "luxury" background)

Single `aria-hidden`, `pointer-events:none`, `z-index:0` layer behind a `position:relative; z-index:1` content column. Stack:
1. **Three aura blobs** — large blurred radial gradients (cyan / blue / violet) drifting on `aura1/2/3`.
2. **Ambient dot field** — 450 individually-positioned dots. Each is an **outer wrapper** carrying a random `floatA–F` drift (16–42s, negative delay so phases are desynced) wrapping an **inner dot** carrying `twinkle` + a JS-driven repel transform. ~18% are brighter `--cyan` "stars".
3. **Cursor repel** — a single `mousemove`→`requestAnimationFrame` handler reads each dot's % position vs. the cursor; within `R=130px` it translates the inner dot away from the cursor up to `MAX=40px`, scaled by proximity, easing back via `transition:transform .4s`. Outer drift + inner repel compose because they live on separate elements.
4. **Vignette** — radial fade to `--bg` (transparent 52% → bg 100%) so dots read in open areas without overpowering content.

Generate the dot array **once** (stable positions/timings) so re-renders never restart the animations.

---

## 5. Component specs

### Routing
The rail is the router. `railDef` holds 12 entries (`{ code, name, view, crumb, title, badge }`); clicking sets `state.view`, which drives the breadcrumb/title and an `is<Screen>` flag per surface. All screens share the chrome, atmosphere, theme, and BD/Client toggle. Map this onto Apex's `src/pages/` + route table.

### AppShell chrome
- **Icon rail** — collapsible (218px ↔ 64px), 2-letter mono tiles, active item = cyan tile + glow + tinted row, red count badges (e.g. Operations · 3). Collapse toggle at the foot.
- **Context bar** — breadcrumb + screen title, sync-status pill, client switcher (logo + "+ N RV VALIDATION"), **BD / CLIENT** segmented toggle, theme toggle.
- **Global filter bar** (Scorecard only) — Range (with dropdown), Product, DMA, Channel chips + dashed Reset.
- **Agent console** (footer) — cyan `›` prompt, blinking caret, directive input, tool chips (`query_metrics` / `simulate_geo` / `propose_action`), Send.

### Scorecard surface
- **HUD ribbon** — mission status, contract week, autopilot/model/alert counters.
- **Hero gauge** — composite Contract Health ring (88%) + three sub-bars (Acquisition / Efficiency / Retention).
- **PrimaryKPIDeck** — 3-col card grid: value, delta vs. target (green/amber), sparkline, mini progress ring. Metrics: Funded Accounts, CPIHH, Portfolio LTV, Blended ROAS, MOB6 Retention.
- **OperatingStreak** — cyan-bordered card, weeks-on-pace segmented bar.
- **Financial summary strip** — Total Spend / Attrib. Revenue / Net Margin / Efficiency / Pacing.
- **Campaign leaderboard** — table (Campaign · Channel · Spend · ROAS), ROAS badge green ≥3.5× else red.
- **Alert wire** — severity bar + tag (CRITICAL/WARNING/INFO) + text + time + ACK; criticals pulse once on entry; empty-state "wire clear".

### Other surfaces (2–11)
- **Spend & Budget** — 4-up KPI (budget/spent/remaining/pace), cumulative pacing chart (plan vs actual), channel-allocation bars, NBD reallocation ledger table.
- **Media Performance** — channel table (spend/CPIHH/CVR/ROAS + sparkline trend), saturation curves (Hill response), efficiency-frontier bubble chart.
- **Creative & Messaging** — creative-unit card grid with format + fatigue tag (Fresh/Aging/Fatigued) and CTR/CVR/spend, message-theme resonance bars.
- **Audience & Geo** — DMA ROAS-intensity grid (heat cells), top-markets list, audience-segment cards (Core/Grow/Trigger/Retain).
- **Product & Conversion** — product-line table (funded/CPIHH/LTV/margin), per-product conversion-path mini-funnels.
- **Acquisition Funnel** — *signature* Sankey (Channel → Visit → Lead → Application → Funded) with filled bezier ribbons + node counts, plus stage-conversion KPI cards vs benchmark.
- **Retention & LTV** — KPI row, cohort-retention heatmap (acquisition month × months-on-book), cumulative-LTV accrual curve with CPIHH breakeven marker.
- **Operations Command** — *HITL centerpiece*, interactive: left **Approval Queue** of Kamino directives (tool tag, confidence, status), right **Directive Review** (rationale, projected impact, risk, tool chain) with Approve / Reject / Defer; rail badge reflects pending count.
- **Full-Funnel Simulator** — interactive: scenario sliders (budget, brand %, SEM %, social %, residual email) feed a saturation-damped mix model that recomputes Funded / CPIHH / ROAS / LTV live vs plan-of-record, plus a funded-trajectory chart.
- **Modeling & Attribution** — incremental-contribution bars (MMM+MTA blend), model-registry table (type / R² / live·stale), incrementality-test results (lift + method + p-value).

### Settings surface
- **Application Mode** — BD/Client perspective + Agent Autopilot (Manual/Assist/Auto) segmented controls.
- **Appearance** — Theme, Density, and **Signal Accent** swatches (live-rewrites `--cyan`).
- **Data & Export** — default format segmented control, response-cache toggle, clear-cache action.
- **Data Source Integrations** — connector cards (Google/Microsoft/Meta/GA4/Snowflake/Salesforce) with brand monogram, **masked API key**, live status pill (Synced/Syncing/Error/Offline), Connect/Disconnect/Reconnect.
- **Benchmark Configuration** — tabbed (Funnel / Media / Defaults / Efficiency / NBD) live slider editor feeding the metric layer, with Reset / Save.

---

## 6. Layout primitives
- Cards: `border-radius:14–16px` desktop, 12px tablet, 10px mobile. `1px solid var(--line)`, `background:var(--panel)`; hover lifts border to `--line2`.
- Section headers: 3px cyan (or red) accent bar + title + mono meta on the right.
- Segmented controls: `--panel2` track, active = `--cyan` fill / `--cyanInk` text.
- Inline styles throughout (per Apex DC convention); only `@font-face`, `@keyframes`, range-input and scrollbar resets live in a stylesheet.
