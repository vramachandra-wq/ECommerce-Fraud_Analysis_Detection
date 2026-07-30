#!/usr/bin/env bash
# Optional hook invoked by the Deploy workflow after files are copied to the server.
# Customize for your host: systemd, podman-compose, uvicorn, etc.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

echo "==> Metro Cart deploy restart"

if command -v podman-compose >/dev/null 2>&1 && [ -f podman-compose.yaml ]; then
  podman-compose -f podman-compose.yaml up -d
fi

if [ -d .venv ]; then
  PY="$ROOT/.venv/bin/python"
else
  PY="python3"
fi

if pgrep -f "uvicorn api.main:app" >/dev/null 2>&1; then
  pkill -f "uvicorn api.main:app" || true
  sleep 2
fi

nohup "$PY" -m uvicorn api.main:app --host 0.0.0.0 --port 8000 \
  > .run/logs/api.log 2>&1 &

echo "==> API restarted on port 8000"
