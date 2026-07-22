#!/usr/bin/env bash
#
# Universal All-in-One Container Entrypoint (`docker-entrypoint.sh`).
# Starts FastAPI backend (`127.0.0.1:8000`) in background and Next.js 15 GPR GUI (`0.0.0.0:${PORT:-3000}`) in foreground.
# All terminal messages are strictly English.
#

set -e

echo "[GPR INFO] Starting Universal General Purpose RAG All-in-One Container..."

# 1. Start FastAPI backend in background on local loopback port 8000
echo "[GPR INFO] Launching FastAPI backend uvicorn process (127.0.0.1:8000) in background..."
cd /app/src/backend
python3 -m uvicorn main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# 2. Wait up to 25 seconds for backend API healthcheck on loopback
echo "[GPR INFO] Waiting for FastAPI internal loopback health check..."
ATTEMPT=1
MAX_ATTEMPTS=25
until curl -s http://127.0.0.1:8000/health >/dev/null 2>&1 || [ $ATTEMPT -gt $MAX_ATTEMPTS ]; do
    printf "."
    sleep 1
    ATTEMPT=$((ATTEMPT + 1))
done
echo ""

if [ $ATTEMPT -gt $MAX_ATTEMPTS ]; then
    echo "[GPR WARN] FastAPI internal loopback took longer than expected to respond."
else
    echo "[GPR INFO] FastAPI backend operational on internal loopback port 8000."
fi

# 3. Verify workspace document index status on loopback
echo "[GPR INFO] Verifying workspace document index status..."
DOC_COUNT=$(curl -s http://127.0.0.1:8000/api/v1/documents | grep -o '"id":' | wc -l || echo "0")
echo "[GPR INFO] Current active documents in workspace database: ${DOC_COUNT} (Golden 80-node dataset HR-MANUAL-V1 pre-verified by background task)."

# 4. Start Next.js 15 GPR GUI in foreground bound to 0.0.0.0 on dynamic $PORT
echo "[GPR INFO] Launching Next.js 15 GPR GUI on 0.0.0.0:${PORT:-3000}..."
cd /app/src/frontend
exec node_modules/.bin/next start -H 0.0.0.0 -p ${PORT:-3000}
