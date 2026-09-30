{% snapshot company_capital_social_snapshot %}
  {{
    config(
      target_schema='snapshots',
      unique_key='cnpj_basico',
      strategy='check',
      check_cols=['capital_social'],
      invalidate_hard_deletes=false
    )
  }}

  select
      cnpj_basico,
      capital_social,
      source_period,
      sample_id
  from {{ ref('stg_companies') }}
{% endsnapshot %}
