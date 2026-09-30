{% macro pseudonymize_identifier(expression, domain) -%}
    case
        when nullif(trim(cast({{ expression }} as varchar)), '') is null then null
        else 'v1:' || sha256('{{ domain }}:' || trim(cast({{ expression }} as varchar)))
    end
{%- endmacro %}
