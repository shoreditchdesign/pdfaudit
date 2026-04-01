#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if [ ! -x "$BACKEND_DIR/.venv/bin/pytest" ]; then
  echo "Backend virtualenv is missing. Run 'npm run setup' from $ROOT_DIR first."
  exit 1
fi

cd "$BACKEND_DIR"
export PYTHONPATH="$BACKEND_DIR"
exec .venv/bin/pytest
