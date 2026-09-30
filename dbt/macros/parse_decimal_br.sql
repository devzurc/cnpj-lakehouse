{% macro parse_decimal_br(column_name) -%}
  try_cast(
    nullif(replace(replace(trim(cast({{ column_name }} as varchar)), '.', ''), ',', '.'), '')
    as decimal(18, 2)
  )
{%- endmacro %}
