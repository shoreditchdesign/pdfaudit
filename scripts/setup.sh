#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND_DIR="$ROOT_DIR/backend"

cd "$ROOT_DIR"

if [ ! -f "$BACKEND_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$BACKEND_DIR/.env"
fi

if [ ! -d "$BACKEND_DIR/.venv" ]; then
  python3 -m venv "$BACKEND_DIR/.venv"
fi

cd "$BACKEND_DIR"
"$BACKEND_DIR/.venv/bin/pip" install '.[dev]'
cd "$ROOT_DIR"

npm install
npm --prefix frontend install

echo "Setup complete."
