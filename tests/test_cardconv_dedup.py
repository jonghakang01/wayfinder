"""Cross-upload duplicate filtering for Convert CSVs (overlapping periods)."""
import importlib
from collections import Counter

core = importlib.import_module("services._cardconv_core")

CSV_HEADER = "Date,Amount,Account Number,Merchant Name,Card Member Name\n"


def _row(date="07/01/2026", amount="45.50", acct="XXXX-1005", merchant="COFFEE"):
    return {"Date": date, "Amount": amount, "Account Number": acct,
            "Merchant Name": merchant, "Card Member Name": "KANG JONGHA"}


def test_tx_key_normalizes_amount_and_case():
    a = core._tx_key(_row(amount="45.5", merchant="starbucks"))
    b = core._tx_key(_row(amount="45.50", merchant="STARBUCKS"))
    assert a == b


def test_tx_key_distinguishes_fields():
    base = core._tx_key(_row())
    assert core._tx_key(_row(date="07/02/2026")) != base
    assert core._tx_key(_row(amount="45.51")) != base
    assert core._tx_key(_row(acct="XXXX-2001")) != base
    assert core._tx_key(_row(merchant="TEA")) != base


def test_dedup_rows_multiset_semantics():
    # 2 prior occurrences absorb only 2 of 3 identical new rows.
    prior = Counter({core._tx_key(_row()): 2})
    kept, skipped = core._dedup_rows([_row(), _row(), _row()], prior)
    assert skipped == 2
    assert len(kept) == 1


def test_dedup_rows_empty_prior_is_noop():
    rows = [_row(), _row(date="07/02/2026")]
    kept, skipped = core._dedup_rows(rows, Counter())
    assert kept == rows and skipped == 0


def test_prior_tx_counter_reads_history_and_excludes(tmp_path, monkeypatch):
    csv_text = CSV_HEADER + (
        "07/01/2026,45.50,XXXX-1005,COFFEE,KANG JONGHA\n"
        "07/01/2026,45.50,XXXX-1005,COFFEE,KANG JONGHA\n")
    (tmp_path / "csv_a.csv").write_text(csv_text)
    monkeypatch.setattr(core, "_uploads_dir", lambda u: tmp_path)
    monkeypatch.setattr(core, "_load_uploads",
                        lambda u: [{"id": "a", "stored_name": "csv_a.csv"},
                                   {"id": "gone", "stored_name": "missing.csv"}])
    counts = core._prior_tx_counter("u")
    assert counts[core._tx_key(_row())] == 2
    # Excluding the upload (re-run case) empties the counter.
    assert core._prior_tx_counter("u", exclude_id="a") == Counter()
