#!/bin/bash
set -e

# 1. Activate Virtual Environment
export VIRTUAL_ENV="/app/venv"
export PATH="/app/venv/bin:$PATH"

# 2. Strict Library Pathing
export LD_LIBRARY_PATH="/nix/var/nix/profiles/default/lib:/app/venv/lib:$LD_LIBRARY_PATH"
export PYTHONPATH="/app/backend:/app/backend/shared_services:$PYTHONPATH"

# 3. Secure SSL Handshake
# Force Python and C-libs (libpq) to use the certifi bundle
CERTS=$(python -c "import certifi; print(certifi.where())")
export SSL_CERT_FILE="$CERTS"
export REQUESTS_CA_BUNDLE="$CERTS"
export CURL_CA_BUNDLE="$CERTS"

# 4. --- ARCHITECT DIAGNOSTIC & IPv4 FORCING ---
echo "🔍 DIAGNOSTIC: Testing Database Connection..."
python3 << END
import socket, os, urllib.parse
try:
    url = os.getenv("DATABASE_URL", "")
    p = urllib.parse.urlparse(url)
    host = p.hostname
    port = p.port or 5432
    print(f"Resolving {host}...")
    # Force IPv4 resolution to prevent OSError on IPv6-only hosts
    ipv4 = socket.gethostbyname(host)
    print(f"✅ Resolved to IPv4: {ipv4}")
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5)
    s.connect((ipv4, port))
    print("✅ NETWORK: Connection successful.")
    s.close()
except Exception as e:
    print(f"❌ NETWORK FAILURE: {e}")
END
# ----------------------------------------------

echo "🚀 Starting Neufin Hub..."
cd /app/backend/shared_services
# Using PORT 8080 as per your uvicorn log
exec uvicorn main:app --host 0.0.0.0 --port "${PORT:-8080}"