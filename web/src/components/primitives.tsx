"use client";
import { ReactNode } from "react";
import { ResponsiveContainer, LineChart as RLineChart, Line } from "recharts";

/* ── CardContainer ─────────────────────────────────────────── */
export function CardContainer({
  title,
  subtitle,
  right,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  right?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section
      className={`rounded-lg border border-line bg-surface p-6 shadow-elev-1 ${className}`}
    >
      {(title || right) && (
        <header className="mb-4 flex items-start justify-between gap-3">
          <div>
            {title && <h2 className="text-sm font-semibold text-fg">{title}</h2>}
            {subtitle && <p className="mt-0.5 text-xs text-fg-2">{subtitle}</p>}
          </div>
          {right}
        </header>
      )}
      {children}
    </section>
  );
}

/* ── Sparkline (Recharts) ──────────────────────────────────── */
export function Sparkline({ data, className = "" }: { data: number[]; className?: string }) {
  if (!data.length) return null;
  const rows = data.map((v, i) => ({ i, v }));
  return (
    <div className={`h-7 w-24 ${className}`} aria-hidden>
      <ResponsiveContainer width="100%" height="100%">
        <RLineChart data={rows} margin={{ top: 2, right: 2, bottom: 2, left: 2 }}>
          <Line type="monotone" dataKey="v" stroke="var(--color-signal)" strokeWidth={1.5} dot={false} isAnimationActive={false} />
        </RLineChart>
      </ResponsiveContainer>
    </div>
  );
}

/* ── KPICard ───────────────────────────────────────────────── */
export function KPICard({
  label,
  value,
  delta,
  deltaDir = "up",
  spark,
  targetMet = false,
  invertDelta = false,
}: {
  label: string;
  value: string;
  delta?: string;
  deltaDir?: "up" | "down";
  spark?: number[];
  targetMet?: boolean;
  invertDelta?: boolean;
}) {
  // For metrics where lower is better (e.g. CPA/CPIHH), a "down" move is positive.
  const good = invertDelta ? deltaDir === "down" : deltaDir === "up";
  return (
    <div className="rounded-lg border border-line bg-surface p-4 shadow-elev-1 transition-shadow hover:shadow-elev-2">
      <div className="text-[10px] font-medium uppercase tracking-[0.06em] text-fg-2">{label}</div>
      <div className="num mt-1 text-2xl font-semibold text-fg">{value}</div>
      <div className="mt-1 flex items-center justify-between">
        {delta && (
          <span className={`text-[11.5px] ${good ? "text-positive" : "text-critical"}`}>
            {deltaDir === "up" ? "▲" : "▼"} {delta}
          </span>
        )}
        {spark && <Sparkline data={spark} />}
      </div>
      {targetMet && (
        <span className="mt-1.5 inline-flex items-center gap-1 rounded-pill border border-[color-mix(in_oklab,var(--color-positive)_40%,transparent)] bg-[color-mix(in_oklab,var(--color-positive)_12%,transparent)] px-2 py-0.5 text-[10px] text-positive">
          ✓ target met
        </span>
      )}
    </div>
  );
}

/* ── Gauge (radial, animates fill via conic-gradient) ──────── */
export function Gauge({ pct, label }: { pct: number; label: string }) {
  return (
    <div className="flex flex-col items-center justify-center">
      <div
        className="relative flex h-36 w-36 items-center justify-center rounded-full transition-[background] duration-700 ease-signal"
        style={{
          background: `conic-gradient(var(--color-signal) 0 ${pct}%, var(--color-bg-elevated) ${pct}% 100%)`,
        }}
        role="img"
        aria-label={`${label}: ${pct}% to target`}
      >
        <div className="absolute inset-[11px] rounded-full bg-surface" />
        <div className="relative text-center">
          <div className="num text-2xl font-bold text-fg">{pct}%</div>
          <div className="text-[9px] uppercase tracking-[0.12em] text-fg-muted">to target</div>
        </div>
      </div>
      <div className="mt-3 text-[11px] uppercase tracking-[0.07em] text-fg-2">{label}</div>
    </div>
  );
}

/* ── Button ────────────────────────────────────────────────── */
export function Button({
  children,
  variant = "primary",
  ...props
}: { variant?: "primary" | "ghost" | "danger" } & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  const base =
    "rounded-md px-3.5 py-2 text-[13px] font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed";
  const styles = {
    primary: "bg-accent text-accent-ink hover:opacity-90",
    ghost: "border border-line bg-elevated text-fg hover:border-line-strong",
    danger: "border border-[color-mix(in_oklab,var(--color-critical)_40%,transparent)] bg-transparent text-critical hover:bg-[color-mix(in_oklab,var(--color-critical)_10%,transparent)]",
  }[variant];
  return <button className={`${base} ${styles}`} {...props}>{children}</button>;
}

/* ── StatusPill / HealthPill ───────────────────────────────── */
export function StatusPill({ tone, children }: { tone: "positive" | "warning" | "critical" | "muted"; children: ReactNode }) {
  const map = {
    positive: "border-[color-mix(in_oklab,var(--color-positive)_40%,transparent)] bg-[color-mix(in_oklab,var(--color-positive)_12%,transparent)] text-positive",
    warning: "border-[color-mix(in_oklab,var(--color-warning)_40%,transparent)] bg-[color-mix(in_oklab,var(--color-warning)_12%,transparent)] text-warning",
    critical: "border-[color-mix(in_oklab,var(--color-critical)_40%,transparent)] bg-[color-mix(in_oklab,var(--color-critical)_12%,transparent)] text-critical",
    muted: "border-line bg-elevated text-fg-2",
  }[tone];
  return <span className={`inline-flex items-center gap-1 rounded-pill border px-2 py-0.5 text-[11px] ${map}`}>{children}</span>;
}

/* ── Skeleton / EmptyState / ErrorState ────────────────────── */
export function Skeleton({ className = "" }: { className?: string }) {
  return <div className={`skeleton rounded-md ${className}`} aria-hidden />;
}
export function EmptyState({ message, hint }: { message: string; hint?: string }) {
  return (
    <div className="flex flex-col items-center justify-center gap-1 rounded-lg border border-dashed border-line py-10 text-center">
      <p className="text-sm text-fg-2">{message}</p>
      {hint && <p className="text-xs text-fg-muted">{hint}</p>}
    </div>
  );
}
export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="flex flex-col items-center justify-center gap-2 rounded-lg border border-[color-mix(in_oklab,var(--color-critical)_30%,transparent)] py-8 text-center" role="alert">
      <p className="text-sm text-critical">{message}</p>
      {onRetry && <Button variant="ghost" onClick={onRetry}>Retry</Button>}
    </div>
  );
}
