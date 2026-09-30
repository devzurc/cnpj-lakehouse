# Matriz de Aceite e Rastreabilidade

| Requisito | Sprint / Tarefa | Artefato Principal | Comando / Método de Verificação |
|---|---|---|---|
| REQ-DBT-01 | S02-01, S02-02, S06-01, S07-01 | Modelos e configurações em `dbt/` | `dbt compile`, `dbt build` com lote ativo explícito |
| REQ-DBT-02 | S02-01, S02-02, S07-01, S10-01, S10-02 | DAG Silver/Gold e contrato Gold para leitura | Documentação de grão, teste de fato e verificador analítico sintético |
| REQ-DBT-03 | S02-02, S07-01 | Snapshot de Capital Social | Fixture de duas versões e teste de exatamente uma versão corrente |
| REQ-DBT-04 | S02-01 | 4 macros em `dbt/macros/` | Compilação dbt e uso nos modelos Silver/Gold |
| REQ-DQ-01 | S02-02, S07-01, S10-02 | Suíte dbt, testes negativos e contrato analítico | `dbt test`, `pytest` e verificador analítico sintético |
| REQ-ARCH-01 | S03-01, S04-04, S08-02, S19-01 | Fluxo Prefect, artefatos e deployment mensal | Ensaio sintético do flow, inspeção do deployment e retenção por `flow_run_id` |
| REQ-ARCH-03 | S13-01 | Amostra configurável em jobs disjuntos | `sample_size` × `parallel_jobs` via `.env` ou `config/sampling.toml`; testes de união e `sample_id` |
| REQ-ARCH-02 | S01-01, S01-02, S04-02, S12-01, S20-01 | Manifestos imutáveis, `ops.sample_manifests` e inventário de fontes | `verify_bronze.py`, `cnpj-lakehouse plan`, reexecução idempotente e integridade de ZIP |
| REQ-EXEC-01 | S03-02, S11-03, S16-01, S17-01, S18-01, S21-01 | README operacional, governança e dossiê local | Clone limpo offline, demo sintética, verificadores e análise DuckDB read-only |
| REQ-FINOPS-01 | S03-02, S07-01, S09-03 | Documento Markdown e PDF (4–7 págs) | `uv run python scripts/verify_finops_pdf.py docs/finops-bigquery-architecture.pdf` |
