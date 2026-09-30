from __future__ import annotations

import subprocess
from pathlib import Path


def test_local_launcher_is_executable_and_covers_operator_commands() -> None:
    script = Path("scripts/local.sh")
    assert script.is_file()
    assert script.stat().st_mode & 0o111
    subprocess.run(["bash", "-n", str(script)], check=True)
    subprocess.run(["bash", "-n", "scripts/lib/runtime.sh"], check=True)
    subprocess.run(["bash", "-n", "scripts/prefect_local.sh"], check=True)
    text = script.read_text(encoding="utf-8")
    runtime_lib = Path("scripts/lib/runtime.sh").read_text(encoding="utf-8")
    for command in ("start)", "run)", "wait)", "status)", "logs)", "stop)"):
        assert command in text
    assert "CNPJ_LAKEHOUSE_SAMPLE_SIZE" in text
    assert "CNPJ_LAKEHOUSE_PARALLEL_JOBS" in text
    assert "parallel_jobs=" in text
    assert "load_operator_env" in text
    assert 'load_operator_env "$repo_root/.env"' in text
    assert 'source "$repo_root/.env"' not in text
    assert 'source "$script_dir/lib/runtime.sh"' in text
    assert "cnpj-lakehouse" in runtime_lib
    assert "cnpj-lakehouse/monthly-ingest" in text
    assert "create-demo-sources" not in text
    assert "cnpj-lakehouse-dashboard" in text
    assert "/mnt/*" in text
    assert r'output_path=\"$runtime_root/run\"' in text
    assert "lakehouse-" in text
    assert "official-" not in text


def test_makefile_and_env_example_use_runtime_run_layout() -> None:
    makefile = Path("Makefile").read_text(encoding="utf-8")
    env_example = Path(".env.example").read_text(encoding="utf-8")
    assert "CNPJ_LAKEHOUSE_RUNTIME_ROOT" in makefile
    assert "$(CNPJ_LAKEHOUSE_RUNTIME_ROOT)/run" in makefile
    assert "CNPJ_LAKEHOUSE_SOURCE_PERIOD" in makefile
    assert "CNPJ_LAKEHOUSE_DUCKDB_PATH=/home/seu-usuario" in env_example
    assert "export CNPJ_LAKEHOUSE" not in env_example
    assert "CNPJ_LAKEHOUSE_SAMPLE_SIZE" in env_example
    assert "CNPJ_LAKEHOUSE_PARALLEL_JOBS" in env_example
    assert "cnpj-lakehouse" in makefile
    assert "uv run cnpj-lakehouse" in makefile
