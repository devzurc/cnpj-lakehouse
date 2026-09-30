with ranked as (
    select
        {{ normalize_cnpj('cnpj_basico') }} as cnpj_basico,
        nullif(trim(razao_social), '') as razao_social,
        nullif(trim(natureza_juridica), '') as natureza_juridica,
        nullif(trim(qualificacao_responsavel), '') as qualificacao_responsavel,
        {{ parse_decimal_br('capital_social_raw') }} as capital_social,
        (
            nullif(trim(cast(capital_social_raw as varchar)), '') is not null
            and {{ parse_decimal_br('capital_social_raw') }} is null
        ) as capital_social_parse_failed,
        nullif(trim(porte_empresa), '') as porte_empresa,
        nullif(trim(ente_federativo_responsavel), '') as ente_federativo_responsavel,
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
        row_number() over (
            partition by {{ normalize_cnpj('cnpj_basico') }}
            order by ingested_at desc, source_file desc, source_row_number desc
        ) as row_rank
    from {{ source('bronze', 'raw_companies') }} as bronze
    where {{ active_batch_filter('bronze') }}
)

select
    * exclude (row_rank),
    {{ add_audit_columns() }}
from ranked
where row_rank = 1
