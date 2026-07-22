/**
 * Smoke tests for all 13 surfaces.
 *
 * Each test renders the surface inside ShellProvider, mocking fetch
 * so BFF calls resolve with empty payloads. The goal is to verify
 * that every surface mounts without throwing — a fast regression guard.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { render, screen } from "./test-utils";

import { Scorecard } from "../surfaces/Scorecard";
import { Spend } from "../surfaces/Spend";
import { Media } from "../surfaces/Media";
import { Creative } from "../surfaces/Creative";
import { Audience } from "../surfaces/Audience";
import { BrandAwareness } from "../surfaces/BrandAwareness";
import { Product } from "../surfaces/Product";
import { Funnel } from "../surfaces/Funnel";
import { Retention } from "../surfaces/Retention";
import { Operations } from "../surfaces/Operations";
import { Simulator } from "../surfaces/Simulator";
import { Modeling } from "../surfaces/Modeling";
import { SettingsView } from "../surfaces/SettingsView";

/* ------------------------------------------------------------------ */
/*  Mock fetch → returns empty JSON for any BFF call                   */
/* ------------------------------------------------------------------ */

const emptyResponse = () =>
  Promise.resolve(
    new Response(JSON.stringify({}), {
      status: 200,
      headers: { "Content-Type": "application/json" },
    }),
  );

let fetchSpy: ReturnType<typeof vi.spyOn>;

beforeEach(() => {
  fetchSpy = vi.spyOn(globalThis, "fetch").mockImplementation(emptyResponse);
});

afterEach(() => {
  fetchSpy.mockRestore();
});

/* ------------------------------------------------------------------ */
/*  Surface smoke tests                                                */
/* ------------------------------------------------------------------ */

describe("Surface smoke tests", () => {
  const surfaces: [string, React.FC][] = [
    ["Scorecard", Scorecard],
    ["Spend", Spend],
    ["Media", Media],
    ["Creative", Creative],
    ["Audience", Audience],
    ["BrandAwareness", BrandAwareness],
    ["Product", Product],
    ["Funnel", Funnel],
    ["Retention", Retention],
    ["Operations", Operations],
    ["Simulator", Simulator],
    ["Modeling", Modeling],
    ["SettingsView", SettingsView],
  ];

  it.each(surfaces)("%s renders without crashing", (_name, Surface) => {
    expect(() => render(<Surface />)).not.toThrow();
  });
});

/* ------------------------------------------------------------------ */
/*  DataGuard shared components                                        */
/* ------------------------------------------------------------------ */

describe("Shared UI components", () => {
  it("Skeleton component renders with loading role", async () => {
    const { Skeleton } = await import("../ui/Skeleton");
    render(<Skeleton rows={3} />);
    expect(screen.getByRole("status")).toBeInTheDocument();
    expect(screen.getByText("Loading…")).toBeInTheDocument();
  });

  it("Empty component renders with headline", async () => {
    const { Empty } = await import("../ui/Empty");
    render(<Empty headline="No data available" />);
    expect(screen.getByText("No data available")).toBeInTheDocument();
  });

  it("ErrorRetry component renders with retry button", async () => {
    const { ErrorRetry } = await import("../ui/ErrorRetry");
    const onRetry = vi.fn();
    const { container } = render(<ErrorRetry message="Something went wrong" onRetry={onRetry} />);
    expect(container.textContent).toContain("Something went wrong");
    // Has a retry button
    const btn = container.querySelector("button");
    expect(btn).toBeTruthy();
  });
});
