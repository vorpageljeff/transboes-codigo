#!/usr/bin/env bash
set -Eeuo pipefail
app_dir="${TRANSBOES_APP_DIR:-/opt/innovagro/apps/transboes}"
cd "$app_dir"
exec 9> .deploy.lock
flock -n 9 || { echo 'Já existe um deploy em andamento' >&2; exit 1; }
set -a
source .env
set +a
previous_commit=$(git rev-parse HEAD)
previous_image=$(docker inspect transboes-api-1 --format '{{.Image}}')
target_commit="${1:-origin/main}"
switched=false
persist_image() {
  python3 - <<'PY'
import os
from pathlib import Path
p=Path('.env')
lines=[line for line in p.read_text().splitlines() if not line.startswith('APP_IMAGE=')]
lines.append('APP_IMAGE='+os.environ['APP_IMAGE'])
p.write_text('\n'.join(lines)+'\n')
p.chmod(0o600)
PY
}
rollback() {
  local result=$?
  trap - ERR
  if [ "$switched" = true ]; then
    export APP_IMAGE="$previous_image"
    git checkout --detach "$previous_commit"
    persist_image
    docker compose --env-file .env -f deploy/docker-compose.production.yml up -d --no-build api
    echo "Rollback da imagem executado; valide o banco e os fluxos. Migration não foi revertida automaticamente." >&2
  else
    git checkout --detach "$previous_commit"
  fi
  exit "$result"
}
trap rollback ERR
git fetch --prune origin
git checkout --detach "$target_commit"
export APP_IMAGE="transboes-api:$(git rev-parse HEAD)"
docker compose --env-file .env -f deploy/docker-compose.production.yml build api
deploy/scripts/backup.sh
docker compose --env-file .env -f deploy/docker-compose.production.yml run --rm -T -e DATABASE_URL="$MIGRATION_DATABASE_URL" api alembic upgrade head < /dev/null
switched=true
docker compose --env-file .env -f deploy/docker-compose.production.yml up -d --no-build
deploy/scripts/healthcheck.sh "https://${API_DOMAIN}/health"
persist_image
trap - ERR
echo "Deploy concluído: $(git rev-parse HEAD)"
