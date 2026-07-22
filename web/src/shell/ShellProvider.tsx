import { createContext, useContext, useState, useEffect, useCallback, type ReactNode } from "react";
import { DEFAULT_VIEW } from "../nav";

type Theme = "dark" | "light";
type Mode = "Client" | "BD";
type Autopilot = "Off" | "Assist" | "Auto";
export type Density = "comfortable" | "compact";
export type ExportFormat = "XLSX" | "CSV" | "PDF";

/* ── Filter system ─────────────────────────────────────────────── */

export const DATE_RANGE_OPTIONS = [
  "Last 4 weeks",
  "Last 12 weeks",
  "Last 26 weeks",
  "YTD",
] as const;

export const PRODUCT_OPTIONS = [
  "Checking",
  "Savings",
  "CD",
  "Money Market",
  "Mortgage",
] as const;

export const DMA_OPTIONS = [
  // Tier 1 — Midwest core
  "Cincinnati (515)",
  "Chicago (602)",
  "Columbus (535)",
  "Indianapolis (527)",
  "Detroit (505)",
  "Cleveland (510)",
  // Tier 2 — Southeast
  "Atlanta (524)",
  "Nashville (659)",
  "Charlotte (517)",
  "Louisville (529)",
  "Raleigh (508)",
  // Tier 3 — National
  "New York (501)",
  "Los Angeles (803)",
  "Dallas (623)",
  "Houston (618)",
  "Phoenix (753)",
  "Denver (560)",
  "Seattle (819)",
  "Miami (528)",
  "Boston (506)",
] as const;

export const CHANNEL_OPTIONS = [
  "SEM / Paid Search",
  "Brand TV / OTT",
  "Social Media",
  "Display / Retarget",
  "Direct Mail",
  "Affiliate / Partner",
] as const;

export interface Filters {
  dateRange: string;
  products: string[];
  dmas: string[];
  channels: string[];
}

const DEFAULT_FILTERS: Filters = {
  dateRange: "Last 12 weeks",
  products: [],   // empty = all
  dmas: [],       // empty = all
  channels: [],   // empty = all
};

interface ShellState {
  theme: Theme;
  mode: Mode;
  autopilot: Autopilot;
  view: string;
  rail: boolean;          // true = expanded, false = collapsed
  accent: string;         // current --cyan override
  density: Density;
  filters: Filters;
  exportFormat: ExportFormat;
  // Actions
  setTheme: (t: Theme) => void;
  setMode: (m: Mode) => void;
  setAutopilot: (a: Autopilot) => void;
  setView: (v: string) => void;
  toggleRail: () => void;
  setAccent: (hex: string) => void;
  setDensity: (d: Density) => void;
  setFilters: (f: Partial<Filters>) => void;
  resetFilters: () => void;
  setExportFormat: (f: ExportFormat) => void;
  /** True when any filter deviates from defaults */
  filtersActive: boolean;
}

const ShellContext = createContext<ShellState | null>(null);

function load<T>(key: string, fallback: T): T {
  try {
    const v = localStorage.getItem(`apex_${key}`);
    return v !== null ? JSON.parse(v) : fallback;
  } catch { return fallback; }
}

function save(key: string, value: unknown) {
  try { localStorage.setItem(`apex_${key}`, JSON.stringify(value)); } catch {}
}

export function ShellProvider({ children }: { children: ReactNode }) {
  const [theme, _setTheme] = useState<Theme>(() => load("theme", "dark"));
  const [mode, _setMode] = useState<Mode>(() => load("mode", "Client"));
  const [autopilot, _setAutopilot] = useState<Autopilot>(() => load("autopilot", "Assist"));
  const [view, _setView] = useState(() => load("view", DEFAULT_VIEW));
  const [rail, _setRail] = useState(() => load("rail", true));
  const [accent, _setAccent] = useState(() => load("accent", "#34E1D4"));
  const [density, _setDensity] = useState<Density>(() => load("density", "comfortable"));
  const [filters, _setFilters] = useState<Filters>(() => load("filters", DEFAULT_FILTERS));
  const [exportFormat, _setExportFormat] = useState<ExportFormat>(() => load("exportFormat", "XLSX"));

  // Sync theme attribute
  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    save("theme", theme);
  }, [theme]);

  // Sync accent CSS variable — only override when user has customised;
  // otherwise let the stylesheet [data-theme] rules handle it.
  const THEME_DEFAULTS: Record<Theme, string> = { dark: "#34E1D4", light: "#0B897E" };
  useEffect(() => {
    if (accent !== THEME_DEFAULTS[theme]) {
      document.documentElement.style.setProperty("--cyan", accent);
    } else {
      document.documentElement.style.removeProperty("--cyan");
    }
    save("accent", accent);
  }, [accent, theme]);

  // When theme flips, reset accent to the new theme's default
  useEffect(() => {
    _setAccent(THEME_DEFAULTS[theme]);
  }, [theme]);

  // Sync density attribute
  useEffect(() => {
    document.documentElement.setAttribute("data-density", density);
    save("density", density);
  }, [density]);

  useEffect(() => { save("mode", mode); }, [mode]);
  useEffect(() => { save("autopilot", autopilot); }, [autopilot]);
  useEffect(() => { save("view", view); }, [view]);
  useEffect(() => { save("rail", rail); }, [rail]);
  useEffect(() => { save("filters", filters); }, [filters]);
  useEffect(() => { save("exportFormat", exportFormat); }, [exportFormat]);

  const setTheme = useCallback((t: Theme) => _setTheme(t), []);
  const setMode = useCallback((m: Mode) => _setMode(m), []);
  const setAutopilot = useCallback((a: Autopilot) => _setAutopilot(a), []);
  const setView = useCallback((v: string) => _setView(v), []);
  const toggleRail = useCallback(() => _setRail(r => !r), []);
  const setAccent = useCallback((hex: string) => _setAccent(hex), []);
  const setDensity = useCallback((d: Density) => _setDensity(d), []);
  const setExportFormat = useCallback((f: ExportFormat) => _setExportFormat(f), []);
  const setFilters = useCallback(
    (partial: Partial<Filters>) => _setFilters((prev) => ({ ...prev, ...partial })),
    [],
  );
  const resetFilters = useCallback(() => _setFilters(DEFAULT_FILTERS), []);

  const filtersActive =
    filters.dateRange !== DEFAULT_FILTERS.dateRange ||
    filters.products.length > 0 ||
    filters.dmas.length > 0 ||
    filters.channels.length > 0;

  return (
    <ShellContext.Provider value={{
      theme, mode, autopilot, view, rail, accent, density, filters, exportFormat,
      setTheme, setMode, setAutopilot, setView, toggleRail, setAccent, setDensity,
      setFilters, resetFilters, setExportFormat, filtersActive,
    }}>
      {children}
    </ShellContext.Provider>
  );
}

export function useShell(): ShellState {
  const ctx = useContext(ShellContext);
  if (!ctx) throw new Error("useShell must be inside <ShellProvider>");
  return ctx;
}
