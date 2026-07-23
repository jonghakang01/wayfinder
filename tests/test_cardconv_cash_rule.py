"""Business rule (강프로 2026-07-22): cash can never match — matching runs
against the AMEX statement, so matched ⇒ AMEX unconditionally.

- Cash receipts (card_brand='other') are excluded from matching candidates.
- Flipping a matched receipt to Cash is blocked (single edit and bulk).
- Manually marking a receipt matched forces card_brand='amex'.
"""
import importlib

core = importlib.import_module("services._cardconv_core")


def _isolate(monkeypatch, receipts, pool_entries):
    state = {"receipts": receipts, "ledger": {"entries": receipts},
             "pool": {"entries": pool_entries}}
    monkeypatch.setattr(core, "_load_receipts", lambda u: state["receipts"])
    monkeypatch.setattr(core, "_save_receipts", lambda u, r: state.update(receipts=r))
    monkeypatch.setattr(core, "_load_ledger", lambda u: state["ledger"])
    monkeypatch.setattr(core, "_save_ledger", lambda u, l: state.update(ledger=l))
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: state["pool"])
    monkeypatch.setattr(core, "_save_tx_pool", lambda u, p: state.update(pool=p))
    return state


def _receipt(rid, brand=None, matched=False, amount=10.0, date="2026-07-01"):
    return {"id": rid, "card_brand": brand, "matched": matched,
            "match_status": "matched" if matched else "pending_match",
            "ocr_date": date, "ocr_amount": amount, "ocr_printed_amount": amount,
            "ocr_handwritten_amount": None, "ocr_currency": "USD", "completed": False}


def test_cash_receipt_never_enters_matching(monkeypatch):
    st = _isolate(monkeypatch,
                  [_receipt("r_cash", brand="other")],
                  [{"id": "t1", "date": "2026-07-01", "amount": 10.0,
                    "merchant": "X", "matched": False, "receipt": None,
                    "status": "open"}])
    res = core._rematch_pool("u")
    assert res["matched"] == 0
    assert st["receipts"][0]["matched"] is False
    assert st["receipts"][0]["card_brand"] == "other"


def test_amex_sibling_matches_where_cash_would_not(monkeypatch):
    st = _isolate(monkeypatch,
                  [_receipt("r_cash", brand="other"),
                   _receipt("r_amex", brand=None, date="2026-07-01")],
                  [{"id": "t1", "date": "2026-07-01", "amount": 10.0,
                    "merchant": "X", "matched": False, "receipt": None,
                    "status": "open"}])
    res = core._rematch_pool("u")
    assert res["matched"] == 1
    by_id = {r["id"]: r for r in st["receipts"]}
    assert by_id["r_amex"]["matched"] is True
    assert by_id["r_amex"]["card_brand"] == "amex"
    assert by_id["r_cash"]["matched"] is False


def test_matched_receipt_cannot_become_cash_single_edit(monkeypatch):
    st = _isolate(monkeypatch, [_receipt("r1", brand="amex", matched=True)], [])
    kind, resp, *_ = core._handle_ledger_update("u", "r1", {"card_brand": ["other"]})
    assert resp["ok"] and resp["cash_blocked"] is True
    assert st["ledger"]["entries"][0]["card_brand"] == "amex"


def test_matched_receipt_cannot_become_cash_bulk(monkeypatch):
    st = _isolate(monkeypatch,
                  [_receipt("r1", brand="amex", matched=True),
                   _receipt("r2", brand="visa", matched=False)], [])
    kind, resp, *_ = core._handle_ledger_bulk(
        "u", {"ids": ["r1", "r2"], "action": "card", "value": "other"})
    assert resp["cash_blocked"] == 1 and resp["updated"] == 1
    by_id = {r["id"]: r for r in st["ledger"]["entries"]}
    assert by_id["r1"]["card_brand"] == "amex"
    assert by_id["r2"]["card_brand"] == "other"


def test_manual_mark_matched_forces_amex(monkeypatch):
    st = _isolate(monkeypatch, [_receipt("r1", brand="other")], [])
    core._handle_status_change("u", "r1", {"status": "matched"})
    assert st["ledger"]["entries"][0]["card_brand"] == "amex"
