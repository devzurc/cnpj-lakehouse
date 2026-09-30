# Requisitos do Desafio

## Requisitos obrigatórios de entrega

| ID | Requisito |
|---|---|
| REQ-DBT-01 | Projeto dbt Core funcional com modelos em camadas (Medallion) e materializações apropriadas. |
| REQ-DBT-02 | Modelos de staging, pelo menos um modelo incremental, dimensões, hierarquia CNAE e fato de empresas ativas. |
| REQ-DBT-03 | Snapshot SCD Tipo 2 para histórico de alterações de Capital Social. |
| REQ-DBT-04 | Pelo menos três macros Jinja reutilizáveis e úteis (`normalize_cnpj`, `parse_decimal_br`, `normalize_cnae`, `add_audit_columns`). |
| REQ-DQ-01 | No mínimo oito testes dbt, cobrindo tipos obrigatórios e regra de negócio customizada; o inventário corrente é reproduzível pelo comando dbt documentado. |
| REQ-ARCH-01 | Fluxo Prefect extrai e carrega amostra, executando sequencialmente dbt snapshot, dbt run e dbt test. |
| REQ-ARCH-02 | Camada Bronze imutável, reprodutível, idempotente e auditável com manifesto de linhagem física. |
| REQ-ARCH-03 | Amostragem configurável em jobs paralelos disjuntos; o padrão do desafio permanece 10.000 empresas em 1 job. |
| REQ-EXEC-01 | Pipeline totalmente executável em ambiente local utilizando DuckDB sem necessidade de credenciais de nuvem. |
| REQ-FINOPS-01 | Documento de arquitetura BigQuery e FinOps para onboarding com extensão entre 4 e 7 páginas A4. |

## Decisões de produto fixadas

- **Arquitetura Medalhão**: Prefect é responsável pela ingestão na camada Bronze; dbt é responsável pelas transformações em Silver, Gold e snapshots.
- **Período de origem operacional**: quando `source_period` não é informado, o pipeline resolve o mês calendário anterior em `America/Sao_Paulo`; um período explícito sempre prevalece. `202601` permanece como período de exemplo e evidência oficial histórica.
- **Amostragem determinística**: Seleção padrão de 10.000 empresas pelo menor ranqueamento de hash SHA-256 do `cnpj_basico` normalizado. Jobs paralelos disjuntos (ADR-013) podem ampliar a coorte sem alterar esse padrão.
- **Preservação de relacionamentos**: Manutenção de todos os registros filhos correspondentes (Estabelecimentos, Sócios e Simples) e carga integral da tabela de domínio CNAE.
- **Data de referência da atividade**: o padrão é o último dia calendário do período de origem resolvido; pode receber override explícito.
- **Escopo crítico local**: Exclusão de chamadas à API da ReceitaWS e de `dim_location` do caminho crítico local para garantir robustez e ausência de limites de taxa externos.
