#!/usr/bin/env bash
# Push the Windows-side scripts to the Desktop, where they actually run.
#
# The repo copy is not what Windows executes. On 2026-08-05 the em-dash fix
# landed in git while the Desktop kept the broken files, so "Open Robot Edge"
# went on failing with its comments being run as commands — and the repo looked
# fine the whole time. Run this after touching anything under scripts/sap_robot.
#
#   bash scripts/sync-desktop-scripts.sh          # copy + verify
#   bash scripts/sync-desktop-scripts.sh --check  # verify only, non-zero on drift
set -u

SRC="$(cd "$(dirname "$0")/sap_robot" && pwd)"
DESK="/mnt/c/Users/Jongha Kang/Desktop"
CHECK_ONLY=0
[ "${1:-}" = "--check" ] && CHECK_ONLY=1

# repo name -> destination path (the Desktop uses friendlier names)
declare -A MAP=(
  ["open-robot-edge.bat"]="$DESK/Open Robot Edge.bat"
  ["sap-robot-edge.bat"]="$DESK/sap-robot-edge.bat"
  ["install-agent.bat"]="$DESK/sap-robot/install-agent.bat"
  ["agent-pair.bat"]="$DESK/sap-robot/agent-pair.bat"
  ["run-agent.vbs"]="$DESK/sap-robot/run-agent.vbs"
  ["install-robot-protocol.bat"]="$DESK/sap-robot/install-robot-protocol.bat"
  ["cdp_relay.py"]="$DESK/sap-robot/cdp_relay.py"
)

if [ ! -d "$DESK" ]; then
  echo "no Windows Desktop here — nothing to sync."
  exit 0
fi
mkdir -p "$DESK/sap-robot"

drift=0
for name in "${!MAP[@]}"; do
  src="$SRC/$name"
  dst="${MAP[$name]}"
  [ -f "$src" ] || { echo "  missing in repo: $name"; drift=1; continue; }
  # cmd.exe reads .bat in the OEM code page; one stray byte above 0x7E breaks
  # the parse (tests/test_windows_scripts_ascii.py guards the repo side). Only
  # .bat and .vbs go through that parser — Python reads its own files as UTF-8.
  if [[ "$name" == *.bat || "$name" == *.vbs ]] && LC_ALL=C grep -q '[^ -~	]' "$src"; then
    echo "  NON-ASCII, refusing to deploy: $name"
    drift=1
    continue
  fi
  if [ -f "$dst" ] && cmp -s "$src" "$dst"; then
    echo "  same: $name"
    continue
  fi
  drift=1
  if [ "$CHECK_ONLY" = "1" ]; then
    echo "  DRIFT: $name"
  else
    cp "$src" "$dst" && echo "  copied: $name -> $dst"
  fi
done

if [ "$CHECK_ONLY" = "1" ] && [ "$drift" != "0" ]; then
  echo "Desktop is out of date — run without --check."
  exit 1
fi
echo "done."
