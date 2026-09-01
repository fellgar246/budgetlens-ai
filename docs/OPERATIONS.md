# Local operations

This document covers availability, recovery, rollback, and hardening commands for the local product. It does not include financial figures.

## Targets

| Environment | Availability | RPO | RTO |
|---|---|---|---|
| `prod` | 99.5% monthly | 24 hours | 4 hours |
| `dev` | No SLA | 24 hours | 4 hours |
| `local` | No SLA | PostgreSQL named volume + bind-mounted `var/storage` | Recreate containers |

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

The local cleanup command purges:

- original import files after 90 days (`ORIGINAL_FILE_RETENTION_DAYS`);
- detailed import error rows after 30 days (`ERROR_REPORT_RETENTION_DAYS`);
- export objects after 24 hours (`EXPORT_RETENTION_HOURS`).

After a purge, job metadata and hashes stay in the database. Object lifecycle on AWS is configured in Terraform when those roots are filled. Conversation retention is configured per organization (7–365 days, default 90) and expired conversations are soft-deleted by the same command.

Business entities use logical archive or disable flags. Original files and exports expire by lifecycle. Local demo data is purged only with an explicit administrative command outside the 1.0 UI:

```text
make reset-local-data CONFIRM=1
```

Audit events are append-only for the application. Identifiers are UUID strings. Timestamps are UTC in RFC 3339. Application retention for audit is one year (`AUDIT_RETENTION_DAYS`, default 365) and is revisable. Expired audit rows are not deleted by the API process.

## Observability

JSON logs use a fixed field set: timestamp, level, service, environment, event, hashed identifiers, duration, outcome, and correlation IDs. They must not contain tokens, cookies, passwords, `DATABASE_URL`, presigned URLs, full prompts, raw file cells, or financial amounts.

- Local/dev log retention: 14 days (`LOG_RETENTION_DAYS`).
- Production log retention: 30–90 days, set on the log group after cost review.
- Conversation text is stored separately from logs and is not written to technical logs.
- Operator metrics (`GET /api/v1/ops/metrics`) expose request counts and duration histogram by route template, pool checkout/wait, query duration by logical name, import job/row/byte ratios, AI usage, estimated cost only when a price table is configured, and safe error codes. Organization IDs are never metric labels.
- Every response includes `X-Trace-Id`. The UI shows that identifier only on error and support surfaces.

### Initial alarms

Thresholds stay as Terraform variables and are calibrated after load tests. Until AWS roots exist, treat these as the local runbook:

| Alarm | Class | Diagnose | Rollback / mitigate |
|---|---|---|---|
| API 5xx above a sustained threshold | application | `GET /api/v1/ops/metrics` error codes and request histogram; logs by `trace_id` | Roll back to the `previous` image if the schema is compatible |
| No healthy API tasks | infrastructure | Process health and host/container status | Restart the API container; keep the previous image |
| Database storage, CPU, or connections critical | dependency | Readiness `503 DATABASE_UNAVAILABLE`, pool `checked_out`/`wait` | Fail closed for writes; restore from a managed snapshot onto an isolated instance |
| Import job failures or timeouts | application | Watchdog `JOB_TIMEOUT`, job status metrics, audit `import.failed` | Re-run the job after the file/mapping is fixed; do not leave jobs in `processing` |
| Elevated grounding failures | application | AI metrics `grounding_failures` and audit `ai.response_failed` | Keep analytics available; disable the copilot provider if the failure is provider-wide |
| Model provider errors or throttling | dependency | AI latency, `rate_limited`, provider 5xx in logs (no prompt text) | Serve analytics; retry with jitter; switch to the stub only in local/test |
| Estimated spend anomaly | infrastructure | Account-level cost controls; estimated cost is labeled as an estimate | Pause non-essential AI traffic; review the price table configuration |
| Certificate expiration | infrastructure | TLS probe and certificate inventory | Rotate the certificate before expiry |

Each alarm should stay linked to this table, the [images and rollback](#images-and-rollback) steps, and the [restore](#restore) steps.

## Exports

Exports expire. Creating and downloading them requires authorization. URLs are not written to logs.

## Conversations

Deletion is logical. Audit keeps metadata (identifiers, outcome) and not the conversation text. Prompts and full answers are not written to CloudWatch by default; usage metadata and hashes are retained.

`CONVERSATION_CONTENT_MODE=full_synthetic` may persist complete message text in `local` and `test` so synthetic demos keep history. In `dev` and `prod` the API stores a redacted placeholder instead. Accepting a production persistence policy (full encrypted text versus redacted storage) is a human decision and remains open. Real customer data stays blocked until that decision and M-08 are complete.

## Terraform state

Remote state uses a versioned, encrypted S3 bucket and Terraform's native `use_lockfile`. Do not add a new DynamoDB lock table. The repository pins Terraform 1.13.5 (1.10 or newer is required for native S3 locking). If an older root still has `dynamodb_table`, upgrade first, apply with both locks, then remove the DynamoDB argument.

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

On AWS `dev` and `prod`, restore a managed snapshot to an isolated instance. Check row counts and tenant isolation on that copy before pointing traffic at it. An isolated restore (AC-026) is required before calling the product production-ready. Until that AWS check runs, R-15 stays unverified and blocks AWS and production release. Locally, `make test-acceptance` clones the test database with `CREATE DATABASE … TEMPLATE` and rechecks counts and tenant isolation.

## Encryption and credentials

On AWS, traffic uses TLS and storage uses managed encryption. CI uses roles/OIDC, not permanent access keys. Domain and use-case code does not import AWS SDKs. Cognito IDs and public issuer URLs are configuration, not secrets. Database credentials and operational secrets live in Secrets Manager. Terraform state is private, versioned, encrypted, and least-privilege; mark sensitive outputs and do not print them in CI.

## Vulnerability response

1. Classify severity and blast radius (tenant leak, secret exposure, upload abuse, AI exfiltration).
2. Revoke affected credentials or sessions.
3. Contain the issue and keep a safe evidence copy.
4. Patch and deploy through the pipeline.
5. Re-run isolation and indicator checks (IDOR matrix, RLS, upload boundaries).
6. Record the incident, the fix, and the preventive follow-up.

## Copilot evaluation

Stub evaluation is deterministic and runs on every pull request (`make test` includes `tests/unit/test_ai_eval.py`). It scores tool selection, scope, numeric accuracy, grounding, safety, and a heuristic clarity rubric against the canonical Alpha FY2026 `Budget Final` dataset. A wrong figure fails `numeric_accuracy`. A cross-tenant leak or a mutation attempt fails the run and blocks release.

```text
make eval-ai
python -m budgetlens eval-ai --output var/ai-eval/stub.json
```

Live provider evaluation is not run on every PR. Use it before release, after a model/prompt/tool-schema change, or on a scheduled job:

```text
AI_PROVIDER=bedrock BEDROCK_MODEL_ID=<id> python -m budgetlens eval-ai --live
```

Each result records prompt version, model ID, tool schema hash, and commit SHA. Do not commit reports that contain non-synthetic answers. Clarity still needs a human pass; do not use another LLM as the only judge.

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

The scan covers Python and JavaScript dependencies, a secret-pattern grep, Terraform `fmt` / TFLint / Checkov when `.tf` files exist, and an optional image scan. A confirmed critical vulnerability blocks the release.
