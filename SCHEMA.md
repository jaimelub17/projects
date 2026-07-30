# Schema Design — Oura Corporate Scorecard (portfolio project)

Simulates the data layer behind a "Corporate Scorecard" for a hardware + subscription
business modeled on Oura's real mix (~80% hardware / ~20% membership revenue).
Built to mirror the KPIs named in the JD: Revenue, Gross Profit/Margin, Units Sold,
Warranty Rate, and subscription metrics (MRR, ARR, Churn).

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
| `fct_subscription_events` | one row per subscription state change | event_id, customer_id, date_id, event_type (signup/renew/cancel), plan_price, mrr_delta |
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
  (revenue ~2x YoY, ~80/20 hardware-subscription split, $6/mo membership price)
  so the KPI outputs are plausible, not just placeholder numbers.
- `mart_revenue_summary` is the one metric ("Gross Margin") that gets a full governed-KPI
  writeup (owner, definition, tests, sign-off) — see `governed_kpis/gross_margin.md` once built.
