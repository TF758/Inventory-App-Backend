# Backend deployment runbook

The backend is deployed as one immutable image with separate API, Celery worker,
Celery beat and one-off release processes.

## Environment mapping

| Environment | Compose overlay | Django settings | Env file |
|---|---|---|---|
| Development | `docker-compose.development.yml` | `inventory.settings.dev` | `.env.dev` |
| Staging | `docker-compose.staging.yml` | `inventory.settings.staging` | `.env.staging` |
| Production | `docker-compose.production.yml` | `inventory.settings.prod` | `.env.production` |

Each env file must exist on the deployment host and must not be committed.
Create it from the corresponding `.example` file and replace every placeholder.

## Required image variables

Deployment commands require an immutable image tag:

```bash
export BACKEND_IMAGE=ghcr.io/OWNER/inventory-app-backend/inventory-api
export IMAGE_TAG=sha-FULL_40_CHARACTER_GIT_SHA
```

## Release

The release service runs migrations once and then collects static files. The API,
worker and beat services are started only after the release step succeeds.

```bash
./scripts/release.sh staging
./scripts/release.sh production
```

The script polls `/health/ready/` and fails if PostgreSQL, Redis or migrations are
not ready.

## Shared storage

The Compose deployment uses environment-specific Docker volumes for:

- Uploaded import files (`/app/media`)
- Generated reports (`/app/reports`)
- Collected static files (`/app/staticfiles`)

This resolves API/worker filesystem isolation on one Docker host. For multiple
hosts or replicas, replace the media and report volumes with shared object
storage before scaling horizontally.

## Database backup and restore

Create a custom-format PostgreSQL backup:

```bash
BACKUP_ROOT=/secure/backups ./scripts/backup_postgres.sh production
```

Copy backups off the Docker host and enforce retention separately. Periodically
verify restore procedures in a non-production environment:

```bash
CONFIRM_RESTORE=YES ./scripts/restore_postgres.sh staging /path/to/backup.dump
```

Restoring replaces data in the selected database. Always create a current backup
before restoring.

## GitHub deployment environments

Create GitHub environments named `development`, `staging` and `production`.
Configure these environment secrets:

- `DEPLOY_HOST`
- `DEPLOY_USER`
- `DEPLOY_PATH`
- `DEPLOY_SSH_PRIVATE_KEY`
- `DEPLOY_KNOWN_HOSTS`
- `GHCR_USERNAME`
- `GHCR_READ_TOKEN` with package read permission

Optional environment variable:

- `DEPLOY_API_PORT`

Set the repository variable `ENABLE_AUTOMATED_DEPLOYMENTS=true` only after all
three environments have been configured and manual deployment has succeeded.
Without that variable, `.github/workflows/deploy-compose.yml` remains available
through manual workflow dispatch but does not automatically deploy.

Production should use a required reviewer in the GitHub `production`
environment.
