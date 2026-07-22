import { useState, useRef, useEffect } from "react";
import { Card, SectionHeader, Pill, DataGuard, SkeletonCard, Skeleton, ChartTooltip, DMAMap } from "../ui";
import type { DMAMapDatum } from "../ui";
import { useSpendOverview, useSpendPacing, useChannelAllocation, useReallocations, useSpendDMA } from "../api/hooks";
import type { DMASpend } from "../api/hooks";
import { useShell } from "../shell/ShellProvider";

/** Map surface channel names → filter option names */
const CH_MAP: Record<string, string> = {
  "SEM / Paid Search": "SEM / Paid Search",
  "Brand Media": "Brand TV / OTT",
  "Social": "Social Media",
  "Direct Mail": "Direct Mail",
  "Partnerships": "Affiliate / Partner",
};

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/* Mock pacing data removed — BFF provides live data via useSpendPacing */

const STATUS_STYLES: Record<string, string> = {
  APPROVED: "text-positive bg-[rgba(79,216,155,.14)]",
  PENDING: "text-warning bg-[rgba(242,177,76,.14)]",
  REVIEW: "text-cyan bg-[var(--cyan-hover)]",
};

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function KpiCards() {
  const { filters } = useShell();
  const spendOverview = useSpendOverview(filters);

  return (
    <DataGuard
      {...spendOverview}
      skeleton={
        <section className="grid grid-cols-2 lg:grid-cols-4 gap-[14px]">
          {Array.from({ length: 4 }, (_, i) => (
            <SkeletonCard key={i} />
          ))}
        </section>
      }
    >
      {(data) => {
        const cards = data.cards ?? [];
        return (
          <section className="grid grid-cols-2 lg:grid-cols-4 gap-[14px] animate-rise">
            {cards.map((c, i) => {
              const isPace = c.label.toUpperCase().includes("PACE");
              return (
                <Card
                  key={c.label}
                  accent={isPace}
                  glow={isPace}
                  className="flex flex-col p-5 animate-rise"
                  style={{ animationDelay: `${i * 0.05}s` }}
                >
                  <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
                    {c.label.toUpperCase()}
                  </span>
                  <div className="text-[30px] font-semibold tracking-[-0.02em] mt-2">
                    {c.value}
                  </div>
                  {c.delta && (
                    <span
                      className={`font-mono text-[11px] font-medium mt-1 ${
                        c.delta_color === "positive" ? "text-positive" : "text-warning"
                      }`}
                    >
                      {c.delta}
                    </span>
                  )}
                </Card>
              );
            })}
          </section>
        );
      }}
    </DataGuard>
  );
}

/** Polyline that draws itself in from left to right on mount. */
function AnimatedPolyline({ points, stroke, strokeWidth, strokeDasharray, ...rest }: {
  points: string; stroke: string; strokeWidth: number; strokeDasharray?: string;
  [k: string]: unknown;
}) {
  const ref = useRef<SVGPolylineElement>(null);
  const [len, setLen] = useState(0);

  useEffect(() => {
    if (ref.current) setLen(ref.current.getTotalLength());
  }, [points]);

  return (
    <polyline
      ref={ref}
      points={points}
      fill="none"
      stroke={stroke}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeDasharray={strokeDasharray ?? (len || 2000).toString()}
      strokeDashoffset={len || 2000}
      style={{
        animation: len ? `drawIn 1s ease forwards` : undefined,
        ...(rest.style as object ?? {}),
      }}
      {...(rest.style ? {} : rest)}
    />
  );
}

function PacingChartInner({ plan, actual }: { plan: number[]; actual: number[] }) {
  const [hover, setHover] = useState<{ idx: number; x: number; y: number } | null>(null);

  // SVG viewBox dimensions
  const W = 600;
  const H = 260;
  const PAD = { top: 24, right: 20, bottom: 36, left: 48 };
  const plotW = W - PAD.left - PAD.right;
  const plotH = H - PAD.top - PAD.bottom;
  const maxY = 40; // $40M ceiling
  const MONTH_NAMES = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  const months = ["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"];

  const x = (i: number) => PAD.left + (i / 12) * plotW;
  const y = (v: number) => PAD.top + plotH - (v / maxY) * plotH;

  const planPoints = plan.map((v, i) => `${x(i)},${y(v)}`).join(" ");
  const actualPoints = actual.map((v, i) => `${x(i)},${y(v)}`).join(" ");

  // Gradient fill under actual line
  const fillPath = [
    `M ${x(0)},${y(0)}`,
    ...actual.map((v, i) => `L ${x(i)},${y(v)}`),
    `L ${x(actual.length - 1)},${y(0)}`,
    "Z",
  ].join(" ");

  return (
    <>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="w-full mt-3"
        style={{ minHeight: 200 }}
        role="img"
        aria-label="Budget pacing chart comparing actual spend against planned allocation over time"
      >
        <title>Budget Pacing</title>
        <defs>
          <linearGradient id="actualFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--cyan)" stopOpacity="0.22" />
            <stop offset="100%" stopColor="var(--cyan)" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Y-axis grid lines + labels */}
        {[0, 10, 20, 30, 40].map((v) => (
          <g key={v}>
            <line
              x1={PAD.left}
              y1={y(v)}
              x2={W - PAD.right}
              y2={y(v)}
              stroke="var(--line)"
              strokeWidth={1}
            />
            <text
              x={PAD.left - 8}
              y={y(v) + 3}
              textAnchor="end"
              className="font-mono"
              style={{ fontSize: 9, fill: "var(--text3)" }}
            >
              ${v}M
            </text>
          </g>
        ))}

        {/* X-axis labels */}
        {months.map((m, i) => (
          <text
            key={m + i}
            x={x(i + 0.5)}
            y={H - 8}
            textAnchor="middle"
            className="font-mono"
            style={{ fontSize: 9, fill: "var(--text3)" }}
          >
            {m}
          </text>
        ))}

        {/* Gradient fill under actual — fades in */}
        <path d={fillPath} fill="url(#actualFill)" style={{ opacity: 0, animation: "fadeIn 0.8s ease 0.6s forwards" }} />

        {/* Plan line (dashed) — draws in */}
        <AnimatedPolyline
          points={planPoints}
          stroke="var(--text3)"
          strokeWidth={1.5}
          strokeDasharray="6 4"
        />

        {/* Actual line — draws in */}
        <AnimatedPolyline
          points={actualPoints}
          stroke="var(--cyan)"
          strokeWidth={2}
          style={{ filter: "drop-shadow(0 0 5px var(--cyan-glow))" }}
        />

        {/* Actual data point dots with hover hit areas */}
        {actual.map((v, i) => {
          const isHovered = hover?.idx === i;
          return (
            <g key={`dot-${i}`}>
              {/* Invisible larger hit area */}
              <circle
                cx={x(i)}
                cy={y(v)}
                r={14}
                fill="transparent"
                onMouseEnter={() => setHover({ idx: i, x: x(i), y: y(v) })}
                onMouseLeave={() => setHover(null)}
                style={{ cursor: "crosshair" }}
              />
              {/* Visible dot */}
              <circle
                cx={x(i)}
                cy={y(v)}
                r={isHovered ? 6 : 4}
                fill="var(--cyan)"
                style={{
                  filter: "drop-shadow(0 0 6px var(--cyan-glow))",
                  transition: "r 0.15s ease",
                  pointerEvents: "none",
                }}
              />
            </g>
          );
        })}

        {/* Hover crosshair */}
        {hover && (
          <line
            x1={hover.x}
            y1={PAD.top}
            x2={hover.x}
            y2={PAD.top + plotH}
            stroke="var(--text3)"
            strokeWidth="1"
            strokeDasharray="3 3"
            strokeOpacity="0.5"
            style={{ pointerEvents: "none" }}
          />
        )}

        {/* Tooltip */}
        <ChartTooltip
          x={hover?.x ?? 0}
          y={hover?.y ?? 0}
          visible={hover !== null}
          viewBoxWidth={W}
          viewBoxHeight={H}
        >
          {hover && (
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <div style={{ fontWeight: 600, color: "var(--text2)", marginBottom: 2 }}>
                {MONTH_NAMES[hover.idx] ?? `M${hover.idx}`}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                <span style={{ color: "var(--cyan)" }}>Actual</span>
                <span style={{ fontWeight: 600 }}>${actual[hover.idx]?.toFixed(1)}M</span>
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                <span style={{ color: "var(--text3)" }}>Plan</span>
                <span style={{ fontWeight: 600 }}>${plan[hover.idx]?.toFixed(1)}M</span>
              </div>
              {plan[hover.idx] != null && actual[hover.idx] != null && (
                <div style={{
                  display: "flex", justifyContent: "space-between", gap: 16,
                  borderTop: "1px solid var(--line)", paddingTop: 3, marginTop: 1,
                }}>
                  <span style={{ color: "var(--text3)" }}>Variance</span>
                  <span style={{
                    fontWeight: 600,
                    color: actual[hover.idx] >= plan[hover.idx] ? "var(--green)" : "var(--amber)",
                  }}>
                    {actual[hover.idx] >= plan[hover.idx] ? "+" : ""}
                    {(actual[hover.idx] - plan[hover.idx]).toFixed(1)}M
                  </span>
                </div>
              )}
            </div>
          )}
        </ChartTooltip>
      </svg>

      {/* Legend */}
      <div className="flex items-center gap-5 mt-2">
        <div className="flex items-center gap-2">
          <div className="w-4 h-[2px] rounded bg-cyan" />
          <span className="font-mono text-[9px] text-fg3">ACTUAL</span>
        </div>
        <div className="flex items-center gap-2">
          <div
            className="w-4 h-[2px] rounded"
            style={{ background: "var(--text3)", borderTop: "1px dashed var(--text3)" }}
          />
          <span className="font-mono text-[9px] text-fg3">PLAN</span>
        </div>
      </div>
    </>
  );
}

function PacingChart() {
  const { filters } = useShell();
  const pacing = useSpendPacing(filters);

  return (
    <Card
      className="flex flex-col p-5 animate-rise"
      style={{ animationDelay: "0.1s" }}
    >
      <SectionHeader title="Budget Pacing" meta="YTD CUMULATIVE" />
      <DataGuard
        {...pacing}
        skeleton={<Skeleton rows={6} className="mt-3" />}
      >
        {(data) => {
          const plan = data.plan?.length ? data.plan : [];
          const actual = data.actual?.length ? data.actual : [];
          if (!plan.length || !actual.length) return null;
          return <PacingChartInner plan={plan} actual={actual} />;
        }}
      </DataGuard>
    </Card>
  );
}

function ChannelAllocation() {
  const { filters } = useShell();
  const allocQuery = useChannelAllocation(filters);

  return (
    <Card
      className="flex flex-col p-5 animate-rise"
      style={{ animationDelay: "0.15s" }}
    >
      <SectionHeader title="Channel Allocation" meta="% OF TOTAL" />
      <DataGuard
        {...allocQuery}
        skeleton={<Skeleton rows={5} className="mt-4" />}
        emptyHeadline="No allocation data"
        emptyBody="Channel allocation data is not available for the selected filters."
      >
        {(data) => {
          const allChannels = data.channels;
          const filtered = filters.channels.length === 0
            ? allChannels
            : allChannels.filter((ch) => filters.channels.includes(CH_MAP[ch.name] ?? ch.name));

          return (
            <div className="flex flex-col gap-[14px] mt-4">
              {filtered.map((ch) => {
                const amt = ch.amount >= 1_000_000
                  ? `$${(ch.amount / 1_000_000).toFixed(1)}M`
                  : `$${(ch.amount / 1_000).toFixed(0)}K`;
                return (
                  <div key={ch.name} className="flex flex-col gap-[5px]">
                    <div className="flex items-center justify-between">
                      <span className="text-[12px] font-medium text-fg">{ch.name}</span>
                      <span className="font-mono text-[11px] text-fg2">{amt}</span>
                    </div>
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-[6px] rounded-[4px] bg-line overflow-hidden">
                        <div
                          className="h-full rounded-[4px] bg-cyan"
                          style={{
                            width: `${ch.pct}%`,
                            opacity: 0.5 + (ch.pct / 100) * 0.5,
                          }}
                        />
                      </div>
                      <span className="font-mono text-[10px] text-fg3 w-[28px] text-right">
                        {ch.pct}%
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          );
        }}
      </DataGuard>
    </Card>
  );
}

function ReallocationLedger() {
  const { filters } = useShell();
  const reallocQuery = useReallocations(filters);

  return (
    <DataGuard
      {...reallocQuery}
      skeleton={<Skeleton rows={5} className="rounded-card border border-line bg-panel p-5" />}
      emptyHeadline="No reallocation data"
      emptyBody="Reallocation ledger data is not available."
    >
      {(data) => (
        <section
          className="rounded-card border border-line bg-panel overflow-hidden animate-rise"
          style={{ animationDelay: "0.2s" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-[18px] py-[15px] border-b border-line">
            <SectionHeader title="Next-Best-Dollar Reallocation Ledger" accent="cyan" />
            <Pill variant="cyan">{data.moves.length} MOVES</Pill>
          </div>

          {/* Column headers */}
          <div className="overflow-x-auto">
          <div className="grid grid-cols-[1.4fr_2fr_.7fr_.7fr_.7fr] gap-2 px-[18px] py-[9px] border-b border-line font-mono text-[9px] tracking-[.1em] text-fg3 min-w-[600px]">
            <span>FROM → TO</span>
            <span>RATIONALE</span>
            <span className="text-right">DELTA</span>
            <span className="text-right">{"Δ"} ROAS</span>
            <span className="text-right">STATUS</span>
          </div>

          {/* Rows */}
          {data.moves.map((row) => {
            const moveName = `${row.from_channel} → ${row.to_channel}`;
            const deltaStr = row.delta >= 1_000_000
              ? `+$${(row.delta / 1_000_000).toFixed(1)}M`
              : `+$${(row.delta / 1_000).toFixed(0)}K`;
            return (
              <div
                key={moveName}
                className="grid grid-cols-[1.4fr_2fr_.7fr_.7fr_.7fr] gap-2 items-center px-[18px] py-3 border-b border-line hover:bg-panel2 transition-colors min-w-[600px]"
              >
                <span className="text-[12px] font-medium text-fg">{moveName}</span>
                <span className="text-[12px] text-fg2">{row.rationale}</span>
                <span className="font-mono text-[11px] text-positive text-right">
                  {deltaStr}
                </span>
                <span className="font-mono text-[11px] text-positive text-right">
                  +{row.roas_impact}×
                </span>
                <div className="flex justify-end">
                  <span
                    className={`inline-block font-mono text-[9px] tracking-[.06em] px-2 py-[3px] rounded-[5px] ${STATUS_STYLES[row.status] ?? "text-fg3 bg-[rgba(164,173,191,.14)]"}`}
                  >
                    {row.status}
                  </span>
                </div>
              </div>
            );
          })}
          </div>
        </section>
      )}
    </DataGuard>
  );
}

/* ------------------------------------------------------------------ */
/*  DMA Choropleth Map                                                 */
/* ------------------------------------------------------------------ */

function toDMAMapData(rows: DMASpend[], metric: "spend" | "cpihh"): DMAMapDatum[] {
  return rows
    .filter((r) => r.dma_code)               // only markets the BFF could geocode
    .map((r) => ({
      dma: r.dma,
      code: r.dma_code!,
      value: metric === "spend" ? r.spend : r.cpihh,
      spend: r.spend,
      cpihh: r.cpihh,
      cx: r.cx,
      cy: r.cy,
      r: r.r,
    }));
}

function DMAGeoSection() {
  const { filters } = useShell();
  const dmaQuery = useSpendDMA(filters);
  const [metric, setMetric] = useState<"spend" | "cpihh">("spend");

  return (
    <Card className="flex flex-col p-5 animate-rise" style={{ animationDelay: "0.25s" }}>
      <div className="flex items-center justify-between">
        <SectionHeader title="DMA Market Map" meta="CLIENT FOOTPRINT" />
        <div className="flex items-center gap-1 bg-[var(--panel2)] rounded-[8px] p-[3px]">
          <button
            className={`font-mono text-[9px] tracking-[.08em] px-2.5 py-1 rounded-[6px] transition-colors ${
              metric === "spend"
                ? "bg-[var(--cyan-active)] text-cyan"
                : "text-fg3 hover:text-fg2"
            }`}
            onClick={() => setMetric("spend")}
            aria-label="Show spend metric"
          >
            SPEND
          </button>
          <button
            className={`font-mono text-[9px] tracking-[.08em] px-2.5 py-1 rounded-[6px] transition-colors ${
              metric === "cpihh"
                ? "bg-[var(--cyan-active)] text-cyan"
                : "text-fg3 hover:text-fg2"
            }`}
            onClick={() => setMetric("cpihh")}
            aria-label="Show CPIHH metric"
          >
            CPIHH
          </button>
        </div>
      </div>

      <DataGuard
        {...dmaQuery}
        skeleton={<Skeleton rows={8} className="mt-3" />}
        emptyHeadline="No DMA data"
        emptyBody="DMA market data is not available for the selected filters."
      >
        {(dmaData) => {
          const mapData = toDMAMapData(dmaData, metric);
          return (
            <>
              <DMAMap data={mapData} metric={metric} className="mt-3" />

              {/* Compact DMA table below the map */}
              <div className="mt-4 overflow-x-auto">
                <div className="grid grid-cols-[1.5fr_0.8fr_0.8fr_0.6fr] gap-2 px-1 py-[6px] border-b border-line font-mono text-[9px] tracking-[.1em] text-fg3 min-w-[400px]">
                  <span>MARKET</span>
                  <span className="text-right">SPEND</span>
                  <span className="text-right">CPIHH</span>
                  <span className="text-right">TIER</span>
                </div>
                {dmaData.map((row) => {
                  const isGeocoded = !!row.dma_code;
                  return (
                    <div
                      key={row.dma}
                      className={`grid grid-cols-[1.5fr_0.8fr_0.8fr_0.6fr] gap-2 items-center px-1 py-2 border-b border-line hover:bg-panel2 transition-colors min-w-[400px] ${
                        isGeocoded ? "" : "opacity-60"
                      }`}
                    >
                      <span className="text-[12px] font-medium text-fg">{row.dma}</span>
                      <span className="font-mono text-[11px] text-fg2 text-right">
                        {row.spend >= 1_000_000
                          ? `$${(row.spend / 1_000_000).toFixed(2)}M`
                          : `$${(row.spend / 1_000).toFixed(0)}K`}
                      </span>
                      <span className="font-mono text-[11px] text-fg2 text-right">
                        ${row.cpihh}
                      </span>
                      <span className="font-mono text-[10px] text-fg3 text-right">
                        T{row.tier}
                      </span>
                    </div>
                  );
                })}
              </div>
            </>
          );
        }}
      </DataGuard>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Spend component                                               */
/* ------------------------------------------------------------------ */

export function Spend() {
  return (
    <div className="flex flex-col gap-4">
      {/* ===== 1. KPI CARDS ===== */}
      <KpiCards />

      {/* ===== 2. PACING + ALLOCATION ===== */}
      <div className="grid gap-4 grid-cols-1 lg:grid-cols-[1.6fr_1fr]">
        <PacingChart />
        <ChannelAllocation />
      </div>

      {/* ===== 3. DMA MARKET MAP ===== */}
      <DMAGeoSection />

      {/* ===== 4. REALLOCATION LEDGER ===== */}
      <ReallocationLedger />
    </div>
  );
}
