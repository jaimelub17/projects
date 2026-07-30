-- Singular test: order lines should never have zero/negative quantity or
-- price. ~0.2% of raw orders violate this on purpose (simulated entry
-- glitch, see PROJECT_LOG.md Step 6) -- warn, not error, since this is a
-- known tracked issue, not something staging silently fixes.
{{ config(severity='warn') }}

select *
from {{ ref('stg_orders') }}
where quantity <= 0 or unit_price <= 0
