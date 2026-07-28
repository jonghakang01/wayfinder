"""Card type is AMEX or Cash only (강프로 2026-07-28).

Visa was dropped from the picker: anything not on the corporate AMEX card is
reimbursed as cash regardless of which card paid it. Legacy 'visa' rows fold
into 'other' on load, and stale pages that still POST 'visa' land on Cash too.
"""
import importlib

core = importlib.import_module("services._cardconv_core")
from tests.test_cardconv_cash_rule import _isolate, _receipt  # noqa: E402


def test_legacy_visa_folds_into_cash_on_load():
    e = core._migrate_entry({"id": "r1", "card_brand": "visa"})
    assert e["card_brand"] == "other"


def test_amex_survives_migration():
    e = core._migrate_entry({"id": "r1", "card_brand": "amex"})
    assert e["card_brand"] == "amex"


def test_unset_brand_stays_unset_on_load():
    e = core._migrate_entry({"id": "r1"})
    assert e["card_brand"] is None


def test_valid_brand_accepts_only_amex_and_cash():
    assert core._valid_brand("amex") == "amex"
    assert core._valid_brand("other") == "other"
    assert core._valid_brand("visa") == "other"   # stale page / bookmark
    assert core._valid_brand("none") is None
    assert core._valid_brand("") is None
    assert core._valid_brand("mastercard") is None


def test_ocr_brand_coercion_has_no_visa():
    assert core._coerce_card_brand("VISA") == "other"
    assert core._coerce_card_brand("Mastercard") == "other"
    assert core._coerce_card_brand("American Express") == "amex"
    assert core._coerce_card_brand("unknown") is None


def test_ledger_edit_to_visa_lands_on_cash(monkeypatch):
    st = _isolate(monkeypatch, [_receipt("r1", brand="amex", matched=False)], [])
    core._handle_ledger_update("u", "r1", {"card_brand": ["visa"]})
    assert st["ledger"]["entries"][0]["card_brand"] == "other"


def test_bulk_edit_to_visa_lands_on_cash(monkeypatch):
    st = _isolate(monkeypatch, [_receipt("r1", brand="amex", matched=False)], [])
    core._handle_ledger_bulk("u", {"ids": ["r1"], "action": "card", "value": "visa"})
    assert st["ledger"]["entries"][0]["card_brand"] == "other"
