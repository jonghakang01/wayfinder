#!/bin/bash
# POV News batch pipeline: collect → cluster → analyze.
# Populates ~/.appdata/pov/pov_results.json which the /pov feed reads.
#
# Usage:
#   bash scripts/pov-pipeline.sh           # full run (collect → cluster → analyze)
#   bash scripts/pov-pipeline.sh collect   # single stage
#   bash scripts/pov-pipeline.sh cluster
#   bash scripts/pov-pipeline.sh analyze

set -e

cd "$(dirname "$0")/.."

# Load .env (ANTHROPIC_API_KEY etc.) — same vars server.py uses.
if [ -f .env ]; then
    set -a
    # shellcheck disable=SC1091
    . ./.env
    set +a
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "ERROR: ANTHROPIC_API_KEY not set (expected in webapp/.env)" >&2
    exit 1
fi

STAGE="${1:-all}"
echo "▶ POV pipeline stage: $STAGE"
python3 -m services.pov_pipeline "$STAGE"
