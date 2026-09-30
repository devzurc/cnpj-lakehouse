# Especificação de Segurança e Governança de Dados

## Classificação e acesso local

- **Bronze restrito**: ZIPs, amostras e tabelas brutas; podem conter dados pessoais, contato e linhagem física.
- **Silver restrito**: modelos que preservam atributos de sócios, documentos mascarados ou contato.
- **Gold controlado**: marts publicados; expor somente os atributos necessários ao consumidor aprovado.
- **Evidências restritas**: manifestos, resultados e logs de execução; não devem conter segredos nem registros de dados.

O diretório de runtime, seus subdiretórios e todos os arquivos produzidos pelo pipeline usam permissões de proprietário somente. O operador mantém os dados até removê-los explicitamente; o projeto oferece apenas inventário de limpeza em modo leitura.

Documentos de sócio e representante legal não ultrapassam a Bronze em valor bruto. A Silver pode conter somente o pseudônimo determinístico e versionado definido na ADR-015; Gold não publica esses campos.

## Integridade e proveniência

Manifestos de fonte e de amostra são endereçados por conteúdo, têm conjunto exato de arquivos e são verificados antes de reutilização. Cada amostra registra versão do algoritmo, manifesto-fonte, hashes/contagens dos cinco arquivos e empresas selecionadas. Evidências dbt são promovidas somente depois de JSON válido, `invocation_id` coerente e atribuição ao `flow_run_id` correto.

## Publicação e dependências

Dados, artefatos e segredos não entram no Git. Dependências passam por auditoria de vulnerabilidades; uma vulnerabilidade sem correção disponível exige exceção documentada, escopo de exposição, mitigação e revisão na próxima atualização. O renderizador PDF aceita somente Markdown rastreado no repositório e não pode buscar recursos de rede.

## Design em nuvem

O design BigQuery separa permissões por camada, restringe Bronze/Silver, usa identidades de workload e aplica políticas de coluna ou views autorizadas antes de disponibilizar campos sensíveis. Esta especificação não autoriza provisionamento em nuvem.
