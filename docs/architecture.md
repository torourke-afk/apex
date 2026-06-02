# Apex — Architecture

## Overview

Apex is an RVGT marketing intelligence platform providing 9 interactive dashboard modules for competitive analysis, campaign performance, and strategic planning. Built on Streamlit with a Python data stack.

## Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| UI Framework | Streamlit (multi-page) | Pages numbered in `src/pages/` |
| Language | Python 3.11+ | |
| Data Processing | pandas | Transformations and aggregation |
| Visualization | Plotly, Altair | Interactive charts |
| Database (dev) | DuckDB | Local file-based, zero config |
| Database (prod) | PostgreSQL | Managed instance |
| API Bus | FastAPI (Kamino) | Inter-service communication |
| Testing | pytest | Unit + integration |

## Directory Structure

```
apex/
├── app.py                    # Streamlit entry point
├── requirements.txt
├── src/
│   ├── config/
│   │   ├── brand.py          # RVGT brand tokens (colors, fonts, spacing)
│   │   └── settings.py       # App-wide settings, env config
│   ├── pages/
│   │   ├── 01_Overview.py
│   │   ├── 02_Market_Intelligence.py
│   │   ├── 03_Campaign_Performance.py
│   │   ├── 04_Competitor_Analysis.py
│   │   ├── 05_Channel_Analytics.py
│   │   ├── 06_Content_Performance.py
│   │   ├── 07_Lead_Pipeline.py
│   │   ├── 08_Budget_Allocation.py
│   │   └── 09_Executive_Summary.py
│   ├── components/           # Reusable Streamlit components
│   ├── data/                 # Data loaders and connectors
│   └── simulator/            # Scenario simulation engines
├── tests/                    # pytest test suite
└── data/
    └── apex.duckdb           # Local dev database
```

## Key Patterns

### State Management
- All cross-page state lives in `st.session_state`.
- Pages read shared state; only the owning page writes it.

### Brand System
- `src/config/brand.py` exports color palette, typography, and spacing tokens.
- All pages import brand tokens — no hardcoded colors.
- **Constraint:** No pure black (`#000000`) or pure white (`#FFFFFF`) anywhere in the UI. Use brand near-black and near-white instead.

### Database Access
- Dev: DuckDB file at `data/apex.duckdb`, initialized by `src/data/init_db.py`.
- Prod: PostgreSQL via connection string in env/settings.
- Data layer abstracts the backend so pages never import DB drivers directly.

### Page Convention
- Files numbered `01_` through `09_` for Streamlit sidebar ordering.
- Each page file is self-contained: imports brand, loads data, renders UI.
- Shared widgets extracted to `src/components/`.

## 9 Dashboard Modules

1. **Overview** — KPI summary, trend sparklines, alerts
2. **Market Intelligence** — Industry trends, market sizing, opportunity mapping
3. **Campaign Performance** — Campaign ROI, A/B results, attribution
4. **Competitor Analysis** — SWOT, positioning maps, share-of-voice
5. **Channel Analytics** — Channel mix, cost-per-acquisition, funnel metrics
6. **Content Performance** — Content engagement, SEO rankings, asset utilization
7. **Lead Pipeline** — Pipeline stages, conversion rates, lead scoring
8. **Budget Allocation** — Spend tracking, budget vs. actual, optimization recs
9. **Executive Summary** — Board-ready rollup, narrative insights, action items
