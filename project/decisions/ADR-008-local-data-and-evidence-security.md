---
id: ADR-008
status: accepted
date: 2026-09-08
decision_makers: [project]
---

# Restringir dados locais e evidências ao proprietário do runtime

## Contexto

Embora a fonte seja pública, os arquivos e o DuckDB preservam dados pessoais e de contato de sócios e estabelecimentos. As evidências dbt também precisam permanecer íntegras e corretamente atribuídas.

## Decisão

O runtime local deve criar seu diretório raiz, dados derivados e artefatos com acesso somente do proprietário (`0700` para diretórios e `0600` para arquivos). A retenção é manual: nenhuma rotina remove dados automaticamente. Uma inspeção de limpeza apenas inventaria arquivos legados e exige autorização explícita para qualquer exclusão.

Os dados são classificados como: Bronze restrito, Silver restrito quando contiver dados de sócios/contato, Gold de consumo controlado e evidências operacionais restritas. Documentação e Git não podem conter registros de dados, segredos ou caminhos pessoais.

## Consequências

Instalações existentes podem exigir uma normalização explícita de permissões. O design BigQuery mantém o princípio de menor privilégio e aplica políticas de coluna/views autorizadas antes de expor atributos sensíveis.

## Validação

Testes verificam os modos criados para dados e artefatos; o inventário não altera arquivos; a auditoria Git confirma que dados, segredos e artefatos transitórios não são rastreados.
