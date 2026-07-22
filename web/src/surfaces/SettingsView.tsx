import { useState, useEffect, useCallback } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { Card, SectionHeader, Segmented, Pill, DataGuard, SkeletonCard, Skeleton } from "../ui";
import { useShell } from "../shell/ShellProvider";
import { useBenchmarks, useSyncStatus, useConnectors, useSyncLog } from "../api/hooks";
import { apiFetch } from "../api/client";
import type { ConnectorStatus, SyncLogEntry } from "../api/types";

/* ------------------------------------------------------------------ */
/*  Constants                                                          */
/* ------------------------------------------------------------------ */

/** Brand colors for known connector types */
const CONNECTOR_COLORS: Record<string, { bg: string; initials: string }> = {
  seed:             { bg: "#6B7280", initials: "SD" },
  google_analytics: { bg: "#E37400", initials: "GA" },
  semrush:          { bg: "#FF642D", initials: "SR" },
  google_ads:       { bg: "#4285F4", initials: "GA" },
  meta_ads:         { bg: "#0668E1", initials: "MA" },
  generic_rest:     { bg: "#8B5CF6", initials: "RS" },
};

const STATUS_VARIANT: Record<string, "green" | "amber" | "red" | "neutral"> = {
  connected:    "green",
  degraded:     "amber",
  disconnected: "neutral",
  error:        "red",
};

const ACCENT_SWATCHES = [
  "#34E1D4",
  "#7C8BFF",
  "#4FD89B",
  "#F2B14C",
  "#FF5C72",
];

const BENCHMARK_TABS = ["Funnel", "Media", "Efficiency", "NBD", "Retention"] as const;
type BenchmarkTab = (typeof BENCHMARK_TABS)[number];

const BENCHMARK_CONFIG: Record<BenchmarkTab, Array<{ label: string; key: string; min: number; max: number; step: number; default: number; unit: string }>> = {
  Funnel: [
    { label: "Visit-to-App Start", key: "f_visit_app", min: 0, max: 20, step: 0.5, default: 8.0, unit: "%" },
    { label: "App Start-to-Complete", key: "f_app_complete", min: 0, max: 100, step: 1, default: 62, unit: "%" },
    { label: "Complete-to-Funded", key: "f_complete_fund", min: 0, max: 100, step: 1, default: 28, unit: "%" },
    { label: "Min Acceptable CVR", key: "f_min_cvr", min: 0, max: 10, step: 0.1, default: 1.4, unit: "%" },
  ],
  Media: [
    { label: "Target ROAS", key: "m_roas", min: 1, max: 10, step: 0.1, default: 3.5, unit: "×" },
    { label: "Max CPA", key: "m_cpa", min: 50, max: 500, step: 10, default: 290, unit: "$" },
    { label: "Brand Lift Min", key: "m_brand_lift", min: 0, max: 30, step: 0.5, default: 5.0, unit: "%" },
    { label: "Frequency Cap", key: "m_freq_cap", min: 1, max: 20, step: 1, default: 7, unit: "/wk" },
  ],
  Efficiency: [
    { label: "CPIHH Target", key: "e_cpihh", min: 100, max: 600, step: 10, default: 290, unit: "$" },
    { label: "Marginal ROAS Floor", key: "e_mroas", min: 1, max: 8, step: 0.1, default: 2.5, unit: "×" },
    { label: "Saturation Threshold", key: "e_sat", min: 50, max: 100, step: 1, default: 85, unit: "%" },
    { label: "Budget Pacing Tolerance", key: "e_pacing", min: 1, max: 20, step: 1, default: 5, unit: "%" },
  ],
  NBD: [
    { label: "New-to-Bank Rate", key: "n_ntb", min: 0, max: 100, step: 1, default: 42, unit: "%" },
    { label: "Cross-Sell Window", key: "n_xsell", min: 30, max: 365, step: 15, default: 90, unit: "d" },
    { label: "Activation Target", key: "n_activation", min: 0, max: 100, step: 1, default: 75, unit: "%" },
    { label: "Deepening Score Min", key: "n_deepen", min: 0, max: 100, step: 1, default: 60, unit: "pt" },
  ],
  Retention: [
    { label: "MOB6 Retention Floor", key: "r_mob6", min: 50, max: 100, step: 1, default: 74, unit: "%" },
    { label: "90-Day Churn Ceiling", key: "r_churn90", min: 0, max: 20, step: 0.5, default: 8.0, unit: "%" },
    { label: "LTV Target", key: "r_ltv", min: 1000, max: 8000, step: 100, default: 4000, unit: "$" },
    { label: "Payback Period Max", key: "r_payback", min: 3, max: 18, step: 1, default: 10, unit: "mo" },
  ],
};

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function ToggleSwitch({
  checked,
  onChange,
}: {
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <button
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="relative w-[40px] h-[22px] rounded-full transition-colors duration-200 cursor-pointer flex-none"
      style={{
        background: checked ? "var(--cyan)" : "var(--line2)",
      }}
    >
      <div
        className="absolute top-[3px] w-[16px] h-[16px] rounded-full transition-transform duration-200"
        style={{
          left: checked ? "21px" : "3px",
          background: checked ? "var(--cyanInk)" : "var(--text3)",
        }}
      />
    </button>
  );
}

function AppModeCard() {
  const { mode, setMode, autopilot, setAutopilot } = useShell();

  return (
    <Card className="flex flex-col gap-5 p-5 animate-rise" style={{ animationDelay: "0.05s" }}>
      <SectionHeader title="Application Mode" />

      <div className="flex flex-col gap-1.5">
        <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
          PERSPECTIVE
        </span>
        <Segmented
          options={["BD", "Client"] as const}
          value={mode === "BD" ? "BD" : "Client"}
          onChange={(v) => setMode(v as "BD" | "Client")}
          size="sm"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
          AGENT AUTOPILOT
        </span>
        <Segmented
          options={["Off", "Assist", "Auto"] as const}
          value={autopilot}
          onChange={setAutopilot}
          size="sm"
        />
      </div>
    </Card>
  );
}

function AppearanceCard() {
  const { theme, setTheme, accent, setAccent, density, setDensity } = useShell();

  return (
    <Card className="flex flex-col gap-5 p-5 animate-rise" style={{ animationDelay: "0.1s" }}>
      <SectionHeader title="Appearance" />

      <div className="flex flex-col gap-1.5">
        <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
          THEME
        </span>
        <Segmented
          options={["dark", "light"] as const}
          value={theme}
          onChange={setTheme}
          size="sm"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
          DENSITY
        </span>
        <Segmented
          options={["comfortable", "compact"] as const}
          value={density}
          onChange={setDensity}
          size="sm"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
          SIGNAL ACCENT
        </span>
        <div className="flex gap-2.5 mt-1">
          {ACCENT_SWATCHES.map((hex) => (
            <button
              key={hex}
              onClick={() => setAccent(hex)}
              className="w-[28px] h-[28px] rounded-full cursor-pointer transition-all duration-150"
              style={{
                background: hex,
                boxShadow:
                  accent === hex
                    ? `0 0 0 2px var(--panel), 0 0 0 4px ${hex}`
                    : "none",
                opacity: accent === hex ? 1 : 0.55,
              }}
              aria-label={`Accent color ${hex}`}
            />
          ))}
        </div>
      </div>
    </Card>
  );
}

function DataExportCard() {
  const queryClient = useQueryClient();
  const { exportFormat: exportFmt, setExportFormat: setExportFmt } = useShell();
  const [cacheEnabled, setCacheEnabled] = useState(true);
  const [clearing, setClearing] = useState(false);

  const handleClearCache = useCallback(async () => {
    setClearing(true);
    await queryClient.invalidateQueries();
    // Brief visual feedback
    setTimeout(() => setClearing(false), 800);
  }, [queryClient]);

  return (
    <Card className="flex flex-col gap-5 p-5 animate-rise" style={{ animationDelay: "0.15s" }}>
      <SectionHeader title="Data & Export" />

      <div className="flex flex-col gap-1.5">
        <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
          DEFAULT EXPORT FORMAT
        </span>
        <Segmented
          options={["XLSX", "CSV", "PDF"] as const}
          value={exportFmt}
          onChange={setExportFmt}
          size="sm"
        />
      </div>

      <div className="flex items-center justify-between">
        <div className="flex flex-col gap-0.5">
          <span className="text-[13px] font-medium">Response Cache</span>
          <span className="font-mono text-[9.5px] text-fg3">
            Cache BFF responses locally
          </span>
        </div>
        <ToggleSwitch checked={cacheEnabled} onChange={setCacheEnabled} />
      </div>

      <button
        onClick={handleClearCache}
        disabled={clearing}
        className="w-full py-2.5 rounded-pill border border-dashed border-line text-fg3 font-mono text-[10px] tracking-[.08em] hover:border-cyan hover:text-cyan transition-colors cursor-pointer bg-transparent disabled:opacity-50"
      >
        {clearing ? "SYNCING…" : "CLEAR CACHE & RESYNC"}
      </button>
    </Card>
  );
}

function formatRelativeTime(iso: string | null): string {
  if (!iso) return "Never";
  const diff = Date.now() - new Date(iso).getTime();
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "Just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  return `${Math.floor(hrs / 24)}d ago`;
}

function ConnectorCard({ c }: { c: ConnectorStatus }) {
  const [syncing, setSyncing] = useState(false);
  const colors = CONNECTOR_COLORS[c.type] ?? { bg: "#6B7280", initials: c.type.slice(0, 2).toUpperCase() };
  const variant = STATUS_VARIANT[c.status] ?? "neutral";

  const handleSync = useCallback(async () => {
    setSyncing(true);
    try {
      await apiFetch("/api/sync/trigger", {
        method: "POST",
        body: JSON.stringify({ connector_id: c.id }),
      });
    } catch {
      // swallow — sync status will update via polling
    } finally {
      setTimeout(() => setSyncing(false), 1200);
    }
  }, [c.id]);

  return (
    <Card className="flex flex-col gap-3 p-4 hover:border-line-strong transition-colors">
      {/* Top row: icon + name + status badge */}
      <div className="flex items-center gap-3">
        <div
          className="flex-none w-[38px] h-[38px] rounded-[10px] flex items-center justify-center text-white font-mono text-[11px] font-bold"
          style={{ background: colors.bg }}
        >
          {colors.initials}
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-semibold whitespace-nowrap overflow-hidden text-ellipsis">
            {c.display_name}
          </div>
          <div className="font-mono text-[10px] text-fg3 mt-0.5">
            {c.domains.length} domain{c.domains.length !== 1 ? "s" : ""}{" "}
            {c.is_fallback && "· fallback"}
          </div>
        </div>
        <Pill variant={variant} dot>
          {c.status.toUpperCase()}
        </Pill>
      </div>

      {/* Domains row */}
      <div className="flex flex-wrap gap-1">
        {c.domains.map((d) => (
          <span
            key={d}
            className="px-1.5 py-0.5 rounded bg-panel2 font-mono text-[8px] tracking-[.06em] text-fg3"
          >
            {d}
          </span>
        ))}
      </div>

      {/* Footer: last sync + rows + sync button */}
      <div className="flex items-center justify-between pt-1 border-t border-line">
        <div className="flex flex-col gap-0.5">
          <span className="font-mono text-[9px] text-fg3">
            Last sync: {formatRelativeTime(c.last_sync)}
          </span>
          <span className="font-mono text-[9px] text-fg3">
            {c.rows_synced.toLocaleString()} rows
            {c.latency_ms != null && ` · ${c.latency_ms}ms`}
          </span>
        </div>
        {!c.is_fallback && (
          <button
            onClick={handleSync}
            disabled={syncing}
            className="px-2.5 py-1 rounded-pill font-mono text-[9px] tracking-[.06em] border border-line text-fg3 hover:border-cyan hover:text-cyan transition-colors cursor-pointer bg-transparent disabled:opacity-50"
          >
            {syncing ? "SYNCING…" : "SYNC"}
          </button>
        )}
      </div>

      {/* Error display */}
      {c.last_error && (
        <div className="px-2.5 py-1.5 rounded bg-[rgba(255,92,114,.08)] font-mono text-[9px] text-critical leading-relaxed">
          {c.last_error}
        </div>
      )}
    </Card>
  );
}

function DataSourcesSection() {
  const connectors = useConnectors();
  const syncStatus = useSyncStatus();
  const syncLog = useSyncLog(5);
  const [syncing, setSyncing] = useState(false);

  const handleSyncAll = useCallback(async () => {
    setSyncing(true);
    try {
      await apiFetch("/api/sync/trigger", {
        method: "POST",
        body: JSON.stringify({}),
      });
    } catch {
      // swallow
    } finally {
      setTimeout(() => setSyncing(false), 2000);
    }
  }, []);

  return (
    <section className="animate-rise" style={{ animationDelay: "0.2s" }}>
      <SectionHeader title="Data Sources" />

      {/* Connector cards — guarded by the connectors hook */}
      <DataGuard
        {...connectors}
        skeleton={
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
            <SkeletonCard /><SkeletonCard /><SkeletonCard />
          </div>
        }
        emptyHeadline="No connectors"
        emptyBody="No data-source connectors are configured."
        className="mt-4"
      >
        {(connData) => {
          const items = connData.connectors ?? [];
          const stats = syncStatus.data?.stats;

          return (
            <>
              {/* Header row with stats + sync-all */}
              <div className="flex items-center justify-between mb-4">
                <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
                  {items.length} CONNECTOR{items.length !== 1 ? "S" : ""}
                </span>
                <div className="flex items-center gap-4">
                  {stats && (
                    <div className="flex items-center gap-3 font-mono text-[9px] text-fg3">
                      <span>{stats.total_rows_synced.toLocaleString()} total rows</span>
                      {stats.recent_errors > 0 && (
                        <Pill variant="red" dot>
                          {stats.recent_errors} ERROR{stats.recent_errors !== 1 ? "S" : ""}
                        </Pill>
                      )}
                    </div>
                  )}
                  <button
                    onClick={handleSyncAll}
                    disabled={syncing}
                    className="px-3 py-1.5 rounded-pill font-mono text-[10px] tracking-[.06em] bg-cyan text-cyan-ink font-semibold cursor-pointer hover:brightness-110 transition-all disabled:opacity-50"
                  >
                    {syncing ? "SYNCING ALL…" : "SYNC ALL"}
                  </button>
                </div>
              </div>

              {/* Connector cards grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                {items.map((c) => (
                  <ConnectorCard key={c.id} c={c} />
                ))}
              </div>
            </>
          );
        }}
      </DataGuard>

      {/* Recent sync log — guarded by the syncLog hook */}
      <DataGuard
        {...syncLog}
        skeleton={<Skeleton rows={3} className="mt-4" />}
        emptyHeadline="No sync history"
        emptyBody="Sync log entries will appear after the first data sync."
        className="mt-4"
      >
        {(logData) =>
          logData.entries.length > 0 ? (
            <Card className="p-4">
              <div className="font-mono text-[9.5px] tracking-[.12em] text-fg3 mb-3">
                RECENT SYNC LOG
              </div>
              <div className="flex flex-col gap-1">
                {logData.entries.map((e: SyncLogEntry) => (
                  <div key={e.id} className="flex items-center gap-3 font-mono text-[10px]">
                    <Pill
                      variant={e.status === "success" ? "green" : e.status === "error" ? "red" : "amber"}
                      dot
                    >
                      {e.status.toUpperCase()}
                    </Pill>
                    <span className="text-fg2">{e.connector_id}</span>
                    <span className="text-fg3">{e.domain}.{e.endpoint}</span>
                    <span className="ml-auto text-fg3">
                      {e.rows_synced} rows · {e.duration_ms}ms
                    </span>
                  </div>
                ))}
              </div>
            </Card>
          ) : null
        }
      </DataGuard>
    </section>
  );
}

/** Map BFF BenchmarkConfig keys to the tab → slider key scheme used by the UI.
 *  API returns e.g. { funnel: { visit_app: 8.5, ... }, media: { roas: 3.6, ... } }.
 *  We prefix with the tab initial to match slider keys: funnel.visit_app → f_visit_app. */
const API_TAB_MAP: Record<string, string> = {
  Funnel: "funnel",
  Media: "media",
  Efficiency: "efficiency",
  NBD: "nbd",
};

function apiBenchmarksToSliderValues(
  apiBenchmarks: Record<string, Record<string, number>>,
): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [tab, apiKey] of Object.entries(API_TAB_MAP)) {
    const apiSection = apiBenchmarks[apiKey];
    if (!apiSection) continue;
    for (const slider of BENCHMARK_CONFIG[tab as BenchmarkTab] ?? []) {
      // slider.key is e.g. "f_visit_app"; API key is e.g. "visit_app"
      const apiFieldKey = slider.key.replace(/^[a-z]_/, "");
      if (apiFieldKey in apiSection) {
        out[slider.key] = apiSection[apiFieldKey];
      }
    }
  }
  return out;
}

function BenchmarkSection() {
  const { filters } = useShell();
  const benchmarks = useBenchmarks(filters);
  const [activeTab, setActiveTab] = useState<BenchmarkTab>("Funnel");
  const [values, setValues] = useState<Record<string, number>>(() => {
    const init: Record<string, number> = {};
    for (const tab of BENCHMARK_TABS) {
      for (const s of BENCHMARK_CONFIG[tab]) {
        init[s.key] = s.default;
      }
    }
    return init;
  });

  // When API benchmark data arrives, use it as defaults (only on first load).
  // Local slider state takes precedence after user interaction.
  const [apiApplied, setApiApplied] = useState(false);
  useEffect(() => {
    if (benchmarks.data && !apiApplied) {
      const apiValues = apiBenchmarksToSliderValues(benchmarks.data as unknown as Record<string, Record<string, number>>);
      if (Object.keys(apiValues).length > 0) {
        setValues((prev) => ({ ...prev, ...apiValues }));
        setApiApplied(true);
      }
    }
  }, [benchmarks.data, apiApplied]);

  const sliders = BENCHMARK_CONFIG[activeTab];

  return (
    <section className="animate-rise" style={{ animationDelay: "0.25s" }}>
      <SectionHeader title="Benchmark Configuration" meta="PERFORMANCE TARGETS" />

      <DataGuard
        {...benchmarks}
        skeleton={
          <div className="flex flex-col gap-4 mt-4">
            <Skeleton rows={1} height="h-10" />
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-5">
              <Skeleton rows={3} /><Skeleton rows={3} />
              <Skeleton rows={3} /><Skeleton rows={3} />
            </div>
          </div>
        }
        emptyHeadline="No benchmarks"
        emptyBody="Benchmark configuration data is not yet available."
        className="mt-4"
      >
        {(_apiBenchmarks) => (
          <Card className="p-5">
            {/* Tab strip */}
            <div className="flex gap-1 p-1 rounded-[10px] border border-line bg-panel2 mb-6">
              {BENCHMARK_TABS.map((tab) => (
                <button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={`
                    px-3 py-1.5 rounded-pill font-mono text-[10px] font-semibold tracking-[.06em]
                    transition-colors duration-150 cursor-pointer
                    ${activeTab === tab
                      ? "bg-cyan text-cyan-ink"
                      : "text-fg3 hover:text-fg2 bg-transparent"
                    }
                  `}
                >
                  {tab.toUpperCase()}
                </button>
              ))}
            </div>

            {/* Slider grid: 2 columns */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-5">
              {sliders.map((s) => {
                const val = values[s.key] ?? s.default;
                return (
                  <div key={s.key} className="flex flex-col gap-2">
                    <div className="flex items-center justify-between">
                      <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
                        {s.label.toUpperCase()}
                      </span>
                      <span className="font-mono text-[12px] font-semibold">
                        {s.unit === "$" ? `$${val}` : `${val}${s.unit}`}
                      </span>
                    </div>
                    <input
                      type="range"
                      min={s.min}
                      max={s.max}
                      step={s.step}
                      value={val}
                      onChange={(e) =>
                        setValues((prev) => ({
                          ...prev,
                          [s.key]: parseFloat(e.target.value),
                        }))
                      }
                      className="w-full"
                      style={{ accentColor: "var(--cyan)" }}
                    />
                    <div className="flex justify-between font-mono text-[8px] text-fg3">
                      <span>{s.unit === "$" ? `$${s.min}` : `${s.min}${s.unit}`}</span>
                      <span>{s.unit === "$" ? `$${s.max}` : `${s.max}${s.unit}`}</span>
                    </div>
                  </div>
                );
              })}
            </div>
          </Card>
        )}
      </DataGuard>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Main SettingsView component                                        */
/* ------------------------------------------------------------------ */

export function SettingsView() {
  return (
    <div className="flex flex-col gap-6">
      {/* ===== Top row: 3 settings cards ===== */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <AppModeCard />
        <AppearanceCard />
        <DataExportCard />
      </div>

      {/* ===== Data Sources (live from BFF) ===== */}
      <DataSourcesSection />

      {/* ===== Benchmarks ===== */}
      <BenchmarkSection />
    </div>
  );
}
