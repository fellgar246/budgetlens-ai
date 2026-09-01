#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

failed=0
warned=0

ok() {
  printf 'OK    %s\n' "$1"
}

fail() {
  printf 'FAIL  %s\n' "$1"
  failed=1
}

warn() {
  printf 'WARN  %s\n' "$1"
  warned=1
}

have() {
  command -v "$1" >/dev/null 2>&1
}

echo "BudgetLens toolchain check"
echo "Repository: $ROOT"
echo

if have git; then
  ok "git $(git --version | awk '{print $3}')"
else
  fail "git is not installed. Install Git and retry."
fi

if have docker; then
  ok "docker $(docker --version | awk '{print $3}' | tr -d ',')"
  if docker compose version >/dev/null 2>&1; then
    ok "docker compose $(docker compose version --short 2>/dev/null || echo present)"
  else
    fail "docker compose v2 is not available. Install Docker Desktop with Compose v2."
  fi
  if docker info >/dev/null 2>&1; then
    ok "docker daemon is running"
  else
    fail "docker daemon is not running. Start Docker Desktop and retry."
  fi
else
  fail "docker is not installed. Install Docker Desktop and retry."
fi

if have node; then
  node_version="$(node -v | tr -d 'v')"
  node_major="$(printf '%s' "$node_version" | cut -d. -f1)"
  if [ "$node_major" -ge 20 ]; then
    ok "node $node_version"
    if [ "$node_major" -lt 22 ]; then
      warn "this repository pins Node.js 22 in .node-version; $node_version works for local install, Compose uses Node 22."
    fi
  else
    fail "node $node_version is too old. Install Node.js 20.11 or newer (22 preferred)."
  fi
else
  fail "node is not installed. Install Node.js 22 LTS (see .node-version)."
fi

if have corepack; then
  ok "corepack $(corepack --version 2>/dev/null || echo present)"
else
  warn "corepack is not available. Enable it from a current Node.js install to activate pnpm."
fi

if have pnpm; then
  ok "pnpm $(pnpm -v)"
elif have corepack; then
  ok "pnpm $(corepack pnpm -v) via corepack (no global shim)"
else
  fail "pnpm is not available. Install Node.js with Corepack, then run: corepack enable && corepack prepare pnpm@10.15.0 --activate"
fi

if have python3; then
  if python3 -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
    ok "python $(python3 --version | awk '{print $2}')"
  else
    fail "python $(python3 --version | awk '{print $2}') is not 3.12. Install Python 3.12 (see .python-version)."
  fi
else
  fail "python3 is not installed. Install Python 3.12."
fi

if have uv; then
  ok "uv $(uv --version | awk '{print $2}')"
else
  fail "uv is not installed. Install from https://docs.astral.sh/uv/ and retry."
fi

if have terraform; then
  tf_version="$(terraform version -json 2>/dev/null | python3 -c 'import json,sys; print(json.load(sys.stdin)["terraform_version"])' 2>/dev/null || terraform version | head -n 1 | awk '{print $2}' | tr -d 'v')"
  pinned="$(cat "$ROOT/infrastructure/terraform/.terraform-version")"
  if [ "$tf_version" = "$pinned" ]; then
    ok "terraform $tf_version"
  else
    warn "terraform $tf_version found; repository pin is $pinned. Local app does not require Terraform."
  fi
else
  warn "terraform is not installed. Required later for AWS environments; not needed to run the local app."
fi

if have tflint; then
  tflint_version="$(tflint --version 2>/dev/null | awk 'NR==1 { print $3 }' | tr -d 'v')"
  pinned_tflint="$(cat "$ROOT/infrastructure/terraform/.tflint-version")"
  if [ "$tflint_version" = "$pinned_tflint" ]; then
    ok "tflint $tflint_version"
  else
    warn "tflint $tflint_version found; repository pin is $pinned_tflint. Local app does not require TFLint."
  fi
else
  warn "tflint is not installed. Required later for AWS environments; pin is infrastructure/terraform/.tflint-version."
fi

if have checkov; then
  checkov_version="$(checkov --version 2>/dev/null | awk 'NR==1 { print $NF }' | tr -d 'v')"
  pinned_checkov="$(cat "$ROOT/infrastructure/terraform/.checkov-version")"
  if [ "$checkov_version" = "$pinned_checkov" ]; then
    ok "checkov $checkov_version"
  else
    warn "checkov $checkov_version found; repository pin is $pinned_checkov. Local app does not require Checkov."
  fi
else
  warn "checkov is not installed. Required later for AWS environments; pin is infrastructure/terraform/.checkov-version."
fi

if have aws; then
  aws_version="$(aws --version 2>&1 | awk '{print $1}')"
  case "$(aws --version 2>&1)" in
    aws-cli/2.*)
      ok "aws ${aws_version}"
      ;;
    *)
      warn "aws ${aws_version} found; AWS environments need AWS CLI v2. Not required to run the local app."
      ;;
  esac
else
  warn "aws CLI is not installed. Required later for AWS environments; not needed to run the local app."
fi

if have jq; then
  ok "jq $(jq --version 2>/dev/null | sed 's/^jq-//')"
else
  warn "jq is not installed. Optional; useful for inspecting JSON logs and AWS CLI output."
fi

if have make; then
  ok "make $(make --version | head -n 1 | awk '{print $3}')"
else
  fail "make is not installed. Install Make or an equivalent task runner and retry."
fi

echo
if [ "$failed" -ne 0 ]; then
  echo "Doctor found missing required tools. Install only the commands listed above; this script does not change your system."
  exit 1
fi

if [ "$warned" -ne 0 ]; then
  echo "Doctor passed with warnings. You can continue local setup."
  exit 0
fi

echo "Doctor passed."
