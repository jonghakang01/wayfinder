#!/bin/bash
# Daily backup of user data (~/.appdata) with 14-day rotation.
# Installed on prod via cron (see deploy/setup-backup.sh). Idempotent.
set -e

SRC="$HOME/.appdata"
DEST="$HOME/backups"
KEEP_DAYS=14
STAMP=$(date +%Y%m%d)

mkdir -p "$DEST"
tar czf "$DEST/appdata-$STAMP.tar.gz" -C "$HOME" .appdata

# Rotate: drop archives older than KEEP_DAYS
find "$DEST" -name "appdata-*.tar.gz" -mtime +$KEEP_DAYS -delete

echo "backup ok: $DEST/appdata-$STAMP.tar.gz ($(du -h "$DEST/appdata-$STAMP.tar.gz" | cut -f1)), total $(ls "$DEST" | wc -l) archives"
