---
name: cnpj-lakehouse-dbt-development
description: Build or review dbt Silver, Gold, macro, snapshot, incremental, and test work. Do not use for raw download mechanics.
---

# dbt development

Read `project/specifications/data-model.md`, `project/specifications/dbt-project.md`, and `project/specifications/quality-strategy.md` before changing dbt assets.

For every model, state and preserve its grain, key, materialization, source period behavior, and data-quality contract. Keep identifiers and codes as strings. Make parsing failures observable through tests rather than silently coercing values.

`normalize_cnpj` returns null for structurally invalid inputs; it must never manufacture a zero CNPJ. Derive CNAE and UF from the same deterministic representative active establishment: matrix first, otherwise the lowest 14-digit CNPJ.

Keep runtime dbt dependencies repository-local: do not add a network-time `dbt deps` requirement to the critical path. Execute core Silver models before the snapshot, then Gold marts, then the complete test suite. Isolate test targets so stale manifests cannot become evidence.

Limit incremental work to the affected reference date. Keep the Capital Social snapshot reproducible with a two-version fixture and exactly one current version. Update model and column documentation with every published-model change.
