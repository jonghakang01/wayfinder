"""Duplicate compare (강프로 2026-07-28, docs/specs/2026-07-28-duplicate-compare.md).

A scan flagged as already-in-the-Ledger used to offer nothing but a confirm()
string. The compare endpoint hands back both sides — the queued scan and every
ledger receipt it collides with, each with the AMEX line it is mapped to — so
the verdict is the user's and not the bucket key's.
"""
import importlib

core = importlib.import_module("services._cardconv_core")


def _staged(eid, amount=45.61, merchant="SF Giants", date="2026-05-10", **kw):
    e = {"id": eid, "file_id": "f_" + eid, "filename": eid + ".jpg",
         "ocr_status": "done", "ocr_date": date, "ocr_merchant": merchant,
         "ocr_amount": amount, "ocr_printed_amount": amount,
         "ocr_handwritten_amount": None, "ocr_time": None, "dup_exempt": False}
    e.update(kw)
    return e


def _ledger(eid, amount=45.61, merchant="SF Giants", date="2026-05-10", **kw):
    e = _staged(eid, amount, merchant, date)
    e.update({"match_status": "matched", "matched": True, "completed": False,
              "matched_transaction": {"date": date, "amount": amount,
                                      "vendor": "SAN FRANCISCO GIANTS"}})
    e.update(kw)
    return e


def _isolate(monkeypatch, staged, ledger):
    st = {"staging": {"entries": staged}, "ledger": {"entries": ledger}}
    monkeypatch.setattr(core, "_load_ocr_staging", lambda u: st["staging"])
    monkeypatch.setattr(core, "_save_ocr_staging", lambda u, d: st.update(staging=d))
    monkeypatch.setattr(core, "_load_ledger", lambda u: st["ledger"])
    monkeypatch.setattr(core, "_load_receipts", lambda u: st["ledger"]["entries"])
    return st


def test_ledger_collision_records_every_match(monkeypatch):
    _isolate(monkeypatch, [_staged("s1")], [_ledger("L1"), _ledger("L2")])
    out = core._flag_staged_dups("u", [_staged("s1")])
    assert out[0]["dup_hint"] == "ledger"
    assert sorted(out[0]["dup_match_ids"]) == ["L1", "L2"]


def test_clean_scan_has_no_matches(monkeypatch):
    _isolate(monkeypatch, [], [_ledger("L1", amount=10.0)])
    out = core._flag_staged_dups("u", [_staged("s1", amount=99.0)])
    assert out[0]["dup_hint"] is None
    assert out[0]["dup_match_ids"] == []


def test_exempt_scan_stops_being_flagged(monkeypatch):
    """Once called a separate purchase, it isn't asked about again."""
    _isolate(monkeypatch, [], [_ledger("L1")])
    out = core._flag_staged_dups("u", [_staged("s1", dup_exempt=True)])
    assert out[0]["dup_hint"] is None
    assert out[0]["dup_match_ids"] == []


def test_compare_returns_both_sides_with_the_mapping(monkeypatch):
    _isolate(monkeypatch, [_staged("s1", ocr_handwritten_amount=99.99)],
             [_ledger("L1"), _ledger("L2", match_status="pending_match",
                                     matched=False, matched_transaction=None)])
    kind, resp, *_ = core._handle_dup_compare("u", {"id": "s1"})
    assert resp["ok"]
    assert resp["staged"]["handwritten"] == 99.99
    assert resp["staged"]["image"].endswith("/f_s1")
    assert len(resp["candidates"]) == 2
    first = resp["candidates"][0]
    assert first["status"] == "MATCHED"
    assert first["matched_transaction"]["vendor"] == "SAN FRANCISCO GIANTS"
    # An unmatched candidate is still shown — with nothing where the line goes.
    assert resp["candidates"][1]["status"] == "PENDING MATCH"
    assert resp["candidates"][1]["matched_transaction"] is None


def test_compare_rejects_an_unknown_id(monkeypatch):
    _isolate(monkeypatch, [_staged("s1")], [_ledger("L1")])
    kind, resp, status = core._handle_dup_compare("u", {"id": "nope"})
    assert status == 404


def test_compare_needs_an_id(monkeypatch):
    _isolate(monkeypatch, [], [])
    kind, resp, status = core._handle_dup_compare("u", {})
    assert status == 400


def test_keep_both_sticks(monkeypatch):
    st = _isolate(monkeypatch, [_staged("s1")], [_ledger("L1")])
    kind, resp, *_ = core._handle_dup_exempt("u", {"id": ["s1"]})
    assert resp["ok"]
    assert st["staging"]["entries"][0]["dup_exempt"] is True


def test_a_ledger_row_without_an_id_still_raises_the_flag(monkeypatch):
    """The warning must not go quiet just because a legacy row predates ids —
    only the compare list depends on having one."""
    _isolate(monkeypatch, [], [{"ocr_amount": 45.61, "ocr_merchant": "SF Giants",
                                "ocr_date": "2026-05-10", "completed": False}])
    out = core._flag_staged_dups("u", [_staged("s1")])
    assert out[0]["dup_hint"] == "ledger"
    assert out[0]["dup_match_ids"] == []


def test_keeping_both_survives_into_the_ledger():
    """'Separate purchases' is a verdict, not a one-render dismissal: the flag
    rides along on confirm and keeps the receipt out of Ledger dup groups."""
    kept = _ledger("L1", dup_exempt=True)
    entries = [kept, _ledger("L2")]
    core._mark_duplicates(entries)
    assert kept["dup"] is False and kept["dup_group_id"] is None
