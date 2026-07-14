"""OCR date normalization: relative dates ("today") resolve to the upload date."""
import importlib

core = importlib.import_module("services._cardconv_core")

UP = "2026-07-14"


def _fields(date, upload=UP):
    return core._ocr_entry_fields({"date": date, "amount": 1.0}, upload_date=upload)


def test_iso_date_passes_through():
    assert _fields("2026-07-01")["ocr_date"] == "2026-07-01"


def test_today_token_uses_upload_date():
    for v in ("today", "TODAY", "Today's date", "오늘"):
        assert _fields(v)["ocr_date"] == UP


def test_today_without_upload_date_is_none():
    assert _fields("today", upload=None)["ocr_date"] is None


def test_placeholder_and_junk_are_none():
    assert _fields("YYYY-MM-DD")["ocr_date"] is None
    assert _fields("no date visible")["ocr_date"] is None
    assert _fields(None)["ocr_date"] is None
