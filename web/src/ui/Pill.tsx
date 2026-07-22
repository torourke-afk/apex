import type { ReactNode } from "react";

type PillVariant = "cyan" | "green" | "amber" | "red" | "neutral";

interface PillProps {
  children: ReactNode;
  variant?: PillVariant;
  dot?: boolean;
  className?: string;
}

const VARIANTS: Record<PillVariant, { text: string; bg: string; dotColor: string }> = {
  cyan:    { text: "text-cyan",     bg: "bg-[var(--cyan-hover)]",       dotColor: "var(--cyan)" },
  green:   { text: "text-positive", bg: "bg-[rgba(79,216,155,.14)]",   dotColor: "var(--green)" },
  amber:   { text: "text-warning",  bg: "bg-[rgba(242,177,76,.14)]",   dotColor: "var(--amber)" },
  red:     { text: "text-critical", bg: "bg-[rgba(255,92,114,.14)]",   dotColor: "var(--red)" },
  neutral: { text: "text-fg3",      bg: "bg-panel2",                    dotColor: "var(--text3)" },
};

export function Pill({ children, variant = "neutral", dot, className = "" }: PillProps) {
  const v = VARIANTS[variant];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-[6px] font-mono text-[9px] tracking-[.06em] ${v.text} ${v.bg} ${className}`}>
      {dot && (
        <span
          className="w-[6px] h-[6px] rounded-full flex-none"
          style={{ background: v.dotColor, boxShadow: `0 0 7px ${v.dotColor}` }}
        />
      )}
      {children}
    </span>
  );
}
