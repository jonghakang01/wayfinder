#!/bin/bash
# Console runner for the SAP trip robot — launched in its own window by
# sap-robot-edge.bat (the Review 🤖 button). Auto mode: newest
# trip_submit_*.json from Downloads, waits for the Other Expense screen,
# then fills every line. The flock keeps a double-click from running two
# robots into the same form.
exec 9>"/tmp/sap-trip-robot.lock"
if ! flock -n 9; then
    echo "another robot run is already active — finish or close it first."
    read -r -p "press Enter to close this window"
    exit 1
fi
cd "$HOME/webapp" || exit 1
export LD_LIBRARY_PATH="$HOME/.local/chromium-libs"
python3 scripts/sap_trip_robot.py "$@"
echo
read -r -p "press Enter to close this window"
