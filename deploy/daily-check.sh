#!/bin/bash
# Daily ops check for the wayfinder droplet. Cron: 23:00 UTC (= 08:00 KST).
# Complements wayfinder-monitor.sh (5-min health + auto-restart): this one
# watches the slow-moving stuff — backup freshness/integrity, disk, staging.
# Silent when everything is fine; Telegram alert only on problems.

TG_ENV="/root/.tg-alert.env"   # TG_TOKEN=... / TG_CHAT=...
[ -f "$TG_ENV" ] && . "$TG_ENV"

PROBLEMS=""

# 1. Daily backup: newest tar must be <26h old and readable.
LATEST=$(ls -t /root/backups/appdata-*.tar.gz 2>/dev/null | head -1)
if [ -z "$LATEST" ]; then
    PROBLEMS="$PROBLEMS\n• 백업 tar가 없음 (/root/backups)"
else
    AGE_H=$(( ( $(date +%s) - $(stat -c %Y "$LATEST") ) / 3600 ))
    if [ "$AGE_H" -gt 26 ]; then
        PROBLEMS="$PROBLEMS\n• 최신 백업이 ${AGE_H}시간 전 ($(basename "$LATEST")) — 일일 백업 실패 의심"
    fi
    if ! tar -tzf "$LATEST" > /dev/null 2>&1; then
        PROBLEMS="$PROBLEMS\n• 백업 tar 손상: $(basename "$LATEST")"
    fi
fi

# 2. Disk usage.
DISK_PCT=$(df / --output=pcent | tail -1 | tr -dc '0-9')
if [ "$DISK_PCT" -gt 85 ]; then
    PROBLEMS="$PROBLEMS\n• 디스크 사용률 ${DISK_PCT}%"
fi

# 3. Staging health (prod is covered by the 5-min monitor).
ST=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 http://localhost:8081/health 2>/dev/null)
if [ "$ST" != "200" ]; then
    PROBLEMS="$PROBLEMS\n• staging(:8081) health $ST"
fi

if [ -n "$PROBLEMS" ] && [ -n "$TG_TOKEN" ]; then
    MSG="🩺 Wayfinder 일일 점검 이상 ($(date '+%Y-%m-%d %H:%M UTC'))$PROBLEMS"
    curl -s -X POST "https://api.telegram.org/bot${TG_TOKEN}/sendMessage" \
        -d chat_id="${TG_CHAT}" --data-urlencode text="$(echo -e "$MSG")" > /dev/null 2>&1
fi
echo "[$(date '+%F %T')] daily-check done problems='$(echo -e "$PROBLEMS" | tr '\n' ';')'" >> /root/backups/daily-check.log
