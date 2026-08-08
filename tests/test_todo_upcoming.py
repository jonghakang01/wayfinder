"""Work due in a few days surfaces inside Today as "Upcoming" (강프로 2026-08-08).

A deadline three days out is met by starting today, not by reading "This week"
and scrolling past it. Tasks due within the soon window ride along in the Today
section under their own divider, keeping their real due badge.
"""
import importlib
from datetime import date, timedelta

todo = importlib.import_module("services.todo")

TODAY = date.today()
TODAY_S = TODAY.isoformat()
WEEK_S = (TODAY + timedelta(days=7)).isoformat()
SOON_S = (TODAY + timedelta(days=3)).isoformat()


def _t(i, **kw):
    t = {"id": i, "title": f"task {i}", "done": False, "project": "",
         "priority": 2, "due_date": None, "note": "", "place_id": ""}
    t.update(kw)
    return t


# ── where it lives ──────────────────────────────────────────────────────────

def test_due_in_three_days_is_upcoming():
    d = (TODAY + timedelta(days=3)).isoformat()
    assert todo._bucket_of(_t(1, due_date=d), TODAY_S, WEEK_S, SOON_S) == "upcoming"


def test_due_today_is_now_not_upcoming():
    assert todo._bucket_of(_t(1, due_date=TODAY_S), TODAY_S, WEEK_S, SOON_S) == "now"


def test_due_past_the_soon_window_stays_in_this_week():
    d = (TODAY + timedelta(days=5)).isoformat()
    assert todo._bucket_of(_t(1, due_date=d), TODAY_S, WEEK_S, SOON_S) == "week"


def test_without_a_soon_window_nothing_is_upcoming():
    """Old callers that never pass soon_str keep the old three buckets."""
    d = (TODAY + timedelta(days=2)).isoformat()
    assert todo._bucket_of(_t(1, due_date=d), TODAY_S, WEEK_S) == "week"


def test_a_daily_task_outranks_the_upcoming_window():
    d = (TODAY + timedelta(days=2)).isoformat()
    assert todo._bucket_of(_t(1, due_date=d, daily=True), TODAY_S, WEEK_S, SOON_S) == "now"


# ── what the page shows ─────────────────────────────────────────────────────

def test_today_section_carries_the_upcoming_divider():
    d = (TODAY + timedelta(days=2)).isoformat()
    html = todo.render([_t(1, due_date=d)], [], "someone")
    assert '<div class="tk-upcoming-head">' in html
    assert "task 1" in html


def test_no_upcoming_work_means_no_divider():
    html = todo.render([_t(1, due_date=TODAY_S)], [], "someone")
    assert '<div class="tk-upcoming-head">' not in html
