#!/usr/bin/env bash
cd "$(dirname "${BASH_SOURCE[0]}")"

if [ -f .server.pid ]; then
  PID=$(cat .server.pid)
  if ps -p $PID > /dev/null 2>&1; then
    echo "[*] Stopping Netris MCP server (PID $PID)..."
    kill $PID
    sleep 1
    if ps -p $PID > /dev/null 2>&1; then
      echo "[*] Forcing process termination..."
      kill -9 $PID
    fi
  else
    echo "[!] Process $PID already stopped."
  fi
  rm -f .server.pid
  echo "[✓] Netris MCP server stopped."
else
  echo "[!] No .server.pid found. Searching for active instances..."
  pkill -f "app/webserver.py" || true
  echo "[✓] Cleaned up running processes."
fi
