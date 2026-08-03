"""Trip-tagged rows (usage other than Regular) leave the bulk SAP xlsx and
travel through their own JSON export instead — SAP's trip flow takes one
submission per line, and a row in both files would be charged twice
(spec 2026-08-03-trip-submission-automation, Q3).
"""
import importlib
import json

core = importlib.import_module("services._cardconv_core")


def _tx(i, usage="Regular", matched=False, rcpt_id=None, **kw):
    e = {"id": f"t{i}", "status": "open", "date": "2026-07-10",
         "merchant": "HOTEL SEOUL", "amount": 120.0, "usage": usage,
         "gl": 53270377, "ser": "306", "purpose": "Hotel stay",
         "matched": matched, "cash": False}
    if rcpt_id:
        e["receipt"] = {"id": rcpt_id}
    e.update(kw)
    return e


def _isolate(monkeypatch, pool_entries, receipts=None):
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: {"entries": pool_entries})
    monkeypatch.setattr(core, "_load_receipts", lambda u: receipts or [])
    monkeypatch.setattr(core, "_export_tag", lambda u: "tester")


def test_effective_usage_prefers_matched_receipt():
    rcpts = {"r1": {"id": "r1", "usage": "Korea Trip"}}
    assert core._effective_usage(_tx(1, "Regular", matched=True, rcpt_id="r1"),
                                 rcpts) == "Korea Trip"
    assert core._effective_usage(_tx(2, "India Trip"), rcpts) == "India Trip"
    assert core._effective_usage(_tx(3), rcpts) == "Regular"


def test_trip_export_groups_by_tag_and_skips_regular(monkeypatch):
    _isolate(monkeypatch, [_tx(1, "Korea Trip"), _tx(2, "Korea Trip"),
                           _tx(3, "India Trip"), _tx(4, "Regular")])
    kind, data, mime, fn = core._handle_trip_export("u", {})
    assert kind == "file_inline" and mime == "application/json"
    payload = json.loads(data)
    assert set(payload["trips"]) == {"Korea Trip", "India Trip"}
    assert len(payload["trips"]["Korea Trip"]) == 2
    line = payload["trips"]["Korea Trip"][0]
    assert line["amount"] == 120.0 and line["gl"] == 53270377
    assert line["cost_center"] == core.FIXED["cost_center"]


def test_trip_export_404_when_nothing_tagged(monkeypatch):
    _isolate(monkeypatch, [_tx(1), _tx(2)])
    kind, _, code = core._handle_trip_export("u", {})
    assert kind == "html" and code == 404


def test_sap_xlsx_excludes_trip_rows(monkeypatch):
    _isolate(monkeypatch, [_tx(1, "Korea Trip"), _tx(2)])
    captured = {}

    def fake_build(entries, username=""):
        captured["entries"] = entries
        return b"xlsx", "f.xlsx"

    monkeypatch.setattr(core, "_build_xlsx_from_entries", fake_build)
    kind, *_ = core._handle_review_download("u", {})
    assert kind == "file_inline"
    assert [e["id"] for e in captured["entries"]] == ["t2"]


def test_sap_xlsx_404_when_only_trips_selected(monkeypatch):
    _isolate(monkeypatch, [_tx(1, "Korea Trip")])
    kind, page, code = core._handle_review_download("u", {})
    assert kind == "html" and code == 404
    assert "trip" in page.lower()
