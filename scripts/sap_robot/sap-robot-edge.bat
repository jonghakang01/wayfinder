@echo off
REM SAP trip-submission robot: Edge in remote-control mode.
REM Uses a dedicated "SAP Robot" profile - sign in to SAP once there; the
REM session sticks for next runs. Your normal Edge windows are untouched.
start msedge.exe --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\EdgeSAPRobot" --no-first-run
