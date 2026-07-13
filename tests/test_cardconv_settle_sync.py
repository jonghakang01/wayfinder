"""Settlement status sync: one status, both surfaces (Ledger ↔ Review).

Every path that changes settlement state must keep the receipt-level
`completed` flag and the linked transaction's `status` in agreement:
- Ledger bulk status action  → tx status + receipt flag
- Ledger ✓ Complete / undo   → receipt flag + tx status
- Review set-status/complete → tx status + receipt flag
"""
import importlib

core = importlib.import_module("services._cardconv_core")


def _isolate(monkeypatch, ledger_entries, pool_entries):
    """In-memory ledger + tx pool; Drive moves are no-ops that count attempts."""
    state = {"ledger": {"entries": ledger_entries},
             "pool": {"entries": pool_entries}}
    monkeypatch.setattr(core, "_load_ledger", lambda u: state["ledger"])
    monkeypatch.setattr(core, "_save_ledger", lambda u, l: state.update(ledger=l))
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: state["pool"])
    monkeypatch.setattr(core, "_save_tx_pool", lambda u, p: state.update(pool=p))
    monkeypatch.setattr(core, "_archive_to_completed", lambda u, fids: len(fids))
    monkeypatch.setattr(core, "_restore_from_completed", lambda u, fids: len(fids))
    return state


def _receipt(rid, completed=False):
    return {"id": rid, "completed": completed, "file_id": None}


def _tx(tid, rid=None, status="open"):
    e = {"id": tid, "status": status}
    if rid:
        e["receipt"] = {"id": rid}
    return e


def test_ledger_bulk_settle_completed_syncs_both(monkeypatch):
    st = _isolate(monkeypatch,
                  [_receipt("r1"), _receipt("r2")],          # r2 unmatched
                  [_tx("t1", "r1")])
    kind, body, *_ = core._handle_ledger_bulk("u", {"ids": ["r1", "r2"],
                                                    "action": "settle",
                                                    "value": "completed"})
    assert body["ok"] and body["updated"] == 2 and body["tx_updated"] == 1
    assert st["pool"]["entries"][0]["status"] == "completed"
    assert all(e["completed"] for e in st["ledger"]["entries"])


def test_ledger_bulk_settle_in_progress_uncompletes_receipt(monkeypatch):
    st = _isolate(monkeypatch,
                  [_receipt("r1", completed=True)],
                  [_tx("t1", "r1", status="completed")])
    core._handle_ledger_bulk("u", {"ids": ["r1"], "action": "settle",
                                   "value": "in_progress"})
    assert st["pool"]["entries"][0]["status"] == "in_progress"
    assert st["ledger"]["entries"][0]["completed"] is False


def test_ledger_bulk_settle_rejects_bad_status(monkeypatch):
    _isolate(monkeypatch, [_receipt("r1")], [])
    res = core._handle_ledger_bulk("u", {"ids": ["r1"], "action": "settle",
                                         "value": "settled"})
    assert res[2] == 400


def test_ledger_complete_mirrors_tx(monkeypatch):
    st = _isolate(monkeypatch, [_receipt("r1")], [_tx("t1", "r1")])
    core._handle_ledger_complete("u", {"ids": ["r1"]})
    assert st["ledger"]["entries"][0]["completed"] is True
    assert st["pool"]["entries"][0]["status"] == "completed"
    core._handle_ledger_complete("u", {"ids": ["r1"], "undo": True})
    assert st["ledger"]["entries"][0]["completed"] is False
    assert st["pool"]["entries"][0]["status"] == "open"


def test_review_set_status_mirrors_receipt(monkeypatch):
    st = _isolate(monkeypatch, [_receipt("r1")], [_tx("t1", "r1")])
    core._handle_review_set_status("u", {"ids": ["t1"], "status": "completed"})
    assert st["ledger"]["entries"][0]["completed"] is True
    core._handle_review_set_status("u", {"ids": ["t1"], "status": "in_progress"})
    assert st["pool"]["entries"][0]["status"] == "in_progress"
    assert st["ledger"]["entries"][0]["completed"] is False


def test_review_complete_mirrors_receipt(monkeypatch):
    st = _isolate(monkeypatch, [_receipt("r1")], [_tx("t1", "r1")])
    core._handle_review_complete("u", {"ids": ["t1"]})
    assert st["ledger"]["entries"][0]["completed"] is True
    core._handle_review_complete("u", {"ids": ["t1"], "undo": True})
    assert st["ledger"]["entries"][0]["completed"] is False
    assert st["pool"]["entries"][0]["status"] == "open"


def test_drive_move_skipped_when_flags_already_agree(monkeypatch):
    """Status changes that don't cross the completed boundary must not
    trigger Drive move attempts (no false 'move failed' warnings)."""
    calls = []
    st = _isolate(monkeypatch,
                  [{"id": "r1", "completed": False, "file_id": "f1",
                    "archived_drive": False}],
                  [_tx("t1", "r1")])
    monkeypatch.setattr(core, "_archive_to_completed",
                        lambda u, fids: calls.append(("archive", set(fids))) or len(fids))
    monkeypatch.setattr(core, "_restore_from_completed",
                        lambda u, fids: calls.append(("restore", set(fids))) or len(fids))
    # open → in_progress: file already in Receipts, nothing to move
    core._handle_ledger_bulk("u", {"ids": ["r1"], "action": "settle",
                                   "value": "in_progress"})
    assert calls == []
    # → completed: crosses the boundary, archive attempted once
    core._handle_ledger_bulk("u", {"ids": ["r1"], "action": "settle",
                                   "value": "completed"})
    assert calls == [("archive", {"f1"})]
    assert st["ledger"]["entries"][0]["archived_drive"] is True


def test_review_unmatched_tx_touches_no_receipt(monkeypatch):
    st = _isolate(monkeypatch, [_receipt("r1")], [_tx("t1")])  # tx has no receipt
    core._handle_review_set_status("u", {"ids": ["t1"], "status": "completed"})
    assert st["pool"]["entries"][0]["status"] == "completed"
    assert st["ledger"]["entries"][0]["completed"] is False
