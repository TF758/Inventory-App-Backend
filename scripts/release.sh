#!/usr/bin/env bash
set -Eeuo pipefail

environment_name="${1:-}"

case "$environment_name" in
  development)
    overlay="docker-compose.development.yml"
    default_port="8000"
    ;;
  staging)
    overlay="docker-compose.staging.yml"
    default_port="8001"
    ;;
  production)
    overlay="docker-compose.production.yml"
    default_port="8000"
    ;;
  *)
    echo "Usage: $0 {development|staging|production}" >&2
    exit 2
    ;;
esac

: "${BACKEND_IMAGE:?Set BACKEND_IMAGE to the registry image name.}"
: "${IMAGE_TAG:?Set IMAGE_TAG to an immutable image tag such as sha-<git-sha>.}"

export API_PORT="${API_PORT:-$default_port}"
export CONTAINER_PORT="${CONTAINER_PORT:-8000}"

compose=(
  docker compose
  -f docker-compose.prod.yml
  -f "$overlay"
)

"${compose[@]}" config --quiet
"${compose[@]}" pull api worker beat release
"${compose[@]}" up -d db redis
"${compose[@]}" run --rm release
"${compose[@]}" up -d api worker beat

health_url="http://127.0.0.1:${API_PORT}/health/ready/"

for attempt in $(seq 1 30); do
  if curl --fail --silent --show-error "$health_url" >/dev/null; then
    echo "Deployment is ready: $health_url"
    "${compose[@]}" ps
    exit 0
  fi

  echo "Waiting for readiness (${attempt}/30)..."
  sleep 5
done

"${compose[@]}" logs --tail=200 api worker beat >&2

echo "Deployment did not become ready: $health_url" >&2
exit 1
