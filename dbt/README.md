# Projeto dbt Core

Este projeto dbt Core lê as tabelas imutáveis da camada `bronze` no banco de dados DuckDB local e materializa modelos padronizados da camada Silver, um snapshot SCD Tipo 2 para histórico de Capital Social e os data marts da camada Gold. O arquivo `profiles.yml` é exclusivamente local e recebe o caminho do banco de dados via variável de ambiente `CNPJ_LAKEHOUSE_DUCKDB_PATH`.

Utilize `dbt build` ou o fluxo do Prefect. Todas as macros e testes genéricos necessários pertencem ao próprio repositório, portanto a execução não resolve pacotes pela rede. O fluxo orquestrado executa deliberadamente a camada Silver antes do snapshot, seguido pela camada Gold e testes, garantindo que a dependência do snapshot exista em um banco de dados limpo e consistente.
