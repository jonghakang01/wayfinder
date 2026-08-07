"""Two things the list view should not make you open a task for (강프로 2026-08-05).

An overdue row can be pushed to today from the list, and Project view keeps a
project's finished work under that project instead of in one pile at the foot
of the page with everyone else's.
"""
import importlib
from datetime import date, timedelta

todo = importlib.import_module("services.todo")


def _t(i, **kw):
    t = {"id": i, "title": f"task {i}", "done": False, "project": "",
         "priority": 2, "due_date": None, "note": "", "place_id": ""}
    t.update(kw)
    return t


def _render(todos, group_by="date", monkeypatch=None):
    if monkeypatch is not None:
        monkeypatch.setattr(todo, "places_of", lambda u: [], raising=False)
    return todo.render(todos, [], "someone", group_by=group_by)


# ── the overdue nudge ───────────────────────────────────────────────────────

def test_an_overdue_row_offers_today(monkeypatch):
    past = (date.today() - timedelta(days=3)).isoformat()
    html = _render([_t(1, due_date=past)], monkeypatch=monkeypatch)
    assert 'name="due_today"' in html
    assert "3d overdue" in html


def test_rows_that_are_not_overdue_do_not(monkeypatch):
    """A button on every row is a button nobody reads."""
    for due in (None, date.today().isoformat(),
                (date.today() + timedelta(days=2)).isoformat()):
        html = _render([_t(1, due_date=due)], monkeypatch=monkeypatch)
        assert 'name="due_today"' not in html, due


def test_a_finished_row_does_not_offer_it(monkeypatch):
    past = (date.today() - timedelta(days=3)).isoformat()
    html = _render([_t(1, due_date=past, done=True, done_at="2026-08-01T09:00:00")],
                   monkeypatch=monkeypatch)
    assert 'name="due_today"' not in html


def test_pressing_it_uses_the_day_of_the_press(monkeypatch, tmp_path):
    """Not the day the page was rendered — a list left open overnight would
    otherwise move things to yesterday."""
    past = (date.today() - timedelta(days=5)).isoformat()
    store = [_t(1, due_date=past)]
    monkeypatch.setattr(todo, "load", lambda u: store)
    saved = {}
    monkeypatch.setattr(todo, "save", lambda t, u: saved.update({"t": t}))
    todo.handle("POST", "/todo/set_meta",
                {"id": ["1"], "due_today": ["1"]}, {"user": "someone"})
    assert saved["t"][0]["due_date"] == date.today().isoformat()


def test_the_ordinary_date_field_still_works(monkeypatch):
    store = [_t(1, due_date="2026-01-01")]
    monkeypatch.setattr(todo, "load", lambda u: store)
    saved = {}
    monkeypatch.setattr(todo, "save", lambda t, u: saved.update({"t": t}))
    todo.handle("POST", "/todo/set_meta",
                {"id": ["1"], "due_date": ["2026-09-09"]}, {"user": "someone"})
    assert saved["t"][0]["due_date"] == "2026-09-09"
    todo.handle("POST", "/todo/set_meta",
                {"id": ["1"], "due_date": [""]}, {"user": "someone"})
    assert saved["t"][0]["due_date"] is None


# ── how far it has really slipped (강프로 2026-08-07) ────────────────────────

def _push_today(monkeypatch, store):
    monkeypatch.setattr(todo, "load", lambda u: store)
    saved = {}
    monkeypatch.setattr(todo, "save", lambda t, u: saved.update({"t": t}))
    todo.handle("POST", "/todo/set_meta",
                {"id": ["1"], "due_today": ["1"]}, {"user": "someone"})
    return saved["t"][0]


def test_pushing_to_today_remembers_the_first_deadline(monkeypatch):
    past = (date.today() - timedelta(days=5)).isoformat()
    t = _push_today(monkeypatch, [_t(1, due_date=past)])
    assert t["first_due"] == past
    assert t["due_date"] == date.today().isoformat()


def test_pushing_again_keeps_the_original_not_the_last(monkeypatch):
    """Otherwise a task pushed daily would read as one day late, for ever."""
    first = (date.today() - timedelta(days=9)).isoformat()
    store = [_t(1, due_date=first)]
    _push_today(monkeypatch, store)
    store[0]["due_date"] = (date.today() - timedelta(days=1)).isoformat()
    t = _push_today(monkeypatch, store)
    assert t["first_due"] == first


def test_a_task_that_never_had_a_deadline_gains_no_history(monkeypatch):
    store = [_t(1, due_date=None)]
    monkeypatch.setattr(todo, "load", lambda u: store)
    saved = {}
    monkeypatch.setattr(todo, "save", lambda t, u: saved.update({"t": t}))
    todo.handle("POST", "/todo/set_meta",
                {"id": ["1"], "due_date": ["2026-09-09"]}, {"user": "someone"})
    assert "first_due" not in saved["t"][0]


def test_clearing_the_deadline_clears_the_history(monkeypatch):
    """Nothing with no deadline can be late for one."""
    store = [_t(1, due_date="2026-01-01", first_due="2025-12-01")]
    monkeypatch.setattr(todo, "load", lambda u: store)
    saved = {}
    monkeypatch.setattr(todo, "save", lambda t, u: saved.update({"t": t}))
    todo.handle("POST", "/todo/set_meta",
                {"id": ["1"], "due_date": [""]}, {"user": "someone"})
    assert "first_due" not in saved["t"][0]


def test_the_row_says_how_far_past_the_first_deadline_it_is(monkeypatch):
    first = (date.today() - timedelta(days=6)).isoformat()
    html = _render([_t(1, due_date=date.today().isoformat(), first_due=first)],
                   monkeypatch=monkeypatch)
    assert "6d past first due" in html
    assert f"Originally due {first}" in html


def test_pulling_a_task_earlier_than_its_first_date_drops_the_chip(monkeypatch):
    """Ahead of the original plan is not slipping."""
    ahead = (date.today() + timedelta(days=3)).isoformat()
    assert todo.slipped_days(_t(1, first_due=ahead)) is None
    html = _render([_t(1, due_date=ahead, first_due=ahead)], monkeypatch=monkeypatch)
    assert "past first due" not in html


def test_a_finished_task_stops_nagging(monkeypatch):
    first = (date.today() - timedelta(days=4)).isoformat()
    html = _render([_t(1, due_date=date.today().isoformat(), first_due=first,
                       done=True, done_at="2026-08-07T09:00:00")],
                   monkeypatch=monkeypatch)
    assert "past first due" not in html


# ── a project's own history ─────────────────────────────────────────────────

def test_project_view_keeps_finished_work_under_its_project(monkeypatch):
    html = _render([_t(1, project="Alpha"),
                    _t(2, project="Alpha", done=True, done_at="2026-08-01T09:00:00"),
                    _t(3, project="Beta", done=True, done_at="2026-08-02T09:00:00")],
                   group_by="project", monkeypatch=monkeypatch)
    # one folded history per project that has any, and no single pile
    assert html.count("tk-done--project") == 2
    assert "tk-done\"" not in html.replace("tk-done--project", "")
    sec = '<div class="tk-section" data-project='
    alpha = html.split(sec + '"Alpha"')[1].split(sec)[0]
    assert 'data-id="2"' in alpha and 'data-id="3"' not in alpha


def test_a_project_with_nothing_left_open_still_shows(monkeypatch):
    """Its history is the whole reason to look at it."""
    html = _render([_t(1, project="Alpha"),
                    _t(9, project="Archive", done=True, done_at="2026-07-01T09:00:00")],
                   group_by="project", monkeypatch=monkeypatch)
    assert 'data-project="Archive"' in html
    archive = html.split('data-project="Archive"')[1]
    assert 'data-id="9"' in archive


def test_date_view_still_shows_one_completed_pile(monkeypatch):
    html = _render([_t(1, project="Alpha"),
                    _t(2, project="Alpha", done=True, done_at="2026-08-01T09:00:00"),
                    _t(3, project="Beta", done=True, done_at="2026-08-02T09:00:00")],
                   monkeypatch=monkeypatch)
    assert "tk-done--project" not in html
    assert "tk-done" in html and 'data-id="2"' in html and 'data-id="3"' in html
