"use client";
import { useState } from "react";
import { useQuery } from "@/lib/hooks";
import { getDirectives, Directive, DirectiveStatus } from "@/lib/bff";
import { CardContainer, Button, Skeleton, ErrorState, EmptyState, StatusPill } from "@/components/primitives";
import { DiffView, MissionTracker } from "@/components/directive";

const STEPS = ["Build", "Review", "Submit", "Approve", "Executed"];

export default function ApprovalsPage() {
  const { data, loading, error, reload } = useQuery(["directives"], getDirectives);
  const [overrides, setOverrides] = useState<Record<string, DirectiveStatus>>({});
  const [celebrating, setCelebrating] = useState<string | null>(null);
  const [confirming, setConfirming] = useState<string | null>(null); // high-impact confirm step
  const [announce, setAnnounce] = useState("");
  const [undo, setUndo] = useState<{ id: string; prev: DirectiveStatus } | null>(null);

  const statusOf = (d: Directive): DirectiveStatus => overrides[d.id] ?? d.status;

  const approve = (d: Directive) => {
    setConfirming(null);
    setOverrides((o) => ({ ...o, [d.id]: "approved" }));
    setCelebrating(d.id);
    setAnnounce(`Directive approved: ${d.title}. Executing.`);
    setTimeout(() => {
      setOverrides((o) => ({ ...o, [d.id]: "executed" }));
      setCelebrating(null);
      setAnnounce(`Directive executed and audit-logged: ${d.title}.`);
    }, 750);
  };

  const reject = (d: Directive) => {
    setOverrides((o) => ({ ...o, [d.id]: "rejected" }));
    setUndo({ id: d.id, prev: "pending" });
    setAnnounce(`Directive rejected: ${d.title}.`);
    setTimeout(() => setUndo((u) => (u?.id === d.id ? null : u)), 5000);
  };

  const onApproveClick = (d: Directive) => {
    if (d.impact === "high" && confirming !== d.id) {
      setConfirming(d.id); // require explicit confirm for high-impact
    } else {
      approve(d);
    }
  };

  const pending = (data ?? []).filter((d) => statusOf(d) === "pending");

  return (
    <div className="mx-auto max-w-3xl">
      <p className="mb-4 text-sm text-fg-2">
        Human-in-the-loop queue. Agents propose; you confirm. Nothing reaches a live account until approved — every decision is audit-logged.
      </p>

      {/* SR-only live region for decisions */}
      <p className="sr-only" role="status" aria-live="polite">{announce}</p>

      {/* Undo toast */}
      {undo && (
        <div className="mb-4 flex items-center justify-between rounded-md border border-line bg-elevated px-4 py-2.5 text-sm">
          <span className="text-fg-2">Directive rejected.</span>
          <button
            className="font-semibold text-accent"
            onClick={() => { setOverrides((o) => ({ ...o, [undo.id]: undo.prev })); setUndo(null); setAnnounce("Reject undone."); }}
          >
            Undo
          </button>
        </div>
      )}

      {error && <ErrorState message="Couldn't load the approval queue." onRetry={reload} />}
      {loading && <div className="flex flex-col gap-4"><Skeleton className="h-56" /><Skeleton className="h-56" /></div>}

      {!loading && !error && pending.length === 0 && !Object.keys(overrides).length && (
        <EmptyState message="Queue clear — no directives awaiting approval." hint="Proposed account changes will appear here for review." />
      )}

      <div className="flex flex-col gap-4">
        {data?.map((d) => {
          const status = statusOf(d);
          const done = status === "executed";
          const rejected = status === "rejected";
          return (
            <CardContainer
              key={d.id}
              className={`relative overflow-hidden ${rejected ? "opacity-60" : ""} ${celebrating === d.id ? "after:absolute after:inset-0 after:animate-[sweep_.7s_cubic-bezier(.2,0,0,1)_forwards] after:bg-gradient-to-r after:from-transparent after:via-[color-mix(in_oklab,var(--color-positive)_35%,transparent)] after:to-transparent" : ""}`}
              right={d.impact === "high" ? <StatusPill tone="warning">high impact</StatusPill> : <StatusPill tone="muted">low impact</StatusPill>}
              title={d.title}
              subtitle={`${d.type} · ${d.rationale}`}
            >
              <DiffView before={d.before} after={d.after} />
              <div className="mt-4"><MissionTracker steps={STEPS} current={done ? 5 : rejected ? 3 : 3} /></div>

              <div className="mt-4 flex items-center gap-2">
                {done ? (
                  <StatusPill tone="positive">✓ executed · audit-logged</StatusPill>
                ) : rejected ? (
                  <StatusPill tone="critical">✕ rejected · audit-logged</StatusPill>
                ) : confirming === d.id ? (
                  <>
                    <span className="text-[12.5px] text-warning">Confirm: this changes a live account.</span>
                    <Button variant="primary" onClick={() => approve(d)}>Confirm {d.title.split(" ")[0].toLowerCase()}</Button>
                    <Button variant="ghost" onClick={() => setConfirming(null)}>Cancel</Button>
                  </>
                ) : (
                  <>
                    <Button variant="primary" onClick={() => onApproveClick(d)}>Approve</Button>
                    <Button variant="ghost" onClick={() => onApproveClick(d)}>Edit &amp; approve</Button>
                    <Button variant="danger" onClick={() => reject(d)}>Reject</Button>
                  </>
                )}
              </div>
            </CardContainer>
          );
        })}
      </div>
    </div>
  );
}
