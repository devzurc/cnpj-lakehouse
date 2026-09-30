{% set reference_date = var('reference_date', env_var('CNPJ_LAKEHOUSE_REFERENCE_DATE', env_var('CNPJ_LAKEHOUSE_REFERENCE_DATE', ''))) %}

{{
  config(
    materialized='incremental',
    unique_key=['reference_date', 'cnpj_basico'],
    incremental_strategy='delete+insert',
    pre_hook="{% if is_incremental() %}delete from {{ this }} where reference_date = cast('" ~ reference_date ~ "' as date){% endif %}"
  )
}}

select
    cast('{{ reference_date }}' as date) as reference_date,
    cnpj_basico,
    active_establishment_count,
    partner_count,
    capital_social,
    principal_cnae,
    uf,
    is_simples_nacional,
    is_mei,
    source_period,
    sample_id,
    {{ add_audit_columns() }}
from {{ ref('int_company_rollup') }}
where active_establishment_count > 0
