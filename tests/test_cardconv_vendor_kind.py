"""Domestic/Overseas (SAP vendor kind) is decided by the receipt currency, on
every export path, not by which trip a row was tagged with.

Before 2026-08-05 the bulk xlsx hardcoded "D" for every line while the trip
robot defaulted every line to "O" — the same charge left through two doors
with opposite answers. The rule now lives in one place: USD is Domestic,
anything else is Overseas, and a row with no receipt currency (over half of
open rows) falls to Domestic where the user can correct it by hand.
"""
import importlib
import json

core = importlib.import_module("services._cardconv_core")


def _tx(i, usage="Regular", rcpt_id=None, **kw):
    e = {"id": f"t{i}", "status": "open", "date": "2026-07-10",
         "merchant": "HOTEL SEOUL", "amount": 120.0, "usage": usage,
         "gl": 53270377, "ser": "306", "purpose": "Hotel stay",
         "matched": bool(rcpt_id), "cash": False}
    if rcpt_id:
        e["receipt"] = {"id": rcpt_id}
    e.update(kw)
    return e


def _rcpt(rid, currency=None):
    return {"id": rid, "ocr_currency": currency, "usage": "Regular"}


# ── the rule ────────────────────────────────────────────────────────────────

def test_usd_is_domestic_everything_else_overseas():
    assert core._vendor_kind({}, _rcpt("r", "USD")) == "D"
    assert core._vendor_kind({}, _rcpt("r", "KRW")) == "O"
    assert core._vendor_kind({}, _rcpt("r", "INR")) == "O"
    assert core._vendor_kind({}, _rcpt("r", "EUR")) == "O"


def test_missing_currency_falls_to_domestic():
    """The common case: an AMEX line with no receipt, or OCR found no currency."""
    assert core._vendor_kind({}, None) == "D"
    assert core._vendor_kind({}, _rcpt("r", None)) == "D"
    assert core._vendor_kind({}, _rcpt("r", "")) == "D"


def test_currency_is_read_case_insensitively():
    assert core._vendor_kind({}, _rcpt("r", "krw")) == "O"
    assert core._vendor_kind({}, _rcpt("r", " usd ")) == "D"


def test_hand_set_value_beats_the_currency():
    """The correction path for rows whose currency is missing or wrong."""
    assert core._vendor_kind({"vendor_kind": "O"}, _rcpt("r", "USD")) == "O"
    assert core._vendor_kind({"vendor_kind": "D"}, _rcpt("r", "KRW")) == "D"


def test_junk_override_is_ignored_not_trusted():
    assert core._vendor_kind({"vendor_kind": "X"}, _rcpt("r", "KRW")) == "O"
    assert core._vendor_kind({"vendor_kind": None}, _rcpt("r", "KRW")) == "O"


def test_ledger_rows_carry_the_currency_themselves():
    """Ledger entries ARE receipts — the Ledger xlsx asks them directly."""
    assert core._vendor_kind({"ocr_currency": "KRW"}, None) == "O"


# ── the trip JSON export ────────────────────────────────────────────────────

def _isolate(monkeypatch, pool_entries, receipts=None):
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: {"entries": pool_entries})
    monkeypatch.setattr(core, "_load_receipts", lambda u: receipts or [])
    monkeypatch.setattr(core, "_export_tag", lambda u: "tester")


def test_trip_export_carries_kind_per_line(monkeypatch):
    """One trip, mixed currencies — the lines must not share a single answer."""
    receipts = [_rcpt("r1", "KRW"), _rcpt("r2", "USD"), _rcpt("r3", "HKD")]
    for r in receipts:
        r["usage"] = "Korea Trip"
    _isolate(monkeypatch,
             [_tx(1, "Korea Trip", rcpt_id="r1"),
              _tx(2, "Korea Trip", rcpt_id="r2"),
              _tx(3, "Korea Trip", rcpt_id="r3"),
              _tx(4, "Korea Trip")],           # no receipt at all
             receipts)
    _, data, _, _ = core._handle_trip_export("u", {})
    lines = json.loads(data)["trips"]["Korea Trip"]
    assert [ln["vendor_kind"] for ln in lines] == ["O", "D", "O", "D"]
    assert [ln["receipt_currency"] for ln in lines] == ["KRW", "USD", "HKD", ""]


def test_trip_export_amount_stays_labelled_usd(monkeypatch):
    """The amount is the settled USD figure even for a ₩ receipt, so the
    currency field must keep saying USD — the receipt's own currency rides
    alongside instead of overwriting it."""
    rc = _rcpt("r1", "KRW")
    rc["usage"] = "Korea Trip"
    _isolate(monkeypatch, [_tx(1, "Korea Trip", rcpt_id="r1")], [rc])
    _, data, _, _ = core._handle_trip_export("u", {})
    line = json.loads(data)["trips"]["Korea Trip"][0]
    assert line["currency"] == "USD"
    assert line["amount"] == 120.0
    assert line["receipt_currency"] == "KRW"


# ── the hand correction ─────────────────────────────────────────────────────

def _capture_pool(monkeypatch, entries, receipts=None):
    pool = {"entries": entries}
    ledger = {"entries": receipts or []}
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: pool)
    monkeypatch.setattr(core, "_save_tx_pool", lambda u, p: None)
    monkeypatch.setattr(core, "_load_ledger", lambda u: ledger)
    monkeypatch.setattr(core, "_save_ledger", lambda u, l: None)
    monkeypatch.setattr(core, "_load_receipts", lambda u: ledger["entries"])
    return pool, ledger


def test_setting_a_kind_pins_the_row(monkeypatch):
    pool, _ = _capture_pool(monkeypatch, [_tx(1)])
    out = core._handle_review_vendor_kind("u", {"id": "t1", "kind": "O"})
    assert out[0] == "json" and out[1]["ok"] and out[1]["kind"] == "O"
    assert pool["entries"][0]["vendor_kind"] == "O"


def test_auto_drops_the_override_so_a_later_receipt_still_counts(monkeypatch):
    """Storing only the override is the point: once the receipt arrives with
    its currency, an untouched row follows it."""
    pool, _ = _capture_pool(monkeypatch, [_tx(1, vendor_kind="O")])
    out = core._handle_review_vendor_kind("u", {"id": "t1", "kind": "auto"})
    assert out[1]["ok"] and out[1]["auto"] is True
    assert "vendor_kind" not in pool["entries"][0]
    assert out[1]["kind"] == "D"          # no receipt → Domestic again


def test_matched_row_mirrors_onto_the_ledger_receipt(monkeypatch):
    """The Ledger has its own xlsx export; it must not disagree with Review."""
    pool, ledger = _capture_pool(monkeypatch, [_tx(1, rcpt_id="r1")],
                                 [_rcpt("r1", "USD")])
    core._handle_review_vendor_kind("u", {"id": "t1", "kind": "O"})
    assert ledger["entries"][0]["vendor_kind"] == "O"
    core._handle_review_vendor_kind("u", {"id": "t1", "kind": "auto"})
    assert "vendor_kind" not in ledger["entries"][0]


def test_bad_input_is_refused(monkeypatch):
    _capture_pool(monkeypatch, [_tx(1)])
    assert core._handle_review_vendor_kind("u", {"kind": "D"})[2] == 400
    assert core._handle_review_vendor_kind("u", {"id": "t1", "kind": "Z"})[2] == 400
    assert core._handle_review_vendor_kind("u", {"id": "nope", "kind": "D"})[2] == 404


# ── the robot's writeback ───────────────────────────────────────────────────

def _robot_file(tmp_path, monkeypatch, payload):
    f = tmp_path / "robot.json"
    f.write_text(json.dumps(payload))
    monkeypatch.setattr(core, "ROBOT_RESULT_FILE", f)
    return f


def test_robot_result_moves_saved_rows_to_in_progress(tmp_path, monkeypatch):
    """A saved SAP submission that leaves the row open gets exported again —
    that is how the same charge reaches SAP twice (2026-08-04)."""
    entries = [_tx(1), _tx(2), _tx(3)]
    saved = {}
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: {"entries": entries})
    monkeypatch.setattr(core, "_save_tx_pool", lambda u, p: saved.update(p))
    monkeypatch.setattr(core, "_apply_receipt_completion", lambda *a, **k: None)
    f = _robot_file(tmp_path, monkeypatch,
                    {"user": "u", "trip": "NY Trip", "saved": ["t1", "t3"], "total": 3})
    note = core._adopt_robot_result("u")
    assert "2 row(s)" in note and "NY Trip" in note
    by_id = {e["id"]: e["status"] for e in saved["entries"]}
    assert by_id == {"t1": "in_progress", "t2": "open", "t3": "in_progress"}
    assert not f.exists()          # consumed, so a reload cannot re-apply it


def test_robot_result_leaves_another_user_alone(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: {"entries": [_tx(1)]})
    monkeypatch.setattr(core, "_pkey", lambda u: u)
    f = _robot_file(tmp_path, monkeypatch, {"user": "someone-else", "saved": ["t1"]})
    assert core._adopt_robot_result("u") == ""
    assert f.exists()              # still there for the account it belongs to


def test_robot_result_is_scoped_to_the_card_profile(tmp_path, monkeypatch):
    """Every card profile shares the login while the rows live in per-profile
    files. Matching on the login alone adopted a run under the wrong profile,
    found no ids, deleted the file and lost the writeback for good."""
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: {"entries": [_tx(1)]})
    monkeypatch.setattr(core, "_pkey", lambda u: "u@ceo_card")
    f = _robot_file(tmp_path, monkeypatch,
                    {"user": "u", "pkey": "u", "saved": ["t1"]})   # default profile's run
    assert core._adopt_robot_result("u") == ""
    assert f.exists()              # kept for the default profile to adopt
    assert _tx(1)["status"] == "open"


def test_result_without_pkey_still_works_for_the_default_profile(tmp_path, monkeypatch):
    """Files written before the key existed must not be stranded."""
    entries = [_tx(1)]
    saved = {}
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: {"entries": entries})
    monkeypatch.setattr(core, "_save_tx_pool", lambda u, p: saved.update(p))
    monkeypatch.setattr(core, "_apply_receipt_completion", lambda *a, **k: None)
    monkeypatch.setattr(core, "_pkey", lambda u: u)        # default profile
    _robot_file(tmp_path, monkeypatch, {"user": "u", "saved": ["t1"]})
    assert "1 row(s)" in core._adopt_robot_result("u")
    assert saved["entries"][0]["status"] == "in_progress"


def test_unrecognised_ids_keep_the_file_instead_of_eating_it(tmp_path, monkeypatch):
    """Recognising none of the ids means this is not the pool the run was
    about — deleting it here is exactly how a writeback vanishes."""
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: {"entries": [_tx(9)]})
    monkeypatch.setattr(core, "_pkey", lambda u: u)
    f = _robot_file(tmp_path, monkeypatch, {"user": "u", "saved": ["t1", "t2"]})
    assert core._adopt_robot_result("u") == ""
    assert f.exists()


def test_trip_export_carries_the_profile_key(monkeypatch):
    rc = _rcpt("r1", "USD")
    rc["usage"] = "NY Trip"
    _isolate(monkeypatch, [_tx(1, "NY Trip", rcpt_id="r1")], [rc])
    monkeypatch.setattr(core, "_pkey", lambda u: "u@ceo_card")
    _, data, _, _ = core._handle_trip_export("u", {})
    assert json.loads(data)["pkey"] == "u@ceo_card"


def test_robot_result_does_not_reopen_finished_rows(tmp_path, monkeypatch):
    done = _tx(1, status="completed")
    monkeypatch.setattr(core, "_load_tx_pool", lambda u: {"entries": [done]})
    _robot_file(tmp_path, monkeypatch, {"user": "u", "saved": ["t1"]})
    assert core._adopt_robot_result("u") == ""
    assert done["status"] == "completed"


def test_missing_or_broken_result_file_is_silent(tmp_path, monkeypatch):
    monkeypatch.setattr(core, "ROBOT_RESULT_FILE", tmp_path / "absent.json")
    assert core._adopt_robot_result("u") == ""
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    monkeypatch.setattr(core, "ROBOT_RESULT_FILE", bad)
    assert core._adopt_robot_result("u") == ""
