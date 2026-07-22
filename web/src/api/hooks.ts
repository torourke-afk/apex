/**
 * Typed React hooks for BFF endpoints.
 *
 * Every hook calls the live BFF via apiFetch. No mock data — the BFF itself
 * has fallback data for any endpoint whose DB tables are empty.
 *
 * Adapter functions map BFF response shapes (snake_case, different field names)
 * to the stable UI view-model types that surfaces consume.
 *
 * All hooks accept an optional Filters argument. When provided the filters are
 * included in the React Query key so data automatically refetches when the user
 * changes the global filter bar.  For BFF endpoints that support server-side
 * filtering (spend/*, funnel/*) the filters are also converted to query params.
 */
import { useState, useCallback } from "react";
import { useQuery as useRQ, keepPreviousData } from "@tanstack/react-query";
import { apiFetch } from "./client";
import type { Filters } from "../shell/ShellProvider";

/* ── Async wrapper (moved from lib/hooks.ts) ──────────────────── */

export interface Async<T> {
  data: T | null;
  loading: boolean;
  error: string | null;
  reload: () => void;
}

function useQuery<T>(key: unknown[], fn: () => Promise<T>): Async<T> {
  const q = useRQ({
    queryKey: key,
    queryFn: fn,
    /* Keep previous data visible while refetching on filter changes.
       Prevents full-page CLS / loading flash when toggling DMA filters. */
    placeholderData: keepPreviousData,
  });
  return {
    data: (q.data ?? null) as T | null,
    loading: q.isLoading,
    error: q.error ? (q.error as Error).message : null,
    reload: () => q.refetch(),
  };
}

/* ── Filter → query-param helpers ────────────────────────────── */

/** Stable serialisation of the Filters object for React Query keys.
 *  Returns an array of primitives so RQ's structural comparison works. */
function filterKey(f?: Filters): unknown[] {
  if (!f) return [];
  return [f.dateRange, f.products.join(","), f.dmas.join(","), f.channels.join(",")];
}

/** Extract the DMA numeric code from a label like "Cincinnati (515)" → "515" */
function dmaCode(label: string): string {
  const m = label.match(/\((\d+)\)/);
  return m ? m[1] : label;
}

/** Convert a dateRange label to ISO date_start / date_end strings. */
function dateRangeToISO(dr: string): { date_start: string; date_end: string } {
  const now = new Date();
  const end = now.toISOString().slice(0, 10);
  let start: Date;
  if (dr === "YTD") {
    start = new Date(now.getFullYear(), 0, 1);
  } else {
    const weeks = dr === "Last 4 weeks" ? 4 : dr === "Last 26 weeks" ? 26 : 12;
    start = new Date(now.getTime() - weeks * 7 * 86_400_000);
  }
  return { date_start: start.toISOString().slice(0, 10), date_end: end };
}

/** Build a query-string suffix (including leading ?) for BFF endpoints that
 *  accept date_start, date_end, and dma params (spend/*, funnel/*). */
function filtersToQS(f?: Filters): string {
  if (!f) return "";
  const p = new URLSearchParams();
  const { date_start, date_end } = dateRangeToISO(f.dateRange);
  p.set("date_start", date_start);
  p.set("date_end", date_end);
  if (f.dmas.length > 0) {
    p.set("dma", f.dmas.map(dmaCode).join(","));
  }
  return `?${p.toString()}`;
}

/* ── Types exposed to surfaces ─────────────────────────────────── */

export interface BudgetOverview {
  cards: Array<{ label: string; value: string; delta?: string; delta_color?: string }>;
}

export interface ChannelSpendBreakdown {
  categories: string[];
  actual: number[];
  plan: number[];
}

export interface DMASpend {
  dma: string;
  tier: number;
  spend: number;
  cpihh: number;
  /** Nielsen DMA code (e.g. "515" for Cincinnati) — from BFF centroid registry */
  dma_code?: string;
  /** Albers USA projected X coordinate */
  cx?: number;
  /** Albers USA projected Y coordinate */
  cy?: number;
  /** Suggested circle radius */
  r?: number;
  /** Two-letter state abbreviation */
  state?: string;
}

export interface FunnelStage {
  stage: string;
  volume: number;
  conversion_rate: number;
  benchmark_rate: number;
  drop_off: number;
  dollar_impact: number;
}

export interface KPIItem {
  id: string;
  label: string;
  value: string;
  delta: string;
  deltaDir: "up" | "down";
  spark: number[];
  targetMet?: boolean;
  invertDelta?: boolean;
}

export interface FinancialSummary {
  strips: Array<{ label: string; value: string; detail: string; detailColor: string }>;
}

export interface AlertItem {
  id: string;
  title: string;
  meta: string;
  tone: "critical" | "warning" | "info";
}

/* SEMOverview — removed in P3 (useSEMOverview deleted) */
/* ShareOfSearch — removed in P3 (useBrandAwareness deleted) */

export interface ApprovalItem {
  id: string;
  title: string;
  status: string;
  directive_type: string;
  priority: string;
}

export interface PipelineItem {
  name: string;
  product_line: string;
  stage: string;
  owner: string;
  priority: string;
  confidence_score: number;
}

export interface TestingVelocity {
  tests_run: number;
  won: number;
  win_rate: number;
  avg_lift_pct: number;
  avg_duration_days: number;
  top_winning_test: string;
}

export interface SurvivalCurve {
  segment: string;
  survival_probs: number[];
}

export interface BenchmarkData {
  funnel: Record<string, number>;
  media: Record<string, number>;
  efficiency: Record<string, number>;
  nbd: Record<string, number>;
  retention: Record<string, number>;
}

/* ── Ops surface types ────────────────────────────────────────── */

export interface CalendarEvent {
  id: string;
  title: string;
  event_type: string;
  date: string;
  channel: string;
  owner: string;
  status: string;
  description: string;
}

export interface OpsCalendarData {
  events: CalendarEvent[];
  total: number;
  as_of: string;
}

export interface CapacityItem {
  id: string;
  team: string;
  channel: string;
  period: string;
  allocated_hours: number;
  used_hours: number;
  available_hours: number;
  utilization_pct: number;
  projects: string[];
}

export interface OpsCapacityData {
  members: CapacityItem[];
  summary: {
    total: number;
    total_allocated_hours: number;
    total_used_hours: number;
    avg_utilization_pct: number;
  };
  as_of: string;
}

export interface CompetitiveFeedItem {
  id: string;
  competitor: string;
  category: string;
  headline: string;
  summary: string;
  source: string;
  detected_at: string;
  impact: string;
  tags: string[];
}

export interface CompetitiveFeedData {
  items: CompetitiveFeedItem[];
  total: number;
  as_of: string;
}

/* ── BFF response shapes (mirror src/api/*.py) ─────────────────── */

interface BFFKpi {
  name: string;
  value: number;
  target: number;
  delta: number;
  delta_pct: number;
  sparkline_data: number[];
  trend: string;
  alert_status: string | null;
  format_type?: string | null;
}

interface BFFFinancialMetric {
  label: string;
  value: number;
  delta: number;
  format: string;
}

interface BFFAlert {
  severity: string;
  kpi_name: string;
  description: string;
  created_at: string;
  module_link: string | null;
}

interface BFFSpendKpi {
  label: string;
  value: number;
  delta: number;
  format: string;
}

interface BFFDmaMarket {
  Market: string;
  Tier: string;
  "Monthly Spend": number;
  CPIHH: number;
  Funded: number;
  /** Centroid fields — injected by BFF dma_centroids module */
  dma_code?: string;
  cx?: number;
  cy?: number;
  r?: number;
  state?: string;
}

interface BFFApprovalItem {
  id: string;
  title: string;
  approval_type: string;
  priority: string;
  owner: string;
  due_date: string | null;
  status: string;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

interface BFFPipelineItem {
  id: string;
  name: string;
  product_line: string;
  stage: string;
  owner: string;
  target_date: string;
  priority: string;
  confidence_score: number;
  description: string;
}

/* BFFSEMMetric — removed in P3 (useSEMOverview deleted) */

/* ── Helpers ───────────────────────────────────────────────────── */

const fmtCurrency = (n: number): string => {
  const abs = Math.abs(n);
  if (abs >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `$${(n / 1_000).toFixed(0)}k`;
  return `$${Math.round(n)}`;
};

/** Signed currency for delta values: "+$45k" / "−$371K" */
const fmtCurrencyDelta = (n: number): string => {
  const abs = Math.abs(n);
  const sign = n > 0 ? "+" : n < 0 ? "-" : "";
  if (abs >= 1_000_000) return `${sign}$${(abs / 1_000_000).toFixed(1)}M`;
  if (abs >= 1_000) return `${sign}$${(abs / 1_000).toFixed(0)}k`;
  return `${sign}$${Math.round(abs)}`;
};

const fmtPct = (n: number): string => `${n.toFixed(1)}%`;

const fmtNum = (n: number): string =>
  Math.abs(n) >= 1000 ? n.toLocaleString(undefined, { maximumFractionDigits: 0 }) : `${n}`;

/* ── Hooks ──────────────────────────────────────────────────────── */

/** Scorecard surface: KPI deck */
export function useScoreboardKPIs(filters?: Filters): Async<{ kpis: KPIItem[]; as_of: string }> {
  return useQuery(["scoreboard-kpis", ...filterKey(filters)], async () => {
    const res = await apiFetch<{ kpis: BFFKpi[]; as_of: string }>(`/api/scorecard/kpis${filtersToQS(filters)}`);
    return {
      kpis: res.kpis.slice(0, 6).map((k) => {
        const invert = /cpl|cpa|cpihh|cac|cost/i.test(k.name);
        return {
          id: k.name.toLowerCase().replace(/\s+/g, "-"),
          label: k.name,
          value: k.format_type === "currency" ? fmtCurrency(k.value) :
                 k.format_type === "percent" ? fmtPct(k.value) :
                 fmtNum(k.value),
          delta: `${Math.abs(k.delta_pct).toFixed(1)}%`,
          deltaDir: (k.delta >= 0 ? "up" : "down") as "up" | "down",
          spark: k.sparkline_data,
          targetMet: invert ? k.value <= k.target : k.value >= k.target,
          invertDelta: invert,
        };
      }),
      as_of: res.as_of,
    };
  });
}

/** Scorecard surface: financial strip */
export function useFinancialSummary(filters?: Filters): Async<FinancialSummary> {
  return useQuery(["financial-summary", ...filterKey(filters)], async () => {
    const res = await apiFetch<{ metrics: BFFFinancialMetric[]; as_of: string }>(`/api/scorecard/financial-summary${filtersToQS(filters)}`);
    return {
      strips: res.metrics.map((m) => ({
        label: m.label.toUpperCase(),
        value: m.format === "currency" ? fmtCurrency(m.value) :
               m.format === "percent" ? fmtPct(m.value) :
               fmtNum(m.value),
        detail: m.delta !== 0
          ? m.format === "currency"
            ? `${m.delta >= 0 ? "up" : "down"} ${fmtCurrency(Math.abs(m.delta))}`
            : `${m.delta >= 0 ? "up" : "down"} ${Math.abs(m.delta).toFixed(1)}%`
          : "",
        detailColor: m.delta >= 0 ? "text-positive" : "text-warning",
      })),
    };
  });
}

/** Scorecard surface: alert wire */
export function useAlerts(filters?: Filters): Async<{ alerts: AlertItem[]; total_count: number }> {
  return useQuery(["alerts", ...filterKey(filters)], async () => {
    const res = await apiFetch<{ alerts: BFFAlert[]; total_count: number }>(`/api/scorecard/alerts?limit=10${filtersToQS(filters).replace("?", "&")}`);
    return {
      alerts: res.alerts.map((a) => ({
        id: `${a.kpi_name}-${a.created_at}`,
        title: a.description,
        meta: `${a.kpi_name} · ${new Date(a.created_at).toLocaleString()}`,
        tone: (a.severity === "error" ? "critical" : a.severity === "warning" ? "warning" : "info") as AlertItem["tone"],
      })),
      total_count: res.total_count,
    };
  });
}

/** Spend surface: top-row KPI cards */
export function useSpendOverview(filters?: Filters): Async<BudgetOverview> {
  return useQuery<BudgetOverview>(["spend-overview", ...filterKey(filters)], async () => {
    const res = await apiFetch<{ kpis: BFFSpendKpi[] }>(`/api/spend/overview${filtersToQS(filters)}`);
    return {
      cards: res.kpis.map((k) => ({
        label: k.label,
        value: k.format === "currency" ? fmtCurrency(k.value) :
               k.format === "percent" ? `${k.value.toFixed(0)}%` :
               fmtNum(k.value),
        delta: k.delta !== 0
          ? k.format === "currency"
            ? fmtCurrencyDelta(k.delta)
            : `${k.delta > 0 ? "+" : ""}${k.delta.toFixed(1)}%`
          : undefined,
        delta_color: k.delta >= 0 ? "positive" : "warning",
      })),
    };
  });
}

/** Spend surface: pacing chart data */
export function useSpendPacing(filters?: Filters): Async<ChannelSpendBreakdown> {
  return useQuery<ChannelSpendBreakdown>(["spend-pacing", ...filterKey(filters)], async () => {
    return apiFetch<ChannelSpendBreakdown>(`/api/spend/pacing${filtersToQS(filters)}`);
  });
}

/** Spend surface: channel allocation breakdown */
export function useChannelAllocation(filters?: Filters): Async<{
  channels: Array<{ name: string; amount: number; pct: number }>;
  total: number;
}> {
  return useQuery(["spend-channel-alloc", ...filterKey(filters)], async () => {
    return apiFetch<{
      channels: Array<{ name: string; amount: number; pct: number }>;
      total: number;
    }>(`/api/spend/channel-allocation${filtersToQS(filters)}`);
  });
}

/** Spend surface: next-best-dollar reallocation ledger */
export function useReallocations(filters?: Filters): Async<{
  moves: Array<{
    from_channel: string;
    to_channel: string;
    rationale: string;
    delta: number;
    roas_impact: number;
    status: string;
  }>;
}> {
  return useQuery(["spend-reallocations", ...filterKey(filters)], async () => {
    return apiFetch<{
      moves: Array<{
        from_channel: string;
        to_channel: string;
        rationale: string;
        delta: number;
        roas_impact: number;
        status: string;
      }>;
    }>("/api/spend/reallocations");
  });
}

/** Scorecard surface: campaign leaderboard */
export function useCampaigns(filters?: Filters): Async<{
  campaigns: Array<{
    name: string;
    channel: string;
    spend: number;
    roas: number;
    funded: number;
    badge: string;
  }>;
  count: number;
}> {
  return useQuery(["scorecard-campaigns", ...filterKey(filters)], async () => {
    return apiFetch<{
      campaigns: Array<{
        name: string;
        channel: string;
        spend: number;
        roas: number;
        funded: number;
        badge: string;
      }>;
      count: number;
    }>(`/api/scorecard/campaigns${filtersToQS(filters)}`);
  });
}

/** Spend surface: DMA geo table */
export function useSpendDMA(filters?: Filters): Async<DMASpend[]> {
  return useQuery<DMASpend[]>(["spend-dma", ...filterKey(filters)], async () => {
    const res = await apiFetch<{ markets: BFFDmaMarket[] }>(`/api/spend/dma${filtersToQS(filters)}`);
    return res.markets.map((m) => ({
      dma: m.Market,
      tier: parseInt(m.Tier) || 1,
      spend: m["Monthly Spend"],
      cpihh: m.CPIHH,
      dma_code: m.dma_code,
      cx: m.cx,
      cy: m.cy,
      r: m.r,
      state: m.state,
    }));
  });
}

/** Funnel surface: stage data */
export function useFunnelStages(filters?: Filters): Async<FunnelStage[]> {
  return useQuery<FunnelStage[]>(["funnel-stages", ...filterKey(filters)], async () => {
    const res = await apiFetch<{
      stages: string[];
      values: number[];
      benchmarks: number[];
      rates: number[];
      bench_rates: number[];
      avg_account_ltv: number;
    }>(`/api/funnel/stages${filtersToQS(filters)}`);
    return res.stages.map((stage, i) => ({
      stage,
      volume: res.values[i] ?? 0,
      conversion_rate: (res.rates[i] ?? 0) * 100,
      benchmark_rate: (res.bench_rates[i] ?? 0) * 100,
      drop_off: i < res.stages.length - 1 ? (res.values[i] ?? 0) - (res.values[i + 1] ?? 0) : 0,
      dollar_impact: i < res.stages.length - 1
        ? ((res.values[i] ?? 0) - (res.values[i + 1] ?? 0)) * (res.avg_account_ltv ?? 0) * 0.01
        : 0,
    }));
  });
}

/* useSEMOverview — removed in P3 (unused, Media uses useMediaChannels instead) */

/* ── Brand Awareness BFF hooks ─────────────────────────────── */

export interface ShareOfSearchPoint {
  date: string;
  brand_msv: number;
  total_msv: number;
  share_of_search: number;
  rank: number;
}

export interface PeerComparisonItem {
  brand: string;
  keyword: string;
  msv: number;
  share: number;
  rank: number;
  msv_delta: number;
  share_delta: number;
}

/** Brand Awareness: Fifth Third's share-of-search trend (monthly) */
export function useShareOfSearch(filters?: Filters): Async<{ points: ShareOfSearchPoint[] }> {
  return useQuery(["brand-sos", ...filterKey(filters)], async () => {
    const res = await apiFetch<{ share_of_search: ShareOfSearchPoint[] }>(
      `/api/brand-awareness/share-of-search${filtersToQS(filters)}`,
    );
    return { points: res.share_of_search ?? [] };
  });
}

/** Brand Awareness: peer comparison table (latest period) */
export function usePeerComparison(filters?: Filters): Async<{ peers: PeerComparisonItem[] }> {
  return useQuery(["brand-peers", ...filterKey(filters)], async () => {
    const res = await apiFetch<{ peer_comparison: PeerComparisonItem[] }>(
      `/api/brand-awareness/peer-comparison${filtersToQS(filters)}`,
    );
    return { peers: res.peer_comparison ?? [] };
  });
}

/** Operations surface: approval queue items */
export function useApprovals(filters?: Filters): Async<ApprovalItem[]> {
  return useQuery<ApprovalItem[]>(["approvals", ...filterKey(filters)], async () => {
    const res = await apiFetch<{ items: BFFApprovalItem[]; count: number }>("/api/ops/approvals");
    return res.items.map((a) => ({
      id: a.id,
      title: a.title,
      status: a.status,
      directive_type: a.approval_type,
      priority: a.priority,
    }));
  });
}

/** Operations surface: launch calendar */
export function useOpsCalendar(filters?: Filters): Async<OpsCalendarData> {
  return useQuery<OpsCalendarData>(["ops-calendar", ...filterKey(filters)], async () => {
    const qs = filtersToQS(filters);
    return apiFetch<OpsCalendarData>(`/api/ops/calendar${qs}`);
  });
}

/** Operations surface: team capacity */
export function useOpsCapacity(filters?: Filters): Async<OpsCapacityData> {
  return useQuery<OpsCapacityData>(["ops-capacity", ...filterKey(filters)], async () => {
    const qs = filtersToQS(filters);
    return apiFetch<OpsCapacityData>(`/api/ops/capacity${qs}`);
  });
}

/** Operations surface: competitive intelligence feed */
export function useCompetitiveFeed(filters?: Filters): Async<CompetitiveFeedData> {
  return useQuery<CompetitiveFeedData>(["competitive-feed", ...filterKey(filters)], async () => {
    const qs = filtersToQS(filters);
    return apiFetch<CompetitiveFeedData>(`/api/ops/competitive-feed${qs}`);
  });
}

/* useProductPipeline — removed in P3 (Product surface uses useProductPerformance instead) */

/** Product surface: A/B testing velocity stats */
export function useTestingVelocity(filters?: Filters): Async<TestingVelocity> {
  return useQuery<TestingVelocity>(["testing-velocity", ...filterKey(filters)], async () => {
    const res = await apiFetch<{
      tests_run: number;
      tests_won: number;
      win_rate: number;
      avg_lift_pct: number;
      avg_duration_days: number;
      top_winning_test: string;
    }>("/api/product/testing-velocity");
    return {
      tests_run: res.tests_run,
      won: res.tests_won,
      win_rate: res.win_rate,
      avg_lift_pct: res.avg_lift_pct,
      avg_duration_days: res.avg_duration_days,
      top_winning_test: res.top_winning_test,
    };
  });
}

/** Retention surface: survival curves by cohort */
export function useRetentionCurves(filters?: Filters): Async<SurvivalCurve[]> {
  return useQuery<SurvivalCurve[]>(["retention-curves", ...filterKey(filters)], async () => {
    const res = await apiFetch<{
      segment_col: string;
      horizon_days: number;
      curves: Record<string, number[]>;
    }>("/api/retention/curves");
    return Object.entries(res.curves).map(([segment, probs]) => ({
      segment,
      survival_probs: probs,
    }));
  });
}

/** Settings surface: benchmark configuration */
export function useBenchmarks(filters?: Filters): Async<BenchmarkData> {
  return useQuery<BenchmarkData>(["benchmarks", ...filterKey(filters)], async () => {
    const res = await apiFetch<{
      benchmarks: {
        sem?: Record<string, number>;
        social?: Record<string, number>;
        simulator?: Record<string, unknown>;
      };
    }>("/api/settings/benchmarks");
    const b = res.benchmarks;
    return {
      funnel: { visit_app: 8.0, app_complete: 62, complete_fund: 28, min_cvr: 1.4, ...(b.simulator as Record<string, number> || {}) },
      media: { roas: 3.5, cpa: b.sem?.cpl ?? 84, brand_lift: 5.0, freq_cap: 7 },
      efficiency: { cpihh: b.sem?.cpl ?? 84, mroas: 2.5, sat: 85, pacing: 5 },
      nbd: { ntb: 42, xsell: 90, activation: 75, deepen: 60 },
      retention: { mob6: 74, churn90: 8.0, ltv: 4000, payback: 10 },
    };
  });
}

/* ── Simulator hooks ─────────────────────────────────────────── */

/** Input shape for POST /api/simulate/ (mirrors BFF ScenarioRequest). */
export interface SimulateInput {
  name?: string;
  mode?: string;
  total_spend: number;
  channels: Record<
    string,
    {
      spend_pct: number;
      cpc: number;
      cpl: number;
      use_cpl?: boolean;
      brand_lift_pct?: number;
    }
  >;
  organic_multiplier?: number;
  aeo_rate?: number;
  visit_to_app_start?: number;
  app_start_to_apply?: number;
  apply_to_approve?: number;
  approve_to_open?: number;
  open_to_fund?: number;
  mob6_rate?: number;
  mob12_rate?: number;
  pfi_conversion_rate?: number;
  ltv_per_hh?: number;
  pfi_ltv_multiplier?: number;
  run_comparison?: boolean;
}

/** Response shape from POST /api/simulate/ (flat dict from dataclass). */
export interface SimulateResult {
  error?: string;
  funded_accounts?: number;
  total_funded?: number;
  total_spend?: number;
  blended_cpihh?: number;
  blended_roas?: number;
  attributed_revenue?: number;
  net_margin_pct?: number;
  mob6_retained?: number;
  portfolio_ltv?: number;
  channels?: Record<string, {
    spend: number;
    clicks: number;
    leads: number;
    funded: number;
    cpihh: number;
    roas: number;
  }>;
  [key: string]: unknown;
}

/** Mutation-style return value — not auto-fetched on mount. */
export interface Mutation<TInput, TResult> {
  mutate: (input: TInput) => Promise<TResult | null>;
  data: TResult | null;
  loading: boolean;
  error: string | null;
  reset: () => void;
}

/** Preset metadata from GET /api/simulate/presets. */
export interface SimPreset {
  name: string;
  label: string;
  description: string;
  available: boolean;
  config: { budget: number; brand: number; sem: number; social: number } | null;
}

/**
 * Mutation-style hook: POST /api/simulate/
 * Does NOT auto-fetch — call `mutate(input)` to run a simulation.
 */
export function useSimulate(): Mutation<SimulateInput, SimulateResult> {
  const [data, setData] = useState<SimulateResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutate = useCallback(async (input: SimulateInput): Promise<SimulateResult | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<SimulateResult>("/api/simulate/", {
        method: "POST",
        body: JSON.stringify(input),
      });
      if (result.error) {
        setError(String(result.error));
        setData(null);
        return null;
      }
      setData(result);
      return result;
    } catch (err) {
      const msg = err instanceof Error ? err.message : "Simulation failed";
      setError(msg);
      setData(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => {
    setData(null);
    setError(null);
    setLoading(false);
  }, []);

  return { mutate, data, loading, error, reset };
}

/** GET /api/simulate/presets — available scenario presets. */
export function useSimPresets(): Async<{ presets: SimPreset[] }> {
  return useQuery(["sim-presets"], () =>
    apiFetch<{ presets: SimPreset[] }>("/api/simulate/presets"),
  );
}

/* ── Creative surface types & hooks ──────────────────────────── */

export interface CreativeAsset {
  name: string;
  theme: string;
  format: string;
  fatigue: "FRESH" | "WATCH" | "TIRED";
  ctr: number;
  cvr: number;
  spend: number;
  impressions: number;
  clicks: number;
  conversions: number;
  thumb_gradient: string;
}

export interface CreativeOverview {
  total_assets: number;
  total_spend: number;
  blended_ctr: number;
  blended_cvr: number;
  total_impressions: number;
  total_conversions: number;
  assets: CreativeAsset[];
}

export interface MessageTheme {
  name: string;
  score: number;
}

/** Creative surface: overview with top creative units */
export function useCreativeOverview(filters?: Filters): Async<CreativeOverview> {
  return useQuery<CreativeOverview>(["creative-overview", ...filterKey(filters)], async () => {
    return apiFetch<CreativeOverview>(`/api/creative/overview${filtersToQS(filters)}`);
  });
}

/* useCreativeAssets — removed in P3 (Creative surface uses useCreativeOverview instead) */

/** Creative surface: message theme resonance */
export function useCreativeThemes(filters?: Filters): Async<{ themes: MessageTheme[] }> {
  return useQuery(["creative-themes", ...filterKey(filters)], async () => {
    return apiFetch<{ themes: MessageTheme[] }>(`/api/creative/themes${filtersToQS(filters)}`);
  });
}

/* ── Modeling surface types & hooks ─────────────────────────── */

export interface AttributionChannel {
  name: string;
  value: number;
  color: string;
}

export interface ModelRegistryItem {
  name: string;
  model_type: string;
  r_squared: number;
  status: string;
  trained_ago: string;
  last_trained: string;
  version: string;
}

export interface IncrementalityTest {
  name: string;
  lift: number;
  method: string;
  p_value: number;
  status: string;
  start_date: string;
  end_date: string;
}

/** Modeling surface: channel attribution */
export function useAttribution(filters?: Filters): Async<{
  channels: AttributionChannel[];
  model_type: string;
  last_updated: string;
}> {
  return useQuery(["modeling-attribution", ...filterKey(filters)], async () => {
    return apiFetch<{
      channels: AttributionChannel[];
      model_type: string;
      last_updated: string;
    }>(`/api/modeling/attribution${filtersToQS(filters)}`);
  });
}

/** Modeling surface: model registry */
export function useModelRegistry(filters?: Filters): Async<{ models: ModelRegistryItem[]; count: number }> {
  return useQuery(["modeling-registry", ...filterKey(filters)], async () => {
    return apiFetch<{ models: ModelRegistryItem[]; count: number }>(`/api/modeling/registry${filtersToQS(filters)}`);
  });
}

/** Modeling surface: incrementality tests */
export function useIncrementalityTests(filters?: Filters): Async<{ tests: IncrementalityTest[]; count: number }> {
  return useQuery(["modeling-incrementality", ...filterKey(filters)], async () => {
    return apiFetch<{ tests: IncrementalityTest[]; count: number }>(`/api/modeling/incrementality${filtersToQS(filters)}`);
  });
}

/* ── Connector & Sync hooks ───────────────────────────────────── */

import type { ConnectorStatus, SyncStatus, SyncLogEntry } from "./types";

/** Settings / Data Sources: connector + sync status */
export function useSyncStatus(): Async<SyncStatus> {
  return useQuery<SyncStatus>(["sync-status"], () =>
    apiFetch<SyncStatus>("/api/sync/status"),
  );
}

/** Settings / Data Sources: list connectors */
export function useConnectors(): Async<{
  connectors: ConnectorStatus[];
  domain_assignments: Record<string, string>;
  available_domains: string[];
}> {
  return useQuery(["connectors"], () =>
    apiFetch<{
      connectors: ConnectorStatus[];
      domain_assignments: Record<string, string>;
      available_domains: string[];
    }>("/api/connectors"),
  );
}

/** Settings / Data Sources: recent sync log */
export function useSyncLog(limit = 20): Async<{ entries: SyncLogEntry[] }> {
  return useQuery(["sync-log", limit], () =>
    apiFetch<{ entries: SyncLogEntry[] }>(`/api/sync/log?limit=${limit}`),
  );
}

/* ══════════════════════════════════════════════════════════════
   P2 — Media surface hooks
   ══════════════════════════════════════════════════════════════ */

export interface MediaChannel {
  name: string;
  color: string;
  spend: number;
  cpihh: number;
  cvr: number;
  roas: number;
  trend: number[];
}

export interface SaturationCurve {
  label: string;
  color: string;
  k: number;
  max_y: number;
  dot_x: number;
}

export interface EfficiencyBubble {
  label: string;
  x: number;
  y: number;
  r: number;
  color: string;
}

export function useMediaChannels(filters?: Filters): Async<{ channels: MediaChannel[]; count: number; total_spend: number }> {
  const fk = filterKey(filters);
  return useQuery(["media-channels", ...fk], () => {
    const params = new URLSearchParams();
    if (filters) {
      const dr = dateRangeToISO(filters.dateRange);
      params.set("date_start", dr.date_start);
      params.set("date_end", dr.date_end);
      if (filters.channels.length) params.set("channel", filters.channels.join(","));
    }
    const qs = params.toString();
    return apiFetch<{ channels: MediaChannel[]; count: number; total_spend: number }>(`/api/media/channels${qs ? `?${qs}` : ""}`);
  });
}

export function useMediaSaturation(filters?: Filters): Async<{ curves: SaturationCurve[] }> {
  const fk = filterKey(filters);
  return useQuery(["media-saturation", ...fk], () =>
    apiFetch<{ curves: SaturationCurve[] }>("/api/media/saturation"),
  );
}

export function useMediaEfficiency(filters?: Filters): Async<{ bubbles: EfficiencyBubble[]; portfolio_avg_roas: number }> {
  const fk = filterKey(filters);
  return useQuery(["media-efficiency", ...fk], () =>
    apiFetch<{ bubbles: EfficiencyBubble[]; portfolio_avg_roas: number }>("/api/media/efficiency"),
  );
}

/* ══════════════════════════════════════════════════════════════
   P2 — Audience surface hooks
   ══════════════════════════════════════════════════════════════ */

export interface AudienceSegment {
  name: string;
  share: number;
  tag: string;
  tag_color: string;
  note: string;
}

export interface TopMarket {
  rank: number;
  name: string;
  code: string;
  roas: number;
  funded: number;
}

export function useAudienceSegments(filters?: Filters): Async<{ segments: AudienceSegment[]; count: number }> {
  const fk = filterKey(filters);
  return useQuery(["audience-segments", ...fk], () =>
    apiFetch<{ segments: AudienceSegment[]; count: number }>("/api/audience/segments"),
  );
}

export function useTopMarkets(filters?: Filters): Async<{ markets: TopMarket[]; count: number }> {
  const fk = filterKey(filters);
  return useQuery(["top-markets", ...fk], () => {
    const params = new URLSearchParams();
    if (filters?.dmas.length) params.set("dma", filters.dmas.map(dmaCode).join(","));
    const qs = params.toString();
    return apiFetch<{ markets: TopMarket[]; count: number }>(`/api/audience/top-markets${qs ? `?${qs}` : ""}`);
  });
}

/* ══════════════════════════════════════════════════════════════
   P2 — Product surface hooks
   ══════════════════════════════════════════════════════════════ */

export interface ProductPerf {
  name: string;
  funded: number;
  cpihh: number;
  ltv: number;
  margin: number;
  margin_status: "positive" | "warning";
}

export interface ConvFunnelStage {
  label: string;
  volume: string;
  pct: number;
}

export interface ConvFunnel {
  name: string;
  stages: ConvFunnelStage[];
}

export function useProductPerformance(filters?: Filters): Async<{ products: ProductPerf[]; conv_funnels: ConvFunnel[]; count: number }> {
  const fk = filterKey(filters);
  return useQuery(["product-performance", ...fk], () => {
    const params = new URLSearchParams();
    if (filters?.products.length) params.set("product", filters.products.join(","));
    const qs = params.toString();
    return apiFetch<{ products: ProductPerf[]; conv_funnels: ConvFunnel[]; count: number }>(`/api/product/performance${qs ? `?${qs}` : ""}`);
  });
}

/* ══════════════════════════════════════════════════════════════
   P2 — Funnel Sankey hook
   ══════════════════════════════════════════════════════════════ */

export interface SankeyChannel {
  name: string;
  pct: number;
  color: string;
  label: string;
}

export interface SankeyStage {
  label: string;
  volume: string;
}

export function useFunnelSankey(filters?: Filters): Async<{ channels: SankeyChannel[]; stages: SankeyStage[]; stage_factors: number[] }> {
  const fk = filterKey(filters);
  return useQuery(["funnel-sankey", ...fk], () => {
    const params = new URLSearchParams();
    if (filters) {
      const dr = dateRangeToISO(filters.dateRange);
      params.set("date_start", dr.date_start);
      params.set("date_end", dr.date_end);
      if (filters.channels.length) params.set("channel", filters.channels.join(","));
    }
    const qs = params.toString();
    return apiFetch<{ channels: SankeyChannel[]; stages: SankeyStage[]; stage_factors: number[] }>(`/api/funnel/sankey${qs ? `?${qs}` : ""}`);
  });
}

/* ══════════════════════════════════════════════════════════════
   P2 — Retention KPI + LTV hooks
   ══════════════════════════════════════════════════════════════ */

export interface RetentionKPI {
  label: string;
  value: string;
  value_suffix: string | null;
  delta: string;
  color: string;
}

export interface LtvPoint {
  mo: number;
  ltv: number;
}

export function useRetentionKPIs(filters?: Filters): Async<{ kpis: RetentionKPI[] }> {
  const fk = filterKey(filters);
  return useQuery(["retention-kpis", ...fk], () =>
    apiFetch<{ kpis: RetentionKPI[] }>("/api/retention/kpis"),
  );
}

export function useRetentionLTV(filters?: Filters): Async<{ points: LtvPoint[]; cpihh: number; breakeven_mob: number }> {
  const fk = filterKey(filters);
  return useQuery(["retention-ltv", ...fk], () =>
    apiFetch<{ points: LtvPoint[]; cpihh: number; breakeven_mob: number }>("/api/retention/ltv"),
  );
}

/* ══════════════════════════════════════════════════════════════
   Metric Layer hooks
   ══════════════════════════════════════════════════════════════ */

export interface MetricDef {
  id: string;
  label: string;
  description: string;
  format: string;
  grain: string;
  direction: string;
  domain: string;
  unit: string;
  tags: string[];
  sparkline: boolean;
}

export function useMetricCatalog(domain?: string): Async<{ metrics: MetricDef[]; count: number }> {
  const qs = domain ? `?domain=${domain}` : "";
  return useQuery(["metric-catalog", domain ?? "all"], () =>
    apiFetch<{ metrics: MetricDef[]; count: number }>(`/api/metrics/catalog${qs}`),
  );
}

/* ══════════════════════════════════════════════════════════════
   Allocation / Optimization Service (#11) hooks
   ══════════════════════════════════════════════════════════════ */

export interface AllocationCombo {
  campaign: string;
  dma: string;
  role: string;
  current_spend: number;
  current_accounts: number;
  optimal_spend: number;
  optimal_accounts: number;
  waste_gap_accounts: number;
  waste_gap_dollars: number;
}

export interface AllocationMove {
  from_channel: string;
  to_channel: string;
  delta: number;
  rationale: string;
  roas_impact: number;
  status: string;
}

export interface OptimizationResult {
  objective: string;
  budget: number;
  current_accounts: number;
  optimal_accounts: number;
  lift_pct: number;
  annual_waste_gap: number;
  top_moves: AllocationMove[];
}

export function useAllocationStatus(): Async<{ combos: AllocationCombo[]; total_waste_gap_dollars: number; total_spend: number; total_accounts: number; combo_count: number }> {
  return useQuery(["allocation-status"], () =>
    apiFetch<{ combos: AllocationCombo[]; total_waste_gap_dollars: number; total_spend: number; total_accounts: number; combo_count: number }>("/api/allocation/status"),
  );
}

export function useAllocationCurves(): Async<{ curves: Array<{ campaign: string; dma: string; points: Array<{ spend: number; accounts: number }>; current_dot: { spend: number; accounts: number }; optimal_dot: { spend: number; accounts: number } }> }> {
  return useQuery(["allocation-curves"], () =>
    apiFetch<{ curves: Array<{ campaign: string; dma: string; points: Array<{ spend: number; accounts: number }>; current_dot: { spend: number; accounts: number }; optimal_dot: { spend: number; accounts: number } }> }>("/api/allocation/curves"),
  );
}

export function useAllocationMoves(): Async<{ moves: AllocationMove[] }> {
  return useQuery(["allocation-moves"], () =>
    apiFetch<{ moves: AllocationMove[] }>("/api/allocation/moves"),
  );
}

export function useOptimize(): Mutation<{ objective: string; budget: number }, OptimizationResult> {
  const [data, setData] = useState<OptimizationResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutate = useCallback(async (input: { objective: string; budget: number }): Promise<OptimizationResult | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<OptimizationResult>("/api/allocation/optimize", {
        method: "POST",
        body: JSON.stringify(input),
      });
      setData(result);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Optimization failed");
      setData(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => { setData(null); setError(null); setLoading(false); }, []);
  return { mutate, data, loading, error, reset };
}

/* ══════════════════════════════════════════════════════════════
   Lens / NL-to-SQL Service (#12) hooks
   ══════════════════════════════════════════════════════════════ */

export interface LensResult {
  sql: string;
  columns: string[];
  rows: Array<Record<string, unknown>>;
  summary: string;
  chart_type: string | null;
  error: string | null;
}

export interface LensExample {
  category: string;
  question: string;
}

export function useLensQuery(): Mutation<{ question: string }, LensResult> {
  const [data, setData] = useState<LensResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mutate = useCallback(async (input: { question: string }): Promise<LensResult | null> => {
    setLoading(true);
    setError(null);
    try {
      const result = await apiFetch<LensResult>("/api/lens/query", {
        method: "POST",
        body: JSON.stringify(input),
      });
      if (result.error) {
        setError(result.error);
        setData(result);
        return result;
      }
      setData(result);
      return result;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Query failed");
      setData(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  const reset = useCallback(() => { setData(null); setError(null); setLoading(false); }, []);
  return { mutate, data, loading, error, reset };
}

export function useLensExamples(): Async<{ examples: LensExample[] }> {
  return useQuery(["lens-examples"], () =>
    apiFetch<{ examples: LensExample[] }>("/api/lens/examples"),
  );
}

export function useLensOntology(): Async<{ concepts: Record<string, unknown>; tables: string[] }> {
  return useQuery(["lens-ontology"], () =>
    apiFetch<{ concepts: Record<string, unknown>; tables: string[] }>("/api/lens/ontology"),
  );
}

/* ══════════════════════════════════════════════════════════════
   Launch / Site Factory Service (#13) hooks
   ══════════════════════════════════════════════════════════════ */

export interface LaunchProposal {
  id: string;
  name: string;
  persona: string;
  product: string;
  status: string;
  current_stage: string;
  created_at: string;
  updated_at: string;
  stages: Array<{
    stage: string;
    status: string;
    entered_at: string | null;
    completed_at: string | null;
  }>;
}

export interface LaunchStats {
  total: number;
  by_stage: Record<string, number>;
  by_status: Record<string, number>;
  avg_cycle_days: number;
  human_gates_waiting: number;
}

export function useLaunchPipeline(): Async<{ proposals: LaunchProposal[]; count: number }> {
  return useQuery(["launch-pipeline"], async () => {
    const res = await apiFetch<LaunchProposal[] | { proposals: LaunchProposal[]; count: number }>("/api/launch/pipeline");
    // BFF may return a bare array or a wrapped object
    if (Array.isArray(res)) {
      return { proposals: res, count: res.length };
    }
    return res;
  });
}

export function useLaunchStats(): Async<LaunchStats> {
  return useQuery(["launch-stats"], () =>
    apiFetch<LaunchStats>("/api/launch/stats"),
  );
}

/* ══════════════════════════════════════════════════════════════
   Audit Service (#14) hooks
   ══════════════════════════════════════════════════════════════ */

export interface AuditFinding {
  rule_id: string;
  rule_name: string;
  category: string;
  severity: string;
  verdict: string;
  evidence: string;
}

export interface AuditReport {
  id: string;
  target_url: string;
  scan_type: string;
  created_at: string;
  overall_score: number;
  pass_count: number;
  warn_count: number;
  fail_count: number;
  findings: AuditFinding[];
}

export interface AuditSummary {
  total_scans: number;
  avg_score: number;
  common_failures: Array<{ rule_id: string; rule_name: string; count: number }>;
}

export function useAuditReports(): Async<{ reports: AuditReport[]; count: number }> {
  return useQuery(["audit-reports"], () =>
    apiFetch<{ reports: AuditReport[]; count: number }>("/api/audit/reports"),
  );
}

export function useAuditSummary(): Async<AuditSummary> {
  return useQuery(["audit-summary"], () =>
    apiFetch<AuditSummary>("/api/audit/summary"),
  );
}

export function useAuditRules(): Async<{ rules: Array<{ id: string; name: string; category: string; severity: string; description: string }> }> {
  return useQuery(["audit-rules"], () =>
    apiFetch<{ rules: Array<{ id: string; name: string; category: string; severity: string; description: string }> }>("/api/audit/rules"),
  );
}

/* ══════════════════════════════════════════════════════════════
   Experiments Service (#15) hooks
   ══════════════════════════════════════════════════════════════ */

export interface ExperimentVariant {
  name: string;
  traffic_pct: number;
  visitors: number;
  conversions: number;
  rate: number;
}

export interface Experiment {
  id: string;
  name: string;
  hypothesis: string;
  metric: string;
  status: string;
  start_date: string | null;
  end_date: string | null;
  variants: ExperimentVariant[];
  results: {
    winner: string | null;
    lift_pct: number | null;
    p_value: number | null;
    confidence: number | null;
    is_significant: boolean;
    power: number | null;
  } | null;
}

export interface ExperimentsSummary {
  total: number;
  running: number;
  completed: number;
  win_rate: number;
  avg_lift: number;
}

export function useExperiments(status?: string): Async<{ experiments: Experiment[]; count: number }> {
  const qs = status ? `?status=${status}` : "";
  return useQuery(["experiments", status ?? "all"], () =>
    apiFetch<{ experiments: Experiment[]; count: number }>(`/api/experiments${qs}`),
  );
}

export function useExperimentsSummary(): Async<ExperimentsSummary> {
  return useQuery(["experiments-summary"], () =>
    apiFetch<ExperimentsSummary>("/api/experiments/summary"),
  );
}
