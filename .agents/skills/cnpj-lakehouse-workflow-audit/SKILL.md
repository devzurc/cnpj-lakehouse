---
name: cnpj-lakehouse-workflow-audit
description: Audit CNPJ Lakehouse cross-layer workflow, governance evidence, and specialist routing; do not implement pipeline changes or authorize external actions.
---

# Workflow audit

Read `project/specifications/ai-governance.md`, the active task, and the specifications relevant to the requested audit surface before inspecting the repository.

Establish the audit boundary first: workflow stages, source/data period, evidence type, and requested decision. Prefer deterministic repository evidence and existing verifiers. Do not download official data, inspect or disclose row-level restricted data, mutate runtime state, or convert an inventory into deletion.

Use the shortest reproducible path first: Docker Compose for operator behavior, then native internals only when a Docker result or a code-level question requires it. Keep findings at aggregate level and state clearly whether the evidence is synthetic, containerized, native, clean-clone, official-volume, or remote.

Route only material independent questions to the matching read-only reviewer. Consolidate findings by severity with the repository evidence, affected invariant, risk, and a concrete next action. Do not use a reviewer as an implementation owner and do not create duplicate reviews of the same concern.

For each finding, distinguish: fixed and verified, accepted exception with a review trigger, deferred tracked remediation, or out of scope. A behavior-changing remediation needs a ready or in-progress task and any required ADR/specification update before implementation. Keep local completion distinct from external delivery authorization.

End with a concise coverage statement: layers reviewed, gates run, residual risks, and whether task/backlog/sprint/checkpoint/changelog need synchronization. Use `cnpj-lakehouse-quality-gates` for actual gate selection; this skill coordinates evidence rather than replacing domain validation.
