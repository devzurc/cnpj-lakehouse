---
id: ADR-012
status: accepted
date: 2026-09-29
decision_makers: [project]
---

# Nomear o produto como CNPJ Lakehouse

## Decisão

A identidade pública do repositório é **CNPJ Lakehouse**. Não aparecem
nomes de cliente ou empresa anteriores em código, documentação, testes,
configuração, skills ou identificadores operacionais.

Namespace canônico:

- Título: CNPJ Lakehouse
- Pacote Python: `cnpj_lakehouse`
- CLI: `cnpj-lakehouse`, `cnpj-lakehouse-serve`, `cnpj-lakehouse-dashboard`
- Variáveis de ambiente: `CNPJ_LAKEHOUSE_*`
- Projeto/perfil dbt: `cnpj_lakehouse`
- Flow Prefect: `cnpj-lakehouse`
- Deployment: `monthly-ingest` (referência `cnpj-lakehouse/monthly-ingest`)
- Runs: `lakehouse-YYYYMMDD-HHMM` (agendado) ou `lakehouse-YYYYMMDDHHMMSS` (disparo)
- Runtime sintético/operador: `$HOME/.local/share/cnpj-lakehouse`
- Runtime de backfill isolado: `$HOME/.local/share/cnpj-lakehouse-official`
- Warehouse: `cnpj_lakehouse.duckdb`
- Volumes Docker: cnpj_lakehouse_runtime, cnpj_lakehouse_prefect_state
- Projeto Compose: `cnpj-lakehouse`
- Skills: `cnpj-lakehouse-*`

Não há aliases para identificadores anteriores. Um warehouse já existente em
outro caminho continua acessível só se o operador exportar
`CNPJ_LAKEHOUSE_RUNTIME_ROOT` / `CNPJ_LAKEHOUSE_DUCKDB_PATH` para esse caminho.

## Consequências

O runner Prefect registra o deployment `cnpj-lakehouse/monthly-ingest`.
Deployments com nomes anteriores na UI local deixam de receber runs. Um
backfill já em memória não deve ser interrompido: após o término, retome no
runtime isolado apontando as variáveis `CNPJ_LAKEHOUSE_*` para o warehouse em uso.

## Validação

Testes de launcher, Compose, settings, backfill e deployment cobrem os nomes
canônicos e o isolamento entre o share sintético e o runtime de backfill.
