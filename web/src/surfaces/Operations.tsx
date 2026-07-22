import { useState, useCallback, memo } from "react";
import { Card, SectionHeader, Pill, DataGuard, Skeleton } from "../ui";
import { useApprovals, useOpsCalendar, useOpsCapacity, useCompetitiveFeed } from "../api/hooks";
import { apiFetch } from "../api/client";
import { useShell } from "../shell/ShellProvider";
import type { ApprovalItem, CalendarEvent, CapacityItem, CompetitiveFeedItem } from "../api/types";

/* ------------------------------------------------------------------ */
/*  Mock data                                                          */
/* ------------------------------------------------------------------ */

interface QueueItem {
  id: string;
  tool: string;
  conf: string;
  status: string;
  statusColor: string;
  title: string;
  risk: string;
  why: string;
  impact: string;
  eta: string;
  toolSteps: string[];
}

const QUEUE_ITEMS: QueueItem[] = [
  {
    id: "d1", tool: "SPEND_OPTIMIZER", conf: "94%", status: "PENDING",
    statusColor: "var(--amber)", title: "Reallocate $120K from Social → SEM in DMA 602",
    risk: "LOW",
    why: "SEM CPA in DMA 602 dropped 18% this week while Social fatigue metrics crossed threshold. Reallocation projects +340 incremental funded accounts at current conversion rates.",
    impact: "+340 funded HH · −$18 CPIHH · +0.4× ROAS",
    eta: "4 min",
    toolSteps: [
      "query_metrics(dma=602, channel=[sem,social])",
      "simulate_realloc(from=social, to=sem, amt=120000)",
      "propose_action(type=budget_move, requires_approval=true)",
    ],
  },
  {
    id: "d2", tool: "CREATIVE_ROTATOR", conf: "87%", status: "PENDING",
    statusColor: "var(--amber)", title: "Pause 'Community Roots' static — fatigue score critical",
    risk: "LOW",
    why: "CTR has declined 42% over 7 days. Fatigue model predicts continued degradation. Replacement creative 'Smart Savings' is tested and ready.",
    impact: "Prevent est. $45K wasted spend over next 2 weeks",
    eta: "2 min",
    toolSteps: [
      "analyze_creative(id=community_roots)",
      "check_replacement_ready(queue=approved)",
      "propose_action(type=creative_pause)",
    ],
  },
  {
    id: "d3", tool: "GEO_OPTIMIZER", conf: "78%", status: "REVIEW",
    statusColor: "var(--cyan)", title: "Increase Cincinnati DMA budget by 15%",
    risk: "MEDIUM",
    why: "Cincinnati ROAS is 5.2× vs portfolio avg 3.8×. Saturation model shows runway for 15% budget increase before diminishing returns.",
    impact: "+$180K spend · est. +520 funded HH",
    eta: "6 min",
    toolSteps: [
      "query_saturation(dma=515)",
      "simulate_budget_change(dma=515, delta=+15%)",
      "check_constraints(total_budget, channel_caps)",
    ],
  },
  {
    id: "d4", tool: "RETENTION_ALERT", conf: "91%", status: "APPROVED",
    statusColor: "var(--green)", title: "Trigger re-engagement campaign for MOB-3 churn risk",
    risk: "LOW",
    why: "Retention model flagged 1,240 accounts at >60% churn probability. Email re-engagement sequence has 34% historical save rate.",
    impact: "Est. 420 accounts retained · $1.76M preserved LTV",
    eta: "3 min",
    toolSteps: [
      "identify_churn_risk(mob=3, threshold=0.6)",
      "select_campaign(type=reengagement)",
      "queue_send(channel=email, segment=churn_risk)",
    ],
  },
];

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function statusVariant(status: string): "amber" | "cyan" | "green" | "neutral" {
  if (status === "PENDING") return "amber";
  if (status === "REVIEW") return "cyan";
  if (status === "APPROVED") return "green";
  return "neutral";
}

function riskVariant(risk: string): "green" | "amber" | "red" {
  if (risk === "LOW") return "green";
  if (risk === "MEDIUM") return "amber";
  return "red";
}

function impactVariant(impact: string): "red" | "amber" | "green" {
  if (impact === "high") return "red";
  if (impact === "medium") return "amber";
  return "green";
}

function eventStatusVariant(status: string): "green" | "amber" | "cyan" | "neutral" {
  const s = status.toLowerCase();
  if (s === "confirmed" || s === "live") return "green";
  if (s === "pending" || s === "draft") return "amber";
  if (s === "in_review" || s === "review") return "cyan";
  return "neutral";
}

/* ------------------------------------------------------------------ */
/*  Sub-components: Approval Queue                                     */
/* ------------------------------------------------------------------ */

const QueueRow = memo(function QueueRow({
  item,
  selected,
  onClick,
  index,
}: {
  item: QueueItem;
  selected: boolean;
  onClick: () => void;
  index: number;
}) {
  return (
    <button
      onClick={onClick}
      className={`
        w-full text-left flex flex-col gap-2 px-[18px] py-[14px] border-b border-line
        transition-colors animate-wirein cursor-pointer
        ${selected
          ? "bg-[var(--cyan-subtle)] border-l-2 border-l-cyan"
          : "hover:bg-panel2 border-l-2 border-l-transparent"
        }
      `}
      style={{ animationDelay: `${0.08 + index * 0.05}s` }}
    >
      {/* Top row: tool + confidence + status */}
      <div className="flex items-center gap-2 flex-wrap">
        <Pill variant="cyan">{item.tool}</Pill>
        <span className="font-mono text-[10px] font-medium text-fg2">
          {item.conf}
        </span>
        <Pill variant={statusVariant(item.status)} dot>{item.status}</Pill>
      </div>

      {/* Title */}
      <span className="text-[12.5px] font-medium leading-snug text-fg">
        {item.title}
      </span>
    </button>
  );
});

function DirectiveDetail({
  item,
  onApprove,
  onReject,
  onDefer,
  actionLoading,
}: {
  item: QueueItem;
  onApprove: (id: string) => void;
  onReject: (id: string) => void;
  onDefer: (id: string) => void;
  actionLoading: string | null;
}) {
  const isBusy = actionLoading === item.id;
  return (
    <div className="flex flex-col gap-5 animate-rise" style={{ animationDelay: "0.05s" }}>
      {/* Header row */}
      <div className="flex items-center gap-3 flex-wrap">
        <Pill variant="cyan">{item.tool}</Pill>
        <span className="font-mono text-[11px] font-medium text-fg2">
          CONFIDENCE {item.conf}
        </span>
        <Pill variant={riskVariant(item.risk)} dot>{item.risk} RISK</Pill>
      </div>

      {/* Title */}
      <h2 className="text-[20px] font-semibold leading-snug tracking-[-0.01em]">
        {item.title}
      </h2>

      {/* Agent Rationale */}
      <div>
        <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
          AGENT RATIONALE
        </span>
        <p className="text-[13px] leading-relaxed text-fg2 mt-2">{item.why}</p>
      </div>

      {/* Projected Impact */}
      <Card accent glow className="p-4">
        <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
          PROJECTED IMPACT
        </span>
        <div className="text-[15px] font-semibold mt-2 text-cyan">{item.impact}</div>
        <div className="font-mono text-[10px] text-fg3 mt-1">
          ETA: {item.eta}
        </div>
      </Card>

      {/* Tool Chain */}
      <Card className="p-4">
        <span className="font-mono text-[9.5px] tracking-[.12em] text-fg3">
          TOOL CHAIN
        </span>
        <div className="flex flex-col gap-2 mt-3">
          {item.toolSteps.map((step, i) => (
            <div key={i} className="flex items-center gap-2.5">
              <span
                className="flex-none w-[18px] h-[18px] rounded-full bg-panel2 border border-line flex items-center justify-center font-mono text-[9px] text-fg3"
              >
                {i + 1}
              </span>
              <code className="font-mono text-[11px] text-fg2">{step}</code>
            </div>
          ))}
        </div>
      </Card>

      {/* Action Buttons */}
      <div className="flex items-center gap-3 pt-2 flex-wrap">
        <button
          onClick={() => onApprove(item.id)}
          disabled={isBusy}
          className="px-5 py-2.5 rounded-pill bg-cyan text-cyan-ink font-mono text-[11px] font-semibold tracking-[.06em] hover:brightness-110 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-wait"
          style={{ boxShadow: "0 0 14px var(--cyan-glow)" }}
        >
          {isBusy ? "EXECUTING…" : "APPROVE & EXECUTE"}
        </button>
        <button
          onClick={() => onReject(item.id)}
          disabled={isBusy}
          className="px-5 py-2.5 rounded-pill border border-line bg-transparent text-fg2 font-mono text-[11px] font-semibold tracking-[.06em] hover:border-critical hover:text-critical transition-colors cursor-pointer disabled:opacity-50 disabled:cursor-wait"
        >
          REJECT
        </button>
        <button
          onClick={() => onDefer(item.id)}
          disabled={isBusy}
          className="px-5 py-2.5 rounded-pill border border-line bg-transparent text-fg3 font-mono text-[11px] font-semibold tracking-[.06em] hover:border-line-strong hover:text-fg2 transition-colors cursor-pointer disabled:opacity-50"
        >
          DEFER
        </button>
      </div>
    </div>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-components: Launch Calendar                                     */
/* ------------------------------------------------------------------ */

function LaunchCalendarSection({ events }: { events: CalendarEvent[] }) {
  return (
    <section
      className="rounded-card border border-line bg-panel overflow-hidden animate-rise"
      style={{ animationDelay: "0.15s" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-[18px] py-[15px] border-b border-line">
        <SectionHeader title="Launch Calendar" accent="cyan" />
        <Pill variant="cyan">{events.length} EVENTS</Pill>
      </div>

      {/* Column headers */}
      <div className="grid grid-cols-[1fr_100px_100px_90px_90px] gap-2 px-[18px] py-[9px] border-b border-line font-mono text-[9px] tracking-[.1em] text-fg3">
        <span>EVENT</span>
        <span>TYPE</span>
        <span>CHANNEL</span>
        <span>DATE</span>
        <span className="text-right">STATUS</span>
      </div>

      {/* Rows */}
      <div className="max-h-[280px] overflow-y-auto">
        {events.map((event) => (
          <div
            key={event.id}
            className="grid grid-cols-[1fr_100px_100px_90px_90px] gap-2 items-center px-[18px] py-3 border-b border-line hover:bg-panel2 transition-colors"
          >
            <div className="flex flex-col gap-0.5 min-w-0">
              <span className="text-[12.5px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">
                {event.title}
              </span>
              <span className="font-mono text-[9px] text-fg3 whitespace-nowrap overflow-hidden text-ellipsis">
                {event.owner}
              </span>
            </div>
            <span className="font-mono text-[10px] text-fg2 capitalize">
              {event.event_type.replace(/_/g, " ")}
            </span>
            <span className="font-mono text-[10px] text-fg2 capitalize">
              {event.channel.replace(/_/g, " ")}
            </span>
            <span className="font-mono text-[10px] text-fg3">
              {event.date}
            </span>
            <div className="flex justify-end">
              <Pill variant={eventStatusVariant(event.status)} dot>
                {event.status.toUpperCase().replace(/_/g, " ")}
              </Pill>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-components: Team Capacity                                      */
/* ------------------------------------------------------------------ */

function TeamCapacitySection({
  members,
  summary,
}: {
  members: CapacityItem[];
  summary: { total: number; total_allocated_hours: number; total_used_hours: number; avg_utilization_pct: number };
}) {
  return (
    <section
      className="rounded-card border border-line bg-panel overflow-hidden animate-rise"
      style={{ animationDelay: "0.2s" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-[18px] py-[15px] border-b border-line">
        <SectionHeader title="Team Capacity" accent="green" />
        <div className="flex items-center gap-3">
          <span className="font-mono text-[9.5px] tracking-[.1em] text-fg3">
            AVG UTIL
          </span>
          <span className={`font-mono text-[12px] font-semibold ${
            summary.avg_utilization_pct > 90 ? "text-critical" : summary.avg_utilization_pct > 75 ? "text-warning" : "text-positive"
          }`}>
            {summary.avg_utilization_pct.toFixed(0)}%
          </span>
        </div>
      </div>

      {/* Capacity bars */}
      <div className="flex flex-col gap-0 max-h-[320px] overflow-y-auto">
        {members.map((member) => {
          const pct = member.utilization_pct;
          const barColor =
            pct > 90 ? "bg-critical" : pct > 75 ? "bg-warning" : "bg-positive";

          return (
            <div
              key={member.id}
              className="flex items-center gap-4 px-[18px] py-3 border-b border-line hover:bg-panel2 transition-colors"
            >
              {/* Team name + channel */}
              <div className="flex flex-col gap-0.5 w-[160px] flex-none">
                <span className="text-[12px] font-medium whitespace-nowrap overflow-hidden text-ellipsis">
                  {member.team}
                </span>
                <span className="font-mono text-[9px] text-fg3 capitalize">
                  {member.channel.replace(/_/g, " ")}
                </span>
              </div>

              {/* Progress bar */}
              <div className="flex-1 flex items-center gap-3">
                <div className="flex-1 h-[6px] rounded-[4px] bg-line overflow-hidden">
                  <div
                    className={`h-full rounded-[4px] ${barColor} transition-all`}
                    style={{ width: `${Math.min(pct, 100)}%` }}
                  />
                </div>
                <span className={`font-mono text-[11px] font-medium w-[40px] text-right ${
                  pct > 90 ? "text-critical" : pct > 75 ? "text-warning" : "text-positive"
                }`}>
                  {pct.toFixed(0)}%
                </span>
              </div>

              {/* Hours detail */}
              <span className="font-mono text-[9px] text-fg3 w-[80px] text-right flex-none">
                {member.used_hours}/{member.allocated_hours}h
              </span>
            </div>
          );
        })}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  Sub-components: Competitive Intel                                   */
/* ------------------------------------------------------------------ */

function CompetitiveIntelSection({ items }: { items: CompetitiveFeedItem[] }) {
  return (
    <section
      className="rounded-card border border-line bg-panel overflow-hidden animate-rise"
      style={{ animationDelay: "0.25s" }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-[18px] py-[15px] border-b border-line">
        <SectionHeader title="Competitive Intel" accent="amber" />
        <Pill variant="amber">{items.length} SIGNALS</Pill>
      </div>

      {/* Feed items */}
      <div className="flex flex-col gap-0 max-h-[360px] overflow-y-auto">
        {items.map((item) => (
          <div
            key={item.id}
            className="flex flex-col gap-2 px-[18px] py-3 border-b border-line hover:bg-panel2 transition-colors"
          >
            {/* Top row: competitor + category + impact */}
            <div className="flex items-center gap-2 flex-wrap">
              <Pill variant="neutral">{item.competitor}</Pill>
              <span className="font-mono text-[9px] tracking-[.06em] text-fg3 uppercase">
                {item.category}
              </span>
              <Pill variant={impactVariant(item.impact)} dot>
                {item.impact.toUpperCase()} IMPACT
              </Pill>
            </div>

            {/* Headline */}
            <span className="text-[12.5px] font-medium leading-snug text-fg">
              {item.headline}
            </span>

            {/* Summary */}
            <p className="text-[11.5px] leading-relaxed text-fg2 line-clamp-2">
              {item.summary}
            </p>

            {/* Footer: source + date + tags */}
            <div className="flex items-center gap-3 flex-wrap">
              <span className="font-mono text-[9px] text-fg3">
                {item.source}
              </span>
              <span className="font-mono text-[9px] text-fg3">
                {item.detected_at}
              </span>
              {item.tags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 rounded bg-panel2 font-mono text-[8px] tracking-[.04em] text-fg3"
                >
                  {tag}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  API -> QueueItem mapper                                            */
/* ------------------------------------------------------------------ */

/** Map BFF ApprovalItem to the richer QueueItem shape used by the UI.
 *  Fields the API doesn't carry (why, impact, toolSteps) fall back to
 *  the matching mock entry so the detail panel stays fully populated. */
function apiToQueueItem(api: ApprovalItem): QueueItem {
  const mock = QUEUE_ITEMS.find((m) => m.id === api.id);
  const statusUpper = api.status.toUpperCase();
  return {
    id: api.id,
    tool: api.directive_type.toUpperCase(),
    conf: api.priority === "HIGH" ? "94%" : api.priority === "MEDIUM" ? "78%" : "65%",
    status: statusUpper,
    statusColor:
      statusUpper === "APPROVED"
        ? "var(--green)"
        : statusUpper === "REVIEW"
          ? "var(--cyan)"
          : "var(--amber)",
    title: api.title,
    // Detail-view fields: not in API, fall back to mock or placeholder
    risk: mock?.risk ?? "MEDIUM",
    why: mock?.why ?? "Agent rationale pending.",
    impact: mock?.impact ?? "Impact analysis pending.",
    eta: mock?.eta ?? "--",
    toolSteps: mock?.toolSteps ?? [],
  };
}

/* ------------------------------------------------------------------ */
/*  Main Operations component                                          */
/* ------------------------------------------------------------------ */

export function Operations() {
  const { filters } = useShell();
  const approvals = useApprovals(filters);
  const calendar = useOpsCalendar(filters);
  const capacity = useOpsCapacity(filters);
  const competitive = useCompetitiveFeed(filters);

  return (
    <div className="flex flex-col gap-4">
      {/* ===== 1. APPROVAL QUEUE (existing) ===== */}
      <DataGuard
        {...approvals}
        skeleton={
          <div className="flex gap-4 items-stretch flex-wrap min-h-[480px]">
            {/* Left panel skeleton */}
            <div
              className="flex flex-col gap-0 rounded-card border border-line bg-panel overflow-hidden"
              style={{ flex: "0 1 420px", minWidth: "320px" }}
            >
              <div className="h-[52px] border-b border-line" />
              <Skeleton rows={4} className="p-4" />
            </div>
            {/* Right panel skeleton */}
            <div
              className="flex-1 min-w-[360px] rounded-card border border-line bg-panel p-6"
              style={{ minHeight: "480px" }}
            >
              <Skeleton rows={6} />
            </div>
          </div>
        }
        emptyHeadline="No pending directives"
        emptyBody="The approval queue is empty. New agent directives will appear here."
      >
        {(apiApprovals) => (
          <OperationsContent apiApprovals={apiApprovals} reload={approvals.reload!} />
        )}
      </DataGuard>

      {/* ===== 2. LAUNCH CALENDAR ===== */}
      <DataGuard
        {...calendar}
        skeleton={
          <div className="rounded-card border border-line bg-panel p-5">
            <Skeleton rows={5} />
          </div>
        }
        emptyHeadline="No upcoming launches"
        emptyBody="The launch calendar is empty. Scheduled campaigns and events will appear here."
      >
        {(calendarData) => (
          <LaunchCalendarSection events={calendarData.events} />
        )}
      </DataGuard>

      {/* ===== 3. TEAM CAPACITY + COMPETITIVE INTEL (side by side) ===== */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Team Capacity */}
        <DataGuard
          {...capacity}
          skeleton={
            <div className="rounded-card border border-line bg-panel p-5">
              <Skeleton rows={6} />
            </div>
          }
          emptyHeadline="No capacity data"
          emptyBody="Team capacity data is not available for the selected period."
        >
          {(capacityData) => (
            <TeamCapacitySection
              members={capacityData.members}
              summary={capacityData.summary}
            />
          )}
        </DataGuard>

        {/* Competitive Intel */}
        <DataGuard
          {...competitive}
          skeleton={
            <div className="rounded-card border border-line bg-panel p-5">
              <Skeleton rows={6} />
            </div>
          }
          emptyHeadline="No competitive intel"
          emptyBody="No competitive intelligence signals detected. New items will appear as they are identified."
        >
          {(feedData) => (
            <CompetitiveIntelSection items={feedData.items} />
          )}
        </DataGuard>
      </div>
    </div>
  );
}

/** Inner component -- rendered only when approval data is available. */
function OperationsContent({
  apiApprovals,
  reload,
}: {
  apiApprovals: ApprovalItem[];
  reload: () => void;
}) {
  // Merge API data with mock fallback -- API drives the queue list,
  // mock enriches fields the API doesn't carry (rationale, impact, toolchain).
  const queueItems: QueueItem[] = apiApprovals.map(apiToQueueItem);

  const [selectedId, setSelectedId] = useState(QUEUE_ITEMS[0].id);
  const [actionLoading, setActionLoading] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const [deferredIds, setDeferredIds] = useState<Set<string>>(new Set());

  const visibleItems = queueItems.filter((d) => !deferredIds.has(d.id));
  const selectedItem = visibleItems.find((d) => d.id === selectedId) ?? visibleItems[0];
  const pendingCount = visibleItems.filter((d) => d.status === "PENDING").length;

  /* ---- Action handlers ---- */

  const handleApprove = useCallback(async (id: string) => {
    setActionLoading(id);
    try {
      await apiFetch<{ success: boolean; message: string }>(
        `/api/ops/approvals/${id}/approve`,
        { method: "POST" },
      );
      reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Approve failed");
    } finally {
      setActionLoading(null);
    }
  }, [reload]);

  const handleReject = useCallback(async (id: string) => {
    setActionLoading(id);
    try {
      await apiFetch<{ success: boolean; message: string }>(
        `/api/ops/approvals/${id}/reject`,
        { method: "POST" },
      );
      reload();
    } catch (err) {
      setActionError(err instanceof Error ? err.message : "Reject failed");
    } finally {
      setActionLoading(null);
    }
  }, [reload]);

  const handleDefer = useCallback((id: string) => {
    setDeferredIds((prev) => new Set(prev).add(id));
    // Auto-select next visible item
    const remaining = queueItems.filter((d) => !deferredIds.has(d.id) && d.id !== id);
    if (remaining.length > 0) setSelectedId(remaining[0].id);
  }, [queueItems, deferredIds]);

  return (
    <div className="flex flex-col gap-4 min-h-[480px]">
      {/* Action error banner */}
      {actionError && (
        <div className="flex items-center justify-between px-4 py-2 rounded-card border border-critical/40 bg-critical/10 animate-rise">
          <span className="text-[12px] text-critical">{actionError}</span>
          <button
            onClick={() => setActionError(null)}
            className="font-mono text-[10px] text-fg3 hover:text-fg transition-colors"
          >
            DISMISS
          </button>
        </div>
      )}

      <div className="flex gap-4 items-stretch flex-col lg:flex-row flex-1">
      {/* ===== Left: Approval Queue ===== */}
      <section
        className="flex flex-col rounded-card border border-line bg-panel overflow-hidden animate-rise lg:max-w-[420px]"
        style={{ flex: "0 1 420px", minWidth: "280px" }}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-[18px] py-[15px] border-b border-line">
          <SectionHeader title="Approval Queue" accent="amber" />
          <Pill variant="amber" dot>{pendingCount} PENDING</Pill>
        </div>

        {/* Queue items */}
        <div className="flex-1 min-h-0 overflow-auto">
          {visibleItems.map((item, i) => (
            <QueueRow
              key={item.id}
              item={item}
              selected={item.id === selectedId}
              onClick={() => setSelectedId(item.id)}
              index={i}
            />
          ))}
        </div>
      </section>

      {/* ===== Right: Directive Review ===== */}
      <section
        className="flex-1 min-w-0 rounded-card border border-line bg-panel p-6 animate-rise"
        style={{ animationDelay: "0.1s", minHeight: "480px" }}
      >
        <div className="mb-5">
          <SectionHeader title="Directive Review" accent="cyan" />
        </div>
        <DirectiveDetail
          key={selectedItem.id}
          item={selectedItem}
          onApprove={handleApprove}
          onReject={handleReject}
          onDefer={handleDefer}
          actionLoading={actionLoading}
        />
      </section>
      </div>
    </div>
  );
}
