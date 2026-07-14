"""Matter Tracker — Outlook 사안 추적 (공 소재·브릿지 관계도), ported from labs.

LOCAL ONLY: the app reads the local Outlook mailbox through a Windows COM
collector, and its data lives in ~/.appdata/matters on this machine. On any
non-WSL host (prod) every route renders a notice instead — mail-derived data
must never reach the server.
"""
import json
import os
import re
from datetime import date, timedelta

META = {
    "name": "Matter Tracker",
    "path": "/matters",
    "icon": "🗂",
    "description": "Outlook 사안 추적 — 공 소재·AI 브리핑·브릿지 관계도 (로컬 전용)",
    "admin_only": True,
}

LOOKBACK_DAYS = 30


def _is_local() -> bool:
    # The COM bridge needs Windows next door; /mnt/c only exists on Jongha's WSL.
    return os.path.exists("/mnt/c")


def _drafts(conn):
    rows = conn.execute("""
        SELECT subject, saved_at FROM drafts_snapshot WHERE scan_run_id =
        (SELECT COALESCE(MAX(scan_run_id), 0) FROM drafts_snapshot)
    """).fetchall()
    return [dict(r) for r in rows]


def _last_scan(conn):
    r = conn.execute(
        "SELECT finished_at, source, changes_summary, error FROM scan_runs "
        "WHERE finished_at IS NOT NULL ORDER BY id DESC LIMIT 1").fetchone()
    return dict(r) if r else None


def _api_payload(db, conn):
    matters = db.annotate_attention(db.list_matters(conn))
    sugg = db.pending_suggestions(conn)
    ai_updated = db.ai_updated_fields(conn)
    for m in matters:
        m["threads"] = db.threads_for_matter(conn, m["id"])
        m["suggestions"] = [s for s in sugg if s["matter_id"] == m["id"]]
        # Badge fields the AI auto-applied last scan, unless the user re-locked them.
        locked = set(m.get("user_locked_fields") or [])
        m["ai_updated"] = [f for f in ai_updated.get(m["id"], []) if f not in locked]
    return {
        "matters": matters, "kpis": db.kpis(conn),
        "drafts": _drafts(conn), "last_scan": _last_scan(conn),
        "new_matter_suggestions": [s for s in sugg if s["field"] == "new_matter"],
        "briefing": db.latest_briefing(conn),
    }


def _attention_feed(db, conn):
    """Compact 'needs you now' list for reminders (scheduler / Telegram)."""
    queue = db.attention_queue(conn)
    return [{
        "id": m["id"], "title": m["title"], "next_action": m["next_action"],
        "people": m["people"], "urgency": m["att"]["urgency"],
        "hours_on_plate": m["att"]["hours_on_plate"],
        "sla_hours": m["att"]["sla_hours"], "overdue": m["att"]["overdue"],
    } for m in queue]


_RECHECK_STOP = {"프로젝트", "관련", "및", "the", "and", "for", "project", "re", "fwd"}


def _parse_terms(terms) -> list:
    """Accept a comma/newline-separated string or a list → clean term list."""
    if isinstance(terms, str):
        terms = re.split(r"[,\n]", terms)
    return [t.strip() for t in (terms or []) if isinstance(t, str) and t.strip()]


def _recheck_queries(matter: dict, terms: list | None = None) -> list:
    """Broaden the evidence net for a single matter. With explicit `terms` the
    sweep is scoped to just those People/keywords; otherwise it falls back to
    every person in People plus the title keywords. Always keeps the matter's own
    search_queries. The COM collector matches subject words (incl. Sent) or
    from:addr (either direction — sender, or my Sent's To), so this surfaces
    threads the routine scan missed — e.g. a mail I sent to a non-listed person
    whose subject still carries the keywords."""
    qs = list(matter.get("search_queries") or [])
    if terms:
        for t in terms:
            if re.fullmatch(r"[\w.+-]+@[\w.-]+", t):
                qs.append(f"from:{t}")
            else:
                qs.append(t)
    else:
        for chunk in re.split(r"[,/]", matter.get("people", "") or ""):
            name = re.sub(r"\(.*?\)", "", chunk).strip()
            for email in re.findall(r"[\w.+-]+@[\w.-]+", name):
                qs.append(f"from:{email}")
            name = re.sub(r"[\w.+-]+@[\w.-]+", "", name).strip()
            if len(name) >= 2:
                qs.append(name)
        title = re.sub(r"\(.*?\)", "", matter.get("title", "") or "")
        for tok in re.split(r"[\s\-–—·:]+", title):
            tok = tok.strip()
            if len(tok) >= 2 and tok.lower() not in _RECHECK_STOP:
                qs.append(tok)
    seen, out = set(), []
    for q in qs:
        if q.lower() not in seen:
            seen.add(q.lower())
            out.append(q)
    return out


def _handle_recheck(db, judge, get_source, conn, mid: int, days: int,
                    terms=None) -> dict:
    """Deep-recheck one matter: sweep People (or the given terms) over a recent
    window (default 3d), attach new threads, re-judge, and propose useful queries."""
    row = conn.execute("SELECT * FROM matters WHERE id=?", (mid,)).fetchone()
    if not row:
        return {"error": "not found"}
    matter = dict(row)
    matter["search_queries"] = json.loads(matter["search_queries"] or "[]")
    matter["user_locked_fields"] = json.loads(matter["user_locked_fields"] or "[]")

    queries = _recheck_queries(matter, _parse_terms(terms))
    src = get_source()
    since = date.today() - timedelta(days=max(1, days))
    if hasattr(src, "prefetch"):
        src.prefetch(queries, since)
    found, hit_queries = {}, []
    for q in queries:
        threads = src.search_threads(q, since)
        if threads:
            hit_queries.append(q)
        for t in threads:
            found[t.id] = t

    existing = {t["id"] for t in db.threads_for_matter(conn, mid)}
    new_count, rows = 0, []
    for t in found.values():
        s = t.summary()
        r = {"id": s.thread_id, "subject": s.subject, "last_message_at": s.last_message_at,
             "last_sender": s.last_sender, "snippet": s.snippet, "outlook_link": s.outlook_link}
        db.upsert_thread(conn, r, matter_id=mid)
        if s.thread_id not in existing:
            new_count += 1
        rows.append(r)

    run_id = db.start_scan_run(conn, "recheck")
    applied = []
    if judge.available():
        res = judge.rejudge_matter(conn, run_id, matter, rows)
        applied = res["applied"]
    db.finish_scan_run(conn, run_id,
                       f"recheck «{matter['title']}»: +{new_count} threads, {len(applied)} applied")

    persisted = {q.lower() for q in matter["search_queries"]}
    suggested = [q for q in hit_queries if q.lower() not in persisted]
    return {"ok": True, "days": days, "found": new_count, "threads_total": len(rows),
            "applied": applied, "suggested_queries": suggested,
            "scoped": bool(_parse_terms(terms))}


def handle(method, path, body, ctx=None):
    from services import _matters_render as render

    if not _is_local():
        if path.startswith("/matters/api"):
            return ("json", {"error": "local-only app"})
        return ("html", render.render_local_only())

    from services import _matters_db as db
    from services import _matters_scan as scan
    from services import _matters_judge as judge
    from services._matters_mail import get_source

    if method == "GET" and path == "/matters":
        return ("html", render.render_page())

    if method == "GET" and path == "/matters/api":
        conn = db.get_conn()
        try:
            return ("json", _api_payload(db, conn))
        finally:
            conn.close()

    # Reminder feed — the ordered 'needs you now' queue (for the scheduler).
    if method == "GET" and path == "/matters/api/attention":
        conn = db.get_conn()
        try:
            return ("json", {"attention": _attention_feed(db, conn)})
        finally:
            conn.close()

    if method == "POST" and path.startswith("/matters/api"):
        conn = db.get_conn()
        try:
            data = body if isinstance(body, dict) else {}

            if path == "/matters/api/scan":
                src = get_source()
                since = date.today() - timedelta(days=LOOKBACK_DAYS)
                res = scan.run_scan(conn, src, since)
                return ("json", {"ok": True, "moved": res["moved"],
                                 "candidates": [c.subject for c in res["candidates"]],
                                 "summary": res["summary"]})
            if path == "/matters/api/structures":
                return ("json", {"ok": True, "updated": judge.refresh_structures(conn)})
            if path == "/matters/api/propose":
                query = str(data.get("query", "")).strip()
                if not query:
                    return ("json", {"error": "검색어를 입력하세요"})
                days = 90  # user-driven search digs deeper than the scan window
                threads = get_source().search_threads(
                    query, date.today() - timedelta(days=days))
                if not threads:
                    return ("json", {"error": f"최근 {days}일 메일에서 '{query}' 검색 결과가 없습니다"})
                created = judge.propose_from_search(conn, query, threads)
                return ("json", {"ok": True, "created": len(created),
                                 "threads_found": len(threads)})
            if path.startswith("/matters/api/suggestions/"):
                sid = int(path.rsplit("/", 1)[1])
                accept = data.get("action") == "accept"
                res = db.resolve_suggestion(conn, sid, accept)
                return ("json", res)
            if path == "/matters/api/matters":
                return ("json", {"ok": True, "id": db.create_matter(conn, data)})
            if path.startswith("/matters/api/matters/") and path.endswith("/recheck"):
                mid = int(path.split("/")[4])
                return ("json", _handle_recheck(db, judge, get_source, conn, mid,
                                                int(data.get("days", 3) or 3),
                                                data.get("terms")))
            if path.startswith("/matters/api/matters/"):
                mid = int(path.rsplit("/", 1)[1])
                ok = db.update_matter(conn, mid, data)
                return ("json", {"ok": ok} if ok else {"error": "not found"})
        except RuntimeError as e:  # mail/judge boundary: Outlook down, API errors
            return ("json", {"error": str(e)})
        except (ValueError, json.JSONDecodeError) as e:
            return ("json", {"error": str(e)})
        finally:
            conn.close()

    return ("html", "<h2>404 Not Found</h2>")
