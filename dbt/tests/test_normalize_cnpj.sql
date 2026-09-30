with basic_cases(input_value, expected_value) as (
    values
        ('00000001', '00000001'),
        ('12.345.678', '12345678'),
        ('', null),
        ('123', null)
),
basic_failures as (
    select input_value
    from basic_cases
    where {{ normalize_cnpj('input_value') }} is distinct from expected_value
),
establishment_cases(cnpj_basico, cnpj_ordem, cnpj_dv, expected_value) as (
    values
        ('00000001', '0001', '95', '00000001000195'),
        ('00000001', '', '95', null),
        ('00000001', '0001', '', null)
),
establishment_failures as (
    select cnpj_basico
    from establishment_cases
    where {{ normalize_cnpj('cnpj_basico', 'cnpj_ordem', 'cnpj_dv') }}
        is distinct from expected_value
)

select * from basic_failures
union all
select * from establishment_failures
