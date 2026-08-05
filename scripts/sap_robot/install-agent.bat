@echo off
REM One-time setup for the SAP agent — double-click this, then never again.
REM
REM Nobody should have to open a terminal to use this (강프로 2026-08-05), so
REM this file does the three things that would otherwise be typed:
REM   1. registers wayfinder-agent:// so the Pair link on the Review page works
REM   2. creates a logon task so the agent is simply always running
REM   3. starts it now, in a hidden window
REM
REM The scheduled task matters for more than convenience: the corporate agent
REM kills process trees launched from a browser within about a second, and a
REM task started by the scheduler is not part of that tree (see 72차).

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
  echo   FAILED — see %LOG%
) else (
  echo   done.
)

echo Creating the logon task so the agent starts with Windows...
schtasks /create /tn "WayfinderAgent" /tr "wscript.exe \"%HERE%run-agent.vbs\"" ^
    /sc onlogon /rl limited /f >> "%LOG%" 2>&1
if errorlevel 1 (
  echo   FAILED — see %LOG%
) else (
  echo   done.
)

echo Starting the agent now...
schtasks /run /tn "WayfinderAgent" >> "%LOG%" 2>&1
if errorlevel 1 (
  echo   could not start it — it will start at your next logon.
) else (
  echo   running.
)

echo.
echo Setup finished. Now open Review in the browser and click "Pair this PC".
echo (Details in %LOG%)
timeout /t 8 >nul
endlocal
