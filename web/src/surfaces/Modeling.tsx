import { Card, SectionHeader, Pill, DataGuard } from "../ui";
import {
  useAttribution,
  useModelRegistry,
  useIncrementalityTests,
} from "../api/hooks";
import type {
  AttributionChannel,
  ModelRegistryItem,
  IncrementalityTest,
} from "../api/hooks";
import { useShell } from "../shell/ShellProvider";

/* ------------------------------------------------------------------ */
/*  BFF integration — all data from live hooks, no mock fallbacks      */
/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/*  Sub-components                                                     */
/* ------------------------------------------------------------------ */

function IncrementalContributionContent({ channels }: { channels: AttributionChannel[] }) {
  const maxPct = 100;
  const barMaxH = 180; // px

  return (
    <div className="flex items-end justify-between gap-4 mt-6 px-4" style={{ height: barMaxH + 40 }}>
      {channels.map((bar) => {
        const pct = bar.value * 200; // scale 0-0.5 → 0-100
        const h = (pct / maxPct) * barMaxH;
        return (
          <div key={bar.name} className="flex flex-col items-center gap-2 flex-1">
            {/* Value label */}
            <span
              className="font-mono text-[12px] font-semibold"
              style={{ color: bar.color }}
            >
              {`${Math.round(bar.value * 100)}%`}
            </span>

            {/* Bar */}
            <div
              className="w-full max-w-[52px] rounded-t-[6px] transition-all duration-500"
              style={{
                height: h,
                background: bar.color,
                opacity: 0.75,
                boxShadow: `0 0 12px ${bar.color}33`,
              }}
            />

            {/* Channel name */}
            <span className="font-mono text-[9px] tracking-[.1em] text-fg3 mt-1">
              {bar.name}
            </span>
          </div>
        );
      })}
    </div>
  );
}

function ModelRegistryContent({ models }: { models: ModelRegistryItem[] }) {
  return (
    <>
      {/* Column headers */}
      <div className="grid grid-cols-[1.4fr_1fr_60px_70px_100px] gap-2 px-[18px] py-[9px] border-b border-line font-mono text-[9px] tracking-[.1em] text-fg3">
        <span>MODEL</span>
        <span>TYPE</span>
        <span className="text-right">R²</span>
        <span className="text-center">STATUS</span>
        <span className="text-right">TRAINED</span>
      </div>

      {/* Rows */}
      {models.map((row) => (
        <div
          key={row.name}
          className="grid grid-cols-[1.4fr_1fr_60px_70px_100px] gap-2 items-center px-[18px] py-3 border-b border-line hover:bg-panel2 transition-colors"
        >
          <span className="text-[13px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">
            {row.name}
          </span>
          <span className="font-mono text-[10px] text-fg2">{row.model_type}</span>
          <span className="font-mono text-[12px] font-medium text-right">
            {row.r_squared.toFixed(2)}
          </span>
          <div className="flex justify-center">
            <Pill variant="green" dot>
              {row.status}
            </Pill>
          </div>
          <span className="font-mono text-[10px] text-fg3 text-right">
            {row.trained_ago}
          </span>
        </div>
      ))}
    </>
  );
}

function IncrementalityContent({ tests }: { tests: IncrementalityTest[] }) {
  return (
    <div className="flex flex-col gap-3 mt-4">
      {tests.map((test) => (
        <div
          key={test.name}
          className="flex flex-col gap-2 p-4 rounded-inner border border-line bg-panel2"
        >
          {/* Top row: name + lift */}
          <div className="flex items-center justify-between">
            <span className="text-[13px] font-semibold">{test.name}</span>
            <span
              className="font-mono text-[14px] font-bold"
              style={{ color: "var(--green)" }}
            >
              +{(test.lift * 100).toFixed(1)}%
            </span>
          </div>

          {/* Bottom row: method + p-value */}
          <div className="flex items-center justify-between">
            <span className="font-mono text-[10px] text-fg3 tracking-[.06em]">
              {test.method}
            </span>
            <span className="font-mono text-[10px] text-fg2">
              p = {test.p_value.toFixed(3)}
            </span>
          </div>

          {/* Significance bar */}
          <div className="w-full h-[4px] rounded-[4px] bg-line overflow-hidden mt-1">
            <div
              className="h-full rounded-[4px]"
              style={{
                width: `${Math.min(100, (1 - test.p_value) * 100)}%`,
                background: "var(--green)",
                opacity: 0.7,
              }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Modeling component                                            */
/* ------------------------------------------------------------------ */

export function Modeling() {
  const { filters } = useShell();
  const attribution = useAttribution(filters);
  const registry = useModelRegistry(filters);
  const incrementality = useIncrementalityTests(filters);

  return (
    <div className="flex flex-col gap-4">
      {/* ===== Top: Incremental Contribution Bar Chart ===== */}
      <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.05s" }}>
        <SectionHeader title="Incremental Contribution" meta="MODELED ATTRIBUTION" />

        <DataGuard
          data={attribution.data}
          loading={attribution.loading}
          error={attribution.error}
          reload={attribution.reload}
        >
          {(data) => (
            <IncrementalContributionContent
              channels={data.channels}
            />
          )}
        </DataGuard>
      </Card>

      {/* ===== Bottom row: Model Registry + Incrementality Tests ===== */}
      <div className="grid gap-4" style={{ gridTemplateColumns: "1.5fr 1fr" }}>
        {/* Model Registry */}
        <Card
          className="overflow-hidden animate-rise"
          style={{ animationDelay: "0.12s" }}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-[18px] py-[15px] border-b border-line">
            <SectionHeader
              title="Model Registry"
              meta={`${registry.data?.count ?? 0} MODELS`}
            />
          </div>

          <DataGuard
            data={registry.data}
            loading={registry.loading}
            error={registry.error}
            reload={registry.reload}
          >
            {(data) => (
              <ModelRegistryContent
                models={data.models}
              />
            )}
          </DataGuard>
        </Card>

        {/* Incrementality Tests */}
        <Card
          className="p-[18px] animate-rise"
          style={{ animationDelay: "0.18s" }}
        >
          <SectionHeader title="Incrementality Tests" meta="ACTIVE EXPERIMENTS" />

          <DataGuard
            data={incrementality.data}
            loading={incrementality.loading}
            error={incrementality.error}
            reload={incrementality.reload}
          >
            {(data) => (
              <IncrementalityContent
                tests={data.tests}
              />
            )}
          </DataGuard>
        </Card>
      </div>
    </div>
  );
}
