"use client";
import { useQuery } from "@/lib/hooks";
import { getFunnel } from "@/lib/bff-extended";
import { CardContainer, Skeleton, ErrorState, StatusPill } from "@/components/primitives";
import { DataTable } from "@/components/charts";

export default function FunnelPage() {
  const { data, loading, error, reload } = useQuery(["funnel"], getFunnel);
  if (error) return <ErrorState message="Couldn't load the funnel." onRetry={reload} />;

  return (
    <div className="flex flex-col gap-4">
      <CardContainer title="Acquisition Funnel" subtitle="Brand UOI → Active — width shows relative conversion, red shows drop-off">
        {loading ? (
          <Skeleton className="h-44" />
        ) : (
          <div className="flex flex-col gap-2">
            {data!.stages.map((s, i) => {
              const max = data!.stages[0].value;
              const pct = (s.value / max) * 100;
              const prev = i > 0 ? data!.stages[i - 1].value : s.value;
              const drop = i > 0 ? Math.round((1 - s.value / prev) * 100) : 0;
              return (
                <div key={s.name} className="flex items-center gap-3">
                  <div className="w-28 text-right text-[12px] text-fg-2">{s.name}</div>
                  <div className="relative h-8 flex-1 rounded-md bg-elevated">
                    <div className="flex h-full items-center rounded-md bg-signal px-2 text-[11px] font-semibold text-accent-ink" style={{ width: `${pct}%` }}>
                      <span className="num">{s.value.toLocaleString()}</span>
                    </div>
                  </div>
                  <div className="w-16 text-[11px]">
                    {i > 0 && <span className="num text-critical">−{drop}%</span>}
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </CardContainer>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CardContainer title="Drop-off Analysis" subtitle="Dollar impact of friction per stage">
          {loading ? <Skeleton className="h-40" /> : (
            <DataTable
              columns={[
                { key: "from", label: "From" },
                { key: "to", label: "To" },
                { key: "lostPct", label: "Lost", render: (r) => <span className="num text-critical">{r.lostPct}%</span> },
                { key: "lostDollars", label: "$ Impact", num: true },
              ]}
              rows={data!.dropoff}
            />
          )}
        </CardContainer>
        <CardContainer title="Abandonment Recovery Tracker" subtitle="Automated Kamino sequences by window">
          {loading ? <Skeleton className="h-40" /> : (
            <DataTable
              columns={[
                { key: "window", label: "Window" },
                { key: "sequence", label: "Sequence" },
                { key: "recovered", label: "Recovered", num: true },
                { key: "status", label: "Status", render: (r) => <StatusPill tone={r.status === "active" ? "positive" : "muted"}>{r.status}</StatusPill> },
              ]}
              rows={data!.recovery}
            />
          )}
        </CardContainer>
      </div>
    </div>
  );
}
