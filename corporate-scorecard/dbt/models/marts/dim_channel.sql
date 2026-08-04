select
    channel_id,
    channel_name
from {{ ref('stg_channels') }}
