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
