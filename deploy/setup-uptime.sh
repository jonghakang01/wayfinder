#!/bin/bash
# One-shot: create a DigitalOcean Uptime check + down alert for prod.
# External to the droplet, so it catches droplet-level failure that the
# on-box monitor can't. Usage: DO_API_TOKEN=dop_v1_xxx bash deploy/setup-uptime.sh <alert-email>
set -e
[ -z "$DO_API_TOKEN" ] && { echo "DO_API_TOKEN env required (cloud.digitalocean.com → API → Tokens)"; exit 1; }
EMAIL="${1:?usage: setup-uptime.sh <alert-email>}"
API="https://api.digitalocean.com/v2"
AUTH="Authorization: Bearer $DO_API_TOKEN"

CHECK_ID=$(curl -s -X POST "$API/uptime/checks" -H "$AUTH" -H "Content-Type: application/json" -d '{
  "name": "wayfinder-prod-health",
  "type": "http",
  "target": "http://134.209.62.57:8080/health",
  "regions": ["us_west", "us_east"],
  "enabled": true
}' | python3 -c "import sys,json; print(json.load(sys.stdin)['check']['id'])")
echo "check created: $CHECK_ID"

curl -s -X POST "$API/uptime/checks/$CHECK_ID/alerts" -H "$AUTH" -H "Content-Type: application/json" -d "{
  \"name\": \"wayfinder-prod-down\",
  \"type\": \"down_global\",
  \"notifications\": {\"email\": [\"$EMAIL\"], \"slack\": []},
  \"period\": \"2m\"
}" | python3 -m json.tool
echo "done — alert email: $EMAIL"
