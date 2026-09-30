#!/usr/bin/env bash
set -euo pipefail
id_file="${CNPJ_LAKEHOUSE_RUNTIME_ROOT:-/runtime}/last-flow-run-id"
[[ -s "$id_file" ]] || { echo "nenhum flow_run_id conhecido" >&2; exit 1; }
run_id="$(<"$id_file")"
for _ in $(seq 1 180); do
  state="$(python - "$run_id" <<'PY'
import json, sys, urllib.request
run_id = sys.argv[1]
with urllib.request.urlopen(f"http://prefect-server:4200/api/flow_runs/{run_id}", timeout=5) as response:
    print(json.load(response)["state"]["type"])
PY
  )"
  echo "flow_run_id=$run_id state=$state"
  case "$state" in
    COMPLETED) exit 0 ;;
    FAILED|CRASHED|CANCELLED|CANCELLING) exit 1 ;;
  esac
  sleep 2
done
echo "timeout aguardando flow run $run_id" >&2
exit 1
