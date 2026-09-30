with ranked as (
    select
        {{ normalize_cnae('cnae_code') }} as cnae_code,
        nullif(trim(cnae_description), '') as cnae_description,
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
            partition by {{ normalize_cnae('cnae_code') }}
            order by ingested_at desc, source_file desc, source_row_number desc
        ) as row_rank
    from {{ source('bronze', 'raw_cnae') }} as bronze
    where {{ active_batch_filter('bronze') }}
)

select
    * exclude (row_rank),
    {{ add_audit_columns() }}
from ranked
where row_rank = 1
