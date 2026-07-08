#!/bin/bash
# Install version-controlled git hooks.
# Run once after cloning the repo (or after adding a new hook).
set -e

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

git config core.hooksPath scripts/hooks
chmod +x scripts/hooks/* 2>/dev/null || true

echo "✅ Git hooks installed → core.hooksPath = scripts/hooks"
echo "   Hooks under version control:"
for h in scripts/hooks/*; do
    [ -f "$h" ] && echo "     • $(basename "$h")"
done
