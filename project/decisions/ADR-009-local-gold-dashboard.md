---
id: ADR-009
status: accepted
date: 2026-09-09
decision_makers: [project]
---

# Expor Gold somente em dashboard local de loopback

## Contexto

O desafio exige execução local com DuckDB e o operador precisa explorar os resultados sem abrir Bronze ou Silver, que podem conter atributos restritos. A auditoria local também identificou a necessidade de distinguir o dashboard de consumo da inspeção operacional por camada.

## Decisão

O projeto fornece um dashboard Streamlit vinculado exclusivamente a `127.0.0.1`. Ele abre o DuckDB com `read_only=True`, consulta apenas a superfície Gold do contrato analítico e apresenta somente agregações, catálogo e tabelas de domínio permitidas. Não cria API pública, autenticação, exportação, cloud, credencial nem mecanismo de escrita.

Bronze, Silver, snapshots e `ops` continuam fora do dashboard. Um inspector de operador pode reportar apenas contagens, grãos, lotes, manifestos e integridade resumida dessas camadas, sem linhas ou campos restritos.

## Consequências

O dashboard é um extra local do desafio e requer dependência versionada e testes de contrato. O operador continua responsável por encerrar o processo e reter/remover runtime manualmente.

## Validação

Testes confirmam abertura read-only, bloqueio de relações fora do contrato e ausência de identificadores de empresa em tabelas analíticas. Um ensaio sintético confirma o dashboard contra um warehouse produzido pelo fluxo.
