"""Un-matching has to undo both halves, and stay undone (강프로 2026-07-28).

The Undo button cleared the receipt's flags and stopped there. The transaction
kept its link, so the Ledger read unmatched while Review still showed the pair
— and then the next pool rebuild re-matched the two, because a pending receipt
is a matching candidate like any other. The undo lasted until the next sync.
"""
import importlib

core = importlib.import_module("services._cardconv_core")


def _matched_pair():
    receipt = {
        "id": "r1", "file_id": "f1", "matched": True, "match_status": "matched",
        "matched_at": "2026-05-31T20:00:00", "card_brand": "amex",
        "usd_settled": 45.61, "match_locked": False,
        "matched_transaction": {"date": "2026-05-10", "amount": 45.61, "vendor": "SFG"},
        "ocr_date": "2026-05-10", "ocr_amount": 45.61, "ocr_merchant": "SF Giants",
    }
    tx = {"id": "tx1", "date": "2026-05-10", "amount": 45.61, "merchant": "SFG",
          "matched": True, "status": "open", "receipt": {"id": "r1", "file_id": "f1"}}
    return receipt, tx


def _isolate(monkeypatch, receipts, txs):
    st = {"ledger": {"entries": receipts}, "pool": {"entries": txs}}
    monkeypatch.setattr(core, "_load_ledger", lambda u: st["ledger"])
    monkeypatch.setattr(core, "_save_ledger", lambda u, d: st.update(ledger=d))
    monkeypatch.setattr(core, "_load_receipts", lambda u: st["ledger"]["entries"])
    monkeypatch.setattr(core, "_save_receipts", lambda u, r: st["ledger"].update(entries=r))
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: st["pool"])
    monkeypatch.setattr(core, "_save_tx_pool", lambda u, d: st.update(pool=d))
    return st


def test_undo_releases_the_transaction_too(monkeypatch):
    r, tx = _matched_pair()
    st = _isolate(monkeypatch, [r], [tx])
    kind, resp, *_ = core._handle_status_change("u", "r1", {"status": "pending_match"})
    assert resp["ok"] and resp["released"] == 1
    assert st["pool"]["entries"][0]["matched"] is False
    assert st["pool"]["entries"][0]["receipt"] is None


def test_undo_clears_what_the_match_wrote_on_the_receipt(monkeypatch):
    r, tx = _matched_pair()
    st = _isolate(monkeypatch, [r], [tx])
    core._handle_status_change("u", "r1", {"status": "pending_match"})
    e = st["ledger"]["entries"][0]
    assert e["matched"] is False
    assert e["matched_transaction"] is None
    assert e["matched_at"] is None
    assert e["usd_settled"] is None


def test_undo_restores_a_date_the_match_backfilled(monkeypatch):
    r, tx = _matched_pair()
    r["ocr_date_original"] = None      # OCR had no date; the statement supplied one
    r["ocr_date"] = "2026-05-10"
    st = _isolate(monkeypatch, [r], [tx])
    core._handle_status_change("u", "r1", {"status": "pending_match"})
    e = st["ledger"]["entries"][0]
    assert e["ocr_date"] is None
    assert "ocr_date_original" not in e   # the marker is spent, not left behind


def test_the_matcher_leaves_a_hand_unmatched_receipt_alone(monkeypatch):
    """Otherwise the next rebuild re-links the pair the user just separated."""
    r, _ = _matched_pair()
    r.update(matched=False, match_status="pending_match", match_locked=True)
    idx, fx, dirty = core._build_receipt_index([r], "u")
    assert not idx and not fx


def test_asking_for_a_rematch_re_arms_it():
    r, _ = _matched_pair()
    r.update(matched=False, match_status="pending_match", match_locked=True)
    idx, _, _ = core._build_receipt_index([r], "u")
    assert not idx                      # locked: skipped
    r["match_locked"] = False           # what _handle_rematch does
    idx2, _, _ = core._build_receipt_index([r], "u")
    assert idx2                         # candidate again


def test_linking_by_hand_re_arms_it():
    r, tx = _matched_pair()
    r.update(matched=False, match_locked=True)
    core._apply_receipt_match(tx, r, [r])
    assert r["match_locked"] is False


def test_a_one_sided_leftover_heals(monkeypatch):
    """Data already stuck in the old shape releases on the next load."""
    r, tx = _matched_pair()
    r.update(matched=False, match_status="pending_match")   # receipt let go
    st = _isolate(monkeypatch, [r], [tx])                   # transaction did not
    monkeypatch.setattr(core, "_rematch_pool", lambda u: None)
    core._heal_orphan_matches("u")
    assert st["pool"]["entries"][0]["receipt"] is None
    assert st["pool"]["entries"][0]["matched"] is False
