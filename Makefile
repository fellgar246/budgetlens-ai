SHELL := /bin/sh
ROOT := $(abspath $(dir $(lastword $(MAKEFILE_LIST))))
API := $(ROOT)/apps/api
PNPM := $(shell command -v pnpm >/dev/null 2>&1 && echo pnpm || echo "corepack pnpm")

.PHONY: doctor bootstrap dev stop logs migrate seed test test-integration test-e2e lint format openapi ci build coverage coverage-unit scan watchdog retain-files test-perf traceability clean-generated reset-local-data

doctor:
	$(ROOT)/scripts/doctor.sh

bootstrap:
	$(ROOT)/scripts/bootstrap.sh

dev:
	docker compose up --build

stop:
	docker compose stop

logs:
	docker compose logs -f

migrate:
	cd "$(API)" && uv run alembic upgrade head

seed:
	cd "$(API)" && uv run python -m budgetlens seed

test:
	cd "$(API)" && uv run pytest -m "not integration and not perf"
	$(PNPM) --filter web test

test-integration:
	cd "$(API)" && uv run pytest -m integration

test-e2e:
	@echo "End-to-end browser tests are not part of the walking skeleton. Install Playwright browsers when that suite is added."

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
		--cov-fail-under=85 --cov-report=term-missing
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

retain-files:
	cd "$(API)" && uv run python -m budgetlens retain-files

test-perf:
	cd "$(API)" && uv run pytest -m perf

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

ci: lint test openapi
	$(PNPM) --filter web build
	$(ROOT)/scripts/scan.sh
	@if docker info >/dev/null 2>&1; then \
		docker image inspect budgetlens-api:local >/dev/null 2>&1 && docker tag budgetlens-api:local budgetlens-api:previous || true; \
		docker image inspect budgetlens-web:local >/dev/null 2>&1 && docker tag budgetlens-web:local budgetlens-web:previous || true; \
		docker build -t budgetlens-api:local "$(API)"; \
		docker build -t budgetlens-web:local -f apps/web/Dockerfile "$(ROOT)"; \
	else \
		echo "NOTE  Docker image builds skipped because the daemon is not running."; \
	fi

clean-generated:
	rm -rf apps/web/.next apps/web/out apps/api/.ruff_cache apps/api/.pytest_cache apps/api/.coverage

reset-local-data:
	CONFIRM="$(CONFIRM)" $(ROOT)/scripts/reset-local-data.sh
