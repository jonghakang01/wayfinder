"""Usage log contract (spec 2026-08-03-usage-dashboard).

A visit is one line per (day, user, app). The dedup set lives in server
memory, so the tests that matter are the ones a restart or a second request
would break: same-day repeats, seen-set rebuild from disk, and the exclusions.
"""
import services._usage as usage


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(usage, "USAGE_DIR", str(tmp_path))
    monkeypatch.setattr(usage, "_seen", set())
    monkeypatch.setattr(usage, "_seen_month", None)


def test_same_day_repeat_records_once(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    for _ in range(3):
        usage.record("a@example.com", "/toast")
    assert len(usage.visits(30)) == 1


def test_restart_does_not_duplicate(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    usage.record("a@example.com", "/toast")
    # a restart = empty in-memory set, same files on disk
    monkeypatch.setattr(usage, "_seen", set())
    monkeypatch.setattr(usage, "_seen_month", None)
    usage.record("a@example.com", "/toast")
    assert len(usage.visits(30)) == 1


def test_distinct_users_and_apps_all_land(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    usage.record("a@example.com", "/toast")
    usage.record("b@example.com", "/toast")
    usage.record("a@example.com", "/cardconv")
    assert len(usage.visits(30)) == 3


def test_anonymous_and_admin_are_not_recorded(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    usage.record("", "/toast")
    usage.record(None, "/toast")
    usage.record("a@example.com", "/admin")
    assert usage.visits(30) == []


def test_page_renders_empty_state(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    html = usage.render_page("admin@example.com")
    assert "No usage data yet" in html


def test_page_renders_data_and_drilldown(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    usage.record("a@example.com", "/toast")
    usage.record("b@example.com", "/toast")
    html = usage.render_page("a@example.com")
    assert "a@example.com" in html and "b@example.com" in html
    drill = usage.render_page("a@example.com", {"app": ["/toast"]})
    assert "by user (30d)" in drill


def test_non_admin_is_blocked_from_usage_route():
    import services.admin as admin
    kind, page = admin.handle("GET", "/admin/usage", {},
                              {"user": "nobody@example.com"})
    assert kind == "html" and "Admins only" in page
