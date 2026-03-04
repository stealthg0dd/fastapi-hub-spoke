#!/bin/bash
set -e

# 1. Activate Environment
export VIRTUAL_ENV="/app/venv"
export PATH="/app/venv/bin:$PATH"

# 2. Strict Library Pathing
# We avoid /usr/local/lib to prevent the kernel/GLIBC mismatch
export LD_LIBRARY_PATH="/nix/var/nix/profiles/default/lib:/app/venv/lib:$LD_LIBRARY_PATH"
export PYTHONPATH="/app/backend:/app/backend/shared_services:$PYTHONPATH"

# 3. SSL Bridge
# Standardize certificates for OpenAI, Google, and Postgres
CERTS=$(python -c "import certifi; print(certifi.where())")
export SSL_CERT_FILE="$CERTS"
export REQUESTS_CA_BUNDLE="$CERTS"
export HTTPX_CA_BUNDLE="$CERTS"

# 4. --- Database Connectivity Diagnostic ---
echo "🔍 ARCHITECT DIAGNOSTIC: Testing Database Connection..."
python3 << END
import socket, os, urllib.parse
try:
    url = os.getenv("DATABASE_URL", "")
    if not url:
        print("❌ ERROR: DATABASE_URL variable is empty.")
        exit(0)
    p = urllib.parse.urlparse(url)
    host, port = p.hostname, (p.port or 5432)
    print(f"Testing route to {host}:{port}...")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((host, port))
    print("✅ NETWORK SUCCESS: DB Port is reachable.")
    s.close()
except Exception as e:
    print(f"❌ NETWORK FAILURE: Cannot reach DB host. Error: {e}")
END
# -------------------------------------

echo "🚀 Starting Neufin Hub..."
cd /app/backend/shared_services
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8000}"