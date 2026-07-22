"use client";
import { useQuery } from "@/lib/hooks";
import { getProductOps } from "@/lib/bff-extended";
import { CardContainer, Skeleton, ErrorState, StatusPill } from "@/components/primitives";
import { BarChart } from "@/components/charts";
import { Alert, AlertWire } from "@/components/directive";

export default function ProductPage() {
  const { data, loading, error, reload } = useQuery(["product-ops"], getProductOps);
  if (error) return <ErrorState message="Couldn't load Product & Ops." onRetry={reload} />;

  return (
    <div className="flex flex-col gap-4">
      <CardContainer title="Product Pipeline" subtitle="Initiatives by development stage">
        {loading ? <Skeleton className="h-40" /> : (
          <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
            {data!.pipeline.map((col) => (
              <div key={col.stage} className="rounded-md border border-line bg-raised p-3">
                <div className="mb-2 text-[11px] uppercase tracking-[0.06em] text-fg-2">{col.stage}</div>
                <div className="flex flex-col gap-2">
                  {col.items.map((it) => (
                    <div key={it.name} className="rounded border border-line bg-surface px-2.5 py-2 text-[12.5px] text-fg">
                      {it.name}
                      <div className="mt-0.5 text-[10px] text-fg-muted">{it.status}</div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </CardContainer>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CardContainer title="Transformation Roadmap" subtitle="Three-wave delivery">
          {loading ? <Skeleton className="h-40" /> : (
            <div className="flex flex-col gap-3">
              {data!.roadmap.map((w, i) => (
                <div key={w.wave} className="flex gap-3">
                  <div className="flex h-6 w-6 flex-none items-center justify-center rounded-pill bg-accent text-[11px] font-bold text-accent-ink">{i + 1}</div>
                  <div>
                    <div className="text-[13px] font-semibold text-fg">{w.wave}</div>
                    <div className="text-[11.5px] text-fg-2">{w.milestones.join(" · ")}</div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContainer>

        <CardContainer title="Team Resource Utilization">
          {loading ? <Skeleton className="h-40" /> : <BarChart data={data!.capacity.map((c) => ({ label: c.team, value: c.util }))} />}
        </CardContainer>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CardContainer title="System Health">
          {loading ? <Skeleton className="h-28" /> : (
            <div className="flex flex-wrap gap-2">
              {data!.health.map((h) => (
                <StatusPill key={h.system} tone={h.status === "ok" ? "positive" : h.status === "warn" ? "warning" : "critical"}>
                  {h.system} · {h.status}
                </StatusPill>
              ))}
            </div>
          )}
        </CardContainer>
        {!loading && (
          <AlertWire title="Competitive intel">
            {data!.intel.map((it) => (
              <li key={it.title}><Alert title={it.title} meta={it.meta} tone="info" /></li>
            ))}
          </AlertWire>
        )}
      </div>
    </div>
  );
}
