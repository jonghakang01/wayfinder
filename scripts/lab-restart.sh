#!/bin/bash
# Start a lab instance of Wayfinder on port 8090 (separate from prod 8080).

set -e

PORT="${1:-8090}"

echo "🔄 Starting lab instance on port $PORT..."

# Kill existing process on this port
lsof -ti:"$PORT" | xargs kill -9 2>/dev/null || true
sleep 0.5

cd "$(dirname "$0")/.."
PORT="$PORT" python3 server.py &>/tmp/server-lab.log &
LAB_PID=$!

echo "⏳ Waiting for lab server..."
for i in {1..15}; do
    if curl -sf "http://localhost:${PORT}/health" >/dev/null 2>&1; then
        echo "✅ Lab ready at http://localhost:${PORT} (PID $LAB_PID)"
        exit 0
    fi
    sleep 1
done

echo "❌ Lab server failed to start. Check /tmp/server-lab.log"
tail -20 /tmp/server-lab.log
exit 1
