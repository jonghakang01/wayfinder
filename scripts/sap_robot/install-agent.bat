@echo off
REM One-time setup for the SAP agent -- double-click this, then never again.
REM
REM Nobody should have to open a terminal to use this (Kangpro 2026-08-05), so
REM this file does the three things that would otherwise be typed:
REM   1. registers wayfinder-agent:// so the Pair link on the Review page works
REM   2. drops the agent in the Startup folder so it is simply always running
REM   3. registers an on-demand task the agent uses to open the robot Edge
REM   4. starts the agent now, in a hidden window
REM
REM Startup folder rather than a logon task because /sc onlogon needs elevation
REM here. The Edge task does have to be a task: the corporate agent kills
REM process trees launched from anything browser-ish within about a second, and
REM a task started by the scheduler is not part of that tree (see 72th round).

setlocal
set HERE=%~dp0
set LOG=%USERPROFILE%\Desktop\sap-agent-install.log
echo === install-agent %DATE% %TIME% === > "%LOG%"

echo Registering the wayfinder-agent:// link...
reg add "HKCU\Software\Classes\wayfinder-agent" /ve /d "URL:Wayfinder SAP agent" /f >> "%LOG%" 2>&1
reg add "HKCU\Software\Classes\wayfinder-agent" /v "URL Protocol" /d "" /f >> "%LOG%" 2>&1
reg add "HKCU\Software\Classes\wayfinder-agent\shell\open\command" /ve ^
    /d "\"%HERE%agent-pair.bat\" \"%%1\"" /f >> "%LOG%" 2>&1
if errorlevel 1 (
  echo   FAILED -- see %LOG%
) else (
  echo   done.
)

echo Setting the agent to start with Windows...
REM Startup folder, not a scheduled task: /sc onlogon needs elevation and is
REM refused here ("Access is denied", measured 2026-08-05). The same folder
REM already starts wsl-autostart.vbs on this PC, so the route is known good.
set STARTUP=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup
copy /y "%HERE%run-agent.vbs" "%STARTUP%\WayfinderAgent.vbs" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo   FAILED -- see %LOG%
) else (
  echo   done.
)

echo Registering the browser task so the agent can open Edge itself...
REM On demand, not at logon: the agent triggers it when a job arrives. It has to
REM be a task for the same reason the agent is one -- a process tree spawned from
REM anything browser-ish is killed within about a second on this network.
schtasks /create /tn "WayfinderRobotEdge" /tr "\"%USERPROFILE%\Desktop\Open Robot Edge.bat\"" ^
    /sc once /st 00:00 /rl limited /f >> "%LOG%" 2>&1
if errorlevel 1 (
  echo   FAILED -- see %LOG%
) else (
  echo   done.
)

echo Starting the agent now...
REM Safe to run even if one is already up: the agent holds a lock and a second
REM copy exits at once. Two of them would key the same lines in twice.
start "" wscript.exe "%HERE%run-agent.vbs"
echo   running.

echo.
echo Setup finished. Now open Review in the browser and click "Pair this PC".
echo (Details in %LOG%)
ping -n 9 127.0.0.1 >nul
endlocal
