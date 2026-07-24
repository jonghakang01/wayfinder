import calendar
import io
import json
import os
import re
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

# Document types drill down: direction → document kind (SOW / MSA / NDA).
# One SOW template per direction (2026-07-22, 강프로: team/individual merged) —
# the rate model (monthly vs hourly resource table) is a toggle inside the
# editor instead of a separate document type.
TYPES = {
    "sea_sow": {
        "dir": "samsung", "kind": "sow", "mode": "hourly", "icon": "📝",
        "label": "Statement of Work",
        "desc": "SOW under the Advertising Services Agreement — resources billed hourly or at monthly rates (pick inside).",
    },
    "agy_sow": {
        "dir": "agency", "kind": "sow", "mode": "hourly", "icon": "📝",
        "label": "Statement of Work",
        "desc": "Vendor SOW under the vendor's MSA — resources billed hourly or at monthly rates (pick inside).",
    },
    "sea_est": {
        "dir": "samsung", "kind": "est", "mode": None, "icon": "🧮",
        "label": "Cost Estimation",
        "desc": "Pick people from the roster, set allocation and months — billing (and internal cost) computes itself. Exports the estimation xlsx.",
    },
    "agy_msa": {
        "dir": "agency", "kind": "msa", "mode": None, "icon": "📜",
        "label": "Master Services Agreement",
        "desc": "The standard Cheil MSA — pick the vendor and effective date; the full legal text exports as-is.",
    },
    "agy_nda": {
        "dir": "agency", "kind": "nda", "mode": None, "icon": "🤐",
        "label": "One-Way NDA",
        "desc": "Confidentiality & nondisclosure agreement signed before vendor talks — vendor + date fill-in.",
    },
}

_ASSETS = os.path.join(os.path.dirname(__file__), "sow_assets")

# Full executed documents rendered beside the template (2026-07-22 강프로:
# the whole Word document, title page through signatures, with the fill-in
# fields highlighted so drafting maps 1:1 to the editor's slots).
SAMPLES = {
    "sea_sow": {
        "src": "Samsung_ Data Engineer.docx (executed Dec 2025)",
        "title": "Data Engineer # 1",
        "date": "Dec 7, 2025", "project": "SEA eCom Data",
        "by": "Jongha Kang", "for": "Nanda Kumar",
        "summary": ("This Statement of Work outlines the provision of Data Engineering "
                    "support focused on building and maintaining the data infrastructure "
                    "that enables analytics, and reporting initiatives across organizations. "
                    "The role is centered on developing reliable, scalable, and high-quality "
                    "data pipelines and systems, while contributing to data platform "
                    "evolution and cross-functional data enablement."),
        "deliverables": [
            "Design, build, and maintain scalable data pipelines to ingest, transform, and process data from multiple sources",
            "Develop and manage ETL/ELT workflows to ensure timely, accurate, and efficient data availability for analytics and personalization use cases.",
            "Model and structure data for consumption by downstream systems, including BI tools, experimentation platforms, and marketing systems.",
            "Ensure data quality, integrity, and reliability through validation checks, monitoring frameworks, and automated alerting mechanisms.",
            "Partner with Data Product Managers, analysts, and business stakeholders to understand data requirements and translate them into scalable engineering solutions.",
            "Optimize data pipelines and queries for performance, cost efficiency, and scalability across growing data volumes.",
            "Manage and maintain data warehouse and/or lake environments, ensuring proper partitioning, indexing, and storage optimization.",
            "Implement and enforce data governance best practices, including schema management, access controls, and documentation standards.",
            "Support real-time and near-real-time data processing needs where required for personalization and campaign activation.",
            "Collaborate with engineering teams to improve data instrumentation, event tracking, and logging across digital platforms.",
            "Troubleshoot data issues, perform root cause analysis, and implement long-term fixes to prevent recurrence.",
            "Build reusable data frameworks, pipeline templates, and tooling to accelerate development and standardize engineering practices.",
            "Maintain clear documentation of data pipelines, schemas, transformations, and dependencies to support transparency and maintainability.",
        ],
        "stk": [["Durga R", "Jongha Kang"], ["durga.r@samsung.com", "jongha.kang@cheil.com"],
                ["Chennai, India", "Mountain View, USA"]],
        "start": "March 23, 2026", "end": "December 31, 2026",
        "res_mode": "hourly",
        "res_rows": [["Data Engineer", "India", "1", "9.3", "$25", "168", "$39,060"]],
        "fee": "$39,060",
        "schedule": [
            ["Mar-26", "$1,260", "1-Apr-26"], ["Apr-26", "$4,200", "1-May-26"],
            ["May-26", "$4,200", "1-Jun-26"], ["Jun-26", "$4,200", "1-Jul-26"],
            ["Jul-26", "$4,200", "1-Aug-26"], ["Aug-26", "$4,200", "1-Sep-26"],
            ["Sep-26", "$4,200", "1-Oct-26"], ["Oct-26", "$4,200", "1-Nov-26"],
            ["Nov-26", "$4,200", "1-Dec-26"], ["Dec-26", "$4,200", "1-Jan-27"],
        ],
    },
    "agy_sow": {
        "src": "eComm Sr. Data Analyst — Cheil-Invictus SOW (executed Jan 2025)",
        "title": "Sr. Data Analyst (Corp Marketing Dashboard Support Scope)",
        "date": "Jan 17, 2025", "project": "Corp Marketing Dashboard Support",
        "by": "", "for": "",
        "vendor_name": "Invictus Data, Inc.",
        "vendor_entity": ("Invictus Data Inc, with its principal place of business located "
                          "at 675 Shady Creek Ln, Los Altos, CA – 94024"),
        "msa_date": "September 28, 2023",
        "summary": ("A skilled Sr. Data Analyst for Bigdata platform to work as a part of a "
                    "growing team to provide business insights, analyze trends, build "
                    "dashboards, data mining using SQL, and other similar technologies."),
        "deliverables": [
            "Analyze business performance, pinpoint key challenges, and present insights using clear and concise visualizations (charts, graphs, tables, or summaries).",
            "Drive innovation by leveraging data to generate insights, develop business cases, and create scalable solutions that foster business growth.",
            "Collaborate with Category/Product Managers to guide product and business decisions through data-driven insights.",
            "Provide data analysis and support for Ecommerce Operations and Trade-in strategies, ensuring alignment with business goals.",
            "Take ownership of a key business area from a data perspective, conducting deep dives and delivering actionable insights.",
            "Partner with product managers, business team members, and engineers to implement accurate tracking and tagging for critical business metrics.",
            "Develop and refine processes to test, learn, and iterate, accelerating growth through continuous improvement.",
            "Extract actionable insights from data using SQL, Spark, Hive, and Tableau, summarizing findings for leadership teams.",
            "Design and maintain Tableau dashboards to meet business needs, while working with engineering teams to build data solutions.",
            "Regularly audit dashboards and business metrics to identify trends, discrepancies, or issues with data pipelines.",
            "Provide ad-hoc analytics and reporting support for executive presentations and decision-making.",
        ],
        "stk": [["Pranav Vishwanathan", ""], ["", ""], ["", ""]],
        "start": "December 1, 2024", "end": "December 31, 2025",
        "res_mode": "hourly",
        "res_rows": [["Pranav Vishwanathan", "Sr. Data Analyst", "1", "13", "$32", "168", "$69,888"]],
        "fee": "$69,888",
        "schedule": [
            ["Dec-24", "$5,824", "1-Jan-25"], ["Jan-25", "$5,824", "1-Feb-25"],
            ["Feb-25", "$5,824", "1-Mar-25"], ["Mar-25", "$5,824", "1-Apr-25"],
            ["Apr-25", "$5,824", "1-May-25"], ["May-25", "$5,824", "1-Jun-25"],
            ["Jun-25", "$5,824", "1-Jul-25"], ["Jul-25", "$5,824", "1-Aug-25"],
            ["Aug-25", "$5,824", "1-Sep-25"], ["Sep-25", "$5,824", "1-Oct-25"],
            ["Oct-25", "$5,824", "1-Nov-25"], ["Nov, Dec-25", "$5,824", "1-Dec-25"],
        ],
    },
    "agy_msa": {
        "src": "MSA Cheil-AIEnterprise (executed May 31, 2024)",
        "note": ("Executed fill-in: Effective Date = May 31, 2024 · Contractor = AIEnterprise Inc. "
                 "The template on the left IS the full executed document — the highlighted date and "
                 "vendor fields were the only vendor-specific edits."),
    },
    "agy_nda": {
        "src": "Cheil NY Vendor One-Way NDA (executed May 29, 2024)",
        "note": ("Executed fill-in: Effective Date = 05/29/2024 · Vendor = AIENTERPRISE INC. "
                 "(signed by Sudhanshu Mohan, CEO). The template on the left is the full executed "
                 "text — only the highlighted date and vendor name vary."),
    },
}

# One-way NDA text lifted from the executed "Cheil NY Vendor One-Way NDA" (slots
# for effective date and vendor name). Kept verbatim, including original quirks.
NDA_TITLE = "CONFIDENTIALITY AND NONDISCLOSURE AGREEMENT"
NDA_INTRO = (
    'This CONFIDENTIALITY AND NONDISCLOSURE AGREEMENT (the "Agreement"), is '
    'entered into as of {date} (the "Effective Date"), by and between {vendor} '
    '(the "Vendor"), and Cheil USA, Inc. (the "Cheil").'
)
NDA_BODY = [
    "WHEREAS, the Vendor and Cheil are engaged in, or may enter into, talks regarding "
    "a potential business relationship, and the Vendor understands that Cheil has "
    "disclosed or may disclose to the Vendor certain confidential and proprietary "
    "information which has commercial and other value in the business of Cheil.",
    "NOW, THEREFORE, in consideration of the foregoing, and the mutual covenants, "
    "terms and conditions set forth herein, and other good and valuable consideration, "
    "the receipt and sufficiency of which are hereby acknowledged, the parties hereto "
    "hereby agree as follows.",
    "1. For purposes of this Agreement, “Confidential Information” shall mean all "
    "technical and business information relating to Cheil’s products, clients, "
    "technology, software, processes, methods, services, research and development, "
    "pricing, future business plans and all other information of Cheil or its clients "
    "which may be disclosed by Cheil or to which the Vendor may be provided access by "
    "Cheil in accordance with this Agreement.",
    "2. Confidential Information shall not include any information that: (i) is or "
    "becomes (through no improper action or inaction by the Vendor) generally "
    "available to the public; (ii) was in its possession or known by it prior to "
    "receipt from Cheil; (iii) was rightfully disclosed to him/her by a third party "
    "without a breach of any confidentiality obligations; or (iv) was independently "
    "developed by the Vendor without reference to any Confidential Information.",
    "3. The Vendor agrees: (i) to hold the Confidential Information in confidence and "
    "to take all reasonable precautions to protect such Confidential Information; "
    "(ii) not to disclose any such Confidential Information or any information derived "
    "therefrom to any third person; and (iii) not to make any use whatsoever at any "
    "time of such Confidential Information except for the limited and sole internal "
    "business purposes for which is has been disclosed by Cheil.  Any employee given "
    "access to any such Confidential Information by the Vendor must have a legitimate "
    "“need to know” such Confidential Information.  The Vendor is liable for all acts "
    "and omissions of third parties to whom he/she discloses Confidential Information.  "
    "Further, the Vendor may make disclosures required by valid order of any court or "
    "other authorized governmental entity, provided the Vendor promptly notifies "
    "Cheil, uses reasonable efforts to limit disclosure and assists Cheil, at Cheil's "
    "expense, to obtain confidential treatment or a protective order for such "
    "Confidential Information.  All Confidential Information is provided “AS IS” and "
    "without any warranties, express, implied or otherwise, and no warranty is made "
    "regarding its accuracy or completeness.  The Vendor shall not reverse engineer, "
    "decompile, translate, adapt, or disassemble any software of the other party, or "
    "attempt to make derivative works from such software.  No licenses or rights under "
    "any patent, copyright, trademark or trade secret are granted, or are to be "
    "implied, by this Agreement.  The Confidential Information shall remain the sole "
    "property of Cheil and the Vendor shall not challenge or contest Cheil’s right to "
    "own and use the Confidential Information or other intellectual property.",
    "4. Immediately upon a request by Cheil at any time, the Vendor will turn over to "
    "Cheil all Confidential Information and all documents or media containing any such "
    "Confidential Information and any and all copies or extracts thereof.  The Vendor "
    "understands that nothing herein: (i) requires the disclosure of any Confidential "
    "Information by Cheil, which shall be disclosed, if at all, solely at the option "
    "of Cheil; or (ii) requires Cheil to proceed with any proposed transaction or "
    "other business relationship in connection with which Confidential Information "
    "may be disclosed.",
    "5. The Vendor acknowledges and agrees that due to the unique nature of the "
    "Confidential Information, there can be no adequate remedy at law for any breach "
    "of its obligations hereunder, that any such breach or any unauthorized use or "
    "release of any Confidential Information will allow the Vendor or third parties "
    "to unfairly compete with Cheil resulting in irreparable harm to Cheil and "
    "therefore, that upon any such breach or any threat thereof, Cheil shall be "
    "entitled to appropriate equitable relief in addition to whatever remedies it "
    "might have at law and to be indemnified by the Vendor from any loss or harm, "
    "including, without limitation, reasonable attorney’s fees and expenses, in "
    "connection with any breach or enforcement of the Vendor’s obligations hereunder "
    "or the unauthorized use or release of any such Confidential Information.  The "
    "Vendor will notify Cheil in writing immediately upon becoming aware of the "
    "occurrence of any such unauthorized release or other breach of confidentiality "
    "obligations hereunder.",
    "6. Neither party shall have the right to assign its rights or obligations under "
    "this Agreement, whether expressly or by operation of law, without the prior "
    "written consent of the other party.  This Agreement shall be binding on, and "
    "inure to the benefit of, each party and their permitted successors and assigns.",
    "7. This Agreement shall be governed by the laws of the State of New York, and "
    "each party irrevocably submits to the exclusive jurisdiction of the courts "
    "located in New York County, New York.  In the event that any of the provisions "
    "of this Agreement shall be held by a court or other tribunal of competent "
    "jurisdiction to be illegal, invalid or unenforceable, such provisions shall be "
    "limited or eliminated to the minimum extent necessary so that this Agreement "
    "shall otherwise remain in full force and effect.  This Agreement supersedes all "
    "prior discussions and writings and constitutes the entire agreement between the "
    "parties with respect to the limited subject matter set forth herein.  No waiver "
    "or modification of this Agreement will be binding upon either party unless made "
    "in writing and signed by a duly authorized representative of such party and no "
    "failure or delay in enforcing any right will be deemed a waiver.",
    "IN WITNESS WHEREOF, the parties have executed this Agreement as of the "
    "Effective Date.",
]

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
        return {"sows": [], "vendors": [], "people": [], "contracts": []}
    try:
        with open(f) as fp:
            d = json.load(fp)
            d.setdefault("sows", [])
            d.setdefault("vendors", [])
            d.setdefault("people", [])
            d.setdefault("contracts", [])
            for p in d["people"]:
                _migrate_person(p)
            return d
    except Exception:
        return {"sows": [], "vendors": [], "people": [], "contracts": []}


def _migrate_person(p):
    """v1 roster fields → the 3-axis schema (Client↔Cheil / Cheil↔Partner /
    Cheil employee) requested 2026-07-22."""
    if "sell_hr" not in p:
        p["sell_hr"] = p.pop("rate", "") or ""
        p["cost_hr"] = p.pop("vendor_cost", "") or ""
        p["role_title"] = p.pop("function", "") or ""
        p["salary_mo"] = p.pop("salary", "") or ""
        # Seeded emails were @samsung.com working addresses.
        em = p.pop("email", "") or ""
        p["email_samsung"] = em if "samsung" in em else ""
        p["email_cheil"] = em if "cheil" in em else ""
    for k in ("project", "sell_mo", "client_duration", "client_budget", "client_po",
              "cost_mo", "partner_duration", "partner_cost", "partner_po",
              "cheil_since", "salary_oh", "pc", "svpn", "ebita", "location"):
        p.setdefault(k, "")
    p.setdefault("linked_sows", [])
    return p


def _num_or_none(v):
    try:
        s = str(v).replace(",", "").replace("$", "").strip()
        return float(s) if s else None
    except (TypeError, ValueError):
        return None


def _person_ebita(p):
    """EBITA by Cheil — manual value wins; else Client budget − Partner cost
    (vendor personnel). Cheil-employee EBITA needs salary+OH × duration and
    stays manual until durations are numeric."""
    manual = _num_or_none(p.get("ebita"))
    if manual is not None:
        return manual, False
    budget = _num_or_none(p.get("client_budget"))
    cost = _num_or_none(p.get("partner_cost"))
    if budget is not None and cost is not None:
        return budget - cost, True
    return None, True


def _save(user, data):
    f = _data_path(user)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def _sow_type(sow):
    """Resolve a record's type key. Legacy team/role types collapse into the
    merged per-direction SOW type (the rate model lives on the record)."""
    t = sow.get("type")
    if t in TYPES:
        return t
    d = "agy" if sow.get("direction") == "agency" else "sea"
    return f"{d}_sow"


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
    overrides = sow.get("schedule_overrides") or {}
    rows = []
    for y, m, frac in spans:
        label = date(y, m, 1).strftime("%b-%y")
        amount = round(monthly * frac, 2)
        if label in overrides:
            try:
                amount = round(float(overrides[label]), 2)
            except (TypeError, ValueError):
                pass
        if rule == "month_end":
            inv = date(y, m, calendar.monthrange(y, m)[1])
        else:
            inv = date(y + 1, 1, 1) if m == 12 else date(y, m + 1, 1)
        rows.append({
            "label": label,
            "amount": amount,
            "invoice": inv.strftime("%-d-%b-%y"),
        })
    # months comes back exact; round only for display so per-line Cost stays
    # equal to the schedule total (a $-level mismatch reads as an error in a
    # finance document).
    return rows, round(sum(r["amount"] for r in rows), 2), sum(f for _, _, f in spans)


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

    # SEA SOWs open with a cover (head) page: Cheil logo + title + meta block,
    # then a page break into the legal preamble. Agency SOWs start directly.
    if not is_agency:
        logo = os.path.join(_ASSETS, "cheil_logo.png")
        if os.path.exists(logo):
            from docx.shared import Inches
            doc.add_picture(logo, width=Inches(3.2))
        p()
    p(sow.get("title") or sow.get("project_name") or "", bold=True, size=14)
    p("STATEMENT OF WORK", bold=True, size=13)
    p()
    p(f"DATE: {_fmt_long(sow.get('date'))}")
    p(f"CLIENT: {SAMSUNG_ENTITY if not is_agency else CHEIL_ENTITY}")
    p(f"PROJECT NAME: {sow.get('project_name') or ''}")
    p(f"PREPARED BY: {sow.get('prepared_by') or ''}")
    p(f"PREPARED FOR: {sow.get('prepared_for') or ''}")
    if not is_agency:
        doc.add_page_break()
    else:
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

    h("Resource Management" if not is_agency else "Resource Planning")
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
                r.get("profile") or "", r.get("location") or "", int(qty), round(months_total, 1),
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


def _replace_in_par(par, old, new):
    """Replace `old` with `new` across a paragraph's runs, splicing at run
    boundaries so surrounding formatting survives (docx runs split words)."""
    full = "".join(r.text for r in par.runs)
    idx = full.find(old)
    if idx < 0:
        return False
    end = idx + len(old)
    pos = 0
    for r in par.runs:
        r_start, r_end = pos, pos + len(r.text)
        if r_end <= idx or r_start >= end:
            pos = r_end
            continue
        keep_head = r.text[: max(0, idx - r_start)]
        keep_tail = r.text[max(0, min(len(r.text), end - r_start)):]
        if r_start <= idx:
            r.text = keep_head + new + keep_tail
        else:
            r.text = keep_tail
        pos = r_end
    return True


def _build_msa_docx(sow, vendor):
    """Fill the stored MSA template (executed-format docx) with the vendor
    name and effective date; every other clause exports byte-identical."""
    from docx import Document
    doc = Document(os.path.join(_ASSETS, "msa_template.docx"))
    reps = [
        ("XXX XX, 2026", _fmt_long(sow.get("date")) or "____________"),
        ("(Your Company Name)", (vendor or {}).get("name") or "____________________"),
    ]
    def walk(pars):
        for par in pars:
            for old, new in reps:
                while _replace_in_par(par, old, new):
                    pass
    walk(doc.paragraphs)
    for t in doc.tables:
        for row in t.rows:
            for c in row.cells:
                walk(c.paragraphs)
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


def _build_nda_docx(sow, vendor):
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt

    doc = Document()
    normal = doc.styles["Normal"]
    normal.font.name = "Times New Roman"
    normal.font.size = Pt(11)
    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.add_run(NDA_TITLE).bold = True
    doc.add_paragraph()
    doc.add_paragraph(NDA_INTRO.format(
        date=_fmt_long(sow.get("date")) or "____________",
        vendor=(vendor or {}).get("name") or "______________________",
    ))
    for par in NDA_BODY:
        doc.add_paragraph()
        doc.add_paragraph(par)
    doc.add_paragraph()
    sig = doc.add_table(rows=4, cols=2)
    sig.rows[0].cells[0].paragraphs[0].add_run(CHEIL_ENTITY).bold = True
    sig.rows[0].cells[1].paragraphs[0].add_run(
        (vendor or {}).get("name") or "[_____________________]").bold = True
    for i, lbl in enumerate(["By: _________________________", "Name:", "Title:"], 1):
        for c in range(2):
            sig.rows[i].cells[c].text = lbl
    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ── html shells ──────────────────────────────────────────────────────────────

def _esc(s):
    return (str(s or "").replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


_CSS = """
.sow-hero{display:grid;grid-template-columns:1fr 1fr;gap:16px;margin:20px 0 34px}
.dir-card{display:flex;flex-direction:column;gap:10px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-xl);padding:30px 28px;text-decoration:none;color:var(--text);transition:.2s;position:relative;overflow:hidden}
.dir-card::before{content:"";position:absolute;top:0;left:0;right:0;height:3px;background:var(--dir-color,var(--accent));opacity:.85}
.dir-card:hover{border-color:var(--dir-color,var(--accent));transform:translateY(-3px);box-shadow:var(--shadow-lg)}
.dir-icon{font-size:2.2rem}
.dir-name{font-size:1.15rem;font-weight:800;letter-spacing:-.02em}
.dir-desc{font-size:.82rem;color:var(--text-muted);line-height:1.5}
.type-grid{display:grid;grid-template-columns:1fr 1fr;gap:14px;margin:20px 0}
.type-card{display:flex;gap:14px;align-items:flex-start;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px;text-decoration:none;color:var(--text);transition:.2s}
.type-card:hover{border-color:var(--accent);transform:translateY(-2px);box-shadow:var(--shadow-md)}
.type-icon{font-size:1.6rem}
.type-name{font-weight:800;font-size:.95rem;margin-bottom:4px}
.type-desc{font-size:.78rem;color:var(--text-muted);line-height:1.5}
.sow-list{display:flex;flex-direction:column;gap:10px}
.sow-row{display:flex;align-items:center;gap:14px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:14px 18px;flex-wrap:wrap}
.sow-row:hover{border-color:var(--accent)}
.sow-title{font-weight:700;color:var(--text);font-size:.92rem}
.sow-meta{font-size:.76rem;color:var(--text-muted)}
.sow-fee{font-weight:700;color:var(--success);font-variant-numeric:tabular-nums;margin-left:auto}
.dir-chip{font-size:.64rem;font-weight:700;padding:2px 8px;border-radius:10px;white-space:nowrap}
.dir-samsung{color:#38bdf8;background:rgba(56,189,248,.12)}
.dir-agency{color:#fb923c;background:rgba(251,146,60,.12)}
/* ── document preview editor ── */
.doc-bar{position:sticky;top:52px;z-index:60;display:flex;align-items:center;gap:10px;background:var(--surface-3);border:1px solid var(--border-bright);border-radius:var(--radius-md);padding:10px 14px;margin-bottom:18px;flex-wrap:wrap}
.doc-bar .spacer{flex:1}
.paper{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:46px 52px;max-width:860px;margin:0 auto 60px;line-height:1.55;font-size:.9rem;color:var(--text)}
.paper h2{font-size:1.05rem;font-weight:800;margin:26px 0 8px}
.paper .doc-title{font-size:1.25rem;font-weight:800}
.paper .legal{color:var(--text-muted);font-size:.8rem;margin:10px 0}
.paper table{width:100%;border-collapse:collapse;margin:10px 0;font-size:.84rem}
.paper th{border:1px solid var(--border-bright);padding:7px 9px;font-size:.7rem;text-transform:uppercase;letter-spacing:.04em;color:var(--text-muted);text-align:left;background:var(--surface-2)}
.paper td{border:1px solid var(--border);padding:6px 9px}
.paper .num{text-align:right;font-variant-numeric:tabular-nums}
.slot{background:rgba(56,189,248,.07);border:none;border-bottom:1.5px dashed rgba(56,189,248,.55);border-radius:4px 4px 0 0;color:var(--text);font:inherit;padding:2px 6px;outline:none;min-width:60px}
.slot:focus{background:rgba(56,189,248,.14);border-bottom-color:var(--accent)}
textarea.slot{width:100%;border:1.5px dashed rgba(56,189,248,.45);border-radius:8px;padding:8px 10px;resize:vertical;line-height:1.5}
select.slot{cursor:pointer}
.paper td .slot{width:100%;min-width:0;padding:3px 5px}
.meta-line{display:flex;gap:8px;align-items:baseline;margin:2px 0}
.meta-line b{font-size:.8rem;letter-spacing:.03em;white-space:nowrap}
.ro-note{font-size:.68rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em;margin-top:26px}
.row-del{background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:.9rem;padding:4px 8px}
.row-del:hover{color:var(--danger)}
.add-row-btn{margin-top:6px}
/* ── side-by-side executed example ── */
.ed-wrap{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:18px;align-items:start;max-width:1760px;margin:0 auto}
.ed-wrap>.paper{margin:0 0 60px;max-width:none}
.ed-wrap.ex-hidden{grid-template-columns:minmax(0,1fr);max-width:900px}
.ed-wrap.ex-hidden .ex-col{display:none}
.ex-col{position:sticky;top:118px;max-height:calc(100vh - 140px);overflow-y:auto;border-radius:var(--radius-lg)}
.ex-paper{background:var(--surface);border:1px dashed var(--border-bright);border-radius:var(--radius-lg);padding:26px 30px;font-size:.8rem;line-height:1.55;color:var(--text-muted)}
.ex-paper h3{font-size:.85rem;font-weight:800;color:var(--text);margin:16px 0 4px}
.ex-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(52,211,153,.1);border:1px solid rgba(52,211,153,.3);color:var(--success);border-radius:99px;padding:3px 12px;font-size:.7rem;font-weight:700;margin-bottom:14px}
.ex-paper table{width:100%;border-collapse:collapse;margin:6px 0;font-size:.72rem}
.ex-paper th{border:1px solid var(--border);padding:4px 6px;font-size:.62rem;text-transform:uppercase;color:var(--text-muted);text-align:left;background:var(--surface-2)}
.ex-paper td{border:1px solid var(--border);padding:4px 6px}
.ex-paper ul{padding-left:18px;margin:4px 0}
.ex-paper li{margin-bottom:4px}
.ex-paper .num{text-align:right;font-variant-numeric:tabular-nums}
.ex-mark{background:rgba(56,189,248,.14);border-bottom:1.5px dashed rgba(56,189,248,.55);border-radius:3px;padding:0 3px;color:var(--text)}
@media(max-width:1100px){.ed-wrap{grid-template-columns:1fr}.ex-col{position:static;max-height:none;order:2}}
@media(max-width:768px){
  .sow-hero,.type-grid{grid-template-columns:1fr}
  .paper{padding:22px 16px}
  .doc-bar{top:0;position:static}
  .paper .table-wrap{overflow-x:auto}
  .paper .table-wrap table{min-width:620px}
  .sow-fee{margin-left:0;flex-basis:100%}
}
"""


def _shell(user, title, body, wide=False):
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>📝 {_esc(title)} · Wayfinder</title><link rel="stylesheet" href="/static/style.css">
<style>{_CSS}{_CTR_CSS}</style></head><body>
<nav><span class="nav-brand">📝 SOW Assistant</span>
<span class="nav-user">👤 {_esc(user)} &nbsp;·&nbsp; <a href="/logout">Logout</a></span></nav>
<div class="container" style="max-width:{'1800px' if wide else '1000px'}">{body}</div></body></html>"""


def _mk(v, field):
    """Highlighted fill-in value in the sample document — maps 1:1 to an
    editable slot in the template on the left."""
    return f'<mark class="ex-mark" title="Fill-in field: {_esc(field)}">{_esc(v)}</mark>'


def _render_example(type_key):
    ex = SAMPLES.get(type_key)
    if not ex:
        return ""
    head = f'<div class="ex-badge">📖 Executed document · {_esc(ex["src"])}</div>'
    if ex.get("note"):
        return ('<div class="ex-col"><div class="ex-paper">' + head +
                f'<p>{_esc(ex["note"])}</p></div></div>')

    is_agency = type_key.startswith("agy")
    p = []
    p.append(head)
    p.append('<div style="font-size:.66rem;color:var(--text-muted);text-transform:uppercase;'
             'letter-spacing:.06em;margin-bottom:14px">Highlighted = the fields you fill in on the left</div>')
    # ── cover / head ──
    if not is_agency:
        p.append('<img src="/sow/asset/logo" alt="Cheil" style="max-width:220px;background:#fff;'
                 'padding:8px 12px;border-radius:6px;margin-bottom:16px">')
    p.append(f'<div style="font-size:1.05rem;font-weight:800;color:var(--text)">{_mk(ex["title"], "Title")}</div>')
    p.append('<div style="font-weight:800;color:var(--text);margin:6px 0 12px">STATEMENT OF WORK</div>')
    p.append(f'<p><b>DATE:</b> {_mk(ex["date"], "SOW Date")}<br>'
             f'<b>CLIENT:</b> {_esc(CHEIL_ENTITY if is_agency else SAMSUNG_ENTITY)}<br>'
             f'<b>PROJECT NAME:</b> {_mk(ex["project"], "Project Name")}<br>'
             + (f'<b>PREPARED BY:</b> {_mk(ex["by"], "Prepared By")}<br>'
                f'<b>PREPARED FOR:</b> {_mk(ex["for"], "Prepared For")}' if ex.get("by") else "")
             + '</p>')
    if not is_agency:
        p.append('<div style="border-top:2px dashed var(--border-bright);margin:16px -30px;position:relative">'
                 '<span style="position:absolute;top:-8px;left:50%;transform:translateX(-50%);'
                 'background:var(--surface);padding:0 8px;font-size:.6rem;color:var(--text-muted);'
                 'text-transform:uppercase;letter-spacing:.08em">Page 2</span></div>')
    # ── preamble ──
    if is_agency:
        p.append("<p>" + _esc(PREAMBLE_AGENCY_1).replace("{sow_date}", _mk(ex["date"], "SOW Date"))
                 .replace("{vendor_entity}", _mk(ex["vendor_entity"], "Vendor entity line")) + "</p>")
        p.append("<p>" + _esc(PREAMBLE_AGENCY_2).replace("{msa_date}", _mk(ex["msa_date"], "Vendor MSA date")) + "</p>")
    else:
        p.append(f"<p>{_esc(PREAMBLE_SAMSUNG)}</p>")
    # ── summary / deliverables ──
    p.append(f'<h3>Executive Summary</h3><p>{_mk(ex["summary"], "Executive Summary")}</p>')
    p.append(f'<h3>{"Service Description" if is_agency else "Deliverables"}</h3><ul>'
             + "".join(f"<li>{_mk(d, 'Deliverables (one per line)')}</li>" for d in ex["deliverables"])
             + "</ul>")
    # ── stakeholders ──
    stk_head = (ex.get("vendor_name", "Contractor") + " POC") if is_agency else "Samsung Manager for this Role"
    labels = ["Name", "Email", "Location"]
    stk_rows = "".join(
        f"<tr><td><b>{labels[i]}</b></td><td>{_mk(row[0], 'Stakeholder') if row[0] else ''}</td>"
        f"<td>{_mk(row[1], 'Stakeholder') if row[1] else ''}</td></tr>"
        for i, row in enumerate(ex["stk"]))
    p.append(f'<h3>Project Stakeholders</h3><div style="overflow-x:auto"><table>'
             f'<tr><th></th><th>{_esc(stk_head)}</th><th>Cheil Project Management &amp; SOW Owner</th></tr>'
             f'{stk_rows}</table></div>')
    # ── period ──
    p.append(f'<h3>Service Period</h3><p>Start Date : {_mk(ex["start"], "Start Date")}<br>'
             f'End Date : {_mk(ex["end"], "End Date")}</p>')
    # ── resources ──
    payer = "Cheil shall pay Contractor" if is_agency else "Samsung shall pay Cheil"
    p.append(f'<h3>{"Resource Planning" if is_agency else "Resource Management"}</h3>'
             f'<p>In consideration for the provision of the Services and Deliverables under this SOW, '
             f'{payer} in accordance with the following rates and fees, subject to the applicable '
             f'terms and conditions of the Agreement:</p>')
    res_head = ["Profile", "Location", "Qty", "# Months", "Hourly", "Hrs/Mo", "Cost"]
    res_rows = "".join("<tr>" + "".join(f"<td>{_mk(c, 'Resources table')}</td>" for c in r) + "</tr>"
                       for r in ex["res_rows"])
    p.append('<div style="overflow-x:auto"><table><tr>'
             + "".join(f"<th>{h}</th>" for h in res_head) + f"</tr>{res_rows}</table></div>")
    # ── payment ──
    p.append(f'<h3>Cost and Payment Schedule</h3><p><b>Fee : {_mk(ex["fee"], "auto-computed Fee")}</b></p>')
    p.append(f"<p>{_esc(PAYMENT_INTRO_AGENCY if is_agency else PAYMENT_INTRO)}</p>")
    sched_rows = "".join(
        f"<tr><td>{_esc(r[0])}</td><td class=\"num\">{_mk(r[1], 'Monthly amount (auto, editable)')}</td>"
        f"<td>{_esc(r[2])}</td></tr>" for r in ex["schedule"])
    p.append('<div style="overflow-x:auto"><table><tr><th>Month</th><th>Amount</th><th>Invoice Date</th></tr>'
             + sched_rows + f'<tr><td><b>Total</b></td><td class="num"><b>{_mk(ex["fee"], "Total")}</b></td><td></td></tr></table></div>')
    p.append(f"<p>{_esc(CHANGE_ORDER_NOTE)}</p>")
    # ── OOP + signatures ──
    p.append("<h3>Out-of-pocket Expense</h3>" + "".join(
        f"<p>{_esc(par)}</p>" for par in (OOP_AGENCY if is_agency else OOP_SAMSUNG).split("\n\n")))
    left = CHEIL_ENTITY if is_agency else SAMSUNG_ENTITY
    right = ex.get("vendor_name", CHEIL_ENTITY) if is_agency else CHEIL_ENTITY
    p.append('<h3>Signatures</h3><p>IN WITNESS WHEREOF, the parties have caused this Statement of Work '
             'to be duly executed by their authorized representatives as set forth below.</p>'
             f'<div style="overflow-x:auto"><table><tr><th>{_esc(left)}</th><th>{_mk(right, "Counterpart") if is_agency else _esc(right)}</th></tr>'
             '<tr><td>Signature: ______________</td><td>Signature: ______________</td></tr>'
             '<tr><td>Name / Title / Date</td><td>Name / Title / Date</td></tr></table></div>')
    return '<div class="ex-col"><div class="ex-paper">' + "".join(p) + "</div></div>"


_EX_TOGGLE_JS = """<script>
(function(){
  var w = document.getElementById('edWrap'), b = document.getElementById('exToggle');
  if(!w || !b) return;
  function apply(off){
    w.classList.toggle('ex-hidden', off);
    b.classList.toggle('btn-ghost', off);
    b.classList.toggle('btn-secondary', !off);
  }
  var off = localStorage.getItem('sowExampleOff') === '1';
  apply(off);
  b.addEventListener('click', function(){
    off = !off;
    localStorage.setItem('sowExampleOff', off ? '1' : '0');
    apply(off);
  });
})();
</script>"""


def _sow_rows(user, data):
    rows = []
    for s in sorted(data["sows"], key=lambda x: x.get("updated", ""), reverse=True):
        t = TYPES[_sow_type(s)]
        if t["kind"] == "sow":
            _, fee, _ = _build_schedule(s)
            fee = _money(fee)
        elif t["kind"] == "est":
            _, _, tot, _ = _est_rows_computed(s)
            fee = _money(tot)
        else:
            fee = "—"
        d = s.get("direction", "samsung")
        chip = f'<span class="dir-chip dir-{d}">{"SEA" if d == "samsung" else "Agency"} · {_esc(t["label"])}</span>'
        rows.append(
            f'<div class="sow-row">'
            f'<div><div class="sow-title">{_esc(s.get("title") or s.get("project_name") or "(untitled)")}</div>'
            f'<div class="sow-meta">{chip} &nbsp;{_esc(s.get("start") or s.get("date") or "")}{(" ~ " + _esc(s.get("end"))) if s.get("end") else ""}</div></div>'
            f'<span class="sow-fee">{fee}</span>'
            f'<span style="display:flex;gap:8px">'
            f'<a class="btn btn-secondary btn-sm" href="/sow/edit?id={s["id"]}">✎ Edit</a>'
            f'<a class="btn btn-primary btn-sm" href="/sow/docx?id={s["id"]}">⬇ docx</a>'
            f'<button class="btn btn-danger btn-sm" onclick="delSow(\'{s["id"]}\')">🗑</button>'
            f'</span></div>'
        )
    return "".join(rows)


_DEL_JS = """<script>
function delSow(id){
  if(!confirm('Delete this SOW?')) return;
  fetch('/sow/delete', {method:'POST', headers:{'Content-Type':'application/x-www-form-urlencoded'}, body:'id='+encodeURIComponent(id)})
    .then(function(){ location.reload(); });
}
</script>"""


def _render_landing(user):
    data = _load(user)
    rows = _sow_rows(user, data)
    contracts = _render_contracts_section(user, data)
    body = f"""
<h1 style="margin:8px 0 4px">Statements of Work</h1>
<p style="color:var(--text-muted);font-size:.86rem;margin-bottom:6px">Who is this SOW with?</p>
<div class="sow-hero">
  <a class="dir-card" href="/sow/types?dir=sea" style="--dir-color:#38bdf8">
    <span class="dir-icon">🔵</span>
    <span class="dir-name">with Samsung (SEA)</span>
    <span class="dir-desc">Cheil as Agency — inbound SOW under the Advertising Services Agreement (Sep 16, 2022). Samsung pays Cheil.</span>
  </a>
  <a class="dir-card" href="/sow/types?dir=agy" style="--dir-color:#fb923c">
    <span class="dir-icon">🟠</span>
    <span class="dir-name">with Agency (Vendor)</span>
    <span class="dir-desc">Cheil as Client — outbound SOW under each vendor's MSA. Cheil pays the contractor.</span>
  </a>
</div>
<div style="display:flex;align-items:center;justify-content:space-between;margin:0 0 12px">
  <h2 style="font-size:1rem;font-weight:800;margin:0">My Documents</h2>
  <span style="display:flex;gap:8px">
    <a class="btn btn-secondary btn-sm" href="/sow/people">👥 People</a>
    <a class="btn btn-secondary btn-sm" href="/sow/vendors">🏢 Vendors</a>
  </span>
</div>
<div class="sow-list">{rows or '<div class="sow-meta" style="padding:36px;text-align:center">No SOWs yet — pick a counterpart above to start.</div>'}</div>
{contracts}
<div class="cmodal-ov" id="cmodalOv"><div class="cmodal" id="cmodal"></div></div>
{_DEL_JS}
{_CTR_JS}"""
    return _shell(user, "SOW Assistant", body)


def _person_docs(data, person):
    """Documents tied to this person: explicit links + auto-detected
    (estimate rows by person_id, SOW resource rows by name)."""
    linked = set(person.get("linked_sows") or [])
    auto = set()
    pname = (person.get("name") or "").strip().lower()
    for s in data["sows"]:
        kind = TYPES.get(_sow_type(s), {}).get("kind")
        if kind == "est":
            if any(r.get("person_id") == person["id"] for r in s.get("rows", [])):
                auto.add(s["id"])
        elif kind == "sow":
            for r in s.get("resources", []):
                nm = (r.get("profile") or r.get("name") or "").strip().lower()
                if pname and nm == pname:
                    auto.add(s["id"])
                    break
    ids = linked | auto
    return [s for s in data["sows"] if s["id"] in ids], auto


def _person_doc_count(data, person):
    docs, _ = _person_docs(data, person)
    return len(docs)


def _fmt_money_cell(v):
    n = _num_or_none(v)
    return _money(n) if n is not None else (_esc(v) if v else "–")


def _render_people(user, saved=False):
    """Excel-style summary grid (강프로 2026-07-22): one row per person, the
    3 money axes as banded column groups, first column pinned, horizontal
    scroll inside the wrapper per the design-system reference-table rule."""
    data = _load(user)

    def mo_auto(hr_v, mo_v):
        if mo_v:
            return _fmt_money_cell(mo_v)
        n = _num_or_none(hr_v)
        return f"${n * 168:,.0f}" if n is not None else "–"

    rows = []
    for p in data["people"]:
        docs, _ = _person_docs(data, p)
        ebita, ebita_auto = _person_ebita(p)
        aff = p.get("affiliation") or "Cheil"
        aff_chip = (f'<span class="dir-chip dir-samsung">{_esc(aff)}</span>' if aff == "Cheil"
                    else f'<span class="dir-chip dir-agency">{_esc(aff)}</span>')
        if ebita is not None:
            col = "var(--success)" if ebita >= 0 else "var(--danger)"
            ebita_html = (f'<span style="color:{col};font-weight:700">{_money(ebita)}</span>'
                          + ('<span style="font-size:.6rem;color:var(--text-muted)"> a</span>' if ebita_auto else ''))
        else:
            ebita_html = "–"
        doc_html = (f'<a href="/sow/person?id={p["id"]}" style="color:var(--accent);text-decoration:none">'
                    f'{len(docs)} 📄</a>' if docs else "–")
        rows.append(
            '<tr>'
            f'<td class="pp-pin"><a href="/sow/person?id={p["id"]}" style="font-weight:700;color:var(--text);text-decoration:none">{_esc(p.get("name"))}</a><br>{aff_chip}</td>'
            f'<td>{_esc(p.get("project") or "–")}</td>'
            f'<td>{_esc(p.get("role_title") or "–")}</td>'
            f'<td class="num">{_fmt_money_cell(p.get("sell_hr"))}</td>'
            f'<td class="num">{mo_auto(p.get("sell_hr"), p.get("sell_mo"))}</td>'
            f'<td>{_esc(p.get("client_duration") or "–")}</td>'
            f'<td class="num">{_fmt_money_cell(p.get("client_budget"))}</td>'
            f'<td>{_esc(p.get("client_po") or "–")}</td>'
            f'<td class="num">{_fmt_money_cell(p.get("cost_hr"))}</td>'
            f'<td class="num">{mo_auto(p.get("cost_hr"), p.get("cost_mo"))}</td>'
            f'<td>{_esc(p.get("partner_duration") or "–")}</td>'
            f'<td class="num">{_fmt_money_cell(p.get("partner_cost"))}</td>'
            f'<td>{_esc(p.get("partner_po") or "–")}</td>'
            f'<td class="num">{_fmt_money_cell(p.get("salary_mo"))}</td>'
            f'<td>{_esc(p.get("cheil_since") or "–")}</td>'
            f'<td class="num">{_fmt_money_cell(p.get("salary_oh"))}</td>'
            f'<td class="num">{ebita_html}</td>'
            f'<td style="text-align:center">{doc_html}</td>'
            '</tr>')

    saved_banner = ('<div style="color:var(--success);font-size:.85rem;margin-bottom:12px">✓ Saved</div>'
                    if saved else "")
    body = f"""
<style>
.pp-wrap{{overflow-x:auto;overscroll-behavior-x:contain;border:1px solid var(--border);border-radius:var(--radius-lg);background:var(--surface)}}
.pp-table{{border-collapse:collapse;font-size:.8rem;min-width:1750px;width:100%}}
.pp-table th{{border:1px solid var(--border);padding:6px 9px;font-size:.62rem;text-transform:uppercase;letter-spacing:.04em;color:var(--text-muted);background:var(--surface-2);text-align:left;white-space:nowrap}}
.pp-table th.grp{{text-align:center;font-weight:800;color:var(--text)}}
.pp-table th.g-sell{{background:rgba(56,189,248,.10)}}
.pp-table th.g-cost{{background:rgba(251,146,60,.10)}}
.pp-table th.g-emp{{background:rgba(52,211,153,.10)}}
.pp-table th.g-ebita{{background:rgba(129,140,248,.12)}}
.pp-table td{{border:1px solid var(--border);padding:7px 9px;white-space:nowrap}}
.pp-table td.num{{text-align:right;font-variant-numeric:tabular-nums}}
.pp-table .pp-pin,.pp-table th:first-child{{position:sticky;left:0;background:var(--surface);z-index:2;min-width:150px;box-shadow:2px 0 6px rgba(0,0,0,.25)}}
.pp-table thead th:first-child{{background:var(--surface-2);z-index:3}}
.pp-table tbody tr:hover td{{background:var(--surface-2)}}
.pp-table tbody tr:hover td.pp-pin{{background:var(--surface-2)}}
</style>
<div style="display:flex;align-items:center;gap:12px;margin:8px 0 4px">
  <a class="btn btn-ghost btn-sm" href="/sow">←</a>
  <h1 style="margin:0">👥 People</h1>
  <span style="flex:1"></span>
  <a class="btn btn-primary btn-sm" href="/sow/person">+ Add person</a>
</div>
<p style="color:var(--text-muted);font-size:.86rem">One row per person — selling side, cost side, employee comp and EBITA in one sweep (scroll sideways; the name column stays pinned). Click a name for the full profile and linked SOWs.</p>
{saved_banner}
<div class="pp-wrap"><table class="pp-table">
  <thead>
    <tr>
      <th rowspan="2">Name / 소속</th><th rowspan="2">Project / SOW</th><th rowspan="2">Role · Title</th>
      <th class="grp g-sell" colspan="5">Client → Cheil</th>
      <th class="grp g-cost" colspan="5">Cheil → Partner</th>
      <th class="grp g-emp" colspan="3">Cheil employee</th>
      <th class="grp g-ebita" rowspan="2">EBITA<br>by Cheil</th>
      <th rowspan="2">Docs</th>
    </tr>
    <tr>
      <th class="g-sell">Selling/hr</th><th class="g-sell">Selling/mo</th><th class="g-sell">Duration</th><th class="g-sell">Budget</th><th class="g-sell">PO</th>
      <th class="g-cost">Contract/hr</th><th class="g-cost">Contract/mo</th><th class="g-cost">Duration</th><th class="g-cost">Cost</th><th class="g-cost">PO</th>
      <th class="g-emp">Salary/mo</th><th class="g-emp">Since</th><th class="g-emp">Salary+OH</th>
    </tr>
  </thead>
  <tbody>{''.join(rows) or '<tr><td colspan="19" style="text-align:center;padding:30px;color:var(--text-muted)">No people yet.</td></tr>'}</tbody>
</table></div>"""
    return _shell(user, "People", body, wide=True)


def _render_person_detail(user, person, saved=False):
    data = _load(user)
    p = person or {}
    docs, auto_ids = _person_docs(data, p) if p.get("id") else ([], set())
    vend_names = [v["name"] for v in data["vendors"]]
    aff_opts = ["Cheil"] + vend_names + ["TBD"]
    cur_aff = p.get("affiliation") or "Cheil"
    if cur_aff not in aff_opts:
        aff_opts.append(cur_aff)
    aff_sel = "".join(f'<option{" selected" if a == cur_aff else ""}>{_esc(a)}</option>' for a in aff_opts)

    def fld(label, name, ph="", typ="text", wide=False):
        return (f'<div class="f-cell{" f-wide" if wide else ""}">'
                f'<div style="font-size:.64rem;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted);margin-bottom:3px">{label}</div>'
                f'<input class="slot" style="width:100%" type="{typ}" name="{name}" value="{_esc(p.get(name))}" placeholder="{_esc(ph)}"></div>')

    ebita, ebita_auto = _person_ebita(p)
    ebita_hint = (f'auto = Client budget − Partner cost = {_money(ebita)}'
                  if (ebita is not None and ebita_auto) else 'auto needs Client budget + Partner cost — or type a value')

    # linked docs: explicit links are checkboxes over every SOW/estimate doc;
    # auto-detected ones are pre-noted.
    doc_opts = []
    linked = set(p.get("linked_sows") or [])
    for s in sorted(data["sows"], key=lambda x: x.get("updated", ""), reverse=True):
        k = TYPES.get(_sow_type(s), {})
        if k.get("kind") not in ("sow", "est"):
            continue
        checked = " checked" if s["id"] in linked else ""
        auto = ' <span style="font-size:.64rem;color:var(--success)">auto-linked</span>' if s["id"] in auto_ids else ""
        doc_opts.append(
            f'<label style="display:flex;align-items:center;gap:8px;padding:5px 0;font-size:.82rem;cursor:pointer">'
            f'<input type="checkbox" name="linked_sows" value="{s["id"]}"{checked}>'
            f'{k.get("icon","")} {_esc(s.get("title") or "(untitled)")}'
            f'<span style="color:var(--text-muted);font-size:.72rem">{_esc(s.get("start") or "")}{(" ~ " + _esc(s.get("end"))) if s.get("end") else ""}</span>'
            f'{auto}'
            f'<a href="/sow/edit?id={s["id"]}" style="margin-left:auto;color:var(--accent);font-size:.74rem;text-decoration:none">open →</a></label>')

    saved_banner = ('<div style="color:var(--success);font-size:.85rem;margin-bottom:12px">✓ Saved</div>'
                    if saved else "")
    body = f"""
<div style="display:flex;align-items:center;gap:12px;margin:8px 0 16px">
  <a class="btn btn-ghost btn-sm" href="/sow/people">←</a>
  <h1 style="margin:0">{_esc(p.get('name') or 'New person')}</h1>
</div>
{saved_banner}
<form method="post" action="/sow/person/save">
<input type="hidden" name="id" value="{_esc(p.get('id') or '')}">
<style>.f-grid3{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}}.f-wide{{grid-column:1/-1}}</style>

<div class="sow-card">
  <div class="sec-title" style="font-size:.8rem;font-weight:800;margin-bottom:12px">Basics</div>
  <div class="f-grid3">
    {fld('Name', 'name', 'required')}
    <div class="f-cell"><div style="font-size:.64rem;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted);margin-bottom:3px">소속</div>
      <select class="slot" style="width:100%" name="affiliation">{aff_sel}</select></div>
    {fld('Role / Title', 'role_title', 'e.g. Sr. Developer')}
    {fld('투입 프로젝트 / SOW', 'project', 'e.g. AEM Bridge 2', wide=True)}
    {fld('Location', 'location', 'US / India')}
  </div>
</div>

<div class="sow-card">
  <div class="sec-title" style="font-size:.8rem;font-weight:800;margin-bottom:12px">Client → Cheil <span style="font-weight:500;color:var(--text-muted)">(selling side)</span></div>
  <div class="f-grid3">
    {fld('Selling Rate (hr)', 'sell_hr', '$/h')}
    {fld('Selling Rate (Mo)', 'sell_mo', 'auto: hr × 168')}
    {fld('Client–Cheil Duration', 'client_duration', 'e.g. Apr – Oct 2026')}
    {fld('Contracted Budget', 'client_budget', '$')}
    {fld('Client–Cheil PO', 'client_po', 'PO #')}
  </div>
</div>

<div class="sow-card">
  <div class="sec-title" style="font-size:.8rem;font-weight:800;margin-bottom:12px">Cheil → Partner <span style="font-weight:500;color:var(--text-muted)">(cost side, vendor personnel)</span></div>
  <div class="f-grid3">
    {fld('Contract Rate (hr)', 'cost_hr', '$/h')}
    {fld('Contract Rate (Mo)', 'cost_mo', 'auto: hr × 168')}
    {fld('Cheil–Partner Duration', 'partner_duration')}
    {fld('Contracted Cost', 'partner_cost', '$')}
    {fld('Cheil–Partner PO (if any)', 'partner_po')}
  </div>
</div>

<div class="sow-card">
  <div class="sec-title" style="font-size:.8rem;font-weight:800;margin-bottom:12px">Cheil employee</div>
  <div class="f-grid3">
    {fld('Salary (Mo)', 'salary_mo', '$')}
    {fld('Cheil Since', 'cheil_since', 'e.g. 2024-03')}
    {fld('Cheil Salary + OH', 'salary_oh', '$')}
  </div>
</div>

<div class="sow-card">
  <div class="sec-title" style="font-size:.8rem;font-weight:800;margin-bottom:12px">EBITA by Cheil</div>
  <div class="f-grid3">
    {fld('EBITA (manual override)', 'ebita', ebita_hint)}
  </div>
</div>

<div class="sow-card">
  <div class="sec-title" style="font-size:.8rem;font-weight:800;margin-bottom:12px">Accounts &amp; equipment</div>
  <div class="f-grid3">
    {fld('Cheil.com Email', 'email_cheil')}
    {fld('Samsung.com Email', 'email_samsung')}
    {fld('PC', 'pc', 'asset / model')}
    {fld('SVPN', 'svpn', 'account / status')}
  </div>
</div>

<div class="sow-card">
  <div class="sec-title" style="font-size:.8rem;font-weight:800;margin-bottom:12px">Linked SOWs &amp; estimates</div>
  {''.join(doc_opts) or '<div style="font-size:.8rem;color:var(--text-muted)">No documents yet.</div>'}
</div>

<div style="display:flex;gap:10px;margin:16px 0 40px">
  <button type="submit" class="btn btn-primary btn-lg">💾 Save</button>
  {f'<button type="button" class="btn btn-danger" onclick="delPerson()">🗑 Delete</button>' if p.get('id') and not docs else ''}
</div>
</form>
<script>
function delPerson(){{
  if(!confirm('Delete this person from the roster?')) return;
  fetch('/sow/person/delete', {{method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}}, body:'id={_esc(p.get("id") or "")}'}})
    .then(function(){{ location.href = '/sow/people'; }});
}}
</script>"""
    return _shell(user, p.get("name") or "New person", body)


def _est_rows_computed(sow):
    """Per-row computed figures + totals for an estimate document."""
    months = float(sow.get("months") or 0)
    out, tot_monthly, tot_total, tot_cost = [], 0.0, 0.0, 0.0
    for r in sow.get("rows", []):
        rate = float(r.get("rate") or 0)
        alloc = float(r.get("alloc") or 1)
        monthly = rate * 168
        mcost = monthly * alloc
        total = mcost * months
        vc = float(r.get("vendor_cost") or 0)
        out.append({**r, "monthly": monthly, "monthly_cost": mcost, "total": total})
        tot_monthly += mcost
        tot_total += total
        tot_cost += vc * 168 * alloc * months
    return out, round(tot_monthly, 2), round(tot_total, 2), round(tot_cost, 2)


def _build_est_xlsx(sow):
    """Estimation workbook in the executed 'Cost Estimation' layout:
    Resource | Function | Email ID | Location | Rate | Monthly | Allocation |
    Monthly Cost | <period total> — with the totals row at the bottom."""
    import openpyxl
    from openpyxl.styles import Font, Alignment, Border, Side

    rows, tot_monthly, tot_total, _ = _est_rows_computed(sow)
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Cost Estimation"
    period = sow.get("period_label") or f"{sow.get('months') or 0} months (Total)"
    headers = ["", "Resource", "Function", "Email ID", "Location", "Rate",
               "Monthly", "Allocation", "Monthly Cost", period]
    thin = Border(bottom=Side(style="thin", color="CCCCCC"))
    ws.append([])
    ws.append(headers)
    for c in ws[2]:
        c.font = Font(bold=True)
        c.border = thin
    for r in rows:
        ws.append(["", r.get("name") or "", r.get("function") or "",
                   r.get("email") or "", r.get("location") or "",
                   float(r.get("rate") or 0), r["monthly"],
                   float(r.get("alloc") or 1), r["monthly_cost"], r["total"]])
    ws.append(["", "", "", "", "", "", "", "", tot_monthly, tot_total])
    for c in ws[ws.max_row]:
        c.font = Font(bold=True)
    widths = [3, 22, 10, 26, 10, 8, 10, 11, 13, 16]
    for i, w in enumerate(widths, 1):
        ws.column_dimensions[openpyxl.utils.get_column_letter(i)].width = w
    for col in ("F", "G", "I", "J"):
        for cell in ws[col]:
            cell.number_format = "#,##0"
            cell.alignment = Alignment(horizontal="right")
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


_EST_JS = """<script>
var EROWS = __ROWS__;
var CFG = __CFG__;
function $id(x){ return document.getElementById(x); }
function money(x){
  if(isNaN(x)) return '$0';
  var r = Math.round(x*100)/100;
  return '$' + (Math.abs(r-Math.round(r))<0.005 ? Math.round(r).toLocaleString('en-US')
              : r.toLocaleString('en-US', {minimumFractionDigits:2}));
}
function months(){ return parseFloat($id('fMonths').value) || 0; }
function renderRows(){
  var tb = $id('estBody'); tb.innerHTML = '';
  EROWS.forEach(function(r, i){
    var tr = document.createElement('tr');
    var opts = '<option value="">— pick —</option>' + CFG.people.map(function(p){
      return '<option value="' + p.id + '"' + (r.person_id === p.id ? ' selected' : '') + '>' + p.name + '</option>';
    }).join('');
    tr.innerHTML =
      '<td><select class="slot" data-k="person_id" data-i="' + i + '">' + opts + '</select></td>'
      + cell(r,'function',i) + cell(r,'location',i) + cell(r,'rate',i)
      + '<td class="num c-monthly"></td>' + cell(r,'alloc',i)
      + '<td class="num c-mcost"></td><td class="num c-total"></td>'
      + '<td style="border:none"><button type="button" class="row-del" onclick="rmRow('+i+')">✕</button></td>';
    tb.appendChild(tr);
  });
  paint();
}
function cell(r, k, i){
  var v = r[k] != null ? String(r[k]).replace(/"/g,'&quot;') : '';
  return '<td><input class="slot" data-k="'+k+'" data-i="'+i+'" value="'+v+'"></td>';
}
function paint(){
  var m = months(), totM = 0, totT = 0, totC = 0, anyVc = false;
  document.querySelectorAll('#estBody tr').forEach(function(tr, i){
    var r = EROWS[i] || {};
    var monthly = (parseFloat(r.rate)||0)*168;
    var mcost = monthly*(parseFloat(r.alloc)||1);
    var total = mcost*m;
    totM += mcost; totT += total;
    var vc = parseFloat(r.vendor_cost)||0;
    if(vc){ anyVc = true; totC += vc*168*(parseFloat(r.alloc)||1)*m; }
    tr.querySelector('.c-monthly').textContent = money(monthly);
    tr.querySelector('.c-mcost').textContent = money(mcost);
    tr.querySelector('.c-total').textContent = money(total);
  });
  $id('totMonthly').textContent = money(totM);
  $id('totTotal').textContent = money(totT);
  var mg = $id('marginLine');
  if(anyVc && totT){
    mg.style.display = '';
    mg.textContent = 'internal cost ' + money(totC) + ' \\u00b7 margin ' + money(totT - totC)
      + ' (' + Math.round((totT - totC)/totT*100) + '%)';
  } else mg.style.display = 'none';
}
function addRow(){ EROWS.push({alloc: 1}); renderRows(); }
function rmRow(i){ EROWS.splice(i,1); renderRows(); }
document.addEventListener('input', function(e){
  var k = e.target.dataset && e.target.dataset.k;
  if(!k) { if(e.target.id === 'fMonths') paint(); return; }
  EROWS[parseInt(e.target.dataset.i)][k] = e.target.value;
  paint();
});
document.addEventListener('change', function(e){
  if(e.target.dataset && e.target.dataset.k === 'person_id'){
    var i = parseInt(e.target.dataset.i);
    var p = CFG.people.find(function(x){ return x.id === e.target.value; });
    if(p){
      EROWS[i] = {person_id: p.id, name: p.name, function: p.function, email: p.email,
                  location: p.location, rate: p.rate, vendor_cost: p.vendor_cost,
                  alloc: EROWS[i].alloc || 1};
      renderRows();
    }
  }
});
document.getElementById('sowForm').addEventListener('submit', function(){
  $id('rowsJson').value = JSON.stringify(EROWS.filter(function(r){
    return r.person_id || String(r.rate||'').trim();
  }));
});
if(!EROWS.length) EROWS.push({alloc: 1});
renderRows();
</script>"""


def _render_est_editor(user, sow, type_key, saved=False):
    data = _load(user)
    t = TYPES[type_key]
    saved_note = ('<span style="color:var(--success);font-size:.8rem;font-weight:700">✓ Saved</span>'
                  if saved else "")
    people = [{"id": p["id"], "name": p.get("name") or "", "function": p.get("role_title") or "",
               "email": p.get("email_samsung") or p.get("email_cheil") or "",
               "location": p.get("location") or "",
               "rate": p.get("sell_hr") or "", "vendor_cost": p.get("cost_hr") or ""}
              for p in data["people"]]
    cfg = {"people": people}
    body = f"""
<form method="post" action="/sow/save" id="sowForm">
<input type="hidden" name="id" value="{_esc(sow.get('id') or '')}">
<input type="hidden" name="type" value="{type_key}">
<input type="hidden" name="rows_json" id="rowsJson">
<div class="doc-bar">
  <a class="btn btn-ghost btn-sm" href="/sow" title="All documents">←</a>
  <span class="dir-chip dir-samsung">SEA</span>
  <span style="font-size:.82rem;font-weight:700">🧮 Cost Estimation</span>
  <a class="btn btn-ghost btn-sm" href="/sow/people">👥 People</a>
  <span class="spacer"></span>
  {saved_note}
  {f'<a class="btn btn-secondary btn-sm" href="/sow/xlsx?id={sow["id"]}">⬇ xlsx</a>' if sow.get('id') else ''}
  <button type="submit" class="btn btn-primary btn-sm">💾 Save</button>
</div>
<div class="paper" style="max-width:1200px">
  <div class="doc-title">{_slot('title', sow.get('title'), 'Estimation title — e.g. AEM Bridge 2', 'style="width:100%;font-weight:800;font-size:1.15rem"')}</div>
  <div style="font-weight:800;margin:8px 0 18px">COST ESTIMATION</div>
  <div class="meta-line"><b>PROJECT:</b> {_slot('project_name', sow.get('project_name'), 'project', 'style="flex:1"')}</div>
  <div class="meta-line"><b>PERIOD:</b> {_slot('period_label', sow.get('period_label'), 'e.g. From Aug til Dec (Total)')}
    <b style="margin-left:14px"># MONTHS:</b> <input class="slot" type="number" step="0.1" min="0" name="months" id="fMonths" value="{_esc(sow.get('months') or 5)}" style="width:80px"></div>

  <h2>Resources <span style="font-size:.7rem;color:var(--text-muted);font-weight:500">Monthly = rate × 168h · Monthly Cost = Monthly × allocation · Total = Monthly Cost × months</span></h2>
  <div class="table-wrap"><table>
    <thead><tr><th>Resource</th><th>Function</th><th>Location</th><th>Rate/h</th><th>Monthly</th><th>Allocation</th><th>Monthly Cost</th><th>Total</th><th style="border:none"></th></tr></thead>
    <tbody id="estBody"></tbody>
    <tfoot><tr><td colspan="6" style="text-align:right"><b>Totals</b></td><td class="num"><b id="totMonthly">$0</b></td><td class="num"><b id="totTotal">$0</b></td><td style="border:none"></td></tr></tfoot>
  </table></div>
  <button type="button" class="btn btn-ghost btn-sm add-row-btn" onclick="addRow()">+ Add resource</button>
  <div id="marginLine" style="display:none;margin-top:10px;font-size:.76rem;color:var(--text-muted)"></div>
  <div class="ro-note">Pick people from the roster — rate/function auto-fill (editable per row). Figures recompute live.</div>
</div>
</form>
""" + _EST_JS.replace("__ROWS__", json.dumps(sow.get("rows", [])).replace("</", "<\\/")) \
             .replace("__CFG__", json.dumps(cfg).replace("</", "<\\/")) + _EX_TOGGLE_JS
    return _shell(user, "Cost Estimation", body, wide=True)


def _render_vendors(user, saved=False):
    data = _load(user)
    counts = {}
    for s in data["sows"]:
        vid = s.get("vendor_id")
        if vid:
            counts[vid] = counts.get(vid, 0) + 1
    rows = []
    for v in data["vendors"]:
        n = counts.get(v["id"], 0)
        del_btn = (f'<button type="button" class="btn btn-danger btn-sm" onclick="delVendor(\'{v["id"]}\')">🗑</button>'
                   if n == 0 else
                   f'<span style="font-size:.72rem;color:var(--text-muted)" title="Referenced by {n} document(s) — delete those first">{n} doc(s)</span>')
        rows.append(f"""
<form method="post" action="/sow/vendor/save" class="sow-card" style="display:grid;grid-template-columns:1fr 2fr 150px auto auto;gap:10px;align-items:center;padding:14px 18px">
  <input type="hidden" name="id" value="{v['id']}">
  <input class="slot" name="name" value="{_esc(v.get('name'))}" placeholder="Vendor name">
  <input class="slot" name="entity_line" value="{_esc(v.get('entity_line'))}" placeholder="Entity line (name + address, used in the SOW/MSA preamble)">
  <input class="slot" type="date" name="msa_date" value="{_esc(v.get('msa_date'))}" title="MSA date">
  <button type="submit" class="btn btn-secondary btn-sm">💾 Save</button>
  {del_btn}
</form>""")
    saved_banner = ('<div style="color:var(--success);font-size:.85rem;margin-bottom:12px">✓ Saved</div>'
                    if saved else "")
    body = f"""
<div style="display:flex;align-items:center;gap:12px;margin:8px 0 4px">
  <a class="btn btn-ghost btn-sm" href="/sow">←</a>
  <h1 style="margin:0">🏢 Vendors</h1>
</div>
<p style="color:var(--text-muted);font-size:.86rem">One row per contractor — name, the entity line that lands in document preambles, and the MSA date. Referenced by Agency-side SOWs, MSAs and NDAs.</p>
{saved_banner}
<form method="post" action="/sow/vendor/save" class="sow-card" style="display:grid;grid-template-columns:1fr 2fr 150px auto;gap:10px;align-items:center;padding:14px 18px;border-style:dashed">
  <input class="slot" name="name" placeholder="+ New vendor name — e.g. Invictus Data, Inc." required>
  <input class="slot" name="entity_line" placeholder="Entity line — Invictus Data Inc, with its principal place of business located at ...">
  <input class="slot" type="date" name="msa_date" title="MSA date">
  <button type="submit" class="btn btn-primary btn-sm">+ Add</button>
</form>
<div style="display:flex;flex-direction:column;gap:0">{''.join(rows) or '<div class="sow-meta" style="padding:30px;text-align:center">No vendors yet.</div>'}</div>
<script>
function delVendor(id){{
  if(!confirm('Delete this vendor?')) return;
  fetch('/sow/vendor/delete', {{method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}}, body:'id='+encodeURIComponent(id)}})
    .then(function(){{ location.reload(); }});
}}
</script>"""
    return _shell(user, "Vendors", body)


def _render_types(user, dir_key):
    is_agy = dir_key == "agy"
    name = "with Agency (Vendor)" if is_agy else "with Samsung (SEA)"

    def cards(kind):
        out = []
        for key, t in TYPES.items():
            if key.startswith(dir_key) and t["kind"] == kind:
                out.append(
                    f'<a class="type-card" href="/sow/new?type={key}">'
                    f'<span class="type-icon">{t["icon"]}</span>'
                    f'<span><div class="type-name">{_esc(t["label"])}</div>'
                    f'<div class="type-desc">{_esc(t["desc"])}</div></span></a>'
                )
        return "".join(out)

    sections = f"""
<h2 style="font-size:.92rem;font-weight:800;margin:22px 0 0">Statement of Work</h2>
<div class="type-grid">{cards('sow')}</div>"""
    if not is_agy:
        sections += f"""
<h2 style="font-size:.92rem;font-weight:800;margin:10px 0 0">Estimation</h2>
<div class="type-grid">{cards('est')}</div>"""
    if is_agy:
        sections += f"""
<h2 style="font-size:.92rem;font-weight:800;margin:10px 0 0">Agreements</h2>
<div class="type-grid">{cards('msa')}{cards('nda')}</div>"""
    else:
        sections += ('<p style="color:var(--text-muted);font-size:.78rem">Master agreement with Samsung '
                     '(Advertising Services Agreement, Sep 16 2022) already exists — SOWs reference it; '
                     'MSA/NDA drafting lives under <a href="/sow/types?dir=agy" style="color:var(--accent)">with Agency</a>.</p>')
    body = f"""
<div style="display:flex;align-items:center;gap:12px;margin:8px 0 4px">
  <a class="btn btn-ghost btn-sm" href="/sow">←</a>
  <h1 style="margin:0">{name}</h1>
</div>
<p style="color:var(--text-muted);font-size:.86rem">Pick the document type — the template opens as a live preview; fill in the highlighted fields.</p>
{sections}"""
    return _shell(user, "Document Type", body)


# ── document editor ──────────────────────────────────────────────────────────

_EDITOR_JS = """<script>
var RES = __RES__;
var OV = __OV__;   /* per-month amount overrides: {'Mar-26': 1260, ...} */
var CFG = __CFG__;
function $id(x){ return document.getElementById(x); }
function mode(){ return $id('fMode').value; }
function money(x){
  if(isNaN(x)) return '$0';
  var r = Math.round(x*100)/100;
  return '$' + (Math.abs(r-Math.round(r))<0.005 ? Math.round(r).toLocaleString('en-US')
              : r.toLocaleString('en-US', {minimumFractionDigits:2}));
}
function monthSpans(s, e){
  if(!s || !e) return [];
  var sd = new Date(s+'T00:00:00'), ed = new Date(e+'T00:00:00');
  if(ed < sd) return [];
  var out = [], y = sd.getFullYear(), m = sd.getMonth();
  while(y < ed.getFullYear() || (y === ed.getFullYear() && m <= ed.getMonth())){
    var last = new Date(y, m+1, 0).getDate();
    var d1 = (y===sd.getFullYear() && m===sd.getMonth()) ? sd.getDate() : 1;
    var d2 = (y===ed.getFullYear() && m===ed.getMonth()) ? ed.getDate() : last;
    var frac = (d1===1 && d2===last) ? 1 : Math.min(1, Math.round((d2-d1+1)/30*100)/100);
    out.push([y, m, frac]);
    m++; if(m===12){ m=0; y++; }
  }
  return out;
}
var MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
function monthlyAmt(){
  var t = 0;
  RES.forEach(function(r){
    if(mode() === 'hourly') t += (parseFloat(r.hourly)||0)*(parseFloat(r.hrs)||0)*(parseFloat(r.qty)||1);
    else t += parseFloat(r.rate)||0;
  });
  return t;
}
var _months = 0;
function schedRows(){
  var spans = monthSpans($id('fStart').value, $id('fEnd').value);
  var monthly = monthlyAmt(), rule = $id('fRule').value;
  _months = 0;
  return spans.map(function(sp){
    var y = sp[0], m = sp[1], frac = sp[2];
    _months += frac;
    var label = MON[m] + '-' + String(y).slice(2);
    var auto = Math.round(monthly*frac*100)/100;
    var amt = (OV[label] != null && OV[label] !== '') ? parseFloat(OV[label]) || 0 : auto;
    var inv;
    if(rule === 'month_end') inv = new Date(y, m+1, 0);
    else inv = (m===11) ? new Date(y+1, 0, 1) : new Date(y, m+1, 1);
    return {label: label, amt: amt, auto: auto, edited: OV[label] != null && OV[label] !== '',
            inv: inv.getDate() + '-' + MON[inv.getMonth()] + '-' + String(inv.getFullYear()).slice(2)};
  });
}
function feeOf(rows){ return rows.reduce(function(a, r){ return a + r.amt; }, 0); }
function paintTotals(rows){
  var fee = feeOf(rows);
  document.querySelectorAll('.feeOut').forEach(function(el){ el.textContent = money(fee); });
  $id('monthsOut') && ($id('monthsOut').textContent = Math.round(_months*10)/10);
  var t = $id('schedTotal'); if(t) t.textContent = money(fee);
  return fee;
}
function renderSched(){
  var rows = schedRows();
  var tb = $id('schedBody'); tb.innerHTML = '';
  rows.forEach(function(r){
    var tr = document.createElement('tr');
    tr.innerHTML = '<td>' + r.label + '</td>'
      + '<td class="num"><input class="slot sched-amt" data-label="' + r.label + '" value="' + r.amt + '"'
      + ' title="' + (r.edited ? 'Edited — auto value ' + money(r.auto) : 'Auto from period × rates; type to override') + '"'
      + (r.edited ? ' style="border-bottom-color:var(--warn)"' : '') + '></td>'
      + '<td>' + r.inv + '</td>';
    tb.appendChild(tr);
  });
  var tr = document.createElement('tr');
  tr.innerHTML = '<td><b>Total</b></td><td class="num"><b id="schedTotal"></b></td>'
    + '<td><button type="button" class="btn btn-ghost btn-sm" onclick="OV={};renderSched()" title="Drop manual edits, back to auto">↺ auto</button></td>';
  tb.appendChild(tr);
  paintTotals(rows);
}
function updateResComputed(){
  if(mode() !== 'hourly') return;
  document.querySelectorAll('#resBody tr').forEach(function(tr, i){
    var r = RES[i] || {};
    var cost = (parseFloat(r.hourly)||0)*(parseFloat(r.hrs)||0)*(parseFloat(r.qty)||1)*_months;
    var tds = tr.querySelectorAll('td.num-ro');
    if(tds[0]) tds[0].textContent = Math.round(_months*10)/10;
    if(tds[1]) tds[1].textContent = money(cost);
  });
}
var HEADS = {
  hourly:  ['Profile','Location','Qty','# Months','Hourly USD','Hrs/Month','Cost'],
  monthly: ['No.','Name','Role','Level','Region','Rate/Month USD']
};
function renderRes(){
  var thead = document.querySelector('#resTableHead');
  thead.innerHTML = '<tr>' + HEADS[mode()].map(function(h){ return '<th>' + h + '</th>'; }).join('') + '<th style="border:none"></th></tr>';
  var tb = $id('resBody'); tb.innerHTML = '';
  RES.forEach(function(r, i){
    var tr = document.createElement('tr'), html = '';
    if(mode() === 'hourly'){
      html = cell(r,'profile',i) + cell(r,'location',i) + cell(r,'qty',i) +
             '<td class="num num-ro"></td>' + cell(r,'hourly',i) + cell(r,'hrs',i) +
             '<td class="num num-ro"></td>';
    } else {
      html = '<td class="num">' + (i+1) + '</td>' + cell(r,'name',i) + cell(r,'role',i) +
             cell(r,'level',i) + cell(r,'region',i) + cell(r,'rate',i);
    }
    tr.innerHTML = html + '<td style="border:none"><button type="button" class="row-del" onclick="rmRow('+i+')">✕</button></td>';
    tb.appendChild(tr);
  });
  updateResComputed();
}
function cell(r, k, i){
  var v = r[k] != null ? String(r[k]).replace(/"/g,'&quot;') : '';
  var dl = (k === 'profile' || k === 'name') ? ' list="peopleList"' : '';
  return '<td><input class="slot" data-k="'+k+'" data-i="'+i+'" value="'+v+'"'+dl+'></td>';
}
function rosterFill(i, name){
  var p = (CFG.people || []).find(function(x){ return x.name === name; });
  if(!p) return;
  var r = RES[i];
  if(mode() === 'hourly'){
    if(!r.hourly && p.rate) r.hourly = p.rate;
    if(!r.location && p.location) r.location = p.location;
  } else {
    if(!r.role && p.function) r.role = p.function;
    if(!r.region && p.location) r.region = p.location;
    if(!r.rate && p.rate) r.rate = String(Math.round(parseFloat(p.rate)*168));
  }
  var tr = document.querySelectorAll('#resBody tr')[i];
  if(tr) tr.querySelectorAll('input[data-k]').forEach(function(inp){
    if(inp.dataset.k !== 'profile' && inp.dataset.k !== 'name')
      inp.value = r[inp.dataset.k] != null ? r[inp.dataset.k] : '';
  });
}
function addRow(){ RES.push({}); renderRes(); renderSched(); updateResComputed(); }
function rmRow(i){ RES.splice(i,1); renderRes(); renderSched(); updateResComputed(); }
function modeSync(){ renderRes(); renderSched(); updateResComputed(); }
/* Typing must never rebuild the input being typed in — update data + computed
   cells in place; full re-renders only on structural events. */
document.addEventListener('input', function(e){
  if(e.target.classList && e.target.classList.contains('sched-amt')){
    OV[e.target.dataset.label] = e.target.value;
    paintTotals(schedRows());
    return;
  }
  var k = e.target.dataset && e.target.dataset.k;
  if(k){
    var i = parseInt(e.target.dataset.i);
    RES[i][k] = e.target.value;
    if(k === 'profile' || k === 'name') rosterFill(i, e.target.value);
    renderSched(); updateResComputed();
  }
});
document.addEventListener('change', function(e){
  if(e.target.id === 'fStart' || e.target.id === 'fEnd' || e.target.id === 'fRule' || e.target.id === 'fDate'){
    renderSched(); updateResComputed(); dateSyncPreamble();
  }
});
function dateSyncPreamble(){
  var dEl = $id('preamDate');
  if(dEl){
    var dv = $id('fDate').value;
    dEl.textContent = dv ? new Date(dv+'T00:00:00').toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'}) : '(date)';
  }
}
var vSel = $id('fVendor');
function vendorSync(){
  if(!vSel) return;
  var v = CFG.vendors[vSel.value] || {};
  var en = $id('preamVendor'), md = $id('preamMsa'), nm = document.querySelectorAll('.vendorName');
  if(en) en.textContent = v.entity_line || v.name || '(vendor — register below)';
  if(md) md.textContent = v.msa_date_long || '(MSA date)';
  nm.forEach(function(el){ el.textContent = v.name || 'Contractor'; });
}
if(vSel) vSel.addEventListener('change', vendorSync);
document.getElementById('sowForm').addEventListener('submit', function(){
  $id('resJson').value = JSON.stringify(RES.filter(function(r){
    return Object.keys(r).some(function(k){ return String(r[k]||'').trim(); });
  }));
  var clean = {};
  Object.keys(OV).forEach(function(k){ if(String(OV[k]).trim() !== '') clean[k] = parseFloat(OV[k]) || 0; });
  $id('ovJson').value = JSON.stringify(clean);
});
if(!RES.length) RES.push({});
vendorSync(); dateSyncPreamble(); renderRes(); renderSched(); updateResComputed();
</script>"""


def _slot(name, value, ph="", extra="", tag="input"):
    return (f'<input class="slot" name="{name}" value="{_esc(value)}" '
            f'placeholder="{_esc(ph)}" {extra}>')


def _render_doc_editor(user, sow, type_key, saved=False):
    data = _load(user)
    t = TYPES[type_key]
    is_agency = t["dir"] == "agency"
    mode = sow.get("res_mode") or t["mode"]
    vendors = {v["id"]: v for v in data["vendors"]}
    for v in vendors.values():
        v["msa_date_long"] = _fmt_long(v.get("msa_date"))
    cur_vendor = vendors.get(sow.get("vendor_id")) or {}
    vend_opts = "".join(
        f'<option value="{vid}"{" selected" if vid == sow.get("vendor_id") else ""}>{_esc(v["name"])}</option>'
        for vid, v in vendors.items()
    )
    dir_chip = ('<span class="dir-chip dir-agency">Agency</span>' if is_agency
                else '<span class="dir-chip dir-samsung">SEA</span>')
    saved_note = ('<span style="color:var(--success);font-size:.8rem;font-weight:700">✓ Saved</span>'
                  if saved else "")
    vendor_bar = ""
    if is_agency:
        vendor_bar = f"""
  <span style="display:flex;align-items:center;gap:6px;font-size:.78rem;color:var(--text-muted)">Vendor
    <select class="slot" name="vendor_id" id="fVendor" style="min-width:150px">
      <option value="">— pick —</option>{vend_opts}
    </select>
  </span>
  <details style="position:relative"><summary class="btn btn-ghost btn-sm" style="list-style:none">+ New vendor</summary>
    <div style="position:absolute;top:calc(100% + 8px);left:0;z-index:80;background:var(--surface-3);border:1px solid var(--border-bright);border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:8px;min-width:300px;box-shadow:var(--shadow-lg)">
      <input class="slot" name="v_name" placeholder="Vendor name — e.g. Invictus Data, Inc.">
      <input class="slot" name="v_entity" placeholder="Entity line (name + address for preamble)">
      <input class="slot" type="date" name="v_msa" title="MSA date">
      <span style="font-size:.7rem;color:var(--text-muted)">Saved together on 💾 Save</span>
    </div>
  </details>"""

    # ── document body ──
    if is_agency:
        preamble = f"""
<p class="legal">This Statement of Work ("Statement of Work" or "SOW") is made effective as of <b id="preamDate">{_esc(_fmt_long(sow.get('date')) or '(date)')}</b> (the "Statement of Work Effective Date") by and between Cheil USA Inc., a Delaware corporation with its principal of business located at 837 Washington Street, 4th Floor, New York, NY 10014 on behalf of itself and its affiliates and subsidiaries ("Cheil") and <b id="preamVendor">{_esc(cur_vendor.get('entity_line') or cur_vendor.get('name') or '(vendor — register above)')}</b> ("Contractor").  Contractor and Cheil may each be referred to herein as a "Party", and, together as the "Parties".</p>
<p class="legal">This SOW is governed by, incorporated into, and made part of, that certain Master Services Agreement (the "Agreement"), dated as of <b id="preamMsa">{_esc(cur_vendor.get('msa_date_long') or '(MSA date)')}</b>, by and between Cheil and Contractor. This SOW defines the Services that Contractor shall provide to Cheil in accordance with the terms of the Agreement and this SOW. […] To the extent there is a conflict between the terms of this SOW and the Agreement, the terms of the Agreement shall control, except for terms where the Agreement expressly permits the SOW to control in the event of conflict with the Agreement.</p>"""
    else:
        preamble = f'<p class="legal">{_esc(PREAMBLE_SAMSUNG)}</p>'

    stk_client_label = (f'<span class="vendorName">{_esc(cur_vendor.get("name") or "Contractor")}</span> POC'
                        if is_agency else "Samsung Manager for this Role")
    client_line = CHEIL_ENTITY if is_agency else SAMSUNG_ENTITY
    oop_html = "".join(f'<p class="legal">{_esc(par)}</p>'
                       for par in (OOP_AGENCY if is_agency else OOP_SAMSUNG).split("\n\n"))
    sig_left = CHEIL_ENTITY if is_agency else SAMSUNG_ENTITY
    sig_right = (f'<span class="vendorName">{_esc(cur_vendor.get("name") or "Contractor")}</span>'
                 if is_agency else CHEIL_ENTITY)

    people_cfg = [{"name": pp.get("name") or "", "function": pp.get("role_title") or "",
                   "location": pp.get("location") or "", "rate": pp.get("sell_hr") or ""}
                  for pp in data["people"]]
    cfg = {"vendors": vendors, "people": people_cfg}
    body = f"""
<form method="post" action="/sow/save" id="sowForm">
<input type="hidden" name="id" value="{_esc(sow.get('id') or '')}">
<input type="hidden" name="type" value="{type_key}">
<input type="hidden" name="resources_json" id="resJson">
<input type="hidden" name="schedule_overrides" id="ovJson">
<div class="doc-bar">
  <a class="btn btn-ghost btn-sm" href="/sow" title="All SOWs">←</a>
  {dir_chip}<span style="font-size:.82rem;font-weight:700">{t['icon']} {_esc(t['label'])}</span>
  {vendor_bar}
  <span class="spacer"></span>
  {saved_note}
  <button type="button" class="btn btn-secondary btn-sm" id="exToggle" title="Show/hide the executed example">📖 Example</button>
  {f'<a class="btn btn-secondary btn-sm" href="/sow/docx?id={sow["id"]}">⬇ docx</a>' if sow.get('id') else ''}
  <button type="submit" class="btn btn-primary btn-sm">💾 Save</button>
</div>

<div class="ed-wrap" id="edWrap">
<div class="paper">
  {'<img src="/sow/asset/logo" alt="Cheil × Samsung" style="max-width:300px;margin-bottom:22px;background:#fff;padding:10px 14px;border-radius:8px">' if not is_agency else ''}
  <div class="doc-title">{_slot('title', sow.get('title'), 'SOW title — e.g. Data Engineer # 1', 'style="width:100%;font-weight:800;font-size:1.15rem"')}</div>
  <div style="font-weight:800;margin:8px 0 18px">STATEMENT OF WORK</div>

  <div class="meta-line"><b>DATE:</b> <input class="slot" type="date" name="date" id="fDate" value="{_esc(sow.get('date') or date.today().isoformat())}"></div>
  <div class="meta-line"><b>CLIENT:</b> <span>{client_line}</span></div>
  <div class="meta-line"><b>PROJECT NAME:</b> {_slot('project_name', sow.get('project_name'), 'e.g. SEA eCom Data', 'style="flex:1"')}</div>
  <div class="meta-line"><b>PREPARED BY:</b> {_slot('prepared_by', sow.get('prepared_by'), 'name')}</div>
  <div class="meta-line"><b>PREPARED FOR:</b> {_slot('prepared_for', sow.get('prepared_for'), 'name')}</div>
  {'<div style="border-top:2px dashed var(--border-bright);margin:26px -52px;position:relative"><span style="position:absolute;top:-9px;left:50%;transform:translateX(-50%);background:var(--surface);padding:0 10px;font-size:.64rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em">Page 2</span></div>' if not is_agency else ''}

  {preamble}

  <h2>Executive Summary</h2>
  <textarea class="slot" name="exec_summary" rows="3" placeholder="What service does this SOW provide?">{_esc(sow.get('exec_summary'))}</textarea>

  <h2>{'Service Description' if is_agency else 'Deliverables'}</h2>
  <textarea class="slot" name="deliverables" rows="7" placeholder="One item per line — rendered as bullets in the document">{_esc(sow.get('deliverables'))}</textarea>

  <h2>Project Stakeholders</h2>
  <div class="table-wrap"><table>
    <tr><th></th><th>{stk_client_label}</th><th>Cheil Project Management &amp; SOW Owner</th></tr>
    <tr><td><b>Name</b></td><td><input class="slot" name="stk_c_name" value="{_esc(sow.get('stk_c_name'))}"></td><td><input class="slot" name="stk_a_name" value="{_esc(sow.get('stk_a_name'))}"></td></tr>
    <tr><td><b>Email</b></td><td><input class="slot" name="stk_c_email" value="{_esc(sow.get('stk_c_email'))}"></td><td><input class="slot" name="stk_a_email" value="{_esc(sow.get('stk_a_email'))}"></td></tr>
    <tr><td><b>Location</b></td><td><input class="slot" name="stk_c_loc" value="{_esc(sow.get('stk_c_loc'))}"></td><td><input class="slot" name="stk_a_loc" value="{_esc(sow.get('stk_a_loc'))}"></td></tr>
  </table></div>

  <h2>Service Period</h2>
  <div class="meta-line"><b>Start Date :</b> <input class="slot" type="date" name="start" id="fStart" value="{_esc(sow.get('start'))}" required></div>
  <div class="meta-line"><b>End Date :</b> <input class="slot" type="date" name="end" id="fEnd" value="{_esc(sow.get('end'))}" required></div>

  <h2>{'Resource Planning' if is_agency else 'Resource Management'}
    <select class="slot" name="res_mode" id="fMode" onchange="modeSync()" style="font-size:.76rem;margin-left:10px;vertical-align:middle" title="Rate model — switches the resource table columns">
      <option value="hourly"{' selected' if mode == 'hourly' else ''}>Hourly (rate × hrs/month)</option>
      <option value="monthly"{' selected' if mode == 'monthly' else ''}>Monthly rate per member</option>
    </select></h2>
  <p class="legal">In consideration for the provision of the Services and Deliverables under this SOW, {'Cheil shall pay Contractor' if is_agency else 'Samsung shall pay Cheil'} in accordance with the following rates and fees, subject to the applicable terms and conditions of the Agreement:</p>
  <div class="table-wrap"><table>
    <thead id="resTableHead"></thead>
    <tbody id="resBody"></tbody>
  </table></div>
  <button type="button" class="btn btn-ghost btn-sm add-row-btn" onclick="addRow()">+ Add resource</button>

  <h2>Cost and Payment Schedule</h2>
  <p><b>Fee : <span class="feeOut">$0</span></b> <span style="color:var(--text-muted);font-size:.78rem">(<span id="monthsOut">0</span> months · amounts are auto-filled, type in any month to override)</span></p>
  <p class="legal">{PAYMENT_INTRO_AGENCY if is_agency else PAYMENT_INTRO}
    <br>Invoice dates: <select class="slot" name="invoice_rule" id="fRule">
      <option value="next_first"{'' if sow.get('invoice_rule') == 'month_end' else ' selected'}>1st of following month</option>
      <option value="month_end"{' selected' if sow.get('invoice_rule') == 'month_end' else ''}>last day of service month</option>
    </select></p>
  <div class="table-wrap"><table>
    <thead><tr><th>Month</th><th>Amount</th><th>Invoice Date</th></tr></thead>
    <tbody id="schedBody"></tbody>
  </table></div>
  <p class="legal">{_esc(CHANGE_ORDER_NOTE)}</p>

  <h2>Out-of-pocket Expense</h2>
  {oop_html}

  <h2>Signatures</h2>
  <p class="legal">IN WITNESS WHEREOF, the parties have caused this Statement of Work to be duly executed by their authorized representatives as set forth below.</p>
  <div class="table-wrap"><table>
    <tr><th>{sig_left}</th><th>{sig_right}</th></tr>
    <tr><td>Signature: ____________________</td><td>Signature: ____________________</td></tr>
    <tr><td>Name: ____________________</td><td>Name: ____________________</td></tr>
    <tr><td>Title: ____________________</td><td>Title: ____________________</td></tr>
    <tr><td>Date: ____________________</td><td>Date: ____________________</td></tr>
  </table></div>
  <div class="ro-note">Highlighted fields are editable · everything else exports as-is to .docx</div>
</div>
{_render_example(type_key)}
</div>
<datalist id="peopleList">{"".join(f'<option value="{_esc(pp["name"])}">' for pp in people_cfg)}</datalist>
</form>
""" + _EDITOR_JS.replace("__RES__", json.dumps(sow.get("resources", [])).replace("</", "<\\/")) \
                .replace("__OV__", json.dumps(sow.get("schedule_overrides") or {}).replace("</", "<\\/")) \
                .replace("__CFG__", json.dumps(cfg).replace("</", "<\\/")) + _EX_TOGGLE_JS
    return _shell(user, "SOW Editor", body, wide=True)


_MSA_PARS = None


def _msa_paragraphs():
    """Extract the MSA template's full text once: [(kind, text)] where kind is
    'title' | 'h' (numbered section heading) | 'p'. Falls back to [] when
    python-docx is unavailable (preview then shows the summary box)."""
    global _MSA_PARS
    if _MSA_PARS is not None:
        return _MSA_PARS
    try:
        from docx import Document
        doc = Document(os.path.join(_ASSETS, "msa_template.docx"))
        out = []
        for p in doc.paragraphs:
            t = " ".join(p.text.split())
            if not t:
                continue
            bold = any(r.bold for r in p.runs if r.text.strip())
            if t == "MASTER SERVICES AGREEMENT":
                kind = "title"
            elif p.style.name == "List Paragraph" and bold:
                kind = "h"
            else:
                kind = "p"
            out.append((kind, t))
        _MSA_PARS = out
    except Exception:
        _MSA_PARS = []
    return _MSA_PARS


_AGREEMENT_JS = """<script>
var CFG = __CFG__;
function $id(x){ return document.getElementById(x); }
function vendorSync(){
  var v = CFG.vendors[$id('fVendor').value] || {};
  document.querySelectorAll('.vendorName').forEach(function(el){
    el.textContent = v.name || '______________________';
  });
}
function dateSync(){
  var dv = $id('fDate').value, el = $id('agrDate');
  if(el) el.textContent = dv ? new Date(dv+'T00:00:00').toLocaleDateString('en-US',{year:'numeric',month:'long',day:'numeric'}) : '____________';
}
document.addEventListener('change', function(){ vendorSync(); dateSync(); });
vendorSync(); dateSync();
</script>"""


def _render_agreement_editor(user, sow, type_key, saved=False):
    data = _load(user)
    t = TYPES[type_key]
    kind = t["kind"]
    vendors = {v["id"]: v for v in data["vendors"]}
    cur_vendor = vendors.get(sow.get("vendor_id")) or {}
    vend_opts = "".join(
        f'<option value="{vid}"{" selected" if vid == sow.get("vendor_id") else ""}>{_esc(v["name"])}</option>'
        for vid, v in vendors.items()
    )
    saved_note = ('<span style="color:var(--success);font-size:.8rem;font-weight:700">✓ Saved</span>'
                  if saved else "")
    vname = f'<b class="vendorName">{_esc(cur_vendor.get("name") or "______________________")}</b>'
    date_slot = f'<input class="slot" type="date" name="date" id="fDate" value="{_esc(sow.get("date") or date.today().isoformat())}">'

    if kind == "msa":
        doc_title = "MASTER SERVICES AGREEMENT"
        pars = _msa_paragraphs()
        if pars:
            chunks, sec_n = [], 0
            for pk, txt in pars:
                if pk == "title":
                    continue  # rendered separately above the date slot
                html = _esc(txt)
                html = html.replace("XXX XX, 2026",
                                    f'<b id="agrDate">{_esc(_fmt_long(sow.get("date")) or "____________")}</b>')
                html = html.replace("(Your Company Name)", vname)
                if pk == "h":
                    sec_n += 1
                    chunks.append(f'<h2 style="font-size:.95rem">{sec_n}. {html}</h2>')
                else:
                    chunks.append(f'<p class="legal">{html}</p>')
            body_doc = "".join(chunks)
        else:
            body_doc = f"""
  <p class="legal">This Master Services Agreement (this "Agreement"), dated as of <b id="agrDate">{_esc(_fmt_long(sow.get('date')) or '____________')}</b> (the "Effective Date"), is made by and between Cheil USA Inc., a Delaware corporation ("Cheil"), and {vname} ("Contractor").</p>
  <div style="background:var(--surface-2);border:1px dashed var(--border-bright);border-radius:10px;padding:16px 18px;margin:18px 0;font-size:.8rem;color:var(--text-muted);line-height:1.7">
    ⚑ Full-text preview needs python-docx on this host — the export still contains the complete
    legal text verbatim from the executed Cheil MSA template.
  </div>"""
    else:
        clauses = "".join(f'<p class="legal">{_esc(par)}</p>' for par in NDA_BODY)
        body_doc = f"""
  <p class="legal">This CONFIDENTIALITY AND NONDISCLOSURE AGREEMENT (the "Agreement"), is entered into as of <b id="agrDate">{_esc(_fmt_long(sow.get('date')) or '____________')}</b> (the "Effective Date"), by and between {vname} (the "Vendor"), and Cheil USA, Inc. (the "Cheil").</p>
  {clauses}
  <div class="table-wrap"><table>
    <tr><th>Cheil USA, Inc.</th><th><span class="vendorName">{_esc(cur_vendor.get('name') or '[_____________________]')}</span></th></tr>
    <tr><td>By: ____________________</td><td>By: ____________________</td></tr>
    <tr><td>Name:</td><td>Name:</td></tr>
    <tr><td>Title:</td><td>Title:</td></tr>
  </table></div>"""
        doc_title = NDA_TITLE

    people_cfg = [{"name": pp.get("name") or "", "function": pp.get("role_title") or "",
                   "location": pp.get("location") or "", "rate": pp.get("sell_hr") or ""}
                  for pp in data["people"]]
    cfg = {"vendors": vendors, "people": people_cfg}
    body = f"""
<form method="post" action="/sow/save" id="sowForm">
<input type="hidden" name="id" value="{_esc(sow.get('id') or '')}">
<input type="hidden" name="type" value="{type_key}">
<div class="doc-bar">
  <a class="btn btn-ghost btn-sm" href="/sow" title="All documents">←</a>
  <span class="dir-chip dir-agency">Agency</span>
  <span style="font-size:.82rem;font-weight:700">{t['icon']} {_esc(t['label'])}</span>
  <span style="display:flex;align-items:center;gap:6px;font-size:.78rem;color:var(--text-muted)">Vendor
    <select class="slot" name="vendor_id" id="fVendor" style="min-width:150px">
      <option value="">— pick —</option>{vend_opts}
    </select>
  </span>
  <details style="position:relative"><summary class="btn btn-ghost btn-sm" style="list-style:none">+ New vendor</summary>
    <div style="position:absolute;top:calc(100% + 8px);left:0;z-index:80;background:var(--surface-3);border:1px solid var(--border-bright);border-radius:10px;padding:14px;display:flex;flex-direction:column;gap:8px;min-width:300px;box-shadow:var(--shadow-lg)">
      <input class="slot" name="v_name" placeholder="Vendor name — e.g. Invictus Data, Inc.">
      <input class="slot" name="v_entity" placeholder="Entity line (name + address)">
      <input class="slot" type="date" name="v_msa" title="MSA date">
      <span style="font-size:.7rem;color:var(--text-muted)">Saved together on 💾 Save</span>
    </div>
  </details>
  <span class="spacer"></span>
  {saved_note}
  <button type="button" class="btn btn-secondary btn-sm" id="exToggle" title="Show/hide the executed example">📖 Example</button>
  {f'<a class="btn btn-secondary btn-sm" href="/sow/docx?id={sow["id"]}">⬇ docx</a>' if sow.get('id') else ''}
  <button type="submit" class="btn btn-primary btn-sm">💾 Save</button>
</div>
<div class="ed-wrap" id="edWrap">
<div class="paper">
  <div style="text-align:center;font-weight:800;font-size:1.05rem;margin-bottom:20px">{doc_title}</div>
  <div class="meta-line" style="margin-bottom:14px"><b>EFFECTIVE DATE:</b> {date_slot}</div>
  {body_doc}
  <div class="ro-note">Highlighted fields are editable · everything else exports as-is to .docx</div>
</div>
{_render_example(type_key)}
</div>
</form>
""" + _AGREEMENT_JS.replace("__CFG__", json.dumps(cfg).replace("</", "<\\/")) + _EX_TOGGLE_JS
    return _shell(user, t["label"], body, wide=True)


# ── routing ──────────────────────────────────────────────────────────────────

def _f(body, key, default=""):
    v = body.get(key, default)
    if isinstance(v, list):
        v = v[0] if v else default
    return (v or "").strip()


# ══════════════════════════════════════════════════════════════════════════
# Uploaded contracts — SEA↔Cheil (upstream) aligned to Cheil↔Vendor (downstream)
# ══════════════════════════════════════════════════════════════════════════

_CONTRACT_MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "doc": "application/msword",
    "txt": "text/plain",
}
_MONTHS = ("January|February|March|April|May|June|July|August|September|"
           "October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec")
_DATE_RE = re.compile(
    r"(?:%s)\.?\s+\d{1,2},?\s+\d{4}" % _MONTHS + r"|\b\d{1,2}/\d{1,2}/\d{2,4}\b",
    re.IGNORECASE)
_AMOUNT_RE = re.compile(r"(?:US)?\$\s?([\d]{1,3}(?:,\d{3})+(?:\.\d{2})?|\d+(?:\.\d{2})?)")


def _contracts_dir(user):
    return os.path.join(DATA_ROOT, user, "sow_contracts")


def _contract_file_path(user, c):
    return os.path.join(_contracts_dir(user), f"{c['id']}.{c.get('ext', 'bin')}")


_ALLOWED_EXT = {"pdf", "docx", "doc", "txt"}


def _safe_filename(fn):
    """Display/storage-safe filename: no path, no control chars/quotes."""
    fn = (fn or "").replace("\r", " ").replace("\n", " ").replace('"', " ").replace("\\", "/")
    fn = os.path.basename(fn).strip()
    return fn[:120] or "contract"


def _safe_ext(fn):
    """Whitelisted, alnum-only extension — keeps it out of the filesystem path
    as anything but a plain suffix (no '/', no '..')."""
    ext = fn.rsplit(".", 1)[-1].lower() if "." in fn else ""
    ext = re.sub(r"[^a-z0-9]", "", ext)[:5]
    return ext if ext in _ALLOWED_EXT else "bin"


def _read_uploaded_files(raw_handler):
    """Parse a multipart body; return list of (filename, bytes, mime)."""
    try:
        ct = raw_handler.headers.get("Content-Type", "")
        m = re.search(r"boundary=([^\s;]+)", ct)
        if not m:
            return []
        boundary = ("--" + m.group(1).strip('"')).encode()
        length = int(raw_handler.headers.get("Content-Length", 0))
        data = raw_handler.rfile.read(length)
    except Exception:
        return []
    files = []
    for part in data.split(boundary):
        if b'filename="' not in part:
            continue
        fn_m = re.search(rb'filename="([^"]*)"', part)
        if not fn_m or not fn_m.group(1):
            continue
        filename = fn_m.group(1).decode("utf-8", errors="replace")
        hdr_end = part.find(b"\r\n\r\n")
        if hdr_end == -1:
            continue
        content = part[hdr_end + 4:]
        if content.endswith(b"\r\n"):
            content = content[:-2]
        if content:
            files.append((filename, content, "application/octet-stream"))
    return files


def _extract_text(content, ext):
    """Best-effort plain text from an uploaded contract (docx/pdf/txt)."""
    try:
        if ext == "docx":
            from docx import Document
            doc = Document(io.BytesIO(content))
            parts = [p.text for p in doc.paragraphs]
            for tbl in doc.tables:
                for row in tbl.rows:
                    parts.append(" | ".join(c.text for c in row.cells))
            return "\n".join(parts)
        if ext == "pdf":
            import fitz
            with fitz.open(stream=content, filetype="pdf") as doc:
                return "\n".join(page.get_text() for page in doc)
        return content.decode("utf-8", errors="replace")
    except Exception as e:
        return f"[could not read {ext}: {e}]"


def _extract_fields(text):
    """Heuristic pull of parties / amount / period / project from contract text.
    Deliberately forgiving — the user confirms & corrects on the popup."""
    low = text.lower()
    flat = re.sub(r"\s+", " ", text)

    # parties — try "by and between X and Y", else entity-like names
    client = agency = vendor = ""
    m = re.search(r"by and between\s+(.+?)\s+(?:\(|,)", flat, re.IGNORECASE)
    n = re.search(r"\band\s+([A-Z][\w&.,'\- ]+?(?:Inc|LLC|L\.L\.C|Corp|Corporation|Ltd|Company)\.?)",
                  flat)
    p1 = (m.group(1).strip() if m else "")
    p2 = (n.group(1).strip() if n else "")
    has_samsung = "samsung" in low
    has_cheil = "cheil" in low
    if has_samsung:
        client = SAMSUNG_ENTITY
        agency = CHEIL_ENTITY
    elif has_cheil:
        agency = CHEIL_ENTITY
    # vendor = whichever named party is neither Cheil nor Samsung
    for cand in (p1, p2):
        cl = cand.lower()
        if cand and "cheil" not in cl and "samsung" not in cl and len(cand) < 90:
            vendor = cand
            break

    # amount — take the largest $ figure (usually the contract total)
    amounts = []
    for a in _AMOUNT_RE.findall(text):
        try:
            amounts.append(float(a.replace(",", "")))
        except ValueError:
            pass
    amount = _money(max(amounts)) if amounts else ""

    # dates — effective/start first, an end/expiry date second
    dates = _DATE_RE.findall(text)
    period_start = dates[0] if dates else ""
    period_end = ""
    em = re.search(r"(?:end date|expir\w*|through|terminat\w*)[^\n]{0,40}?(" +
                   _DATE_RE.pattern + ")", text, re.IGNORECASE)
    if em:
        period_end = em.group(1)
    elif len(dates) > 1:
        period_end = dates[-1]

    # project name — a "Project Name:" label, else the doc title-ish first line
    project = ""
    pm = re.search(r"project\s*name\s*[:\-]\s*(.+)", text, re.IGNORECASE)
    if pm:
        project = pm.group(1).strip().split("\n")[0][:120]
    else:
        pm = re.search(r"project\s*[:\-]\s*(.+)", text, re.IGNORECASE)
        if pm:
            project = pm.group(1).strip().split("\n")[0][:120]

    side = "sea" if has_samsung else ("vendor" if vendor else "sea")
    return {"client": client, "agency": agency, "vendor": vendor,
            "amount": amount, "period_start": period_start,
            "period_end": period_end, "project_name": project, "side": side}


def _norm_tokens(s):
    return set(re.findall(r"[a-z0-9]+", (s or "").lower())) - {
        "the", "a", "an", "of", "for", "and", "sow", "project", "cheil", "samsung"}


def _suggest_parents(data, vendor):
    """SEA contracts ranked by project-name overlap — candidate parents for a
    vendor contract (one SEA↔Cheil deal can hold many Cheil↔Vendor deals)."""
    mine = _norm_tokens(vendor.get("project_name"))
    out = []
    for c in data.get("contracts", []):
        if c.get("side") != "sea":
            continue
        theirs = _norm_tokens(c.get("project_name"))
        score = len(mine & theirs) / max(1, len(mine | theirs)) if (mine or theirs) else 0
        out.append((score, c))
    out.sort(key=lambda x: x[0], reverse=True)
    return out


def _contract_by_id(data, cid):
    return next((c for c in data.get("contracts", []) if c["id"] == cid), None)


def _contract_groups(data):
    """1:many grouping. Returns (groups, orphans):
      groups  = [(sea_contract, [vendor children…]) …] for every SEA contract
      orphans = vendor contracts with no valid SEA parent
    A vendor's `linked_id` points to its SEA parent."""
    cs = data.get("contracts", [])
    seas = [c for c in cs if c.get("side") == "sea"]
    sea_ids = {s["id"] for s in seas}
    children = {s["id"]: [] for s in seas}
    orphans = []
    for c in cs:
        if c.get("side") == "sea":
            continue
        pid = c.get("linked_id")
        if pid in sea_ids:
            children[pid].append(c)
        else:
            orphans.append(c)
    groups = [(s, children[s["id"]]) for s in seas]
    return groups, orphans


_SIDE_META = {
    "sea": ("SEA ↔ Cheil", "dir-samsung", "#38bdf8", "🔵"),
    "vendor": ("Cheil ↔ Vendor", "dir-agency", "#fb923c", "🟠"),
}


def _contract_card(c, draggable=False):
    label, chip, color, icon = _SIDE_META.get(c.get("side"), _SIDE_META["sea"])
    parties = c.get("vendor") or c.get("client") or "—"
    drag = ' draggable="true"' if draggable else ""
    return (
        f'<div class="ctr-card" data-cid="{c["id"]}"{drag} '
        f'onclick="openContract(\'{c["id"]}\')" style="cursor:pointer">'
        + ('<span class="ctr-grip">⠿</span>' if draggable else '')
        + f'<div class="ctr-top"><span class="dir-chip {chip}">{icon} {label}</span>'
        f'<span class="ctr-amt">{_esc(c.get("amount") or "")}</span></div>'
        f'<div class="ctr-title">{_esc(c.get("project_name") or c.get("filename") or "(untitled contract)")}</div>'
        f'<div class="ctr-meta">{_esc(parties)}'
        + (f' · {_esc(c.get("period_start"))}' if c.get("period_start") else "")
        + (f' ~ {_esc(c.get("period_end"))}' if c.get("period_end") else "")
        + '</div></div>')


def _render_contracts_section(user, data):
    groups, orphans = _contract_groups(data)
    gblocks = []
    for sea, kids in groups:
        kid_cards = "".join(_contract_card(v, draggable=True) for v in kids)
        empty = ('<div class="ctr-drop-hint">Drag vendor contracts here</div>'
                 if not kids else "")
        gblocks.append(
            f'<div class="ctr-group">{_contract_card(sea)}'
            f'<div class="ctr-children" data-seadrop data-sea="{sea["id"]}">'
            f'{kid_cards}{empty}</div></div>')
    groups_html = "".join(gblocks) or (
        '<div class="sow-meta" style="padding:22px;text-align:center">'
        'No SEA↔Cheil contracts yet — upload one to start a group.</div>')
    orphan_html = (
        '<div class="ctr-orphans" data-seadrop data-sea="">'
        '<div class="ctr-orphan-hd">Unlinked vendor contracts '
        '<span>· drag onto a SEA↔Cheil contract above to align them</span></div>'
        + ("".join(_contract_card(c, draggable=True) for c in orphans)
           if orphans else '<div class="ctr-drop-hint">None — drop a vendor card here to unlink it</div>')
        + '</div>')
    return f"""
<div style="display:flex;align-items:center;justify-content:space-between;margin:30px 0 12px">
  <h2 style="font-size:1rem;font-weight:800;margin:0">📎 Contracts</h2>
</div>
<div class="ctr-dropzone" id="ctrDrop" data-filedrop tabindex="0">
  <input type="file" id="ctrFile" accept=".pdf,.docx,.doc,.txt" hidden>
  <b>⬆ Drop a contract here</b> or click to upload — PDF/Word, parsed automatically.
</div>
<div class="ctr-groups">{groups_html}</div>
{orphan_html}"""


def _render_contract_frag(user, data, cid):
    """Popup body for one contract: extracted fields (editable) + text preview
    + original download + link controls."""
    c = _contract_by_id(data, cid)
    if not c:
        return '<div class="cmodal-body"><p>Contract not found.</p></div>'
    label, chip, color, icon = _SIDE_META.get(c.get("side"), _SIDE_META["sea"])

    # link controls — 1:many (a vendor belongs under one SEA; a SEA holds many)
    if c.get("side") == "vendor":
        parent = _contract_by_id(data, c.get("linked_id")) if c.get("linked_id") else None
        if parent and parent.get("side") == "sea":
            link_html = (
                f'<div class="ctr-linked">🔗 Under <b>{_esc(parent.get("project_name") or parent.get("filename"))}</b> '
                '(SEA ↔ Cheil)'
                f'<button class="btn btn-danger btn-sm" onclick="ctrPost(\'/sow/contract/unlink\',{{id:\'{c["id"]}\'}})">Unlink</button></div>')
        else:
            opts = []
            for score, cand in _suggest_parents(data, c):
                tag = " ★ suggested" if score > 0 else ""
                opts.append(f'<option value="{cand["id"]}">{_esc(cand.get("project_name") or cand.get("filename"))}{tag}</option>')
            if opts:
                link_html = (
                    '<div class="ctr-linkbox"><b>Align under a SEA ↔ Cheil contract:</b>'
                    f'<select id="lnk_{c["id"]}" class="slot">{"".join(opts)}</select>'
                    f'<button class="btn btn-primary btn-sm" onclick="ctrAssign(\'{c["id"]}\')">🔗 Confirm</button>'
                    '<div class="sow-meta">★ = project-name match. You can also drag the card onto a SEA contract.</div></div>')
            else:
                link_html = '<div class="sow-meta">No SEA ↔ Cheil contract to align under yet.</div>'
    else:
        _, kids = next(((s, k) for s, k in _contract_groups(data)[0] if s["id"] == c["id"]),
                       (c, []))
        if kids:
            items = "".join(
                f'<li>{_esc(k.get("project_name") or k.get("filename"))}'
                f' <span class="sow-meta">{_esc(k.get("vendor") or "")}</span></li>' for k in kids)
            link_html = (f'<div class="ctr-linkbox"><b>Aligned vendor contracts ({len(kids)}):</b>'
                         f'<ul class="ctr-kidlist">{items}</ul>'
                         '<div class="sow-meta">Drag a vendor card onto this contract to add more.</div></div>')
        else:
            link_html = ('<div class="sow-meta" style="margin-top:16px;padding-top:14px;'
                         'border-top:1px solid var(--border)">No vendor contracts aligned yet — '
                         'drag a vendor card onto this contract on the main screen.</div>')

    def fld(lbl, key, val):
        return (f'<label class="ctr-fld"><span>{lbl}</span>'
                f'<input class="slot" name="{key}" value="{_esc(val)}"></label>')

    preview = _esc((c.get("raw_text") or "")[:6000])
    return f"""
<div class="cmodal-head">
  <span class="dir-chip {chip}">{icon} {label}</span>
  <span class="cmodal-file">{_esc(c.get("filename") or "")}</span>
  <button class="cmodal-x" onclick="closeContract()">✕</button>
</div>
<div class="cmodal-body">
  <form onsubmit="ctrSave('{c['id']}');return false" class="ctr-form">
    <div class="ctr-grid">
      {fld("Client (payer)", "client", c.get("client"))}
      {fld("Agency", "agency", c.get("agency"))}
      {fld("Vendor / Contractor", "vendor", c.get("vendor"))}
      {fld("Contract amount", "amount", c.get("amount"))}
      {fld("Period start", "period_start", c.get("period_start"))}
      {fld("Period end", "period_end", c.get("period_end"))}
      {fld("Project name", "project_name", c.get("project_name"))}
      <label class="ctr-fld"><span>Side</span>
        <select class="slot" name="side">
          <option value="sea"{' selected' if c.get('side')=='sea' else ''}>SEA ↔ Cheil</option>
          <option value="vendor"{' selected' if c.get('side')=='vendor' else ''}>Cheil ↔ Vendor</option>
        </select></label>
    </div>
    <div class="ctr-actions">
      <button class="btn btn-primary btn-sm" type="submit">💾 Save fields</button>
      <a class="btn btn-secondary btn-sm" href="/sow/contract/file?id={c['id']}" target="_blank">⬇ Original</a>
      <button class="btn btn-danger btn-sm" type="button" onclick="ctrPost('/sow/contract/delete',{{id:'{c['id']}'}})">🗑 Delete</button>
    </div>
  </form>
  {link_html}
  <details class="ctr-prev"><summary>📄 Document text preview</summary><pre>{preview}</pre></details>
</div>"""


_CTR_CSS = """
.ctr-dropzone{display:block;width:100%;text-align:center;background:var(--surface-2,var(--surface));border:2px dashed var(--border-bright);border-radius:var(--radius-lg);padding:16px 18px;margin-bottom:16px;cursor:pointer;color:var(--text-muted);font-size:.82rem;transition:.15s}
.ctr-dropzone:hover{border-color:var(--accent);color:var(--text)}
.ctr-dropzone b{color:var(--text)}
.ctr-dropzone.drag-over{border-color:var(--accent);background:rgba(56,189,248,.10);color:var(--text)}
.ctr-groups{display:flex;flex-direction:column;gap:16px}
.ctr-group{background:var(--surface-2,var(--surface));border:1px solid var(--border);border-radius:var(--radius-xl);padding:12px}
.ctr-group>.ctr-card{border-left:3px solid #38bdf8}
.ctr-children{display:flex;flex-direction:column;gap:8px;margin:10px 0 2px 20px;padding:8px;border-left:2px dashed var(--border);border-radius:0 var(--radius-md) var(--radius-md) 0;min-height:20px;transition:.15s}
.ctr-children.drag-over,.ctr-orphans.drag-over{background:rgba(56,189,248,.10);border-color:var(--accent)}
.ctr-children .ctr-card{border-left:3px solid #fb923c}
.ctr-drop-hint{font-size:.72rem;color:var(--text-muted);font-style:italic;padding:6px 4px}
.ctr-orphans{margin-top:16px;padding:12px;border:1px dashed var(--border-bright);border-radius:var(--radius-lg);display:flex;flex-direction:column;gap:8px;transition:.15s}
.ctr-orphan-hd{font-size:.74rem;font-weight:700;color:var(--text)}
.ctr-orphan-hd span{font-weight:400;color:var(--text-muted)}
.ctr-card{position:relative;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:14px 16px;transition:.15s}
.ctr-card:hover{border-color:var(--accent);box-shadow:var(--shadow-md)}
.ctr-card[draggable="true"]{padding-left:30px}
.ctr-card.dragging{opacity:.45}
.ctr-grip{position:absolute;left:9px;top:50%;transform:translateY(-50%);color:var(--text-muted);cursor:grab;font-size:1rem;letter-spacing:-2px}
.ctr-top{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-bottom:6px}
.ctr-amt{font-weight:800;color:var(--success);font-variant-numeric:tabular-nums;font-size:.86rem}
.ctr-title{font-weight:700;font-size:.9rem;color:var(--text);margin-bottom:3px}
.ctr-meta{font-size:.74rem;color:var(--text-muted)}
.ctr-kidlist{margin:8px 0 0;padding-left:18px;font-size:.82rem}
.ctr-kidlist li{margin-bottom:4px}
.cmodal-ov{position:fixed;inset:0;background:rgba(0,0,0,.55);display:none;align-items:flex-start;justify-content:center;z-index:200;padding:40px 16px;overflow-y:auto}
.cmodal-ov.show{display:flex}
.cmodal{background:var(--surface);border:1px solid var(--border-bright);border-radius:var(--radius-xl);max-width:720px;width:100%;box-shadow:var(--shadow-lg)}
.cmodal-head{display:flex;align-items:center;gap:10px;padding:14px 18px;border-bottom:1px solid var(--border)}
.cmodal-file{font-size:.76rem;color:var(--text-muted);margin-left:auto;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;max-width:50%}
.cmodal-x{background:none;border:none;color:var(--text-muted);font-size:1.1rem;cursor:pointer;padding:2px 6px}
.cmodal-x:hover{color:var(--danger)}
.cmodal-body{padding:18px}
.ctr-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 14px}
.ctr-fld{display:flex;flex-direction:column;gap:3px}
.ctr-fld>span{font-size:.68rem;text-transform:uppercase;letter-spacing:.04em;color:var(--text-muted)}
.ctr-fld .slot{width:100%}
.ctr-actions{display:flex;gap:8px;margin-top:14px;flex-wrap:wrap}
.ctr-linkbox,.ctr-linked{margin-top:16px;padding-top:14px;border-top:1px solid var(--border);display:flex;flex-direction:column;gap:8px;font-size:.82rem}
.ctr-linked{flex-direction:row;align-items:center;gap:10px}
.ctr-prev{margin-top:14px}
.ctr-prev summary{cursor:pointer;font-size:.8rem;color:var(--text-muted)}
.ctr-prev pre{white-space:pre-wrap;font-size:.72rem;max-height:300px;overflow:auto;background:var(--surface-2,var(--surface));border:1px solid var(--border);border-radius:8px;padding:10px;margin-top:8px}
@media(max-width:768px){.ctr-children{margin-left:8px}.ctr-grid{grid-template-columns:1fr}}
"""

_CTR_JS = """<script>
function closeContract(){document.getElementById('cmodalOv').classList.remove('show');}
function openContract(id){
  fetch('/sow/contract?frag=1&id='+encodeURIComponent(id))
    .then(function(r){return r.text();})
    .then(function(h){document.getElementById('cmodal').innerHTML=h;
      document.getElementById('cmodalOv').classList.add('show');});
}
function ctrPost(url,obj){
  var b=Object.keys(obj).map(function(k){return k+'='+encodeURIComponent(obj[k]);}).join('&');
  fetch(url,{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:b})
    .then(function(){location.reload();});
}
function ctrSave(id){
  var f=document.querySelector('#cmodal form.ctr-form');
  var b='id='+encodeURIComponent(id);
  f.querySelectorAll('input,select').forEach(function(el){b+='&'+el.name+'='+encodeURIComponent(el.value);});
  fetch('/sow/contract/save',{method:'POST',headers:{'Content-Type':'application/x-www-form-urlencoded'},body:b})
    .then(function(){location.reload();});
}
function ctrAssign(id){
  var sel=document.getElementById('lnk_'+id);
  if(!sel||!sel.value)return;
  ctrPost('/sow/contract/assign',{vendor:id,sea:sel.value});
}
function ctrUpload(files){
  if(!files||!files.length)return;
  var fd=new FormData(); fd.append('file', files[0]);
  fetch('/sow/contract/upload',{method:'POST',body:fd})
    .then(function(r){ location.href = r.url || '/sow'; });
}
var ctrDragId=null;
document.addEventListener('dragstart',function(e){
  var card=e.target.closest('.ctr-card[draggable="true"]');
  if(!card){return;}
  ctrDragId=card.getAttribute('data-cid');
  e.dataTransfer.effectAllowed='move';
  try{e.dataTransfer.setData('text/plain',ctrDragId);}catch(err){}
  card.classList.add('dragging');
});
document.addEventListener('dragend',function(e){
  var card=e.target.closest('.ctr-card'); if(card)card.classList.remove('dragging');
  ctrDragId=null;
});
document.addEventListener('dragover',function(e){
  var t=e.target.closest('[data-seadrop],[data-filedrop]');
  if(t){e.preventDefault(); t.classList.add('drag-over');}
});
document.addEventListener('dragleave',function(e){
  var t=e.target.closest('[data-seadrop],[data-filedrop]');
  if(t && !t.contains(e.relatedTarget))t.classList.remove('drag-over');
});
document.addEventListener('drop',function(e){
  var fzone=e.target.closest('[data-filedrop]');
  if(fzone){e.preventDefault(); fzone.classList.remove('drag-over');
    if(e.dataTransfer.files&&e.dataTransfer.files.length)ctrUpload(e.dataTransfer.files);
    return;}
  var t=e.target.closest('[data-seadrop]');
  if(!t)return;
  e.preventDefault(); t.classList.remove('drag-over');
  if(e.dataTransfer.files&&e.dataTransfer.files.length){ctrUpload(e.dataTransfer.files); return;}
  var vid=ctrDragId||(e.dataTransfer&&e.dataTransfer.getData('text/plain'));
  if(!vid)return;
  ctrPost('/sow/contract/assign',{vendor:vid,sea:t.getAttribute('data-sea')||''});
});
document.addEventListener('DOMContentLoaded',function(){
  var ov=document.getElementById('cmodalOv');
  if(ov)ov.addEventListener('click',function(e){if(e.target===ov)closeContract();});
  var dz=document.getElementById('ctrDrop'), fi=document.getElementById('ctrFile');
  if(dz&&fi){
    dz.addEventListener('click',function(){fi.click();});
    fi.addEventListener('change',function(){ctrUpload(fi.files);});
  }
  var m=location.search.match(/[?&]newc=([^&]+)/);
  if(m)openContract(decodeURIComponent(m[1]));
});
</script>"""


def handle(method, path, body, ctx):
    user = ctx.get("user", "guest")

    if method == "GET" and path == "/sow":
        return ("html", _render_landing(user))

    # ── uploaded contracts ────────────────────────────────────────────────
    if method == "GET" and path == "/sow/contract":
        data = _load(user)
        return ("html", _render_contract_frag(user, data, _f(body, "id")))

    if method == "POST" and path == "/sow/contract/upload":
        raw = body.get("__raw__") or body.get("__raw_handler__")
        files = _read_uploaded_files(raw) if raw else []
        if not files:
            return ("redirect", "/sow")
        fn, content, _mime = files[0]
        fn = _safe_filename(fn)
        ext = _safe_ext(fn)
        text = _extract_text(content, ext)
        fields = _extract_fields(text)
        cid = uuid.uuid4().hex[:8]
        data = _load(user)
        rec = {"id": cid, "filename": fn, "ext": ext,
               "uploaded": datetime.now().isoformat(timespec="seconds"),
               "raw_text": text[:200000], "linked_id": None}
        rec.update({k: fields.get(k, "") for k in
                    ("client", "agency", "vendor", "amount",
                     "period_start", "period_end", "project_name", "side")})
        try:
            os.makedirs(_contracts_dir(user), exist_ok=True)
            with open(_contract_file_path(user, rec), "wb") as fp:
                fp.write(content)
        except OSError:
            return ("redirect", "/sow")
        data.setdefault("contracts", []).append(rec)
        _save(user, data)
        return ("redirect", f"/sow?newc={cid}")

    if method == "POST" and path == "/sow/contract/save":
        data = _load(user)
        c = _contract_by_id(data, _f(body, "id"))
        if c:
            for k in ("client", "agency", "vendor", "amount",
                      "period_start", "period_end", "project_name"):
                c[k] = _f(body, k)
            c["side"] = "vendor" if _f(body, "side") == "vendor" else "sea"
            _save(user, data)
        return ("redirect", "/sow")

    if method == "POST" and path == "/sow/contract/assign":
        # Align a vendor contract under a SEA↔Cheil parent (1:many). An empty
        # or invalid `sea` unlinks. `vendor` may currently be tagged either
        # side; assigning it under a SEA also forces its side to vendor.
        data = _load(user)
        v = _contract_by_id(data, _f(body, "vendor"))
        sea = _contract_by_id(data, _f(body, "sea"))
        if v:
            if sea and sea.get("side") == "sea" and sea["id"] != v["id"]:
                v["side"] = "vendor"
                v["linked_id"] = sea["id"]
            else:
                v["linked_id"] = None
            _save(user, data)
        return ("redirect", "/sow")

    if method == "POST" and path == "/sow/contract/unlink":
        data = _load(user)
        a = _contract_by_id(data, _f(body, "id"))
        if a:
            a["linked_id"] = None
            _save(user, data)
        return ("redirect", "/sow")

    if method == "POST" and path == "/sow/contract/delete":
        data = _load(user)
        c = _contract_by_id(data, _f(body, "id"))
        if c:
            # deleting a SEA parent orphans its vendor children
            for other in data["contracts"]:
                if other.get("linked_id") == c["id"]:
                    other["linked_id"] = None
            try:
                os.remove(_contract_file_path(user, c))
            except OSError:
                pass
            data["contracts"] = [x for x in data["contracts"] if x["id"] != c["id"]]
            _save(user, data)
        return ("redirect", "/sow")

    if method == "GET" and path == "/sow/contract/file":
        data = _load(user)
        c = _contract_by_id(data, _f(body, "id"))
        if not c:
            return ("redirect", "/sow")
        try:
            with open(_contract_file_path(user, c), "rb") as fp:
                blob = fp.read()
        except OSError:
            return ("redirect", "/sow")
        mime = _CONTRACT_MIME.get(c.get("ext"), "application/octet-stream")
        return ("file_inline", blob, mime, c.get("filename") or f"{c['id']}.{c.get('ext')}")

    if method == "GET" and path.startswith("/sow/types"):
        d = _f(body, "dir")
        return ("html", _render_types(user, "agy" if d == "agy" else "sea"))

    if method == "GET" and path == "/sow/vendors":
        return ("html", _render_vendors(user, saved=_f(body, "saved") == "1"))

    if method == "GET" and path == "/sow/people":
        return ("html", _render_people(user, saved=_f(body, "saved") == "1"))

    if method == "GET" and path == "/sow/person":
        pid = _f(body, "id")
        data = _load(user)
        person = next((p for p in data["people"] if p["id"] == pid), None)
        return ("html", _render_person_detail(user, person or {},
                                              saved=_f(body, "saved") == "1"))

    if method == "POST" and path == "/sow/person/save":
        data = _load(user)
        pid = _f(body, "id")
        name = _f(body, "name")
        if not name:
            return ("redirect", "/sow/people")
        cur = next((p for p in data["people"] if p["id"] == pid), None)
        linked = body.get("linked_sows") or []
        if not isinstance(linked, list):
            linked = [linked]
        rec = _migrate_person({"id": pid or uuid.uuid4().hex[:8], "name": name,
                               "sell_hr": ""})
        for k in ("affiliation", "role_title", "project", "location",
                  "sell_hr", "sell_mo", "client_duration", "client_budget", "client_po",
                  "cost_hr", "cost_mo", "partner_duration", "partner_cost", "partner_po",
                  "salary_mo", "cheil_since", "salary_oh", "ebita",
                  "email_cheil", "email_samsung", "pc", "svpn"):
            rec[k] = _f(body, k)
        rec["affiliation"] = rec["affiliation"] or "Cheil"
        rec["linked_sows"] = [str(x) for x in linked if x]
        if cur:
            data["people"][data["people"].index(cur)] = rec
        else:
            data["people"].append(rec)
        _save(user, data)
        return ("redirect", f"/sow/person?id={rec['id']}&saved=1")

    if method == "POST" and path == "/sow/person/delete":
        data = _load(user)
        pid = _f(body, "id")
        person = next((p for p in data["people"] if p["id"] == pid), None)
        if person and _person_doc_count(data, person) == 0:
            data["people"] = [p for p in data["people"] if p["id"] != pid]
            _save(user, data)
        return ("redirect", "/sow/people")

    if method == "GET" and path.startswith("/sow/xlsx"):
        sid = _f(body, "id")
        data = _load(user)
        sow = next((s for s in data["sows"] if s["id"] == sid), None)
        if not sow or TYPES.get(_sow_type(sow), {}).get("kind") != "est":
            return ("redirect", "/sow")
        blob = _build_est_xlsx(sow)
        safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in (sow.get("title") or "Estimation"))[:60].strip()
        return ("file_inline", blob,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                f"Cheil_Estimation_{safe}.xlsx")

    if method == "POST" and path == "/sow/vendor/save":
        data = _load(user)
        vid = _f(body, "id")
        name = _f(body, "name")
        if not name:
            return ("redirect", "/sow/vendors")
        rec = {"id": vid or uuid.uuid4().hex[:8], "name": name,
               "entity_line": _f(body, "entity_line"), "msa_date": _f(body, "msa_date")}
        cur = next((v for v in data["vendors"] if v["id"] == vid), None)
        if cur:
            data["vendors"][data["vendors"].index(cur)] = rec
        else:
            data["vendors"].append(rec)
        _save(user, data)
        return ("redirect", "/sow/vendors?saved=1")

    if method == "POST" and path == "/sow/vendor/delete":
        data = _load(user)
        vid = _f(body, "id")
        if any(s.get("vendor_id") == vid for s in data["sows"]):
            return ("redirect", "/sow/vendors")
        data["vendors"] = [v for v in data["vendors"] if v["id"] != vid]
        _save(user, data)
        return ("redirect", "/sow/vendors")

    if method == "GET" and path == "/sow/asset/logo":
        logo = os.path.join(_ASSETS, "cheil_logo.png")
        if os.path.exists(logo):
            return ("binary", open(logo, "rb").read(), "image/png")
        return ("html", "", )

    def _editor_for(kind):
        return {"sow": _render_doc_editor, "est": _render_est_editor}.get(kind, _render_agreement_editor)

    if method == "GET" and path.startswith("/sow/new"):
        tkey = _f(body, "type")
        if tkey not in TYPES:
            return ("redirect", "/sow")
        return ("html", _editor_for(TYPES[tkey]["kind"])(user, {}, tkey))

    if method == "GET" and path.startswith("/sow/edit"):
        # GET dispatch strips the query string; params arrive as the body dict.
        sid = _f(body, "id")
        data = _load(user)
        sow = next((s for s in data["sows"] if s["id"] == sid), None)
        if not sow:
            return ("redirect", "/sow")
        tkey = _sow_type(sow)
        return ("html", _editor_for(TYPES[tkey]["kind"])(user, sow, tkey, saved=_f(body, "saved") == "1"))

    if method == "POST" and path == "/sow/save":
        data = _load(user)
        sid = _f(body, "id") or uuid.uuid4().hex[:10]
        tkey = _f(body, "type")
        t = TYPES.get(tkey) or TYPES["sea_sow"]
        try:
            resources = json.loads(_f(body, "resources_json") or "[]")
            assert isinstance(resources, list)
        except Exception:
            resources = []
        try:
            overrides = json.loads(_f(body, "schedule_overrides") or "{}")
            assert isinstance(overrides, dict)
            overrides = {str(k): float(v) for k, v in overrides.items()}
        except Exception:
            overrides = {}
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
        if t["kind"] == "est":
            try:
                est_rows = json.loads(_f(body, "rows_json") or "[]")
                assert isinstance(est_rows, list)
            except Exception:
                est_rows = []
            rec = {
                "id": sid, "type": tkey, "direction": t["dir"], "kind": "est",
                "title": _f(body, "title"), "project_name": _f(body, "project_name"),
                "period_label": _f(body, "period_label"),
                "months": _f(body, "months") or "0",
                "rows": est_rows,
                "created": (sow or {}).get("created") or datetime.now().isoformat(),
                "updated": datetime.now().isoformat(),
            }
            if sow:
                data["sows"][data["sows"].index(sow)] = rec
            else:
                data["sows"].append(rec)
            _save(user, data)
            return ("redirect", f"/sow/edit?id={sid}&saved=1")
        if t["kind"] != "sow":
            vend = next((v for v in data["vendors"] if v["id"] == vendor_id), None)
            label = "MSA" if t["kind"] == "msa" else "NDA"
            rec = {
                "id": sid, "type": tkey, "direction": t["dir"], "kind": t["kind"],
                "date": _f(body, "date"), "vendor_id": vendor_id,
                "title": f"{label} — {(vend or {}).get('name') or 'vendor TBD'}",
                "created": (sow or {}).get("created") or datetime.now().isoformat(),
                "updated": datetime.now().isoformat(),
            }
            if sow:
                data["sows"][data["sows"].index(sow)] = rec
            else:
                data["sows"].append(rec)
            _save(user, data)
            return ("redirect", f"/sow/edit?id={sid}&saved=1")
        rec = {
            "id": sid,
            "type": tkey if tkey in TYPES else "sea_sow",
            "direction": t["dir"],
            "res_mode": _f(body, "res_mode") if _f(body, "res_mode") in ("monthly", "hourly") else t["mode"],
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
            "resources": resources,
            "schedule_overrides": overrides,
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
        kind = TYPES[_sow_type(sow)]["kind"]
        builder = {"sow": _build_docx, "msa": _build_msa_docx, "nda": _build_nda_docx}[kind]
        blob = builder(sow, vendor)
        safe = "".join(c if c.isalnum() or c in " ._-" else "_" for c in (sow.get("title") or "SOW"))[:60].strip()
        prefix = {"sow": "Cheil_SOW", "msa": "Cheil_MSA", "nda": "Cheil_NDA"}[kind]
        fname = f"{prefix}_{safe}_{sow.get('date') or date.today().isoformat()}.docx"
        return ("file_inline", blob,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document", fname)

    return ("html", "<h2>404 Not Found</h2>")
