# APE-28 Fix: Button Border-Radius (M-2 Blocker)

## Problem

`src/config/brand.py:335` uses `BORDER_RADIUS["sm"]` (4px) for primary buttons. The brand spec requires 8px for buttons, which is `BORDER_RADIUS["md"]`.

## Exact Change

**File:** `src/config/brand.py`, line 335

**Current:**
```css
border-radius: {BORDER_RADIUS["sm"]};
```

**Required:**
```css
border-radius: {BORDER_RADIUS["md"]};
```

This is the only button-specific border-radius that needs changing. Cards at line 310 correctly use `BORDER_RADIUS["lg"]` (12px). The spec is:
- Cards: 12px (`lg`) ✓ already correct
- Buttons: 8px (`md`) ← this fix

## Verification

Grep `src/config/brand.py` for `button` context lines and confirm primary button uses `BORDER_RADIUS["md"]`.
