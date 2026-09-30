---
id: ADR-002
status: accepted
date: 2026-09-06
decision_makers: [project]
---

# Estabelecer fronteira de responsabilidades na Arquitetura Medalhão

## Contexto

A ingestão e modelagem de dados volumosos e heterogêneos requer uma separação nítida de responsabilidades para evitar acoplamento entre os estágios de transferência/validação de arquivos e os estágios de transformação relacional e regras de negócio.

## Decisão

Adotar a Arquitetura Medalhão com limites estritos de propriedade:
- **Prefect**: Gerencia o download em streaming, cálculo de checksums SHA-256, amostragem determinística e carga nas tabelas brutas da camada Bronze, além de orquestrar os subprocessos subsequentes.
- **dbt Core**: É o único proprietário das transformações das camadas Silver (limpeza, tipagem e deduplicação), Gold (marts dimensionais e fatos analíticos) e Snapshots (SCD Tipo 2).

## Consequências

A linhagem de dados brutos permanece perfeitamente reproduzível e auditável na camada Bronze. As regras de negócio e testes dbt ficam isolados e modulares, permitindo reprocessamentos (`--full-refresh`) sem a necessidade de reexecutar downloads pesados da rede.

## Validação

Testes de integração garantem que comandos dbt nunca escrevem no schema `bronze` e que o fluxo Prefect apenas executa cargas imutáveis na camada Bronze antes de delegar a execução ao dbt.
