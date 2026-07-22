"use client";
import { useState } from "react";
import { runSimulation, SimInputs, SimResult } from "@/lib/bff";
import { CardContainer, KPICard, Button, Skeleton, StatusPill } from "@/components/primitives";

const DEFAULTS: SimInputs = { annualSpend: 18, brandPct: 0.4, mob6Retention: 0.62, baseLtv: 1850 };

export default function SimulatorPage() {
  const [inputs, setInputs] = useState<SimInputs>(DEFAULTS);
  const [result, setResult] = useState<SimResult | null>(null);
  const [running, setRunning] = useState(false);
  const [committed, setCommitted] = useState(false);

  const set = (k: keyof SimInputs, v: number) => setInputs((i) => ({ ...i, [k]: v }));

  const run = async () => {
    setRunning(true);
    setCommitted(false);
    const r = await runSimulation(inputs);
    setResult(r);
    setRunning(false);
  };

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-[320px_1fr]">
      {/* Inputs */}
      <CardContainer title="Inputs" subtitle="BD Mode · industry benchmarks">
        <div className="flex flex-col gap-5">
          <Slider label="Annual Media Spend ($M)" min={0.5} max={50} step={0.5} value={inputs.annualSpend} fmt={(v) => `$${v}M`} onChange={(v) => set("annualSpend", v)} />
          <Slider label="Brand Media %" min={0} max={1} step={0.05} value={inputs.brandPct} fmt={(v) => `${Math.round(v * 100)}%`} onChange={(v) => set("brandPct", v)} />
          <Slider label="MOB6 Retention Rate" min={0.3} max={0.9} step={0.01} value={inputs.mob6Retention} fmt={(v) => `${Math.round(v * 100)}%`} onChange={(v) => set("mob6Retention", v)} />
          <Slider label="Base LTV per HH ($)" min={500} max={4000} step={50} value={inputs.baseLtv} fmt={(v) => `$${v}`} onChange={(v) => set("baseLtv", v)} />
          <Button variant="primary" onClick={run} disabled={running}>{running ? "Running…" : "Run simulation"}</Button>
        </div>
      </CardContainer>

      {/* Results */}
      <div className="flex flex-col gap-4">
        <CardContainer title="Simulation Results" subtitle="Projected full-funnel outcome">
          {running ? (
            <div className="relative" role="status" aria-live="polite">
              <div className="mb-3 flex items-center gap-2 text-[12.5px] text-fg-2">
                <span className="h-2 w-2 animate-beacon rounded-pill bg-signal" aria-hidden />
                Modeling funnel — running the allocator…
              </div>
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
                {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} className="h-[88px]" />)}
              </div>
            </div>
          ) : result ? (
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 animate-rise-in">
              <KPICard label="Total Spend" value={result.totalSpend} />
              <KPICard label="Funded Accounts" value={result.fundedAccounts} delta="vs benchmark" deltaDir="up" />
              <KPICard label="Retained HH (MOB6)" value={result.retainedHH} />
              <KPICard label="PFI Households" value={result.pfiHH} />
              <KPICard label="Portfolio LTV" value={result.portfolioLtv} />
              <KPICard label="CPIHH" value={result.cpihh} delta="lower is better" deltaDir="down" invertDelta />
            </div>
          ) : (
            <p className="py-8 text-center text-sm text-fg-2">Set inputs and run a simulation to see projected funnel outcomes.</p>
          )}
        </CardContainer>

        {result && !running && (
          <CardContainer title="Funnel Waterfall" subtitle="Projected volume vs industry benchmark">
            <div className="flex items-end gap-4 pt-2" style={{ height: 160 }}>
              {result.waterfall.map((w) => {
                const max = Math.max(...result.waterfall.map((x) => x.value));
                return (
                  <div key={w.stage} className="flex flex-1 flex-col items-center gap-1">
                    <div className="num text-[10px] text-fg-2">{w.value.toLocaleString()}</div>
                    <div className="flex w-full items-end justify-center gap-1" style={{ height: 110 }}>
                      <div className="w-1/2 rounded-t bg-signal" style={{ height: `${(w.value / max) * 100}%` }} title="Projected" />
                      <div className="w-1/2 rounded-t bg-elevated" style={{ height: `${(w.benchmark / max) * 100}%` }} title="Benchmark" />
                    </div>
                    <div className="text-[10px] text-fg-muted">{w.stage}</div>
                  </div>
                );
              })}
            </div>
            <div className="mt-4 flex items-center gap-3">
              {committed ? (
                <StatusPill tone="positive">✓ staged as directive — awaiting approval</StatusPill>
              ) : (
                <>
                  <Button variant="primary" onClick={() => setCommitted(true)}>Commit as directive</Button>
                  <span className="text-xs text-fg-muted">Routes to the approval queue — never an instant write.</span>
                </>
              )}
            </div>
          </CardContainer>
        )}
      </div>
    </div>
  );
}

function Slider({ label, min, max, step, value, fmt, onChange }: {
  label: string; min: number; max: number; step: number; value: number; fmt: (v: number) => string; onChange: (v: number) => void;
}) {
  return (
    <label className="block">
      <div className="mb-1.5 flex items-center justify-between">
        <span className="text-[12px] text-fg-2">{label}</span>
        <span className="num text-[12px] font-semibold text-fg">{fmt(value)}</span>
      </div>
      <input
        type="range" min={min} max={max} step={step} value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        className="w-full accent-[var(--color-accent)]"
        aria-label={label}
      />
    </label>
  );
}
