# CNPJ Lakehouse repository instructions

## Source of truth

Before changing files, read `project/active-sprint.md`, `project/backlog.md`, and every specification linked by remaining work. Historical sprint evidence lives in `project/delivery-history.md`; do not recreate `project/sprints/*/tasks/`.

The precedence for product truth is:

1. Explicit user instruction
2. Accepted ADRs in `project/decisions/`
3. Canonical specifications in `project/specifications/`
4. The active sprint and open backlog items
5. Repository conventions

Do not invent a requirement, source schema, or operational policy. Record a behavior-changing discovery in `project/knowledge/verified-insights.md`; create or amend an ADR before implementing a new material decision.

## Simple operating defaults

- Prefer the documented Docker Compose path for operators; keep Python/uv as the native development fallback.
- Start with synthetic sources and aggregate evidence. Never expose restricted rows, secrets, personal paths, or generated runtime files.
- Make the smallest coherent change: reuse existing scripts, verifiers, ADRs and skills before adding a new abstraction.
- Use a specialist skill only when the changed surface matches it; use reviewers only for an independent material risk.
- Finish with one concise operator path in the README and record remaining validation gaps explicitly.

## Delivery rules

- Work only on backlog items whose status is `ready` or `in_progress`.
- Keep one implementation owner per worktree area. Use subagents only for bounded, read-only reviews.
- Update backlog, active sprint, delivery history, checkpoint and changelog in the same change that implements remaining work.
- Do not mark an item `done` until its stated verification passes.
- Keep `project/checkpoints/delivery-readiness.md` synchronized when release readiness or an external-action boundary changes.
- Keep CNPJ and all codes as strings; preserve leading zeroes.
- Keep downloaded data, DuckDB files, and generated artifacts outside Git.
- The local DuckDB pipeline is the critical path. Do not add GCP execution, ReceitaWS, or optional marts without explicit user authorization.
- Do not create/delete repositories, push Git, change PR or release state, or run cloud commands without explicit user authorization immediately before the action.

## Quality

Run the smallest relevant quality gate first, then the gates required by the change. Do not broaden test runs without a change or unresolved concern that justifies it.

Label evidence as synthetic, official-volume, clean-clone, or remote. `UV_OFFLINE=1` with a populated cache proves that the rehearsal made no external resolution; it does not prove a cold-cache air-gapped installation. Never report a repository as published until its remote branch is verified.

## Public identity

Do not use former client or company names in source, documentation,
configuration, tests, examples, or agent instructions. Refer to project
requirements, technical challenge requirements, or delivery requirements.

```yaml
privacy:
  forbidden_public_identifiers:
    - former client/company name
```

## Subagent policy

Use the configured reviewers only when an independent architecture, dbt, data-quality, or FinOps review materially improves confidence. Reviewers report findings and do not edit code; the main agent evaluates and integrates conclusions.

For cross-layer audit routing, reviewer boundaries, and the evidence/remediation lifecycle, follow `project/specifications/ai-governance.md`. A reviewer finding never bypasses task ownership, ADR/specification precedence, or external-action authorization.
