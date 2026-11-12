#!/usr/bin/env bash
# One command: install what's missing, build the UI, start the API + UI on http://localhost:8000
set -euo pipefail
cd "$(dirname "$0")/.."
PORT="${PORT:-8000}"
PY="${PY:-python3}"

if ! command -v tesseract >/dev/null 2>&1; then
  echo "! Tesseract OCR not found (needed for the scanned Kelso Villa brochures)."
  echo "  macOS: brew install tesseract    Ubuntu: sudo apt-get install -y tesseract-ocr"
  exit 1
fi
command -v node >/dev/null 2>&1 || { echo "! Node.js 18+ not found. macOS: brew install node"; exit 1; }

if [ ! -x .venv/bin/python ]; then
  rm -rf .venv
  "$PY" -m venv .venv >/dev/null 2>&1 || { rm -rf .venv; echo "(python venv unavailable; installing into $PY directly)"; }
fi
if [ -x .venv/bin/python ]; then
  # shellcheck disable=SC1091
  source .venv/bin/activate
  PY=python
fi
"$PY" -m pip install -q -r requirements.txt -r agency_platform/requirements.txt

(cd agency_platform/frontend && { [ -d node_modules ] || npm install --silent; } && npm run build --silent)

if [ "${1:-}" = "--reset" ]; then
  rm -rf agency_platform/data
fi

echo ""
echo "  Agency Review Platform -> http://localhost:${PORT}"
echo "  (first start extracts the sample documents; give it ~20 seconds)"
echo ""
( sleep 4; command -v open >/dev/null 2>&1 && open "http://localhost:${PORT}" ) >/dev/null 2>&1 &
exec "$PY" -m uvicorn agency_platform.server:app --host 127.0.0.1 --port "$PORT"
