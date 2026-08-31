#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname "$0")/.." && pwd)"
FAILED=0
TMPDIR="${TMPDIR:-/tmp}"

fail() {
  echo "FAIL  $1" >&2
  FAILED=1
}

echo "Scanning Python dependencies..."
REQS="$TMPDIR/budgetlens-reqs.txt"
if (cd "$ROOT/apps/api" && uv export --frozen --no-dev --no-hashes >"$REQS"); then
  if (cd "$ROOT/apps/api" && uv run --with pip-audit pip-audit -r "$REQS" >"$TMPDIR/budgetlens-pip-audit.txt" 2>&1); then
    echo "PASS  pip-audit"
  elif grep -qi "critical" "$TMPDIR/budgetlens-pip-audit.txt"; then
    fail "pip-audit reported a critical finding"
    cat "$TMPDIR/budgetlens-pip-audit.txt"
  else
    echo "NOTE  pip-audit completed with non-critical findings"
    cat "$TMPDIR/budgetlens-pip-audit.txt"
  fi
else
  echo "NOTE  could not export the Python lockfile for pip-audit"
fi

echo "Scanning JavaScript dependencies..."
if (cd "$ROOT" && corepack pnpm audit --audit-level=critical >"$TMPDIR/budgetlens-npm-audit.txt" 2>&1); then
  echo "PASS  pnpm audit"
else
  fail "pnpm audit reported a critical finding"
  cat "$TMPDIR/budgetlens-npm-audit.txt"
fi

echo "Scanning tracked files for secrets..."
if git -C "$ROOT" grep -I -E "AKIA[0-9A-Z]{16}|BEGIN (RSA |OPENSSH )?PRIVATE KEY|aws_secret_access_key" -- ':!.env.example' >"$TMPDIR/budgetlens-secret-scan.txt" 2>/dev/null; then
  fail "possible secret material in tracked files"
  cat "$TMPDIR/budgetlens-secret-scan.txt"
else
  echo "PASS  secret scan"
fi

TF_FILE=$(find "$ROOT/infrastructure" -name "*.tf" -print -quit 2>/dev/null || true)
if [ -n "$TF_FILE" ]; then
  echo "Checking Terraform formatting..."
  if command -v terraform >/dev/null 2>&1; then
    if terraform -chdir="$ROOT/infrastructure/terraform" fmt -check; then
      echo "PASS  terraform fmt"
    else
      fail "terraform fmt -check failed"
    fi
  else
    echo "NOTE  terraform binary is not installed"
  fi
else
  echo "NOTE  no Terraform files to format yet"
fi

if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1 && command -v trivy >/dev/null 2>&1; then
  trivy image --severity CRITICAL --exit-code 1 budgetlens-api:local || fail "image scan reported a critical finding"
else
  echo "NOTE  image scan skipped (docker/trivy not available)"
fi

if [ "$FAILED" -ne 0 ]; then
  exit 1
fi

echo "Scan complete."
