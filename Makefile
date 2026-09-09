SHELL := /bin/sh
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
API := $(ROOT)/apps/api
PNPM := $(shell command -v pnpm >/dev/null 2>&1 && echo pnpm || echo "corepack pnpm")

.PHONY: doctor bootstrap dev stop logs migrate seed eval-ai test test-integration test-contract test-e2e test-acceptance lint format openapi ci build coverage coverage-unit scan watchdog import-job retain-files test-perf web-perf load-volume load-test traceability clean-generated reset-local-data record-cost-estimate record-gate check-gates review-apply teardown-dev preflight-deploy plan-environment apply-environment verify-infra smoke-release seed-demo observe-release restore-test rollback-release portfolio-check

doctor:
	$(ROOT)/scripts/doctor.sh

bootstrap:
	$(ROOT)/scripts/bootstrap.sh

dev:
	mkdir -p "$(ROOT)/var/storage"
	docker compose up --build

stop:
	docker compose stop

logs:
	docker compose logs -f

migrate:
	cd "$(API)" && uv run alembic upgrade head

seed:
	cd "$(API)" && uv run python -m budgetlens seed

eval-ai:
	cd "$(API)" && uv run python -m budgetlens eval-ai

test:
	cd "$(API)" && uv run pytest -m "not integration and not perf"
	$(PNPM) --filter web test

test-integration:
	cd "$(API)" && uv run pytest -m integration

test-contract:
	cd "$(API)" && uv run pytest tests/unit/test_openapi.py

test-e2e:
	$(PNPM) --filter web test:e2e

test-acceptance:
	cd "$(API)" && uv run pytest -m acceptance
	$(PNPM) --filter web test tests/acceptance-display.test.tsx

lint:
	cd "$(API)" && uv run ruff check src tests migrations
	cd "$(API)" && uv run ruff format --check src tests migrations
	cd "$(API)" && uv run pyright
	$(PNPM) --filter web lint
	$(PNPM) --filter web typecheck
	$(PNPM) --filter web format:check

format:
	cd "$(API)" && uv run ruff check --fix src tests migrations
	cd "$(API)" && uv run ruff format src tests migrations
	$(PNPM) --filter web format

openapi:
	cd "$(API)" && uv run python "$(ROOT)/scripts/export_openapi.py"

coverage:
	cd "$(API)" && uv run pytest tests/unit/domain \
		--cov=budgetlens.domain.money --cov=budgetlens.domain.variance \
		--cov=budgetlens.domain.fiscal --cov=budgetlens.domain.financial_entry \
		--cov-branch --cov-fail-under=85 --cov-report=term-missing
	cd "$(API)" && uv run pytest -m "not perf" \
		--cov=budgetlens --cov-report=term-missing --cov-fail-under=75

coverage-unit:
	cd "$(API)" && uv run pytest -m "not integration and not perf" \
		--cov=budgetlens --cov-report=term-missing

scan:
	chmod +x "$(ROOT)/scripts/scan.sh"
	$(ROOT)/scripts/scan.sh

watchdog:
	cd "$(API)" && uv run python -m budgetlens watchdog

import-job:
	cd "$(API)" && uv run python -m budgetlens import-job $(OPERATION) $(JOB_ID)

retain-files:
	cd "$(API)" && uv run python -m budgetlens retain-files

test-perf:
	cd "$(API)" && uv run pytest -m perf

web-perf:
	bash "$(ROOT)/scripts/web-perf-baseline.sh"

load-volume:
	cd "$(API)" && uv run python "$(ROOT)/scripts/load_volume.py"

load-test:
	python3 "$(ROOT)/scripts/load_test.py" $(LOAD_TEST_ARGS)

traceability:
	cd "$(API)" && uv run pytest tests/unit/test_traceability.py

build:
	$(PNPM) --filter web build
	@if docker info >/dev/null 2>&1; then \
		docker image inspect budgetlens-api:local >/dev/null 2>&1 && docker tag budgetlens-api:local budgetlens-api:previous || true; \
		docker image inspect budgetlens-web:local >/dev/null 2>&1 && docker tag budgetlens-web:local budgetlens-web:previous || true; \
		docker build -t budgetlens-api:local "$(API)"; \
		docker build -t budgetlens-web:local -f apps/web/Dockerfile "$(ROOT)"; \
	else \
		echo "Skipping image builds; Docker daemon is not running."; \
		exit 1; \
	fi

ci:
	chmod +x "$(ROOT)/scripts/ci.sh" "$(ROOT)/scripts/ci-e2e.sh"
	$(ROOT)/scripts/ci.sh
	@if docker info >/dev/null 2>&1; then \
		docker image inspect budgetlens-api:local >/dev/null 2>&1 && docker tag budgetlens-api:local budgetlens-api:previous || true; \
		docker image inspect budgetlens-web:local >/dev/null 2>&1 && docker tag budgetlens-web:local budgetlens-web:previous || true; \
		docker build -t budgetlens-api:local "$(API)"; \
		docker build -t budgetlens-web:local -f apps/web/Dockerfile "$(ROOT)"; \
	else \
		echo "NOTE  Docker image builds skipped because the daemon is not running."; \
	fi

clean-generated:
	rm -rf apps/web/.next apps/web/out apps/web/playwright-report apps/web/test-results \
		apps/api/.ruff_cache apps/api/.pytest_cache apps/api/.coverage apps/api/htmlcov

reset-local-data:
	CONFIRM="$(CONFIRM)" $(ROOT)/scripts/reset-local-data.sh

record-cost-estimate:
	python3 "$(ROOT)/scripts/record_cost_estimate.py" \
		--environment "$(ENVIRONMENT)" \
		--source "$(SOURCE)" \
		--monthly-estimate "$(MONTHLY_ESTIMATE)" \
		--currency "$(if $(CURRENCY),$(CURRENCY),USD)" \
		--notes "$(NOTES)"

record-gate:
	python3 "$(ROOT)/scripts/record_gate.py" --record \
		--gate "$(GATE)" \
		--environment "$(if $(ENVIRONMENT),$(ENVIRONMENT),dev)" \
		--recorded-by "$(RECORDED_BY)" \
		--status "$(if $(STATUS),$(STATUS),complete)" \
		--notes "$(NOTES)" \
		$(foreach item,$(DELIVERABLES),--deliverable "$(item)")

check-gates:
	python3 "$(ROOT)/scripts/record_gate.py" --check \
		--scope "$(if $(SCOPE),$(SCOPE),apply)" \
		--environment "$(if $(ENVIRONMENT),$(ENVIRONMENT),dev)" \
		$(if $(FROM_ENV),--from-env,) \
		--ai-provider "$(if $(AI_PROVIDER),$(AI_PROVIDER),stub)"

review-apply:
	python3 "$(ROOT)/scripts/record_gate.py" --review-apply \
		--environment "$(if $(ENVIRONMENT),$(ENVIRONMENT),dev)" \
		--recorded-by "$(RECORDED_BY)" \
		--account "$(ACCOUNT)" \
		--role "$(ROLE)" \
		--region "$(REGION)" \
		--image-digest "$(IMAGE_DIGEST)" \
		--confirm "$(CONFIRM)" \
		--notes "$(NOTES)" \
		$(if $(FIRST_APPLY),--first-apply,) \
		$(if $(REQUIRE_PRIOR),--require-prior,) \
		$(if $(FROM_ENV),--from-env,)

teardown-dev:
	ENVIRONMENT=dev CONFIRM="$(CONFIRM)" APPLY_DESTROY="$(APPLY_DESTROY)" \
		SNAPSHOT="$(SNAPSHOT)" DISABLE_DELETION_PROTECTION="$(DISABLE_DELETION_PROTECTION)" \
		EMPTY_BUCKET="$(EMPTY_BUCKET)" $(ROOT)/scripts/teardown-environment.sh

preflight-deploy:
	python3 "$(ROOT)/scripts/deploy_preflight.py" --print-checklist
	python3 "$(ROOT)/scripts/deploy_preflight.py" --check \
		--environment "$(if $(ENVIRONMENT),$(ENVIRONMENT),dev)" \
		--image-digest "$(IMAGE_DIGEST)" \
		--ci-status "$(CI_STATUS)" \
		--account "$(ACCOUNT)" \
		--role "$(ROLE)" \
		--region "$(REGION)" \
		--ai-provider "$(if $(AI_PROVIDER),$(AI_PROVIDER),stub)" \
		--bedrock-model-id "$(BEDROCK_MODEL_ID)" \
		$(if $(MIGRATION_REVIEWED),--migration-reviewed,) \
		$(if $(BUDGET_REVIEWED),--budget-reviewed,) \
		$(if $(BACKUP_REVIEWED),--backup-reviewed,) \
		$(if $(FIRST_APPLY),--first-apply,) \
		$(if $(REQUIRE_GATES),--require-gates,) \
		$(if $(FROM_ENV),--from-env,)

plan-environment:
	ENVIRONMENT="$(if $(ENVIRONMENT),$(ENVIRONMENT),dev)" \
		TF_STATE_BUCKET="$(TF_STATE_BUCKET)" AWS_REGION="$(if $(AWS_REGION),$(AWS_REGION),$(REGION))" \
		AWS_ACCOUNT_ID="$(if $(AWS_ACCOUNT_ID),$(AWS_ACCOUNT_ID),$(ACCOUNT))" \
		API_IMAGE="$(IMAGE_DIGEST)" $(ROOT)/scripts/plan-environment.sh

apply-environment:
	ENVIRONMENT="$(if $(ENVIRONMENT),$(ENVIRONMENT),dev)" PLAN_FILE="$(PLAN_FILE)" \
		CONFIRM="$(CONFIRM)" CONFIRM_PROD="$(CONFIRM_PROD)" $(ROOT)/scripts/apply-environment.sh

verify-infra:
	ENVIRONMENT="$(if $(ENVIRONMENT),$(ENVIRONMENT),dev)" \
		ACCOUNT="$(ACCOUNT)" $(ROOT)/scripts/verify-infrastructure.sh

smoke-release:
	API_HEALTH_URL="$(API_HEALTH_URL)" APPLICATION_URL="$(APPLICATION_URL)" \
		VERSION_URL="$(VERSION_URL)" EXPECTED_COMMIT="$(EXPECTED_COMMIT)" \
		$(ROOT)/scripts/smoke-release.sh

seed-demo:
	ENVIRONMENT="$(if $(ENVIRONMENT),$(ENVIRONMENT),dev)" CLUSTER="$(CLUSTER)" \
		TASK_DEFINITION="$(TASK_DEFINITION)" SUBNETS="$(SUBNETS)" \
		SECURITY_GROUPS="$(SECURITY_GROUPS)" IMAGE="$(IMAGE_DIGEST)" \
		$(ROOT)/scripts/run-seed-task.sh

observe-release:
	python3 "$(ROOT)/scripts/observe_release.py" --print-checklist
	python3 "$(ROOT)/scripts/observe_release.py" --record \
		--environment "$(if $(ENVIRONMENT),$(ENVIRONMENT),dev)" \
		--recorded-by "$(RECORDED_BY)" \
		--window "$(if $(WINDOW),$(WINDOW),agreed post-deploy window)" \
		--output "$(ROOT)/var/observation-$(if $(ENVIRONMENT),$(ENVIRONMENT),dev).json" \
		$(foreach item,$(NOTES),--note "$(item)")

restore-test:
	MODE="$(if $(MODE),$(MODE),aws)" SNAPSHOT_ID="$(SNAPSHOT_ID)" CONFIRM="$(CONFIRM)" \
		DELETE_RESTORE="$(DELETE_RESTORE)" APPLICATION_URL="$(APPLICATION_URL)" \
		$(ROOT)/scripts/restore-test.sh

rollback-release:
	PREVIOUS_TASK_DEFINITION="$(PREVIOUS_TASK_DEFINITION)" \
		PREVIOUS_WEB_SOURCE="$(PREVIOUS_WEB_SOURCE)" CLUSTER="$(CLUSTER)" \
		SERVICE="$(SERVICE)" WEB_BUCKET="$(WEB_BUCKET)" \
		DISTRIBUTION_ID="$(DISTRIBUTION_ID)" RUN_SMOKE="$(RUN_SMOKE)" \
		API_HEALTH_URL="$(API_HEALTH_URL)" APPLICATION_URL="$(APPLICATION_URL)" \
		$(ROOT)/scripts/rollback-release.sh

portfolio-check:
	python3 "$(ROOT)/scripts/portfolio_release.py" --print-checklist
	python3 "$(ROOT)/scripts/portfolio_release.py" --check
