interface SegmentedProps<T extends string> {
  options: T[];
  value: T;
  onChange: (v: T) => void;
  size?: "sm" | "md";
}

export function Segmented<T extends string>({ options, value, onChange, size = "md" }: SegmentedProps<T>) {
  const pad = size === "sm" ? "px-2.5 py-1" : "px-3 py-1.5";
  const font = size === "sm" ? "text-[9px]" : "text-[10px]";

  return (
    <div className="flex gap-1 p-1 rounded-[10px] border border-line bg-panel2" role="radiogroup">
      {options.map(opt => {
        const isActive = value === opt;
        return (
        <button
          key={opt}
          role="radio"
          aria-checked={isActive}
          onClick={() => onChange(opt)}
          className={`
            ${pad} rounded-pill font-mono ${font} font-semibold tracking-[.06em]
            transition-colors duration-150
            focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none
            ${isActive
              ? "bg-cyan text-cyan-ink"
              : "text-fg3 hover:text-fg2"
            }
          `}
        >
          {opt.toUpperCase()}
        </button>
        );
      })}
    </div>
  );
}
