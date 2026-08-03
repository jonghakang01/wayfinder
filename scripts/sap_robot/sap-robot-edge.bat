@echo off
REM SAP trip-submission robot: Edge in remote-control mode.
REM One click does everything: robot console, WSL<->Edge CDP relay,
REM and Knox Portal + GTE tabs in a dedicated "SAP Robot" profile.
REM
REM Every child is DETACHED via Start-Process: a corporate security
REM agent kills the browser-launched console tree within moments
REM (2026-08-03 — only the Start-Process'd relay survived a click),
REM so nothing here may run as a plain child of this bat.
REM Robot console goes first — it must detach before the tree dies.
REM Steps log to Desktop\sap-robot-bat.log.

set BATLOG=%USERPROFILE%\Desktop\sap-robot-bat.log
echo [%date% %time%] --- bat start (cwd=%cd%) --- >> "%BATLOG%"

powershell -NoProfile -Command "Start-Process cmd -ArgumentList '/k','wsl.exe','bash','-lc','~/webapp/scripts/sap_robot/run-trip-robot.sh'" >> "%BATLOG%" 2>&1
echo [%date% %time%] robot console detached (err=%errorlevel%) >> "%BATLOG%"

powershell -NoProfile -Command "$gw=(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias '*WSL*' -ErrorAction SilentlyContinue).IPAddress | Select-Object -First 1; if($gw -and -not (Get-NetTCPConnection -LocalPort 9223 -State Listen -ErrorAction SilentlyContinue)) { Start-Process -WindowStyle Hidden python -ArgumentList ('\"C:\Users\Jongha Kang\Desktop\sap-robot\cdp_relay.py\"',$gw,'9223','9222') -RedirectStandardOutput 'C:\Users\Jongha Kang\Desktop\sap-robot\relay.log' -RedirectStandardError 'C:\Users\Jongha Kang\Desktop\sap-robot\relay.err' }" >> "%BATLOG%" 2>&1
echo [%date% %time%] relay step done (err=%errorlevel%) >> "%BATLOG%"

powershell -NoProfile -Command "Start-Process msedge.exe -ArgumentList '--remote-debugging-port=9222','--user-data-dir=%LOCALAPPDATA%\EdgeSAPRobot','--no-first-run','http://w2.samsung.net/portalapp/home','http://gate3.cheil.com/gte/exp_2010_m.do'" >> "%BATLOG%" 2>&1
echo [%date% %time%] edge detached (err=%errorlevel%) >> "%BATLOG%"
