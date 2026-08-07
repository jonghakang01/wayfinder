"""Work with a distant deadline that still needs doing today (강프로 2026-08-07).

"Due가 나중까지여도 매일매일 조금씩은 해야" — a far due date reads as permission
to skip, and the list happily agreed by filing the task under Later. A task can
now be marked daily: it sits in Today whatever the deadline says, and it asks
whether time went in rather than whether it is finished.
"""
import importlib
from datetime import date, timedelta

todo = importlib.import_module("services.todo")

TODAY = date.today()
TODAY_S = TODAY.isoformat()
FAR = (TODAY + timedelta(days=40)).isoformat()


def _t(i, **kw):
    t = {"id": i, "title": f"task {i}", "done": False, "project": "",
         "priority": 2, "due_date": None, "note": "", "place_id": ""}
    t.update(kw)
    return t


def _render(todos, monkeypatch):
    monkeypatch.setattr(todo, "places_of", lambda u: [], raising=False)
    return todo.render(todos, [], "someone")


def _post(monkeypatch, store, body):
    monkeypatch.setattr(todo, "load", lambda u: store)
    saved = {}
    monkeypatch.setattr(todo, "save", lambda t, u: saved.update({"t": t}))
    todo.handle("POST", "/todo/set_meta", body, {"user": "someone"})
    return saved["t"][0]


# ── where it lives ──────────────────────────────────────────────────────────

def test_a_daily_task_is_in_today_however_far_the_deadline():
    assert todo._bucket_of(_t(1, due_date=FAR, daily=True), TODAY_S, TODAY_S) == "now"


def test_the_same_task_without_the_flag_is_not():
    assert todo._bucket_of(_t(1, due_date=FAR), TODAY_S, TODAY_S) == "later"


def test_a_finished_daily_task_stops_claiming_today():
    assert todo._bucket_of(_t(1, due_date=FAR, daily=True, done=True),
                           TODAY_S, TODAY_S) != "now"


def test_a_dateless_daily_task_still_reaches_today():
    """The flag is the whole reason it is there — no due date to fall back on."""
    assert todo._bucket_of(_t(1, daily=True), TODAY_S, TODAY_S) == "now"


# ── what it says ────────────────────────────────────────────────────────────

def test_the_row_offers_a_way_to_log_a_bit_of_work(monkeypatch):
    html = _render([_t(1, due_date=FAR, daily=True)], monkeypatch)
    assert 'name="touch"' in html
    assert ">Daily</span>" in html


def test_it_says_how_long_it_has_been_left(monkeypatch):
    """The counter is the point: 'in 40d' alone reads as permission to skip."""
    html = _render([_t(1, due_date=FAR, daily=True,
                       last_touch=(TODAY - timedelta(days=4)).isoformat())], monkeypatch)
    assert "4d untouched" in html
    assert "in 40d" in html          # both signals, side by side


def test_untouched_counts_from_the_day_it_was_marked_when_never_worked_on():
    t = _t(1, daily=True, daily_since=(TODAY - timedelta(days=3)).isoformat())
    assert todo.untouched_days(t, TODAY) == 3


def test_nothing_nags_on_the_day_it_was_marked():
    t = _t(1, daily=True, daily_since=TODAY_S)
    assert todo.untouched_days(t, TODAY) is None


def test_once_worked_on_today_the_row_settles(monkeypatch):
    html = _render([_t(1, due_date=FAR, daily=True, last_touch=TODAY_S)], monkeypatch)
    assert "Did some today" in html
    # The rendered chip, not the class name — that also appears in the <style>
    # block, so a bare class check passes on the stylesheet and proves nothing.
    assert 'class="tk-chip tk-chip--stale"' not in html
    assert 'name="touch"' not in html     # nothing left to press until tomorrow


def test_a_plain_task_says_none_of_this(monkeypatch):
    html = _render([_t(1, due_date=FAR)], monkeypatch)
    assert ">Daily</span>" not in html
    assert 'name="touch"' not in html


# ── the switch ──────────────────────────────────────────────────────────────

def test_logging_a_bit_stamps_today_and_does_not_finish_the_task(monkeypatch):
    t = _post(monkeypatch, [_t(1, due_date=FAR, daily=True)],
              {"id": ["1"], "touch": ["1"]})
    assert t["last_touch"] == TODAY_S
    assert t["done"] is False
    assert t["due_date"] == FAR       # its own deadline is untouched


def test_turning_it_on_gives_the_counter_something_to_count_from(monkeypatch):
    t = _post(monkeypatch, [_t(1, due_date=FAR)],
              {"id": ["1"], "daily_flag": ["1"]})
    assert t["daily"] is True
    assert t["daily_since"] == TODAY_S


def test_turning_it_off_clears_the_history(monkeypatch):
    """Otherwise switching it back on would inherit a stale 'untouched' count."""
    t = _post(monkeypatch, [_t(1, daily=True, daily_since="2026-01-01",
                               last_touch="2026-01-02")],
              {"id": ["1"], "daily_flag": ["0"]})
    assert t["daily"] is False
    assert "daily_since" not in t and "last_touch" not in t


def test_the_switch_can_be_turned_off_at_all(monkeypatch):
    """An unchecked box submits nothing, so the sheet posts an explicit 0 — and
    the sheet has to actually carry that field for this to work."""
    html = todo.render([_t(1)], [], "someone")
    assert 'name="daily_flag"' in html
    assert 'id="tkSdailyFlag"' in html


def test_a_second_press_on_the_same_day_changes_nothing(monkeypatch):
    store = [_t(1, daily=True)]
    _post(monkeypatch, store, {"id": ["1"], "touch": ["1"]})
    t = _post(monkeypatch, store, {"id": ["1"], "touch": ["1"]})
    assert t["last_touch"] == TODAY_S
