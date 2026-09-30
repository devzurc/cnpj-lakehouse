# Registro de Alterações (Changelog)

Todas as alterações notáveis deste projeto serão documentadas neste arquivo.

O formato é baseado em [Keep a Changelog](https://keepachangelog.com/pt-BR/1.0.0/),
e este projeto adere ao [Versionamento Semântico](https://semver.org/lang/pt-BR/).

## [Não publicado]

### Em andamento
- Sprint 23 (`in_progress`; S23-01): identidade pública CNPJ Lakehouse (`cnpj_lakehouse`, CLI `cnpj-lakehouse`, variáveis `CNPJ_LAKEHOUSE_*`, dbt `cnpj_lakehouse`, flow `cnpj-lakehouse`, volumes `cnpj_lakehouse_runtime` e `cnpj_lakehouse_prefect_state`, projeto Compose `cnpj-lakehouse`). README de portfólio, workflow de CI e agregados Gold de regime, capital e concentração de CNAE. Versão `1.0.0`. Gates locais: estrutura; `ruff check .`; FinOps PDF 6 páginas; `pytest -q` 99 passed (417 s); `docker.exe compose` `start` / `demo` COMPLETED / `verify` (3 empresas sintéticas, `sample_id` `7e6c1d126e749e4673c4`, Bronze, Silver e Gold). A publicação do histórico limpo ainda não está registrada neste texto.
- Auditoria transversal 2026-09-14: checkpoint alinhado a `origin/main` (`19d48b9`); 67 Markdowns rastreados sem links relativos quebrados; comandos FinOps passam a citar `docs/finops-bigquery-architecture.pdf`. Gates: estrutura; `ruff check .`; FinOps PDF 6 páginas; `UV_OFFLINE=1 uv sync --all-groups --locked`; `pytest -q` 99 passed (505 s); `docker.exe compose config`; `./scripts/docker.sh start` / `demo` / `verify` / `stop` (3 empresas sintéticas, mesmo `sample_id`). CLI `docker` nativo ausente neste WSL; o launcher usou `docker.exe`. S12-01 permanece `blocked`. Nenhuma publicação remota é implícita.
- Sprint 22 (`complete`; S22-01): auditoria de submissão contra o desafio original e matriz de handoff. Estrutura, Ruff, PDF FinOps, sync offline, `pytest -q` (99 passed, 415 s) e demo Docker sintética com verificadores Bronze, warehouse e contrato analítico passaram. Nenhuma publicação remota é implícita.
- Sprint 21 (`complete`; S21-01): auditoria documental (66 Markdowns, 0 links relativos quebrados; specs de inventário alinhadas) e publicação verificada de `origin/main` (`f3f6942`). Gates: estrutura; `ruff check .`; FinOps PDF 6 páginas; `UV_OFFLINE=1 uv sync --all-groups --locked`; `pytest -q` 99 passed (450 s); `docker compose config`. S12-01 permanece `blocked`.
- Sprint 20 (`complete`; S20-01): inventário present/missing/Bronze; ZIP local `reused` sem HTTP; mesma coorte reutiliza Bronze; segundo sample no período recusado.
- Sprint 19 (`complete`; S19-01): UI Prefect no browser usa same-origin `/api`; runner/bootstrap falam com `http://prefect-server:4200/api` e não montam o SQLite do servidor. Recreate: health 200, `monthly-ingest` READY, sem `database is locked`.
- Sprint 18 (`complete`; S18-01): ADR-016; índice no lugar das pastas de tarefa; README único. Revalidação: `UV_OFFLINE=1 uv sync --all-groups --locked`; estrutura; Ruff; `pytest -q` 92 passed; Docker `start`, duas `demo` COMPLETED, `verify` (3 empresas, Bronze idempotente), dashboard e Prefect 200, `stop`. S12-01 permanece `blocked`.
- Sprint 17 (`complete`; S17-01): contexto Docker explícito e reconciliação da evidência de entrega.
- Sprint 14 (`complete`; S14-01 `done`): recuperação fail-closed e workers locais por arquivo; S12-01 segue bloqueada.
- Sprint 13 (`complete`; S13-01 `done`): amostragem configurável em jobs disjuntos (ADR-013).

### Adicionado
- ADR-016: forma do repositório de entrega (specs/ADRs/skills permanecem; diário de sprint vira índice).
- ADR-015: documentos de sócio e representante passam a pseudônimos SHA-256 versionados na Silver; métricas de CNPJ inválido ficam agregadas por arquivo no manifesto da amostra.
- ADR-013: amostragem configurável (`CNPJ_LAKEHOUSE_SAMPLE_SIZE` × `CNPJ_LAKEHOUSE_PARALLEL_JOBS` ou `config/sampling.toml`); 4×5.000 = 20.000 CNPJs disjuntos, extração paralela, um Bronze/DuckDB. Padrão do desafio permanece 1×10.000. Backfill oficial permanece 1 job.
- ADR-014: processos locais limitados por arquivo, merge determinístico, métricas agregadas e recuperação explícita de warehouse; Bronze/dbt continuam single-writer.
- Identidade pública CNPJ Lakehouse: pacote `cnpj_lakehouse`, CLI `cnpj-lakehouse`, variáveis `CNPJ_LAKEHOUSE_*`, dbt `cnpj_lakehouse`, flow `cnpj-lakehouse` (ADR-012).
- Sprint 12: descoberta de períodos com um único diretório no índice, CLI `list-source-periods` / `backfill-year` e launcher `scripts/backfill.sh`.
- Sprint 11: dashboard Gold read-only, inspector seguro, launcher `local.sh`, runtime Docker Compose (ADR-009/010) e README E2E com layout `$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run`.
- ADR-009, dashboard Streamlit vinculado a `127.0.0.1` e inspector seguro de metadados por camada, sem linhas restritas.
- Sprint 08: resolução automática do mês calendário anterior em `America/Sao_Paulo`, deployment Prefect local mensal e runbook de rerun/backfill.
- Sprint 06: helpers de runtime owner-only, validação explícita do lote dbt e testes de regressão para permissões/entradas obrigatórias.
- Sprint 05: especificação canônica de governança de IA, matriz de roteamento para sete skills e seis revisores, e skill `cnpj-lakehouse-workflow-audit` para auditorias transversais sem mutação.
- Sprint 04 de remediação: ADRs de lote ativo e segurança local, especificação de governança, skill de segurança e revisores de segurança/higiene.
- Reuso autenticado de amostras, validação de manifestos, hashes de registro e testes de adulteração.
- Isolamento de `target` dbt, lock de escrita DuckDB, variáveis de lote ativo e retenção validada de artefatos owner-only.
- Registro de exceção limitada para a única vulnerabilidade WeasyPrint sem correção disponível; atualização para WeasyPrint 68.1 remove a vulnerabilidade corrigível.
- Manifestos de fonte imutáveis e endereçados por conteúdo, com URL, tamanho, SHA-256, membros ZIP, contagem de linhas e identificador determinístico.
- Verificador Bronze para tamanho exato da amostra, concordância com manifesto, linhagem, CNAE e ausência de órfãos.
- Testes negativos para resolução de shards, HTTP permanente/transitório, resíduos `.part`, ZIPs inválidos, schema drift, encoding e reutilização segura.
- Documentação de grão intermediário, teste genérico local de chave composta e teste singular da macro `normalize_cnpj`.
- Testes do flow Prefect decorado, ordem dbt, propagação de falha e isolamento de artefatos obsoletos.
- Checkpoint de prontidão que separa evidências locais aprovadas da publicação externa pendente.
- Hardening das skills, revisores somente-leitura, salvaguardas remotas e validador de governança.

### Alterado
- O launcher Prefect declara timeout SQLite de 60 segundos; a documentação corrente obtém o inventário dbt por comando em vez de fixar uma contagem histórica.
- Amostras gzip agora têm cabeçalho determinístico; `ingestion_workers` usa processos `spawn`, tem máximo aplicado em todas as fronteiras e a recuperação falha ao encontrar warehouses concorrentes ou legado incompatível.
- O CLI e flow aceitam `source_period` opcional: o valor explícito continua prioritário e a data de referência deriva do período resolvido.
- O deployment `cnpj-lakehouse/monthly-ingest` agenda dia 7 às 09:00 em `America/Sao_Paulo`, com amostra de 10.000, `full_refresh=false`, fontes remotas e `output_path=$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run`.
- README, `.env.example`, `.gitignore`, launcher Prefect, dependências e documentação YAML foram simplificados e reconciliados para revisão local portátil.
- Carga Bronze migrou de inserção linha a linha para importação DuckDB transacional em lote, preservando hashes canônicos.
- Reexecuções reutilizam manifestos somente após correspondência de arquivos, tamanhos e checksums; amostras concluídas retornam no-op.
- O estabelecimento representativo é escolhido em uma única linha ativa determinística: matriz primeiro, senão o menor CNPJ completo.
- O runtime dbt deixou de resolver pacotes externos e retém artefatos de cada comando sob o UUID real do flow Prefect.
- Documentação e contratos dbt foram ampliados para a suíte real de 40 testes.

### Corrigido
- O contrato Gold no flow Prefect falha in-process com a mensagem do verificador (`ValueError`), não com `CalledProcessError` de subprocesso.
- As quatro etapas dbt usam `task_run_name` em português (`executar-dbt-silver|snapshot|gold|testes`) sem alterar os rótulos de artefato.
- Os testes de orquestração chamam o corpo do flow sem anexar à API Prefect do operador (`127.0.0.1:4200`).
- README, execução local e o runbook Gold apontam o backfill para o runtime isolado; o README deixa explícito que só o download é paralelo (3 streams) e que meses/dbt são sequenciais.
- O launcher de backfill usa `cnpj_official_runtime_root` (nunca o share sintético) e grava `cnpj_lakehouse.duckdb` no runtime isolado.
- O runtime deixa de depender do umask para dados/evidências restritos e o dbt deixa de aceitar lote ativo ausente como resultado vazio.
- `normalize_cnpj` não fabrica mais `00000000` para entradas vazias ou estruturalmente inválidas.
- CNAE e UF representativos não podem mais vir de estabelecimentos diferentes.
- O download remove arquivos parciais após falhas e limita retentativas a erros transitórios.
- Caminhos pessoais, telemetria dbt e artefatos gerados foram removidos do conjunto rastreado.
- Contagens, nomes de tabelas operacionais e estados de sprint foram reconciliados em toda a documentação.
- Sprint 07: a execução direta do CLI não depende mais de uma API Prefect efêmera; a qualidade agora cobre SCD2, grão de CNAE secundário, decimais inválidos e fontes-filhas vazias.

### Verificado
- Sprint 16: clone Linux limpo com `UV_OFFLINE=1` (cache populado), estrutura, Ruff e suíte completa passou; Docker Compose completou duas demos sintéticas aguardadas pelo launcher, verificadores Bronze/Warehouse/contrato e rerun idempotente. O launcher aceita Docker Engine Linux e fallback `docker.exe` quando a integração WSL não está disponível.
- Identidade pública na árvore atual: busca case-insensitive pelo identificador do cliente anterior = 0 em conteúdo e nomes de arquivo; `pytest -q` 74 passed; `ruff check .`; estrutura (36/7/6); dbt parse/compile/ls em warehouse temporário; PDF FinOps 6 páginas. Histórico Git ainda contém o identificador anterior (12 commits). Deployment Prefect novo ainda não registrado na UI local.
- Publicação Git: `origin/main` atualizado em 2026-09-10 (inclui a correção da UI Prefect).
- Sprints 09–10: revisão `c933b73` passou clone limpo offline, estrutura, Ruff, regressão, demo sintética, verificadores Bronze/Warehouse/contrato analítico e rerun idempotente; scorecard local atingiu 100/100.
- Sprint 09: clone limpo da revisão local `29a58e3` passou sincronização offline por cache, estrutura, Ruff, testes, demo sintética completa, verificadores e rerun idempotente, sem publicação externa.
- Sprint 08: servidor Prefect dedicado local confirmou o cron/timezone/parâmetros; ensaio sintético confirmou ordem, artefatos e propagação dbt. `pytest -q` passou com 42 testes, assim como Ruff, estrutura, PDF FinOps e diff.
- Sprint 07: `pytest -q`, demo sintética completa, `dbt debug/compile/build/snapshot`, verificadores Bronze/Warehouse, estrutura, Ruff, PDF FinOps (6 páginas) e `git diff --check` passaram sem ações externas.
- Sprint 06: `UV_OFFLINE=1 uv sync --all-groups --locked`, estrutura, Ruff, diff e `pytest -q` (31 passed, 1 skipped) passaram; caches e saídas dbt ignoradas foram removidos da árvore de trabalho.
- Sprint 05: validador estrutural confirmou sincronização e presença de 17 tarefas, 7 skills e 6 revisores; validação da nova skill, Ruff e diff passaram.
- Flow oficial 202601: 10.000 empresas, 10.349 estabelecimentos, 4.057 sócios, 7.058 registros do Simples, 1.359 CNAEs e 3.948 fatos ativos.
- Bronze e warehouse oficiais passaram nos verificadores; a segunda carga foi idempotente.
- Silver, snapshot, Gold e os 40 testes dbt concluíram no flow `0a3b5683-833a-4991-a048-042aa553996c`.
- Ensaio em clone limpo com `UV_OFFLINE=1`: sincronização pelo lockfile/cache local, 20 testes, flow de demonstração, verificadores, idempotência e árvore Git limpa.
- PDF FinOps em Português-BR validado com seis páginas A4.

## [0.1.0] - 2026-09-07

### Adicionado
- **Sprint 00**: Sistema operacional do projeto, especificações canônicas, 6 ADRs, governança e salvaguardas de agentes.
- **Sprint 01**: Resolução de fontes Receita Federal (espelho 202601), streaming de download, amostragem determinística rankeada por SHA-256 (10.000 empresas preservando relacionamentos) e carga imutável na camada Bronze do DuckDB.
- **Sprint 02**: Modelagem dbt Core (camadas Silver e Gold), macros (`normalize_cnpj`, `parse_decimal_br`, `normalize_cnae`, `add_audit_columns`), snapshot SCD Tipo 2 para histórico de Capital Social e fato incremental `fct_company_activity_daily`.
- **Sprint 03**: Orquestração via Prefect 3.8.5, retenção de artefatos por comando dbt, servidor local Prefect, script de renderização e validação de PDF FinOps BigQuery e runbook de reprodução local.
