/**
 * BFF hook tests — verify each hook correctly transforms BFF responses.
 *
 * Uses vi.spyOn(fetch) to simulate BFF responses and renderHook
 * to exercise the React Query + adapter logic in isolation.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";
import { ShellProvider } from "../shell/ShellProvider";
import {
  useScoreboardKPIs,
  useFinancialSummary,
  useAlerts,
  useSpendOverview,
  useSpendPacing,
  useChannelAllocation,
  useReallocations,
  useCampaigns,
  useShareOfSearch,
  usePeerComparison,
  useMediaChannels,
  useRetentionKPIs,
  useFunnelStages,
} from "../api/hooks";

/* ── Setup ─────────────────────────────────────────────────── */

let fetchSpy: ReturnType<typeof vi.spyOn>;

function mockFetch(data: unknown) {
  fetchSpy.mockResolvedValueOnce(
    new Response(JSON.stringify(data), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );
}

function wrapper({ children }: { children: ReactNode }) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  return (
    <QueryClientProvider client={qc}>
      <ShellProvider>{children}</ShellProvider>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  fetchSpy = vi.spyOn(globalThis, "fetch");
});

afterEach(() => {
  fetchSpy.mockRestore();
});

/* ── Scorecard KPIs ───────────────────────────────────────── */

describe("useScoreboardKPIs", () => {
  it("transforms BFF KPI response into UI model", async () => {
    mockFetch({
      kpis: [
        {
          name: "Funded Accounts",
          value: 12500,
          target: 15000,
          delta: -2500,
          delta_pct: -16.7,
          sparkline_data: [10, 11, 12, 12.5],
          trend: "declining",
          alert_status: "warning",
          format_type: "number",
        },
      ],
      as_of: "2025-07-01T00:00:00",
    });

    const { result } = renderHook(() => useScoreboardKPIs(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    const kpi = result.current.data!.kpis[0];
    expect(kpi.label).toBe("Funded Accounts");
    expect(kpi.id).toBe("funded-accounts");
    expect(kpi.value).toBe("12,500");
    expect(kpi.delta).toBe("16.7%");
    expect(kpi.deltaDir).toBe("down");
    expect(kpi.spark).toEqual([10, 11, 12, 12.5]);
  });

  it("applies invert logic for cost KPIs", async () => {
    mockFetch({
      kpis: [
        {
          name: "Blended CPL",
          value: 80,
          target: 90,
          delta: -10,
          delta_pct: -11.1,
          sparkline_data: [95, 88, 82, 80],
          trend: "improving",
          alert_status: null,
          format_type: "currency",
        },
      ],
      as_of: "2025-07-01T00:00:00",
    });

    const { result } = renderHook(() => useScoreboardKPIs(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    const kpi = result.current.data!.kpis[0];
    expect(kpi.invertDelta).toBe(true);
    // CPL below target is good
    expect(kpi.targetMet).toBe(true);
    expect(kpi.value).toBe("$80");
  });
});

/* ── Financial Summary ────────────────────────────────────── */

describe("useFinancialSummary", () => {
  it("formats currency and percent metrics", async () => {
    mockFetch({
      metrics: [
        { label: "Total Spend MTD", value: 4820000, delta: 5.2, format: "currency" },
        { label: "QTD Pacing", value: 94.2, delta: -2.1, format: "percent" },
      ],
      as_of: "2025-07-01T00:00:00",
    });

    const { result } = renderHook(() => useFinancialSummary(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    const strips = result.current.data!.strips;
    expect(strips[0].label).toBe("TOTAL SPEND MTD");
    expect(strips[0].value).toBe("$4.8M");
    // Currency delta renders as "up $X" not percentage
    expect(strips[0].detail).toContain("up");
    expect(strips[1].value).toBe("94.2%");
  });
});

/* ── Alerts ───────────────────────────────────────────────── */

describe("useAlerts", () => {
  it("maps severity to tone", async () => {
    mockFetch({
      alerts: [
        { severity: "error", kpi_name: "CPA", description: "CPA exceeds target", created_at: "2025-07-01 09:00", module_link: null },
        { severity: "info", kpi_name: "Funded", description: "Funded on pace", created_at: "2025-07-01 08:00", module_link: null },
      ],
      total_count: 2,
    });

    const { result } = renderHook(() => useAlerts(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    expect(result.current.data!.alerts[0].tone).toBe("critical");
    expect(result.current.data!.alerts[1].tone).toBe("info");
    expect(result.current.data!.total_count).toBe(2);
  });
});

/* ── Spend Overview ───────────────────────────────────────── */

describe("useSpendOverview", () => {
  it("formats budget KPIs correctly", async () => {
    mockFetch({
      kpis: [
        { label: "Total Spend MTD", value: 4820000, delta: -3.6, format: "currency" },
        { label: "QTD Pacing", value: 94.2, delta: -2.1, format: "percent" },
      ],
    });

    const { result } = renderHook(() => useSpendOverview(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    expect(result.current.data!.cards[0].value).toBe("$4.8M");
    expect(result.current.data!.cards[1].value).toBe("94%");
  });
});

/* ── Channel Allocation ───────────────────────────────────── */

describe("useChannelAllocation", () => {
  it("returns channels with amount and pct", async () => {
    mockFetch({
      channels: [
        { name: "Brand Media", amount: 8100000, pct: 51 },
        { name: "Performance SEM", amount: 2200000, pct: 14 },
      ],
      total: 15900000,
    });

    const { result } = renderHook(() => useChannelAllocation(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    expect(result.current.data!.channels).toHaveLength(2);
    expect(result.current.data!.channels[0].name).toBe("Brand Media");
    expect(result.current.data!.channels[0].amount).toBe(8100000);
    expect(result.current.data!.total).toBe(15900000);
  });
});

/* ── Reallocations ────────────────────────────────────────── */

describe("useReallocations", () => {
  it("returns moves with all fields", async () => {
    mockFetch({
      moves: [
        {
          from_channel: "Social",
          to_channel: "SEM",
          rationale: "Lower CPA",
          delta: 120000,
          roas_impact: 0.4,
          status: "APPROVED",
        },
      ],
    });

    const { result } = renderHook(() => useReallocations(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    const move = result.current.data!.moves[0];
    expect(move.from_channel).toBe("Social");
    expect(move.to_channel).toBe("SEM");
    expect(move.status).toBe("APPROVED");
    expect(move.delta).toBe(120000);
  });
});

/* ── Campaigns ────────────────────────────────────────────── */

describe("useCampaigns", () => {
  it("returns campaign data with badge colors", async () => {
    mockFetch({
      campaigns: [
        { name: "CD - Brand", channel: "TV", spend: 3900000, roas: 170.5, funded: 1200, badge: "green" },
        { name: "General Banking", channel: "SEM", spend: 1300000, roas: 62.5, funded: 450, badge: "green" },
      ],
      count: 2,
    });

    const { result } = renderHook(() => useCampaigns(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    expect(result.current.data!.campaigns).toHaveLength(2);
    expect(result.current.data!.campaigns[0].name).toBe("CD - Brand");
    expect(result.current.data!.campaigns[0].badge).toBe("green");
    expect(result.current.data!.count).toBe(2);
  });
});

/* ── Share of Search (Brand Awareness BFF) ────────────────── */

describe("useShareOfSearch", () => {
  it("returns SoS time-series points", async () => {
    mockFetch({
      share_of_search: [
        { date: "2024-08-01", brand_msv: 169005, total_msv: 1695777, share_of_search: 0.0997, rank: 5 },
        { date: "2024-09-01", brand_msv: 154382, total_msv: 1809556, share_of_search: 0.0853, rank: 6 },
      ],
    });

    const { result } = renderHook(() => useShareOfSearch(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    const pts = result.current.data!.points;
    expect(pts).toHaveLength(2);
    expect(pts[0].share_of_search).toBe(0.0997);
    expect(pts[0].rank).toBe(5);
    expect(pts[1].date).toBe("2024-09-01");
  });

  it("handles empty response gracefully", async () => {
    mockFetch({ share_of_search: [] });

    const { result } = renderHook(() => useShareOfSearch(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    expect(result.current.data!.points).toHaveLength(0);
  });
});

/* ── Peer Comparison (Brand Awareness BFF) ────────────────── */

describe("usePeerComparison", () => {
  it("returns ranked peer list", async () => {
    mockFetch({
      peer_comparison: [
        { brand: "PNC Bank", keyword: "pnc bank", msv: 309194, share: 17.7, rank: 1, msv_delta: 3917, share_delta: 0.62 },
        { brand: "Fifth Third Bank", keyword: "fifth third bank", msv: 162809, share: 9.3, rank: 5, msv_delta: -19838, share_delta: -0.92 },
      ],
    });

    const { result } = renderHook(() => usePeerComparison(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    const peers = result.current.data!.peers;
    expect(peers).toHaveLength(2);
    expect(peers[0].brand).toBe("PNC Bank");
    expect(peers[0].rank).toBe(1);
    expect(peers[1].brand).toBe("Fifth Third Bank");
    expect(peers[1].share_delta).toBeCloseTo(-0.92);
  });

  it("handles missing peer_comparison key", async () => {
    mockFetch({});

    const { result } = renderHook(() => usePeerComparison(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    expect(result.current.data!.peers).toHaveLength(0);
  });
});

/* ── Media Channels ───────────────────────────────────────── */

describe("useMediaChannels", () => {
  it("returns channel performance data", async () => {
    mockFetch({
      channels: [
        { name: "SEM", color: "#34E1D4", spend: 5000000, cpihh: 280, cvr: 2.1, roas: 3.8, trend: [3.2, 3.5, 3.8] },
      ],
      count: 1,
      total_spend: 5000000,
    });

    const { result } = renderHook(() => useMediaChannels(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    expect(result.current.data!.channels[0].name).toBe("SEM");
    expect(result.current.data!.total_spend).toBe(5000000);
  });
});

/* ── Retention KPIs ───────────────────────────────────────── */

describe("useRetentionKPIs", () => {
  it("returns KPI cards", async () => {
    mockFetch({
      kpis: [
        { label: "MOB-6 Retention", value: "74%", value_suffix: null, delta: "+2.1%", color: "positive" },
      ],
    });

    const { result } = renderHook(() => useRetentionKPIs(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    expect(result.current.data!.kpis[0].label).toBe("MOB-6 Retention");
    expect(result.current.data!.kpis[0].value).toBe("74%");
  });
});

/* ── Funnel Stages ────────────────────────────────────────── */

describe("useFunnelStages", () => {
  it("computes drop-off and dollar impact", async () => {
    mockFetch({
      stages: ["Visits", "App Start", "Complete"],
      values: [100000, 8000, 5000],
      benchmarks: [0, 0, 0],
      rates: [1.0, 0.08, 0.625],
      bench_rates: [1.0, 0.1, 0.7],
      avg_account_ltv: 4000,
    });

    const { result } = renderHook(() => useFunnelStages(), { wrapper });
    await waitFor(() => expect(result.current.data).not.toBeNull());

    const stages = result.current.data!;
    expect(stages).toHaveLength(3);
    expect(stages[0].stage).toBe("Visits");
    expect(stages[0].volume).toBe(100000);
    // Drop-off from Visits to App Start = 100000 - 8000 = 92000
    expect(stages[0].drop_off).toBe(92000);
    // Dollar impact = 92000 * 4000 * 0.01 = 3680000
    expect(stages[0].dollar_impact).toBe(3680000);
  });
});

/* ── Error handling ───────────────────────────────────────── */

describe("Hook error handling", () => {
  it("surfaces fetch error in Async.error", async () => {
    fetchSpy.mockResolvedValueOnce(
      new Response("Internal Server Error", { status: 500 }),
    );

    const { result } = renderHook(() => useScoreboardKPIs(), { wrapper });
    await waitFor(() => expect(result.current.error).not.toBeNull());

    expect(result.current.error).toContain("500");
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("surfaces network error in Async.error", async () => {
    fetchSpy.mockRejectedValueOnce(new Error("Network failure"));

    const { result } = renderHook(() => useAlerts(), { wrapper });
    await waitFor(() => expect(result.current.error).not.toBeNull());

    expect(result.current.error).toContain("Network failure");
  });
});
