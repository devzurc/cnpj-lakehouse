---
id: ADR-015
status: accepted
date: 2026-09-10
decision_makers: [project]
---

# Pseudonimizar identificadores restritos fora da Bronze

## Decisão

Os campos de documento de sócio e representante legal permanecem brutos somente na Bronze restrita. A Silver não publica esses valores: para cada valor não vazio, publica um pseudônimo determinístico `v1:` seguido de SHA-256 do valor normalizado e separado por domínio.

O pseudônimo não é tratado como anonimização: a Silver continua restrita, e a versão permite trocar a representação em uma decisão futura. Nenhum valor Bronze bruto entra em modelos, artefatos, logs, documentação de evidência ou Git.

Durante a seleção, o manifesto da amostra registra por arquivo de Estabelecimentos apenas as contagens de CNPJ básico estruturalmente inválido, válido e selecionado. Nenhum CNPJ inválido ou candidato é gravado nessa evidência.

## Consequências

Os consumidores Silver podem reconciliar um mesmo identificador dentro do ambiente autorizado sem receber o valor bruto. O valor bruto continua disponível exclusivamente na Bronze para a finalidade de ingestão e auditoria restrita.
