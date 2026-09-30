{{ config(materialized='view') }}

select
    cnpj_basico,
    capital_social,
    source_period,
    sample_id,
    dbt_valid_from as valid_from,
    dbt_valid_to as valid_to,
    dbt_valid_to is null as is_current,
    {{ add_audit_columns() }}
from {{ ref('company_capital_social_snapshot') }}
