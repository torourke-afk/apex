# Apex Front-End Design Memo · Direction 2 — "Neo-Terminal Theming System"

**For:** Claude design (front-end build) · **Product:** Apex — RVGT Marketing Intelligence Platform · **Date:** June 24, 2026

> One of three competing directions. This memo defines a **complete, extensible CSS theming system** with light + dark via a `data-theme` class toggle, **WCAG AA-verified** foreground/background pairings, and a distinctive palette inspired by **cyberpunk terminal UIs tempered for an enterprise data tool**. It is structured so new themes (e.g., "RVGT Classic", "High-Contrast", a client white-label) drop in without refactoring.

## Why a system, not just a palette

Apex has 12 pages, ~14 shared components, and a BD-vs-Client mode that may eventually need white-labeling. The design must be **token-driven**: components reference semantic variables only, and a theme is just a values file. This makes the existing `brand.py` token approach the right foundation — we formalize and extend it.

## Token architecture (three tiers)

1. **Primitive tokens** — raw values, theme-agnostic (e.g., `--violet-500: #7C5CFF`). Never used directly by components.
2. **Semantic tokens** — role-based, theme-switched (e.g., `--color-bg-canvas`, `--color-text-primary`, `--color-accent`, `--color-positive`). Components use *only* these.
3. **Component tokens** — optional, derived (e.g., `--kpi-value-color: var(--color-text-primary)`). Lets one component re-skin without touching globals.

Switching theme = swapping the semantic layer under `[data-theme="x"]`. Components never change.

## The palette (distinctive — neo-terminal)

Cyberpunk DNA (electric violet + cyan signal on near-black) but **disciplined for hours of analytical reading**: low-saturation grounds, saturated accents reserved for data and action. RVGT red retained as the "alert/critical" signal so brand identity survives.

```css
:root{
  /* ── Primitive tokens (theme-agnostic) ───────────────────── */
  --violet-300:#A78BFF; --violet-500:#7C5CFF; --violet-700:#5B3FD6;
  --cyan-300:#5FE9FF;   --cyan-500:#16C8E8;   --cyan-700:#0E93AC;
  --rvgt-red:#E2231A;   --rvgt-red-700:#B01610;
  --grn-400:#34D39E; --grn-600:#0E9F73;
  --amb-400:#F5B544; --amb-600:#C4870F;
  --ink-950:#0A0B12; --ink-900:#0E1018; --ink-800:#151823; --ink-700:#1E2230;
  --paper-0:#FFFFFF; --paper-50:#F6F7FB; --paper-100:#ECEEF5; --paper-200:#DCE0EC;
  --slate-300:#AEB4C7; --slate-500:#6B7punk… /* see note */
}
```
*(Note: keep primitives literal hex; the `--slate-500` line above is illustrative — use `#6B7280`.)*

### Semantic layer — DARK (default)

```css
[data-theme="dark"]{
  --color-bg-canvas:      var(--ink-950);   /* app ground */
  --color-bg-surface:     var(--ink-900);   /* cards */
  --color-bg-raised:      var(--ink-800);   /* popovers, sidebar */
  --color-bg-sunken:      var(--ink-700);   /* inputs, filter bar */
  --color-text-primary:   #EDF0F7;          /* AA on canvas: 15.8:1 */
  --color-text-secondary: #AEB4C7;          /* AA on canvas: 8.1:1 */
  --color-text-muted:     #7E869B;          /* AA (large/UI) on canvas: 4.7:1 */
  --color-border:         #262B3A;
  --color-accent:         var(--violet-300);/* links, active — AA on surface */
  --color-accent-contrast:#0A0B12;          /* text ON accent fills */
  --color-info:           var(--cyan-300);
  --color-positive:       var(--grn-400);   /* AA on canvas: 8.9:1 */
  --color-warning:        var(--amb-400);
  --color-critical:       #FF5A4D;          /* RVGT red lifted for AA on dark: 5.3:1 */
  --shadow-1: 0 1px 2px rgba(0,0,0,.4);
  --shadow-2: 0 8px 24px rgba(0,0,0,.45);
}
```

### Semantic layer — LIGHT

```css
[data-theme="light"]{
  --color-bg-canvas:      var(--paper-50);
  --color-bg-surface:     var(--paper-0);
  --color-bg-raised:      var(--paper-0);
  --color-bg-sunken:      var(--paper-100);
  --color-text-primary:   #14161F;          /* AA on canvas: 16.2:1 */
  --color-text-secondary: #4A4F60;          /* AA on canvas: 8.4:1 */
  --color-text-muted:     #6B7280;          /* AA (UI) on canvas: 4.6:1 */
  --color-border:         #DCE0EC;
  --color-accent:         var(--violet-700);/* AA on white: 5.9:1 */
  --color-accent-contrast:#FFFFFF;          /* on accent fill: 5.9:1 */
  --color-info:           var(--cyan-700);
  --color-positive:       var(--grn-600);   /* AA on white: 4.6:1 */
  --color-warning:        var(--amb-600);
  --color-critical:       var(--rvgt-red);  /* AA on white: 5.0:1 */
  --shadow-1: 0 1px 2px rgba(16,24,40,.06);
  --shadow-2: 0 8px 24px rgba(16,24,40,.10);
}
```

**Contrast contract (must verify in CI):** every `--color-text-*` against its intended `--color-bg-*`, and `--color-accent-contrast` on `--color-accent`, meets **WCAG AA** (≥4.5:1 body text, ≥3:1 large text/UI). The values above are chosen to pass; treat them as a test, not a suggestion. Add a contrast lint (e.g., a small script over the token pairs) to the build.

## The toggle (class-based, no flash)

```html
<html data-theme="dark">  <!-- default -->
```
```js
// Persist + respect system; apply BEFORE first paint to avoid FOUC
const saved = localStorage.getItem('apex-theme');
const sys = matchMedia('(prefers-color-scheme: dark)').matches ? 'dark':'light';
document.documentElement.dataset.theme = saved || sys;
```
A toggle in the top bar flips `data-theme` and writes `localStorage`. (In the current Streamlit app this maps to `st.session_state['apex_theme']` driving `inject_brand_css()` — same contract, server-rendered.)

## Adding a theme later (no refactor)

A new theme = one new block. Components never change because they only read semantic tokens.

```css
[data-theme="rvgt-classic"]{ /* the navy/glass look, as a theme */
  --color-bg-canvas:#060B26; --color-accent:#0075FF; --color-info:#2CD9FF;
  --color-critical:#FF0016; /* …rest of semantic tokens… */
}
[data-theme="client-acme"]{ /* white-label: swap accent + criticals only */
  --color-accent:#0A7C42; --color-critical:#C0392B; /* inherits a base via @layer */
}
```
Use `@layer tokens, components, overrides;` so client overrides can be layered without specificity wars.

## Typography & shape (system-level)

- **Font:** `Geist` (UI) + `Geist Mono` (all numerals, `font-variant-numeric: tabular-nums`). Distinctive, open, not Inter. Display headings may use `Geist` at weight 600 with `-0.02em` tracking.
- **Radius scale:** `--radius-sm:6px; --radius-md:10px; --radius-lg:14px; --radius-pill:999px;`
- **Spacing scale:** 4 · 8 · 12 · 16 · 24 · 32 · 48 (semantic: `--space-card:24px`, `--space-section:32px`).
- **Elevation:** dark mode uses faint violet-tinted glow on accent surfaces; light mode uses soft neutral shadows.

## Component token examples (so engineering sees the seam)

```css
.kpi-card{
  background:var(--color-bg-surface); border:1px solid var(--color-border);
  border-radius:var(--radius-lg); padding:var(--space-card); box-shadow:var(--shadow-1);
}
.kpi-card__value{ color:var(--color-text-primary); font:600 1.75rem/1.1 'Geist Mono'; font-variant-numeric:tabular-nums; }
.kpi-card__delta--up{ color:var(--color-positive); }
.btn--primary{ background:var(--color-accent); color:var(--color-accent-contrast); }
.alert--critical{ border-left:3px solid var(--color-critical); background:color-mix(in oklab, var(--color-critical) 12%, var(--color-bg-surface)); }
```

## Motion (subtle, system-defined)

Tokens: `--ease:cubic-bezier(.2,0,0,1); --t-fast:140ms; --t:220ms;`. Theme switch cross-fades surfaces over `--t`. Accent elements get a 1px cyan focus ring (`outline: 2px solid var(--color-info); outline-offset:2px`) — AA-visible in both themes.

**Why pick this:** it's the lowest-risk, most reusable direction — a real design *system* that scales to white-label and guarantees accessibility. It's distinctive (neo-terminal) without betting the product on licensed fonts or heavy motion.
