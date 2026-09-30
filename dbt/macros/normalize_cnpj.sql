{% macro normalize_cnpj(cnpj_basico, cnpj_ordem=none, cnpj_dv=none) -%}
  {%- set basic_text = "trim(cast(" ~ cnpj_basico ~ " as varchar))" -%}
  {%- set basic_digits = "regexp_replace(" ~ basic_text ~ ", '[-./ ]', '', 'g')" -%}
  {%- if cnpj_ordem is none or cnpj_dv is none -%}
    case
      when regexp_full_match({{ basic_text }}, '[-0-9./ ]+') and length({{ basic_digits }}) = 8 then {{ basic_digits }}
      else null
    end
  {%- else -%}
    {%- set order_text = "trim(cast(" ~ cnpj_ordem ~ " as varchar))" -%}
    {%- set dv_text = "trim(cast(" ~ cnpj_dv ~ " as varchar))" -%}
    {%- set order_digits = "regexp_replace(" ~ order_text ~ ", '[-./ ]', '', 'g')" -%}
    {%- set dv_digits = "regexp_replace(" ~ dv_text ~ ", '[-./ ]', '', 'g')" -%}
    case
      when regexp_full_match({{ basic_text }}, '[-0-9./ ]+')
        and regexp_full_match({{ order_text }}, '[-0-9./ ]+')
        and regexp_full_match({{ dv_text }}, '[-0-9./ ]+')
        and length({{ basic_digits }}) = 8
        and length({{ order_digits }}) = 4
        and length({{ dv_digits }}) = 2
        then {{ basic_digits }} || {{ order_digits }} || {{ dv_digits }}
      else null
    end
  {%- endif -%}
{%- endmacro %}
