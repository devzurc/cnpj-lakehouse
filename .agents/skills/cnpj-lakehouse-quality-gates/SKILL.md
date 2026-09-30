---
name: cnpj-lakehouse-quality-gates
description: Select and run proportionate lakehouse validation for ingestion, dbt, orchestration, documentation, and task-completion evidence. Do not use to broaden checks without a relevant change.
---

# Quality gates

Read the active task's verification section first. Run the smallest relevant checks, then the mandatory gates for that task.

Choose gates by changed surface:

- Docker/runtime: validate Compose syntax, shell wrappers, healthchecks, synthetic E2E in containers when Docker is available, persistence across restart, and the existing verifiers. If Docker is unavailable, report that boundary instead of simulating success.

- ingestion: focused fixture tests, negative archive/download cases, idempotency, then `verify_bronze.py` for a completed sample;
- dbt: isolated compile/run/snapshot/test fixtures, grain and current-version assertions, then `verify_warehouse.py`;
- orchestration: decorated-flow order, failure propagation, stale-artifact rejection, and grouping by Prefect `flow_run_id`;
- documentation or governance: structure validation, relevant renderer/verifier, skill validation, `git diff --check`, and tracked-file hygiene;
- release readiness: `UV_OFFLINE=1 uv sync --all-groups --locked` in a clean clone, the documented demo flow, deterministic verifiers, idempotent rerun, and a clean worktree.

Distinguish synthetic, official-volume, clean-clone, and remote-publication evidence. A cached dependency install with `UV_OFFLINE=1` proves no external resolution during the rehearsal, not universal air-gapped installability. Preserve actionable failure output in task evidence and do not rerun broad suites after unchanged passing results.
