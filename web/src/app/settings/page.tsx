"use client";
import { useState } from "react";
import { useQuery } from "@/lib/hooks";
import { getSettings } from "@/lib/bff-extended";
import { useTheme } from "@/lib/theme";
import { CardContainer, Button, Skeleton, ErrorState, StatusPill } from "@/components/primitives";

export default function SettingsPage() {
  const { data, loading, error, reload } = useQuery(["settings"], getSettings);
  const { theme, toggle } = useTheme();
  const [mode, setMode] = useState<"BD" | "Client">("BD");

  if (error) return <ErrorState message="Couldn't load settings." onRetry={reload} />;

  return (
    <div className="flex max-w-3xl flex-col gap-4">
      <CardContainer title="Application Mode" subtitle="Controls data sources + simulator behavior platform-wide">
        <div className="flex gap-2">
          {(["BD", "Client"] as const).map((m) => (
            <Button key={m} variant={mode === m ? "primary" : "ghost"} onClick={() => setMode(m)}>{m} Mode</Button>
          ))}
        </div>
      </CardContainer>

      <CardContainer title="Appearance" subtitle="Theme">
        <Button variant="ghost" onClick={toggle}>◐ Switch to {theme === "dark" ? "light" : "dark"} mode</Button>
      </CardContainer>

      <CardContainer title="Data Source Integrations" subtitle="Connect external platforms">
        {loading ? <Skeleton className="h-32" /> : (
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3">
            {data!.connectors.map((c) => (
              <div key={c.name} className="flex items-center justify-between rounded-md border border-line bg-raised px-3 py-2.5">
                <span className="text-[13px] text-fg">{c.name}</span>
                <StatusPill tone={c.status === "connected" ? "positive" : c.status === "syncing" ? "warning" : "critical"}>{c.status}</StatusPill>
              </div>
            ))}
          </div>
        )}
      </CardContainer>

      <CardContainer title="Benchmarks" subtitle="Governed inputs the metric layer + simulator consume">
        <div className="flex flex-wrap gap-2">
          {["Funnel rates", "Media coefficients", "Simulator defaults", "Channel efficiency", "NBD bounds"].map((b) => (
            <span key={b} className="rounded-pill border border-line bg-elevated px-2.5 py-1 text-[11px] text-fg-2">{b}</span>
          ))}
        </div>
        <p className="mt-3 text-xs text-fg-muted">Edit benchmark sliders here; values feed the Allocation + Simulation services.</p>
      </CardContainer>

      <CardContainer title="API & MCP">
        <p className="text-sm text-fg-2">API keys and the MCP server config (so RV agentic tooling can query Apex) live here. Read tools open; write tools route through the approval queue.</p>
      </CardContainer>
    </div>
  );
}
