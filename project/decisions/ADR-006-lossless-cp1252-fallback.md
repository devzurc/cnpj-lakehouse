---
id: ADR-006
status: accepted
date: 2026-09-07
decision_makers: [project]
---

# Preservar bytes indefinidos em arquivos fonte nominais CP1252

## Contexto

O arquivo oficial `Estabelecimentos0.zip` de Janeiro de 2026 da Receita Federal contém o byte `0x8F` em um campo textual. A tabela de codificação Windows CP1252 deixa essa posição de byte indefinida, fazendo com que o decodificador estrito do Python (`errors='strict'`) lance uma exceção e aborte a leitura de um arquivo CSV que, fora isso, é íntegro, possui CRC válido e adere ao contrato de 30 colunas.

## Decisão

Decodificar todos os bytes definidos utilizando CP1252. Exclusivamente para as posições de byte indefinidas na tabela CP1252, mapear cada byte de forma reversível e sem perdas (*lossless*) para o code point Unicode C1 idêntico. Não substituir por caracteres de interrogação (`?`), não descartar e não normalizar esses bytes na camada Bronze.

## Consequências

O arquivo oficial da Receita Federal pode ser processado em sua totalidade enquanto o texto bruto permanece reversível byte a byte. A camada Silver pode subsequentemente aplicar regras explícitas de higienização para apresentação final, mas a camada Bronze preserva fielmente a evidência física da fonte de dados original.

## Validação

Uma fixture de teste de regressão injeta deliberadamente o byte `0x8F`, verifica o parsing com sucesso contra o contrato da tabela e comprova a recuperação exata byte a byte através da codificação Latin-1.
