/**
 * ErrorRetry — error state with retry button.
 *
 * Displays the error message and a RETRY button that calls `onRetry`.
 */

interface ErrorRetryProps {
  /** Error message to display */
  message: string;
  /** Retry callback */
  onRetry?: () => void;
  /** Extra Tailwind classes */
  className?: string;
}

export function ErrorRetry({
  message,
  onRetry,
  className = "",
}: ErrorRetryProps) {
  return (
    <div
      className={`flex flex-col items-center justify-center py-12 px-6 text-center ${className}`}
      role="alert"
    >
      {/* Warning icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="32"
        height="32"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="text-critical mb-3"
        aria-hidden="true"
      >
        <circle cx="12" cy="12" r="10" />
        <line x1="12" y1="8" x2="12" y2="12" />
        <line x1="12" y1="16" x2="12.01" y2="16" />
      </svg>

      <p className="font-mono text-[11px] text-fg2 mb-3 max-w-[340px] leading-relaxed">
        {message}
      </p>

      {onRetry && (
        <button
          onClick={onRetry}
          className="px-4 py-1.5 rounded-pill border border-line bg-panel2 font-mono text-[10px] tracking-[.06em] text-fg2 hover:border-cyan hover:text-cyan transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none"
        >
          ↻ RETRY
        </button>
      )}
    </div>
  );
}
