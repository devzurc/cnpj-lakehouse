{% macro active_batch_value(name, environment_name) -%}
  {%- set value = var(name, env_var(environment_name, "")) -%}
  {%- set normalized = value | string | trim -%}
  {%- if normalized == "" -%}
    {{ exceptions.raise_compiler_error("Required active-batch input is blank: " ~ name) }}
  {%- endif -%}
  {{ return(normalized) }}
{%- endmacro %}

{% macro active_batch_filter(relation_alias) -%}
  {%- set source_period = active_batch_value("source_period", "CNPJ_LAKEHOUSE_SOURCE_PERIOD") -%}
  {%- set sample_id = active_batch_value("sample_id", "CNPJ_LAKEHOUSE_SAMPLE_ID") -%}
  {%- set _ = active_batch_value("reference_date", "CNPJ_LAKEHOUSE_REFERENCE_DATE") -%}
  {{ relation_alias }}.source_period = '{{ source_period }}'
  and {{ relation_alias }}.sample_id = '{{ sample_id }}'
{%- endmacro %}
