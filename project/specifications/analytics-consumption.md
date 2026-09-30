# Contrato de Consumo Analítico DuckDB

## Limite de acesso

O dashboard local autorizado pela ADR-009 abre o arquivo DuckDB em modo somente-leitura e consulta exclusivamente as relações Gold e colunas listadas neste contrato. Ele atende somente em `127.0.0.1`; Bronze, Silver, snapshots, `ops`, dados de sócios, contato, razão social e metadados de auditoria não são superfícies de consumo visual.

O contrato não cria API pública, exportação, cloud ou credencial. O consumidor deve receber o caminho do warehouse produzido pelo pipeline e nunca iniciar download ou Prefect para ler dados já materializados.

## Relações e colunas autorizadas

| Relação | Grão | Colunas autorizadas | Uso esperado |
|---|---|---|---|
| `gold.dim_company_current` | `cnpj_basico` | `cnpj_basico`, `natureza_juridica`, `porte_empresa`, `capital_social`, `principal_cnae`, `uf`, `is_simples_nacional`, `is_mei`, `source_period`, `sample_id` | Segmentação e joins dimensionais do lote corrente. |
| `gold.dim_cnae` | `cnae_code` | `cnae_code`, `cnae_description`, `source_period` | Rótulos de atividade econômica. |
| `gold.dim_cnae_hierarchy` | `cnae_code` | `cnae_code`, `division_code`, `group_code`, `class_code`, `subclass_description`, `source_period` | Agregação por hierarquia CNAE. |
| `gold.fct_company_activity_daily` | `reference_date + cnpj_basico` | `reference_date`, `cnpj_basico`, `active_establishment_count`, `partner_count`, `capital_social`, `principal_cnae`, `uf`, `is_simples_nacional`, `is_mei`, `source_period`, `sample_id` | Métricas de empresas ativas por data e segmento. |

`cnpj_basico` é chave técnica de junção e não deve ser exposto como lista de entidades em visualizações agregadas. `null` em `is_simples_nacional` e `is_mei` significa informação desconhecida, não `false`.

## Inspector operacional

O inspector de operador pode ler metadados de Bronze, Silver, snapshots e `ops` para relatar contagens, grãos, lote ativo, manifestos, arquivos de fonte presentes/faltantes e integridade. Ele não imprime linhas, razões sociais, contatos, documentos, CNPJ ou hashes de registro dessas camadas. O comando `cnpj-lakehouse plan --source-period YYYYMM` resume a próxima ação (`reuse_bronze`, `download_missing`, `ingest_present_archives` ou `conflict`) sem baixar dados.

## Consultas de referência

Toda consulta à fato filtra a data de referência explicitamente:

```sql
select
  uf,
  count(*) as empresas_ativas,
  sum(active_establishment_count) as estabelecimentos_ativos
from gold.fct_company_activity_daily
where reference_date = date '2026-01-31'
group by uf
order by empresas_ativas desc;
```

```sql
select
  hierarchy.division_code,
  hierarchy.subclass_description,
  count(*) as empresas_ativas
from gold.fct_company_activity_daily as fact
join gold.dim_cnae_hierarchy as hierarchy
  on fact.principal_cnae = hierarchy.cnae_code
where fact.reference_date = date '2026-01-31'
group by hierarchy.division_code, hierarchy.subclass_description
order by empresas_ativas desc;
```

Para backfill ou rerun, o pipeline continua responsável por selecionar `source_period`, `sample_id` e `reference_date`; a visualização apenas lê a partição Gold já materializada.
