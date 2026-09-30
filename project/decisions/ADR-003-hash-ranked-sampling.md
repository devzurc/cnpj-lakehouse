---
id: ADR-003
status: accepted
date: 2026-09-06
decision_makers: [project]
---

# Selecionar empresas com amostragem determinística rankeada por hash

## Contexto

A base completa de CNPJs da Receita Federal possui dezenas de gigabytes e centenas de milhões de registros. Para o ambiente de avaliação e desenvolvimento local ágil, o desafio solicita uma amostra representativa de 10.000 empresas que preserve estritamente os relacionamentos entre a tabela de empresas e suas filiais (estabelecimentos), sócios e opção tributária. Uma amostragem ingênua (ex.: primeiros $N$ registros de um arquivo) sofreria viés de ordenação alfabética ou regional dos lotes da Receita Federal e não garantiria integridade referencial.

## Decisão

Implementar um algoritmo de amostragem determinística baseado no menor ranqueamento de hash SHA-256 da chave composta `{source_period}:{cnpj_basico}`:
1. Varrer em streaming todos os shards de Estabelecimentos e extrair os CNPJs básicos normalizados (8 dígitos com zero à esquerda).
2. Manter uma fila de prioridade com capacidade limitada (*bounded min-heap*) retendo os 10.000 menores digests SHA-256.
3. Varrer novamente os arquivos e reter todos os registros vinculados a esses CNPJs básicos nas tabelas de Estabelecimentos, Empresas, Sócios e Simples Nacional.
4. Carregar 100% da tabela de domínio CNAE.

## Consequências

A amostra gerada é rigorosamente estável e determinística para o mesmo período e tamanho de amostra, independente da ordem de leitura dos arquivos. Os relacionamentos relacionais entre empresa-mãe e seus filhos são preservados integralmente.

## Validação

Testes unitários e de integração verificam que a lista de CNPJs selecionados é idêntica em reexecuções, que nenhuma filial ou sócio fica órfão na camada Bronze e que zeros à esquerda em CNPJs são integralmente preservados.
