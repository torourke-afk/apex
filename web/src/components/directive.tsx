"use client";
import { ReactNode } from "react";

/* ── AlertWire + Alert ─────────────────────────────────────── */
export type AlertTone = "critical" | "warning" | "info";
export function Alert({ title, meta, tone }: { title: string; meta: string; tone: AlertTone }) {
  const border = {
    critical: "border-l-critical",
    warning: "border-l-warning",
    info: "border-l-line-strong",
  }[tone];
  const bg = tone === "critical" ? "bg-[color-mix(in_oklab,var(--color-critical)_10%,var(--color-bg-surface))]" : "bg-raised";
  return (
    <div className={`mb-2 rounded-r-md border-l-[3px] ${border} ${bg} px-3 py-2 animate-rise-in`}>
      <div className="text-[12.5px] text-fg">{title}</div>
      <div className="num mt-0.5 text-[11px] text-fg-muted">{meta}</div>
    </div>
  );
}
export function AlertWire({ children, title = "Alert wire" }: { children: ReactNode; title?: string }) {
  return (
    <div className="rounded-lg border border-line bg-surface p-4 shadow-elev-1" role="region" aria-label={title}>
      <h2 className="mb-2.5 text-xs font-medium uppercase tracking-[0.06em] text-fg-2">{title}</h2>
      <ul aria-live="polite" className="m-0 list-none p-0">{children}</ul>
    </div>
  );
}

/* ── MissionTracker ────────────────────────────────────────── */
export function MissionTracker({ steps, current }: { steps: string[]; current: number }) {
  return (
    <div>
      <div className="flex gap-1.5">
        {steps.map((_, i) => (
          <span key={i} className={`h-1.5 flex-1 rounded-pill ${i < current ? "bg-signal" : "bg-elevated"}`} />
        ))}
      </div>
      <div className="mt-1.5 flex gap-1.5 text-[10px]">
        {steps.map((s, i) => (
          <span key={s} className={`flex-1 ${i < current ? "text-fg" : "text-fg-muted"}`}>{s}</span>
        ))}
      </div>
    </div>
  );
}

/* ── DiffView (approval-queue before/after) ────────────────── */
export function DiffView({
  before,
  after,
}: {
  before: { label: string; value: string }[];
  after: { label: string; value: string }[];
}) {
  return (
    <div className="mt-3 grid grid-cols-2 gap-2.5">
      <DiffCol heading="Current (live)" tone="critical" rows={before} />
      <DiffCol heading="Proposed" tone="positive" rows={after} />
    </div>
  );
}
function DiffCol({ heading, tone, rows }: { heading: string; tone: "critical" | "positive"; rows: { label: string; value: string }[] }) {
  const border = tone === "critical"
    ? "border-[color-mix(in_oklab,var(--color-critical)_40%,transparent)]"
    : "border-[color-mix(in_oklab,var(--color-positive)_40%,transparent)]";
  const head = tone === "critical" ? "text-critical" : "text-positive";
  return (
    <div className={`rounded-md border ${border} p-2.5`}>
      <div className={`mb-1.5 text-[10.5px] uppercase tracking-[0.5px] ${head}`}>{heading}</div>
      {rows.map((r) => (
        <div key={r.label} className="num flex justify-between py-0.5 font-mono text-[12px] text-fg">
          <span className="text-fg-2">{r.label}</span>
          <span>{r.value}</span>
        </div>
      ))}
    </div>
  );
}
