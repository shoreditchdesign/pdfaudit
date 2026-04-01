#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

if [ ! -x "$BACKEND_DIR/.venv/bin/uvicorn" ]; then
  echo "Backend virtualenv is missing. Run 'npm run setup' from $ROOT_DIR first."
  exit 1
fi

if lsof -tiTCP:8000 -sTCP:LISTEN >/dev/null 2>&1; then
  echo "Port 8000 is already in use. Run 'npm run stop' from $ROOT_DIR, then retry."
  exit 1
fi

cd "$BACKEND_DIR"
exec .venv/bin/uvicorn app.main:app --reload
