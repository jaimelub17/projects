# Corporate Scorecard (portfolio project)

An end-to-end "governed KPI" data project, built to mirror the work described
in a Senior Data Analyst — Corporate Financial Reporting role at a consumer
wearables company: synthetic hardware + subscription transactional data,
modeled with dbt into audit-ready financial KPI marts with reconciliation
controls. Developed locally on DuckDB, migrated to Databricks (Unity Catalog)
with an executive-facing dashboard on top — totals reconcile across both
engines to the penny. See the build-status checklist in
[`SCHEMA.md`](SCHEMA.md) for exactly what is and isn't in scope.

## Why this exists

I was really excited about this opportunity and wanted to show that I can do the job: take raw transactional data, build a governed KPI layer with tests and documentation, and make it trustworthy enough for a CFO and auditors.

## Stack

- **dbt Core** — staging → marts, tests, docs, one governed-KPI writeup
- **DuckDB** — local dev target (fast iteration, zero infra)
- **Databricks Free Edition** — Unity Catalog, lineage, Databricks SQL dashboard
- **Python** — synthetic data generation, scaled to roughly track a real
  wearables company's public 2024–2025 growth (see `SCHEMA.md`)

## Status

See [`SCHEMA.md`](SCHEMA.md) for the dimensional model and KPI marts this
project builds toward.

## Local setup (Windows cmd)

```cmd
python -m venv venv
venv\Scripts\pip install -r requirements.txt
cd dbt
set DBT_PROFILES_DIR=%cd%
..\venv\Scripts\dbt debug
```
