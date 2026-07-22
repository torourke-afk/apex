"use client";
import { useState } from "react";
import { useQuery } from "@/lib/hooks";
import { getRetention } from "@/lib/bff-extended";
import { CardContainer, KPICard, Skeleton, ErrorState } from "@/components/primitives";

export default function RetentionPage() {
  const { data, loading, error, reload } = useQuery(["retention"], getRetention);
  const [active, setActive] = useState<Record<string, boolean>>({ all: true, pfi: true, switchers: true });
  const [obs, setObs] = useState(6); // observation month (MOB)

  if (error) return <ErrorState message="Couldn't load retention." onRetry={reload} />;

  const colors = ["var(--color-signal)", "var(--color-positive)", "var(--color-warning)"];
  const W = 360, H = 180;

  return (
    <div className="flex flex-col gap-4">
      <CardContainer title="Segment Filters" subtitle="Select segments to overlay">
        {loading ? <Skeleton className="h-10" /> : (
          <div className="flex flex-wrap gap-2">
            {data!.segments.map((s) => (
              <button
                key={s.id} onClick={() => setActive((a) => ({ ...a, [s.id]: !a[s.id] }))}
                aria-pressed={active[s.id]}
                className={`rounded-pill border px-3 py-1.5 text-[12.5px] font-semibold transition-colors ${
                  active[s.id] ? "border-accent bg-accent text-accent-ink" : "border-line bg-elevated text-fg-2"
                }`}
              >{s.label}</button>
            ))}
          </div>
        )}
      </CardContainer>

      <CardContainer title="Survival Curve" subtitle={`Retention by month on book · observation: MOB ${obs}`}>
        {loading ? <Skeleton className="h-52" /> : (
          <>
            <svg viewBox={`0 0 ${W} ${H}`} className="w-full" style={{ height: H }} role="img" aria-label="survival curves">
              {data!.segments.filter((s) => active[s.id]).map((s, si) => {
                const pts = s.curve.map((v, i) => `${(i / (s.curve.length - 1)) * W},${H - (v / 100) * (H - 10) - 5}`).join(" ");
                return <polyline key={s.id} points={pts} fill="none" stroke={colors[si % colors.length]} strokeWidth="2" />;
              })}
              <line x1={(obs / 6) * W} y1="0" x2={(obs / 6) * W} y2={H} stroke="var(--color-text-muted)" strokeDasharray="4 4" />
            </svg>
            <label className="mt-3 block">
              <div className="mb-1.5 flex justify-between text-[12px] text-fg-2"><span>Observation date (MOB)</span><span className="num text-fg">{obs}</span></div>
              <input type="range" min={0} max={6} value={obs} onChange={(e) => setObs(parseInt(e.target.value))} className="w-full accent-[var(--color-accent)]" aria-label="Observation month" />
            </label>
          </>
        )}
      </CardContainer>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
        {loading ? Array.from({ length: 3 }).map((_, i) => <Skeleton key={i} className="h-[104px]" />)
          : data!.kpis.map((k) => (
              <KPICard key={k.segment} label={`${k.segment} · MOB6`} value={k.mob6} delta={k.decay} deltaDir="down" invertDelta />
            ))}
      </div>
    </div>
  );
}
