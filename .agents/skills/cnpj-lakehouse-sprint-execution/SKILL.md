---
name: cnpj-lakehouse-sprint-execution
description: Execute a CNPJ Lakehouse sprint task when task status, dependencies, acceptance criteria, and evidence must remain synchronized. Do not use for unrelated coding work.
---

# Sprint execution

Read `project/active-sprint.md`, `project/backlog.md`, `project/delivery-history.md`, and the specifications named by remaining work before changing code or documentation.

Only begin `ready` or `in_progress` backlog items, and confirm every dependency is `done`. If an explicit user request introduces new work after recorded items are complete, add a bounded backlog row and update `active-sprint.md` before implementation. Do not recreate `project/sprints/*/tasks/` (ADR-016). Keep one owner per worktree area and preserve unrelated user changes.

Keep implementation inside the item scope. Amend an ADR before making a new material decision; record only behavior-changing, verified discoveries in `project/knowledge/verified-insights.md`. Treat independent reviewer findings as input: classify them as remediated, documented exception, tracked follow-up, or out of scope before closing the item.

Run the smallest relevant check first, followed by every verification named by the work. Record commands and observable results without local secrets or transient absolute paths. Update backlog, active sprint, delivery history, checkpoint, and changelog when their truth changes; do not mark an item `done` while a mandatory check fails.

Treat local completion and external delivery as separate checkpoints. Creating repositories, pushing commits, opening or merging PRs, publishing releases, and running cloud commands require explicit authorization immediately before the mutation. Record a pending external action instead of implying that a local pass means it occurred.
