"""AMEX Billing Support File (.xls) → Posted-CSV adapter regression tests.

The Billing Support File is a legacy BIFF .xls with a metadata block above
the header row (unlike the Master xlsx whose header is row 1). The synthetic
fixture mirrors the real layout: header at row 13, supplemental cardmember
columns for the managed card, basic-only rows without transaction fields.
"""
import csv
import io

import pytest

from services import _cardconv_core as cc

xlwt = pytest.importorskip("xlwt")

_HEADER = [
    "Product", "Basic \nCardmember \nLast Name", "Basic \nCardmember \nFirst Name",
    "Basic Cardmember \nMiddle Name", "Basic \nCardmember \nPrefix Name",
    "Basic \nCardmember \nSuffix Name", "Basic Card Account No.", "Employee ID",
    "Cost Center", "Universal ID", "Supplemental \nCardmember Last \nName",
    "Supplemental \nCardmember First \nName", "Supplemental \nAccount Number",
    "Basic Control Account Name", "Basic Control Account No.",
    "Business Process Date", "Transaction Date", "Transaction \nReference No.",
    "Transaction \nAmount \nUSD", "Transaction \nDescription 1",
]


def _billing_xls() -> bytes:
    wb = xlwt.Workbook()
    ws = wb.add_sheet("Statement_1006")
    ws.write(0, 0, "THIS IS NOT A STATEMENT OR REMITTANCE ADVICE")
    ws.write(2, 0, "Billing Support File Name:")
    ws.write(2, 1, "Cardmember Monthly Account Detail")
    ws.write(4, 1, "3787-501435-31006")
    for j, h in enumerate(_HEADER):
        ws.write(12, j, h)
    # supplemental (managed card) transaction row
    row = ["CORPORATE CARD", "CBA", "ANDY", "JUNG", "", "", "3787-501435-31006",
           "", "", "", "LEE", "HYUNA", "3787-501435-31253", "ANDY JUNG",
           "3791-105545-51002", "07/21/2026", "07/21/2026", "0027968437072",
           "900.00", "FACEBK *TEST   MENLO PARK         US   "]
    for j, v in enumerate(row):
        if v != "":
            ws.write(13, j, v)
    # basic-only summary row without transaction fields — must be dropped
    for j, v in enumerate(["CORPORATE CARD", "CBA", "ANDY", "JUNG", "", "",
                           "3787-501435-31006"]):
        if v != "":
            ws.write(14, j, v)
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_billing_xls_adapts_to_posted_shape():
    out = cc._master_xlsx_to_csv_bytes(_billing_xls())
    rows = list(csv.DictReader(io.StringIO(out.decode("utf-8"))))
    assert len(rows) == 1
    r = rows[0]
    assert r["Card Member Name"] == "HYUNA LEE"
    assert r["Date"] == "2026-07-21"
    assert r["Amount"] == "900.00"
    assert r["Account Number"] == "378750143531253"
    assert "FACEBK *TEST" in r["Merchant Name"]


def test_billing_xls_rows_pass_member_filter():
    csv_bytes = cc._master_xlsx_to_csv_bytes(_billing_xls())
    reader = csv.DictReader(io.TextIOWrapper(io.BytesIO(csv_bytes),
                                             encoding="utf-8-sig", newline=""))
    target = {"HYUNA LEE"}
    kept = [r for r in reader
            if r.get("Card Member Name", "").strip().upper() in target]
    assert len(kept) == 1


def test_master_xlsx_header_row_one_still_works():
    # regression: the Master export (header at row 1) must survive the
    # generalized header scan
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.append(["T.Date", "Desc", "Amt", "Recon"])
    ws.append(["2026-07-01", "TEST MERCHANT", 12.34, ""])
    buf = io.BytesIO()
    wb.save(buf)
    out = cc._master_xlsx_to_csv_bytes(buf.getvalue())
    rows = list(csv.DictReader(io.StringIO(out.decode("utf-8"))))
    assert len(rows) == 1
    assert rows[0]["Merchant Name"] == "TEST MERCHANT"
    assert rows[0]["Amount"] == "12.34"
