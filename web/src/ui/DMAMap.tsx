import { useState, useMemo } from "react";
import { ChartTooltip } from "./ChartTooltip";
import { US_STATE_PATHS, STATE_LABEL_CENTROIDS } from "./us-states";

/* ------------------------------------------------------------------ */
/*  Types                                                              */
/* ------------------------------------------------------------------ */

export interface DMAMapDatum {
  dma: string;
  code: string;
  value: number;
  spend: number;
  cpihh: number;
  /** Albers USA projected centroid X */
  cx?: number;
  /** Albers USA projected centroid Y */
  cy?: number;
  /** Suggested circle radius */
  r?: number;
}

interface DMAMapProps {
  data: DMAMapDatum[];
  metric: "spend" | "cpihh";
  className?: string;
}

/* ------------------------------------------------------------------ */
/*  Full US viewport (standard Albers USA: 960 × 600)                  */
/* ------------------------------------------------------------------ */

const FULL_US = { x: 55, y: 0, w: 910, h: 590 };

/* ------------------------------------------------------------------ */
/*  Auto-fit viewBox from DMA centroids                                */
/* ------------------------------------------------------------------ */

function computeViewBox(data: DMAMapDatum[]): {
  x: number;
  y: number;
  w: number;
  h: number;
} {
  const withPos = data.filter((d) => d.cx != null && d.cy != null);
  if (withPos.length === 0) return FULL_US;

  let minX = Infinity,
    maxX = -Infinity,
    minY = Infinity,
    maxY = -Infinity;
  for (const d of withPos) {
    const r = d.r ?? 20;
    minX = Math.min(minX, d.cx! - r);
    maxX = Math.max(maxX, d.cx! + r);
    minY = Math.min(minY, d.cy! - r);
    maxY = Math.max(maxY, d.cy! + r);
  }

  // Add generous padding (30% of span, minimum 80px)
  const spanX = maxX - minX;
  const spanY = maxY - minY;
  const padX = Math.max(80, spanX * 0.30);
  const padY = Math.max(80, spanY * 0.30);

  const vb = {
    x: Math.max(0, minX - padX),
    y: Math.max(0, minY - padY),
    w: Math.min(960, spanX + padX * 2),
    h: Math.min(600, spanY + padY * 2),
  };

  // Enforce minimum aspect ratio so the map doesn't get too narrow
  const minW = 250;
  const minH = 200;
  if (vb.w < minW) {
    const cx = vb.x + vb.w / 2;
    vb.x = cx - minW / 2;
    vb.w = minW;
  }
  if (vb.h < minH) {
    const cy = vb.y + vb.h / 2;
    vb.y = cy - minH / 2;
    vb.h = minH;
  }

  return vb;
}

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function quantize(value: number, min: number, max: number): number {
  if (max === min) return 0.5;
  return Math.max(0, Math.min(1, (value - min) / (max - min)));
}

function intensityFill(t: number): string {
  const pct = Math.round(18 + t * 62);
  return `color-mix(in srgb, var(--cyan) ${pct}%, transparent)`;
}

function intensityStroke(t: number): string {
  const pct = Math.round(30 + t * 50);
  return `color-mix(in srgb, var(--cyan) ${pct}%, transparent)`;
}

function fmt$(v: number): string {
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(2)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

/** Short label (max 3 chars) from market name */
function shortLabel(dma: string): string {
  // "Cincinnati, OH" → "CIN", "New York, NY" → "NYC", "Los Angeles, CA" → "LAX"
  const SPECIAL: Record<string, string> = {
    "New York": "NYC",
    "Los Angeles": "LAX",
    "San Francisco": "SFO",
    "Washington": "DCA",
    "Dallas": "DFW",
  };
  const city = dma.split(",")[0].trim();
  return SPECIAL[city] ?? city.substring(0, 3).toUpperCase();
}

/** Smart label placement — avoid overlapping the circle */
function labelPos(
  cx: number,
  cy: number,
  r: number,
  vb: { x: number; y: number; w: number; h: number },
): { x: number; y: number; anchor: "start" | "middle" | "end" } {
  const midX = vb.x + vb.w / 2;
  const midY = vb.y + vb.h / 2;
  const gap = 4;

  // If market is in the right half → label goes right; left half → label goes left
  // Bottom third → label goes above
  if (cy > midY + vb.h * 0.2) {
    // Bottom area — put label above or to the side
    if (cx > midX) {
      return { x: cx + r + gap, y: cy, anchor: "start" };
    }
    return { x: cx - r - gap, y: cy, anchor: "end" };
  }
  // Default: label below
  if (cx > midX + vb.w * 0.15) {
    return { x: cx + r + gap, y: cy, anchor: "start" };
  }
  if (cx < midX - vb.w * 0.15) {
    return { x: cx - r - gap, y: cy, anchor: "end" };
  }
  return { x: cx, y: cy + r + 8, anchor: "middle" };
}

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

export function DMAMap({ data, metric, className = "" }: DMAMapProps) {
  const [hover, setHover] = useState<{
    datum: DMAMapDatum;
    x: number;
    y: number;
  } | null>(null);

  /* Compute auto-fit viewBox from data centroids */
  const vb = useMemo(() => computeViewBox(data), [data]);

  /* Dynamic scale for font sizes and strokes based on viewBox */
  const scale = useMemo(() => Math.max(1, vb.w / 360), [vb.w]);

  /* Value range for colour scaling */
  const { minVal, maxVal } = useMemo(() => {
    const vals = data
      .filter((d) => d.cx != null)
      .map((d) => (metric === "spend" ? d.spend : d.cpihh));
    if (vals.length === 0) return { minVal: 0, maxVal: 1 };
    return { minVal: Math.min(...vals), maxVal: Math.max(...vals) };
  }, [data, metric]);

  /* Markets with valid centroid positions */
  const marketsWithPos = useMemo(
    () => data.filter((d) => d.cx != null && d.cy != null),
    [data],
  );

  /* Which state IDs should be visible (all within viewBox) */
  const visibleStates = useMemo(() => {
    // Show all states whose label centroid falls within the viewBox (with padding)
    const pad = 60;
    return US_STATE_PATHS.filter((st) => {
      const c = STATE_LABEL_CENTROIDS[st.id];
      if (!c) return true; // Show if no centroid (rare)
      return (
        c[0] >= vb.x - pad &&
        c[0] <= vb.x + vb.w + pad &&
        c[1] >= vb.y - pad &&
        c[1] <= vb.y + vb.h + pad
      );
    });
  }, [vb]);

  /* State labels that fit in the viewBox */
  const visibleLabels = useMemo(() => {
    return Object.entries(STATE_LABEL_CENTROIDS).filter(
      ([, pos]) =>
        pos[0] >= vb.x + 5 &&
        pos[0] <= vb.x + vb.w - 5 &&
        pos[1] >= vb.y + 5 &&
        pos[1] <= vb.y + vb.h - 5,
    );
  }, [vb]);

  const marketCount = marketsWithPos.length;
  const isNarrow = vb.w < 400;

  return (
    <svg
      viewBox={`${vb.x} ${vb.y} ${vb.w} ${vb.h}`}
      className={`w-full ${className}`}
      style={{ minHeight: 280 }}
      role="img"
      aria-label={`DMA market map showing ${metric === "spend" ? "spend intensity" : "cost per incremental household"} across ${marketCount} markets`}
    >
      <title>DMA Market Map</title>

      <defs>
        {/* Soft glow behind each DMA circle */}
        <filter id="dmaGlow" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation={3 * scale * 0.4} result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
        <filter id="dmaGlowHover" x="-50%" y="-50%" width="200%" height="200%">
          <feGaussianBlur stdDeviation={5 * scale * 0.4} result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
        {/* Legend gradient */}
        <linearGradient id="dmaLegGrad" x1="0" y1="0" x2="1" y2="0">
          <stop offset="0%" stopColor="var(--cyan)" stopOpacity="0.18" />
          <stop offset="50%" stopColor="var(--cyan)" stopOpacity="0.50" />
          <stop offset="100%" stopColor="var(--cyan)" stopOpacity="0.80" />
        </linearGradient>
      </defs>

      {/* ── State outlines ─────────────────────────────────────────── */}
      {visibleStates.map((st) => (
        <path
          key={st.id}
          d={st.d}
          fill="var(--panel2)"
          stroke="var(--line2)"
          strokeWidth={0.8 * (scale * 0.4)}
          strokeLinejoin="round"
          aria-label={st.name}
        />
      ))}

      {/* ── State abbreviation labels (subtle) ─────────────────────── */}
      {visibleLabels.map(([abbr, pos]) => (
        <text
          key={`stlbl-${abbr}`}
          x={pos[0]}
          y={pos[1]}
          textAnchor="middle"
          dominantBaseline="central"
          className="font-mono"
          style={{
            fontSize: isNarrow ? 7 : 9 * (scale * 0.5),
            fill: "var(--text3)",
            pointerEvents: "none",
            letterSpacing: "0.14em",
            opacity: 0.35,
          }}
        >
          {abbr}
        </text>
      ))}

      {/* ── DMA market regions ─────────────────────────────────────── */}
      {marketsWithPos.map((datum) => {
        const val = metric === "spend" ? datum.spend : datum.cpihh;
        const t = quantize(val, minVal, maxVal);
        const isHovered = hover?.datum.code === datum.code;
        const baseR = datum.r ?? 18;
        const r = isHovered ? baseR + 2 : baseR;
        const lp = labelPos(datum.cx!, datum.cy!, baseR, vb);

        return (
          <g key={datum.code}>
            {/* Dashed range ring */}
            <circle
              cx={datum.cx}
              cy={datum.cy}
              r={baseR + 5}
              fill="none"
              stroke={intensityStroke(t)}
              strokeWidth={0.6 * (scale * 0.4)}
              strokeDasharray={`${2.5 * scale * 0.4} ${2 * scale * 0.4}`}
              style={{
                opacity: isHovered ? 0.7 : 0.3,
                transition: "opacity 0.2s ease",
              }}
            />

            {/* Main DMA circle */}
            <circle
              cx={datum.cx}
              cy={datum.cy}
              r={r}
              fill={intensityFill(t)}
              stroke={isHovered ? "var(--cyan)" : intensityStroke(t)}
              strokeWidth={isHovered ? 1.4 * (scale * 0.4) : 0.7 * (scale * 0.4)}
              style={{
                cursor: "crosshair",
                transition: "all 0.2s ease",
                filter: isHovered ? "url(#dmaGlowHover)" : "url(#dmaGlow)",
              }}
              onMouseEnter={() =>
                setHover({ datum, x: datum.cx!, y: datum.cy! })
              }
              onMouseLeave={() => setHover(null)}
              aria-label={`${datum.dma}: ${metric === "spend" ? fmt$(datum.spend) : `$${datum.cpihh}`}`}
            />

            {/* Center dot */}
            <circle
              cx={datum.cx}
              cy={datum.cy}
              r={2 * (scale * 0.4)}
              fill="var(--cyan)"
              style={{ pointerEvents: "none", opacity: 0.9 }}
            />

            {/* DMA label */}
            <text
              x={lp.x}
              y={lp.y}
              textAnchor={lp.anchor}
              dominantBaseline="central"
              className="font-mono"
              style={{
                fontSize: isNarrow ? 6.5 : 8 * (scale * 0.45),
                fill: isHovered ? "var(--cyan)" : "var(--text)",
                pointerEvents: "none",
                letterSpacing: "0.08em",
                fontWeight: isHovered ? 600 : 500,
                transition: "fill 0.15s ease",
              }}
            >
              {shortLabel(datum.dma)}
            </text>
          </g>
        );
      })}

      {/* ── Legend bar ──────────────────────────────────────────────── */}
      <rect
        x={vb.x + 12}
        y={vb.y + vb.h - 26}
        width={70 * (scale * 0.5)}
        height={4 * (scale * 0.4)}
        rx={2}
        fill="url(#dmaLegGrad)"
      />
      <text
        x={vb.x + 12}
        y={vb.y + vb.h - 32}
        className="font-mono"
        style={{
          fontSize: (isNarrow ? 5.5 : 7) * (scale * 0.45),
          fill: "var(--text3)",
          letterSpacing: "0.1em",
        }}
      >
        LOW
      </text>
      <text
        x={vb.x + 12 + 70 * (scale * 0.5)}
        y={vb.y + vb.h - 32}
        textAnchor="end"
        className="font-mono"
        style={{
          fontSize: (isNarrow ? 5.5 : 7) * (scale * 0.45),
          fill: "var(--text3)",
          letterSpacing: "0.1em",
        }}
      >
        HIGH
      </text>
      <text
        x={vb.x + 12}
        y={vb.y + vb.h - 14}
        className="font-mono"
        style={{
          fontSize: (isNarrow ? 5.5 : 7) * (scale * 0.45),
          fill: "var(--text3)",
        }}
      >
        {metric === "spend" ? "SPEND INTENSITY" : "CPIHH"}
      </text>

      {/* ── Tooltip ────────────────────────────────────────────────── */}
      <ChartTooltip
        x={hover?.x ?? 0}
        y={hover?.y ?? 0}
        visible={hover !== null}
        viewBoxWidth={vb.x + vb.w}
        viewBoxHeight={vb.y + vb.h}
      >
        {hover && (
          <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
            <div
              style={{
                fontWeight: 600,
                color: "var(--text)",
                marginBottom: 2,
                borderBottom: "1px solid var(--line)",
                paddingBottom: 3,
              }}
            >
              {hover.datum.dma}
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 16,
              }}
            >
              <span style={{ color: "var(--text3)" }}>Spend</span>
              <span style={{ fontWeight: 600, color: "var(--cyan)" }}>
                {fmt$(hover.datum.spend)}
              </span>
            </div>
            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                gap: 16,
              }}
            >
              <span style={{ color: "var(--text3)" }}>CPIHH</span>
              <span style={{ fontWeight: 600 }}>${hover.datum.cpihh}</span>
            </div>
          </div>
        )}
      </ChartTooltip>
    </svg>
  );
}
