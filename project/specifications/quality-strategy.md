# Estratégia de Qualidade de Dados e Testes

## Testes dbt Obrigatórios e Casos Cobertos

A suíte de testes dbt implementada cobre as verificações rigorosas de integridade e negócio abaixo. O desafio exige pelo menos oito; a contagem corrente é reproduzida por `uv run python -m dbt.cli.main ls --resource-type test --project-dir dbt --profiles-dir dbt` e não deve ser fixada nesta especificação.

1. `dim_company_current.cnpj_basico`: não nulo (`not_null`).
2. `dim_company_current.cnpj_basico`: valor único (`unique`).
3. `stg_establishments.cnpj`: não nulo (`not_null`).
4. `stg_establishments.cnpj`: valor único (`unique`).
5. Integridade referencial Estabelecimentos → Empresas: todo estabelecimento relaciona-se a um CNPJ básico existente (`relationships`).
6. Integridade referencial Sócios → Empresas: todo sócio relaciona-se a uma empresa existente (`relationships`).
7. Situação cadastral dos estabelecimentos: aceita somente os valores oficiais `01`, `02`, `03`, `04` e `08` (`accepted_values`).
8. Integridade referencial de atividades econômicas: CNAE principal dos estabelecimentos relaciona-se à tabela de domínio `stg_cnae` (`relationships`).
9. Capital Social não negativo: macro de teste customizado `non_negative` validando que valores monetários são `>= 0`.
10. Unicidade da chave primária composta do fato diário: combinação única de `[reference_date, cnpj_basico]` (`unique_combination`).
11. `fct_company_activity_daily.reference_date`: não nulo (`not_null`).
12. `fct_company_activity_daily.cnpj_basico`: não nulo (`not_null`).
13. Regra de negócio customizada de empresa ativa: toda linha na fato possui contagem de estabelecimentos ativos estritamente maior que zero (`active_company_has_establishments`).

## Verificações Não-dbt (Testes em Python / Pytest)

- **Corrupção e Integridade de Arquivos**: Testes com arquivos ZIP truncados, com CRC inválido ou membros ausentes garantem falha imediata sem promoção para a camada Bronze.
- **Validação de Contratos e Encodings**: Verificação de contagem estrita de colunas por dataset e decodificação CP1252 com preservação de bytes indefinidos (ADR-006).
- **Idempotência de Ingestão**: Reexecução com a mesma coorte (`source_period` + empresas distintas) é no-op na Bronze. ZIPs já presentes não disparam HTTP. Um segundo tamanho de amostra no mesmo período falha de forma segura. Reexecução com o mesmo `sample_id` também não duplica linhas.
- **Privacidade Silver**: Testes confirmam que documentos de sócio e representante não aparecem em valor bruto fora da Bronze, e que os pseudônimos versionados são determinísticos.
- **Observabilidade de CNPJ inválido**: Fixtures com valores inválidos confirmam métricas por arquivo sem registrar o valor descartado.
- **Comportamento do Snapshot SCD Tipo 2**: Fixture com duas versões temporais consecutivas comprova que apenas variações no Capital Social encerram o registro anterior (`valid_to`) e abrem nova versão ativa.
- **Subprocessos dbt e Prefect**: Testes de ponta a ponta validam que códigos de erro emitidos pelo dbt são capturados e propagados pelo Prefect.
