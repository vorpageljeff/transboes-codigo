#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

backup_file="${1:?uso: restore.sh /caminho/backup.dump.gz}"
app_dir="${TRANSBOES_APP_DIR:-/opt/innovagro/apps/transboes}"
test -f "$backup_file"
cd "$app_dir"
set -a
source .env
set +a
gzip -dc "$backup_file" | docker compose --env-file .env -f deploy/docker-compose.production.yml exec -T db \
  pg_restore --exit-on-error --single-transaction --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"
echo "Restore concluído. Execute migrations e valide a aplicação."
