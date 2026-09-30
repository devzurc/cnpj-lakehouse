---
id: ADR-010
title: Runtime local containerizado com Docker Compose
status: accepted
date: 2026-09-09
---

# ADR-010 — Runtime local containerizado com Docker Compose

## Decisão

O projeto oferece Docker Compose como caminho reproduzível para subir Prefect Server, runner, bootstrap sintético, DuckDB/dbt e dashboard. O estado é persistido nos volumes nomeados cnpj_lakehouse_runtime e cnpj_lakehouse_prefect_state; as portas publicadas no host ficam restritas a `127.0.0.1`.

## Consequências

- Python, uv, Prefect, dbt e Streamlit são instalados a partir do lockfile na imagem.
- O bootstrap padrão é sintético, idempotente e usa `sample_size=3`, período `202601` e referência `2026-01-31`.
- O dashboard recebe o DuckDB em modo read-only e exibe somente Gold.
- O browser fala com a API em `/api` no mesmo origin; runner e bootstrap usam `http://prefect-server:4200/api`. Só o servidor monta `cnpj_lakehouse_prefect_state`.
- `docker compose stop` preserva evidências; remoção de volumes é deliberadamente uma operação manual.
- Docker Desktop/Engine, virtualização, arquitetura suportada e portas livres continuam sendo pré-requisitos do host.
- Nenhum serviço habilita cloud, download oficial ou publicação externa.
