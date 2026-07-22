import { useState, useRef, useEffect, useCallback } from "react";
import {
  useShell,
  DATE_RANGE_OPTIONS,
  PRODUCT_OPTIONS,
  DMA_OPTIONS,
  CHANNEL_OPTIONS,
} from "./ShellProvider";
/** Maps shell view IDs → BFF export surface IDs */
const EXPORTABLE: Record<string, string> = {
  scorecard: "scorecard",
  spend: "spend",
  media: "media",
  creative: "sem",     // creative uses SEM data for export
  audience: "social",  // audience maps to social
  brand: "awareness",
  product: "product",
  funnel: "funnel",
  retention: "retention",
  operations: "operations",
};

/* ------------------------------------------------------------------ */
/*  Generic dropdown popover                                           */
/* ------------------------------------------------------------------ */

function useClickOutside(ref: React.RefObject<HTMLElement | null>, handler: () => void) {
  useEffect(() => {
    function onDown(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) handler();
    }
    document.addEventListener("mousedown", onDown);
    return () => document.removeEventListener("mousedown", onDown);
  }, [ref, handler]);
}

/* ---- Single-select dropdown (date range) ---- */

function DateDropdown({
  value,
  options,
  onChange,
}: {
  value: string;
  options: readonly string[];
  onChange: (v: string) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false));

  return (
    <div className="relative" ref={ref} onKeyDown={(e) => { if (e.key === "Escape") setOpen(false); }}>
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label="Date range"
        className="flex items-center gap-2 px-3 py-1.5 rounded-pill border border-line bg-panel2 font-mono text-[11px] text-fg hover:border-line-strong transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none"
      >
        {value}
        <span className="text-[9px] text-fg3">{open ? "▴" : "▾"}</span>
      </button>

      {open && (
        <div role="listbox" aria-label="Date range options" className="absolute top-full left-0 mt-1 min-w-[180px] rounded-inner border border-line bg-panel shadow-lg z-50 py-1 animate-rise">
          {options.map((opt) => (
            <button
              key={opt}
              role="option"
              aria-selected={opt === value}
              onClick={() => { onChange(opt); setOpen(false); }}
              className={`w-full text-left px-3 py-2 font-mono text-[11px] transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none ${
                opt === value
                  ? "text-cyan bg-[var(--cyan-subtle)]"
                  : "text-fg2 hover:bg-panel2 hover:text-fg"
              }`}
            >
              {opt === value && <span className="mr-1.5">●</span>}
              {opt}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

/* ---- Multi-select dropdown (product / DMA / channel) ---- */

function MultiDropdown({
  label,
  options,
  selected,
  onChange,
}: {
  label: string;
  options: readonly string[];
  selected: string[];
  onChange: (next: string[]) => void;
}) {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  useClickOutside(ref, () => setOpen(false));

  const toggle = useCallback(
    (opt: string) => {
      onChange(
        selected.includes(opt)
          ? selected.filter((s) => s !== opt)
          : [...selected, opt],
      );
    },
    [selected, onChange],
  );

  const count = selected.length;

  return (
    <div className="relative" ref={ref} onKeyDown={(e) => { if (e.key === "Escape") setOpen(false); }}>
      <button
        onClick={() => setOpen(!open)}
        aria-expanded={open}
        aria-haspopup="listbox"
        aria-label={`${label}${count > 0 ? `, ${count} selected` : ''}`}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-pill border font-mono text-[10.5px] tracking-[.04em] transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none ${
          count > 0
            ? "border-cyan bg-[var(--cyan-subtle)] text-cyan"
            : "border-line bg-panel2 text-fg2 hover:border-line-strong hover:text-fg"
        }`}
      >
        {label}
        {count > 0 && (
          <span className="flex items-center justify-center w-[16px] h-[16px] rounded-full bg-cyan text-cyan-ink text-[9px] font-bold">
            {count}
          </span>
        )}
        <span className="text-[9px] text-fg3 ml-0.5">{open ? "▴" : "▾"}</span>
      </button>

      {open && (
        <div role="listbox" aria-label={`${label} options`} aria-multiselectable="true" className="absolute top-full left-0 mt-1 min-w-[220px] rounded-inner border border-line bg-panel shadow-lg z-50 py-1 animate-rise">
          {/* Select All / Clear */}
          <div className="flex items-center justify-between px-3 py-1.5 border-b border-line mb-1">
            <button
              onClick={() => onChange([...options])}
              className="font-mono text-[9px] tracking-[.08em] text-fg3 hover:text-cyan transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none"
            >
              SELECT ALL
            </button>
            <button
              onClick={() => onChange([])}
              className="font-mono text-[9px] tracking-[.08em] text-fg3 hover:text-cyan transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none"
            >
              CLEAR
            </button>
          </div>

          {options.map((opt) => {
            const active = selected.includes(opt);
            return (
              <button
                key={opt}
                role="option"
                aria-selected={active}
                onClick={() => toggle(opt)}
                className={`w-full text-left px-3 py-2 font-mono text-[11px] flex items-center gap-2.5 transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none ${
                  active
                    ? "text-cyan bg-[var(--cyan-subtle)]"
                    : "text-fg2 hover:bg-panel2 hover:text-fg"
                }`}
              >
                {/* Checkbox */}
                <span
                  className={`flex-none w-[14px] h-[14px] rounded-[3px] border flex items-center justify-center text-[9px] ${
                    active
                      ? "border-cyan bg-[var(--cyan-active)] text-cyan"
                      : "border-line bg-panel2"
                  }`}
                >
                  {active && "✓"}
                </span>
                {opt}
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  FilterBar                                                          */
/* ------------------------------------------------------------------ */

const API_BASE = import.meta.env.VITE_API_URL ?? "";

export function FilterBar() {
  const { view, filters, setFilters, resetFilters, filtersActive, exportFormat } = useShell();
  const [exporting, setExporting] = useState(false);

  const exportSurface = EXPORTABLE[view];

  const handleExport = useCallback(async () => {
    if (!exportSurface) return;
    setExporting(true);
    try {
      const fmt = exportFormat.toLowerCase();
      const url = `${API_BASE}/api/export/${exportSurface}?format=${fmt}`;
      const res = await fetch(url);
      if (!res.ok) {
        const body = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
        throw new Error(body.detail ?? `Export failed: ${res.status}`);
      }
      const blob = await res.blob();
      const disposition = res.headers.get("Content-Disposition") ?? "";
      const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
      const filename = filenameMatch?.[1] ?? `apex-${exportSurface}.${fmt}`;
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      setTimeout(() => {
        URL.revokeObjectURL(a.href);
        document.body.removeChild(a);
      }, 100);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : String(e);
      if (msg.includes("missing Python package") || msg.includes("No module named")) {
        // Dependency missing — auto-fallback to CSV
        try {
          const csvUrl = `${API_BASE}/api/export/${exportSurface}?format=csv`;
          const csvRes = await fetch(csvUrl);
          if (csvRes.ok) {
            const blob = await csvRes.blob();
            const disposition = csvRes.headers.get("Content-Disposition") ?? "";
            const filenameMatch = disposition.match(/filename="?([^"]+)"?/);
            const filename = filenameMatch?.[1] ?? `apex-${exportSurface}.csv`;
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = filename;
            document.body.appendChild(a);
            a.click();
            setTimeout(() => { URL.revokeObjectURL(a.href); document.body.removeChild(a); }, 100);
          }
        } catch (csvErr) {
          console.error("CSV fallback also failed:", csvErr);
        }
      } else {
        console.error("Export error:", e);
      }
    } finally {
      setTimeout(() => setExporting(false), 600);
    }
  }, [exportSurface, exportFormat]);

  return (
    <div className="flex flex-wrap items-center gap-2 md:gap-2.5 px-3 md:px-4 py-2 md:py-2.5 mx-3 md:mx-5 my-2 rounded-[11px] border border-line bg-panel">
      <span className="font-mono text-[9px] tracking-[.16em] text-fg3">FILTER</span>

      {/* Date range — single select */}
      <DateDropdown
        value={filters.dateRange}
        options={DATE_RANGE_OPTIONS}
        onChange={(v) => setFilters({ dateRange: v })}
      />

      {/* Product — multi-select */}
      <MultiDropdown
        label="PRODUCT"
        options={PRODUCT_OPTIONS}
        selected={filters.products}
        onChange={(v) => setFilters({ products: v })}
      />

      {/* DMA — multi-select */}
      <MultiDropdown
        label="DMA"
        options={DMA_OPTIONS}
        selected={filters.dmas}
        onChange={(v) => setFilters({ dmas: v })}
      />

      {/* Channel — multi-select */}
      <MultiDropdown
        label="CHANNEL"
        options={CHANNEL_OPTIONS}
        selected={filters.channels}
        onChange={(v) => setFilters({ channels: v })}
      />

      <div className="flex-1" />

      {/* Export */}
      {exportSurface && (
        <button
          onClick={handleExport}
          disabled={exporting}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-pill border border-line bg-panel2 font-mono text-[10px] tracking-[.06em] text-fg2 hover:border-cyan hover:text-cyan transition-colors cursor-pointer disabled:opacity-50 focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none"
        >
          <svg aria-hidden="true" xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
            <polyline points="7 10 12 15 17 10" />
            <line x1="12" y1="15" x2="12" y2="3" />
          </svg>
          {exporting ? "EXPORTING…" : `EXPORT ${exportFormat}`}
        </button>
      )}

      {/* Reset */}
      <button
        onClick={resetFilters}
        className={`px-3 py-1.5 rounded-pill border border-dashed bg-transparent font-mono text-[10px] tracking-[.06em] transition-colors cursor-pointer focus-visible:ring-2 focus-visible:ring-cyan focus-visible:outline-none ${
          filtersActive
            ? "border-cyan text-cyan hover:bg-[var(--cyan-subtle)]"
            : "border-line-strong text-fg3 hover:text-fg2"
        }`}
      >
        ↺ RESET
      </button>
    </div>
  );
}
