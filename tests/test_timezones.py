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


# ── the list is yours to order (강프로 2026-08-07) ───────────────────────────

def test_move_up_swaps_with_the_row_above(tz):
    tz.save(USER, ["Asia/Tokyo", "Europe/London", "Asia/Seoul"])
    tz.move(USER, "Europe/London", "up")
    assert tz.load(USER) == ["Europe/London", "Asia/Tokyo", "Asia/Seoul"]


def test_move_down_swaps_with_the_row_below(tz):
    tz.save(USER, ["Asia/Tokyo", "Europe/London", "Asia/Seoul"])
    tz.move(USER, "Europe/London", "down")
    assert tz.load(USER) == ["Asia/Tokyo", "Asia/Seoul", "Europe/London"]


def test_the_ends_clamp(tz):
    """Top row up and bottom row down are no-ops, not wrap-arounds."""
    tz.save(USER, ["Asia/Tokyo", "Asia/Seoul"])
    tz.move(USER, "Asia/Tokyo", "up")
    tz.move(USER, "Asia/Seoul", "down")
    assert tz.load(USER) == ["Asia/Tokyo", "Asia/Seoul"]


def test_moving_a_city_not_on_the_list_changes_nothing(tz):
    before = tz.load(USER)
    tz.move(USER, "Asia/Dubai", "up")
    assert tz.load(USER) == before


def test_the_move_route_is_wired_and_junk_directions_are_not(tz):
    tz.save(USER, ["Asia/Tokyo", "Asia/Seoul"])
    kind, target = tz.handle("POST", "/timezones/move",
                             {"tz": ["Asia/Seoul"], "dir": ["up"]}, {"user": USER})
    assert kind == "redirect"
    assert tz.load(USER) == ["Asia/Seoul", "Asia/Tokyo"]
    tz.handle("POST", "/timezones/move",
              {"tz": ["Asia/Seoul"], "dir": ["sideways"]}, {"user": USER})
    assert tz.load(USER) == ["Asia/Seoul", "Asia/Tokyo"]


# ── the zone's everyday name rides beside the city (강프로 2026-08-07) ────────

def test_every_zone_has_a_calling_name(tz):
    assert set(tz.ABBRS) == tz.VALID
    assert tz.ABBRS["Asia/Seoul"] == "KST"
    assert tz.ABBRS["Asia/Kolkata"] == "IST"


def test_the_requested_cities_are_the_ones_offered(tz):
    assert tz.LABELS["America/Los_Angeles"] == "Mountain View"
    assert tz.LABELS["America/Chicago"] == "Dallas"
    assert tz.LABELS["America/New_York"] == "New York"
    assert tz.LABELS["Asia/Kolkata"] == "Chennai / Hyderabad"


def test_rows_and_picker_carry_the_name(tz):
    tz.save(USER, ["Asia/Seoul"])
    _, html = tz.handle("GET", "/timezones", {}, {"user": USER})
    assert '<span class="tz-abbr">KST</span>' in html
    assert "Seoul (KST)" in html
    # arrows render, and the single row's both arrows are dead ends
    assert 'name="dir" value="up"' in html
    assert html.count("disabled") >= 2
