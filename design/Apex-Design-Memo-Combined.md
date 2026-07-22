# Apex Front-End Design Memo · "Signal Deck"

**The combined direction — Neo-Terminal theming system × Mission Control engagement, in Space Grotesk + JetBrains Mono.**

**For:** Claude design (front-end build) · **Product:** Apex — RVGT Marketing Intelligence Platform · **Date:** June 24, 2026 (rev. June 24 — reconciled to delivered Executive Scorecard mockup)

> This is the chosen direction, merging the two finalists. **Direction 2 (Neo-Terminal)** supplies the foundation: a clean, token-driven, WCAG-AA theming system with light/dark via a class toggle and drop-in new themes. **Direction 3 (Mission Control)** supplies the personality: a calm strategy-console feel with celebration-on-real-wins and progressive-reward feedback, applied to Apex's agentic directive/approval loop. Typography is **Space Grotesk + JetBrains Mono**. Hand this to engineering as the front-end spec; it merges back into the unified microservice build (the UI is a thin client over the Gateway/BFF).
>
> **Source of truth:** the delivered `design/mockups/Executive-Scorecard.dc.html` mockup. The token values, font, and palette below are reconciled to it (Space Grotesk UI font, teal `#34E1D4` signal accent, the `--panel/--elev/--cyan` value set). Semantic token *names* (`--color-bg-surface`, `--color-accent`, …) are retained so the system stays portable; each maps to a mockup value, given in the tables below.

---

## 1. Concept — "Signal Deck"

Apex is a CMO-grade marketing-intelligence console across 7 domains (Executive Scorecard, Spend, Channels [Brand/Performance/SEO/AEO], Funnel, Product & Ops, Simulator, Retention) plus an agentic directive layer. The design treats it as a **signal deck**: calm and legible at rest, instrument-like under load, and quietly satisfying when you win or commit an action. Saturation is reserved for *live data and outcomes*; chrome stays desaturated. Engagement comes from honest feedback systems borrowed from games — never decoration for its own sake.

Two non-negotiable promises:
1. **It's a system, not a skin.** Components reference semantic tokens only; a theme is a values block. Accessibility is enforced, not hoped for.
2. **Feedback is earned and true.** Celebrations fire only on objectively-good, rare events; rewards reflect real operating discipline. Everything respects `prefers-reduced-motion`.

---

## 2. Typography — Space Grotesk + JetBrains Mono

Simple and modern; Space Grotesk gives the UI a clean technical character that suits an instrument/console without being a generic grotesk.

- **UI / headings / body:** **Space Grotesk**. Weights: 400 body, 500 labels, 600 headings/values, 700 for the single hero figure. Display headings use `-0.02em` tracking; uppercase HUD/instrument labels use `letter-spacing: 0.06em`.
- **Numerals / data / console / code:** **JetBrains Mono**, with **`font-variant-numeric: tabular-nums` everywhere a number appears** so values lock into columns across rows. Also used for the mission-control console input line and any monospace affordance.

```css
--font-sans: 'Space Grotesk', ui-sans-serif, system-ui, sans-serif;
--font-mono: 'JetBrains Mono', ui-monospace, 'SF Mono', monospace;
```
Load both via Google Fonts (matches the mockup):
`https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap`. Fallback to system if a network fetch fails.

Type scale (rem): `xs .75 · sm .8125 · base .9375 · lg 1.125 · xl 1.5 · 2xl 2 · 3xl 2.75`. Line-height 1.1 for big values, 1.5 for body. Hero figure = `2.75rem / 700 / mono`.

---

## 3. The theming system (from Direction 2)

### 3.1 Three-tier tokens
1. **Primitive** — raw values, theme-agnostic (e.g. `--teal-400:#34E1D4`). Never used by components.
2. **Semantic** — role-based, theme-switched (`--color-bg-canvas`, `--color-text-primary`, `--color-accent`…). Components use only these.
3. **Component** — optional, derived (`--kpi-value-color: var(--color-text-primary)`).

Switching theme swaps the semantic layer under `[data-theme="x"]`; components never change.

### 3.2 Palette — reconciled to the delivered mockup (teal signal accent)

Values come directly from `design/mockups/Executive-Scorecard.dc.html`. The mockup uses the short token names (`--bg`, `--panel`, `--cyan`, …); we keep our portable semantic names and map each to the mockup value (mapping shown in the comment). Both are valid to ship — Tailwind can alias either set.

**DARK (default)** — the primary "signal deck" surface:
```css
[data-theme="dark"]{                 /* mockup :root */
  --color-bg-canvas:#06080C;         /* --bg  */
  --color-bg-base:#0A0E14;           /* --bg2  (radial-gradient partner) */
  --color-bg-surface:#0D1118;        /* --panel */
  --color-bg-raised:#10151E;         /* --panel2 */
  --color-bg-elevated:#151B26;       /* --elev */
  --color-text-primary:#E8ECF4;      /* --text  */
  --color-text-secondary:#969FB2;    /* --text2 */
  --color-text-muted:#586173;        /* --text3 */
  --color-border:rgba(255,255,255,.07);   /* --line  */
  --color-border-strong:rgba(255,255,255,.13); /* --line2 */
  --color-accent:#34E1D4;            /* --cyan — teal signal accent */
  --color-accent-contrast:#04100F;   /* --cyanInk */
  --color-signal:#34E1D4;            /* same teal — live/active */
  --color-positive:#4FD89B;          /* --green */
  --color-warning:#F2B14C;           /* --amber */
  --color-critical:#FF5C72;          /* --red — used for criticals/destructive */
  --color-grid:rgba(255,255,255,.035);     /* --grid (ledger texture) */
  --shadow-1:0 1px 2px rgba(0,0,0,.4); --shadow-2:0 8px 24px rgba(0,0,0,.45);
}
```

**LIGHT:**
```css
[data-theme="light"]{                /* mockup [data-theme="light"] */
  --color-bg-canvas:#E9ECF1;         /* --bg  */
  --color-bg-base:#F3F5F8;           /* --bg2 */
  --color-bg-surface:#FFFFFF;        /* --panel */
  --color-bg-raised:#FAFBFD;         /* --panel2 */
  --color-bg-elevated:#FFFFFF;       /* --elev */
  --color-text-primary:#0C1018;      /* --text  */
  --color-text-secondary:#525C6F;    /* --text2 */
  --color-text-muted:#8A92A3;        /* --text3 */
  --color-border:rgba(12,18,28,.10);       /* --line */
  --color-border-strong:rgba(12,18,28,.18);/* --line2 */
  --color-accent:#0C998D;            /* --cyan (darkened teal for AA on white) */
  --color-accent-contrast:#FFFFFF;   /* --cyanInk */
  --color-signal:#0C998D;
  --color-positive:#138A58;          /* --green */
  --color-warning:#9C6E12;           /* --amber */
  --color-critical:#D4374F;          /* --red */
  --color-grid:rgba(12,18,28,.05);         /* --grid */
  --shadow-1:0 1px 2px rgba(16,24,40,.06); --shadow-2:0 8px 24px rgba(16,24,40,.10);
}
```

**Contrast contract (enforce in CI):** every `--color-text-*` on its `--color-bg-*`, and `--color-accent-contrast` on `--color-accent`, meets **WCAG AA** (≥4.5:1 body, ≥3:1 large/UI). Ship a small token-pair contrast lint in the build; treat the values above as a test. Note the teal accent is **darkened to `#0C998D` in light mode** specifically to clear AA on white; the bright `#34E1D4` is dark-mode only. The contrast lint must verify the active-theme accent, not just one value.

### 3.3 Toggle (class-based, no flash)
```js
const saved = localStorage.getItem('apex-theme');
const sys = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark':'light';
document.documentElement.dataset.theme = saved || sys;   // apply before first paint
```
Top-bar toggle flips `data-theme` + writes `localStorage`. (The new build is React + Tailwind, so this is the canonical mechanism; the legacy Streamlit shell achieved the same via `st.session_state['apex_theme']` → `inject_brand_css()`.)

### 3.4 Adding themes later (no refactor)
```css
[data-theme="rvgt-classic"]{ --color-bg-canvas:#060B26; --color-accent:#0075FF; --color-signal:#2CD9FF; --color-critical:#FF0016; /* … */ }
[data-theme="client-acme"]{ --color-accent:#0A7C42; --color-critical:#C0392B; /* inherits base via @layer */ }
```
Use `@layer tokens, components, overrides;` so white-label client overrides avoid specificity wars.

### 3.5 Shape, spacing, motion tokens
```css
--radius-sm:6px; --radius-md:10px; --radius-lg:14px; --radius-pill:999px;
--space-1:4px; --space-2:8px; --space-3:12px; --space-4:16px; --space-6:24px; --space-8:32px; --space-12:48px;
--space-card:24px; --space-section:32px;
--ease:cubic-bezier(.2,0,0,1); --t-fast:140ms; --t:220ms; --t-slow:420ms;
```
Focus ring (AA-visible both themes): `outline:2px solid var(--color-signal); outline-offset:2px;`

---

## 4. The Mission-Control layer (from Direction 3)

Borrow game *feedback systems*, not aesthetics. Two mechanics, applied with executive restraint.

### 4.1 Consequence feedback (celebration on real wins)
Fire **only** on objectively-good, rare events; ≤600ms; never blocking; never on routine refresh; **max one celebratory element on screen at once**; all gated by `prefers-reduced-motion`.

- **KPI crosses target:** value pulses once, a thin progress ring completes around it in `--color-positive`, a "▲ target met" chip slides in. No confetti.
- **Directive completes:** the queue row plays a left→right success sweep (positive-green gradient wipe), then settles with a checkmark that draws itself.
- **Scenario beats plan (Simulator):** the headline delta counts up and **over-shoots ~4% then eases back** (anticipation curve) so the win lands.
- **Losing/missing is never punitive** — neutral, explanatory states only.

### 4.2 Progressive rewards (earned depth + momentum)
- **Operating streaks:** "On-pace 6 weeks" / "Alerts cleared 12 days" as subtle, data-true momentum on the Scorecard — discipline, not points.
- **Progressive disclosure:** advanced levers (per-DMA bid overrides, simulator advanced controls) stay collapsed until the basic flow is engaged — power features surface as "unlocked tools."
- **Mission tracker:** multi-step flows (build scenario → review → submit directive → approve → executed) render as a horizontal segmented bar that fills as you advance.

### 4.3 Optional sound
Default **off**, opt-in only, global mute respected: one soft tick for criticals, one soft positive tone for completions. Never required.

---

## 5. Layout system

Persistent **left icon rail** (collapsible) + **top context bar** + main canvas, with an omnipresent **agent console** docked at the bottom (the directive/chat entry, styled as a console input line with a blinking caret in `--color-signal`). A right-hand **alert wire** appears on the Scorecard and where relevant.

Three signature screen patterns (carried from Mission Control, themed by the system):

- **A · Command Console (Executive Scorecard).** Top status ribbon (all-systems-nominal vs. N alerts) as a HUD. Hero KPI as a **radial gauge** (target = the ring; fill animates on load). 2×3 grid of KPI "instruments" (sparkline + delta + target ring). Right rail = alert wire, newest sliding in, criticals get one attention pulse then go quiet. Bottom = agent console line.
- **B · Strategy Map (Spend / Funnel).** Channels/DMAs as nodes sized by spend; funnel flows as throttled particle streams (density = volume). Sliders rebalance with spring easing; **"Commit plan"** stages a *pending directive* (not an instant write) → enters approval queue with a soft "queued" tick + a mission-tracker segment fill.
- **C · Mission Debrief (Simulator / Retention).** Left = baseline plan, right = simulated outcome. Run = brief scan-line sweep over the projection (≤900ms) resolving into the over-shoot count-up headline. A plain-language debrief panel ties to the agent.

---

## 6. Component spec (semantic tokens only)

```css
.kpi-card{ background:var(--color-bg-surface); border:1px solid var(--color-border);
  border-radius:var(--radius-lg); padding:var(--space-card); box-shadow:var(--shadow-1); }
.kpi-card__label{ font:500 var(--fs-xs)/1 var(--font-sans); letter-spacing:.06em; text-transform:uppercase; color:var(--color-text-secondary); }
.kpi-card__value{ font:600 2rem/1.1 var(--font-mono); font-variant-numeric:tabular-nums; color:var(--color-text-primary); }
.kpi-card__delta--up{ color:var(--color-positive); } .kpi-card__delta--down{ color:var(--color-critical); }
.kpi-card__ring{ /* SVG target ring; stroke=var(--color-positive); animates stroke-dashoffset on cross-target */ }

.btn--primary{ background:var(--color-accent); color:var(--color-accent-contrast); border:none; border-radius:var(--radius-md); font:600 var(--fs-sm) var(--font-sans); }
.alert--critical{ border-left:3px solid var(--color-critical);
  background:color-mix(in oklab, var(--color-critical) 12%, var(--color-bg-surface)); }
.console{ font:400 var(--fs-sm) var(--font-mono); color:var(--color-text-secondary);
  border:1px solid var(--color-border); border-radius:var(--radius-md); }
.console__caret{ color:var(--color-signal); animation:blink 1s steps(1) infinite; }
.chip--agent{ background:color-mix(in oklab, var(--color-accent) 16%, transparent); color:var(--color-accent);
  border:1px solid color-mix(in oklab, var(--color-accent) 30%, transparent); border-radius:var(--radius-pill); }
.mission-track__seg{ background:var(--color-bg-elevated); } .mission-track__seg--filled{ background:var(--color-signal); }
```

**Implementation = React + Tailwind.** Build each as a typed **React** component styled with **Tailwind** classes that resolve to the semantic CSS custom properties above (Tailwind theme maps `accent → var(--color-accent)`, `critical → var(--color-critical)`, etc.), so light/dark and future themes swap via `data-theme` with zero component edits. The CSS shown here is the token/intent contract; in code it lives as Tailwind utilities + a small `globals.css` token sheet. These map 1:1 onto the existing Apex surfaces (kpi_card, chart_wrapper, data_table, filter_bar, global_filter_strip, metric_strip, card_container, section_header, alert_badge, chat_drawer → agent console, scenario_compare → Mission Debrief), now rebuilt as the React library. The directive flow uses the Kamino `DirectiveStatus` state machine over the BFF; the approval queue is the "commit → queued → approved → executed" tracker.

---

## 7. Motion choreography

- **Page load:** instruments "power on" in a 50ms stagger (panel backlight fades up, then gauge needles/rings sweep to value); KPI values roll up on tabular numerals; charts draw their stroke (`stroke-dashoffset`, `--t-slow`).
- **Theme switch:** surfaces cross-fade over `--t`.
- **Hover/active:** signal-cyan focus ring; nav active state = accent fill with `--color-accent-contrast` text.
- **Reduced motion:** drop staggers, sweeps, count-ups, and celebrations → instant states. The system must be fully usable and legible with motion off.

---

## 8. Why this is the right merge

The theming system makes it **safe, accessible, and reusable** (white-label-ready, AA-guaranteed) — the lowest-risk backbone. The mission-control layer makes it **engaging exactly where Apex needs it** — the agentic directive/approval and simulation surfaces — without betting the product on heavy motion. Space Grotesk + JetBrains Mono keep it simple and modern while giving the numerals the precision a data tool demands, and the teal signal accent matches the delivered mockup.

## 9. Build target — React + Tailwind over the BFF

This is delivered as a **Next.js (App Router) + TypeScript + Tailwind CSS** front end — a *thin client* over the unified microservice **Gateway/BFF** (the React app consumes BFF JSON via typed TanStack Query hooks; SQL and metric computation stay in the data layer and never surface in components). Tailwind's theme references the semantic CSS variables, so the token system, light/dark toggle, and white-label themes are pure config. Charts via Recharts/visx (gauge + curves), motion via Framer Motion (reduced-motion gated), DnD via dnd-kit, icons via lucide-react. The full build instructions — DESIGN.md, the component library, and the accessibility/responsive pass — are in the companion **`Apex-React-Frontend-Scaffold-Prompt.md`**.
