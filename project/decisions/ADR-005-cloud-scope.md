---
id: ADR-005
status: accepted
date: 2026-09-06
decision_makers: [project]
---

# Manter execução em nuvem fora do caminho crítico do desafio

## Contexto

O desafio solicita uma proposta de arquitetura analítica escalável em Google BigQuery com boas práticas de FinOps e onboarding. A criação de infraestrutura real em nuvem pública exigiria vincular contas de faturamento pessoais ou institucionais, gerar chaves de serviço e incorrer em custos financeiros reais tanto para o desenvolvedor quanto para os avaliadores.

## Decisão

Entregar a proposta de BigQuery e FinOps como documentação técnica rigorosa e detalhada de modelagem física (particionamento, clustering, DDLs, controle de custos e governança IAM) em Markdown e PDF, sem requerer credenciais de nuvem, deploys de infraestrutura como código (Terraform) ou cobranças financeiras.

## Consequências

O esforço de desenvolvimento concentra-se 100% na qualidade do código Python, modelagem dbt, testes de dados e robustez da pipeline DuckDB, garantindo conformidade estrita com todos os requisitos obrigatórios do desafio.

## Validação

O documento técnico `docs/finops-bigquery-architecture.md` é validado e renderizado com sucesso via `scripts/render_finops_pdf.py` e verificado via `scripts/verify_finops_pdf.py`, atestando a cobertura de todos os critérios de FinOps exigidos.
