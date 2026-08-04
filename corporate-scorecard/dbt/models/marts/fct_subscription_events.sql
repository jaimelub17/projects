-- Same earliest-known-version join as fct_orders, same reason: event_date
-- values (2024-2025) predate when SCD tracking began.

with earliest_customer_version as (
    select customer_id, min(valid_from) as first_valid_from
    from {{ ref('dim_customer') }}
    group by customer_id
)

select
    e.event_id,
    d.date_id,
    c.customer_sk,
    e.event_type,
    e.plan_price,
    e.mrr_delta
from {{ ref('stg_subscription_events') }} e
left join {{ ref('dim_date') }} d
    on e.event_date = d.date_day
left join earliest_customer_version ecv
    on e.customer_id = ecv.customer_id
left join {{ ref('dim_customer') }} c
    on ecv.customer_id = c.customer_id
    and ecv.first_valid_from = c.valid_from
