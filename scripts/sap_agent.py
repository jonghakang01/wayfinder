"""SAP submission agent — the hands (spec docs/specs/2026-08-05-sap-agent-multiuser.md).

Runs on the user's own PC and keeps asking the Wayfinder server whether there
is anything to key into GTE. The server decides *what* to submit and remembers
what happened; this process only types and reports. That split is what lets the
screen show progress no matter which server the page came from — the PC reaches
out, never the other way round.

Phase 1 keeps the existing WSL + playwright + CDP-relay plumbing and swaps only
the two ends: work arrives from the server instead of the Downloads folder, and
the outcome goes back over HTTP instead of into /tmp. Phase 3 replaces this file
with a Windows executable that talks CDP directly.

Setup (once):
    ~/.wayfinder-agent.json   {"base_url": "https://…", "token": "<paired token>"}
  or env: WAYFINDER_BASE_URL / WAYFINDER_AGENT_TOKEN

Run:
    LD_LIBRARY_PATH=$HOME/.local/chromium-libs python3 scripts/sap_agent.py
    --once      handle at most one job, then exit (for testing)
    --dry-run   fill every field but never press Save
"""
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from sap_trip_robot import (SCREEN_URL_PART, SEL, _find_screen, _grid_total,  # noqa: E402
                            _ensure_form_open, fill_line)

CONFIG_FILE = Path.home() / ".wayfinder-agent.json"
LOCK_FILE = Path.home() / ".wayfinder-agent.lock"
POLL_SEC = 5          # matches the page's own polling, so the strip feels live
HEARTBEAT_SEC = 10    # AGENT_ONLINE_SEC on the server is 25


def _claim_single_instance():
    """Hold a lock for as long as this process lives, or bail out.

    Both the Startup entry and the pairing handler start the agent, so two can
    easily be asked for. Two agents polling the same queue would pick up the
    same job and key every line into SAP twice."""
    import fcntl
    f = LOCK_FILE.open("w")
    try:
        fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return None
    return f          # kept open on purpose: closing it drops the lock


def _config(quiet: bool = False):
    """(base_url, token). Returns None when quiet and nothing is configured —
    the polling loop calls it every round to notice a fresh pairing."""
    cfg = {}
    try:
        cfg = json.loads(CONFIG_FILE.read_text())
    except Exception:
        pass
    base = os.environ.get("WAYFINDER_BASE_URL") or cfg.get("base_url") or ""
    token = os.environ.get("WAYFINDER_AGENT_TOKEN") or cfg.get("token") or ""
    if not base or not token:
        if quiet:
            return None
        print("this PC is not paired yet — open Review in the browser and "
              'click "Pair a PC", then "Pair this PC".')
        sys.exit(1)
    return base.rstrip("/"), token


BASE, TOKEN = "", ""


def _call(path, data=None):
    """One request to the server. Never raises: a dropped network must not end
    a run that is halfway through typing into SAP."""
    req = urllib.request.Request(
        BASE + path,
        data=json.dumps(data).encode() if data is not None else None,
        headers={"Content-Type": "application/json", "X-Agent-Token": TOKEN})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        if e.code in (401, 403):
            print("the server rejected this token — re-pair from Review.")
            sys.exit(1)
        print(f"  server said {e.code} on {path}")
    except Exception as e:
        print(f"  cannot reach the server ({e})")
    return None


def _report_state(edge, screen, job_id=None, done=None):
    body = {"edge": bool(edge), "screen": bool(screen)}
    if job_id:
        body["job_id"] = job_id
    if done is not None:
        body["done"] = done
    _call("/cardconv/agent/state", body)


def _look_at_edge(p):
    """(edge_up, screen_open) — the two things only this PC can answer.

    A short timeout on purpose: the default is 30 s, and a closed browser is
    the normal case here, so the whole loop would stall on the answer it was
    always going to get."""
    try:
        b = p.chromium.connect_over_cdp(f"http://{_gateway()}:9223", timeout=2500)
    except Exception:
        return False, False
    try:
        urls = [pg.url for c in b.contexts for pg in c.pages]
        return True, any(SCREEN_URL_PART in u for u in urls)
    finally:
        b.close()


def _gateway():
    from sap_trip_robot import _gateway_ip
    return _gateway_ip()


def _open_edge():
    """Ask Windows to start the robot Edge — the user should not have to.

    Through the scheduled task rather than the .bat directly: a process tree
    started from anything browser-ish is killed within about a second on this
    network, and a task started by the scheduler is not in that tree (72차).
    Signing in to Knox is still a person's job when the profile's session has
    lapsed; that is the one step no agent can take."""
    try:
        r = subprocess.run(["schtasks.exe", "/run", "/tn", "WayfinderRobotEdge"],
                           capture_output=True, timeout=25)
        if r.returncode == 0:
            print("  asked Windows to open the robot Edge.")
            return True
        print("  could not start the browser task — run 'Install SAP Agent' once.")
    except Exception as e:
        print(f"  could not start the browser task ({e})")
    return False


def run_job(p, job, dry_run=False):
    """Key one job in, reporting each line as it lands."""
    trip = job.get("trip") or next(iter(job.get("trips") or {}), "")
    lines = (job.get("trips") or {}).get(trip) or []
    print(f"job {job.get('id')}: '{trip}', {len(lines)} line(s)")
    saved, failures = [], []
    try:
        b, pg = _find_screen(p)
    except SystemExit:
        # _find_screen was written for a one-shot console and exits when the
        # entry screen never shows. Here that would kill a long-lived agent and
        # leave the job hanging with the page saying "waiting to be picked up"
        # forever — so it becomes an ordinary reported failure instead.
        print("  the entry screen never appeared — reporting the job as undone.")
        _call("/cardconv/agent/result",
              {"job_id": job.get("id"), "saved": [],
               "failures": [{"tx_id": l.get("tx_id"),
                             "why": "the SAP entry screen never opened"}
                            for l in lines]})
        return 0, lines
    pg.on("dialog", lambda d: (print(f"  [dialog] {d.message[:120]}"), d.accept()))
    for i, line in enumerate(lines, 1):
        head = f"[{i}/{len(lines)}] {line.get('date')} {line.get('merchant')} ${line.get('amount')}"
        print(head)
        try:
            _ensure_form_open(pg)
            # The export already decided Domestic/Overseas per line, so the
            # flag the old robot took on the command line is not consulted.
            fill_line(pg, line, overseas=True)
        except Exception as e:
            print(f"  fill failed: {e}")
            failures.append({"tx_id": line.get("tx_id"), "why": f"fill failed: {e}"})
            continue
        if dry_run:
            print("  (dry run — not saving)")
            continue
        try:
            before = _grid_total(pg)
            pg.click(SEL["save"])
            pg.wait_for_timeout(2500)
            after = _grid_total(pg)
            if before is not None and after is not None and after <= before:
                raise RuntimeError(f"grid Total stayed at {after} — the save did not land")
            saved.append(line.get("tx_id"))
            print(f"  saved (Total {before} -> {after}).")
        except Exception as e:
            print(f"  save failed: {e}")
            failures.append({"tx_id": line.get("tx_id"), "why": str(e)})
        _report_state(True, True, job.get("id"), len(saved))
    b.close()
    # Report even a run where nothing landed: the rows staying open with no
    # explanation on screen is the failure mode this whole path exists to end.
    _call("/cardconv/agent/result",
          {"job_id": job.get("id"),
           "saved": [i for i in saved if i],
           "failures": failures,
           # A fill-only run saves nothing by design; without this the page
           # would read the empty list as "every line was refused".
           "dry_run": bool(dry_run),
           "filled": len(lines) - len(failures)})
    print(f"done. {len(saved)}/{len(lines)} saved."
          if not dry_run else
          f"done. {len(lines) - len(failures)}/{len(lines)} filled, nothing saved.")
    return len(saved), failures


def main():
    global BASE, TOKEN
    # A watched console must show its progress as it happens, not when the
    # buffer happens to flush.
    try:
        sys.stdout.reconfigure(line_buffering=True)
    except AttributeError:
        pass
    lock = _claim_single_instance()
    if lock is None:
        print("another agent is already running — nothing to do.")
        return
    BASE, TOKEN = _config()
    once = "--once" in sys.argv
    dry_run = "--dry-run" in sys.argv
    # Check the token before anything slow, so a wrong one says so at once
    # instead of after the first browser probe times out.
    if _call("/cardconv/agent/job") is None:
        print("could not reach the server with this token — nothing will run.")
        sys.exit(1)
    print(f"agent up — {BASE} (polling every {POLL_SEC}s)"
          + (" [dry run]" if dry_run else ""))

    from playwright.sync_api import sync_playwright
    last_beat = 0.0
    with sync_playwright() as p:
        while True:
            # Re-read every round: pairing rewrites this file, and requiring a
            # restart to notice would put the user back in a terminal.
            fresh = _config(quiet=True)
            if fresh and fresh != (BASE, TOKEN):
                BASE, TOKEN = fresh
                print(f"config changed — now reporting to {BASE}")
            edge, screen = _look_at_edge(p)
            now = time.time()
            if now - last_beat >= HEARTBEAT_SEC:
                _report_state(edge, screen)
                last_beat = now
            job = _call("/cardconv/agent/job")
            if job and job.get("id"):
                # Work arrived and no browser is up — open it rather than
                # waiting fifteen minutes for someone to notice.
                if not edge:
                    _open_edge()
                try:
                    # The job can ask for fill-only too, so the safe first run
                    # is a checkbox on the page rather than a command-line flag
                    # nobody without a terminal can reach.
                    run_job(p, job, dry_run or bool(job.get("dry_run")))
                except Exception as e:
                    # Anything unhandled still has to close the job, or the
                    # page waits on a run that already ended.
                    print(f"  the run broke: {e}")
                    _call("/cardconv/agent/result",
                          {"job_id": job.get("id"), "saved": [],
                           "failures": [{"tx_id": None, "why": f"agent error: {e}"}]})
                if once:
                    return
            time.sleep(POLL_SEC)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nagent stopped.")
