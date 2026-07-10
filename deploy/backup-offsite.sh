#!/bin/bash
# Off-site backup: encrypt the latest appdata tar and push it to the private
# GitHub repo jonghakang01/wayfinder-backup. Survives loss of the DO account.
#
# Runs on prod via cron (04:40 KST, after backup-appdata.sh at 04:30).
# Requirements on the server (installed 2026-07-09):
#   /root/.wayfinder-backup-key        encryption passphrase (copy kept on local PC)
#   /root/.ssh/wayfinder_backup        write deploy key for the backup repo
#
# Restore (on any machine holding the key file):
#   git clone git@github.com:jonghakang01/wayfinder-backup.git
#   openssl enc -d -aes-256-cbc -pbkdf2 -pass file:~/.wayfinder-backup-key \
#     -in appdata-latest.tar.gz.enc -out appdata.tar.gz
#   tar xzf appdata.tar.gz
# Older versions: git log / git checkout <sha> -- appdata-latest.tar.gz.enc

BACKUP_DIR="/root/backups"
KEY_FILE="/root/.wayfinder-backup-key"
SSH_KEY="/root/.ssh/wayfinder_backup"
REPO_DIR="/root/backup-offsite-repo"
REPO_URL="git@github.com:jonghakang01/wayfinder-backup.git"
export GIT_SSH_COMMAND="ssh -i $SSH_KEY -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

latest=$(ls -1t "$BACKUP_DIR"/appdata-*.tar.gz 2>/dev/null | head -1)
if [ -z "$latest" ]; then
    echo "[offsite] no local backup tar found in $BACKUP_DIR — run backup-appdata.sh first"
    exit 1
fi
if [ ! -f "$KEY_FILE" ]; then
    echo "[offsite] missing key file $KEY_FILE"
    exit 1
fi

if [ ! -d "$REPO_DIR/.git" ]; then
    git clone "$REPO_URL" "$REPO_DIR" || exit 1
fi
cd "$REPO_DIR" || exit 1
git pull --rebase --quiet || true

openssl enc -aes-256-cbc -pbkdf2 -pass "file:$KEY_FILE" \
    -in "$latest" -out "$REPO_DIR/appdata-latest.tar.gz.enc" || exit 1

git add appdata-latest.tar.gz.enc
if git diff --cached --quiet; then
    echo "[offsite] no changes since last push"
    exit 0
fi
git -c user.name="wayfinder-backup" -c user.email="backup@wayfinder" \
    commit -m "backup $(basename "$latest") $(date '+%Y-%m-%d %H:%M %Z')" --quiet
git push --quiet && echo "[offsite] pushed $(basename "$latest") (encrypted)"
