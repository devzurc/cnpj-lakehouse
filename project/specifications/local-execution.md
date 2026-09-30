# Especificação de Execução Local

O caminho recomendado no host com Python 3.12 e `uv` é iniciar `scripts/local.sh start` e disparar o deployment `cnpj-lakehouse/monthly-ingest` na UI Prefect. Configure `CNPJ_LAKEHOUSE_RUNTIME_ROOT` para o sistema de arquivos Linux nativo; não processe arquivos volumosos em montagens do Windows/OneDrive (`/mnt/c`). Warehouse, Bronze e artefatos ficam em `$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run`.

Docker Engine/Desktop executa a mesma aplicação via `docker-compose.yml` quando o host não deve instalar Python. O launcher `scripts/docker.sh` (ou `scripts/docker.ps1` no PowerShell) usa os volumes nomeados `cnpj_lakehouse_runtime` e `cnpj_lakehouse_prefect_state`. Portas continuam restritas a loopback; `start` não dispara runs automaticamente.

## Comandos recomendados

```bash
uv sync --all-groups --locked
export CNPJ_LAKEHOUSE_RUNTIME_ROOT="${CNPJ_LAKEHOUSE_RUNTIME_ROOT:-$HOME/.local/share/cnpj-lakehouse}"
export CNPJ_LAKEHOUSE_DUCKDB_PATH="$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run/warehouse/cnpj_lakehouse.duckdb"

uv run python scripts/validate_project_structure.py
uv run pytest -q
uv run ruff check .

./scripts/local.sh start
```

O `start` registra o deployment `cnpj-lakehouse/monthly-ingest` (fonte remota, amostra resolvida em runtime: `.env` / `config/sampling.toml` / 10.000×1) e não dispara o flow. Execute na UI ou com `./scripts/local.sh run`. Antes de um segundo run, `uv run cnpj-lakehouse plan --source-period YYYYMM --sample-size N` lista ZIPs presentes/faltantes e se a Bronze do período já cobre essa coorte. No ensaio Docker, use `--sample-size 3`. Fontes sintéticas ficam restritas a testes (`cnpj-lakehouse create-demo-sources`).

CLI direto (mesmo layout `/run`, rejeita `/mnt`):

```bash
uv run cnpj-lakehouse run --source-period 202601 --sample-size 10000 \
  --output-path "$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run"
```

Para 20.000 empresas em 4 jobs de 5.000 (faixas disjuntas, um DuckDB), no runtime operador — **nunca** `$HOME/.local/share/cnpj-lakehouse-official` e **sem** reiniciar o worker do backfill 2026:

```bash
export CNPJ_LAKEHOUSE_SAMPLE_SIZE=5000
export CNPJ_LAKEHOUSE_PARALLEL_JOBS=4
# ou: cp config/sampling.toml.example config/sampling.toml e edite o arquivo
uv run cnpj-lakehouse run --source-period 202601
```

O `scripts/local.sh` lê `.env` na raiz do repositório como arquivo restrito de `KEY=VALUE`; ele não executa conteúdo de shell. Só aceita `CNPJ_LAKEHOUSE_RUNTIME_ROOT`, `CNPJ_LAKEHOUSE_DUCKDB_PATH`, `CNPJ_LAKEHOUSE_SAMPLE_SIZE`, `CNPJ_LAKEHOUSE_PARALLEL_JOBS` e `CNPJ_LAKEHOUSE_INGESTION_WORKERS`, sem aspas ou expansão. `local.sh run` só envia `sample_size`/`parallel_jobs` ao Prefect quando as variáveis estão definidas; caso contrário o flow usa o arquivo TOML ou o padrão do desafio. `CNPJ_LAKEHOUSE_INGESTION_WORKERS` controla processos locais limitados por arquivo para validação e filtragem; não altera a coorte. O padrão é 2 e o máximo é 4, para preservar RAM e responsividade da máquina.

## Capacidade mínima de armazenamento

Recomenda-se um mínimo de **15 GiB livres** no caminho de dados Linux configurado **antes de cada** download remoto. Um mês compactado fica em torno de 7 GiB; oito meses retidos no disco aproximam **55 GiB** além do DuckDB. O volume descompactado em streaming excede as estimativas superficiais do edital.

## Operação mensal, rerun e backfill

O deployment `monthly-ingest` executa no dia **7 às 09:00 em `America/Sao_Paulo`** e processa automaticamente o mês calendário anterior, gravando em `$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run`. Não há execução diária nem retry para um lote ainda indisponível: a falha de resolução fica visível no run Prefect, preservando o estado anterior. Para reexecutar a mesma coorte, `cnpj-lakehouse plan --source-period YYYYMM --sample-size N` deve mostrar `reuse_bronze`; ZIPs presentes não disparam HTTP e a Bronze não duplica. Um segundo tamanho de amostra no mesmo `YYYYMM` é recusado.

Para backfill de um ano, use o runtime isolado — nunca o share sintético `$HOME/.local/share/cnpj-lakehouse` e nunca `/mnt`:

```bash
export CNPJ_LAKEHOUSE_RUNTIME_ROOT="$HOME/.local/share/cnpj-lakehouse-official"
./scripts/backfill.sh 2026
```

O launcher lista no índice só os `YYYYMM` com exatamente um diretório `YYYY-MM-DD`, executa `cnpj-lakehouse run` com `sample_size=10000` e `full_refresh=false`, e verifica cada partição. Cada mês é sequencial no mesmo DuckDB; só o download interno usa até 3 streams. A `reference_date` é o último dia civil do mês (ADR-004). Em 2026 o espelho tinha jan–ago no momento do desenho; set–dez entram quando existir um único diretório. `scripts/local.sh wait` (cerca de 6 minutos) serve a um run curto já disparado; volume público leva horas por mês e usa o CLI de backfill.

A amostra ranqueia `sha256("{source_period}:{cnpj_basico}")`, então os CNPJs da coorte **mudam entre meses**. `5.000×4` e `20.000×1` produzem o mesmo conjunto de empresas, mas `sample_id` diferentes (ADR-013); o dbt troca o lote ativo. `dim_company_current` mostra só o lote ativo da última execução dbt; a fato guarda todas as `reference_date`. CLI avulso continua válido: `uv run cnpj-lakehouse run --source-period YYYYMM --sample-size 10000 --output-path "$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run"`.

## Quatro terminais (diagnóstico)

Use somente se precisar isolar servidor, runner e dashboard. Os comandos de `scripts/prefect_local.sh` (`server`, `serve`, `status`) e `uv run cnpj-lakehouse-dashboard` permanecem válidos; o `output_path` do flow deve ser `$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run`.
