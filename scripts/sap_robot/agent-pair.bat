@echo off
REM Protocol handler for wayfinder-agent:// — Windows hands us the whole URL.
REM Writes the agent's config on the WSL side and restarts it, so pairing is a
REM single click on the Review page with no terminal and no file editing.

setlocal
set LOG=%USERPROFILE%\Desktop\sap-agent-pair.log
echo === pair %DATE% %TIME% === >> "%LOG%"

REM The URL carries the token, so it must not be echoed anywhere. $HOME rather
REM than a hardcoded path, because the next PC to run this is not this one.
wsl.exe -e bash -lc "python3 \"$HOME/webapp/scripts/sap_robot/agent_pair.py\" \"$1\"" _ "%~1" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo Pairing failed — see %LOG%
  timeout /t 8 >nul
  endlocal
  exit /b 1
)

REM Pick the new token up straight away rather than at the next logon.
schtasks /end /tn "WayfinderAgent" >> "%LOG%" 2>&1
schtasks /run /tn "WayfinderAgent" >> "%LOG%" 2>&1

echo This PC is paired. The agent is running — go back to the browser.
timeout /t 5 >nul
endlocal
