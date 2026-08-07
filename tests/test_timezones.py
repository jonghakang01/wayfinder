import importlib
import os
import shutil
import tempfile

import pytest

MOD = "services.timezones"
USER = "__testuser__"


@pytest.fixture
def tz(monkeypatch):
    """A throwaway DATA_ROOT — these tests write, and the real one is a user's."""
    mod = importlib.import_module(MOD)
    d = tempfile.mkdtemp()
    monkeypatch.setattr(mod, "DATA_ROOT", d)
    yield mod
    shutil.rmtree(d, ignore_errors=True)


def test_meta_is_valid():
    m = importlib.import_module(MOD).META
    assert m["path"] == "/timezones"
    assert m["name"] and isinstance(m["name"], str)


def test_get_renders_html(tz):
    kind, html = tz.handle("GET", "/timezones", {}, {"user": USER})
    assert kind == "html"
    assert "Time Zones" in html
    # The home row is the browser's job to name, but its slot has to be there.
    assert 'data-tz="__home__"' in html


def test_first_visit_has_defaults(tz):
    assert tz.load(USER) == tz.DEFAULT_ZONES


def test_add_and_remove_round_trip(tz):
    tz.add(USER, "Asia/Tokyo")
    assert "Asia/Tokyo" in tz.load(USER)
    tz.remove(USER, "Asia/Tokyo")
    assert "Asia/Tokyo" not in tz.load(USER)


def test_add_rejects_unknown_zone(tz):
    tz.add(USER, "Mars/Olympus_Mons")
    assert "Mars/Olympus_Mons" not in tz.load(USER)


def test_add_is_idempotent(tz):
    before = tz.load(USER)
    tz.add(USER, before[0])
    assert tz.load(USER) == before


def test_add_stops_at_the_limit(tz):
    for zone in tz.VALID:
        tz.add(USER, zone)
    assert len(tz.load(USER)) == tz.MAX_ZONES


def test_load_drops_zones_this_build_forgot(tz):
    os.makedirs(os.path.join(tz.DATA_ROOT, USER), exist_ok=True)
    with open(tz._file(USER), "w") as f:
        f.write('{"zones": ["Asia/Seoul", "Atlantis/Central"]}')
    assert tz.load(USER) == ["Asia/Seoul"]


def test_post_add_redirects(tz):
    kind, target = tz.handle("POST", "/timezones/add", {"tz": [""]}, {"user": USER})
    assert kind == "redirect"
    assert target == "/timezones"


def test_labels_cover_every_offered_zone(tz):
    assert set(tz.LABELS) == tz.VALID
    assert all(z in tz.VALID for z in tz.DEFAULT_ZONES)
