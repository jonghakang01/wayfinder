import os

# Central data root. Overridable so staging/test can isolate from prod data.
# Prod leaves WAYFINDER_DATA_ROOT unset → defaults to ~/.appdata (unchanged).
DATA_ROOT = os.environ.get("WAYFINDER_DATA_ROOT") or os.path.expanduser("~/.appdata")
