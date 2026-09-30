# Especificação do Projeto dbt Core

## Materializações por Camada

- **Staging (`models/staging`)**: `view` — Projeções limpas sobre as tabelas brutas Bronze, sem persistência redundante em disco.
- **Intermediárias (`models/intermediate`)**: `table` — Agregações reutilizadas e consolidações pré-calculadas para otimizar desempenho de joins downstream.
- **Dimensões Gold (`models/marts/dim_*`)**: `table` — Tabelas dimensionais físicas reconstruídas para consultas de alta performance.
- **Histórico de Capital (`models/marts/dim_company_capital_history`)**: `view` — Projeção analítica amigável sobre o snapshot SCD Tipo 2.
- **Fato de Atividade (`models/marts/fct_company_activity_daily`)**: `incremental` — Utiliza estratégia nativa `delete+insert` do adaptador DuckDB escopada cirurgicamente ao `reference_date`.

## Lote Ativo

Cada invocação recebe `source_period`, `sample_id` e `reference_date`. Staging filtra a Bronze por `source_period + sample_id` antes de qualquer deduplicação; a fato remove toda a partição da data solicitada antes de inserir o resultado ativo.

## Macros Jinja Obrigatórias

- `normalize_cnpj(cnpj_basico, cnpj_ordem=none, cnpj_dv=none)`: Remove pontuações, preserva os zeros à esquerda e retorna nulo quando a estrutura não possui exatamente 8 dígitos para raiz ou 14 dígitos para estabelecimento completo.
- `parse_decimal_br(expression)`: Converte seguramente valores numéricos formatados no padrão brasileiro (ex.: `1.234.567,89`) para o tipo `decimal(18,2)`, tratando nulos e formatações inconsistentes sem interromper o pipeline.
- `normalize_cnae(expression)`: Limpa e formata o código de atividade econômica, retornando exatamente 7 dígitos numéricos ou nulo.
- `add_audit_columns()`: Injeta metadados de execução padrão do dbt (`dbt_invocation_id` e `dbt_updated_at`), mantendo a rastreabilidade conjunta com o `source_period` e `sample_id` vindos da camada Bronze.

## Snapshot de Histórico de Capital Social (SCD Tipo 2)

O snapshot `company_capital_social_snapshot` (localizado em `dbt/snapshots/`) adota a estratégia `check`:
- **Chave única (`unique_key`)**: `cnpj_basico`
- **Coluna monitorada (`check_cols`)**: `['capital_social']`
- **Schema alvo**: `snapshots`
- **Comportamento**: Apenas alterações reais no valor do Capital Social encerram a versão anterior (`valid_to = now()`) e abrem uma nova versão vigente. Execuções com dados idênticos são estritamente idempotentes e não criam novas versões.

Todos os testes genéricos de negócio, inclusive unicidade de combinação de colunas, pertencem ao repositório. Um ambiente sincronizado executa dbt sem resolver pacotes externos pela rede.
