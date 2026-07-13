"""Matter Tracker port — scan pipeline with the fake source, suggestion apply."""
import importlib
from datetime import date

from services import _matters_db as db
from services import _matters_scan as scan
from services._matters_mail import get_source

SINCE = date(2026, 7, 1)


def _conn(tmp_path, monkeypatch):
    monkeypatch.setattr(db, "DB_PATH", tmp_path / "t.db")
    conn = db.get_conn()
    db.create_matter(conn, {
        "title": "테스트 사안", "ball": "나", "status": "진행중",
        "search_queries": ["Contract Structure Inquiry"],
    })
    return conn


def test_meta_local_only_guard():
    mod = importlib.import_module("services.matters")
    assert mod.META["path"] == "/matters" and mod.META["admin_only"] is True
    # On this dev machine /mnt/c exists; the guard itself must be callable.
    assert isinstance(mod._is_local(), bool)


def test_fake_scan_attaches_threads(tmp_path, monkeypatch):
    conn = _conn(tmp_path, monkeypatch)
    res = scan.run_scan(conn, get_source("fake"), SINCE, use_judge=False)
    m = db.list_matters(conn)[0]
    threads = db.threads_for_matter(conn, m["id"])
    assert threads and threads[0]["id"].startswith("fake:")
    assert "미발송 초안" in res["summary"]


def test_suggestion_accept_updates_matter(tmp_path, monkeypatch):
    conn = _conn(tmp_path, monkeypatch)
    m = db.list_matters(conn)[0]
    conn.execute("INSERT INTO suggestions (matter_id, field, proposed_value, reason)"
                 " VALUES (?,?,?,?)", (m["id"], "ball", "상대", "r"))
    conn.commit()
    sid = db.pending_suggestions(conn)[0]["id"]
    assert db.resolve_suggestion(conn, sid, accept=True)["ok"]
    m2 = db.list_matters(conn)[0]
    assert m2["ball"] == "상대" and "ball" not in m2["user_locked_fields"]


def test_no_write_apis_in_mail_module():
    """Read-only rule: no Outlook write calls in the mail layer."""
    import pathlib
    text = (pathlib.Path("services/_matters_mail.py")).read_text()
    for token in (".Send(", ".Delete(", ".Move(", ".FlagRequest"):
        assert token not in text
