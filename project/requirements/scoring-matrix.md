# Matriz de Pontuação e Avaliação

| Área de Avaliação | Pontos | Evidências e Comprovações |
|---|---:|---|
| Domínio de dbt Core | 30 | Modelos em camadas, macros Jinja, estratégia incremental, snapshot SCD2, testes e documentação. |
| Arquitetura e Resiliência | 25 | Manifesto Bronze, retentativas controladas no Prefect, idempotência, isolamento de falhas e retenção de artefatos. |
| Qualidade de Dados | 20 | Contratos de fonte, suíte dbt acima do mínimo de 8 (inventário via `dbt ls`), testes negativos e amostra determinística com integridade relacional. |
| BigQuery e FinOps | 15 | Documento de design físico, particionamento/clusterização, controles orçamentários e monitoramento (4–7 páginas em PDF). |
| Código Limpo e Governança Git | 10 | Reprodutibilidade local, uv.lock, higiene do repositório Git e histórico rastreável de tarefas e evidências. |
