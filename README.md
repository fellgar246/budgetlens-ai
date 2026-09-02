# BudgetLens

BudgetLens turns tabular budget and actuals files into explainable variance analysis. Financial totals are calculated by tested application code. The assistant can only query those results; it never writes financial data.

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
| `make scan` | Dependency, secret, Terraform (fmt/TFLint/Checkov), and optional image scans. Critical findings fail the command. |
| `make watchdog` | Mark stale processing import jobs as timed out. |
| `python -m budgetlens import-job validate\|apply <job-id>` | Run the same import modules as a worker process. |
| `make retain-files` | Delete expired original files, import error reports, and export objects. |
| `make test-perf` | Large-file preview timing. |
| `make traceability` | Check that every FR/NFR/AC, plan, gate, and high-impact risk is catalogued. |
| `make reset-local-data CONFIRM=1` | Destroy the local database volume and object storage. |

## Configuration

Copy `.env.example` to `.env`. Every variable is documented there with type, secrecy, and environments. Precedence: safe defaults, then the untracked repository-root `.env` (also used when commands run from `apps/api`), then process environment variables, then Secrets Manager for secrets on AWS.

`AUTH_MODE=dev` is rejected when `APP_ENV=prod`. API docs are enabled only when `APP_ENV` is `local` or `test`.

The browser calls `NEXT_PUBLIC_API_BASE_URL` (default `http://localhost:8000`). Do not point that variable at the Docker service name; the request runs in the browser.

## Local identity

`AUTH_MODE=dev` is available only when `APP_ENV` is `local` or `test`. Send `Authorization: Bearer <user-id>` and, for tenant-scoped routes, `X-Organization-Id`. `make seed` upserts two isolated organizations (Alpha in MXN with a January fiscal year, Beta in USD starting in April) plus viewer, analyst, admin, a dual-organization user, and a platform operator with no tenant membership. It also loads a synthetic financial dataset: revenue and expense, zero-budget rows, a negative actual, UNASSIGNED cost centers, overlapping account codes, and several periods. The web header lists those identities. Publish, activate, archive, and import commit require `Idempotency-Key`. JSON uses `snake_case`; amounts and ratios are decimal strings; every response includes `X-Trace-Id`.

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

Operational runbooks for rollback, restore, retention, load measurement, and local recovery are in `docs/OPERATIONS.md`. CI/CD, OIDC, and release evidence are in `docs/CICD.md`. Requirements, acceptance, and external gates are in `docs/TRACEABILITY.md`. Risks are in `docs/RISKS.md`. Deferred Should work is in `docs/BACKLOG.md`. Branch, commit, pull request, and definition-of-done conventions are in `docs/CONTRIBUTING.md`.

`packages/api-client/openapi.json` is generated (`make openapi`). A snapshot change needs an explicit review; do not edit that file by hand.
