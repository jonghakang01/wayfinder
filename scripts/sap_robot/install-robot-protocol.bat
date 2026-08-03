@echo off
REM One-time setup: registers the wayfinder-robot:// link protocol so the
REM "Robot" button on the cardconv Review page can launch sap-robot-edge.bat.
REM User-level registry (HKCU) - no admin rights needed.

reg add "HKCU\Software\Classes\wayfinder-robot" /ve /d "URL:Wayfinder SAP Robot" /f
reg add "HKCU\Software\Classes\wayfinder-robot" /v "URL Protocol" /d "" /f
reg add "HKCU\Software\Classes\wayfinder-robot\shell\open\command" /ve /d "\"C:\Users\Jongha Kang\Desktop\sap-robot-edge.bat\"" /f
echo.
echo Done. The Review page's robot button will now launch the robot Edge.
echo (The browser asks for permission on the first click only.)
pause
