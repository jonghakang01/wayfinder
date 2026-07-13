#!/usr/bin/env python3
"""SQLite layer — schema, migration, seed import."""
import json
import sqlite3
import sys
from datetime import date, datetime
from pathlib import Path

DB_PATH = Path.home() / ".appdata" / "matters" / "tracker.db"

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_version (v INTEGER);
CREATE TABLE IF NOT EXISTS matters (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT '진행중',      -- 진행중|회신대기|보류|완료
    ball TEXT NOT NULL DEFAULT '나',            -- 나|공동|상대
    people TEXT DEFAULT '',
    waiting TEXT DEFAULT '',
    next_action TEXT DEFAULT '',
    last_contact TEXT DEFAULT '',               -- YYYY-MM-DD
    notes TEXT DEFAULT '',
    search_queries TEXT DEFAULT '[]',           -- JSON list
    user_locked_fields TEXT DEFAULT '[]',       -- JSON list
    archived INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now','localtime')),
    updated_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS threads (
    id TEXT PRIMARY KEY,                        -- 'com:...' | 'graph:...' | 'fake:...'
    matter_id INTEGER,
    subject TEXT, last_message_at TEXT, last_sender TEXT,
    snippet TEXT, outlook_link TEXT
);
CREATE TABLE IF NOT EXISTS suggestions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    matter_id INTEGER, field TEXT, proposed_value TEXT, reason TEXT,
    status TEXT DEFAULT 'pending',              -- pending|accepted|dismissed
    scan_run_id INTEGER,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
CREATE TABLE IF NOT EXISTS scan_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at TEXT, finished_at TEXT, source TEXT,
    changes_summary TEXT, error TEXT
);
CREATE TABLE IF NOT EXISTS drafts_snapshot (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_run_id INTEGER, subject TEXT, saved_at TEXT, recipient TEXT,
    note TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS briefings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    scan_run_id INTEGER, text TEXT,
    created_at TEXT DEFAULT (datetime('now','localtime'))
);
"""

MATTER_FIELDS = ("title", "status", "ball", "people", "waiting", "next_action",
                 "last_contact", "notes", "search_queries", "user_locked_fields",
                 "archived", "structure")


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # idempotent column adds (schema evolves without a version table)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matters)")}
    if "structure" not in cols:
        conn.execute("ALTER TABLE matters ADD COLUMN structure TEXT DEFAULT ''")
        conn.commit()
    return conn


def list_matters(conn):
    rows = conn.execute(
        "SELECT * FROM matters WHERE archived=0 ORDER BY "
        "CASE ball WHEN '나' THEN 0 WHEN '공동' THEN 1 ELSE 2 END, last_contact DESC"
    ).fetchall()
    out = []
    for r in rows:
        m = dict(r)
        m["search_queries"] = json.loads(m["search_queries"] or "[]")
        m["user_locked_fields"] = json.loads(m["user_locked_fields"] or "[]")
        out.append(m)
    return out


def create_matter(conn, data: dict) -> int:
    fields, values = [], []
    for k in MATTER_FIELDS:
        if k in data:
            v = data[k]
            if k in ("search_queries", "user_locked_fields"):
                v = json.dumps(v if isinstance(v, list) else [], ensure_ascii=False)
            fields.append(k)
            values.append(v)
    if "title" not in fields:
        raise ValueError("title required")
    sql = f"INSERT INTO matters ({','.join(fields)}) VALUES ({','.join('?' * len(fields))})"
    cur = conn.execute(sql, values)
    conn.commit()
    return cur.lastrowid


def update_matter(conn, mid: int, data: dict, lock_edited=True) -> bool:
    row = conn.execute("SELECT * FROM matters WHERE id=?", (mid,)).fetchone()
    if not row:
        return False
    locked = set(json.loads(row["user_locked_fields"] or "[]"))
    sets, values = [], []
    for k in MATTER_FIELDS:
        if k not in data:
            continue
        v = data[k]
        if k in ("search_queries", "user_locked_fields"):
            v = json.dumps(v if isinstance(v, list) else [], ensure_ascii=False)
        sets.append(f"{k}=?")
        values.append(v)
        # A direct user edit locks the field against future AI suggestions.
        if lock_edited and k not in ("user_locked_fields", "archived"):
            locked.add(k)
    if not sets:
        return True
    sets.append("user_locked_fields=?")
    values.append(json.dumps(sorted(locked), ensure_ascii=False))
    sets.append("updated_at=datetime('now','localtime')")
    values.append(mid)
    conn.execute(f"UPDATE matters SET {','.join(sets)} WHERE id=?", values)
    conn.commit()
    return True


def upsert_thread(conn, t: dict, matter_id=None) -> bool:
    """Insert or update a thread. Returns True if the last_message_at advanced
    (i.e. genuinely new activity), which the scan uses to flag movement."""
    row = conn.execute("SELECT last_message_at FROM threads WHERE id=?", (t["id"],)).fetchone()
    is_new_activity = row is None or (t.get("last_message_at", "") > (row["last_message_at"] or ""))
    conn.execute("""
        INSERT INTO threads (id, matter_id, subject, last_message_at, last_sender, snippet, outlook_link)
        VALUES (:id, :matter_id, :subject, :last_message_at, :last_sender, :snippet, :outlook_link)
        ON CONFLICT(id) DO UPDATE SET
            matter_id=COALESCE(excluded.matter_id, threads.matter_id),
            subject=excluded.subject, last_message_at=excluded.last_message_at,
            last_sender=excluded.last_sender, snippet=excluded.snippet,
            outlook_link=excluded.outlook_link
    """, {**t, "matter_id": matter_id})
    conn.commit()
    return is_new_activity


def threads_for_matter(conn, matter_id: int) -> list:
    rows = conn.execute(
        "SELECT * FROM threads WHERE matter_id=? ORDER BY last_message_at DESC", (matter_id,)
    ).fetchall()
    return [dict(r) for r in rows]


def start_scan_run(conn, source: str) -> int:
    cur = conn.execute(
        "INSERT INTO scan_runs (started_at, source) VALUES (datetime('now','localtime'), ?)", (source,))
    conn.commit()
    return cur.lastrowid


def finish_scan_run(conn, run_id: int, summary: str, error: str = ""):
    conn.execute(
        "UPDATE scan_runs SET finished_at=datetime('now','localtime'), changes_summary=?, error=? WHERE id=?",
        (summary, error, run_id))
    conn.commit()


def replace_drafts_snapshot(conn, run_id: int, drafts: list):
    for d in drafts:
        conn.execute(
            "INSERT INTO drafts_snapshot (scan_run_id, subject, saved_at, recipient) VALUES (?,?,?,?)",
            (run_id, d.get("subject", ""), d.get("last_message_at", ""), d.get("last_sender", "")))
    conn.commit()


def kpis(conn):
    ms = list_matters(conn)
    today = date.today()

    def days_ago(m):
        try:
            return (today - date.fromisoformat(m["last_contact"])).days
        except (ValueError, TypeError):
            return None

    active = [m for m in ms if m["status"] != "완료"]
    stale = [m for m in active
             if (lambda d: d is not None and d >= 5)(days_ago(m))]
    drafts_n = conn.execute("""
        SELECT COUNT(*) FROM drafts_snapshot WHERE scan_run_id =
        (SELECT COALESCE(MAX(scan_run_id), 0) FROM drafts_snapshot)
    """).fetchone()[0]
    return {
        "my_action": len([m for m in active if m["ball"] == "나"]),
        "waiting_reply": len([m for m in active if m["ball"] == "상대"]),
        "drafts": drafts_n,
        "stale": len(stale),
        "in_progress": len([m for m in ms if m["status"] == "진행중"]),
    }


def import_seed(conn, seed_path: Path):
    seed = json.loads(seed_path.read_text())
    n = 0
    for m in seed.get("matters", []):
        create_matter(conn, {
            "title": m["title"], "status": m.get("status", "진행중"),
            "ball": m.get("ball", "나"), "people": m.get("people", ""),
            "waiting": m.get("waiting", ""), "next_action": m.get("next", ""),
            "last_contact": _norm_date(m.get("last", "")),
            "notes": m.get("notes", ""),
            "search_queries": m.get("search_queries", []),
        })
        n += 1
    run = conn.execute(
        "INSERT INTO scan_runs (started_at, finished_at, source, changes_summary) "
        "VALUES (datetime('now','localtime'), datetime('now','localtime'), 'seed', ?)",
        (f"seed import: {n} matters",))
    run_id = run.lastrowid
    for d in seed.get("drafts", []):
        conn.execute(
            "INSERT INTO drafts_snapshot (scan_run_id, subject, saved_at) VALUES (?,?,?)",
            (run_id, d.get("txt", ""), d.get("d", "")))
    conn.commit()
    return n


def _norm_date(s: str) -> str:
    s = (s or "").strip()
    if not s:
        return ""
    try:
        return date.fromisoformat(s).isoformat()
    except ValueError:
        pass
    # '7/10' → current-year ISO
    try:
        mm, dd = s.split("/")
        return date(datetime.now().year, int(mm), int(dd)).isoformat()
    except Exception:
        return s


# --- suggestions / briefings (L3) --------------------------------------------

def pending_suggestions(conn) -> list:
    rows = conn.execute(
        "SELECT * FROM suggestions WHERE status='pending' ORDER BY id").fetchall()
    return [dict(r) for r in rows]


def resolve_suggestion(conn, sid: int, accept: bool) -> dict:
    """Accept applies the proposal (new matter or field update, locks nothing);
    dismiss just marks it. Locked fields are refused at apply time too."""
    row = conn.execute("SELECT * FROM suggestions WHERE id=? AND status='pending'",
                       (sid,)).fetchone()
    if not row:
        return {"error": "not found"}
    if not accept:
        conn.execute("UPDATE suggestions SET status='dismissed' WHERE id=?", (sid,))
        conn.commit()
        return {"ok": True, "status": "dismissed"}

    if row["field"] == "new_matter":
        data = json.loads(row["proposed_value"])
        mid = create_matter(conn, {
            "title": data.get("title", "(제목 없음)"),
            "people": data.get("people", ""),
            "next_action": data.get("next_action", ""),
            "search_queries": data.get("search_queries", []),
        })
        result = {"ok": True, "status": "accepted", "matter_id": mid}
    else:
        m = conn.execute("SELECT * FROM matters WHERE id=?", (row["matter_id"],)).fetchone()
        if not m:
            return {"error": "matter gone"}
        if row["field"] in json.loads(m["user_locked_fields"] or "[]"):
            conn.execute("UPDATE suggestions SET status='dismissed' WHERE id=?", (sid,))
            conn.commit()
            return {"ok": True, "status": "dismissed", "locked": True}
        update_matter(conn, row["matter_id"], {row["field"]: row["proposed_value"]},
                      lock_edited=False)
        result = {"ok": True, "status": "accepted"}
    conn.execute("UPDATE suggestions SET status='accepted' WHERE id=?", (sid,))
    conn.commit()
    return result


def latest_briefing(conn):
    row = conn.execute(
        "SELECT text, created_at FROM briefings ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None
