/**
 * Smoke tests for UI primitive components.
 *
 * These verify that each component renders without crashing
 * and exposes the expected accessible semantics.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "../../__tests__/test-utils";
import { Card } from "../Card";
import { SectionHeader } from "../SectionHeader";
import { Pill } from "../Pill";
import { Segmented } from "../Segmented";
import { MiniRing } from "../MiniRing";
import { Sparkline } from "../Sparkline";
import { Skeleton, SkeletonCard, SkeletonTable } from "../Skeleton";
import { Empty } from "../Empty";
import { ErrorRetry } from "../ErrorRetry";
import { DataGuard } from "../DataGuard";

/* ── Card ────────────────────────────────────────────────────── */

describe("Card", () => {
  it("renders children", () => {
    render(<Card>Hello</Card>);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });
});

/* ── SectionHeader ───────────────────────────────────────────── */

describe("SectionHeader", () => {
  it("renders title text", () => {
    render(<SectionHeader title="Revenue" />);
    expect(screen.getByText("Revenue")).toBeInTheDocument();
  });
});

/* ── Pill ────────────────────────────────────────────────────── */

describe("Pill", () => {
  it("renders children", () => {
    render(<Pill>Active</Pill>);
    expect(screen.getByText("Active")).toBeInTheDocument();
  });
});

/* ── Segmented ───────────────────────────────────────────────── */

describe("Segmented", () => {
  it("renders options as radio buttons", () => {
    render(
      <Segmented
        options={["Day", "Week", "Month"]}
        value="Week"
        onChange={() => {}}
      />,
    );
    const radios = screen.getAllByRole("radio");
    expect(radios).toHaveLength(3);
    // Active option should be checked
    const weekBtn = screen.getByRole("radio", { name: "WEEK" });
    expect(weekBtn).toHaveAttribute("aria-checked", "true");
  });

  it("has radiogroup role on container", () => {
    render(
      <Segmented options={["A", "B"]} value="A" onChange={() => {}} />,
    );
    expect(screen.getByRole("radiogroup")).toBeInTheDocument();
  });
});

/* ── MiniRing ────────────────────────────────────────────────── */

describe("MiniRing", () => {
  it("exposes percentage via aria-label", () => {
    render(<MiniRing pct={75} color="var(--cyan)" />);
    const img = screen.getByRole("img");
    expect(img).toHaveAttribute("aria-label", "75%");
  });
});

/* ── Sparkline ───────────────────────────────────────────────── */

describe("Sparkline", () => {
  it("renders without crashing", () => {
    const { container } = render(
      <Sparkline data={[10, 20, 15, 30]} color="var(--cyan)" />,
    );
    const svg = container.querySelector("svg");
    expect(svg).toBeInTheDocument();
    // Decorative — should be hidden from AT
    expect(svg).toHaveAttribute("aria-hidden", "true");
  });
});

/* ── Skeleton ────────────────────────────────────────────────── */

describe("Skeleton", () => {
  it("renders with loading status", () => {
    render(<Skeleton rows={3} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });
});

describe("SkeletonCard", () => {
  it("renders with loading status", () => {
    render(<SkeletonCard />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});

describe("SkeletonTable", () => {
  it("renders with loading status", () => {
    render(<SkeletonTable cols={3} rows={2} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
  });
});

/* ── Empty ────────────────────────────────────────────────────── */

describe("Empty", () => {
  it("renders default headline", () => {
    render(<Empty />);
    expect(screen.getByText("No data")).toBeInTheDocument();
  });

  it("renders custom headline and body", () => {
    render(<Empty headline="Nothing here" body="Try a different filter" />);
    expect(screen.getByText("Nothing here")).toBeInTheDocument();
    expect(screen.getByText("Try a different filter")).toBeInTheDocument();
  });
});

/* ── ErrorRetry ──────────────────────────────────────────────── */

describe("ErrorRetry", () => {
  it("renders error message with alert role", () => {
    render(<ErrorRetry message="Something broke" />);
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Something broke")).toBeInTheDocument();
  });

  it("renders retry button when onRetry is provided", () => {
    render(<ErrorRetry message="Oops" onRetry={() => {}} />);
    expect(screen.getByText(/RETRY/)).toBeInTheDocument();
  });

  it("hides retry button when onRetry is omitted", () => {
    render(<ErrorRetry message="Oops" />);
    expect(screen.queryByText(/RETRY/)).not.toBeInTheDocument();
  });
});

/* ── DataGuard ───────────────────────────────────────────────── */

describe("DataGuard", () => {
  it("shows skeleton while loading", () => {
    render(
      <DataGuard data={null} loading={true} error={null}>
        {(d) => <span>{d}</span>}
      </DataGuard>,
    );
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows error with retry on error", () => {
    render(
      <DataGuard data={null} loading={false} error="Network fail" reload={() => {}}>
        {(d) => <span>{d}</span>}
      </DataGuard>,
    );
    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Network fail")).toBeInTheDocument();
    expect(screen.getByText(/RETRY/)).toBeInTheDocument();
  });

  it("shows empty state when data is null", () => {
    render(
      <DataGuard data={null} loading={false} error={null}>
        {(d) => <span>{d}</span>}
      </DataGuard>,
    );
    expect(screen.getByText("No data")).toBeInTheDocument();
  });

  it("shows empty for empty arrays", () => {
    render(
      <DataGuard data={[]} loading={false} error={null}>
        {(d) => <span>{d.length}</span>}
      </DataGuard>,
    );
    expect(screen.getByText("No results")).toBeInTheDocument();
  });

  it("renders children when data is present", () => {
    render(
      <DataGuard data={{ value: 42 }} loading={false} error={null}>
        {(d) => <span>Answer: {d.value}</span>}
      </DataGuard>,
    );
    expect(screen.getByText("Answer: 42")).toBeInTheDocument();
  });
});
