#!/usr/bin/env python3
"""Windows-side Outlook COM collector — runs under Windows Python, not WSL.

Standalone by design: the WSL app copies this single file to a Windows-local
directory and executes it via powershell.exe, so it must not import anything
from the repo. Reads classic Outlook over COM and prints ONE JSON document to
stdout. READ-ONLY: no Send/Delete/Move/Flag calls anywhere.

Usage (Windows python):
  python outlook_collect.py --queries-file request.json --since 2026-06-13
"""
import argparse
import json
import re
import sys
from datetime import date, datetime

INBOX, SENT, DRAFTS = 6, 5, 16
MAX_ITEMS = 1000
SNIPPET = 200
OL_MAIL = 43

CONNECT_HINT = (
    "Outlook COM 연결 실패. 클래식 Outlook 실행 여부와 '새 Outlook 사용' 토글(꺼야 함), "
    "pip install pywin32 를 확인하세요."
)


def snippet(body: str) -> str:
    return re.sub(r"\s+", " ", body or "").strip()[:SNIPPET]


def to_iso(dt) -> str:
    if dt is None:
        return ""
    try:
        if getattr(dt, "tzinfo", None) is not None:
            dt = dt.astimezone().replace(tzinfo=None)
        return datetime(dt.year, dt.month, dt.day, dt.hour, dt.minute, dt.second).isoformat()
    except (ValueError, OSError, OverflowError):
        return ""


def subject_matches(query: str, subject: str) -> bool:
    """Every query word must appear in the subject (Outlook search tokenizes)."""
    s = subject.lower()
    return all(w in s for w in query.lower().split())


class Collector:
    def __init__(self) -> None:
        try:
            import pythoncom
            import win32com.client
        except ImportError as e:
            raise SystemExit(f"pywin32 없음: {e}") from e
        pythoncom.CoInitialize()
        try:
            app = win32com.client.Dispatch("Outlook.Application")
            self._ns = app.GetNamespace("MAPI")
            self._ns.GetDefaultFolder(INBOX).Name  # probe: New Outlook fails here
        except Exception as e:
            raise SystemExit(f"{CONNECT_HINT}\n원인: {e}") from e
        self._loaded: dict[int, list[dict]] = {}

    # -- folder walk (once per folder, queries matched in memory) ---------

    def _walk(self, folder_id: int, sort_key: str, since: date) -> list[dict]:
        if folder_id in self._loaded:
            return self._loaded[folder_id]
        items = self._ns.GetDefaultFolder(folder_id).Items
        items.Sort(f"[{sort_key}]", True)
        floor = datetime.combine(since, datetime.min.time())
        out: list[dict] = []
        item, n = items.GetFirst(), 0
        while item is not None and n < MAX_ITEMS:
            n += 1
            mail, item = item, items.GetNext()
            if getattr(mail, "Class", None) != OL_MAIL:
                continue
            when = to_iso(getattr(mail, sort_key, None))
            if not when:
                continue
            if datetime.fromisoformat(when) < floor:
                break
            out.append(self._record(mail, when))
        self._loaded[folder_id] = out
        return out

    def _record(self, mail, when: str) -> dict:
        sender_email = getattr(mail, "SenderEmailAddress", "") or ""
        if getattr(mail, "SenderEmailType", "") == "EX":
            sender_email = self._smtp_address(mail) or sender_email
        conv = getattr(mail, "ConversationID", None) or (
            "topic:" + (getattr(mail, "ConversationTopic", "") or "").lower())
        return {
            "conv": conv,
            "topic": getattr(mail, "ConversationTopic", "") or getattr(mail, "Subject", "") or "",
            "subject": getattr(mail, "Subject", "") or "(제목 없음)",
            "sender_name": getattr(mail, "SenderName", "") or "",
            "sender_email": sender_email,
            "to": getattr(mail, "To", "") or "",
            "when": when,
            "body": snippet(getattr(mail, "Body", "")),
            "entryid": getattr(mail, "EntryID", "") or "",
        }

    @staticmethod
    def _smtp_address(mail) -> str:
        try:
            sender = mail.Sender
            if sender is not None:
                exch = sender.GetExchangeUser()
                if exch is not None:
                    return exch.PrimarySmtpAddress or ""
        except Exception:
            pass
        return ""

    # -- public ------------------------------------------------------------

    def search(self, query: str, since: date) -> list[dict]:
        if query.lower().startswith("from:"):
            addr = query[5:].strip().lower()
            pool = self._walk(INBOX, "ReceivedTime", since)
            hits = [r for r in pool if addr in r["sender_email"].lower()]
        else:
            pool = (self._walk(INBOX, "ReceivedTime", since)
                    + self._walk(SENT, "SentOn", since))
            hits = [r for r in pool if subject_matches(query, r["subject"])]

        threads: dict[str, dict] = {}
        for r in hits:
            t = threads.setdefault(r["conv"], {
                "id": r["conv"], "subject": r["topic"],
                "outlook_link": f"outlook:{r['entryid']}", "messages": []})
            t["messages"].append({
                "sender": r["sender_email"] or r["sender_name"],
                "sent_at": r["when"], "body": r["body"]})
        for t in threads.values():
            t["messages"].sort(key=lambda m: m["sent_at"])
        return list(threads.values())

    def recent_inbox(self, since: date) -> list[dict]:
        latest: dict[str, dict] = {}
        for r in self._walk(INBOX, "ReceivedTime", since):
            cur = latest.get(r["conv"])
            if cur is None or r["when"] > cur["last_message_at"]:
                latest[r["conv"]] = {
                    "thread_id": r["conv"], "subject": r["subject"],
                    "last_sender": r["sender_email"] or r["sender_name"],
                    "last_message_at": r["when"], "snippet": r["body"]}
        return sorted(latest.values(), key=lambda s: s["last_message_at"], reverse=True)

    def drafts(self, since: date) -> list[dict]:
        items = self._ns.GetDefaultFolder(DRAFTS).Items
        items.Sort("[LastModificationTime]", True)
        floor = datetime.combine(since, datetime.min.time())
        out: list[dict] = []
        item, n = items.GetFirst(), 0
        while item is not None and n < MAX_ITEMS:
            n += 1
            mail, item = item, items.GetNext()
            when = to_iso(getattr(mail, "LastModificationTime", None))
            if not when or datetime.fromisoformat(when) < floor:
                break
            out.append({
                "thread_id": "", "subject": getattr(mail, "Subject", "") or "(제목 없음)",
                "last_sender": getattr(mail, "To", "") or "",  # recipient by convention
                "last_message_at": when,
                "snippet": snippet(getattr(mail, "Body", ""))})
        return out


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    ap = argparse.ArgumentParser()
    ap.add_argument("--queries-file", required=True)
    ap.add_argument("--since", required=True, help="YYYY-MM-DD")
    args = ap.parse_args()

    with open(args.queries_file, encoding="utf-8") as f:
        queries = json.load(f)
    since = date.fromisoformat(args.since)

    try:
        c = Collector()
        payload = {
            "ok": True,
            "queries": {q: c.search(q, since) for q in queries},
            "inbox": c.recent_inbox(since),
            "drafts": c.drafts(since),
        }
    except SystemExit as e:
        print(json.dumps({"ok": False, "error": str(e)}, ensure_ascii=False))
        return 1
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
