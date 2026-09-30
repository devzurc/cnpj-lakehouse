select
    {{ normalize_cnpj('cnpj_basico') }} as cnpj_basico,
    nullif(trim(identificador_socio), '') as partner_type_code,
    nullif(trim(nome_socio), '') as partner_name,
    {{ pseudonymize_identifier('cnpj_cpf_socio', 'partner-document') }} as partner_document_pseudonym,
    nullif(trim(qualificacao_socio), '') as partner_qualification_code,
    try_strptime(nullif(trim(data_entrada_sociedade_raw), ''), '%Y%m%d')::date as partnership_start_date,
    nullif(trim(pais), '') as country_code,
    {{ pseudonymize_identifier('representante_legal', 'legal-representative-document') }}
        as legal_representative_document_pseudonym,
    nullif(trim(nome_representante), '') as legal_representative_name,
    nullif(trim(qualificacao_representante_legal), '') as legal_representative_qualification_code,
    nullif(trim(faixa_etaria), '') as age_range_code,
    source_period,
    source_file,
    source_member,
    source_row_number,
    source_url,
    source_file_sha256,
    sample_id,
    ingestion_batch_id,
    ingested_at,
    record_hash,
    {{ add_audit_columns() }}
from {{ source('bronze', 'raw_partners') }} as bronze
where {{ active_batch_filter('bronze') }}
qualify row_number() over (
    partition by source_period, sample_id, record_hash
    order by ingested_at desc, source_file desc, source_row_number desc
) = 1
