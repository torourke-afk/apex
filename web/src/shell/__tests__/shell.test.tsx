/**
 * Smoke tests for shell chrome components.
 *
 * Verifies that each shell component renders without crashing
 * and exposes the expected accessible landmarks and controls.
 */

import { describe, it, expect } from "vitest";
import { render, screen } from "../../__tests__/test-utils";
import { Rail } from "../Rail";
import { ContextBar } from "../ContextBar";
import { FilterBar } from "../FilterBar";
import { AgentConsole } from "../AgentConsole";

/* ── Rail ────────────────────────────────────────────────────── */

describe("Rail", () => {
  it("renders main navigation landmark", () => {
    render(<Rail />);
    expect(screen.getByRole("navigation")).toBeInTheDocument();
  });

  it("renders nav buttons with accessible names", () => {
    render(<Rail />);
    const nav = screen.getByRole("navigation");
    const buttons = nav.querySelectorAll("button");
    // Every button should have an aria-label
    buttons.forEach((btn) => {
      // The toggle button and nav buttons should all have aria-label
      expect(
        btn.getAttribute("aria-label") || btn.textContent?.trim(),
      ).toBeTruthy();
    });
  });
});

/* ── ContextBar ──────────────────────────────────────────────── */

describe("ContextBar", () => {
  it("renders mode selector group", () => {
    render(<ContextBar />);
    expect(screen.getByRole("group")).toBeInTheDocument();
  });

  it("has pressed state on active mode button", () => {
    render(<ContextBar />);
    const group = screen.getByRole("group");
    const buttons = group.querySelectorAll("button");
    // Exactly one should have aria-pressed="true"
    const pressed = Array.from(buttons).filter(
      (b) => b.getAttribute("aria-pressed") === "true",
    );
    expect(pressed).toHaveLength(1);
  });
});

/* ── FilterBar ───────────────────────────────────────────────── */

describe("FilterBar", () => {
  it("renders without crashing", () => {
    const { container } = render(<FilterBar />);
    expect(container.firstChild).toBeInTheDocument();
  });

  it("has date range button with aria-expanded", () => {
    render(<FilterBar />);
    const dateBtn = screen.getByLabelText("Date range");
    expect(dateBtn).toHaveAttribute("aria-expanded", "false");
    expect(dateBtn).toHaveAttribute("aria-haspopup", "listbox");
  });
});

/* ── AgentConsole ────────────────────────────────────────────── */

describe("AgentConsole", () => {
  it("renders footer landmark", () => {
    render(<AgentConsole />);
    // contentinfo role = footer
    const footer = screen.getByRole("contentinfo");
    expect(footer).toBeInTheDocument();
  });

  it("has labeled input", () => {
    render(<AgentConsole />);
    expect(screen.getByLabelText("Agent directive")).toBeInTheDocument();
  });
});
