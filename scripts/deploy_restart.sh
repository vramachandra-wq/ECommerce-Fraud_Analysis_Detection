#!/usr/bin/env bash
# Restart Metro Cart API after an SSH deploy extract.
# Expected layout: <deploy-root>/metro-cart/ (this script lives in metro-cart/scripts/)
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

RUN_DIR="${RUN_DIR:-$ROOT/.run}"
LOG_DIR="$RUN_DIR/logs"
PID_FILE="$RUN_DIR/api.pid"
mkdir -p "$LOG_DIR"

PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if [[ -x "$ROOT/.venv/bin/python" ]]; then
    PYTHON_BIN="$ROOT/.venv/bin/python"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="$(command -v python3)"
  else
    PYTHON_BIN="$(command -v python)"
  fi
fi

if [[ ! -d "$ROOT/.venv" ]]; then
  echo "==> Creating virtualenv at $ROOT/.venv"
  "$PYTHON_BIN" -m venv "$ROOT/.venv"
  PYTHON_BIN="$ROOT/.venv/bin/python"
fi

echo "==> Installing dependencies"
"$PYTHON_BIN" -m pip install --upgrade pip
"$PYTHON_BIN" -m pip install -r "$ROOT/requirements.txt"

stop_existing() {
  if [[ -f "$PID_FILE" ]]; then
    old_pid="$(cat "$PID_FILE" || true)"
    if [[ -n "${old_pid:-}" ]] && kill -0 "$old_pid" 2>/dev/null; then
      echo "==> Stopping previous API (pid $old_pid)"
      kill "$old_pid" 2>/dev/null || true
      for _ in $(seq 1 20); do
        kill -0 "$old_pid" 2>/dev/null || break
        sleep 0.25
      done
      kill -9 "$old_pid" 2>/dev/null || true
    fi
    rm -f "$PID_FILE"
  fi
  # Fallback: stop any uvicorn bound to the configured port.
  API_PORT="${API_PORT:-8000}"
  if command -v pgrep >/dev/null 2>&1; then
    pgrep -f "uvicorn api.main:app" | while read -r pid; do
      echo "==> Stopping leftover uvicorn pid $pid"
      kill "$pid" 2>/dev/null || true
    done
  fi
}

stop_existing

export APP_ENV="${APP_ENV:-production}"
export COOKIE_SECURE="${COOKIE_SECURE:-true}"
export GROQ_SSL_VERIFY="${GROQ_SSL_VERIFY:-true}"
export SCHEMA_STRICT="${SCHEMA_STRICT:-true}"

HOST="${API_HOST:-0.0.0.0}"
PORT="${API_PORT:-8000}"
LOG_FILE="$LOG_DIR/api.log"

echo "==> Starting API on ${HOST}:${PORT}"
nohup "$PYTHON_BIN" -m uvicorn api.main:app \
  --host "$HOST" \
  --port "$PORT" \
  >>"$LOG_FILE" 2>&1 &
echo $! >"$PID_FILE"

# Brief readiness wait
for _ in $(seq 1 30); do
  if curl -fsS "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    echo "==> API healthy (pid $(cat "$PID_FILE"))"
    exit 0
  fi
  sleep 1
done

echo "WARNING: API started but /health did not become ready; check $LOG_FILE" >&2
exit 0
