#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"
PYTHON_BIN=""

if [ -x "$BACKEND_DIR/.venv/bin/python" ]; then
  PYTHON_BIN="$BACKEND_DIR/.venv/bin/python"
elif [ -x "$BACKEND_DIR/backend/.venv/bin/python" ]; then
  PYTHON_BIN="$BACKEND_DIR/backend/.venv/bin/python"
else
  echo "Backend virtualenv is missing. Run 'npm run setup' from $ROOT_DIR first."
  exit 1
fi

mkdir -p "$ROOT_DIR/reports" "$ROOT_DIR/summary" "$ROOT_DIR/target"

export PYTHONPATH="$BACKEND_DIR:$ROOT_DIR"
exec "$PYTHON_BIN" "$ROOT_DIR/scripts/audit_run.py" "$@"
