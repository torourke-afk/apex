import { useEffect, useRef } from "react";
import { Rail } from "./Rail";
import { ContextBar } from "./ContextBar";
import { FilterBar } from "./FilterBar";
import { AgentConsole } from "./AgentConsole";
import { Atmosphere } from "./Atmosphere";
import { useShell } from "./ShellProvider";
import { NAV } from "../nav";
import { SurfaceRouter } from "../surfaces/SurfaceRouter";

/**
 * Force-restart CSS animations on all animated descendants.
 *
 * When React recreates DOM via `key={view}`, the browser sometimes
 * doesn't detect new CSS animations on freshly-inserted elements
 * (elements with `animation-fill-mode: both` stay at their initial
 * keyframe state — opacity 0). This function clears and re-applies
 * the animation property so the browser sees a fresh trigger.
 */
function restartAnimations(root: HTMLElement) {
  const sel =
    ".animate-rise, .animate-rise-slow, .animate-wirein, .animate-ringhero, .animate-ringkpi";
  root.querySelectorAll(sel).forEach((node) => {
    const el = node as HTMLElement;
    el.style.animation = "none";
    void el.offsetHeight; // force reflow
    el.style.animation = "";
  });
  // Also check root itself
  if (root.matches?.(sel)) {
    root.style.animation = "none";
    void root.offsetHeight;
    root.style.animation = "";
  }
}

export function AppShell() {
  const { view } = useShell();
  const showFilter = view !== "settings" && view !== "brand";  // Filter bar on all surfaces except Settings and Awareness (which has its own)
  const mainRef = useRef<HTMLElement>(null);

  // After every surface transition, force-restart CSS animations.
  // Two passes: one immediate (for static content) and one after
  // 200 ms (to catch content that appears once hook loading resolves).
  useEffect(() => {
    const el = mainRef.current;
    if (!el) return;

    const raf = requestAnimationFrame(() => restartAnimations(el));
    const timer = setTimeout(() => restartAnimations(el), 200);

    return () => {
      cancelAnimationFrame(raf);
      clearTimeout(timer);
    };
  }, [view]);

  return (
    <div className="flex h-screen overflow-hidden relative">
      {/* Atmosphere behind everything */}
      <Atmosphere />

      {/* Rail */}
      <div className="relative z-10 flex-none h-full">
        <Rail />
      </div>

      {/* Main content area */}
      <div className="relative z-10 flex-1 flex flex-col min-w-0 h-full">
        <ContextBar />
        {showFilter && <FilterBar />}

        {/* Surface content */}
        <main ref={mainRef} className="flex-1 overflow-y-auto px-3 md:px-5 py-3 md:py-4" key={view}>
          <SurfaceRouter />
        </main>

        <AgentConsole />
      </div>
    </div>
  );
}
