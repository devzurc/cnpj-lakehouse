#!/usr/bin/env bash
set -euo pipefail

# Runtime padrão: $HOME/.local/share/cnpj-lakehouse.
# start  : sobe API Prefect, runner do deployment cnpj-lakehouse/monthly-ingest e dashboard Gold.
# run    : dispara um flow run nomeado lakehouse-AAAAMMDDHHMMSS (amostra via .env/TOML, padrão 10.000).
# wait   : espera o último run conhecido (timeout curto; backfill anual usa scripts/backfill.sh).
# status : health da API, PIDs e URLs.
# logs   : últimas linhas dos logs privados.
# stop   : encerra processos registrados e preserva o runtime.

command_name="${1:-start}"
script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
repo_root="$(cd "$script_dir/.." && pwd)"
load_operator_env() {
  local env_file="$1" line key value
  [[ -f "$env_file" ]] || return 0
  while IFS= read -r line || [[ -n "$line" ]]; do
    [[ -z "$line" || "$line" == \#* ]] && continue
    if [[ "$line" =~ ^(CNPJ_LAKEHOUSE_RUNTIME_ROOT|CNPJ_LAKEHOUSE_DUCKDB_PATH|CNPJ_LAKEHOUSE_SAMPLE_SIZE|CNPJ_LAKEHOUSE_PARALLEL_JOBS|CNPJ_LAKEHOUSE_INGESTION_WORKERS)=([A-Za-z0-9_./:-]+)$ ]]; then
      key="${BASH_REMATCH[1]}"
      value="${BASH_REMATCH[2]}"
      export "$key=$value"
    else
      echo "invalid .env entry; use one supported CNPJ_LAKEHOUSE_* KEY=VALUE setting per line" >&2
      return 2
    fi
  done <"$env_file"
}
load_operator_env "$repo_root/.env"
# shellcheck source=lib/runtime.sh
source "$script_dir/lib/runtime.sh"

runtime_root="$(cnpj_default_runtime_root)"
case "$runtime_root" in
  /mnt/*) echo "CNPJ_LAKEHOUSE_RUNTIME_ROOT must use Linux-native storage: $runtime_root" >&2; exit 2 ;;
esac

export CNPJ_LAKEHOUSE_RUNTIME_ROOT="$runtime_root"
export PREFECT_HOME="$runtime_root/prefect"
export PREFECT_API_URL="${PREFECT_API_URL:-http://127.0.0.1:4200/api}"
export PREFECT_UI_API_URL="$PREFECT_API_URL"
export CNPJ_LAKEHOUSE_DUCKDB_PATH="$(cnpj_default_duckdb_path "$runtime_root")"
pid_dir="$runtime_root/pids"
log_dir="$runtime_root/logs"
mkdir -p -m 700 "$pid_dir" "$log_dir"
chmod 700 "$runtime_root" "$pid_dir" "$log_dir"

server_pid="$pid_dir/server.pid"
runner_pid="$pid_dir/runner.pid"
dashboard_pid="$pid_dir/dashboard.pid"
run_id_file="$runtime_root/last-flow-run-id"
deployment="cnpj-lakehouse/monthly-ingest"

is_alive() { [[ -s "$1" ]] && kill -0 "$(<"$1")" 2>/dev/null; }
wait_for() {
  local label="$1" url="$2" i
  for i in $(seq 1 90); do
    if curl --fail --silent "$url" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  echo "timeout aguardando $label ($url)" >&2
  return 1
}
wait_for_deployment() {
  for _ in $(seq 1 90); do
    if uv run prefect deployment inspect "$deployment" >/dev/null 2>&1; then return 0; fi
    sleep 1
  done
  echo "timeout aguardando deployment $deployment" >&2
  return 1
}
start_process() {
  local name="$1" pid_file="$2" log_file="$3"; shift 3
  if is_alive "$pid_file"; then echo "$name já ativo (PID $(<"$pid_file"))"; return; fi
  nohup "$@" >"$log_file" 2>&1 < /dev/null &
  echo $! >"$pid_file"
  chmod 600 "$pid_file" "$log_file"
  echo "$name iniciado (PID $!)"
}
stop_process() {
  local name="$1" pid_file="$2" pid
  if ! is_alive "$pid_file"; then rm -f "$pid_file"; echo "$name já parado"; return; fi
  pid="$(<"$pid_file")"
  kill "$pid" 2>/dev/null || true
  for _ in $(seq 1 20); do kill -0 "$pid" 2>/dev/null || break; sleep 1; done
  if kill -0 "$pid" 2>/dev/null; then echo "$name não encerrou em 20s (PID $pid)" >&2; return 1; fi
  rm -f "$pid_file"; echo "$name parado"
}
dispatch_run() {
  local output="$log_dir/last-run-create.log"
  local run_args=(
    --flow-run-name "lakehouse-$(date +%Y%m%d%H%M%S)"
    -p "output_path=\"$runtime_root/run\""
    -p 'full_refresh=false'
  )
  if [[ -n "${CNPJ_LAKEHOUSE_SAMPLE_SIZE:-}" ]]; then
    run_args+=(-p "sample_size=${CNPJ_LAKEHOUSE_SAMPLE_SIZE}")
  fi
  if [[ -n "${CNPJ_LAKEHOUSE_PARALLEL_JOBS:-}" ]]; then
    run_args+=(-p "parallel_jobs=${CNPJ_LAKEHOUSE_PARALLEL_JOBS}")
  fi
  if [[ -n "${CNPJ_LAKEHOUSE_INGESTION_WORKERS:-}" ]]; then
    run_args+=(-p "ingestion_workers=${CNPJ_LAKEHOUSE_INGESTION_WORKERS}")
  fi
    CNPJ_LAKEHOUSE_RUNTIME_ROOT="$runtime_root" uv run prefect deployment run "$deployment" \
    "${run_args[@]}" | tee "$output"
  local id
  id="$(grep -Eo '[0-9a-f]{8}-[0-9a-f-]{27,}' "$output" | tail -1 || true)"
  [[ -n "$id" ]] || { echo "não foi possível capturar flow_run_id; consulte $output" >&2; return 1; }
  printf '%s\n' "$id" >"$run_id_file"; chmod 600 "$run_id_file"
  echo "flow_run_id=$id"
}
status() {
  echo "runtime=$runtime_root"
  echo "deployment=$deployment"
  echo "warehouse=$CNPJ_LAKEHOUSE_DUCKDB_PATH"
  curl --fail --silent "$PREFECT_API_URL/health" >/dev/null 2>&1 && echo "Prefect API: healthy" || echo "Prefect API: down"
  for pair in "server:$server_pid" "runner:$runner_pid" "dashboard:$dashboard_pid"; do
    name="${pair%%:*}"; file="${pair#*:}"
    if is_alive "$file"; then echo "$name: active (PID $(<"$file"))"; else echo "$name: stopped"; fi
  done
  [[ -s "$run_id_file" ]] && echo "last_flow_run_id=$(<"$run_id_file")"
  echo "Prefect UI: http://127.0.0.1:4200/"
  echo "Gold dashboard: http://127.0.0.1:8501/"
}
case "$command_name" in
  start)
    if curl --fail --silent "$PREFECT_API_URL/health" >/dev/null 2>&1; then
      echo "Prefect API já ativa"
    else
      start_process "Prefect server" "$server_pid" "$log_dir/server.log" bash scripts/prefect_local.sh server
      wait_for "Prefect API" "$PREFECT_API_URL/health"
    fi
    start_process "Prefect runner" "$runner_pid" "$log_dir/runner.log" bash scripts/prefect_local.sh serve
    wait_for_deployment
    start_process "Gold dashboard" "$dashboard_pid" "$log_dir/dashboard.log" env CNPJ_LAKEHOUSE_DUCKDB_PATH="$CNPJ_LAKEHOUSE_DUCKDB_PATH" uv run cnpj-lakehouse-dashboard
    echo "Dispare o deployment $deployment na UI ou com: $0 run"
    status
    ;;
  run) dispatch_run ;;
  wait)
    [[ -s "$run_id_file" ]] || { echo "nenhum flow_run_id conhecido" >&2; exit 1; }
    id="$(<"$run_id_file")"
    for _ in $(seq 1 180); do
      payload="$(curl --fail --silent "$PREFECT_API_URL/flow_runs/$id")"
      state="$(printf '%s' "$payload" | sed -n 's/.*"type":"\([A-Z_]*\)".*/\1/p')"
      echo "flow_run_id=$id state=${state:-UNKNOWN}"
      case "$state" in COMPLETED|FAILED|CRASHED|CANCELLED|CANCELLING) [[ "$state" == COMPLETED ]] || exit 1; exit 0;; esac
      sleep 2
    done
    echo "timeout aguardando flow run $id" >&2; exit 1
    ;;
  status) status ;;
  logs) tail -n "${CNPJ_LAKEHOUSE_LOG_LINES:-80}" "$log_dir"/*.log 2>/dev/null || true ;;
  stop)
    stop_process "Gold dashboard" "$dashboard_pid" || true
    stop_process "Prefect runner" "$runner_pid" || true
    stop_process "Prefect server" "$server_pid" || true
    echo "runtime preservado em $runtime_root"
    ;;
  *) echo "Usage: $0 {start|run|wait|status|logs|stop}" >&2; exit 2 ;;
esac
