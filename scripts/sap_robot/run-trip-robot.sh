#!/bin/bash
# Console runner for the SAP trip robot — launched in its own window by
# sap-robot-edge.bat (the Review 🤖 button). Auto mode: newest
# trip_submit_*.json from Downloads, waits for the Other Expense screen,
# then fills every line. The flock keeps a double-click from running two
# robots into the same form.
#
# Everything the robot prints is teed to RUNLOG, so the outcome survives the
# window closing — on 2026-08-04 the console reported its result to a window
# that was gone by the time anyone asked what happened.
LOG=/tmp/sap-robot-console.log
RUNLOG=/tmp/sap-robot-run.log
note() { echo "[$(date '+%F %T')] $*" >> "$LOG"; }
note "wrapper begin (python3=$(command -v python3 || echo MISSING))"

# Lock scope = the python run only. A finished window sitting at a prompt
# must NOT block the next run (2026-08-03).
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
    python3 -u scripts/sap_trip_robot.py "$@" 2>&1 | tee "$RUNLOG"
    exit "${PIPESTATUS[0]}"
) 9>"/tmp/sap-trip-robot.lock"
rc=$?
note "run exit=$rc"

# A clean run closes on its own — a window that has to be dismissed is one
# more thing to do, and the log holds everything it was showing. A failure
# keeps the window up, because that is the one time the text still matters.
echo
if [ "$rc" -eq 0 ]; then
    echo "done — this window closes in 5 seconds. Full log: $RUNLOG"
    sleep 5
else
    echo "finished with errors (exit $rc). Full log: $RUNLOG"
    read -r -p "press Enter to close this window"
fi
