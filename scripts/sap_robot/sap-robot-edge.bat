@echo off
REM SAP trip-submission robot: Edge in remote-control mode.
REM Opens Knox Portal + GTE (Business Trip Maintain) as tabs on launch.
REM Uses a dedicated "SAP Robot" profile - sign in once there; the session
REM sticks for next runs. Your normal Edge windows are untouched.
start msedge.exe --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\EdgeSAPRobot" --no-first-run "http://w2.samsung.net/portalapp/home" "http://gate3.cheil.com/gte/exp_2010_m.do"
