# Project Log

A running record of what was built, in what order, and *why* — including decisions,
mistakes caught along the way, and the reasoning behind each one. Kept for two reasons:
it's the raw material for explaining this project in an interview, and it's the same
kind of change-log discipline the JD asks for around governed KPIs.

Each entry: what happened, why, what it means going forward.

## Rebuilding this by hand (planned, not started yet)

Once the initial build is finished, the plan is to redo the whole thing by
hand — typing every command and file yourself, with Claude guiding (telling
you what to type and where) rather than executing it directly. This log and
the [Guide artifact](https://claude.ai/code/artifact/55ace1d2-7d62-433f-9944-5ca448f8169e)
exist specifically to make that possible: every step already has the real
commands and the real SQL, in order, copyable.

**To practice from a clean slate when you're ready:**
1. Copy the whole `oura-corporate-scorecard` folder somewhere else (e.g.
   `oura-scorecard-practice`) — this keeps the original as your answer key.
2. In the copy, delete everything generated/gitignored so you're rebuilding
   for real, not just re-running against files that already exist:
   `venv/`, `dbt/*.duckdb`, `dbt/target/`, `dbt/logs/`, `dbt/dbt_packages/`.
3. Also safe to delete the `.sql`/`.yml`/`.py` files themselves if you want
   to type those from scratch too, not just the commands around them —
   the original folder (or `git log`/`git show` in it) is still there to
   check your work against.
4. Work through the Guide top to bottom, one step at a time, typing each
   command and file yourself before checking the answer key.

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

## Step 6 — Staging models, with a real caught-and-fixed test failure

**What we did:** Built one staging model per seed table (`stg_geo`,
`stg_channels`, `stg_products`, `stg_customers`, `stg_orders`,
`stg_subscription_events`, `stg_returns_warranty`) — each does light
cleanup (casting `order_date`/`signup_date`/etc. to real `date` types,
consistent naming), not heavy transformation. Staging's job is to
standardize, not to silently fix business-meaningful data problems.

Added test coverage (`_staging.yml` + one custom singular test) mapped
directly to the seven data-quality issues injected back in Step 4:
`unique`/`not_null` on every primary key, `relationships` tests on every
foreign key, `accepted_values` on `event_type`, and a custom singular test
(`assert_orders_have_positive_values.sql`) checking for the zero/negative
quantity and price rows. Known, tracked issues (nulls, orphaned FKs, bad
values) are set to `severity: warn` — visible, not build-blocking. Genuine
defects get left at the default `error` severity.

**Ran it for real, on purpose, before fixing anything:** `stg_orders.sql`
initially had no deduplication logic. Running `dbt build` produced a real
`FAIL 104 unique_stg_orders_order_id` error — 104 duplicate `order_id`
rows, exactly matching the count of duplicates injected in Step 4. Every
other test landed at its documented count too (209 null geo_id, 64 orphaned
customer_id, 43 bad values, 7 null acquisition_channel_id, 4 orphaned claim
order_id) — confirming the injected issues and the tests built to catch
them actually agree with each other.

**Fixed it:** changed `stg_orders.sql` to `SELECT DISTINCT` (the duplicates
are exact row copies, so a straight distinct removes them without touching
real data). Re-ran `dbt build` — `unique_stg_orders_order_id` now `PASS`,
zero errors, only the intentionally-tracked warnings remain.

**Why this sequence matters:** this is the actual demonstration promised in
`SCHEMA.md` — a real failing test, explained, with a real fix and a re-run
proving it worked. Not narrated, not simulated.

**The SQL** (all seven staging models are this same shape — read from the
seed, rename/cast, nothing fancier; `stg_orders` is the one with `DISTINCT`
added after the failure above):

```sql
-- stg_orders.sql (final, post-fix)
select distinct
    order_id,
    customer_id,
    product_id,
    cast(order_date as date) as order_date,
    geo_id,
    channel_id,
    quantity,
    unit_price,
    unit_cost,
    discount_amount
from {{ ref('seed_orders') }}
```

```sql
-- stg_customers.sql
select
    customer_id,
    cast(signup_date as date) as signup_date,
    geo_id,
    acquisition_channel_id
from {{ ref('seed_customers') }}
```

```sql
-- stg_subscription_events.sql (deduplicated up front, no fail/fix demo needed twice)
select distinct
    event_id,
    customer_id,
    cast(event_date as date) as event_date,
    event_type,
    plan_price,
    mrr_delta
from {{ ref('seed_subscription_events') }}
```

```sql
-- stg_returns_warranty.sql
select
    claim_id,
    order_id,
    cast(claim_date as date) as claim_date,
    claim_type,
    resolution,
    cost_to_company
from {{ ref('seed_returns_warranty') }}
```

`stg_geo`, `stg_channels`, `stg_products` are each a plain `select` of every
column, unchanged, from their seed — no cleanup needed, so no transformation
to show.

The one custom test (a "singular test" — a raw SQL query that should return
zero rows; contrast with the generic `not_null`/`unique`/`relationships`
tests declared in YAML):

```sql
-- tests/assert_orders_have_positive_values.sql
{{ config(severity='warn') }}

select *
from {{ ref('stg_orders') }}
where quantity <= 0 or unit_price <= 0
```

---

## Step 7 — SCD Type 2 via dbt snapshot

**What we did:** Built `snapshots/customer_snapshot.sql` using dbt's native
snapshot feature (`strategy='check'`, watching `geo_id` and
`acquisition_channel_id` for changes), sourced from `stg_customers`.

Ran `dbt snapshot` once — captured all 2000 customers as version 1
(`dbt_valid_from` = now, `dbt_valid_to` = null).

To prove the mechanism actually works rather than just exist as a schema
mockup, directly updated `geo_id` for 3 customers (10, 20, 30) in the live
DuckDB table — simulating what a real address-change sync from a source
system would look like between two snapshot runs. Ran `dbt snapshot` again:
dbt detected the changed `check_cols` for those 3 customers, closed out
their old rows (`dbt_valid_to` set to the second run's timestamp), and
inserted new current rows. The other 1997 customers were untouched — still
exactly one row each. Table went from 2000 to 2003 rows, confirmed by
direct query.

**Known artifact of this demo:** the geo_id change was made directly against
the live DuckDB table, not the seed CSV. If `dbt seed` is re-run, `geo_id`
for customers 10/20/30 will revert to their original seed values, which
would register as a *third* change on the next `dbt snapshot` run. This is
expected and fine — it's a one-time simulation to prove the mechanism, not
a permanent generator change. Documented here so it isn't confusing later.

**Why this matters for the JD:** this directly demonstrates "slowly-changing
dimensions for org/cost-center hierarchies" — same mechanism, different
attribute. `dim_customer` (once built) will source from `customer_snapshot`
instead of `stg_customers` directly, so historical reports stay accurate
even as customers move regions.

**The SQL** — the entire mechanism is declared in a `config()` block, not
hand-written history logic:

```sql
-- snapshots/customer_snapshot.sql
{% snapshot customer_snapshot %}

{{
    config(
      target_schema='main',
      unique_key='customer_id',
      strategy='check',
      check_cols=['geo_id', 'acquisition_channel_id'],
    )
}}

select
    customer_id,
    geo_id,
    acquisition_channel_id
from {{ ref('stg_customers') }}

{% endsnapshot %}
```

`strategy='check'` tells dbt "compare `check_cols` between what the source
looks like right now and what's already stored — if either value differs
from the current version, close it out and insert a new one." Everything
else (`dbt_valid_from`, `dbt_valid_to`, `dbt_scd_id`) is generated
automatically; nothing here hand-writes the history logic.

---

## Step 8 — Remaining dimension models

**What we did:** Built the rest of the dimension layer: `dim_date` (a real
day-grain date spine, 2024-01-01 through 2025-12-31, with year/quarter/
month/week/fiscal_period columns via DuckDB's `generate_series`), plus
straightforward `dim_product`, `dim_geo`, `dim_channel` pass-throughs from
staging, and `dim_customer` -- built from `customer_snapshot` (not
`stg_customers` directly) so it carries full SCD Type 2 history. Used dbt's
built-in `dbt_scd_id` column as the dimension's surrogate key rather than
hand-rolling one. Added tests: `dim_customer.customer_sk` is unique (one row
per *version*), `customer_id` is intentionally NOT unique (by design -- SCD2).

**Verification:** `dbt build` — 54 total nodes, 49 pass, 5 expected warnings
(same tracked counts as Step 6), 0 errors.

**The SQL:**

```sql
-- dim_date.sql -- a real date spine, generated, not hand-typed
with spine as (
    select unnest(generate_series(
        date '2024-01-01', date '2025-12-31', interval 1 day
    )) as date_day
)

select
    cast(strftime(date_day, '%Y%m%d') as integer) as date_id,
    date_day,
    extract(year from date_day) as year,
    extract(quarter from date_day) as quarter,
    extract(month from date_day) as month,
    extract(week from date_day) as week,
    'FY' || extract(year from date_day) || '-Q' || extract(quarter from date_day) as fiscal_period
from spine
```

```sql
-- dim_customer.sql -- the SCD2 payoff: built on the snapshot, not stg_customers
select
    dbt_scd_id as customer_sk,
    customer_id,
    geo_id,
    acquisition_channel_id,
    dbt_valid_from as valid_from,
    dbt_valid_to as valid_to,
    (dbt_valid_to is null) as is_current
from {{ ref('customer_snapshot') }}
```

```sql
-- dim_product.sql / dim_geo.sql / dim_channel.sql -- all three are this same
-- plain pass-through shape, just a straight select from staging
select
    product_id,
    ring_model,
    color,
    list_price,
    unit_cost
from {{ ref('stg_products') }}
```

---

## Step 9 — Caught and fixed an instability in the SCD2 demo

**What happened:** Running `dbt build` again (which always re-runs `dbt seed`
first) reloaded `seed_customers.csv` from disk -- silently reverting the
live-only database mutation from Step 7. The next `dbt snapshot` then saw
that as *another* change and added a third row for customers 10/20/30,
turning a clean 2-version history into a confusing 3-version one. This is
exactly the risk flagged (but not yet fixed) at the end of Step 7.

**Why it mattered:** every future `dbt build` for the rest of this project
would have kept corrupting this table. Not an acceptable state to build on.

**Fixed by making the change permanent and durable instead of a one-time
live mutation:**
1. Dropped `customer_snapshot`, reseeded from the still-original CSV, and
   ran `dbt snapshot` once to capture a clean baseline (customers 10/20/30
   at their original geo_id).
2. Edited `dbt/seeds/seed_customers.csv` directly -- permanently setting
   `geo_id = 5` for customers 10, 20, 30. This is now the tracked, real
   ground truth, not a throwaway mutation.
3. Reseeded and ran `dbt snapshot` again -- captured exactly one clean
   transition per customer (2000 -> 2003 rows, same as Step 7's result).
4. Ran `dbt build` a second time to confirm stability: row counts held
   exactly steady (2003), proving no further drift on repeated builds.

**Worth knowing:** because the change now lives in the CSV, reading
`seed_customers.csv` alone only ever shows the *current* state (geo_id=5) --
the fact that these customers ever lived elsewhere is only visible in
`customer_snapshot`'s history. That's not a limitation, it's the actual
point of Type 2 SCDs: the source system only ever holds "now," and the
snapshot is the only place "then" survives.

---

<!-- New entries get appended below as each day's work happens. -->
