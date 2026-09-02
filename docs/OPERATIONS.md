# Operations

This document covers availability, recovery, rollback, cost controls, and hardening for local and AWS environments. It does not include a fixed monthly price. Record a dated estimate from official AWS prices before the first apply or after a size change.

## Targets

| Environment | Availability | RPO | RTO |
|---|---|---|---|
| `prod` | 99.5% monthly | 24 hours | 4 hours |
| `dev` | No SLA | 24 hours | 4 hours |
| `local` | No SLA | PostgreSQL named volume + bind-mounted `var/storage` | Recreate containers |

`prod` and `dev` copies on AWS use managed backups. Locally, `make reset-local-data CONFIRM=1` destroys data.

The production SLO is 99.5% of non-AI requests succeeding, excluding announced maintenance. Calibrate alarm thresholds from a baseline. Do not page on a single error.

## Daily checklist

- Open alarms on the SNS topic and CloudWatch dashboard.
- ECS tasks healthy (`HealthyHostCount` and `GET /api/v1/health/ready`).
- RDS free storage, CPU, and connections.
- Import jobs stuck in `processing` or marked `failed`.
- Bedrock or copilot errors, throttling, and latency (`GET /api/v1/ops/metrics` `ai` block).
- Accumulated spend and forecast in Billing and Cost Explorer. A budget is an alert, not a hard cap.
- Certificates and custom domains.
- Pending dependency or image vulnerabilities (`make scan`).

## Cost and account guardrails

Do not copy a dollar figure from this repository as the expected bill. Prices, region, usage, and models change. Before `apply`:

1. Review `cost_visible_sizes` in the environment outputs or `python scripts/record_cost_estimate.py --print-sizes --environment <dev|prod>`.
2. Enter those sizes into the official [AWS Pricing Calculator](https://calculator.aws/) or the AWS Price List. Do not invent a price.
3. Record the dated result: `make record-cost-estimate ENVIRONMENT=dev SOURCE='https://calculator.aws/#...' MONTHLY_ESTIMATE='<human figure>'`.
4. Confirm the budget and alarm email subscriptions manually. Terraform does not treat them as confirmed.

Account controls live in `infrastructure/terraform/bootstrap`:

- Monthly AWS Budget with chosen actual and forecast percent alerts. It does not stop spend.
- Cost Anomaly Detection when Cost Explorer is enabled and `enable_cost_anomaly_detection` is approved.
- Cost allocation tags (`Project`, `Environment`, `CostCenter`, `Owner`) when `enable_cost_allocation_tags` is approved.
- Required resource tags for Cost Explorer grouping.

Application AI usage is visible on `GET /api/v1/ops/metrics`. Estimated cost appears only when a price table is configured and is labeled as an estimate.

Principal cost drivers and the control for each:

| Driver | Unit | Control |
|---|---|---|
| NAT Gateway | hours and data | One in development; destroy unused environments; interface endpoints only with an ADR |
| RDS | hours, class, storage, backup | Small instance and single-AZ in development; storage alarms |
| ECS Fargate | vCPU, memory, time | Desired count 1 in development; autoscaling only in production after metrics |
| ALB | hours and LCUs | One per environment; review traffic |
| CloudFront | requests and data | Cache static assets; do not cache private API data |
| S3 | storage, requests, egress | Lifecycle on `uploads/`, `errors/`, `exports/` |
| CloudWatch | ingest and retention | Sanitized logs; short development retention |
| Bedrock | tokens and model | Configurable model; keep `ai_provider=stub` until live eval; cache only safe responses if designed |
| Cognito | users and operations | Watch MAU; self-registration stays off |

## Development policy

- Seed and demos use synthetic data only.
- Desired API count is 1. RDS is single-AZ. Log retention is 14 days.
- Destroy ephemeral environments when they are not needed. Follow [teardown](#teardown) and keep state or backups only on purpose.
- If development stays up as a portfolio demo, measure the real monthly cost for one week and then decide optimizations.

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

After a purge, job metadata and hashes stay in the database. Object lifecycle on AWS is configured in the Terraform storage module (`uploads/`, `errors/`, `exports/`). Conversation retention is configured per organization (7–365 days, default 90) and expired conversations are soft-deleted by the same command.

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

Thresholds stay as Terraform variables in the observability module and are calibrated after load tests. Do not copy a threshold blindly from another environment.

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

Remote state uses a versioned, encrypted S3 bucket created by `infrastructure/terraform/bootstrap` and Terraform's native `use_lockfile`. Do not add a new DynamoDB lock table. The repository pins Terraform 1.13.5 (1.10 or newer is required for native S3 locking). If an older root still has `dynamodb_table`, upgrade first, apply with both locks, then remove the DynamoDB argument.

Environment roots live in `infrastructure/terraform/environments/dev` and `environments/prod`. They do not share workspaces. Static checks (`fmt`, `validate`, TFLint, Checkov) do not need AWS credentials. A real plan still requires a recorded account, region, a dated cost estimate, and an image digest.

Required tags on every managed resource: `Project=BudgetLens`, `Environment`, `ManagedBy=Terraform`, `Owner`, `CostCenter`, and `DataClassification`.

Remaining human steps before apply are the manual gates in [GATES.md](GATES.md): secure the AWS account (M-01), choose a region (M-02), record the dated cost estimate and confirm budget email (M-03), keep Bedrock stub until model access (M-04), configure GitHub Environments for OIDC (M-05), and complete the apply review (M-09). Production apply is never `-auto-approve`. Record gates with `scripts/record_gate.py`; never paste secret keys, database passwords, or Cognito tokens.

## CI/CD

The GitHub pipeline is documented in [CICD.md](CICD.md). CI uses GitHub OIDC roles, not permanent access keys. Images publish with a commit SHA and, for SemVer tags, that version. Deploy identity is the image digest. Development can apply after `main`; production requires the protected `prod` environment, a human approval, the same digest, an RDS snapshot, a one-off migration, smoke tests, and written evidence.

## Images and rollback

`make build` keeps the `previous` tag when a `local` image already exists.

```text
docker tag budgetlens-api:local budgetlens-api:previous
# ...new build...
docker tag budgetlens-api:previous budgetlens-api:local
docker compose up -d api
```

Do not roll back to an incompatible schema. If the new version required a migration, application rollback uses an image compatible with the current schema.

On AWS, `scripts/rollback-release.sh` updates the ECS service to the previous task definition and can restore the previous web artifact. It does not downgrade the database. Terraform rollback is a new plan from reverted code.

## Restore

Local recovery is recreation, not point-in-time restore:

```text
make reset-local-data CONFIRM=1
make migrate
make seed
```

On AWS `dev` and `prod`, restore a managed snapshot to an isolated instance. Check row counts and tenant isolation on that copy before pointing traffic at it. An isolated restore (AC-026) is required before calling the product production-ready. Until that AWS check runs, R-15 stays unverified and blocks AWS and production release. Locally, `make test-acceptance` clones the test database with `CREATE DATABASE … TEMPLATE` and rechecks counts and tenant isolation.

## Backups

- RDS automated backups follow the environment RPO (`backup_retention_days` is 7 in development and 14 in production).
- Take a snapshot before a high-risk change: `DB_IDENTIFIER=<id> scripts/snapshot-db.sh`. Production deploy already does this.
- A backup that has not been restored onto an isolated resource does not count as a strategy. Use the [restore](#restore) steps.
- S3 versioning and lifecycle stay aligned with retention for uploads, errors, and exports.
- The Terraform state bucket is versioned, encrypted, and least-privilege. Do not empty it during environment teardown.

## Runbooks

### Deploy and rollback

Use [CICD.md](CICD.md) for the pipeline and [images and rollback](#images-and-rollback) for the commands. Production apply is never `-auto-approve`. Application rollback does not downgrade the database.

### Database migration failure

1. Do not shift traffic to a schema-dependent image.
2. Keep the previous task definition from the deploy job.
3. Inspect the one-off migration task logs. Do not print secrets.
4. Fix forward with a new expand-compatible migration, or keep the previous image if it matches the current schema.
5. Do not run `alembic downgrade` against AWS.

### Restore database

Follow [restore](#restore). Restore onto an isolated instance first. Compare tenant counts before changing DNS or the application secret.

### Bedrock unavailable or throttled

1. Analytics stays available. The copilot returns 503 `AI_UNAVAILABLE`.
2. Check `ai` metrics and logs for `rate_limited` or provider 5xx. Do not write prompts to the ticket.
3. Retry with jitter. Switch `ai_provider` to `stub` only in local or test.
4. Keep the model ID configurable. Do not cache private responses unless a later design allows it.

### Import job stuck

1. Confirm the job is still `processing` and older than the watchdog timeout.
2. Run `make watchdog` locally or the operations task on AWS.
3. The job must become `failed` with `JOB_TIMEOUT`. Re-run after the file or mapping is fixed.
4. Do not delete job metadata to "unstick" a hash.

### S3 access denied

1. Check the task role, bucket policy, and KMS key policy. Readiness stays up because storage is not a readiness dependency.
2. Uploads and exports return 503 `STORAGE_UNAVAILABLE`.
3. Never make the data or web bucket public to clear the error.
4. Confirm the object key prefix (`uploads/`, `errors/`, `exports/`) and the caller organization.

### Secret rotation

1. Do not print `DATABASE_URL`, `STORAGE_KEY_PEPPER`, or Terraform-sensitive outputs.
2. Rotate the RDS master password in RDS, then update the Secrets Manager JSON for `DATABASE_URL` without echoing it.
3. Force a new ECS deployment so tasks pick up the new secret version.
4. Confirm `GET /api/v1/health/ready` and revoke the previous secret version after the service is stable.
5. Terraform does not store the password as an input or output.

### Cognito login incident

1. Confirm the user pool, app client, hosted UI domain, and callback URLs from Terraform outputs. Those IDs are not secrets.
2. Check CloudWatch and the API for `401`/`403` without writing tokens to the ticket.
3. Disable a compromised user in the Cognito console. Terraform does not create users.
4. Keep self-registration off. Do not add a client secret to the public SPA.

### Unexpected cost spike

1. Open AWS Budgets and Cost Explorer. Confirm the email alert. A budget does not stop spend.
2. Group by `Project`, `Environment`, `CostCenter`, and service. NAT, RDS, and Bedrock are the usual drivers.
3. Pause non-essential AI traffic (`ai_provider=stub` in a new plan) and stop unused tasks.
4. If the environment is ephemeral, follow [teardown](#teardown).
5. Record the sizes that changed and a new dated estimate before the next apply.

### Teardown

Use `scripts/teardown-environment.sh`. It never destroys the bootstrap state bucket.

```text
ENVIRONMENT=dev CONFIRM=1 SNAPSHOT=1 scripts/teardown-environment.sh
# review the destroy plan
ENVIRONMENT=dev CONFIRM=1 SNAPSHOT=1 DISABLE_DELETION_PROTECTION=1 \
  EMPTY_BUCKET=<exact-data-or-web-bucket> APPLY_DESTROY=1 \
  scripts/teardown-environment.sh
```

Required order:

1. Confirm environment and account from Terraform outputs and `aws sts get-caller-identity`.
2. Export any audit or demo data that must be kept.
3. Take a snapshot if the data should be recoverable.
4. Disable deletion protection only with `DISABLE_DELETION_PROTECTION=1`.
5. Empty S3 only when `EMPTY_BUCKET` equals the exact data or web bucket name.
6. Review `terraform plan -destroy`.
7. Apply the saved destroy plan only with `APPLY_DESTROY=1`. Production also needs `CONFIRM_PROD=1`.
8. Keep or delete remote state as a separate decision. Never delete the state bucket from this script.

`make teardown-dev CONFIRM=1` is the development wrapper.

## Scaling

Before increasing CPU, memory, task count, or database class:

1. Confirm the metric and the constraint.
2. Measure the specific query, import, or tool.
3. Optimize the index, code, or a safe cache.
4. Right-size the existing task or instance.
5. Record the change and a new dated cost estimate.

Do not introduce Redis, a managed queue, or a database proxy without evidence and a new ADR. BL-1110 remains a Could item.

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
