"use client";
import { useState } from "react";
import { useQuery } from "@/lib/hooks";
import { getLaunch } from "@/lib/bff-extended";
import { CardContainer, Button, Skeleton, ErrorState, StatusPill } from "@/components/primitives";
import { DataTable } from "@/components/charts";

export default function LaunchPage() {
  const { data, loading, error, reload } = useQuery(["launch"], getLaunch);
  const [stage, setStage] = useState("proof");
  const [launched, setLaunched] = useState(false);

  if (error) return <ErrorState message="Couldn't load the launch pipeline." onRetry={reload} />;

  const tone = (r: "pass" | "warn" | "fail") => (r === "pass" ? "positive" : r === "warn" ? "warning" : "critical");

  return (
    <div className="flex flex-col gap-4">
      <p className="text-sm text-fg-2">
        Operator-paced launch pipeline — each stage runs then waits at a human gate. First-party pages only (Member FDIC / EHL, real offer T&Cs; no affiliate or competitor comparisons).
      </p>

      {/* Stage rail */}
      <CardContainer>
        {loading ? <Skeleton className="h-12" /> : (
          <div className="flex flex-wrap gap-1.5">
            {data!.stages.map((s) => (
              <button
                key={s.key} onClick={() => setStage(s.key)} aria-current={stage === s.key}
                className={`rounded-pill border px-2.5 py-1 text-[11.5px] font-medium transition-colors ${
                  stage === s.key ? "border-accent bg-accent text-accent-ink"
                  : s.state === "done" ? "border-line bg-[color-mix(in_oklab,var(--color-positive)_12%,transparent)] text-positive"
                  : s.state === "active" ? "border-line-strong bg-elevated text-fg"
                  : "border-line bg-elevated text-fg-muted"
                }`}
              >
                {s.label}{s.gate ? " ⚑" : ""}
              </button>
            ))}
          </div>
        )}
      </CardContainer>

      {!loading && (
        <>
          {/* Delivery board */}
          {stage === "jira" && (
            <CardContainer title="Delivery board" subtitle="Move tickets Backlog → Done to unlock proofing (gate)">
              <div className="grid grid-cols-4 gap-3">
                {(["Backlog", "In Progress", "In Review", "Done"] as const).map((lane) => (
                  <div key={lane} className="rounded-md border border-line bg-raised p-2.5">
                    <div className="mb-2 text-[10.5px] uppercase tracking-[0.06em] text-fg-2">{lane}</div>
                    {data!.tickets.filter((t) => t.lane === lane).map((t) => (
                      <div key={t.id} className="mb-2 rounded border border-line bg-surface px-2 py-1.5 text-[12px] text-fg">
                        <span className="num text-fg-muted">{t.id}</span> {t.title}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            </CardContainer>
          )}

          {/* Recommendations (Lens) */}
          {(stage === "lens" || stage === "recs") && (
            <CardContainer title="Lens recommendations" subtitle="Persona → first-party Momentum offer plan">
              <div className="grid grid-cols-2 gap-3 sm:grid-cols-5">
                {data!.recommendations.map((r) => (
                  <div key={r.label} className="rounded-md border border-line bg-raised p-3">
                    <div className="text-[10px] uppercase tracking-[0.06em] text-fg-2">{r.label}</div>
                    <div className="num mt-1 text-[15px] font-semibold text-fg">{r.value}</div>
                  </div>
                ))}
              </div>
            </CardContainer>
          )}

          {/* Compliance */}
          {stage === "compliance" && (
            <CardContainer title="Compliance scan" subtitle="Agentic — one assertion at a time, with evidence">
              <DataTable
                columns={[
                  { key: "assertion", label: "Assertion" },
                  { key: "result", label: "Result", render: (r) => <StatusPill tone={tone(r.result)}>{r.result}</StatusPill> },
                  { key: "evidence", label: "Evidence" },
                ]}
                rows={data!.compliance}
              />
            </CardContainer>
          )}

          {/* QA */}
          {stage === "qa" && (
            <CardContainer title="QA scan" subtitle="Lighthouse-ish + offer reconcile + link/schema crawl">
              <DataTable
                columns={[
                  { key: "assertion", label: "Check" },
                  { key: "result", label: "Result", render: (r) => <StatusPill tone={tone(r.result)}>{r.result}</StatusPill> },
                  { key: "evidence", label: "Evidence" },
                ]}
                rows={data!.qa}
              />
            </CardContainer>
          )}

          {/* A/B + Launch */}
          {(stage === "ab" || stage === "launch" || stage === "approve") && (
            <CardContainer title="A/B Test Setup" subtitle="Two-proportion z-test on a seeded funnel sim">
              <div className="flex flex-wrap items-center gap-6">
                <div><div className="text-[10px] uppercase text-fg-2">Metric</div><div className="text-[14px] text-fg">{data!.experiment.metric}</div></div>
                <div><div className="text-[10px] uppercase text-fg-2">Variant A</div><div className="num text-[14px] text-fg">{data!.experiment.variantA}%</div></div>
                <div><div className="text-[10px] uppercase text-fg-2">Variant B</div><div className="num text-[14px] text-positive">{data!.experiment.variantB}%</div></div>
                <div><div className="text-[10px] uppercase text-fg-2">Lift</div><div className="num text-[14px] text-positive">{data!.experiment.lift}</div></div>
                <div><div className="text-[10px] uppercase text-fg-2">Confidence</div>
                  <div className="num text-[14px]"><StatusPill tone={data!.experiment.powered ? "positive" : "warning"}>{data!.experiment.confidence}{data!.experiment.powered ? "" : " · underpowered"}</StatusPill></div>
                </div>
              </div>
              <div className="mt-4 flex items-center gap-3">
                {launched ? <StatusPill tone="positive">✓ launched · first-party · registered</StatusPill> : (
                  <>
                    <Button variant="primary" onClick={() => setLaunched(true)}>Approve &amp; launch</Button>
                    <span className="text-xs text-fg-muted">Human launch gate · performance feeds back into Lens for the next persona.</span>
                  </>
                )}
              </div>
            </CardContainer>
          )}

          {/* default: proofing / factory / preview placeholder */}
          {!["jira", "lens", "recs", "compliance", "qa", "ab", "launch", "approve"].includes(stage) && (
            <CardContainer title={data!.stages.find((s) => s.key === stage)?.label} subtitle="Stage workspace">
              <p className="text-sm text-fg-2">
                {stage === "proof" && "Review the rendered creative with markup pins + comment thread; Request changes triggers a real revise-to-v2 loop. Approve to continue."}
                {stage === "factory" && "Author copy, then build the multi-page site to real static HTML (routes, JSON-LD, disclosures, calculator, sitemap)."}
                {stage === "preview" && "The built site is served at a live local URL and previewed in an iframe."}
              </p>
            </CardContainer>
          )}
        </>
      )}
    </div>
  );
}
