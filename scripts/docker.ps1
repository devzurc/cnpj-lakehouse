param([ValidateSet('start','run','wait','status','logs','verify','stop','demo')][string]$Command = 'start')
# docker.ps1 — equivalente Windows do docker.sh.
$ErrorActionPreference = 'Stop'
switch ($Command) {
  'start' {
    docker compose -f docker-compose.yml up -d --force-recreate prefect-server prefect-runner dashboard
    Write-Host 'Prefect UI: http://127.0.0.1:4200/'
    Write-Host 'Deployment: cnpj-lakehouse/monthly-ingest'
    Write-Host 'Gold dashboard: http://127.0.0.1:8501/'
  }
  'run' { Write-Host 'Na Prefect UI, execute cnpj-lakehouse/monthly-ingest (amostra via .env, padrão 10.000, fonte remota).' }
  'demo' {
    docker compose -f docker-compose.yml run --rm bootstrap
    docker compose -f docker-compose.yml run --rm bootstrap bash scripts/docker_wait.sh
  }
  'verify' { docker compose -f docker-compose.yml --profile tools run --rm verify }
  'status' { docker compose -f docker-compose.yml ps }
  'logs' { docker compose -f docker-compose.yml logs --tail=80 }
  'stop' { docker compose -f docker-compose.yml stop }
  'wait' { docker compose -f docker-compose.yml run --rm bootstrap bash scripts/docker_wait.sh }
}
