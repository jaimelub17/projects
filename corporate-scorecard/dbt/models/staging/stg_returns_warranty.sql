select
    claim_id,
    order_id,
    cast(claim_date as date) as claim_date,
    claim_type,
    resolution,
    cost_to_company
from {{ ref('seed_returns_warranty') }}
