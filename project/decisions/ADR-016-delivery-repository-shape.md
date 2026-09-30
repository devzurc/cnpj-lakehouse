---
id: ADR-016
status: accepted
date: 2026-09-10
decision_makers: [project]
---

# Forma do repositório de entrega

## Contexto

As Sprints 00–17 deixaram 55 Markdowns de tarefa como diário de processo. O validador estrutural exigia cada README, o que acoplava a entrega ao histórico de execução. Para o recrutador o caminho operacional é Docker → Prefect → Bronze/dbt/Gold → verify → dashboard; as especificações e ADRs já registram o porquê.

## Decisão

O repositório de entrega retém especificações canônicas, ADRs, requisitos, knowledge, checkpoint, skills e revisores. O histórico de sprints vive em um único índice (`project/delivery-history.md`). Não há pastas `project/sprints/*/tasks/`.

Trabalho residual (hoje S12-01, backfill oficial 2026) fica no backlog e no checkpoint, sem pasta de tarefa. Trabalho novo reabre uma linha no backlog e em `project/active-sprint.md`; não recria a árvore histórica.

O validador confirma artefatos canônicos, skills, revisores, higiene Git e o índice. Ele não conta READMEs de tarefa.

## Consequências

Evidência agregada permanece no checkpoint e no CHANGELOG. IDs históricos (`S01-01`, …) continuam na matriz de aceite como rastreio, não como caminhos de arquivo. Spark/Dask/Ray continuam fora do escopo (ADR-014).

## Validação

`uv run python scripts/validate_project_structure.py` passa sem `project/sprints/`. O README descreve o ensaio sintético e o ingest oficial sem o guia `docs/delivery-handoff.md`.
