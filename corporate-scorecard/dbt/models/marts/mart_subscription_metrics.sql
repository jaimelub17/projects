-- Governed KPI mart: membership metrics (MRR, ARR, churn), month grain.
--
-- MRR here is the running total of mrr_delta -- an OPERATING metric, not
-- GAAP-recognized subscription revenue (which would be recognized ratably
-- across each covered month under ASC 606). A real Finance team keeps
-- those two numbers separate; so does this project.
--
-- churn_rate_pct uses beginning-of-month active subscribers as the
-- denominator (cancels this month / active at month start) -- the standard
-- definition, and the reason both _bom and _eom columns exist.

with months as (

    select distinct date_trunc('month', date_day) as month_start
    from {{ ref('dim_date') }}

),

monthly_events as (

    select
        date_trunc('month', d.date_day) as month_start,
        count(*) filter (where e.event_type = 'signup') as new_subscribers,
        count(*) filter (where e.event_type = 'cancel') as churned_subscribers,
        sum(e.mrr_delta) as mrr_delta
    from {{ ref('fct_subscription_events') }} e
    join {{ ref('dim_date') }} d on e.date_id = d.date_id
    group by 1

),

running as (

    select
        m.month_start,
        coalesce(e.new_subscribers, 0) as new_subscribers,
        coalesce(e.churned_subscribers, 0) as churned_subscribers,
        sum(coalesce(e.new_subscribers, 0) - coalesce(e.churned_subscribers, 0))
            over (order by m.month_start) as active_subscribers_eom,
        round(sum(coalesce(e.mrr_delta, 0)) over (order by m.month_start), 2) as mrr
    from months m
    left join monthly_events e on m.month_start = e.month_start

)

select
    month_start,
    new_subscribers,
    churned_subscribers,
    coalesce(lag(active_subscribers_eom) over (order by month_start), 0)
        as active_subscribers_bom,
    active_subscribers_eom,
    mrr,
    round(mrr * 12, 2) as arr,
    round(100.0 * churned_subscribers
        / nullif(lag(active_subscribers_eom) over (order by month_start), 0), 2)
        as churn_rate_pct
from running
order by month_start
