"""One-sided match links heal lazily on load (2026-07-21 Sumiya case).

A pool rebuild can drop the transaction-side link while the receipt keeps its
matched flags: Ledger shows "Matched", Review shows the transaction open, and
the matcher skips the receipt forever. _heal_orphan_matches must detect the
orphan and either re-link it (matching open tx exists) or reset it to
pending_match (no candidate), and must be a no-op when links are consistent.
"""
import importlib

core = importlib.import_module("services._cardconv_core")


def _isolate(monkeypatch, receipts, pool_entries):
    state = {"receipts": receipts, "pool": {"entries": pool_entries},
             "saves": {"receipts": 0, "pool": 0}}

    def save_receipts(u, r):
        state["receipts"] = r
        state["saves"]["receipts"] += 1

    def save_pool(u, p):
        state["pool"] = p
        state["saves"]["pool"] += 1

    monkeypatch.setattr(core, "_load_receipts", lambda u: state["receipts"])
    monkeypatch.setattr(core, "_save_receipts", save_receipts)
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: state["pool"])
    monkeypatch.setattr(core, "_save_tx_pool", save_pool)
    return state


def _orphan_receipt(rid="r1", amount=143.65, date="2025-12-13"):
    return {"id": rid, "matched": True, "match_status": "matched",
            "usd_settled": amount, "ocr_date": date, "ocr_amount": amount,
            "ocr_printed_amount": amount, "ocr_handwritten_amount": None,
            "ocr_currency": "USD", "completed": False,
            "matched_transaction": {"date": date, "amount": amount, "vendor": "X"}}


def test_orphan_relinks_to_open_transaction(monkeypatch):
    st = _isolate(monkeypatch, [_orphan_receipt()],
                  [{"id": "t1", "date": "2025-12-13", "amount": 143.65,
                    "merchant": "TST* SUMIYA", "matched": False,
                    "receipt": None, "status": "open"}])
    core._heal_orphan_matches("u")
    tx = st["pool"]["entries"][0]
    assert tx["matched"] and tx["receipt"]["id"] == "r1"
    assert st["receipts"][0]["matched"] is True


def test_orphan_without_candidate_resets_to_pending(monkeypatch):
    st = _isolate(monkeypatch, [_orphan_receipt()], [])
    core._heal_orphan_matches("u")
    r = st["receipts"][0]
    assert r["matched"] is False and r["match_status"] == "pending_match"
    assert r["usd_settled"] is None
    assert st["saves"]["receipts"] == 1


def test_consistent_links_are_untouched(monkeypatch):
    receipt = dict(_orphan_receipt())
    st = _isolate(monkeypatch, [receipt],
                  [{"id": "t1", "matched": True, "receipt": {"id": "r1"},
                    "status": "open"}])
    core._heal_orphan_matches("u")
    assert st["saves"]["receipts"] == 0 and st["saves"]["pool"] == 0


def test_consistent_state_triggers_no_rematch(monkeypatch):
    """No orphans on either side → the check stays a cheap no-op (the old
    skip-pool-load shortcut hid ghost tx links when no receipt was matched,
    so the pool is now always inspected — but rematch must not run)."""
    st = _isolate(monkeypatch, [{"id": "r1", "matched": False}], [])
    monkeypatch.setattr(core, "_rematch_pool",
                        lambda u: (_ for _ in ()).throw(AssertionError("rematch ran")))
    core._heal_orphan_matches("u")
    assert st["saves"]["receipts"] == 0


def test_ghost_tx_link_heals_and_repairs_to_survivor(monkeypatch):
    """Deleting the matched copy of a duplicate leaves the transaction pointing
    at a ghost receipt id (2026-07-22 STARBUCKS case): the matcher skipped the
    'matched' tx forever and the surviving copy could never pair. The rematch
    heal must unlink the ghost and immediately re-match the survivor."""
    survivor = {"id": "rB", "matched": False, "match_status": "pending_match",
                "ocr_date": "2026-07-13", "ocr_amount": 26.65,
                "ocr_printed_amount": 26.65, "ocr_handwritten_amount": None,
                "ocr_currency": "USD", "completed": False,
                "matched_transaction": {"date": "2026-07-13", "amount": 26.65,
                                        "vendor": "STARBUCKS DIGITAL"}}
    ghost_tx = {"id": "t1", "date": "2026-07-13", "amount": 26.65,
                "merchant": "STARBUCKS DIGITAL OPEN LO", "matched": True,
                "receipt": {"id": "rA_deleted"}, "status": "open"}
    st = _isolate(monkeypatch, [survivor], [ghost_tx])
    core._rematch_pool("u")
    tx = st["pool"]["entries"][0]
    r = st["receipts"][0]
    assert tx["matched"] is True
    assert (tx.get("receipt") or {}).get("id") == "rB"
    assert r["matched"] is True and r["match_status"] == "matched"


def test_receipt_demote_clears_stale_snapshot(monkeypatch):
    """A receipt demoted to pending by the orphan heal must drop its old
    matched_transaction snapshot — a pending row with a ↳ matched line reads
    as a stuck half-match."""
    orphan = _orphan_receipt()
    st = _isolate(monkeypatch, [orphan], [])   # no tx at all
    core._rematch_pool("u")
    r = st["receipts"][0]
    assert r["matched"] is False
    assert r["match_status"] == "pending_match"
    assert r.get("matched_transaction") is None
