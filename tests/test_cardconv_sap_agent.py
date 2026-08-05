"""The SAP agent's contract with the server (spec 2026-08-05-sap-agent-multiuser).

The old path dropped a file in /tmp for Review to find, which only ever worked
when the page and the robot sat on the same machine — and the real usage is a
browser on prod with the robot on a PC (verified 2026-08-05: the export in
Downloads matched prod's rows 4/4 and local's 0/4). So the PC now reports in
over HTTP, and everything below is that contract.
"""
import importlib
import json

core = importlib.import_module("services._cardconv_core")


def _tx(i, usage="NY Trip", rcpt_id=None, **kw):
    e = {"id": f"t{i}", "status": "open", "date": "2026-07-10",
         "merchant": "FAT WITCH BAKERY", "amount": 62.28, "usage": usage,
         "gl": 53410177, "ser": "160", "purpose": "Meal", "matched": bool(rcpt_id),
         "cash": False}
    if rcpt_id:
        e["receipt"] = {"id": rcpt_id}
    e.update(kw)
    return e


def _wire(monkeypatch, tmp_path, entries, receipts=None):
    """Point every store at tmp_path so a test never touches real data."""
    monkeypatch.setattr(core, "DATA_DIR", tmp_path)
    monkeypatch.setattr(core, "AGENT_TOKENS_FILE", tmp_path / "agent_tokens.json")
    monkeypatch.setattr(core, "_ensure_dirs", lambda: None)
    pool = {"entries": entries}
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: pool)
    monkeypatch.setattr(core, "_save_tx_pool", lambda u, p: pool.update(p))
    monkeypatch.setattr(core, "_load_receipts", lambda u: receipts or [])
    monkeypatch.setattr(core, "_apply_receipt_completion", lambda *a, **k: None)
    monkeypatch.setattr(core, "_pkey", lambda u: u)
    return pool


# ── pairing ─────────────────────────────────────────────────────────────────

def test_token_resolves_to_its_owner(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path, [])
    tok = core._issue_agent_token("someone")
    assert core.resolve_agent_token(tok) == "someone"
    assert core.resolve_agent_token("") is None
    assert core.resolve_agent_token("nonsense") is None


def test_reissuing_retires_the_previous_token(monkeypatch, tmp_path):
    """A token pasted onto a PC that no longer runs it must stop working."""
    _wire(monkeypatch, tmp_path, [])
    old = core._issue_agent_token("someone")
    new = core._issue_agent_token("someone")
    assert core.resolve_agent_token(old) is None
    assert core.resolve_agent_token(new) == "someone"


def test_pairing_refuses_to_mint_over_a_live_pairing(monkeypatch, tmp_path):
    """A click landing before the page knew a PC was paired used to wipe it —
    the decision cannot live in the client (observed 2026-08-05)."""
    _wire(monkeypatch, tmp_path, [])
    first = core._handle_agent_pair("me", {})[1]
    assert first["token"] and first["paired"] is False
    again = core._handle_agent_pair("me", {})[1]
    assert again["paired"] is True and "token" not in again
    assert core.resolve_agent_token(first["token"]) == "me"   # still works


def test_pairing_mints_when_told_to(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path, [])
    old = core._handle_agent_pair("me", {})[1]["token"]
    new = core._handle_agent_pair("me", {"force": True})[1]["token"]
    assert new and new != old
    assert core.resolve_agent_token(old) is None


def test_force_accepts_the_shapes_a_form_post_sends(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path, [])
    core._handle_agent_pair("me", {})
    assert "token" in core._handle_agent_pair("me", {"force": ["true"]})[1]
    assert "token" in core._handle_agent_pair("me", {"force": "1"})[1]
    assert "token" not in core._handle_agent_pair("me", {"force": "no"})[1]


def test_reissuing_leaves_other_accounts_alone(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path, [])
    theirs = core._issue_agent_token("them")
    core._issue_agent_token("me")
    assert core.resolve_agent_token(theirs) == "them"


# ── presence ────────────────────────────────────────────────────────────────

def test_unpaired_then_paired_then_online(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path, [])
    assert core._agent_status("me") == {"paired": False, "online": False}
    core._issue_agent_token("me")
    st = core._agent_status("me")
    assert st["paired"] and not st["online"]      # never checked in
    core._agent_seen("me", {"edge": True, "screen": False})
    st = core._agent_status("me")
    assert st["online"] and st["edge"] and not st["screen"]


def test_a_stale_check_in_reads_as_offline(monkeypatch, tmp_path):
    """The button must not promise work to a PC that stopped listening."""
    _wire(monkeypatch, tmp_path, [])
    core._issue_agent_token("me")
    core._agent_seen("me", {"edge": True, "screen": True})
    toks = core._load_agent_tokens()
    for r in toks.values():
        r["last_seen"] = "2020-01-01T00:00:00"
    core._save_agent_tokens(toks)
    assert core._agent_status("me")["online"] is False


# ── queueing ────────────────────────────────────────────────────────────────

def _online(monkeypatch, tmp_path, entries, receipts=None):
    pool = _wire(monkeypatch, tmp_path, entries, receipts)
    core._issue_agent_token("me")
    core._agent_seen("me", {"edge": True, "screen": True})
    return pool


def test_offline_agent_cannot_be_handed_work(monkeypatch, tmp_path):
    _wire(monkeypatch, tmp_path, [_tx(1)])
    core._issue_agent_token("me")
    out = core._handle_agent_submit("me", {"ids": ["t1"]})
    assert out[2] == 409 and "offline" in out[1]["error"]


def test_queueing_builds_a_job_with_the_lines(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, [_tx(1), _tx(2)])
    out = core._handle_agent_submit("me", {"ids": ["t1", "t2"]})
    assert out[1]["ok"] and out[1]["total"] == 2 and out[1]["trip"] == "NY Trip"
    job = core._load_agent_job("me")
    assert job["state"] == "queued" and job["pkey"] == "me"
    assert len(job["trips"]["NY Trip"]) == 2
    assert {l["vendor_kind"] for l in job["trips"]["NY Trip"]} == {"D"}


def test_a_second_job_is_refused_while_one_is_live(monkeypatch, tmp_path):
    """SAP's screen is one form typed serially — two jobs would interleave."""
    _online(monkeypatch, tmp_path, [_tx(1)])
    core._handle_agent_submit("me", {"ids": ["t1"]})
    out = core._handle_agent_submit("me", {"ids": ["t1"]})
    assert out[2] == 409


def test_rows_without_a_trip_tag_are_refused(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, [_tx(1, usage="Regular")])
    out = core._handle_agent_submit("me", {"ids": ["t1"]})
    assert out[2] == 400 and "no trip-tagged rows" in out[1]["error"]


def test_two_trips_at_once_are_refused(monkeypatch, tmp_path):
    """One trip per submission — SAP files each trip separately."""
    _online(monkeypatch, tmp_path, [_tx(1, "NY Trip"), _tx(2, "Korea Trip")])
    out = core._handle_agent_submit("me", {"ids": ["t1", "t2"]})
    assert out[2] == 400 and "one trip at a time" in out[1]["error"]


def test_empty_selection_is_refused(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, [_tx(1)])
    assert core._handle_agent_submit("me", {"ids": []})[2] == 400


# ── the run ─────────────────────────────────────────────────────────────────

def test_agent_receives_the_job_once_it_is_queued(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, [_tx(1)])
    assert core._handle_agent_job("me")[1] == {}          # nothing yet
    core._handle_agent_submit("me", {"ids": ["t1"]})
    job = core._handle_agent_job("me")[1]
    assert job["state"] == "queued" and job["trips"]["NY Trip"]


def test_progress_moves_the_job_to_running(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, [_tx(1), _tx(2)])
    core._handle_agent_submit("me", {"ids": ["t1", "t2"]})
    jid = core._load_agent_job("me")["id"]
    core._handle_agent_state("me", {"edge": "1", "screen": "1",
                                    "job_id": jid, "done": 1})
    job = core._load_agent_job("me")
    assert job["state"] == "running" and job["progress"]["done"] == 1


def test_result_marks_only_the_rows_that_landed(monkeypatch, tmp_path):
    pool = _online(monkeypatch, tmp_path, [_tx(1), _tx(2), _tx(3)])
    core._handle_agent_submit("me", {"ids": ["t1", "t2", "t3"]})
    jid = core._load_agent_job("me")["id"]
    out = core._handle_agent_result("me", {
        "job_id": jid, "saved": ["t1", "t3"],
        "failures": [{"tx_id": "t2", "why": "GTE refused the Save"}]})
    assert out[1]["ok"] and out[1]["marked"] == 2
    assert {e["id"]: e["status"] for e in pool["entries"]} == {
        "t1": "in_progress", "t2": "open", "t3": "in_progress"}
    job = core._load_agent_job("me")
    assert job["state"] == "done" and job["results"]["saved"] == ["t1", "t3"]
    assert job["results"]["failures"][0]["why"] == "GTE refused the Save"


def test_a_run_that_saved_nothing_still_reports(monkeypatch, tmp_path):
    """Rows left open with no explanation on screen is the failure mode this
    whole path exists to end."""
    pool = _online(monkeypatch, tmp_path, [_tx(1)])
    core._handle_agent_submit("me", {"ids": ["t1"]})
    jid = core._load_agent_job("me")["id"]
    out = core._handle_agent_result("me", {
        "job_id": jid, "saved": [],
        "failures": [{"tx_id": "t1", "why": "Save refused"}]})
    assert out[1]["marked"] == 0
    assert pool["entries"][0]["status"] == "open"
    assert core._load_agent_job("me")["state"] == "done"


def test_a_finished_job_is_not_handed_out_again(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, [_tx(1)])
    core._handle_agent_submit("me", {"ids": ["t1"]})
    jid = core._load_agent_job("me")["id"]
    core._handle_agent_result("me", {"job_id": jid, "saved": ["t1"]})
    assert core._handle_agent_job("me")[1] == {}


def test_a_result_for_an_unknown_job_is_refused(monkeypatch, tmp_path):
    """A stale agent restarting must not reopen a job that already closed."""
    _online(monkeypatch, tmp_path, [_tx(1)])
    assert core._handle_agent_result("me", {"job_id": "nope", "saved": ["t1"]})[2] == 404
    core._handle_agent_submit("me", {"ids": ["t1"]})
    assert core._handle_agent_result("me", {"job_id": "wrong", "saved": ["t1"]})[2] == 404


def test_result_cannot_mark_rows_outside_the_pool(monkeypatch, tmp_path):
    """The agent reports ids; the server still only touches its own rows."""
    pool = _online(monkeypatch, tmp_path, [_tx(1)])
    core._handle_agent_submit("me", {"ids": ["t1"]})
    jid = core._load_agent_job("me")["id"]
    out = core._handle_agent_result("me", {"job_id": jid,
                                          "saved": ["t1", "someone-elses-row"]})
    assert out[1]["marked"] == 1
    assert [e["id"] for e in pool["entries"]] == ["t1"]


# ── what the screen reads ───────────────────────────────────────────────────

def test_state_endpoint_carries_agent_and_job(monkeypatch, tmp_path):
    _online(monkeypatch, tmp_path, [_tx(1)])
    st = core._handle_robot_state("me")[1]
    assert st["agent"]["online"] and st["job"] is None
    core._handle_agent_submit("me", {"ids": ["t1"]})
    st = core._handle_robot_state("me")[1]
    assert st["job"]["state"] == "queued"


def test_jobs_are_scoped_per_card_profile(monkeypatch, tmp_path):
    """Rows live in per-profile files; a job must not leak across them."""
    _online(monkeypatch, tmp_path, [_tx(1)])
    core._handle_agent_submit("me", {"ids": ["t1"]})
    monkeypatch.setattr(core, "_pkey", lambda u: "me@ceo_card")
    assert core._load_agent_job("me") == {}
    assert core._handle_agent_job("me")[1] == {}
