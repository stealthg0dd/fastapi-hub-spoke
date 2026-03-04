#!/bin/bash
# Railway / Nixpacks startup script for the FastAPI backend.
#
# Why this exists:
#   Railway's custom Start Command field overrides nixpacks.toml [start].
#   The nixpacks python311 nix package installs 'python3.11' but the generic
#   'python3' alias may not exist in the container PATH.  This script finds
#   whichever interpreter is available and uses the correct working directory
#   so that 'main:app' resolves to backend/shared_services/main.py.

set -e

# ── 1. Find the Python interpreter ──────────────────────────────────────────
PYTHON=""
for candidate in python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done

if [ -z "$PYTHON" ]; then
    echo "ERROR: No Python interpreter found in PATH" >&2
    exit 1
fi

echo "Using interpreter: $(command -v $PYTHON) ($($PYTHON --version))"

# ── 2. Move into the service directory ──────────────────────────────────────
# This makes 'main:app' resolvable and puts shared_services/ on sys.path
# automatically (Python adds CWD when running -m).
SERVICE_DIR="$(dirname "$0")/backend/shared_services"
cd "$SERVICE_DIR"

echo "Working directory: $(pwd)"

# ── 3. Start uvicorn ────────────────────────────────────────────────────────
exec "$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"
