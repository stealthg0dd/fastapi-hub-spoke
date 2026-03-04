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

# ── 2. Handle SSL Certificates ─────────────────────────────────────────────
# Search for the cert bundle that Nix already installed
if [ -f "/etc/ssl/certs/ca-bundle.crt" ]; then
    export SSL_CERT_FILE=/etc/ssl/certs/ca-bundle.crt
elif [ -f "/etc/ssl/certs/ca-certificates.crt" ]; then
    export SSL_CERT_FILE=/etc/ssl/certs/ca-certificates.crt
fi

# ── 3. Configure Paths ──────────────────────────────────────────────────────
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/nix/var/nix/profiles/default/lib:/usr/lib:/usr/local/lib
export PYTHONPATH=$PYTHONPATH:/app/.local/lib/python3.11/site-packages:/app/backend

# ── 4. Start uvicorn ────────────────────────────────────────────────────────
SERVICE_DIR="/app/backend/shared_services"
cd "$SERVICE_DIR"

echo "Starting Neufin Hub-Spoke with $PYTHON"
exec "$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"