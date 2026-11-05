#!/usr/bin/env bash
# Nightly database backup for ScorePath.
#   ./deploy/backup.sh                      # backs up to /mnt/media/backups/scorepath
#   BACKUP_DIR=/some/other/place ./deploy/backup.sh
# Keeps the newest 14 backups. Restore instructions are in INSTALL.md.
set -euo pipefail

cd "$(dirname "$0")/.."
BACKUP_DIR="${BACKUP_DIR:-/mnt/media/backups/scorepath}"
KEEP="${KEEP:-14}"
mkdir -p "$BACKUP_DIR"

stamp="$(date +%Y%m%d-%H%M%S)"
out="$BACKUP_DIR/scorepath-$stamp.sql.gz"
tmp="$out.partial"

# pg_dump runs inside the db container using the container's own credentials.
docker compose exec -T db sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" --no-owner' | gzip > "$tmp"

# A real dump is never this small; refuse to keep an empty or broken file.
if [ "$(stat -c %s "$tmp")" -lt 2000 ]; then
  rm -f "$tmp"
  echo "Backup looks empty; nothing saved." >&2
  exit 1
fi
mv "$tmp" "$out"
chmod 600 "$out"

# Delete all but the newest $KEEP backups.
ls -1t "$BACKUP_DIR"/scorepath-*.sql.gz | tail -n +"$((KEEP + 1))" | xargs -r rm -f --
echo "Saved $out"
