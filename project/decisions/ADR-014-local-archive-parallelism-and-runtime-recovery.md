---
id: ADR-014
status: accepted
date: 2026-09-10
decision_makers: [project]
---

# Paralelizar arquivos localmente e recuperar runtime de modo explícito

## Decisão

O backfill mantém uma coorte determinística de 10.000 empresas e um único DuckDB writer. Validação, ranking local de shards de estabelecimentos e filtragem de arquivos independentes usam processos locais limitados. Os resultados são fundidos na ordem canônica antes de Bronze.

O padrão é dois workers locais, com máximo configurável de quatro. `parallel_jobs` continua sendo semântica de coorte e não controla esta concorrência física.

Artefatos de runtime com identidade anterior só são reutilizados após compatibilidade comprovada; caso contrário a execução falha com diagnóstico explícito, sem apagar ou mesclar warehouses.

## Consequências

Não há Spark, Dask, Ray, múltiplos workers Prefect ou múltiplos writers DuckDB. Períodos continuam em ordem no trecho Bronze→Gold. Métricas agregadas por estágio são obrigatórias para comparar execução serial e concorrente.
