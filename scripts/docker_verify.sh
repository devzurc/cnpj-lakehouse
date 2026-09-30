#!/usr/bin/env bash
set -euo pipefail
database="${CNPJ_LAKEHOUSE_DUCKDB_PATH:-/runtime/run/warehouse/cnpj_lakehouse.duckdb}"
uv run --no-sync python scripts/verify_bronze.py --database "$database" --expect-period 202601 --expect-sample-size 3
uv run --no-sync python scripts/verify_warehouse.py --database "$database" --expect-period 202601 --expect-reference-date 2026-01-31 --expect-sample-size 3
uv run --no-sync python scripts/verify_analytics_contract.py --database "$database" --expect-reference-date 2026-01-31
uv run --no-sync python scripts/inspect_local_warehouse.py --database "$database"
uv run --no-sync cnpj-lakehouse plan --source-period 202601 --output-path "$(dirname "$(dirname "$database")")" --sample-size 3 \
  | uv run --no-sync python -c "import json,sys; p=json.load(sys.stdin); assert p['action']=='reuse_bronze', p; assert p['archives']['required']==32; assert p['archives']['needs_download'] is False"
