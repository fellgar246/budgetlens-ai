#!/bin/sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
cd "$ROOT"

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Created .env from .env.example"
else
  echo ".env already exists"
fi

if command -v corepack >/dev/null 2>&1; then
  PNPM="corepack pnpm"
elif command -v pnpm >/dev/null 2>&1; then
  PNPM="pnpm"
else
  echo "pnpm is not available."
  echo "Enable the pinned package manager with:"
  echo "  corepack enable"
  echo "  corepack prepare pnpm@10.15.0 --activate"
  exit 1
fi

if ! command -v uv >/dev/null 2>&1; then
  echo "uv is not available. Install uv and retry."
  exit 1
fi

echo "Installing JavaScript workspace dependencies..."
${PNPM} install

echo "Installing API dependencies..."
(
  cd apps/api
  uv sync
)

mkdir -p var/storage
echo "Created var/storage"

echo
echo "Bootstrap complete. Next:"
echo "  make doctor"
echo "  make dev"
echo "  make migrate   # Compose already migrates; required when the API runs on the host"
echo "  make seed"
echo "  make test"
