-- Governed KPI mart: Warranty Rate, month grain.
--
-- Definition note: this is a PERIOD rate (warranty claims filed this month
-- / units sold this month), which is how a monthly scorecard tracks it.
-- Claims lag their orders by 10-45 days, so this is not a COHORT rate
-- (claims per unit of a given sales cohort) -- a warranty-cost deep-dive
-- would use the cohort version. The distinction matters and is worth
-- saying out loud; the scorecard convention is the period rate.
--
-- Recent-period immaturity: because claims lag orders, the most recent
-- month's rate is right-censored (its orders' claims mostly haven't been
-- filed yet) and will read LOW until the claim window closes. Real
-- warranty reporting carries the same caveat.

with monthly_units as (

    select
        date_trunc('month', d.date_day) as month_start,
        sum(f.quantity) as units_sold
    from {{ ref('fct_orders') }} f
    join {{ ref('dim_date') }} d on f.date_id = d.date_id
    group by 1

),

monthly_claims as (

    select
        date_trunc('month', d.date_day) as month_start,
        count(*) filter (where w.claim_type = 'warranty') as warranty_claims,
        count(*) filter (where w.claim_type = 'return') as return_claims
    from {{ ref('fct_returns_warranty') }} w
    join {{ ref('dim_date') }} d on w.date_id = d.date_id
    group by 1

)

select
    u.month_start,
    u.units_sold,
    coalesce(c.warranty_claims, 0) as warranty_claims,
    coalesce(c.return_claims, 0) as return_claims,
    round(100.0 * coalesce(c.warranty_claims, 0) / nullif(u.units_sold, 0), 2)
        as warranty_rate_pct
from monthly_units u
left join monthly_claims c on u.month_start = c.month_start
order by u.month_start
