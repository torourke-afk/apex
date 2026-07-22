import { useState, useEffect } from "react";
import { Card, SectionHeader, Pill, DataGuard, SkeletonCard, ChartTooltip } from "../ui";
import { useFunnelStages, useFunnelSankey } from "../api/hooks";
import { useShell } from "../shell/ShellProvider";

/* ------------------------------------------------------------------ */
/*  Sankey diagram — SVG ribbon layout constants                       */
/* ------------------------------------------------------------------ */

const STAGE_X = [20, 190, 360, 530, 700];
const STAGE_W = 18;
const VB_W = 760;
const VB_H = 340;

/**
 * Builds a cubic-bezier ribbon path between two rectangles.
 */
function ribbon(
  x1: number,
  y1Top: number,
  y1Bot: number,
  x2: number,
  y2Top: number,
  y2Bot: number,
): string {
  const cx = (x1 + x2) / 2;
  return [
    `M ${x1},${y1Top}`,
    `C ${cx},${y1Top} ${cx},${y2Top} ${x2},${y2Top}`,
    `L ${x2},${y2Bot}`,
    `C ${cx},${y2Bot} ${cx},${y1Bot} ${x1},${y1Bot}`,
    "Z",
  ].join(" ");
}

/** Stage bar teal gradient — darker at top, lighter at bottom */
const STAGE_COLORS = [
  "var(--cyan)",
  "var(--cyan)",
  "var(--cyan)",
  "var(--cyan)",
];

function SankeyDiagramInner({ data }: { data: { channels: { name: string; label: string; pct: number; color: string }[]; stages: { label: string; volume?: string }[]; stage_factors: number[] } }) {
  const [hoveredChannel, setHoveredChannel] = useState<string | null>(null);
  const [revealed, setRevealed] = useState(false);
  useEffect(() => { const t = setTimeout(() => setRevealed(true), 80); return () => clearTimeout(t); }, []);

  const barH = VB_H - 100;
  const barTop = 56;

  const channels = data.channels;
  const stages = data.stages;
  const stageHeights = data.stage_factors.map((f) => f * barH);

  // Channel bars at stage 0
  let chY = barTop;
  const channelBars = channels.map((ch) => {
    const h = (ch.pct / 100) * barH;
    const top = chY;
    chY += h + 2;
    return { ...ch, top, h };
  });

  // Track ribbon midpoints for tooltip positioning
  const hoveredBar = hoveredChannel ? channelBars.find((c) => c.name === hoveredChannel) : null;
  const tooltipX = hoveredBar ? STAGE_X[0] + STAGE_W + (STAGE_X[1] - STAGE_X[0] - STAGE_W) / 2 : 0;
  const tooltipY = hoveredBar ? hoveredBar.top + hoveredBar.h / 2 : 0;

  // Compute stage-to-stage conversion rates for labels
  const convRates: string[] = [];
  for (let i = 1; i < data.stage_factors.length; i++) {
    const rate = data.stage_factors[i] / (data.stage_factors[i - 1] || 1) * 100;
    convRates.push(`${rate.toFixed(0)}%`);
  }

  return (
    <Card
      className="flex flex-col p-5 animate-rise"
      style={{ animationDelay: "0.05s" }}
    >
      <SectionHeader title="Acquisition Flow" meta="FULL-FUNNEL SANKEY" />

      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="w-full mt-3" style={{ minHeight: 260 }} role="img" aria-label="Acquisition funnel Sankey diagram showing flow from channel mix through application stages to approval">
        <title>Acquisition Funnel Flow</title>
        <defs>
          {channels.map((ch) => (
            <linearGradient key={ch.name} id={`grad-${ch.name}`} x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor={ch.color} stopOpacity="0.55" />
              <stop offset="100%" stopColor={ch.color} stopOpacity="0.12" />
            </linearGradient>
          ))}
          <linearGradient id="stage-bar-grad" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--cyan)" stopOpacity="0.5" />
            <stop offset="100%" stopColor="var(--cyan)" stopOpacity="0.15" />
          </linearGradient>
        </defs>

        {/* Stage column labels + volumes */}
        {stages.map((s, i) => (
          <g key={s.label}>
            <text
              x={STAGE_X[i] + STAGE_W / 2}
              y={20}
              textAnchor="middle"
              className="font-mono"
              style={{ fontSize: 8.5, fill: "var(--text3)", letterSpacing: "0.1em" }}
            >
              {s.label}
            </text>
            {s.volume && (
              <text
                x={STAGE_X[i] + STAGE_W / 2}
                y={34}
                textAnchor="middle"
                className="font-mono"
                style={{ fontSize: 11, fill: "var(--text)", fontWeight: 600 }}
              >
                {s.volume}
              </text>
            )}
          </g>
        ))}

        {/* Conversion rate labels between stages */}
        {convRates.map((rate, i) => {
          const midX = (STAGE_X[i + 1] + STAGE_X[i + 2]) / 2 + STAGE_W / 2;
          return (
            <text
              key={`conv-${i}`}
              x={midX}
              y={44}
              textAnchor="middle"
              className="font-mono"
              style={{ fontSize: 9, fill: "var(--cyan)", fontWeight: 500, opacity: 0.8 }}
            >
              {rate} →
            </text>
          );
        })}

        {/* Ribbons with entrance animation */}
        <g style={{
          opacity: revealed ? 1 : 0,
          transform: revealed ? "translateX(0)" : "translateX(-8px)",
          transition: "opacity 0.6s ease, transform 0.6s ease",
        }}>
          {channelBars.map((ch) => {
            const paths: React.ReactNode[] = [];
            let prevTop = ch.top;
            let prevH = ch.h;
            const isHovered = hoveredChannel === ch.name;
            const isDimmed = hoveredChannel !== null && !isHovered;

            for (let s = 1; s < stages.length; s++) {
              const nextBarH = s < stageHeights.length ? stageHeights[s] : stageHeights[stageHeights.length - 1];
              const sliceH = (ch.pct / 100) * nextBarH;
              const offsetAbove = channelBars
                .slice(0, channelBars.indexOf(ch))
                .reduce((sum, c) => sum + (c.pct / 100) * nextBarH + 1.5, 0);
              const nextTop = barTop + offsetAbove;

              paths.push(
                <path
                  key={`${ch.name}-${s}`}
                  d={ribbon(
                    STAGE_X[s - 1] + STAGE_W,
                    prevTop,
                    prevTop + prevH,
                    STAGE_X[s],
                    nextTop,
                    nextTop + sliceH,
                  )}
                  fill={`url(#grad-${ch.name})`}
                  stroke={ch.color}
                  strokeWidth={isHovered ? 1.2 : 0.4}
                  strokeOpacity={isHovered ? 0.7 : 0.2}
                  opacity={isDimmed ? 0.15 : 1}
                  style={{
                    transition: "opacity 0.25s ease, stroke-width 0.15s ease, stroke-opacity 0.15s ease",
                    transitionDelay: `${s * 0.06}s`,
                  }}
                />,
              );

              paths.push(
                <path
                  key={`hit-${ch.name}-${s}`}
                  d={ribbon(
                    STAGE_X[s - 1] + STAGE_W,
                    prevTop,
                    prevTop + prevH,
                    STAGE_X[s],
                    nextTop,
                    nextTop + sliceH,
                  )}
                  fill="transparent"
                  stroke="transparent"
                  strokeWidth="8"
                  onMouseEnter={() => setHoveredChannel(ch.name)}
                  onMouseLeave={() => setHoveredChannel(null)}
                  style={{ cursor: "crosshair" }}
                />,
              );

              prevTop = nextTop;
              prevH = sliceH;
            }
            return <g key={ch.name}>{paths}</g>;
          })}
        </g>

        {/* Stage bars */}
        {stages.map((_, i) => {
          if (i === 0) {
            return channelBars.map((ch) => {
              const isHovered = hoveredChannel === ch.name;
              const isDimmed = hoveredChannel !== null && !isHovered;
              return (
                <g key={`bar-${ch.name}`}>
                  <rect
                    x={STAGE_X[0]}
                    y={ch.top}
                    width={STAGE_W}
                    height={ch.h}
                    rx={3}
                    fill={ch.color}
                    fillOpacity={isDimmed ? 0.15 : 0.75}
                    style={{ transition: "fill-opacity 0.25s ease" }}
                    onMouseEnter={() => setHoveredChannel(ch.name)}
                    onMouseLeave={() => setHoveredChannel(null)}
                    cursor="crosshair"
                  />
                  <text
                    x={STAGE_X[0] - 5}
                    y={ch.top + ch.h / 2 + 3}
                    textAnchor="end"
                    className="font-mono"
                    style={{
                      fontSize: 8,
                      fill: ch.color,
                      opacity: isDimmed ? 0.25 : 1,
                      transition: "opacity 0.25s ease",
                      pointerEvents: "none",
                    }}
                  >
                    {ch.label}
                  </text>
                </g>
              );
            });
          }
          const h = i <= stageHeights.length ? stageHeights[i - 1] : stageHeights[stageHeights.length - 1];
          return (
            <rect
              key={`stage-${i}`}
              x={STAGE_X[i]}
              y={barTop}
              width={STAGE_W}
              height={h}
              rx={3}
              fill="url(#stage-bar-grad)"
            />
          );
        })}

        {/* Bottom: end-to-end conversion annotation */}
        {stages.length >= 2 && data.stage_factors.length > 0 && (
          <g>
            <line
              x1={STAGE_X[1] + STAGE_W / 2}
              y1={barTop + stageHeights[0] + 12}
              x2={STAGE_X[stages.length - 1] + STAGE_W / 2}
              y2={barTop + stageHeights[0] + 12}
              stroke="var(--text3)"
              strokeWidth={0.5}
              strokeDasharray="3,3"
              opacity={0.5}
            />
            <text
              x={(STAGE_X[1] + STAGE_X[stages.length - 1]) / 2 + STAGE_W / 2}
              y={barTop + stageHeights[0] + 24}
              textAnchor="middle"
              className="font-mono"
              style={{ fontSize: 9, fill: "var(--text3)" }}
            >
              E2E {(data.stage_factors[data.stage_factors.length - 1] * 100).toFixed(0)}%
            </text>
          </g>
        )}

        {/* Tooltip */}
        <ChartTooltip
          x={tooltipX}
          y={tooltipY}
          visible={hoveredChannel !== null}
          viewBoxWidth={VB_W}
          viewBoxHeight={VB_H}
        >
          {hoveredBar && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              <div style={{ fontWeight: 600, color: hoveredBar.color, marginBottom: 2, fontSize: 13 }}>
                {hoveredBar.name}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                <span style={{ color: "var(--text3)", fontSize: 11 }}>Channel share</span>
                <span style={{ fontWeight: 600, fontSize: 11 }}>{hoveredBar.pct.toFixed(1)}%</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                <span style={{ color: "var(--text3)", fontSize: 11 }}>Est. volume</span>
                <span style={{ fontWeight: 600, fontSize: 11 }}>
                  {stages[1]?.volume ? `~${Math.round(hoveredBar.pct / 100 * parseFloat(stages[1].volume.replace(/[KMk]/g, (m: string) => m === 'K' || m === 'k' ? '000' : '000000').replace(/[^0-9.]/g, '')))}` : "—"}
                </span>
              </div>
            </div>
          )}
        </ChartTooltip>
      </svg>
    </Card>
  );
}

function SankeyDiagram() {
  const { filters } = useShell();
  const sankeyQuery = useFunnelSankey(filters);

  return (
    <DataGuard
      {...sankeyQuery}
      skeleton={<SkeletonCard className="h-[300px]" />}
      emptyHeadline="No sankey data"
      emptyBody="Funnel sankey data is not yet available."
    >
      {(data) => <SankeyDiagramInner data={data} />}
    </DataGuard>
  );
}

/* ------------------------------------------------------------------ */
/*  Conversion Rate Cards                                              */
/* ------------------------------------------------------------------ */

function ConversionCardBar({ rate, bench, positive }: { rate: string; bench: string; positive: boolean }) {
  const [filled, setFilled] = useState(false);
  useEffect(() => { const t = setTimeout(() => setFilled(true), 200); return () => clearTimeout(t); }, []);
  const rateVal = Math.min(parseFloat(rate), 100);
  const benchVal = parseFloat(bench);

  return (
    <div className="mt-3 flex items-center gap-2">
      <div className="flex-1 h-[6px] rounded-[4px] bg-line overflow-hidden relative">
        <div
          className="absolute top-0 h-full w-[2px] bg-fg3 rounded z-10"
          style={{ left: `${benchVal}%` }}
          title={`Benchmark: ${bench}`}
        />
        <div
          className={`h-full rounded-[4px] ${positive ? "bg-cyan" : "bg-warning"}`}
          style={{
            width: filled ? `${rateVal}%` : "0%",
            transition: "width 0.8s cubic-bezier(0.22, 1, 0.36, 1)",
          }}
        />
      </div>
    </div>
  );
}

function ConversionCards() {
  const { filters } = useShell();
  const funnelStages = useFunnelStages(filters);

  return (
    <DataGuard
      {...funnelStages}
      skeleton={
        <div className="grid grid-cols-4 gap-[14px]">
          <SkeletonCard /><SkeletonCard /><SkeletonCard /><SkeletonCard />
        </div>
      }
      emptyHeadline="No funnel data"
      emptyBody="Funnel stages are not yet available."
    >
      {(stages) => {
        const r1 = (stages[1]?.volume ?? 0) / (stages[0]?.volume || 1) * 100;
        const b1 = stages[0]?.benchmark_rate ?? 30;
        const r2 = (stages[2]?.volume ?? 0) / (stages[1]?.volume || 1) * 100;
        const b2 = stages[1]?.benchmark_rate ?? 0.5;
        const r3 = (stages[3]?.volume ?? 0) / (stages[2]?.volume || 1) * 100;
        const b3 = stages[2]?.benchmark_rate ?? 65;
        const e2e = (stages[3]?.volume ?? 0) / (stages[0]?.volume || 1) * 100;
        const e2eBench = (b1 / 100) * (b2 / 100) * (b3 / 100) * 100;

        const mkDelta = (actual: number, bench: number) => {
          const diff = actual - bench;
          return { text: `${diff >= 0 ? "↑" : "↓"} ${Math.abs(diff).toFixed(1)}`, positive: diff >= 0 };
        };
        const d1 = mkDelta(r1, b1);
        const d2 = mkDelta(r2, b2);
        const d3 = mkDelta(r3, b3);
        const d4 = mkDelta(e2e, e2eBench);

        const cards = [
          { label: "APP START → ID VERIFY", rate: `${r1.toFixed(1)}%`, delta: d1.text, bench: `${b1.toFixed(1)}%`, positive: d1.positive },
          { label: "ID VERIFY → SUBMIT", rate: `${r2.toFixed(1)}%`, delta: d2.text, bench: `${b2.toFixed(1)}%`, positive: d2.positive },
          { label: "SUBMIT → APPROVED", rate: `${r3.toFixed(1)}%`, delta: d3.text, bench: `${b3.toFixed(1)}%`, positive: d3.positive },
          { label: "END-TO-END CVR", rate: `${e2e.toFixed(1)}%`, delta: d4.text, bench: `${e2eBench.toFixed(1)}%`, positive: d4.positive },
        ];

        return (
          <section className="grid grid-cols-4 gap-[14px] animate-rise" style={{ animationDelay: "0.12s" }}>
            {cards.map((c, i) => (
              <Card key={c.label} className="flex flex-col p-5" style={{ animationDelay: `${0.12 + i * 0.06}s` }}>
                <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
                  {c.label}
                </span>

                <div className="text-[28px] font-semibold tracking-[-0.02em] mt-2 font-mono tabular-nums">
                  {c.rate}
                </div>

                <div className="flex items-center gap-2 mt-1">
                  <span
                    className={`font-mono text-[11px] font-medium ${
                      c.positive ? "text-positive" : "text-warning"
                    }`}
                  >
                    {c.delta}
                  </span>
                  <span className="font-mono text-[9.5px] text-fg3">
                    vs bench {c.bench}
                  </span>
                </div>

                <ConversionCardBar rate={c.rate} bench={c.bench} positive={c.positive} />
              </Card>
            ))}
          </section>
        );
      }}
    </DataGuard>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Funnel component                                              */
/* ------------------------------------------------------------------ */

export function Funnel() {
  return (
    <div className="flex flex-col gap-4">
      {/* ===== 1. SANKEY FLOW ===== */}
      <SankeyDiagram />

      {/* ===== 2. CONVERSION RATE CARDS ===== */}
      <ConversionCards />
    </div>
  );
}
