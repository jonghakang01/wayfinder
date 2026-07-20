"""Windows-interop environment for subprocesses that call *.exe from WSL.

Under the wayfinder-dev systemd user service the process has no login-shell
environment: Windows PATH entries and the WSL_INTEROP socket are missing, so
`powershell.exe` fails with FileNotFoundError. Every subprocess that crosses
into Windows must go through interop_env() / POWERSHELL.
"""
import glob
import os

POWERSHELL = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"
_WIN_PATHS = "/mnt/c/Windows/System32:/mnt/c/Windows/System32/WindowsPowerShell/v1.0"


def interop_env() -> dict:
    """os.environ copy with Windows PATH entries and a live WSL_INTEROP socket."""
    env = dict(os.environ)
    if "/mnt/c/" not in env.get("PATH", ""):
        env["PATH"] = env.get("PATH", "") + ":" + _WIN_PATHS
    sock = env.get("WSL_INTEROP")
    if not sock or not os.path.exists(sock):
        # The boot init's socket survives as the /run/WSL/1_interop symlink;
        # otherwise fall back to the most recently created session socket.
        candidates = (["/run/WSL/1_interop"] if os.path.exists("/run/WSL/1_interop") else
                      sorted(glob.glob("/run/WSL/*_interop"), key=os.path.getmtime, reverse=True))
        if candidates:
            env["WSL_INTEROP"] = candidates[0]
    return env
