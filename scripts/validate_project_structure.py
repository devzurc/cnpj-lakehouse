"""Validate the CNPJ Lakehouse delivery scaffold without external dependencies."""

from __future__ import annotations

import re
import subprocess
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SPRINT_ROOT = ROOT / "project" / "sprints"
VALID_SPRINT_STATUSES = {"planned", "in_progress", "blocked", "complete"}

REQUIRED_PATHS = (
    "AGENTS.md",
    "CHANGELOG.md",
    ".gitignore",
    ".env.example",
    "project/active-sprint.md",
    "project/backlog.md",
    "project/delivery-history.md",
    "project/checkpoints/delivery-readiness.md",
    "project/decisions/ADR-016-delivery-repository-shape.md",
    "project/requirements/challenge-requirements.md",
    "project/requirements/acceptance-matrix.md",
    "project/specifications/architecture.md",
    "project/specifications/source-contracts.md",
    "project/specifications/sampling-and-bronze.md",
    "project/specifications/data-model.md",
    "project/specifications/analytics-consumption.md",
    "project/specifications/dbt-project.md",
    "project/specifications/prefect-flow.md",
    "project/specifications/quality-strategy.md",
    "project/specifications/local-execution.md",
    "project/specifications/bigquery-finops.md",
    "project/specifications/security-and-data-governance.md",
    "project/specifications/ai-governance.md",
    ".codex/rules/remote-actions.rules",
)

FORBIDDEN_PATHS = ("docs/delivery-handoff.md",)

SKILLS = (
    "cnpj-lakehouse-sprint-execution",
    "cnpj-lakehouse-ingestion",
    "cnpj-lakehouse-dbt-development",
    "cnpj-lakehouse-quality-gates",
    "cnpj-lakehouse-finops-documentation",
    "cnpj-lakehouse-security-governance",
    "cnpj-lakehouse-workflow-audit",
)

AGENTS = (
    "architecture-reviewer",
    "dbt-reviewer",
    "data-quality-reviewer",
    "finops-reviewer",
    "security-governance-reviewer",
    "repository-hygiene-reviewer",
)

REQUIRED_REMOTE_RULE_PREFIXES = (
    'pattern = ["git", "push"]',
    'pattern = ["gh", "repo",',
    'pattern = ["gh", "pr",',
    'pattern = ["gh", "release",',
    'pattern = [["gcloud", "bq", "gsutil"]]',
)

REQUIRED_GITIGNORE_PATTERNS = (
    ".env",
    "*.duckdb",
    "dbt/target/",
    "dbt/dbt_packages/",
    "dbt/logs/",
    "dbt/.user.yml",
)


def frontmatter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---\n"):
        raise ValueError("missing YAML frontmatter")
    _, raw, _ = text.split("---\n", 2)
    values: dict[str, str] = {}
    for line in raw.splitlines():
        if not line or line.lstrip().startswith("#") or ":" not in line:
            continue
        key, value = line.split(":", 1)
        values[key.strip()] = value.strip().strip('"')
    return values


def prohibited_tracked_path(path: str) -> bool:
    return (
        path == ".env"
        or path.endswith(("/.env", ".duckdb"))
        or path.startswith(("dbt/target/", "dbt/logs/", "dbt/dbt_packages/"))
        or path == "dbt/.user.yml"
        or ".duckdb." in path
        or any(part in {".venv", ".pytest_cache", ".ruff_cache", "__pycache__"} for part in Path(path).parts)
    )


def tracked_files() -> list[str]:
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=ROOT,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return []
    return [path for path in result.stdout.split("\0") if path]


def leftover_sprint_tasks() -> list[str]:
    if not SPRINT_ROOT.is_dir():
        return []
    return sorted(
        str(path.relative_to(ROOT)) for path in SPRINT_ROOT.glob("*/tasks/*/README.md")
    )


def backlog_open_items(text: str) -> list[tuple[str, str]]:
    items: list[tuple[str, str]] = []
    for line in text.splitlines():
        match = re.search(r"\|\s*(S\d{2}-\d{2})\s*\|.+\|\s*`([^`]+)`\s*\|", line)
        if match:
            items.append((match.group(1), match.group(2)))
    return items


def main() -> int:
    errors: list[str] = []

    for relative_path in REQUIRED_PATHS:
        if not (ROOT / relative_path).is_file():
            errors.append(f"missing required file: {relative_path}")

    for relative_path in FORBIDDEN_PATHS:
        if (ROOT / relative_path).is_file():
            errors.append(f"obsolete handoff file must be merged into README: {relative_path}")

    leftover = leftover_sprint_tasks()
    if leftover:
        errors.append(
            "historical sprint task files must not remain: " + ", ".join(leftover[:8])
            + ("…" if len(leftover) > 8 else "")
        )

    history_text = (ROOT / "project/delivery-history.md").read_text(encoding="utf-8")
    for marker in ("S12-01", "blocked", "S18", "ADR-016"):
        if marker not in history_text:
            errors.append(f"delivery history missing marker: {marker}")

    backlog_text = (ROOT / "project/backlog.md").read_text(encoding="utf-8")
    open_items = backlog_open_items(backlog_text)
    if not any(task_id == "S12-01" and status == "blocked" for task_id, status in open_items):
        errors.append("backlog must keep S12-01 as `blocked`")
    done_legacy = [task_id for task_id, status in open_items if status == "done"]
    if done_legacy:
        errors.append(f"backlog must not list completed historical tasks: {', '.join(done_legacy)}")

    active_sprint_path = ROOT / "project/active-sprint.md"
    active_sprint_text = active_sprint_path.read_text(encoding="utf-8")
    try:
        active_sprint = frontmatter(active_sprint_path)
    except ValueError as error:
        errors.append(f"project/active-sprint.md: {error}")
        active_sprint = {}
    active_sprint_id = active_sprint.get("sprint")
    active_sprint_status = active_sprint.get("status")
    if active_sprint_status not in VALID_SPRINT_STATUSES:
        errors.append(f"active sprint has invalid status: {active_sprint_status}")
    if not active_sprint_id:
        errors.append("active sprint must name a sprint id")
    elif active_sprint_id not in history_text:
        errors.append(f"delivery history does not mention {active_sprint_id}")

    changelog_text = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if "## [Não publicado]" not in changelog_text:
        errors.append("CHANGELOG.md must retain a Não publicado section")

    checkpoint_text = (ROOT / "project/checkpoints/delivery-readiness.md").read_text(
        encoding="utf-8"
    )
    for marker in ("APROVADO", "PENDENTE", "origin"):
        if marker not in checkpoint_text:
            errors.append(f"delivery checkpoint missing marker: {marker}")

    if active_sprint_status == "in_progress":
        sprint_number = re.fullmatch(r"sprint-(\d+)(?:-.+)?", active_sprint_id or "")
        sprint_label = f"Sprint {sprint_number.group(1)}" if sprint_number else active_sprint_id
        if sprint_label not in checkpoint_text:
            errors.append(f"delivery checkpoint does not mention active {sprint_label}")
        if sprint_label not in changelog_text:
            errors.append(f"CHANGELOG.md does not mention active {sprint_label}")
    elif active_sprint_status == "complete":
        if "S12-01" not in active_sprint_text and "blocked" not in active_sprint_text:
            errors.append("complete active-sprint must still record S12-01 as blocked")

    for skill in SKILLS:
        skill_root = ROOT / ".agents/skills" / skill
        skill_file = skill_root / "SKILL.md"
        metadata_file = skill_root / "agents/openai.yaml"
        if not skill_file.is_file() or not metadata_file.is_file():
            errors.append(f"skill {skill}: missing SKILL.md or agents/openai.yaml")
            continue
        try:
            metadata = frontmatter(skill_file)
        except ValueError as error:
            errors.append(f"skill {skill}: {error}")
            continue
        if metadata.get("name") != skill or not metadata.get("description"):
            errors.append(f"skill {skill}: invalid name or missing description")
        interface_text = metadata_file.read_text(encoding="utf-8")
        if f"${skill}" not in interface_text:
            errors.append(f"skill {skill}: default prompt must explicitly invoke the skill")
        if "allow_implicit_invocation: true" not in interface_text:
            errors.append(f"skill {skill}: implicit invocation policy must remain enabled")

    for agent_name in AGENTS:
        path = ROOT / ".codex/agents" / f"{agent_name}.toml"
        if not path.is_file():
            errors.append(f"missing custom agent: {agent_name}")
            continue
        try:
            config = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            errors.append(f"agent {agent_name}: invalid TOML ({error})")
            continue
        if config.get("name") != agent_name:
            errors.append(f"agent {agent_name}: unexpected name")
        if config.get("sandbox_mode") != "read-only":
            errors.append(f"agent {agent_name}: must be read-only")
        if "do not edit" not in config.get("developer_instructions", "").lower():
            errors.append(f"agent {agent_name}: must explicitly prohibit edits")

    rules = ROOT / ".codex/rules/remote-actions.rules"
    if rules.is_file():
        rules_text = rules.read_text(encoding="utf-8")
        for prefix in REQUIRED_REMOTE_RULE_PREFIXES:
            if prefix not in rules_text:
                errors.append(f"remote action rules missing protected prefix: {prefix}")

    gitignore_text = (ROOT / ".gitignore").read_text(encoding="utf-8")
    for pattern in REQUIRED_GITIGNORE_PATTERNS:
        if pattern not in gitignore_text:
            errors.append(f".gitignore missing runtime exclusion: {pattern}")

    for path in tracked_files():
        if prohibited_tracked_path(path):
            errors.append(f"prohibited generated or sensitive path is tracked: {path}")
        if path.startswith("project/sprints/") and path.endswith("/README.md") and "/tasks/" in path:
            errors.append(f"tracked sprint task file must be removed: {path}")

    if errors:
        print("Project structure validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Project structure valid: delivery-history, {len(SKILLS)} skills, {len(AGENTS)} reviewers."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
