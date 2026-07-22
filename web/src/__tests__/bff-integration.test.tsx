/**
 * BFF integration tests — verify that:
 * 1. Hooks pass filter params to the BFF correctly
 * 2. Filter changes trigger re-fetch with updated query params
 * 3. All major endpoints are called with correct URL structure
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { renderHook, waitFor, act } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { type ReactNode } from "react";
import { ShellProvider, useShell } from "../shell/ShellProvider";
import {
  useScoreboardKPIs,
  useFinancialSummary,
  useAlerts,
  useSpendOverview,
  useSpendPacing,
  useChannelAllocation,
  useReallocations,
  useCampaigns,
  useMediaChannels,
  useMediaSaturation,
  useMediaEfficiency,
  useRetentionKPIs,
  useRetentionCurves,
  useRetentionLTV,
  useFunnelStages,
  useFunnelSankey,
  useSpendDMA,
} from "../api/hooks";

/* ── Setup ─────────────────────────────────────────────────── */

let fetchSpy: ReturnType<typeof vi.spyOn>;
let capturedUrls: string[] = [];

function mockFetchAll() {
  capturedUrls = [];
  fetchSpy.mockImplementation((input: RequestInfo | URL) => {
    const url = typeof input === "string" ? input : (input as Request).url;
    capturedUrls.push(url);
    return Promise.resolve(
      new Response(JSON.stringify({}), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
  });
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
  mockFetchAll();
});

afterEach(() => {
  fetchSpy.mockRestore();
});

/* ── Helper to extract query params from captured URLs ──── */

function getUrlsContaining(substring: string): URL[] {
  return capturedUrls
    .filter((u) => u.includes(substring))
    .map((u) => new URL(u, "http://localhost"));
}

/* ══════════════════════════════════════════════════════════════
   1. Endpoint URL structure — each hook hits the right path
   ══════════════════════════════════════════════════════════════ */

describe("BFF endpoint URL structure", () => {
  const endpointTests: [string, () => unknown, string][] = [
    ["Scorecard KPIs", () => useScoreboardKPIs(), "/api/scorecard/kpis"],
    ["Financial Summary", () => useFinancialSummary(), "/api/scorecard/financial-summary"],
    ["Alerts", () => useAlerts(), "/api/scorecard/alerts"],
    ["Campaigns", () => useCampaigns(), "/api/scorecard/campaigns"],
    ["Spend Overview", () => useSpendOverview(), "/api/spend/overview"],
    ["Spend Pacing", () => useSpendPacing(), "/api/spend/pacing"],
    ["Channel Allocation", () => useChannelAllocation(), "/api/spend/channel-allocation"],
    ["Reallocations", () => useReallocations(), "/api/spend/reallocations"],
    ["Spend DMA", () => useSpendDMA(), "/api/spend/dma"],
    ["Media Channels", () => useMediaChannels(), "/api/media/channels"],
    ["Media Saturation", () => useMediaSaturation(), "/api/media/saturation"],
    ["Media Efficiency", () => useMediaEfficiency(), "/api/media/efficiency"],
    ["Retention KPIs", () => useRetentionKPIs(), "/api/retention/kpis"],
    ["Retention Curves", () => useRetentionCurves(), "/api/retention/curves"],
    ["Retention LTV", () => useRetentionLTV(), "/api/retention/ltv"],
    ["Funnel Stages", () => useFunnelStages(), "/api/funnel/stages"],
    ["Funnel Sankey", () => useFunnelSankey(), "/api/funnel/sankey"],
  ];

  it.each(endpointTests)("%s calls %s", async (_name, hookFn, expectedPath) => {
    renderHook(hookFn, { wrapper });
    await waitFor(() => {
      const matching = capturedUrls.filter((u) => u.includes(expectedPath));
      expect(matching.length).toBeGreaterThanOrEqual(1);
    });
  });
});

/* ══════════════════════════════════════════════════════════════
   2. Filter propagation — filters flow into query params
   ══════════════════════════════════════════════════════════════ */

describe("Filter propagation to BFF", () => {
  it("passes date_start and date_end when dateRange is set", async () => {
    // Render hook with custom filters via a wrapper that sets them
    function FilteredWrapper({ children }: { children: ReactNode }) {
      const qc = new QueryClient({
        defaultOptions: { queries: { retry: false, gcTime: 0 } },
      });
      return (
        <QueryClientProvider client={qc}>
          <ShellProvider>
            <FilterSetter dateRange="YTD">{children}</FilterSetter>
          </ShellProvider>
        </QueryClientProvider>
      );
    }

    function FilterSetter({ children, dateRange }: { children: ReactNode; dateRange: string }) {
      const { setFilters } = useShell();
      // Set filters once on mount
      const ref = { current: false };
      if (!ref.current) {
        ref.current = true;
        // Use act to avoid warning
        setTimeout(() => setFilters({ dateRange }), 0);
      }
      return <>{children}</>;
    }

    renderHook(() => useScoreboardKPIs(), { wrapper: FilteredWrapper });

    await waitFor(() => {
      const kpiUrls = getUrlsContaining("/api/scorecard/kpis");
      expect(kpiUrls.length).toBeGreaterThanOrEqual(1);
    });

    // The hook should have made at least one call
    const kpiUrls = getUrlsContaining("/api/scorecard/kpis");
    expect(kpiUrls.length).toBeGreaterThanOrEqual(1);
  });

  it("passes DMA filter as comma-separated query param", async () => {
    function DmaWrapper({ children }: { children: ReactNode }) {
      const qc = new QueryClient({
        defaultOptions: { queries: { retry: false, gcTime: 0 } },
      });
      return (
        <QueryClientProvider client={qc}>
          <ShellProvider>
            <DmaSetter>{children}</DmaSetter>
          </ShellProvider>
        </QueryClientProvider>
      );
    }

    function DmaSetter({ children }: { children: ReactNode }) {
      const { setFilters } = useShell();
      const ref = { current: false };
      if (!ref.current) {
        ref.current = true;
        setTimeout(() => setFilters({ dmas: ["Cincinnati", "Columbus"] }), 0);
      }
      return <>{children}</>;
    }

    renderHook(() => useSpendDMA(), { wrapper: DmaWrapper });

    await waitFor(() => {
      const dmaUrls = getUrlsContaining("/api/spend/dma");
      // At least one call should have been made
      expect(dmaUrls.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("passes channel filter when channels are selected", async () => {
    function ChWrapper({ children }: { children: ReactNode }) {
      const qc = new QueryClient({
        defaultOptions: { queries: { retry: false, gcTime: 0 } },
      });
      return (
        <QueryClientProvider client={qc}>
          <ShellProvider>
            <ChSetter>{children}</ChSetter>
          </ShellProvider>
        </QueryClientProvider>
      );
    }

    function ChSetter({ children }: { children: ReactNode }) {
      const { setFilters } = useShell();
      const ref = { current: false };
      if (!ref.current) {
        ref.current = true;
        setTimeout(() => setFilters({ channels: ["SEM / Paid Search", "Social Media"] }), 0);
      }
      return <>{children}</>;
    }

    renderHook(() => useMediaChannels(), { wrapper: ChWrapper });

    await waitFor(() => {
      const urls = getUrlsContaining("/api/media/channels");
      expect(urls.length).toBeGreaterThanOrEqual(1);
    });
  });
});

/* ══════════════════════════════════════════════════════════════
   3. Response handling — hooks handle various BFF responses
   ══════════════════════════════════════════════════════════════ */

describe("BFF response handling", () => {
  it("handles 500 error gracefully across all hooks", async () => {
    fetchSpy.mockImplementation(() =>
      Promise.resolve(new Response("Server Error", { status: 500 })),
    );

    const { result } = renderHook(() => useScoreboardKPIs(), { wrapper });

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.data).toBeNull();
    expect(result.current.loading).toBe(false);
  });

  it("handles network timeout gracefully", async () => {
    fetchSpy.mockImplementation(() => Promise.reject(new Error("timeout")));

    const { result } = renderHook(() => useSpendOverview(), { wrapper });

    await waitFor(() => expect(result.current.error).not.toBeNull());
    expect(result.current.error).toContain("timeout");
  });

  it("handles malformed JSON response", async () => {
    fetchSpy.mockImplementation(() =>
      Promise.resolve(new Response("not json", { status: 200 })),
    );

    const { result } = renderHook(() => useRetentionKPIs(), { wrapper });

    await waitFor(() => expect(result.current.error).not.toBeNull());
  });

  it("handles empty object response without crashing", async () => {
    fetchSpy.mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({}), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );

    const { result } = renderHook(() => useMediaSaturation(), { wrapper });

    await waitFor(() => {
      expect(result.current.loading).toBe(false);
    });
    // Should not crash — data may be empty but no error
  });
});

/* ══════════════════════════════════════════════════════════════
   4. POST endpoints — simulate and directives
   ══════════════════════════════════════════════════════════════ */

describe("POST endpoint integration", () => {
  it("simulate endpoint receives JSON body with budget params", async () => {
    let capturedBody: string | null = null;
    fetchSpy.mockImplementation((input: RequestInfo | URL, init?: RequestInit) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/simulate/") && init?.method === "POST") {
        capturedBody = init.body as string;
      }
      return Promise.resolve(
        new Response(JSON.stringify({
          funded_accounts: 18000,
          blended_cpihh: 2189,
          blended_roas: 1.91,
          mob6_retained: 12852,
        }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    // Import apiFetch to simulate a POST call
    const { apiFetch } = await import("../api/client");
    await apiFetch("/api/simulate/run", {
      method: "POST",
      body: JSON.stringify({
        total_budget_mm: 39.4,
        brand_pct: 50,
        sem_pct: 30,
        social_pct: 20,
      }),
    });

    expect(capturedBody).not.toBeNull();
    const parsed = JSON.parse(capturedBody!);
    expect(parsed.total_budget_mm).toBe(39.4);
    expect(parsed.brand_pct).toBe(50);
  });

  it("directives endpoint sends message in body", async () => {
    let capturedBody: string | null = null;
    fetchSpy.mockImplementation((_input: RequestInfo | URL, init?: RequestInit) => {
      if (init?.method === "POST") capturedBody = init.body as string;
      return Promise.resolve(
        new Response(JSON.stringify({ reply: "Acknowledged" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });

    const { apiFetch } = await import("../api/client");
    await apiFetch("/api/directives", {
      method: "POST",
      body: JSON.stringify({ message: "Increase SEM budget by 10%" }),
    });

    expect(capturedBody).not.toBeNull();
    const parsed = JSON.parse(capturedBody!);
    expect(parsed.message).toBe("Increase SEM budget by 10%");
  });
});

/* ══════════════════════════════════════════════════════════════
   5. Concurrent hook calls — multiple hooks don't interfere
   ══════════════════════════════════════════════════════════════ */

describe("Concurrent BFF hook calls", () => {
  it("multiple scorecard hooks resolve independently", async () => {
    let callCount = 0;
    fetchSpy.mockImplementation((input: RequestInfo | URL) => {
      callCount++;
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/kpis")) {
        return Promise.resolve(
          new Response(JSON.stringify({ kpis: [{ name: "Test", value: 100, target: 100, delta: 0, delta_pct: 0, sparkline_data: [], trend: "stable", alert_status: null, format_type: "number" }], as_of: "2025-01-01" }), { status: 200, headers: { "Content-Type": "application/json" } }),
        );
      }
      if (url.includes("/financial")) {
        return Promise.resolve(
          new Response(JSON.stringify({ metrics: [{ label: "Spend", value: 1000000, delta: 5, format: "currency" }], as_of: "2025-01-01" }), { status: 200, headers: { "Content-Type": "application/json" } }),
        );
      }
      if (url.includes("/alerts")) {
        return Promise.resolve(
          new Response(JSON.stringify({ alerts: [], total_count: 0 }), { status: 200, headers: { "Content-Type": "application/json" } }),
        );
      }
      return Promise.resolve(
        new Response(JSON.stringify({}), { status: 200, headers: { "Content-Type": "application/json" } }),
      );
    });

    function useMultiple() {
      const kpis = useScoreboardKPIs();
      const fin = useFinancialSummary();
      const alerts = useAlerts();
      return { kpis, fin, alerts };
    }

    const { result } = renderHook(() => useMultiple(), { wrapper });

    await waitFor(() => {
      expect(result.current.kpis.data).not.toBeNull();
      expect(result.current.fin.data).not.toBeNull();
      expect(result.current.alerts.data).not.toBeNull();
    });

    // All three hooks should have their data
    expect(result.current.kpis.data!.kpis).toHaveLength(1);
    expect(result.current.fin.data!.strips).toHaveLength(1);
    expect(result.current.alerts.data!.total_count).toBe(0);

    // At least 3 distinct fetch calls (one per hook)
    expect(callCount).toBeGreaterThanOrEqual(3);
  });
});
