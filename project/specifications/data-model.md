# Especificação do Modelo de Dados

## Esquemas (Schemas)

- `bronze`: tabelas brutas imutáveis da fonte (arquivos Receita Federal carregados).
- `silver`: modelos de staging e tabelas intermediárias de consolidação.
- `gold`: dimensões publicadas, projeções analíticas e tabelas fato.
- `snapshots`: tabelas de histórico SCD Tipo 2 geridas pelo dbt.
- `ops`: tabelas operacionais de controle de ingestão e auditoria.

## Modelos da Camada Silver

| Modelo | Grão Principal | Observações e Regras de Negócio |
|---|---|---|
| `stg_companies` | `cnpj_basico` corrente | CNPJ em string com zeros à esquerda, razão social, Capital Social em decimal(18,2) e linhagem Bronze. |
| `stg_establishments` | `cnpj` de 14 dígitos corrente | Situação cadastral normalizada, datas, UF, CNAE primário e CNAEs secundários brutos. |
| `stg_partners` | `source_period + partner record hash` | Documentos brutos permanecem na Bronze; a Silver expõe somente pseudônimos SHA-256 versionados, que nunca são chaves isoladas. |
| `stg_simples` | `source_period + cnpj_basico` | Converte 'S'/'N'/vazio para true/false/null. Ausência de linha significa desconhecido, não false. |
| `stg_cnae` | `cnae_code` | Código de 7 dígitos e descrição oficial da subclasse CNAE. |
| `int_establishment_secondary_cnae` | `establishment + secondary CNAE` | Normalização que explode a lista de CNAEs secundários em linhas individuais. Não alimenta um mart Gold; permanece na Silver para qualidade e reuso. |
| `int_company_rollup` | `cnpj_basico` corrente | Agregação intermediária: contagem de ativos, contagem de sócios, estabelecimento ativo representativo e flags tributárias. |

## Modelos da Camada Gold

| Modelo | Grão Principal | Materialização | Descrição |
|---|---|---|---|
| `dim_company_current` | `cnpj_basico` | `table` | Dimensão atualizada de empresas com atributos cadastrais consolidados. |
| `dim_cnae` | `cnae_code` | `table` | Dimensão de consulta oficial de subclasses CNAE. |
| `dim_cnae_hierarchy` | `cnae_code` | `table` | Dimensão com enriquecimento da hierarquia CNAE (divisão, grupo, classe e subclasse). |
| `dim_company_capital_history` | `cnpj_basico + valid_from` | `view` | Visão analítica de projeção do histórico de alterações do Capital Social sobre o snapshot SCD2. |
| `fct_company_activity_daily` | `reference_date + cnpj_basico` | `incremental` | Fato diária de atividade contendo apenas empresas ativas. |

### Regras de Negócio Fundamentais

- **Definição de Empresa Ativa**: Uma empresa é considerada ativa se e somente se possui ao menos um estabelecimento com `situacao_cadastral = '02'`.
- **Estabelecimento Representativo**: Prioriza a Matriz ativa (`matriz_filial_code = '1'`); caso inexistente ou inativa, adota a filial ativa com menor CNPJ de 14 dígitos ordenado lexicograficamente.
- **Tratamento de Simples Nacional / MEI**: A ausência de registro na fonte do Simples Nacional representa estado desconhecido (`null`), nunca `false`.
- **Conteúdo da Tabela Fato**: Contém apenas empresas ativas na data de referência; inclui contagem de estabelecimentos ativos, quantidade de sócios, Capital Social, CNAE principal, UF, e flags de Simples Nacional e MEI. O `reference_date` padrão é o último dia do período da fonte (`source_period`).

## Consumo Analítico

O consumo de uma visualização local é limitado ao contrato [analytics-consumption.md](analytics-consumption.md), que seleciona relações e colunas Gold adequadas para leitura. As demais camadas e colunas Gold não listadas não são interface analítica pública.
