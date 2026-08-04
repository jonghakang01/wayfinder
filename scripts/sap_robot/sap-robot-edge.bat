@echo off
REM SAP trip-submission robot: start the robot console. That is all it does.
REM
REM It used to also start the relay and open Edge. On 2026-08-04 the corporate
REM security agent killed this tree ~6 seconds in — after the console and relay
REM had detached but BEFORE the Edge line ran, so the browser never appeared
REM and the button looked dead. Every extra step here is another step that can
REM be cut off, so opening Edge moved to a shortcut the user double-clicks:
REM   Desktop\Open Robot Edge.bat  (repo: scripts/sap_robot/open-robot-edge.bat)
REM
REM The robot waits up to 15 minutes for the entry screen, so the order does
REM not matter — press this before or after opening Edge.
REM Steps log to Desktop\sap-robot-bat.log.

set BATLOG=%USERPROFILE%\Desktop\sap-robot-bat.log
echo [%date% %time%] --- robot console requested --- >> "%BATLOG%"

powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/k','wsl.exe','bash','-lc','~/webapp/scripts/sap_robot/run-trip-robot.sh'"
echo [%date% %time%] robot console detached (err=%errorlevel%) >> "%BATLOG%"
