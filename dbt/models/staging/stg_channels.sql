select
    channel_id,
    channel_name
from {{ ref('seed_channels') }}
