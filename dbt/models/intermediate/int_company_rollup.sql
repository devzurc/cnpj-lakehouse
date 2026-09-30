with establishment_metrics as (
    select
        cnpj_basico,
        count(*) as active_establishment_count
    from {{ ref('stg_establishments') }}
    where situacao_cadastral = '02'
    group by 1
),
representative_establishment as (
    select
        cnpj_basico,
        principal_cnae,
        uf,
        row_number() over (
            partition by cnpj_basico
            order by
                case when matriz_filial_code = '1' then 0 else 1 end,
                cnpj
        ) as representative_rank
    from {{ ref('stg_establishments') }}
    where situacao_cadastral = '02'
),
partner_metrics as (
    select cnpj_basico, count(*) as partner_count
    from {{ ref('stg_partners') }}
    group by 1
)

select
    company.cnpj_basico,
    company.razao_social,
    company.natureza_juridica,
    company.porte_empresa,
    company.capital_social,
    coalesce(establishment.active_establishment_count, 0) as active_establishment_count,
    coalesce(partner.partner_count, 0) as partner_count,
    representative.principal_cnae,
    representative.uf,
    case simples.simples_flag when 'S' then true when 'N' then false else null end as is_simples_nacional,
    case simples.mei_flag when 'S' then true when 'N' then false else null end as is_mei,
    company.source_period,
    company.sample_id,
    {{ add_audit_columns() }}
from {{ ref('stg_companies') }} as company
left join establishment_metrics as establishment using (cnpj_basico)
left join representative_establishment as representative
    on company.cnpj_basico = representative.cnpj_basico
    and representative.representative_rank = 1
left join partner_metrics as partner using (cnpj_basico)
left join {{ ref('stg_simples') }} as simples using (cnpj_basico)
