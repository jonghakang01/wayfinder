"""A foreign receipt's USD figure follows the numbers it derives from
(강프로 2026-08-07): correct the ARS amount — or the date, which picks the
rate — and the USD estimate must move with it, not sit stale from OCR time.
"""
import importlib

core = importlib.import_module("services._cardconv_core")

ENTRY = {
    "id": "r1", "ocr_currency": "ARS",
    "ocr_printed_amount": 10000.0, "ocr_handwritten_amount": None,
    "ocr_amount": 10000.0, "usd_estimate": 10.0, "fx_rate": 1000.0,
}


def _update(monkeypatch, body, entry=None):
    store = {"entries": [dict(entry or ENTRY)]}
    monkeypatch.setattr(core, "_load_ledger", lambda u: store)
    monkeypatch.setattr(core, "_save_ledger", lambda u, l: None)
    # 1 USD = 1250 ARS on whatever date is asked for
    monkeypatch.setattr(core, "_fx_rate", lambda cur, d: 1250.0)
    kind, payload, *rest = core._handle_ledger_update("someone", "r1", body)
    assert payload.get("ok"), payload
    return store["entries"][0], payload


def test_editing_the_ars_amount_moves_the_usd(monkeypatch):
    e, _ = _update(monkeypatch, {"ocr_printed_amount": ["25000"]})
    assert e["ocr_amount"] == 25000.0
    assert e["usd_estimate"] == 20.0          # 25000 / 1250
    assert e["fx_rate"] == 1250.0


def test_editing_the_date_repicks_the_rate(monkeypatch):
    seen = {}
    def rate(cur, d):
        seen["date"] = d
        return 1250.0
    store = {"entries": [dict(ENTRY)]}
    monkeypatch.setattr(core, "_load_ledger", lambda u: store)
    monkeypatch.setattr(core, "_save_ledger", lambda u, l: None)
    monkeypatch.setattr(core, "_fx_rate", rate)
    core._handle_ledger_update("someone", "r1", {"ocr_date": ["2026-08-06"]})
    assert seen["date"] == "2026-08-06"


def test_a_usd_receipt_gains_no_phantom_estimate(monkeypatch):
    e, _ = _update(monkeypatch, {"ocr_printed_amount": ["50"]},
                   entry={"id": "r1", "ocr_currency": "USD",
                          "ocr_printed_amount": 10.0,
                          "ocr_handwritten_amount": None, "ocr_amount": 10.0})
    assert "usd_estimate" not in e or e.get("usd_estimate") is None


def test_a_failed_rate_keeps_the_old_estimate(monkeypatch):
    """A missing rate must not blank a number that was at least in the
    ballpark — stale beats gone."""
    store = {"entries": [dict(ENTRY)]}
    monkeypatch.setattr(core, "_load_ledger", lambda u: store)
    monkeypatch.setattr(core, "_save_ledger", lambda u, l: None)
    monkeypatch.setattr(core, "_fx_rate", lambda cur, d: None)
    core._handle_ledger_update("someone", "r1", {"ocr_printed_amount": ["25000"]})
    assert store["entries"][0]["usd_estimate"] == 10.0


def test_the_saved_entry_rides_back_in_the_response(monkeypatch):
    """The panel shows what was saved instead of closing on a promise."""
    _, payload = _update(monkeypatch, {"ocr_printed_amount": ["25000"]})
    assert payload["entry"]["usd_estimate"] == 20.0
    assert payload["entry"]["id"] == "r1"
