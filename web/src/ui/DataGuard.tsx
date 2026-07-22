/**
 * DataGuard — async-state wrapper.
 *
 * Takes the standard Async<T> shape from our hooks
 * (`{ data, loading, error, reload }`) and renders
 * Skeleton / ErrorRetry / Empty / children automatically.
 *
 * Usage:
 *   const kpi = useScorecard();
 *   <DataGuard {...kpi} skeleton={<SkeletonCard />}>
 *     {(data) => <RealContent data={data} />}
 *   </DataGuard>
 */

import { type ReactNode } from "react";
import { Skeleton } from "./Skeleton";
import { ErrorRetry } from "./ErrorRetry";
import { Empty } from "./Empty";

interface DataGuardProps<T> {
  /** Data value (null while loading or on error) */
  data: T | null;
  /** Is the fetch in-flight? */
  loading: boolean;
  /** Error message, if any */
  error: string | null;
  /** Refetch callback */
  reload?: () => void;
  /** Custom skeleton (default: 4 rows) */
  skeleton?: ReactNode;
  /** Custom empty-state headline */
  emptyHeadline?: string;
  /** Custom empty-state body */
  emptyBody?: string;
  /** Render children when data is available */
  children: (data: T) => ReactNode;
  /** Extra Tailwind classes on the wrapper */
  className?: string;
}

export function DataGuard<T>({
  data,
  loading,
  error,
  reload,
  skeleton,
  emptyHeadline,
  emptyBody,
  children,
  className = "",
}: DataGuardProps<T>) {
  // Loading state
  if (loading && data === null) {
    return (
      <div className={className}>
        {skeleton ?? <Skeleton rows={4} />}
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className={className}>
        <ErrorRetry message={error} onRetry={reload} />
      </div>
    );
  }

  // Empty state — data resolved but is empty-ish
  if (data === null || data === undefined) {
    return (
      <div className={className}>
        <Empty headline={emptyHeadline} body={emptyBody} />
      </div>
    );
  }

  // Also check arrays
  if (Array.isArray(data) && data.length === 0) {
    return (
      <div className={className}>
        <Empty
          headline={emptyHeadline ?? "No results"}
          body={emptyBody ?? "Try adjusting your filters."}
        />
      </div>
    );
  }

  // Data is available — render children
  return <>{children(data)}</>;
}
