import { CardContainer } from "./primitives";

export function StubPage({ title, blurb, components }: { title: string; blurb: string; components: string[] }) {
  return (
    <div className="mx-auto max-w-3xl">
      <CardContainer title={title} subtitle="Specified — slated for the next build phase">
        <p className="text-sm text-fg-2">{blurb}</p>
        <div className="mt-4">
          <div className="mb-2 text-[11px] uppercase tracking-[0.06em] text-fg-muted">Feature components (per screen spec)</div>
          <div className="flex flex-wrap gap-2">
            {components.map((c) => (
              <span key={c} className="rounded-pill border border-line bg-elevated px-2.5 py-1 text-[11px] text-fg-2">{c}</span>
            ))}
          </div>
        </div>
      </CardContainer>
    </div>
  );
}
