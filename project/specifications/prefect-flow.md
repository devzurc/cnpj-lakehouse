# Especificação do Fluxo Orquestrado Prefect

## Nomes na UI e na operação

| Peça | Nome | Função |
| --- | --- | --- |
| Flow | `cnpj-lakehouse` | Pipeline completo: espelho CNPJ → Bronze → dbt → Gold. |
| Deployment | `monthly-ingest` | Automação mensal do flow; referência `cnpj-lakehouse/monthly-ingest`. |
| Run agendado | `lakehouse-YYYYMMDD-HHMM` | Nome estável (America/Sao_Paulo), sem rótulo aleatório. |
| Run manual | `lakehouse-YYYYMMDDHHMMSS` | Disparo via `local.sh run` ou UI. |
| Worker | `cnpj-lakehouse-serve` | Processo que registra o deployment e executa os runs. |

Tarefas na UI (função Python entre parênteses):

| Tarefa | Etapa |
| --- | --- |
| `inventariar-lote` | Compara os 32 ZIPs no disco com as amostras Bronze do período (`inventory_source_batch`). |
| `resolver-fontes-do-lote` | Descobre o diretório `YYYY-MM-DD` e a lista contratada de ZIPs (`resolve_sources`). |
| `baixar-zips-do-lote` | Download com 3 streams e manifesto SHA-256 (`download_source_files`). |
| `validar-integridade-dos-arquivos` | ZIP, encoding, campos; reusa manifesto se os hashes coincidem (`validate_archives`). |
| `amostrar-empresas-relacionadas` | Ranking SHA-256 e grafo empresa/estabelecimento/sócio/Simples (`build_relationship_preserving_sample`). |
| `reutilizar-bronze-existente` | No-op se o `sample_id` já está na Bronze (`lookup_completed_bronze`). |
| `carregar-bronze` | Carga append-only no DuckDB (`load_bronze_task`). |
| `executar-dbt` | Tarefa Python única; cada invocação usa `task_run_name` distinto na UI (`run_dbt_task`). |
| `executar-dbt-silver` | dbt run staging+intermediate (`artifact_label=01-dbt-run-core`). |
| `executar-dbt-snapshot` | Snapshot de Capital Social (`artifact_label=02-dbt-snapshot`). |
| `executar-dbt-gold` | dbt run marts Gold (`artifact_label=03-dbt-run-marts`). |
| `executar-dbt-testes` | dbt test (`artifact_label=04-dbt-test`). |
| `validar-contrato-analitico` | Contrato Gold in-process; falha com a mensagem do verificador antes de `Completed`. |

O fluxo (`cnpj_lakehouse_flow`) expõe os parâmetros:

- `source_period` (opcional): período de origem no formato `YYYYMM` (ex.: `202601`). Quando ausente, resolve o mês calendário anterior em `America/Sao_Paulo`; um valor explícito sempre prevalece.
- `sample_size` (opcional): empresas por job. Vazio usa `.env` / `config/sampling.toml` / 10.000.
- `parallel_jobs` (opcional): jobs disjuntos em paralelo. Vazio usa env / arquivo / 1.
- `ingestion_workers` (opcional): processos locais limitados para arquivos independentes. Vazio usa env / arquivo / 2; não altera a coorte.
- `output_path`: caminho do diretório de execução no armazenamento Linux nativo.
- `reference_date` (opcional): data de corte do fato diário (padrão: último dia civil do `source_period`).
- `full_refresh` (booleano): reconstrói modelos incrementais sem truncar a camada Bronze.
- `source_dir` (opcional): caminho para diretório de arquivos fonte locais pré-baixados.
- `base_url` (opcional): URL base alternativa para o espelho de arquivos.

Em Docker Compose, o servidor Prefect é acessado pelos demais serviços em `http://prefect-server:4200/api`; o runner registra o deployment oficial `cnpj-lakehouse/monthly-ingest`. A UI no browser usa `PREFECT_UI_API_URL=/api` (same-origin: `localhost` ou `127.0.0.1`). Só o serviço `prefect-server` monta o SQLite em `prefect_state`. Fontes sintéticas só podem ser usadas pelo comando explícito de demonstração/teste. No host, a UI permanece publicada somente em `127.0.0.1:4200`.

## Ordem Canônica de Execução das Tarefas

```text
inventariar-lote
       │
       ├─ reuse_bronze ────────────────────────────┐
       │                                           │
       ▼                                           │
resolver-fontes-do-lote                            │
       │                                           │
       ▼                                           │
baixar-zips-do-lote (só HTTP nos ausentes; presentes = reused) │
       │                                           │
       ▼                                           │
validar-integridade-dos-arquivos                   │
       │                                           │
       ▼                                           │
amostrar-empresas-relacionadas                     │
       │                                           │
       ▼                                           │
carregar-bronze (ou reutilizar-bronze-existente)   │
       │                                           │
       ▼                                           │
executar-dbt-silver ◄──────────────────────────────┘
       │
       ▼
executar-dbt-snapshot
       │
       ▼
executar-dbt-gold
       │
       ▼
executar-dbt-testes
       │
       ▼
validar-contrato-analitico
```

## Concorrência

O pipeline é local e single-warehouse. Download e validação/filtragem por arquivo com `ingestion_workers>1` podem ser paralelos. `parallel_jobs>1` continua sendo apenas o contrato de coortes disjuntas. Bronze, dbt e o contrato Gold permanecem single-writer.

| Etapa | Modo | Motivo |
| --- | --- | --- |
| Download dos ZIPs | Até 3 streams | I/O de rede; limite explícito em `download_source_files`. |
| Extração da amostra (`parallel_jobs>1`) | Até N jobs | Faixas disjuntas do ranking SHA-256; um `sample_id` Bronze após a fusão (ADR-013). |
| Validação e filtragem por arquivo (`ingestion_workers>1`) | Até 4 processos locais | Fragmentos determinísticos por arquivo; fusão antes de Bronze (ADR-014). |
| Validação, amostragem 1 job, Bronze | Sequencial | Um DuckDB; lock exclusivo do run. |
| dbt Silver → snapshot → Gold → testes | Sequencial | Dependência de modelos (`stg_companies` alimenta o snapshot; marts leem o snapshot). |
| Contrato Gold | Sequencial, após dbt | O flow só marca `Completed` com o schema publicado. |
| Backfill anual (`backfill.sh`) | Um `source_period` por vez | O mesmo warehouse acumula partições Gold; dois meses em paralelo corromperiam o lote ativo. |

Não há fan-out diário, workers distribuídos nem execução GCP neste caminho.

## Regras de Execução e Resiliência

- **Concorrência e Locks**: Downloads operam com limite de 3 requisições simultâneas. Um lock exclusivo por warehouse cobre Bronze, dbt e validação Gold de uma execução inteira; outra execução aguarda a liberação antes de escrever ou trocar o lote ativo.
- **Sequenciamento dbt**: A camada Silver (staging/intermediate) é executada antes do snapshot porque o snapshot referencia sua origem higienizada em `stg_companies`; os marts Gold são executados após o snapshot.
- **Chamadas de Subprocessos Seguras**: Todos os comandos dbt são invocados via listas de argumentos (`sys.executable, "-m", "dbt.cli.main", ...`), evitando interpolação insegura de shell. Qualquer código de saída diferente de zero encerra o fluxo com falha imediata. A validação Gold chama o verificador de contrato no mesmo processo e propaga `ValueError` na UI Prefect.
- **Contexto Prefect**: Dentro de um flow run as tarefas geram runs na UI. `run_local_pipeline` (CLI e testes) executa o mesmo corpo sem API efêmera. Artefatos dbt fora de um flow usam `flow_run_id=local`.
- **Isolamento de testes**: O ensaio do flow decorado chama o corpo do flow sem anexar a `127.0.0.1:4200` e sem subir servidor Prefect efêmero no plano de controle do operador.
- **Reutilização Segura**: `inventariar-lote` lista ZIPs presentes e faltantes e as amostras Bronze do período. Arquivo local com tamanho > 0 não dispara HTTP (`reused`). Se os 32 ZIPs já estão no volume, a resolução usa o diretório de download e não consulta o índice remoto. A mesma coorte (`source_period` + número de empresas) reutiliza a Bronze sem nova amostragem. Um segundo tamanho de amostra no mesmo período é recusado. Manifestos imutáveis com checksums correspondentes evitam repetir a leitura integral dos ZIPs.
- **Execução Offline**: Macros e testes genéricos pertencem ao repositório; o flow não resolve pacotes dbt pela rede em runtime.
- **Retenção de Artefatos**: Cada invocação usa `target` privado sob `flow_run_id=<uuid>`. `manifest.json` e `run_results.json` só são retidos após JSON válido e `invocation_id` coerente; logs e artefatos são owner-only.
- **Agendamento mensal**: O deployment `cnpj-lakehouse/monthly-ingest` agenda `0 9 7 * *` no timezone `America/Sao_Paulo`. Executa fontes remotas, amostra resolvida em runtime (`.env` / `config/sampling.toml` / padrão 10.000×1), `full_refresh=false` e `output_path=$CNPJ_LAKEHOUSE_RUNTIME_ROOT/run` em armazenamento Linux. A ausência do lote no dia 7 termina o run com falha visível e segura; não há retry diário. Reruns com o mesmo `sample_id` reutilizam a Bronze de modo idempotente.
- **Backfill anual**: `scripts/backfill.sh` e `cnpj-lakehouse backfill-year` percorrem meses com um único diretório no índice, em série, no runtime isolado. O `local.sh wait` (cerca de 6 minutos) cobre um run já disparado; não é o gate de volume público.
- **Servidor local**: O launcher usa SQLite com WAL fornecido pelo Prefect, armazenamento Linux nativo e timeout explícito de 60 segundos. Durante um flow ativo, acompanhe pelo dashboard Prefect; não dispare inspeções CLI repetidas em paralelo, pois elas podem disputar o plano de controle SQLite.
