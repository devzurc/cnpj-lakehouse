---
id: ADR-007
status: accepted
date: 2026-09-08
decision_makers: [project]
---

# Delimitar cada execução dbt a um lote Bronze ativo e substituir integralmente a partição do fato

## Contexto

Bronze é append-only e pode conter múltiplos períodos, amostras e reexecuções. Modelos Silver/Gold de estado corrente não podem combinar linhas desses lotes. Além disso, uma reexecução da mesma `reference_date` precisa remover empresas que deixaram de estar ativas.

## Decisão

Cada invocação dbt recebe obrigatoriamente `source_period`, `sample_id` e `reference_date` como variáveis. Todas as fontes Bronze que alimentam staging, intermediários e marts são filtradas pelo par `source_period + sample_id`. O snapshot continua acumulando a história de Capital Social das empresas presentes no lote ativo.

O fato `fct_company_activity_daily` substitui transacionalmente todas as linhas da `reference_date` solicitada antes de inserir o resultado ativo do lote, inclusive quando o resultado estiver vazio. Outras datas permanecem inalteradas.

## Consequências

Uma execução mensal ou com outro tamanho de amostra deixa de contaminar os modelos correntes e a partição incremental. Chamadas dbt diretas devem informar as três variáveis, evitando uma data padrão incompatível com o lote.

## Validação

Fixtures de dois períodos/lotes demonstram isolamento de parceiros e Simples, ausência atual vira `null`, uma empresa inativada desaparece da mesma partição e uma data não afetada permanece idêntica.
