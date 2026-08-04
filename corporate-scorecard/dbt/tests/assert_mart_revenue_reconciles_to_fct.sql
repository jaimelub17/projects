-- Reconciliation control (error severity, on purpose): the governed
-- scorecard number must tie back to the transactional fact table to the
-- penny. If this returns a row, the number leadership sees and the number
-- the transactions support have diverged -- exactly the failure mode a
-- governed-KPI program exists to prevent.

with mart_total as (
    select sum(revenue) as v from {{ ref('mart_revenue_summary') }}
),

fct_total as (
    select sum(revenue) as v from {{ ref('fct_orders') }}
)

select
    m.v as mart_revenue,
    f.v as fct_revenue,
    m.v - f.v as diff
from mart_total m, fct_total f
where abs(m.v - f.v) > 0.01
