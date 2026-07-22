import { Card, SectionHeader, Pill, DataGuard, SkeletonTable, SkeletonCard } from "../ui";
import { useProductPerformance, useTestingVelocity } from "../api/hooks";
import type { ConvFunnel } from "../api/hooks";
import { useShell } from "../shell/ShellProvider";

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function FunnelCard({ funnel, delay }: { funnel: ConvFunnel; delay: number }) {
  return (
    <Card className="flex flex-col p-5 animate-rise" style={{ animationDelay: `${delay}s` }}>
      <div className="flex items-center justify-between mb-4">
        <span className="text-[13px] font-semibold">{funnel.name}</span>
        <Pill variant="cyan">{funnel.stages[funnel.stages.length - 1].volume} FUNDED</Pill>
      </div>

      <div className="flex flex-col gap-3">
        {funnel.stages.map((stage) => (
          <div key={stage.label} className="flex flex-col gap-1.5">
            <div className="flex items-center justify-between">
              <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
                {stage.label.toUpperCase()}
              </span>
              <span className="font-mono text-[11px] font-medium text-fg">
                {stage.volume}
              </span>
            </div>
            <div className="w-full h-[5px] rounded-[5px] bg-line overflow-hidden">
              <div
                className="h-full rounded-[5px] bg-cyan transition-all duration-500"
                style={{
                  width: `${stage.pct}%`,
                  opacity: stage.pct === 100 ? 1 : 0.5 + (stage.pct / 200),
                }}
              />
            </div>
            <span className="font-mono text-[9px] text-fg3">{stage.pct}%</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

function TestingVelocityStrip({ velocity }: { velocity: { tests_run: number; won: number; win_rate: number; avg_lift_pct: number; avg_duration_days: number; top_winning_test: string } }) {
  const stats = [
    { label: "TESTS RUN", value: String(velocity.tests_run) },
    { label: "WON", value: String(velocity.won) },
    { label: "WIN RATE", value: `${velocity.win_rate}%` },
    { label: "AVG LIFT", value: `${velocity.avg_lift_pct}%` },
    { label: "AVG DURATION", value: `${velocity.avg_duration_days}d` },
  ];
  return (
    <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.28s" }}>
      <SectionHeader title="Testing Velocity" meta={`TOP TEST: ${velocity.top_winning_test}`} />
      <div className="grid grid-cols-5 gap-4 mt-3">
        {stats.map((s) => (
          <div key={s.label} className="flex flex-col">
            <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">{s.label}</span>
            <span className="text-[22px] font-semibold tracking-[-0.02em] mt-1">{s.value}</span>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Product component                                             */
/* ------------------------------------------------------------------ */

export function Product() {
  const { filters } = useShell();
  const perfQuery = useProductPerformance(filters);
  const velocityQuery = useTestingVelocity(filters);

  return (
    <div className="flex flex-col gap-4">
      {/* ===== Product Performance + Conversion Funnels (single BFF call) ===== */}
      <DataGuard
        {...perfQuery}
        skeleton={<SkeletonTable cols={5} rows={5} />}
        emptyHeadline="No product data"
        emptyBody="Product performance data is not available yet."
      >
        {(perfData) => (
          <>
            {/* ===== Product Line Performance Table ===== */}
            <section
              className="rounded-card border border-line bg-panel overflow-hidden animate-rise"
              style={{ animationDelay: "0.05s" }}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-[18px] py-[15px] border-b border-line">
                <SectionHeader title="Product Line Performance" accent="cyan" />
                <span className="font-mono text-[9.5px] tracking-[.1em] text-fg3">
                  QUARTER TO DATE
                </span>
              </div>

              {/* Column headers */}
              <div className="grid grid-cols-[1.5fr_90px_90px_90px_90px] gap-2 px-[18px] py-[9px] border-b border-line font-mono text-[9px] tracking-[.1em] text-fg3">
                <span>PRODUCT</span>
                <span className="text-right">FUNDED</span>
                <span className="text-right">CPIHH</span>
                <span className="text-right">LTV</span>
                <span className="text-right">MARGIN</span>
              </div>

              {/* Rows */}
              {perfData.products.map((p) => (
                <div
                  key={p.name}
                  className="grid grid-cols-[1.5fr_90px_90px_90px_90px] gap-2 items-center px-[18px] py-3 border-b border-line hover:bg-panel2 transition-colors"
                >
                  <span className="text-[13px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">
                    {p.name}
                  </span>
                  <span className="font-mono text-[12px] text-fg text-right">
                    {p.funded.toLocaleString()}
                  </span>
                  <span className="font-mono text-[12px] text-fg text-right">
                    ${p.cpihh}
                  </span>
                  <span className="font-mono text-[12px] text-fg text-right">
                    ${p.ltv.toLocaleString()}
                  </span>
                  <span className={`font-mono text-[12px] font-medium text-right ${p.margin_status === "positive" ? "text-positive" : "text-warning"}`}>
                    {Math.round(p.margin * 100)}%
                  </span>
                </div>
              ))}
            </section>

            {/* ===== Conversion Funnel Cards ===== */}
            <div className="flex items-center gap-2.5 mt-1">
              <SectionHeader title="Conversion Funnels" accent="cyan" />
            </div>

            <div className="grid grid-cols-[repeat(auto-fit,minmax(300px,1fr))] gap-4">
              {perfData.conv_funnels.map((funnel, i) => (
                <FunnelCard key={funnel.name} funnel={funnel} delay={0.15 + i * 0.06} />
              ))}
            </div>
          </>
        )}
      </DataGuard>

      {/* ===== Testing Velocity (from BFF) ===== */}
      <DataGuard
        {...velocityQuery}
        skeleton={<SkeletonCard />}
        emptyHeadline="No testing data"
        emptyBody="A/B testing velocity data is not available yet."
      >
        {(velocity) => <TestingVelocityStrip velocity={velocity} />}
      </DataGuard>
    </div>
  );
}
