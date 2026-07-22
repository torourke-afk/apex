import { Skeleton } from "@/components/primitives";

export default function Loading() {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-12" />
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} className="h-[104px]" />)}
      </div>
      <Skeleton className="h-64" />
    </div>
  );
}
