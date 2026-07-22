"use client";
import { useState } from "react";
import { useQuery } from "@/lib/hooks";
import { getSpend } from "@/lib/bff-extended";
import { CardContainer, KPICard, Button, Skeleton, ErrorState, StatusPill } from "@/components/primitives";
import { BarChart, DataTable } from "@/components/charts";

export default function SpendPage() {
  const { data, loading, error, reload } = useQuery(["spend"], getSpend);
  const [mix, setMix] = useState<Record<string, number> | null>(null);
  const [committed, setCommitted] = useState(false);

  const mixVal = (ch: string, fallback: number) => mix?.[ch] ?? fallback;

  if (error) return <ErrorState message="Couldn't load spend allocation." onRetry={reload} />;

  return (
    <div className="flex flex-col gap-4">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {loading
          ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[104px]" />)
          : data!.kpis.map((k) => (
              <KPICard key={k.label} label={k.label} value={k.value} delta={k.delta} deltaDir={k.dir} invertDelta={k.invert} />
            ))}
      </div>

      <CardContainer title="Pacing & Burn by Channel" subtitle="Actual spend vs plan — filtered period">
        {loading ? <Skeleton className="h-40" /> : <BarChart data={data!.pacing.map((p) => ({ label: p.channel, value: p.actual, compare: p.plan }))} />}
      </CardContainer>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CardContainer title="DMA Spend Distribution" subtitle="By market tier">
          {loading ? (
            <Skeleton className="h-48" />
          ) : (
            <DataTable
              columns={[
                { key: "metro", label: "Metro" },
                { key: "tier", label: "Tier", render: (r) => <StatusPill tone={r.tier === 1 ? "positive" : r.tier === 2 ? "warning" : "muted"}>{`Tier ${r.tier}`}</StatusPill> },
                { key: "spend", label: "Spend", num: true },
                { key: "cac", label: "CAC", num: true },
              ]}
              rows={data!.geos}
            />
          )}
        </CardContainer>

        <CardContainer title="Channel Mix Control" subtitle="Allocation within approved bands">
          {loading ? (
            <Skeleton className="h-48" />
          ) : (
            <div className="flex flex-col gap-4">
              {data!.mix.map((m) => {
                const v = mixVal(m.channel, m.pct);
                return (
                  <label key={m.channel} className="block">
                    <div className="mb-1.5 flex items-center justify-between">
                      <span className="text-[12px] text-fg-2">{m.channel}</span>
                      <span className="num text-[12px] font-semibold text-fg">{v}% <span className="text-fg-muted">({m.min}–{m.max})</span></span>
                    </div>
                    <input
                      type="range" min={m.min} max={m.max} value={v}
                      onChange={(e) => { setMix((x) => ({ ...(x ?? {}), [m.channel]: parseInt(e.target.value) })); setCommitted(false); }}
                      className="w-full accent-[var(--color-accent)]" aria-label={`${m.channel} allocation`}
                    />
                  </label>
                );
              })}
              <div className="flex items-center gap-3">
                {committed ? (
                  <StatusPill tone="positive">✓ staged as directive — awaiting approval</StatusPill>
                ) : (
                  <>
                    <Button variant="primary" onClick={() => setCommitted(true)} disabled={!mix}>Commit plan</Button>
                    <span className="text-xs text-fg-muted">Routes to the approval queue — never an instant write.</span>
                  </>
                )}
              </div>
            </div>
          )}
        </CardContainer>
      </div>
    </div>
  );
}
