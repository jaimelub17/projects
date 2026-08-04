# Oura Corporate Scorecard (portfolio project)

A small end-to-end "governed KPI" data project, built to mirror the actual work
described in Oura's Senior Data Analyst — Corporate Financial Reporting JD:
synthetic hardware + subscription transactional data, modeled with dbt into
audit-ready financial KPI marts with reconciliation controls. Currently built
on DuckDB locally; migration to Databricks (Unity Catalog) and an
executive-facing dashboard are the next planned steps — see the build-status
checklist in [`SCHEMA.md`](SCHEMA.md) for exactly what is and isn't done.

## Why this exists

This isn't a resume bullet — it's a working proof of concept that I can do the
job: take raw transactional data, build a governed KPI layer with tests and
documentation, and make it trustworthy enough for a CFO and auditors.

## Stack

- **dbt Core** — staging → marts, tests, docs, one governed-KPI writeup
- **DuckDB** — local dev target (fast iteration, zero infra)
- **Databricks Free Edition** — Unity Catalog, lineage, Databricks SQL dashboard
- **Python** — synthetic data generation, scaled to roughly track Oura's real
  2024–2025 growth (see `SCHEMA.md`)

## Status

See [`SCHEMA.md`](SCHEMA.md) for the dimensional model and KPI marts this
project builds toward, and [`PROJECT_LOG.md`](PROJECT_LOG.md) for a running,
step-by-step record of what was built and why.

## Local setup (Windows cmd)

```cmd
python -m venv venv
venv\Scripts\pip install -r requirements.txt
cd dbt
set DBT_PROFILES_DIR=%cd%
..\venv\Scripts\dbt debug
```
