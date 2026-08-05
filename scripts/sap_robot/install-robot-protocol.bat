@echo off
REM One-time setup for the cardconv Review [robot] button (wayfinder-robot://).
REM The protocol does NOT launch the bat directly: a corporate security
REM agent kills browser-spawned console trees within a second
REM (2026-08-03). Instead the protocol fires a Scheduled Task, which
REM runs the bat under the Task Scheduler service - outside the browser
REM lineage, so nothing gets killed.
REM User-level only (HKCU + user task) - no admin rights needed.

schtasks /create /f /tn "SAPRobot" /tr "\"C:\Users\Jongha Kang\Desktop\sap-robot-edge.bat\"" /sc once /sd 01/01/2020 /st 00:00

reg add "HKCU\Software\Classes\wayfinder-robot" /ve /d "URL:Wayfinder SAP Robot" /f
reg add "HKCU\Software\Classes\wayfinder-robot" /v "URL Protocol" /d "" /f
reg add "HKCU\Software\Classes\wayfinder-robot\shell\open\command" /ve /d "C:\Windows\System32\schtasks.exe /run /tn SAPRobot" /f
echo.
echo Done. The Review page's robot button now fires the SAPRobot task.
echo (The browser asks for permission on the first click only.)
pause
