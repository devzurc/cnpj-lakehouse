# Checkpoint de Prontidão da Entrega

Última reconciliação: 2026-09-30 — Sprint 23 `complete` (`S23-01`); `origin/main` = `b7d3cfe` em `devzurc/cnpj-lakehouse`, tag `v1.0.0`; S12-01 permanece bloqueada

Este checkpoint resume evidências já verificadas. Ele não substitui especificações, ADRs ou artefatos de execução e não concede autorização para ações externas.

## Estado Atual

> A Sprint 23 publicou a identidade CNPJ Lakehouse. `origin/main` é `b7d3cfe` e a tag `v1.0.0` está no remoto. S12 permanece bloqueada. Cloud, PR e GitHub Release exigem autorização explícita.

| Área | Estado | Evidência durável |
|---|---|---|
| Requisitos e rastreabilidade | APROVADO LOCAL | Matriz de aceite e scorecard ligam requisitos às evidências atuais. IDs de sprint são rastreio, não pastas. |
| Bronze oficial 202601 | APROVADO | Amostra `24700fc9536c350fbb89`: 10.000 empresas, 10.349 estabelecimentos, 4.057 sócios, 7.058 registros do Simples e 1.359 CNAEs; verificador reforçado passou. |
| Silver, snapshot e Gold | APROVADO LOCAL — S15-01 | Documentos de sócio/representante são pseudônimos na Silver; valor bruto só na Bronze. |
| Orquestração Prefect | APROVADO LOCAL | Alvos dbt privados, lock exclusivo, contrato Gold in-process e `task_run_name` português. |
| Agendamento mensal Prefect | APROVADO LOCAL — S19-01 | Código nomeia `cnpj-lakehouse/monthly-ingest` (`0 9 7 * *`, `America/Sao_Paulo`). Após recreate: `/api/health` 200, `ui-settings.api_url=/api`, filter de deployments devolve `monthly-ingest` READY. |
| Contrato analítico DuckDB | APROVADO LOCAL — S11-02 | Dashboard Gold em loopback; quatro relações autorizadas read-only. |
| Inventário de ingestão | APROVADO LOCAL — S20-01 | `cnpj-lakehouse plan` lista ZIPs presentes/faltantes e Bronze do período; ZIP local não dispara HTTP; mesma coorte reutiliza Bronze; segundo sample no `YYYYMM` é recusado. |
| Operação e README E2E | APROVADO LOCAL — S21-01 | README único. Validador: índice + 7 skills + 6 revisores. `UV_OFFLINE=1 uv sync --all-groups --locked`; `pytest -q` 99 passed (505 s em 2026-09-14); 67 Markdowns rastreados sem links relativos quebrados. |
| Amostragem paralela | APROVADO LOCAL — S13-01 | Padrão 1×10.000; extração paralela; Bronze/dbt sequenciais. |
| Backfill 2026 | BLOQUEADO — S12-01 | Janeiro verificado; conclusão anual pendente. |
| Runtime Docker Compose | APROVADO LOCAL — S23-01 | Em 2026-09-30, `./scripts/docker.sh start` / `demo` / `verify` via `docker.exe`: imagens `cnpj-lakehouse-*`; flow sintético COMPLETED; 3 empresas nas camadas Bronze, Silver e Gold (`sample_id` `7e6c1d126e749e4673c4`); contrato analítico sem duplicidades, referências ausentes ou falha de snapshot. CLI `docker` nativo ausente neste WSL. |
| FinOps | APROVADO | `docs/finops-bigquery-architecture.pdf` (6 páginas A4). |
| Identidade pública | APROVADO — S23-01 | Namespace `cnpj-lakehouse` no código, Compose, volumes e skills. Repositório `https://github.com/devzurc/cnpj-lakehouse`. Histórico publicado: um commit, `b7d3cfe`. |
| Clone limpo | APROVADO LOCAL — S21-01 | `UV_OFFLINE=1` com cache populado nesta revisão (2026-09-14); pytest 99 passed. Não prova cache vazio. |
| Higiene Git local | APROVADO | Runtime, DuckDB e artefatos dbt excluídos; PDF FinOps rastreado. |
| Governança de IA | APROVADO — ADR-016 | 7 skills e 6 revisores; validador não exige diário de tarefas. |
| Repositório GitHub | APROVADO | `https://github.com/devzurc/cnpj-lakehouse`, público. |
| Publicação do branch `main` | APROVADO | `origin/main` = `b7d3cfe`. Tag `v1.0.0` enviada. PR, GitHub Release e cloud permanecem PENDENTE. |

## Gates para Alterações Futuras

1. Ler `project/active-sprint.md`, o backlog aberto e as especificações vinculadas.
2. Executar o menor gate relevante e depois a verificação obrigatória da mudança.
3. Atualizar backlog, índice, changelog e este checkpoint quando a verdade registrada mudar.
4. Confirmar `git diff --check`, higiene dos arquivos rastreados e worktree.
5. Tratar publicação Git, PR, release e cloud como checkpoints externos.

## Próxima Ação Externa

`origin/main` está em `b7d3cfe`, tag `v1.0.0`. PR, GitHub Release e cloud exigem autorização imediata antes da ação.
