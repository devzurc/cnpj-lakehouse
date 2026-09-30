with ranked as (
    select
        {{ normalize_cnpj('cnpj_basico') }} as cnpj_basico,
        case upper(nullif(trim(opcao_simples), '')) when 'S' then 'S' when 'N' then 'N' end as simples_flag,
        try_strptime(nullif(trim(data_opcao_simples_raw), ''), '%Y%m%d')::date as simples_opt_in_date,
        try_strptime(nullif(trim(data_exclusao_simples_raw), ''), '%Y%m%d')::date as simples_opt_out_date,
        case upper(nullif(trim(opcao_mei), '')) when 'S' then 'S' when 'N' then 'N' end as mei_flag,
        try_strptime(nullif(trim(data_opcao_mei_raw), ''), '%Y%m%d')::date as mei_opt_in_date,
        try_strptime(nullif(trim(data_exclusao_mei_raw), ''), '%Y%m%d')::date as mei_opt_out_date,
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
    from {{ source('bronze', 'raw_simples') }} as bronze
    where {{ active_batch_filter('bronze') }}
)

select
    * exclude (row_rank),
    {{ add_audit_columns() }}
from ranked
where row_rank = 1
