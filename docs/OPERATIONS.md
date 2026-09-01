# Local operations

This document covers availability, recovery, rollback, and hardening commands for the local product. It does not include financial figures.

## Targets

| Environment | Availability | RPO | RTO |
|---|---|---|---|
| `prod` | 99.5% monthly | 24 hours | 4 hours |
| `dev` | No SLA | 24 hours | 4 hours |
| `local` | No SLA | Docker volume / `var/storage` | Recreate containers |

`prod` and `dev` copies on AWS use managed backups. Locally, `make reset-local-data CONFIRM=1` destroys data.

## Health

- Liveness: `GET /api/v1/health/live` stays 200 while the process responds.
- Readiness: `GET /api/v1/health/ready` is 200 when the database is available and 503 when it is not. Object storage and the AI provider do not affect readiness.
- If the database fails during a request, the API returns 503 `DATABASE_UNAVAILABLE` without internal details.
- If object storage fails, uploads and exports return 503 `STORAGE_UNAVAILABLE`; financial reads continue.
- If the AI provider fails, analytics continues and the copilot returns 503 `AI_UNAVAILABLE`.
- Technical metrics (operator): `GET /api/v1/ops/metrics`. These do not include amounts or prompts.

Failure classification:

- **application:** 5xx from the API process;
- **dependency:** database, object storage, or another provider;
- **infrastructure:** host process, disk, or network.

## Jobs and files

Import jobs in `processing` must not stay there indefinitely. The watchdog marks them `failed` with `JOB_TIMEOUT`.

```text
make watchdog
make retain-files
```

The initial retention window for original files is 90 days (`ORIGINAL_FILE_RETENTION_DAYS`). After a purge, job metadata is kept.

## Exports

Exports expire. Creating and downloading them requires authorization. URLs are not written to logs.

## Conversations

Deletion is logical. Audit keeps metadata (identifiers, outcome) and not the conversation text.

## Images and rollback

`make build` keeps the `previous` tag when a `local` image already exists.

```text
docker tag budgetlens-api:local budgetlens-api:previous
# ...new build...
docker tag budgetlens-api:previous budgetlens-api:local
docker compose up -d api
```

Do not roll back to an incompatible schema. If the new version required a migration, application rollback uses an image compatible with the current schema.

## Restore

Local recovery is recreation, not point-in-time restore:

```text
make reset-local-data CONFIRM=1
make migrate
make seed
```

On AWS `dev` and `prod`, restore a managed snapshot to an isolated instance. Check row counts and tenant isolation on that copy before pointing traffic at it. An isolated restore (AC-026) is required before calling the product production-ready. Until that check runs, R-15 stays unverified and blocks AWS and production release.

## Encryption and credentials

On AWS, traffic uses TLS and storage uses managed encryption. CI uses roles/OIDC, not permanent access keys. Domain and use-case code does not import AWS SDKs.

## Load

```text
python scripts/generate_large_dataset.py
python scripts/load_test.py --token <user-id> --organization-id <org> --budget-version-id <version>
```

The read threshold is p95 < 500 ms, excluding AI. Preview of a 25 MiB CSV must finish in under 60 s.

## Scans

```text
make scan
```

A confirmed critical vulnerability blocks the release.
