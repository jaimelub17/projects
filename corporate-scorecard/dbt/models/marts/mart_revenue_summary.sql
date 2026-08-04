-- Governed KPI mart: Revenue / Gross Profit / Gross Margin / Units Sold,
-- month grain. Includes period-over-period columns (MoM, YoY) since
-- executive scorecards are always read against a prior period.
--
-- Known tracked issue inherited from upstream: the 48 zero-quantity/
-- zero-price order rows (entry glitches, warn-severity in staging) are
-- included, not silently filtered -- consistent with the project stance
-- that data problems get flagged and monitored, not quietly dropped.

with monthly as (

    select
        date_trunc('month', d.date_day) as month_start,
        min(d.fiscal_period) as fiscal_period,
        sum(f.revenue) as revenue,
        sum(f.cogs) as cogs,
        sum(f.quantity) as units_sold
    from {{ ref('fct_orders') }} f
    join {{ ref('dim_date') }} d on f.date_id = d.date_id
    group by 1

)

select
    month_start,
    fiscal_period,
    round(revenue, 2) as revenue,
    round(cogs, 2) as cogs,
    round(revenue - cogs, 2) as gross_profit,
    round(100.0 * (revenue - cogs) / nullif(revenue, 0), 2) as gross_margin_pct,
    units_sold,
    round(100.0 * (revenue / nullif(lag(revenue) over (order by month_start), 0) - 1), 1)
        as revenue_mom_pct,
    round(100.0 * (revenue / nullif(lag(revenue, 12) over (order by month_start), 0) - 1), 1)
        as revenue_yoy_pct
from monthly
order by month_start
