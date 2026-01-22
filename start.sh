#!/usr/bin/env bash
set -euo pipefail

# Lightweight start script for POSIX environments (Docker / WSL / macOS).
# Usage examples:
#  ./start.sh --port 8000 --host 0.0.0.0 --check

PORT=8000
HOST="127.0.0.1"
REDIS_URL="${REDIS_URL:-}"
ADMIN_TOKEN="${ADMIN_TOKEN:-}"
OPENAI_KEY="${OPENAI_API_KEY:-}"
CHECK=0

print_usage(){
  cat <<EOF
Usage: $0 [--port PORT] [--host HOST] [--redis-url URL] [--admin-token TOKEN] [--openai-key KEY] [--check]
  --check   : dry-run, print env and command but do not execute
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --host) HOST="$2"; shift 2 ;;
    --redis-url) REDIS_URL="$2"; shift 2 ;;
    --admin-token) ADMIN_TOKEN="$2"; shift 2 ;;
    --openai-key) OPENAI_KEY="$2"; shift 2 ;;
    --check) CHECK=1; shift ;;
    -h|--help) print_usage; exit 0 ;;
    *) echo "Unknown arg: $1"; print_usage; exit 2 ;;
  esac
done

VENV_PY="./.venv/bin/python"
if [ ! -x "$VENV_PY" ]; then
  VENV_PY="$(command -v python || true)"
  if [ -z "$VENV_PY" ]; then
    echo "python not found in PATH and .venv/bin/python missing" >&2
    exit 2
  fi
fi

CMD="$VENV_PY -m uvicorn fastapi_app:app --host $HOST --port $PORT"

if [ "$CHECK" -eq 1 ]; then
  echo "Dry-run: would run with env:"
  [ -n "$REDIS_URL" ] && echo "REDIS_URL=$REDIS_URL"
  [ -n "$ADMIN_TOKEN" ] && echo "ADMIN_TOKEN=$ADMIN_TOKEN"
  [ -n "$OPENAI_KEY" ] && echo "OPENAI_API_KEY=$OPENAI_KEY"
  echo "$CMD"
  exit 0
fi

# Export environment variables for the server process
[ -n "$REDIS_URL" ] && export REDIS_URL="$REDIS_URL"
[ -n "$ADMIN_TOKEN" ] && export ADMIN_TOKEN="$ADMIN_TOKEN"
[ -n "$OPENAI_KEY" ] && export OPENAI_API_KEY="$OPENAI_KEY"

echo "Starting server: $CMD"
exec $CMD
