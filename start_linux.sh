#!/usr/bin/env bash
# PDFly — one-click launcher for Linux/macOS
# Usage:  bash start_linux.sh   (or chmod +x && ./start_linux.sh)
set -e
cd "$(dirname "$0")"

echo "============================================"
echo "  PDFly - iLovePDF style PDF toolkit"
echo "============================================"

if ! python3 -c "import flask" 2>/dev/null; then
  echo "[1/2] Installing Python packages..."
  pip3 install -r requirements.txt
fi

echo "[2/2] Starting server at http://localhost:5000"
PORT="${PORT:-5000}"
exec python3 app.py
