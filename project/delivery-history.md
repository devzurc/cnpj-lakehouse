# Índice de entrega

Evidência agregada das sprints 00–22. Contratos vigentes estão em `specifications/` e `decisions/`. O checkpoint resume prontidão local versus ações externas. Não reabrir pastas de tarefa para consultar este histórico.

| Sprint | Resultado | Estado |
|---|---|---|
| 23 (`sprint-23-cnpj-lakehouse-identity`, S23-01) | Identidade `cnpj-lakehouse`, README de portfólio, CI e agregados Gold. Gates locais passaram. Repositório `devzurc/cnpj-lakehouse`, tag `v1.0.0` em `origin/main`. | complete |
| 22 (`sprint-22-submission-readiness`, S22-01) | Auditoria de submissão contra o PDF original e checklist de handoff; estrutura, Ruff, PDF FinOps, sync offline, 99 testes e demo Docker sintética passaram. Revalidado em 2026-09-14 | complete |
| 00 | Governança, specs, skills e revisores | complete |
| 01 | Ingestão Bronze, amostra determinística, relacionamentos | complete |
| 02 | dbt Silver, snapshot SCD2, Gold e testes | complete |
| 03 | Prefect, artefatos por `flow_run_id`, PDF FinOps | complete |
| 04 | Segurança local, lote ativo, isolamento dbt | complete |
| 05 | Governança de IA (7 skills, 6 revisores) | complete |
| 06 | Higiene Git, runtime owner-only | complete |
| 07 | Qualidade, ensaio sintético E2E | complete |
| 08 | Período mensal dinâmico e deployment `monthly-ingest` | complete |
| 09 | Scorecard, clone limpo, dossiê local | complete |
| 10 | Contrato analítico Gold e verificador | complete |
| 11 | Dashboard Gold read-only e README operacional | complete |
| 12 | Backfill oficial 2026 em warehouse isolado (`S12-01`) | blocked |
| 13 | Amostragem em jobs disjuntos (ADR-013) | complete |
| 14 | Workers locais por arquivo e recuperação (ADR-014) | complete |
| 15 | Pseudônimo de documentos na Silver (ADR-015) | complete |
| 16 | Handoff local e prova de clone | complete |
| 17 | `.dockerignore` e revalidação Docker/pytest | complete |
| 18 (`sprint-18-recruiter-repository-hygiene`, S18-01) | Forma do repositório de entrega (ADR-016): índice no lugar das pastas de tarefa | complete |
| 19 (`sprint-19-prefect-ui-loopback`, S19-01) | UI Prefect no loopback; SQLite só no servidor | complete |
| 20 (`sprint-20-ingestion-inventory`, S20-01) | Inventário present/missing/Bronze; mesmo lote não baixa de novo | complete |
| 21 (`sprint-21-delivery-publication`, S21-01) | Auditoria documental e publicação de `main` | complete |

`S12-01` permanece `blocked`: janeiro oficial verificado; a série anual não foi concluída. Não misturar o warehouse sintético com o runtime oficial.
