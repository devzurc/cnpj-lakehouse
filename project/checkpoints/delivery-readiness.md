# Checkpoint de Prontidão da Entrega

Última reconciliação: 2026-09-29 — Sprint 23 `in_progress` (`S23-01`); identidade CNPJ Lakehouse no código; publicação do histórico limpo permanece checkpoint externo; S12-01 permanece bloqueada

Este checkpoint resume evidências já verificadas. Ele não substitui especificações, ADRs ou artefatos de execução e não concede autorização para ações externas.

## Estado Atual

> A Sprint 23 define a identidade CNPJ Lakehouse e revalidou o ensaio Docker sintético em 2026-09-30. S12 permanece bloqueada. Sprints 20–22 concluíram inventário, publicação anterior e a auditoria de submissão. Cloud, PR e release exigem autorização explícita. A publicação deste histórico limpo ainda está pendente.

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
| Identidade pública | APROVADO LOCAL — S23-01 | Namespace `cnpj-lakehouse` no código, Compose, volumes e skills. Containers do ensaio: `cnpj-lakehouse-prefect-server-1`, `cnpj-lakehouse-prefect-runner-1`, `cnpj-lakehouse-dashboard-1`. A publicação deste histórico ainda está pendente. |
| Clone limpo | APROVADO LOCAL — S21-01 | `UV_OFFLINE=1` com cache populado nesta revisão (2026-09-14); pytest 99 passed. Não prova cache vazio. |
| Higiene Git local | APROVADO | Runtime, DuckDB e artefatos dbt excluídos; PDF FinOps rastreado. |
| Governança de IA | APROVADO — ADR-016 | 7 skills e 6 revisores; validador não exige diário de tarefas. |
| Repositório GitHub | CRIADO | Remoto `origin` configurado. Rename público exige autorização. |
| Publicação do branch `main` | APROVADO | Push autorizado em 2026-09-10; `origin/main` = `19d48b9` (inventário S20 + auditoria S21 + registro da publicação). Commits locais de S22 e desta auditoria ainda não foram enviados. PR, release, rename do remoto e cloud permanecem PENDENTE. |

## Gates para Alterações Futuras

1. Ler `project/active-sprint.md`, o backlog aberto e as especificações vinculadas.
2. Executar o menor gate relevante e depois a verificação obrigatória da mudança.
3. Atualizar backlog, índice, changelog e este checkpoint quando a verdade registrada mudar.
4. Confirmar `git diff --check`, higiene dos arquivos rastreados e worktree.
5. Tratar publicação Git, PR, release e cloud como checkpoints externos.

## Próxima Ação Externa

`origin/main` está em `19d48b9`. Os commits locais de S22 (checklist de submissão) e desta auditoria ainda não foram publicados. PR, release, rename do remoto e cloud exigem autorização imediata antes da ação.
