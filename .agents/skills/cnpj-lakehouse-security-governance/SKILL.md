---
name: cnpj-lakehouse-security-governance
description: Harden or review local data security, governance, dependency risk, and delivery hygiene. Do not use for cloud deployment.
---

# security and data governance

Read `project/specifications/security-and-data-governance.md`, the active task, and relevant accepted ADRs before changing controls or documentation.

Classify Bronze, sensitive Silver, Gold, and execution evidence separately. Keep local runtime data and artifacts owner-only; retention is manual and any cleanup must first inventory targets without deleting them. Do not introduce credentials, cloud execution, or personal data into Git.

Validate content-addressed manifests and execution evidence before reuse or promotion. Audit dependencies with a deterministic tool; a vulnerability without an available fix needs a limited documented exception, trusted-input scope, mitigation, and review trigger.

For BigQuery design work, preserve least privilege, layer separation, data minimization, and controlled exposure through column policies or authorized views. This skill documents the design only and never authorizes cloud resources.
