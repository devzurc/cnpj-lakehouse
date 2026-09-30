{% test non_negative(model, column_name) %}
select *
from {{ model }}
where {{ column_name }} < 0
{% endtest %}

{% test active_company_has_establishments(model) %}
select *
from {{ model }}
where active_establishment_count <= 0
{% endtest %}

{% test unique_combination(model, combination_of_columns) %}
select
  {% for column_name in combination_of_columns -%}
  {{ column_name }}{% if not loop.last %}, {% endif %}
  {%- endfor %},
  count(*) as duplicate_count
from {{ model }}
group by
  {% for column_name in combination_of_columns -%}
  {{ column_name }}{% if not loop.last %}, {% endif %}
  {%- endfor %}
having count(*) > 1
{% endtest %}
