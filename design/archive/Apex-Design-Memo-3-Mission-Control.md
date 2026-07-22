# Apex Front-End Design Memo · Direction 3 — "Mission Control" (game-design analogy)

**For:** Claude design (front-end build) · **Product:** Apex — RVGT Marketing Intelligence Platform · **Date:** June 24, 2026

> One of three competing directions. The brief: make a professional analytics tool **highly engaging** by borrowing from **video-game design** — specifically **strategy/4X + flight-sim "mission control"** UIs — applying *celebration animations* and *progressive rewards* without turning a CMO tool into a toy.

## The analogy

A marketing org running paid media is, structurally, a **strategy game**: you allocate scarce resources (budget) across a map (DMAs/channels), watch systems respond over turns (weeks), get alerts when something breaches, and issue commands (directives) that take effect after confirmation. Apex's agentic directive layer *is* a command queue. So model the UI as a **mission-control console**: calm at rest, legible under load, and quietly satisfying when you win.

The discipline: borrow the *feedback systems* of games (clear state, momentum, reward), **not** their aesthetics (no cartoon, no confetti spam, no XP bars on a CMO's screen). Every game mechanic must map to a real analytical truth.

## Two mechanics, applied professionally

### 1. Celebration animations → "consequence feedback"
Games celebrate meaningful wins. In Apex, celebrate **only events that are objectively good and rare**: a KPI crossing its target, a directive completing successfully, an alert resolved, a scenario beating plan. Celebration = a **brief, tasteful flourish** (≤600ms), never blocking, never on routine renders.

- KPI crosses target: the value pulses once, a thin **progress ring completes** around it with a single soft chime-glow (color = `--color-positive`), and a small "▲ target met" chip slides in. No confetti.
- Directive completes: the queue row plays a **left-to-right success sweep** (a gradient wipe in positive-green), then settles with a checkmark that draws itself.
- Scenario beats plan in the Simulator: the winning delta **counts up and over-shoots by ~4% then eases back** (an anticipation curve borrowed from game juice) so the win *lands*.

### 2. Progressive rewards → "earned depth & momentum"
Games reveal complexity as you demonstrate mastery, and show momentum. In Apex this is **not** points — it's **earned context and streaks of good operating behavior**:

- **Operating streaks:** "On-pace 6 weeks" / "Alerts cleared 12 days" shown as a subtle momentum indicator on the Scorecard — a flame-free, data-true streak. Rewards consistent discipline, the thing CMOs actually want.
- **Progressive disclosure:** advanced controls (e.g., per-DMA bid overrides, simulator advanced levers) stay collapsed until the user has engaged the basic flow — reducing first-run overwhelm, surfacing power features as "unlocked tools" once relevant.
- **Mission progress:** multi-step flows (build scenario → review → submit directive → approve → executed) render as a **horizontal mission tracker** with segments that fill as you advance — the satisfying "objective progress" bar, applied to a real workflow.

## Three concrete layout ideas

### Layout A — "Command Console" (Executive Scorecard)
A dark mission-control deck. Top: a **status ribbon** (all-systems-nominal vs. N alerts) like a HUD. Center: the hero KPI as a **radial gauge** (target = the ring; fill animates on load). Flanking: a 2×3 grid of KPI "instruments," each a small card with a sparkline and a target ring. Right rail: the **alert wire** as an incoming-comms feed, newest sliding in from the top with a soft ping for criticals. Bottom: the **command bar** (the chat/directive entry) styled like a console input line with a blinking caret.

*Micro-interactions:* on load, instruments power-on in a 50ms stagger (panel backlight fades up, then needles sweep to value); criticals in the alert wire get a single attention pulse, then go quiet.

### Layout B — "Strategy Map" (Spend Allocation / Funnel)
Treat budget allocation as a **resource-map**. Channels/DMAs are nodes sized by spend; flows between funnel stages are animated **particle streams** whose density = volume (subtle, throttled). Dragging a budget slider re-balances the map in real time with eased transitions — the "RTS resource reallocation" feel. A **"commit plan"** action stages changes as a *pending directive* (not instant), reinforcing human-in-the-loop: you're issuing orders, not flipping switches.

*Micro-interactions:* slider drag → nodes resize with spring easing; "commit" → the affected flows brighten and a mission-tracker segment fills; the directive enters the approval queue with a soft "queued" tick.

### Layout C — "Mission Debrief" (Simulator / Retention)
Scenario modeling as a **pre/post mission briefing**. Left: the plan (baseline). Right: the simulated outcome. Run = a brief "computing" state (a scan-line sweep over the projection area, ≤900ms) that resolves into the result with the over-shoot count-up on the headline delta. A **debrief panel** summarizes "what changed and why" in plain language (ties to the chat/agent). Beating plan triggers the consequence-feedback flourish; missing plan stays neutral and explanatory (never punitive — losing must feel informative, not bad).

## Visual language (so it stays professional)

- **Palette:** near-black mission ground (`#0B0E16`), instrument surfaces a touch lighter, **single signal accent** in cyan (`#3FE0FF`) for live/active, **positive green** for wins, **RVGT red** strictly for criticals/destructive. Saturation only on live data and outcomes; chrome stays desaturated.
- **Type:** `Geist` + `Geist Mono` (tabular-nums); a slightly condensed display weight for HUD labels (uppercase, `0.06em` tracking) to read as instrumentation.
- **Sound:** optional, default-off, opt-in only — a single soft tick for criticals and a soft positive tone for completions. Never required; respect a global mute.
- **Restraint rules:** celebrations ≤600ms, never block input, never fire on routine data refresh, max one celebratory element on screen at a time, all gated by `prefers-reduced-motion`.

## Why pick this

Highest engagement and the best fit for Apex's **directive/approval loop** — it makes issuing and tracking agentic actions genuinely satisfying and reinforces human-in-the-loop by framing changes as "orders," not instant writes. Risk: requires the most motion/QA discipline to avoid feeling gimmicky to executive users; the mitigations above (rarity, brevity, data-truth, opt-in sound) are mandatory, not optional.
