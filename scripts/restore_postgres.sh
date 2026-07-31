#!/usr/bin/env bash
set -Eeuo pipefail

environment_name="${1:-}"
backup_file="${2:-}"

case "$environment_name" in
  development) overlay="docker-compose.development.yml" ;;
  staging) overlay="docker-compose.staging.yml" ;;
  production) overlay="docker-compose.production.yml" ;;
  *)
    echo "Usage: CONFIRM_RESTORE=YES $0 {development|staging|production} <backup.dump>" >&2
    exit 2
    ;;
esac

if [[ -z "$backup_file" || ! -f "$backup_file" ]]; then
  echo "Backup file not found: $backup_file" >&2
  exit 2
fi

if [[ "${CONFIRM_RESTORE:-}" != "YES" ]]; then
  echo "Restore blocked. Re-run with CONFIRM_RESTORE=YES." >&2
  exit 3
fi

if [[ -f "${backup_file}.sha256" ]]; then
  sha256sum --check "${backup_file}.sha256"
fi

compose=(
  docker compose
  -f docker-compose.prod.yml
  -f "$overlay"
)

"${compose[@]}" config --quiet
"${compose[@]}" up -d db

cat "$backup_file" | "${compose[@]}" exec -T db sh -Eeuc '
  pg_restore \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --clean \
    --if-exists \
    --no-owner \
    --no-acl \
    --exit-on-error
'

echo "Restore completed from: $backup_file"
