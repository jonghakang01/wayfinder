"""Matter Tracker port — scan pipeline with the fake source, suggestion apply."""
import importlib
import os
from datetime import date

import pytest

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


def test_oversight_new_matter_lands_in_monitoring_tier(tmp_path, monkeypatch):
    """A CC/oversight proposal (ball=상대, urgency=low) must not start an
    action-queue SLA clock when accepted."""
    conn = _conn(tmp_path, monkeypatch)
    import json as _json
    conn.execute("INSERT INTO suggestions (matter_id, field, proposed_value, reason)"
                 " VALUES (NULL, 'new_matter', ?, 'oversight')",
                 (_json.dumps({"title": "감시 사안", "people": "A, B",
                               "ball": "상대", "urgency": "low"}),))
    conn.commit()
    sid = [s for s in db.pending_suggestions(conn) if s["field"] == "new_matter"][0]["id"]
    res = db.resolve_suggestion(conn, sid, accept=True)
    m = next(x for x in db.list_matters(conn) if x["id"] == res["matter_id"])
    db.annotate_attention([m])
    assert m["ball"] == "상대" and m["urgency"] == "low"
    assert not m["ball_since"]
    assert m["att"]["tier"] != "action"


def test_matter_queries_include_thread_subject_for_forks(tmp_path, monkeypatch):
    """A FW/RE that spawned a NEW conversation keeps the subject words, so the
    scan derives a normalized-subject query from each attached thread."""
    conn = _conn(tmp_path, monkeypatch)
    src = get_source("fake")
    m = db.list_matters(conn)[0]
    db.upsert_thread(conn, {
        "id": "fake:t-fork", "subject": "[EXTERNAL EMAIL] RE: Cheil-AIE Contract Reconfirm",
        "last_message_at": "2026-07-14T09:00:00", "last_sender": "x@y.com",
        "snippet": "", "outlook_link": ""}, matter_id=m["id"])
    qs = scan._matter_queries(conn, src, m)
    assert "Cheil-AIE Contract Reconfirm" in qs
    assert scan._norm_subject("FW: RE: [External Email] 전달: Hello World") == "Hello World"


@pytest.mark.skipif(not os.path.exists("/mnt/c"),
                    reason="matters handle() is local-only (guards on the Windows mount)")
def test_split_apply_reassigns_threads(tmp_path, monkeypatch):
    """Applying a split plan creates the new matter, moves only the listed
    threads to it, and keeps the rest on the original."""
    import services.matters as matters_svc
    conn = _conn(tmp_path, monkeypatch)  # handle() opens its own conn to the same tmp DB
    m = db.list_matters(conn)[0]
    for i in (1, 2):
        db.upsert_thread(conn, {
            "id": f"fake:sp{i}", "subject": f"Topic {i}", "last_message_at": f"2026-07-0{i}T09:00:00",
            "last_sender": "a@b.com", "snippet": "", "outlook_link": ""}, matter_id=m["id"])
    plan = {"split": [{"title": "분리된 사안", "people": "A", "next_action": "",
                       "ball": "상대", "urgency": "low", "search_queries": ["Topic 2"],
                       "thread_ids": ["fake:sp2", "fake:not-mine"]}],
            "keep": {"title": "남는 사안"}}
    kind, res = matters_svc.handle("POST", f"/matters/api/matters/{m['id']}/split_apply", plan,
                                   {"user": "jongha.kang"})
    assert res["ok"] and res["created"][0]["threads"] == 1  # foreign id ignored
    new_id = res["created"][0]["id"]
    nm = next(x for x in db.list_matters(conn) if x["id"] == new_id)
    assert nm["ball"] == "상대" and nm["urgency"] == "low"
    assert {t["id"] for t in db.threads_for_matter(conn, new_id)} == {"fake:sp2"}
    assert "fake:sp1" in {t["id"] for t in db.threads_for_matter(conn, m["id"])}
    assert next(x for x in db.list_matters(conn) if x["id"] == m["id"])["title"] == "남는 사안"
