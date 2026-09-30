# Premissas do Projeto

- **Acesso e disponibilidade da fonte**: O espelho público de Janeiro de 2026 (`2026-01-11`) da Casa dos Dados / Receita Federal permanece acessível via HTTP ou os arquivos equivalentes são fornecidos localmente através do parâmetro `--source-dir`.
- **Preservação de relacionamentos na amostra**: Uma amostra baseada em 10.000 empresas (`cnpj_basico`) produz naturalmente mais de 10.000 linhas nas tabelas de estabelecimentos e sócios, pois uma empresa pode possuir múltiplas filiais e sócios.
- **Entregável FinOps**: O entregável de FinOps e BigQuery é aceito como documentação técnica em Markdown acompanhado do PDF renderizado de 4 a 7 páginas A4 (`docs/finops-bigquery-architecture.pdf`).
- **Layout oficial de arquivos**: A estrutura e quantidade de colunas dos arquivos da Receita Federal permanecem consistentes com as contagens documentadas (Empresas: 7, Estabelecimentos: 30, Sócios: 11, Simples: 7, CNAE: 2).
- **Ambiente de execução local**: O runtime é Python 3.12 gerenciado via `uv`. O armazenamento de dados e do banco DuckDB deve estar localizado no sistema de arquivos nativo do Linux (ext4 no WSL/Linux) para evitar concorrência e problemas de I/O em sistemas de arquivos compartilhados como o OneDrive/NTFS.
