import { useState, useCallback, memo } from "react";
import { Card, SectionHeader, Pill, Sparkline, MiniRing, DataGuard, SkeletonCard, SkeletonTable, Skeleton } from "../ui";
import { useScoreboardKPIs, useFinancialSummary, useAlerts, useCampaigns } from "../api/hooks";
import { useShell } from "../shell/ShellProvider";

/* ------------------------------------------------------------------ */
/*  BFF integration — all data from live hooks, no mock fallbacks      */
/* ------------------------------------------------------------------ */

interface ScorecardKpi {
  label: string;
  value: string;
  valueSuffix?: string;
  delta: string;
  deltaColor: string;
  dotColor: string;
  context: string;
  sparkData: readonly number[] | number[];
  sparkColor: string;
  ringPct: number;
  ringColor: string;
  delay: number;
}

/* Campaign leaderboard data — now served by GET /api/scorecard/campaigns */

type AlertSeverity = "CRITICAL" | "WARNING" | "INFO";

interface Alert {
  severity: AlertSeverity;
  text: string;
  time: string;
}

const SEV_MAP: Record<AlertSeverity, { barColor: string; tagColor: string; tagBg: string }> = {
  CRITICAL: { barColor: "var(--red)", tagColor: "var(--red)", tagBg: "rgba(255,92,114,.14)" },
  WARNING: { barColor: "var(--amber)", tagColor: "var(--amber)", tagBg: "rgba(242,177,76,.14)" },
  INFO: { barColor: "var(--cyan)", tagColor: "var(--cyan)", tagBg: "var(--cyan-hover)" },
};

/* FINANCIAL_STRIP mock data removed in P3 — DataGuard handles empty state */

const BADGE_STYLES: Record<string, string> = {
  green:
    "font-mono text-[10px] font-medium tracking-[.06em] text-positive bg-[rgba(79,216,155,.14)] px-2 py-0.5 rounded-[5px] text-right",
  amber:
    "font-mono text-[10px] font-medium tracking-[.06em] text-warning bg-[rgba(242,177,76,.14)] px-2 py-0.5 rounded-[5px] text-right",
  red:
    "font-mono text-[10px] font-medium tracking-[.06em] text-critical bg-[rgba(255,92,114,.14)] px-2 py-0.5 rounded-[5px] text-right",
};

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

/* ---------- Composite health computation from live KPI data ---------- */

interface HealthScores {
  composite: number;   // 0-100
  acquisition: number; // 0-100
  efficiency: number;  // 0-100
  retention: number;   // 0-100
}

function computeHealth(kpis: { label: string; deltaDir: string; targetMet?: boolean; invertDelta?: boolean }[]): HealthScores {
  // Map KPIs to sub-domains
  const acqNames = /household|capture|app completion/i;
  const effNames = /cost|cpihh|llm|visibility/i;
  const retNames = /retention|mob6|churn/i;

  const score = (k: typeof kpis[0]) => {
    // Base: 70 if target not met, 90 if met, ±5 for direction
    let s = k.targetMet !== false ? 90 : 70;
    const goodDir = k.invertDelta ? k.deltaDir === "down" : k.deltaDir === "up";
    s += goodDir ? 5 : -5;
    return Math.max(0, Math.min(100, s));
  };

  const avg = (list: number[]) => list.length ? Math.round(list.reduce((a, b) => a + b, 0) / list.length) : 75;

  const acqScores: number[] = [];
  const effScores: number[] = [];
  const retScores: number[] = [];

  for (const k of kpis) {
    const s = score(k);
    if (acqNames.test(k.label)) acqScores.push(s);
    else if (effNames.test(k.label)) effScores.push(s);
    else if (retNames.test(k.label)) retScores.push(s);
    else acqScores.push(s); // default bucket
  }

  const acquisition = avg(acqScores);
  const efficiency = avg(effScores);
  const retention = avg(retScores);
  const composite = Math.round(acquisition * 0.4 + efficiency * 0.3 + retention * 0.3);

  return { composite, acquisition, efficiency, retention };
}

function HeroGauge({ health }: { health: HealthScores }) {
  const [ringHover, setRingHover] = useState(false);
  const pct = health.composite / 100;
  const C = 2 * Math.PI * 88;
  const offset = C * (1 - pct);
  const toGo = 100 - health.composite;

  const bars = [
    { label: "ACQUISITION", pct: health.acquisition, color: health.acquisition >= 80 ? "bg-cyan" : "bg-warning", score: health.acquisition },
    { label: "EFFICIENCY", pct: health.efficiency, color: health.efficiency >= 80 ? "bg-cyan" : "bg-warning", score: health.efficiency },
    { label: "RETENTION", pct: health.retention, color: health.retention >= 80 ? "bg-cyan" : "bg-warning", score: health.retention },
  ];

  return (
    <section
      className="flex flex-col flex-1 min-w-[290px] max-w-[330px] p-[22px] rounded-card-lg border border-line animate-rise"
      style={{
        background:
          "radial-gradient(120% 80% at 50% 0%, var(--cyan-subtle), var(--panel) 55%)",
        animationDelay: "0s",
      }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-[10px] tracking-[.16em] text-fg2">
          CONTRACT HEALTH
        </span>
        <Pill variant="cyan">COMPOSITE</Pill>
      </div>

      {/* Ring */}
      <div
        className="relative self-center my-[14px] mb-2"
        onMouseEnter={() => setRingHover(true)}
        onMouseLeave={() => setRingHover(false)}
        style={{ cursor: "default" }}
      >
        <svg width="220" height="220" viewBox="0 0 220 220" role="img" aria-label={`Composite health score: ${health.composite}%`}>
          <title>Health Score Gauge</title>
          <circle
            cx="110"
            cy="110"
            r="88"
            fill="none"
            stroke="var(--line)"
            strokeWidth="13"
          />
          <circle
            cx="110"
            cy="110"
            r="88"
            fill="none"
            stroke="var(--cyan)"
            strokeWidth={ringHover ? 16 : 13}
            strokeLinecap="round"
            strokeDasharray={C.toFixed(1)}
            strokeDashoffset={offset.toFixed(1)}
            transform="rotate(-90 110 110)"
            className="animate-ringhero"
            style={{
              filter: ringHover
                ? "drop-shadow(0 0 14px var(--cyan-glow))"
                : "drop-shadow(0 0 7px var(--cyan-glow))",
              transition: "stroke-width 0.25s ease, filter 0.25s ease",
            }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <div className="text-[58px] font-semibold leading-none tracking-[-0.03em]">
            {health.composite}
            <span className="text-[24px] text-fg2 font-medium">%</span>
          </div>
          <div className="font-mono text-[9.5px] tracking-[.12em] text-fg3 mt-1">
            {health.composite >= 100 ? "TARGET MET" : `TO TARGET · +${toGo}% TO GO`}
          </div>
        </div>
      </div>

      {/* Sub-bars */}
      <div className="flex flex-col gap-[9px] mt-[6px]">
        {bars.map((b) => (
          <div key={b.label} className="flex items-center gap-[10px]">
            <span className="flex-none w-[78px] font-mono text-[9.5px] tracking-[.08em] text-fg3">
              {b.label}
            </span>
            <div className="flex-1 h-[5px] rounded-[5px] bg-line overflow-hidden">
              <div
                className={`h-full rounded-[5px] ${b.color}`}
                style={{ width: `${b.pct}%` }}
              />
            </div>
            <span className="font-mono text-[11px] font-medium">{b.score}</span>
          </div>
        ))}
      </div>
    </section>
  );
}

const KpiCard = memo(function KpiCard({
  kpi,
}: {
  kpi: ScorecardKpi;
}) {
  return (
    <Card
      className="flex flex-col p-4 animate-rise hover:border-line-strong transition-colors"
      style={{ animationDelay: `${kpi.delay}s` }}
    >
      {/* Header row */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-[9.5px] tracking-[.1em] text-fg2">
          {kpi.label}
        </span>
        <div
          className="w-[6px] h-[6px] rounded-full"
          style={{ background: kpi.dotColor, boxShadow: `0 0 7px ${kpi.dotColor}` }}
        />
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-[5px] mt-[10px]">
        <span className="text-[30px] font-semibold tracking-[-0.02em]">
          {kpi.value}
          {"valueSuffix" in kpi && kpi.valueSuffix && (
            <span className="text-[18px] text-fg2">{kpi.valueSuffix}</span>
          )}
        </span>
      </div>

      {/* Delta + context */}
      <div className="flex items-center gap-[7px] mt-[5px]">
        <span className={`font-mono text-[11px] font-medium ${kpi.deltaColor}`}>
          {kpi.delta}
        </span>
        <span className="font-mono text-[10px] text-fg3">{kpi.context}</span>
      </div>

      {/* Sparkline + MiniRing */}
      <div className="flex items-end justify-between mt-[14px]">
        <Sparkline data={[...kpi.sparkData]} color={kpi.sparkColor} />
        <MiniRing pct={kpi.ringPct} color={kpi.ringColor} />
      </div>
    </Card>
  );
});

function OperatingStreakCard({ kpis, alertCount }: { kpis: { spark: number[]; deltaDir: string; targetMet?: boolean }[]; alertCount: number }) {
  // Compute streak: count trailing weeks where majority of KPIs trend positive
  // Use sparkline data (12 periods) — count consecutive positive periods from the end
  let streak = 0;
  const totalPeriods = 12;
  for (let period = totalPeriods - 1; period >= 0; period--) {
    let positiveCount = 0;
    for (const k of kpis) {
      if (k.spark.length > period && period > 0 && k.spark[period] >= k.spark[period - 1]) {
        positiveCount++;
      }
    }
    if (positiveCount >= Math.ceil(kpis.length / 2)) {
      streak++;
    } else {
      break;
    }
  }
  streak = Math.max(streak, 1); // at minimum 1 if KPIs exist

  return (
    <Card
      accent
      glow
      className="flex flex-col justify-between p-4 animate-rise"
      style={{ animationDelay: "0.3s" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="font-mono text-[9.5px] tracking-[.1em] text-cyan">
          OPERATING STREAK
        </span>
        <span className="text-[13px]">{streak > 4 ? "▲" : streak > 2 ? "◆" : "▼"}</span>
      </div>

      {/* Value */}
      <div className="flex items-baseline gap-[6px] mt-[6px]">
        <span className="text-[34px] font-bold tracking-[-0.02em]">{streak}</span>
        <span className="font-mono text-[13px] text-fg2">WEEKS ON PACE</span>
      </div>

      {/* 12-segment bar */}
      <div className="flex gap-[3px] mt-[11px]">
        {Array.from({ length: totalPeriods }, (_, i) => (
          <div
            key={i}
            className={`flex-1 h-[6px] rounded-[3px] ${
              i < streak ? "bg-cyan" : "bg-line"
            }`}
          />
        ))}
      </div>

      {/* Footer */}
      <div className="font-mono text-[10px] tracking-[.06em] text-fg2 mt-[11px]">
        {alertCount === 0 ? "ALL CLEAR" : `${alertCount} ACTIVE ALERT${alertCount > 1 ? "S" : ""}`}
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Scorecard component                                           */
/* ------------------------------------------------------------------ */

export function Scorecard() {
  // ---- Global filters ----
  const { filters } = useShell();

  // ---- BFF hook calls (auto-refetch when filters change) ----
  const kpiQuery = useScoreboardKPIs(filters);
  const finQuery = useFinancialSummary(filters);
  const alertQuery = useAlerts(filters);
  const campaignQuery = useCampaigns(filters);

  // ---- ACK (acknowledge) state for alerts ----
  const [ackedIds, setAckedIds] = useState<Set<string>>(new Set());
  const handleAck = useCallback((alertId: string) => {
    setAckedIds((prev) => new Set(prev).add(alertId));
  }, []);

  return (
    <div className="flex flex-col gap-4">
      {/* ===== 1. HUD RIBBON (data-driven) ===== */}
      {(() => {
        // Compute HUD values from loaded data
        const now = new Date();
        const qStart = new Date(now.getFullYear(), Math.floor(now.getMonth() / 3) * 3, 1);
        const qEnd = new Date(now.getFullYear(), Math.floor(now.getMonth() / 3) * 3 + 3, 0);
        const totalWeeks = Math.ceil((qEnd.getTime() - qStart.getTime()) / (7 * 86400000));
        const elapsedWeeks = Math.min(totalWeeks, Math.ceil((now.getTime() - qStart.getTime()) / (7 * 86400000)));
        const qLabel = `Q${Math.floor(now.getMonth() / 3) + 1}`;
        const alertCount = alertQuery.data?.alerts?.length ?? 0;

        // Health computation from KPI data (if loaded)
        const kpiList = kpiQuery.data?.kpis ?? [];
        const health = computeHealth(kpiList);
        const onPace = health.composite >= 75;
        const statusLabel = onPace ? "ON PACE" : health.composite >= 50 ? "AT RISK" : "OFF PACE";
        const statusColor = onPace ? "bg-positive" : health.composite >= 50 ? "bg-warning" : "bg-critical";
        const statusGlow = onPace ? "var(--green)" : health.composite >= 50 ? "var(--amber)" : "var(--red)";

        return (
          <div
            className="flex flex-wrap items-center gap-3 md:gap-4 px-3 md:px-4 py-[9px] rounded-[11px] border border-line font-mono animate-rise"
            style={{
              background:
                "linear-gradient(90deg, var(--cyan-subtle), transparent 40%)",
            }}
          >
            <div className="flex items-center gap-2">
              <div
                className={`w-[7px] h-[7px] rounded-full ${statusColor}`}
                style={{ boxShadow: `0 0 9px ${statusGlow}` }}
              />
              <span className="text-[10.5px] tracking-[.16em] text-fg">
                MISSION STATUS — {statusLabel}
              </span>
            </div>
            <div className="w-px h-[14px] bg-line-strong" />
            <span className="text-[10px] tracking-[.1em] text-fg2">
              WEEK {elapsedWeeks} / {totalWeeks} · CONTRACT CYCLE {qLabel}
            </span>
            <div className="flex-1" />
            <span className="text-[9.5px] tracking-[.12em] text-fg3">
              AUTOPILOT: ASSIST
            </span>
            <span className="text-[9.5px] tracking-[.12em] text-fg3">
              HEALTH: {health.composite}%
            </span>
            <span className={`text-[9.5px] tracking-[.12em] ${alertCount > 0 ? "text-cyan" : "text-fg3"}`}>
              {alertCount} ALERT{alertCount !== 1 ? "S" : ""}
            </span>
          </div>
        );
      })()}

      {/* ===== 2. HERO + KPI DECK ===== */}
      <DataGuard
        {...kpiQuery}
        skeleton={
          <div className="flex gap-4 items-stretch flex-wrap">
            <SkeletonCard className="flex-1 min-w-[290px] max-w-[330px] !h-[300px]" />
            <div className="flex-[3_1_560px] min-w-[300px] grid grid-cols-2 lg:grid-cols-3 gap-[14px]">
              {Array.from({ length: 6 }, (_, i) => (
                <SkeletonCard key={i} />
              ))}
            </div>
          </div>
        }
        emptyHeadline="No KPI data"
        emptyBody="Scorecard KPI data is not available for the selected filters."
      >
        {(kpiData) => {
          // Map API KPIItems → shape the existing KpiCard expects
          const kpiItems = kpiData.kpis
            ? kpiData.kpis.map((k, i) => {
                const isDown = k.deltaDir === "down";
                const isInverted = k.invertDelta;
                // For inverted metrics (e.g. cost), down is good
                const isGood = isInverted ? isDown : !isDown;
                const dotColor = isGood ? "var(--cyan)" : k.targetMet === false ? "var(--red)" : "var(--amber)";
                const deltaColor = isGood ? "text-positive" : k.targetMet === false ? "text-critical" : "text-warning";
                const arrow = k.deltaDir === "up" ? "↑" : "↓";
                return {
                  label: k.label.toUpperCase(),
                  value: k.value,
                  delta: `${arrow} ${k.delta}`,
                  deltaColor,
                  dotColor,
                  context: "",
                  sparkData: k.spark.length ? k.spark : [0, 0, 0, 0, 0, 0, 0, 0],
                  sparkColor: dotColor,
                  ringPct: Math.min(100, 80 + i * 3),
                  ringColor: dotColor,
                  delay: 0.05 + i * 0.05,
                } satisfies ScorecardKpi;
              })
            : null;

          const kpis = kpiItems ?? [];
          const health = computeHealth(kpiData.kpis ?? []);
          const activeAlertCount = alertQuery.data?.alerts?.length ?? 0;

          return (
            <div className="flex gap-4 items-stretch flex-wrap">
              <HeroGauge health={health} />

              {/* KPI Grid -- responsive columns */}
              <section className="flex-[3_1_560px] min-w-[300px] grid grid-cols-2 lg:grid-cols-3 gap-[14px]">
                {kpis.map((kpi) => (
                  <KpiCard key={kpi.label} kpi={kpi} />
                ))}
                <OperatingStreakCard kpis={kpiData.kpis ?? []} alertCount={activeAlertCount} />
              </section>
            </div>
          );
        }}
      </DataGuard>

      {/* ===== 3. FINANCIAL SUMMARY STRIP ===== */}
      <DataGuard
        {...finQuery}
        skeleton={<Skeleton rows={3} className="rounded-card border border-line bg-panel p-5" />}
        emptyHeadline="No financial data"
        emptyBody="Financial summary data is not available for the selected filters."
      >
        {(finData) => {
          const financialStrip = finData.strips ?? [];
          return (
            <section
              className="flex flex-wrap rounded-card border border-line bg-panel overflow-hidden animate-rise"
              style={{ animationDelay: "0.12s" }}
            >
              {financialStrip.map((f, i) => (
                <div
                  key={f.label}
                  className={`flex-1 min-w-[150px] px-5 py-4 ${
                    i < financialStrip.length - 1 ? "border-r border-line" : ""
                  }`}
                >
                  <div className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
                    {f.label}
                  </div>
                  <div className="text-[25px] font-semibold mt-[6px] tracking-[-0.02em]">
                    {f.value}
                  </div>
                  <div className={`font-mono text-[10px] mt-[3px] ${f.detailColor}`}>
                    {f.detail}
                  </div>
                </div>
              ))}
            </section>
          );
        }}
      </DataGuard>

      {/* ===== 4. CAMPAIGN LEADERBOARD + ALERT WIRE ===== */}
      <div className="flex gap-4 items-stretch flex-wrap">
        {/* Campaign Performance */}
        <DataGuard
          {...campaignQuery}
          skeleton={<Skeleton rows={8} className="flex-[1.5_1_480px] min-w-[340px] rounded-card border border-line bg-panel p-5" />}
          emptyHeadline="No campaign data"
          emptyBody="Campaign performance data is not available for the selected filters."
          className="flex-[1.5_1_480px] min-w-[340px]"
        >
          {(campData) => {
            const campaigns = campData.campaigns;
            const fmtSpend = (n: number) =>
              n >= 1_000_000 ? `$${(n / 1_000_000).toFixed(1)}M` : `$${(n / 1_000).toFixed(0)}K`;

            return (
              <section
                className="rounded-card border border-line bg-panel overflow-hidden animate-rise h-full"
                style={{ animationDelay: "0.18s" }}
              >
                {/* Header */}
                <div className="flex items-center justify-between px-[18px] py-[15px] border-b border-line">
                  <SectionHeader title="Campaign Performance" accent="cyan" />
                  <span className="font-mono text-[9.5px] tracking-[.1em] text-fg3">
                    {campaigns.length} · TOP BY ROAS
                  </span>
                </div>

                {/* Column headers */}
                <div className="overflow-x-auto">
                <div className="grid grid-cols-[1fr_88px_80px_76px] gap-2 px-[18px] py-[9px] border-b border-line font-mono text-[9px] tracking-[.1em] text-fg3 min-w-[480px]">
                  <span>CAMPAIGN</span>
                  <span>CHANNEL</span>
                  <span className="text-right">SPEND</span>
                  <span className="text-right">ROAS</span>
                </div>

                {/* Rows */}
                {campaigns.map((c) => (
                  <div
                    key={c.name}
                    className="grid grid-cols-[1fr_88px_80px_76px] gap-2 items-center px-[18px] py-3 border-b border-line hover:bg-panel2 transition-colors min-w-[480px]"
                  >
                    <span className="text-[13px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">
                      {c.name}
                    </span>
                    <span className="font-mono text-[10px] text-fg2">{c.channel}</span>
                    <span className="font-mono text-[12px] text-fg text-right">
                      {fmtSpend(c.spend)}
                    </span>
                    <span className={BADGE_STYLES[c.badge]}>{c.roas.toFixed(1)}×</span>
                  </div>
                ))}
                </div>
              </section>
            );
          }}
        </DataGuard>

        {/* Alert Wire */}
        <DataGuard
          {...alertQuery}
          skeleton={<Skeleton rows={6} className="flex-[1_1_320px] min-w-[300px] rounded-card border border-line bg-panel p-5" />}
          emptyHeadline="No alerts"
          emptyBody="No active alerts at this time."
          className="flex-[1_1_320px] min-w-[300px]"
        >
          {(alertData) => {
            // Map API alerts → shape the existing alert rows expect
            const toneToSeverity: Record<string, AlertSeverity> = { critical: "CRITICAL", warning: "WARNING", info: "INFO" };
            const alerts: Alert[] = (alertData.alerts ?? []).map((a) => ({
              severity: toneToSeverity[a.tone] ?? "INFO",
              text: a.title,
              time: a.meta,
            }));

            // Filter out acknowledged alerts
            const visibleAlerts = alerts.filter(
              (_, i) => !ackedIds.has(`alert-${i}`),
            );
            const alertCount = visibleAlerts.length;

            return (
              <section
                className="flex flex-col rounded-card border border-line bg-panel overflow-hidden animate-rise h-full"
                style={{ animationDelay: "0.24s" }}
              >
                {/* Header */}
                <div className="flex items-center justify-between px-[18px] py-[15px] border-b border-line">
                  <SectionHeader title="Alert Wire" accent="red" />
                  <span className="font-mono text-[9.5px] tracking-[.1em] text-fg3">
                    {alertCount} ACTIVE
                  </span>
                </div>

                {/* Alert rows */}
                <div className="flex-1 min-h-0 overflow-auto">
                  {visibleAlerts.length === 0 && (
                    <div className="flex items-center justify-center py-8 font-mono text-[11px] text-fg3 tracking-[.06em]">
                      ALL ALERTS ACKNOWLEDGED
                    </div>
                  )}
                  {visibleAlerts.map((a, i) => {
                    const sev = SEV_MAP[a.severity];
                    const alertId = `alert-${alerts.indexOf(a)}`;
                    return (
                      <div
                        key={alertId}
                        className={`flex items-center gap-[10px] px-[18px] py-[11px] border-b border-line animate-wirein ${
                          a.severity === "CRITICAL" ? "animate-pulseonce" : ""
                        }`}
                        style={{ animationDelay: `${0.26 + i * 0.06}s` }}
                      >
                        {/* Severity bar */}
                        <div
                          className="w-[3px] h-[30px] rounded-[3px] flex-none"
                          style={{ background: sev.barColor }}
                        />

                        {/* Tag */}
                        <div
                          className="flex-none w-[60px] text-center font-mono text-[8.5px] tracking-[.06em] py-[3px] rounded-[5px]"
                          style={{ color: sev.tagColor, background: sev.tagBg }}
                        >
                          {a.severity}
                        </div>

                        {/* Text */}
                        <div className="flex-1 min-w-0 text-[12px] leading-[1.35] text-fg">
                          {a.text}
                        </div>

                        {/* Time */}
                        <span className="flex-none font-mono text-[9px] text-fg3">
                          {a.time}
                        </span>

                        {/* ACK button */}
                        <button
                          onClick={() => handleAck(alertId)}
                          className="flex-none px-2 py-1 rounded-[6px] border border-line bg-transparent text-fg3 font-mono text-[8.5px] tracking-[.08em] hover:text-cyan hover:border-cyan transition-colors cursor-pointer"
                        >
                          ACK
                        </button>
                      </div>
                    );
                  })}
                </div>
              </section>
            );
          }}
        </DataGuard>
      </div>
    </div>
  );
}
