select
    geo_id,
    country,
    region,
    nullif(state, '') as state
from {{ ref('seed_geo') }}
