"""Apex seed package.

Modules:
  seed_campaigns  — campaign performance data (20+ DMAs, >=10k rows)
  seed_funnel     — funnel_events (6 stages, >=10k rows)
  seed_cohorts    — cohort_retention (MOB1–MOB12, >=10k rows)
  seed_kpis       — kpi_summary (13 KPIs, >=10k rows)
  validation      — pandera schemas for each table
  run_all         — orchestrator: seeds all tables in dependency order

Quick start:
    python -m src.data.seeds.run_all
"""
