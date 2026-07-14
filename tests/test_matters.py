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


def test_scan_queries_derive_people_from_queries():
    """Routine scan sweeps from: queries for every People email, so a matter's
    correspondence (incl. my outbound — collector matches To on Sent) is seen
    even when the stored search_queries miss it."""
    m = {"search_queries": ["Cheil-AIE IOT Project SOW", "from:smohan@aie.com"],
         "people": "S Mohan (smohan@aie.com), Ram Kumar <ram.kumar@aie.com> / 강프로"}
    qs = scan._scan_queries(m)
    assert qs[:2] == ["Cheil-AIE IOT Project SOW", "from:smohan@aie.com"]
    assert "from:ram.kumar@aie.com" in qs
    assert qs.count("from:smohan@aie.com") == 1  # no dup with stored query
    assert scan._scan_queries({"search_queries": [], "people": ""}) == []


def test_scan_conversation_refresh(tmp_path, monkeypatch):
    """A new message in an already-attached conversation is reflected on the
    next scan even when no stored query matches it any more (my outbound
    replies included) — the conv: refresh derived from attached threads."""
    conn = _conn(tmp_path, monkeypatch)
    src = get_source("fake")
    m = db.list_matters(conn)[0]
    scan.run_scan(conn, src, SINCE, use_judge=False)
    attached = db.threads_for_matter(conn, m["id"])
    assert attached
    tid = attached[0]["id"]

    # Wipe the matter's queries (subject drift) and grow the conversation.
    conn.execute("UPDATE matters SET search_queries='[]', people='' WHERE id=?", (m["id"],))
    conn.commit()
    thread = src.get_thread(tid)
    from services._matters_mail import Message
    thread.messages.append(Message(sender="me@cheil.com",
                                   sent_at="2099-01-01T09:00:00", body="my reply"))

    qs = scan._matter_queries(conn, src, {**m, "search_queries": [], "people": ""})
    assert f"conv:{tid.removeprefix('fake:')}" in qs
    scan.run_scan(conn, src, SINCE, use_judge=False)
    refreshed = next(t for t in db.threads_for_matter(conn, m["id"]) if t["id"] == tid)
    assert refreshed["last_message_at"] == "2099-01-01T09:00:00"
