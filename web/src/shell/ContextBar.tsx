import { useShell } from "./ShellProvider";
import { NAV } from "../nav";
import { Sun, Moon } from "lucide-react";

export function ContextBar() {
  const { view, theme, setTheme, mode, setMode } = useShell();
  const entry = NAV.find(n => n.view === view) ?? NAV[0];

  return (
    <header className="flex items-center h-[60px] px-3 md:px-5 border-b border-line bg-header-bg backdrop-blur-md gap-2">
      {/* Breadcrumb + title */}
      <div className="flex items-center gap-2 md:gap-3 min-w-0">
        <span className="font-mono text-[9px] tracking-[.14em] text-fg3 hidden md:inline">
          {entry.crumb}
        </span>
        <span className="text-[16px] md:text-[18px] font-semibold truncate">{entry.title}</span>
      </div>

      <div className="flex-1" />

      {/* Sync pill -- hidden on small screens */}
      <div role="status" aria-live="polite" className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-pill border border-line mr-4">
        <div className="w-[6px] h-[6px] rounded-full bg-positive shadow-[0_0_7px_var(--green)]" />
        <span className="font-mono text-[10px] tracking-[.08em] text-fg2">SYNCED · 2m AGO</span>
      </div>

      {/* Client badge -- compact on small screens */}
      <div className="hidden md:flex items-center gap-2 mr-4">
        <div className="w-[18px] h-[18px] rounded-[5px] bg-gradient-to-br from-[#1a5d9e] to-[#0d2d4d] flex items-center justify-center">
          <span className="text-[7px] font-mono font-bold text-white">5/3</span>
        </div>
        <span className="font-mono text-[10px] text-fg2">Fifth Third</span>
        <span className="font-mono text-[9px] text-fg3 hidden lg:inline">+ 2 RV VALIDATION</span>
      </div>

      {/* BD / CLIENT toggle */}
      <div role="group" aria-label="Mode selector" className="flex gap-1 p-1 rounded-pill border border-line bg-panel2 mr-2 md:mr-4">
        {(["BD", "Client"] as const).map(m => (
          <button
            key={m}
            onClick={() => setMode(m)}
            aria-pressed={mode === m}
            className={`
              px-2 md:px-3 py-1 rounded-[6px] font-mono text-[10px] font-semibold tracking-[.06em]
              transition-colors duration-150
              focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none
              ${mode === m
                ? "bg-cyan text-cyan-ink"
                : "text-fg3 hover:text-fg2"
              }
            `}
          >
            {m.toUpperCase()}
          </button>
        ))}
      </div>

      {/* Theme toggle */}
      <button
        onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        aria-label={theme === "dark" ? "Switch to light theme" : "Switch to dark theme"}
        className="w-9 h-9 rounded-[10px] border border-line bg-panel2 flex items-center justify-center text-fg3 hover:text-fg2 transition-colors focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none flex-none"
      >
        {theme === "dark" ? <Sun size={16} aria-hidden="true" /> : <Moon size={16} aria-hidden="true" />}
      </button>
    </header>
  );
}
