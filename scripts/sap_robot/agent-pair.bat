@echo off
REM Protocol handler for wayfinder-agent:// -- Windows hands us the whole URL.
REM Writes the agent's config on the WSL side and restarts it, so pairing is a
REM single click on the Review page with no terminal and no file editing.

setlocal
set LOG=%USERPROFILE%\Desktop\sap-agent-pair.log
echo === pair %DATE% %TIME% === >> "%LOG%"

REM The URL carries the token, so it must not be echoed anywhere. $HOME rather
REM than a hardcoded path, because the next PC to run this is not this one.
wsl.exe -e bash -lc "python3 \"$HOME/webapp/scripts/sap_robot/agent_pair.py\" \"$1\"" _ "%~1" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo Pairing failed -- see %LOG%
  ping -n 9 127.0.0.1 >nul
  endlocal
  exit /b 1
)

REM Start one if none is running. No restart is needed to pick the new token
REM up: the agent re-reads its config every poll, and a second copy exits on
REM the lock rather than keying the same lines in twice.
start "" wscript.exe "%~dp0run-agent.vbs"

echo This PC is paired. The agent is running -- go back to the browser.
ping -n 6 127.0.0.1 >nul
endlocal
