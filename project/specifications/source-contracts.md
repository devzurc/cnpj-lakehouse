# Especificação dos Contratos de Fonte

## Resolução e Descoberta de Fontes

- **Índice Raiz do Espelho**: `https://dados-abertos-rf-cnpj.casadosdados.com.br/arquivos/`
- **Diretório Canônico de Janeiro de 2026**: `https://dados-abertos-rf-cnpj.casadosdados.com.br/arquivos/2026-01-11/`
- **Arquivos Obrigatórios Requeridos**:
  - `Estabelecimentos0.zip` até `Estabelecimentos9.zip` (10 shards numerados).
  - `Empresas0.zip` até `Empresas9.zip` (10 shards numerados).
  - `Socios0.zip` até `Socios9.zip` (10 shards numerados).
  - `Simples.zip` (arquivo único).
  - `Cnaes.zip` (arquivo único).

O resolvedor de fontes seleciona exatamente um diretório no padrão `YYYY-MM-DD` correspondente ao período solicitado no formato `YYYYMM` (ex.: `202601`). Caso nenhum ou mais de um diretório correspondente seja encontrado, a execução é abortada imediatamente com erro explícito.

## Formato dos Arquivos e Decodificação

- Todos os membros contidos nos arquivos ZIP são tratados como texto CSV sem cabeçalho (*headerless*), delimitados por ponto e vírgula (`;`), com campos textuais delimitados por aspas duplas (`"`).
- A codificação nominal é Windows CP1252. Caso um arquivo oficial contenha bytes indefinidos no padrão CP1252 (como o byte `0x8F` no arquivo oficial de Janeiro/2026), o decodificador preserva o byte de forma reversível (*lossless*) mapeando-o para o ponto de código Unicode C1 idêntico (conforme ADR-006).
- Valores vazios são mantidos em seu formato bruto na camada Bronze e normalizados para tipos nulos apropriados na camada Silver.

## Contratos de Esquema e Campos por Dataset

| Dataset | Shards | Qtd. Colunas | Lista Exata de Colunas |
|---|---:|---:|---|
| **Empresas** | 10 | 7 | `cnpj_basico`, `razao_social`, `natureza_juridica`, `qualificacao_responsavel`, `capital_social_raw`, `porte_empresa`, `ente_federativo_responsavel` |
| **Estabelecimentos** | 10 | 30 | `cnpj_basico`, `cnpj_ordem`, `cnpj_dv`, `identificador_matriz_filial`, `nome_fantasia`, `situacao_cadastral`, `data_situacao_cadastral_raw`, `motivo_situacao_cadastral`, `nome_cidade_exterior`, `pais`, `data_inicio_atividade_raw`, `cnae_fiscal_principal`, `cnae_fiscal_secundaria`, `tipo_logradouro`, `logradouro`, `numero`, `complemento`, `bairro`, `cep`, `uf`, `municipio`, `ddd_1`, `telefone_1`, `ddd_2`, `telefone_2`, `ddd_fax`, `fax`, `correio_eletronico`, `situacao_especial`, `data_situacao_especial_raw` |
| **Sócios** | 10 | 11 | `cnpj_basico`, `identificador_socio`, `nome_socio`, `cnpj_cpf_socio`, `qualificacao_socio`, `data_entrada_sociedade_raw`, `pais`, `representante_legal`, `nome_representante`, `qualificacao_representante_legal`, `faixa_etaria` |
| **Simples** | 1 | 7 | `cnpj_basico`, `opcao_simples`, `data_opcao_simples_raw`, `data_exclusao_simples_raw`, `opcao_mei`, `data_opcao_mei_raw`, `data_exclusao_mei_raw` |
| **CNAE** | 1 | 2 | `cnae_code`, `cnae_description` |

Toda linha lida deve possuir rigorosamente a contagem de colunas esperada pelo contrato. Membros de arquivos ZIP devem ser legíveis, não criptografados, não vazios e com CRC verificado ao final da leitura do fluxo.

Após a validação, um manifesto endereçado por conteúdo deve ser persistido sob o `source_period`, contendo URL, nome, dataset, tamanho em bytes, SHA-256, membros ZIP e contagem de linhas de cada arquivo. Um conjunto idêntico de checksums reutiliza essa validação; conteúdo alterado produz um novo `manifest_id` imutável.
