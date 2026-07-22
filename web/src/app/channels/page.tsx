"use client";
import { useState } from "react";
import { useQuery } from "@/lib/hooks";
import { getChannels } from "@/lib/bff-extended";
import { CardContainer, KPICard, Gauge, Skeleton, ErrorState, StatusPill } from "@/components/primitives";
import { BarChart, LineChart, DataTable } from "@/components/charts";

const TABS = ["Performance (SEM)", "Paid Social", "SEO", "AEO"] as const;

export default function ChannelsPage() {
  const { data, loading, error, reload } = useQuery(["channels"], getChannels);
  const [tab, setTab] = useState<(typeof TABS)[number]>("Performance (SEM)");

  if (error) return <ErrorState message="Couldn't load channels." onRetry={reload} />;

  return (
    <div className="flex flex-col gap-4">
      <div role="tablist" aria-label="Channel" className="flex gap-1.5">
        {TABS.map((t) => (
          <button
            key={t} role="tab" aria-selected={tab === t} onClick={() => setTab(t)}
            className={`rounded-pill border px-3.5 py-1.5 text-[13px] font-semibold transition-colors ${
              tab === t ? "border-accent bg-accent text-accent-ink" : "border-line bg-elevated text-fg-2 hover:text-fg"
            }`}
          >
            {t}
          </button>
        ))}
      </div>

      {loading ? (
        <Skeleton className="h-64" />
      ) : tab === "Performance (SEM)" ? (
        <>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
            {data!.sem.kpis.map((k) => <KPICard key={k.label} label={k.label} value={k.value} delta={k.delta} deltaDir={k.dir} invertDelta={k.invert} />)}
          </div>
          <CardContainer title="Google vs Microsoft" subtitle="Spend split by search engine">
            <BarChart data={data!.sem.engines.map((e) => ({ label: e.engine, value: e.spend }))} />
          </CardContainer>
        </>
      ) : tab === "Paid Social" ? (
        <CardContainer title="Platform Breakdown">
          <DataTable
            columns={[
              { key: "platform", label: "Platform" },
              { key: "spend", label: "Spend", num: true },
              { key: "roas", label: "ROAS", render: (r) => <StatusPill tone="positive"><span className="num">{r.roas}</span></StatusPill> },
            ]}
            rows={data!.social.platforms}
          />
        </CardContainer>
      ) : tab === "SEO" ? (
        <>
          <div className="grid grid-cols-3 gap-3">
            {data!.seo.kpis.map((k) => <KPICard key={k.label} label={k.label} value={k.value} delta={k.delta} deltaDir={k.dir} />)}
          </div>
          <CardContainer title="Keyword Rankings" subtitle="Position change vs prior period">
            <DataTable
              columns={[
                { key: "kw", label: "Keyword" },
                { key: "pos", label: "Position", num: true },
                { key: "change", label: "Change", render: (r) => (
                  <span className={`num ${r.change > 0 ? "text-positive" : r.change < 0 ? "text-critical" : "text-fg-muted"}`}>
                    {r.change > 0 ? `▲ ${r.change}` : r.change < 0 ? `▼ ${Math.abs(r.change)}` : "—"}
                  </span>
                ) },
              ]}
              rows={data!.seo.rankings}
            />
          </CardContainer>
        </>
      ) : (
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-[240px_1fr]">
          <CardContainer title="LLM Visibility Score" subtitle="AI-answer presence">
            <Gauge pct={data!.aeo.score} label="Visibility" />
            <div className="mt-3"><LineChart series={[{ data: data!.aeo.trend }]} height={80} /></div>
          </CardContainer>
          <CardContainer title="Competitive AEO Benchmark" subtitle="LLM Visibility vs tracked competitors">
            <BarChart data={data!.aeo.competitors.map((c) => ({ label: c.name, value: c.score }))} />
          </CardContainer>
        </div>
      )}
    </div>
  );
}
