{{ config(materialized='table') }}

select
    cnpj_basico,
    razao_social,
    natureza_juridica,
    porte_empresa,
    capital_social,
    principal_cnae,
    uf,
    is_simples_nacional,
    is_mei,
    source_period,
    sample_id,
    {{ add_audit_columns() }}
from {{ ref('int_company_rollup') }}
