#!/usr/bin/env bash
set -Eeuo pipefail

environment_name="${1:-}"
backup_root="${BACKUP_ROOT:-./backups/$environment_name}"

case "$environment_name" in
  development) overlay="docker-compose.development.yml" ;;
  staging) overlay="docker-compose.staging.yml" ;;
  production) overlay="docker-compose.production.yml" ;;
  *)
    echo "Usage: $0 {development|staging|production}" >&2
    exit 2
    ;;
esac

compose=(
  docker compose
  -f docker-compose.prod.yml
  -f "$overlay"
)

"${compose[@]}" config --quiet
"${compose[@]}" up -d db

mkdir -p "$backup_root"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
backup_file="$backup_root/inventory-${environment_name}-${timestamp}.dump"
temporary_file="${backup_file}.partial"

cleanup() {
  rm -f "$temporary_file"
}
trap cleanup EXIT

"${compose[@]}" exec -T db sh -Eeuc '
  pg_dump \
    --username="$POSTGRES_USER" \
    --dbname="$POSTGRES_DB" \
    --format=custom \
    --no-owner \
    --no-acl
' > "$temporary_file"

if [[ ! -s "$temporary_file" ]]; then
  echo "Backup was empty; refusing to keep it." >&2
  exit 1
fi

mv "$temporary_file" "$backup_file"
trap - EXIT

sha256sum "$backup_file" > "${backup_file}.sha256"

echo "Backup created: $backup_file"
echo "Checksum: ${backup_file}.sha256"
