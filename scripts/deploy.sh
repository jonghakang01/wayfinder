#!/bin/bash
# Deploy current branch to production by adding [deploy] tag to commits.
# Run this when you actually want to push to production (134.209.62.57).

set -e

cd "$(dirname "$0")/.."

# Check if there are unpushed commits
UNPUSHED=$(git log @{u}..HEAD --oneline 2>/dev/null | wc -l)
if [ "$UNPUSHED" -eq 0 ]; then
    echo "ℹ️  No unpushed commits."
    echo "   Add [deploy] to your next commit message, or trigger manually:"
    echo "   gh workflow run 'Deploy to Server'"
    exit 0
fi

echo "🚀 Triggering production deploy for $UNPUSHED commit(s)..."

# Amend last commit to add [deploy] tag if not present
LAST_MSG=$(git log -1 --pretty=%B)
if [[ "$LAST_MSG" != *"[deploy]"* ]]; then
    git commit --amend -m "$LAST_MSG [deploy]" --no-edit 2>/dev/null || \
        git commit --amend -m "$(git log -1 --pretty=%B) [deploy]"
    echo "✅ Added [deploy] tag to last commit"
fi

git push --force-with-lease

echo ""
echo "🎉 Deployment triggered. Monitor:"
echo "   gh run watch"
echo "   curl http://134.209.62.57/health"
