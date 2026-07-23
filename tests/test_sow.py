import importlib

MOD = "services.sow"


def _mod():
    return importlib.import_module(MOD)


def test_meta_is_valid():
    m = _mod().META
    assert m["path"] == "/sow"
    assert m["name"] and isinstance(m["name"], str)
    assert m.get("admin_only") is True


def test_get_renders_html():
    kind, html = _mod().handle("GET", "/sow", {}, {"user": "__testuser__"})
    assert kind == "html"
    assert "SOW Assistant" in html


def test_schedule_matches_executed_data_engineer_sow():
    # Real numbers from "Samsung_ Data Engineer.docx": Mar 23 - Dec 31 2026,
    # 1 x $25/h x 168h/mo => 9.3 months, first month $1,260, total $39,060.
    m = _mod()
    sow = {
        "start": "2026-03-23", "end": "2026-12-31",
        "res_mode": "hourly",
        "resources": [{"profile": "Data Engineer", "qty": 1, "hourly": 25, "hrs": 168}],
        "invoice_rule": "next_first",
    }
    rows, fee, months = m._build_schedule(sow)
    assert round(months, 1) == 9.3
    assert rows[0]["amount"] == 1260
    assert rows[1]["amount"] == 4200
    assert fee == 39060
    assert rows[0]["invoice"] == "1-Apr-26"
    assert len(rows) == 10


def test_schedule_monthly_mode_full_months():
    m = _mod()
    sow = {
        "start": "2026-04-01", "end": "2026-09-30",
        "res_mode": "monthly",
        "resources": [{"name": "A", "rate": 30168}],
        "invoice_rule": "month_end",
    }
    rows, fee, months = m._build_schedule(sow)
    assert months == 6.0
    assert len(rows) == 6
    assert fee == 30168 * 6
    assert rows[0]["invoice"] == "30-Apr-26"


def test_docx_builds_valid_zip():
    m = _mod()
    sow = {
        "id": "t1", "direction": "samsung", "title": "Test SOW",
        "project_name": "Test", "date": "2026-07-22",
        "start": "2026-08-01", "end": "2026-10-31",
        "res_mode": "monthly", "resources": [{"name": "A", "role": "Dev", "rate": 1000}],
        "exec_summary": "Summary", "deliverables": "Do a thing\nDo another",
    }
    blob = m._build_docx(sow, None)
    assert blob[:2] == b"PK"
    assert len(blob) > 5000


def test_docx_agency_uses_vendor_msa():
    m = _mod()
    sow = {
        "id": "t2", "direction": "agency", "title": "Vendor SOW",
        "project_name": "P", "date": "2026-07-22",
        "start": "2026-08-01", "end": "2026-08-31",
        "res_mode": "hourly",
        "resources": [{"profile": "Analyst", "qty": 1, "hourly": 30, "hrs": 160}],
    }
    vendor = {"id": "v1", "name": "Invictus Data, Inc.",
              "entity_line": "Invictus Data Inc, Los Altos CA", "msa_date": "2023-09-28"}
    blob = m._build_docx(sow, vendor)
    assert blob[:2] == b"PK"


def test_msa_docx_fills_vendor_and_date():
    m = _mod()
    sow = {"id": "t3", "type": "agy_msa", "direction": "agency", "kind": "msa",
           "date": "2026-08-01"}
    vendor = {"id": "v1", "name": "Nendrasys Technologies Inc."}
    blob = m._build_msa_docx(sow, vendor)
    assert blob[:2] == b"PK"
    import zipfile, io, re
    xml = zipfile.ZipFile(io.BytesIO(blob)).read("word/document.xml").decode("utf-8", "ignore")
    txt = re.sub(r"<[^>]+>", "", xml)
    assert "Nendrasys Technologies Inc." in txt
    assert "August 1, 2026" in txt
    assert "Your Company Name" not in txt
    assert "XXX" not in txt


def test_nda_docx_builds():
    m = _mod()
    sow = {"id": "t4", "type": "agy_nda", "direction": "agency", "kind": "nda",
           "date": "2026-08-01"}
    blob = m._build_nda_docx(sow, {"id": "v1", "name": "Acme Corp"})
    assert blob[:2] == b"PK"
    import zipfile, io, re
    txt = re.sub(r"<[^>]+>", "", zipfile.ZipFile(io.BytesIO(blob)).read("word/document.xml").decode("utf-8", "ignore"))
    assert "CONFIDENTIALITY AND NONDISCLOSURE AGREEMENT" in txt
    assert "Acme Corp" in txt


def test_schedule_overrides_apply_per_month():
    m = _mod()
    sow = {
        "start": "2026-04-01", "end": "2026-06-30",
        "res_mode": "monthly", "resources": [{"name": "A", "rate": 1000}],
        "schedule_overrides": {"May-26": 750},
    }
    rows, fee, months = m._build_schedule(sow)
    assert [r["amount"] for r in rows] == [1000, 750, 1000]
    assert fee == 2750


def test_legacy_types_collapse_to_merged_sow():
    m = _mod()
    assert m._sow_type({"type": "sea_role"}) == "sea_sow"
    assert m._sow_type({"type": "agy_team", "direction": "agency"}) == "agy_sow"
    assert m._sow_type({"type": "agy_msa"}) == "agy_msa"


def test_sample_renders_full_document():
    m = _mod()
    html = m._render_example("sea_sow")
    for needle in ["STATEMENT OF WORK", "Advertising Services Agreement",
                   "Out-of-pocket Expense", "Signatures", "1-Jan-27", "ex-mark"]:
        assert needle in html, needle
    html2 = m._render_example("agy_sow")
    assert "Master Services Agreement" in html2 and "Invictus" in html2


def test_estimate_computation_matches_executed_file():
    # AEM Bridge 2 numbers: $40/h dev → 6,720/mo, alloc 1, 5 months = 33,600;
    # Woosuk $227 @ 10% → 3,813.6/mo, 19,068 total.
    m = _mod()
    sow = {"months": 5, "rows": [
        {"name": "Woosuk", "rate": 227, "alloc": 0.1},
        {"name": "Anuj", "rate": 40, "alloc": 1},
    ]}
    rows, tot_monthly, tot_total, _ = m._est_rows_computed(sow)
    assert rows[0]["monthly"] == 227 * 168
    assert round(rows[0]["monthly_cost"], 1) == 3813.6
    assert round(rows[0]["total"], 0) == 19068
    assert rows[1]["total"] == 33600
    assert round(tot_total, 0) == 19068 + 33600


def test_estimate_xlsx_builds_with_totals():
    m = _mod()
    sow = {"id": "e1", "title": "AEM Bridge 2", "months": 5,
           "period_label": "From Aug til Dec (Total)",
           "rows": [{"name": "Anuj Patel", "function": "Dev", "email": "a@x.com",
                     "location": "India", "rate": 40, "alloc": 1}]}
    blob = m._build_est_xlsx(sow)
    assert blob[:2] == b"PK"
    import openpyxl, io
    ws = openpyxl.load_workbook(io.BytesIO(blob)).active
    vals = [[c.value for c in r] for r in ws.iter_rows()]
    assert vals[1][1] == "Resource" and vals[1][9] == "From Aug til Dec (Total)"
    assert vals[2][1] == "Anuj Patel" and vals[2][6] == 6720 and vals[2][9] == 33600
    assert vals[3][8] == 6720 and vals[3][9] == 33600  # totals row


def test_person_migration_and_ebita():
    m = _mod()
    legacy = {"id": "p1", "name": "A", "rate": "122", "vendor_cost": "90",
              "function": "Dev", "email": "a@samsung.com", "salary": ""}
    p = m._migrate_person(legacy)
    assert p["sell_hr"] == "122" and p["cost_hr"] == "90"
    assert p["role_title"] == "Dev" and p["email_samsung"] == "a@samsung.com"
    # EBITA: manual wins; else budget - partner cost; else None
    p["client_budget"] = "102,480"
    p["partner_cost"] = "80000"
    v, auto = m._person_ebita(p)
    assert v == 22480 and auto is True
    p["ebita"] = "25000"
    v, auto = m._person_ebita(p)
    assert v == 25000 and auto is False
    v, auto = m._person_ebita({"client_budget": "100"})
    assert v is None
