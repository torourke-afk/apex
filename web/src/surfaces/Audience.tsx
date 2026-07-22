import { memo } from "react";
import { Card, SectionHeader, DataGuard, Skeleton } from "../ui";
import { useSpendDMA, useAudienceSegments, useTopMarkets } from "../api/hooks";
import type { AudienceSegment } from "../api/hooks";
import { useShell } from "../shell/ShellProvider";

/* ------------------------------------------------------------------ */
/*  DMA Heatmap Grid                                                   */
/* ------------------------------------------------------------------ */

// Deterministic pseudo-random based on cell index
function seededOpacity(index: number): number {
  const x = Math.sin(index * 127.1 + 311.7) * 43758.5453;
  const raw = x - Math.floor(x); // 0..1
  return 0.12 + raw * 0.88; // map to 0.12..1.0
}

function DmaGrid({ dmaData }: { dmaData: { dma: string; spend: number; cpihh: number }[] | null }) {
  const cols = 14;

  // When API data is available, use it for the heatmap cells
  if (dmaData && dmaData.length > 0) {
    const maxSpend = Math.max(...dmaData.map((d) => d.spend));
    const total = dmaData.length;

    return (
      <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.05s" }}>
        <SectionHeader title="DMA Performance Grid" meta={`${total} MARKETS · SPEND HEAT`} />

        <div
          className="grid gap-[3px] mt-4"
          style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
        >
          {dmaData.map((d, i) => {
            const opacity = maxSpend > 0 ? 0.12 + (d.spend / maxSpend) * 0.88 : 0.12;
            return (
              <div
                key={i}
                className="aspect-square rounded-[3px] transition-opacity hover:opacity-100"
                style={{
                  background: `color-mix(in srgb, var(--cyan) ${(opacity * 100).toFixed(0)}%, transparent)`,
                }}
                title={`${d.dma} — Spend $${(d.spend / 1000).toFixed(0)}K · CPIHH $${d.cpihh.toFixed(0)}`}
              />
            );
          })}
        </div>

        {/* Legend */}
        <div className="flex items-center gap-2 mt-3">
          <span className="font-mono text-[9px] tracking-[.1em] text-fg3">LOW</span>
          <div className="flex-1 h-[5px] rounded-[3px]"
            style={{
              background: "linear-gradient(90deg, var(--cyan-hover), var(--cyan))",
            }}
          />
          <span className="font-mono text-[9px] tracking-[.1em] text-fg3">HIGH</span>
        </div>
      </Card>
    );
  }

  // Fallback: original deterministic mock grid
  const total = 70;

  return (
    <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.05s" }}>
      <SectionHeader title="DMA Performance Grid" meta="70 MARKETS · ROAS HEAT" />

      <div
        className="grid gap-[3px] mt-4"
        style={{ gridTemplateColumns: `repeat(${cols}, 1fr)` }}
      >
        {Array.from({ length: total }, (_, i) => {
          const opacity = seededOpacity(i);
          return (
            <div
              key={i}
              className="aspect-square rounded-[3px] transition-opacity hover:opacity-100"
              style={{
                background: `color-mix(in srgb, var(--cyan) ${(opacity * 100).toFixed(0)}%, transparent)`,
              }}
              title={`DMA ${500 + i} — ROAS ${(2 + opacity * 4).toFixed(1)}×`}
            />
          );
        })}
      </div>

      {/* Legend */}
      <div className="flex items-center gap-2 mt-3">
        <span className="font-mono text-[9px] tracking-[.1em] text-fg3">LOW</span>
        <div className="flex-1 h-[5px] rounded-[3px]"
          style={{
            background: "linear-gradient(90deg, var(--cyan-hover), var(--cyan))",
          }}
        />
        <span className="font-mono text-[9px] tracking-[.1em] text-fg3">HIGH</span>
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Top Markets ranked list                                            */
/* ------------------------------------------------------------------ */

function TopMarkets({ markets, totalCount }: { markets: { rank: number; name: string; code: string; roas: number; funded: number }[]; totalCount: number }) {
  return (
    <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.1s" }}>
      <SectionHeader title="Top Markets" meta={`${markets.length} OF ${totalCount} · BY ROAS`} />

      <div className="flex flex-col mt-3">
        {markets.map((m, i) => (
          <div
            key={m.rank}
            className={`flex items-center gap-3 py-[10px] ${
              i < markets.length - 1 ? "border-b border-line" : ""
            } hover:bg-panel2 transition-colors px-2 rounded-[6px]`}
          >
            {/* Rank */}
            <span className="font-mono text-[18px] font-semibold text-cyan w-[28px]">
              {String(m.rank).padStart(2, "0")}
            </span>

            {/* Name + code */}
            <div className="flex-1 min-w-0">
              <div className="text-[13px] font-medium">{m.name}</div>
              <div className="font-mono text-[9px] tracking-[.08em] text-fg3">{m.code}</div>
            </div>

            {/* ROAS */}
            <span className="font-mono text-[12px] font-medium text-positive bg-[rgba(79,216,155,.14)] px-2 py-0.5 rounded-[5px]">
              {m.roas.toFixed(1)}&times;
            </span>

            {/* Funded */}
            <span className="font-mono text-[10px] text-fg3 w-[90px] text-right">
              {m.funded.toLocaleString()} funded
            </span>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ------------------------------------------------------------------ */
/*  Audience Segment Card                                              */
/* ------------------------------------------------------------------ */

const SegmentCard = memo(function SegmentCard({
  segment,
  delay,
}: {
  segment: AudienceSegment;
  delay: number;
}) {
  const sharePct = Math.round(segment.share * 100);

  return (
    <Card
      className="flex flex-col p-4 animate-rise hover:border-line-strong transition-colors"
      style={{ animationDelay: `${delay}s` }}
    >
      {/* Header */}
      <div className="flex items-center justify-between">
        <span className="text-[14px] font-semibold">{segment.name}</span>
        <span
          className="font-mono text-[8.5px] tracking-[.08em] px-2 py-0.5 rounded-[5px]"
          style={{
            color: segment.tag_color,
            background:
              segment.tag_color === "var(--green)"
                ? "rgba(79,216,155,.14)"
                : segment.tag_color === "var(--cyan)"
                ? "var(--cyan-hover)"
                : segment.tag_color === "var(--amber)"
                ? "rgba(242,177,76,.14)"
                : "rgba(164,173,191,.14)",
          }}
        >
          {segment.tag}
        </span>
      </div>

      {/* Share */}
      <div className="flex items-baseline gap-1.5 mt-3">
        <span className="text-[28px] font-semibold tracking-[-0.02em]">
          {sharePct}%
        </span>
        <span className="font-mono text-[9.5px] tracking-[.1em] text-fg3">SHARE</span>
      </div>

      {/* Share bar */}
      <div className="h-[5px] rounded-[3px] bg-line mt-2 overflow-hidden">
        <div
          className="h-full rounded-[3px]"
          style={{
            width: `${sharePct}%`,
            background: segment.tag_color,
            opacity: 0.7,
          }}
        />
      </div>

      {/* Note */}
      <div className="font-mono text-[10px] text-fg3 mt-3 leading-[1.4]">
        {segment.note}
      </div>
    </Card>
  );
});

/* ------------------------------------------------------------------ */
/*  Main Audience component                                            */
/* ------------------------------------------------------------------ */

export function Audience() {
  const { filters } = useShell();

  // ---- BFF hook calls (filters drive server-side filtering) ----
  const dmaQuery = useSpendDMA(filters);
  const marketsQuery = useTopMarkets(filters);
  const segmentsQuery = useAudienceSegments(filters);

  return (
    <div className="flex flex-col gap-4">
      {/* ===== Top row: DMA Grid + Top Markets ===== */}
      <DataGuard
        {...dmaQuery}
        skeleton={
          <div className="grid gap-4" style={{ gridTemplateColumns: "1.5fr 1fr" }}>
            <Skeleton rows={6} className="rounded-card border border-line bg-panel p-5" />
            <Skeleton rows={6} className="rounded-card border border-line bg-panel p-5" />
          </div>
        }
        emptyHeadline="No DMA data"
        emptyBody="DMA performance data is not available for the selected filters."
      >
        {(dmaData) => (
          <div className="grid gap-4" style={{ gridTemplateColumns: "1.5fr 1fr" }}>
            <DmaGrid dmaData={dmaData} />
            <DataGuard
              {...marketsQuery}
              skeleton={<Skeleton rows={6} className="rounded-card border border-line bg-panel p-5" />}
              emptyHeadline="No market data"
              emptyBody="Top market data is not available for the selected filters."
            >
              {(marketsData) => (
                <TopMarkets markets={marketsData.markets} totalCount={marketsData.count} />
              )}
            </DataGuard>
          </div>
        )}
      </DataGuard>

      {/* ===== Audience Segments ===== */}
      <section>
        <div className="mb-3">
          <SectionHeader title="Audience Segments" meta="ACQUISITION MIX" />
        </div>

        <DataGuard
          {...segmentsQuery}
          skeleton={
            <div className="grid grid-cols-4 gap-[14px]">
              {Array.from({ length: 4 }, (_, i) => (
                <Skeleton key={i} rows={4} className="rounded-card border border-line bg-panel p-4" />
              ))}
            </div>
          }
          emptyHeadline="No segment data"
          emptyBody="Audience segment data is not available for the selected filters."
        >
          {(segData) => (
            <div className="grid grid-cols-4 gap-[14px]">
              {segData.segments.map((seg, i) => (
                <SegmentCard key={seg.name} segment={seg} delay={0.2 + i * 0.05} />
              ))}
            </div>
          )}
        </DataGuard>
      </section>
    </div>
  );
}
