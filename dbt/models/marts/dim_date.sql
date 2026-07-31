-- Date spine, 2024-01-01 through 2025-12-31.
--
-- The spine generator is the one genuinely dialect-specific piece of SQL in
-- this project: DuckDB spells it generate_series + unnest, Databricks/Spark
-- spells it sequence + explode. Branching on target.type keeps a single
-- model portable across both. Everything below the spine is engine-neutral
-- (date_id is plain arithmetic on purpose -- no strftime/date_format).

{% if target.type == 'databricks' %}
with spine as (
    select explode(sequence(
        date '2024-01-01', date '2025-12-31', interval 1 day
    )) as date_day
)
{% else %}
with spine as (
    select unnest(generate_series(
        date '2024-01-01', date '2025-12-31', interval 1 day
    )) as date_day
)
{% endif %}

select
    cast(
        extract(year from date_day) * 10000
        + extract(month from date_day) * 100
        + extract(day from date_day)
    as integer) as date_id,
    date_day,
    extract(year from date_day) as year,
    extract(quarter from date_day) as quarter,
    extract(month from date_day) as month,
    extract(week from date_day) as week,
    'FY' || extract(year from date_day) || '-Q' || extract(quarter from date_day) as fiscal_period
from spine
