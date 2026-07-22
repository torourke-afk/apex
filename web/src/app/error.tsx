"use client";
import { ErrorState } from "@/components/primitives";

export default function Error({ reset }: { error: Error; reset: () => void }) {
  return (
    <div className="mx-auto max-w-lg pt-10">
      <ErrorState message="Something went wrong loading this screen." onRetry={reset} />
    </div>
  );
}
