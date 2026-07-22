"use client";
import { useQuery } from "@/lib/hooks";
import { getScorecard } from "@/lib/bff";
import { CardContainer, KPICard, Gauge, Skeleton, ErrorState, StatusPill } from "@/components/primitives";
import { AlertWire, Alert } from "@/components/directive";

export default function ScorecardPage() {
  const { data, loading, error, reload } = useQuery(["scorecard"], getScorecard);

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[1fr_320px]">
      {/* HUD ribbon */}
      <div className="lg:col-span-2">
        <div className="flex flex-wrap items-center gap-4 rounded-lg border border-line bg-surface px-4 py-2.5 text-[12.5px]">
          <span className="num text-fg-2">Q2 · MTD</span>
          <span className="text-fg-muted">Fifth Third + RV validation accounts</span>
          <div className="ml-auto flex gap-3.5 text-fg-2">
            {data?.streak.map((s) => (
              <span key={s.label}>
                {s.label} <b className="num text-fg">{s.value}</b>
              </span>
            ))}
          </div>
        </div>
      </div>

      {/* Left: gauge + KPIs + campaigns */}
      <div className="flex flex-col gap-4">
        {error ? (
          <ErrorState message="Couldn't load the scorecard." onRetry={reload} />
        ) : (
          <>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-[200px_1fr]">
              <CardContainer>
                {loading ? <Skeleton className="mx-auto h-36 w-36 rounded-full" /> : <Gauge pct={data!.goalPct} label="Funded-account goal" />}
              </CardContainer>
              <div className="grid grid-cols-2 gap-3">
                {loading
                  ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[104px]" />)
                  : data!.kpis.map((k) => (
                      <KPICard
                        key={k.id}
                        label={k.label}
                        value={k.value}
                        delta={k.delta}
                        deltaDir={k.deltaDir}
                        spark={k.spark}
                        targetMet={k.targetMet}
                        invertDelta={k.invertDelta}
                      />
                    ))}
              </div>
            </div>

            <CardContainer title="Campaign performance" subtitle="Top campaigns by ROAS">
              {loading ? (
                <Skeleton className="h-40" />
              ) : (
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-left text-[11px] uppercase tracking-[0.5px] text-fg-2">
                      <th className="py-2 font-medium">Campaign</th>
                      <th className="py-2 font-medium">Spend</th>
                      <th className="py-2 font-medium">ROAS</th>
                    </tr>
                  </thead>
                  <tbody>
                    {data!.campaigns.map((c) => (
                      <tr key={c.name} className="border-t border-line">
                        <td className="py-2.5 text-fg">{c.name}</td>
                        <td className="num py-2.5 text-fg-2">{c.spend}</td>
                        <td className="py-2.5">
                          <StatusPill tone={c.status === "ok" ? "positive" : c.status === "warn" ? "warning" : "critical"}>
                            <span className="num">{c.roas}</span>
                          </StatusPill>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </CardContainer>
          </>
        )}
      </div>

      {/* Right: alert wire */}
      <div>
        {loading ? (
          <CardContainer title="Alert wire"><Skeleton className="h-48" /></CardContainer>
        ) : (
          <AlertWire>
            {data?.alerts.map((a) => (
              <li key={a.id}>
                <Alert title={a.title} meta={a.meta} tone={a.tone} />
              </li>
            ))}
          </AlertWire>
        )}
      </div>
    </div>
  );
}
