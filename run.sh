#!/usr/bin/env bash
# PDFly launcher (Linux/macOS)
set -e
cd "$(dirname "$0")"
if ! python3 -c "import flask" 2>/dev/null; then
  echo "Installing dependencies…"
  pip3 install -r requirements.txt
fi
PORT="${PORT:-5000}"
echo "→ PDFly running at http://localhost:${PORT}"
exec python3 app.py
