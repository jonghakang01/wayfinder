import csv, io, json, os, re, base64, uuid
from datetime import date, datetime
from pathlib import Path

import openpyxl

DATA_DIR   = Path(os.path.expanduser("~/.appdata/cardconv"))
KW_FILE    = DATA_DIR / "keywords.json"
HIST_FILE  = DATA_DIR / "history.json"
OUT_DIR    = DATA_DIR / "outputs"
TOKENS_DIR = DATA_DIR / "tokens"
CREDS_FILE = DATA_DIR / "google_credentials.json"
_SVC_DIR   = Path(__file__).parent
TEMPLATE   = _SVC_DIR / "cardconv_template.xlsx"  # bundled with service
TEMPLATE_FALLBACK = Path(os.path.expanduser(
    "~/Desktop/US업무/법카 정산/Automation/for upload.xlsx"
))

SCOPES = [
    'https://www.googleapis.com/auth/drive.file',
    'https://www.googleapis.com/auth/drive.readonly',
]
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


def _migrate_entry(e: dict) -> dict:
    """Ensure a receipt entry has v2 fields (id, ocr_status, match_status)."""
    e = dict(e)
    if not e.get("id"):
        e["id"] = "rcpt_" + (e.get("file_id") or uuid.uuid4().hex)[:8]
    if "ocr_status" not in e:
        e["ocr_status"] = "done" if e.get("ocr_amount") is not None else "pending"
    # v2.1: handwritten-priority OCR. Legacy entries keep ocr_amount as printed total.
    e.setdefault("ocr_printed_amount", e.get("ocr_amount"))
    e.setdefault("ocr_handwritten_amount", None)
    if "match_status" not in e:
        if e.get("matched"):
            e["match_status"] = "matched"
        elif e.get("ocr_amount") is None:
            e["match_status"] = "pending_match"
        else:
            e["match_status"] = "unmatched"
    return e


def _load_ledger(username: str) -> dict:
    """Load ledger, auto-migrating v1 (list) to v2 (dict) format."""
    f = _receipts_file(username)
    raw = None
    if f.exists():
        try:
            raw = json.loads(f.read_text())
        except Exception:
            raw = None
    if raw is None:
        return {"version": 2, "last_batch_at": None, "entries": []}
    if isinstance(raw, list):  # v1 → v2
        return {"version": 2, "last_batch_at": None,
                "entries": [_migrate_entry(e) for e in raw]}
    raw["entries"] = [_migrate_entry(e) for e in raw.get("entries", [])]
    raw.setdefault("version", 2)
    raw.setdefault("last_batch_at", None)
    return raw


def _save_ledger(username: str, ledger: dict):
    _ensure_dirs()
    _receipts_file(username).write_text(json.dumps(ledger, ensure_ascii=False, indent=2))


def _ledger_entries(username: str) -> list:
    return _load_ledger(username)["entries"]


def _ledger_stats(entries: list) -> dict:
    matched = sum(1 for e in entries if e.get("match_status") == "matched")
    unmatched = sum(1 for e in entries if e.get("match_status") == "unmatched")
    pending = sum(1 for e in entries if e.get("match_status") == "pending_match")
    return {"total": len(entries), "matched": matched,
            "unmatched": unmatched, "pending_match": pending}


def _load_receipts(username: str) -> list:
    """Backward-compatible entries accessor (returns ledger entries list)."""
    return _ledger_entries(username)


def _save_receipts(username: str, receipts: list):
    """Persist entries list into v2 ledger, preserving wrapper metadata."""
    ledger = _load_ledger(username)
    ledger["entries"] = receipts
    _save_ledger(username, ledger)


def _drive_meta_file(username: str) -> Path:
    return DATA_DIR / f"drive_meta_{username}.json"


def _load_drive_meta(username: str) -> dict:
    f = _drive_meta_file(username)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def _save_drive_meta(username: str, meta: dict):
    _ensure_dirs()
    _drive_meta_file(username).write_text(json.dumps(meta, ensure_ascii=False, indent=2))


def _review_file(username: str) -> Path:
    return DATA_DIR / f"review_{username}.json"


def _load_review(username: str) -> dict:
    f = _review_file(username)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def _save_review(username: str, review: dict):
    _ensure_dirs()
    _review_file(username).write_text(json.dumps(review, ensure_ascii=False, indent=2))


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


def _get_receipts_folder_ids(service, username: str) -> tuple:
    """Return (receipts_folder_id, matched_folder_id), creating folders if needed."""
    wayfinder_id = _get_or_create_folder(service, 'Wayfinder')
    receipts_id  = _get_or_create_folder(service, 'Receipts', wayfinder_id)
    matched_id   = _get_or_create_folder(service, 'Matched', receipts_id)
    # Cache receipts folder ID for UI link
    meta = _load_drive_meta(username)
    if meta.get('receipts_folder_id') != receipts_id:
        meta['receipts_folder_id'] = receipts_id
        _save_drive_meta(username, meta)
    return receipts_id, matched_id


def _upload_file_to_drive(username: str, file_bytes: bytes, filename: str,
                           mime_type: str) -> tuple:
    """Upload to Drive under Wayfinder/Receipts/. Returns (file_id, drive_url)."""
    from googleapiclient.http import MediaIoBaseUpload
    service = _get_drive_service(username)
    if not service:
        return None, None
    receipts_id, _ = _get_receipts_folder_ids(service, username)
    media  = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type)
    result = service.files().create(
        body={'name': filename, 'parents': [receipts_id]},
        media_body=media,
        fields='id,webViewLink'
    ).execute()
    fid = result.get('id')
    url = result.get('webViewLink') or f'https://drive.google.com/file/d/{fid}/view'
    return fid, url


def _move_to_matched_folder(username: str, file_id: str) -> bool:
    """Move receipt file from Wayfinder/Receipts/ to Wayfinder/Receipts/Matched/."""
    try:
        service = _get_drive_service(username)
        if not service:
            return False
        receipts_id, matched_id = _get_receipts_folder_ids(service, username)
        service.files().update(
            fileId=file_id,
            addParents=matched_id,
            removeParents=receipts_id,
            fields='id,parents'
        ).execute()
        return True
    except Exception:
        return False


# ── OCR ───────────────────────────────────────────────────────────────────────

_OCR_PROMPT = (
    'Look at this receipt CAREFULLY. There may be handwritten numbers '
    '(e.g., tip amount, final total written by hand on top of the printed receipt). '
    'Inspect tip line, total line, and any margin notes for handwriting. '
    'Extract: '
    '1) date (YYYY-MM-DD), '
    '2) merchant name, '
    '3) printed_amount: the PRINTED/typed total (number only), '
    '4) handwritten_amount: any HAND-WRITTEN final amount including tip (number only, '
    'null if none visible). '
    'Handwritten amount, when present, is the REAL final amount and overrides printed. '
    'Return JSON only: '
    '{"date":"YYYY-MM-DD","merchant":"name","printed_amount":0.00,"handwritten_amount":null}'
)


def _normalize_ocr(result: dict) -> dict:
    """Derive the final `amount` (handwritten priority) and coerce numeric fields.

    Keeps backward compat with the old single-`amount` shape: if a model still returns
    only `amount`, it is treated as the printed total.
    """
    if not result:
        return result

    def _num(v):
        if v is None:
            return None
        try:
            return round(float(v), 2)
        except (ValueError, TypeError):
            return None

    printed = _num(result.get("printed_amount"))
    handwritten = _num(result.get("handwritten_amount"))
    legacy = _num(result.get("amount"))
    if printed is None and legacy is not None:
        printed = legacy
    result["printed_amount"] = printed
    result["handwritten_amount"] = handwritten
    # Handwritten (tip-inclusive) total wins; fall back to printed.
    result["amount"] = handwritten if handwritten is not None else printed
    return result


def _ocr_receipt(file_bytes: bytes, mime_type: str) -> dict:
    """OCR receipt using Claude Vision. Returns {date, amount, merchant, ...} or {}."""
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
                {"type": "text", "text": _OCR_PROMPT}
            ]}]
        )
        text = resp.content[0].text.strip()
        m = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if m:
            result = _normalize_ocr(json.loads(m.group(0)))
            result["_model"] = "Claude"
            return result
    except Exception:
        pass
    return {}


# Configurable via GEMINI_OCR_MODEL (.env). gemini-2.5-flash: fast/cheap, strong on
# KR+EN receipts. Bump to gemini-2.5-pro if accuracy issues arise (~10x cost).
_DEFAULT_GEMINI_OCR_MODEL = "gemini-2.5-flash"


def _ocr_receipt_gemini(file_bytes: bytes, mime_type: str) -> dict:
    """OCR receipt using Gemini Vision. Returns {date, amount, merchant, _model} or {}."""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return {}
    try:
        # New unified SDK (google-genai). Old google.generativeai is deprecated.
        from google import genai
        from google.genai import types
        client = genai.Client(api_key=api_key)
        model_name = os.environ.get('GEMINI_OCR_MODEL', _DEFAULT_GEMINI_OCR_MODEL)
        # Inline bytes handle both images and PDFs (<20MB)
        resp = client.models.generate_content(
            model=model_name,
            contents=[
                types.Part.from_bytes(data=file_bytes, mime_type=mime_type),
                _OCR_PROMPT,
            ],
        )
        text = (resp.text or "").strip()
        m = re.search(r'\{[^{}]+\}', text, re.DOTALL)
        if m:
            result = _normalize_ocr(json.loads(m.group(0)))
            result["_model"] = "Gemini"
            return result
    except Exception:
        pass
    return {}


def _ocr_receipt_auto(file_bytes: bytes, mime_type: str) -> dict:
    """Primary OCR: Gemini first, fallback to Claude on failure."""
    result = _ocr_receipt_gemini(file_bytes, mime_type)
    if result and result.get("amount") is not None:
        return result
    return _ocr_receipt(file_bytes, mime_type)


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

    if TEMPLATE.exists():
        template_path = TEMPLATE
    elif TEMPLATE_FALLBACK.exists():
        template_path = TEMPLATE_FALLBACK
    else:
        raise FileNotFoundError("Template file not found. Please upload 'for upload.xlsx' to ~/.appdata/cardconv/template.xlsx")

    reader = csv.DictReader(io.TextIOWrapper(io.BytesIO(csv_bytes), encoding='utf-8-sig', newline=''))
    rows   = [r for r in reader if r.get("Card Member Name","").strip().upper() in TARGET_NAMES]

    wb = openpyxl.load_workbook(template_path)
    ws = wb["sheetMst"]

    start = 2
    while ws.cell(start, 1).value is not None:
        start += 1

    posting_dt = datetime(today.year, today.month, today.day)
    unmatched  = 0
    review_rows     = []   # per-transaction rows for the Review page
    receipt_matched = 0    # transactions with a matched receipt

    # Build receipt lookup: (date_str, rounded_amount) → receipt record
    receipts      = []
    receipts_map  = {}
    receipts_dirty = False
    if username:
        receipts = _load_receipts(username)
        for r in receipts:
            rdate   = r.get("ocr_date")
            ramount = r.get("ocr_amount")
            # Treat literal "YYYY-MM-DD" placeholder as None
            if rdate == "YYYY-MM-DD":
                rdate = None
            if ramount is not None:
                try:
                    key = (rdate, round(float(ramount), 2))
                    receipts_map[key] = r
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

        # Receipt match in column 27; move matched receipts to Matched folder
        inv_date_str = inv_dt.strftime("%Y-%m-%d") if inv_dt else None
        amt_rounded  = round(amount, 2)
        receipt_match = None
        if receipts_map:
            receipt_match = receipts_map.get((inv_date_str, amt_rounded))
            if not receipt_match:
                for (rdate, ramt), r in receipts_map.items():
                    amt_match  = abs(ramt - amt_rounded) <= 0.01
                    date_match = (rdate is None or rdate == inv_date_str)
                    # Also try merchant name fuzzy match
                    ocr_merchant = (r.get("ocr_merchant") or "").upper()
                    merch_match  = ocr_merchant and (
                        ocr_merchant in vendor.upper() or vendor.upper()[:10] in ocr_merchant
                    )
                    if amt_match and (date_match or merch_match):
                        receipt_match = r
                        break
            if receipt_match:
                fn  = receipt_match.get('filename', '')
                url = receipt_match.get('drive_url', '')
                ws.cell(start, 27).value = f"✅ {fn} ({url})" if url else f"✅ {fn}"
                # Move to Matched folder on first match
                fid = receipt_match.get('file_id')
                if fid and username and not receipt_match.get('matched'):
                    if _move_to_matched_folder(username, fid):
                        receipt_match['matched'] = True
                        receipt_match['match_status'] = 'matched'
                        receipt_match['matched_at'] = datetime.now().isoformat()
                        receipt_match['matched_transaction'] = {
                            'date':   inv_date_str,
                            'amount': amt_rounded,
                            'vendor': vendor,
                        }
                        receipts_dirty = True
            else:
                ws.cell(start, 27).value = "❌ Missing"

        # Collect a Review row for this transaction
        rcpt_info = None
        if receipt_match:
            receipt_matched += 1
            rcpt_info = {
                "file_id":    receipt_match.get("file_id"),
                "filename":   receipt_match.get("filename"),
                "drive_url":  receipt_match.get("drive_url"),
                "ocr_amount": receipt_match.get("ocr_amount"),
            }
        review_rows.append({
            "id":          "rv_" + uuid.uuid4().hex[:8],
            "date":        inv_date_str,
            "merchant":    vendor,
            "amount":      amt_rounded,
            "gl":          gl,
            "ser":         ser,
            "purpose":     purpose,
            "matched":     bool(receipt_match),
            "receipt":     rcpt_info,
            "loss_reason": "",
        })

        start += 1

    if receipts_dirty and username:
        _save_receipts(username, receipts)

    # Persist Review snapshot for the Review page
    if username:
        _save_review(username, {
            "generated_at": datetime.now().isoformat(),
            "source":       filename,
            "out_filename": out_fn,
            "total":        len(rows),
            "matched":      receipt_matched,
            "unmatched":    len(rows) - receipt_matched,
            "kw_unmatched": unmatched,
            "rows":         review_rows,
        })

    buf = io.BytesIO()
    wb.save(buf)
    xlsx_bytes = buf.getvalue()
    (OUT_DIR / out_fn).write_bytes(xlsx_bytes)
    return xlsx_bytes, out_fn, len(rows), unmatched


# ── Ledger ──────────────────────────────────────────────────────────────────

_SUPPORTED_MIME = {'image/jpeg', 'image/png', 'application/pdf', 'image/gif', 'image/webp'}


def _run_batch_ocr(username: str) -> dict:
    """Scan Drive, OCR new/pending files, update ledger. Returns stats dict."""
    service = _get_drive_service(username)
    if not service:
        return {"error": "drive not connected"}
    try:
        receipts_id, _ = _get_receipts_folder_ids(service, username)
        results = service.files().list(
            q=(f"'{receipts_id}' in parents and trashed=false "
               f"and mimeType!='application/vnd.google-apps.folder'"),
            fields="files(id,name,mimeType,webViewLink)"
        ).execute()
        drive_files = results.get('files', [])

        ledger  = _load_ledger(username)
        entries = ledger["entries"]
        by_fid  = {e.get("file_id"): e for e in entries}
        processed = failed = 0

        for f in drive_files:
            fid  = f.get('id')
            mime = f.get('mimeType', '')
            if mime not in _SUPPORTED_MIME:
                continue
            existing = by_fid.get(fid)
            if existing and existing.get("ocr_status") == "done" \
                    and existing.get("ocr_amount") is not None:
                continue  # already OCR'd successfully
            content  = service.files().get_media(fileId=fid).execute()
            ocr      = _ocr_receipt_auto(content, mime)
            ocr_date = ocr.get("date")
            if ocr_date == "YYYY-MM-DD":
                ocr_date = None
            has_ocr  = ocr.get("amount") is not None
            url      = f.get('webViewLink') or f'https://drive.google.com/file/d/{fid}/view'
            if has_ocr:
                processed += 1
            else:
                failed += 1
            update = {
                "file_id":      fid,
                "filename":     f.get('name', ''),
                "drive_url":    url,
                "mime_type":    mime,
                "ocr_status":   "done" if has_ocr else "failed",
                "ocr_date":     ocr_date,
                "ocr_amount":   ocr.get("amount"),
                "ocr_printed_amount":     ocr.get("printed_amount"),
                "ocr_handwritten_amount": ocr.get("handwritten_amount"),
                "ocr_merchant": ocr.get("merchant"),
                "ocr_model":    ocr.get("_model"),
            }
            if existing:
                existing.update(update)
                existing.setdefault("match_status", "unmatched" if has_ocr else "pending_match")
            else:
                update["id"] = "rcpt_" + (fid or uuid.uuid4().hex)[:8]
                update["match_status"] = "unmatched" if has_ocr else "pending_match"
                update["uploaded_at"] = datetime.now().strftime("%Y-%m-%d %H:%M")
                update["synced_at"] = datetime.now().isoformat()
                entries.append(update)
                by_fid[fid] = update

        ledger["last_batch_at"] = datetime.now().isoformat()
        _save_ledger(username, ledger)
        return {"processed": processed, "failed": failed, "total": len(entries)}
    except Exception as e:
        return {"error": str(e)}


def _handle_batch_run(username: str, ctx):
    """POST /cardconv/batch/run — X-Batch-Secret authenticated batch OCR trigger."""
    secret = os.environ.get("CARDCONV_BATCH_SECRET", "")
    headers = (ctx or {}).get("headers")
    provided = headers.get("X-Batch-Secret", "") if headers else ""
    if not secret or provided != secret:
        return ("json", {"error": "unauthorized"}, 401)
    return ("json", _run_batch_ocr(username))


def _apply_ledger_filters(entries: list, status: str, dfrom: str, dto: str) -> list:
    """Filter + sort ledger entries by status and OCR-date range.

    Shared by the JSON API and the PDF export so both honor identical filters.
    Date filters keep entries without an OCR date always visible.
    """
    filtered = entries
    if status and status != "all":
        filtered = [e for e in filtered if e.get("match_status") == status]
    if dfrom:
        filtered = [e for e in filtered if not e.get("ocr_date") or e["ocr_date"] >= dfrom]
    if dto:
        filtered = [e for e in filtered if not e.get("ocr_date") or e["ocr_date"] <= dto]
    return sorted(
        filtered,
        key=lambda e: e.get("ocr_date") or e.get("uploaded_at") or "",
        reverse=True,
    )


def _handle_ledger_api(username: str, query: dict):
    """GET /cardconv/ledger/api — filtered JSON data."""
    entries = _ledger_entries(username)
    status  = (query.get("status", ["all"]) or ["all"])[0]
    dfrom   = (query.get("from", [""]) or [""])[0]
    dto     = (query.get("to", [""]) or [""])[0]
    try:
        page = max(1, int((query.get("page", ["1"]) or ["1"])[0]))
    except ValueError:
        page = 1
    try:
        limit = max(1, int((query.get("limit", ["50"]) or ["50"])[0]))
    except ValueError:
        limit = 50

    filtered = _apply_ledger_filters(entries, status, dfrom, dto)

    stats   = _ledger_stats(filtered)
    total_f = len(filtered)
    pages   = max(1, (total_f + limit - 1) // limit)
    start   = (page - 1) * limit
    return ("json", {
        "total":       stats["total"],
        "matched":     stats["matched"],
        "unmatched":   stats["unmatched"],
        "pending_match": stats["pending_match"],
        "page":        page,
        "pages":       pages,
        "entries":     filtered[start:start + limit],
    })


def _handle_status_change(username: str, entry_id: str, body: dict):
    """POST /cardconv/ledger/<id>/status — manual status override."""
    raw = body.get("status", "")
    status = (raw[0] if isinstance(raw, list) else str(raw)).strip()
    if status not in ("matched", "unmatched", "pending_match"):
        return ("json", {"error": "invalid status"}, 400)
    ledger = _load_ledger(username)
    for e in ledger["entries"]:
        if e.get("id") == entry_id:
            e["match_status"] = status
            e["matched"] = (status == "matched")
            if status == "matched":
                e["matched_at"] = datetime.now().isoformat()
            _save_ledger(username, ledger)
            return ("json", {"ok": True})
    return ("json", {"error": "not found"}, 404)


def _handle_image_proxy(username: str, file_id: str):
    """GET /cardconv/receipts/image/<file_id> — Drive media proxy, inline."""
    service = _get_drive_service(username)
    if not service:
        return ("html", "<p>Drive not connected</p>", 401)
    try:
        meta    = service.files().get(fileId=file_id, fields="mimeType").execute()
        mime    = meta.get("mimeType", "image/jpeg")
        content = service.files().get_media(fileId=file_id).execute()
        return ("binary", content, mime, None)
    except Exception as e:
        return ("html", f"<p>Image load error: {e}</p>", 404)


# ── PDF export ────────────────────────────────────────────────────────────────

_DEJAVU_DIR = "/usr/share/fonts/truetype/dejavu"
# Font candidates, preferred first. A CJK font (e.g. apt install fonts-nanum on
# the server) renders Korean merchant names; DejaVu covers Latin/symbols without
# crashing on non-ASCII. Each entry is (family, regular_path, bold_path).
_PDF_FONT_CANDIDATES = [
    ("Nanum", "/usr/share/fonts/truetype/nanum/NanumGothic.ttf",
              "/usr/share/fonts/truetype/nanum/NanumGothicBold.ttf"),
    ("NotoKR", "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
               "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"),
    ("DejaVu", f"{_DEJAVU_DIR}/DejaVuSans.ttf",
               f"{_DEJAVU_DIR}/DejaVuSans-Bold.ttf"),
]
_PDF_STATUS_LABEL = {"matched": "Matched", "unmatched": "Unmatched",
                     "pending_match": "Pending Match"}
_PDF_STATUS_COLOR = {"matched": (22, 163, 74), "unmatched": (220, 38, 38),
                     "pending_match": (217, 119, 6)}


def _compress_receipt_image(raw: bytes, max_w: int = 700, quality: int = 72):
    """Resize + recompress a receipt image into a small JPEG.

    Returns (jpeg_bytes, (w, h)) or None on failure. Caps width at max_w px and
    re-encodes as JPEG to keep the embedded PDF small (~quality 70-75).
    """
    from PIL import Image
    try:
        img = Image.open(io.BytesIO(raw))
        img = img.convert("RGB")  # flatten alpha/CMYK/palette for JPEG
        if img.width > max_w:
            h = max(1, round(img.height * max_w / img.width))
            img = img.resize((max_w, h), Image.LANCZOS)
        out = io.BytesIO()
        img.save(out, format="JPEG", quality=quality, optimize=True)
        return out.getvalue(), img.size
    except Exception:
        return None


def _fetch_drive_image(service, file_id: str):
    """Fetch raw image bytes from Drive, or None if unavailable."""
    if not service or not file_id:
        return None
    try:
        return service.files().get_media(fileId=file_id).execute()
    except Exception:
        return None


def _handle_ledger_pdf(username: str, query: dict):
    """GET /cardconv/ledger/download.pdf — filtered receipts as a compact PDF.

    Honors the same status/date filters as the ledger view. Receipts are laid out
    as a compact table (one row each: thumbnail, date, merchant, printed,
    handwritten, final, status) fitting ~13-15 rows per A4 page.
    """
    from fpdf import FPDF

    status = (query.get("status", ["all"]) or ["all"])[0]
    dfrom  = (query.get("from", [""]) or [""])[0]
    dto    = (query.get("to", [""]) or [""])[0]
    entries = _apply_ledger_filters(_ledger_entries(username), status, dfrom, dto)
    stats   = _ledger_stats(entries)
    service = _get_drive_service(username)

    pdf = FPDF(orientation="P", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_margins(15, 15, 15)

    # Prefer a Unicode TTF so non-Latin-1 merchant names don't crash rendering.
    FONT, unicode_ok = "Helvetica", False
    for fam, reg, bold in _PDF_FONT_CANDIDATES:
        if os.path.exists(reg) and os.path.exists(bold):
            pdf.add_font(fam, "", reg)
            pdf.add_font(fam, "B", bold)
            FONT, unicode_ok = fam, True
            break

    def S(t):  # sanitize for core (Latin-1) font fallback
        t = "" if t is None else str(t)
        return t if unicode_ok else t.encode("latin-1", "replace").decode("latin-1")

    def money(a):
        return "-" if a is None else "$%.2f" % a

    pdf.add_page()

    # Header
    pdf.set_font(FONT, "B", 16)
    pdf.cell(0, 9, S("Receipt Ledger"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font(FONT, "", 9)
    pdf.set_text_color(110, 110, 110)
    flabel = {"all": "All"}.get(status) or _PDF_STATUS_LABEL.get(status, status)
    rng = f"{dfrom or '...'} ~ {dto or '...'}"
    pdf.cell(0, 5.5, S(f"User: {username}    Filter: {flabel}    Date: {rng}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.cell(0, 5.5, S(f"Total {stats['total']}   Matched {stats['matched']}   "
                       f"Unmatched {stats['unmatched']}   Pending {stats['pending_match']}"),
             new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(3)

    if not entries:
        pdf.set_font(FONT, "", 11)
        pdf.cell(0, 12, S("No receipts for the selected filter."),
                 new_x="LMARGIN", new_y="NEXT")

    # ── Table layout: one receipt per row, ~13-15 rows per A4 page ──
    # Column widths (mm) sum to the effective page width (180mm @ A4/15mm margins).
    epw = pdf.epw
    COLS = [
        ("",            "thumb",  16),
        ("Date",        "date",   20),
        ("Merchant",    "merch",  56),
        ("Printed",     "print",  22),
        ("Handwritten", "hand",   24),
        ("Final",       "final",  22),
        ("Status",      "status", 20),
    ]
    scale  = epw / sum(c[2] for c in COLS)
    widths = [c[2] * scale for c in COLS]
    cx     = [pdf.l_margin]
    for w in widths:
        cx.append(cx[-1] + w)
    x0    = pdf.l_margin
    ROW_H = 17.0
    PAD   = 1.5
    HDR_H = 8.0

    def fit(text, max_w, size):
        # Truncate to fit a cell width at the given font size (handles CJK widths).
        pdf.set_font(FONT, "", size)
        text = S(text)
        if pdf.get_string_width(text) <= max_w:
            return text
        ell = S("…")
        while text and pdf.get_string_width(text + ell) > max_w:
            text = text[:-1]
        return text + ell

    def draw_header_row():
        y = pdf.get_y()
        pdf.set_fill_color(243, 244, 246)
        pdf.set_draw_color(200, 200, 200)
        pdf.set_line_width(0.2)
        pdf.set_font(FONT, "B", 8)
        pdf.set_text_color(80, 80, 80)
        for i, (label, key, _w) in enumerate(COLS):
            align = "L" if key in ("thumb", "date", "merch") else \
                    ("C" if key == "status" else "R")
            pdf.set_xy(cx[i], y)
            pdf.cell(widths[i], HDR_H, S(label), border=1, align=align, fill=True)
        pdf.set_text_color(0, 0, 0)
        pdf.set_y(y + HDR_H)

    if entries:
        draw_header_row()

    for idx, e in enumerate(entries, 1):
        # Compress the thumbnail small — table cells are ~14mm tall.
        jpeg = dim = None
        if e.get("file_id"):
            comp = _compress_receipt_image(
                _fetch_drive_image(service, e.get("file_id")) or b"",
                max_w=220, quality=68)
            if comp:
                jpeg, dim = comp

        # Page break (repeat the header on the new page).
        if pdf.get_y() + ROW_H > pdf.page_break_trigger:
            pdf.add_page()
            draw_header_row()

        y0 = pdf.get_y()
        if idx % 2 == 0:  # zebra striping for readability
            pdf.set_fill_color(249, 250, 251)
            pdf.rect(x0, y0, epw, ROW_H, style="F")

        # Light cell grid
        pdf.set_draw_color(228, 228, 228)
        pdf.set_line_width(0.15)
        for i in range(len(COLS)):
            pdf.rect(cx[i], y0, widths[i], ROW_H)

        # Thumbnail (centered) or placeholder
        if jpeg and dim:
            cw, ch = widths[0] - 2 * PAD, ROW_H - 2 * PAD
            dw = cw
            dh = dw * dim[1] / dim[0]
            if dh > ch:
                dh, dw = ch, ch * dim[0] / dim[1]
            try:
                pdf.image(io.BytesIO(jpeg),
                          x=cx[0] + (widths[0] - dw) / 2,
                          y=y0 + (ROW_H - dh) / 2, w=dw, h=dh)
            except Exception:
                pass
        else:
            pdf.set_xy(cx[0], y0)
            pdf.set_font(FONT, "", 6)
            pdf.set_text_color(180, 180, 180)
            pdf.cell(widths[0], ROW_H, S("no img"), align="C")

        def txt(i, text, align="R", bold=False, color=(0, 0, 0), size=8):
            # fpdf2 vertically centers text within the cell height.
            pdf.set_xy(cx[i] + 1, y0)
            pdf.set_font(FONT, "B" if bold else "", size)
            pdf.set_text_color(*color)
            pdf.cell(widths[i] - 2, ROW_H, text, align=align)

        txt(1, S(e.get("ocr_date") or "-"), align="L")
        txt(2, fit(e.get("ocr_merchant") or "-", widths[2] - 2, 8), align="L")
        txt(3, S(money(e.get("ocr_printed_amount"))), color=(130, 130, 130))
        hw = e.get("ocr_handwritten_amount")
        txt(4, S(money(hw)), color=(217, 119, 6) if hw is not None else (130, 130, 130))
        txt(5, S(money(e.get("ocr_amount"))), bold=True)
        st = e.get("match_status")
        txt(6, S(_PDF_STATUS_LABEL.get(st, st or "-")), align="C", size=7,
            color=_PDF_STATUS_COLOR.get(st, (0, 0, 0)))

        pdf.set_text_color(0, 0, 0)
        pdf.set_y(y0 + ROW_H)

    out = pdf.output()
    data = bytes(out)
    fname = f"receipts_{username}_{date.today().isoformat()}.pdf"
    return ("binary", data, "application/pdf", fname)


# ── HTTP handler ──────────────────────────────────────────────────────────────

def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user")
    if user != ADMIN:
        return ("html", "<h2 style='padding:40px;color:#f87171'>Access denied</h2>")

    # Tab pages: Ledger (main) | Convert | Review | Keywords
    if method == "GET" and path == "/cardconv":
        return ("redirect", "/cardconv/ledger")
    if method == "GET" and path == "/cardconv/convert":
        return ("html", _render_convert(user))
    if method == "GET" and path == "/cardconv/review":
        return ("html", _render_review(user))
    if method == "GET" and path == "/cardconv/keywords":
        return ("html", _render_keywords(user))
    if method == "POST" and path == "/cardconv/review/reason":
        return _handle_review_reason(user, body)

    # Ledger
    if method == "GET" and path == "/cardconv/ledger":
        return ("html", _render_ledger(user))
    if method == "GET" and path == "/cardconv/ledger/api":
        return _handle_ledger_api(user, body)  # GET passes query dict as body
    if method == "GET" and path == "/cardconv/ledger/download.pdf":
        return _handle_ledger_pdf(user, body)  # GET passes query dict as body
    if method == "POST" and path.startswith("/cardconv/ledger/") and path.endswith("/status"):
        entry_id = path[len("/cardconv/ledger/"):-len("/status")]
        return _handle_status_change(user, entry_id, body)
    if method == "GET" and path.startswith("/cardconv/receipts/image/"):
        file_id = path[len("/cardconv/receipts/image/"):]
        return _handle_image_proxy(user, file_id)
    if method == "POST" and path == "/cardconv/batch/run":
        return _handle_batch_run(user, ctx)

    # Drive OAuth
    if method == "GET" and path == "/cardconv/drive/connect":
        return _handle_drive_connect(user)
    if method == "POST" and path == "/cardconv/drive/auth":
        return _handle_drive_auth(user, body)

    # Drive sync
    if method == "POST" and path == "/cardconv/drive/sync":
        return _handle_drive_sync(user)

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
        return ("redirect", "/cardconv/keywords")

    # Keyword delete
    if method == "POST" and path == "/cardconv/keyword/delete":
        kw  = (body.get("kw", [""])[0]).strip().upper()
        kws = [k for k in _load_kw() if k["kw"].upper() != kw]
        _save_kw(kws)
        return ("redirect", "/cardconv/keywords")

    return ("redirect", "/cardconv/ledger")


def _get_client_info():
    import json as _json
    data = _json.loads(CREDS_FILE.read_text())
    return data.get("installed", data.get("web", {}))


def _handle_drive_connect(username: str):
    if not CREDS_FILE.exists():
        return ("html", f"<p style='padding:20px;color:var(--danger)'>Credentials file not found: {CREDS_FILE}</p>")
    try:
        import urllib.parse as _up
        c = _get_client_info()
        params = {
            "client_id":     c["client_id"],
            "redirect_uri":  "urn:ietf:wg:oauth:2.0:oob",
            "response_type": "code",
            "scope":         " ".join(SCOPES),
            "access_type":   "offline",
            "prompt":        "consent",
        }
        auth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + _up.urlencode(params)
        return ("html", _render_drive_connect(username, auth_url))
    except Exception as e:
        return ("html", f"<p style='padding:20px;color:var(--danger)'>Drive connect error: {e}</p>")


def _handle_drive_auth(username: str, body):
    raw = body.get("code", "")
    code = (raw[0] if isinstance(raw, list) else str(raw)).strip()
    if not code:
        return ("redirect", "/cardconv/ledger")
    try:
        import json as _json, urllib.request as _req, urllib.parse as _up
        c = _get_client_info()
        token_data = _up.urlencode({
            "code":          code,
            "client_id":     c["client_id"],
            "client_secret": c["client_secret"],
            "redirect_uri":  "urn:ietf:wg:oauth:2.0:oob",
            "grant_type":    "authorization_code",
        }).encode()
        req = _req.Request("https://oauth2.googleapis.com/token", data=token_data,
                           headers={"Content-Type": "application/x-www-form-urlencoded"})
        resp = _req.urlopen(req)
        token_json = _json.loads(resp.read())
        if "error" in token_json:
            raise Exception(f"{token_json['error']}: {token_json.get('error_description','')}")
        c = _get_client_info()
        save_data = {
            "token":         token_json.get("access_token"),
            "refresh_token": token_json.get("refresh_token"),
            "token_uri":     "https://oauth2.googleapis.com/token",
            "client_id":     c["client_id"],
            "client_secret": c["client_secret"],
            "scopes":        SCOPES,
        }
        _ensure_dirs()
        (TOKENS_DIR / f"{username}.json").write_text(_json.dumps(save_data))
    except Exception as e:
        return ("html", f"<p style='padding:20px;color:var(--danger)'>Auth error: {e} "
                        f"<a href='/cardconv/ledger' style='color:var(--accent)'>Back</a></p>")
    return ("redirect", "/cardconv/ledger")


def _handle_drive_sync(username: str):
    """Scan Drive Wayfinder/Receipts/ folder, OCR new files, append to receipts json."""
    service = _get_drive_service(username)
    if not service:
        return ("redirect", "/cardconv/ledger")
    try:
        receipts_id, _ = _get_receipts_folder_ids(service, username)
        # List files directly in Receipts (exclude subfolders)
        results = service.files().list(
            q=(f"'{receipts_id}' in parents and trashed=false "
               f"and mimeType!='application/vnd.google-apps.folder'"),
            fields="files(id,name,mimeType,webViewLink)"
        ).execute()
        drive_files = results.get('files', [])

        existing     = _load_receipts(username)
        # IDs where OCR already succeeded — skip those only
        ocr_done_ids = {r.get('file_id') for r in existing
                        if r.get('ocr_amount') is not None or r.get('matched')}
        existing_map = {r.get('file_id'): r for r in existing}
        supported    = {'image/jpeg', 'image/png', 'application/pdf', 'image/gif', 'image/webp'}

        for f in drive_files:
            fid = f.get('id')
            if fid in ocr_done_ids:
                continue
            mime = f.get('mimeType', '')
            if mime not in supported:
                continue
            content = service.files().get_media(fileId=fid).execute()
            ocr     = _ocr_receipt_auto(content, mime)
            url     = f.get('webViewLink') or f'https://drive.google.com/file/d/{fid}/view'
            # Fix: treat "YYYY-MM-DD" placeholder as None
            ocr_date = ocr.get("date")
            if ocr_date == "YYYY-MM-DD":
                ocr_date = None
            has_ocr = ocr.get("amount") is not None
            entry = {
                "file_id":      fid,
                "filename":     f.get('name', ''),
                "drive_url":    url,
                "mime_type":    mime,
                "uploaded_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
                "ocr_status":   "done" if has_ocr else "failed",
                "ocr_date":     ocr_date,
                "ocr_amount":   ocr.get("amount"),
                "ocr_printed_amount":     ocr.get("printed_amount"),
                "ocr_handwritten_amount": ocr.get("handwritten_amount"),
                "ocr_merchant": ocr.get("merchant"),
                "ocr_model":    ocr.get("_model"),
            }
            if fid in existing_map:
                existing_map[fid].update(entry)
            else:
                entry["id"] = "rcpt_" + (fid or uuid.uuid4().hex)[:8]
                entry["match_status"] = "unmatched" if has_ocr else "pending_match"
                entry["synced_at"] = datetime.now().isoformat()
                existing.append(entry)

        _save_receipts(username, existing)
    except Exception as e:
        return ("html", f"<p style='padding:20px;color:var(--danger)'>Sync error: {e} "
                        f"<a href='/cardconv/ledger' style='color:var(--accent)'>Back</a></p>")
    return ("redirect", "/cardconv/ledger")


def _handle_receipt_upload(username: str, body):
    raw = body.get("__raw_handler__")
    if raw is None:
        return ("redirect", "/cardconv/ledger")
    if not _is_drive_connected(username):
        return ("html", "<p style='padding:20px;color:var(--danger)'>Connect Google Drive first. "
                        "<a href='/cardconv/ledger' style='color:var(--accent)'>Back</a></p>")

    files = _parse_multipart_files(raw)
    if not files:
        return ("redirect", "/cardconv/ledger")

    receipts  = _load_receipts(username)
    supported = {'image/jpeg', 'image/png', 'application/pdf', 'image/gif', 'image/webp'}

    for filename, content, mime_type in files:
        if mime_type not in supported:
            continue
        file_id, drive_url = _upload_file_to_drive(username, content, filename, mime_type)
        ocr = _ocr_receipt_auto(content, mime_type)
        ocr_date = ocr.get("date")
        if ocr_date == "YYYY-MM-DD":
            ocr_date = None
        has_ocr = ocr.get("amount") is not None
        receipts.append({
            "id":           "rcpt_" + (file_id or uuid.uuid4().hex)[:8],
            "file_id":      file_id,
            "filename":     filename,
            "drive_url":    drive_url,
            "mime_type":    mime_type,
            "uploaded_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
            "synced_at":    datetime.now().isoformat(),
            "ocr_status":   "done" if has_ocr else "failed",
            "ocr_date":     ocr_date,
            "ocr_amount":   ocr.get("amount"),
            "ocr_printed_amount":     ocr.get("printed_amount"),
            "ocr_handwritten_amount": ocr.get("handwritten_amount"),
            "ocr_merchant": ocr.get("merchant"),
            "ocr_model":    ocr.get("_model"),
            "match_status": "unmatched" if has_ocr else "pending_match",
        })

    _save_receipts(username, receipts)
    return ("redirect", "/cardconv/ledger")


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
        return ("redirect", "/cardconv/ledger")

    try:
        xlsx_bytes, out_fn, total, unmatched = convert(csv_bytes, csv_name, username=user)
        _add_hist({
            "filename":  out_fn,
            "source":    csv_name,
            "rows":      total,
            "unmatched": unmatched,
            "date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        # Conversion result is staged in review_{user}.json; review before download.
        return ("redirect", "/cardconv/review")
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
  <span class="nav-user"><a href="/cardconv/ledger" class="nav-back">← Back to Ledger</a></span>
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


# ── Shared tab bar ───────────────────────────────────────────────────────────

_CC_TAB_CSS = (
    ".cc-tabs{display:flex;gap:0;border-bottom:1px solid var(--border);margin-bottom:20px;flex-wrap:wrap}"
    ".cc-tab{padding:10px 20px;font-size:.82rem;font-weight:600;color:var(--text-muted);"
    "border-bottom:2px solid transparent;text-decoration:none;transition:color .15s,border-color .15s}"
    ".cc-tab:hover{color:var(--text)}"
    ".cc-tab.active{color:var(--accent);border-bottom-color:var(--accent)}"
    ".tab-badge{display:inline-flex;align-items:center;justify-content:center;min-width:16px;height:16px;"
    "background:#ef4444;border-radius:8px;font-size:.62rem;font-weight:700;color:#fff;padding:0 4px;"
    "margin-left:5px;vertical-align:middle}"
)


def _tab_bar(active: str, user: str) -> str:
    """Shared Card Converter tab bar. active ∈ ledger|convert|review|keywords."""
    unmatched_n = _ledger_stats(_ledger_entries(user))["unmatched"]
    badge = f'<span class="tab-badge">{unmatched_n}</span>' if unmatched_n else ''
    tabs = [
        ("ledger",   "/cardconv/ledger",   "Receipt Ledger" + badge),
        ("convert",  "/cardconv/convert",  "Convert"),
        ("review",   "/cardconv/review",   "Review"),
        ("keywords", "/cardconv/keywords", "Keywords"),
    ]
    out = ['<div class="cc-tabs">']
    for key, href, label in tabs:
        cls = "cc-tab active" if key == active else "cc-tab"
        out.append(f'<a href="{href}" class="{cls}">{label}</a>')
    out.append('</div>')
    return "".join(out)


# Shared upload-zone CSS (used by Convert and Ledger register section)
_UPLOAD_CSS = (
    ".upload-zone{border:2px dashed var(--border);border-radius:var(--radius-lg);padding:40px 20px;"
    "text-align:center;cursor:pointer;transition:.2s;background:var(--surface)}"
    ".upload-zone:hover,.upload-zone.drag-over{border-color:var(--accent);background:var(--surface-2)}"
    ".upload-zone input[type=file]{display:none}"
)


# ── Ledger register section (Drive + receipt upload) ───────────────────────────

def _register_section(user: str) -> str:
    """Drive status + receipt upload — moved onto the Ledger page."""
    connected = _is_drive_connected(user)
    meta = _load_drive_meta(user)
    receipts_folder_id = meta.get('receipts_folder_id')
    if connected:
        folder_link = ""
        if receipts_folder_id:
            folder_link = (f'<a href="https://drive.google.com/drive/folders/{receipts_folder_id}" '
                           f'target="_blank" class="btn btn-ghost btn-sm">📂 Open in Drive →</a>')
        drive_status_html = f'''
      <span style="font-size:.88rem;font-weight:600;color:var(--success)">✅ Connected</span>
      {folder_link}
      <form method="POST" action="/cardconv/drive/sync" style="display:inline;margin-left:4px">
        <button type="submit" class="btn btn-ghost btn-sm">🔄 Sync from Drive</button>
      </form>'''
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
        drive_status_html = (
            '<span style="font-size:.88rem;font-weight:600;color:var(--danger)">❌ Not connected</span>'
            '<a href="/cardconv/drive/connect" class="btn btn-primary btn-sm">Connect Google Drive</a>'
        )
        receipt_upload_html = ('<p style="color:var(--text-muted);font-size:.85rem">'
                               'Connect Google Drive above to enable receipt upload.</p>')
    return f'''
  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Google Drive</span>
    </div>
    <div class="notepad-body" style="padding:14px 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap">
      {drive_status_html}
    </div>
  </div>
  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">Register Receipts</span>
    </div>
    <div class="notepad-body" style="padding:20px">
      {receipt_upload_html}
    </div>
  </div>'''


# Receipt-upload drop-zone JS (injected into the Ledger page)
_RCPT_JS = r'''
const rcptZone = document.getElementById('rcptZone');
const rcptInfo = document.getElementById('rcptInfo');
const rcptList = document.getElementById('rcptFileList');
function handleRcptFiles(input){
  if(input.files.length>0){
    rcptList.innerHTML = Array.from(input.files).map(f =>
      '<span style="background:var(--surface-3);padding:3px 8px;border-radius:4px;font-size:.78rem">'+f.name+'</span>').join('');
    rcptInfo.style.display='block';
    rcptZone.style.borderColor='var(--accent)';
  }
}
if(rcptZone){
  rcptZone.addEventListener('dragover', e => { e.preventDefault(); rcptZone.classList.add('drag-over'); });
  rcptZone.addEventListener('dragleave', () => rcptZone.classList.remove('drag-over'));
  rcptZone.addEventListener('drop', e => {
    e.preventDefault(); rcptZone.classList.remove('drag-over');
    const input = document.getElementById('rcptFiles');
    if(e.dataTransfer.files.length>0){ input.files = e.dataTransfer.files; handleRcptFiles(input); }
  });
}
'''


# ── Convert page ───────────────────────────────────────────────────────────────

def _render_convert(user: str) -> str:
    from server import CSS_VER
    hist = _load_hist()
    hist_rows = ""
    for h in hist:
        unm = (f'<span style="font-size:.72rem;color:var(--warn)">{h["unmatched"]} unmatched</span>'
               if h.get("unmatched") else "")
        hist_rows += (
            f'<div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)">'
            f'<span style="font-size:.8rem;color:var(--text-muted);min-width:130px">{h["date"]}</span>'
            f'<span style="flex:1;font-size:.85rem;color:var(--text);font-weight:600">{h["filename"]}</span>'
            f'<span style="font-size:.78rem;color:var(--success)">{h["rows"]} rows</span>'
            f'{unm}'
            f'<a href="/cardconv/download/{h["filename"]}" class="btn btn-ghost btn-sm">⬇ Download</a>'
            f'</div>')
    if not hist_rows:
        hist_rows = '<div style="color:var(--text-muted);font-size:.85rem;padding:16px 0">No conversions yet</div>'

    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>💳 Convert · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
<style>{_CC_TAB_CSS}{_UPLOAD_CSS}</style>
</head><body>
<nav>
  <span class="nav-brand">💳 Card Converter</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container" style="max-width:860px">
  {_tab_bar("convert", user)}

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
        <div id="fileInfo" style="display:none;margin-top:12px;padding:12px 16px;background:var(--surface-2);border-radius:var(--radius-md);align-items:center;gap:12px">
          <span style="font-size:1.2rem">📄</span>
          <span id="fileName" style="flex:1;font-size:.85rem;font-weight:600;color:var(--text)"></span>
          <button type="submit" class="btn btn-primary">Convert → Review</button>
        </div>
      </form>
      <p style="font-size:.78rem;color:var(--text-muted);margin-top:14px">
        Conversion matches receipts from the Ledger and opens the <b>Review</b> page before download.
      </p>
    </div>
  </div>

  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Recent Conversions</span>
    </div>
    <div class="notepad-body" style="padding:8px 16px 12px">
      {hist_rows}
    </div>
  </div>
</div>
<script>
const csvZone = document.getElementById('dropZone');
const csvInfo = document.getElementById('fileInfo');
const csvName = document.getElementById('fileName');
function handleCsvFile(input){{
  if(input.files[0]){{ csvName.textContent = input.files[0].name; csvInfo.style.display='flex'; csvZone.style.display='none'; }}
}}
csvZone.addEventListener('dragover', e => {{ e.preventDefault(); csvZone.classList.add('drag-over'); }});
csvZone.addEventListener('dragleave', () => csvZone.classList.remove('drag-over'));
csvZone.addEventListener('drop', e => {{
  e.preventDefault(); csvZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if(f){{ document.getElementById('csvFile').files = e.dataTransfer.files; csvName.textContent=f.name; csvInfo.style.display='flex'; csvZone.style.display='none'; }}
}});
</script>
</body></html>'''


# ── Keywords page ────────────────────────────────────────────────────────────

def _render_keywords(user: str) -> str:
    from server import CSS_VER
    kws = _load_kw()
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
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔑 Keywords · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
<style>{_CC_TAB_CSS}
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
  {_tab_bar("keywords", user)}

  <div class="notepad-card" id="keywords">
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
      <div style="max-height:480px;overflow-y:auto">
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
</body></html>'''


# ── Review page ──────────────────────────────────────────────────────────────

def _handle_review_reason(username: str, body: dict):
    """POST /cardconv/review/reason — save a loss reason for an unmatched row."""
    def _val(k):
        v = body.get(k, "")
        return (v[0] if isinstance(v, list) else str(v))
    rid = _val("id").strip()
    reason = _val("reason")
    if not rid:
        return ("json", {"error": "missing id"}, 400)
    review = _load_review(username)
    for r in review.get("rows", []):
        if r.get("id") == rid:
            r["loss_reason"] = reason
            _save_review(username, review)
            return ("json", {"ok": True})
    return ("json", {"error": "not found"}, 404)


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;")) if s is not None else ""


def _render_review(user: str) -> str:
    from server import CSS_VER
    review    = _load_review(user)
    rows      = review.get("rows", [])
    total     = review.get("total", len(rows))
    matched   = review.get("matched", 0)
    unmatched = review.get("unmatched", 0)
    out_fn    = review.get("out_filename", "")
    source    = review.get("source", "")
    gen_at    = (review.get("generated_at", "") or "")[:19].replace("T", " ")

    if not rows:
        body_html = ('<tr><td colspan="6" style="text-align:center;color:var(--text-muted);padding:40px">'
                     'No conversion yet — upload a CSV on the '
                     '<a href="/cardconv/convert" style="color:var(--accent)">Convert</a> tab.</td></tr>')
    else:
        trs = []
        for r in rows:
            is_matched = r.get("matched")
            rc = r.get("receipt") or {}
            if is_matched and rc.get("file_id"):
                fid   = rc["file_id"]
                tn    = f'https://drive.google.com/thumbnail?id={fid}&sz=w80'
                proxy = f'/cardconv/receipts/image/{fid}'
                amt   = rc.get("ocr_amount")
                amt_s = f'${amt:,.2f}' if isinstance(amt, (int, float)) else ''
                link  = (f'<a href="{_esc(rc.get("drive_url"))}" target="_blank" class="btn btn-ghost btn-sm" '
                         f'style="padding:2px 6px">🔗</a>' if rc.get("drive_url") else '')
                receipt_cell = (
                    '<div style="display:flex;align-items:center;gap:8px">'
                    f'<img class="receipt-thumb" src="{tn}" loading="lazy" '
                    f'onerror="this.onerror=null;this.src=\'{proxy}\'">'
                    f'<span style="font-size:.78rem;color:var(--text-muted)">{amt_s}</span>{link}</div>')
                action_cell = '<span class="status-badge status-matched">✅ Matched</span>'
            else:
                receipt_cell = '<span style="color:var(--danger);font-size:.8rem;font-weight:600">❌ Missing</span>'
                action_cell = (f'<textarea class="reason-input" data-id="{_esc(r.get("id"))}" rows="1" '
                               f'placeholder="영수증 분실 사유 입력...">{_esc(r.get("loss_reason"))}</textarea>')
            amount   = r.get("amount")
            amt_disp = f'${amount:,.2f}' if isinstance(amount, (int, float)) else (_esc(amount) or '–')
            row_cls  = '' if is_matched else ' class="row-unmatched"'
            trs.append(
                f'<tr{row_cls}>'
                f'<td>{_esc(r.get("date")) or "–"}</td>'
                f'<td style="font-weight:600">{_esc(r.get("merchant"))}</td>'
                f'<td>{amt_disp}</td>'
                f'<td style="color:var(--text-muted)">{_esc(r.get("gl"))}</td>'
                f'<td>{receipt_cell}</td>'
                f'<td>{action_cell}</td>'
                '</tr>')
        body_html = "".join(trs)

    download_btn = (f'<a href="/cardconv/download/{out_fn}" class="btn btn-primary">⬇ Download xlsx</a>'
                    if out_fn else '')
    meta_line = f'{_esc(source)} &nbsp;·&nbsp; {gen_at}' if source else 'No conversion staged'

    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔍 Review · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
<style>{_CC_TAB_CSS}
.stat-grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}}
.stat-card{{background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);padding:16px 20px;text-align:center}}
.stat-value{{font-size:1.6rem;font-weight:700;color:var(--text);line-height:1.2}}
.stat-label{{font-size:.73rem;color:var(--text-muted);margin-top:4px;text-transform:uppercase;letter-spacing:.06em}}
.rv-table{{width:100%;border-collapse:collapse;font-size:.83rem}}
.rv-table th{{padding:8px 12px;text-align:left;font-size:.72rem;font-weight:700;text-transform:uppercase;letter-spacing:.07em;color:var(--text-muted);border-bottom:1px solid var(--border)}}
.rv-table td{{padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:middle}}
.rv-table tr:last-child td{{border-bottom:none}}
.row-unmatched td{{background:rgba(239,68,68,.07)}}
.receipt-thumb{{width:40px;height:40px;border-radius:6px;object-fit:cover;border:1px solid var(--border);background:var(--surface-3)}}
.status-badge{{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:999px;font-size:.72rem;font-weight:700;white-space:nowrap}}
.status-matched{{background:rgba(34,197,94,.15);color:#22c55e}}
.reason-input{{width:100%;min-width:160px;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:.78rem;padding:5px 8px;outline:none;resize:vertical;font-family:inherit}}
.reason-input:focus{{border-color:var(--accent)}}
.rv-foot{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 4px;flex-wrap:wrap}}
@media(max-width:600px){{.stat-grid{{grid-template-columns:1fr 1fr 1fr}}}}
</style>
</head><body>
<nav>
  <span class="nav-brand">💳 Card Converter</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container" style="max-width:920px">
  {_tab_bar("review", user)}

  <div style="font-size:.8rem;color:var(--text-muted);margin-bottom:12px">{meta_line}</div>

  <div class="stat-grid">
    <div class="stat-card"><div class="stat-value">{total}</div><div class="stat-label">Total</div></div>
    <div class="stat-card"><div class="stat-value" style="color:#22c55e">{matched}</div><div class="stat-label">Matched</div></div>
    <div class="stat-card"><div class="stat-value" style="color:#ef4444">{unmatched}</div><div class="stat-label">Unmatched</div></div>
  </div>

  <div class="notepad-card">
    <div class="notepad-body" style="padding:8px 16px 4px;overflow-x:auto">
      <table class="rv-table">
        <thead><tr>
          <th>Date</th><th>Merchant</th><th>Amount</th><th>G/L Account</th><th>Receipt</th><th>Action</th>
        </tr></thead>
        <tbody>{body_html}</tbody>
      </table>
    </div>
  </div>

  <div class="rv-foot">
    <span style="font-size:.78rem;color:var(--text-muted)">미매칭 거래는 빨간색으로 표시되며 분실 사유를 입력하면 자동 저장됩니다.</span>
    {download_btn}
  </div>
</div>
<script>
document.querySelectorAll('.reason-input').forEach(t => {{
  let last = t.value;
  t.addEventListener('blur', () => {{
    if(t.value === last) return;
    last = t.value;
    fetch('/cardconv/review/reason', {{
      method:'POST', headers:{{'Content-Type':'application/json'}},
      body: JSON.stringify({{id: t.dataset.id, reason: t.value}})
    }});
  }});
}});
</script>
</body></html>'''


def _render_ledger(user: str) -> str:
    from server import CSS_VER
    return (_LEDGER_HTML
            .replace("__CSSVER__", str(CSS_VER))
            .replace("__USER__", user)
            .replace("__TABS__", _tab_bar("ledger", user))
            .replace("__REGISTER__", _register_section(user))
            .replace("__TABCSS__", _CC_TAB_CSS + _UPLOAD_CSS)
            .replace("__RCPTJS__", _RCPT_JS))


# Raw (non-f) template so CSS/JS braces need no escaping; only __TOKENS__ are filled.
_LEDGER_HTML = r'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🧾 Receipt Ledger · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v=__CSSVER__">
<style>
__TABCSS__
.stat-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin-bottom:16px}
.stat-card{background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);
  padding:16px 20px;text-align:center}
.stat-value{font-size:1.6rem;font-weight:700;color:var(--text);line-height:1.2}
.stat-label{font-size:.73rem;color:var(--text-muted);margin-top:4px;text-transform:uppercase;letter-spacing:.06em}
.filter-bar{display:flex;align-items:center;gap:10px;padding:10px 16px;background:var(--surface-2);
  border:1px solid var(--border);border-radius:var(--radius-md);margin-bottom:14px;flex-wrap:wrap}
.filter-bar input[type=date],.filter-bar select{background:var(--surface);border:1px solid var(--border);
  border-radius:6px;color:var(--text);font-size:.82rem;padding:5px 8px;outline:none}
.filter-bar input[type=date]:focus,.filter-bar select:focus{border-color:var(--accent)}
.ledger-table{width:100%;border-collapse:collapse;font-size:.83rem}
.ledger-table th{padding:8px 12px;text-align:left;font-size:.72rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.07em;color:var(--text-muted);border-bottom:1px solid var(--border)}
.ledger-table td{padding:10px 12px;border-bottom:1px solid var(--border);vertical-align:middle}
.ledger-table tbody tr:hover td{background:var(--surface-2);cursor:pointer}
.ledger-table tr:last-child td{border-bottom:none}
.receipt-thumb{width:40px;height:40px;border-radius:6px;object-fit:cover;border:1px solid var(--border);
  background:var(--surface-3);cursor:zoom-in}
.receipt-thumb-placeholder{width:40px;height:40px;border-radius:6px;border:1px dashed var(--border);
  display:flex;align-items:center;justify-content:center;font-size:.75rem;color:var(--text-muted)}
.status-badge{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:999px;
  font-size:.72rem;font-weight:700;white-space:nowrap}
.status-matched{background:rgba(34,197,94,.15);color:#22c55e}
.status-unmatched{background:rgba(239,68,68,.15);color:#ef4444}
.status-pending_match{background:rgba(245,158,11,.15);color:#f59e0b}
.ai-badge{font-size:.62rem;font-weight:700;padding:1px 6px;border-radius:10px;white-space:nowrap}
.ai-badge.gemini{color:#1a73e8;background:rgba(26,115,232,.1)}
.ai-badge.claude{color:#7c3aed;background:rgba(124,58,237,.1)}
.overlay-bg{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:100;opacity:0;pointer-events:none;transition:opacity .2s}
.overlay-bg.open{opacity:1;pointer-events:all}
.detail-panel{position:fixed;top:0;right:0;width:420px;max-width:100vw;height:100vh;background:var(--surface);
  border-left:1px solid var(--border);z-index:101;transform:translateX(100%);
  transition:transform .25s cubic-bezier(.4,0,.2,1);overflow-y:auto;display:flex;flex-direction:column}
.detail-panel.open{transform:translateX(0)}
.detail-panel-header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;
  border-bottom:1px solid var(--border)}
.detail-section{padding:16px 20px;border-bottom:1px solid var(--border)}
.detail-section-title{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
  color:var(--text-muted);margin-bottom:10px}
.detail-row{display:flex;justify-content:space-between;font-size:.84rem;padding:4px 0}
.detail-row .key{color:var(--text-muted)}
.detail-row .val{font-weight:600;color:var(--text)}
.receipt-image-full{width:100%;border-radius:var(--radius-md);border:1px solid var(--border);
  object-fit:contain;max-height:320px;background:var(--surface-2)}
.detail-actions{padding:16px 20px;display:flex;flex-direction:column;gap:8px;margin-top:auto}
.pagination{display:flex;align-items:center;justify-content:center;gap:12px;padding:14px;font-size:.82rem;color:var(--text-muted)}
.pagination button{background:var(--surface-2);border:1px solid var(--border);border-radius:6px;color:var(--text);
  padding:4px 12px;font-size:.8rem;cursor:pointer}
.pagination button:disabled{opacity:.4;cursor:default}
@media(max-width:600px){.detail-panel{width:100vw}.stat-grid{grid-template-columns:1fr 1fr}}
</style>
</head><body>
<nav>
  <span class="nav-brand">💳 Card Converter</span>
  <span class="nav-user">👤 __USER__ &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container" style="max-width:860px">

  __TABS__

  __REGISTER__

  <div class="stat-grid">
    <div class="stat-card"><div class="stat-value" id="statTotal">–</div><div class="stat-label">Total</div></div>
    <div class="stat-card"><div class="stat-value" id="statMatched" style="color:#22c55e">–</div><div class="stat-label">Matched</div></div>
    <div class="stat-card"><div class="stat-value" id="statUnmatched" style="color:#ef4444">–</div><div class="stat-label">Unmatched</div></div>
  </div>

  <div class="filter-bar">
    📅 <input type="date" id="fFrom"> ~ <input type="date" id="fTo">
    <span style="margin-left:8px">Status:</span>
    <select id="fStatus">
      <option value="all">All</option>
      <option value="matched">Matched</option>
      <option value="unmatched">Unmatched</option>
      <option value="pending_match">Pending Match</option>
    </select>
    <button class="btn btn-ghost btn-sm" id="fReset">Reset</button>
    <button class="btn btn-secondary btn-sm" id="fDownload" style="margin-left:auto">📄 Download as PDF</button>
  </div>

  <div class="notepad-card">
    <div class="notepad-body" style="padding:8px 16px 4px">
      <table class="ledger-table">
        <thead><tr>
          <th>Date</th><th>Printed</th><th>Handwritten</th><th>Final</th><th>Merchant</th><th>Receipt</th><th>Status</th><th>AI</th>
        </tr></thead>
        <tbody id="ledgerBody"></tbody>
      </table>
      <div class="pagination">
        <button id="pPrev">Prev</button>
        <span id="pInfo">1 / 1</span>
        <button id="pNext">Next</button>
      </div>
    </div>
  </div>

</div>

<div class="overlay-bg" id="overlay"></div>
<div class="detail-panel" id="panel">
  <div class="detail-panel-header">
    <span style="font-weight:700;font-size:.95rem">Receipt Detail</span>
    <button class="btn btn-ghost btn-sm" id="panelClose">× Close</button>
  </div>
  <div class="detail-section">
    <div class="detail-section-title">Receipt Image</div>
    <img class="receipt-image-full" id="dImage" alt="receipt">
  </div>
  <div class="detail-section">
    <div class="detail-section-title">OCR Result</div>
    <div class="detail-row"><span class="key">Date</span><span class="val" id="dDate">–</span></div>
    <div class="detail-row"><span class="key">Amount (final)</span><span class="val" id="dAmount">–</span></div>
    <div class="detail-row"><span class="key">Printed</span><span class="val" id="dPrinted">–</span></div>
    <div class="detail-row"><span class="key">Handwritten</span><span class="val" id="dHand">–</span></div>
    <div class="detail-row"><span class="key">Merchant</span><span class="val" id="dMerchant">–</span></div>
    <div class="detail-row"><span class="key">AI Model</span><span class="val" id="dModel">–</span></div>
  </div>
  <div class="detail-section" id="dMatchSection">
    <div class="detail-section-title">Matched CSV Transaction</div>
    <div class="detail-row"><span class="key">Date</span><span class="val" id="dmDate">–</span></div>
    <div class="detail-row"><span class="key">Amount</span><span class="val" id="dmAmount">–</span></div>
    <div class="detail-row"><span class="key">Vendor</span><span class="val" id="dmVendor">–</span></div>
  </div>
  <div class="detail-section">
    <div class="detail-section-title">Status</div>
    <div id="dStatus"></div>
  </div>
  <div class="detail-actions">
    <button class="btn btn-ghost btn-sm" data-set="matched" style="color:#22c55e">✅ Mark Matched</button>
    <button class="btn btn-ghost btn-sm" data-set="unmatched" style="color:#ef4444">❌ Mark Unmatched</button>
    <button class="btn btn-ghost btn-sm" data-set="pending_match" style="color:#f59e0b">⏳ Mark Pending</button>
  </div>
</div>

<script>
let CUR_PAGE = 1, CUR_ID = null, ENTRIES = [];
const $ = id => document.getElementById(id);
const STATUS_LABEL = {matched:'✅ Matched', unmatched:'❌ Unmatched', pending_match:'⏳ Pending Match'};

function fmtAmt(a){ return (a===null||a===undefined) ? '–' : '$' + Number(a).toFixed(2); }

function thumb(e){
  if(!e.file_id) return '<div class="receipt-thumb-placeholder">🧾</div>';
  const proxy = '/cardconv/receipts/image/' + e.file_id;
  const tn = 'https://drive.google.com/thumbnail?id=' + e.file_id + '&sz=w80';
  return '<img class="receipt-thumb" src="' + tn + '" loading="lazy" ' +
         'onerror="this.onerror=null;this.src=\'' + proxy + '\'">';
}

function aiBadge(m){
  if(m==='Gemini') return '<span class="ai-badge gemini">Gemini</span>';
  if(m==='Claude') return '<span class="ai-badge claude">Claude</span>';
  return '<span style="color:var(--text-muted);font-size:.72rem">–</span>';
}

async function load(){
  const p = new URLSearchParams();
  if($('fFrom').value) p.set('from', $('fFrom').value);
  if($('fTo').value)   p.set('to', $('fTo').value);
  p.set('status', $('fStatus').value);
  p.set('page', CUR_PAGE);
  const r = await fetch('/cardconv/ledger/api?' + p.toString());
  const d = await r.json();
  $('statTotal').textContent = d.total;
  $('statMatched').textContent = d.matched;
  $('statUnmatched').textContent = d.unmatched;
  ENTRIES = d.entries;
  const body = $('ledgerBody');
  if(!d.entries.length){
    body.innerHTML = '<tr><td colspan="8" style="text-align:center;color:var(--text-muted);padding:30px">No receipts</td></tr>';
  } else {
    body.innerHTML = d.entries.map((e,i) => {
      const h = e.ocr_handwritten_amount;
      const handCell = (h===null||h===undefined)
        ? '<td style="color:var(--text-muted)">–</td>'
        : '<td style="color:#f59e0b;font-weight:600">' + fmtAmt(h) + ' ✍️</td>';
      return '<tr data-i="' + i + '">' +
        '<td>' + (e.ocr_date||'–') + '</td>' +
        '<td style="color:var(--text-muted)">' + fmtAmt(e.ocr_printed_amount) + '</td>' +
        handCell +
        '<td style="font-weight:700">' + fmtAmt(e.ocr_amount) + '</td>' +
        '<td>' + (e.ocr_merchant||'–') + '</td>' +
        '<td>' + thumb(e) + '</td>' +
        '<td><span class="status-badge status-' + (e.match_status||'unmatched') + '">' +
          (STATUS_LABEL[e.match_status]||e.match_status||'–') + '</span></td>' +
        '<td>' + aiBadge(e.ocr_model) + '</td>' +
      '</tr>';
    }).join('');
    body.querySelectorAll('tr[data-i]').forEach(tr =>
      tr.addEventListener('click', () => openPanel(ENTRIES[+tr.dataset.i])));
  }
  $('pInfo').textContent = d.page + ' / ' + d.pages;
  $('pPrev').disabled = d.page <= 1;
  $('pNext').disabled = d.page >= d.pages;
  CUR_PAGE = d.page;
  window._pages = d.pages;
}

function openPanel(e){
  CUR_ID = e.id;
  $('dDate').textContent = e.ocr_date || '–';
  $('dAmount').textContent = fmtAmt(e.ocr_amount);
  $('dPrinted').textContent = fmtAmt(e.ocr_printed_amount);
  const hand = (e.ocr_handwritten_amount===null||e.ocr_handwritten_amount===undefined);
  $('dHand').textContent = hand ? '–' : (fmtAmt(e.ocr_handwritten_amount) + ' ✍️');
  $('dHand').style.color = hand ? '' : '#f59e0b';
  $('dMerchant').textContent = e.ocr_merchant || '–';
  $('dModel').textContent = e.ocr_model || '–';
  const img = $('dImage');
  if(e.file_id){ img.src = '/cardconv/receipts/image/' + e.file_id; img.style.display='block'; }
  else { img.style.display='none'; }
  const mt = e.matched_transaction;
  $('dMatchSection').style.display = mt ? 'block' : 'none';
  if(mt){
    $('dmDate').textContent = mt.date || '–';
    $('dmAmount').textContent = fmtAmt(mt.amount);
    $('dmVendor').textContent = mt.vendor || '–';
  }
  $('dStatus').innerHTML = '<span class="status-badge status-' + (e.match_status||'unmatched') + '">' +
    (STATUS_LABEL[e.match_status]||e.match_status||'–') + '</span>';
  $('overlay').classList.add('open');
  $('panel').classList.add('open');
}

function closePanel(){
  $('overlay').classList.remove('open');
  $('panel').classList.remove('open');
  CUR_ID = null;
}

async function setStatus(status){
  if(!CUR_ID) return;
  await fetch('/cardconv/ledger/' + CUR_ID + '/status', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({status: status})
  });
  closePanel();
  load();
}

function setDefaultDates(){
  const now = new Date();
  const first = new Date(now.getFullYear(), now.getMonth(), 1);
  const iso = d => d.toISOString().slice(0,10);
  $('fFrom').value = iso(first);
  $('fTo').value = iso(now);
}

document.querySelectorAll('.detail-actions button').forEach(b =>
  b.addEventListener('click', () => setStatus(b.dataset.set)));
$('panelClose').addEventListener('click', closePanel);
$('overlay').addEventListener('click', closePanel);
document.addEventListener('keydown', e => { if(e.key==='Escape') closePanel(); });
$('fFrom').addEventListener('change', () => { CUR_PAGE=1; load(); });
$('fTo').addEventListener('change', () => { CUR_PAGE=1; load(); });
$('fStatus').addEventListener('change', () => { CUR_PAGE=1; load(); });
$('fReset').addEventListener('click', () => { $('fStatus').value='all'; setDefaultDates(); CUR_PAGE=1; load(); });
$('fDownload').addEventListener('click', () => {
  // Download respects the currently applied filters (status + date range).
  const p = new URLSearchParams();
  if($('fFrom').value) p.set('from', $('fFrom').value);
  if($('fTo').value)   p.set('to', $('fTo').value);
  p.set('status', $('fStatus').value);
  window.location = '/cardconv/ledger/download.pdf?' + p.toString();
});
$('pPrev').addEventListener('click', () => { if(CUR_PAGE>1){CUR_PAGE--; load();} });
$('pNext').addEventListener('click', () => { if(CUR_PAGE<window._pages){CUR_PAGE++; load();} });

setDefaultDates();
load();
</script>
<script>__RCPTJS__</script>
</body></html>'''
