import type { ReactNode } from "react";

interface CardProps {
  children: ReactNode;
  className?: string;
  accent?: boolean;   // cyan-bordered accent variant
  glow?: boolean;     // radial gradient glow background
  style?: React.CSSProperties;
}

export function Card({ children, className = "", accent, glow, style }: CardProps) {
  const base = "rounded-card border bg-panel";
  const border = accent
    ? "border-[var(--cyan-active)]"
    : "border-line hover:border-line-strong";
  const bg = glow
    ? "bg-[radial-gradient(130%_100%_at_100%_0%,var(--cyan-hover),var(--panel)_60%)]"
    : "";

  return (
    <div className={`${base} ${border} ${bg} ${className}`} style={style}>
      {children}
    </div>
  );
}
