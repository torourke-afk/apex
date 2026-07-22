import type { ReactNode } from "react";

interface ChartTooltipProps {
  x: number;
  y: number;
  visible: boolean;
  children: ReactNode;
  /** Width of the SVG viewBox — used to flip tooltip when near right edge */
  viewBoxWidth?: number;
  /** Height of the SVG viewBox — used to flip tooltip when near bottom edge */
  viewBoxHeight?: number;
}

/**
 * Floating SVG tooltip rendered via foreignObject.
 * Positions itself offset from (x, y) and flips when near edges.
 * pointer-events: none so it never captures the mouse.
 */
export function ChartTooltip({
  x,
  y,
  visible,
  children,
  viewBoxWidth = 800,
  viewBoxHeight = 400,
}: ChartTooltipProps) {
  const OFFSET_X = 12;
  const OFFSET_Y = -8;
  const TIP_W = 160;
  const TIP_H = 120;

  // Flip horizontally if too close to the right edge
  const flipX = x + OFFSET_X + TIP_W > viewBoxWidth - 10;
  const tx = flipX ? x - OFFSET_X - TIP_W : x + OFFSET_X;

  // Flip vertically if too close to the top
  const flipY = y + OFFSET_Y < 10;
  const ty = flipY ? y + 12 : y + OFFSET_Y - TIP_H + 20;

  return (
    <foreignObject
      x={tx}
      y={ty}
      width={TIP_W}
      height={TIP_H}
      style={{
        pointerEvents: "none",
        opacity: visible ? 1 : 0,
        transition: "opacity 0.15s ease",
        overflow: "visible",
      }}
    >
      <div
        style={{
          pointerEvents: "none",
          background: "var(--panel2)",
          border: "1px solid var(--line)",
          borderRadius: 8,
          boxShadow: "0 4px 16px rgba(0,0,0,.35)",
          padding: "6px 10px",
          fontFamily: "'JetBrains Mono', monospace",
          fontSize: 10,
          color: "var(--text)",
          width: "max-content",
          maxWidth: TIP_W,
        }}
      >
        {children}
      </div>
    </foreignObject>
  );
}
