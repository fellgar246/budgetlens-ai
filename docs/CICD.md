# CI/CD and release

GitHub Actions authenticates to AWS with OIDC. Do not store `AWS_ACCESS_KEY_ID` or `AWS_SECRET_ACCESS_KEY`.

## Workflows

| Workflow | Trigger | Purpose |
|---|---|---|
| `CI` | Pull request and push to `main` | Path detection, API, contract, web, E2E, scans, Terraform checks |
| `Build` | Push to `main` or `v*.*.*` | One API image, SBOM/provenance when available, image scan, SHA/semver tags, immutable web artifact |
| `Terraform plan` | Manual or Terraform PR | Remote-backend plan, secret-free summary, fail unexpected destroys |
| `Deploy dev` | Successful `Build` on `main` or manual | Digest deploy, one-off migration, web upload, smoke, compatible rollback |
| `Deploy prod` | `v*.*.*` tag or manual | Protected `prod` environment, same digest, RDS snapshot, migrate, smoke, evidence |

`Build` never publishes or deploys `latest`. Production promotes the same image digest.

Set `AUTO_DEPLOY_DEV=false` to keep development deploys manual.

## GitHub variables

Configure these repository or environment variables. They are not secrets.

| Variable | Used by |
|---|---|
| `AWS_REGION` | All AWS jobs |
| `AWS_ACCOUNT_ID` | Terraform `-var` |
| `TF_STATE_BUCKET` | Remote backend |
| `PLAN_ROLE_ARN` | Terraform plan |
| `DEPLOY_DEV_ROLE_ARN` | Build publish and deploy-dev |
| `DEPLOY_PROD_ROLE_ARN` | Deploy-prod |
| `DEV_ECR_REPOSITORY` | Image publish |
| `PROD_ECR_REPOSITORY` | Digest promotion |
| `DEV_APPLICATION_URL` | Public frontend build and smoke |
| `PROD_APPLICATION_URL` | Production frontend build and smoke |
| `AUTO_DEPLOY_DEV` | Optional; `false` disables automatic dev deploy |

GitHub Environments (gate M-05; create them in the repository UI):

- `dev` — used by deploy-dev OIDC (`environment:dev`)
- `prod` — required reviewers; production apply never uses `-auto-approve` without a plan file from the same job

Creating the remote repository, branch protection, and environment reviewers is a human action. Workflows only assume AWS through OIDC after those settings exist.

Frontend public values (`NEXT_PUBLIC_API_BASE_URL`, `NEXT_PUBLIC_APP_ENV`) are reviewed before the static build. Secrets stay in Secrets Manager at runtime.

## Branch protection

On `main`:

- Require the `CI` job
- Require a review when a team exists, especially for `infrastructure/`, migrations, and auth
- Require conversations to be resolved
- Do not allow force-push

`.github/CODEOWNERS` lists those paths. Replace `@budgetlens/maintainers` with the real team.

## Release identity

- Application releases use SemVer tags `vMAJOR.MINOR.PATCH`
- `/version` and the ECS task definition record `GIT_SHA` and `APP_VERSION`
- Deploy identity is the image digest
- Changelog fragments come from commits or pull request titles (`python scripts/changelog.py`)
- Each deploy writes evidence: commit/tag, digest, plan, migration revision, smoke, AI/model note, known risks, rollback target

## Rollback

Application rollback restores the previous task definition and/or previous web artifact. It does not downgrade the database. Terraform rollback is a new plan from reverted code, not a state edit.

See [OPERATIONS.md](OPERATIONS.md#images-and-rollback). Cost estimates, daily checks, and teardown are in [OPERATIONS.md](OPERATIONS.md). Manual gates, including GitHub Environments (M-05) and apply review (M-09), are in [GATES.md](GATES.md). Do not ask for access keys, root passwords, or tokens in a plan.
