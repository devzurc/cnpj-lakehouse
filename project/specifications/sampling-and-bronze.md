# Especificação de Amostragem Determinística e Camada Bronze

## Algoritmo de Amostragem Determinística

1. **Varredura em Streaming**: Lê todos os shards de Estabelecimentos (`Estabelecimentos0.zip` a `Estabelecimentos9.zip`) por streaming, sem carregar arquivos completos na memória RAM. A execução pode processar arquivos independentes em processos locais limitados; cada resultado é fundido na ordem canônica de arquivo antes do ranking global (ADR-014).
2. **Normalização Prévia**: Extrai e valida o `cnpj_basico` (8 posições em texto, preservando zeros à esquerda).
3. **Cálculo de Hash e Score**: Calcula a pontuação determinística para cada CNPJ básico único: `sha256("{source_period}:{cnpj_basico}")`.
4. **Fila de Prioridade Limitada (*Bounded Heap*)**: Mantém os $N$ menores scores (onde $N = \text{sample\_size} \times \text{parallel\_jobs}$, padrão $N = 10.000$ com 1 job) em uma estrutura de min-heap de tamanho fixo. Com `parallel_jobs > 1`, a extração dos registros filhos ocorre em paralelo em faixas disjuntas do ranking; o domínio CNAE é copiado uma vez e as faixas são fundidas em um único `sample_id` (ADR-013).
5. **Filtragem de Filiais**: Lê novamente os shards de Estabelecimentos e extrai todas as linhas cujos CNPJs pertençam às empresas selecionadas no passo 4. Arquivos independentes podem gerar fragmentos privados em paralelo, fundidos deterministamente antes da carga.
6. **Filtragem Relacional**: Varre em streaming os shards de Empresas (`Empresas0..9`), Sócios (`Socios0..9`) e Simples Nacional (`Simples.zip`), retendo exatamente as linhas correspondentes às empresas selecionadas. A concorrência por arquivo não cria writers DuckDB concorrentes.
7. **Cópia Integral de Domínio**: Copia 100% dos registros do arquivo de atividades econômicas CNAE (`Cnaes.zip`).
8. **Validação de Integridade**: Dispara falha imediata caso alguma empresa selecionada em Estabelecimentos não possua registro correspondente no dataset de Empresas.

O identificador `sample_id` é gerado via digest SHA-256 do período da fonte, manifesto dos arquivos de origem, tamanho da amostra por job, versão do algoritmo e, se `parallel_jobs ≠ 1`, o número de jobs. Entradas idênticas produzem rigorosamente o mesmo conjunto de CNPJs e o mesmo `sample_id`. Com um job, o digest permanece o de ADR-003.

O manifesto da amostra registra por arquivo de Estabelecimentos somente três contagens agregadas: CNPJ básico inválido, válido e selecionado. Não retém valores inválidos, candidatos fora da coorte ou linhas de origem nessa observabilidade.

## Metadados e Linhagem da Camada Bronze

Todas as tabelas brutas no esquema `bronze` contêm colunas obrigatórias de linhagem física e auditoria:
- `source_period`: período mensal da fonte (`YYYYMM`).
- `source_file`: nome do arquivo ZIP baixado.
- `source_member`: nome do arquivo CSV interno descompactado.
- `source_url`: URL de origem de onde o arquivo foi obtido.
- `source_file_sha256`: checksum SHA-256 do arquivo ZIP de origem.
- `source_row_number`: número original da linha no membro CSV descompactado.
- `sample_id`: identificador determinístico da amostra.
- `ingestion_batch_id`: UUID único do lote de ingestão.
- `ingested_at`: timestamp UTC da carga no DuckDB.
- `record_hash`: hash SHA-256 da serialização canônica JSON dos valores brutos da linha.

A linhagem física única de cada linha é dada pela tupla `(source_file_sha256, source_member, source_row_number)`.

## Idempotência e Append-Only

- Downloads parciais utilizam a extensão temporária `.part` e são promovidos apenas após confirmação do checksum SHA-256.
- A tabela `ops.sample_manifests` registra as amostras já carregadas. Caso o mesmo `sample_id` seja reexecutado, a etapa de carga Bronze atua como *no-op*, retornando os metadados existentes sem duplicar linhas.
- O inventário local compara os 32 arquivos contratados no diretório de download com as amostras Bronze do `source_period`. ZIPs já presentes não são baixados de novo. A mesma quantidade de empresas distintas (`count(distinct cnpj_basico)`) no período reutiliza a Bronze sem copiar fontes; a contagem de linhas nos shards Empresas não é o tamanho da coorte. Um segundo lote (por exemplo ensaio de 3 empresas e oficial de 10.000 no mesmo `YYYYMM`) é recusado para não misturar warehouse.
- A camada Bronze é estritamente *append-only*. O parâmetro `--full-refresh` do dbt reconstrói apenas os modelos derivados (Silver e Gold), sem jamais truncar, duplicar ou apagar o histórico de dados brutos na Bronze.
