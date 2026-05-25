#!/bin/bash
# Wayfinder health monitor - runs on production server
HEALTH_URL="http://localhost:8765/health"
LOG="/var/log/wayfinder-monitor.log"
EMAIL="jongha.kang01@gmail.com"
APP="wayfinder"

STATUS=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL" 2>/dev/null)
TS=$(date '+%Y-%m-%d %H:%M:%S')

if [ "$STATUS" != "200" ]; then
    echo "[$TS] FAIL status=$STATUS" >> "$LOG"
    # restart service
    systemctl restart "$APP"
    sleep 5
    STATUS2=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$HEALTH_URL" 2>/dev/null)
    if [ "$STATUS2" = "200" ]; then
        MSG="[Wayfinder] Auto-recovered at $TS (was $STATUS, restarted OK)"
    else
        MSG="[Wayfinder] DOWN at $TS (status=$STATUS, restart failed, now=$STATUS2)"
    fi
    echo "[$TS] $MSG" >> "$LOG"
    echo "$MSG" | mail -s "Wayfinder Alert" "$EMAIL" 2>/dev/null || true
else
    echo "[$TS] OK" >> "$LOG"
fi
