"""Regression net: every routable service must honor the Wayfinder contract.

A service is any services/*.py that server.load_services() picks up
(not underscore-prefixed, not auth.py) and that exposes a META dict.
Such a module MUST:
  - META["path"] be a str starting with "/"
  - META have a non-empty "name"
  - expose a callable handle(method, path, body, ctx)

This test parametrizes over the real services directory, so a newly
scaffolded app is covered automatically — and a broken/renamed contract
fails CI before it reaches production.
"""
import importlib
import os

import pytest

SERVICES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "services"
)


def _service_names():
    return [
        f[:-3]
        for f in sorted(os.listdir(SERVICES_DIR))
        if f.endswith(".py") and not f.startswith("_") and f not in ("auth.py", "__init__.py")
    ]


@pytest.mark.parametrize("name", _service_names())
def test_service_contract(name):
    mod = importlib.import_module(f"services.{name}")
    if not hasattr(mod, "META"):
        pytest.skip(f"{name}: helper module (no META), not routed")
    m = mod.META
    assert isinstance(m.get("path"), str) and m["path"].startswith(
        "/"
    ), f"{name}: META['path'] must be a str starting with '/'"
    assert m.get("name"), f"{name}: META['name'] must be non-empty"
    assert callable(getattr(mod, "handle", None)), f"{name}: must expose handle()"


def test_no_duplicate_paths():
    paths = {}
    for name in _service_names():
        mod = importlib.import_module(f"services.{name}")
        p = getattr(mod, "META", {}).get("path")
        if not p:
            continue
        assert p not in paths, f"path {p} used by both {paths[p]} and {name}"
        paths[p] = name
