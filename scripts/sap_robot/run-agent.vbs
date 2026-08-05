' Start the SAP agent with no window at all.
'
' The agent is a background listener, not something to watch: a console would
' sit on the taskbar for the whole session inviting someone to close it, and
' closing it is what stops the Submit button working. Logs go to a file the
' Desktop can reach instead.
'
' Run by the WayfinderAgent logon task (install-agent.bat).
Option Explicit
Dim sh, cmd, home
Set sh = CreateObject("WScript.Shell")
home = sh.ExpandEnvironmentStrings("%USERPROFILE%")

' bash -lc so the login profile is loaded: the agent needs the chromium
' libraries on LD_LIBRARY_PATH, exactly as the trip robot does.
cmd = "wsl.exe -e bash -lc ""LD_LIBRARY_PATH=$HOME/.local/chromium-libs " & _
      "python3 $HOME/webapp/scripts/sap_agent.py " & _
      ">> $HOME/.wayfinder-agent.log 2>&1"""

' 0 = hidden window, False = do not wait for it to finish.
sh.Run cmd, 0, False
