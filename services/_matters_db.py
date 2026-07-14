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
    updated_at TEXT DEFAULT (datetime('now','localtime')),
    ball_since TEXT DEFAULT '',                 -- when the ball landed on me (SLA clock)
    urgency TEXT DEFAULT 'normal'               -- urgent|normal|low
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
                 "archived", "structure", "ball_since", "urgency")

# --- attention model ----------------------------------------------------------
# The tracker is a "needs my action within 24h" dashboard: the clock runs only
# while the ball is on my side, and urgency sets the SLA.
ON_PLATE_BALL = {"나", "공동"}
CLOSED_STATUS = {"완료", "보류"}
URGENCY_SLA = {"urgent": 4, "normal": 24, "low": None}  # hours; None = reference only


def _now_str():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _parse_dt(s):
    if not s:
        return None
    s = str(s)
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:19], fmt)
        except ValueError:
            continue
    return None


def annotate_attention(matters, now=None):
    """Add an `att` block to each matter: tier (action|waiting|reference),
    hours on my plate, SLA, and whether it has breached (overdue)."""
    now = now or datetime.now()
    for m in matters:
        urg = m.get("urgency") or "normal"
        closed = m.get("status") in CLOSED_STATUS
        on_plate = m.get("ball") in ON_PLATE_BALL and not closed
        base = _parse_dt(m.get("ball_since")) or _parse_dt(m.get("last_contact"))
        hours = (now - base).total_seconds() / 3600 if base else None
        sla = URGENCY_SLA.get(urg, 24)
        if on_plate and urg != "low":
            tier = "action"
            overdue = sla is not None and hours is not None and hours >= sla
        elif m.get("ball") == "상대" and not closed:
            tier, overdue = "waiting", False
        else:
            tier, overdue = "reference", False
        m["att"] = {
            "tier": tier, "urgency": urg, "sla_hours": sla, "overdue": overdue,
            "hours_on_plate": round(hours, 1) if hours is not None else None,
        }
    return matters


def _attention_sort_key(m):
    a = m["att"]
    h = a["hours_on_plate"] or 0
    sla = a["sla_hours"] or 24
    urg_rank = {"urgent": 0, "normal": 1, "low": 2}.get(a["urgency"], 1)
    # overdue first (most-overdue on top), then urgency, then longest on plate.
    return (0 if a["overdue"] else 1, -(h - sla) if a["overdue"] else 0, urg_rank, -h)


def attention_queue(conn, now=None):
    """Ordered 'needs you now' list — the reminder feed for the scheduler."""
    ms = annotate_attention(list_matters(conn), now)
    action = [m for m in ms if m["att"]["tier"] == "action"]
    action.sort(key=_attention_sort_key)
    return action


def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    # idempotent column adds (schema evolves without a version table)
    cols = {r[1] for r in conn.execute("PRAGMA table_info(matters)")}
    adds = {
        "structure": "TEXT DEFAULT ''",
        "ball_since": "TEXT DEFAULT ''",
        "urgency": "TEXT DEFAULT 'normal'",
    }
    changed = False
    for col, decl in adds.items():
        if col not in cols:
            conn.execute(f"ALTER TABLE matters ADD COLUMN {col} {decl}")
            changed = True
    # Backfill the SLA clock for pre-existing on-plate matters so they don't all
    # read as instantly overdue: seed ball_since from last_contact.
    if "ball_since" not in cols:
        conn.execute("UPDATE matters SET ball_since=last_contact "
                     "WHERE (ball_since='' OR ball_since IS NULL) AND last_contact!=''")
    if changed:
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
    # Start the SLA clock: a new matter defaults to ball='나' (on my plate).
    if "ball_since" not in fields and data.get("ball", "나") in ON_PLATE_BALL:
        fields.append("ball_since")
        values.append(_now_str())
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
    # Restart the SLA clock whenever the ball newly lands on my side.
    if "ball" in data and data["ball"] in ON_PLATE_BALL \
            and data["ball"] != row["ball"] and "ball_since" not in data:
        sets.append("ball_since=?")
        values.append(_now_str())
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
    ms = annotate_attention(list_matters(conn))
    action = [m for m in ms if m["att"]["tier"] == "action"]
    drafts_n = conn.execute("""
        SELECT COUNT(*) FROM drafts_snapshot WHERE scan_run_id =
        (SELECT COALESCE(MAX(scan_run_id), 0) FROM drafts_snapshot)
    """).fetchone()[0]
    return {
        # Hero: what actually needs me now, and how much has breached SLA.
        "needs_now": len(action),
        "overdue": len([m for m in action if m["att"]["overdue"]]),
        "drafts": drafts_n,
        "waiting": len([m for m in ms if m["att"]["tier"] == "waiting"]),
        "reference": len([m for m in ms if m["att"]["tier"] == "reference"]),
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
        fields = {
            "title": data.get("title", "(제목 없음)"),
            "people": data.get("people", ""),
            "next_action": data.get("next_action", ""),
            "search_queries": data.get("search_queries", []),
        }
        # Oversight proposals (Jongha only CC'd / not the one asked to act)
        # arrive as ball=상대 + urgency=low so they land in the monitoring
        # tiers instead of starting an action-queue SLA clock.
        if data.get("ball") in ("나", "공동", "상대"):
            fields["ball"] = data["ball"]
        if data.get("urgency") in ("urgent", "normal", "low"):
            fields["urgency"] = data["urgency"]
        mid = create_matter(conn, fields)
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


AUTO_FIELDS = {"status", "ball", "waiting", "next_action", "last_contact", "people"}


def apply_pending_suggestions(conn) -> dict:
    """Revisit leftover pending field-suggestions from older scans and apply them
    under the new auto-apply rule: unlocked fields are written and marked
    accepted; locked ones are dismissed. new_matter proposals are left pending
    (creating a matter stays a user decision)."""
    rows = conn.execute(
        "SELECT * FROM suggestions WHERE status='pending' AND field!='new_matter' "
        "ORDER BY scan_run_id, id").fetchall()
    applied = dismissed = 0
    for r in rows:
        m = conn.execute("SELECT * FROM matters WHERE id=?", (r["matter_id"],)).fetchone()
        locked = set(json.loads(m["user_locked_fields"] or "[]")) if m else set()
        if not m or r["field"] not in AUTO_FIELDS or r["field"] in locked:
            conn.execute("UPDATE suggestions SET status='dismissed' WHERE id=?", (r["id"],))
            dismissed += 1
            continue
        update_matter(conn, r["matter_id"], {r["field"]: r["proposed_value"]}, lock_edited=False)
        conn.execute("UPDATE suggestions SET status='accepted' WHERE id=?", (r["id"],))
        applied += 1
    conn.commit()
    return {"applied": applied, "dismissed": dismissed}


def ai_updated_fields(conn) -> dict:
    """{matter_id: [field, ...]} that the AI auto-applied in the most recent scan —
    used to badge those fields 🤖 until the user edits them."""
    run = conn.execute(
        "SELECT MAX(scan_run_id) FROM suggestions WHERE status='accepted' "
        "AND field!='new_matter'").fetchone()[0]
    if not run:
        return {}
    rows = conn.execute(
        "SELECT matter_id, field FROM suggestions WHERE status='accepted' "
        "AND field!='new_matter' AND scan_run_id=?", (run,)).fetchall()
    out = {}
    for r in rows:
        out.setdefault(r["matter_id"], []).append(r["field"])
    return out


def latest_briefing(conn):
    row = conn.execute(
        "SELECT text, created_at FROM briefings ORDER BY id DESC LIMIT 1").fetchone()
    return dict(row) if row else None
