# Schema Design — Corporate Scorecard (portfolio project)

Simulates the data layer behind a "Corporate Scorecard" for a hardware +
subscription consumer wearables business: hardware-dominant revenue with a
growing membership layer (~9% subscription share in our 2-year window; the
benchmark company's real ~20% reflects membership cohorts accumulated over many
more years — see "Modeling assumptions" below). Built to mirror the KPIs a
corporate financial reporting role owns: Revenue, Gross Profit/Margin, Units
Sold, Warranty Rate, and subscription metrics (MRR, ARR, Churn).

## Dimensions

| Table | Grain | Key columns |
|---|---|---|
| `dim_customer` | one row per customer | customer_id, signup_date, region, acquisition_channel |
| `dim_product` | one row per SKU | product_id, ring_model (Gen3 / Ring 4), color, size, unit_cost, list_price |
| `dim_date` | one row per calendar day | date_id, date, year, quarter, month, week, fiscal_period |
| `dim_geo` | one row per country/state | geo_id, country, region, state |
| `dim_channel` | one row per sales channel | channel_id, channel_name (D2C web, Amazon, Target, Best Buy) |

## Facts

| Table | Grain | Key columns |
|---|---|---|
| `fct_orders` | one row per order line item | order_id, customer_id, product_id, date_id, geo_id, channel_id, quantity, unit_price, unit_cost, discount_amount, revenue, cogs |
| `fct_subscription_events` | one row per subscription state change | event_id, customer_id, date_id, event_type (signup/cancel), plan_price, mrr_delta |
| `fct_returns_warranty` | one row per return/warranty claim | claim_id, order_id, date_id, claim_type, resolution, cost_to_company |

## KPI Marts (the governed, audit-grade layer)

| Mart | Grain | Metrics |
|---|---|---|
| `mart_revenue_summary` | month | revenue, cogs, gross_profit, gross_margin_pct, units_sold |
| `mart_subscription_metrics` | month | active_subscribers, new_subscribers, churned_subscribers, mrr, arr, churn_rate |
| `mart_warranty_rate` | month | units_sold, warranty_claims, warranty_rate_pct |

## Lineage (planned)

```
seeds/*.csv
  -> staging: stg_orders, stg_customers, stg_subscriptions, stg_returns  (1:1 clean-up, typing, renaming)
    -> marts: dim_customer, dim_product, dim_date, dim_geo, dim_channel
    -> marts: fct_orders, fct_subscription_events, fct_returns_warranty
      -> marts: mart_revenue_summary, mart_subscription_metrics, mart_warranty_rate
        -> exposure: Databricks SQL dashboard / Genie space
```

## Notes / decisions

- Numbers are synthetic but scaled to roughly track Oura's real 2024-2025 growth
  (revenue ~2x YoY, $5.99/mo membership price) so the KPI outputs are plausible,
  not just placeholder numbers.
- `mart_revenue_summary` is the one metric ("Gross Margin") that gets a full governed-KPI
  writeup (owner, definition, tests, sign-off) — see `governed_kpis/gross_margin.md` once built.
- `fct_subscription_events` only ever has `signup`/`cancel` rows, not `renew`. Monthly
  renewals were deliberately left out — MRR is a running total of `mrr_delta`, so a
  renewal event would add rows without adding any information a KPI needs. (Corrected
  here after the doc had drifted from what the generator actually produces — this table
  used to say "signup/renew/cancel".)

## Build status

- [x] Seed data (customers, products, geo, channels, orders, subscription events, claims)
- [x] Staging models (`models/staging/`) — 1:1 cleanup/typing of every seed table,
  with `dbt test` coverage tuned to the known injected data-quality issues
  (see PROJECT_LOG.md Step 6)
- [x] SCD Type 2 on customer geo/channel via `dbt snapshot` (`snapshots/customer_snapshot.sql`)
  — see PROJECT_LOG.md Step 7. `dim_customer` will source from this snapshot,
  not directly from `stg_customers`, once built.
- [x] `dim_date`, `dim_product`, `dim_geo`, `dim_channel`, `dim_customer` (SCD2,
  sourced from `customer_snapshot`) — see PROJECT_LOG.md Steps 8-9
- [x] Fact models (`fct_orders`, `fct_subscription_events`, `fct_returns_warranty`)
  — see PROJECT_LOG.md Step 10 for the SCD2 join design decision
- [x] KPI marts (`mart_revenue_summary`, `mart_subscription_metrics`,
  `mart_warranty_rate`) with two error-severity reconciliation controls —
  see PROJECT_LOG.md Step 12
- [x] dbt docs site with lineage graph (`dbt docs generate` / `serve`) — see
  PROJECT_LOG.md Step 14
- [x] Governed-KPI one-pager: [`governed_kpis/gross_margin.md`](governed_kpis/gross_margin.md)
- [x] Databricks migration — full build green on Databricks Free Edition
  (Unity Catalog `workspace.oura_scorecard`), totals reconcile to DuckDB to
  the penny. See PROJECT_LOG.md Step 16.
- [x] Dashboard (Databricks AI/BI, built in-workspace) + dbt exposure
  (`models/exposures.yml`) — lineage now terminates at the executive surface.
  See PROJECT_LOG.md Step 18. **Build complete — everything in the original
  scope is done.**

## Modeling assumptions (benchmarked, not guessed)

Oura is private and doesn't publish financials, so assumptions below are grounded
against the closest public comparable rather than picked arbitrarily.

- **Hardware gross margin (~57%)**: benchmarked against Garmin's Fitness segment,
  which posted a 59% gross margin in Q4 2025 (Garmin FY2025 10-K / Q4 earnings
  release). Closest available public proxy for a consumer wearables hardware margin.
- **Subscription churn**: modeled as a retention/hazard curve, not a flat monthly
  probability — risk is highest in a subscriber's first 1-2 months (12%, 8%) and
  declines with tenure down to a 2% floor after month 6. This matches the real
  shape of subscription-business churn (early-tenure risk is always highest) rather
  than an unrealistic constant rate.
- **Customer behavior (rebuilt in the Step 11 realism audit)**: customers are
  *derived from orders* — ~90% of orders create a new customer, ~10% are repeat
  purchases (upgrades/gifts) — giving ~1.11 orders per customer, matching real
  ring-buyer behavior. `signup_date` is the first order date, and subscriptions
  attach 0-30 days *after* that first ring purchase at a ~90% attach rate (Oura's
  real attach is reportedly very high; a membership without a ring makes no sense).
- **Known honest deviation — subscription revenue share (~9% vs Oura's real ~20%)**:
  our 2-year window only accumulates 2 years of membership cohorts; Oura's real 20%
  share sits on top of cohorts built up over many more years of ring sales. We
  document the deviation rather than distorting churn/attach/pricing to force the
  ratio. (Before the Step 11 audit this was far worse — the v2 generator produced
  a 1.1% share and 10.2 orders/customer; see PROJECT_LOG.md Step 11.)

## Intentional data-quality issues (for the staging layer & dbt tests to catch)

Injected on purpose, at known rates, so there's something real for `dbt test` to
catch — a dataset with zero data-quality issues doesn't demonstrate anything about
the governed-KPI / staging-layer process. Counts below are from the current seed
generation (`random.seed(42)`, reproducible):

| Issue | Table | Simulates | Count |
|---|---|---|---|
| Null `geo_id` | `seed_orders` | Channel integration gap | 206 |
| Orphaned `customer_id` | `seed_orders` | Order synced before customer record | 70 |
| Zero `quantity` / `unit_price` | `seed_orders` | Data entry glitch | 48 |
| Duplicate `order_id` rows | `seed_orders` | Ingestion pipeline replay bug | 104 |
| Null `acquisition_channel_id` | `seed_customers` | Incomplete profile data | 100 |
| Duplicate `event_id` rows | `seed_subscription_events` | Webhook double-fire | 161 |
| Orphaned `order_id` | `seed_returns_warranty` | Claim logged before order fully synced | 7 |

(Counts updated after the Step 11 data rebuild — same injection *rates*, new
volumes because the customer/subscription universe grew ~10x.)

Each of these should map to a specific dbt test in the staging layer
(`not_null`, `unique`, `relationships`) — the point is to be able to show a
failing test, explain what it caught, and show the staging model's fix.
