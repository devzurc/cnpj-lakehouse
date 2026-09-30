select distinct
    establishment.cnpj,
    establishment.cnpj_basico,
    {{ normalize_cnae('secondary_cnae.cnae_code_raw') }} as secondary_cnae_code,
    establishment.source_period,
    establishment.sample_id,
    {{ add_audit_columns() }}
from {{ ref('stg_establishments') }} as establishment
cross join unnest(string_split(coalesce(establishment.secondary_cnaes_raw, ''), ','))
    as secondary_cnae(cnae_code_raw)
where {{ normalize_cnae('secondary_cnae.cnae_code_raw') }} is not null
