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

## Plain-language glossary

Every term used in this log, defined once. If a step below reads as
jargon, the answer is probably here.

**Tools & environment**
- **dbt (data build tool):** the framework this whole project is built in.
  Each transformation is a plain SQL `SELECT` in its own file; dbt figures
  out build order, creates the tables, runs the tests, and generates docs.
- **model:** one `.sql` file containing one `SELECT`. dbt turns it into a
  table or view in the database.
- **seed:** a CSV file that `dbt seed` loads into the database as a table.
  Here, seeds stand in for data an ingestion tool (Fivetran) would land.
- **snapshot:** dbt's built-in history keeper — each run records what
  changed since the last run. The mechanism behind our SCD Type 2.
- **test:** *generic* tests are declared in YAML (`unique`, `not_null`,
  `relationships`, `accepted_values`); *singular* tests are hand-written
  SQL queries that must return zero rows.
- **severity (warn vs error):** an `error` test failure stops the build; a
  `warn` reports and continues. Known, tracked data issues are warn here;
  hard invariants (reconciliation) are error.
- **DuckDB:** a database engine that runs as one local file — our fast,
  zero-setup development target.
- **Databricks / Unity Catalog:** the cloud data platform (and its
  governance layer) the project migrated to; our tables live under
  `workspace.oura_scorecard`.
- **venv:** an isolated Python environment so this project's packages
  can't collide with anything else on the machine.
- **.env:** a gitignored file holding connection settings — the pattern
  that keeps anything workspace-specific or secret out of git history.
- **OAuth:** login-in-the-browser authentication; nothing long-lived is
  stored on disk.
- **execution policy:** the Windows security default that blocks `.ps1`
  scripts; `.cmd` batch files aren't subject to it (see Step 16).

**Modeling**
- **dimensional model / star schema:** facts (events — orders, claims,
  subscription events) surrounded by dimensions (context — customer,
  product, date, geo, channel).
- **grain:** what one row means in a table (one order line, one claim,
  one month). The first question to ask of any table.
- **staging layer (`stg_*`):** the first cleanup layer — rename, cast
  types, deduplicate. It standardizes; it never silently fixes
  business-meaningful problems.
- **mart:** a final, consumption-ready table that serves a governed KPI.
- **natural vs surrogate key:** natural = the business's own id
  (`customer_id`); surrogate = a per-version key (`customer_sk`) so that
  history can hold several rows for the same natural key.
- **SCD Type 2:** keeping dimension history by *adding a new row* (with
  `valid_from`/`valid_to`) instead of overwriting — so old reports stay
  reproducible.
- **lineage:** the traceable path from raw source to executive number.
- **unknown member / late-arriving dimension / late-arriving fact:**
  standard patterns for nulls and orphans — see the practice backlog.
- **right-censoring:** recent periods look incomplete because their events
  (e.g. warranty claims) haven't happened yet. A real reporting
  phenomenon, not a bug (Step 12).

**Finance**
- **Revenue / COGS / gross profit / gross margin %:** sales in dollars /
  direct cost of the goods sold / the difference / the difference as a
  percent of revenue.
- **MRR / ARR:** monthly recurring revenue (active subscribers × monthly
  price — an operating metric, not GAAP revenue); ARR = MRR × 12.
- **churn rate:** cancels this month ÷ active subscribers at the start of
  the month.
- **reconciliation:** proving two independently computed versions of the
  same number agree — our error-severity controls do this on every build.
- **governed KPI:** a metric treated as a contract: locked definition,
  single owner, tests protecting it, sign-off, and a change log
  (`governed_kpis/gross_margin.md` is the worked example).

---

## Promotion workflow — how a change reaches both engines

Nothing syncs automatically. DuckDB and Databricks are two separate copies
of the outputs, both built from one source of truth: this repo (model SQL +
seed CSVs). Neither database is ever edited directly — change the source,
rebuild each target, verify they agree. Always local first (feedback in
seconds), then Databricks.

```
local:      cd dbt  ->  dbt build          (DBT_PROFILES_DIR set to dbt/)
databricks: .\dbt-databricks.cmd build     (from the repo root)
```

**When to do what — by the kind of change you made:**

| What changed | Then run (locally first, then Databricks) |
|---|---|
| A model's SQL (`stg_*`, `dim_*`, `fct_*`, `mart_*`) | `dbt build --select <model>+` — the `+` also rebuilds everything downstream of it |
| Tests (rules in `.yml`, or `tests/*.sql`) | `dbt build --select <model>`, or just `dbt test --select <test_name>` |
| Seed CSV *rows* (e.g. the SCD2 geo edit) | `dbt seed --select <seed>` → `dbt snapshot` **if** `seed_customers` changed (the snapshot watches geo/channel) → `dbt build` |
| Seed CSV *columns* (schema change) | `dbt seed --full-refresh` → `dbt build` |
| Full data regeneration (`generate_data.py` re-run) | The full dance, per engine: drop the snapshot table → `dbt seed --full-refresh` → `dbt snapshot` (clean baseline) → re-apply the customers 10/20/30 geo edit to the CSV → `dbt seed --select seed_customers` → `dbt snapshot` → `dbt build`. (Steps 9/11/12 lesson: regenerated values register as spurious customer "changes" unless the snapshot is re-baselined.) |
| Docs only (`.md` files, `.yml` descriptions) | Nothing to rebuild — `dbt docs generate` to refresh the docs site |
| Connection config (`.env`, `profiles.yml`) | Nothing to rebuild — `dbt debug` to verify the connection still works |

**Always finish a data change with the reconciliation habit:** re-run the
Step 17 fingerprint on both engines and confirm they still agree.

**Real-company mapping:** the "then Databricks" step wouldn't be a human
typing a command — CI runs the build on every pull request, and a
scheduler rebuilds production nightly after ingestion lands. This manual
two-step is the honest local-scale version of that; knowing what the
automation would replace is the point.

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

## Step 10 — Fact tables, and a real SCD2 join design decision

**What we did:** Built `fct_orders`, `fct_subscription_events`, and
`fct_returns_warranty`, joining the staging tables to the dimensions built
in Step 8.

**The design decision that mattered:** the textbook SCD2 fact join matches
each transaction to the dimension version whose `valid_from`/`valid_to`
range covers the transaction's date. That doesn't work here — our snapshot
history only started existing in dev-time (2026-07-30), while every
`order_date`/`event_date` is from 2024-2025, entirely *before* tracking
began. Every `dbt_valid_from` timestamp is later than every transaction
date, so a naive range join would match zero rows for every single record.
Caught this before writing the join, not after debugging an all-null
`customer_sk` column. Used each customer's **earliest known version**
instead — the closest available approximation of "their state during
2024-2025" given what the data actually supports — and documented the
tradeoff directly in `fct_orders.sql` as a comment, not just in this log.

**Verified (per the quality-check standard):**
1. **Connections resolve correctly:** `dbt build` — 71 nodes, 64 pass, 7
   warnings, 0 errors. Every warning traces to an already-tracked upstream
   gap (7 null channel, 43 bad values, 207 null geo at staging; the 64
   orphaned-customer orders correctly propagate to a null `fct_orders.
   customer_sk`, not silently dropped or defaulted).
2. **The earliest-version join actually does what it's supposed to:**
   queried orders for customers 10/20/30 (the customers moved in Step 9) —
   every one of their orders resolves to `customer_sk` for their *original*
   region (`is_current = false`), not their current one. Confirms the join
   picks the pre-move version, as intended.
3. **Numbers sanity-checked against a known reference, and a real
   discrepancy got chased down, not shrugged off:** total revenue through
   `fct_orders` is $7,591,511.85 (20,973 rows). Raw `seed_orders` (which
   still contains the 104 duplicate rows from Step 4) totals $7,627,034.20
   — a $35,522.35 gap that exactly equals the duplicated rows' value.
   Confirms the Step 6 dedup fix is correctly reflected all the way through
   to the final fact table, and that the join introduces no fan-out
   (`fct_orders` row count and revenue match `stg_orders` exactly).

**The SQL:**

```sql
-- fct_orders.sql
with earliest_customer_version as (
    select customer_id, min(valid_from) as first_valid_from
    from {{ ref('dim_customer') }}
    group by customer_id
)

select
    o.order_id,
    d.date_id,
    c.customer_sk,
    o.product_id,
    o.geo_id,
    o.channel_id,
    o.quantity,
    o.unit_price,
    o.unit_cost,
    o.discount_amount,
    round(o.quantity * o.unit_price, 2) as revenue,
    round(o.quantity * o.unit_cost, 2) as cogs
from {{ ref('stg_orders') }} o
left join {{ ref('dim_date') }} d
    on o.order_date = d.date_day
left join earliest_customer_version ecv
    on o.customer_id = ecv.customer_id
left join {{ ref('dim_customer') }} c
    on ecv.customer_id = c.customer_id
    and ecv.first_valid_from = c.valid_from
```

`fct_subscription_events.sql` uses the identical `earliest_customer_version`
pattern for the same reason. `fct_returns_warranty.sql` is simpler — just a
join to `dim_date` on `claim_date`, no customer dimension involved.

---

## Step 11 — Data realism audit: found 3 structural flaws, rebuilt the generator

**What we did:** Before building the KPI marts, audited the synthetic data
against Oura's actual published economics — not just "does it build" but
"would a Finance interviewer who computed unit economics from these marts
believe them." Ran six checks; three failed badly:

| Check | Was | Real Oura / target | Verdict |
|---|---|---|---|
| Revenue growth | ~2.0x YoY | ~2x YoY | pass |
| Gross margin | 55.6% | ~57-59% (Garmin comp) | pass |
| Average order value | $362 | ring ASP $299-499 | pass |
| Claim rate | ~2.9% | 1-3% consumer electronics | pass |
| Orders per customer | **10.2** | ~1.1 (people buy one ring) | **fail** |
| 2025 hardware/sub split | **98.9 / 1.1** | ~80 / 20 | **fail** |
| Orders before customer existed | **5,656 (27%)** | 0 | **fail** |
| Units per subscriber | **16.4 : 1** | ~1.1 : 1 | **fail** |

**Root cause (one flaw, three symptoms):** the v2 generator created a fixed
pool of 2,000 customers *independently* of orders, then scattered 21K orders
across them at random. Customer count was decoupled from order volume
(-> 10.2 rings each), subscriptions scaled with the tiny customer pool
while units scaled with orders (-> membership business 20x too small), and
signup dates had no relationship to purchase dates (-> 27% of orders
predate their customer). Our own SCHEMA.md claimed an "~80/20 mix" the data
never delivered — the same doc-vs-reality drift we've caught elsewhere,
this time in the foundation.

**The fix (generator v3):** invert the dependency — customers are now
*derived from orders*:
1. Orders are generated first, chronologically, from the growth curve.
2. ~90% of orders create a new customer; ~10% are repeats (biased toward
   early customers, who realistically upgrade Gen3 -> Ring 4). Result:
   18,860 customers, 1.11 orders/customer.
3. `signup_date` = first order date; subscription attaches 0-30 days
   *after* the first ring purchase (a membership without a ring makes no
   sense) at a 90% attach rate.

**Documented honest deviation:** the 2025 subscription share lands at 9.0%,
not Oura's real ~20% — a 2-year window only accumulates 2 years of
membership cohorts, while Oura's real share sits on cohorts from many more
years of ring sales. Documented in SCHEMA.md rather than distorting churn/
attach/pricing to force the ratio.

**Cascade handled:** regenerating the CSVs wiped the Step 9 SCD2 state, so
the demo was redone with the same documented two-phase procedure (drop
snapshot -> baseline snapshot of 18,860 customers -> permanent CSV edit
moving customers 10/20/30 to geo_id 5 -> reseed -> second snapshot).
Result: 18,863 rows, exactly 2 versions per moved customer. All injected
DQ counts changed with the new volumes (206 null geo, 70 orphan customers,
48 bad values, 104 dup orders, 114 null channels, 161 dup signups, 9 orphan
claims) — SCHEMA.md table updated to match.

**Verified (quality-check standard):**
1. `dbt build`: 71 nodes, 64 pass, 7 warnings, 0 errors — and every warning
   count matches the generator's injection log exactly.
2. Re-ran the full audit: orders/customer 1.11 (median 1, max 5), sub share
   9.0%, orders-before-signup 0, units/subscriber 1.4:1.
3. Regression checks: growth still 2.0x ($2.54M -> $5.06M), margin 55.5%,
   fct_orders row count matches stg_orders exactly (no join fan-out), and
   the raw-vs-fct revenue gap ($36,405.15) is exactly the 104 duplicate
   rows the staging layer removes.

**Why this step matters for the interview:** "I audited my own synthetic
data against the company's real economics, found the subscription business
was 20x too small and customers owned 10 rings each, traced both to one
structural root cause, and rebuilt it" is the governed-KPI ethos applied
to my own work — the numbers have to survive scrutiny, including mine.

---

## Step 12 — KPI marts with reconciliation controls, plus one more artifact caught

**What we did:** Built the three governed KPI marts the project exists for,
all at month grain:
- `mart_revenue_summary` — revenue, COGS, gross profit, gross margin %,
  units sold, plus MoM/YoY period-over-period columns (window functions
  over the month spine — scorecards are always read against a prior period).
- `mart_subscription_metrics` — new/churned/active subscribers, MRR, ARR,
  churn rate. Churn uses beginning-of-month actives as the denominator (the
  standard definition — which is why both `_bom` and `_eom` columns exist).
  The model comment states explicitly that MRR here is an operating metric,
  not ASC 606 GAAP-recognized revenue.
- `mart_warranty_rate` — monthly warranty rate, documented as a PERIOD rate
  (vs a cohort rate, which a warranty-cost deep-dive would use).

**Beyond generic tests — reconciliation controls (error severity):**
1. `assert_mart_revenue_reconciles_to_fct` — the scorecard revenue total
   must tie back to `fct_orders` to the penny. If the number leadership
   sees diverges from what the transactions support, the build fails.
2. `assert_mrr_ties_to_active_subscribers` — MRR must equal active
   subscribers x $5.99 every month. The two figures come from different
   columns of the same events, so drift between them means a calc bug.
These are the JD's "reconciliation" requirement in working form — and
unlike the warn-severity data-quality tests, they hard-fail the build.

**Quality-check pass, and what it caught:** read the actual numbers, not
just test results. Revenue: Nov +62% MoM (seasonality), YoY ~100% (the 2x
growth), margin stable ~55.5%. Subscriptions: actives 727 -> 11,100, MRR
ends at $66,489 (= 11,100 x $5.99 exactly), churn matures from 11% to
~4.7% as the base's tenure mix ages — the retention curve visible in
aggregate. But **December 2025's warranty rate read 3.11% — double the
~1.5% norm.** Root cause: the generator *clamped* claims landing after the
data window back to Dec 31, piling ~a month of future claims into December.
Real data does the opposite — unfiled claims simply don't exist yet, so
recent months read LOW (right-censoring), a real phenomenon Finance calls
"immature" warranty rates. Fixed the generator to censor instead of clamp;
December now reads 1.53%.

**Second-order ripple handled:** the one-line generator fix shifted the RNG
sequence downstream, changing *which* customers got null channels (114 ->
100, different rows). Since `acquisition_channel_id` is a snapshot
check_col, the old SCD2 baseline would have logged hundreds of spurious
"changes" — so the snapshot was rebuilt from scratch via the documented
two-phase procedure (baseline 18,860 -> permanent CSV edit for customers
10/20/30 -> 18,863 rows, 2 versions each). SCHEMA.md DQ counts updated
(claims 571 total, 7 orphaned, 100 null channels).

**Verified:** full `dbt build` — 90 nodes, 83 pass, 7 warnings (each
matching the generator's injection log exactly), 0 errors. Both
reconciliation controls pass. Snapshot stable at 18,863 across rebuilds.

---

## Step 13 — Full-system verification audit (34 checks, every layer)

**What we did:** Stepped back and verified the entire system end to end —
not the incremental per-step checks, but everything at once, including the
things "already verified" in earlier steps (trust, but re-verify after 12
steps of churn). Five layers:

- **A. Row-count lineage (12 checks):** every row accounted for from seed
  to mart. seed_orders 21,021 = stg 20,917 + 104 dups; fct = stg exactly
  (no join fan-out); snapshot 18,863 = 18,860 customers + 3 moves;
  sub events 21,287 = 21,126 + 161 dups; claims 571 identical at all
  layers; dim_date 731 days; 24 months in every mart.
- **B. Documented DQ counts vs live data (6 checks):** every count in
  SCHEMA.md's injection table re-queried against the database — all match
  (206, 70, 48, 104, 100, 7).
- **C. Financial recomputation via independent paths (7 checks):** mart
  revenue == fct == stg qty x price ($7,599,897.60 at all three layers);
  gross profit ties; final MRR ($66,489) recomputed from raw staging
  events bypassing the marts entirely — matches; the Dec-25 YoY column
  matches a hand recompute (101.3%).
- **D. SCD2 integrity (5 checks):** exactly 3 customers with exactly 2
  versions, nobody with more, exactly one current row per customer, zero
  gaps between version windows (v1.valid_to == v2.valid_from), and the 70
  null customer_sk rows in fct_orders are exactly the 70 known orphans.
- **E. FK coverage (4 checks):** every date, product, and non-null
  customer key in the fact tables resolves to its dimension.

**Result: 34 of 34 checks pass.** Plus a fresh `dbt build` stability run
first: 90 nodes, 83 pass, 7 known warnings, 0 errors — identical to the
previous run, no drift.

**Docs-vs-reality findings (4 caught, all fixed):**
1. The Guide's commit log was missing 2 commits (33fee81, c192abb — the
   two doc-only commits) and claimed "9 commits" when git shows 11.
2. The Guide's "70 files changed" stat was a drifted estimate; the real
   unique-file count is 45. Relabeled to "files in repo" and corrected.
3. README claimed the project is "deployed on Databricks (Unity Catalog)
   with an executive-facing dashboard" — present tense for work that
   hasn't happened. Reworded to point at the build-status checklist.
4. README's setup snippet ran `venv\Scripts\dbt debug` *after* `cd dbt` —
   a path that doesn't exist from inside dbt/. Anyone following the README
   verbatim would hit an error. Fixed to `..\venv\`.

**Why this step exists:** the incremental checks each verified the piece
being built; this pass verified the *joints between* pieces and the claims
the docs make about the whole. The four findings were all in the docs, not
the data — consistent with the project's recurring lesson that
documentation drift is the failure mode that sneaks through.

---

## Step 14 — dbt docs site + the governed-KPI one-pager

**What we did (two deliverables):**

1. **Generated and served the dbt documentation site.** `dbt docs generate`
   compiles every model/column description and test from the `.yml` files
   we've maintained since Step 6, queries the live database for schema
   stats, and produces a searchable static site with a clickable lineage
   graph (`target/index.html` + `catalog.json`). Served locally with
   `dbt docs serve --port 8080`. Verified in the browser: model pages
   render with descriptions, columns, and test markers; the lineage graph
   opens with all 11 models as nodes. This is the JD's "full lineage to
   source systems" as a working, screenshot-able artifact — and it cost
   zero extra writing, because it's generated from documentation that
   already existed. That's the point worth making in the interview: docs
   that live next to the code get maintained; docs that live in a wiki
   drift (as Step 13 demonstrated with our own README).

2. **Wrote the governed-KPI one-pager** — `governed_kpis/gross_margin.md`,
   the artifact SCHEMA.md has promised since Day 1. It locks Gross Margin's
   definition the way the JD describes ("locked definitions, single owner,
   formal sign-off, documented change-management"): formula, explicit
   in/out-of-scope decisions (returns NOT netted, no warranty reserve in
   COGS — each a real definitional choice documented rather than implied),
   full lineage, the table of dbt controls protecting the number (with
   severity and what each prevents), a change-management process, a
   versioned change log, and known limitations on the record — including
   *why* realized margin (55.5%) runs below the benchmark-derived list
   margin (~57%): discount mix, quantified and explainable.

**Why the one-pager matters most:** anyone can compute a margin. The
one-pager demonstrates understanding that a governed KPI is a *contract* —
what's in, what's out, who owns it, what protects it, and how it changes —
which is the actual job described in the JD.

**Verified:** docs site loads and renders (screenshot in session), lineage
graph opens with all nodes; `catalog.json` written clean; one-pager's
control table cross-checked against the live test suite (every named test
exists and runs at the stated severity).

---

## Step 15 — Databricks migration prep (connection pending)

**What we did:** everything migration-related that doesn't require the
workspace connection yet:

1. **Installed `dbt-databricks`** (1.12.3) alongside `dbt-duckdb` in the
   same venv — one project, two adapters.
2. **Added a `databricks` target to `profiles.yml`** — catalog `workspace`,
   schema `oura_scorecard`, `auth_type: oauth`. Host and HTTP path come
   from `env_var()` so nothing workspace-specific enters git; auth is
   OAuth (browser login on first run), so **no long-lived token is stored
   anywhere at all**. profiles.yml was safe to commit when it held only a
   local file path; the moment real infrastructure enters the picture,
   secrets discipline starts — the same reason the JD cares about SOX and
   audit trails.
3. **Added `.env.example` + `dbt-databricks.ps1`** — a one-line runner
   that loads the gitignored `.env` and runs any dbt command with
   `--target databricks`.
4. **Portability audit of every model.** Findings: everything is
   engine-neutral except `dim_date.sql` (DuckDB's `generate_series` +
   `unnest` vs Spark's `sequence` + `explode`, and `strftime` vs
   `date_format`) and the snapshot's hardcoded `target_schema='main'`
   (a DuckDB default that would create a stray schema on Databricks).
   Fixed: the spine branches on `target.type` (the one honestly
   dialect-specific piece of SQL in the project), `date_id` became plain
   arithmetic (year x 10000 + month x 100 + day — no dialect functions at
   all), and the snapshot config lets each target use its own default
   schema.

**Note for the migration itself:** the SCD2 history (18,863 rows including
the 3 moved customers' 2 versions) lives in DuckDB dev-time state. On
Databricks the snapshot starts fresh from the current CSV — 18,860
customers at one version each. That's normal and honest: a migration
carries the *pipeline*, not one dev environment's accumulated history.

**Verified:** full DuckDB `dbt build` after all changes — 90 nodes, 83
pass, 7 known warnings, 0 errors. `date_id` values identical under the new
arithmetic (spot-checked 20240101, 20240102). Snapshot stable at 18,863.

---

## Step 16 — Databricks migration: same SQL, same results, to the penny

**What happened, in order:**

1. **First connection attempt failed** — Windows' default execution policy
   (Restricted) refused to run the `.ps1` runner script. Fixed by
   converting the runner to a `.cmd` batch file (not subject to execution
   policy) rather than loosening the security setting itself — a scoped
   workaround beats weakening a machine-wide default.
2. **OAuth login completed by the user in their own browser** — no tokens
   stored, credential cached locally by the Databricks SDK.
   `dbt debug --target databricks`: All checks passed.
3. **Full `dbt build` against Databricks Free Edition** (Unity Catalog,
   `workspace.oura_scorecard`, serverless SQL warehouse): **90 nodes — 83
   pass, 7 warnings, 0 errors.** Every warning count identical to the
   DuckDB build (100, 206, 70, 48, 7, 70, 7) — the same tests catching the
   same injected issues on a completely different engine.
4. **The `dim_date` dialect branch worked on its first live run** —
   compiled to `sequence` + `explode` on Databricks, `generate_series` +
   `unnest` on DuckDB. It remains the only dialect-specific SQL in the
   project.

**Reconciliation (the number that matters):**

| Metric | DuckDB | Databricks |
|---|---|---|
| fct_orders rows | 20,917 | 20,917 |
| Total revenue | $7,599,897.60 | $7,599,897.60 |
| Mart revenue | $7,599,897.60 | $7,599,897.60 |
| Final MRR | $66,489 | $66,489 |
| Snapshot rows | 18,863 | 18,860 (fresh baseline — expected) |

The snapshot difference is the documented one from Step 15: SCD2 history
is environment state, not pipeline code. Databricks starts its own history
from the current CSV (one version per customer); the 3-customer version
history remains visible in the DuckDB environment.

**The interview line this step earns:** "I developed locally on DuckDB for
fast iteration, then pointed the same dbt project at Databricks — one
dialect branch in one model, everything else unchanged, and the totals
reconciled to the penny on the first migrated build."

---

## Practice backlog — the mess left in on purpose

The five unfixed data-quality issues below are deliberate practice
material for the hand-rebuild phase, not oversights. Each is tracked by a
warn-severity test today ("track, don't silently repair"); each has a
different industry-standard fix, and knowing *which* treatment a problem
deserves — fix, track, quarantine, or business rule — is the judgment
being practiced. The generator is deterministic (`random.seed(42)`), so
this mess is reproducible: it can't be accidentally destroyed.

| # | Issue | Count | The fix to practice | Pattern name |
|---|---|---|---|---|
| 1 | Orders missing `geo_id` | 206 | Add a `-1 / Unknown` row to `dim_geo`; route null geos to it so geo-sliced reports stop silently dropping orders | Unknown member |
| 2 | Customers missing `acquisition_channel_id` | 100 | Same treatment in `dim_channel` | Unknown member |
| 3 | Orders referencing nonexistent customers | 70 | Create placeholder rows in `dim_customer` so facts join to *something*; backfill when the real record syncs | Late-arriving dimension |
| 4 | Zero-quantity / zero-price order rows | 48 | Exclude from revenue via a documented business rule — version the exclusion in `governed_kpis/gross_margin.md` (this one is a change-management exercise, not just SQL) | Business rule + KPI versioning |
| 5 | Claims referencing unsynced orders | 7 | Hold in a quarantine model until the parent order arrives | Late-arriving fact |

Also re-practicable any time (the fix lives in SQL, the mess stays in the
raw seeds): delete `DISTINCT` from `stg_orders.sql`, run `dbt build`,
watch `unique_stg_orders_order_id` fail with 104 duplicates, put it back.
A 2-minute rehearsal of the Step 6 story on demand.

**Definition of done for each backlog item:** the warn test either passes
(issue genuinely resolved) or is replaced by a test asserting the new
handling (e.g. "all null geos map to Unknown"), PROJECT_LOG.md gets a
step entry, and — for #4 — the governed-KPI doc gets a version bump with
the change logged.

---

## Step 17 — Post-migration data scrutiny: 15 checks, 15 pass, zero findings

**What we did:** a deeper scrutiny pass than the Step 13 audit, in two
parts — and for the first time in this project, a scrutiny pass that
found nothing to fix.

**Part 1 — cross-engine fingerprint (8 values).** The Step 16
reconciliation compared totals; totals can match even if rows land in the
wrong month. So this fingerprint adds a *month-weighted* revenue sum
(each month's revenue × its YYYYMM key) that only matches if every
month's allocation is identical on both engines. All 8 values identical
on DuckDB and Databricks: 24 mart months, $7,599,897.60 total revenue,
month-weighted sum 1,538,783,976,488, 22,587 units, 16,113 new
subscribers, 5,013 churned, cumulative MRR $650,082.72, 399 warranty
claims.

**Part 2 — distribution realism (7 checks).** Does the realized data
actually behave the way the generator's documented design says?

| Check | Design | Realized |
|---|---|---|
| Channel mix | 35/30/15/10/10 | 35.2/29.9/15.1/9.8/10.0 |
| Product mix | 15/15/10/25/25/10 | 14.8/15.2/9.8/24.8/25.3/10.2 |
| Discount incidence | 25% | 25.4% |
| Two-ring orders | 8% | 8.1% |
| Subscription attach lag | 0–30 days | 0–30, avg 14.7 |
| Month-1 churn hazard | 12% | 12.0% |
| Nov seasonality ratio | ~1.70 | 1.72 |

**Why a zero-finding audit is still worth logging:** it's the first time
the system has been scrutinized and come back clean, which is itself
information — after 16 steps of building and 6 caught issues, the checks
that used to find problems now don't. That's what "trustworthy enough to
stop re-checking constantly" looks like, and it's the state a governed
reporting platform is supposed to converge to.

---

<!-- New entries get appended below as each day's work happens. -->
