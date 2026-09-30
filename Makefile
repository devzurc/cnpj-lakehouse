.PHONY: validate-project install lint test dbt-build run-sample

CNPJ_LAKEHOUSE_RUNTIME_ROOT ?= $(HOME)/.local/share/cnpj-lakehouse
CNPJ_LAKEHOUSE_DUCKDB_PATH ?= $(CNPJ_LAKEHOUSE_RUNTIME_ROOT)/run/warehouse/cnpj_lakehouse.duckdb
export CNPJ_LAKEHOUSE_RUNTIME_ROOT
export CNPJ_LAKEHOUSE_DUCKDB_PATH

validate-project:
	uv run python scripts/validate_project_structure.py

install:
	uv sync --all-groups --locked

lint:
	uv run ruff check .

test:
	uv run pytest -q

dbt-build:
	@test -n "$(CNPJ_LAKEHOUSE_SOURCE_PERIOD)" && test -n "$(CNPJ_LAKEHOUSE_SAMPLE_ID)" && test -n "$(CNPJ_LAKEHOUSE_REFERENCE_DATE)" || ( \
		echo "dbt-build requires CNPJ_LAKEHOUSE_SOURCE_PERIOD, CNPJ_LAKEHOUSE_SAMPLE_ID and CNPJ_LAKEHOUSE_REFERENCE_DATE" >&2; exit 2)
	uv run python -m dbt.cli.main build --project-dir dbt --profiles-dir dbt

run-sample:
	uv run cnpj-lakehouse run --source-period 202601 --output-path $(CNPJ_LAKEHOUSE_RUNTIME_ROOT)/run
