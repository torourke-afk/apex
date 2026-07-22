/**
 * Re-export types from hooks for surfaces that import from api/types.
 */
export type {
  KPIItem,
  FinancialSummary,
  AlertItem,
  BudgetOverview,
  ChannelSpendBreakdown,
  DMASpend,
  FunnelStage,
  ApprovalItem,
  PipelineItem,
  TestingVelocity,
  SurvivalCurve,
  BenchmarkData,
  SimulateInput,
  SimulateResult,
  SimPreset,
  Mutation,
  CalendarEvent,
  OpsCalendarData,
  CapacityItem,
  OpsCapacityData,
  CompetitiveFeedItem,
  CompetitiveFeedData,
} from "./hooks";

export type { Filters } from "../shell/ShellProvider";

/* ------------------------------------------------------------------ */
/*  Connector & Sync types                                             */
/* ------------------------------------------------------------------ */

export interface ConnectorStatus {
  id: string;
  type: string;
  display_name: string;
  enabled: boolean;
  is_fallback: boolean;
  domains: string[];
  status: "connected" | "degraded" | "disconnected" | "error";
  last_sync: string | null;
  last_error: string | null;
  rows_synced: number;
  latency_ms: number | null;
  refresh_interval_minutes: number;
}

export interface SyncLogEntry {
  id: string;
  connector_id: string;
  domain: string;
  endpoint: string;
  started_at: string;
  finished_at: string | null;
  status: "running" | "success" | "error";
  rows_synced: number;
  error: string | null;
  duration_ms: number;
}

export interface SyncStatus {
  is_running: boolean;
  last_full_sync: string | null;
  connectors: ConnectorStatus[];
  stats: {
    total_syncs: number;
    recent_errors: number;
    total_rows_synced: number;
  };
}
