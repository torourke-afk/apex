import { useShell } from "./ShellProvider";
import { NAV } from "../nav";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { useState, useEffect } from "react";

export function Rail() {
  const { view, setView, rail, toggleRail } = useShell();

  // Auto-collapse rail on screens narrower than 1024px
  const [isSmallScreen, setIsSmallScreen] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia("(max-width: 1023px)");
    const handler = (e: MediaQueryListEvent | MediaQueryList) => setIsSmallScreen(e.matches);
    handler(mq);
    mq.addEventListener("change", handler);
    return () => mq.removeEventListener("change", handler);
  }, []);

  // On small screens, force collapsed regardless of user preference
  const expanded = isSmallScreen ? false : rail;

  return (
    <nav
      aria-label="Main navigation"
      className="flex flex-col h-full border-r border-line bg-panel transition-[width] duration-200 ease-out"
      style={{ width: expanded ? 218 : 64 }}
    >
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-4 py-4">
        <div className="w-[26px] h-[26px] flex items-center justify-center">
          <div className="w-[9px] h-[9px] bg-cyan rotate-45" />
        </div>
        {expanded && (
          <span className="font-mono text-[13px] font-bold tracking-[.18em] text-fg">
            APEX
          </span>
        )}
      </div>

      {/* Nav items */}
      <div className="flex-1 overflow-y-auto py-2">
        {NAV.map((entry) => {
          const active = view === entry.view;
          const Icon = entry.icon;
          return (
            <button
              key={entry.view}
              onClick={() => setView(entry.view)}
              aria-label={`${entry.name}${entry.badge ? `, ${entry.badge} notifications` : ''}`}
              aria-current={active ? "page" : undefined}
              className={`
                relative flex items-center gap-3 w-full px-3 py-2 text-left
                transition-colors duration-150
                focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none
                ${active
                  ? "text-cyan"
                  : "text-fg3 hover:text-fg2"
                }
              `}
            >
              {/* Active indicator glow */}
              {active && (
                <div aria-hidden="true" className="absolute inset-y-0 left-0 w-[3px] rounded-r bg-cyan shadow-[0_0_8px_var(--cyan)]" />
              )}

              {/* Icon tile */}
              <div
                className={`
                  flex-none w-9 h-9 rounded-[10px] flex items-center justify-center
                  text-[11px] font-mono font-bold tracking-wider
                  transition-colors duration-150
                  ${active
                    ? "bg-[var(--cyan-hover)] text-cyan shadow-[0_0_12px_var(--cyan-hover)]"
                    : "bg-elev text-fg3"
                  }
                `}
              >
                <Icon size={18} strokeWidth={1.8} aria-hidden="true" />
              </div>

              {/* Label */}
              {expanded && (
                <span className={`text-[12.5px] font-medium truncate ${active ? "text-cyan" : ""}`}>
                  {entry.name}
                </span>
              )}

              {/* Badge */}
              {entry.badge && entry.badge > 0 && (
                <span className="absolute right-3 top-1/2 -translate-y-1/2 min-w-[18px] h-[18px] flex items-center justify-center rounded-full bg-critical text-[9px] font-mono font-bold text-white px-1">
                  {entry.badge}
                </span>
              )}
            </button>
          );
        })}
      </div>

      {/* Collapse toggle -- hidden on small screens where rail is always collapsed */}
      {!isSmallScreen && (
        <button
          onClick={toggleRail}
          aria-label={expanded ? "Collapse navigation" : "Expand navigation"}
          className="flex items-center justify-center gap-2 px-4 py-3 border-t border-line text-fg3 hover:text-fg2 transition-colors focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none"
        >
          {expanded ? <ChevronLeft size={16} aria-hidden="true" /> : <ChevronRight size={16} aria-hidden="true" />}
          {expanded && <span className="font-mono text-[11px] tracking-[.08em]">COLLAPSE</span>}
        </button>
      )}
    </nav>
  );
}
