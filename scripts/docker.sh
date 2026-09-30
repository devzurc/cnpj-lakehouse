#!/usr/bin/env bash
set -euo pipefail

# docker.sh — mesma aplicação via Docker Compose (sem Python no host).
# start  : API Prefect, runner monthly-ingest e dashboard em loopback.
# run    : instrução para disparar cnpj-lakehouse/monthly-ingest na UI.
# demo   : ensaio sintético (bootstrap) — não é o caminho de entrega.
# wait   : espera o flow run criado pelo bootstrap.
# verify : verificadores Bronze/Warehouse/contrato no warehouse do volume.
# status / logs / stop : operação dos containers; stop preserva volumes.

command_name="${1:-start}"
docker_bin="docker"
if ! docker version >/dev/null 2>&1; then
  if command -v docker.exe >/dev/null 2>&1 && docker.exe version >/dev/null 2>&1; then
    docker_bin="docker.exe"
  else
  cat >&2 <<'EOF'
Docker CLI não encontrado neste terminal.
Instale/inicie Docker Desktop e habilite a integração com sua distribuição WSL,
ou instale Docker Engine no Linux. Guias: https://docs.docker.com/desktop/setup/install/
Depois confirme com: docker --version && docker compose version
EOF
  exit 127
  fi
fi
compose=("$docker_bin" compose -f docker-compose.yml)
case "$command_name" in
  start)
    "${compose[@]}" up -d --force-recreate prefect-server prefect-runner dashboard
    echo "Prefect UI: http://127.0.0.1:4200/"
    echo "Deployment: cnpj-lakehouse/monthly-ingest"
    echo "Gold dashboard: http://127.0.0.1:8501/"
    ;;
  run) echo "Na Prefect UI, execute cnpj-lakehouse/monthly-ingest (amostra via .env, padrão 10.000, fonte remota)." ;;
  demo)
    "${compose[@]}" run --rm bootstrap
    "${compose[@]}" run --rm bootstrap bash scripts/docker_wait.sh
    ;;
  wait) "${compose[@]}" run --rm bootstrap bash scripts/docker_wait.sh ;;
  status) "${compose[@]}" ps ;;
  logs) "${compose[@]}" logs --tail="${CNPJ_LAKEHOUSE_LOG_LINES:-80}" ;;
  verify) "${compose[@]}" --profile tools run --rm verify ;;
  stop) "${compose[@]}" stop ;;
  *) echo "Usage: $0 {start|run|demo|wait|status|logs|verify|stop}" >&2; exit 2 ;;
esac
