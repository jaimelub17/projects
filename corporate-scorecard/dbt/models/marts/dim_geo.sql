select
    geo_id,
    country,
    region,
    state
from {{ ref('stg_geo') }}
