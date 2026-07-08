#!/bin/bash
# One-time staging environment setup. RUN ON THE PROD SERVER (via SSH).
# Idempotent — safe to re-run. Creates a staging instance on :8081 with
# data isolated from prod (~/.appdata-staging), driven by systemd.
set -e

REPO_URL="https://github.com/jonghakang01/wayfinder.git"
STAGING_DIR="$HOME/webapp-staging"
DATA_ROOT="$HOME/.appdata-staging"
PORT=8081
SERVICE=wayfinder-staging

echo "▶ Staging setup: $STAGING_DIR on :$PORT (data → $DATA_ROOT)"

# 1. Clone or update the staging checkout
if [ ! -d "$STAGING_DIR/.git" ]; then
    git clone "$REPO_URL" "$STAGING_DIR"
fi
cd "$STAGING_DIR" && git pull origin main

# 2. Staging .env — seed from prod once, then keep independent.
#    WAYFINDER_DATA_ROOT/PORT come from systemd (below), NOT from .env.
if [ ! -f "$STAGING_DIR/.env" ] && [ -f "$HOME/webapp/.env" ]; then
    cp "$HOME/webapp/.env" "$STAGING_DIR/.env"
    echo "  seeded .env from prod"
fi
mkdir -p "$DATA_ROOT"

# 3. Python deps (same set as prod)
pip3 install openpyxl anthropic google-genai google-auth google-auth-oauthlib \
    google-api-python-client fpdf2 Pillow --break-system-packages -q 2>/dev/null || true

# 4. systemd unit — Environment= wins over server.py's .env setdefault,
#    so data isolation and port are guaranteed here.
SUDO=""; [ "$(id -u)" -ne 0 ] && SUDO="sudo"
$SUDO tee /etc/systemd/system/$SERVICE.service > /dev/null <<UNIT
[Unit]
Description=Wayfinder Staging
After=network.target

[Service]
Type=simple
User=$USER
WorkingDirectory=$STAGING_DIR
Environment=PORT=$PORT
Environment=WAYFINDER_DATA_ROOT=$DATA_ROOT
ExecStart=/usr/bin/python3 $STAGING_DIR/server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
UNIT

$SUDO systemctl daemon-reload
$SUDO systemctl enable $SERVICE
$SUDO systemctl restart $SERVICE

sleep 2
if curl -sf "http://localhost:$PORT/health" > /dev/null; then
    echo "✅ Staging up → http://localhost:$PORT  (data isolated at $DATA_ROOT)"
else
    echo "❌ Staging health check failed. Check: journalctl -u $SERVICE -n 30"
    exit 1
fi
