import { memo } from "react";
import { Card, SectionHeader, DataGuard } from "../ui";
import { useCreativeOverview, useCreativeThemes } from "../api/hooks";
import type { CreativeAsset, MessageTheme } from "../api/hooks";
import { useShell } from "../shell/ShellProvider";

/* ------------------------------------------------------------------ */
/*  BFF integration — all data from live hooks, no mock fallbacks      */
/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

const fmtPct = (n: number): string => `${(n * 100).toFixed(1)}%`;

const fmtCurrency = (n: number): string => {
  if (Math.abs(n) >= 1_000_000) return `$${(n / 1_000_000).toFixed(1)}M`;
  if (Math.abs(n) >= 1_000) return `$${(n / 1_000).toFixed(0)}K`;
  return `$${Math.round(n)}`;
};

const fatigueColor = (f: string): string => {
  switch (f) {
    case "FRESH": return "var(--green)";
    case "WATCH": return "var(--amber)";
    case "TIRED": return "var(--red)";
    default: return "var(--text3)";
  }
};

/* ------------------------------------------------------------------ */
/*  Creative Card sub-component                                        */
/* ------------------------------------------------------------------ */

const CreativeCard = memo(function CreativeCard({
  card,
  delay,
}: {
  card: CreativeAsset;
  delay: number;
}) {
  return (
    <Card
      className="flex flex-col overflow-hidden animate-rise hover:border-line-strong transition-colors"
      style={{ animationDelay: `${delay}s` }}
    >
      {/* Thumbnail */}
      <div
        className="h-[100px] relative"
        style={{ background: card.thumb_gradient }}
      >
        {/* Format badge */}
        <span className="absolute top-2.5 left-2.5 font-mono text-[8.5px] tracking-[.08em] px-2 py-1 rounded-[5px] bg-[rgba(0,0,0,.55)] text-fg backdrop-blur-sm">
          {card.format}
        </span>

        {/* Fatigue indicator */}
        <span
          className="absolute top-2.5 right-2.5 font-mono text-[8.5px] tracking-[.08em] px-2 py-1 rounded-[5px]"
          style={{
            color: fatigueColor(card.fatigue),
            background: "rgba(0,0,0,.55)",
            backdropFilter: "blur(4px)",
          }}
        >
          {card.fatigue}
        </span>
      </div>

      {/* Content */}
      <div className="flex flex-col gap-2 p-3.5">
        {/* Title + theme */}
        <div>
          <div className="text-[13px] font-semibold leading-tight">{card.name}</div>
          <div className="font-mono text-[9.5px] tracking-[.06em] text-fg3 mt-0.5">
            {card.theme}
          </div>
        </div>

        {/* Metrics row */}
        <div className="flex items-center gap-3 mt-1">
          <div className="flex flex-col">
            <span className="font-mono text-[9px] tracking-[.1em] text-fg3">CTR</span>
            <span className="font-mono text-[13px] font-medium">{fmtPct(card.ctr)}</span>
          </div>
          <div className="w-px h-[22px] bg-line" />
          <div className="flex flex-col">
            <span className="font-mono text-[9px] tracking-[.1em] text-fg3">CVR</span>
            <span className="font-mono text-[13px] font-medium">{fmtPct(card.cvr)}</span>
          </div>
          <div className="w-px h-[22px] bg-line" />
          <div className="flex flex-col">
            <span className="font-mono text-[9px] tracking-[.1em] text-fg3">SPEND</span>
            <span className="font-mono text-[13px] font-medium">{fmtCurrency(card.spend)}</span>
          </div>
        </div>
      </div>
    </Card>
  );
});

/* ------------------------------------------------------------------ */
/*  Message Theme Resonance chart                                      */
/* ------------------------------------------------------------------ */

function ThemeResonanceContent({ themes }: { themes: MessageTheme[] }) {
  const maxPct = 100;

  return (
    <div className="flex flex-col gap-3 mt-4">
      {themes.map((theme) => (
        <div key={theme.name} className="flex items-center gap-3">
          {/* Label */}
          <span className="flex-none w-[160px] text-[12px] text-fg2 truncate">
            {theme.name}
          </span>

          {/* Bar */}
          <div className="flex-1 h-[8px] rounded-[4px] bg-line overflow-hidden">
            <div
              className="h-full rounded-[4px] bg-cyan transition-all duration-500"
              style={{
                width: `${(theme.score / maxPct) * 100}%`,
                opacity: 0.3 + (theme.score / maxPct) * 0.7,
              }}
            />
          </div>

          {/* Score */}
          <span className="flex-none w-[36px] font-mono text-[12px] font-medium text-right">
            {theme.score}
          </span>
        </div>
      ))}
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Main Creative component                                            */
/* ------------------------------------------------------------------ */

export function Creative() {
  const { filters } = useShell();
  const overview = useCreativeOverview(filters);
  const themes = useCreativeThemes(filters);

  return (
    <div className="flex flex-col gap-4">
      {/* ===== Top Creative Units ===== */}
      <section className="animate-rise" style={{ animationDelay: "0.05s" }}>
        <div className="flex items-center justify-between mb-3">
          <SectionHeader title="Top Creative Units" meta="BY CTR · LAST 30 DAYS" />
        </div>

        <DataGuard
          data={overview.data}
          loading={overview.loading}
          error={overview.error}
          reload={overview.reload}
        >
          {(data) => (
            <div className="grid grid-cols-3 gap-[14px]">
              {data.assets.map(
                (card, i) => (
                  <CreativeCard key={card.name} card={card} delay={0.08 + i * 0.05} />
                ),
              )}
            </div>
          )}
        </DataGuard>
      </section>

      {/* ===== Message Theme Resonance ===== */}
      <Card className="p-[18px] animate-rise" style={{ animationDelay: "0.3s" }}>
        <SectionHeader title="Message Theme Resonance" meta="RESONANCE INDEX" />

        <DataGuard
          data={themes.data}
          loading={themes.loading}
          error={themes.error}
          reload={themes.reload}
        >
          {(data) => (
            <ThemeResonanceContent
              themes={data.themes}
            />
          )}
        </DataGuard>
      </Card>
    </div>
  );
}
