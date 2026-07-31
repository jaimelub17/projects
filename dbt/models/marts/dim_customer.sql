-- SCD Type 2: sourced from the customer_snapshot (dbt snapshot), not directly
-- from stg_customers, so fact tables can join to the customer version that
-- was actually current at the time of each transaction.
select
    dbt_scd_id as customer_sk,
    customer_id,
    geo_id,
    acquisition_channel_id,
    dbt_valid_from as valid_from,
    dbt_valid_to as valid_to,
    (dbt_valid_to is null) as is_current
from {{ ref('customer_snapshot') }}
