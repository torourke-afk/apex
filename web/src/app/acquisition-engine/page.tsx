"use client";
import { useEffect, useRef, useState } from "react";
import { useQuery } from "@/lib/hooks";
import { getAllocation, AllocateData } from "@/lib/bff-extended";
import { CardContainer, KPICard, Button, Skeleton, ErrorState, StatusPill } from "@/components/primitives";
import { ResponseCurveChart, DataTable } from "@/components/charts";

export default function AcquisitionEnginePage() {
  const [objective, setObjective] = useState<"Profit" | "Volume">("Profit");
  const { data, loading, error, reload } = useQuery(["allocate", objective], () => getAllocation(objective));
  const [t, setT] = useState(0); // rollout progress 0→1
  const [running, setRunning] = useState(false);
  const [committed, setCommitted] = useState(false);
  const raf = useRef<number | null>(null);

  const runRollout = () => {
    setRunning(true); setCommitted(false);
    const start = performance.now();
    const dur = 4000;
    const tick = (now: number) => {
      const p = Math.min((now - start) / dur, 1);
      setT(p);
      if (p < 1) raf.current = requestAnimationFrame(tick);
      else setRunning(false);
    };
    raf.current = requestAnimationFrame(tick);
  };
  useEffect(() => () => { if (raf.current) cancelAnimationFrame(raf.current); }, []);

  if (error) return <ErrorState message="Couldn't load the allocation engine." onRetry={reload} />;

  const maxSpend = data ? Math.max(...data.combos.map((c) => c.optimalSpend)) * 1.1 : 1;

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-line bg-surface px-4 py-3">
        <span className="text-[12.5px] text-fg-2">Objective</span>
        {(["Profit", "Volume"] as const).map((o) => (
          <Button key={o} variant={objective === o ? "primary" : "ghost"} onClick={() => { setObjective(o); setT(0); }}>{o}</Button>
        ))}
        <div className="ml-auto text-[12.5px] text-fg-2">Budget <b className="num text-fg">{data?.budget ? `$${(data.budget / 1e6).toFixed(2)}M/wk` : "—"}</b></div>
      </div>

      {/* Waste gap headline */}
      <CardContainer>
        {loading ? <Skeleton className="h-24" /> : (
          <div className="flex flex-wrap items-end justify-between gap-4">
            <div>
              <div className="text-[11px] uppercase tracking-[0.07em] text-fg-2">Left on the table / year · same budget</div>
              <div className="num mt-1 text-5xl font-bold text-accent">{data!.moneyLeftPerYear}</div>
            </div>
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              <KPICard label="CAC today" value={data!.today.cac} />
              <KPICard label="CAC optimal" value={data!.optimal.cac} delta="−23%" deltaDir="down" invertDelta />
              <KPICard label="Accounts today" value={data!.today.accounts} />
              <KPICard label="Accounts optimal" value={data!.optimal.accounts} delta="+34%" deltaDir="up" />
            </div>
          </div>
        )}
      </CardContainer>

      {/* Response curves */}
      <CardContainer title="Per-campaign response curves" subtitle="Each dot sits below its curve = waste; ring = optimal spend. Bounded 0.4×–2.0×, ≤20%/wk.">
        {loading ? <Skeleton className="h-64" /> : (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {data!.combos.slice(0, 8).map((c) => (
              <div key={c.id}>
                <div className="mb-1 flex items-center justify-between text-[11px]">
                  <span className="text-fg">{c.campaign} · {c.geo}</span>
                  <StatusPill tone={c.role === "Scale" ? "positive" : c.role === "Defend" ? "warning" : "muted"}>{c.role}</StatusPill>
                </div>
                <ResponseCurveChart
                  k={c.k} sRef={data!.sRef} currentSpend={c.currentSpend} optimalSpend={c.optimalSpend}
                  currentAccounts={c.currentAccounts} optimalAccounts={c.optimalAccounts} maxSpend={maxSpend} t={t}
                />
              </div>
            ))}
          </div>
        )}
        {!loading && (
          <div className="mt-4 flex items-center gap-3">
            <Button variant="primary" onClick={runRollout} disabled={running}>{running ? "Simulating rollout…" : t >= 1 ? "Replay rollout" : "▶ Run 30-day rollout"}</Button>
            <span className="text-xs text-fg-muted">Dots travel onto their curves as the agent learns the true response.</span>
          </div>
        )}
      </CardContainer>

      {/* Top moves + geo flow */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        <CardContainer title="Top moves" subtitle="Current → optimal, role-tagged">
          {loading ? <Skeleton className="h-48" /> : (
            <DataTable
              columns={[
                { key: "campaign", label: "Campaign", render: (r) => `${r.campaign} · ${r.geo}` },
                { key: "role", label: "Role", render: (r) => <StatusPill tone={r.role === "Scale" ? "positive" : r.role === "Defend" ? "warning" : "muted"}>{r.role}</StatusPill> },
                { key: "currentSpend", label: "Now", render: (r) => <span className="num">${(r.currentSpend / 1000).toFixed(0)}k</span> },
                { key: "optimalSpend", label: "Optimal", render: (r) => <span className="num text-positive">${(r.optimalSpend / 1000).toFixed(0)}k</span> },
              ]}
              rows={data!.combos}
            />
          )}
        </CardContainer>
        <CardContainer title="Geo money-flow" subtitle="Donor → recipient as the plan executes">
          {loading ? <Skeleton className="h-48" /> : (
            <div className="flex flex-col gap-3">
              {data!.flows.map((f) => (
                <div key={`${f.from}-${f.to}`} className="flex items-center gap-3 text-[13px]">
                  <span className="w-24 text-right text-fg-2">{f.from}</span>
                  <div className="relative h-1.5 flex-1 overflow-hidden rounded-pill bg-elevated">
                    <div className="absolute inset-y-0 left-0 rounded-pill bg-accent transition-[width] duration-700" style={{ width: `${t * 100}%` }} />
                  </div>
                  <span className="w-24 text-fg">{f.to}</span>
                  <span className="num w-16 text-right text-positive">${(f.amount / 1000).toFixed(0)}k</span>
                </div>
              ))}
              <div className="mt-2 flex items-center gap-3">
                {committed ? (
                  <StatusPill tone="positive">✓ staged as directive — awaiting approval</StatusPill>
                ) : (
                  <>
                    <Button variant="primary" onClick={() => setCommitted(true)} disabled={t < 1}>Commit reallocation</Button>
                    <span className="text-xs text-fg-muted">{t < 1 ? "Run the rollout first." : "Routes to the approval queue — never an instant write."}</span>
                  </>
                )}
              </div>
            </div>
          )}
        </CardContainer>
      </div>
    </div>
  );
}
