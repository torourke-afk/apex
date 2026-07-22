import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import {
  ALL_DMAS,
  DMA_REGION,
  DMAQ,
} from "../data/searchTrends";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

const REGIONS = ["All", "Midwest", "Southeast", "Other"] as const;

/** Regional competitors for the overlap filter (AND with Fifth Third) */
const OVERLAP_BANKS = ["Huntington", "KeyBank", "Regions", "PNC", "Truist"] as const;

/** Preset: Fifth Third Midwest core markets */
const MIDWEST_CORE = [
  "Cincinnati",
  "Columbus, OH",
  "Cleveland-Akron (Canton)",
  "Dayton",
  "Toledo",
  "Detroit",
  "Grand Rapids-Kalmzoo-B.Crk",
  "Indianapolis",
  "Chicago",
  "Louisville",
  "Lexington",
] as const;

/** Region badge letter + color */
const REGION_BADGE: Record<string, { letter: string; cls: string }> = {
  Midwest:   { letter: "M", cls: "text-cyan"    },
  Southeast: { letter: "S", cls: "text-amber"   },
  Other:     { letter: "O", cls: "text-fg3"     },
};

/* ------------------------------------------------------------------ */
/*  Click-outside hook                                                 */
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

/* ------------------------------------------------------------------ */
/*  Component                                                          */
/* ------------------------------------------------------------------ */

interface AwarenessFilterBarProps {
  onDmasChange: (dmas: readonly string[]) => void;
}

export function AwarenessFilterBar({ onDmasChange }: AwarenessFilterBarProps) {
  /* ---- State ---- */
  const [selectedDmas, setSelectedDmas] = useState<Set<string>>(() => new Set(ALL_DMAS));
  const [region, setRegion] = useState<string>("All");
  const [compOverlap, setCompOverlap] = useState<Set<string>>(() => new Set());
  const [search, setSearch] = useState("");
  const [expanded, setExpanded] = useState(false);
  const [regionOpen, setRegionOpen] = useState(false);

  const regionRef = useRef<HTMLDivElement>(null);
  useClickOutside(regionRef, () => setRegionOpen(false));

  /* ---- Notify parent whenever selection changes ---- */
  useEffect(() => {
    const arr = ALL_DMAS.filter((d) => selectedDmas.has(d));
    onDmasChange(arr.length > 0 ? arr : ALL_DMAS);
  }, [selectedDmas, onDmasChange]);

  /* ---- Quick-filter logic (region + competitor overlap) ---- */
  const applyQuickFilters = useCallback(
    (nextRegion: string, nextComp: Set<string>) => {
      let base = ALL_DMAS.slice();

      // Region filter
      if (nextRegion !== "All") {
        base = base.filter((d) => DMA_REGION[d] === nextRegion);
      }

      // Competitor overlap: keep DMAs where Fifth Third has data AND every selected competitor has data
      if (nextComp.size > 0) {
        const ftData = DMAQ["Fifth Third"] || {};
        base = base.filter((d) => {
          if (!ftData[d]) return false;
          return [...nextComp].every((c) => (DMAQ[c] || {})[d] !== undefined);
        });
      }

      setSelectedDmas(new Set(base));
    },
    [],
  );

  /* ---- Handlers ---- */
  const handleRegionChange = useCallback(
    (r: string) => {
      setRegion(r);
      setRegionOpen(false);
      applyQuickFilters(r, compOverlap);
    },
    [compOverlap, applyQuickFilters],
  );

  const handleCompToggle = useCallback(
    (bank: string) => {
      setCompOverlap((prev) => {
        const next = new Set(prev);
        if (next.has(bank)) next.delete(bank);
        else next.add(bank);
        applyQuickFilters(region, next);
        return next;
      });
    },
    [region, applyQuickFilters],
  );

  const handleDmaToggle = useCallback((dma: string) => {
    setSelectedDmas((prev) => {
      const next = new Set(prev);
      if (next.has(dma)) next.delete(dma);
      else next.add(dma);
      return next;
    });
  }, []);

  const handleSelectAll = useCallback(() => {
    setRegion("All");
    setCompOverlap(new Set());
    setSelectedDmas(new Set(ALL_DMAS));
  }, []);

  const handleSelectNone = useCallback(() => {
    setRegion("All");
    setCompOverlap(new Set());
    setSelectedDmas(new Set());
  }, []);

  const handlePresetMidwest = useCallback(() => {
    setRegion("All");
    setCompOverlap(new Set());
    setSelectedDmas(new Set(MIDWEST_CORE.filter((d) => ALL_DMAS.includes(d))));
  }, []);

  const handlePresetOverlap = useCallback((mode: "either" | "both") => {
    setRegion("All");
    setCompOverlap(new Set());

    const ftDmas = new Set(Object.keys(DMAQ["Fifth Third"] || {}));
    const pncDmas = new Set(Object.keys(DMAQ["PNC"] || {}));
    const huntDmas = new Set(Object.keys(DMAQ["Huntington"] || {}));

    const result = [...ftDmas].filter((d) =>
      mode === "both"
        ? pncDmas.has(d) && huntDmas.has(d)
        : pncDmas.has(d) || huntDmas.has(d),
    );

    setSelectedDmas(new Set(result));
  }, []);

  /* ---- Derived ---- */
  const count = selectedDmas.size;
  const total = ALL_DMAS.length;
  const countLabel = count === total ? `all ${total} DMAs` : `${count} of ${total} DMAs`;

  // Filtered DMA list for the checkbox grid
  const visibleDmas = useMemo(() => {
    const lc = search.toLowerCase();
    return lc ? ALL_DMAS.filter((d) => d.toLowerCase().includes(lc)) : ALL_DMAS;
  }, [search]);

  /* ---- Summary chips when collapsed ---- */
  const summaryChips: string[] = [];
  if (region !== "All") summaryChips.push(region);
  if (compOverlap.size > 0) summaryChips.push(`∩ ${[...compOverlap].join(", ")}`);

  /* ---- Render ---- */
  return (
    <div className="rounded-[11px] border border-line bg-panel mb-4">
      {/* ===== Header row — always visible ===== */}
      <button
        type="button"
        onClick={() => setExpanded((p) => !p)}
        className="w-full flex items-center gap-3 px-4 py-2.5 cursor-pointer group"
      >
        <span className="font-mono text-[9px] tracking-[.16em] text-cyan font-semibold">
          DMA FILTER
        </span>
        <span className="font-mono text-[10px] text-fg3">
          ({countLabel})
        </span>

        {/* Summary chips when collapsed */}
        {!expanded && summaryChips.length > 0 && (
          <div className="flex gap-1.5 ml-1">
            {summaryChips.map((chip) => (
              <span
                key={chip}
                className="px-2 py-0.5 rounded-pill bg-[var(--cyan-subtle)] border border-[var(--cyan-hover)] font-mono text-[9px] text-cyan"
              >
                {chip}
              </span>
            ))}
          </div>
        )}

        <div className="flex-1" />

        <span className="font-mono text-[9px] text-fg3 group-hover:text-fg transition-colors">
          {expanded ? "▴ COLLAPSE" : "▾ EXPAND"}
        </span>
      </button>

      {/* ===== Expanded panel ===== */}
      {expanded && (
        <div className="px-4 pb-4 pt-0 border-t border-line">
          {/* Row 1: Region + Competitor overlap */}
          <div className="flex items-center gap-4 mt-3 flex-wrap">
            {/* Region dropdown */}
            <div className="flex items-center gap-2">
              <span className="font-mono text-[9px] tracking-[.08em] text-fg3">REGION</span>
              <div className="relative" ref={regionRef}>
                <button
                  type="button"
                  onClick={() => setRegionOpen((p) => !p)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-pill border font-mono text-[10.5px] tracking-[.04em] transition-colors cursor-pointer ${
                    region !== "All"
                      ? "border-cyan bg-[var(--cyan-subtle)] text-cyan"
                      : "border-line bg-panel2 text-fg2 hover:border-line-strong"
                  }`}
                >
                  {region === "All" ? "All regions" : region}
                  <span className="text-[9px] text-fg3">{regionOpen ? "▴" : "▾"}</span>
                </button>

                {regionOpen && (
                  <div className="absolute top-full left-0 mt-1 min-w-[160px] rounded-inner border border-line bg-panel shadow-lg z-50 py-1 animate-rise">
                    {REGIONS.map((r) => (
                      <button
                        key={r}
                        type="button"
                        onClick={() => handleRegionChange(r)}
                        className={`w-full text-left px-3 py-2 font-mono text-[11px] transition-colors cursor-pointer ${
                          r === region
                            ? "text-cyan bg-[var(--cyan-subtle)]"
                            : "text-fg2 hover:bg-panel2 hover:text-fg"
                        }`}
                      >
                        {r === region && <span className="mr-1.5">●</span>}
                        {r === "All" ? "All regions" : r}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>

            {/* Divider */}
            <div className="w-px h-[20px] bg-line" />

            {/* Competitor overlap checkboxes */}
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-mono text-[9px] tracking-[.08em] text-fg3 whitespace-nowrap">
                OVERLAP WITH 5/3
              </span>
              {OVERLAP_BANKS.map((bank) => {
                const active = compOverlap.has(bank);
                return (
                  <button
                    key={bank}
                    type="button"
                    onClick={() => handleCompToggle(bank)}
                    className={`flex items-center gap-1.5 px-2.5 py-1 rounded-pill border font-mono text-[10px] tracking-[.04em] transition-colors cursor-pointer ${
                      active
                        ? "border-cyan bg-[var(--cyan-hover)] text-cyan"
                        : "border-line bg-panel2 text-fg3 hover:text-fg hover:border-line-strong"
                    }`}
                  >
                    <span
                      className={`w-[12px] h-[12px] rounded-[3px] border flex items-center justify-center text-[8px] ${
                        active
                          ? "border-cyan bg-[var(--cyan-active)] text-cyan"
                          : "border-line bg-panel2"
                      }`}
                    >
                      {active && "✓"}
                    </span>
                    {bank}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Row 2: Search + Presets */}
          <div className="flex items-center gap-2 mt-3 flex-wrap">
            {/* DMA search */}
            <input
              type="text"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="find DMA…"
              className="h-[28px] w-[170px] rounded-[8px] border border-line bg-panel2 px-2.5 font-mono text-[10px] text-fg placeholder:text-fg3 focus:outline-none focus:border-[var(--cyan-glow)]"
            />

            {/* Preset buttons */}
            <PresetBtn label="All" onClick={handleSelectAll} />
            <PresetBtn label="None" onClick={handleSelectNone} />
            <PresetBtn label="5/3 Midwest core" onClick={handlePresetMidwest} active={false} />
            <PresetBtn label="5/3 ∩ PNC/Hunt" onClick={() => handlePresetOverlap("either")} />
            <PresetBtn label="5/3 ∩ PNC ∩ Hunt" onClick={() => handlePresetOverlap("both")} />
          </div>

          {/* DMA checkbox grid */}
          <div className="mt-3 max-h-[220px] overflow-y-auto rounded-[8px] border border-line bg-panel2 p-2">
            <div className="grid gap-x-2 gap-y-0.5" style={{ gridTemplateColumns: "repeat(auto-fill, minmax(220px, 1fr))" }}>
              {visibleDmas.map((dma) => {
                const checked = selectedDmas.has(dma);
                const badge = REGION_BADGE[DMA_REGION[dma]] || REGION_BADGE.Other;

                return (
                  <label
                    key={dma}
                    className="flex items-center gap-1.5 py-0.5 cursor-pointer group/dma"
                  >
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={() => handleDmaToggle(dma)}
                      className="sr-only"
                    />
                    <span
                      className={`flex-none w-[13px] h-[13px] rounded-[3px] border flex items-center justify-center text-[8px] transition-colors ${
                        checked
                          ? "border-cyan bg-[var(--cyan-active)] text-cyan"
                          : "border-line bg-panel group-hover/dma:border-line-strong"
                      }`}
                    >
                      {checked && "✓"}
                    </span>
                    <span className={`font-mono text-[10px] truncate ${checked ? "text-fg2" : "text-fg3"} group-hover/dma:text-fg transition-colors`}>
                      {dma}
                    </span>
                    <span className={`font-mono text-[9px] flex-none ${badge.cls}`}>
                      {badge.letter}
                    </span>
                  </label>
                );
              })}
            </div>

            {visibleDmas.length === 0 && (
              <div className="text-center py-4 font-mono text-[10px] text-fg3">
                No DMAs match "{search}"
              </div>
            )}
          </div>

          {/* Footer hint */}
          <div className="mt-2 font-mono text-[9px] text-fg3 leading-relaxed">
            Region + competitor-AND combine (intersection) to set the DMA selection. Applies to the tiles, quarterly chart, and per-capita bar. The comparison table below always shows all DMAs.
          </div>
        </div>
      )}
    </div>
  );
}

/* ---- Preset button ---- */

function PresetBtn({ label, onClick, active }: { label: string; onClick: () => void; active?: boolean }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={`h-[28px] px-3 rounded-[8px] border font-mono text-[9.5px] tracking-[.04em] transition-colors cursor-pointer ${
        active
          ? "border-cyan bg-[var(--cyan-hover)] text-cyan"
          : "border-line bg-panel2 text-fg3 hover:text-fg hover:border-line-strong"
      }`}
    >
      {label}
    </button>
  );
}
