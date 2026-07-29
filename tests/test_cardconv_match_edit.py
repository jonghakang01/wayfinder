"""The manual-match popover can fix a receipt, not just link it (강프로 2026-07-28).

A receipt that failed to match is usually one whose OCR is wrong, and the list
that surfaces it is the natural place to correct it — otherwise you leave for
the Ledger, edit, come back, and re-open the popover.

These are render-contract tests: the popover is client-side, so what's checked
here is that the markup and handlers the browser needs are actually emitted.
The behaviour itself was verified in the browser (save round-trip, refusal of a
non-numeric amount, one editor at a time, 44px targets at 390px).
"""
import importlib

render = importlib.import_module("services._cardconv_render")
core = importlib.import_module("services._cardconv_core")


def _page():
    return render._RV_HTML if hasattr(render, "_RV_HTML") else None


def test_edit_handlers_are_defined_in_the_review_page():
    src = open(render.__file__, encoding="utf-8").read()
    for fn in ("function rvToggleEdit", "function rvSaveEdit"):
        assert fn in src, fn


def test_the_row_still_matches_on_click():
    """Editing is additive — the popover's reason for existing must survive."""
    src = open(render.__file__, encoding="utf-8").read()
    assert 'onclick="rvDoMatch(this.parentNode)"' in src
    assert "class=\"mm-edit\"" in src


def test_no_inline_onclick_carries_an_escaped_quote():
    """An escaped quote inside an f-string-rendered attribute kills the whole
    script block — the page loads and every handler is simply undefined."""
    src = open(render.__file__, encoding="utf-8").read()
    assert "closest(\\'" not in src


def test_cleared_fields_use_a_sentinel():
    """parse_qs drops empty values, so a blank field would never reach the
    server and the old value would silently survive the save."""
    src = open(render.__file__, encoding="utf-8").read()
    assert "'__clear__'" in src.split("function rvSaveEdit")[1][:1200]


def test_the_update_endpoint_accepts_every_edited_field(monkeypatch):
    """The form posts these four; the backend has to take all of them."""
    entry = {"id": "r1", "ocr_date": "2026-01-01", "ocr_merchant": "Old",
             "ocr_printed_amount": 1.0, "ocr_handwritten_amount": None,
             "match_status": "pending_match", "matched": False}
    st = {"ledger": {"entries": [entry]}}
    monkeypatch.setattr(core, "_load_ledger", lambda u: st["ledger"])
    monkeypatch.setattr(core, "_save_ledger", lambda u, d: st.update(ledger=d))
    monkeypatch.setattr(core, "_load_receipts", lambda u: st["ledger"]["entries"])
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: {"entries": []})

    kind, resp, *_ = core._handle_ledger_update("u", "r1", {
        "ocr_date": ["2026-05-10"], "ocr_merchant": ["New Merchant"],
        "ocr_printed_amount": ["45.61"], "ocr_handwritten_amount": ["50.00"],
    })
    assert resp["ok"]
    e = st["ledger"]["entries"][0]
    assert e["ocr_date"] == "2026-05-10"
    assert e["ocr_merchant"] == "New Merchant"
    assert e["ocr_printed_amount"] == 45.61
    assert e["ocr_handwritten_amount"] == 50.00
