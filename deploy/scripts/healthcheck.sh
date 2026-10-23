#!/usr/bin/env bash
set -Eeuo pipefail

health_url="${1:?uso: healthcheck.sh https://api.exemplo.com/health}"
for attempt in {1..20}; do
  if curl --fail --silent --show-error --max-time 5 "$health_url" | grep -q '"status":"ok"'; then
    echo "Healthcheck aprovado: $health_url"
    exit 0
  fi
  sleep 3
done
echo "Healthcheck falhou após 20 tentativas: $health_url" >&2
exit 1

