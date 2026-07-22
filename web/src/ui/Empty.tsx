/**
 * Empty — empty-state guidance placeholder.
 *
 * Shown when a query returns no data. Displays an icon, headline, and
 * optional guidance text.
 */

interface EmptyProps {
  /** Primary headline (default: "No data") */
  headline?: string;
  /** Secondary guidance text */
  body?: string;
  /** Extra Tailwind classes */
  className?: string;
}

export function Empty({
  headline = "No data",
  body,
  className = "",
}: EmptyProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center py-16 px-6 text-center ${className}`}
      role="status"
    >
      {/* Ghost icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="40"
        height="40"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-fg3 mb-4 opacity-50"
        aria-hidden="true"
      >
        <rect x="3" y="3" width="18" height="18" rx="2" />
        <path d="M9 14l2 2 4-4" opacity="0.3" />
        <line x1="8" y1="9" x2="16" y2="9" opacity="0.5" />
      </svg>

      <p className="font-ui text-sm text-fg2 font-medium mb-1">
        {headline}
      </p>

      {body && (
        <p className="font-mono text-[10px] text-fg3 max-w-[280px] leading-relaxed">
          {body}
        </p>
      )}
    </div>
  );
}
