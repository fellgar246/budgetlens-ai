# BudgetLens

BudgetLens turns tabular budget and actuals files into explainable variance analysis. Spreadsheet formulas and chat answers invent totals; this product imports the file, validates it, and calculates variance in tested application code. The assistant can only query those results; it never writes financial data.

This repository is a **local portfolio demo** at application version `0.1.0`. AWS modules and OIDC workflows are in the tree. They are not applied from a clone. Tag `v1.0.0` stays blocked until recorded production gates exist.

What a reviewer can do without private knowledge:

- Import a synthetic workbook and see validation fail closed on formulas and bad rows
- Drill into a variance (zero-budget percent is `N/A`, not a fabricated ratio)
- Ask the copilot for Maintenance in January and open matching evidence
- Switch from Alpha to Beta and confirm the previous tenant disappears
- Read how the same API image would run on ECS behind CloudFront

Honest limits: one functional currency per organization, monthly periods, stub copilot unless a human enables Bedrock, synthetic data only, no public production URL, no invented monthly AWS price.

| Guide | Purpose |
|---|---|
| [docs/DEMO.md](docs/DEMO.md) | 6–8 minute local walkthrough |
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | Runtime and Terraform diagrams |
| [docs/AI_EVALUATION.md](docs/AI_EVALUATION.md) | Stub eval aggregate (20/20); no live claim |
| [docs/COST.md](docs/COST.md) | Dated sizes; no invented bill |
| [docs/RELEASE.md](docs/RELEASE.md) | Checklist; `v1.0.0` remains gated |
| [docs/WEB.md](docs/WEB.md) | Static web app, keyboard walkthrough, Lighthouse |
| [docs/DECISIONS.md](docs/DECISIONS.md) | ADRs and tradeoffs |
| [sample-data/README.md](sample-data/README.md) | Synthetic files and expected facts |

This repository is a monorepo:

- `apps/web` — Next.js static web app
- `apps/api` — FastAPI service with domain, application, ports, adapters, and HTTP routes
- `packages/api-client` — typed HTTP client and OpenAPI snapshot
- `infrastructure/terraform` — `bootstrap/`, `modules/`, and `environments/dev` plus `environments/prod` for AWS. Local development does not apply these roots.
- `compose.yaml` — local Next.js dev server, API (optional reload), PostgreSQL, and an optional worker profile

## Pinned toolchain

| Tool | Pin | Where it is recorded |
|---|---|---|
| Python | 3.12 | `.python-version`, `apps/api/pyproject.toml` |
| Node.js | 22 (local 20.11+ accepted) | `.node-version`, `package.json` engines |
| pnpm | 10.15.0 | `package.json` `packageManager` |
| uv | latest compatible with the lockfile | `apps/api/uv.lock` |
| PostgreSQL | 16.6 | `compose.yaml` |
| Terraform | 1.13.5 | `infrastructure/terraform/.terraform-version` |
| TFLint | 0.64.0 | `infrastructure/terraform/.tflint-version` |
| Checkov | 3.3.9 | `infrastructure/terraform/.checkov-version` |
| Playwright | 1.62.1 | `apps/web/package.json` |

Task runner: **Make**. Type checker: **Pyright** (strict). Database access: **synchronous SQLAlchemy 2** with the `psycopg` driver so Alembic and the API share one model.

## Local URLs

- Web: http://localhost:3000
- API: http://localhost:8000
- OpenAPI UI (local and test only): http://localhost:8000/docs

## Onboarding

Requires macOS or Linux, Docker Desktop, Python 3.12, Node.js 20.11+, and [uv](https://docs.astral.sh/uv/).

```text
cp .env.example .env
make doctor
make bootstrap
make dev
```

`make doctor` only reports missing tools; it does not install anything. `make dev` builds and starts PostgreSQL, the API with source reload, and the Next.js dev server. The API applies migrations on startup. Seeds are never applied automatically, including on AWS.

In another terminal:

```text
make migrate
make seed
make test
```

`make migrate` is idempotent. Compose already upgrades the database when the API starts; run it on the host when you are not using the API container.

After seed, open http://localhost:3000, sign in as a demo user, and choose Alpha or Beta. API docs stay local-only at http://localhost:8000/docs. Readiness is `GET /api/v1/health/ready`.

To run the API on the host (PostgreSQL still in Docker):

```text
docker compose up -d postgres
make migrate
cd apps/api && uv run uvicorn budgetlens.main:app --reload --port 8000
pnpm --filter web dev
```

## Commands

| Command | Purpose |
|---|---|
| `make doctor` | Check required tools. Does not install anything. |
| `make bootstrap` | Create `.env` if missing, install dependencies, create local storage. |
| `make dev` | Start Compose services (`COMPOSE_PROFILES=worker make dev` also starts the worker). |
| `make stop` | Stop containers without deleting volumes. |
| `make logs` | Follow Compose logs. |
| `make migrate` | Apply Alembic migrations using host `DATABASE_URL`. |
| `make seed` | Upsert Alpha/Beta tenants, local users, catalog dimensions, and a synthetic financial dataset. Idempotent. |
| `make eval-ai` | Run the stub copilot evaluation dataset (AI-E01–E12, AI-S01–S08). Live Bedrock: `python -m budgetlens eval-ai --live`. |
| `make test` | API unit tests and web unit tests. |
| `make test-integration` | API tests that need PostgreSQL. |
| `make test-contract` | OpenAPI snapshot and TypeScript client path checks. |
| `make test-e2e` | Playwright journeys against a running app (`E2E_BASE_URL`, default http://localhost:3000). |
| `make test-acceptance` | Release catalog AC-001–AC-026 (API suite plus web display checks). |
| `make lint` | Ruff, Pyright, ESLint, TypeScript, Prettier check. |
| `make format` | Apply formatters. |
| `make openapi` | Refresh `packages/api-client/openapi.json`. |
| `make clean-generated` | Delete regenerable caches and build outputs. Never deletes database or `var/storage`. |
| `make ci` | Lint, types, unit, integration when PostgreSQL is up, OpenAPI contract, web build, security scan, and image builds when Docker is up. |
| `make coverage` | 85% branch coverage on the financial engine and 75% backend with the integration suite. |
| `make coverage-unit` | Informational unit coverage, no fail threshold. |
| `make scan` | Dependency, secret, SBOM inputs, Terraform (fmt/TFLint/Checkov), and optional image scans. Critical findings fail the command. |
| `make watchdog` | Mark stale processing import jobs as timed out. The optional worker profile runs the same loop and stops on SIGTERM. |
| `python -m budgetlens import-job validate\|apply <job-id>` | Run the same import modules as a worker process. |
| `make retain-files` | Delete expired original files, import error reports, and export objects. |
| `make test-perf` | Large-file preview timing. |
| `make web-perf` | Lighthouse HTML/JSON for the local web app (`var/lighthouse/`). Needs Chrome and a running stack. |
| `make load-volume` | Insert up to 250k synthetic Alpha rows for local read measurement. |
| `make load-test` | Measure variance-summary p95 against a running API (`var/perf/`). |
| `make traceability` | Check that every FR/NFR/AC, plan, gate, and high-impact risk is catalogued. |
| `make reset-local-data CONFIRM=1` | Destroy the local database volume and object storage. |
| `make record-cost-estimate ENVIRONMENT=dev SOURCE='https://calculator.aws/#…' MONTHLY_ESTIMATE='…'` | Record a dated official AWS estimate. Does not invent a price. |
| `make record-gate GATE=M-01 ENVIRONMENT=dev RECORDED_BY='…' DELIVERABLES='…'` | Record a human manual gate. Never include secrets. |
| `make check-gates SCOPE=apply ENVIRONMENT=dev` | Fail if required human gates are missing. |
| `make review-apply ENVIRONMENT=dev … CONFIRM=1` | Record M-09 after the apply checklist. Does not run Terraform. |
| `make teardown-dev CONFIRM=1` | Review a development destroy plan. Apply only with `APPLY_DESTROY=1`. |
| `make preflight-deploy …` | Secret-free AWS deploy preflight. Does not apply Terraform. |
| `make smoke-release API_HEALTH_URL=…` | Public HTTPS, health, version, and trace-id smoke. |
| `make seed-demo ENVIRONMENT=dev …` | Explicit AWS demo seed. Refuses production. |
| `make observe-release RECORDED_BY=…` | Record post-deploy observation evidence. |
| `make restore-test MODE=local` | Isolated restore checklist. AWS requires `SNAPSHOT_ID` and `CONFIRM=1`. |
| `make portfolio-check` | Secret-free portfolio docs, links, and release-tag guard. Does not create a tag. |

## Configuration

Copy `.env.example` to `.env`. Every variable is documented there with type, secrecy, and environments. Precedence: safe defaults, then the untracked repository-root `.env` (also used when commands run from `apps/api`), then process environment variables, then Secrets Manager for secrets on AWS.

`AUTH_MODE=dev` is rejected when `APP_ENV=prod`. API docs are enabled only when `APP_ENV` is `local` or `test`.

The browser calls `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`). Do not point that variable at the Docker service name; the request runs in the browser.

## Local identity

`AUTH_MODE=dev` is available only when `APP_ENV` is `local` or `test`. Send `Authorization: Bearer <user-id>` and, for tenant-scoped routes, `X-Organization-Id`. `AUTH_MODE=oidc` validates issuer, audience, expiry, and JWKS. The web app uses `NEXT_PUBLIC_AUTH_MODE=oidc` with a public client and PKCE; live Cognito remains an AWS apply step. `make seed` upserts two isolated organizations (Alpha in MXN with a January fiscal year, Beta in USD starting in April) plus viewer, analyst, admin, a dual-organization user, and a platform operator with no tenant membership. It also loads a synthetic financial dataset: revenue and expense, zero-budget rows, a negative actual, UNASSIGNED cost centers, overlapping account codes, and several periods. The web header lists those identities. Publish, activate, archive, and import commit require `Idempotency-Key`. JSON uses `snake_case`; amounts and ratios are decimal strings; every response includes `X-Trace-Id`.

`GET /me` returns the active role, persona, and capability matrix. Changing organization clears incompatible filters and cached view state. A forged `organization_id` in the URL, payload, or `X-Organization-Id` header returns `403` or `404` without saying whether the other tenant exists. The operator can open `/estado` and never receives financial rows by default.

The web shell follows the product journeys: summary, variances, imports, scenarios, copilot, settings, and operation. Those views load live tenant data when a local session is selected; empty, loading, and error states stay visible when there is nothing to show. `/catalogo` remains a harness for dimensions and budget versions. Amounts stay as four-decimal values; the API never returns infinity or `NaN` for variance.

If a host port is busy, change `WEB_PORT`, `API_PORT`, or `POSTGRES_PORT` in `.env`. Internal Compose URLs stay the same. Also update `CORS_ORIGINS` and `NEXT_PUBLIC_API_BASE_URL` when those host ports change.

Set `API_RELOAD=0` to start the API container without uvicorn reload. Object uploads use `LocalObjectStorage` at `./var/storage` (bind-mounted into the API). There is no local AWS emulator.

Recommended editor settings live in `.vscode/`: format on save, the `uv` interpreter, workspace TypeScript, pytest and Vitest discovery, tasks for `dev` / `test` / `lint`, and debug configs for FastAPI and Next.js. Those files do not embed secrets.

## Troubleshooting

**Docker daemon is not running.** Start Docker Desktop, wait until it is idle, then rerun `make doctor` and `make dev`.

**Port already allocated.** Set `WEB_PORT`, `API_PORT`, or `POSTGRES_PORT` in `.env` and restart Compose. Internal service URLs stay the same. The default host port for PostgreSQL is `5433` so a local engine on `5432` does not intercept host tests.

**Database volume is incompatible after an engine upgrade.** Stop services and reset only if you can discard local data: `make reset-local-data CONFIRM=1`.

**Pending migration.** Compose runs `alembic upgrade head` when the API starts. On the host, run `make migrate` against the same `DATABASE_URL`.

**Wrong Node or pnpm.** Prefer `corepack enable` and `corepack prepare pnpm@10.15.0 --activate` if you can write to the Node bin directory. If that is blocked, `corepack pnpm` works from this repository without a global shim. Compose builds use Node 22 regardless of the host version.

**`uv sync` fails.** Confirm `python3 --version` is 3.12.x and that you are in `apps/api` or using the Makefile targets.

**Local storage permission errors.** Compose bind-mounts `./var/storage` (ignored by Git) into the API. Recreate it with `mkdir -p var/storage`. `make bootstrap` and `make dev` create the directory if it is missing.

**Playwright browsers are missing.** Install Chromium once: `pnpm --filter web exec playwright install chromium`. Start the app with `make dev`, then run `make test-e2e`.

**Acceptance catalog.** `make test-acceptance` runs the mapped API cases. With the stack up, `scripts/acceptance-local-stack.sh` checks web, API, and readiness. `scripts/acceptance-rollback.sh` and `scripts/acceptance-restore.sh` document the local rollback and restore checks.

**Readiness returns 503.** PostgreSQL is not reachable. Check `docker compose ps` and `DATABASE_URL`. Liveness stays 200 while the process can serve requests.

## Security notes

Do not commit `.env`, credentials, Terraform state, uploads, or real financial files. Local PostgreSQL credentials in `.env.example` are labeled development-only. Logs must not include tokens, `DATABASE_URL`, or financial rows.

The ordered AWS deploy runbook is `docs/DEPLOYMENT.md`. Operational runbooks for rollback, restore, cost estimates, teardown, retention, load measurement, and local recovery are in `docs/OPERATIONS.md`. CI/CD, OIDC, and release evidence are in `docs/CICD.md`. Manual gates that the code must not assume are in `docs/GATES.md`. Requirements, acceptance, and external gates are in `docs/TRACEABILITY.md`. Risks are in `docs/RISKS.md`. Deferred Should work is in `docs/BACKLOG.md`. Branch, commit, pull request, and definition-of-done conventions are in `docs/CONTRIBUTING.md`. Portfolio demo, architecture, sanitized AI eval, dated cost sizes, and the release checklist are `docs/DEMO.md`, `docs/ARCHITECTURE.md`, `docs/AI_EVALUATION.md`, `docs/COST.md`, and `docs/RELEASE.md`.

`packages/api-client/openapi.json` is generated (`make openapi`). A snapshot change needs an explicit review; do not edit that file by hand.
