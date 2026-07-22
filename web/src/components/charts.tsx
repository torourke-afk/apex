"use client";
import { ReactNode } from "react";
import {
  ResponsiveContainer, BarChart as RBarChart, Bar, LineChart as RLineChart, Line,
  XAxis, YAxis, Tooltip, CartesianGrid,
} from "recharts";

const C = {
  signal: "var(--color-signal)",
  elevated: "var(--color-bg-elevated)",
  positive: "var(--color-positive)",
  warning: "var(--color-warning)",
  line: "var(--color-border)",
  fg2: "var(--color-text-secondary)",
};

const tooltipStyle = {
  background: "var(--color-bg-elevated)",
  border: "1px solid var(--color-border)",
  borderRadius: 8,
  fontSize: 12,
  color: "var(--color-text-primary)",
};

/* ── BarChart (Recharts; paired bars when `compare` present) ───── */
export function BarChart({
  data,
  height = 150,
}: {
  data: { label: string; value: number; compare?: number }[];
  height?: number;
}) {
  const hasCompare = data.some((d) => d.compare != null);
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RBarChart data={data} margin={{ top: 8, right: 4, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={C.line} vertical={false} />
        <XAxis dataKey="label" tick={{ fill: C.fg2, fontSize: 10 }} axisLine={{ stroke: C.line }} tickLine={false} />
        <YAxis tick={{ fill: C.fg2, fontSize: 10 }} axisLine={false} tickLine={false} />
        <Tooltip contentStyle={tooltipStyle} cursor={{ fill: "var(--color-bg-raised)", opacity: 0.4 }} />
        <Bar dataKey="value" name="actual" fill={C.signal} radius={[3, 3, 0, 0]} />
        {hasCompare && <Bar dataKey="compare" name="plan/benchmark" fill={C.elevated} radius={[3, 3, 0, 0]} />}
      </RBarChart>
    </ResponsiveContainer>
  );
}

/* ── LineChart (Recharts; single/multi series) ─────────────────── */
export function LineChart({ series, height = 140 }: { series: { name?: string; data: number[] }[]; height?: number }) {
  const colors = [C.signal, C.positive, C.warning];
  const len = Math.max(...series.map((s) => s.data.length));
  const rows = Array.from({ length: len }, (_, i) => {
    const row: Record<string, number> = { i };
    series.forEach((s, si) => (row[`s${si}`] = s.data[i]));
    return row;
  });
  return (
    <ResponsiveContainer width="100%" height={height}>
      <RLineChart data={rows} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
        <CartesianGrid stroke={C.line} vertical={false} />
        <XAxis dataKey="i" hide />
        <YAxis tick={{ fill: C.fg2, fontSize: 10 }} axisLine={false} tickLine={false} width={32} />
        <Tooltip contentStyle={tooltipStyle} />
        {series.map((s, si) => (
          <Line key={si} type="monotone" dataKey={`s${si}`} name={s.name ?? `series ${si + 1}`} stroke={colors[si % colors.length]} strokeWidth={2} dot={false} />
        ))}
      </RLineChart>
    </ResponsiveContainer>
  );
}

/* ── ResponseCurveChart (Next-Best-Dollar: curve + waste-gap dot + optimal ring) ── */
export function ResponseCurveChart({
  k,
  sRef,
  currentSpend,
  optimalSpend,
  currentAccounts,
  optimalAccounts,
  maxSpend,
  t = 1,
}: {
  k: number; sRef: number; currentSpend: number; optimalSpend: number;
  currentAccounts: number; optimalAccounts: number; maxSpend: number; t?: number;
}) {
  const W = 260, H = 150, pad = 8;
  const acc = (s: number) => k * Math.log(1 + s / sRef);
  const maxAcc = acc(maxSpend) || 1;
  const x = (s: number) => pad + (s / maxSpend) * (W - 2 * pad);
  const y = (a: number) => H - pad - (a / maxAcc) * (H - 2 * pad);
  const curve = Array.from({ length: 40 }, (_, i) => {
    const s = (i / 39) * maxSpend;
    return `${x(s)},${y(acc(s))}`;
  }).join(" ");
  // dot animates from current toward optimal as t goes 0→1
  const dotSpend = currentSpend + (optimalSpend - currentSpend) * t;
  const dotAcc = currentAccounts + (optimalAccounts - currentAccounts) * t;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: H }} role="img" aria-label="response curve">
      <polyline points={curve} fill="none" stroke="var(--color-signal)" strokeWidth="1.5" opacity="0.85" />
      {/* optimal-spend ring */}
      <circle cx={x(optimalSpend)} cy={y(optimalAccounts)} r="5" fill="none" stroke="var(--color-positive)" strokeWidth="1.5" />
      {/* waste-gap connector (dashed) from dot up to its curve */}
      <line x1={x(dotSpend)} y1={y(dotAcc)} x2={x(dotSpend)} y2={y(acc(dotSpend))} stroke="var(--color-critical)" strokeWidth="1" strokeDasharray="3 3" opacity={1 - t} />
      {/* today's dot (below the curve = waste) */}
      <circle cx={x(dotSpend)} cy={y(dotAcc)} r="4" fill="var(--color-critical)" />
    </svg>
  );
}

/* ── DataTable (sortable-ish, conditional badges via render) ───── */
export function DataTable<T>({
  columns,
  rows,
}: {
  columns: { key: string; label: string; render?: (row: T) => ReactNode; num?: boolean }[];
  rows: T[];
}) {
  return (
    <table className="w-full text-sm">
      <thead>
        <tr className="text-left text-[11px] uppercase tracking-[0.5px] text-fg-2">
          {columns.map((c) => (
            <th key={c.key} className="py-2 font-medium">{c.label}</th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row, i) => (
          <tr key={i} className="border-t border-line">
            {columns.map((c) => (
              <td key={c.key} className={`py-2.5 ${c.num ? "num text-fg-2" : "text-fg"}`}>
                {c.render ? c.render(row) : String((row as Record<string, unknown>)[c.key] ?? "")}
              </td>
            ))}
          </tr>
        ))}
      </tbody>
    </table>
  );
}
