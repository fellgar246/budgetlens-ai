# AWS deployment runbook

This runbook runs after plans 00–09 and gates M-01–M-09. Concrete commands live in `scripts/` and `.github/workflows/`. A human still authorizes apply. Do not paste secret keys, database passwords, or tokens.

```text
python scripts/deploy_preflight.py --print-checklist
make preflight-deploy ENVIRONMENT=dev ACCOUNT='<id>' ROLE='<role>' REGION='us-east-1' \
  IMAGE_DIGEST='repo@sha256:…' CI_STATUS=green
make check-gates SCOPE=apply ENVIRONMENT=dev
make review-apply ENVIRONMENT=dev RECORDED_BY='<human>' ACCOUNT='<id>' ROLE='<role>' \
  REGION='us-east-1' IMAGE_DIGEST='repo@sha256:…' CONFIRM=1
```

## 1. Preflight

- [ ] CI on `main` is green.
- [ ] API image is built, scanned, and published by digest. Never `latest`.
- [ ] Frontend artifact is built.
- [ ] OpenAPI and the generated client are synchronized.
- [ ] Migration is reviewed and expand-compatible.
- [ ] AWS identity shows the expected account, role, and region.
- [ ] Budget and a dated official cost estimate are reviewed.
- [ ] Bedrock model access is confirmed, or the copilot stays stub.
- [ ] Backup or snapshot matches the change risk.

`scripts/deploy_preflight.py --check` records those items without secrets. GitHub `Deploy dev` and `Deploy prod` print the same checklist.

## 2. Bootstrap state and OIDC

First time only, with temporary administrative credentials:

```text
CONFIRM=1 AWS_REGION=us-east-1 scripts/bootstrap-state.sh
# review bucket, versioning, encryption, public access, and CI roles
CONFIRM=1 APPLY=1 AWS_REGION=us-east-1 scripts/bootstrap-state.sh
```

Then migrate the backend with partial config from the outputs (`backend.hcl.example`). Verify the lockfile and that the CI role can read state. Do not add state, plan files, or `backend.hcl` to Git. See [bootstrap/README.md](../infrastructure/terraform/bootstrap/README.md).

## 3. Environment plan

```text
ENVIRONMENT=dev TF_STATE_BUCKET='<bucket>' AWS_REGION=us-east-1 \
  AWS_ACCOUNT_ID='<id>' scripts/plan-environment.sh
```

Review create/change/destroy, IAM wildcards, network exposure, RDS deletion, buckets, frontend public values, and Cognito callbacks. Record M-09. An unexpected destroy is rejected by `scripts/terraform_plan_guard.py` and is never applied to “try it”.

## 4. Apply base infrastructure

```text
ENVIRONMENT=dev PLAN_FILE=infrastructure/terraform/environments/dev/tfplan \
  CONFIRM=1 scripts/apply-environment.sh
ENVIRONMENT=dev scripts/verify-infrastructure.sh
```

Apply uses the saved plan file and is never `terraform apply -auto-approve`. After apply:

1. Capture non-sensitive outputs.
2. Verify VPC, subnets, and security groups.
3. Verify RDS is not public. The secret ARN may be listed; the password is not.
4. Verify application buckets stay private.
5. Verify ECR, ECS, ALB, and log groups.
6. Verify Cognito and CloudFront.

## 5. Migration

```text
IMAGE='repo@sha256:…' CLUSTER='…' TASK_DEFINITION='…' \
  SUBNETS='…' SECURITY_GROUPS='…' scripts/run-migration-task.sh
```

Inspect the exit code and sanitized logs. Query the migration head through `GET /api/v1/ops/metrics` (`migration_version`) or `GET /api/v1/health/ready`. If the task fails, do not shift traffic to a schema-dependent API image. Fix forward with an expand-compatible migration.

## 6. Application deploy

1. Update the task definition with the image digest (Terraform `api_image`).
2. Deploy ECS and wait for stability. The service uses a circuit breaker.
3. Upload the frontend artifact with cache headers (`scripts/deploy-web.sh`).
4. Invalidate HTML and manifests only. Do not blanket-invalidate hashed `/_next/static` assets.
5. Confirm `GET /api/v1/version` matches the expected commit.

GitHub `Deploy dev` (after `Build` on `main`) and `Deploy prod` (SemVer tag or manual promotion) follow this order. Production promotes the same digest and takes an RDS snapshot first.

## 7. Smoke tests

```text
API_HEALTH_URL='https://…/api/v1/health/ready' \
  APPLICATION_URL='https://…' \
  EXPECTED_COMMIT='<sha>' \
  scripts/smoke-release.sh
```

Automated checks: CloudFront/web over HTTPS, `/health/live`, `/health/ready`, `/version`, `X-Trace-Id`, and secret-free bodies.

Human or authenticated demo checks:

- Cognito login and logout.
- Organization selector.
- Small synthetic import.
- Dashboard and variance endpoints.
- Cross-tenant negative check with controlled demo users.
- Copilot stub on AWS, or Bedrock with AI-E01 after M-04.
- Audit metadata without fixture raw cells or tokens.

## 8. Demo seed

Never seed on API startup. Seed is an explicit administrative task:

```text
make seed                          # local / test only
ENVIRONMENT=dev CLUSTER='…' TASK_DEFINITION='…' \
  SUBNETS='…' SECURITY_GROUPS='…' scripts/run-seed-task.sh
```

The command:

- requires `APP_ENV=dev` on AWS and refuses `APP_ENV=prod`;
- creates only the known Alpha/Beta demo organizations and users;
- is idempotent;
- writes a `demo.seeded` audit event.

Production Terraform does not create a seed task (`create_seed_task = false`).

## 9. Post-deploy observation

During the agreed window, watch 5xx and latency, healthy tasks and restarts, database connections and storage, Bedrock errors or throttling, import failures, spend, and ingested logs.

```text
python scripts/observe_release.py --print-checklist
make observe-release ENVIRONMENT=dev RECORDED_BY='<human>' WINDOW='2h'
```

Write release evidence (`scripts/release_evidence.py`): commit or tag, digest, plan, migration revision, smoke, AI/model note, known risks, and rollback target. Do not store secrets.

## 10. Rollback

### API without an incompatible schema change

```text
PREVIOUS_TASK_DEFINITION='<arn>' CLUSTER='…' SERVICE='…' \
  RUN_SMOKE=1 API_HEALTH_URL='https://…/api/v1/health/ready' \
  scripts/rollback-release.sh
```

Select the previous task definition or digest, update the ECS service, wait for stability, and smoke.

### Frontend

Restore the previous artifact, invalidate HTML and manifests, and smoke login/dashboard.

### Migration

Do not run an automatic destructive downgrade. Deploy a schema-compatible app or a corrective expand migration. Restore the database only for a severe incident, after evaluating data loss against the RPO.

### Terraform

Revert the change in Git, generate a new plan, and review it. Do not edit state by hand except as an expert procedure with a backup.

## 11. Restore test

```text
MODE=local scripts/restore-test.sh
SNAPSHOT_ID='<snapshot>' CONFIRM=1 scripts/restore-test.sh
# after authorization and cost review
SNAPSHOT_ID='<snapshot>' CONFIRM=1 DELETE_RESTORE=1 scripts/restore-test.sh
```

1. Restore onto an isolated resource named `budgetlens-dev-restore`.
2. Do not point production or development traffic at it.
3. Check schema, counts, and tenant invariants.
4. Document the observed RPO and RTO.
5. Delete the restored resource after authorization and review cost.

Locally, `make test-acceptance` clones with `CREATE DATABASE … TEMPLATE`. An AWS isolated restore (AC-026) is required before calling the product production-ready. Until that check runs, R-15 stays unverified.

## 12. Development teardown

Destructive and deliberate. See [OPERATIONS.md](OPERATIONS.md#teardown).

```text
make teardown-dev CONFIRM=1
ENVIRONMENT=dev CONFIRM=1 SNAPSHOT=1 DISABLE_DELETION_PROTECTION=1 \
  EMPTY_BUCKET='<exact-data-or-web-bucket>' APPLY_DESTROY=1 \
  scripts/teardown-environment.sh
```

1. Confirm the exact account and environment.
2. Export evidence that must be kept.
3. Review deletion protection, buckets, and snapshots.
4. Generate and review the destroy plan.
5. Empty buckets only with the exact name and authorization.
6. Apply the saved destroy plan.
7. Check for orphaned resources and Cost Explorer later.
8. Keep state according to policy. This script never deletes the bootstrap state bucket.
