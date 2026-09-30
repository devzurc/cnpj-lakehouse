# Especificação de Arquitetura BigQuery e FinOps

O entregável oficial desta especificação é um documento técnico em Português-BR com extensão entre 4 e 7 páginas A4 (`docs/finops-bigquery-architecture.md` e respectivo PDF), focado no design de arquitetura de nuvem para GCP, sem exigir infraestrutura provisionada nem credenciais em tempo de execução.

## Diretrizes de Armazenamento e Datasets

- **Google Cloud Storage (GCS)**: Armazena os arquivos da camada Bronze imutável organizados por caminhos de período da fonte e checksum SHA-256 (`source_period=YYYYMM/source_sha256=.../`).
- **Datasets BigQuery**: Criação de datasets na mesma região geográfica do bucket GCS (ex.: `southamerica-east1` ou `us-central1`), separados por camada: `raw` (ou `bronze`), `silver`, `gold` e `snapshots`.
- **Particionamento e Clusterização**:
  - Tabelas brutas volumosas (`raw`): particionadas por data de ingestão (`DATE(ingested_at)`) e clusterizadas por `cnpj_basico`.
  - Fato analítica diária (`fct_company_activity_daily`): particionada por `reference_date`, configurada com `require_partition_filter = true` e clusterizada por `uf`, `principal_cnae` e `cnpj_basico`.
  - Dimensões estáticas (`dim_cnae`, `dim_cnae_hierarchy`): não devem ser particionadas, por se tratarem de tabelas de domínio pequenas.
  - Snapshots de histórico (SCD Tipo 2): particionados por data de vigência (`DATE(valid_from)`) e clusterizados por `cnpj_basico`.
- **Cargas Incrementais**: Operações `MERGE` rigorosamente escopadas à partição do `reference_date` para evitar leituras completas de tabela.

## Controles Operacionais de FinOps

- **Prevenção de consultas dispendiosas**: Proibição de `SELECT *` em rotinas de produção; projeção estrita de colunas necessárias; exigência de predicados de partição; estimativas preliminares via *dry run* e configuração de `maximumBytesBilled` em jobs de risco.
- **Atribuição de custos via Labels**: Aplicação de tags padronizadas em todos os jobs (`application=cnpj_lakehouse`, `layer=raw|silver|gold`, `source_period=...`, `environment=...`, `owner=...`) viabilizando rateio contábil.
- **Orçamentos e Alertas**: Definição de orçamentos (*budgets*) mensais no GCP Cloud Billing com gatilhos de notificação antecipados e críticos.
- **Políticas de Retenção e Ciclo de Vida**: Regras de ciclo de vida no GCS para cópias transitórias e expiração automática de tabelas intermediárias de staging.
- **Observabilidade**: Monitoramento contínuo de consumo de bytes processados e `slot-ms` através de consultas na visualização `INFORMATION_SCHEMA.JOBS`.
- **Rigor analítico**: A redução de custos deve ser explicada pelo pruning de partições e clustering que diminui bytes escaneados e tempo de slot; jamais alegar estimativas de percentuais fixos de economia sem comprovação empírica mensurada.
