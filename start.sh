#!/bin/bash
# Railway / Nixpacks startup script for the FastAPI backend.

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

# ── 2. Configure Environment Paths ──────────────────────────────────────────
# Point Python to the custom installation directory used in nixpacks.toml
# and ensure the backend root is available for cross-module imports.
export PYTHONPATH=$PYTHONPATH:/app/.local/lib/python3.11/site-packages:/app/backend

# ── 3. Move into the service directory ──────────────────────────────────────
# This makes 'main:app' resolvable.
SERVICE_DIR="/app/backend/shared_services"
cd "$SERVICE_DIR"

echo "Working directory: $(pwd)"

# ── 4. Start uvicorn ────────────────────────────────────────────────────────
# We use $PYTHON -m uvicorn to ensure it uses the specific interpreter we found
exec "$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"