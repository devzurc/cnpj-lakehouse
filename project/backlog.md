# Backlog Priorizado

Itens abertos. Histórico `done` está em [delivery-history.md](delivery-history.md).

| Prioridade | ID | Entregável | Complexidade | Dependências | Status |
|---|---|---|---|---|---|
| P0 | S23-01 | Identidade pública CNPJ Lakehouse, histórico limpo e superfície de portfólio | M | — | `in_progress` |
| P1 | S12-01 | Backfill mensal oficial de 2026 em warehouse isolado | L | S11-03 | `blocked` |

`S23-01` troca o namespace operacional para `cnpj-lakehouse`, publica um histórico sem identificadores anteriores e abre o README, o CI e o dashboard para leitura de portfólio. O fluxo oficial de 202601 validou a amostra relacional de 10.000 empresas. A conclusão anual permanece pendente. Cloud continua fora de escopo.
