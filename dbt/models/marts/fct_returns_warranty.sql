select
    w.claim_id,
    w.order_id,
    d.date_id,
    w.claim_type,
    w.resolution,
    w.cost_to_company
from {{ ref('stg_returns_warranty') }} w
left join {{ ref('dim_date') }} d
    on w.claim_date = d.date_day
