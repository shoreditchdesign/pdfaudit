#!/usr/bin/env bash
set -euo pipefail

for port in 3001 8000; do
  pids="$(lsof -tiTCP:"$port" -sTCP:LISTEN || true)"
  if [ -n "$pids" ]; then
    echo "Stopping listeners on port $port: $pids"
    kill $pids || true
  fi
done

echo "Stop complete."
