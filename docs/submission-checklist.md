# Checklist de submissão do desafio

Este guia orienta a avaliação do repositório contra o PDF do desafio. O caminho
crítico é local: DuckDB, dbt Core e Prefect não exigem credencial de nuvem. O
desenho BigQuery é uma proposta documentada, sem provisionamento cloud.

## Cobertura dos requisitos

| Pedido do desafio | Onde avaliar | Evidência reproduzível |
| --- | --- | --- |
| dbt em camadas, staging, dimensões, fato e incremental | `dbt/models/` e [modelo de dados](../project/specifications/data-model.md) | `uv run pytest -q` e o ensaio Docker abaixo |
| Snapshot SCD Tipo 2 de Capital Social | `dbt/snapshots/company_capital_social_snapshot.sql` | Teste de duas versões na suíte Python |
| Ao menos três macros Jinja aplicadas | `dbt/macros/` | Compile/testes dbt executados pelo flow |
| Oito ou mais testes dbt, nativos e regra customizada | [estratégia de qualidade](../project/specifications/quality-strategy.md) | `uv run python -m dbt.cli.main ls --resource-type test --project-dir dbt --profiles-dir dbt` |
| Flow Prefect: extração, Bronze, dbt e qualidade | `cnpj_lakehouse/flows/cnpj_lakehouse.py` e [fluxo](../project/specifications/prefect-flow.md) | Ensaio sintético do mesmo deployment |
| Amostra local e relações preservadas | [amostragem e Bronze](../project/specifications/sampling-and-bronze.md) | `./scripts/docker.sh verify` mostra apenas contagens agregadas |
| FinOps e desenho BigQuery | [documento FinOps](finops-bigquery-architecture.md) e PDF rastreado | `uv run python scripts/verify_finops_pdf.py docs/finops-bigquery-architecture.pdf` (PDF com 6 páginas A4) |
| Código limpo e execução local | [README](../README.md), `uv.lock` e `.gitignore` | Estrutura, Ruff, testes e Compose abaixo |

## Roteiro curto para avaliação

Com Docker em execução, a demonstração sintética conclui em minutos e não baixa
dados públicos:

```bash
./scripts/docker.sh start
./scripts/docker.sh demo
./scripts/docker.sh verify
```

O último comando valida Bronze, Gold, contrato analítico e idempotência sem
imprimir linhas de dados restritos. Para os gates de código e documentação:

```bash
UV_OFFLINE=1 uv sync --all-groups --locked
uv run python scripts/validate_project_structure.py
uv run ruff check .
uv run pytest -q
uv run python scripts/verify_finops_pdf.py docs/finops-bigquery-architecture.pdf
docker compose config
```

`UV_OFFLINE=1` pressupõe cache local preenchido; ele demonstra que o ensaio não
resolve dependências na rede, não uma instalação air-gapped de cache vazio.

## Limites declarados

- A evidência de volume oficial de janeiro de 2026 está registrada com contagens
  agregadas no [checkpoint de entrega](../project/checkpoints/delivery-readiness.md).
- O backfill anual de 2026 continua bloqueado e não é pré-requisito do desafio,
  que pede uma amostra local.
- O ensaio Compose foi repetido em 2026-09-14: o flow sintético concluiu e os
  verificadores confirmaram 3 empresas consistentes em Bronze, Silver e Gold,
  sem duplicidades no contrato analítico. Neste WSL o launcher usou `docker.exe`.
- Push, PR, release e cloud são ações externas: a aprovação local não afirma que
  qualquer uma delas foi executada.

Para o e-mail, inclua o link do repositório se o acesso estiver liberado ao time
avaliador. Caso seja privado, envie os dados de acesso ou anexe o artefato do
repositório, conforme solicitado no desafio.
