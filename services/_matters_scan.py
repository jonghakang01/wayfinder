#!/usr/bin/env python3
"""Scan pipeline (L2) — pull mail activity per matter, record what moved.

For each matter, run its search_queries against the MailSource, attach found
threads, and note which matters saw genuinely new activity since the last stored
state. AI judgement (status/ball proposals, new-matter detection) is L3 — this
layer only collects and reports, never overwrites matter fields.

Usage:
  python3 -m scan --dry-run     # report changes, write threads/scan_run, no matter edits
  python3 -m scan               # same (matter edits are L3's job regardless)
  MAIL_SOURCE=fake python3 -m scan
"""
import sys
from datetime import date, timedelta

from services import _matters_db as db
from services._matters_mail import get_source

LOOKBACK_DAYS = 30


def run_scan(conn, source, since: date, use_judge: bool = True) -> dict:
    run_id = db.start_scan_run(conn, source.name)
    # Revisit any field-suggestions left pending by older scans — apply them under
    # the auto-apply rule before this run generates fresh judgement.
    db.apply_pending_suggestions(conn)
    moved, seen_threads = [], set()
    threads_by_matter: dict[int, list] = {}
    try:
        # Batch sources (COM bridge) collect everything in one spawn.
        if hasattr(source, "prefetch"):
            all_queries = [q for m in db.list_matters(conn)
                           for q in (m.get("search_queries") or [])]
            source.prefetch(all_queries, since)

        for m in db.list_matters(conn):
            queries = m.get("search_queries") or []
            matter_new = False
            for q in queries:
                for t in source.search_threads(q, since):
                    if t.id in seen_threads:
                        continue
                    seen_threads.add(t.id)
                    s = t.summary()
                    row = {"id": s.thread_id, "subject": s.subject,
                           "last_message_at": s.last_message_at, "last_sender": s.last_sender,
                           "snippet": s.snippet, "outlook_link": s.outlook_link}
                    if db.upsert_thread(conn, row, matter_id=m["id"]):
                        matter_new = True
                    threads_by_matter.setdefault(m["id"], []).append(row)
            if matter_new:
                moved.append(m["title"])

        # Inbox items matching no known matter → new-matter candidates (L3 judges).
        known = {r["id"] for r in conn.execute("SELECT id FROM threads").fetchall()}
        candidates = [s for s in source.list_recent_inbox(since) if s.thread_id not in known]

        drafts = source.list_drafts()
        db.replace_drafts_snapshot(conn, run_id, [d.__dict__ for d in drafts])

        # L3: batched Claude judgement → pending suggestions + briefing.
        # A judge failure must not fail the scan.
        judge_res = None
        if use_judge:
            from services import _matters_judge as judge
            if judge.available():
                try:
                    judge_res = judge.run(conn, run_id, db.list_matters(conn),
                                          threads_by_matter, candidates, drafts)
                except RuntimeError as e:
                    print(f"[judge] 실패(스캔은 계속): {e}")
                try:
                    n = judge.refresh_structures(conn)
                    print(f"[judge] 관계도 갱신 {n}건")
                except RuntimeError as e:
                    print(f"[judge] 관계도 갱신 실패(스캔은 계속): {e}")

        summary = _summarize(moved, candidates, drafts)
        if judge_res:
            summary += f" · AI 제안 {judge_res['stored']}건"
        db.finish_scan_run(conn, run_id, summary)
        return {"moved": moved, "candidates": candidates, "drafts": len(drafts),
                "summary": summary, "judge": judge_res}
    except Exception as e:  # noqa: BLE001 — record failure, don't crash the scheduler
        db.finish_scan_run(conn, run_id, "", error=str(e))
        raise


def _summarize(moved, candidates, drafts) -> str:
    parts = []
    if moved:
        parts.append(f"{len(moved)}개 사안에 새 활동: " + ", ".join(moved))
    if candidates:
        parts.append(f"신규 사안 후보 {len(candidates)}건")
    parts.append(f"미발송 초안 {len(drafts)}건")
    return " · ".join(parts) if parts else "변화 없음"
