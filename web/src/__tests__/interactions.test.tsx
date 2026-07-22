/**
 * Component interaction tests.
 *
 * Tests beyond smoke-level: user interactions like clicks, form changes,
 * keyboard events, state transitions, and error recovery.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "./test-utils";

/* ── Shared mock fetch ──────────────────────────────────────── */

let fetchSpy: ReturnType<typeof vi.spyOn>;

function mockJSON(data: unknown = {}) {
  return new Response(JSON.stringify(data), {
    status: 200,
    headers: { "Content-Type": "application/json" },
  });
}

const emptyResponse = () => Promise.resolve(mockJSON());

beforeEach(() => {
  fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(emptyResponse);
});

afterEach(() => {
  fetchSpy.mockRestore();
});

/* ══════════════════════════════════════════════════════════════
   1. FilterBar — dropdowns, selection, reset
   ══════════════════════════════════════════════════════════════ */

describe("FilterBar interactions", () => {
  let FilterBar: typeof import("../shell/FilterBar").FilterBar;

  beforeEach(async () => {
    ({ FilterBar } = await import("../shell/FilterBar"));
  });

  it("opens date range dropdown on click and selects an option", async () => {
    render(<FilterBar />);

    // The trigger button shows default date range
    const trigger = screen.getByLabelText("Date range");
    expect(trigger).toBeInTheDocument();
    expect(trigger.textContent).toContain("Last 12 weeks");

    // Open the dropdown
    fireEvent.click(trigger);

    // Listbox should appear with options
    const listbox = screen.getByRole("listbox", { name: "Date range options" });
    expect(listbox).toBeInTheDocument();

    // Select a different option
    const ytdOption = screen.getByRole("option", { name: /YTD/ });
    fireEvent.click(ytdOption);

    // Dropdown should close and trigger should update
    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
    expect(trigger.textContent).toContain("YTD");
  });

  it("opens multi-select dropdown and toggles options", async () => {
    render(<FilterBar />);

    // Open PRODUCT dropdown
    const productBtn = screen.getByLabelText("PRODUCT");
    fireEvent.click(productBtn);

    const productListbox = screen.getByRole("listbox", { name: "PRODUCT options" });
    expect(productListbox).toBeInTheDocument();
    expect(productListbox).toHaveAttribute("aria-multiselectable", "true");

    // Select "Checking"
    const checkingOpt = screen.getByRole("option", { name: /Checking/ });
    fireEvent.click(checkingOpt);
    expect(checkingOpt).toHaveAttribute("aria-selected", "true");

    // Select "CD"
    const cdOpt = screen.getByRole("option", { name: /^CD$/ });
    fireEvent.click(cdOpt);
    expect(cdOpt).toHaveAttribute("aria-selected", "true");

    // Button should show count badge
    // Close and check the trigger has the count
    fireEvent.click(productBtn);
    expect(productBtn.textContent).toContain("2");
  });

  it("closes dropdown on Escape key", async () => {
    render(<FilterBar />);

    const trigger = screen.getByLabelText("Date range");
    fireEvent.click(trigger);

    expect(screen.getByRole("listbox")).toBeInTheDocument();

    // Press Escape on the container
    fireEvent.keyDown(trigger.closest("div")!, { key: "Escape" });

    expect(screen.queryByRole("listbox")).not.toBeInTheDocument();
  });

  it("reset button clears filters back to defaults", async () => {
    render(<FilterBar />);

    // Change date range
    const trigger = screen.getByLabelText("Date range");
    fireEvent.click(trigger);
    fireEvent.click(screen.getByRole("option", { name: /YTD/ }));

    expect(trigger.textContent).toContain("YTD");

    // Click reset
    const resetBtn = screen.getByText(/RESET/);
    fireEvent.click(resetBtn);

    // Date range should revert to default
    expect(trigger.textContent).toContain("Last 12 weeks");
  });
});

/* ══════════════════════════════════════════════════════════════
   2. Simulator — sliders and buttons
   ══════════════════════════════════════════════════════════════ */

describe("Simulator interactions", () => {
  let Simulator: typeof import("../surfaces/Simulator").Simulator;

  beforeEach(async () => {
    ({ Simulator } = await import("../surfaces/Simulator"));
  });

  it("renders slider inputs for budget and channel mix", () => {
    render(<Simulator />);

    // Should have 4 range sliders: budget, brand, sem, social
    const sliders = screen.getAllByRole("slider");
    expect(sliders.length).toBeGreaterThanOrEqual(4);

    // Budget slider has default 39.4
    const budgetSlider = sliders[0];
    expect(budgetSlider).toHaveAttribute("min", "20");
    expect(budgetSlider).toHaveAttribute("max", "60");
  });

  it("shows RUN SIMULATION and RESET TO PLAN buttons", async () => {
    // Provide a realistic mock so the auto-simulation on mount succeeds
    fetchSpy.mockImplementation((input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/simulate/") && !url.includes("presets")) {
        return Promise.resolve(mockJSON({
          funded_accounts: 18000,
          blended_cpihh: 2189,
          blended_roas: 1.91,
          mob6_retained: 12852,
        }));
      }
      return Promise.resolve(mockJSON({ presets: [] }));
    });

    render(<Simulator />);

    // Simulator auto-fires a simulation on mount, so button may start as "RUNNING..."
    // Wait for it to settle back to "RUN SIMULATION"
    await waitFor(() => {
      expect(screen.getByText("RUN SIMULATION")).toBeInTheDocument();
    });
    expect(screen.getByText("RESET TO PLAN")).toBeInTheDocument();
  });

  it("RUN SIMULATION calls the BFF simulate endpoint", async () => {
    let simCallCount = 0;
    fetchSpy.mockImplementation((input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/simulate/") && !url.includes("presets")) {
        simCallCount++;
        return Promise.resolve(mockJSON({
          funded_accounts: 18000,
          blended_cpihh: 2189,
          blended_roas: 1.91,
          mob6_retained: 12852,
        }));
      }
      return Promise.resolve(mockJSON({ presets: [] }));
    });

    render(<Simulator />);

    // Wait for the auto-run on mount to complete
    await waitFor(() => {
      expect(screen.getByText("RUN SIMULATION")).toBeInTheDocument();
    });

    const countBefore = simCallCount;
    fireEvent.click(screen.getByText("RUN SIMULATION"));

    // Should have made an additional call
    await waitFor(() => {
      expect(simCallCount).toBeGreaterThan(countBefore);
    });
  });

  it("RESET TO PLAN restores default slider values", async () => {
    fetchSpy.mockImplementation((input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/simulate/") && !url.includes("presets"))
        return Promise.resolve(mockJSON({ funded_accounts: 18000, blended_cpihh: 2189, blended_roas: 1.91, mob6_retained: 12852 }));
      return Promise.resolve(mockJSON({ presets: [] }));
    });

    render(<Simulator />);

    await waitFor(() => {
      expect(screen.getByText("RUN SIMULATION")).toBeInTheDocument();
    });

    const sliders = screen.getAllByRole("slider");
    const budgetSlider = sliders[0];

    // Change budget
    fireEvent.change(budgetSlider, { target: { value: "50" } });
    expect(budgetSlider).toHaveValue("50");

    // Reset
    fireEvent.click(screen.getByText("RESET TO PLAN"));

    // Budget should revert to 39.4
    expect(budgetSlider).toHaveValue("39.4");
  });

  it("adjusting channel mix updates output cards", async () => {
    fetchSpy.mockImplementation((input) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      if (url.includes("/api/simulate/") && !url.includes("presets"))
        return Promise.resolve(mockJSON({ funded_accounts: 18000, blended_cpihh: 2189, blended_roas: 1.91, mob6_retained: 12852 }));
      return Promise.resolve(mockJSON({ presets: [] }));
    });

    render(<Simulator />);

    // Find the SEM slider (third slider)
    const sliders = screen.getAllByRole("slider");
    const semSlider = sliders[2]; // budget, brand, sem

    // Before change: should show the initial funded accounts number
    const fundedBefore = screen.getByText("FUNDED ACCOUNTS")
      ?.closest("[class*='flex-col']")
      ?.querySelector(".text-\\[28px\\]")?.textContent;

    // Increase SEM
    fireEvent.change(semSlider, { target: { value: "60" } });

    // After change: funded accounts should differ
    const fundedAfter = screen.getByText("FUNDED ACCOUNTS")
      ?.closest("[class*='flex-col']")
      ?.querySelector(".text-\\[28px\\]")?.textContent;

    // Values should be different since we changed the mix
    expect(fundedAfter).not.toBe(fundedBefore);
  });
});

/* ══════════════════════════════════════════════════════════════
   3. Operations — approval queue interactions
   ══════════════════════════════════════════════════════════════ */

describe("Operations interactions", () => {
  let Operations: typeof import("../surfaces/Operations").Operations;

  /* All 4 Operations hooks fire on mount — mock every endpoint group */
  const MOCK_CALENDAR = {
    events: [{ id: "e1", title: "Summer Push", event_type: "campaign_launch", date: "2025-07-15", channel: "sem", owner: "Marketing", status: "confirmed", description: "" }],
    total: 1,
    as_of: "2025-07-01",
  };
  const MOCK_CAPACITY = {
    members: [{ id: "c1", team: "SEM", channel: "sem", period: "Jul 2025", allocated_hours: 160, used_hours: 120, available_hours: 40, utilization_pct: 75, projects: [] }],
    summary: { total: 1, total_allocated_hours: 160, total_used_hours: 120, avg_utilization_pct: 75 },
    as_of: "2025-07-01",
  };
  const MOCK_COMPETITIVE = {
    items: [{ id: "ci1", competitor: "PNC", category: "digital", headline: "PNC launches new app", summary: "Redesigned mobile banking", source: "Press release", detected_at: "2025-07-01", impact: "medium", tags: ["mobile"] }],
    total: 1,
    as_of: "2025-07-01",
  };

  function mockOpsApprovals(approvals: unknown[], extraRoutes?: (url: string, method: string) => Response | null) {
    fetchSpy.mockImplementation((input, init) => {
      const url = typeof input === "string" ? input : (input as Request).url;
      const method = init?.method ?? "GET";

      // Extra routes (approve / reject POST handlers)
      if (extraRoutes) {
        const r = extraRoutes(url, method);
        if (r) return Promise.resolve(r);
      }

      if (url.includes("/api/ops/approvals") && !url.includes("/approve") && !url.includes("/reject")) {
        return Promise.resolve(mockJSON({ items: approvals, count: approvals.length }));
      }
      if (url.includes("/api/ops/calendar"))
        return Promise.resolve(mockJSON(MOCK_CALENDAR));
      if (url.includes("/api/ops/capacity"))
        return Promise.resolve(mockJSON(MOCK_CAPACITY));
      if (url.includes("/api/ops/competitive-feed"))
        return Promise.resolve(mockJSON(MOCK_COMPETITIVE));
      return Promise.resolve(mockJSON({}));
    });
  }

  const makeApproval = (id: string, title: string, priority = "HIGH", status = "PENDING") => ({
    id,
    title,
    approval_type: "spend_optimizer",
    priority,
    owner: "Kamino",
    due_date: null,
    status,
    notes: null,
    created_at: "2025-07-01",
    updated_at: "2025-07-01",
  });

  beforeEach(async () => {
    ({ Operations } = await import("../surfaces/Operations"));
  });

  it("renders approval queue with pending items", async () => {
    mockOpsApprovals([
      makeApproval("d1", "Reallocate $120K"),
      makeApproval("d2", "Pause creative"),
    ]);

    render(<Operations />);

    // Title appears in queue row and detail panel — use getAllByText
    await waitFor(() => {
      expect(screen.getAllByText("Reallocate $120K").length).toBeGreaterThanOrEqual(1);
    });
    expect(screen.getAllByText("Pause creative").length).toBeGreaterThanOrEqual(1);
  });

  it("APPROVE button calls the BFF approve endpoint", async () => {
    mockOpsApprovals(
      [makeApproval("d1", "Reallocate budget")],
      (url, method) => {
        if (url.includes("/api/ops/approvals/d1/approve") && method === "POST")
          return mockJSON({ success: true, message: "Approved" });
        return null;
      },
    );

    render(<Operations />);

    await waitFor(() => {
      expect(screen.getAllByText("Reallocate budget").length).toBeGreaterThanOrEqual(1);
    });

    fireEvent.click(screen.getByText("APPROVE & EXECUTE"));

    await waitFor(() => {
      const postCalls = fetchSpy.mock.calls.filter(
        ([url, init]) =>
          typeof url === "string" &&
          url.includes("/approve") &&
          init?.method === "POST",
      );
      expect(postCalls.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("REJECT button calls the BFF reject endpoint", async () => {
    mockOpsApprovals(
      [makeApproval("d1", "Pause creative", "HIGH", "PENDING")],
      (url, method) => {
        if (url.includes("/api/ops/approvals/d1/reject") && method === "POST")
          return mockJSON({ success: true, message: "Rejected" });
        return null;
      },
    );

    render(<Operations />);

    await waitFor(() => {
      expect(screen.getAllByText("Pause creative").length).toBeGreaterThanOrEqual(1);
    });

    fireEvent.click(screen.getByText("REJECT"));

    await waitFor(() => {
      const postCalls = fetchSpy.mock.calls.filter(
        ([url, init]) =>
          typeof url === "string" &&
          url.includes("/reject") &&
          init?.method === "POST",
      );
      expect(postCalls.length).toBeGreaterThanOrEqual(1);
    });
  });

  it("DEFER button hides the item from queue", async () => {
    mockOpsApprovals([
      makeApproval("d1", "Item One"),
      makeApproval("d2", "Item Two", "MEDIUM"),
    ]);

    render(<Operations />);

    await waitFor(() => {
      expect(screen.getAllByText("Item One").length).toBeGreaterThanOrEqual(1);
    });
    expect(screen.getAllByText("Item Two").length).toBeGreaterThanOrEqual(1);

    fireEvent.click(screen.getByText("DEFER"));

    // Item One should be gone from the queue (may still be in detail briefly)
    await waitFor(() => {
      expect(screen.queryAllByText("Item One").length).toBe(0);
    });
    expect(screen.getAllByText("Item Two").length).toBeGreaterThanOrEqual(1);
  });
});

/* ══════════════════════════════════════════════════════════════
   4. ErrorBoundary — error catching and recovery
   ══════════════════════════════════════════════════════════════ */

describe("ErrorBoundary", () => {
  let ErrorBoundary: typeof import("../ui/ErrorBoundary").ErrorBoundary;

  beforeEach(async () => {
    ({ ErrorBoundary } = await import("../ui/ErrorBoundary"));
  });

  // Suppress console.error for intentional throws
  const originalError = console.error;
  beforeEach(() => { console.error = vi.fn(); });
  afterEach(() => { console.error = originalError; });

  function ThrowingChild({ shouldThrow = true }: { shouldThrow?: boolean }) {
    if (shouldThrow) throw new Error("Test render error");
    return <div>All good</div>;
  }

  it("renders children when no error", () => {
    render(
      <ErrorBoundary>
        <div>Child content</div>
      </ErrorBoundary>,
    );

    expect(screen.getByText("Child content")).toBeInTheDocument();
  });

  it("renders error fallback when child throws", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    );

    // Should show the error alert
    const alert = screen.getByRole("alert");
    expect(alert).toBeInTheDocument();
    expect(alert.textContent).toContain("Test render error");
    expect(alert.textContent).toContain("RENDER ERROR");
  });

  it("shows RETRY button in error state", () => {
    render(
      <ErrorBoundary>
        <ThrowingChild />
      </ErrorBoundary>,
    );

    const retryBtn = screen.getByText("RETRY");
    expect(retryBtn).toBeInTheDocument();
    expect(retryBtn.tagName).toBe("BUTTON");
  });

  it("renders custom fallback when provided", () => {
    render(
      <ErrorBoundary fallback={<div>Custom fallback</div>}>
        <ThrowingChild />
      </ErrorBoundary>,
    );

    expect(screen.getByText("Custom fallback")).toBeInTheDocument();
    expect(screen.queryByRole("alert")).not.toBeInTheDocument();
  });
});

/* ══════════════════════════════════════════════════════════════
   5. DataGuard — state rendering
   ══════════════════════════════════════════════════════════════ */

describe("DataGuard state transitions", () => {
  let DataGuard: typeof import("../ui/DataGuard").DataGuard;

  beforeEach(async () => {
    ({ DataGuard } = await import("../ui/DataGuard"));
  });

  it("renders skeleton when loading and data is null", () => {
    render(
      <DataGuard data={null} loading={true} error={null}>
        {(d) => <div>Data: {String(d)}</div>}
      </DataGuard>,
    );

    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.queryByText(/^Data:/)).not.toBeInTheDocument();
  });

  it("renders children with data when loaded", () => {
    render(
      <DataGuard data={{ count: 42 }} loading={false} error={null}>
        {(d) => <div>Count: {d.count}</div>}
      </DataGuard>,
    );

    expect(screen.getByText("Count: 42")).toBeInTheDocument();
  });

  it("renders error with retry button when error", () => {
    const reload = vi.fn();
    render(
      <DataGuard data={null} loading={false} error="BFF timeout" reload={reload}>
        {(d) => <div>Data: {String(d)}</div>}
      </DataGuard>,
    );

    expect(screen.getByText(/BFF timeout/)).toBeInTheDocument();
    const retryBtn = screen.getByText(/RETRY/i);
    fireEvent.click(retryBtn);
    expect(reload).toHaveBeenCalledTimes(1);
  });

  it("renders empty state for empty arrays", () => {
    render(
      <DataGuard
        data={[]}
        loading={false}
        error={null}
        emptyHeadline="Nothing here"
        emptyBody="Try adjusting your filters."
      >
        {(d) => <div>Items: {(d as unknown[]).length}</div>}
      </DataGuard>,
    );

    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByText("Try adjusting your filters.")).toBeInTheDocument();
    expect(screen.queryByText(/^Items:/)).not.toBeInTheDocument();
  });

  it("renders empty state when data is null and not loading", () => {
    render(
      <DataGuard data={null} loading={false} error={null} emptyHeadline="No data">
        {(d) => <div>Data: {String(d)}</div>}
      </DataGuard>,
    );

    expect(screen.getByText("No data")).toBeInTheDocument();
  });

  it("renders custom skeleton when provided", () => {
    render(
      <DataGuard data={null} loading={true} error={null} skeleton={<div data-testid="custom-skel">Loading custom...</div>}>
        {(d) => <div>Data: {String(d)}</div>}
      </DataGuard>,
    );

    expect(screen.getByTestId("custom-skel")).toBeInTheDocument();
  });
});

/* ══════════════════════════════════════════════════════════════
   6. ShellProvider — context and state
   ══════════════════════════════════════════════════════════════ */

describe("ShellProvider state management", () => {
  it("provides default filter values", async () => {
    const { useShell } = await import("../shell/ShellProvider");

    function Inspector() {
      const { filters, filtersActive } = useShell();
      return (
        <div>
          <span data-testid="dr">{filters.dateRange}</span>
          <span data-testid="active">{String(filtersActive)}</span>
        </div>
      );
    }

    // Use our custom render which wraps in ShellProvider
    render(<Inspector />);

    expect(screen.getByTestId("dr").textContent).toBe("Last 12 weeks");
    expect(screen.getByTestId("active").textContent).toBe("false");
  });

  it("filtersActive becomes true when filters deviate from defaults", async () => {
    const { useShell } = await import("../shell/ShellProvider");

    function FilterChanger() {
      const { filters, filtersActive, setFilters } = useShell();
      return (
        <div>
          <span data-testid="active">{String(filtersActive)}</span>
          <span data-testid="dr">{filters.dateRange}</span>
          <button onClick={() => setFilters({ dateRange: "YTD" })}>
            Change
          </button>
        </div>
      );
    }

    render(<FilterChanger />);

    expect(screen.getByTestId("active").textContent).toBe("false");

    fireEvent.click(screen.getByText("Change"));

    expect(screen.getByTestId("active").textContent).toBe("true");
    expect(screen.getByTestId("dr").textContent).toBe("YTD");
  });
});
