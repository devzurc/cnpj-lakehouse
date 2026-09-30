# Glossário de Termos

- **`cnpj_basico`**: Identificador cadastral de 8 dígitos atribuído pela Receita Federal à empresa (raiz do CNPJ). Sempre tratado como string preservando zeros à esquerda.
- **CNPJ do Estabelecimento**: Identificador completo de 14 dígitos formado pelo CNPJ básico (8 dígitos), ordem do estabelecimento (4 dígitos) e dígitos verificadores (2 dígitos).
- **Razão Social**: Nome empresarial registrado oficialmente perante os órgãos competentes.
- **Capital Social**: Valor bruto ou integralizado do capital da empresa, armazenado como texto no formato brasileiro (`1.234,56`) e convertido para `decimal(18,2)`.
- **CNAE (Classificação Nacional de Atividades Econômicas)**: Padrão nacional de classificação estruturado em Seção, Divisão (2 dígitos), Grupo (3 dígitos), Classe (5 dígitos) e Subclasse (7 dígitos).
- **Matriz / Filial**: Indicador que distingue a sede principal da empresa (`matriz_filial_code = '1'`) de suas dependências (`'2'`).
- **Situação Cadastral**: Código do estado de funcionamento do estabelecimento (`01` = Nula, `02` = Ativa, `03` = Suspensa, `04` = Inapta, `08` = Baixada).
- **QSA (Quadro de Sócios e Administradores)**: Dados sobre a composição societária e representantes legais da pessoa jurídica.
- **Simples Nacional & MEI**: Regimes tributários diferenciados para micro e pequenas empresas e microempreendedores individuais.
- **`source_period`**: Identificador do período mensal de referência dos dados no formato `YYYYMM` (ex: `202601`).
- **`reference_date`**: Data de corte analítica transportada pelos fatos da camada Gold (padrão: último dia do `source_period`).
- **`sample_id`**: Identificador hash SHA-256 único e determinístico gerado a partir do manifesto da fonte, tamanho da amostra e algoritmo de seleção.
- **Camadas Medalhão (Bronze / Silver / Gold)**:
  - **Bronze**: Dados brutos imutáveis carregados dos arquivos públicos, com metadados de auditoria e linhagem física.
  - **Silver**: Dados normalizados, tipados, deduplicados e consolidados intermediários gerenciados pelo dbt.
  - **Gold**: Data marts dimensionais e fatos prontos para consumo analítico.
- **SCD Tipo 2 (Slowly Changing Dimensions)**: Mecanismo de versionamento histórico implementado via dbt snapshot com colunas de controle `valid_from` e `valid_to` para rastrear variações de Capital Social.
