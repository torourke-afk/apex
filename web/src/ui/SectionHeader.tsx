interface SectionHeaderProps {
  title: string;
  meta?: string;
  accent?: "cyan" | "red" | "green" | "amber";
}

const ACCENT_COLORS = {
  cyan: "bg-cyan",
  red: "bg-critical",
  green: "bg-positive",
  amber: "bg-warning",
};

export function SectionHeader({ title, meta, accent = "cyan" }: SectionHeaderProps) {
  return (
    <div className="flex items-center justify-between">
      <div className="flex items-center gap-2.5">
        <div className={`w-[3px] h-[15px] rounded-[3px] ${ACCENT_COLORS[accent]}`} />
        <span className="text-[14px] font-semibold">{title}</span>
      </div>
      {meta && (
        <span className="font-mono text-[9.5px] tracking-[.1em] text-fg3">{meta}</span>
      )}
    </div>
  );
}
