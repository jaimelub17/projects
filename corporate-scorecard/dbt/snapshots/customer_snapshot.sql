{% snapshot customer_snapshot %}

{{
    config(
      unique_key='customer_id',
      strategy='check',
      check_cols=['geo_id', 'acquisition_channel_id'],
    )
}}

select
    customer_id,
    geo_id,
    acquisition_channel_id
from {{ ref('stg_customers') }}

{% endsnapshot %}
