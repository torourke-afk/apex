# Apex — Paperclip Dev Team Setup Guide

## Prerequisites

Before starting, ensure you have the following installed:

- **Node.js 20+** and **pnpm** (for Paperclip server)
- **Python 3.11+** (for Apex application)
- **Claude Code CLI** (`npm install -g @anthropic-ai/claude-code`)
- **Anthropic API key** with access to claude-sonnet-4-6 and claude-opus-4-6
- **Redis** (optional for dev — Kamino directive bus; can be deferred to Phase 5)
- **Git** (for version control)

## 1. Install Paperclip

```bash
# Clone Paperclip
git clone https://github.com/nicholasgriffintn/paperclip.git
cd paperclip

# Install dependencies
pnpm install

# Copy environment config
cp .env.example .env
```

Edit `.env` and set your Anthropic API key:
```
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

## 2. Set Up the Apex Project

```bash
# Navigate to the Apex project root
cd /path/to/Apex

# Create Python virtual environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows

# Install Python dependencies
pip install -r requirements.txt

# Copy environment config
cp .env.example .env
# Edit .env with your local settings (defaults work for dev)
```

Verify the Streamlit app launches:
```bash
streamlit run src/app.py --server.headless true
# Should start on http://localhost:8501 with all 9 page stubs in sidebar
```

## 3. Link Paperclip to Apex

Copy (or symlink) the `paperclip/` directory from this project into your Paperclip installation's projects folder:

```bash
# From the Paperclip repo root:
ln -s /path/to/Apex/paperclip ./projects/apex
```

Or set the project path in Paperclip's dashboard when you create the project.

## 4. Agent Overview

The team has 5 agents in a reporting hierarchy:

```
Tech Lead (opus) ← heartbeat trigger
├── Frontend Engineer (sonnet) ← task_ready trigger
├── Backend Engineer (sonnet) ← task_ready trigger
├── Data Engineer (sonnet) ← task_ready trigger
└── QA Engineer (sonnet) ← engineer_done trigger
```

| Agent | Model | Budget | Scope |
|-------|-------|--------|-------|
| Tech Lead | claude-opus-4-6 | $500/mo | Planning, architecture, review, coordination |
| Frontend | claude-sonnet-4-6 | $400/mo | Streamlit pages, components, brand CSS |
| Backend | claude-sonnet-4-6 | $400/mo | FastAPI, Pydantic models, DB, simulator engine |
| Data Engineer | claude-sonnet-4-6 | $300/mo | Seed data, ETL pipelines, benchmarks |
| QA | claude-sonnet-4-6 | $250/mo | Testing, verification, brand compliance |

**Total monthly budget: $1,850**

## 5. Task Flow

The workflow follows this cycle:

1. **Tech Lead** reads `tasks/backlog.md` on each heartbeat (every 30 minutes)
2. **Tech Lead** picks the highest-priority TODO item, breaks it into implementation specs, and writes them to `tasks/current/` (e.g., `frontend-scorecard.md`, `backend-data-ingestion.md`)
3. **Engineer agents** (Frontend, Backend, Data Engineer) pick up their assigned specs from `tasks/current/`
4. Each engineer writes their output summary to `tasks/<role>_output.md`
5. **QA** triggers on `engineer_done`, reads all output summaries, runs tests, and writes results to `tasks/qa_results.md`
6. **Tech Lead** reviews QA results: PASSED → moves backlog item to DONE; FAILED → writes a revision spec back to `tasks/current/`

## 6. First Run

Start the Paperclip server and trigger the first heartbeat:

```bash
# From the Paperclip repo:
pnpm dev
```

Open the Paperclip dashboard (default: http://localhost:3000) and:

1. Select the "apex" project
2. The Tech Lead agent will auto-trigger on the first heartbeat
3. It will read `tasks/backlog.md` and pick up item **1.1 — Project Scaffolding & Brand System**
4. It will write implementation specs to `tasks/current/`
5. The engineer agents will pick up their specs and start building

Monitor progress in the dashboard. Each agent writes status updates to the `tasks/` directory.

## 7. Directory Structure

```
Apex/
├── src/
│   ├── app.py                    # Streamlit entry point
│   ├── pages/                    # 9 module pages (numbered)
│   ├── components/               # Reusable UI components
│   ├── config/
│   │   ├── brand.py              # RVGT colors, fonts, CSS
│   │   └── settings.py           # Pydantic BaseSettings
│   ├── models/                   # Pydantic data models
│   ├── api/                      # FastAPI routes
│   ├── data/
│   │   ├── seeds/                # Demo data generators
│   │   ├── etl/                  # Transform pipelines
│   │   ├── benchmarks/           # Industry benchmark tables
│   │   └── validation/           # pandera schemas
│   ├── simulator/                # 5-stage waterfall engine
│   ├── kamino/                   # Directive bus client
│   └── integrations/             # External API connectors
├── tests/                        # Mirrors src/ structure
├── alembic/                      # DB migrations
├── docs/
│   └── architecture.md           # System design (maintained by Tech Lead)
├── paperclip/
│   ├── paperclip.config.json     # Paperclip project config
│   ├── agents/                   # Agent definitions (5 JSON files)
│   ├── tasks/
│   │   ├── backlog.md            # Prioritized work items
│   │   └── current/              # Active task specs
│   └── skills/                   # Agent-specific skills (future)
├── requirements.txt
├── .env.example
└── Apex Build Specification v2.docx  # Master build spec
```

## 8. Key Files for Reference

- **Build spec:** `Apex Build Specification v2.docx` — the master document defining all 9 modules, data contracts, and the 5-phase implementation roadmap
- **Architecture:** `docs/architecture.md` — tech stack, directory conventions, data flow
- **Brand system:** `src/config/brand.py` — all RVGT colors, fonts, and CSS injection
- **Backlog:** `paperclip/tasks/backlog.md` — 20 prioritized work items across 5 phases

## 9. Development Conventions

- **State:** Use `st.session_state` for all cross-page data
- **Caching:** `st.cache_data` for query results, `st.cache_resource` for connections
- **Colors:** Always import from `src/config/brand.py` — never hardcode hex values
- **Models:** All data shapes as Pydantic models in `src/models/`
- **Tests:** Every new module gets unit tests in `tests/` (mirrors `src/` structure)
- **No pure black/white:** Use `COLORS.NEAR_BLACK` (#1A1A2E) and `COLORS.NEAR_WHITE` (#FAFBFC)
- **Chart palette order:** Mahogany → RVGT Red → Onyx → Iron → Alloy

## 10. Monitoring & Cost Control

Each agent has a monthly budget cap with an 80% warning threshold. Monitor usage in the Paperclip dashboard. If an agent hits 80% of its budget, it will log a warning. At 100%, it stops executing.

The scheduler runs a heartbeat every 30 minutes with a max of 3 concurrent agents. Adjust in `paperclip.config.json` if you need to throttle or speed up.
