select
    customer_id,
    cast(signup_date as date) as signup_date,
    geo_id,
    acquisition_channel_id
from {{ ref('seed_customers') }}
