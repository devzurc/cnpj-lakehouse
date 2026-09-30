#!/usr/bin/env bash
set -euo pipefail

# prefect_local.sh — processos isolados do plano de controle Prefect.
# server : API + UI em 127.0.0.1:4200 (SQLite em $CNPJ_LAKEHOUSE_RUNTIME_ROOT/prefect).
# serve  : worker que registra e executa cnpj-lakehouse/monthly-ingest.
# status : health da UI/API e inspeção do deployment.

command_name="${1:-}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/runtime.sh
source "$script_dir/lib/runtime.sh"

runtime_root="$(cnpj_default_runtime_root)"

case "$runtime_root" in
  /mnt/*)
    echo "CNPJ_LAKEHOUSE_RUNTIME_ROOT must use Linux-native storage, not /mnt: $runtime_root" >&2
    exit 2
    ;;
esac

export CNPJ_LAKEHOUSE_RUNTIME_ROOT="$runtime_root"
export PREFECT_HOME="$runtime_root/prefect"
export PREFECT_API_URL="http://127.0.0.1:4200/api"
export PREFECT_UI_API_URL="http://127.0.0.1:4200/api"
# Prefect's SQLite backend already uses WAL; give connections the same bounded
# wait as its busy timeout when a local operator performs a supported inspection.
export PREFECT_API_DATABASE_TIMEOUT="${PREFECT_API_DATABASE_TIMEOUT:-60}"
export PREFECT_API_DATABASE_CONNECTION_TIMEOUT="${PREFECT_API_DATABASE_CONNECTION_TIMEOUT:-60}"
mkdir -p -m 700 "$PREFECT_HOME"
chmod 700 "$PREFECT_HOME"

case "$command_name" in
  server)
    exec uv run prefect server start --host 127.0.0.1 --port 4200
    ;;
  serve)
    curl --fail --silent --show-error "$PREFECT_API_URL/health" >/dev/null
    exec uv run cnpj-lakehouse-serve
    ;;
  status)
    curl --fail --silent --show-error "http://127.0.0.1:4200/" >/dev/null
    echo "Dashboard: healthy (http://127.0.0.1:4200/)"
    curl --fail --silent --show-error "$PREFECT_API_URL/health" >/dev/null
    echo "API: healthy ($PREFECT_API_URL/health)"
    uv run prefect deployment inspect "cnpj-lakehouse/monthly-ingest" >/dev/null
    echo "Deployment: cnpj-lakehouse/monthly-ingest exists"
    uv run prefect flow-run ls --limit 5
    ;;
  *)
    echo "Usage: $0 {server|serve|status}" >&2
    exit 2
    ;;
esac
