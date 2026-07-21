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


def test_no_matched_receipts_short_circuits(monkeypatch):
    st = _isolate(monkeypatch, [{"id": "r1", "matched": False}], [])
    # _load_tx_pool must not even be called — replace it with a tripwire.
    monkeypatch.setattr(core, "_load_tx_pool",
                        lambda u: (_ for _ in ()).throw(AssertionError("pool loaded")))
    core._heal_orphan_matches("u")
    assert st["saves"]["receipts"] == 0
