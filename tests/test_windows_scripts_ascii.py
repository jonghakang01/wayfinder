"""Windows scripts must be pure ASCII.

cmd.exe reads .bat files in the OEM code page. A UTF-8 em dash inside an
`if (...)` block turns into bytes that close the block early, and the whole
file dies with "the was unexpected at this time" — which is exactly how the
agent installer failed on first use (2026-08-05). Nothing about the message
points at the character, so the guard has to be mechanical.
"""
from pathlib import Path

import pytest

SCRIPTS = sorted((Path(__file__).parent.parent / "scripts" / "sap_robot").glob("*.bat")) + \
          sorted((Path(__file__).parent.parent / "scripts" / "sap_robot").glob("*.vbs"))


def test_there_are_scripts_to_check():
    """A rename that empties this list would make every test below vacuous."""
    assert SCRIPTS, "no .bat/.vbs found under scripts/sap_robot"


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_script_is_ascii_only(path):
    raw = path.read_bytes()
    offenders = []
    for lineno, line in enumerate(raw.split(b"\n"), 1):
        bad = {b for b in line if b > 0x7E}
        if bad:
            offenders.append(f"{path.name}:{lineno} {sorted(bad)} {line[:70]!r}")
    assert not offenders, "non-ASCII bytes break cmd parsing:\n" + "\n".join(offenders)


@pytest.mark.parametrize("path", SCRIPTS, ids=lambda p: p.name)
def test_script_is_not_empty(path):
    """A rewrite that truncates a file leaves something that parses fine and
    does nothing at all — the installer was emptied that way once."""
    assert path.stat().st_size > 0, f"{path.name} is empty"
