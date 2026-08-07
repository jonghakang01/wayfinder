#!/bin/bash
# Daily Drive batch OCR trigger — runs on prod via cron.
#
# This replaced the GitHub Actions schedule (2026-08-07): the workflow was a
# machine in another country SSHing in to run this one curl, its schedule fired
# 1-2.5h late every day, and on 8/6 GitHub never assigned a runner at all so
# the day was silently skipped. The batch endpoint itself scans the whole Drive
# folder and skips what is already handled, so a missed day self-heals — but
# the trigger should not be the fragile part.
#
# Install (idempotent):
#   cp ~/webapp/deploy/drive-sync.sh /root/drive-sync.sh && chmod +x /root/drive-sync.sh
#   crontab line:  0 7 * * * /root/drive-sync.sh >> /root/drive-sync.log 2>&1
#   (07:00 server-local = the 10:00 AM EDT the old workflow intended)
#
# Failure goes to Telegram — a red X on a page nobody watches is not an alert.
# Manual run any time: bash /root/drive-sync.sh

ENV_FILE="$HOME/webapp/.env"

get() { grep "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2-; }

notify() {
    local tok chat
    tok=$(get TELEGRAM_TOKEN); chat=$(get TG_ADMIN_CHAT_ID)
    [ -z "$tok" ] || [ -z "$chat" ] && return 0
    curl -sf -m 10 "https://api.telegram.org/bot${tok}/sendMessage" \
        --data-urlencode "chat_id=${chat}" \
        --data-urlencode "text=$1" >/dev/null || true
}

secret=$(get CARDCONV_BATCH_SECRET)
if [ -z "$secret" ]; then
    echo "[drive-sync] $(date -Is) no CARDCONV_BATCH_SECRET in $ENV_FILE"
    notify "⚠️ Drive sync: 서버에 CARDCONV_BATCH_SECRET이 없어 실행 못 함"
    exit 1
fi

result=$(curl -sf -m 600 -X POST http://localhost:8080/cardconv/batch/run \
    -H "X-Batch-Secret: $secret" -H "Content-Type: application/json" -d '{}')
rc=$?

if [ $rc -ne 0 ]; then
    echo "[drive-sync] $(date -Is) FAILED curl rc=$rc"
    notify "⚠️ Drive sync 실패 (curl rc=$rc) — 서버 로그: /root/drive-sync.log"
    exit 1
fi

echo "[drive-sync] $(date -Is) ok: $result"
# Quiet on success — a daily "it worked" ping trains you to ignore the channel.
