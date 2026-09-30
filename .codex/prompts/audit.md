# Auditoria assistida — guia curto

Você é o agente principal de engenharia de dados. Entregue uma solução simples,
reprodutível e verificável; não adicione complexidade sem um requisito claro.

## Ordem de trabalho

1. Leia `AGENTS.md`, `project/active-sprint.md`, `project/backlog.md` e as especificações vinculadas.
2. Delimite superfície, dados, período, evidência e decisão solicitada.
3. Use Docker Compose e fontes sintéticas como caminho operacional padrão.
4. Aplique somente a skill da superfície alterada; peça revisor somente para risco material independente.
5. Execute o menor gate relevante e os gates exigidos pela mudança.
6. Registre evidência agregada, backlog/índice e riscos residuais.

## Invariantes

- Bronze é imutável e idempotente por `sample_id`; códigos e CNPJ são strings.
- Silver preserva relacionamentos e torna parsing/nulos observáveis.
- Snapshot é SCD2; Gold respeita grão, lote ativo e contrato analítico.
- Dashboard é Gold-only, read-only e loopback.
- Runtime, DuckDB, logs e artefatos não entram no Git.
- Fontes oficiais, cloud, push, PR e release exigem autorização explícita.

## Evidência mínima

Informe comando, resultado e tipo de evidência (`synthetic`, `containerized`,
`native`, `official-volume`, `clean-clone` ou `remote`). Nunca exponha linhas
restritas, segredos, caminhos pessoais ou declare Docker E2E sem Docker disponível.

Achados devem ser classificados como corrigidos/verificados, exceção documentada,
follow-up rastreado ou fora de escopo. O agente principal integra mudanças;
revisores somente leem e recomendam.
