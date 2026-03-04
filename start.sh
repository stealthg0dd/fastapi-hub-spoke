#!/bin/bash
set -e

# ── 1. Activate the Virtual Environment ─────────────────────────────────────
# This automatically handles PYTHONPATH and the correct PIP-installed packages
export VIRTUAL_ENV="/app/venv"
export PATH="/app/venv/bin:$PATH"

# ── 2. Library & Pathing ────────────────────────────────────────────────────
# Ensure C++ libraries for NumPy/PGVector are visible
export LD_LIBRARY_PATH="$LD_LIBRARY_PATH:/nix/var/nix/profiles/default/lib:/usr/lib:/usr/local/lib"
export PYTHONPATH="/app/backend:$PYTHONPATH"

# ── 3. The "Bulletproof" SSL Fix ────────────────────────────────────────────
# We use the venv's certifi for all DB and OpenAI connections
CERTS=$(python -c "import certifi; print(certifi.where())")
export SSL_CERT_FILE="$CERTS"
export REQUESTS_CA_BUNDLE="$CERTS"
export HTTXX_CA_BUNDLE="$CERTS"

echo "🔒 SSL verification secured via venv/certifi."

# ── 4. Start the Application ───────────────────────────────────────────────
echo "🚀 Starting Neufin Hub from Virtual Environment..."
cd /app/backend/shared_services
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"