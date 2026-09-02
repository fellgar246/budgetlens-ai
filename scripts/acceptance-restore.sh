#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

python3 "${ROOT}/scripts/restore_test.py" --print-checklist
echo "Local restore recreates the database; it is not point-in-time recovery."
echo "For an isolated count check, run:"
echo "  cd apps/api && uv run pytest -m acceptance tests/integration/acceptance/test_operations.py"
echo "On AWS, restore a managed snapshot to budgetlens-dev-restore before calling the product production-ready:"
echo "  SNAPSHOT_ID=<id> CONFIRM=1 scripts/restore-test.sh"
