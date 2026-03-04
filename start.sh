#!/bin/bash
set -e

# 1. Activate Environment
export VIRTUAL_ENV="/app/venv"
export PATH="/app/venv/bin:$PATH"

# 2. Library Pathing
# Including /nix/var/nix/profiles/default/lib ensures libpq is found
export LD_LIBRARY_PATH="/nix/var/nix/profiles/default/lib:/usr/lib/x86_64-linux-gnu:$LD_LIBRARY_PATH"
export PYTHONPATH="/app/backend:/app/backend/shared_services:$PYTHONPATH"

# 3. SSL Bridge
CERTS=$(python -c "import certifi; print(certifi.where())")
export SSL_CERT_FILE="$CERTS"
export REQUESTS_CA_BUNDLE="$CERTS"
export HTTPX_CA_BUNDLE="$CERTS"

# 4. --- DB CONNECTIVITY DIAGNOSTIC ---
echo "🔍 DIAGNOSTIC: Testing Database Connection..."
python3 << END
import socket, os, urllib.parse
try:
    url = os.getenv("DATABASE_URL", "")
    p = urllib.parse.urlparse(url)
    host = p.hostname
    port = p.port or 5432
    print(f"Attempting to reach {host}:{port}...")
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