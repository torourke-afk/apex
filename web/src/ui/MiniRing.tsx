interface MiniRingProps {
  pct: number;
  color: string;
  size?: number;
}

export function MiniRing({ pct, color, size = 56 }: MiniRingProps) {
  const r = 24;
  const c = 2 * Math.PI * r;
  const offset = c * (1 - pct / 100);
  const label = pct >= 100 ? "✓" : String(Math.round(pct));

  return (
    <svg width={size} height={size} viewBox="0 0 60 60" className="animate-ringkpi" role="img" aria-label={`${pct}%`}>
      <circle cx="30" cy="30" r={r} fill="none" stroke="var(--line)" strokeWidth="5" />
      <circle
        cx="30" cy="30" r={r}
        fill="none" stroke={color} strokeWidth="5"
        strokeLinecap="round"
        strokeDasharray={c.toFixed(1)}
        strokeDashoffset={offset.toFixed(1)}
        transform="rotate(-90 30 30)"
      />
      <text
        x="30" y="34"
        textAnchor="middle"
        className="font-mono text-[13px] font-medium"
        fill="var(--text)"
      >
        {label}
      </text>
    </svg>
  );
}
