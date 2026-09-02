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
if git -C "$ROOT" grep -I -E "AKIA[0-9A-Z]{16}|BEGIN (RSA |OPENSSH )?PRIVATE KEY|aws_secret_access_key" -- ':!.env.example' ':!scripts/scan.sh' >"$TMPDIR/budgetlens-secret-scan.txt" 2>/dev/null; then
  fail "possible secret material in tracked files"
  cat "$TMPDIR/budgetlens-secret-scan.txt"
else
  echo "PASS  secret scan"
fi

TF_DIR="$ROOT/infrastructure/terraform"
TF_FILE=$(find "$TF_DIR" -name "*.tf" -print -quit 2>/dev/null || true)
if [ -n "$TF_FILE" ]; then
  echo "Checking Terraform formatting..."
  if command -v terraform >/dev/null 2>&1; then
    if terraform -chdir="$TF_DIR" fmt -check -recursive; then
      echo "PASS  terraform fmt"
    else
      fail "terraform fmt -check failed"
    fi

    echo "Validating Terraform roots..."
    for tf_root in bootstrap environments/dev environments/prod; do
      if terraform -chdir="$TF_DIR/$tf_root" init -backend=false -input=false -no-color >/dev/null; then
        if terraform -chdir="$TF_DIR/$tf_root" validate -no-color; then
          echo "PASS  terraform validate $tf_root"
        else
          fail "terraform validate failed in $tf_root"
        fi
      else
        echo "NOTE  terraform init -backend=false failed in $tf_root (providers unavailable)"
      fi
    done
  else
    echo "NOTE  terraform binary is not installed"
  fi

  echo "Linting Terraform..."
  if command -v tflint >/dev/null 2>&1; then
    pinned_tflint="$(cat "$TF_DIR/.tflint-version")"
    found_tflint="$(tflint --version 2>/dev/null | awk 'NR==1 { print $3 }' | tr -d 'v')"
    if [ -n "$found_tflint" ] && [ "$found_tflint" != "$pinned_tflint" ]; then
      echo "NOTE  tflint $found_tflint found; repository pin is $pinned_tflint"
    fi
    if tflint --init --chdir="$TF_DIR" && tflint --recursive --chdir="$TF_DIR"; then
      echo "PASS  tflint"
    else
      fail "tflint failed"
    fi
  else
    echo "NOTE  tflint is not installed (pin $TF_DIR/.tflint-version)"
  fi

  echo "Scanning Terraform..."
  if command -v checkov >/dev/null 2>&1; then
    pinned_checkov="$(cat "$TF_DIR/.checkov-version")"
    found_checkov="$(checkov --version 2>/dev/null | awk 'NR==1 { print $NF }' | tr -d 'v')"
    if [ -n "$found_checkov" ] && [ "$found_checkov" != "$pinned_checkov" ]; then
      echo "NOTE  checkov $found_checkov found; repository pin is $pinned_checkov"
    fi
    if checkov -d "$TF_DIR" --config-file "$TF_DIR/.checkov.yaml" --framework terraform; then
      echo "PASS  checkov"
    else
      fail "checkov reported a finding"
    fi
  else
    echo "NOTE  checkov is not installed (pin $TF_DIR/.checkov-version)"
  fi
else
  echo "NOTE  no Terraform files to lint or scan yet"
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
