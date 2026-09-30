---
name: cnpj-lakehouse-finops-documentation
description: Write or review the Portuguese BigQuery FinOps and onboarding document with defensible physical-design and cost guidance. Do not use for cloud deployment.
---

# FinOps documentation

Read `project/specifications/bigquery-finops.md` and `docs/AGENTS.md` before editing the document.

Describe a production design with immutable GCS Bronze, aligned BigQuery datasets, partitioning, clustering, required partition filters, scoped MERGE, labels, lifecycle, budgets, and job monitoring. Explain query cost in terms of bytes processed and capacity use in terms of slot-ms. Do not claim fixed savings percentages without measured evidence.

Include a compact physical-design matrix for every major raw, Gold and snapshot table: table, partitioning, clustering, expected query pattern, and benefit. Require labels for every pipeline job; if interactive jobs are excluded, state the exception and governance explicitly.

Keep the final Portuguese document within the required 4–7 A4 pages; the accepted artifact currently renders to six. Include local onboarding and the repository delivery reference. After material edits, render and run `uv run python scripts/verify_finops_pdf.py docs/finops-bigquery-architecture.pdf`; do not treat this design document as authorization to deploy cloud resources.
