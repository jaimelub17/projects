# Governed KPI: Gross Margin %

|  |  |
|---|---|
| **Status** | Governed — locked definition |
| **Version** | 1.0 (see change log) |
| **Metric owner** | Analytics (single named owner — the JD's "single owner" requirement) |
| **Business sign-off** | VP Finance (simulated here; in a real org this row names the person and date) |
| **Served from** | `mart_revenue_summary.gross_margin_pct` — the ONLY sanctioned source |
| **Grain** | Month |
| **Current value** | ~55.5% blended (2024–2025) |

## Locked definition

```
Gross Margin % = (Revenue − COGS) / Revenue × 100

Revenue = SUM(quantity × unit_price)   -- unit_price is post-discount
COGS    = SUM(quantity × unit_cost)    -- standard cost per SKU
```

Computed per order line in `fct_orders`, aggregated by calendar month in
`mart_revenue_summary`. Revenue is recognized on order date.

### Explicitly IN scope
- Hardware order lines only (membership revenue is a separate metric family
  in `mart_subscription_metrics` — never blended into this number)
- Discounts — netted into `unit_price` before revenue is computed
- All sales channels and geos, including orders with a missing geo tag
  (~1%, tracked by a warn-severity test)

### Explicitly OUT of scope (documented exclusions)
- **Returns/refunds are NOT netted out of revenue.** They are tracked
  separately in `fct_returns_warranty`. A "net revenue" variant would be a
  new versioned metric, not a silent redefinition of this one.
- **Warranty replacement/repair costs are NOT loaded into COGS** (no
  warranty reserve). Under GAAP a warranty accrual would hit COGS; this
  model doesn't simulate it — see Known limitations.
- Freight, duties, payment processing fees — no source data in this model.
- The ~48 zero-quantity/zero-price glitch rows are INCLUDED (tracked by
  `assert_orders_have_positive_values`, warn severity) — flagged and
  monitored rather than silently filtered.

## Lineage (source → executive number)

```
seed_orders (NetSuite stand-in)
  → stg_orders        dedup (SELECT DISTINCT), date typing
    → fct_orders      revenue & cogs computed per line, dims joined
      → mart_revenue_summary   month grain, margin %, MoM/YoY
```

Interactive version: `dbt docs serve` → any model → lineage graph.

## Controls protecting this number

| Control | Type | Severity | What it prevents |
|---|---|---|---|
| `unique_stg_orders_order_id` | generic | **error** | double-counted revenue from replayed rows (caught 104 real duplicates in Step 6) |
| `assert_mart_revenue_reconciles_to_fct` | reconciliation | **error** | scorecard number diverging from transactional truth (must tie to the penny) |
| `not_null_mart_revenue_summary_*` | generic | **error** | silent nulls in the served metric |
| `relationships` on `product_id` | FK | **error** | order lines costed against a nonexistent SKU |
| `assert_orders_have_positive_values` | singular | warn | zero/negative qty or price rows entering unnoticed |
| `not_null_stg_orders_geo_id` | generic | warn | geo-sliced margin silently dropping untagged orders |

## Change management

1. Any definition change starts as a PR touching this document AND the SQL.
2. Version bumps (1.0 → 1.1 for clarifications, 2.0 for semantic changes).
3. Sign-off recorded in the change log below before merge.
4. Downstream consumers (dashboards, planning models) notified via the
   exposure list; the old definition's last-served date is recorded.

## Change log

| Date | Version | Change | Approved by |
|---|---|---|---|
| 2026-07-30 | 1.0 | Initial locked definition | (simulated sign-off) |

## Known limitations (honest, on the record)

1. **~55.5% vs the ~57–59% benchmark** (Garmin Fitness segment): our unit
   costs were set for ~57% at list price; realized margin is lower because
   ~25% of orders carry a 10–15% discount. Directionally consistent, and
   the gap is explainable — which is the standard that matters.
2. **Order-date recognition** is a simplification vs shipment-date
   recognition under ASC 606.
3. **No warranty reserve in COGS** (see exclusions) — real hardware gross
   margin would carry one.
