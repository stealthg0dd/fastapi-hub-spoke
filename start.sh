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

# ── 2. Configure Paths ──────────────────────────────────────────────────────
export PYTHONPATH=$PYTHONPATH:/app/.local/lib/python3.11/site-packages:/app/backend
export LD_LIBRARY_PATH=$LD_LIBRARY_PATH:/nix/var/nix/profiles/default/lib:/usr/lib:/usr/local/lib

# ── 3. Runtime SSL Resolution ──────────────────────────────────────────────
# We ask Python where its own 'certifi' certificates are. 
# This is the 'Solid Resolution' for the SSL OSError.
if $PYTHON -c "import certifi" &>/dev/null; then
    export SSL_CERT_FILE=$($PYTHON -c "import certifi; print(certifi.where())")
    export REQUESTS_CA_BUNDLE=$SSL_CERT_FILE
    echo "SSL Certificates resolved via certifi: $SSL_CERT_FILE"
fi

# ── 4. Start uvicorn ────────────────────────────────────────────────────────
SERVICE_DIR="/app/backend/shared_services"
cd "$SERVICE_DIR"

echo "Starting Neufin Backend..."
exec "$PYTHON" -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"