"""Usage log contract (specs 2026-08-03-usage-dashboard,
2026-08-04-admin-tabs-usage-charts).

A row is one (day, user, app, hour). The dedup set lives in server memory, so
the tests that matter are the ones a restart or a second request would break:
same-hour repeats, seen-set rebuild from disk, the exclusions, and rows written
before hour/device existed.
"""
import json

import services._usage as usage


def _isolate(monkeypatch, tmp_path):
    monkeypatch.setattr(usage, "USAGE_DIR", str(tmp_path))
    monkeypatch.setattr(usage, "_seen", set())
    monkeypatch.setattr(usage, "_seen_month", None)


def _write_legacy(tmp_path, day, user, app):
    """A row from before hour/device were tracked."""
    month = day[:7]
    with open(tmp_path / f"{month}.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps({"d": day, "u": user, "a": app}) + "\n")


def test_same_hour_repeat_records_once(monkeypatch, tmp_path):
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


def test_several_hours_in_a_day_are_one_visit_day(monkeypatch, tmp_path):
    """The row count grew hourly; every count that means "how many days" has to
    collapse them or the dashboard inflates."""
    _isolate(monkeypatch, tmp_path)
    from datetime import date
    today = date.today().isoformat()
    month = today[:7]
    with open(tmp_path / f"{month}.jsonl", "w", encoding="utf-8") as f:
        for hour in (9, 13, 18):
            f.write(json.dumps({"d": today, "u": "a@example.com",
                                "a": "/toast", "h": hour, "m": 0}) + "\n")
    rows = usage.visits(30)
    assert len(rows) == 3
    assert len(usage.visit_days(rows)) == 1


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


def test_mobile_agent_is_flagged_desktop_is_not(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    usage.record("a@example.com", "/toast", "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0)")
    usage.record("b@example.com", "/toast", "Mozilla/5.0 (X11; Linux x86_64)")
    devices = {u: m for _, u, _, _, m in usage.visits(30)}
    assert devices["a@example.com"] is True
    assert devices["b@example.com"] is False


def test_legacy_rows_survive_with_unknown_hour_and_device(monkeypatch, tmp_path):
    """Rows written before 2026-08-04 must still count, not vanish."""
    _isolate(monkeypatch, tmp_path)
    from datetime import date
    today = date.today().isoformat()
    _write_legacy(tmp_path, today, "old@example.com", "/toast")
    rows = usage.visits(30)
    assert len(rows) == 1
    assert rows[0][3] is None and rows[0][4] is None
    assert len(usage.visit_days(rows)) == 1
    # and a legacy row must not be re-written by a fresh visit the same hour
    usage.record("old@example.com", "/toast")
    assert len(usage.visit_days(usage.visits(30))) == 1


def test_body_renders_empty_state(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    html = usage.render_body("admin@example.com")
    assert "No usage data yet" in html


def test_body_renders_data_charts_and_drilldown(monkeypatch, tmp_path):
    _isolate(monkeypatch, tmp_path)
    usage.record("a@example.com", "/toast")
    usage.record("b@example.com", "/toast")
    html = usage.render_body("a@example.com")
    assert "a@example.com" in html and "b@example.com" in html
    for section in ("Daily activity", "Share by app", "Hour of day",
                    "Device", "Dormant accounts"):
        assert section in html
    drill = usage.render_body("a@example.com", {"app": ["/toast"]})
    assert "by user (30d)" in drill


def test_non_admin_is_blocked_from_admin_tabs():
    import services.admin as admin
    for path in ("/admin", "/admin/usage"):
        kind, page = admin.handle("GET", path, {},
                                  {"user": "nobody@example.com"})
        assert kind == "html" and "Admins only" in page


def test_old_usage_route_redirects_into_the_tab(monkeypatch):
    import services.admin as admin
    monkeypatch.setattr(admin.auth, "is_admin", lambda u: True)
    kind, target = admin.handle("GET", "/admin/usage", {},
                                {"user": "admin@example.com"})
    assert kind == "redirect" and target == "/admin?tab=usage"
    kind, target = admin.handle("GET", "/admin/usage", {"app": ["/toast"]},
                                {"user": "admin@example.com"})
    assert kind == "redirect" and target == "/admin?tab=usage&app=/toast"


def test_usage_tab_renders_through_admin(monkeypatch, tmp_path):
    import services.admin as admin
    _isolate(monkeypatch, tmp_path)
    page = admin.render_admin("admin@example.com", tab="usage")
    assert "adm-tab" in page and "Active users" in page
    users = admin.render_admin("admin@example.com", tab="users")
    assert "Global service control" in users
