# Runbook de Análise Local DuckDB

Este runbook atende à exploração local e ao dashboard Gold autorizado pela ADR-009. Para subir o stack completo use `scripts/local.sh`; Docker Compose é a alternativa sem Python no host. Ele não baixa o espelho público, não exporta dados e não usa credenciais.

## Subir e desligar o stack

No diretório do repositório:

```bash
export CNPJ_LAKEHOUSE_RUNTIME_ROOT="$HOME/.local/share/cnpj-lakehouse"
export CNPJ_LAKEHOUSE_DUCKDB_PATH="$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run/warehouse/cnpj_lakehouse.duckdb"
./scripts/local.sh start
./scripts/local.sh status
```

Use [Prefect UI](http://127.0.0.1:4200/) para acompanhar o run `cnpj-lakehouse/monthly-ingest` e [Gold dashboard](http://127.0.0.1:8501/) para explorar as agregações. `./scripts/local.sh logs` mostra os logs privados; `./scripts/local.sh stop` encerra apenas os processos registrados e preserva o runtime para auditoria.

### Alternativa Docker multiplataforma

Com Docker Engine/Desktop instalado, a mesma operação não exige Python no host:

```bash
./scripts/docker.sh start
./scripts/docker.sh demo
./scripts/docker.sh verify
./scripts/docker.sh stop
```

No PowerShell, use `scripts/docker.ps1`. O Compose usa os volumes nomeados `cnpj_lakehouse_runtime` (DuckDB, camadas e artefatos) e `cnpj_lakehouse_prefect_state` (SQLite do Prefect). `stop` não remove esses volumes. O comando `demo` executa fontes sintéticas; a ingestão do espelho público continua no host via `backfill.sh` ou `monthly-ingest`.

## Pré-requisito

Execute previamente o pipeline para produzir o warehouse. O caminho padrão é `$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run/warehouse/cnpj_lakehouse.duckdb`, em armazenamento Linux nativo. Abra o arquivo somente em modo leitura:

```bash
export CNPJ_LAKEHOUSE_RUNTIME_ROOT="${CNPJ_LAKEHOUSE_RUNTIME_ROOT:-$HOME/.local/share/cnpj-lakehouse}"
export CNPJ_LAKEHOUSE_DUCKDB_PATH="$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run/warehouse/cnpj_lakehouse.duckdb"
uv run python - <<'PY'
import duckdb
import os
from pathlib import Path

database = Path(os.environ["CNPJ_LAKEHOUSE_DUCKDB_PATH"])
with duckdb.connect(str(database), read_only=True) as connection:
    print(connection.execute("select count(*) from gold.fct_company_activity_daily").fetchone())
PY
```

Nunca abra Bronze, Silver, snapshots ou `ops` como fonte da visualização.

## Dashboard Gold local

Após produzir o warehouse, o launcher já inicia o dashboard em loopback. Para um processo isolado:

```bash
export CNPJ_LAKEHOUSE_DUCKDB_PATH="$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run/warehouse/cnpj_lakehouse.duckdb"
uv run cnpj-lakehouse-dashboard
```

Abra `http://127.0.0.1:8501`, selecione a partição e use as agregações por UF e CNAE. O dashboard abre DuckDB em modo read-only e não lista CNPJ. Antes de um segundo run, `uv run cnpj-lakehouse plan --source-period YYYYMM --sample-size N` lista ZIPs presentes/faltantes e se a Bronze já cobre a coorte. A inspeção de camadas restritas fica no resumo seguro de `scripts/inspect_local_warehouse.py` (contagens, manifestos e arquivos de fonte; sem linhas).

## Consulta por período e lote

Selecione primeiro as partições disponíveis:

```sql
select distinct reference_date, source_period, sample_id
from gold.fct_company_activity_daily
order by reference_date desc, source_period desc;
```

Em seguida, filtre a fato em `reference_date` e, quando houver mais de um lote para o mesmo período, em `sample_id`:

```sql
select uf, count(*) as empresas_ativas
from gold.fct_company_activity_daily
where reference_date = date '2026-01-31'
  and sample_id = 'sample_id_do_lote'
group by uf
order by empresas_ativas desc;
```

As relações e colunas permitidas estão no [contrato analítico](../project/specifications/analytics-consumption.md). `cnpj_basico` é somente chave de junção; visuais devem privilegiar agregações.

## Rerun e backfill

O consumidor não altera o DuckDB. O warehouse operacional padrão é `$HOME/.local/share/cnpj-lakehouse`. O backfill anual usa o runtime isolado `$HOME/.local/share/cnpj-lakehouse-official` (nunca o share sintético). Cada mês gera uma `reference_date` no último dia civil (não há um fato por dia):

```bash
export CNPJ_LAKEHOUSE_RUNTIME_ROOT="$HOME/.local/share/cnpj-lakehouse-official"
export CNPJ_LAKEHOUSE_DUCKDB_PATH="$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run/warehouse/cnpj_lakehouse.duckdb"
./scripts/backfill.sh 2026
uv run cnpj-lakehouse-dashboard
```

Em 2026 o índice tinha jan–ago com um diretório cada; meses sem lote único são omitidos. A coorte de 10.000 empresas muda com o `source_period`. `dim_company_current` reflete o último lote dbt; a fato acumula partições. `local.sh wait` não substitui este launcher.

Para um único período avulso, execute o pipeline com `--source-period YYYYMM`; o valor explícito vence o período automático. Para substituir a referência analítica, informe `--reference-date YYYY-MM-DD`. Após a execução, selecione novamente a partição Gold atualizada; o contrato de consumo não muda.
