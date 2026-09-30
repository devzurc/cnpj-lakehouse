# Especificação de Governança de IA

## Objetivo e limites

A assistência por IA acelera descoberta, implementação e verificação, mas não substitui a fonte de verdade, a decisão humana nem a autorização para ações externas. O agente principal é o único responsável por integrar evidências, alterar o worktree e manter a tarefa sincronizada. Skills orientam um domínio; revisores independentes apenas leem e reportam.

Toda mudança começa no trabalho residual: ler `project/active-sprint.md`, o backlog aberto, ADRs e especificações vinculadas. O histórico de sprints está em `project/delivery-history.md` (ADR-016); não recriar pastas de tarefa para consultar evidência antiga. Uma descoberta que muda comportamento requer ADR ou atualização da especificação canônica antes da implementação. Uma correção decorrente de auditoria entra como item rastreado no backlog, nunca como alteração implícita do revisor.

O padrão operacional é simples: Docker Compose primeiro para operadores, execução nativa apenas para desenvolvimento, fontes sintéticas antes de oficiais e evidência agregada antes de qualquer exposição visual. Não criar novas camadas de processo quando uma skill, verificador ou documento existente já cobre o risco.

## Método de trabalho assistido

1. **Descobrir**: o agente principal delimita escopo, fonte de verdade, dados afetados e evidência existente.
2. **Executar**: aplica a skill especializada quando ela muda decisões ou reduz risco; mantém um único owner para cada área alterada.
3. **Revisar quando material**: solicita revisão somente-leitura independente para risco transversal, contrato alterado, achado não resolvido ou gate de entrega. Revisão decorativa não é necessária.
4. **Remediar**: o agente principal classifica cada achado como corrigido, aceito com exceção documentada ou fora de escopo. Achados que exigem mudança viram tarefa/ADR antes do código.
5. **Evidenciar**: executa os gates proporcionais, distingue evidência sintética, oficial, clone limpo e remota, e sincroniza tarefa, backlog, sprint, checkpoint, rastreabilidade e changelog quando a verdade registrada mudar.

Em qualquer entrega, o agente deve deixar explícitos: o comando feliz para o operador, a validação executada, o que não foi validado e a ação externa ainda não autorizada.

Um parecer de IA é evidência revisável, não aprovação automática. Não expor dados de linha, segredos, caminhos pessoais ou artefatos restritos em prompts, evidências ou documentação.

## Roteamento de skills

| Superfície | Skill | Uso obrigatório quando aplicável |
|---|---|---|
| Planejamento, estado e entrega | `cnpj-lakehouse-sprint-execution` | Criar/executar tarefa de sprint ou atualizar evidência/estado. |
| Fonte, amostragem e Bronze | `cnpj-lakehouse-ingestion` | Alterar ou revisar download, manifesto, amostra ou carga raw. |
| Silver, Gold e dbt | `cnpj-lakehouse-dbt-development` | Alterar ou revisar modelos, macros, snapshot, incremental ou testes dbt. |
| Gatilhos de qualidade | `cnpj-lakehouse-quality-gates` | Selecionar validação de uma alteração rastreada. |
| Documento BigQuery/FinOps | `cnpj-lakehouse-finops-documentation` | Alterar ou revisar o deliverable FinOps; não provisiona cloud. |
| Segurança e governança | `cnpj-lakehouse-security-governance` | Alterar ou revisar classificação, permissões, integridade de evidências ou advisory. |
| Auditoria transversal | `cnpj-lakehouse-workflow-audit` | Auditar fluxo, consistência documental e encaminhar remediações; não implementa pipeline. |

## Roteamento de revisores

| Risco material | Revisor somente-leitura | Foco de evidência |
|---|---|---|
| Fronteiras Medallion, recuperação, lock ou orquestração | `architecture-reviewer` | ownership, idempotência, recuperação e escopo local. |
| Contratos de fontes, amostras e dados | `data-quality-reviewer` | completude, relacionamento, tipos, nulos e testes. |
| Modelagem dbt e warehouse | `dbt-reviewer` | grão, join, incremental, snapshot, macro e teste. |
| Design/documento BigQuery | `finops-reviewer` | custo, desenho físico, onboarding e ausência de deploy. |
| Dados sensíveis, integridade de evidência e dependências | `security-governance-reviewer` | classificação, acesso, exceções e proveniência. |
| Arquivos, documentação e gestão de trabalho | `repository-hygiene-reviewer` | drift comprovado, itens rastreados e inventário não destrutivo. |

O revisor retorna achados ordenados por severidade, com evidência, invariante afetado, risco e recomendação. Ele não edita, não executa comandos mutantes, não baixa dados oficiais e não cria autorização. O agente principal pode pedir vários pareceres se os riscos forem independentes; não pode atribuir a dois agentes a mesma alteração.

## Autoridade, segurança e evidência

As regras em `.codex/rules/remote-actions.rules` e `AGENTS.md` prevalecem para push, GitHub, release e cloud: uma passagem local não autoriza nenhuma dessas ações. Exclusão de runtime continua manual, precedida de inventário somente-leitura. Dados Bronze/Silver e evidências operacionais são restritos conforme a especificação de segurança.

O validador estrutural é um gate de consistência, não uma prova de correção semântica. Ele exige os artefatos canônicos, o índice `project/delivery-history.md`, backlog só com itens abertos (S12-01 `blocked`), skills e revisores válidos, e a ausência de `project/sprints/*/tasks/`. Sprint, checkpoint e changelog devem mencionar o estado corrente quando houver trabalho `in_progress`. Os gates de dados, dbt e orquestração continuam necessários conforme a alteração.
