# Scorecard de Entrega Local

Este scorecard mede a entrega local verificável. Ele não concede publicação, PR, release ou uso de cloud.

| Área | Pontos | Evidência principal | Gate para 100/100 local | Estado atual |
|---|---:|---|---|---|
| Domínio de dbt Core | 30 | Medalhão, macros, incremental, SCD2 e testes | `dbt compile/build`, testes dbt e pytest sintéticos | Aprovado local; S21 passou |
| Arquitetura e resiliência | 25 | Bronze imutável, locks, idempotência, Prefect e artefatos | demo Docker, verificadores e inspeção do deployment | Aprovado local; S18 Docker + S20 inventário |
| Qualidade de dados | 20 | contratos, testes dbt, negativos e amostragem determinística | `pytest -q`, `dbt test`, `verify_bronze.py` | Aprovado local; 2026-09-14 `pytest -q` 99 passed |
| BigQuery e FinOps | 15 | desenho físico e controles no PDF em Português | `verify_finops_pdf.py docs/finops-bigquery-architecture.pdf` | Aprovado local |
| Código limpo e governança Git | 10 | lockfile, higiene, índice de entrega | estrutura, Ruff, diff e clone limpo | Aprovado local; S21 passou |
| **Total local** | **100** | matriz de aceite e [delivery-history](../delivery-history.md) | gates S21 e worktree intencional | **100/100 local** |

## Condição de pontuação máxima local

Os cinco blocos de pontuação exigem gates executados na revisão candidata atual. Reconciliação 2026-09-14: estrutura, Ruff, FinOps PDF (6 páginas A4), `UV_OFFLINE=1 uv sync --all-groups --locked`, `pytest -q` (99 passed), 67 Markdowns rastreados e ensaio Docker sintético via `docker.exe`. Publicação remota exige `origin/main` verificado após o push.
