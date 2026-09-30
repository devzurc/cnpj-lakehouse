with ranked as (
    select
        {{ normalize_cnpj('cnpj_basico') }} as cnpj_basico,
        {{ normalize_cnpj('cnpj_basico', 'cnpj_ordem', 'cnpj_dv') }} as cnpj,
        nullif(trim(identificador_matriz_filial), '') as matriz_filial_code,
        nullif(trim(nome_fantasia), '') as nome_fantasia,
        nullif(trim(situacao_cadastral), '') as situacao_cadastral,
        try_strptime(nullif(trim(data_situacao_cadastral_raw), ''), '%Y%m%d')::date as data_situacao_cadastral,
        nullif(trim(motivo_situacao_cadastral), '') as motivo_situacao_cadastral,
        try_strptime(nullif(trim(data_inicio_atividade_raw), ''), '%Y%m%d')::date as data_inicio_atividade,
        {{ normalize_cnae('cnae_fiscal_principal') }} as principal_cnae,
        nullif(trim(cnae_fiscal_secundaria), '') as secondary_cnaes_raw,
        nullif(trim(uf), '') as uf,
        nullif(trim(municipio), '') as municipio_code,
        nullif(trim(cep), '') as cep,
        nullif(trim(correio_eletronico), '') as email,
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
            partition by {{ normalize_cnpj('cnpj_basico', 'cnpj_ordem', 'cnpj_dv') }}
            order by ingested_at desc, source_file desc, source_row_number desc
        ) as row_rank
    from {{ source('bronze', 'raw_establishments') }} as bronze
    where {{ active_batch_filter('bronze') }}
)

select
    * exclude (row_rank),
    {{ add_audit_columns() }}
from ranked
where row_rank = 1
