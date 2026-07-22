import { useState, useMemo, useCallback, useRef, memo } from "react";
import { Card, SectionHeader, Segmented } from "../ui";
import { DataGuard } from "../ui/DataGuard";
import { AwarenessFilterBar } from "./AwarenessFilterBar";
import { useShareOfSearch, usePeerComparison } from "../api/hooks";
import type { ShareOfSearchPoint, PeerComparisonItem } from "../api/hooks";
import { useShell } from "../shell/ShellProvider";
import {
  BANKS,
  BRAND_COLORS,
  QUARTERS,
  LQ_IDX,
  LQA_IDX,
  TRAIL_IDX,
  ALL_DMAS,
  DMA_POP,
  DMAQ,
  CMP_ROWS,
  CMP_COL_ORDER,
  type CmpRow,
} from "../data/searchTrends";

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

/** Format large numbers: >=1M → "X.XM", >=1K → "XK", else rounded */
function fmtN(n: number): string {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${Math.round(n / 1_000)}K`;
  return String(Math.round(n));
}

/** Format YoY percentage with sign */
function fmtPct(v: number | null): string {
  if (v === null) return "—";
  const sign = v >= 0 ? "+" : "";
  return `${sign}${v.toFixed(1)}%`;
}

/** Quarterly series: sum volumes across selected DMAs for a brand */
function bSeries(brand: string, dmas: readonly string[]): number[] {
  const bd = DMAQ[brand] || {};
  return QUARTERS.map((_, qi) =>
    dmas.reduce((s, d) => s + (bd[d]?.[qi] ?? 0), 0),
  );
}

/** Trailing 4-quarter total */
function bTrail(brand: string, dmas: readonly string[]): number {
  const s = bSeries(brand, dmas);
  return TRAIL_IDX.reduce((acc, i) => acc + s[i], 0);
}

/** Total 18+ population across DMAs where brand has data */
function bPop(brand: string, dmas: readonly string[]): number {
  const bd = DMAQ[brand] || {};
  return dmas.reduce((s, d) => s + (bd[d] ? (DMA_POP[d] || 0) : 0), 0);
}

/** Per-capita search intensity: trailing-4Q MSV per 1,000 adults */
function bPer1k(brand: string, dmas: readonly string[]): number {
  const pop = bPop(brand, dmas);
  return pop > 0 ? (bTrail(brand, dmas) / pop) * 1000 : 0;
}

/** Brand display color — maps Fifth Third to the accent teal for UI elements */
function brandUiColor(brand: string): string {
  return brand === "Fifth Third" ? "var(--cyan)" : BRAND_COLORS[brand] ?? "var(--text2)";
}

/** Chart-line color — uses the actual brand hex (acceptable for data ink) */
function brandChartColor(brand: string): string {
  return BRAND_COLORS[brand] ?? "#888";
}

/* ------------------------------------------------------------------ */
/*  1. Competitor KPI Tiles                                            */
/* ------------------------------------------------------------------ */

interface KpiTileProps {
  brand: string;
  msv: number;
  yoy: number | null;
  per1k: number;
  selected: boolean;
  isFifthThird: boolean;
  onClick: () => void;
  delay: number;
}

const KpiTile = memo(function KpiTile({ brand, msv, yoy, per1k, selected, isFifthThird, onClick, delay }: KpiTileProps) {
  const yoyColor = yoy === null ? "text-fg3" : yoy >= 0 ? "text-positive" : "text-critical";
  const dimmed = !selected;

  return (
    <Card
      accent={isFifthThird}
      glow={isFifthThird}
      className={`flex flex-col p-[14px] min-w-[150px] cursor-pointer select-none animate-rise transition-all duration-200 ${dimmed ? "opacity-30" : ""}`}
      style={{ animationDelay: `${delay}s`, filter: dimmed ? "grayscale(0.85)" : undefined }}
    >
      <button
        type="button"
        className="flex flex-col items-start w-full text-left"
        onClick={onClick}
      >
        {/* Brand name */}
        <span
          className="font-mono text-[9px] tracking-[.1em] font-semibold truncate w-full"
          style={{ color: brandUiColor(brand) }}
        >
          {brand.toUpperCase()}
        </span>

        {/* Latest quarter MSV */}
        <div className="text-[26px] font-semibold tracking-[-0.02em] mt-1.5 text-fg">
          {fmtN(msv)}
        </div>

        {/* Quarter label + YoY */}
        <div className="flex items-baseline gap-1.5 mt-1">
          <span className="font-mono text-[9px] tracking-[.06em] text-fg3">
            {QUARTERS[LQ_IDX]}
          </span>
          <span className={`font-mono text-[9px] tracking-[.06em] font-medium ${yoyColor}`}>
            YoY {fmtPct(yoy)}
          </span>
        </div>

        {/* Per-capita */}
        <span className="font-mono text-[9px] tracking-[.06em] text-fg3 mt-0.5">
          /1k: {per1k.toFixed(1)}
        </span>
      </button>
    </Card>
  );
});

/* ------------------------------------------------------------------ */
/*  2. Quarterly Search Volume Line Chart (SVG)                        */
/* ------------------------------------------------------------------ */

interface LineChartProps {
  brands: string[];
  mode: "abs" | "idx";
  dmas: readonly string[];
}

function QuarterlyLineChart({ brands, mode, dmas }: LineChartProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);

  const W = 900;
  const H = 340;
  const pad = { t: 28, r: 90, b: 44, l: 64 };
  const cw = W - pad.l - pad.r;
  const ch = H - pad.t - pad.b;

  // Build series for each selected brand
  const seriesMap = useMemo(() => {
    const m: Record<string, number[]> = {};
    for (const b of brands) {
      const raw = bSeries(b, dmas);
      if (mode === "idx") {
        const base = raw.find((v) => v > 0) || 1;
        m[b] = raw.map((v) => (v / base) * 100);
      } else {
        m[b] = raw;
      }
    }
    return m;
  }, [brands, mode, dmas]);

  // Compute y-axis range
  const allVals = Object.values(seriesMap).flat().filter((v) => v > 0);
  const hasData = allVals.length > 0;
  const dataMin = hasData ? Math.min(...allVals) : 0;
  const dataMax = hasData ? Math.max(...allVals) : 1;
  const margin = (dataMax - dataMin) * 0.12 || dataMax * 0.12 || 1;
  const yMin = Math.max(0, dataMin - margin);
  const yMax = dataMax + margin;
  const yRange = yMax - yMin || 1;

  // Y ticks (4-5 nice ticks)
  const yStep = (() => {
    const raw = yRange / 5;
    const mag = Math.pow(10, Math.floor(Math.log10(raw)));
    const norms = [1, 2, 5, 10];
    return mag * (norms.find((n) => n * mag >= raw) || 10);
  })();
  const yTicks: number[] = [];
  for (let t = Math.ceil(yMin / yStep) * yStep; t <= yMax; t += yStep) {
    yTicks.push(t);
  }

  function toY(v: number) {
    return pad.t + ch - ((v - yMin) / yRange) * ch;
  }
  function toX(i: number) {
    return pad.l + (i / (QUARTERS.length - 1)) * cw;
  }

  /** Catmull-Rom to cubic Bezier SVG path for smooth curves (tension ≈ 0.25) */
  function toSmoothPath(data: number[]): string {
    if (data.length < 2) return "";
    const pts = data.map((v, i) => ({ x: toX(i), y: toY(v) }));
    const t = 0.25; // tension
    let d = `M${pts[0].x.toFixed(1)},${pts[0].y.toFixed(1)}`;
    for (let i = 0; i < pts.length - 1; i++) {
      const p0 = pts[Math.max(0, i - 1)];
      const p1 = pts[i];
      const p2 = pts[i + 1];
      const p3 = pts[Math.min(pts.length - 1, i + 2)];
      const cp1x = p1.x + (p2.x - p0.x) * t;
      const cp1y = p1.y + (p2.y - p0.y) * t;
      const cp2x = p2.x - (p3.x - p1.x) * t;
      const cp2y = p2.y - (p3.y - p1.y) * t;
      d += ` C${cp1x.toFixed(1)},${cp1y.toFixed(1)} ${cp2x.toFixed(1)},${cp2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
    }
    return d;
  }

  // Handle mouse move for crosshair
  function handleMouseMove(e: React.MouseEvent<SVGSVGElement>) {
    const svg = svgRef.current;
    if (!svg) return;
    const rect = svg.getBoundingClientRect();
    const svgX = ((e.clientX - rect.left) / rect.width) * W;
    // Find nearest quarter index
    const rawIdx = (svgX - pad.l) / cw * (QUARTERS.length - 1);
    const idx = Math.round(Math.max(0, Math.min(QUARTERS.length - 1, rawIdx)));
    setHoverIdx(idx);
  }

  // Tooltip data at hovered quarter
  const tooltipData = useMemo(() => {
    if (hoverIdx === null) return null;
    return brands
      .map((b) => ({ brand: b, val: seriesMap[b]?.[hoverIdx] ?? 0 }))
      .sort((a, b) => b.val - a.val);
  }, [hoverIdx, brands, seriesMap]);

  if (!hasData) return <div className="text-center text-fg3 font-mono text-xs py-8">No data for selected DMAs</div>;

  return (
    <svg
      ref={svgRef}
      width="100%"
      viewBox={`0 0 ${W} ${H}`}
      className="mt-3"
      style={{ overflow: "visible" }}
      onMouseMove={handleMouseMove}
      onMouseLeave={() => setHoverIdx(null)}
      role="img"
      aria-label="Quarterly brand awareness trend line chart comparing search share across competitors"
    >
      <title>Quarterly Brand Awareness Trends</title>
      {/* Y grid */}
      {yTicks.map((t) => (
        <g key={t}>
          <line
            x1={pad.l}
            y1={toY(t)}
            x2={W - pad.r}
            y2={toY(t)}
            stroke="var(--line)"
            strokeWidth="1"
          />
          <text
            x={pad.l - 10}
            y={toY(t) + 3}
            textAnchor="end"
            className="font-mono"
            style={{ fontSize: 9, fill: "var(--text3)" }}
          >
            {mode === "idx" ? Math.round(t) : fmtN(t)}
          </text>
        </g>
      ))}

      {/* Vertical grid lines (light) at each quarter */}
      {QUARTERS.map((_, i) => (
        <line
          key={`vg-${i}`}
          x1={toX(i)}
          y1={pad.t}
          x2={toX(i)}
          y2={pad.t + ch}
          stroke="var(--line)"
          strokeWidth="0.5"
          strokeOpacity="0.4"
        />
      ))}

      {/* X-axis line */}
      <line
        x1={pad.l}
        y1={pad.t + ch}
        x2={W - pad.r}
        y2={pad.t + ch}
        stroke="var(--line2)"
        strokeWidth="1"
      />

      {/* X labels */}
      {QUARTERS.map((q, i) => (
        <text
          key={q}
          x={toX(i)}
          y={H - 8}
          textAnchor="middle"
          className="font-mono"
          style={{ fontSize: 8, fill: "var(--text3)", letterSpacing: "0.04em" }}
        >
          {q.replace("20", "'")}
        </text>
      ))}

      {/* Lines + dots — Fifth Third drawn last (on top) */}
      {brands
        .slice()
        .sort((a, b) => (a === "Fifth Third" ? 1 : b === "Fifth Third" ? -1 : 0))
        .map((brand) => {
          const data = seriesMap[brand];
          if (!data) return null;
          const isFT = brand === "Fifth Third";
          const isNB = brand === "Non-Brand";
          const color = brandChartColor(brand);
          const lastVal = data[data.length - 1];
          const endX = toX(data.length - 1);
          const endY = toY(lastVal);

          return (
            <g key={brand}>
              {/* Smooth line */}
              <path
                d={toSmoothPath(data)}
                fill="none"
                stroke={color}
                strokeWidth={isFT ? 3.5 : 1.8}
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeDasharray={isNB ? "6 4" : undefined}
              />
              {/* Data point dots */}
              {data.map((v, i) => (
                <circle
                  key={i}
                  cx={toX(i)}
                  cy={toY(v)}
                  r={hoverIdx === i ? (isFT ? 5 : 3.5) : (isFT ? 2.5 : 1.5)}
                  fill={color}
                  stroke={hoverIdx === i ? "var(--bg)" : "none"}
                  strokeWidth={hoverIdx === i ? 1.5 : 0}
                  style={{ transition: "r 0.1s" }}
                />
              ))}
              {/* End label */}
              <text
                x={endX + 8}
                y={endY + 3}
                className="font-mono"
                style={{ fontSize: 8.5, fill: color, letterSpacing: "0.04em", fontWeight: isFT ? 600 : 400 }}
              >
                {brand}
              </text>
            </g>
          );
        })}

      {/* Hover crosshair + tooltip */}
      {hoverIdx !== null && (
        <g>
          {/* Vertical crosshair */}
          <line
            x1={toX(hoverIdx)}
            y1={pad.t}
            x2={toX(hoverIdx)}
            y2={pad.t + ch}
            stroke="var(--text3)"
            strokeWidth="1"
            strokeDasharray="3 3"
            strokeOpacity="0.6"
          />

          {/* Tooltip background */}
          <rect
            x={Math.min(toX(hoverIdx) + 12, W - pad.r - 160)}
            y={pad.t + 4}
            width={152}
            height={14 + (tooltipData?.length ?? 0) * 14 + 4}
            rx={6}
            fill="var(--panel)"
            stroke="var(--line)"
            strokeWidth="1"
            opacity="0.95"
          />

          {/* Tooltip quarter label */}
          <text
            x={Math.min(toX(hoverIdx) + 20, W - pad.r - 152)}
            y={pad.t + 17}
            className="font-mono"
            style={{ fontSize: 9, fill: "var(--text2)", fontWeight: 600 }}
          >
            {QUARTERS[hoverIdx]}
          </text>

          {/* Tooltip brand values */}
          {tooltipData?.map((d, i) => {
            const tx = Math.min(toX(hoverIdx) + 20, W - pad.r - 152);
            const ty = pad.t + 30 + i * 14;
            return (
              <g key={d.brand}>
                <circle
                  cx={tx}
                  cy={ty - 3}
                  r={3}
                  fill={brandChartColor(d.brand)}
                />
                <text
                  x={tx + 8}
                  y={ty}
                  className="font-mono"
                  style={{ fontSize: 8.5, fill: "var(--text2)" }}
                >
                  {d.brand}
                </text>
                <text
                  x={tx + 130}
                  y={ty}
                  textAnchor="end"
                  className="font-mono"
                  style={{ fontSize: 8.5, fill: "var(--text)", fontWeight: 600 }}
                >
                  {mode === "idx" ? Math.round(d.val) : fmtN(d.val)}
                </text>
              </g>
            );
          })}
        </g>
      )}
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  3. Demand Intensity Horizontal Bar Chart                           */
/* ------------------------------------------------------------------ */

interface IntensityBarProps {
  brands: string[];
  dmas: readonly string[];
}

function DemandIntensityBars({ brands, dmas }: IntensityBarProps) {
  const ranked = useMemo(() => {
    return brands
      .map((b) => ({ brand: b, val: bPer1k(b, dmas) }))
      .filter((r) => r.val > 0)
      .sort((a, b) => b.val - a.val);
  }, [brands, dmas]);

  const maxVal = ranked[0]?.val || 1;

  return (
    <div className="flex flex-col gap-[6px] mt-3">
      {ranked.map((r) => {
        const pct = (r.val / maxVal) * 100;
        const isFT = r.brand === "Fifth Third";
        const color = brandChartColor(r.brand);

        return (
          <div key={r.brand} className="flex items-center gap-3">
            {/* Label */}
            <span
              className="font-mono text-[10px] tracking-[.04em] w-[90px] text-right flex-none truncate"
              style={{ color: brandUiColor(r.brand) }}
            >
              {r.brand}
            </span>

            {/* Bar track */}
            <div className="flex-1 h-[18px] rounded-[4px] relative" style={{ background: "var(--panel2)" }}>
              <div
                className="h-full rounded-[4px] transition-all duration-500"
                style={{
                  width: `${pct}%`,
                  background: color,
                  opacity: 0.75,
                  boxShadow: isFT ? `0 0 12px ${color}55` : undefined,
                }}
              />
            </div>

            {/* Value label */}
            <span className="font-mono text-[10px] text-fg2 w-[50px] text-right flex-none">
              {r.val.toFixed(1)}
            </span>
          </div>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  4. DMA x Brand Comparison Table                                    */
/* ------------------------------------------------------------------ */

type CmpMetric = "per1k" | "msv" | "yoy";

interface CmpTableProps {
  brands: string[];
  metric: CmpMetric;
  sortCol: string;
  sortDir: "asc" | "desc";
  filter: string;
  showAll: boolean;
  onSort: (col: string) => void;
  onFilter: (v: string) => void;
  onToggleAll: () => void;
  onMetric: (m: CmpMetric) => void;
}

/** Heat-shade for per-capita mode: higher values → more green */
function heatBg(val: number, maxVal: number): string | undefined {
  if (maxVal <= 0) return undefined;
  const intensity = Math.min(val / maxVal, 1);
  return `rgba(79,216,155,${(intensity * 0.22).toFixed(3)})`;
}

function CmpTable({
  brands,
  metric,
  sortCol,
  sortDir,
  filter,
  showAll,
  onSort,
  onFilter,
  onToggleAll,
  onMetric,
}: CmpTableProps) {
  // Filter rows by DMA name search
  const filteredRows = useMemo(() => {
    const lf = filter.toLowerCase();
    return lf
      ? CMP_ROWS.filter((r) => r.dma.toLowerCase().includes(lf))
      : CMP_ROWS;
  }, [filter]);

  // Columns in display order, limited to selected brands
  const cols = useMemo(
    () => CMP_COL_ORDER.filter((c) => brands.includes(c)),
    [brands],
  );

  // Extract cell value for sorting
  const cellVal = useCallback(
    (row: CmpRow, col: string): number => {
      const bd = row.b[col];
      if (!bd) return -Infinity;
      if (metric === "per1k") return bd.per1k;
      if (metric === "msv") return bd.msv;
      return bd.yoy ?? -Infinity;
    },
    [metric],
  );

  // Sort rows
  const sortedRows = useMemo(() => {
    const dir = sortDir === "asc" ? 1 : -1;
    return [...filteredRows].sort((a, b) => {
      if (sortCol === "dma") return dir * a.dma.localeCompare(b.dma);
      if (sortCol === "pop") return dir * (a.pop - b.pop);
      return dir * (cellVal(a, sortCol) - cellVal(b, sortCol));
    });
  }, [filteredRows, sortCol, sortDir, cellVal]);

  const visibleRows = showAll ? sortedRows : sortedRows.slice(0, 50);
  const hasMore = sortedRows.length > 50 && !showAll;

  // Max per-capita for heat shading
  const maxPer1k = useMemo(() => {
    let mx = 0;
    for (const r of CMP_ROWS) {
      for (const col of cols) {
        const v = r.b[col]?.per1k ?? 0;
        if (v > mx) mx = v;
      }
    }
    return mx;
  }, [cols]);

  // CSV download
  function downloadCsv() {
    const header = ["DMA", "Population", ...cols.map((c) => `${c} (${metric})`)];
    const rows = sortedRows.map((r) => {
      const vals = cols.map((c) => {
        const bd = r.b[c];
        if (!bd) return "";
        if (metric === "per1k") return bd.per1k.toFixed(1);
        if (metric === "msv") return String(bd.msv);
        return bd.yoy !== null ? bd.yoy.toFixed(1) : "";
      });
      return [r.dma, String(r.pop), ...vals];
    });
    const csv = [header, ...rows].map((r) => r.map((c) => `"${c}"`).join(",")).join("\n");
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `brand-awareness-${metric}-${new Date().toISOString().slice(0, 10)}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }

  // Sort arrow indicator
  function sortArrow(col: string) {
    if (sortCol !== col) return "";
    return sortDir === "asc" ? " ▲" : " ▼";
  }

  // Format cell value for display
  function fmtCell(row: CmpRow, col: string): string {
    const bd = row.b[col];
    if (!bd) return "—";
    if (metric === "per1k") return bd.per1k.toFixed(1);
    if (metric === "msv") return fmtN(bd.msv);
    return fmtPct(bd.yoy);
  }

  // Cell color for YoY mode
  function cellColor(row: CmpRow, col: string): string | undefined {
    if (metric !== "yoy") return undefined;
    const bd = row.b[col];
    if (!bd || bd.yoy === null) return "var(--text3)";
    return bd.yoy >= 0 ? "var(--green)" : "var(--red)";
  }

  const metricLabels: Record<CmpMetric, string> = {
    per1k: "/1k",
    msv: "MSV (4Q)",
    yoy: "YoY %",
  };

  return (
    <div className="flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between mb-3 gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <Segmented
            options={["per1k", "msv", "yoy"] as CmpMetric[]}
            value={metric}
            onChange={onMetric}
            size="sm"
          />
          <span className="font-mono text-[9px] tracking-[.08em] text-fg3">
            {sortedRows.length} DMAs
          </span>
        </div>

        <div className="flex items-center gap-3">
          {/* Search filter */}
          <div className="relative">
            <input
              type="text"
              value={filter}
              onChange={(e) => onFilter(e.target.value)}
              placeholder="Filter DMAs..."
              className="h-[28px] w-[180px] rounded-[8px] border border-line bg-panel2 px-2.5 font-mono text-[10px] text-fg placeholder:text-fg3 focus:outline-none focus:border-[var(--cyan-glow)]"
            />
          </div>

          {/* CSV button */}
          <button
            type="button"
            onClick={downloadCsv}
            className="h-[28px] px-3 rounded-[8px] border border-line bg-panel2 font-mono text-[9px] tracking-[.06em] text-fg3 hover:text-fg hover:border-line-strong transition-colors"
          >
            CSV
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto">
        <table className="w-full border-collapse" role="table" aria-label="DMA market share comparison by competitor">
          <thead>
            <tr className="border-b border-line">
              <th
                className="text-left px-2 py-2 font-mono text-[9px] tracking-[.1em] text-fg3 cursor-pointer hover:text-fg transition-colors sticky left-0 bg-panel z-10"
                onClick={() => onSort("dma")}
              >
                DMA{sortArrow("dma")}
              </th>
              <th
                className="text-right px-2 py-2 font-mono text-[9px] tracking-[.1em] text-fg3 cursor-pointer hover:text-fg transition-colors w-[70px]"
                onClick={() => onSort("pop")}
              >
                POP{sortArrow("pop")}
              </th>
              {cols.map((col) => {
                const isFT = col === "Fifth Third";
                return (
                  <th
                    key={col}
                    className={`text-right px-2 py-2 font-mono text-[9px] tracking-[.1em] cursor-pointer hover:text-fg transition-colors min-w-[72px] ${isFT ? "text-cyan" : "text-fg3"}`}
                    style={isFT ? { background: "var(--cyan-subtle)" } : undefined}
                    onClick={() => onSort(col)}
                  >
                    {col.toUpperCase()}{sortArrow(col)}
                    <div className="font-normal text-[8px] opacity-60">{metricLabels[metric]}</div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((row) => (
              <tr
                key={row.dma}
                className="border-b border-line hover:bg-panel2 transition-colors"
              >
                <td className="text-left px-2 py-1.5 text-[11px] text-fg2 truncate max-w-[200px] sticky left-0 bg-panel z-10">
                  {row.dma}
                </td>
                <td className="text-right px-2 py-1.5 font-mono text-[10px] text-fg3 w-[70px]">
                  {fmtN(row.pop)}
                </td>
                {cols.map((col) => {
                  const isFT = col === "Fifth Third";
                  const bg =
                    metric === "per1k" && row.b[col]
                      ? heatBg(row.b[col].per1k, maxPer1k)
                      : undefined;

                  return (
                    <td
                      key={col}
                      className={`text-right px-2 py-1.5 font-mono text-[10px] min-w-[72px] ${isFT ? "font-medium" : ""}`}
                      style={{
                        background: isFT
                          ? bg
                            ? `linear-gradient(${bg}, var(--cyan-subtle))`
                            : "var(--cyan-subtle)"
                          : bg,
                        color: cellColor(row, col) ?? (row.b[col] ? "var(--text)" : "var(--text3)"),
                      }}
                    >
                      {fmtCell(row, col)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Show more / fewer */}
      {(hasMore || (showAll && sortedRows.length > 50)) && (
        <button
          type="button"
          onClick={onToggleAll}
          className="mt-3 self-center px-4 py-1.5 rounded-[8px] border border-line bg-panel2 font-mono text-[9px] tracking-[.06em] text-fg3 hover:text-fg hover:border-line-strong transition-colors"
        >
          {showAll ? `Show top 50 of ${sortedRows.length}` : `Show all ${sortedRows.length} DMAs`}
        </button>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Legend Row                                                          */
/* ------------------------------------------------------------------ */

function ChartLegend({
  brands,
  onToggle,
  selected,
}: {
  brands: readonly string[];
  onToggle: (b: string) => void;
  selected: Set<string>;
}) {
  return (
    <div className="flex flex-wrap gap-x-4 gap-y-1 mt-3">
      {brands.map((b) => {
        const on = selected.has(b);
        return (
          <button
            key={b}
            type="button"
            onClick={() => onToggle(b)}
            className={`flex items-center gap-1.5 transition-all duration-150 ${on ? "" : "opacity-30"}`}
            style={{ filter: on ? undefined : "grayscale(0.85)" }}
          >
            <span
              className="w-[8px] h-[8px] rounded-full flex-none"
              style={{
                background: brandChartColor(b),
                boxShadow: on ? `0 0 6px ${brandChartColor(b)}` : undefined,
              }}
            />
            <span className={`font-mono text-[9px] tracking-[.04em] ${on ? "text-fg3" : "text-fg3 line-through"}`}>{b}</span>
          </button>
        );
      })}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  5. Share of Search Trend Card (BFF data)                           */
/* ------------------------------------------------------------------ */

function ShareOfSearchCard({ points }: { points: ShareOfSearchPoint[] }) {
  if (points.length === 0) return null;

  const latest = points[points.length - 1];
  const prev = points.length > 1 ? points[points.length - 2] : null;
  const delta = prev ? latest.share_of_search - prev.share_of_search : 0;
  const deltaSign = delta >= 0 ? "+" : "";

  // Sparkline SVG
  const W = 180;
  const H = 36;
  const pad = 2;
  const shares = points.map((p) => p.share_of_search);
  const mn = Math.min(...shares);
  const mx = Math.max(...shares);
  const range = mx - mn || 0.01;

  const pts = shares.map((v, i) => {
    const x = pad + (i / (shares.length - 1)) * (W - 2 * pad);
    const y = H - pad - ((v - mn) / range) * (H - 2 * pad);
    return `${x.toFixed(1)},${y.toFixed(1)}`;
  });

  return (
    <Card accent className="p-[14px] animate-rise" style={{ animationDelay: "0.02s" }}>
      <div className="flex items-center justify-between">
        <span className="font-mono text-[9px] tracking-[.1em] text-cyan font-semibold">
          SHARE OF SEARCH
        </span>
        <span className="font-mono text-[9px] tracking-[.06em] text-fg3">
          #{latest.rank} rank
        </span>
      </div>

      <div className="flex items-end gap-3 mt-2">
        <span className="text-[28px] font-semibold tracking-[-0.02em] text-fg tabular-nums">
          {(latest.share_of_search * 100).toFixed(1)}%
        </span>
        <span className={`font-mono text-[10px] tracking-[.04em] mb-1 ${delta >= 0 ? "text-positive" : "text-critical"}`}>
          {deltaSign}{(delta * 100).toFixed(2)}pp
        </span>
      </div>

      <svg width="100%" viewBox={`0 0 ${W} ${H}`} className="mt-2" style={{ overflow: "visible" }}>
        <polyline
          points={pts.join(" ")}
          fill="none"
          stroke="var(--cyan)"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
        {/* End dot */}
        <circle
          cx={parseFloat(pts[pts.length - 1].split(",")[0])}
          cy={parseFloat(pts[pts.length - 1].split(",")[1])}
          r="3"
          fill="var(--cyan)"
        />
      </svg>

      <div className="flex items-center justify-between mt-1.5">
        <span className="font-mono text-[8px] text-fg3">
          {points[0].date.slice(0, 7)}
        </span>
        <span className="font-mono text-[8px] text-fg3">
          {latest.date.slice(0, 7)}
        </span>
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  6. Peer Ranking Strip (BFF data)                                   */
/* ------------------------------------------------------------------ */

function PeerRankingStrip({ peers }: { peers: PeerComparisonItem[] }) {
  if (peers.length === 0) return null;

  const fifthThird = peers.find((p) => p.brand.includes("Fifth Third"));

  return (
    <Card className="p-[14px] animate-rise" style={{ animationDelay: "0.06s" }}>
      <SectionHeader title="Peer Ranking" meta={`${peers.length} BANKS · LATEST MONTH`} />
      <div className="flex flex-col gap-[4px] mt-3">
        {peers.slice(0, 10).map((p) => {
          const isFT = p.brand.includes("Fifth Third");
          const maxMsv = peers[0]?.msv || 1;
          const barPct = (p.msv / maxMsv) * 100;
          const deltaColor = p.share_delta >= 0 ? "text-positive" : "text-critical";

          return (
            <div
              key={p.brand}
              className={`flex items-center gap-2 px-2 py-[5px] rounded-[6px] transition-colors ${isFT ? "bg-[var(--cyan-subtle)]" : "hover:bg-panel2"}`}
            >
              {/* Rank */}
              <span className={`font-mono text-[10px] w-[18px] text-right flex-none ${isFT ? "text-cyan font-semibold" : "text-fg3"}`}>
                #{p.rank}
              </span>

              {/* Brand */}
              <span className={`text-[11px] w-[110px] flex-none truncate ${isFT ? "text-cyan font-medium" : "text-fg2"}`}>
                {p.brand}
              </span>

              {/* Bar */}
              <div className="flex-1 h-[14px] rounded-[3px] relative" style={{ background: "var(--panel2)" }}>
                <div
                  className="h-full rounded-[3px]"
                  style={{
                    width: `${barPct}%`,
                    background: isFT ? "var(--cyan)" : "var(--text3)",
                    opacity: isFT ? 0.7 : 0.25,
                  }}
                />
              </div>

              {/* Share */}
              <span className={`font-mono text-[10px] w-[42px] text-right flex-none ${isFT ? "text-fg font-medium" : "text-fg2"}`}>
                {p.share.toFixed(1)}%
              </span>

              {/* Delta */}
              <span className={`font-mono text-[9px] w-[50px] text-right flex-none ${deltaColor}`}>
                {p.share_delta >= 0 ? "+" : ""}{p.share_delta.toFixed(1)}pp
              </span>
            </div>
          );
        })}
      </div>

      {fifthThird && (
        <div className="mt-3 pt-2 border-t border-line flex items-center gap-3">
          <span className="font-mono text-[9px] tracking-[.06em] text-fg3">FIFTH THIRD</span>
          <span className="font-mono text-[11px] text-fg font-medium tabular-nums">
            {fmtN(fifthThird.msv)} MSV
          </span>
          <span className="font-mono text-[10px] text-fg3">
            {fifthThird.share.toFixed(1)}% share
          </span>
          <span className={`font-mono text-[10px] ${fifthThird.msv_delta >= 0 ? "text-positive" : "text-critical"}`}>
            {fifthThird.msv_delta >= 0 ? "+" : ""}{fmtN(fifthThird.msv_delta)} MSV
          </span>
        </div>
      )}
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Component                                                     */
/* ------------------------------------------------------------------ */

export function BrandAwareness() {
  // ---- Global filters (for BFF hooks) ----
  const { filters } = useShell();

  // ---- BFF hooks ----
  const sosQuery = useShareOfSearch(filters);
  const peerQuery = usePeerComparison(filters);

  // ---- Local DMA filter state (managed by AwarenessFilterBar) ----
  const [effectiveDmas, setEffectiveDmas] = useState<readonly string[]>(ALL_DMAS);

  const handleDmasChange = useCallback((dmas: readonly string[]) => {
    setEffectiveDmas(dmas);
  }, []);

  // ---- State ----
  const [selectedBrands, setSelectedBrands] = useState<Set<string>>(
    () => new Set(BANKS as readonly string[]),
  );
  const [chartMode, setChartMode] = useState<"abs" | "idx">("abs");
  const [cmpMetric, setCmpMetric] = useState<CmpMetric>("per1k");
  const [cmpSort, setCmpSort] = useState<string>("Fifth Third");
  const [cmpDir, setCmpDir] = useState<"asc" | "desc">("desc");
  const [cmpFilter, setCmpFilter] = useState("");
  const [showAllRows, setShowAllRows] = useState(false);

  // Toggle a brand in/out
  const toggleBrand = useCallback((brand: string) => {
    setSelectedBrands((prev) => {
      const next = new Set(prev);
      if (next.has(brand)) {
        // Don't allow deselecting all brands
        if (next.size > 1) next.delete(brand);
      } else {
        next.add(brand);
      }
      return next;
    });
  }, []);

  // Selected brands as array (preserving BANKS order)
  const activeBrands = useMemo(
    () => (BANKS as readonly string[]).filter((b) => selectedBrands.has(b)),
    [selectedBrands],
  );

  // Pre-compute KPI data for all banks (reactive to DMA filter)
  const kpiData = useMemo(() => {
    return (BANKS as readonly string[]).map((brand) => {
      const series = bSeries(brand, effectiveDmas);
      const lq = series[LQ_IDX];
      const lqa = series[LQA_IDX];
      const yoy = lqa > 0 ? ((lq - lqa) / lqa) * 100 : null;
      const per1k = bPer1k(brand, effectiveDmas);
      return { brand, msv: lq, yoy, per1k };
    });
  }, [effectiveDmas]);

  // Handle sort column click
  const handleSort = useCallback(
    (col: string) => {
      if (cmpSort === col) {
        setCmpDir((d) => (d === "asc" ? "desc" : "asc"));
      } else {
        setCmpSort(col);
        setCmpDir("desc");
      }
    },
    [cmpSort],
  );

  return (
    <div className="flex flex-col gap-4">
      {/* ===== 0. DMA Filter Panel ===== */}
      <AwarenessFilterBar onDmasChange={handleDmasChange} />

      {/* ===== 1. KPI Tiles + Share of Search (horizontally scrollable) ===== */}
      <div className="overflow-x-auto pb-1 -mx-1 px-1">
        <div className="flex gap-[10px] min-w-max">
          {/* SoS card from BFF */}
          {sosQuery.data && sosQuery.data.points.length > 0 && (
            <ShareOfSearchCard points={sosQuery.data.points} />
          )}
          {kpiData.map((k, i) => (
            <KpiTile
              key={k.brand}
              brand={k.brand}
              msv={k.msv}
              yoy={k.yoy}
              per1k={k.per1k}
              selected={selectedBrands.has(k.brand)}
              isFifthThird={k.brand === "Fifth Third"}
              onClick={() => toggleBrand(k.brand)}
              delay={0.03 + i * 0.04}
            />
          ))}
        </div>
      </div>

      {/* ===== 2. Quarterly Search Volume ===== */}
      <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.1s" }}>
        <div className="flex items-center justify-between">
          <SectionHeader title="Quarterly Search Volume" meta={`${QUARTERS[0]} — ${QUARTERS[LQ_IDX]}${effectiveDmas.length < ALL_DMAS.length ? ` · ${effectiveDmas.length} DMAs` : ""}`} />
          <Segmented
            options={["abs", "idx"]}
            value={chartMode}
            onChange={(v) => setChartMode(v as "abs" | "idx")}
            size="sm"
          />
        </div>
        <QuarterlyLineChart brands={activeBrands} mode={chartMode} dmas={effectiveDmas} />
        <ChartLegend brands={BANKS} onToggle={toggleBrand} selected={selectedBrands} />
      </Card>

      {/* ===== 3. Demand Intensity (Per-Capita) ===== */}
      <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.18s" }}>
        <SectionHeader title="Demand Intensity" meta={`MSV PER 1,000 ADULTS · TRAILING 4Q${effectiveDmas.length < ALL_DMAS.length ? ` · ${effectiveDmas.length} DMAs` : ""}`} />
        <DemandIntensityBars brands={activeBrands} dmas={effectiveDmas} />
      </Card>

      {/* ===== 3b. Peer Ranking from BFF ===== */}
      <DataGuard {...peerQuery} emptyHeadline="No peer data">
        {(data) => <PeerRankingStrip peers={data.peers} />}
      </DataGuard>

      {/* ===== 4. DMA x Brand Comparison ===== */}
      <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.24s" }}>
        <SectionHeader title="DMA × Brand Comparison" meta={`${CMP_ROWS.length} MARKETS`} />
        <div className="mt-3">
          <CmpTable
            brands={activeBrands}
            metric={cmpMetric}
            sortCol={cmpSort}
            sortDir={cmpDir}
            filter={cmpFilter}
            showAll={showAllRows}
            onSort={handleSort}
            onFilter={setCmpFilter}
            onToggleAll={() => setShowAllRows((p) => !p)}
            onMetric={setCmpMetric}
          />
        </div>
      </Card>
    </div>
  );
}
