@echo off
REM SAP trip-submission robot: Edge in remote-control mode.
REM One click does everything: starts the WSL<->Edge CDP relay (if not
REM already running), opens Knox Portal + GTE as tabs in a dedicated
REM "SAP Robot" profile, AND starts the robot console — it grabs the
REM newest trip_submit_*.json from Downloads and waits until you reach
REM the Other Expense screen, then fills on its own.
REM Your normal Edge windows are untouched.

powershell -NoProfile -Command "$gw=(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias '*WSL*' -ErrorAction SilentlyContinue).IPAddress | Select-Object -First 1; if($gw -and -not (Get-NetTCPConnection -LocalPort 9223 -State Listen -ErrorAction SilentlyContinue)) { Start-Process -WindowStyle Hidden python -ArgumentList ('\"C:\Users\Jongha Kang\Desktop\sap-robot\cdp_relay.py\"',$gw,'9223','9222') -RedirectStandardOutput 'C:\Users\Jongha Kang\Desktop\sap-robot\relay.log' -RedirectStandardError 'C:\Users\Jongha Kang\Desktop\sap-robot\relay.err' }"

start msedge.exe --remote-debugging-port=9222 --user-data-dir="%LOCALAPPDATA%\EdgeSAPRobot" --no-first-run "http://w2.samsung.net/portalapp/home" "http://gate3.cheil.com/gte/exp_2010_m.do"

start "SAP Trip Robot" wsl.exe bash -lc "~/webapp/scripts/sap_robot/run-trip-robot.sh"
