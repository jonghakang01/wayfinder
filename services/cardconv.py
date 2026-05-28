import csv, io, json, os, re, base64
from datetime import date, datetime
from pathlib import Path

import openpyxl

DATA_DIR   = Path(os.path.expanduser("~/.appdata/cardconv"))
KW_FILE    = DATA_DIR / "keywords.json"
HIST_FILE  = DATA_DIR / "history.json"
OUT_DIR    = DATA_DIR / "outputs"
TOKENS_DIR = DATA_DIR / "tokens"
CREDS_FILE = DATA_DIR / "google_credentials.json"
TEMPLATE   = Path(os.path.expanduser(
    "~/Desktop/US업무/법카 정산/Automation/for upload.xlsx"
))

SCOPES = ['https://www.googleapis.com/auth/drive.file']
ADMIN  = "jongha.kang"
TARGET_NAMES = {"JONG KANG", "JONGHA KANG"}

META = {
    "name": "Card Converter",
    "path": "/cardconv",
    "icon": "💳",
    "description": "Corporate card CSV → SAP upload xlsx",
    "admin_only": True,
}

DEFAULT_KW = [
    {"kw": "STARBUCKS",         "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "CAFE",              "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "COFFEE",            "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "BAKERY",            "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "SWEETGREEN",        "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "SRA CAFE",          "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "KOBRICK",           "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "DOORDASH",          "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "GRUBHUB",           "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "WHOLEFDS",          "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "TRADER JOE",        "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "RESTAURANT",        "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "GRILL",             "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "PIZZA",             "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "BURGER",            "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "SUSHI",             "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "PARIS BAGUETTE",    "gl": 53410177, "ser": "160", "purpose": "Coffee, Snack and meal"},
    {"kw": "AMAZON",            "gl": 53210177, "ser": "021", "purpose": "Office supply purchases"},
    {"kw": "HOME DEPOT",        "gl": 53210177, "ser": "021", "purpose": "Office supply purchases"},
    {"kw": "BEST BUY",          "gl": 53210177, "ser": "021", "purpose": "Office supply purchases"},
    {"kw": "TARGET",            "gl": 53210177, "ser": "021", "purpose": "Office supply purchases"},
    {"kw": "COSTCO",            "gl": 53210177, "ser": "021", "purpose": "Office supply purchases"},
    {"kw": "NESPRESSO",         "gl": 53210177, "ser": "021", "purpose": "Office supply purchases"},
    {"kw": "PG&E",              "gl": 53210177, "ser": "021", "purpose": "Office Utilities"},
    {"kw": "UBER",              "gl": 53270377, "ser": "306", "purpose": "Uber travel"},
    {"kw": "LYFT",              "gl": 53270377, "ser": "306", "purpose": "Lyft travel"},
    {"kw": "ENTERPRISE",        "gl": 53270377, "ser": "306", "purpose": "Car rental"},
    {"kw": "HERTZ",             "gl": 53270377, "ser": "306", "purpose": "Car rental"},
    {"kw": "AVIS",              "gl": 53270377, "ser": "306", "purpose": "Car rental"},
    {"kw": "CHEVRON",           "gl": 53270377, "ser": "306", "purpose": "Gas for car"},
    {"kw": "SHELL",             "gl": 53270377, "ser": "306", "purpose": "Gas for car"},
    {"kw": "ROBBIE",            "gl": 53270377, "ser": "306", "purpose": "Gas for car"},
    {"kw": "GARAGE",            "gl": 53270377, "ser": "306", "purpose": "Parking"},
    {"kw": "PARKING",           "gl": 53270377, "ser": "306", "purpose": "Parking"},
    {"kw": "FASTRAK",           "gl": 53270377, "ser": "306", "purpose": "Car Toll"},
    {"kw": "TOLL",              "gl": 53270377, "ser": "306", "purpose": "Rental Toll"},
    {"kw": "SPOTHERO",          "gl": 53270377, "ser": "306", "purpose": "Parking"},
    {"kw": "CAR WASH",          "gl": 53270377, "ser": "306", "purpose": "Car wash for Car"},
    {"kw": "XPRESS",            "gl": 53270377, "ser": "306", "purpose": "Car wash for Car"},
    {"kw": "HYATT",             "gl": 53270377, "ser": "306", "purpose": "Hotel accommodation"},
    {"kw": "MARRIOTT",          "gl": 53270377, "ser": "306", "purpose": "Hotel accommodation"},
    {"kw": "HILTON",            "gl": 53270377, "ser": "306", "purpose": "Hotel accommodation"},
    {"kw": "HOTEL",             "gl": 53270377, "ser": "306", "purpose": "Hotel accommodation"},
    {"kw": "UNITED AIRLINES",   "gl": 53270377, "ser": "306", "purpose": "Flight travel"},
    {"kw": "KOREAN AIR",        "gl": 53270377, "ser": "306", "purpose": "Flight travel"},
    {"kw": "SINGAPORE AIRLINES","gl": 53270377, "ser": "306", "purpose": "Flight travel"},
    {"kw": "BRITISH AIRWAYS",   "gl": 53270377, "ser": "306", "purpose": "Flight travel"},
    {"kw": "AMERICAN AIRLINES", "gl": 53270377, "ser": "306", "purpose": "Flight travel"},
    {"kw": "TOTAL WINE",        "gl": 53410103, "ser": "159", "purpose": "Purchase for client"},
    {"kw": "WINE",              "gl": 53410103, "ser": "159", "purpose": "Purchase for client"},
    {"kw": "OPENAI",            "gl": 53311577, "ser": "085", "purpose": "AI subscription"},
    {"kw": "ANTHROPIC",         "gl": 53311577, "ser": "085", "purpose": "AI subscription"},
    {"kw": "CLAUDE",            "gl": 53311577, "ser": "085", "purpose": "AI subscription"},
    {"kw": "CHATGPT",           "gl": 53311577, "ser": "085", "purpose": "AI subscription"},
    {"kw": "PERPLEXITY",        "gl": 53311577, "ser": "085", "purpose": "AI subscription"},
    {"kw": "LOVABLE",           "gl": 53311577, "ser": "085", "purpose": "AI subscription"},
    {"kw": "MANUS AI",          "gl": 53311577, "ser": "085", "purpose": "AI subscription"},
    {"kw": "GOOGLE *GOOGLE",    "gl": 53311577, "ser": "085", "purpose": "AI subscription"},
    {"kw": "GOOGLE ONE",        "gl": 53311577, "ser": "085", "purpose": "AI subscription"},
    {"kw": "RHINO NETWORK",     "gl": 53290177, "ser": "052", "purpose": "Office Network setup"},
    {"kw": "RITZ",              "gl": 53470177, "ser": "289", "purpose": "Coffee, Snack and meal"},
    {"kw": "JO MALONE",         "gl": 53470177, "ser": "289", "purpose": "Coffee, Snack and meal"},
]

FIXED = {
    "receipt_type": "D",
    "employee_id":  20170321,
    "payee":        "A0016672",
    "domestic":     "D",
    "currency":     "USD",
    "tax_code":     "VV",
    "cost_center":  "AG010238",
}


# ── Data helpers ─────────────────────────────────────────────────────────────

def _ensure_dirs():
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TOKENS_DIR.mkdir(parents=True, exist_ok=True)


def _load_kw():
    _ensure_dirs()
    if KW_FILE.exists():
        try:
            return json.loads(KW_FILE.read_text())
        except Exception:
            pass
    _save_kw(DEFAULT_KW)
    return DEFAULT_KW


def _save_kw(kws):
    _ensure_dirs()
    KW_FILE.write_text(json.dumps(kws, ensure_ascii=False, indent=2))


def _load_hist():
    if HIST_FILE.exists():
        try:
            return json.loads(HIST_FILE.read_text())
        except Exception:
            pass
    return []


def _save_hist(hist):
    HIST_FILE.write_text(json.dumps(hist, ensure_ascii=False, indent=2))


def _add_hist(entry: dict):
    hist = _load_hist()
    hist.insert(0, entry)
    _save_hist(hist[:20])


def _receipts_file(username: str) -> Path:
    return DATA_DIR / f"receipts_{username}.json"


def _load_receipts(username: str) -> list:
    f = _receipts_file(username)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return []


def _save_receipts(username: str, receipts: list):
    _ensure_dirs()
    _receipts_file(username).write_text(json.dumps(receipts, ensure_ascii=False, indent=2))


# ── Drive OAuth helpers ───────────────────────────────────────────────────────

def _get_creds(username: str):
    """Load and auto-refresh OAuth credentials for user. Returns None if not connected."""
    _ensure_dirs()
    token_file = TOKENS_DIR / f"{username}.json"
    if not CREDS_FILE.exists() or not token_file.exists():
        return None
    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        creds = Credentials.from_authorized_user_file(str(token_file), SCOPES)
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
            token_file.write_text(creds.to_json())
        if creds and creds.valid:
            return creds
    except Exception:
        pass
    return None


def _is_drive_connected(username: str) -> bool:
    return _get_creds(username) is not None


def _get_drive_service(username: str):
    from googleapiclient.discovery import build
    creds = _get_creds(username)
    if not creds:
        return None
    return build('drive', 'v3', credentials=creds)


def _get_or_create_folder(service, name: str, parent_id: str = None) -> str:
    """Return Drive folder ID, creating it if it doesn't exist."""
    q = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
    if parent_id:
        q += f" and '{parent_id}' in parents"
    res = service.files().list(q=q, fields='files(id)').execute()
    files = res.get('files', [])
    if files:
        return files[0]['id']
    meta = {'name': name, 'mimeType': 'application/vnd.google-apps.folder'}
    if parent_id:
        meta['parents'] = [parent_id]
    return service.files().create(body=meta, fields='id').execute()['id']


def _upload_file_to_drive(username: str, file_bytes: bytes, filename: str,
                           mime_type: str, folder_ym: str) -> tuple:
    """Upload to Drive under Wayfinder/Receipts/YYYY-MM/. Returns (file_id, drive_url)."""
    from googleapiclient.http import MediaIoBaseUpload
    service = _get_drive_service(username)
    if not service:
        return None, None
    wayfinder_id = _get_or_create_folder(service, 'Wayfinder')
    receipts_id  = _get_or_create_folder(service, 'Receipts', wayfinder_id)
    month_id     = _get_or_create_folder(service, folder_ym, receipts_id)
    media  = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type)
    result = service.files().create(
        body={'name': filename, 'parents': [month_id]},
        media_body=media,
        fields='id,webViewLink'
    ).execute()
    fid = result.get('id')
    url = result.get('webViewLink') or f'https://drive.google.com/file/d/{fid}/view'
    return fid, url


# ── OCR ───────────────────────────────────────────────────────────────────────

def _ocr_receipt(file_bytes: bytes, mime_type: str) -> dict:
    """OCR receipt using Claude Vision. Returns {date, amount, merchant} or {}."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return {}
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        b64 = base64.standard_b64encode(file_bytes).decode()
        if mime_type == 'application/pdf':
            block = {
                "type": "document",
                "source": {"type": "base64", "media_type": "application/pdf", "data": b64}
            }
        else:
            block = {
                "type": "image",
                "source": {"type": "base64", "media_type": mime_type, "data": b64}
            }
        resp = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=256,
            messages=[{"role": "user", "content": [
                block,
                {"type": "text", "text": (
                    'Extract from this receipt: date (YYYY-MM-DD), total amount (number only), '
                    'merchant name. Return JSON: {"date": "YYYY-MM-DD", "amount": 0.00, "merchant": "name"}'
                )}
            ]}]
        )
        text = resp.content[0].text.strip()
        m = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if m:
            return json.loads(m.group(0))
    except Exception:
        pass
    return {}


# ── Multipart file parser ─────────────────────────────────────────────────────

_MIME_MAP = {
    'jpg': 'image/jpeg', 'jpeg': 'image/jpeg',
    'png': 'image/png',  'pdf': 'application/pdf',
    'gif': 'image/gif',  'webp': 'image/webp',
}


def _parse_multipart_files(raw_handler) -> list:
    """Parse multipart body; returns list of (filename, bytes, mime_type)."""
    ct = raw_handler.headers.get("Content-Type", "")
    m  = re.search(r'boundary=([^\s;]+)', ct)
    if not m:
        return []
    boundary = ("--" + m.group(1)).encode()
    length   = int(raw_handler.headers.get("Content-Length", 0))
    data     = raw_handler.rfile.read(length)
    files    = []
    for part in data.split(boundary):
        if b'filename="' not in part:
            continue
        fn_m = re.search(rb'filename="([^"]+)"', part)
        if not fn_m:
            continue
        filename = fn_m.group(1).decode('utf-8', errors='replace')
        hdr_end  = part.find(b"\r\n\r\n")
        if hdr_end == -1:
            continue
        content = part[hdr_end + 4:]
        if content.endswith(b"\r\n"):
            content = content[:-2]
        ext  = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
        mime = _MIME_MAP.get(ext, 'application/octet-stream')
        if content:
            files.append((filename, content, mime))
    return files


# ── Conversion logic ──────────────────────────────────────────────────────────

def _classify(merchant: str, rules: list):
    m = merchant.upper()
    for r in rules:
        if r["kw"].upper() in m:
            return r["gl"], r["ser"], r["purpose"]
    return None, None, None


def _fmt_card(acct: str):
    acct = re.sub(r'\D', '', acct)
    if len(acct) >= 8:
        masked = acct[:4] + "********" + acct[-4:]
        supp   = f"{acct[:4]}-{acct[4:10]}-{acct[10:]}" if len(acct) == 15 else acct
    else:
        masked = acct; supp = acct
    return masked, supp


def _name_parts(full: str):
    p = full.strip().split()
    return (p[-1], " ".join(p[:-1])) if len(p) >= 2 else (full, "")


def _parse_date(s: str):
    for fmt in ("%Y-%m-%d", "%m/%d/%Y", "%m/%d/%y"):
        try:
            return datetime.strptime(s.strip(), fmt)
        except ValueError:
            pass
    return None


def convert(csv_bytes: bytes, filename: str, username: str = None) -> tuple:
    """Returns (xlsx_bytes, out_filename, total_rows, unmatched_count)."""
    rules  = _load_kw()
    today  = date.today()
    m      = re.search(r'(\d{4}-\d{2}-\d{2})', filename)
    tag    = m.group(1) if m else today.strftime("%Y-%m-%d")
    out_fn = f"for_upload_{tag}.xlsx"

    if not TEMPLATE.exists():
        alts = list(Path.home().rglob("for upload.xlsx"))
        if not alts:
            raise FileNotFoundError("Template 'for upload.xlsx' not found on server.")
        template_path = alts[0]
    else:
        template_path = TEMPLATE

    text   = csv_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    rows   = [r for r in reader if r.get("Card Member Name","").strip().upper() in TARGET_NAMES]

    wb = openpyxl.load_workbook(template_path)
    ws = wb["sheetMst"]

    start = 2
    while ws.cell(start, 1).value is not None:
        start += 1

    posting_dt = datetime(today.year, today.month, today.day)
    unmatched  = 0

    # Build receipt lookup: (date_str, rounded_amount) → receipt record
    receipts_map = {}
    if username:
        for r in _load_receipts(username):
            rdate   = r.get("ocr_date")
            ramount = r.get("ocr_amount")
            if rdate and ramount is not None:
                try:
                    receipts_map[(rdate, round(float(ramount), 2))] = r
                except (ValueError, TypeError):
                    pass

    for row in rows:
        merchant = row.get("Merchant Name", "").strip()
        dba      = row.get("Merchant Doing Business As", "").strip()
        vendor   = dba if (dba and dba != merchant) else merchant
        try:
            amount = float(row.get("Amount", 0))
        except ValueError:
            amount = 0.0
        inv_dt       = _parse_date(row.get("Date", ""))
        masked, supp = _fmt_card(row.get("Account Number", ""))
        last, first  = _name_parts(row.get("Card Member Name", ""))

        gl, ser, purpose = _classify(vendor, rules)
        if gl is None:
            gl, ser, purpose = _classify(merchant, rules)
        if gl is None:
            unmatched += 1
            gl, ser, purpose = 53410177, "160", "Coffee, Snack and meal"

        ws.cell(start,  1).value = FIXED["receipt_type"]
        ws.cell(start,  2).value = FIXED["employee_id"]
        ws.cell(start,  3).value = FIXED["payee"]
        ws.cell(start,  4).value = None
        ws.cell(start,  5).value = inv_dt
        ws.cell(start,  6).value = FIXED["domestic"]
        ws.cell(start,  7).value = vendor
        ws.cell(start,  8).value = posting_dt
        ws.cell(start,  9).value = gl
        ws.cell(start, 10).value = ser
        ws.cell(start, 11).value = FIXED["currency"]
        ws.cell(start, 12).value = FIXED["tax_code"]
        ws.cell(start, 13).value = None
        ws.cell(start, 14).value = amount
        ws.cell(start, 15).value = FIXED["cost_center"]
        ws.cell(start, 16).value = None
        ws.cell(start, 17).value = None
        ws.cell(start, 18).value = purpose
        ws.cell(start, 19).value = None
        ws.cell(start, 20).value = masked
        ws.cell(start, 21).value = last
        ws.cell(start, 22).value = first
        ws.cell(start, 23).value = supp
        ws.cell(start, 24).value = None
        ws.cell(start, 25).value = None
        ws.cell(start, 26).value = amount

        # Receipt match in column 27
        if receipts_map and inv_dt:
            inv_date_str  = inv_dt.strftime("%Y-%m-%d")
            amt_rounded   = round(amount, 2)
            receipt_match = receipts_map.get((inv_date_str, amt_rounded))
            if not receipt_match:
                for (rdate, ramt), r in receipts_map.items():
                    if rdate == inv_date_str and abs(ramt - amt_rounded) <= 0.01:
                        receipt_match = r
                        break
            if receipt_match:
                fn  = receipt_match.get('filename', '')
                url = receipt_match.get('drive_url', '')
                ws.cell(start, 27).value = f"✅ {fn} ({url})" if url else f"✅ {fn}"
            else:
                ws.cell(start, 27).value = "❌ Missing"

        start += 1

    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()
    (OUT_DIR / out_fn).write_bytes(xlsx_bytes)
    return xlsx_bytes, out_fn, len(rows), unmatched


# ── HTTP handler ──────────────────────────────────────────────────────────────

def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user")
    if user != ADMIN:
        return ("html", "<h2 style='padding:40px;color:#f87171'>Access denied</h2>")

    # Drive OAuth
    if method == "GET" and path == "/cardconv/drive/connect":
        return _handle_drive_connect(user)
    if method == "POST" and path == "/cardconv/drive/auth":
        return _handle_drive_auth(user, body)

    # Receipt upload
    if method == "POST" and path == "/cardconv/receipts/upload":
        return _handle_receipt_upload(user, body)

    # File download
    if method == "GET" and path.startswith("/cardconv/download/"):
        fname = path[len("/cardconv/download/"):]
        fpath = OUT_DIR / fname
        if fpath.exists() and fpath.suffix == ".xlsx":
            return ("file", str(fpath),
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", fname)
        return ("html", "<h2>File not found</h2>", 404)

    # CSV upload
    if method == "POST" and path == "/cardconv/upload":
        return _handle_upload(body, user)

    # Keyword add
    if method == "POST" and path == "/cardconv/keyword/add":
        kw      = (body.get("kw",      [""])[0]).strip().upper()
        gl      = (body.get("gl",      [""])[0]).strip()
        ser     = (body.get("ser",     [""])[0]).strip()
        purpose = (body.get("purpose", [""])[0]).strip()
        if kw and gl and purpose:
            kws = _load_kw()
            if not any(k["kw"] == kw for k in kws):
                kws.insert(0, {"kw": kw, "gl": int(gl), "ser": ser, "purpose": purpose})
                _save_kw(kws)
        return ("redirect", "/cardconv")

    # Keyword delete
    if method == "POST" and path == "/cardconv/keyword/delete":
        kw  = (body.get("kw", [""])[0]).strip().upper()
        kws = [k for k in _load_kw() if k["kw"].upper() != kw]
        _save_kw(kws)
        return ("redirect", "/cardconv")

    return ("html", _render(user))


def _handle_drive_connect(username: str):
    if not CREDS_FILE.exists():
        return ("html", f"<p style='padding:20px;color:var(--danger)'>Credentials file not found: {CREDS_FILE}</p>")
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        auth_url, _ = flow.authorization_url(access_type='offline', prompt='consent')
        return ("html", _render_drive_connect(username, auth_url))
    except Exception as e:
        return ("html", f"<p style='padding:20px;color:var(--danger)'>Drive connect error: {e}</p>")


def _handle_drive_auth(username: str, body):
    raw = body.get("code", "")
    code = (raw[0] if isinstance(raw, list) else str(raw)).strip()
    if not code:
        return ("redirect", "/cardconv")
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
        flow = InstalledAppFlow.from_client_secrets_file(str(CREDS_FILE), SCOPES)
        flow.redirect_uri = 'urn:ietf:wg:oauth:2.0:oob'
        flow.fetch_token(code=code)
        creds = flow.credentials
        _ensure_dirs()
        (TOKENS_DIR / f"{username}.json").write_text(creds.to_json())
    except Exception as e:
        return ("html", f"<p style='padding:20px;color:var(--danger)'>Auth error: {e} "
                        f"<a href='/cardconv' style='color:var(--accent)'>Back</a></p>")
    return ("redirect", "/cardconv")


def _handle_receipt_upload(username: str, body):
    raw = body.get("__raw_handler__")
    if raw is None:
        return ("redirect", "/cardconv")
    if not _is_drive_connected(username):
        return ("html", "<p style='padding:20px;color:var(--danger)'>Connect Google Drive first. "
                        "<a href='/cardconv' style='color:var(--accent)'>Back</a></p>")

    files = _parse_multipart_files(raw)
    if not files:
        return ("redirect", "/cardconv")

    receipts  = _load_receipts(username)
    folder_ym = datetime.now().strftime("%Y-%m")
    supported = {'image/jpeg', 'image/png', 'application/pdf', 'image/gif', 'image/webp'}

    for filename, content, mime_type in files:
        if mime_type not in supported:
            continue
        file_id, drive_url = _upload_file_to_drive(username, content, filename, mime_type, folder_ym)
        ocr = _ocr_receipt(content, mime_type)
        receipts.append({
            "file_id":      file_id,
            "filename":     filename,
            "drive_url":    drive_url,
            "uploaded_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
            "ocr_date":     ocr.get("date"),
            "ocr_amount":   ocr.get("amount"),
            "ocr_merchant": ocr.get("merchant"),
        })

    _save_receipts(username, receipts)
    return ("redirect", "/cardconv")


def _handle_upload(body, user=None):
    raw = body.get("__raw_handler__")
    if raw is None:
        return ("html", "<p>Upload error: no raw handler</p>")
    ct = raw.headers.get("Content-Type", "")
    m  = re.search(r'boundary=([^\s;]+)', ct)
    if not m:
        return ("html", "<p>Upload error: no boundary</p>")
    boundary  = ("--" + m.group(1)).encode()
    length    = int(raw.headers.get("Content-Length", 0))
    data      = raw.rfile.read(length)

    csv_bytes = None
    csv_name  = "upload.csv"
    for part in data.split(boundary):
        if b'filename="' not in part:
            continue
        fn_m = re.search(rb'filename="([^"]+)"', part)
        if fn_m:
            csv_name = fn_m.group(1).decode()
        hdr_end = part.find(b"\r\n\r\n")
        if hdr_end == -1:
            continue
        content = part[hdr_end + 4:]
        if content.endswith(b"\r\n"):
            content = content[:-2]
        csv_bytes = content
        break

    if not csv_bytes:
        return ("redirect", "/cardconv")

    try:
        xlsx_bytes, out_fn, total, unmatched = convert(csv_bytes, csv_name, username=user)
        _add_hist({
            "filename":  out_fn,
            "source":    csv_name,
            "rows":      total,
            "unmatched": unmatched,
            "date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        return ("file_inline", xlsx_bytes,
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                out_fn)
    except Exception as e:
        return ("html", f"<p style='color:red;padding:20px'>Error: {e}</p>")


# ── Render helpers ─────────────────────────────────────────────────────────────

def _render_drive_connect(username: str, auth_url: str) -> str:
    from server import CSS_VER
    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔗 Connect Google Drive · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
</head><body>
<nav>
  <span class="nav-brand">🔗 Connect Google Drive</span>
  <span class="nav-user"><a href="/cardconv" class="nav-back">← Back to Card Converter</a></span>
</nav>
<div class="container" style="max-width:640px">
  <div class="notepad-card">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">Authorize Google Drive Access</span>
    </div>
    <div class="notepad-body" style="padding:28px;display:flex;flex-direction:column;gap:20px">
      <ol style="color:var(--text-muted);font-size:.88rem;line-height:2.2;padding-left:22px">
        <li>Click the button below to open Google authorization page</li>
        <li>Sign in and grant <b style="color:var(--text)">Drive file access</b></li>
        <li>Copy the authorization code shown on that page</li>
        <li>Paste it in the field below and click Confirm</li>
      </ol>
      <a href="{auth_url}" target="_blank" class="btn btn-primary" style="width:fit-content">
        🔗 Open Google Authorization Page
      </a>
      <form method="POST" action="/cardconv/drive/auth" style="display:flex;flex-direction:column;gap:12px">
        <div style="display:flex;flex-direction:column;gap:6px">
          <label style="font-size:.72rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em">Authorization Code</label>
          <input type="text" name="code" placeholder="Paste the code from Google here..." required
            style="padding:10px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface-2);color:var(--text);font-size:.88rem;outline:none">
        </div>
        <button type="submit" class="btn btn-accent" style="width:fit-content">✅ Confirm &amp; Connect</button>
      </form>
    </div>
  </div>
</div>
</body></html>'''


def _render(user: str) -> str:
    from server import CSS_VER
    kws      = _load_kw()
    hist     = _load_hist()
    receipts = _load_receipts(user)
    connected = _is_drive_connected(user)

    # ── Drive status section ──
    if connected:
        drive_status_html = '<span style="font-size:.88rem;font-weight:600;color:var(--success)">✅ Connected</span>'
    else:
        drive_status_html = (
            '<span style="font-size:.88rem;font-weight:600;color:var(--danger)">❌ Not connected</span>'
            '<a href="/cardconv/drive/connect" class="btn btn-primary btn-sm">Connect Google Drive</a>'
        )

    # ── Receipt upload section ──
    if connected:
        receipt_upload_html = '''
      <form id="rcptForm" method="POST" action="/cardconv/receipts/upload" enctype="multipart/form-data">
        <div class="upload-zone" id="rcptZone" onclick="document.getElementById('rcptFiles').click()">
          <div style="font-size:2rem;margin-bottom:8px">🧾</div>
          <div style="font-weight:700;color:var(--text);margin-bottom:4px">Drop receipts here</div>
          <div style="font-size:.8rem;color:var(--text-muted)">JPG · PNG · PDF &nbsp;·&nbsp; Multiple files supported &nbsp;·&nbsp; OCR runs automatically</div>
          <input type="file" id="rcptFiles" name="files" multiple accept=".jpg,.jpeg,.png,.pdf" onchange="handleRcptFiles(this)">
        </div>
        <div id="rcptInfo" style="display:none;margin-top:12px;padding:12px 16px;background:var(--surface-2);border-radius:var(--radius-md)">
          <div id="rcptFileList" style="font-size:.82rem;color:var(--text);margin-bottom:10px;display:flex;flex-wrap:wrap;gap:6px"></div>
          <button type="submit" class="btn btn-primary">📤 Upload &amp; OCR</button>
        </div>
      </form>'''
    else:
        receipt_upload_html = '<p style="color:var(--text-muted);font-size:.85rem">Connect Google Drive above to enable receipt upload.</p>'

    # ── Receipts list ──
    receipt_rows = ""
    for r in receipts[:30]:
        ocr_parts = []
        if r.get("ocr_date"):
            ocr_parts.append(r["ocr_date"])
        if r.get("ocr_amount") is not None:
            ocr_parts.append(f'${r["ocr_amount"]}')
        if r.get("ocr_merchant"):
            ocr_parts.append(r["ocr_merchant"])
        ocr_info = f'<div style="font-size:.72rem;color:var(--text-muted);margin-top:2px">{" · ".join(ocr_parts)}</div>' if ocr_parts else ''
        drive_link = (f'<a href="{r["drive_url"]}" target="_blank" class="btn btn-ghost btn-sm">🔗</a>'
                      if r.get("drive_url") else "")
        receipt_rows += f'''<div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)">
      <span style="font-size:.75rem;color:var(--text-muted);min-width:110px;flex-shrink:0">{r.get("uploaded_at","")}</span>
      <div style="flex:1;min-width:0">
        <div style="font-size:.85rem;font-weight:600;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap">{r.get("filename","")}</div>
        {ocr_info}
      </div>
      {drive_link}
    </div>'''

    receipts_section = ""
    if receipts:
        receipts_section = f'''
  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Receipts ({len(receipts)})</span>
    </div>
    <div class="notepad-body" style="padding:8px 16px 12px">
      {receipt_rows}
    </div>
  </div>'''

    # ── History rows ──
    hist_rows = ""
    for h in hist:
        hist_rows += f'''<div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)">
      <span style="font-size:.8rem;color:var(--text-muted);min-width:130px">{h["date"]}</span>
      <span style="flex:1;font-size:.85rem;color:var(--text);font-weight:600">{h["filename"]}</span>
      <span style="font-size:.78rem;color:var(--success)">{h["rows"]} rows</span>
      {f'<span style="font-size:.72rem;color:var(--warn)">{h["unmatched"]} unmatched</span>' if h.get("unmatched") else ""}
      <a href="/cardconv/download/{h["filename"]}" class="btn btn-ghost btn-sm">⬇ Download</a>
    </div>'''
    if not hist_rows:
        hist_rows = '<div style="color:var(--text-muted);font-size:.85rem;padding:16px 0">No conversions yet</div>'

    # ── Keyword rows ──
    kw_rows = ""
    for k in kws:
        kw_rows += f'''<tr>
      <td style="font-weight:600;color:var(--accent)">{k["kw"]}</td>
      <td style="color:var(--text-muted)">{k["gl"]}</td>
      <td style="color:var(--text-muted)">{k["ser"]}</td>
      <td style="flex:1;color:var(--text)">{k["purpose"]}</td>
      <td><form method="POST" action="/cardconv/keyword/delete" style="display:inline">
        <input type="hidden" name="kw" value="{k["kw"]}">
        <button class="btn btn-danger btn-sm">✕</button>
      </form></td>
    </tr>'''

    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>💳 Card Converter · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
<style>
.upload-zone{{border:2px dashed var(--border);border-radius:var(--radius-lg);padding:40px 20px;text-align:center;cursor:pointer;transition:.2s;background:var(--surface)}}
.upload-zone:hover,.upload-zone.drag-over{{border-color:var(--accent);background:var(--surface-2)}}
.upload-zone input[type=file]{{display:none}}
.kw-table{{width:100%;border-collapse:collapse;font-size:.82rem}}
.kw-table td{{padding:8px 10px;border-bottom:1px solid var(--border)}}
.kw-table tr:last-child td{{border-bottom:none}}
</style>
</head><body>
<nav>
  <span class="nav-brand">💳 Card Converter</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container" style="max-width:860px">

  <!-- Google Drive Status -->
  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Google Drive</span>
    </div>
    <div class="notepad-body" style="padding:14px 20px;display:flex;align-items:center;gap:16px">
      {drive_status_html}
    </div>
  </div>

  <!-- Receipt Upload -->
  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">Upload Receipts</span>
    </div>
    <div class="notepad-body" style="padding:20px">
      {receipt_upload_html}
    </div>
  </div>

  {receipts_section}

  <!-- CSV Upload -->
  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">Upload CSV</span>
    </div>
    <div class="notepad-body" style="padding:20px">
      <form id="upForm" method="POST" action="/cardconv/upload" enctype="multipart/form-data">
        <div class="upload-zone" id="dropZone" onclick="document.getElementById('csvFile').click()">
          <div style="font-size:2rem;margin-bottom:8px">📎</div>
          <div style="font-weight:700;color:var(--text);margin-bottom:4px">Drop Posted_*.csv here</div>
          <div style="font-size:.8rem;color:var(--text-muted)">or click to browse</div>
          <input type="file" id="csvFile" name="file" accept=".csv" onchange="handleCsvFile(this)">
        </div>
        <div id="fileInfo" style="display:none;margin-top:12px;padding:12px 16px;background:var(--surface-2);border-radius:var(--radius-md);display:flex;align-items:center;gap:12px">
          <span style="font-size:1.2rem">📄</span>
          <span id="fileName" style="flex:1;font-size:.85rem;font-weight:600;color:var(--text)"></span>
          <button type="submit" class="btn btn-primary">Convert &amp; Download</button>
        </div>
      </form>
    </div>
  </div>

  <!-- History -->
  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Recent Conversions</span>
    </div>
    <div class="notepad-body" style="padding:8px 16px 12px">
      {hist_rows}
    </div>
  </div>

  <!-- Keywords -->
  <div class="notepad-card">
    <div class="notepad-header" style="display:flex;align-items:center;justify-content:space-between">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Keywords ({len(kws)})</span>
    </div>
    <div class="notepad-body" style="padding:12px 16px">
      <form method="POST" action="/cardconv/keyword/add" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;align-items:flex-end">
        <div style="display:flex;flex-direction:column;gap:4px">
          <label style="font-size:.7rem;color:var(--text-muted);font-weight:600">KEYWORD</label>
          <input name="kw" placeholder="e.g. STARBUCKS" required style="padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.82rem;width:160px">
        </div>
        <div style="display:flex;flex-direction:column;gap:4px">
          <label style="font-size:.7rem;color:var(--text-muted);font-weight:600">G/L ACCOUNT</label>
          <input name="gl" placeholder="53410177" required style="padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.82rem;width:110px">
        </div>
        <div style="display:flex;flex-direction:column;gap:4px">
          <label style="font-size:.7rem;color:var(--text-muted);font-weight:600">SER.</label>
          <input name="ser" placeholder="160" style="padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.82rem;width:70px">
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:180px">
          <label style="font-size:.7rem;color:var(--text-muted);font-weight:600">PURPOSE</label>
          <input name="purpose" placeholder="Coffee, Snack and meal" required style="padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.82rem;width:100%">
        </div>
        <button type="submit" class="btn btn-primary btn-sm" style="align-self:flex-end">+ Add</button>
      </form>
      <div style="max-height:320px;overflow-y:auto">
        <table class="kw-table">
          <thead style="position:sticky;top:0;background:var(--surface)">
            <tr style="border-bottom:1px solid var(--border)">
              <th style="padding:6px 10px;text-align:left;font-size:.7rem;color:var(--text-muted);font-weight:700;text-transform:uppercase">Keyword</th>
              <th style="padding:6px 10px;text-align:left;font-size:.7rem;color:var(--text-muted);font-weight:700;text-transform:uppercase">G/L</th>
              <th style="padding:6px 10px;text-align:left;font-size:.7rem;color:var(--text-muted);font-weight:700;text-transform:uppercase">Ser.</th>
              <th style="padding:6px 10px;text-align:left;font-size:.7rem;color:var(--text-muted);font-weight:700;text-transform:uppercase">Purpose</th>
              <th></th>
            </tr>
          </thead>
          <tbody>{kw_rows}</tbody>
        </table>
      </div>
    </div>
  </div>

</div>
<script>
// CSV upload zone
const csvZone = document.getElementById('dropZone');
const csvInfo = document.getElementById('fileInfo');
const csvName = document.getElementById('fileName');

function handleCsvFile(input) {{
  if (input.files[0]) {{
    csvName.textContent = input.files[0].name;
    csvInfo.style.display = 'flex';
    csvZone.style.display = 'none';
  }}
}}

csvZone.addEventListener('dragover', e => {{ e.preventDefault(); csvZone.classList.add('drag-over'); }});
csvZone.addEventListener('dragleave', () => csvZone.classList.remove('drag-over'));
csvZone.addEventListener('drop', e => {{
  e.preventDefault();
  csvZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) {{
    document.getElementById('csvFile').files = e.dataTransfer.files;
    csvName.textContent = f.name;
    csvInfo.style.display = 'flex';
    csvZone.style.display = 'none';
  }}
}});

// Receipt upload zone
const rcptZone = document.getElementById('rcptZone');
const rcptInfo = document.getElementById('rcptInfo');
const rcptList = document.getElementById('rcptFileList');

function handleRcptFiles(input) {{
  if (input.files.length > 0) {{
    rcptList.innerHTML = Array.from(input.files).map(f =>
      `<span style="background:var(--surface-3);padding:3px 8px;border-radius:4px;font-size:.78rem">${{f.name}}</span>`
    ).join('');
    rcptInfo.style.display = 'block';
    rcptZone.style.borderColor = 'var(--accent)';
  }}
}}

if (rcptZone) {{
  rcptZone.addEventListener('dragover', e => {{ e.preventDefault(); rcptZone.classList.add('drag-over'); }});
  rcptZone.addEventListener('dragleave', () => rcptZone.classList.remove('drag-over'));
  rcptZone.addEventListener('drop', e => {{
    e.preventDefault();
    rcptZone.classList.remove('drag-over');
    const input = document.getElementById('rcptFiles');
    if (e.dataTransfer.files.length > 0) {{
      input.files = e.dataTransfer.files;
      handleRcptFiles(input);
    }}
  }});
}}
</script>
</body></html>'''
