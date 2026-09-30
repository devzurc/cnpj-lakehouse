from __future__ import annotations

import subprocess
from pathlib import Path


def test_docker_compose_declares_local_services_and_named_volumes() -> None:
    compose = Path("docker-compose.yml").read_text(encoding="utf-8")
    docker_script = Path("scripts/docker.sh").read_text(encoding="utf-8")
    for service in ("prefect-server:", "prefect-runner:", "dashboard:", "bootstrap:", "verify:"):
        assert service in compose
    assert '"127.0.0.1:4200:4200"' in compose
    assert '"127.0.0.1:8501:8501"' in compose
    assert "name: cnpj_lakehouse_runtime" in compose
    assert "name: cnpj_lakehouse_prefect_state" in compose
    assert "PREFECT_UI_API_URL: /api" in compose
    assert "PREFECT_API_URL: http://prefect-server:4200/api" in compose
    assert compose.count("prefect_state:/prefect") == 1
    dockerfile = Path("Dockerfile").read_text(encoding="utf-8")
    assert "PREFECT_UI_API_URL=/api" in dockerfile
    assert "PREFECT_UI_API_URL=http://prefect-server:4200/api" not in dockerfile
    assert "PREFECT_UI_API_URL=http://127.0.0.1:4200/api" not in dockerfile
    assert "CNPJ_LAKEHOUSE_DUCKDB_PATH: /runtime/run/warehouse/cnpj_lakehouse.duckdb" in compose
    assert "cnpj-lakehouse-serve" in compose
    assert "cnpj-lakehouse/monthly-ingest" in docker_script
    assert 'up -d --force-recreate prefect-server prefect-runner dashboard' in docker_script
    assert "up -d --force-recreate prefect-server prefect-runner dashboard" in Path("scripts/docker.ps1").read_text(encoding="utf-8")
    assert "CNPJ_LAKEHOUSE_SAMPLE_SIZE: ${CNPJ_LAKEHOUSE_SAMPLE_SIZE:-10000}" in compose
    assert "CNPJ_LAKEHOUSE_PARALLEL_JOBS: ${CNPJ_LAKEHOUSE_PARALLEL_JOBS:-1}" in compose
    assert '"${compose[@]}" run --rm bootstrap' in docker_script
    assert '"${compose[@]}" run --rm bootstrap bash scripts/docker_wait.sh' in docker_script
    assert 'docker_bin="docker"' in docker_script
    assert 'docker_bin="docker.exe"' in docker_script
    verify = Path("scripts/docker_verify.sh").read_text(encoding="utf-8")
    assert "cnpj-lakehouse plan --source-period 202601" in verify
    assert "reuse_bronze" in verify


def test_docker_operator_scripts_have_valid_shell_syntax() -> None:
    for name in ("docker.sh", "docker_bootstrap.sh", "docker_wait.sh", "docker_verify.sh"):
        script = Path("scripts") / name
        assert script.stat().st_mode & 0o111
        subprocess.run(["bash", "-n", str(script)], check=True)


def test_docker_ps1_demo_waits_like_bash() -> None:
    powershell = Path("scripts/docker.ps1").read_text(encoding="utf-8")
    assert "'demo' {" in powershell
    demo_block = powershell.split("'demo' {", 1)[1].split("}", 1)[0]
    assert "run --rm bootstrap" in demo_block
    assert "scripts/docker_wait.sh" in demo_block
