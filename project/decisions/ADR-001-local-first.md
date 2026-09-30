---
id: ADR-001
status: accepted
date: 2026-09-06
decision_makers: [project]
---

# Utilizar DuckDB como motor de execução oficial obrigatório

## Contexto

O desafio de engenharia propõe o processamento dos dados públicos de CNPJ da Receita Federal e a definição de uma arquitetura analítica em nuvem (BigQuery). Para viabilizar uma entrega totalmente auditável, reprodutível e livre de barreiras de custo, faturamento em nuvem ou provisionamento de credenciais pagas por parte dos avaliadores, é necessário estabelecer um motor de execução padrão para o pipeline.

## Decisão

Implementar e validar todo o pipeline de ponta a ponta localmente utilizando DuckDB como banco de dados analítico e engine SQL do dbt Core. A arquitetura BigQuery permanece como um entregável de design de produção, modelagem física e guia de FinOps.

## Consequências

O projeto é 100% executável por qualquer avaliador sem necessidade de conta GCP ou credenciais de serviço. O tempo de engenharia prioriza a corretude semântica dos dados, testes e resiliência antes da complexidade operacional de nuvem.

## Validação

Validação com execução bem-sucedida do pipeline via dbt Core (`dbt-duckdb`) e Prefect, persistindo os dados em arquivo `.duckdb` local e passando em todos os testes unitários e de integração sem dependências de serviços em nuvem.
