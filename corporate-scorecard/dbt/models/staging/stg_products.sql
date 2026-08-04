select
    product_id,
    ring_model,
    color,
    list_price,
    unit_cost
from {{ ref('seed_products') }}
