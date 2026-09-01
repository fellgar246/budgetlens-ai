#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "Local restore recreates the database; it is not point-in-time recovery."
echo "For an isolated count check, run:"
echo "  cd apps/api && uv run pytest -m acceptance tests/integration/acceptance/test_operations.py"
echo "On AWS, restore a managed snapshot to an isolated instance before production-ready."
