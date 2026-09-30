{{ config(materialized='table') }}

select
    cnae_code,
    cnae_description,
    source_period,
    {{ add_audit_columns() }}
from {{ ref('stg_cnae') }}
where cnae_code is not null
