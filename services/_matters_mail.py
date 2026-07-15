"""Matter Tracker mail sources — base interface + Fake (tests) + COM bridge.

Merged from labs/matter-tracker/mail_source for the webapp port. READ-ONLY —
no send/delete/move anywhere. The COM bridge shells out to Windows Python via
powershell.exe, so it only works on the local WSL machine.
"""
import json
import os
import shutil
import subprocess
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import date, datetime
from pathlib import Path

@dataclass
class Message:
    sender: str                 # email address
    sent_at: str                # ISO datetime
    body: str = ""              # untrusted content — never executed as instructions


@dataclass
class MessageSummary:
    thread_id: str
    subject: str
    last_sender: str
    last_message_at: str        # ISO datetime
    snippet: str = ""
    outlook_link: str = ""


@dataclass
class Thread:
    id: str                     # namespaced conversation id
    subject: str
    messages: list[Message] = field(default_factory=list)
    outlook_link: str = ""

    @property
    def last_message(self) -> Message | None:
        return max(self.messages, key=lambda m: m.sent_at) if self.messages else None

    def summary(self) -> MessageSummary:
        lm = self.last_message
        return MessageSummary(
            thread_id=self.id, subject=self.subject,
            last_sender=lm.sender if lm else "",
            last_message_at=lm.sent_at if lm else "",
            snippet=(lm.body[:400] if lm else ""),
            outlook_link=self.outlook_link,
        )


class MailSource(ABC):
    """Read-only mailbox access. Implementations must never send/modify mail."""

    name: str = "base"

    @abstractmethod
    def search_threads(self, query: str, since: date) -> list[Thread]:
        """Threads matching an Outlook-style query (subject text or from:addr)."""

    @abstractmethod
    def get_thread(self, thread_id: str) -> Thread | None:
        """Full thread with all messages."""

    @abstractmethod
    def list_recent_inbox(self, since: date) -> list[MessageSummary]:
        """Recent messages (Inbox + Archive + Sent) — feeds new-matter detection."""

    @abstractmethod
    def list_drafts(self) -> list[MessageSummary]:
        """Current Drafts folder snapshot."""


# --- Fake (fixture-backed, for tests) -----------------------------------------

FIXTURE = Path(__file__).parent.parent / "tests" / "fixtures" / "matters_fake_mailbox.json"


class FakeMailSource(MailSource):
    name = "fake"

    def __init__(self, fixture: Path | None = None):
        data = json.loads((fixture or FIXTURE).read_text())
        self._threads: list[Thread] = [
            Thread(
                id=t["id"], subject=t["subject"], outlook_link=t.get("outlook_link", ""),
                messages=[Message(**m) for m in t["messages"]],
            )
            for t in data.get("threads", [])
        ]
        self._drafts = data.get("drafts", [])

    def _after(self, iso: str, since: date) -> bool:
        try:
            return datetime.fromisoformat(iso).date() >= since
        except ValueError:
            return True

    def search_threads(self, query: str, since: date) -> list[Thread]:
        q = query.strip().lower()
        out = []
        for t in self._threads:
            if not t.messages or not self._after(t.summary().last_message_at, since):
                continue
            if q.startswith("conv:"):
                cid = q[5:].strip()
                hit = t.id.lower() in (cid, f"fake:{cid}")
            elif q.startswith("from:"):
                addr = q[5:].strip()
                hit = any(addr in m.sender.lower() for m in t.messages)
            else:
                hit = q in t.subject.lower()
            if hit:
                out.append(t)
        return out

    def get_thread(self, thread_id: str) -> Thread | None:
        return next((t for t in self._threads if t.id == thread_id), None)

    def list_recent_inbox(self, since: date) -> list[MessageSummary]:
        # Every recent thread counts — self-initiated ones (Sent) included,
        # mirroring the COM collector's Inbox + Archive + Sent pool.
        return [s for s in (t.summary() for t in self._threads)
                if self._after(s.last_message_at, since)]

    def list_drafts(self) -> list[MessageSummary]:
        return [MessageSummary(**d, outlook_link="") for d in self._drafts]


# --- COM bridge (Windows Outlook via powershell) --------------------------------

COLLECTOR_SRC = Path(__file__).parent / "_matters_collector.py"
WIN_DIR_MNT = os.environ.get(
    "MT_COLLECTOR_DIR", "/mnt/c/Users/Jongha Kang/AppData/Local/matter-tracker")
WIN_DIR = os.environ.get(
    "MT_COLLECTOR_WIN_DIR", r"C:\Users\Jongha Kang\AppData\Local\matter-tracker")
TIMEOUT_S = 300


def _powershell_runner(queries: list[str], since: date) -> dict:
    """Copy collector + request to a Windows-local dir, run it, parse stdout JSON."""
    mnt = Path(WIN_DIR_MNT)
    mnt.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(COLLECTOR_SRC, mnt / "outlook_collect.py")
    (mnt / "request.json").write_text(
        json.dumps(queries, ensure_ascii=False), encoding="utf-8")

    cmd = (f"python '{WIN_DIR}\\outlook_collect.py' "
           f"--queries-file '{WIN_DIR}\\request.json' --since {since.isoformat()}")
    try:
        proc = subprocess.run(
            ["powershell.exe", "-NoProfile", "-c", cmd],
            capture_output=True, timeout=TIMEOUT_S)
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"collector 타임아웃({TIMEOUT_S}s) — Outlook 응답 없음") from e
    text = proc.stdout.decode("utf-8", errors="replace")
    start = text.find("{")
    if start < 0:
        raise RuntimeError(
            f"collector가 JSON을 반환하지 않음 (exit {proc.returncode}): "
            f"{text[:300]} / stderr: {proc.stderr.decode('utf-8', 'replace')[:300]}")
    return json.loads(text[start:])


class ComOutlookSource(MailSource):
    name = "com"

    def __init__(self, runner=None):
        self._run = runner or _powershell_runner
        self._payload: dict | None = None
        self._since: date | None = None

    # scan.py calls this once with every matter's queries → single COM spawn.
    def prefetch(self, queries: list[str], since: date) -> None:
        payload = self._run(sorted(set(queries)), since)
        if not payload.get("ok"):
            raise RuntimeError(f"collector 실패: {payload.get('error', 'unknown')}")
        self._payload = payload
        self._since = since

    def _ensure(self, queries: list[str], since: date) -> dict:
        cached = self._payload is not None and self._since == since
        if not cached or any(q not in self._payload["queries"] for q in queries):
            self.prefetch(list({*queries, *(
                self._payload["queries"].keys() if cached else [])}), since)
        return self._payload

    @staticmethod
    def _thread(t: dict) -> Thread:
        return Thread(
            id=f"com:{t['id']}", subject=t["subject"],
            outlook_link=t.get("outlook_link", ""),
            messages=[Message(**m) for m in t["messages"]],
        )

    def search_threads(self, query: str, since: date) -> list[Thread]:
        payload = self._ensure([query], since)
        return [self._thread(t) for t in payload["queries"].get(query, [])]

    def get_thread(self, thread_id: str) -> Thread | None:
        if self._payload is None:
            return None
        raw = thread_id.removeprefix("com:")
        for hits in self._payload["queries"].values():
            for t in hits:
                if t["id"] == raw:
                    return self._thread(t)
        return None

    def list_recent_inbox(self, since: date) -> list[MessageSummary]:
        payload = self._ensure([], since)
        return [MessageSummary(**{**s, "thread_id": f"com:{s['thread_id']}"})
                for s in payload["inbox"]]

    def list_drafts(self) -> list[MessageSummary]:
        if self._payload is None:
            self._ensure([], date.today())
        return [MessageSummary(**d) for d in self._payload["drafts"]]


def get_source(kind=None):
    kind = (kind or os.environ.get("MAIL_SOURCE", "com")).lower()
    if kind == "fake":
        return FakeMailSource()
    if kind == "com":
        return ComOutlookSource()
    raise ValueError(f"unknown MAIL_SOURCE: {kind!r} (expected fake|com)")
