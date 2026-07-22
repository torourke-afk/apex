/**
 * Skeleton — shimmer loading placeholder.
 *
 * Renders animated pulsing bars that match the layout being loaded.
 * Use `<Skeleton />` for a single line, `<Skeleton rows={4} />` for a table,
 * or `<SkeletonCard />` for a full card placeholder.
 */

interface SkeletonProps {
  /** Width class (default: "w-full") */
  width?: string;
  /** Height class (default: "h-3") */
  height?: string;
  /** Render multiple rows */
  rows?: number;
  /** Extra Tailwind classes */
  className?: string;
}

export function Skeleton({
  width = "w-full",
  height = "h-3",
  rows = 1,
  className = "",
}: SkeletonProps) {
  return (
    <div className={`flex flex-col gap-2.5 ${className}`} role="status" aria-label="Loading">
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className={`${width} ${height} rounded-[4px] bg-line animate-pulse`}
          style={i % 2 === 1 ? { width: "75%" } : undefined}
        />
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}

/** Card-shaped skeleton with header + body rows. */
export function SkeletonCard({ className = "" }: { className?: string }) {
  return (
    <div
      className={`rounded-card border border-line bg-panel p-5 ${className}`}
      role="status"
      aria-label="Loading"
    >
      {/* Header bar */}
      <div className="h-3 w-1/3 rounded-[4px] bg-line animate-pulse mb-4" />
      {/* Large value */}
      <div className="h-7 w-1/2 rounded-[4px] bg-line animate-pulse mb-3" />
      {/* Sub-line */}
      <div className="h-2.5 w-1/4 rounded-[4px] bg-line animate-pulse" />
      <span className="sr-only">Loading…</span>
    </div>
  );
}

/** Table skeleton — header row + N body rows */
export function SkeletonTable({
  cols = 4,
  rows = 5,
  className = "",
}: {
  cols?: number;
  rows?: number;
  className?: string;
}) {
  return (
    <div
      className={`rounded-card border border-line bg-panel p-4 ${className}`}
      role="status"
      aria-label="Loading table"
    >
      {/* Header */}
      <div className="flex gap-3 mb-3 pb-3 border-b border-line">
        {Array.from({ length: cols }, (_, i) => (
          <div
            key={i}
            className="h-3 rounded-[4px] bg-line animate-pulse flex-1"
          />
        ))}
      </div>
      {/* Rows */}
      {Array.from({ length: rows }, (_, r) => (
        <div key={r} className="flex gap-3 mb-2.5">
          {Array.from({ length: cols }, (_, c) => (
            <div
              key={c}
              className="h-2.5 rounded-[4px] bg-line animate-pulse flex-1"
              style={{ opacity: 0.5 + Math.random() * 0.5 }}
            />
          ))}
        </div>
      ))}
      <span className="sr-only">Loading…</span>
    </div>
  );
}
