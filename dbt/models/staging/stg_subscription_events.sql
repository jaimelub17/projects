select distinct
    event_id,
    customer_id,
    cast(event_date as date) as event_date,
    event_type,
    plan_price,
    mrr_delta
from {{ ref('seed_subscription_events') }}
