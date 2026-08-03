"""Duplicate detection compares printed transaction times exactly, to the
second (강프로 2026-08-03). Two same-amount purchases at one merchant print
different timestamps; two copies of one receipt print the same one — the old
±5-minute tolerance grouped the former as duplicates.
"""
import importlib

core = importlib.import_module("services._cardconv_core")


def _entry(i, time=None, amount=12.5, merchant="CAFE", date="2026-08-01"):
    return {"id": f"r{i}", "ocr_amount": amount, "ocr_merchant": merchant,
            "ocr_date": date, "ocr_time": time, "dup_exempt": False,
            "match_status": "unmatched"}


def test_times_close_exact_semantics():
    f = core._times_close
    assert f(None, "13:45")            # unknown side stays compatible
    assert f("13:45", "13:45")
    assert not f("13:45", "13:47")     # 2 minutes apart = separate purchases
    assert f("13:45:22", "13:45:22")
    assert not f("13:45:22", "13:45:31")   # same minute, different seconds
    assert f("13:45", "13:45:22")      # one side lacks seconds -> minute precision


def test_coerce_time_keeps_seconds():
    f = core._coerce_time
    assert f("13:45:22") == "13:45:22"
    assert f("1:45:22 PM") == "13:45:22"
    assert f("13:45") == "13:45"
    assert f("garbage") is None


def test_seconds_split_a_duplicate_group():
    a, b = _entry(1, "18:02:11"), _entry(2, "18:02:45")
    core._mark_duplicates([a, b])
    assert not a["dup"] and not b["dup"]


def test_identical_timestamps_still_group():
    a, b = _entry(1, "18:02:11"), _entry(2, "18:02:11")
    core._mark_duplicates([a, b])
    assert a["dup"] and b["dup"]
    assert a["dup_group_id"] == b["dup_group_id"]


def test_missing_time_still_groups_with_dated_twin():
    a, b = _entry(1, "18:02:11"), _entry(2, None)
    core._mark_duplicates([a, b])
    assert a["dup"] and b["dup"]
