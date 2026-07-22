# Apex Front-End Design Memo · Direction 1 — "Editorial Instrument"

**For:** Claude design (front-end build) · **Product:** Apex — RVGT Marketing Intelligence Platform · **Date:** June 24, 2026

> This is one of three competing directions. Build it as a self-contained design language that could be handed to engineering and merged into the Apex front end. Apex is a CMO-grade marketing-intelligence dashboard: 7 domains (Executive Scorecard, Spend, Channels [Brand/Performance/SEO/AEO], Funnel, Product & Ops, Simulator, Retention) plus an agentic directive/approval layer.

## Design intent

Reject the generic dark-SaaS-dashboard look. Treat Apex like a **financial broadsheet meets a precision instrument** — the authority of the *Financial Times* / Bloomberg Terminal, rendered with editorial typography and a single confident accent. Data should feel *printed and exact*, not glowing and decorative. Surprise comes from restraint and craft: tabular numerals that lock into columns, hairline rules instead of boxes, one decisive red.

## Typography (distinctive, intentional)

Avoid Inter/Arial. Use a deliberate three-family system:

- **Display / headings:** **GT Sectra** or **Fraunces** (a high-contrast serif). Used for page titles, section heads, and the single hero KPI per page. This is the editorial signature.
- **UI / labels / body:** **Söhne** or **Neue Haas Grotesk** (fallback: **Geist**) — a grotesk with real personality, not Inter. Tight tracking on labels (`letter-spacing: 0.04em; text-transform: uppercase` for metric labels).
- **Numerals / data:** **Söhne Mono** or **Commit Mono** with `font-variant-numeric: tabular-nums` everywhere a number appears. Numbers must align vertically across rows.

Weight choreography: headings at **300 (light) for large display** + **600 for the value**, so a KPI reads as a light serif label over a heavy value. Never bold body text; emphasis comes from the serif/grotesk contrast, not weight spam.

## Color & theme (bold dominant + sharp accent)

A warm-paper / ink system with a single scarlet — RVGT red survives, but as a *scalpel*, not a wash.

```css
:root{
  /* Dominant ground: warm ink-on-paper, not navy */
  --paper:        #F4F1EA;   /* light mode ground — warm newsprint */
  --paper-raised: #FBF9F4;   /* cards */
  --ink:          #1A1714;   /* near-black warm ink (never #000) */
  --ink-soft:     #5B554C;   /* secondary text */
  --rule:         #D8D2C4;   /* hairline rules */
  /* The one accent */
  --scarlet:      #E2231A;   /* RVGT red — used at <8% of surface area */
  --scarlet-ink:  #B01610;   /* pressed/active */
  /* Data semantics — muted, editorial, not neon */
  --pos:          #1F6F4A;   /* deep green */
  --neg:          #C0392B;
  --warn:         #B8860B;   /* dark goldenrod */
}
[data-theme="dark"]{
  --paper:        #16130F;   /* warm near-black, not navy */
  --paper-raised: #201C17;
  --ink:          #EDE8DF;
  --ink-soft:     #A39B8C;
  --rule:         #322C24;
  --scarlet:      #FF4438;
  --pos:          #4FB783; --neg:#F0735F; --warn:#E0A82E;
}
```

Rule: the dominant 90% of every screen is paper/ink. Scarlet appears only on the single most important number, the active nav item, and destructive/approve actions. The discipline *is* the distinctiveness.

## Background & depth (atmosphere via lines, not fills)

- **No card shadows.** Depth comes from **hairline rules** (`0.5px solid var(--rule)`) and **whitespace**, like a printed page. Cards are defined by a top rule + generous padding, not a floating box.
- A **faint baseline grid** texture on the ground: `background-image: linear-gradient(var(--rule) 0.5px, transparent 0.5px); background-size: 100% 28px; opacity: .25;` behind data regions — evokes ledger paper.
- The hero KPI sits on a subtle **paper gradient** (`linear-gradient(180deg, var(--paper-raised), var(--paper))`) with a single scarlet 2px rule on its left edge.
- Charts: no gridlines except a single hairline baseline; series drawn as thin 1.5px strokes; the "winning" series in scarlet, all others in ink-soft.

## Motion & micro-interactions (high-impact moments)

- **Page-load staggered reveal:** on navigation, the page composes top-to-bottom — page title (serif) fades+rises first (200ms), then the KPI row reveals **left-to-right with a 60ms stagger per card**, the value counting up via tabular-num ticker, then charts draw their stroke in (`stroke-dashoffset` animation, 500ms ease-out). The screen *assembles like a page going to print*.
- **KPI tick:** values animate from prior period to current with an odometer roll on the tabular numerals; delta arrow draws after the number settles.
- **Scarlet underline on hover:** nav and tab items get a scarlet rule that wipes in from left (150ms) — the only "playful" motion, and it's restrained.
- **Directive approval:** approving a directive stamps a faint scarlet "APPROVED" letterpress mark that fades, then the row settles into the executed state. Make the consequential moment feel weighty.
- Respect `prefers-reduced-motion`: drop staggers and counts, keep instant states.

## Signature layout moves

- **One hero metric per page**, set in large light serif with a heavy value — the editorial lede. Everything else is supporting copy.
- **Ledger tables**: tabular-num columns, hairline row rules, scarlet conditional badges (e.g., ROAS < target). No zebra striping.
- **Margin notes**: secondary context (benchmarks, "vs. plan") set in small grotesk in the right margin, like footnotes.

## Apex-specific applications

- **Executive Scorecard:** front-page broadsheet — one giant hero KPI (e.g., funded accounts), a row of staggered supporting KPIs, the alert feed as a dated "wire" column.
- **Simulator:** before/after as two columns of a ledger; the scarlet delta is the headline.
- **Directive queue:** reads like an editor's approval desk — each directive a typeset entry awaiting the scarlet stamp.

**Why pick this:** it will not look like any other dashboard. The risk: it demands typographic discipline and licensed fonts (Söhne/GT Sectra) — budget for fonts or use Fraunces + Geist as open fallbacks.
