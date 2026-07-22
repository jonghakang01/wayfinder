"""OCR staging: per-entry discard + duplicate hints (2026-07-22).

A staged receipt can be rejected before it reaches the Ledger; its Drive file
is trashed only when no other staged or ledger entry still references it.
Staged entries matching an active ledger receipt (amount+merchant, compatible
date/time) or an earlier queue entry are flagged so the UI unchecks them.
"""
import importlib

core = importlib.import_module("services._cardconv_core")


def _isolate(monkeypatch, staged, ledger_entries):
    state = {"staging": {"entries": staged}, "ledger": {"entries": ledger_entries}}
    monkeypatch.setattr(core, "_load_ocr_staging", lambda u: state["staging"])
    monkeypatch.setattr(core, "_save_ocr_staging",
                        lambda u, d: state.update(staging=d))
    monkeypatch.setattr(core, "_load_ledger", lambda u: state["ledger"])
    monkeypatch.setattr(core, "_get_drive_service", lambda u: None)
    return state


def _staged(eid, fid="f1", amount=10.0, merchant="STARBUCKS", date="2026-07-01"):
    return {"id": eid, "file_id": fid, "ocr_amount": amount,
            "ocr_merchant": merchant, "ocr_date": date, "ocr_status": "done"}


def test_discard_entry_removes_only_target(monkeypatch):
    st = _isolate(monkeypatch, [_staged("e1"), _staged("e2", fid="f2")], [])
    kind, resp, *_ = core._handle_ocr_staging_discard_entry("u", {"id": "e1"})
    assert kind == "json" and resp["ok"]
    assert [e["id"] for e in st["staging"]["entries"]] == ["e2"]
    assert resp["remaining"] == 1


def test_discard_entry_unknown_id_404(monkeypatch):
    _isolate(monkeypatch, [_staged("e1")], [])
    kind, resp, code = core._handle_ocr_staging_discard_entry("u", {"id": "nope"})
    assert code == 404


def test_dup_hint_against_ledger(monkeypatch):
    _isolate(monkeypatch, [], [])
    monkeypatch.setattr(core, "_load_ledger", lambda u: {"entries": [
        {"ocr_amount": 25.5, "ocr_merchant": "Blue Bottle", "ocr_date": "2026-07-01",
         "completed": False},
        {"ocr_amount": 99.0, "ocr_merchant": "Done Store", "ocr_date": "2026-07-01",
         "completed": True},
    ]})
    entries = [
        _staged("a", amount=25.5, merchant="BLUE BOTTLE", date="2026-07-01"),
        _staged("b", amount=99.0, merchant="Done Store", date="2026-07-01"),
        _staged("c", amount=7.0, merchant="Fresh Place", date="2026-07-02"),
    ]
    core._flag_staged_dups("u", entries)
    assert entries[0]["dup_hint"] == "ledger"      # case-insensitive merchant match
    assert entries[1]["dup_hint"] is None          # completed ledger rows don't count
    assert entries[2]["dup_hint"] is None


def test_dup_hint_within_batch_and_missing_date(monkeypatch):
    _isolate(monkeypatch, [], [])
    entries = [
        _staged("a", amount=12.0, merchant="Cafe X", date="2026-07-01"),
        _staged("b", amount=12.0, merchant="Cafe X", date=None),   # dateless twin
        _staged("c", amount=12.0, merchant="Cafe Y", date="2026-07-01"),
    ]
    core._flag_staged_dups("u", entries)
    assert entries[0]["dup_hint"] is None
    assert entries[1]["dup_hint"] == "staged"
    assert entries[2]["dup_hint"] is None


def test_discard_tombstones_fid_so_sync_skips_it(monkeypatch):
    st = _isolate(monkeypatch, [_staged("e1", fid="fX")], [])
    st["discarded"] = {}
    monkeypatch.setattr(core, "_load_discarded_fids", lambda u: dict(st["discarded"]))
    monkeypatch.setattr(core, "_mark_discarded_fid",
                        lambda u, f, name=None: st["discarded"].__setitem__(f, "t"))
    core._handle_ocr_staging_discard_entry("u", {"id": "e1"})
    assert "fX" in st["discarded"]

    # sync must not re-stage the tombstoned file even though Drive still has it
    class _Files:
        def list(self, **kw):
            class _R:
                def execute(self):
                    return {"files": [
                        {"id": "fX", "name": "a.jpg", "mimeType": "image/jpeg"},
                        {"id": "fY", "name": "b.jpg", "mimeType": "image/jpeg"},
                    ]}
            return _R()

    class _Svc:
        def files(self):
            return _Files()

    monkeypatch.setattr(core, "_get_drive_service", lambda u: _Svc())
    monkeypatch.setattr(core, "_get_receipts_folder_id", lambda s, u: "folder")
    monkeypatch.setattr(core, "_load_receipts", lambda u: [])
    new = core._list_new_drive_files("u")
    assert [f["id"] for f in new] == ["fY"]


def test_discard_keeps_file_referenced_by_ledger_untombstoned(monkeypatch):
    st = _isolate(monkeypatch, [_staged("e1", fid="fShared")],
                  [{"file_id": "fShared", "ocr_amount": 1.0, "multi_ocr": True}])
    st["discarded"] = {}
    monkeypatch.setattr(core, "_mark_discarded_fid",
                        lambda u, f, name=None: st["discarded"].__setitem__(f, "t"))
    core._handle_ocr_staging_discard_entry("u", {"id": "e1"})
    assert st["discarded"] == {}
