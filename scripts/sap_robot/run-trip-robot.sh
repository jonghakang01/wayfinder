#!/bin/bash
# Console runner for the SAP trip robot — launched in its own window by
# sap-robot-edge.bat (the Review 🤖 button). Auto mode: newest
# trip_submit_*.json from Downloads, waits for the Other Expense screen,
# then fills every line. The flock keeps a double-click from running two
# robots into the same form. Every run leaves a trail in LOG so a closed
# window is still diagnosable from WSL.
LOG=/tmp/sap-robot-console.log
note() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }
note "wrapper begin (python3=$(command -v python3 || echo MISSING))"

# Lock scope = the python run only. A finished window sitting at the
# final "press Enter" prompt must NOT block the next run (2026-08-03).
(
    if ! flock -n 9; then
        note "refused: another run holds the lock"
        echo "another robot run is already active — finish or close it first."
        exit 9
    fi
    if ! cd "$HOME/webapp"; then
        note "refused: cd $HOME/webapp failed"
        echo "cannot cd to $HOME/webapp"
        exit 8
    fi
    export LD_LIBRARY_PATH="$HOME/.local/chromium-libs"
    python3 -u scripts/sap_trip_robot.py "$@"
) 9>"/tmp/sap-trip-robot.lock"
rc=$?
note "run exit=$rc"
echo
read -r -p "press Enter to close this window"
