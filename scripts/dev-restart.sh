#!/bin/bash
# Restart local dev server with latest code and verify it's healthy.
# Run this after every code change before testing on localhost.

set -e

echo "🔄 Restarting local dev server..."

# Kill existing server
lsof -ti:8080 | xargs kill -9 2>/dev/null || true
sleep 1

# Start fresh
cd "$(dirname "$0")/.."
python3 server.py &>/tmp/server.log &
SERVER_PID=$!

# Wait for server to be ready
echo "⏳ Waiting for server..."
for i in {1..10}; do
    if curl -sf http://localhost:8080/health > /dev/null 2>&1; then
        echo "✅ Server ready at http://localhost:8080 (PID $SERVER_PID)"
        exit 0
    fi
    sleep 1
done

echo "❌ Server failed to start. Check /tmp/server.log"
cat /tmp/server.log | tail -20
exit 1
