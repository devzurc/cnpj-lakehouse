{{ config(materialized='table') }}

select
    cnae_code,
    substr(cnae_code, 1, 2) as division_code,
    substr(cnae_code, 1, 3) as group_code,
    substr(cnae_code, 1, 5) as class_code,
    cnae_description as subclass_description,
    source_period,
    {{ add_audit_columns() }}
from {{ ref('dim_cnae') }}
