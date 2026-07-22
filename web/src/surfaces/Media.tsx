import { useState, useRef, useEffect } from "react";
import { Card, SectionHeader, Sparkline, DataGuard, SkeletonTable, ChartTooltip } from "../ui";
import { useMediaChannels, useMediaSaturation, useMediaEfficiency } from "../api/hooks";
import type { SaturationCurve, EfficiencyBubble } from "../api/hooks";
import { useShell } from "../shell/ShellProvider";

/* ------------------------------------------------------------------ */
/*  Animated SVG path — draws in from left to right                    */
/* ------------------------------------------------------------------ */

function AnimatedPath({ d, stroke, strokeWidth, duration = 0.8, delay = 0 }: {
  d: string; stroke: string; strokeWidth: number; duration?: number; delay?: number;
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
        animation: len ? `drawIn ${duration}s ease ${delay}s forwards` : undefined,
      }}
    />
  );
}

/* ------------------------------------------------------------------ */
/*  Saturation Curves SVG                                              */
/* ------------------------------------------------------------------ */

function SaturationCurves({ curves }: { curves: SaturationCurve[] }) {
  const [hover, setHover] = useState<{ label: string; x: number; y: number; color: string; responseRate: number } | null>(null);

  const W = 380;
  const H = 220;
  const pad = { t: 20, r: 20, b: 36, l: 44 };
  const cw = W - pad.l - pad.r;
  const ch = H - pad.t - pad.b;

  function curvePath(k: number, maxY: number) {
    const pts: string[] = [];
    for (let i = 0; i <= 40; i++) {
      const t = i / 40;
      const x = pad.l + t * cw;
      const y = pad.t + ch - maxY * (1 - Math.exp(-k * t * 3)) * ch;
      pts.push(`${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`);
    }
    return pts.join(" ");
  }

  function dotPos(k: number, maxY: number, dotX: number) {
    const y = pad.t + ch - maxY * (1 - Math.exp(-k * dotX * 3)) * ch;
    return { x: pad.l + dotX * cw, y };
  }

  /** Compute response rate at the current dot position */
  function responseRate(k: number, maxY: number, dotX: number) {
    return maxY * (1 - Math.exp(-k * dotX * 3)) * 100;
  }

  // Grid lines
  const gridLines = [0.25, 0.5, 0.75, 1.0];

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      className="mt-3"
      style={{ overflow: "visible" }}
      role="img"
      aria-label="Saturation curves chart showing diminishing returns by channel"
    >
      <title>Channel Saturation Curves</title>
      {/* Y-axis grid */}
      {gridLines.map((g) => {
        const y = pad.t + ch - g * ch;
        return (
          <g key={g}>
            <line
              x1={pad.l} y1={y} x2={W - pad.r} y2={y}
              stroke="var(--line)" strokeWidth="1"
            />
            <text
              x={pad.l - 8} y={y + 3}
              textAnchor="end"
              className="font-mono"
              style={{ fontSize: 9, fill: "var(--text3)" }}
            >
              {Math.round(g * 100)}%
            </text>
          </g>
        );
      })}

      {/* X-axis */}
      <line
        x1={pad.l} y1={pad.t + ch} x2={W - pad.r} y2={pad.t + ch}
        stroke="var(--line2)" strokeWidth="1"
      />
      <text
        x={pad.l + cw / 2} y={H - 4}
        textAnchor="middle"
        className="font-mono"
        style={{ fontSize: 9, fill: "var(--text3)", letterSpacing: "0.1em" }}
      >
        SPEND INDEX
      </text>

      {/* Curves */}
      {curves.map((c, ci) => {
        const d = curvePath(c.k, c.max_y);
        const dot = dotPos(c.k, c.max_y, c.dot_x);
        const isHovered = hover?.label === c.label;
        const rate = responseRate(c.k, c.max_y, c.dot_x);
        return (
          <g key={c.label}>
            {/* Line — draws in with stagger, highlight on hover */}
            <AnimatedPath
              d={d}
              stroke={c.color}
              strokeWidth={isHovered ? 3 : 2}
              duration={0.8}
              delay={ci * 0.15}
            />
            {/* Invisible larger hit area for line */}
            <path
              d={d}
              fill="none"
              stroke="transparent"
              strokeWidth="14"
              strokeLinecap="round"
              onMouseEnter={() => setHover({ label: c.label, x: dot.x, y: dot.y, color: c.color, responseRate: rate })}
              onMouseLeave={() => setHover(null)}
              style={{ cursor: "crosshair" }}
            />
            {/* Current spend dot */}
            <circle
              cx={dot.x} cy={dot.y}
              r={isHovered ? 6 : 4}
              fill={c.color}
              style={{
                filter: `drop-shadow(0 0 5px ${c.color})`,
                transition: "r 0.15s ease",
                pointerEvents: "none",
              }}
            />
            {/* Label */}
            <text
              x={dot.x + 8} y={dot.y - 8}
              className="font-mono"
              style={{ fontSize: 9, fill: c.color, letterSpacing: "0.06em", pointerEvents: "none" }}
            >
              {c.label}
            </text>
          </g>
        );
      })}

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
            <div style={{ fontWeight: 600, color: hover.color, marginBottom: 1 }}>
              {hover.label}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 14 }}>
              <span style={{ color: "var(--text3)" }}>Response</span>
              <span style={{ fontWeight: 600 }}>{hover.responseRate.toFixed(1)}%</span>
            </div>
          </div>
        )}
      </ChartTooltip>
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Efficiency Frontier SVG                                            */
/* ------------------------------------------------------------------ */

function EfficiencyFrontier({
  bubbles,
  portfolio_avg_roas,
}: {
  bubbles: EfficiencyBubble[];
  portfolio_avg_roas: number;
}) {
  const [hover, setHover] = useState<{ label: string; x: number; y: number; color: string; roas: number; spendShare: number } | null>(null);

  const W = 380;
  const H = 220;
  const pad = { t: 20, r: 20, b: 36, l: 44 };
  const cw = W - pad.l - pad.r;
  const ch = H - pad.t - pad.b;

  const yMax = 6;
  const yTicks = [1, 2, 3, 4, 5];

  function toSvg(bx: number, by: number) {
    return {
      x: pad.l + bx * cw,
      y: pad.t + ch - (by / yMax) * ch,
    };
  }

  // Portfolio avg ROAS line
  const avgY = pad.t + ch - (portfolio_avg_roas / yMax) * ch;

  return (
    <svg
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      className="mt-3"
      style={{ overflow: "visible" }}
      role="img"
      aria-label="Efficiency frontier scatter plot comparing spend efficiency to ROAS across channels"
    >
      <title>Channel Efficiency Frontier</title>
      {/* Y grid */}
      {yTicks.map((t) => {
        const y = pad.t + ch - (t / yMax) * ch;
        return (
          <g key={t}>
            <line
              x1={pad.l} y1={y} x2={W - pad.r} y2={y}
              stroke="var(--line)" strokeWidth="1"
            />
            <text
              x={pad.l - 8} y={y + 3}
              textAnchor="end"
              className="font-mono"
              style={{ fontSize: 9, fill: "var(--text3)" }}
            >
              {t}x
            </text>
          </g>
        );
      })}

      {/* X-axis */}
      <line
        x1={pad.l} y1={pad.t + ch} x2={W - pad.r} y2={pad.t + ch}
        stroke="var(--line2)" strokeWidth="1"
      />
      <text
        x={pad.l + cw / 2} y={H - 4}
        textAnchor="middle"
        className="font-mono"
        style={{ fontSize: 9, fill: "var(--text3)", letterSpacing: "0.1em" }}
      >
        SPEND SHARE
      </text>

      {/* Portfolio avg dashed line */}
      <line
        x1={pad.l} y1={avgY} x2={W - pad.r} y2={avgY}
        stroke="var(--text3)" strokeWidth="1"
        strokeDasharray="4 4"
      />
      <text
        x={W - pad.r} y={avgY - 6}
        textAnchor="end"
        className="font-mono"
        style={{ fontSize: 8, fill: "var(--text3)", letterSpacing: "0.06em" }}
      >
        AVG {portfolio_avg_roas.toFixed(1)}x
      </text>

      {/* Bubbles — scale in with stagger */}
      {bubbles.map((b, bi) => {
        const pos = toSvg(b.x, b.y);
        const isHovered = hover?.label === b.label;
        return (
          <g key={b.label} style={{
            transformOrigin: `${pos.x}px ${pos.y}px`,
            animation: `scaleIn 0.4s ease ${0.1 + bi * 0.08}s both`,
          }}>
            {/* Bubble fill */}
            <circle
              cx={pos.x} cy={pos.y} r={b.r}
              fill={b.color}
              opacity={isHovered ? 0.38 : 0.22}
              stroke={b.color}
              strokeWidth={isHovered ? 2.5 : 1.5}
              style={{ transition: "opacity 0.15s ease, stroke-width 0.15s ease" }}
            />
            {/* Invisible larger hit area */}
            <circle
              cx={pos.x} cy={pos.y}
              r={Math.max(b.r + 4, 16)}
              fill="transparent"
              onMouseEnter={() => setHover({
                label: b.label,
                x: pos.x,
                y: pos.y,
                color: b.color,
                roas: b.y,
                spendShare: b.x * 100,
              })}
              onMouseLeave={() => setHover(null)}
              style={{ cursor: "crosshair" }}
            />
            {/* Label */}
            <text
              x={pos.x} y={pos.y + 3}
              textAnchor="middle"
              className="font-mono"
              style={{ fontSize: 8, fill: "var(--text)", letterSpacing: "0.06em", pointerEvents: "none" }}
            >
              {b.label}
            </text>
          </g>
        );
      })}

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
            <div style={{ fontWeight: 600, color: hover.color, marginBottom: 1 }}>
              {hover.label}
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 14 }}>
              <span style={{ color: "var(--text3)" }}>ROAS</span>
              <span style={{ fontWeight: 600 }}>{hover.roas.toFixed(1)}x</span>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between", gap: 14 }}>
              <span style={{ color: "var(--text3)" }}>Spend share</span>
              <span style={{ fontWeight: 600 }}>{hover.spendShare.toFixed(0)}%</span>
            </div>
            <div style={{
              display: "flex", justifyContent: "space-between", gap: 14,
              borderTop: "1px solid var(--line)", paddingTop: 3, marginTop: 1,
            }}>
              <span style={{ color: "var(--text3)" }}>vs Avg</span>
              <span style={{
                fontWeight: 600,
                color: hover.roas >= portfolio_avg_roas ? "var(--green)" : "var(--amber)",
              }}>
                {hover.roas >= portfolio_avg_roas ? "+" : ""}{(hover.roas - portfolio_avg_roas).toFixed(1)}x
              </span>
            </div>
          </div>
        )}
      </ChartTooltip>
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Media component                                               */
/* ------------------------------------------------------------------ */

export function Media() {
  // ---- Global filters ----
  const { filters } = useShell();

  // ---- BFF hook calls (auto-refetch when filters change) ----
  const channelsAsync = useMediaChannels(filters);
  const saturationAsync = useMediaSaturation(filters);
  const efficiencyAsync = useMediaEfficiency(filters);

  return (
    <div className="flex flex-col gap-4">
      {/* ===== Channel Performance Table ===== */}
      <DataGuard
        {...channelsAsync}
        skeleton={<SkeletonTable cols={6} rows={6} />}
        emptyHeadline="No channel data"
        emptyBody="Channel performance data is not available yet."
      >
        {({ channels }) => {
          // Apply channel filter client-side as a safety net
          const filtered = filters.channels.length === 0
            ? channels
            : channels.filter((ch) => filters.channels.includes(ch.name));

          return (
            <section
              className="rounded-card border border-line bg-panel overflow-hidden animate-rise"
              style={{ animationDelay: "0.05s" }}
            >
              {/* Header */}
              <div className="flex items-center justify-between px-[18px] py-[15px] border-b border-line">
                <SectionHeader title="Channel Performance" meta="ROLLING 4 WEEKS" />
              </div>

              {/* Column headers */}
              <div className="overflow-x-auto">
              <div className="grid grid-cols-[1fr_90px_80px_72px_72px_100px] gap-2 px-[18px] py-[9px] border-b border-line font-mono text-[9px] tracking-[.1em] text-fg3 min-w-[600px]">
                <span>CHANNEL</span>
                <span className="text-right">SPEND</span>
                <span className="text-right">CPIHH</span>
                <span className="text-right">CVR</span>
                <span className="text-right">ROAS</span>
                <span className="text-right">TREND</span>
              </div>

              {/* Rows */}
              {filtered.map((ch) => (
                <div
                  key={ch.name}
                  className="grid grid-cols-[1fr_90px_80px_72px_72px_100px] gap-2 items-center px-[18px] py-3 border-b border-line hover:bg-panel2 transition-colors min-w-[600px]"
                >
                  {/* Channel name with color dot */}
                  <div className="flex items-center gap-2.5">
                    <div
                      className="w-[8px] h-[8px] rounded-full flex-none"
                      style={{ background: ch.color, boxShadow: `0 0 6px ${ch.color}` }}
                    />
                    <span className="text-[13px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">
                      {ch.name}
                    </span>
                  </div>

                  <span className="font-mono text-[12px] text-fg text-right">
                    ${(ch.spend / 1e6).toFixed(1)}M
                  </span>
                  <span className="font-mono text-[12px] text-fg2 text-right">
                    ${ch.cpihh}
                  </span>
                  <span className="font-mono text-[12px] text-fg2 text-right">
                    {(ch.cvr * 100).toFixed(1)}%
                  </span>
                  <span className="font-mono text-[11px] font-medium text-right text-positive bg-[rgba(79,216,155,.14)] px-2 py-0.5 rounded-[5px] justify-self-end">
                    {ch.roas.toFixed(1)}x
                  </span>
                  <div className="flex justify-end">
                    <Sparkline data={ch.trend} color={ch.color} width={80} height={24} />
                  </div>
                </div>
              ))}
              </div>
            </section>
          );
        }}
      </DataGuard>

      {/* ===== 2-Column: Saturation Curves + Efficiency Frontier ===== */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <DataGuard
          {...saturationAsync}
          emptyHeadline="No saturation data"
          emptyBody="Saturation curve data is not available yet."
        >
          {({ curves }) => (
            <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.2s" }}>
              <SectionHeader title="Saturation Curves" meta="MARGINAL RESPONSE" />
              <SaturationCurves curves={curves} />
            </Card>
          )}
        </DataGuard>

        <DataGuard
          {...efficiencyAsync}
          emptyHeadline="No efficiency data"
          emptyBody="Efficiency frontier data is not available yet."
        >
          {({ bubbles, portfolio_avg_roas }) => (
            <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.25s" }}>
              <SectionHeader title="Efficiency Frontier" meta="ROAS vs SPEND SHARE" />
              <EfficiencyFrontier
                bubbles={bubbles}
                portfolio_avg_roas={portfolio_avg_roas}
              />
            </Card>
          )}
        </DataGuard>
      </div>
    </div>
  );
}
