# Velocity Lens — Agentic Paid Media Engine

**The Acquisition pillar of the FITB / RV 2.0 Platform.** A full-architecture build spec for an AI-native paid-media optimization engine, with GlitchAds, Graphed, Parallel AI, and Atria as the reference architecture.

Version 2.0 · June 23, 2026 · Full-architecture spec (technical + UX/UI)

---

## FITB Alignment (read first)

This document was realigned on June 23, 2026 against the **#fitb-platform** Slack channel and the **Platform Updates** notes canvas (most recent entry June 19, 2026). It is **no longer a generic four-vendor clone** — it is scoped to the **Acquisition pillar** of the RV 2.0 / Velocity 2.0 platform, internally referred to as **Velocity Lens / the Agentic Paid Media Engine**. The other three pillars (Conversion / "Site Factory", Deepening / "Agentic Banker Assist", Operations) are out of scope here and are noted only where they consume Velocity Lens output.

**Agreed decisions reflected in this spec (source: #fitb-platform, June 1–19, 2026):**

- **Pillar framing.** The platform is structured as four pillars — **Acquisition · Conversion · Deepening · Operations**. This document = Acquisition.
- **Product goal (Lachlan, May 27; Cameron, May 29).** "An AI-driven acquisition engine that operates at real-time arbitrage speed across paid media and SEO — finding the sweet spot of geo, cohort, keyword, and offer continuously rather than in quarterly human cycles," with human-intervention flags for bid pressure, budget shifts, and strategic calls, and anticipation of the shift from traditional SEO to **agentic search**.
- **Channels.** Demo spans **Google, Microsoft (Bing), and Meta** ad platforms — not just Google. (June 19 notes.)
- **Rollout posture (June 19 decision).** Velocity Lens ships as a **read-only geo-level paid-media analysis tool FIRST**, before pursuing agentic budget deployment. *This spec defines the full agentic engine, but the build is explicitly phased so the read-only analysis layer is the first shippable product (see Part E).*
- **Human-in-the-loop is mandatory.** Budget reallocation and creative both require explicit human sign-off / confirmation before anything is deployed via API. (Cameron, May 29; June 19 notes.)
- **Target KPIs (Lachlan, May 27).** CAC, CAC-to-LTV ratio, **funded accounts per media dollar**, share of voice on priority keywords.
- **Demo components already built (Cameron/Tala, June 19).** Always-on budget reallocation engine using **optimization curves per campaign** across Google/Microsoft/Meta; **geo-level reallocation simulation**; **top-mover curves**; API-based deployment with human-in-the-loop confirmation.

**FITB-specific constraints to design around (source: notes canvas, June 19):**

- Fifth Third's current process: budget reviewed **monthly/quarterly** with limited proactive day-to-day changes — Velocity Lens is deliberately ahead of their roadmap.
- Some data feeds (**spend by geo, campaign-level platform data**) are **not yet fully integrated**; may require manual pulls initially. The data layer must tolerate manual/batch ingestion at first.
- Fifth Third's Energy team is only building a Slack-based LLM chatbot; **no platform acquisition automation exists** on their side yet.
- **Long implementation lead times** — Velocity Lens went demo→build-approval in ~5.5 months. Phasing and a credible read-only MVP matter.
- Validate on **real RV data** (TPG, Bankrate, Frontier, or Energy via Mason) for credibility before FITB deployment.

> **Reading note.** Throughout, references to **GlitchAds / Graphed / Parallel AI / Atria** are *reference architecture* for how a best-in-class paid-media engine is built — they are vendors we are learning from, not products being cloned. Apex/Velocity Lens is the FITB-context build.

---

## 0. How to read this document

This is a complete build plan for one product, **Apex**, that absorbs the strongest capabilities of four competitors into a single coherent platform. It is written to be handed directly to engineering and design:

- **Part A — Competitive Synthesis.** What each of the four does, and what we take from each.
- **Part B — Product Definition.** Apex's scope, personas, and feature inventory.
- **Part C — Microservice Architecture.** Services, data model, AI/agent runtime, data pipeline, integrations, infra, security. Implementation-ready.
- **Part D — UX/UI Specification.** Information architecture, design system, screen-by-screen specs, component library, and agent-interaction patterns — written so it can be given to Claude Code to scaffold the front end.
- **Part E — Delivery.** Phased roadmap, build sequence, and risks.

> **Sourcing note.** Feature claims are drawn from each company's public marketing site (June 2026). Marketing copy describes *intended* behavior, not verified implementation. Where a mechanism is inferred rather than stated, it is marked **(inferred)**.

---

## Part A — Competitive Synthesis

### A.1 The four products at a glance

| Product | One-line | Primary channel | Core wedge | Buyer |
|---|---|---|---|---|
| **GlitchAds** (glitchads.ai) | Complete Google Ads management platform with AI campaign creation, daily optimization, analytics | Google Ads | End-to-end automation: build → optimize → report | SMB, agencies, enterprise PPC |
| **Graphed** (graphed.com) | Deploy AI agents for marketing, on a managed data pipeline + warehouse | Cross-channel (Meta, Google, TikTok, SEO, email) | "Virtual marketing employees" + warehouse-backed truth | Growth teams who lack data engineering |
| **Parallel AI** (withparallel.ai) | AI agent platform for Google Ads *work* with human-in-the-loop approval | Google Ads | Judgment + human control + shareable deliverables | Paid-media agencies, in-house, enterprise |
| **Atria** (tryatria.com) | AI ad-creative engine trained on $5B+ ad spend; insight → brief → creative → launch | Meta, TikTok (paid social) | Creative intelligence + market dataset + creative velocity | Performance/creative teams, DTC brands, agencies |

### A.2 What we take from each

**From GlitchAds — the execution spine for search.**
- AI campaign generation from a website URL (analyze business → headlines, descriptions, keywords, targeting in minutes).
- Smart asset creation tied to funnel stage (headlines, descriptions, sitelinks, callouts, structured snippets).
- Keyword research via Keyword Planner API + competitor + historical data.
- Daily optimization loop: budget optimization to target CPA, recommendations engine, performance monitoring with alerts (high CPC, zero impressions, no conversions, overspend).
- Analytics: daily dashboards, historical trend analysis, scheduled/white-label reporting.
- Workflow automation: background task processing, smart notifications, bulk operations.
- Platform: Google Ads API sync, multi-account management, role-based team collaboration (Owner/Admin/Member).

**From Graphed — the data + agent infrastructure.**
- Managed data pipeline across 750+ connectors (Shopify, Meta, Google, GA4, HubSpot…) with scheduled syncs, retries, freshness checks.
- A modeled **marketing warehouse**: one SQL definition layer that every chart, alert, and agent reads from ("same curated truth").
- A roster of specialist **agents** (Paid Ads, SEO, Content Strategist, Outreach) configured in plain English, working autonomously, reporting to Slack.
- **Agent runtime**: isolated compute, tools, and memory per agent with direct warehouse access.
- Live, warehouse-backed reporting dashboards (drag-and-drop, shareable, freshness-aware).
- **MCP server** so any AI assistant (Cursor, Claude Code, Windsurf) can explore schemas, run queries, trigger agent actions.

**From Parallel AI — the trust & control layer.**
- Connected-context chat over the ad account ("not a blank prompt") for analysis, reporting, optimization review.
- **Human-in-the-loop approval**: agents investigate/draft/summarize freely, but high-impact account changes wait behind explicit human approval before touching a live account.
- **Shareable output as first-class objects**: report, document, checklist, spreadsheet, next-step summary a teammate/client can review without rebuilding the analysis.

**From Atria — the creative intelligence engine.**
- **Raya-style AI strategist** trained on a large cross-account ad dataset; analyzes brand + ads + data, layers competitor + market intel, finds winning personas/hooks/messages.
- "Winning formula" extraction → creative briefs → auto-generated creative variants.
- Ad library / swipe inspiration, competitor ad intel.
- Batch upload dozens of creatives to Meta, one-click launch, performance read-back.
- **Ad grading**: every ad graded with specific fix recommendations; learnings compound campaign-to-campaign.
- API & MCP surface; SOC 2 Type II.

### A.3 The unifying thesis

The four products are slices of one workflow. Read end to end:

```
DATA (Graphed)  →  INSIGHT (Atria + Parallel chat)  →  CREATIVE & CAMPAIGN BUILD (Atria + GlitchAds)
   →  HUMAN APPROVAL (Parallel)  →  LAUNCH (Atria/GlitchAds)  →  OPTIMIZE (GlitchAds/Graphed agents)
   →  REPORT (all four)  →  LEARNINGS LOOP (Atria)
```

**Apex** is that full loop on one warehouse, with one agent runtime, across both **paid search** (Google) and **paid social/creative** (Meta, TikTok) — governed by human-in-the-loop control and surfaced through both a chat agent and structured dashboards.

---

## Part B — Product Definition

### B.1 Scope statement

Velocity Lens is the **Acquisition pillar** of the RV 2.0 platform: an AI-native paid-media optimization engine that lets the RV/FITB paid-media team **connect spend + performance data, analyze geo/cohort/keyword/offer opportunity continuously, simulate and (later) deploy budget reallocation, generate compliant creative, and route every spend or creative change through human sign-off** before it reaches a live ad account. Channels: **Google, Microsoft (Bing), and Meta** at v1 (matching the demo); SEO and **agentic search** are explicit forward-looking expansions. It operates for a **single regulated advertiser (Fifth Third)** initially, with RV businesses (TPG/Bankrate/Frontier/Energy) as validation accounts — not a multi-tenant SMB/agency SaaS.

> **Why this differs from the vendor reference set.** GlitchAds/Atria target SMBs and agencies (self-serve, multi-tenant, white-label). Velocity Lens targets an enterprise bank: fewer accounts, far stricter compliance, mandatory human sign-off, and KPIs tied to **funded accounts per media dollar** rather than generic ROAS.

### B.2 Personas

| Persona | Goal | Primary surface |
|---|---|---|
| **RV paid-media analyst** (e.g., Chris Turley) | Continuous geo/cohort/keyword/offer optimization instead of monthly cycles; trustworthy recommendations | Opportunity explorer, reallocation simulator, approval queue |
| **RV acquisition lead** | Judgment + governance; decide what gets deployed | Reallocation review, human-in-the-loop confirmation, exec dashboard |
| **FITB stakeholder / marketing lead** | Confidence that spend moves are compliant and explainable | Read-only analysis dashboards, share-of-voice + funded-accounts reporting |
| **Compliance reviewer** | Nothing non-compliant reaches a live account or live creative | Approval queue with diffs, audit log, creative compliance guardrails |
| **Creative strategist** | Compliant ad creative tied to performance + demand signals | Creative hypothesis workflow, variant generator (with required human sign-off) |

### B.3 Feature inventory (the master list)

Eight capability domains scoped to the Acquisition pillar. Each maps to services in Part C. The **★** marks capabilities explicitly built/agreed in the #fitb-platform demo; **(later)** marks agentic deployment behind the read-only-first decision.

**1. Data & Connectors**
- Connectors for **Google Ads, Microsoft Advertising, Meta** + Snowflake/warehouse and RV validation accounts (TPG/Bankrate/Frontier/Energy).
- Scheduled syncs with retries and freshness checks; per-source health status.
- **Tolerate manual/batch ingestion** for spend-by-geo and campaign-level platform data not yet integrated at FITB. ★(constraint)
- Modeled marketing warehouse on **Snowflake** (FITB's stack) with shared SQL metric definitions — including **funded accounts per media dollar** and **CPIHH as a calculated column** (per notes: move CPIHH out of Excel into Snowflake).

**2. Opportunity Identification & Arbitrage Intelligence**
- Continuous scan of **geo × cohort × keyword × offer** for the optimal combination — replacing the monthly/quarterly human cycle. ★
- **Optimization curves per campaign** (spend→return response curves) across Google/Microsoft/Meta. ★
- **Top-mover curves** surfacing where marginal dollars move the KPI most. ★
- Share-of-voice tracking on priority keywords.
- Whitespace / opportunity-benchmarking: net-new spend opportunities a quarterly review would miss.
- **Agentic-search readiness** — anticipate the shift from traditional SEO to LLM/agentic search surfaces. (forward-looking)

**3. Geo-Level Reallocation Engine**
- **Geo-level reallocation simulation** — model moving budget between geos/campaigns and project KPI impact. ★
- Budget allocation to a goal (CAC, CAC-to-LTV, funded accounts per media dollar) with guardrails.
- **Read-only analysis mode** (ships first) vs. **agentic deployment mode** (later, gated). ★(decision)

**4. Analysis & Conversational Agent**
- Connected-context chat grounded in the warehouse (no blank prompt) for spend, pacing, geo, keyword, and reporting questions.
- Investigate / draft / summarize / prepare recommendations → shareable deliverables (report, doc, checklist, spreadsheet, next-step summary).

**5. Creative (compliant, performance-driven)**
- Auto-generate ad copy/visual creative from performance data + demand signals, tied to segments, continuously tested.
- **Compliance guardrails + required human sign-off** before any creative goes live. ★(constraint)
- Creative-performance-hypothesis workflow (what to test next and why).

**6. Optimization & Monitoring**
- Recommendations engine (bid/budget moves, negative keywords, underperformers).
- Performance monitoring + alerts (overspend, pacing drift, KPI-threshold breaches).
- Continuous daily loop; flags humans on bid pressure, budget shifts, strategic calls. ★

**7. Human-in-the-Loop Control (mandatory)**
- Action classification: analysis/draft (free) vs. budget-deploy or creative-publish (requires explicit confirmation). ★
- **API-based deployment with human-in-the-loop confirmation** before changes hit a live account. ★
- Full append-only audit log of agent + human actions (compliance evidence).

**8. Launch, Reporting & Extensibility**
- Push approved budget/creative changes to Google/Microsoft/Meta via official APIs; rollback; sync-back to Snowflake.
- Live warehouse-backed dashboards (geo maps, optimization curves, KPI tiles), freshness-aware; scheduled reports.
- RBAC, audit-log export, **MCP server** so RV's Claude/agentic tooling can query and (via the gate) act.
- SOC 2 / enterprise security posture appropriate to a bank advertiser.

---

## Part C — Microservice Architecture

### C.1 Architectural principles

1. **One warehouse as source of truth.** Every dashboard, alert, and agent reads from the same modeled metric layer. No service computes its own private version of "ROAS."
2. **Agents are stateless orchestrators over stateful tools.** Agent runtime holds reasoning + per-agent memory; all side effects go through governed tool services.
3. **Nothing reaches a live ad account without passing the policy/approval gate.** Activation is the only path to external write, and it enforces human-in-the-loop rules.
4. **Async-first.** Long operations (sync, campaign generation, creative generation, optimization) run as background jobs with status events, not blocking requests.
5. **Multi-tenant isolation by default.** Tenant ID is enforced at the data layer (row-level security) and at the agent-runtime boundary (per-tenant credentials, per-agent sandbox).

### C.2 Service map

Twelve core services plus shared infrastructure. Each is independently deployable, owns its data, and communicates via gRPC/REST (sync) and an event bus (async).

| # | Service | Responsibility | Owns (datastore) |
|---|---|---|---|
| 1 | **Identity & Tenant Service** | Auth (OIDC), orgs, users, RBAC, multi-account membership | Postgres (auth schema) |
| 2 | **Connector Service** | OAuth to 750+ sources, credential vaulting, connection health | Postgres + secrets vault |
| 3 | **Ingestion/Pipeline Service** | Scheduled syncs, retries, freshness checks, change-data-capture | Job store (Postgres) + object storage (raw landing) |
| 4 | **Warehouse & Metrics Service** | Modeled tables, shared SQL metric definitions, semantic layer | Columnar warehouse (e.g., ClickHouse/BigQuery) |
| 5 | **Insight & Creative-Intelligence Service** | Winning-formula extraction, ad grading, competitor/market dataset, embeddings | Vector DB + warehouse views |
| 6 | **Agent Orchestration Service** | Plans/executes agent runs, tool routing, per-agent memory, scheduling | Postgres (runs) + Redis (state) |
| 7 | **Generation Service** | URL→campaign, asset/keyword generation, creative variant generation, briefs | Postgres (drafts) + object storage (assets) |
| 8 | **Optimization Service** | Budget allocation, recommendations, threshold monitoring, alert rules | Postgres + warehouse reads |
| 9 | **Policy & Approval Service** | Action classification, approval queue, diffs, audit log | Postgres (append-only audit) |
| 10 | **Activation Service** | Writes to Google/Meta/TikTok APIs, batch upload, rollback, sync-back | Postgres (action ledger) |
| 11 | **Reporting & Dashboard Service** | Dashboard config, chart compilation, scheduled/white-label reports, shareable deliverables | Postgres (configs) + warehouse reads |
| 12 | **Notification & Collaboration Service** | Slack/email, in-app notifications, comments, share links | Postgres + queue |

Plus: **API Gateway / BFF**, **MCP Server**, **Event Bus**, **Job Workers**, **Object Storage**, **Secrets Vault**, **Observability stack**.

### C.3 High-level diagram (text)

```
                         ┌──────────────────────────────────────────┐
   Web SPA  ── HTTPS ──►  │   API Gateway / BFF (GraphQL + REST)      │
   MCP client ─────────►  │   MCP Server (tools = governed actions)   │
                         └───────┬───────────────────────┬──────────┘
                                 │                        │
                ┌────────────────┴────────┐     ┌─────────┴─────────────┐
                │  Identity & Tenant       │     │  Agent Orchestration   │
                └──────────────────────────┘     │  (per-agent runtime)   │
                                                  └───┬───────┬───────┬───┘
   Connector ─► Ingestion ─► Warehouse & Metrics ◄────┘       │       │
       │            │              ▲                          │       │
   Secrets       Object         Insight & Creative-Intel ◄────┘       │
   Vault         Storage             │                                │
                                Generation ── drafts ──► Policy & Approval ──► Activation ──► Google/Meta/TikTok
                                Optimization ── proposed actions ──────┘          │
                                                                          (sync-back to Warehouse)
                Reporting/Dashboards ◄── Warehouse        Notification & Collaboration ◄── Event Bus
```

### C.4 Service detail

**1. Identity & Tenant Service.** OIDC/OAuth2 (Auth0/Cognito/Keycloak). Models `Organization → Account(s) → User`, membership with roles **Owner/Admin/Member** (GlitchAds parity), plus agency↔client account linking for multi-account management. Issues short-lived JWTs carrying `tenant_id`, `account_ids`, `role`. Enforces row-level security context downstream.

**2. Connector Service.** Wraps a connector framework — **Airbyte** for the long tail of 750+ sources (Graphed visibly uses Airbyte connector icons) plus **first-party connectors** for Google Ads, Meta Marketing, TikTok Business where deep write access and rate-limit control matter. Stores OAuth tokens in a secrets vault, never in app DB. Exposes `connect`, `test`, `health`, `revoke`. Emits `source.connected` / `source.health_changed`.

**3. Ingestion/Pipeline Service.** Orchestrates syncs via a workflow engine (**Temporal** or **Dagster/Airflow**). Per-source schedules, exponential-backoff retries, freshness SLAs, CDC where supported. Lands raw to object storage, then triggers transforms. Emits `sync.completed` with row counts + freshness. Dashboards/agents are gated on `pipeline_healthy` (Graphed behavior).

**4. Warehouse & Metrics Service.** Columnar store (**ClickHouse** self-hosted, or **BigQuery/Snowflake** managed). Transformations in **dbt**: staging → marts (`fct_spend`, `fct_conversions`, `dim_campaign`, `dim_creative`, …). A **semantic/metric layer** (dbt MetricFlow or Cube) defines metrics once (`roas`, `cpa`, `blended_roas`); all consumers query through it. This is the literal embodiment of "every chart, alert, and agent reads from the same SQL definitions."

**5. Insight & Creative-Intelligence Service.** The "Raya" brain.
- Maintains a **cross-account creative dataset** (anonymized, opt-in) used for market benchmarking — the moat Atria describes.
- Computes embeddings of ad creative (image/video/copy) via multimodal models; clusters into hooks/personas/formats.
- **Winning-formula extraction**: correlates creative attributes with performance from the warehouse to surface what wins.
- **Ad grading**: scores each ad on attributes + predicted/realized performance and returns specific fixes.
- Stores vectors in **pgvector/Pinecone/Weaviate**; serves similarity ("ads like this," "competitors doing X").

**6. Agent Orchestration Service.** The runtime behind both the chat agent (Parallel-style) and specialist agents (Graphed-style).
- Each agent run = a plan executed by an LLM with a **tool registry** (warehouse query, insight lookup, generation, optimization proposal, activation *proposal only*, notification).
- **Per-agent memory** (episodic in Redis/Postgres, semantic in vector store) so agents "never lose learnings" (Atria).
- **Isolated execution** per agent/tenant: scoped credentials, sandboxed tool access, resource limits (Graphed "isolated compute, tools, and memory per agent").
- Plain-English configuration → structured agent spec; agents ask clarifying questions before first run (Graphed flow).
- Scheduler triggers recurring runs (e.g., "daily at 8:00 AM ET"). Built on a durable workflow engine so runs survive restarts.

**7. Generation Service.** Stateless LLM-backed generators:
- **URL→campaign**: crawl/analyze site → business profile → campaign skeleton, ad groups, keywords (via Keyword Planner API through Connector Service), targeting, copy. Target: minutes (GlitchAds "under 5 minutes").
- **Asset generation**: funnel-aware RSAs, sitelinks, callouts, snippets; social hooks/scripts/storyboards.
- **Creative variant generation**: from a winning formula + brand kit → image/video variants (multimodal gen) + copy.
- **Brief builder**: turns insights into structured creative briefs.
- All outputs are **drafts** — they never go live without passing Policy & Approval.

**8. Optimization Service.** Reads warehouse metrics, runs rules + models:
- Budget allocation to target CPA/ROAS; reallocation proposals (move budget winner↔loser).
- Recommendations: negative keywords, underperformers, bid/budget changes.
- Threshold monitoring → alerts (high CPC, zero impressions, no conversions, overspend, ROAS < threshold).
- Emits **proposed actions** to Policy & Approval (never writes directly).

**9. Policy & Approval Service (the trust layer — Parallel's contribution).**
- **Action classifier**: every proposed action tagged low-impact (auto-executable per tenant policy) or high-impact (pause campaign, change budget >X%, edit live creative → requires human approval).
- **Approval queue**: presents a human-readable **diff** (before/after) and rationale; approve/reject/edit.
- **Audit log**: append-only record of who/what/when for every agent + human action (enterprise governance, SOC 2 evidence).
- Tenant-configurable policy (SMB may auto-approve more; enterprise locks everything behind review).

**10. Activation Service.** The *only* writer to external ad platforms.
- Adapters for **Google Ads API**, **Meta Marketing API**, **TikTok Business API**.
- Batch creative upload (Atria "batch upload dozens of creatives") + one-click launch.
- Idempotent action ledger, rate-limit handling, partial-failure recovery, **rollback**.
- Sync-back: writes results to warehouse so the optimization/learning loop closes.

**11. Reporting & Dashboard Service.** Dashboard configs (drag-and-drop layouts) compiled to metric-layer queries; refresh on `sync.completed` (freshness-aware). Scheduled + **white-label** report generation (PDF/HTML/email). **Shareable deliverables** as persistent objects (report, doc, checklist, spreadsheet, next-step summary — Parallel) with share links + access control.

**12. Notification & Collaboration Service.** Slack + email + in-app. Agent run summaries to channels ("Send a Slack summary each morning"). Comments/mentions on deliverables and approvals.

### C.5 Cross-cutting infrastructure

- **API Gateway / BFF**: GraphQL for the SPA (aggregates across services), REST for public API. AuthN/Z, rate limiting, request tracing.
- **MCP Server**: exposes governed tools (`query_metrics`, `list_agents`, `run_agent`, `get_insights`, `propose_action`) so Claude Code/Cursor/Windsurf can operate Apex. Read tools are open; write tools route through Policy & Approval. (Both Graphed and Atria ship MCP — this is table stakes.)
- **Event Bus**: Kafka or NATS. Topics: `source.*`, `sync.*`, `agent.run.*`, `action.proposed/approved/executed`, `alert.*`.
- **Job Workers**: Temporal workers for sync, generation, optimization, activation.
- **Object Storage**: S3/GCS for raw landings, generated creative, report artifacts.
- **Secrets Vault**: HashiCorp Vault / cloud KMS for OAuth tokens + API keys.
- **Observability**: OpenTelemetry traces, Prometheus/Grafana metrics, structured logs; per-tenant cost metering for LLM + warehouse usage.

### C.6 Recommended stack

| Layer | Choice | Why |
|---|---|---|
| Language (services) | **Go** (high-throughput: ingestion, activation, gateway) + **Python** (AI: generation, insight, agents) | Go for I/O concurrency; Python for ML/LLM ecosystem |
| LLM orchestration | **LangGraph / custom graph** + provider-agnostic router (Anthropic, OpenAI) | Durable agent graphs, model fallback |
| Workflow engine | **Temporal** | Durable, retryable long-running jobs |
| Connectors | **Airbyte** (long tail) + first-party (Google/Meta/TikTok) | Breadth + deep write control |
| Warehouse | **Snowflake** (FITB's existing stack — keeps CPIHH/funded-accounts metrics where the data lives) | Columnar analytics; aligns with FITB reality |
| Transform/metrics | **dbt + Cube/MetricFlow** | One metric definition, many consumers |
| Vector store | **pgvector** (start) → **Pinecone/Weaviate** (scale) | Creative similarity + agent memory |
| App DB | **Postgres** (per-service schemas, RLS) | Relational + row-level multi-tenancy |
| Cache/state | **Redis** | Agent state, sessions, rate limits |
| Event bus | **Kafka** or **NATS** | Async backbone |
| Frontend | **Next.js (React) + TypeScript + Tailwind + shadcn/ui** | SSR, component velocity (see Part D) |
| Infra | **Kubernetes** + Terraform, multi-AZ | Independent scaling per service |

### C.7 Core data model (essential entities)

```
Organization(id, name, plan, created_at)
Account(id, org_id, platform_scope, type[brand|agency_client], name)
User(id, org_id, email, name)
Membership(user_id, account_id, role[owner|admin|member])

Source(id, account_id, connector_type, status, last_sync_at, freshness_sla)
Credential(id, source_id, vault_ref)            # token in vault, not here
SyncRun(id, source_id, started_at, status, rows, freshness_at)

# Warehouse (modeled, in columnar store)
fct_spend, fct_conversions, fct_creative_perf, dim_campaign, dim_adgroup, dim_creative, dim_keyword
Metric(name, sql_definition, grain)              # semantic layer

Creative(id, account_id, platform, type, asset_ref, attributes_json, embedding_ref)
WinningFormula(id, account_id, persona, hook, message, format, evidence_refs, score)
AdGrade(id, creative_id, score, fixes_json, graded_at)

Agent(id, account_id, type, spec_json, schedule_cron, memory_ref, status)
AgentRun(id, agent_id, started_at, status, plan_json, summary, deliverable_refs)

Draft(id, account_id, kind[campaign|asset|creative|brief], payload_json, created_by_agent_run)
ProposedAction(id, account_id, source_run_id, kind, impact[low|high], diff_json, status)
Approval(id, proposed_action_id, decided_by, decision, decided_at)
ActivationAction(id, proposed_action_id, platform, external_ref, status, executed_at)
AuditEvent(id, account_id, actor[agent|user], action, target, before, after, ts)   # append-only

Dashboard(id, account_id, layout_json, share_scope)
Deliverable(id, account_id, kind[report|doc|checklist|spreadsheet|summary], content_ref, share_link)
Notification(id, account_id, channel, payload, sent_at)
```

Multi-tenancy: every table carries `account_id` (or `org_id`); Postgres **row-level security** policies bind queries to the JWT tenant context. Warehouse access is scoped per account via row filters in the metric layer.

### C.8 Three canonical request flows

**Flow 1 — URL → live search campaign (GlitchAds path, governed).**
```
User submits URL → Generation Service crawls + profiles → drafts campaign/keywords/assets
→ Draft stored → user reviews in builder → submits → Policy classifies (high-impact: new live campaign)
→ Approval queue → approved → Activation pushes to Google Ads API → sync-back to Warehouse
→ Reporting reflects new campaign → Optimization begins daily monitoring
```

**Flow 2 — Creative velocity loop (Atria path).**
```
Sync lands Meta/TikTok data → Insight Service extracts winning formulas + grades ads
→ Creative Agent run: pick winning formula → Generation builds variants + brief
→ Drafts → human approve → Activation batch-uploads to Meta → one-click launch
→ performance syncs back → Insight updates formulas (compounding learnings)
```

**Flow 3 — Conversational analysis → shareable deliverable (Parallel path).**
```
User asks chat agent a question → Agent Orchestration plans → queries Warehouse via metric layer
+ pulls Insights → drafts answer → can emit a Deliverable (report/checklist/spreadsheet)
→ any proposed account change becomes a ProposedAction in the approval queue, never auto-applied
```

---

## Part D — UX/UI Specification (hand to Claude Code)

> **Instruction to the front-end builder:** Build a **Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui** application. State via **TanStack Query** (server) + **Zustand** (UI). Charts via **Recharts**. Drag-and-drop dashboards via **dnd-kit**. Icons via **lucide-react**. All data comes from the GraphQL BFF; mock with MSW until services exist. Implement dark mode first (default), light mode second. Follow the design tokens and screen specs below exactly.

### D.1 Design language

- **Tone:** operator-grade, dense but calm. This is a control surface for spend, not a marketing site. High information density, generous use of status color, no decorative gradients in the app shell.
- **Layout model:** persistent left nav rail + top context bar + main canvas. A **right-hand Agent panel** can slide over any screen (the agent is omnipresent, Parallel-style).
- **Motion:** 150–200ms ease-out for panels and state changes; skeleton loaders for warehouse-backed data; a subtle "freshness pulse" when data re-syncs.

### D.2 Design tokens

```
/* Color — dark theme (default) */
--bg-app: #0B0E14;          --bg-surface: #131722;     --bg-elevated: #1A1F2E;
--border: #232938;          --text-primary: #E6E9F0;   --text-secondary: #97A0B5;
--brand: #5B8DEF;           --brand-strong: #3B6FD4;
--success: #2BD9A0;  --warning: #F5B544;  --danger: #F2545B;  --info: #5B8DEF;
--agent-accent: #A78BFA;    /* agent/AI surfaces use violet to distinguish from human UI */

/* Typography */
--font-sans: "Inter", system-ui;  --font-mono: "JetBrains Mono", monospace;
text-xs 12 / sm 14 / base 15 / lg 18 / xl 22 / 2xl 28 / 3xl 36   (line-height 1.4–1.5)

/* Spacing scale: 4 8 12 16 24 32 48 64 ;  radius: sm 6  md 10  lg 14  full 999 ;  shadow: subtle, low-spread */
```

Status semantics are consistent everywhere: **success=on-track**, **warning=needs-attention**, **danger=breach/over-threshold**, **violet=agent-generated**.

### D.3 Information architecture (navigation)

> **FITB scoping note for the front-end builder.** This is the Velocity Lens (Acquisition) surface. Phase 1 is **read-only** — the Approvals and live-deploy actions are present in the IA but disabled/hidden until Phase 3. Lead with **Opportunity Explorer**, **Optimization Curves**, **Geo Reallocation Simulator**, and **Dashboards**. Use FITB acquisition KPIs (CAC, CAC-to-LTV, funded accounts per media dollar, CPIHH, share of voice), not generic ROAS.

Left nav rail (top to bottom):

1. **Home** — acquisition operator dashboard (KPIs, agent activity, what needs me)
2. **Opportunity Explorer** — geo×cohort×keyword×offer scan, whitespace, share-of-voice
3. **Optimization Curves** — per-campaign spend→return curves + top-mover curves across Google/Microsoft/Meta
4. **Geo Reallocation Simulator** — model budget moves, projected KPI impact (read-only sim in Phase 1)
5. **Creative** — performance-hypothesis workflow, compliant variant generation (human sign-off required)
6. **Dashboards** — geo maps, KPI tiles, reporting
7. **Approvals** — human-in-the-loop confirmation queue *(Phase 3; hidden in read-only MVP)*
8. **Deliverables** — shareable reports/docs/checklists/spreadsheets
9. **Connections** — Google/Microsoft/Meta + Snowflake, sync health (manual-pull fallback)
10. **Settings** — RBAC, policy, audit-log export, API & MCP

Top context bar: **account switcher** (multi-account/agency), global search, freshness indicator, notifications, user menu. Persistent **"Ask Apex"** button (bottom-right) opens the Agent panel anywhere.

### D.4 Screen specifications

For each screen: purpose, layout, key components, states.

**D.4.1 Home / Operator Dashboard** *(Graphed exec overview + GlitchAds daily dashboard)*
- **Purpose:** the single morning glance — what agents did, what needs me, how spend is doing.
- **Layout:** top KPI strip (Spend MTD, Blended ROAS, CPA, Conversions — each with delta vs prior period and freshness timestamp). Below: 3-column grid — (a) **Agent Activity Feed** (live, violet-accented cards: "Paused 'Summer Sale' — ROAS 1.1x < 2x, saved $840/day, 2m ago"), (b) **Needs Your Attention** (approval count, alerts, breaches), (c) **Performance sparkline cluster**.
- **States:** empty (no connections → CTA to Connections), syncing (skeleton + freshness pulse), alert (danger banner if a campaign breached).

**D.4.2 Agents — Roster** *(Graphed "AI marketing employees")*
- Grid of **agent cards**: name, type icon, status pill (Running / Drafting / Idle / Needs approval), one-line current activity, next-run countdown, connected-source icons, mini-stats (e.g., Actions today, Budget saved).
- Primary CTA: **+ Deploy agent**.

**D.4.3 Agents — Builder** *(Graphed plain-English config flow)*
- **Conversational setup:** big text field "Tell this agent what to do, in plain English." Example ghost text: *"Monitor my Meta and Google campaigns. Pause anything below 2x ROAS and shift budget to the top performer."*
- Agent replies inline with **clarifying questions** ("Check ROAS daily or hourly?"). User answers in chat.
- Result compiles into a structured **spec panel** (right side): Schedule, Channels, Thresholds, Scope, **Autonomy level** (read-only / propose-only / auto-low-impact). The autonomy selector is where Parallel's control model lives — default = propose-only.
- Save → agent appears in roster.

**D.4.4 Agent Run Detail**
- Timeline of the run's plan + tool calls (query → insight → proposed action), each step expandable. Produced deliverables linked. Any proposed actions show as cards with **"Send to approval"**.

**D.4.5 Campaigns** *(GlitchAds spine)*
- Tabs: **Search (Google)** | **Social (Meta/TikTok)**.
- **URL→Campaign wizard** (primary entry for SMB): paste URL → live progress ("Analyzing business… generating keywords… writing copy…") → review screen with editable campaign tree (campaigns → ad groups → keywords → assets), each AI-generated field marked violet and editable.
- Campaign list: table with health column (green/yellow/red), spend, CPA, ROAS, status; **bulk operations** toolbar (multi-select → pause/adjust budget/add negatives).
- Submitting changes routes through **Approvals** (diff preview), never instant.

**D.4.6 Creative Studio** *(Atria engine)*
- **Insights tab:** "winning formulas" board — cards for personas, hooks, messages, formats with performance evidence and a confidence score; competitor/market-intel section.
- **Swipe Library:** searchable ad inspiration grid (filter by industry/format/platform), similarity search ("find ads like this").
- **Brief Builder:** select a winning formula → auto-drafted creative brief (editable structured doc).
- **Variant Generator:** brief + brand kit → grid of generated creative variants (image/video/copy), each selectable; **batch-select → "Send to launch."**
- **Ad Grader:** drop in (or pick) an ad → grade score + ranked **specific fixes**; "regenerate with fixes" action.

**D.4.7 Dashboards** *(Graphed live reporting)*
- **dnd-kit** canvas: drag chart/KPI tiles, bind each to a **metric from the semantic layer** (dropdown of governed metrics — never raw SQL for end users). Freshness badge per tile. Toolbar: add tile, time range, breakdown dimension, **Share** (scoped view), **Schedule report**, **White-label** toggle (agency: client logo/colors).

**D.4.8 Approvals** *(Parallel control layer — the trust centerpiece)*
- Queue list (sorted by impact, then age). Each item opens a **diff view**: left = current live state, right = proposed change, with agent **rationale** and supporting metrics. Actions: **Approve / Reject / Edit & approve**. Bulk approve for low-impact. Every decision writes to the audit log (visible via "History").
- This screen must feel *safe*: explicit, reversible, legible. No silent writes anywhere in the app.

**D.4.9 Deliverables** *(Parallel shareable output)*
- Library of generated artifacts (report / doc / checklist / spreadsheet / next-step summary) with type icon, source (which agent/chat), created date, **share link** + access scope. Click → rendered viewer with export (PDF/CSV) and comments.

**D.4.10 Connections** *(Graphed data layer)*
- Grid of connected sources with **health status** (synced / syncing / error), last-sync time, row counts. **+ Add source** opens a searchable catalog ("Browse 750+") with 2-click OAuth. Per-source detail: schedule, freshness SLA, sync history.

**D.4.11 Settings**
- **Team & Roles:** invite users, assign Owner/Admin/Member, manage account/agency links.
- **Policy:** define autonomy + approval thresholds per account (what's auto vs. requires approval).
- **API & MCP:** API keys, copyable `mcp_config.json` snippet, scopes.
- **Billing, Security (SOC 2 statement, audit-log export).**

### D.5 Signature components (build as reusable)

- **`<AgentPanel>`** — slide-over chat grounded in account context; shows tool-call chips inline; can spawn deliverables and proposed actions. Violet accent throughout.
- **`<KPITile>`** — value + delta + sparkline + freshness timestamp; status-aware color.
- **`<HealthPill>`** / **`<StatusPill>`** — consistent status vocabulary.
- **`<DiffView>`** — before/after for approvals (also reused for campaign edits).
- **`<MetricBinder>`** — dropdown that exposes only semantic-layer metrics.
- **`<CampaignTree>`** — editable hierarchy with per-field "AI-generated" markers.
- **`<CreativeCard>`** / **`<CreativeGrid>`** — selectable, gradeable.
- **`<ActivityFeedItem>`** — agent action with entity, impact, timestamp.
- **`<FreshnessIndicator>`** — global + per-tile "synced Xs ago" with pulse on refresh.

### D.6 Interaction principles (non-negotiable)

1. **The agent is everywhere but never silent.** AI surfaces are visually distinct (violet) and every AI action is inspectable.
2. **No write without a diff + approval gate** (unless tenant policy explicitly auto-approves low-impact).
3. **One number, everywhere.** Any metric shown traces to the semantic layer; never two definitions of ROAS.
4. **Freshness is always visible.** Users must know how stale a number is before acting on it.
5. **Density with escape hatches.** Default to operator density; progressive disclosure for SMB simplicity.

---

## Part E — Delivery

### E.1 Phased roadmap

Phasing reflects the **June 19 decision: ship the read-only analysis tool first, then agentic deployment.** Phase 1 is the shippable MVP and the FITB demo target; agentic budget deployment is deliberately gated to Phase 3.

**Phase 0 — Foundations (weeks 1–6).** Identity/RBAC, Connectors (Google Ads, Microsoft Advertising, Meta + Snowflake), Ingestion with **manual/batch fallback** for spend-by-geo and campaign-level data, Snowflake warehouse + dbt + semantic layer (incl. **CPIHH and funded-accounts-per-media-dollar as modeled metrics**), app shell + design system. Validate on RV data (TPG/Bankrate/Frontier/Energy via Mason). *Exit:* connect sources, see governed acquisition KPIs on a dashboard.

**Phase 1 — Read-only Velocity Lens MVP (weeks 7–14). ← first shippable / FITB demo.** Opportunity Identification (geo×cohort×keyword×offer scan), **optimization curves per campaign**, **top-mover curves**, **geo-level reallocation simulation**, share-of-voice, read-only dashboards + analysis chat + shareable deliverables. **No live writes.** *Exit:* the agreed read-only geo-level paid-media analysis tool, demoable to FITB. Reference arch: **Graphed** (data/dashboards) + **Parallel** (connected-context analysis, no auto-write).

**Phase 2 — Compliant creative (weeks 15–22).** Creative-performance-hypothesis workflow, performance-driven copy/visual generation with **compliance guardrails + required human sign-off**, variant testing. Reference arch: **Atria**, constrained for a regulated advertiser. *Exit:* creative ideation→variant→(human-approved) test loop.

**Phase 3 — Agentic deployment + control (weeks 23–30). ← gated by read-only-first decision.** Policy & Approval service, **API-based budget/creative deployment with mandatory human-in-the-loop confirmation**, rollback, sync-back, recommendations engine, monitoring/alerts, MCP server. Reference arch: **GlitchAds** (optimization/activation) under **Parallel** governance. *Exit:* end-to-end agentic engine where nothing deploys without explicit sign-off.

**Phase 4 — Hardening & forward bets.** Enterprise security/SOC 2 posture, audit-log export, agentic-search readiness, cost metering. Accounts for FITB's ~5.5-month build-approval lead time and ~18-month AI-coding adoption horizon.

### E.2 Build sequence dependencies

```
Identity → Connector → Ingestion → Warehouse/Metrics → (everything else)
Warehouse → Optimization, Insight, Reporting
Generation + Optimization → Policy/Approval → Activation
Agent Orchestration depends on: Warehouse, Insight, Generation, Optimization, Policy (it orchestrates them)
MCP Server depends on: stable tool contracts in Agent + Warehouse + Policy
```

### E.3 Key risks & mitigations

| Risk | Mitigation |
|---|---|
| **FITB data not integrated** (spend-by-geo, campaign-level data may need manual pulls — notes, June 19) | Build read-only analysis on whatever lands; manual/batch ingestion fallback; don't block the MVP on full integration |
| **Long FITB build-approval lead time** (~5.5 months demo→approval — Velocity Lens) | Read-only-first MVP gives a credible, low-risk thing to approve early; phase agentic deployment behind it |
| **Bank compliance on autonomous spend/creative** | Mandatory human-in-the-loop confirmation, creative compliance guardrails, append-only audit log, agentic deployment gated to Phase 3 |
| **Ad-platform API write approval & rate limits** (Google/Microsoft/Meta) | Apply early for access; read-only first (no writes until Phase 3); queue + backoff in Activation |
| **Ahead of FITB's roadmap** (their Energy team is only at a Slack chatbot; AI-coding adoption ~18 mo out) | Position Velocity Lens as RV-operated, validated on RV data first; keep the FITB-facing surface simple and read-only initially |
| **Creative-intelligence cold start** (Atria's moat is $5B of ad data we don't have) | Start with FITB/RV first-party performance data + public ad libraries; the advantage compounds over time |
| **Attribution to funded accounts** (the real KPI, not ROAS) | Model funded-accounts-per-media-dollar and CPIHH in Snowflake as first-class metrics; align with Catherine's reporting-foundation work |

### E.4 Definition of done

**Phase 1 (read-only MVP — the FITB demo target):** The RV paid-media team can connect Google/Microsoft/Meta + Snowflake; see acquisition KPIs (CAC, CAC-to-LTV, funded accounts per media dollar, CPIHH, share of voice) refresh on dashboards; view **optimization curves per campaign** and **top-mover curves**; run a **geo-level reallocation simulation** and see projected KPI impact; ask the analysis agent questions grounded in the warehouse; and export a shareable deliverable — **with zero live writes** and every recommendation explainable.

**Full engine (Phase 3):** On top of the above, the engine continuously identifies geo×cohort×keyword×offer opportunities, proposes budget reallocations and compliant creative, and — only after **explicit human-in-the-loop confirmation** — deploys via Google/Microsoft/Meta APIs with rollback and sync-back, every action audit-logged. RV's Claude/agentic tooling can drive it via MCP, with writes still passing the confirmation gate.

---

## Appendix — Feature → Service traceability

| Capability (origin) | Service(s) | Screen(s) |
|---|---|---|
| URL→campaign, assets, keywords (GlitchAds) | Generation, Connector | Campaigns (wizard) |
| Daily optimization, alerts (GlitchAds) | Optimization | Home, Campaigns |
| Multi-account, RBAC, bulk ops (GlitchAds) | Identity, (all) | Settings, Campaigns |
| 750+ connectors, pipeline, warehouse (Graphed) | Connector, Ingestion, Warehouse | Connections, Dashboards |
| Specialist agents, plain-English config (Graphed) | Agent Orchestration | Agents |
| Live dashboards, MCP server (Graphed) | Reporting, MCP Server | Dashboards, Settings |
| Connected-context chat (Parallel) | Agent Orchestration, Warehouse | Agent panel |
| Human-in-the-loop approval (Parallel) | Policy & Approval | Approvals |
| Shareable deliverables (Parallel) | Reporting | Deliverables |
| Winning formulas, ad grading (Atria) | Insight & Creative-Intelligence | Creative Studio |
| Variant generation, brief builder (Atria) | Generation | Creative Studio |
| Batch upload, one-click launch (Atria) | Activation | Creative Studio, Campaigns |
| Compounding learnings (Atria) | Insight, Agent memory | Creative Studio, Agents |

