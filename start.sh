#!/usr/bin/env bash
set -e
cd "$(dirname "${BASH_SOURCE[0]}")"

# 1. Initialise Python virtual environment if absent
if [ ! -d .venv ]; then
  echo "[*] Creating Python virtual environment in .venv..."
  python3 -m venv .venv
fi

# 2. Install dependencies
echo "[*] Installing dependencies..."
./.venv/bin/pip install --quiet -r requirements.txt

# 3. Initialise configuration if not present
if [ ! -f .env ] && [ -f .env.example ]; then
  echo "[*] Generating initial .env from template..."
  cp .env.example .env
fi

if [ ! -f config.json ] && [ -f config.example.json ]; then
  echo "[*] Generating initial config.json from template..."
  cp config.example.json config.json
fi

# 4. Resolve port configuration
PORT="${PORT:-8750}"
STDIO_MODE=false

while [[ "$#" -gt 0 ]]; do
  case $1 in
    --port) PORT="$2"; shift ;;
    --stdio) STDIO_MODE=true ;;
    *) echo "Unknown parameter: $1"; exit 1 ;;
  esac
  shift
done

export PORT
export PYTHONPATH="$(pwd):$(pwd)/app"

if [ "$STDIO_MODE" = true ]; then
  echo "=========================================================="
  echo " Starting Netris MCP Server in STDIO mode"
  echo "=========================================================="
  exec ./.venv/bin/python -m app.server
else
  echo "=========================================================="
  echo " Starting Netris Demo Tool on http://localhost:${PORT}"
  echo " Health Endpoint: http://localhost:${PORT}/api/health"
  echo "=========================================================="

  # Launch webserver in background and save PID to facilitate stop.sh
  ./.venv/bin/python app/webserver.py --port "${PORT}" &
  PID=$!
  echo $PID > .server.pid
  echo "[*] Server running with PID ${PID}"
fi
