select distinct
    order_id,
    customer_id,
    product_id,
    cast(order_date as date) as order_date,
    geo_id,
    channel_id,
    quantity,
    unit_price,
    unit_cost,
    discount_amount
from {{ ref('seed_orders') }}
