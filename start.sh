#!/bin/bash
set -e

# ── 1. Locate Python ────────────────────────────────────────────────────────
PYTHON="python3.11"

# ── 2. Environment Pathing ──────────────────────────────────────────────────
# Ensure we prioritize the packages we just installed in the /app/.local folder
export PATH="/app/.local/bin:$PATH"
export PYTHONPATH="/app/.local/lib/python3.11/site-packages:/app/backend:$PYTHONPATH"
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/nix/var/nix/profiles/default/lib:/usr/lib:/usr/local/lib"

# ── 3. The "Bulletproof" SSL Fix ────────────────────────────────────────────
# Instead of looking at the OS, we force Python to use the certs from 'certifi'
if $PYTHON -c "import certifi" &>/dev/null; then
    CERTS=$($PYTHON -c "import certifi; print(certifi.where())")
    export SSL_CERT_FILE="$CERTS"
    export REQUESTS_CA_BUNDLE="$CERTS"
    export HTTXX_CA_BUNDLE="$CERTS"
    echo "🔒 SSL verification locked to certifi: $CERTS"
else
    echo "⚠️ Warning: certifi not found, SSL might fail."
fi

# ── 4. Execution ────────────────────────────────────────────────────────────
echo "🚀 Starting Neufin Hub..."
cd /app/backend/shared_services
exec $PYTHON -m uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"