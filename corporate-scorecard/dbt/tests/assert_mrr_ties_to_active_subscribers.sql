-- Internal consistency control (error severity): with a single $5.99 plan,
-- MRR must equal active subscribers x 5.99 in every month. The two figures
-- are computed from different columns of the same events (mrr_delta vs
-- event counts), so this catches any drift between the two calculations.

select
    month_start,
    mrr,
    active_subscribers_eom,
    round(active_subscribers_eom * 5.99, 2) as expected_mrr
from {{ ref('mart_subscription_metrics') }}
where abs(mrr - active_subscribers_eom * 5.99) > 0.01
