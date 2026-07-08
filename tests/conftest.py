import os
import sys

# Make repo root importable so tests can `import services.<name>`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
