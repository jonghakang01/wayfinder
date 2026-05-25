#!/bin/bash
# Pre-deploy smoke test — run by QA (태양) before git push
# Usage: bash scripts/smoke-test.sh [base_url]
BASE="${1:-http://localhost:8765}"
PASS=0
FAIL=0

check() {
    local desc="$1" url="$2" expect="$3"
    local status
    status=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null)
    if [ "$status" = "$expect" ]; then
        echo "  ✓ $desc ($status)"
        PASS=$((PASS+1))
    else
        echo "  ✗ $desc — expected $expect, got $status"
        FAIL=$((FAIL+1))
    fi
}

echo "=== Wayfinder Smoke Test: $BASE ==="
check "Health endpoint"         "$BASE/health"   "200"
check "Login page"              "$BASE/login"    "200"
check "Root redirects to login" "$BASE/"         "302"
check "Todo (auth required)"    "$BASE/todo"     "302"
check "Habit (auth required)"   "$BASE/habit"    "302"
check "Report (auth required)"    "$BASE/report"     "302"
check "Dashboard (auth required)" "$BASE/dashboard" "302"
check "Static CSS"              "$BASE/static/style.css" "200"

echo ""
echo "Result: $PASS passed, $FAIL failed"
if [ $FAIL -gt 0 ]; then
    echo "BLOCKED: Fix failures before deploying."
    exit 1
else
    echo "OK: Safe to deploy."
    exit 0
fi
