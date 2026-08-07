"""Ambiguous printed dates (강프로 2026-07-28).

A receipt that prints "24-02-26" gives three numbers and no convention, and the
old code dropped anything that wasn't already ISO. The agreed reading: the part
that could be a year is the year, the more recent one wins when two could be,
and of the remaining two anything past 12 is the day — otherwise US order.
"""
import importlib
from datetime import datetime

core = importlib.import_module("services._cardconv_core")

TODAY = datetime(2026, 7, 28)
TODAY_AUG = datetime(2026, 8, 7)


def r(s):
    return core._resolve_ambiguous_date(s, today=TODAY)


def test_two_year_candidates_take_the_recent_one():
    # 24 and 26 both read as years; 26 is the one you are living in.
    assert r("24-02-26") == "2026-02-24"
    assert r("26-02-24") == "2026-02-24"


def test_a_number_past_twelve_can_only_be_the_day():
    assert r("02-26-24") == "2026-02-24"   # year 26, then 24 must be the day
    assert r("25-31-12") == "2025-12-31"   # 31 is the day, 12 the month


def test_two_ambiguous_parts_read_month_first():
    # Both fit either slot — the statement is a US AMEX one.
    assert r("12-05-25") == "2025-12-05"
    assert r("25-05-12") == "2025-05-12"


def test_a_written_out_year_outranks_a_guess():
    assert r("2024-02-26") == "2024-02-26"
    assert r("02/26/2024") == "2024-02-26"


def test_separators_are_interchangeable():
    assert r("12/05/25") == "2025-12-05"
    assert r("12.05.25") == "2025-12-05"


def test_silence_beats_a_bad_guess():
    assert r("24-25-26") is None      # two day-sized numbers, no reading works
    assert r("02-30-25") is None      # February has no 30th
    assert r("hello") is None
    assert r(None) is None
    assert r("05-06") is None         # not three parts


def test_a_date_with_no_plausible_year_is_left_alone():
    """Better the CSV backfill supplies it than we invent a year."""
    assert r("05-06-07") is None      # 2007 is a decade out of range


def test_ocr_fields_now_keep_an_ambiguous_date(monkeypatch):
    """It used to be thrown away for not being ISO."""
    monkeypatch.setattr(core, "_fx_usd_estimate", lambda *a, **k: (None, None))
    out = core._ocr_entry_fields({"date": "2026-02-24", "amount": 10.0})
    assert out["ocr_date"] == "2026-02-24"


def test_relative_dates_still_use_the_upload_date(monkeypatch):
    monkeypatch.setattr(core, "_fx_usd_estimate", lambda *a, **k: (None, None))
    out = core._ocr_entry_fields({"date": "today", "amount": 10.0},
                                 upload_date="2026-07-28")
    assert out["ocr_date"] == "2026-07-28"


# ── the order is decided by evidence, not assumed US (강프로 2026-08-07) ──────
# An Argentine receipt printed "06/08" kept reading as June 8th when it was
# August 6th. The currency names the country, the country names the convention,
# and the upload day anchors the tie when the currency is unknown.

def test_a_foreign_currency_receipt_reads_day_first():
    got = core._resolve_ambiguous_date("06/08/26", today=TODAY_AUG, currency="ARS")
    assert got == "2026-08-06"


def test_a_usd_receipt_still_reads_month_first():
    got = core._resolve_ambiguous_date("06/08/26", today=TODAY_AUG, currency="USD")
    assert got == "2026-06-08"


def test_unknown_currency_leans_on_the_upload_day():
    """Receipts are photographed within days of the purchase, not months."""
    got = core._resolve_ambiguous_date("06/08/26", today=TODAY_AUG,
                                       ref_date="2026-08-07")
    assert got == "2026-08-06"


def test_no_currency_and_no_anchor_keeps_the_old_us_reading():
    assert core._resolve_ambiguous_date("12-05-25", today=TODAY) == "2025-12-05"


def test_a_reading_in_the_future_loses_to_one_in_the_past():
    """A receipt is for a purchase that already happened."""
    # 09/10 on Sep 12: month-first Sep 10 (past) vs day-first Oct 9 (future).
    got = core._resolve_ambiguous_date("09/10/26", today=datetime(2026, 9, 12),
                                       currency="ARS")
    assert got == "2026-09-10"     # the past one, even against the ARS day-first lean


def test_the_ocr_pipeline_hands_the_context_down(monkeypatch):
    monkeypatch.setattr(core, "_fx_usd_estimate", lambda *a, **k: (None, None))
    out = core._ocr_entry_fields({"date": "06/08/26", "amount": 10.0,
                                  "currency": "ARS"},
                                 upload_date="2026-08-07")
    assert out["ocr_date"] == "2026-08-06"
