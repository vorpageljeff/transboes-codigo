#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
app_dir="${TRANSBOES_APP_DIR:-/opt/innovagro/apps/transboes}"
backup_dir="${BACKUP_DIR:-/opt/innovagro/backups/transboes}"
mkdir -p "$backup_dir/daily" "$backup_dir/weekly"
cd "$app_dir"
set -a
source .env
set +a
timestamp=$(date +%Y-%m-%d_%H%M%S)
backup_temp=$(mktemp "$backup_dir/daily/.pending.XXXXXX")
trap 'rm -f "$backup_temp"' EXIT
compose=(docker compose --env-file .env -f deploy/docker-compose.production.yml)
"${compose[@]}" exec -T db pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc < /dev/null | gzip > "$backup_temp"
gzip -t "$backup_temp"
gzip -dc "$backup_temp" | "${compose[@]}" exec -T db pg_restore --list > /dev/null
if [ "$(id -u)" = "0" ]; then
  chown --reference="$backup_dir" "$backup_temp"
fi
mv "$backup_temp" "$backup_dir/daily/transboes_${timestamp}.dump.gz"
if [ "$(date +%u)" = "7" ]; then
  cp -p "$backup_dir/daily/transboes_${timestamp}.dump.gz" "$backup_dir/weekly/"
fi
python3 - "$backup_dir" <<'PY'
import sys
from pathlib import Path
for directory, keep in [('daily',7),('weekly',4)]:
    files=sorted((Path(sys.argv[1])/directory).glob('*.dump.gz'), reverse=True)
    for file in files[keep:]: file.unlink()
PY
echo "Backup validado: $backup_dir/daily/transboes_${timestamp}.dump.gz"
