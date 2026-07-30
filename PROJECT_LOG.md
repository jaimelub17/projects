# Project Log

A running record of what was built, in what order, and *why* — including decisions,
mistakes caught along the way, and the reasoning behind each one. Kept for two reasons:
it's the raw material for explaining this project in an interview, and it's the same
kind of change-log discipline the JD asks for around governed KPIs.

Each entry: what happened, why, what it means going forward.

---

## Step 1 — Environment setup

**What we did:** Installed Python 3.12 (not previously on the machine — only a
Microsoft Store stub existed). Created a project-local virtual environment
(`venv/`) and installed `dbt-core` + `dbt-duckdb`. Initialized a git repo.
Scaffolded the dbt project (`dbt_project.yml`, `profiles.yml`) targeting DuckDB
as a local, zero-infrastructure dev database. Ran `dbt debug` to confirm the
project and database connection were both wired correctly before writing anything.

**Why:** DuckDB lets us iterate on the data model fast with no signups or cloud
setup, while still writing real dbt/SQL — the same SQL will later point at
Databricks with no rewrite needed, just a different `profiles.yml` target.

**Also produced:** `SCHEMA.md` v1 — the dimensional model (dims, facts, KPI
marts) sketched out *before* any data or SQL was written.

---

## Step 2 — Synthetic data generation (v1)

**What we did:** Wrote `data_gen/generate_data.py` to fabricate 7 seed CSVs:
geo, channels, products, customers, orders, subscription events, warranty
claims. Ran `dbt seed` to load them into DuckDB as real tables.

**Why:** There's no real Oura data available (private company), so a synthetic
dataset stands in for what would normally already exist in NetSuite/Zuora/etc.
Volumes and growth were parameterized to loosely match Oura's real public
numbers (~2x YoY revenue growth, ~80/20 hardware/subscription split).

**Caught a mistake:** A quick sanity-check query showed revenue only grew
~1.5x year over year, not the targeted ~2x. Root cause: a monthly compounding
growth rate (3.5%/month) that doesn't actually reach 2x/year when compounded
over 12 months. Fixed the rate (5.95%/month) and re-verified before moving on.
**Lesson applied:** verify output against a known expectation before building
anything on top of it — don't trust a script just because it ran without errors.

---

## Step 3 — Critical review: is this data good enough?

**What we did:** Before building anything on top of the seed data, stepped back
and asked whether it was realistic enough to be worth building on, and whether
a real open dataset (e.g. Olist Brazilian e-commerce, UCI Online Retail II)
would be a stronger foundation.

**Decision — kept the synthetic approach, but committed to hardening it.**
Reasoning: no open dataset maps onto a hardware+subscription hybrid business
without still needing synthetic data bolted on top, and well-known public
datasets (Olist especially) risk looking like a relabeled stock dataset to
anyone who recognizes them — worse for credibility than honestly-synthetic
data. The actual problems with the v1 data weren't "not real enough" so much
as "too clean and too simplistic" — fixable directly.

---

## Step 4 — Hardening the data generator

**What we did, and why each change was made:**

1. **Retention/hazard churn curve, not a flat monthly probability.**
   Real subscription churn is highest in a customer's first 1-2 months (12%,
   8%) and declines with tenure (down to a 2% floor after month 6). A flat
   rate doesn't reflect real subscription-business behavior and wouldn't hold
   up if asked about churn modeling directly.
2. **Hardware margin benchmarked, not guessed.** Oura doesn't publish
   financials, so unit costs were set to produce a ~57% gross margin,
   benchmarked against Garmin's real Fitness segment gross margin (59%,
   Q4 2025 10-K/earnings release) — the closest available public comparable.
3. **Seven categories of data-quality issues injected on purpose, at known
   rates:** null geo_ids, orphaned customer_ids, zero-value rows, duplicate
   order rows, null acquisition channels, duplicate subscription events,
   orphaned claim references. Reasoning: a dataset with zero data-quality
   issues gives `dbt test` nothing real to catch, which undercuts the entire
   "governed, audit-grade" premise of the project. Each issue simulates a
   specific realistic failure mode (e.g. "pipeline replay bug," "webhook
   double-fire") documented with exact counts in `SCHEMA.md`.

**Verification:** Re-ran the generator, reloaded seeds with
`dbt seed --full-refresh`, and directly queried DuckDB to confirm each
injected issue actually landed (duplicate `order_id` count, null `geo_id`
count via `IS NULL` after learning DuckDB auto-casts empty CSV strings to
NULL in numeric columns, orphaned FK counts via `LEFT JOIN ... IS NULL`).
Confirmed revenue growth was still ~2x YoY after all changes.

---

## Step 5 — Doc/reality reconciliation

**What we did:** Reviewed `SCHEMA.md` critically against what was actually
built and found two mismatches:
1. `fct_subscription_events` doc said `event_type (signup/renew/cancel)`, but
   the generator only ever produces `signup`/`cancel` (renewal events were
   deliberately skipped since MRR is a running total of `mrr_delta` and a
   renewal row adds no information). **Fixed** the doc to match reality.
2. `dim_date` was listed in the schema design but never actually built.
   **Decision:** keep it in scope rather than quietly drop it — added it to
   an explicit "Build status" checklist in `SCHEMA.md` for Day 3-4, since the
   JD specifically calls out "period-over-period comparisons," which needs a
   real date dimension (fiscal periods, quarters) to do properly.

**Why this step matters:** documentation that drifts from what's actually
implemented is exactly the kind of thing external auditors flag. Catching and
fixing it here is a small, concrete example of the same discipline.

---

<!-- New entries get appended below as each day's work happens. -->
