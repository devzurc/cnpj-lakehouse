---
id: ADR-011
status: accepted
date: 2026-09-09
decision_makers: [project]
---

# Tornar o fluxo oficial Prefect a interface principal de entrega

## Decisão

O deployment Prefect local é a única orquestração de produção: fontes remotas
oficiais, Bronze, dbt, validação analítica e dashboard passam pelo mesmo fluxo.
O operador inicia a infraestrutura e dispara manualmente o deployment na UI.
Fontes sintéticas permanecem restritas a testes e ensaios de desenvolvimento.

O runtime é sempre externo ao repositório. Um lock exclusivo cobre uma execução
inteira do warehouse, da carga Bronze até a validação analítica. Bronze preserva
valores brutos vazios como strings; uma mudança incompatível de contrato requer
novo runtime, sem reescrever o histórico append-only existente.

## Consequências

Backfill anual submete execuções sequenciais do mesmo fluxo Prefect. Artefatos
dbt exigem IDs de invocação não vazios e coerentes antes de promoção. A evidência
anterior que converteu vazios em nulos é diagnóstica e não certifica a entrega.

## Validação

Testes cobrem preservação de vazios, isolamento do runtime, lock de execução,
propagação de falha, validação Gold e reexecução idempotente. A certificação
official-volume usa warehouse novo e verificadores agregados por período.
