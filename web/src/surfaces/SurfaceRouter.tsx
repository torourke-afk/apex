import { lazy, Suspense, useRef, useEffect, useState, type ComponentType } from "react";
import { useShell } from "../shell/ShellProvider";
import { ErrorBoundary } from "../ui/ErrorBoundary";
import { SkeletonCard } from "../ui/Skeleton";

/* ── Lazy-loaded surfaces ──────────────────────────────────── */

const Scorecard      = lazy(() => import("./Scorecard").then(m => ({ default: m.Scorecard })));
const Spend          = lazy(() => import("./Spend").then(m => ({ default: m.Spend })));
const Funnel         = lazy(() => import("./Funnel").then(m => ({ default: m.Funnel })));
const Media          = lazy(() => import("./Media").then(m => ({ default: m.Media })));
const Creative       = lazy(() => import("./Creative").then(m => ({ default: m.Creative })));
const Audience       = lazy(() => import("./Audience").then(m => ({ default: m.Audience })));
const BrandAwareness = lazy(() => import("./BrandAwareness").then(m => ({ default: m.BrandAwareness })));
const Product        = lazy(() => import("./Product").then(m => ({ default: m.Product })));
const Operations     = lazy(() => import("./Operations").then(m => ({ default: m.Operations })));
const Simulator      = lazy(() => import("./Simulator").then(m => ({ default: m.Simulator })));
const Retention      = lazy(() => import("./Retention").then(m => ({ default: m.Retention })));
const Modeling       = lazy(() => import("./Modeling").then(m => ({ default: m.Modeling })));
const SettingsView   = lazy(() => import("./SettingsView").then(m => ({ default: m.SettingsView })));

/* ── Surface map ───────────────────────────────────────────── */

const SURFACES: Record<string, ComponentType> = {
  scorecard: Scorecard,
  spend: Spend,
  funnel: Funnel,
  media: Media,
  creative: Creative,
  audience: Audience,
  brand: BrandAwareness,
  product: Product,
  operations: Operations,
  simulator: Simulator,
  retention: Retention,
  modeling: Modeling,
  settings: SettingsView,
};

/* ── Placeholder ───────────────────────────────────────────── */

function Placeholder({ title }: { title: string }) {
  return (
    <div className="flex items-center justify-center h-64 rounded-card border border-line bg-panel animate-rise">
      <div className="text-center">
        <div className="font-mono text-[10px] tracking-[.12em] text-fg3 mb-2">SURFACE</div>
        <div className="text-[18px] font-semibold">{title}</div>
        <div className="font-mono text-[11px] text-fg3 mt-2">Build in progress</div>
      </div>
    </div>
  );
}

/* ── Suspense fallback ─────────────────────────────────────── */

function SurfaceLoading() {
  return (
    <div className="space-y-4 p-2 animate-rise">
      <SkeletonCard />
      <SkeletonCard />
    </div>
  );
}

/* ── Fade transition wrapper ───────────────────────────────── */

function FadeTransition({ viewKey, children }: { viewKey: string; children: React.ReactNode }) {
  const [visible, setVisible] = useState(false);
  const prevKey = useRef(viewKey);

  useEffect(() => {
    if (viewKey !== prevKey.current) {
      setVisible(false);
      prevKey.current = viewKey;
      // Trigger fade-in on next frame
      const raf = requestAnimationFrame(() => setVisible(true));
      return () => cancelAnimationFrame(raf);
    } else {
      setVisible(true);
    }
  }, [viewKey]);

  return (
    <div
      className="transition-opacity duration-200 ease-out"
      style={{ opacity: visible ? 1 : 0 }}
    >
      {children}
    </div>
  );
}

/* ── Router ────────────────────────────────────────────────── */

export function SurfaceRouter() {
  const { view } = useShell();

  const Surface = SURFACES[view];
  const content = Surface
    ? <Surface />
    : <Placeholder title={view.charAt(0).toUpperCase() + view.slice(1)} />;

  return (
    <ErrorBoundary key={view}>
      <FadeTransition viewKey={view}>
        <Suspense fallback={<SurfaceLoading />}>
          {content}
        </Suspense>
      </FadeTransition>
    </ErrorBoundary>
  );
}
