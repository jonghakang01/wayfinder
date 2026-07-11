"""Handwritten 'w/ NAME' companion note — extraction, match snapshot, purpose."""
from services._cardconv_core import (
    _coerce_companions,
    _normalize_ocr,
    _apply_receipt_match,
)


def test_coerce_strips_w_prefix():
    assert _coerce_companions("w/sds") == "sds"
    assert _coerce_companions("w/ John, Amy") == "John, Amy"
    assert _coerce_companions("with Kim") == "Kim"
    assert _coerce_companions("  sds  ") == "sds"


def test_coerce_rejects_empty_and_nonstring():
    assert _coerce_companions(None) is None
    assert _coerce_companions("") is None
    assert _coerce_companions("w/ ") is None
    assert _coerce_companions(123) is None


def test_coerce_caps_length():
    assert len(_coerce_companions("x" * 200)) == 60


def test_normalize_ocr_carries_companions():
    r = _normalize_ocr({"printed_amount": 10.0, "companions": "w/sds"})
    assert r["companions"] == "sds"


def test_normalize_ocr_companions_fallback_from_handwriting():
    r = _normalize_ocr({"printed_amount": 10.0, "companions": None,
                        "handwriting_notes": "33.10  w/sds"})
    assert r["companions"] == "sds"
    r2 = _normalize_ocr({"printed_amount": 10.0,
                         "handwriting_notes": "with John, Amy"})
    assert r2["companions"] == "John, Amy"
    r3 = _normalize_ocr({"printed_amount": 10.0, "handwriting_notes": "45.00"})
    assert r3["companions"] is None


def test_match_snapshot_includes_companions():
    receipt = {"id": "rcpt_1", "file_id": "f1", "ocr_companions": "sds",
               "ocr_amount": 10.0, "ocr_date": "2026-07-01"}
    entry = {"date": "2026-07-01", "amount": 10.0, "merchant": "CAFE"}
    _apply_receipt_match(entry, receipt, [receipt])
    assert entry["receipt"]["companions"] == "sds"
