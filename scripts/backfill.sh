#!/usr/bin/env bash
set -euo pipefail

# Runtime padrão: $HOME/.local/share/cnpj-lakehouse-official (nunca o share sintético).
# Uso: ./scripts/backfill.sh [year] [from_period]
# Cada mês: download → amostra 10.000 → Bronze → dbt → verificadores.
# Não usa o share sintético ~/.local/share/cnpj-lakehouse nem /mnt.

year="${1:-2026}"
from_period="${2:-}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=lib/runtime.sh
source "$script_dir/lib/runtime.sh"

demo_root="$HOME/.local/share/cnpj-lakehouse"
runtime_root="$(cnpj_official_runtime_root)"
case "$runtime_root" in
  /mnt/*) echo "CNPJ_LAKEHOUSE_RUNTIME_ROOT must use Linux-native storage: $runtime_root" >&2; exit 2 ;;
esac
if [[ "$runtime_root" == "$demo_root" ]]; then
  echo "backfill must not use the synthetic demo runtime: $runtime_root" >&2
  exit 2
fi

export CNPJ_LAKEHOUSE_RUNTIME_ROOT="$runtime_root"
export CNPJ_LAKEHOUSE_DUCKDB_PATH="$(cnpj_default_duckdb_path "$runtime_root")"
mkdir -p -m 700 "$runtime_root/logs" "$runtime_root/run"
chmod 700 "$runtime_root" "$runtime_root/logs" "$runtime_root/run"

echo "runtime=$runtime_root year=$year from_period=${from_period:-<index>}"
echo "warehouse=$CNPJ_LAKEHOUSE_DUCKDB_PATH"
echo "Prefira este launcher ao local.sh wait (timeout curto de ensaio)."
df -h "$runtime_root" 2>/dev/null || df -h "$(dirname "$runtime_root")"

args=(backfill-year --year "$year" --sample-size 10000 --runtime-root "$runtime_root")
if [[ -n "${CNPJ_LAKEHOUSE_INGESTION_WORKERS:-}" ]]; then
  args+=(--ingestion-workers "$CNPJ_LAKEHOUSE_INGESTION_WORKERS")
fi
if [[ -n "$from_period" ]]; then
  args+=(--from-period "$from_period")
fi
uv run cnpj-lakehouse "${args[@]}"
if [[ -f "$CNPJ_LAKEHOUSE_DUCKDB_PATH" ]]; then
  uv run python scripts/inspect_local_warehouse.py --database "$CNPJ_LAKEHOUSE_DUCKDB_PATH"
fi
echo "Gold dashboard: CNPJ_LAKEHOUSE_DUCKDB_PATH=$CNPJ_LAKEHOUSE_DUCKDB_PATH uv run cnpj-lakehouse-dashboard"
