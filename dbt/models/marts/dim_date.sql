with spine as (
    select unnest(generate_series(
        date '2024-01-01', date '2025-12-31', interval 1 day
    )) as date_day
)

select
    cast(strftime(date_day, '%Y%m%d') as integer) as date_id,
    date_day,
    extract(year from date_day) as year,
    extract(quarter from date_day) as quarter,
    extract(month from date_day) as month,
    extract(week from date_day) as week,
    'FY' || extract(year from date_day) || '-Q' || extract(quarter from date_day) as fiscal_period
from spine
