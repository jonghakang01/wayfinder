"""Matter Tracker — Outlook 사안 추적 (공 소재·브릿지 관계도), ported from labs.

LOCAL ONLY: the app reads the local Outlook mailbox through a Windows COM
collector, and its data lives in ~/.appdata/matters on this machine. On any
non-WSL host (prod) every route renders a notice instead — mail-derived data
must never reach the server.
"""
import json
import os
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
    matters = db.list_matters(conn)
    sugg = db.pending_suggestions(conn)
    for m in matters:
        m["threads"] = db.threads_for_matter(conn, m["id"])
        m["suggestions"] = [s for s in sugg if s["matter_id"] == m["id"]]
    return {
        "matters": matters, "kpis": db.kpis(conn),
        "drafts": _drafts(conn), "last_scan": _last_scan(conn),
        "new_matter_suggestions": [s for s in sugg if s["field"] == "new_matter"],
        "briefing": db.latest_briefing(conn),
    }


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
