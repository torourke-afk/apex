import { useState, useMemo, useEffect, useCallback, memo } from "react";
import { Card, SectionHeader, DataGuard } from "../ui";
import { useSimulate, useSimPresets } from "../api/hooks";
import type { SimulateInput, SimulateResult } from "../api/hooks";

/* ------------------------------------------------------------------ */
/*  Constants & formulas                                               */
/* ------------------------------------------------------------------ */

const PLAN = { budget: 39.4, brand: 42, sem: 33, social: 18 };

// Model calibrated from DuckDB: 28,851 funded from $68.4M spend (CPIHH ~$2,371)
// Retention: S(180) = 71.7%, LTV(12mo) ~ $6,547
const FUNDED_PER_M = 422; // 28851 / 68.4
const LTV_PER_HH = 6547;
const MOB6_RATE = 0.717;

function computeOutputs(budget: number, brand: number, sem: number, social: number) {
  const email = Math.max(0, 100 - brand - sem - social);
  // SEM and social drive most acquisitions; brand has indirect lift
  const semEff = 1.0;  // baseline efficiency
  const brandEff = 0.35; // brand drives awareness, lower direct conversion
  const socialEff = 0.75;
  const emailEff = 0.25;
  const blendedEff = (sem * semEff + brand * brandEff + social * socialEff + email * emailEff) / 100;
  const funded = Math.round(budget * FUNDED_PER_M * blendedEff);
  const cpihh = funded > 0 ? Math.round((budget * 1e6) / funded) : 0;
  const roas = funded > 0 ? +((funded * LTV_PER_HH) / (budget * 1e6)).toFixed(2) : 0;
  const retained = Math.round(funded * MOB6_RATE);
  return { funded, cpihh, roas, retained, email };
}

const planOutputs = computeOutputs(PLAN.budget, PLAN.brand, PLAN.sem, PLAN.social);

/* ------------------------------------------------------------------ */
/*  Trajectory chart helpers                                           */
/* ------------------------------------------------------------------ */

function buildTrajectory(funded: number) {
  // 8 time points: simulated ramp for both plan and scenario
  const planFinal = planOutputs.funded;
  const scenFinal = funded;
  return Array.from({ length: 8 }, (_, i) => {
    const t = (i + 1) / 8;
    const curve = 1 - Math.pow(1 - t, 1.6); // S-ish ramp
    return {
      plan: Math.round(planFinal * curve),
      scenario: Math.round(scenFinal * curve),
    };
  });
}

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

const SliderInput = memo(function SliderInput({
  label,
  value,
  min,
  max,
  step,
  unit,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  unit: string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
          {label}
        </span>
        <span className="font-mono text-[13px] font-semibold text-fg">
          {unit === "$" ? `$${value.toFixed(1)}M` : `${value}%`}
        </span>
      </div>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(parseFloat(e.target.value))}
        style={{ accentColor: "var(--cyan)" }}
      />
    </div>
  );
});

const OutputCard = memo(function OutputCard({
  label,
  value,
  planValue,
  format,
  delay,
}: {
  label: string;
  value: number;
  planValue: number;
  format: "number" | "dollar" | "roas" | "pct";
  delay: number;
}) {
  const diff = value - planValue;
  const isPositive = format === "dollar" ? diff <= 0 : diff >= 0;

  let formatted: string;
  let deltaStr: string;

  switch (format) {
    case "number":
      formatted = value.toLocaleString();
      deltaStr = `${diff >= 0 ? "+" : ""}${diff.toLocaleString()}`;
      break;
    case "dollar":
      formatted = `$${value.toLocaleString()}`;
      deltaStr = `${diff >= 0 ? "+$" : "−$"}${Math.abs(diff).toLocaleString()}`;
      break;
    case "roas":
      formatted = `${value.toFixed(2)}×`;
      deltaStr = `${diff >= 0 ? "+" : ""}${diff.toFixed(2)}`;
      break;
    case "pct":
      formatted = value.toLocaleString();
      deltaStr = `${diff >= 0 ? "+" : ""}${diff.toLocaleString()}`;
      break;
  }

  return (
    <Card
      className="flex flex-col p-4 animate-rise"
      style={{ animationDelay: `${delay}s` }}
    >
      <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
        {label}
      </span>
      <span className="text-[28px] font-semibold tracking-[-0.02em] mt-2">
        {formatted}
      </span>
      <span
        className={`font-mono text-[11px] font-medium mt-1 ${
          diff === 0 ? "text-fg3" : isPositive ? "text-positive" : "text-warning"
        }`}
      >
        {deltaStr} vs plan
      </span>
    </Card>
  );
});

function TrajectoryChart({
  trajectory,
}: {
  trajectory: { plan: number; scenario: number }[];
}) {
  const [hoverIdx, setHoverIdx] = useState<number | null>(null);
  const W = 540;
  const H = 220;
  const padL = 50;
  const padR = 16;
  const padT = 16;
  const padB = 28;
  const chartW = W - padL - padR;
  const chartH = H - padT - padB;

  const allVals = trajectory.flatMap((p) => [p.plan, p.scenario]);
  const maxVal = Math.max(...allVals) * 1.12;

  const getX = (i: number) => padL + (i / (trajectory.length - 1)) * chartW;
  const getYPlan = (i: number) => padT + chartH - (trajectory[i].plan / maxVal) * chartH;
  const getYScen = (i: number) => padT + chartH - (trajectory[i].scenario / maxVal) * chartH;

  const planPoints = trajectory.map((_, i) => `${getX(i).toFixed(1)},${getYPlan(i).toFixed(1)}`).join(" ");
  const scenPoints = trajectory.map((_, i) => `${getX(i).toFixed(1)},${getYScen(i).toFixed(1)}`).join(" ");

  const months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug"];

  return (
    <svg
      width="100%"
      height={H}
      viewBox={`0 0 ${W} ${H}`}
      preserveAspectRatio="xMidYMid meet"
      className="overflow-visible"
      role="img"
      aria-label="Budget simulation forecast chart comparing baseline and scenario projections"
      onMouseLeave={() => setHoverIdx(null)}
    >
      <title>Simulation Forecast</title>
      {/* Grid lines */}
      {[0.25, 0.5, 0.75, 1].map((frac) => {
        const y = padT + chartH - frac * chartH;
        const label = Math.round(frac * maxVal).toLocaleString();
        return (
          <g key={frac}>
            <line x1={padL} y1={y} x2={W - padR} y2={y} stroke="var(--line)" strokeWidth="1" />
            <text x={padL - 6} y={y + 3} textAnchor="end" className="font-mono" style={{ fontSize: "8px", fill: "var(--text3)" }}>
              {label}
            </text>
          </g>
        );
      })}

      {/* X-axis labels */}
      {months.map((m, i) => (
        <text key={m} x={getX(i)} y={H - 4} textAnchor="middle" className="font-mono" style={{ fontSize: "8px", fill: "var(--text3)" }}>
          {m}
        </text>
      ))}

      {/* Area fill between plan and scenario */}
      <polygon
        points={[
          ...trajectory.map((_, i) => `${getX(i).toFixed(1)},${getYScen(i).toFixed(1)}`),
          ...trajectory.map((_, i) => `${getX(trajectory.length - 1 - i).toFixed(1)},${getYPlan(trajectory.length - 1 - i).toFixed(1)}`),
        ].join(" ")}
        fill="var(--cyan)"
        opacity={0.06}
      />

      {/* Plan of Record (dashed) */}
      <polyline points={planPoints} fill="none" stroke="var(--text3)" strokeWidth="1.5" strokeDasharray="6 4" strokeLinecap="round" strokeLinejoin="round" />

      {/* Scenario (solid cyan) */}
      <polyline points={scenPoints} fill="none" stroke="var(--cyan)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" style={{ filter: "drop-shadow(0 0 5px var(--cyan-glow))" }} />

      {/* Hover crosshair + dots + tooltip */}
      {hoverIdx !== null && hoverIdx < trajectory.length && (
        <g>
          <line x1={getX(hoverIdx)} y1={padT} x2={getX(hoverIdx)} y2={padT + chartH} stroke="var(--text3)" strokeWidth="0.5" strokeDasharray="3,3" opacity={0.5} />
          <circle cx={getX(hoverIdx)} cy={getYPlan(hoverIdx)} r="4" fill="var(--bg2)" stroke="var(--text3)" strokeWidth="1.5" />
          <circle cx={getX(hoverIdx)} cy={getYScen(hoverIdx)} r="4.5" fill="var(--bg2)" stroke="var(--cyan)" strokeWidth="2" style={{ filter: "drop-shadow(0 0 4px var(--cyan-glow))" }} />
          {/* Tooltip box */}
          {(() => {
            const tx = getX(hoverIdx);
            const ty = Math.min(getYPlan(hoverIdx), getYScen(hoverIdx)) - 8;
            const flip = tx > W - 120;
            const bx = flip ? tx - 108 : tx + 8;
            const pt = trajectory[hoverIdx];
            const delta = pt.scenario - pt.plan;
            return (
              <foreignObject x={bx} y={ty - 46} width={100} height={50}>
                <div style={{ background: "var(--bg2)", border: "1px solid var(--line)", borderRadius: 6, padding: "5px 8px", fontSize: 10, fontFamily: "var(--font-mono)", lineHeight: 1.5 }}>
                  <div style={{ color: "var(--text3)" }}>{months[hoverIdx] ?? `M${hoverIdx + 1}`}</div>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <span style={{ color: "var(--text3)" }}>Plan</span>
                    <span style={{ fontWeight: 600, color: "var(--text)" }}>{pt.plan.toLocaleString()}</span>
                  </div>
                  <div style={{ display: "flex", justifyContent: "space-between", gap: 8 }}>
                    <span style={{ color: "var(--cyan)" }}>Scen</span>
                    <span style={{ fontWeight: 600, color: "var(--cyan)" }}>{pt.scenario.toLocaleString()}</span>
                  </div>
                  {delta !== 0 && (
                    <div style={{ color: delta > 0 ? "var(--positive)" : "var(--warning)", fontWeight: 600, textAlign: "right" }}>
                      {delta > 0 ? "+" : ""}{delta.toLocaleString()}
                    </div>
                  )}
                </div>
              </foreignObject>
            );
          })()}
        </g>
      )}

      {/* Endpoint dots */}
      {(() => {
        const last = trajectory.length - 1;
        return (
          <>
            <circle cx={getX(last)} cy={getYPlan(last)} r="3" fill="var(--text3)" />
            <circle cx={getX(last)} cy={getYScen(last)} r="4" fill="var(--cyan)" style={{ filter: "drop-shadow(0 0 5px var(--cyan-glow))" }} />
          </>
        );
      })()}

      {/* Invisible hit areas for hover */}
      {trajectory.map((_, i) => (
        <rect
          key={`hit-${i}`}
          x={getX(i) - chartW / trajectory.length / 2}
          y={padT}
          width={chartW / trajectory.length}
          height={chartH}
          fill="transparent"
          onMouseEnter={() => setHoverIdx(i)}
          style={{ cursor: "crosshair" }}
        />
      ))}

      {/* Legend */}
      <g transform={`translate(${padL + 4}, ${padT + 4})`}>
        <line x1="0" y1="0" x2="16" y2="0" stroke="var(--text3)" strokeWidth="1.5" strokeDasharray="4 3" />
        <text x="20" y="3" className="font-mono" style={{ fontSize: "8px", fill: "var(--text3)" }}>PLAN OF RECORD</text>
        <line x1="0" y1="14" x2="16" y2="14" stroke="var(--cyan)" strokeWidth="2" />
        <text x="20" y="17" className="font-mono" style={{ fontSize: "8px", fill: "var(--cyan)" }}>SCENARIO</text>
      </g>
    </svg>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Simulator component                                           */
/* ------------------------------------------------------------------ */

/** Build the BFF request payload from slider state. */
function buildSimRequest(
  budget: number,
  brand: number,
  sem: number,
  social: number,
): SimulateInput {
  const email = Math.max(0, 100 - brand - sem - social);
  return {
    name: "Scenario",
    mode: "bd",
    total_spend: budget * 1_000_000,
    channels: {
      brand: { spend_pct: brand / 100, cpc: 2.5, cpl: 120, brand_lift_pct: 0.05 },
      sem: { spend_pct: sem / 100, cpc: 3.8, cpl: 84, use_cpl: true },
      social: { spend_pct: social / 100, cpc: 1.9, cpl: 95 },
      email: { spend_pct: email / 100, cpc: 0.1, cpl: 12 },
    },
  };
}

/** Extract display-friendly outputs from BFF response, or return null. */
function parseSimResult(
  res: SimulateResult,
): { funded: number; cpihh: number; roas: number; retained: number } | null {
  // The BFF returns a flat dict from the engine dataclass.
  // Try common field names the engine might use.
  const funded =
    (res.funded_accounts as number) ??
    (res.total_funded as number) ??
    (res.funded as number);
  const cpihh =
    (res.blended_cpihh as number) ??
    (res.blended_cpl as number) ??
    (res.cpihh as number);
  const roas =
    (res.portfolio_roas as number) ??
    (res.roas as number);
  const retained =
    (res.retained_mob6 as number) ??
    (res.mob6_retained as number) ??
    (res.retained as number);

  if (funded == null || cpihh == null || roas == null || retained == null) return null;
  return {
    funded: Math.round(funded),
    cpihh: Math.round(cpihh),
    roas: +Number(roas).toFixed(2),
    retained: Math.round(retained),
  };
}

export function Simulator() {
  const [budget, setBudget] = useState(PLAN.budget);
  const [brand, setBrand] = useState(PLAN.brand);
  const [sem, setSem] = useState(PLAN.sem);
  const [social, setSocial] = useState(PLAN.social);

  /* ── BFF hooks ─────────────────────────────────────────────── */
  const presets = useSimPresets();
  const sim = useSimulate();

  /* Client-side fallback computation (always up-to-date) */
  const clientOutputs = useMemo(
    () => computeOutputs(budget, brand, sem, social),
    [budget, brand, sem, social],
  );

  /* Prefer BFF result when available, fall back to client-side */
  const bffOutputs = sim.data ? parseSimResult(sim.data) : null;
  const outputs = bffOutputs ?? clientOutputs;
  const usingBFF = bffOutputs !== null;

  const trajectory = useMemo(() => buildTrajectory(outputs.funded), [outputs.funded]);

  /* ── Run simulation via BFF ────────────────────────────────── */
  const runSimulation = useCallback(() => {
    sim.mutate(buildSimRequest(budget, brand, sem, social));
  }, [budget, brand, sem, social, sim]);

  /* Fire an initial simulation on mount (best-effort) */
  const [hasRun, setHasRun] = useState(false);
  useEffect(() => {
    if (!hasRun) {
      setHasRun(true);
      sim.mutate(buildSimRequest(budget, brand, sem, social));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function resetToPlan() {
    setBudget(PLAN.budget);
    setBrand(PLAN.brand);
    setSem(PLAN.sem);
    setSocial(PLAN.social);
    sim.reset();
  }

  return (
    <div className="flex gap-4 items-stretch flex-wrap">
      {/* ===== Left: Scenario Inputs ===== */}
      <section
        className="flex flex-col rounded-card border border-line bg-panel overflow-hidden animate-rise"
        style={{ flex: "0 1 400px", minWidth: "320px" }}
      >
        {/* Header */}
        <div className="px-[18px] py-[15px] border-b border-line">
          <SectionHeader title="Scenario Inputs" accent="cyan" />
        </div>

        <div className="flex flex-col gap-6 p-[18px]">
          {/* Presets selector */}
          <DataGuard
            {...presets}
            skeleton={
              <div className="h-8 rounded bg-panel2 animate-pulse" />
            }
            emptyHeadline="No presets"
            emptyBody="Presets unavailable."
          >
            {(data) => (
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
                  PRESETS
                </span>
                <div className="flex gap-2 flex-wrap">
                  {data.presets.map((p) => (
                    <button
                      key={p.name}
                      disabled={!p.available || !p.config}
                      title={p.description}
                      onClick={() => {
                        if (p.config) {
                          setBudget(p.config.budget);
                          setBrand(p.config.brand);
                          setSem(p.config.sem);
                          setSocial(p.config.social);
                          sim.reset();
                        }
                      }}
                      className="px-2.5 py-1 rounded-pill border border-line bg-transparent text-fg2 font-mono text-[9px] tracking-[.06em] hover:border-cyan hover:text-cyan transition-colors cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                      {p.label}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </DataGuard>

          {/* Budget Slider */}
          <SliderInput
            label="TOTAL BUDGET"
            value={budget}
            min={20}
            max={60}
            step={0.1}
            unit="$"
            onChange={setBudget}
          />

          {/* Channel Mix Sliders */}
          <div className="flex flex-col gap-5">
            <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
              CHANNEL MIX
            </span>

            <SliderInput
              label="BRAND %"
              value={brand}
              min={0}
              max={80}
              step={1}
              unit="%"
              onChange={setBrand}
            />

            <SliderInput
              label="SEM %"
              value={sem}
              min={0}
              max={80}
              step={1}
              unit="%"
              onChange={setSem}
            />

            <SliderInput
              label="SOCIAL %"
              value={social}
              min={0}
              max={80}
              step={1}
              unit="%"
              onChange={setSocial}
            />
          </div>

          {/* Email/CRM Residual */}
          <Card className="flex items-center justify-between p-3">
            <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
              EMAIL / CRM (RESIDUAL)
            </span>
            <span
              className={`font-mono text-[13px] font-semibold ${
                clientOutputs.email < 0 ? "text-critical" : "text-fg"
              }`}
            >
              {clientOutputs.email}%
            </span>
          </Card>

          {clientOutputs.email < 0 && (
            <span className="font-mono text-[9px] text-critical">
              Channel allocation exceeds 100%. Adjust sliders.
            </span>
          )}

          {/* Run + Reset Buttons */}
          <div className="flex gap-2">
            <button
              onClick={runSimulation}
              disabled={sim.loading || clientOutputs.email < 0}
              className="flex-1 py-2.5 rounded-pill bg-cyan text-cyan-ink font-mono text-[10px] font-bold tracking-[.08em] hover:brightness-110 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {sim.loading ? "RUNNING..." : "RUN SIMULATION"}
            </button>
            <button
              onClick={resetToPlan}
              className="flex-1 py-2.5 rounded-pill border border-line bg-transparent text-fg3 font-mono text-[10px] font-semibold tracking-[.08em] hover:border-cyan hover:text-cyan transition-colors cursor-pointer"
            >
              RESET TO PLAN
            </button>
          </div>

          {/* BFF status indicator */}
          {sim.error && (
            <span className="font-mono text-[9px] text-warning">
              BFF unavailable — using client-side model
            </span>
          )}
          {usingBFF && (
            <span className="font-mono text-[9px] text-positive">
              Results from server simulation
            </span>
          )}
        </div>
      </section>

      {/* ===== Right: Projected Outcome ===== */}
      <section
        className="flex-1 min-w-[400px] flex flex-col gap-4 animate-rise"
        style={{ animationDelay: "0.1s" }}
      >
        {/* Output Cards -- 2x2 grid */}
        <Card
          accent
          glow
          className="p-5"
        >
          <div className="mb-4">
            <SectionHeader title="Projected Outcome" accent="cyan" />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <OutputCard
              label="FUNDED ACCOUNTS"
              value={outputs.funded}
              planValue={planOutputs.funded}
              format="number"
              delay={0.12}
            />
            <OutputCard
              label="BLENDED CPIHH"
              value={outputs.cpihh}
              planValue={planOutputs.cpihh}
              format="dollar"
              delay={0.16}
            />
            <OutputCard
              label="PORTFOLIO ROAS"
              value={outputs.roas}
              planValue={planOutputs.roas}
              format="roas"
              delay={0.20}
            />
            <OutputCard
              label="RETAINED @ MOB6"
              value={outputs.retained}
              planValue={planOutputs.retained}
              format="number"
              delay={0.24}
            />
          </div>
        </Card>

        {/* Funded Trajectory Chart */}
        <Card className="p-5">
          <div className="mb-4">
            <SectionHeader title="Funded Trajectory" accent="cyan" />
          </div>
          <TrajectoryChart trajectory={trajectory} />
        </Card>
      </section>
    </div>
  );
}
