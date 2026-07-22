"use client";
import { useState } from "react";

/** Docked agent/directive console — Mission-Control input line.
 *  A proposed account change here would become a Directive in the approval queue (never an instant write). */
export function AgentConsole() {
  const [value, setValue] = useState("");
  const chips = ["query_metrics", "simulate_geo", "propose_action"];

  return (
    <div className="border-t border-line bg-surface px-5 py-2.5">
      <form
        onSubmit={(e) => e.preventDefault()}
        className="flex items-center gap-2.5"
        role="search"
        aria-label="Ask Apex"
      >
        <span className="font-mono text-signal animate-blink" aria-hidden>
          ▮
        </span>
        <input
          value={value}
          onChange={(e) => setValue(e.target.value)}
          placeholder="Ask Apex — e.g. reallocate $40k → Cincinnati DMA, cap CPA at $230…"
          aria-label="Ask Apex command input"
          className="flex-1 bg-transparent font-mono text-sm text-fg-2 placeholder:text-fg-muted focus:outline-none"
        />
        <div className="hidden gap-1.5 md:flex" aria-hidden>
          {chips.map((c) => (
            <span
              key={c}
              className="rounded-pill border border-[color-mix(in_oklab,var(--color-accent)_30%,transparent)] bg-[color-mix(in_oklab,var(--color-accent)_16%,transparent)] px-2 py-0.5 font-mono text-[10px] text-accent"
            >
              {c}
            </span>
          ))}
        </div>
      </form>
    </div>
  );
}
