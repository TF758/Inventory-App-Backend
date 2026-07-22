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

The release service runs deployment checks plus `check_storage` before migrations.
The storage check writes, reads, and deletes a private probe object through both
the `default` and `reports` aliases. The script then polls `/health/ready/` and
fails if PostgreSQL, Redis or migrations are not ready.

## Durable application storage

Imports and generated reports use Django's named `STORAGES` configuration. The
API and Celery workers therefore use storage keys rather than container-local
absolute paths.

The supported modes are:

- `STORAGE_BACKEND=filesystem`: local development or a single Docker host.
  `STORAGE_SHARED=True` is mandatory in staging and production, and the API and
  worker services must mount the same durable `inventory_media` and
  `inventory_reports` volumes.
- `STORAGE_BACKEND=s3`: recommended for staging and production. This supports
  AWS S3 and S3-compatible services such as MinIO, Cloudflare R2 and DigitalOcean
  Spaces through `AWS_S3_ENDPOINT_URL`.

The default storage alias holds import uploads under `MEDIA_STORAGE_PREFIX`. The
`reports` alias stores generated workbooks under `REPORT_STORAGE_PREFIX`. Objects
remain private and are streamed through authenticated API endpoints; clients do
not receive bucket URLs.

Production deployment checks reject an unknown backend, missing named aliases,
unshared filesystem storage, missing S3 bucket names, non-HTTPS production S3
endpoints, or disabled S3 TLS verification. Single-host filesystem storage is
accepted in production with a warning, but must be replaced before adding API or
worker replicas on another host.

### Moving existing files to object storage

No database migration is required because `ReportJob.report_file` and pending
import parameters already contain relative storage keys. Before switching an
environment from filesystem storage to S3:

1. Stop new imports and report generation, then allow active jobs to finish.
2. Copy `/app/media/` into the bucket's `MEDIA_STORAGE_PREFIX` path.
3. Copy `/app/reports/` into the bucket's `REPORT_STORAGE_PREFIX` path.
4. Configure the S3 variables in the environment file.
5. Run the release step and verify an existing report download plus a new import.
6. Retain the old volumes until the new storage has been validated and backed up.

Static files remain on the `inventory_staticfiles` volume and are served by
WhiteNoise; they are not part of application upload storage.

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

## Production security boundaries

Staging and production force the following controls regardless of conflicting
environment values:

- DRF Basic Authentication is disabled.
- WebSocket JWTs are rejected from query strings. Use the `jwt` WebSocket
  subprotocol pair instead.
- Prometheus metrics are not public. Set `METRICS_BEARER_TOKEN` and send it as
  `Authorization: Bearer <token>` from the scraper. An empty token disables the
  endpoint.
- API documentation is never public. Staging may enable staff-only docs with
  `API_DOCS_ENABLED=True`; production disables docs by default.
- WebSocket origins are checked against `ALLOWED_HOSTS`.

Production also validates HTTPS origins during `python manage.py check --deploy`.
Use only `https://` values for `FRONTEND_URL`, `CORS_ALLOWED_ORIGINS`, and
`CSRF_TRUSTED_ORIGINS`, and never use `*` in `ALLOWED_HOSTS`.

The staging and production Compose overlays bind the API port to `127.0.0.1` so
clients cannot bypass the trusted reverse proxy and forge proxy security headers.
The internal production health check sends `X-Forwarded-Proto: https` so Django
can keep `SECURE_SSL_REDIRECT=True` without redirecting the container probe. The
external reverse proxy must strip any incoming `X-Forwarded-Proto` value and set
its own trusted value.

### Metrics scraper example

```bash
curl \
  -H "Authorization: Bearer ${METRICS_BEARER_TOKEN}" \
  https://api.example.com/metrics
```

Do not put the metrics token in URLs, Compose files, source control, or logs.


## Background-job reliability and recovery

P1.3 separates asynchronous work into four Celery queues:

- `default` for short general-purpose tasks such as email delivery.
- `imports` for CSV ingestion and database writes.
- `reports` for workbook generation and durable report storage.
- `maintenance` for cleanup, snapshots, log maintenance, and stale-job recovery.

Compose runs dedicated `worker-imports` and `worker-reports` services. The
existing `worker` service consumes `default,maintenance`. Keep all three worker
services running; starting only the general worker will leave import and report
messages queued.

Import and report tasks use late acknowledgement, reject messages when a worker
process is lost, use a prefetch multiplier of one, and have task-specific soft
and hard time limits. The hard limits must remain lower than
`JOB_STALE_AFTER_SECONDS`; the deployment check rejects unsafe combinations that
could let recovery take over a task that is still allowed to run.

`ReportJob.task_id`, `attempt_count`, and `heartbeat_at` form a database-backed
execution lease. A second delivery cannot execute an active job owned by another
task id. Redelivery of the same task id can resume safely, and report writes use
execution-scoped storage keys so a stale worker cannot delete replacement
output. Import retries rely on database duplicate checks and never repeat the
import phase after a result payload has been committed.

Run the migration included with P1.3 before starting the new workers:

```bash
python manage.py migrate
```

Configure the recovery schedule with `JOB_RECOVERY_CRON`. The release service
installs or updates the Beat entry after migrations; it can also be refreshed
manually with:

```bash
python manage.py setup_logger
python manage.py setup_db_cleaners
```

The recovery task requeues jobs whose worker lease has expired, dispatches jobs
left pending after a broker outage, and moves jobs to a client-safe failed state
when `JOB_MAX_ATTEMPTS` is exhausted. Abandoned import uploads are removed when a
cancelled or exhausted import becomes terminal.

Before every release, validate that enabled database Beat entries still point to
registered Celery tasks:

```bash
python manage.py check_celery_tasks
```

The production Compose release service runs `setup_db_cleaners` and then this
registry check automatically after migrations and before application services
are promoted. A misspelled or removed enabled task causes the release to stop.

Useful operational checks:

```bash
celery -A inventory inspect ping
celery -A inventory inspect active_queues
celery -A inventory inspect active
python manage.py check --deploy --fail-level ERROR
python manage.py check_celery_tasks
```

During a worker deployment, Docker allows a two-minute graceful shutdown. Work
that cannot finish before the container stops is redelivered and then reconciled
through the job lease and recovery task.
