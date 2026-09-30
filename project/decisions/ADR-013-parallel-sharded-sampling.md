---
id: ADR-013
status: accepted
date: 2026-09-10
decision_makers: [project]
---

# Permitir amostragem configurável em jobs paralelos disjuntos

## Contexto

O desafio pede 10.000 empresas em um único lote. Operadores podem querer uma coorte maior (por exemplo 20.000) sem abandonar o ranking SHA-256 nem o DuckDB local. Quatro execuções independentes de 5.000 com o mesmo algoritmo devolveriam o mesmo conjunto, não 20.000 empresas distintas. O DuckDB não admite vários writers no mesmo warehouse.

## Decisão

- O padrão operacional permanece **1 job × 10.000** (desafio). `backfill-year` / `scripts/backfill.sh` passam `parallel_jobs=1` e ignoram `.env`/`sampling.toml` para o número de jobs.
- O operador configura `sample_size` (empresas por job) e `parallel_jobs` via `.env` (`CNPJ_LAKEHOUSE_SAMPLE_SIZE`, `CNPJ_LAKEHOUSE_PARALLEL_JOBS`) ou `config/sampling.toml`. Precedência: argumento CLI/flow > ambiente > arquivo > padrão.
- O deployment `monthly-ingest` persiste `sample_size`/`parallel_jobs` vazios; cada run resolve o plano no worker (env, arquivo ou padrão 1×10.000).
- `parallel_jobs=4` e `sample_size=5000` selecionam os 20.000 menores hashes, particionados em quatro faixas disjuntas de ranking. A extração dos filhos (estabelecimentos, empresas, sócios, Simples) corre em paralelo; o domínio CNAE é copiado uma vez.
- As faixas são fundidas em **um** `sample_id` Bronze antes da carga. dbt continua filtrando um lote ativo (`source_period + sample_id`). A escrita DuckDB permanece sequencial sob o lock do run.
- Com `parallel_jobs=1` o `sample_id` e o conjunto de CNPJs são idênticos ao algoritmo já aceito (ADR-003).

## Consequências

Não há fan-out de warehouses nem meses em paralelo. Escalar além de um DuckDB local exigiria outro ADR. O worker Prefect em memória do backfill oficial não deve ser reiniciado só para esta opção.

## Validação

Testes sintéticos cobrem união disjunta, estabilidade do `sample_id` no padrão 1×10.000, leitura de `.env`/TOML, flow com dois jobs de tamanho 1, e backfill com `parallel_jobs=1` mesmo se o ambiente pedir 4.
