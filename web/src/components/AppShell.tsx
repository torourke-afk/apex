"use client";
import { useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useTheme } from "@/lib/theme";
import { AgentConsole } from "./AgentConsole";
import { Atmosphere } from "./Atmosphere";

const NAV = [
  { href: "/", label: "Scorecard", icon: "▣" },
  { href: "/spend", label: "Spend", icon: "◧" },
  { href: "/channels", label: "Channels", icon: "◈" },
  { href: "/funnel", label: "Funnel", icon: "⧗" },
  { href: "/product", label: "Product & Ops", icon: "▦" },
  { href: "/simulator", label: "Simulator", icon: "⌗" },
  { href: "/retention", label: "Retention", icon: "◠" },
  { href: "/approvals", label: "Approvals", icon: "✓", badgeKey: "approvals" },
  { href: "/acquisition-engine", label: "Acquisition Engine", icon: "◎" },
  { href: "/launch", label: "Launch", icon: "▶" },
  { href: "/settings", label: "Settings", icon: "⚙" },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const { theme, toggle } = useTheme();
  const [expanded, setExpanded] = useState(true);

  return (
    <div className="relative z-[1] flex min-h-screen">
      <Atmosphere />
      {/* Left nav rail (expandable: icon + label) */}
      <nav
        aria-label="Primary"
        className={`sticky top-0 flex h-screen flex-col gap-1.5 border-r border-line bg-surface py-3 transition-[width] duration-200 ease-signal ${
          expanded ? "w-[200px] px-2" : "w-[60px] items-center"
        }`}
      >
        <div className="mb-2 flex items-center gap-2 px-1">
          <div className="flex h-9 w-9 flex-none items-center justify-center rounded-md bg-accent font-bold text-accent-ink">A</div>
          {expanded && <span className="text-[15px] font-semibold tracking-tight">Apex</span>}
          <button
            onClick={() => setExpanded((e) => !e)}
            aria-label={expanded ? "Collapse navigation" : "Expand navigation"}
            aria-expanded={expanded}
            className="ml-auto rounded p-1 text-fg-muted hover:text-fg"
          >
            {expanded ? "‹" : "›"}
          </button>
        </div>
        {NAV.map((n) => {
          const active = pathname === n.href;
          return (
            <Link
              key={n.href}
              href={n.href}
              aria-label={n.label}
              aria-current={active ? "page" : undefined}
              title={expanded ? undefined : n.label}
              className={`relative flex items-center gap-2.5 rounded-md text-[13px] font-medium transition-colors duration-150 ease-signal ${
                expanded ? "px-2.5 py-2" : "h-9 w-9 justify-center"
              } ${
                active
                  ? "bg-[color-mix(in_oklab,var(--color-accent)_18%,transparent)] text-accent"
                  : "text-fg-2 hover:bg-[color-mix(in_oklab,var(--color-accent)_12%,transparent)] hover:text-accent"
              }`}
            >
              <span className="text-[17px]" aria-hidden>{n.icon}</span>
              {expanded && <span className="truncate">{n.label}</span>}
              {n.badgeKey === "approvals" && (
                <span className={`flex h-4 min-w-4 items-center justify-center rounded-pill bg-critical px-1 text-[9px] font-bold text-white ${expanded ? "ml-auto" : "absolute right-0.5 top-0.5"}`}>
                  3
                </span>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Main column */}
      <div className="flex min-h-screen flex-1 flex-col">
        {/* Top context bar */}
        <header className="sticky top-0 z-10 flex h-[54px] items-center gap-3.5 border-b border-line bg-[color-mix(in_oklab,var(--color-bg-canvas)_86%,transparent)] px-5 backdrop-blur">
          <PageTitle pathname={pathname} />
          <Status />
          <div className="flex-1" />
          <span className="hidden text-xs text-fg-2 sm:inline">Fifth Third · BD Mode</span>
          <button
            onClick={toggle}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            className="rounded-pill border border-line bg-elevated px-3 py-1.5 text-xs font-semibold text-fg-2 transition-colors hover:text-fg"
          >
            ◐ {theme === "dark" ? "Light" : "Dark"}
          </button>
        </header>

        <main className="flex-1 px-5 py-5">{children}</main>

        <AgentConsole />
      </div>
    </div>
  );
}

function PageTitle({ pathname }: { pathname: string }) {
  const found = NAV.find((n) => n.href === pathname);
  const title =
    pathname === "/" ? "Executive Scorecard" : found?.label ?? "Apex";
  return <h1 className="text-base font-semibold">{title}</h1>;
}

function Status() {
  return (
    <div className="flex items-center gap-2 text-xs text-fg-2" role="status">
      <span
        className="h-2 w-2 rounded-pill bg-signal animate-beacon"
        aria-hidden
      />
      <span className="text-signal">all systems nominal</span>
    </div>
  );
}
