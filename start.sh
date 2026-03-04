#!/bin/bash
set -e

# ── 1. Find the Python interpreter ──────────────────────────────────────────
PYTHON=""
for candidate in python3.11 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
        PYTHON="$candidate"
        break
    fi
done

# ── 2. The Critical Library Fix ─────────────────────────────────────────────
# We point to the Nix store locations for C++ libraries so NumPy doesn't crash.
# We also include our custom .local site-packages.
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/nix/var/nix/profiles/default/lib:/usr/lib:/usr/local/lib
export PYTHONPATH=$PYTHONPATH:/app/.local/lib/python3.11/site-packages:/app/backend

echo "Using interpreter: $PYTHON"
echo "LD_LIBRARY_PATH: $LD_LIBRARY_PATH"

# ── 3. Start uvicorn ────────────────────────────────────────────────────────
SERVICE_DIR="/app/backend/shared_services"
cd "$SERVICE_DIR"

exec "$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"