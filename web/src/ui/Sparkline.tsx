interface SparklineProps {
  data: number[];
  color: string;
  width?: number;
  height?: number;
}

export function Sparkline({ data, color, width = 92, height = 28 }: SparklineProps) {
  if (data.length < 2) return null;

  const mn = Math.min(...data);
  const mx = Math.max(...data);
  const rng = mx - mn || 1;

  const points = data
    .map((v, i) => {
      const x = (i * width) / (data.length - 1);
      const y = height - 4 - ((v - mn) / rng) * (height - 8);
      return `${x.toFixed(1)},${y.toFixed(1)}`;
    })
    .join(" ");

  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} fill="none" aria-hidden="true">
      <polyline
        points={points}
        stroke={color}
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}
