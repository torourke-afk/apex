# Apex (web/) — UX Audit of Core Flows

**Auditor:** senior UX review · **Date:** June 24, 2026 · **Build:** vertical slice (Scorecard, Approvals/Directive, Simulator + shell), MSW-mocked, dark default.

**Method:** walked the real user paths end-to-end against the running build — (1) land on Scorecard → read status → triage an alert; (2) open Approvals → review a directive diff → approve → watch it execute; (3) open Simulator → set inputs → run → commit a scenario as a directive. Severity scale: **P0 blocks/derails the task · P1 real friction or risk · P2 polish.** Each finding has a concrete fix.

---

## Summary

The slice is coherent and the core happy paths work: the design system reads cleanly, the directive approval loop is legible, and the Simulator → commit → approval handoff is the strongest flow. The biggest gaps are **missing feedback and terminal states** (reject does nothing visible; no toasts; no audit surface), **weak wayfinding** (no labels on the icon rail, page title is the only "where am I"), and **error/empty paths that exist in primitives but aren't wired into every screen**. None are P0 for a demo; several are P1 before real users.

| # | Area | Severity | Issue (one line) |
|---|---|---|---|
| 1 | Approvals | **P1** | "Reject" gives no feedback — the card just vanishes silently |
| 2 | Global | **P1** | Icon-only nav rail has no visible labels; relies on title attr |
| 3 | Approvals | **P1** | No confirmation/undo on a high-impact approve; instant + irreversible-feeling |
| 4 | Simulator | **P1** | "Run" has no progress affordance beyond skeletons; long runs feel stalled |
| 5 | Scorecard | **P1** | Alert wire items aren't actionable — can't acknowledge or jump to the cause |
| 6 | Global | **P1** | No global error/empty handling if the BFF is down on first paint of stubs |
| 7 | Approvals | **P2** | Diff doesn't highlight *which* fields changed; eye must compare manually |
| 8 | Simulator | **P2** | Inputs have no "reset to defaults" or scenario save/name |
| 9 | Scorecard | **P2** | Hero gauge and KPI "target met" lack an accessible text equivalent of the win |
| 10 | Global | **P2** | No loading state on the agent console; submitting does nothing yet |
| 11 | Global | **P2** | Theme toggle label/icon don't announce state to screen readers |
| 12 | Approvals | **P2** | Mission tracker shows "step 3/5" with no way to see steps 1–2 history |

---

## Detailed findings

### 1. Reject is a dead end — no feedback (P1)
**Path:** Approvals → click **Reject**. The card disappears with no confirmation, no "rejected" state, no undo, and no entry anywhere. The user can't tell if it worked or how to recover. Approve at least animates to "executed"; reject just removes the item.
**Why it matters:** rejecting a proposed spend change is a real decision a user will second-guess. Silent removal erodes trust in an approval tool.
**Fix:** on reject, transition the card to a muted "Rejected · {reason}" terminal state (mirror the executed state), keep it in the list collapsed, and show a toast with **Undo** (5s). Capture an optional one-line reason; write it to the (future) audit log. Add the same `aria-live` announcement used for approve.

### 2. Icon-only nav rail has no readable labels (P1, a11y)
**Path:** any screen → left rail. Items are single glyphs (▣ ◧ ◈ …) with `title`/`aria-label` only. New users can't tell Spend from Channels without hovering each; `title` tooltips are slow and don't appear on touch/keyboard.
**Fix:** make the rail expandable (icon + label) with a persistent toggle, default expanded on first visit; or show labels on hover/focus as a flyout. At minimum, add a tooltip-on-focus (not just title) and an "active page" text indicator. Keep the collapsed 60px mode as an option, not the only mode.

### 3. High-impact approve feels instant and irreversible (P1)
**Path:** Approvals → **Approve** on a high-impact directive (pause a live campaign). One click → success sweep → executed. For a "human-in-the-loop" safety surface, a single unguarded click on a live-account change is too easy to fire by accident.
**Fix:** for `impact: "high"`, require a confirmation step — either a two-stage button ("Approve" → "Confirm pause") or a small confirm popover summarizing the live effect ("Pauses Brand·Broad, ~$840/day"). Keep low-impact one-click. Add a brief post-action **Undo** window before it's truly committed.

### 4. "Run simulation" lacks real progress feedback (P1)
**Path:** Simulator → **Run**. Button flips to "Running…" and result tiles skeleton, but there's no scan-line/progress and no time expectation. The spec calls for the Mission-Debrief "computing" sweep; right now a 600ms+ run reads as a possible hang on slower data.
**Fix:** add the spec's scan-line sweep over the results region while running, plus disable inputs during the run and show a subtle "modeling funnel…" caption. On completion, animate the headline (Funded Accounts / CPIHH) count-up so the result "lands."

### 5. Alerts aren't actionable (P1)
**Path:** Scorecard → Alert wire shows "ROAS breach — Brand·Broad" but you can't acknowledge it, mute it, or jump to the campaign/directive that fixes it. It's a read-only feed in a tool whose whole point is acting on signals.
**Fix:** each alert gets an overflow action: **Acknowledge** (removes with `aria-live` confirm) and **Investigate** (deep-links to the relevant campaign or pre-fills a directive in the agent console). Critical alerts should offer a one-click "review proposed fix" if a directive already exists.

### 6. No screen-level error/empty path on the stubs and first load (P1)
**Path:** if the BFF/mock errors on first paint, Scorecard handles it (ErrorState + retry) but the stub pages and the shell don't. A failed load on a real screen would show an empty card with no recovery.
**Fix:** wrap each route in a shared error boundary + a standard `ErrorState` with retry, and ensure every data region renders one of {loading, empty, error, populated}. Add a Next.js `error.tsx` and `loading.tsx` at the app level so no route can render blank.

### 7. Diff doesn't highlight changed fields (P2)
**Path:** Approvals → diff shows current vs proposed side by side, but unchanged and changed rows look identical; the user manually scans for what moved.
**Fix:** bold/recolor only the rows that differ, add a "Δ" marker and (where numeric) the delta (e.g., `daily_budget $300 → — (−$300)`). Dim unchanged rows.

### 8. Simulator inputs can't be reset or saved (P2)
**Path:** after dragging four sliders, there's no "reset to BD defaults" and no way to name/save a scenario for the Scenario Comparison the spec calls for.
**Fix:** add **Reset to defaults** and **Save scenario** (name + store), feeding a compare view. Show the active mode (BD/Client) as a labeled control, not just caption text.

### 9. The "win" moments aren't announced to assistive tech (P2, a11y)
**Path:** Scorecard gauge fills and a KPI shows "✓ target met"; Approvals plays a success sweep. These are purely visual — a screen-reader user gets nothing.
**Fix:** pair each celebration with a visually-hidden `aria-live="polite"` message ("Funded-account goal 78% to target" / "Directive approved and executed"). The sweep stays decorative; the meaning is announced.

### 10. Agent console is inert (P2)
**Path:** bottom console accepts text and shows tool chips, but submitting does nothing (no echo, no pending state, no "this will create a directive" affordance).
**Fix:** on submit, show a pending agent response state and, when a command implies an account change, surface "→ will be staged as a directive for approval" so the governance model is visible at the point of action. (Wire to the agent service later; stub the interaction now.)

### 11. Theme toggle doesn't announce state (P2, a11y)
**Fix:** the button already has a dynamic `aria-label` ("Switch to light mode") — good — but also reflect the current theme with `aria-pressed` or a visually-hidden "current: dark" so state, not just the action, is clear.

### 12. Mission tracker hides history (P2)
**Path:** Approvals card shows step 3/5 but the completed steps aren't inspectable (who built/submitted, when).
**Fix:** make completed segments hoverable/expandable to show the timestamp + actor, tying into the audit log.

---

## What's working (keep)
- The directive **diff + approve → execute** loop is the clearest flow; the consequence-feedback sweep is tasteful and not overdone.
- **Simulator → Commit as directive** correctly routes through approval instead of writing — the governance model is legible.
- Token system + theme toggle are clean; numerals use tabular mono throughout; focus ring is visible in both themes.
- Loading skeletons and the ErrorState/EmptyState primitives exist — they just need to be wired into every region (finding 6).

## Recommended fix order
1. **P1 feedback gaps first:** #1 (reject state + undo), #3 (confirm high-impact), #4 (run progress), #5 (actionable alerts).
2. **P1 wayfinding & resilience:** #2 (nav labels), #6 (error/empty everywhere).
3. **P2 polish:** #7–#12.
