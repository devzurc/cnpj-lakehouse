#!/usr/bin/env bash
set -euo pipefail
# Ensaio sintético no volume Docker — não usa o espelho público.
runtime_root="${CNPJ_LAKEHOUSE_RUNTIME_ROOT:-/runtime}"
source_dir="$runtime_root/demo-source"
deployment="cnpj-lakehouse/monthly-ingest"
mkdir -p -m 700 "$runtime_root"
if [[ ! -f "$source_dir/DEMO_ONLY.json" ]]; then
  mkdir -p -m 700 "$source_dir"
  rmdir "$source_dir" 2>/dev/null || { echo "fonte existente sem DEMO_ONLY.json: $source_dir" >&2; exit 1; }
  uv run --no-sync cnpj-lakehouse create-demo-sources --output-path "$source_dir"
fi
for _ in $(seq 1 90); do
  if uv run --no-sync prefect deployment inspect "$deployment" >/dev/null 2>&1; then break; fi
  sleep 1
done
uv run --no-sync prefect deployment inspect "$deployment" >/dev/null
run_output="$runtime_root/last-run-create.log"
uv run --no-sync prefect deployment run "$deployment" \
  --flow-run-name "docker-synthetic-$(date +%Y%m%d%H%M%S)" \
  -p "source_dir=\"$source_dir\"" -p 'sample_size=3' -p 'source_period="202601"' \
  -p 'reference_date="2026-01-31"' -p "output_path=\"$runtime_root/run\"" \
  -p 'full_refresh=false' | tee "$run_output"
grep -Eo '[0-9a-f]{8}-[0-9a-f-]{27,}' "$run_output" | tail -1 > "$runtime_root/last-flow-run-id" || true
