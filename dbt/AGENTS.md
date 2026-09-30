# dbt-area instructions

Preserve Medallion boundaries: Bronze is Prefect-owned raw data; dbt owns Silver, Gold, and snapshots. All model changes require an explicit grain, primary key, materialization, tests, and documentation. Use macros for CNPJ, decimal, CNAE, and audit semantics. Keep DuckDB as the executable adapter.

Invalid CNPJ structures remain null and observable; never manufacture zero identifiers. CNAE and UF representative attributes must come from the same active establishment row, preferring the matrix and otherwise the lowest full CNPJ. Preserve exactly one current Capital Social snapshot version and fact uniqueness by reference date plus CNPJ básico.

Keep runtime dependencies repository-local and do not add `dbt deps` to the critical path. Use isolated target directories for tests so stale artifacts cannot become evidence.

Read `project/specifications/dbt-project.md`, `project/specifications/data-model.md`, and `project/specifications/quality-strategy.md` before changing this area.
