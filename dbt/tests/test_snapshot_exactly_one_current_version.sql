select cnpj_basico
from {{ ref('company_capital_social_snapshot') }}
group by 1
having count(*) filter (where dbt_valid_to is null) != 1
