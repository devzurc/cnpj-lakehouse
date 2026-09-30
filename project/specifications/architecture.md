# Especificação de Arquitetura

```text
Espelho Receita Federal (Casa dos Dados) / Diretório local
                         │
                         ▼
Prefect: inventariar → resolver → baixar → validar → amostragem → carga Bronze
                         │
                         ├── dbt run --select staging intermediate
                         ├── dbt snapshot (Capital Social SCD2)
                         ├── dbt run --select marts
                         └── dbt test
                         │
      DuckDB: bronze → silver → gold / snapshots → artefatos de execução
```

## Limites e Responsabilidades das Camadas

- **Bronze**: Arquivos ZIP originais imutáveis, arquivos gzip de amostra, tabelas brutas no DuckDB, manifestos de ingestão com checksums e metadados de linhagem física. O inventário compara os 32 ZIPs contratados com as amostras do período: arquivo local não é baixado de novo; a mesma coorte reutiliza a Bronze; um segundo tamanho de amostra no mesmo `YYYYMM` é recusado.
- **Silver**: Modelos de staging e transformações intermediárias gerenciados pelo dbt Core (padronização de tipos, normalização de CNPJ/CNAE, decodificação segura e deduplicação).
- **Gold**: Data marts analíticos dimensionais (`dim_company_current`, `dim_cnae`, `dim_cnae_hierarchy`), projeção de histórico de capital e fato diária incremental de empresas ativas (`fct_company_activity_daily`).
- **Snapshots**: Histórico SCD Tipo 2 gerenciado nativamente pelo dbt (`company_capital_social_snapshot`).
- **`ops`**: Tabelas operacionais de controle de auditoria de ingestão e metadados de execução (`ops.sample_manifests`).

## Runtime de Execução

O DuckDB é o motor de execução obrigatório e oficial da entrega. A arquitetura BigQuery é abordada exclusivamente no documento de FinOps e design de nuvem. O pipeline completo opera localmente sem necessidade de credenciais de provedores de nuvem.

## Comportamento em Caso de Falhas

- **Falhas transitórias de rede**: Timeouts de conexão, quedas temporárias de rede, respostas HTTP 429 e HTTP 5xx recebem retentativas controladas (*bounded retries* com backoff exponencial).
- **Falhas permanentes**: Alterações de esquema não contratadas (*schema drift*), corrupção de arquivo ZIP, erros HTTP 404, parâmetros inválidos e erros em subprocessos do dbt causam interrupção imediata da execução com log detalhado de contexto e retenção de artefatos para diagnóstico.
