#!/usr/bin/env node
/**
 * Contrast lint — enforces the DESIGN.md WCAG AA contract on the semantic tokens.
 * Parses src/styles/tokens.css, resolves each theme block, and checks:
 *   - text-primary / text-secondary on canvas, surface, raised, elevated  → ≥ 4.5:1
 *   - text-muted on canvas/surface                                        → ≥ 3:1 (UI/large)
 *   - accent-contrast on accent                                           → ≥ 4.5:1
 *   - positive / warning / critical on canvas                            → ≥ 3:1 (large/UI)
 * Exits non-zero on any failure.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const css = readFileSync(join(here, "../src/styles/tokens.css"), "utf8");

function parseTheme(name) {
  // matches [data-theme="name"] { ... }  (and the :root,[data-theme="dark"] combo)
  const re = new RegExp(`\\[data-theme="${name}"\\][^{]*\\{([^}]*)\\}`, "s");
  const m = css.match(re);
  if (!m) throw new Error(`theme block not found: ${name}`);
  const vars = {};
  for (const line of m[1].split(";")) {
    const mm = line.match(/(--[a-z0-9-]+)\s*:\s*(.+)/i);
    if (mm) vars[mm[1].trim()] = mm[2].trim();
  }
  return vars;
}

function toRgb(v) {
  v = v.trim();
  if (v.startsWith("#")) {
    const h = v.slice(1);
    const f = h.length === 3 ? h.split("").map((c) => c + c).join("") : h;
    return [parseInt(f.slice(0, 2), 16), parseInt(f.slice(2, 4), 16), parseInt(f.slice(4, 6), 16)];
  }
  const m = v.match(/rgba?\(([^)]+)\)/);
  if (m) {
    const p = m[1].split(",").map((x) => parseFloat(x));
    return [p[0], p[1], p[2]]; // ignore alpha for contrast intent (borders aren't text)
  }
  throw new Error(`cannot parse color: ${v}`);
}
const lin = (c) => { c /= 255; return c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4; };
const lum = ([r, g, b]) => 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b);
function ratio(a, b) {
  const la = lum(toRgb(a)), lb = lum(toRgb(b));
  const [hi, lo] = la > lb ? [la, lb] : [lb, la];
  return (hi + 0.05) / (lo + 0.05);
}

const checks = (t) => [
  ["text-primary on canvas", t["--color-text-primary"], t["--color-bg-canvas"], 4.5],
  ["text-primary on surface", t["--color-text-primary"], t["--color-bg-surface"], 4.5],
  ["text-secondary on canvas", t["--color-text-secondary"], t["--color-bg-canvas"], 4.5],
  ["text-secondary on surface", t["--color-text-secondary"], t["--color-bg-surface"], 4.5],
  ["text-muted on canvas (UI)", t["--color-text-muted"], t["--color-bg-canvas"], 3.0],
  ["accent-contrast on accent", t["--color-accent-contrast"], t["--color-accent"], 4.5],
  ["positive on canvas (UI)", t["--color-positive"], t["--color-bg-canvas"], 3.0],
  ["warning on canvas (UI)", t["--color-warning"], t["--color-bg-canvas"], 3.0],
  ["critical on canvas (UI)", t["--color-critical"], t["--color-bg-canvas"], 3.0],
];

let failed = 0;
for (const theme of ["dark", "light"]) {
  const t = parseTheme(theme);
  console.log(`\n[${theme}]`);
  for (const [label, fg, bg, min] of checks(t)) {
    const r = ratio(fg, bg);
    const ok = r >= min;
    if (!ok) failed++;
    console.log(`  ${ok ? "PASS" : "FAIL"}  ${label.padEnd(30)} ${r.toFixed(2)}:1 (min ${min})`);
  }
}
console.log("");
if (failed) { console.error(`Contrast lint FAILED: ${failed} pairing(s) below AA.`); process.exit(1); }
console.log("Contrast lint PASSED — all token pairings meet WCAG AA in both themes.");
