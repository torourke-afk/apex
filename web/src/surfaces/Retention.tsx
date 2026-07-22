import { useState, useRef, useEffect } from "react";
import { Card, SectionHeader, DataGuard, SkeletonCard, SkeletonTable, ChartTooltip } from "../ui";
import { useRetentionCurves, useRetentionKPIs, useRetentionLTV } from "../api/hooks";
import type { RetentionKPI, LtvPoint } from "../api/hooks";
import { useShell } from "../shell/ShellProvider";

/* ------------------------------------------------------------------ */
/*  Static labels                                                      */
/* ------------------------------------------------------------------ */

const MOB_HEADERS = ["MOB1", "MOB2", "MOB3", "MOB4", "MOB5", "MOB6", "MOB7", "MOB8"];

/** SVG path that draws itself in from left to right on mount. */
function AnimatedPath({ d, stroke, strokeWidth, duration = 0.8 }: {
  d: string; stroke: string; strokeWidth: number; duration?: number;
}) {
  const ref = useRef<SVGPathElement>(null);
  const [len, setLen] = useState(0);

  useEffect(() => {
    if (ref.current) setLen(ref.current.getTotalLength());
  }, [d]);

  return (
    <path
      ref={ref}
      d={d}
      fill="none"
      stroke={stroke}
      strokeWidth={strokeWidth}
      strokeLinecap="round"
      strokeLinejoin="round"
      strokeDasharray={len || 1000}
      strokeDashoffset={len || 1000}
      style={{
        animation: len ? `drawIn ${duration}s ease forwards` : undefined,
      }}
    />
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

interface CohortRow {
  cohort: string;
  vals: (number | null)[];
}

function KpiRow() {
  const { filters } = useShell();
  const retentionKpis = useRetentionKPIs(filters);

  return (
    <DataGuard
      {...retentionKpis}
      skeleton={
        <div className="grid grid-cols-4 gap-3">
          {Array.from({ length: 4 }, (_, i) => (
            <SkeletonCard key={i} />
          ))}
        </div>
      }
      emptyHeadline="No retention KPIs"
      emptyBody="Retention KPI data is not yet available."
    >
      {(kpiData) => (
        <div className="grid grid-cols-4 gap-3">
          {kpiData.kpis.map((kpi: RetentionKPI, i: number) => (
            <Card
              key={kpi.label}
              className="flex flex-col p-4 animate-rise"
              style={{ animationDelay: `${0.05 + i * 0.05}s` }}
            >
              <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
                {kpi.label}
              </span>
              <div className="flex items-baseline gap-[3px] mt-[10px]">
                <span className="text-[28px] font-semibold tracking-[-0.02em]">
                  {kpi.value}
                </span>
                {kpi.value_suffix && (
                  <span className="text-[16px] text-fg2 font-medium">{kpi.value_suffix}</span>
                )}
              </div>
              <span className={`font-mono text-[10px] mt-[5px] ${kpi.color}`}>
                {kpi.delta}
              </span>
            </Card>
          ))}
        </div>
      )}
    </DataGuard>
  );
}

function CohortHeatmap({ cohortData }: { cohortData: CohortRow[] }) {
  return (
    <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.15s" }}>
      <SectionHeader title="Cohort Retention" meta="MOB1 – MOB8 · % RETAINED" />

      <div className="mt-4 overflow-x-auto">
        {/* Header row */}
        <div className="grid grid-cols-[60px_repeat(8,1fr)] gap-[3px] mb-[3px]">
          <div /> {/* empty corner */}
          {MOB_HEADERS.map((h) => (
            <div
              key={h}
              className="text-center font-mono text-[9px] tracking-[.1em] text-fg3 py-1.5"
            >
              {h}
            </div>
          ))}
        </div>

        {/* Data rows */}
        {cohortData.map((row) => (
          <div
            key={row.cohort}
            className="grid grid-cols-[60px_repeat(8,1fr)] gap-[3px] mb-[3px]"
          >
            {/* Row label */}
            <div className="flex items-center font-mono text-[9.5px] tracking-[.08em] text-fg2 pl-1">
              {row.cohort}
            </div>

            {/* Cells */}
            {row.vals.map((val, ci) => {
              if (val === null) {
                return (
                  <div
                    key={ci}
                    className="rounded-[6px] h-[36px]"
                    style={{ background: "var(--panel2)" }}
                  />
                );
              }
              // Scale opacity: 60% at 65, 100% at 100
              const opacity = 0.12 + (val / 100) * 0.35;
              return (
                <div
                  key={ci}
                  className="flex items-center justify-center rounded-[6px] h-[36px] font-mono text-[11px] font-medium transition-colors"
                  style={{
                    background: `color-mix(in srgb, var(--cyan) ${(opacity * 100).toFixed(0)}%, transparent)`,
                    color: val >= 85 ? "var(--cyanInk)" : "var(--text)",
                  }}
                >
                  {val}
                </div>
              );
            })}
          </div>
        ))}
      </div>
    </Card>
  );
}

function LtvAccrualChart({
  points,
  cpihh,
  breakeven_mob,
}: {
  points: LtvPoint[];
  cpihh: number;
  breakeven_mob: number;
}) {
  const [hover, setHover] = useState<{ idx: number; x: number; y: number } | null>(null);

  const W = 380;
  const H = 260;
  const pad = { t: 20, r: 20, b: 36, l: 50 };
  const cw = W - pad.l - pad.r;
  const ch = H - pad.t - pad.b;

  const maxMo = Math.max(...points.map((p) => p.mo), 12);
  const maxLtv = Math.max(...points.map((p) => p.ltv)) * 1.1 || 4500;

  function toX(mo: number) {
    return pad.l + (mo / maxMo) * cw;
  }
  function toY(ltv: number) {
    return pad.t + ch - (ltv / maxLtv) * ch;
  }

  // Build line path
  const linePath = points
    .map((p, i) => {
      const x = toX(p.mo);
      const y = toY(p.ltv);
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  // Build area path (closed at bottom)
  const lastPt = points[points.length - 1];
  const areaPath = lastPt
    ? linePath +
      ` L${toX(lastPt.mo).toFixed(1)},${(pad.t + ch).toFixed(1)}` +
      ` L${toX(points[0].mo).toFixed(1)},${(pad.t + ch).toFixed(1)} Z`
    : "";

  // CPIHH threshold line
  const cpY = toY(cpihh);

  // Breakeven marker
  const bePt = points.find((p) => p.mo === breakeven_mob);
  const beX = toX(breakeven_mob);
  const beY = toY(bePt?.ltv ?? cpihh);

  // Y-axis ticks — derive from maxLtv
  const tickStep = maxLtv > 8000 ? 2000 : 1000;
  const yTicks: number[] = [];
  for (let t = 0; t <= maxLtv; t += tickStep) {
    yTicks.push(t);
  }

  // Endpoint
  const endPt = lastPt ?? { mo: 12, ltv: 0 };

  const hoveredPt = hover !== null ? points[hover.idx] : null;

  return (
    <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.2s" }}>
      <SectionHeader title="Cumulative LTV Accrual" meta="$ PER COHORT" />
      <svg
        width="100%"
        viewBox={`0 0 ${W} ${H}`}
        className="mt-3"
        style={{ overflow: "visible" }}
        role="img"
        aria-label="Cumulative lifetime value accrual chart showing dollar value per cohort over months"
      >
        <title>Cumulative LTV Accrual</title>
        <defs>
          <linearGradient id="ltv-fill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="var(--green)" stopOpacity="0.25" />
            <stop offset="100%" stopColor="var(--green)" stopOpacity="0.02" />
          </linearGradient>
        </defs>

        {/* Y grid */}
        {yTicks.map((t) => {
          const y = toY(t);
          return (
            <g key={t}>
              <line
                x1={pad.l}
                y1={y}
                x2={W - pad.r}
                y2={y}
                stroke="var(--line)"
                strokeWidth="1"
              />
              <text
                x={pad.l - 8}
                y={y + 3}
                textAnchor="end"
                className="font-mono"
                style={{ fontSize: 9, fill: "var(--text3)" }}
              >
                ${(t / 1000).toFixed(t === 0 ? 0 : 1)}K
              </text>
            </g>
          );
        })}

        {/* X axis */}
        <line
          x1={pad.l}
          y1={pad.t + ch}
          x2={W - pad.r}
          y2={pad.t + ch}
          stroke="var(--line2)"
          strokeWidth="1"
        />
        {/* X labels */}
        {[0, 3, 6, 9, 12].filter((mo) => mo <= maxMo).map((mo) => (
          <text
            key={mo}
            x={toX(mo)}
            y={H - 6}
            textAnchor="middle"
            className="font-mono"
            style={{ fontSize: 9, fill: "var(--text3)", letterSpacing: "0.06em" }}
          >
            M{mo}
          </text>
        ))}

        {/* CPIHH threshold line */}
        <line
          x1={pad.l}
          y1={cpY}
          x2={W - pad.r}
          y2={cpY}
          stroke="var(--red)"
          strokeWidth="1"
          strokeDasharray="5 4"
          opacity="0.7"
        />
        <text
          x={W - pad.r}
          y={cpY - 6}
          textAnchor="end"
          className="font-mono"
          style={{ fontSize: 8, fill: "var(--red)", letterSpacing: "0.06em" }}
        >
          CPIHH ${cpihh}
        </text>

        {/* Area fill — fades in */}
        {areaPath && (
          <path
            d={areaPath}
            fill="url(#ltv-fill)"
            style={{ opacity: 0, animation: "fadeIn 0.8s ease 0.4s forwards" }}
          />
        )}

        {/* Line — draws in via strokeDashoffset */}
        {linePath && <AnimatedPath d={linePath} stroke="var(--green)" strokeWidth={2} duration={1} />}

        {/* Breakeven marker */}
        <line
          x1={beX}
          y1={pad.t}
          x2={beX}
          y2={pad.t + ch}
          stroke="var(--cyan)"
          strokeWidth="1"
          strokeDasharray="3 3"
          opacity="0.5"
        />
        <circle
          cx={beX}
          cy={beY}
          r="5"
          fill="var(--cyan)"
          style={{ filter: "drop-shadow(0 0 6px var(--cyan-glow))" }}
        />
        <text
          x={beX}
          y={pad.t - 6}
          textAnchor="middle"
          className="font-mono"
          style={{ fontSize: 8, fill: "var(--cyan)", letterSpacing: "0.06em" }}
        >
          BREAKEVEN MOB{breakeven_mob}
        </text>

        {/* Interactive data point hit areas + visible dots */}
        {points.map((p, i) => {
          const px = toX(p.mo);
          const py = toY(p.ltv);
          const isHovered = hover?.idx === i;
          const isEndpoint = p.mo === endPt.mo;
          return (
            <g key={`ltv-pt-${i}`}>
              {/* Invisible larger hit area */}
              <circle
                cx={px}
                cy={py}
                r={14}
                fill="transparent"
                onMouseEnter={() => setHover({ idx: i, x: px, y: py })}
                onMouseLeave={() => setHover(null)}
                style={{ cursor: "crosshair" }}
              />
              {/* Glow ring on hover */}
              {isHovered && (
                <circle
                  cx={px}
                  cy={py}
                  r={10}
                  fill="none"
                  stroke="var(--green)"
                  strokeWidth="1.5"
                  opacity="0.4"
                  style={{ pointerEvents: "none" }}
                />
              )}
              {/* Visible dot */}
              <circle
                cx={px}
                cy={py}
                r={isHovered ? 6 : isEndpoint ? 4 : 3}
                fill="var(--green)"
                style={{
                  filter: "drop-shadow(0 0 5px var(--green))",
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
            y1={pad.t}
            x2={hover.x}
            y2={pad.t + ch}
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
          {hoveredPt && (
            <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
              <div style={{ fontWeight: 600, color: "var(--text2)", marginBottom: 2 }}>
                M{hoveredPt.mo}
              </div>
              <div style={{ display: "flex", justifyContent: "space-between", gap: 16 }}>
                <span style={{ color: "var(--green)" }}>Cum. LTV</span>
                <span style={{ fontWeight: 600 }}>
                  ${hoveredPt.ltv.toLocaleString(undefined, { maximumFractionDigits: 0 })}
                </span>
              </div>
              <div style={{
                display: "flex", justifyContent: "space-between", gap: 16,
                borderTop: "1px solid var(--line)", paddingTop: 3, marginTop: 1,
              }}>
                <span style={{ color: "var(--text3)" }}>vs CPIHH</span>
                <span style={{
                  fontWeight: 600,
                  color: hoveredPt.ltv >= cpihh ? "var(--green)" : "var(--red)",
                }}>
                  {hoveredPt.ltv >= cpihh ? "Past breakeven" : `$${(cpihh - hoveredPt.ltv).toLocaleString(undefined, { maximumFractionDigits: 0 })} to go`}
                </span>
              </div>
            </div>
          )}
        </ChartTooltip>
      </svg>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Retention component                                           */
/* ------------------------------------------------------------------ */

export function Retention() {
  const { filters } = useShell();
  const retentionCurves = useRetentionCurves(filters);
  const retentionLtv = useRetentionLTV(filters);

  return (
    <div className="flex flex-col gap-4">
      {/* ===== Top row: KPI cards (from BFF) ===== */}
      <KpiRow />

      {/* ===== Middle row: Heatmap (from BFF) + LTV Chart (from BFF) ===== */}
      <DataGuard
        {...retentionCurves}
        skeleton={
          <div className="grid gap-4" style={{ gridTemplateColumns: "1.2fr 1fr" }}>
            <SkeletonTable cols={9} rows={8} />
            <SkeletonCard />
          </div>
        }
        emptyHeadline="No retention data"
        emptyBody="Cohort survival curves are not yet available."
      >
        {(curvesData) => {
          const cohortData: CohortRow[] = curvesData.map((curve) => ({
            cohort: curve.segment.toUpperCase().slice(0, 3),
            vals: Array.from({ length: 8 }, (_, i) =>
              i < curve.survival_probs.length ? Math.round(curve.survival_probs[i] * 100) : null
            ) as (number | null)[],
          }));

          return (
            <div className="grid gap-4" style={{ gridTemplateColumns: "1.2fr 1fr" }}>
              <CohortHeatmap cohortData={cohortData} />
              <DataGuard
                {...retentionLtv}
                skeleton={<SkeletonCard />}
                emptyHeadline="No LTV data"
                emptyBody="LTV accrual data is not yet available."
              >
                {(ltvData) => (
                  <LtvAccrualChart
                    points={ltvData.points}
                    cpihh={ltvData.cpihh}
                    breakeven_mob={ltvData.breakeven_mob}
                  />
                )}
              </DataGuard>
            </div>
          );
        }}
      </DataGuard>
    </div>
  );
}
