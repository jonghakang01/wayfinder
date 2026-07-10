"""Transaction pool: cross-upload dedup, ingest, migration, complete workflow."""
import importlib
import json
from collections import Counter

core = importlib.import_module("services._cardconv_core")

CSV_HEADER = "Date,Amount,Account Number,Merchant Name,Merchant Doing Business As,Card Member Name\n"
MEMBER = "KANG JONGHA"


def _row(date="07/01/2026", amount="45.50", acct="XXXX-1005", merchant="COFFEE"):
    return {"Date": date, "Amount": amount, "Account Number": acct,
            "Merchant Name": merchant, "Card Member Name": MEMBER}


def _csv(*rows):
    return (CSV_HEADER + "".join(
        f'{r["Date"]},{r["Amount"]},{r["Account Number"]},{r["Merchant Name"]},,{MEMBER}\n'
        for r in rows)).encode()


def _isolate(tmp_path, monkeypatch, uploads=None, review=None, receipts=None):
    """Point every storage accessor the pool touches at tmp_path."""
    monkeypatch.setattr(core, "_tx_pool_file", lambda u: tmp_path / f"pool_{u}.json")
    monkeypatch.setattr(core, "_uploads_dir", lambda u: tmp_path)
    monkeypatch.setattr(core, "_load_uploads", lambda u: uploads or [])
    monkeypatch.setattr(core, "_load_review", lambda u: review or {})
    monkeypatch.setattr(core, "_load_receipts", lambda u: receipts if receipts is not None else [])
    monkeypatch.setattr(core, "_save_receipts", lambda u, r: None)
    monkeypatch.setattr(core, "_get_card_member_names", lambda u: [MEMBER])
    monkeypatch.setattr(core, "_load_kw", lambda: {})
    monkeypatch.setattr(core, "_ensure_dirs", lambda: None)


def test_tx_key_normalizes_amount_and_case():
    a = core._tx_key(_row(amount="45.5", merchant="starbucks"))
    b = core._tx_key(_row(amount="45.50", merchant="STARBUCKS"))
    assert a == b


def test_dedup_rows_multiset_semantics():
    prior = Counter({core._tx_key(_row()): 2})
    kept, skipped = core._dedup_rows([_row(), _row(), _row()], prior)
    assert skipped == 2 and len(kept) == 1


def test_ingest_dedups_across_uploads(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    s1 = core._ingest_csv("u", _csv(_row(), _row(date="07/02/2026", amount="12.00", merchant="TAXI")), "a.csv")
    assert (s1["added"], s1["dup_skipped"]) == (2, 0)
    # Overlapping upload: repeats both + 1 new
    s2 = core._ingest_csv("u", _csv(_row(), _row(date="07/02/2026", amount="12.00", merchant="TAXI"),
                                    _row(date="07/03/2026", amount="99.99", merchant="HOTEL")), "b.csv")
    assert (s2["added"], s2["dup_skipped"]) == (1, 2)
    pool = core._load_tx_pool("u")
    assert len(pool["entries"]) == 3
    assert all(e["status"] == "open" for e in pool["entries"])
    assert pool["last_ingest"]["dup_skipped"] == 2


def test_migration_keeps_everything_open(tmp_path, monkeypatch):
    # Completion is an explicit user action — migration must not assume old
    # uploads are settled. Duplicates across uploads still ingest once.
    (tmp_path / "csv_old.csv").write_bytes(_csv(_row(date="05/01/2026", merchant="OLD")))
    (tmp_path / "csv_new.csv").write_bytes(
        _csv(_row(date="05/01/2026", merchant="OLD"),          # duplicate of old upload
             _row(date="06/01/2026", merchant="NEWSHOP")))
    uploads = [  # newest first, matching _load_uploads order
        {"id": "new", "stored_name": "csv_new.csv", "filename": "new.csv"},
        {"id": "old", "stored_name": "csv_old.csv", "filename": "old.csv"},
    ]
    legacy_review = {"rows": [{
        "date": "2026-06-01", "amount": 45.50, "merchant": "NEWSHOP",
        "matched": True, "receipt": {"id": "r1"}, "loss_reason": "",
    }]}
    _isolate(tmp_path, monkeypatch, uploads=uploads, review=legacy_review)

    pool = core._load_tx_pool("u")
    assert len(pool["entries"]) == 2  # duplicate row ingested once
    by_merchant = {e["merchant"]: e for e in pool["entries"]}
    assert by_merchant["OLD"]["status"] == "open"
    assert by_merchant["NEWSHOP"]["status"] == "open"
    # Open batch inherits match info from the legacy review snapshot
    assert by_merchant["NEWSHOP"]["matched"] is True
    assert by_merchant["NEWSHOP"]["receipt"] == {"id": "r1"}


def test_complete_and_undo(tmp_path, monkeypatch):
    _isolate(tmp_path, monkeypatch)
    core._ingest_csv("u", _csv(_row(), _row(date="07/02/2026", merchant="TAXI")), "a.csv")
    pool = core._load_tx_pool("u")
    ids = [e["id"] for e in pool["entries"]]

    kind, resp = core._handle_review_complete("u", {"ids": ids})
    assert resp["touched"] == 2
    pool = core._load_tx_pool("u")
    assert all(e["status"] == "completed" and e["completed_at"] for e in pool["entries"])

    kind, resp = core._handle_review_complete("u", {"ids": [ids[0]], "undo": True})
    pool = core._load_tx_pool("u")
    statuses = {e["id"]: e["status"] for e in pool["entries"]}
    assert statuses[ids[0]] == "open" and statuses[ids[1]] == "completed"


def test_reupload_of_completed_txs_stays_deduped(tmp_path, monkeypatch):
    # Completed transactions must not resurrect when the same CSV comes again.
    _isolate(tmp_path, monkeypatch)
    core._ingest_csv("u", _csv(_row()), "a.csv")
    pool = core._load_tx_pool("u")
    core._handle_review_complete("u", {"ids": [pool["entries"][0]["id"]]})
    s = core._ingest_csv("u", _csv(_row()), "a-again.csv")
    assert (s["added"], s["dup_skipped"]) == (0, 1)
    assert len(core._load_tx_pool("u")["entries"]) == 1
