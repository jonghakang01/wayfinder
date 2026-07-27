"""UX/UI standard gate — runs on every pytest / pre-push.

The standard lives at /design (services/design.py) + docs/mobile_ux_guideline.md.
This freezes the machine-checkable part: a change may never add a violation, and
fixing violations must lower tests/uxui_baseline.json (run
`python3 tests/uxui_lint.py --write`).
"""
import pytest

import uxui_lint as lint

BASE = lint.load_baseline()
MODULES = [p.name for p in lint.ui_modules()]


@pytest.mark.parametrize("name", MODULES)
def test_no_new_uxui_violations(name):
    path = lint.SERVICES / name
    hits = lint.lint_module(path)
    allowed = BASE.get(name, {})
    counts = lint._tally(hits)
    for rule in lint.RULES:
        got, cap = counts.get(rule, 0), allowed.get(rule, 0)
        if got > cap:
            detail = "\n".join(f"    services/{name}:{ln}  {msg}"
                               for r, ln, msg in hits if r == rule)
            pytest.fail(
                f"new UX/UI violation in services/{name} [{rule}] {got} > baseline {cap}\n"
                f"{detail}\n  standard: /design · docs/mobile_ux_guideline.md")


@pytest.mark.parametrize("name", MODULES)
def test_baseline_is_tight(name):
    """Debt only goes down: once fixed, the baseline must be lowered."""
    counts = lint._tally(lint.lint_module(lint.SERVICES / name))
    allowed = BASE.get(name, {})
    stale = {r: (counts.get(r, 0), c) for r, c in allowed.items() if counts.get(r, 0) < c}
    assert not stale, (f"services/{name} improved {stale} (rule: now, baseline) — "
                       f"run `python3 tests/uxui_lint.py --write` to lock it in")


def test_design_page_is_the_reference():
    """The living contract itself must stay clean."""
    assert not lint.lint_module(lint.SERVICES / "design.py")
