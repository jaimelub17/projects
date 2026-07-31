-- Note on the customer_sk join: a "proper" SCD2 fact join would match each
-- order to the dim_customer version whose valid_from/valid_to range covers
-- order_date. That doesn't work here -- our snapshot history only started
-- existing in dev-time (today), while every order_date is from 2024-2025,
-- entirely before tracking began. So every dbt_valid_from timestamp is
-- *later* than every order_date, and a range join would match nothing.
-- Instead, join to each customer's EARLIEST known version -- the closest
-- available approximation of "their state during 2024-2025." In a real,
-- continuously-running snapshot system (tracking from day one), the range
-- join above is the correct pattern -- see dim_customer for that mechanism.

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
