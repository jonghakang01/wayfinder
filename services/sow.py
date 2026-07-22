import calendar
import io
import json
import os
import uuid
from datetime import date, datetime

from ._paths import DATA_ROOT

META = {
    "name": "SOW Assistant",
    "path": "/sow",
    "icon": "📝",
    "description": "Statement of Work drafting & payment schedule automation",
    "hidden": False,
    "admin_only": True,
}

CHEIL_ENTITY = "Cheil USA, Inc."
SAMSUNG_ENTITY = "Samsung Electronics America, Inc."

# Fixed legal boilerplate lifted verbatim from executed SOW samples.
PREAMBLE_SAMSUNG = (
    'This Statement of Work ("Statement of Work" or "SOW"), shall be construed and '
    'treated as a "Statement of Work" under, and as defined in, that certain '
    'Advertising Services Agreement ("Agreement") dated as of September 16, 2022 by '
    'and between Cheil USA Inc ("Agency" or "Cheil") and Samsung Electronics America, '
    'Inc., a New York corporation ("Samsung"). This SOW is valid and binding when '
    'signed on behalf of both parties and shall be effective as of the Start Date of '
    'Service ("Effective Date"). Capitalized terms used herein and not otherwise '
    "defined shall have the meaning given such terms in the Agreement."
)
PREAMBLE_AGENCY_1 = (
    'This Statement of Work ("Statement of Work" or "SOW") is made effective as of '
    '{sow_date} (the "Statement of Work Effective Date") by and between Cheil USA '
    "Inc., a Delaware corporation with its principal of business located at 837 "
    "Washington Street, 4th Floor, New York, NY 10014 on behalf of itself and its "
    'affiliates and subsidiaries ("Cheil") and {vendor_entity} ("Contractor").  '
    'Contractor and Cheil may each be referred to herein as a "Party", and, together '
    'as the "Parties".'
)
PREAMBLE_AGENCY_2 = (
    "This SOW is governed by, incorporated into, and made part of, that certain "
    'Master Services Agreement (the "Agreement"), dated as of {msa_date}, by and '
    "between Cheil and Contractor. This SOW defines the Services that Contractor "
    "shall provide to Cheil in accordance with the terms of the Agreement and this "
    "SOW.  The terms of this SOW are limited to the scope of this SOW, and shall not "
    "be applicable to any other SOWs, which may be executed and attached to the "
    "Agreement. Capitalized terms used herein and not otherwise defined shall have "
    "the meanings given them in the Agreement.  To the extent there is a conflict "
    "between the terms of this SOW and the Agreement, the terms of the Agreement "
    "shall control, except for terms where the Agreement expressly permits the SOW "
    "to control in the event of conflict with the Agreement."
)
OOP_SAMSUNG = (
    "All out of pocket expenses are a pass through cost as per the Agreement between "
    "Samsung and Cheil.\n\n"
    "No travel cost is included in the annual cost for providing this Service set "
    "forth in this SOW. If the Samsung team requires Agency personnel to travel, cost "
    "of approved travel will be reimbursed and invoiced separately within 30 days of "
    "completion of travel.\n\n"
    "Reimbursable travel-related expenses are limited to transportation, "
    "accommodation, and meals/subsistence costs, in each case that are directly "
    "related to work performed for Samsung pursuant to this SOW.  If (a) Agency "
    "reasonably requires any Agency personnel to travel to a specific site for the "
    "performance of the Services that is outside of such Agency personnel's local "
    "metropolitan area and (b) Samsung expressly approves such travel in writing, "
    "then the reasonable and documented expenses actually incurred as a result of "
    "such travel will be reimbursed by Samsung.  However, any such travel-related "
    "expenses will only be reimbursed where a travel expense maximum amount has been "
    "specifically authorized by the Samsung team in writing; and the total amount of "
    "travel expenses does not exceed the maximum amount authorized by the Samsung "
    "team. Travel-related expenses will be reimbursed by Samsung only if such "
    "expenses comply with Samsung's applicable travel policy, as provided from time "
    "to time by Samsung."
)
OOP_AGENCY = (
    "All out of pocket expenses are a pass through cost as per the most current "
    "Master Service Agreement between Cheil USA and Contractor.\n\n"
    "No travel cost is included in the cost for providing this service. If the Cheil "
    "team requires the Contractor to travel, cost of approved travel will be "
    "reimbursed and invoiced separately within 30 days of completion of travel."
)
PAYMENT_INTRO = (
    "Agency will invoice Samsung on a monthly basis at the beginning of the "
    "following month as set forth in the table below."
)
PAYMENT_INTRO_AGENCY = (
    "Contractor will invoice Cheil on a monthly basis at the end of the month as "
    "set forth in the table below."
)
CHANGE_ORDER_NOTE = (
    "Any additional costs for the Service beyond those outlined above must receive "
    "prior approval and be agreed upon through a change order to this Statement of "
    "Work executed by the parties."
)


# ── data ─────────────────────────────────────────────────────────────────────

def _data_path(user):
    return os.path.join(DATA_ROOT, user, "sow.json")


def _load(user):
    f = _data_path(user)
    if not os.path.exists(f):
        return {"sows": [], "vendors": []}
    try:
        with open(f) as fp:
            d = json.load(fp)
            d.setdefault("sows", [])
            d.setdefault("vendors", [])
            return d
    except Exception:
        return {"sows": [], "vendors": []}


def _save(user, data):
    f = _data_path(user)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


# ── schedule math ────────────────────────────────────────────────────────────

def _parse_date(s):
    try:
        return date.fromisoformat((s or "").strip())
    except Exception:
        return None


def _month_spans(start, end):
    """[(year, month, fraction)] covering start..end. Partial months use the
    days/30 convention observed in executed SOWs (Mar 23-31 → 0.3)."""
    if not start or not end or end < start:
        return []
    spans, y, m = [], start.year, start.month
    while (y, m) <= (end.year, end.month):
        last = calendar.monthrange(y, m)[1]
        s = start if (y, m) == (start.year, start.month) else date(y, m, 1)
        e = end if (y, m) == (end.year, end.month) else date(y, m, last)
        full = s.day == 1 and e.day == last
        frac = 1.0 if full else min(1.0, round(((e - s).days + 1) / 30, 2))
        spans.append((y, m, frac))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return spans


def _monthly_amount(sow):
    total = 0.0
    for r in sow.get("resources", []):
        try:
            if sow.get("res_mode") == "hourly":
                total += float(r.get("hourly") or 0) * float(r.get("hrs") or 0) * float(r.get("qty") or 1)
            else:
                total += float(r.get("rate") or 0)
        except (TypeError, ValueError):
            pass
    return round(total, 2)


def _build_schedule(sow):
    start, end = _parse_date(sow.get("start")), _parse_date(sow.get("end"))
    spans = _month_spans(start, end)
    monthly = _monthly_amount(sow)
    rule = sow.get("invoice_rule") or "next_first"
    rows = []
    for y, m, frac in spans:
        amount = round(monthly * frac, 2)
        if rule == "month_end":
            inv = date(y, m, calendar.monthrange(y, m)[1])
        else:
            inv = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        rows.append({
            "label": date(y, m, 1).strftime("%b-%y"),
            "amount": amount,
            "invoice": inv.strftime("%-d-%b-%y"),
        })
    return rows, round(sum(r["amount"] for r in rows), 2), round(sum(f for _, _, f in spans), 1)


def _money(x):
    try:
        x = float(x)
    except (TypeError, ValueError):
        return "$0"
    return f"${x:,.0f}" if abs(x - round(x)) < 0.005 else f"${x:,.2f}"


def _fmt_long(iso):
    d = _parse_date(iso)
    return d.strftime("%B %-d, %Y") if d else (iso or "")


# ── docx ─────────────────────────────────────────────────────────────────────

def _build_docx(sow, vendor):
    from docx import Document
    from docx.shared import Pt

    schedule, fee, months_total = _build_schedule(sow)
    is_agency = sow.get("direction") == "agency"
    counterpart = (vendor or {}).get("name") or "Contractor" if is_agency else SAMSUNG_ENTITY

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Calibri"
    normal.font.size = Pt(10)

    def p(text="", bold=False, size=None):
        par = doc.add_paragraph()
        run = par.add_run(text)
        run.bold = bold
        if size:
            run.font.size = Pt(size)
        return par

    def h(text):
        p(text, bold=True, size=12)

    def table(headers, rows, total_row=None):
        t = doc.add_table(rows=1, cols=len(headers))
        t.style = "Table Grid"
        for i, hd in enumerate(headers):
            cell = t.rows[0].cells[i]
            cell.text = ""
            cell.paragraphs[0].add_run(hd).bold = True
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = str(v)
        if total_row:
            cells = t.add_row().cells
            for i, v in enumerate(total_row):
                cells[i].text = ""
                cells[i].paragraphs[0].add_run(str(v)).bold = True
        return t

    p(sow.get("title") or sow.get("project_name") or "", bold=True, size=14)
    p("STATEMENT OF WORK", bold=True, size=13)
    p()
    p(f"DATE: {_fmt_long(sow.get('date'))}")
    p(f"CLIENT: {SAMSUNG_ENTITY if not is_agency else CHEIL_ENTITY}")
    p(f"PROJECT NAME: {sow.get('project_name') or ''}")
    p(f"PREPARED BY: {sow.get('prepared_by') or ''}")
    p(f"PREPARED FOR: {sow.get('prepared_for') or ''}")
    p()

    if is_agency:
        p(PREAMBLE_AGENCY_1.format(
            sow_date=_fmt_long(sow.get("date")),
            vendor_entity=(vendor or {}).get("entity_line") or counterpart,
        ))
        p()
        p(PREAMBLE_AGENCY_2.format(msa_date=_fmt_long((vendor or {}).get("msa_date")) or "the MSA date"))
    else:
        p(PREAMBLE_SAMSUNG)
    p()

    h("Executive Summary")
    for line in (sow.get("exec_summary") or "").splitlines():
        if line.strip():
            p(line.strip())
    p()

    h("Deliverables:" if not is_agency else "Service Description:")
    for line in (sow.get("deliverables") or "").splitlines():
        if line.strip():
            doc.add_paragraph(line.strip(), style="List Bullet")
    p()

    h("Project Stakeholders:")
    client_label = ((vendor or {}).get("name") or "Contractor") + " POC" if is_agency \
        else "Samsung Manager for this Role"
    table(
        ["", client_label, "Cheil Project Management & SOW Owner"],
        [
            ["Name", sow.get("stk_c_name") or "", sow.get("stk_a_name") or ""],
            ["Email", sow.get("stk_c_email") or "", sow.get("stk_a_email") or ""],
            ["Location", sow.get("stk_c_loc") or "", sow.get("stk_a_loc") or ""],
        ],
    )
    p()

    h("Service Period")
    p(f"Start Date : {_fmt_long(sow.get('start'))}")
    p(f"End Date : {_fmt_long(sow.get('end'))}")
    p()

    h("Resource Management")
    payer, payee = ("Cheil", "Contractor") if is_agency else ("Samsung", "Cheil")
    p(
        "In consideration for the provision of the Services and Deliverables under "
        f"this SOW, {payer} shall pay {payee} in accordance with the following rates "
        "and fees, subject to the applicable terms and conditions of the Agreement:"
    )
    if sow.get("res_mode") == "hourly":
        rows = []
        for r in sow.get("resources", []):
            qty = float(r.get("qty") or 1)
            cost = float(r.get("hourly") or 0) * float(r.get("hrs") or 0) * qty * months_total
            rows.append([
                r.get("profile") or "", r.get("location") or "", int(qty), months_total,
                _money(r.get("hourly")), r.get("hrs") or "", _money(cost),
            ])
        table(
            ["Profile", "Location", "# of Resources", "# of Months", "Hourly Cost",
             "# of Anticipated Hrs/Month", "Cost"],
            rows, total_row=["Total Cost", "", "", "", "", "", _money(fee)],
        )
    else:
        rows = []
        for i, r in enumerate(sow.get("resources", []), 1):
            rows.append([
                i, r.get("name") or "", r.get("role") or "", r.get("level") or "",
                r.get("region") or "", _money(r.get("rate")),
            ])
        table(["No.", "Name", "Role", "Level", "Region", "Rate/Month (USD)"], rows)
    p()

    h("Cost and Payment Schedule")
    p(f"Fee : {_money(fee)}", bold=True)
    p()
    p("Payment Schedule :")
    p(PAYMENT_INTRO_AGENCY if is_agency else PAYMENT_INTRO)
    table(
        ["Month", "Amount", "Invoice Date"],
        [[r["label"], _money(r["amount"]), r["invoice"]] for r in schedule],
        total_row=["Total", _money(fee), ""],
    )
    p()
    p(CHANGE_ORDER_NOTE)
    p()

    h("Out-of-pocket Expense")
    for para in (OOP_AGENCY if is_agency else OOP_SAMSUNG).split("\n\n"):
        p(para)
        p()

    h("Signatures")
    p(
        "IN WITNESS WHEREOF, the parties have caused this Statement of Work to be "
        "duly executed by their authorized representatives as set forth below."
    )
    p()
    left = CHEIL_ENTITY if is_agency else SAMSUNG_ENTITY
    right = ((vendor or {}).get("name") or "Contractor") if is_agency else CHEIL_ENTITY
    sig = doc.add_table(rows=5, cols=2)
    sig.rows[0].cells[0].paragraphs[0].add_run(left).bold = True
    sig.rows[0].cells[1].paragraphs[0].add_run(right).bold = True
    for i, lbl in enumerate(["Signature:", "Name:", "Title:", "Date:"], 1):
        for c in range(2):
            sig.rows[i].cells[c].text = f"{lbl} _______________________"

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── html ─────────────────────────────────────────────────────────────────────

def _esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _shell(user, title, body):
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>📝 {_esc(title)} · Wayfinder</title><link rel="stylesheet" href="/static/style.css">
<style>
.sow-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:18px 20px;margin-bottom:14px}}
.sow-list{{display:flex;flex-direction:column;gap:12px}}
.sow-row{{display:flex;align-items:center;gap:14px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:16px 18px;flex-wrap:wrap}}
.sow-row:hover{{border-color:var(--accent)}}
.sow-title{{font-weight:700;color:var(--text);font-size:.95rem}}
.sow-meta{{font-size:.78rem;color:var(--text-muted)}}
.sow-fee{{font-weight:700;color:var(--success);font-variant-numeric:tabular-nums;margin-left:auto}}
.dir-chip{{font-size:.66rem;font-weight:700;padding:2px 8px;border-radius:10px;white-space:nowrap}}
.dir-samsung{{color:#38bdf8;background:rgba(56,189,248,.12)}}
.dir-agency{{color:#fb923c;background:rgba(251,146,60,.12)}}
.f-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.f-field{{display:flex;flex-direction:column;gap:4px}}
.f-field>span{{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted)}}
.f-field input,.f-field select,.f-field textarea{{background:var(--surface-2);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:.88rem;padding:9px 11px;outline:none;width:100%}}
.f-field input:focus,.f-field select:focus,.f-field textarea:focus{{border-color:var(--accent)}}
.f-wide{{grid-column:1/-1}}
.sec-title{{font-size:.8rem;font-weight:800;color:var(--text);margin:0 0 12px;display:flex;align-items:center;gap:8px}}
.sec-title::before{{content:"";width:4px;height:1em;border-radius:99px;background:var(--accent)}}
.res-table{{width:100%;border-collapse:collapse;font-size:.84rem}}
.res-table th{{font-size:.68rem;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted);text-align:left;padding:6px 8px;border-bottom:1px solid var(--border)}}
.res-table td{{padding:5px 4px}}
.res-table input{{width:100%;background:var(--surface-2);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:.84rem;padding:7px 9px;outline:none}}
.res-table input:focus{{border-color:var(--accent)}}
.sched-table{{width:100%;border-collapse:collapse;font-size:.84rem}}
.sched-table th{{font-size:.68rem;text-transform:uppercase;color:var(--text-muted);text-align:left;padding:6px 10px;border-bottom:1px solid var(--border)}}
.sched-table td{{padding:6px 10px;border-bottom:1px solid var(--border);font-variant-numeric:tabular-nums}}
.sched-table tr:last-child td{{border-bottom:none;font-weight:700}}
@media(max-width:768px){{
  .f-grid{{grid-template-columns:1fr}}
  .res-wrap{{overflow-x:auto}}
  .res-table{{min-width:560px}}
  .sow-fee{{margin-left:0;flex-basis:100%}}
}}
</style></head><body>
<nav><span class="nav-brand">📝 SOW Assistant</span>
<span class="nav-user">👤 {_esc(user)} &nbsp;·&nbsp; <a href="/logout">Logout</a></span></nav>
<div class="container" style="max-width:1000px">{body}</div></body></html>"""


def _render_list(user):
    data = _load(user)
    rows = []
    for s in sorted(data["sows"], key=lambda x: x.get("updated", ""), reverse=True):
        _, fee, _ = _build_schedule(s)
        d = s.get("direction", "samsung")
        chip = f'<span class="dir-chip dir-{d}">{"with Samsung" if d == "samsung" else "with Agency"}</span>'
        rows.append(
            f'<div class="sow-row">'
            f'<div><div class="sow-title">{_esc(s.get("title") or s.get("project_name") or "(untitled)")}</div>'
            f'<div class="sow-meta">{chip} &nbsp;{_esc(s.get("start") or "")} ~ {_esc(s.get("end") or "")}</div></div>'
            f'<span class="sow-fee">{_money(fee)}</span>'
            f'<span style="display:flex;gap:8px">'
            f'<a class="btn btn-secondary btn-sm" href="/sow/edit?id={s["id"]}">✎ Edit</a>'
            f'<a class="btn btn-primary btn-sm" href="/sow/docx?id={s["id"]}">⬇ docx</a>'
            f'<button class="btn btn-danger btn-sm" onclick="delSow(\'{s["id"]}\')">🗑</button>'
            f'</span></div>'
        )
    body = f"""
<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin:8px 0 20px;flex-wrap:wrap">
  <h1 style="margin:0">Statements of Work</h1>
  <a class="btn btn-primary" href="/sow/new">+ New SOW</a>
</div>
<div class="sow-list">{''.join(rows) or '<div class="sow-meta" style="padding:40px;text-align:center">No SOWs yet — create the first one.</div>'}</div>
<script>
function delSow(id){{
  if(!confirm('Delete this SOW?')) return;
  fetch('/sow/delete', {{method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}}, body:'id='+encodeURIComponent(id)}})
    .then(function(){{ location.reload(); }});
}}
</script>"""
    return _shell(user, "SOW Assistant", body)


def _render_editor(user, sow=None, saved=False):
    data = _load(user)
    sow = sow or {}
    is_agency = sow.get("direction") == "agency"
    res_mode = sow.get("res_mode") or "monthly"
    vendors = data["vendors"]
    vend_opts = "".join(
        f'<option value="{v["id"]}"{" selected" if v["id"] == sow.get("vendor_id") else ""}>{_esc(v["name"])}</option>'
        for v in vendors
    )
    schedule, fee, months_total = _build_schedule(sow) if sow.get("start") else ([], 0, 0)
    sched_html = ""
    if schedule:
        srows = "".join(
            f'<tr><td>{r["label"]}</td><td>{_money(r["amount"])}</td><td>{r["invoice"]}</td></tr>'
            for r in schedule
        )
        sched_html = f"""
<div class="sow-card">
  <div class="sec-title">Payment Schedule (auto · {months_total} months)</div>
  <table class="sched-table">
    <tr><th>Month</th><th>Amount</th><th>Invoice Date</th></tr>
    {srows}
    <tr><td>Total</td><td>{_money(fee)}</td><td></td></tr>
  </table>
</div>"""
    # Raw JSON for the <script> block — HTML-escaping would corrupt it; only
    # guard against a literal </script> terminator.
    res_json = json.dumps(sow.get("resources", [])).replace("</", "<\\/")
    saved_banner = (
        '<div style="background:rgba(52,211,153,.12);border:1px solid rgba(52,211,153,.35);'
        'color:var(--success);border-radius:10px;padding:10px 14px;margin-bottom:14px;font-size:.85rem">'
        "✓ Saved — payment schedule recomputed below.</div>" if saved else ""
    )
    body = f"""
<div style="display:flex;align-items:center;justify-content:space-between;gap:12px;margin:8px 0 20px;flex-wrap:wrap">
  <h1 style="margin:0">{'Edit SOW' if sow.get('id') else 'New SOW'}</h1>
  <span style="display:flex;gap:8px">
    {f'<a class="btn btn-primary" href="/sow/docx?id={sow["id"]}">⬇ Download docx</a>' if sow.get('id') else ''}
    <a class="btn btn-ghost" href="/sow">← All SOWs</a>
  </span>
</div>
{saved_banner}
<form method="post" action="/sow/save" id="sowForm">
<input type="hidden" name="id" value="{_esc(sow.get('id') or '')}">
<input type="hidden" name="resources_json" id="resJson">

<div class="sow-card">
  <div class="sec-title">Basics</div>
  <div class="f-grid">
    <div class="f-field"><span>Direction</span>
      <select name="direction" id="fDir" onchange="dirSync()">
        <option value="samsung"{'' if is_agency else ' selected'}>with Samsung (Cheil = Agency)</option>
        <option value="agency"{' selected' if is_agency else ''}>with Agency (Cheil = Client)</option>
      </select></div>
    <div class="f-field"><span>SOW Date</span><input type="date" name="date" value="{_esc(sow.get('date') or date.today().isoformat())}"></div>
    <div class="f-field f-wide"><span>Title (document heading)</span><input name="title" value="{_esc(sow.get('title'))}" placeholder="e.g. Data Engineer # 1"></div>
    <div class="f-field f-wide"><span>Project Name</span><input name="project_name" value="{_esc(sow.get('project_name'))}" placeholder="e.g. SEA eCom Data"></div>
    <div class="f-field"><span>Prepared By</span><input name="prepared_by" value="{_esc(sow.get('prepared_by'))}"></div>
    <div class="f-field"><span>Prepared For</span><input name="prepared_for" value="{_esc(sow.get('prepared_for'))}"></div>
    <div class="f-field f-wide" id="vendorBlock" style="{'' if is_agency else 'display:none'}">
      <span>Vendor (MSA registry)</span>
      <select name="vendor_id">{vend_opts or '<option value="">— none registered —</option>'}</select>
      <details style="margin-top:8px"><summary style="font-size:.78rem;color:var(--text-muted);cursor:pointer">+ Register new vendor</summary>
        <div class="f-grid" style="margin-top:10px">
          <div class="f-field"><span>Vendor name</span><input name="v_name" placeholder="e.g. Invictus Data, Inc."></div>
          <div class="f-field"><span>MSA date</span><input type="date" name="v_msa"></div>
          <div class="f-field f-wide"><span>Entity line (name + address, for preamble)</span><input name="v_entity" placeholder="Invictus Data Inc, with its principal place of business located at ..."></div>
        </div>
      </details>
    </div>
  </div>
</div>

<div class="sow-card">
  <div class="sec-title">Summary & Scope</div>
  <div class="f-grid">
    <div class="f-field f-wide"><span>Executive Summary</span><textarea name="exec_summary" rows="3">{_esc(sow.get('exec_summary'))}</textarea></div>
    <div class="f-field f-wide"><span>Deliverables / Service Description (one per line → bullets)</span><textarea name="deliverables" rows="6">{_esc(sow.get('deliverables'))}</textarea></div>
  </div>
</div>

<div class="sow-card">
  <div class="sec-title">Stakeholders</div>
  <div class="f-grid">
    <div class="f-field"><span id="cLabel">{'Vendor POC' if is_agency else 'Samsung Manager'} — Name</span><input name="stk_c_name" value="{_esc(sow.get('stk_c_name'))}"></div>
    <div class="f-field"><span>Cheil Owner — Name</span><input name="stk_a_name" value="{_esc(sow.get('stk_a_name'))}"></div>
    <div class="f-field"><span>Email</span><input name="stk_c_email" value="{_esc(sow.get('stk_c_email'))}"></div>
    <div class="f-field"><span>Email</span><input name="stk_a_email" value="{_esc(sow.get('stk_a_email'))}"></div>
    <div class="f-field"><span>Location</span><input name="stk_c_loc" value="{_esc(sow.get('stk_c_loc'))}"></div>
    <div class="f-field"><span>Location</span><input name="stk_a_loc" value="{_esc(sow.get('stk_a_loc'))}"></div>
  </div>
</div>

<div class="sow-card">
  <div class="sec-title">Service Period & Invoicing</div>
  <div class="f-grid">
    <div class="f-field"><span>Start Date</span><input type="date" name="start" value="{_esc(sow.get('start'))}" required></div>
    <div class="f-field"><span>End Date</span><input type="date" name="end" value="{_esc(sow.get('end'))}" required></div>
    <div class="f-field f-wide"><span>Invoice Date Rule</span>
      <select name="invoice_rule">
        <option value="next_first"{'' if sow.get('invoice_rule') == 'month_end' else ' selected'}>1st of following month</option>
        <option value="month_end"{' selected' if sow.get('invoice_rule') == 'month_end' else ''}>Last day of service month</option>
      </select></div>
  </div>
</div>

<div class="sow-card">
  <div class="sec-title">Resources</div>
  <div class="f-grid" style="margin-bottom:12px">
    <div class="f-field"><span>Rate Model</span>
      <select name="res_mode" id="fMode" onchange="modeSync()">
        <option value="monthly"{'' if res_mode == 'hourly' else ' selected'}>Monthly rate (Name/Role/Level/Region)</option>
        <option value="hourly"{' selected' if res_mode == 'hourly' else ''}>Hourly (Profile/Qty/Hrs per month)</option>
      </select></div>
  </div>
  <div class="res-wrap">
  <table class="res-table" id="resTable"><thead></thead><tbody></tbody></table>
  </div>
  <button type="button" class="btn btn-ghost btn-sm" onclick="addRow()" style="margin-top:10px">+ Add resource</button>
</div>

<div style="display:flex;gap:10px;margin:18px 0 40px">
  <button type="submit" class="btn btn-primary btn-lg">💾 Save & Recompute</button>
</div>
</form>
{sched_html}
<script>
var RES = {res_json};
var COLS = {{
  monthly: [['name','Name'],['role','Role'],['level','Level'],['region','Region'],['rate','Rate/Month USD']],
  hourly:  [['profile','Profile'],['location','Location'],['qty','Qty'],['hourly','Hourly USD'],['hrs','Hrs/Month']]
}};
function mode(){{ return document.getElementById('fMode').value; }}
function renderTable(){{
  var cols = COLS[mode()];
  var head = '<tr>' + cols.map(function(c){{ return '<th>'+c[1]+'</th>'; }}).join('') + '<th></th></tr>';
  document.querySelector('#resTable thead').innerHTML = head;
  var tb = document.querySelector('#resTable tbody');
  tb.innerHTML = '';
  RES.forEach(function(r, i){{
    var tr = document.createElement('tr');
    tr.innerHTML = cols.map(function(c){{
      return '<td><input data-k="'+c[0]+'" data-i="'+i+'" value="'+(r[c[0]]!=null?String(r[c[0]]).replace(/"/g,'&quot;'):'')+'"></td>';
    }}).join('') + '<td><button type="button" class="btn btn-danger btn-sm" onclick="rmRow('+i+')">✕</button></td>';
    tb.appendChild(tr);
  }});
}}
function addRow(){{ RES.push({{}}); renderTable(); }}
function rmRow(i){{ RES.splice(i,1); renderTable(); }}
function modeSync(){{ renderTable(); }}
function dirSync(){{
  var ag = document.getElementById('fDir').value === 'agency';
  document.getElementById('vendorBlock').style.display = ag ? '' : 'none';
  document.getElementById('cLabel').textContent = (ag ? 'Vendor POC' : 'Samsung Manager') + ' — Name';
}}
document.addEventListener('input', function(e){{
  var k = e.target.dataset && e.target.dataset.k;
  if(k) RES[parseInt(e.target.dataset.i)][k] = e.target.value;
}});
document.getElementById('sowForm').addEventListener('submit', function(){{
  document.getElementById('resJson').value = JSON.stringify(RES.filter(function(r){{
    return Object.keys(r).some(function(k){{ return String(r[k]||'').trim(); }});
  }}));
}});
if(!RES.length) RES.push({{}});
renderTable();
</script>"""
    return _shell(user, "SOW Editor", body)


# ── routing ──────────────────────────────────────────────────────────────────

def _f(body, key, default=""):
    v = body.get(key, default)
    if isinstance(v, list):
        v = v[0] if v else default
    return (v or "").strip()


def handle(method, path, body, ctx):
    user = ctx.get("user", "guest")

    if method == "GET" and path == "/sow":
        return ("html", _render_list(user))

    if method == "GET" and path.startswith("/sow/new"):
        return ("html", _render_editor(user))

    if method == "GET" and path.startswith("/sow/edit"):
        # GET dispatch strips the query string; params arrive as the body dict.
        sid = _f(body, "id")
        data = _load(user)
        sow = next((s for s in data["sows"] if s["id"] == sid), None)
        if not sow:
            return ("redirect", "/sow")
        return ("html", _render_editor(user, sow, saved=_f(body, "saved") == "1"))

    if method == "POST" and path == "/sow/save":
        data = _load(user)
        sid = _f(body, "id") or uuid.uuid4().hex[:10]
        try:
            resources = json.loads(_f(body, "resources_json") or "[]")
            assert isinstance(resources, list)
        except Exception:
            resources = []
        # Inline vendor registration rides along with the save.
        vendor_id = _f(body, "vendor_id")
        v_name = _f(body, "v_name")
        if v_name:
            vendor_id = uuid.uuid4().hex[:8]
            data["vendors"].append({
                "id": vendor_id, "name": v_name,
                "entity_line": _f(body, "v_entity"),
                "msa_date": _f(body, "v_msa"),
            })
        sow = next((s for s in data["sows"] if s["id"] == sid), None)
        rec = {
            "id": sid,
            "direction": _f(body, "direction") or "samsung",
            "date": _f(body, "date"),
            "title": _f(body, "title"),
            "project_name": _f(body, "project_name"),
            "prepared_by": _f(body, "prepared_by"),
            "prepared_for": _f(body, "prepared_for"),
            "vendor_id": vendor_id,
            "exec_summary": _f(body, "exec_summary"),
            "deliverables": _f(body, "deliverables"),
            "stk_c_name": _f(body, "stk_c_name"), "stk_c_email": _f(body, "stk_c_email"),
            "stk_c_loc": _f(body, "stk_c_loc"),
            "stk_a_name": _f(body, "stk_a_name"), "stk_a_email": _f(body, "stk_a_email"),
            "stk_a_loc": _f(body, "stk_a_loc"),
            "start": _f(body, "start"), "end": _f(body, "end"),
            "invoice_rule": _f(body, "invoice_rule") or "next_first",
            "res_mode": _f(body, "res_mode") or "monthly",
            "resources": resources,
            "created": (sow or {}).get("created") or datetime.now().isoformat(),
            "updated": datetime.now().isoformat(),
        }
        if sow:
            data["sows"][data["sows"].index(sow)] = rec
        else:
            data["sows"].append(rec)
        _save(user, data)
        return ("redirect", f"/sow/edit?id={sid}&saved=1")

    if method == "POST" and path == "/sow/delete":
        data = _load(user)
        sid = _f(body, "id")
        data["sows"] = [s for s in data["sows"] if s["id"] != sid]
        _save(user, data)
        return ("redirect", "/sow")

    if method == "GET" and path.startswith("/sow/docx"):
        sid = _f(body, "id")
        data = _load(user)
        sow = next((s for s in data["sows"] if s["id"] == sid), None)
        if not sow:
            return ("redirect", "/sow")
        vendor = next((v for v in data["vendors"] if v["id"] == sow.get("vendor_id")), None)
        blob = _build_docx(sow, vendor)
        safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in (sow.get("title") or "SOW"))[:60].strip()
        fname = f"Cheil_SOW_{safe}_{sow.get('date') or date.today().isoformat()}.docx"
        return ("file_inline", blob,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fname)

    return ("html", "<h2>404 Not Found</h2>")
