---
id: ADR-004
status: accepted
date: 2026-09-06
decision_makers: [project]
---

# Padronizar a data de referência de atividade para o último dia do período da fonte

## Contexto

A tabela fato diária `fct_company_activity_daily` captura métricas e o estado operacional de empresas ativas em uma data de referência analítica (`reference_date`). Como a base da Receita Federal é disponibilizada em lotes mensais agregados (ex.: `202601`), é necessário definir uma convenção canônica estável para determinar o valor padrão do `reference_date` quando não fornecido explicitamente pelo operador.

## Decisão

Adotar como padrão o último dia civil do mês correspondente ao `source_period` processado (ex.: para `source_period = 202601`, a data de referência padrão é `2026-01-31`), permitindo sobreposição explícita através do parâmetro `reference_date` na execução do pipeline Prefect.

## Consequências

As partições da tabela fato tornam-se naturalmente consistentes e idempotentes entre execuções mensais. O modelo incremental do dbt pode fazer a substituição cirúrgica (`delete+insert`) da partição exata daquele mês sem risco de duplicidade de chaves primárias.

## Validação

Testes de inserção incremental verificam que reprocessamentos com o mesmo `reference_date` substituem atomicamente apenas a partição afetada, mantendo integridade e contagens sem duplicação.
