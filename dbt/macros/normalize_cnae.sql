{% macro normalize_cnae(column_name) -%}
  case
    when regexp_full_match(trim(cast({{ column_name }} as varchar)), '[0-9]{7}')
      then trim(cast({{ column_name }} as varchar))
    else null
  end
{%- endmacro %}
