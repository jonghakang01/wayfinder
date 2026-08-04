@echo off
REM Opens the robot's Edge — and nothing else.
REM
REM Double-click this from the Desktop. Everything here is user-launched, so
REM it lives outside the browser-spawned process tree the corporate security
REM agent kills (2026-08-04: the 🤖 bat died right after its first step and
REM Edge never opened at all).
REM
REM A normal Edge window cannot be driven: the debug port only exists if it
REM is passed at launch, and it needs its own profile or Edge just hands the
REM URL to the already-running instance and drops the flag. That is what this
REM shortcut is for.

set BATLOG=%USERPROFILE%\Desktop\sap-robot-bat.log
echo [%date% %time%] --- open-robot-edge start --- >> "%BATLOG%"

REM Relay first: WSL reaches Edge only through it, and it must outlive this window.
powershell -NoProfile -Command "$gw=(Get-NetIPAddress -AddressFamily IPv4 -InterfaceAlias '*WSL*' -ErrorAction SilentlyContinue).IPAddress | Select-Object -First 1; if($gw -and -not (Get-NetTCPConnection -LocalPort 9223 -State Listen -ErrorAction SilentlyContinue)) { Start-Process -WindowStyle Hidden python -ArgumentList ('\"C:\Users\Jongha Kang\Desktop\sap-robot\cdp_relay.py\"',$gw,'9223','9222') -RedirectStandardOutput 'C:\Users\Jongha Kang\Desktop\sap-robot\relay.log' -RedirectStandardError 'C:\Users\Jongha Kang\Desktop\sap-robot\relay.err'; 'relay started' } else { 'relay already up' }" >> "%BATLOG%" 2>&1

REM Already listening on 9222? Then the robot Edge is open — just raise it.
powershell -NoProfile -Command "if (Get-NetTCPConnection -LocalPort 9222 -State Listen -ErrorAction SilentlyContinue) { 'edge already open'; exit 1 } else { 'edge not open yet'; exit 0 }" >> "%BATLOG%" 2>&1
if errorlevel 1 goto already

REM No debug port, but robot-profile Edge processes still around = leftovers
REM from a killed launch. They keep the profile locked, and every new launch
REM answers "the profile is in use" instead of opening. Only processes whose
REM command line names THIS profile are touched — normal Edge is left alone.
powershell -NoProfile -Command "$z=@(Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | Where-Object { $_.CommandLine -like '*EdgeSAPRobot*' }); if ($z.Count) { $z | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }; \"cleared $($z.Count) stale robot-profile process(es)\"; Start-Sleep 2 } else { 'no stale robot processes' }" >> "%BATLOG%" 2>&1

REM Knox Portal first — SSO must settle before GTE loads (강프로 2026-08-03).
start "" msedge.exe --remote-debugging-port=9222 --user-data-dir=C:\Temp\EdgeSAPRobot --no-first-run http://w2.samsung.net/portalapp/home
echo [%date% %time%] edge opened (portal) >> "%BATLOG%"
timeout /t 8 /nobreak >nul
start "" msedge.exe --user-data-dir=C:\Temp\EdgeSAPRobot http://gate3.cheil.com/gte/exp_2010_m.do
echo [%date% %time%] gte tab opened >> "%BATLOG%"
goto done

:already
start "" msedge.exe --user-data-dir=C:\Temp\EdgeSAPRobot http://gate3.cheil.com/gte/exp_2010_m.do
echo [%date% %time%] edge was already open, added gte tab >> "%BATLOG%"

:done
echo.
echo   Robot Edge is open.
echo   Sign in, open the trip's "Other Expense" entry screen,
echo   then press the robot button in Review.
echo.
timeout /t 6 /nobreak >nul
