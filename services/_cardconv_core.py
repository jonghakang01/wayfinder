import csv, io, json, os, re, base64, uuid
from datetime import date, datetime
from pathlib import Path

import openpyxl

# ── Web Push helpers ──────────────────────────────────────────────────────────
def _push_subs_file(username: str) -> Path:
    return DATA_DIR / f"push_subs_{username}.json"

def _load_push_subs(username: str) -> list:
    f = _push_subs_file(username)
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text())
    except Exception:
        return []

def _save_push_subs(username: str, subs: list):
    _push_subs_file(username).write_text(json.dumps(subs, ensure_ascii=False))

def _send_push_notification(username: str, title: str, body: str, url: str = "/cardconv/ledger"):
    """Send Web Push to all stored subscriptions for the user. Silently skips on error."""
    subs = _load_push_subs(username)
    if not subs:
        return
    pem_path = DATA_DIR / "vapid_private.pem"
    if not pem_path.exists():
        return
    try:
        from pywebpush import webpush, WebPushException
        payload = json.dumps({"title": title, "body": body, "url": url})
        pem = pem_path.read_text()
        dead = []
        for sub in subs:
            try:
                webpush(
                    subscription_info=sub,
                    data=payload,
                    vapid_private_key=pem,
                    vapid_claims={"sub": "mailto:jongha.kang01@gmail.com"},
                    content_encoding="aes128gcm",
                )
            except WebPushException as e:
                if e.response and e.response.status_code in (404, 410):
                    dead.append(sub)
        if dead:
            _save_push_subs(username, [s for s in subs if s not in dead])
    except Exception:
        pass

from services._paths import DATA_ROOT
DATA_DIR   = Path(DATA_ROOT) / "cardconv"
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
    "name": "Cheil USA AMEX Converter",
    "path": "/cardconv",
    "icon": "💳",
    "description": "Corporate card CSV → SAP upload xlsx",
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
    if "id" not in entry:
        entry["id"] = uuid.uuid4().hex[:10]
    hist = _load_hist()
    hist.insert(0, entry)
    _save_hist(hist[:100])


def _receipts_file(username: str) -> Path:
    return DATA_DIR / f"receipts_{username}.json"


def _migrate_entry(e: dict) -> dict:
    """Ensure a receipt entry has v2 fields (id, ocr_status, match_status)."""
    e = dict(e)
    if not e.get("id"):
        e["id"] = "rcpt_" + (e.get("file_id") or uuid.uuid4().hex)[:8]
    # Multi-receipt: legacy entries are the only receipt on their image → index 0.
    e.setdefault("sub_index", 0)
    if "ocr_status" not in e:
        e["ocr_status"] = "done" if e.get("ocr_amount") is not None else "pending"
    # v2.1: handwritten-priority OCR. Legacy entries keep ocr_amount as printed total.
    e.setdefault("ocr_printed_amount", e.get("ocr_amount"))
    e.setdefault("ocr_handwritten_amount", None)
    # v2.2: multi-receipt bounding box overlay. Legacy entries have no bbox.
    e.setdefault("ocr_bbox", None)
    # v2.3: card brand (amex/visa/other, OCR-detected, user-editable), usage tag
    # (default "Regular"), and completion state (completed entries are hidden from
    # the default Ledger view, Sync and Mapping, and their Drive originals are
    # moved to a "Completed" folder).
    e.setdefault("card_brand", None)
    e.setdefault("usage", "Regular")
    e.setdefault("completed", False)
    e.setdefault("completed_at", None)
    e.setdefault("archived_drive", False)
    if "match_status" not in e:
        if e.get("matched"):
            e["match_status"] = "matched"
        else:
            # Initial state is always pending_match. unmatched is reserved for
            # receipts that were tried against a CSV but failed to match.
            e["match_status"] = "pending_match"
    # Backfill OCR date from the matched CSV transaction for legacy entries that
    # were matched while OCR failed to read a date.
    if e.get("match_status") == "matched" and e.get("ocr_date") in (None, "", "unknown"):
        mt_date = (e.get("matched_transaction") or {}).get("date")
        if mt_date:
            e["ocr_date_original"] = e.get("ocr_date")
            e["ocr_date"] = mt_date
    # A matched receipt is an AMEX transaction (the CSV is an AMEX statement);
    # backfill the brand for already-matched entries that predate card detection.
    if e.get("match_status") == "matched" and not e.get("card_brand"):
        e["card_brand"] = "amex"
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


# ── OCR Staging (pre-ledger visual review) ────────────────────────────────────

def _ocr_staging_file(username: str) -> Path:
    return DATA_DIR / f"ocr_staging_{username}.json"

def _load_ocr_staging(username: str) -> dict:
    f = _ocr_staging_file(username)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {"entries": []}

def _save_ocr_staging(username: str, data: dict):
    _ensure_dirs()
    _ocr_staging_file(username).write_text(json.dumps(data, ensure_ascii=False, indent=2))

def _clear_ocr_staging(username: str):
    f = _ocr_staging_file(username)
    if f.exists():
        f.unlink()

def _handle_ocr_staging_confirm(username: str, body: dict):
    """POST /cardconv/receipts/review/confirm (JSON) — apply manual edits and add to ledger.

    Expects JSON body: {"confirmed": [{"id":..., "ocr_date":..., "ocr_merchant":...,
                                       "ocr_amount":..., "ocr_handwritten_amount":...}, ...]}
    Also accepts legacy FormData with just confirmed[] IDs (no edits).
    """
    staging = _load_ocr_staging(username)
    all_entries = staging.get("entries", [])

    # Build a correction map from the JSON payload.
    confirmed_list = body.get("confirmed", [])
    is_ajax = (isinstance(confirmed_list, list) and confirmed_list
               and isinstance(confirmed_list[0], dict))
    if is_ajax:
        # JSON path (modal fetch): each item has id + corrected fields
        corrections = {item["id"]: item for item in confirmed_list if "id" in item}
        confirmed_ids = set(corrections.keys())
    else:
        # Legacy FormData path: just a list of IDs, no corrections
        if isinstance(confirmed_list, str):
            confirmed_list = [confirmed_list]
        confirmed_ids = set(confirmed_list)
        corrections = {}

    confirmed = []
    for e in all_entries:
        if e.get("id") not in confirmed_ids:
            continue
        entry = dict(e)
        fix = corrections.get(e["id"], {})
        if fix.get("ocr_date") is not None:
            entry["ocr_date"] = fix["ocr_date"] or None
        if fix.get("ocr_merchant") is not None:
            entry["ocr_merchant"] = fix["ocr_merchant"] or None
        for amt_key in ("ocr_amount", "ocr_handwritten_amount"):
            raw = fix.get(amt_key)
            if raw is not None:
                try:
                    entry[amt_key] = float(raw) if str(raw).strip() else None
                except (ValueError, TypeError):
                    pass
        # Recompute final amount after manual correction.
        hw = entry.get("ocr_handwritten_amount")
        pr = entry.get("ocr_amount")
        entry["ocr_final_amount"] = hw if hw is not None else pr
        confirmed.append(entry)

    if confirmed:
        receipts = _load_receipts(username)
        receipts.extend(confirmed)
        _save_receipts(username, receipts)

    _clear_ocr_staging(username)
    # Native form (staging page) submissions navigate the browser, so send them
    # back to the Ledger; the modal's fetch path keeps getting JSON.
    if is_ajax:
        return ("json", {"ok": True, "added": len(confirmed)})
    return ("redirect", "/cardconv/ledger")


# ── User settings: card member names ──────────────────────────────────────────

DEFAULT_CARD_NAMES = ["JONG KANG", "JONGHA KANG"]


def _user_settings_file(username: str) -> Path:
    return DATA_DIR / f"user_settings_{username}.json"


def _load_user_settings(username: str) -> dict:
    f = _user_settings_file(username)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return {}


def _save_user_settings(username: str, data: dict):
    _ensure_dirs()
    _user_settings_file(username).write_text(json.dumps(data, ensure_ascii=False, indent=2))


def _get_card_member_names(username: str) -> list:
    """User's card member names (uppercased). Defaults to JONG/JONGHA KANG."""
    if not username:
        return list(DEFAULT_CARD_NAMES)
    names = _load_user_settings(username).get("card_member_names")
    if not names:
        return list(DEFAULT_CARD_NAMES)
    return [n.strip().upper() for n in names if str(n).strip()]


# ── Uploaded CSV store (Convert page reuse) ────────────────────────────────────

def _uploads_dir(username: str) -> Path:
    return DATA_DIR / f"uploads_{username}"


def _uploads_index_file(username: str) -> Path:
    return DATA_DIR / f"uploads_{username}.json"


def _load_uploads(username: str) -> list:
    f = _uploads_index_file(username)
    if f.exists():
        try:
            return json.loads(f.read_text())
        except Exception:
            pass
    return []


def _save_uploads(username: str, items: list):
    _ensure_dirs()
    _uploads_index_file(username).write_text(json.dumps(items, ensure_ascii=False, indent=2))


def _save_uploaded_csv(username: str, csv_bytes: bytes, orig_name: str,
                       rows: int, out_filename: str) -> dict:
    """Persist the raw CSV under uploads_{user}/ and index it for reuse."""
    d = _uploads_dir(username)
    d.mkdir(parents=True, exist_ok=True)
    uid = "csv_" + uuid.uuid4().hex[:8]
    (d / f"{uid}.csv").write_bytes(csv_bytes)
    entry = {
        "id":           uid,
        "filename":     orig_name,
        "stored_name":  f"{uid}.csv",
        "uploaded_at":  datetime.now().strftime("%Y-%m-%d %H:%M"),
        "rows":         rows,
        "out_filename": out_filename,
    }
    items = _load_uploads(username)
    items.insert(0, entry)
    _save_uploads(username, items)
    return entry


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


def _get_receipts_folder_id(service, username: str) -> str:
    """Return the Wayfinder/Receipts/ folder id, creating it if needed.
    (The legacy Matched/ subfolder is no longer created or used.)"""
    wayfinder_id = _get_or_create_folder(service, 'Wayfinder')
    receipts_id  = _get_or_create_folder(service, 'Receipts', wayfinder_id)
    # Cache receipts folder ID for UI link
    meta = _load_drive_meta(username)
    if meta.get('receipts_folder_id') != receipts_id:
        meta['receipts_folder_id'] = receipts_id
        _save_drive_meta(username, meta)
    return receipts_id


def _upload_file_to_drive(username: str, file_bytes: bytes, filename: str,
                           mime_type: str) -> tuple:
    """Upload to Drive under Wayfinder/Receipts/. Returns (file_id, drive_url)."""
    from googleapiclient.http import MediaIoBaseUpload
    service = _get_drive_service(username)
    if not service:
        return None, None
    receipts_id = _get_receipts_folder_id(service, username)
    media  = MediaIoBaseUpload(io.BytesIO(file_bytes), mimetype=mime_type)
    result = service.files().create(
        body={'name': filename, 'parents': [receipts_id]},
        media_body=media,
        fields='id,webViewLink'
    ).execute()
    fid = result.get('id')
    url = result.get('webViewLink') or f'https://drive.google.com/file/d/{fid}/view'
    return fid, url


# ── OCR ───────────────────────────────────────────────────────────────────────

_OCR_PROMPT = (
    'This image may contain ONE OR MULTIPLE receipts (e.g. several small '
    'receipts scanned together on a single page). Identify EACH distinct receipt. '
    'For EACH receipt look CAREFULLY for handwritten numbers (e.g. tip amount, '
    'final total written by hand on top of the printed receipt). '
    'Inspect tip line, total line, and any margin notes for handwriting. '
    'For each receipt extract: '
    '1) date (YYYY-MM-DD), '
    '2) merchant name, '
    '3) printed_amount: the PRINTED/typed total (number only), '
    '4) handwritten_amount: any HAND-WRITTEN final amount including tip (number only, '
    'null if none visible). '
    'Handwritten amount, when present, is the REAL final amount and overrides printed. '
    '5) card_brand: the payment card brand used, normalized to one of "amex", '
    '"visa", "other", or null only if there is NO card information at all (e.g. '
    'cash payment). Determine it from BOTH of these signals: '
    '(a) brand text/logo on the receipt — "AMERICAN EXPRESS"/"AMEX"/"AMX" -> "amex", '
    '"VISA" -> "visa", any other brand (Mastercard, Discover, etc.) -> "other"; AND '
    '(b) the card account number, even when masked (e.g. "XXXX-XXXXXX-X1234", '
    '"************1234", "ending in 1234", "AETC 3759"): use the FIRST visible digit '
    '- a number starting with 3 (15-digit, 4-6-5 grouping) -> "amex"; starting with 4 '
    '-> "visa"; starting with 2 or 5 -> "other". If (a) and (b) disagree, prefer the '
    'explicit brand text. AMEX receipts often show "AMEX", "AETC", or a 15-digit / '
    '3-prefixed card number — treat any of these as "amex". '
    'For each receipt, ALSO return its bounding box in the image as bbox: '
    '[ymin, xmin, ymax, xmax] using a 0-1000 normalized coordinate system '
    '(0=top/left, 1000=bottom/right). '
    'Return a JSON ARRAY ONLY, one object per receipt: '
    '[{"date":"YYYY-MM-DD","merchant":"name","printed_amount":0.00,"handwritten_amount":null,'
    '"card_brand":"amex","bbox":[100,50,800,950]}]. '
    'If only one receipt is visible, return an array with a single element.'
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
    # bbox: [ymin, xmin, ymax, xmax] in 0-1000 normalized coords (None if absent/invalid).
    result["bbox"] = _coerce_bbox(result.get("bbox"))
    result["card_brand"] = _coerce_card_brand(result.get("card_brand"))
    return result


def _coerce_card_brand(v):
    """Normalize a model's card-brand string to 'amex'/'visa'/'other' or None."""
    if not v:
        return None
    s = str(v).strip().lower()
    if not s or s in ("null", "none", "unknown"):
        return None
    if "amex" in s or "american express" in s or s == "amx":
        return "amex"
    if "visa" in s:
        return "visa"
    return "other"


def _coerce_bbox(v):
    """Validate a model bbox into [ymin, xmin, ymax, xmax] ints, or None."""
    if not isinstance(v, (list, tuple)) or len(v) != 4:
        return None
    try:
        box = [int(round(float(x))) for x in v]
    except (ValueError, TypeError):
        return None
    # Clamp to the 0-1000 normalized range and require a positive area.
    box = [max(0, min(1000, c)) for c in box]
    ymin, xmin, ymax, xmax = box
    if ymax <= ymin or xmax <= xmin:
        return None
    return box


def _extract_ocr_list(text: str) -> list:
    """Parse a model OCR response into a list of normalized receipt dicts.

    Accepts either a JSON ARRAY (multi-receipt, current prompt) or a single
    JSON OBJECT (back-compat). Returns [] when nothing parseable is found.
    """
    if not text:
        return []
    text = text.strip()
    parsed = None
    # Prefer a top-level array (one image may hold multiple receipts).
    m = re.search(r'\[.*\]', text, re.DOTALL)
    if m:
        try:
            parsed = json.loads(m.group(0))
        except Exception:
            parsed = None
    if parsed is None:  # fall back to a single object
        m = re.search(r'\{.*\}', text, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
            except Exception:
                parsed = None
    if parsed is None:
        return []
    if isinstance(parsed, dict):
        parsed = [parsed]
    return [_normalize_ocr(item) for item in parsed if isinstance(item, dict)]


def _ocr_receipt(file_bytes: bytes, mime_type: str) -> list:
    """OCR receipt(s) using Claude Vision. Returns a list of receipt dicts (may be empty)."""
    api_key = os.environ.get('ANTHROPIC_API_KEY')
    if not api_key:
        return []
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
            max_tokens=1024,  # room for multiple receipts in one image
            messages=[{"role": "user", "content": [
                block,
                {"type": "text", "text": _OCR_PROMPT}
            ]}]
        )
        results = _extract_ocr_list(resp.content[0].text)
        for r in results:
            r["_model"] = "Claude"
        return results
    except Exception:
        pass
    return []


# Configurable via GEMINI_OCR_MODEL (.env). gemini-2.5-flash: fast/cheap, strong on
# KR+EN receipts. Bump to gemini-2.5-pro if accuracy issues arise (~10x cost).
_DEFAULT_GEMINI_OCR_MODEL = "gemini-2.5-flash"


def _ocr_receipt_gemini(file_bytes: bytes, mime_type: str) -> list:
    """OCR receipt(s) using Gemini Vision. Returns a list of receipt dicts (may be empty)."""
    api_key = os.environ.get('GEMINI_API_KEY')
    if not api_key:
        return []
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
        results = _extract_ocr_list(resp.text or "")
        for r in results:
            r["_model"] = "Gemini"
        return results
    except Exception:
        pass
    return []


def _ocr_receipt_auto(file_bytes: bytes, mime_type: str) -> list:
    """Primary OCR: Gemini first, fall back to Claude. Returns a list of receipt dicts.

    One image may contain multiple receipts, so callers must iterate the result.
    """
    results = _ocr_receipt_gemini(file_bytes, mime_type)
    if results and any(r.get("amount") is not None for r in results):
        return results
    claude = _ocr_receipt(file_bytes, mime_type)
    return claude or results


def _sub_entry_id(file_id: str, sub_index: int) -> str:
    """Stable ledger entry id for the Nth receipt found in one image."""
    base = (file_id or uuid.uuid4().hex)[:8]
    return f"rcpt_{base}_{sub_index}"


def _ocr_entry_fields(ocr: dict) -> dict:
    """Map a normalized OCR dict to the ledger entry's ocr_* fields."""
    ocr_date = ocr.get("date")
    if ocr_date == "YYYY-MM-DD":  # treat placeholder as missing
        ocr_date = None
    has_ocr = ocr.get("amount") is not None
    return {
        "ocr_status":             "done" if has_ocr else "failed",
        "ocr_date":               ocr_date,
        "ocr_amount":             ocr.get("amount"),
        "ocr_printed_amount":     ocr.get("printed_amount"),
        "ocr_handwritten_amount": ocr.get("handwritten_amount"),
        "ocr_merchant":           ocr.get("merchant"),
        "ocr_model":              ocr.get("_model"),
        "ocr_bbox":               ocr.get("bbox"),
        "card_brand":             ocr.get("card_brand"),
    }


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

    target_names = set(_get_card_member_names(username))
    reader = csv.DictReader(io.TextIOWrapper(io.BytesIO(csv_bytes), encoding='utf-8-sig', newline=''))
    rows   = [r for r in reader if r.get("Card Member Name","").strip().upper() in target_names]

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
            if r.get("completed"):
                continue  # completed receipts are archived — excluded from mapping
            rdate = r.get("ocr_date")
            if rdate == "YYYY-MM-DD":
                rdate = None
            # Handwritten amount takes priority as the final match target.
            hw = r.get("ocr_handwritten_amount")
            pr = r.get("ocr_printed_amount") or r.get("ocr_amount")
            ramount = hw if hw is not None else pr
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

        # Receipt match in column 27
        inv_date_str = inv_dt.strftime("%Y-%m-%d") if inv_dt else None
        amt_rounded  = round(amount, 2)
        receipt_match = None
        if receipts_map:
            receipt_match = receipts_map.get((inv_date_str, amt_rounded))
            if not receipt_match:
                for (rdate, ramt), r in receipts_map.items():
                    amt_match = abs(ramt - amt_rounded) <= 0.01
                    if not amt_match:
                        continue
                    if rdate is None:
                        date_match = True
                    elif rdate == inv_date_str:
                        date_match = True
                    else:
                        # Allow ±1 day for card posting date vs transaction date skew
                        try:
                            from datetime import timedelta
                            rd = date.fromisoformat(rdate)
                            id_ = date.fromisoformat(inv_date_str) if inv_date_str else None
                            date_match = id_ is not None and abs((rd - id_).days) <= 1
                        except Exception:
                            date_match = False
                    if date_match:
                        receipt_match = r
                        break
            if receipt_match:
                fn  = receipt_match.get('filename', '')
                url = receipt_match.get('drive_url', '')
                ws.cell(start, 27).value = f"✅ {fn} ({url})" if url else f"✅ {fn}"
                # Update match metadata always (even if Drive folder move fails).
                if not receipt_match.get('matched'):
                    receipt_match['matched'] = True
                    receipt_match['match_status'] = 'matched'
                    receipt_match['matched_at'] = datetime.now().isoformat()
                    receipt_match['matched_transaction'] = {
                        'date':   inv_date_str,
                        'amount': amt_rounded,
                        'vendor': vendor,
                    }
                    # The CSV is an AMEX statement, so a matched receipt is an AMEX
                    # transaction — fill the brand when OCR left it unknown (don't
                    # override an explicit OCR reading).
                    if not receipt_match.get('card_brand'):
                        receipt_match['card_brand'] = 'amex'
                    # Backfill OCR date from the matched CSV transaction when OCR
                    # failed to read it. Keep the original in ocr_date_original.
                    if receipt_match.get('ocr_date') in (None, '', 'unknown') and inv_date_str:
                        receipt_match['ocr_date_original'] = receipt_match.get('ocr_date')
                        receipt_match['ocr_date'] = inv_date_str
                    receipts_dirty = True
                    # NOTE: Drive folder auto-move is deprecated. Drive is a plain
                    # store; the Wayfinder ledger is the single source of truth.
            else:
                ws.cell(start, 27).value = "❌ Missing"

        # Collect a Review row for this transaction
        rcpt_info = None
        if receipt_match:
            receipt_matched += 1
            mfid = receipt_match.get("file_id")
            # Sibling receipts sharing the same source image (multi-receipt page).
            # Used to draw every bbox in the lightbox and highlight the matched one.
            siblings = [
                {"id": s.get("id"), "ocr_bbox": s.get("ocr_bbox")}
                for s in receipts
                if mfid and s.get("file_id") == mfid and s.get("ocr_bbox")
            ]
            rcpt_info = {
                "file_id":      mfid,
                "id":           receipt_match.get("id"),
                "filename":     receipt_match.get("filename"),
                "drive_url":    receipt_match.get("drive_url"),
                "ocr_amount":   receipt_match.get("ocr_amount"),
                "ocr_date":     receipt_match.get("ocr_date"),
                "ocr_merchant": receipt_match.get("ocr_merchant"),
                "ocr_bbox":     receipt_match.get("ocr_bbox"),
                "siblings":     siblings if len(siblings) > 1 else [],
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
        receipts_id = _get_receipts_folder_id(service, username)
        results = service.files().list(
            q=(f"'{receipts_id}' in parents "
               f"and trashed=false and mimeType!='application/vnd.google-apps.folder'"),
            fields="files(id,name,mimeType,webViewLink)"
        ).execute()
        drive_files = results.get('files', [])

        ledger  = _load_ledger(username)
        entries = ledger["entries"]

        # Skip files already confirmed in the ledger.
        done_fids = {e.get("file_id") for e in entries
                     if (e.get("multi_ocr") and e.get("ocr_amount") is not None)
                     or e.get("matched") or e.get("completed")}
        # Also skip files already waiting in the staging queue (accumulated from
        # previous runs the user hasn't reviewed yet).
        staging = _load_ocr_staging(username)
        staged_fids = {e.get("file_id") for e in staging.get("entries", [])}
        skip_fids = done_fids | staged_fids

        new_staged = []
        now_disp = datetime.now().strftime("%Y-%m-%d %H:%M")
        now_iso  = datetime.now().isoformat()

        for f in drive_files:
            fid  = f.get('id')
            mime = f.get('mimeType', '')
            if mime not in _SUPPORTED_MIME:
                continue
            if fid in skip_fids:
                continue
            content  = service.files().get_media(fileId=fid).execute()
            ocr_list = _ocr_receipt_auto(content, mime) or [{}]
            url      = f.get('webViewLink') or f'https://drive.google.com/file/d/{fid}/view'
            for sub_index, ocr in enumerate(ocr_list):
                entry = {
                    "id":           _sub_entry_id(fid, sub_index),
                    "file_id":      fid,
                    "sub_index":    sub_index,
                    "filename":     f.get('name', ''),
                    "drive_url":    url,
                    "mime_type":    mime,
                    "match_status": "pending_match",
                    "multi_ocr":    True,
                    "uploaded_at":  now_disp,
                    "synced_at":    now_iso,
                }
                entry.update(_ocr_entry_fields(ocr))
                new_staged.append(entry)

        # Accumulate into staging queue — never replace, always append.
        if new_staged:
            staging.setdefault("entries", []).extend(new_staged)
            staging["staged_at"] = now_iso
            _save_ocr_staging(username, staging)

        ledger["last_batch_at"] = now_iso
        _save_ledger(username, ledger)

        if new_staged:
            total_pending = len(staging.get("entries", []))
            _send_push_notification(
                username,
                title="🧾 New receipts ready to review",
                body=f"{len(new_staged)} new receipt{'s' if len(new_staged) != 1 else ''} synced from Drive — {total_pending} total pending review.",
                url="/cardconv/ledger",
            )
        return {"staged": len(new_staged), "total_pending": len(staging.get("entries", []))}
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


def _apply_ledger_filters(entries: list, status: str, dfrom: str, dto: str,
                          card_brand: str = "", usage: str = "",
                          completed: str = "hide") -> list:
    """Filter + sort ledger entries by status, OCR-date range, card brand, usage
    and completion state.

    Shared by the JSON API, the PDF export and the xlsx export so all honor
    identical filters. Date filters keep entries without an OCR date always
    visible. `completed` is one of: "hide" (default — exclude completed),
    "only" (completed only), "all" (include both).
    """
    filtered = entries
    if status and status != "all":
        filtered = [e for e in filtered if e.get("match_status") == status]
    if dfrom:
        filtered = [e for e in filtered if not e.get("ocr_date") or e["ocr_date"] >= dfrom]
    if dto:
        filtered = [e for e in filtered if not e.get("ocr_date") or e["ocr_date"] <= dto]
    if card_brand and card_brand != "all":
        if card_brand == "unknown":
            filtered = [e for e in filtered if not e.get("card_brand")]
        else:
            filtered = [e for e in filtered if e.get("card_brand") == card_brand]
    if usage and usage != "all":
        filtered = [e for e in filtered if (e.get("usage") or "Regular") == usage]
    if completed == "only":
        filtered = [e for e in filtered if e.get("completed")]
    elif completed != "all":  # "hide" (default)
        filtered = [e for e in filtered if not e.get("completed")]
    return sorted(
        filtered,
        key=lambda e: e.get("ocr_date") or e.get("uploaded_at") or "",
        reverse=True,
    )


def _mark_duplicates(entries: list):
    """Flag likely-duplicate receipts in-place.

    Two receipts are duplicates when their final amount and merchant match AND
    their dates are compatible — equal, or at least one side missing (OCR often
    fails to read a date on one copy of the same receipt). Date is deliberately
    NOT part of the bucket key so a date-less entry still groups with its dated
    twin; multi-receipt sub-entries (different file_id, same OCR values) group
    too since file_id is ignored. Within a group the keeper / head is chosen by
    match_status priority (matched > unmatched > pending_match), then a present
    date; the rest are flagged for easy bulk-deletion.
    Sets e['dup'] (bool), e['dup_keep'] (bool) and e['dup_group_id'] (str|None)
    on each entry. dup_group_id lets the UI collapse a group into one row.
    """
    for e in entries:
        e["dup"] = False
        e["dup_keep"] = False
        e["dup_group_id"] = None

    # Bucket by (amount, merchant); date handled per-pair below.
    buckets = {}
    for e in entries:
        amt = e.get("ocr_amount")
        if amt is None:
            continue
        merch = (e.get("ocr_merchant") or "").strip().lower()
        buckets.setdefault((round(amt, 2), merch), []).append(e)

    gi = 0
    for bucket in buckets.values():
        if len(bucket) < 2:
            continue
        # Partition into date-compatible groups (equal date, or a missing date
        # absorbed into the first dated group it meets).
        used = [False] * len(bucket)
        for i in range(len(bucket)):
            if used[i]:
                continue
            group, used[i] = [bucket[i]], True
            anchor = bucket[i].get("ocr_date")
            for j in range(i + 1, len(bucket)):
                if used[j]:
                    continue
                dj = bucket[j].get("ocr_date")
                if anchor is None or dj is None or anchor == dj:
                    group.append(bucket[j])
                    used[j] = True
                    if anchor is None:
                        anchor = dj  # lock onto the first known date
            if len(group) < 2:
                continue
            gid = f"dg_{gi}"
            gi += 1
            # Keeper / group head: status priority first
            # (matched > unmatched > pending_match), then a present date,
            # then the earliest uploaded_at / id for a stable tiebreak.
            status_rank = {"matched": 0, "unmatched": 1, "pending_match": 2}
            group.sort(key=lambda e: (
                status_rank.get(e.get("match_status"), 3),
                e.get("ocr_date") is None,
                str(e.get("uploaded_at") or ""),
                str(e.get("id") or ""),
            ))
            for k, e in enumerate(group):
                e["dup"] = True
                e["dup_keep"] = (k == 0)
                e["dup_group_id"] = gid


def _handle_ledger_delete(username: str, body: dict):
    """POST /cardconv/ledger/delete — remove entries by id from the ledger.

    Body: {"ids": [...], "also_drive": bool}. When also_drive is true, the
    corresponding Drive originals are moved to the trash (best-effort).
    """
    raw = body.get("ids", [])
    ids = {str(i) for i in (raw if isinstance(raw, list) else [raw]) if i}
    if not ids:
        return ("json", {"error": "no ids"}, 400)
    also_drive = bool(body.get("also_drive"))

    ledger = _load_ledger(username)
    removed_entries = [e for e in ledger["entries"] if e.get("id") in ids]
    ledger["entries"] = [e for e in ledger["entries"] if e.get("id") not in ids]
    _save_ledger(username, ledger)

    trashed = 0
    if also_drive and removed_entries:
        service = _get_drive_service(username)
        if service:
            for e in removed_entries:
                fid = e.get("file_id")
                if not fid:
                    continue
                try:
                    service.files().update(fileId=fid, body={"trashed": True}).execute()
                    trashed += 1
                except Exception:
                    pass  # best-effort; ledger removal already succeeded
    return ("json", {"ok": True, "removed": len(removed_entries), "trashed": trashed})


def _revoke_drive_token(username: str) -> None:
    """Best-effort: ask Google to revoke the stored OAuth token before deletion."""
    token_file = TOKENS_DIR / f"{username}.json"
    if not token_file.exists():
        return
    try:
        import urllib.parse as _up, urllib.request as _ur
        data = json.loads(token_file.read_text())
        tok = data.get("refresh_token") or data.get("token")
        if not tok:
            return
        req = _ur.Request(
            "https://oauth2.googleapis.com/revoke",
            data=_up.urlencode({"token": tok}).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        _ur.urlopen(req, timeout=5)
    except Exception:
        pass


def purge_user_data(username: str) -> None:
    """Delete ALL cardconv data for a user (Drive token + connection, ledger,
    receipts, uploads, settings, push subs). Called when an admin deletes the
    account so nothing — especially the Google Drive token — is left behind."""
    import shutil
    _revoke_drive_token(username)
    for f in [
        TOKENS_DIR / f"{username}.json",
        _drive_meta_file(username),
        _receipts_file(username),
        _review_file(username),
        _ocr_staging_file(username),
        _user_settings_file(username),
        _uploads_index_file(username),
        _push_subs_file(username),
    ]:
        try:
            Path(f).unlink()
        except FileNotFoundError:
            pass
        except Exception:
            pass
    shutil.rmtree(_uploads_dir(username), ignore_errors=True)


def _get_completed_folder_id(service, username: str) -> str:
    """Drive folder ID for Wayfinder/Receipts/Completed/, created on demand."""
    receipts_id = _get_receipts_folder_id(service, username)
    return _get_or_create_folder(service, 'Completed', receipts_id)


def _archive_to_completed(username: str, file_ids: set) -> int:
    """Best-effort move of Drive originals into the Completed folder.

    Returns the count moved. The ledger `completed` flag is the source of truth,
    so any Drive failure is swallowed and reported only via the returned count.
    """
    if not file_ids:
        return 0
    service = _get_drive_service(username)
    if not service:
        return 0
    try:
        completed_id = _get_completed_folder_id(service, username)
        receipts_id = _get_receipts_folder_id(service, username)
    except Exception:
        return 0
    moved = 0
    for fid in file_ids:
        if not fid:
            continue
        try:
            # Drop the source parent; addParents is idempotent.
            cur = service.files().get(fileId=fid, fields='parents').execute()
            parents = set(cur.get('parents', []))
            remove = ",".join(parents & {receipts_id}) or None
            service.files().update(
                fileId=fid, addParents=completed_id,
                removeParents=remove, fields='id,parents'
            ).execute()
            moved += 1
        except Exception:
            pass  # best-effort; ledger flag already reflects completion
    return moved


def _restore_from_completed(username: str, file_ids: set) -> int:
    """Best-effort move of Drive originals back from Completed to Receipts."""
    if not file_ids:
        return 0
    service = _get_drive_service(username)
    if not service:
        return 0
    try:
        completed_id = _get_completed_folder_id(service, username)
        receipts_id = _get_receipts_folder_id(service, username)
    except Exception:
        return 0
    moved = 0
    for fid in file_ids:
        if not fid:
            continue
        try:
            service.files().update(
                fileId=fid, addParents=receipts_id,
                removeParents=completed_id, fields='id,parents'
            ).execute()
            moved += 1
        except Exception:
            pass
    return moved


def _handle_ledger_complete(username: str, body: dict):
    """POST /cardconv/ledger/complete — mark entries complete (or undo).

    Body: {"ids": [...], "undo": bool}. Completing flags entries and moves their
    Drive originals to the Completed folder; the ledger flag is authoritative so
    Drive moves are best-effort. Multiple ledger entries can share one Drive file
    (multi-receipt page) — that file is only moved when ALL its entries agree.
    """
    raw = body.get("ids", [])
    ids = {str(i) for i in (raw if isinstance(raw, list) else [raw]) if i}
    if not ids:
        return ("json", {"error": "no ids"}, 400)
    undo = bool(body.get("undo"))

    ledger = _load_ledger(username)
    now = datetime.now().isoformat()
    touched = []
    for e in ledger["entries"]:
        if e.get("id") in ids:
            e["completed"] = not undo
            e["completed_at"] = None if undo else now
            touched.append(e)

    # A Drive file's correct location is derived purely from its siblings: it
    # belongs in Completed iff EVERY entry sharing that file is completed,
    # otherwise in Receipts. Computing this per affected file (rather than per
    # touched entry) keeps a multi-receipt page consistent — partially-completed
    # pages stay in Receipts, and the archived_drive flag is synced across all
    # siblings so it never goes stale on an un-touched sibling.
    by_file = {}
    for e in ledger["entries"]:
        fid = e.get("file_id")
        if fid:
            by_file.setdefault(fid, []).append(e)
    affected = {e.get("file_id") for e in touched if e.get("file_id")}
    to_archive, to_restore = set(), set()
    for fid in affected:
        sibs = by_file.get(fid, [])
        if sibs and all(s.get("completed") for s in sibs):
            to_archive.add(fid)
        else:
            to_restore.add(fid)

    moved = 0
    if to_archive:
        moved += _archive_to_completed(username, to_archive)
    if to_restore:
        moved += _restore_from_completed(username, to_restore)
    # Sync archived_drive across every entry of each affected file.
    for e in ledger["entries"]:
        fid = e.get("file_id")
        if fid in to_archive:
            e["archived_drive"] = True
        elif fid in to_restore:
            e["archived_drive"] = False
    _save_ledger(username, ledger)
    # `attempted` = Drive moves we tried; the UI warns when moved < attempted
    # (e.g. Drive offline) while the ledger flag — the source of truth — is set.
    return ("json", {"ok": True, "count": len(touched),
                     "moved": moved, "attempted": len(to_archive) + len(to_restore)})


def _parse_filter_params(query: dict) -> dict:
    """Extract the shared Ledger filter params from a query dict.

    Used by the JSON API, PDF export and xlsx export so all interpret the
    status/date/card-brand/usage/completed filters identically.
    """
    def _q(key, default):
        return (query.get(key, [default]) or [default])[0]
    return {
        "status":     _q("status", "all"),
        "dfrom":      _q("from", ""),
        "dto":        _q("to", ""),
        "card_brand": _q("card_brand", "all"),
        "usage":      _q("usage", "all"),
        "completed":  _q("completed", "hide"),
    }


def _handle_ledger_api(username: str, query: dict):
    """GET /cardconv/ledger/api — filtered JSON data."""
    ledger  = _load_ledger(username)
    entries = ledger["entries"]
    f = _parse_filter_params(query)
    try:
        page = max(1, int((query.get("page", ["1"]) or ["1"])[0]))
    except ValueError:
        page = 1
    try:
        limit = max(1, int((query.get("limit", ["50"]) or ["50"])[0]))
    except ValueError:
        limit = 50

    filtered = _apply_ledger_filters(entries, f["status"], f["dfrom"], f["dto"],
                                     f["card_brand"], f["usage"], f["completed"])
    _mark_duplicates(filtered)

    stats   = _ledger_stats(filtered)
    total_f = len(filtered)
    pages   = max(1, (total_f + limit - 1) // limit)
    start   = (page - 1) * limit
    # Distinct usage tags across the whole ledger (for the filter dropdown), and
    # a completed count so the UI can surface how many are archived.
    usages = sorted({(e.get("usage") or "Regular") for e in entries})
    completed_n = sum(1 for e in entries if e.get("completed"))
    return ("json", {
        "total":       stats["total"],
        "matched":     stats["matched"],
        "unmatched":   stats["unmatched"],
        "pending_match": stats["pending_match"],
        "completed":   completed_n,
        "usages":      usages,
        "page":        page,
        "pages":       pages,
        "last_synced": ledger.get("last_batch_at"),
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
                # Matched ⇒ AMEX transaction; fill brand only when unknown.
                if not e.get("card_brand"):
                    e["card_brand"] = "amex"
            _save_ledger(username, ledger)
            return ("json", {"ok": True})
    return ("json", {"error": "not found"}, 404)


def _handle_rematch(username: str, entry_id: str):
    """POST /cardconv/ledger/<id>/rematch — re-try CSV matching for a pending/unmatched entry."""
    ledger = _load_ledger(username)
    entries = ledger["entries"]
    entry = next((e for e in entries if e.get("id") == entry_id), None)
    if not entry:
        return ("json", {"error": "not found"}, 404)

    rdate = entry.get("ocr_date")
    if rdate == "YYYY-MM-DD":
        rdate = None
    # Handwritten amount takes priority over printed as the final match target.
    hw = entry.get("ocr_handwritten_amount")
    pr = entry.get("ocr_printed_amount") or entry.get("ocr_amount")
    raw_amount = hw if hw is not None else pr
    if raw_amount is None:
        return ("json", {"error": "no OCR amount to match against"}, 400)
    try:
        ramount = round(float(raw_amount), 2)
    except (ValueError, TypeError):
        return ("json", {"error": "invalid amount"}, 400)

    uploads = _load_uploads(username)
    uploads_dir_path = _uploads_dir(username)
    target_names = set(_get_card_member_names(username))
    matched_tx = None

    for upload in uploads:
        csv_path = uploads_dir_path / upload.get("stored_name", "")
        if not csv_path.exists():
            continue
        try:
            csv_bytes = csv_path.read_bytes()
            reader = csv.DictReader(
                io.TextIOWrapper(io.BytesIO(csv_bytes), encoding='utf-8-sig', newline=''))
            rows = [r for r in reader
                    if r.get("Card Member Name", "").strip().upper() in target_names]
        except Exception:
            continue

        for row in rows:
            try:
                amount = round(float(row.get("Amount", 0)), 2)
            except ValueError:
                continue
            if abs(amount - ramount) > 0.01:
                continue

            inv_dt = _parse_date(row.get("Date", ""))
            inv_date_str = inv_dt.strftime("%Y-%m-%d") if inv_dt else None

            if rdate is None or inv_date_str is None:
                date_match = True
            elif rdate == inv_date_str:
                date_match = True
            else:
                try:
                    from datetime import timedelta as _td
                    rd  = date.fromisoformat(rdate)
                    id_ = date.fromisoformat(inv_date_str)
                    date_match = abs((rd - id_).days) <= 1
                except Exception:
                    date_match = False

            if date_match:
                merchant = row.get("Merchant Name", "").strip()
                dba      = row.get("Merchant Doing Business As", "").strip()
                matched_tx = {
                    "date":   inv_date_str,
                    "amount": amount,
                    "vendor": dba if (dba and dba != merchant) else merchant,
                }
                break
        if matched_tx:
            break

    now_iso = datetime.now().isoformat()
    if matched_tx:
        entry["matched"]             = True
        entry["match_status"]        = "matched"
        entry["matched_at"]          = now_iso
        entry["matched_transaction"] = matched_tx
        if entry.get("ocr_date") in (None, "", "unknown") and matched_tx.get("date"):
            entry["ocr_date_original"] = entry.get("ocr_date")
            entry["ocr_date"]          = matched_tx["date"]
    else:
        entry["match_status"] = "unmatched"
        entry["matched"]      = False

    _save_ledger(username, ledger)
    return ("json", {"ok": True, "matched": bool(matched_tx), "entry": entry})


def _handle_reocr(username: str, entry_id: str):
    """POST /cardconv/ledger/<id>/reocr — re-run OCR for all entries sharing the same file_id."""
    service = _get_drive_service(username)
    if not service:
        return ("json", {"error": "Drive not connected"}, 401)
    ledger = _load_ledger(username)
    entries = ledger["entries"]

    # Find the target entry to get its file_id
    target = next((e for e in entries if e.get("id") == entry_id), None)
    if not target:
        return ("json", {"error": "not found"}, 404)
    file_id = target.get("file_id")
    if not file_id:
        return ("json", {"error": "no file_id on entry"}, 400)

    try:
        meta    = service.files().get(fileId=file_id, fields="mimeType,name,webViewLink").execute()
        mime    = meta.get("mimeType", "image/jpeg")
        content = service.files().get_media(fileId=file_id).execute()
    except Exception as e:
        return ("json", {"error": f"Drive fetch failed: {e}"}, 500)

    ocr_list = _ocr_receipt_auto(content, mime) or [{}]

    # Preserve non-OCR fields from the existing sibling entries (matched at same sub_index)
    siblings = {e.get("sub_index", 0): e for e in entries if e.get("file_id") == file_id}

    # Remove all existing entries for this file_id
    entries[:] = [e for e in entries if e.get("file_id") != file_id]

    url     = meta.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view"
    now_iso = datetime.now().isoformat()
    updated = []
    for sub_index, ocr in enumerate(ocr_list):
        fields  = _ocr_entry_fields(ocr)
        sibling = siblings.get(sub_index, {})
        entry   = {
            "id":           _sub_entry_id(file_id, sub_index),
            "file_id":      file_id,
            "sub_index":    sub_index,
            "filename":     sibling.get("filename") or meta.get("name", ""),
            "drive_url":    url,
            "mime_type":    mime,
            "match_status": sibling.get("match_status", "pending_match"),
            "matched":      sibling.get("matched", False),
            "multi_ocr":    True,
            "uploaded_at":  sibling.get("uploaded_at", now_iso),
            "synced_at":    now_iso,
            "reocr_at":     now_iso,
        }
        if sibling.get("matched_at"):
            entry["matched_at"] = sibling["matched_at"]
        if sibling.get("matched_transaction"):
            entry["matched_transaction"] = sibling["matched_transaction"]
        entry.update(fields)
        entries.append(entry)
        updated.append(entry)

    _save_ledger(username, ledger)
    return ("json", {"ok": True, "updated": updated})


def _handle_image_proxy(username: str, file_id: str, bbox: list = None):
    """GET /cardconv/receipts/image/<file_id>[?bbox=ymin,xmin,ymax,xmax] — Drive proxy with optional crop.
    Always auto-rotates via EXIF so receipts display upright.
    """
    service = _get_drive_service(username)
    if not service:
        return ("html", "<p>Drive not connected</p>", 401)
    try:
        from PIL import Image as _Img, ImageOps as _IOP
        content = service.files().get_media(fileId=file_id).execute()
        img = _Img.open(io.BytesIO(content))
        img = _IOP.exif_transpose(img)   # auto-rotate
        img = img.convert("RGB")

        if bbox and len(bbox) == 4:
            w, h = img.size
            ymin, xmin, ymax, xmax = [max(0, min(1000, v)) for v in bbox]
            left   = int(xmin / 1000 * w)
            upper  = int(ymin / 1000 * h)
            right  = int(xmax / 1000 * w)
            lower  = int(ymax / 1000 * h)
            pad = max(6, min(w, h) // 40)
            left, upper = max(0, left - pad), max(0, upper - pad)
            right, lower = min(w, right + pad), min(h, lower + pad)
            img = img.crop((left, upper, right, lower))

        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=88, optimize=True)
        return ("binary", buf.getvalue(), "image/jpeg", None)
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

    Returns (jpeg_bytes, (w, h)) or None on failure. Auto-rotates via EXIF,
    caps width at max_w px, and re-encodes as JPEG to keep the PDF small.
    """
    from PIL import Image, ImageOps
    try:
        img = Image.open(io.BytesIO(raw))
        img = ImageOps.exif_transpose(img)   # honour EXIF orientation tag
        img = img.convert("RGB")             # flatten alpha/CMYK/palette for JPEG
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
    """GET /cardconv/ledger/download.pdf — landscape A4, 5 cols × 2 rows = 10 per page.
    Images only (no text), EXIF auto-rotated, maximally sized with minimal gaps.
    Multi-receipt source images span extra columns.
    """
    from fpdf import FPDF

    f = _parse_filter_params(query)
    status, dfrom, dto = f["status"], f["dfrom"], f["dto"]
    entries = _apply_ledger_filters(_ledger_entries(username), status, dfrom, dto,
                                    f["card_brand"], f["usage"], f["completed"])
    stats   = _ledger_stats(entries)
    service = _get_drive_service(username)

    pdf = FPDF(orientation="L", unit="mm", format="A4")
    pdf.set_auto_page_break(auto=False)
    MRG  = 5          # tight margins to maximise image area
    GAP  = 1.0        # gap between cells
    PAD  = 0.5        # inner padding within each cell
    pdf.set_margins(MRG, MRG, MRG)

    FONT, unicode_ok = "Helvetica", False
    for fam, reg, bold in _PDF_FONT_CANDIDATES:
        if os.path.exists(reg) and os.path.exists(bold):
            pdf.add_font(fam, "", reg)
            pdf.add_font(fam, "B", bold)
            FONT, unicode_ok = fam, True
            break

    def S(t):
        t = "" if t is None else str(t)
        return t if unicode_ok else t.encode("latin-1", "replace").decode("latin-1")

    # ── Group entries by file_id ──
    seen: dict  = {}
    groups: list = []
    for e in entries:
        fid = e.get("file_id") or ""
        if fid and fid in seen:
            groups[seen[fid]][1].append(e)
        else:
            seen[fid] = len(groups)
            groups.append((fid, [e]))

    # ── Grid: 5 cols × 2 rows, images only ──
    N_COLS = 5
    N_ROWS = 2
    HDR_H  = 9.0      # one-line header (first page only)
    PAGE_W = 297 - 2 * MRG   # 287mm
    PAGE_H = 210 - 2 * MRG   # 200mm
    CELL_W = (PAGE_W - GAP * (N_COLS - 1)) / N_COLS    # ≈56.6mm
    ROW_H  = (PAGE_H - HDR_H - GAP * (N_ROWS - 1)) / N_ROWS  # ≈94mm (first page)
    ROW_H_CONT = (PAGE_H - GAP * (N_ROWS - 1)) / N_ROWS      # ≈99.5mm (no header)

    def cell_inner_w(span: int) -> float:
        return CELL_W * span + GAP * (span - 1)

    def _best_orientation(jpeg: bytes, dim: tuple, cell_w: float, cell_h: float):
        """Return (jpeg, dim) rotated 90° if that gives significantly better cell coverage."""
        from PIL import Image as _PILImg
        def coverage(iw, ih, cw, ch):
            dw = cw
            dh = dw * ih / iw
            if dh > ch:
                dh, dw = ch, ch * iw / ih
            return dw * dh
        normal  = coverage(dim[0], dim[1], cell_w, cell_h)
        rotated = coverage(dim[1], dim[0], cell_w, cell_h)
        if rotated > normal * 1.15:          # rotate if ≥15% better fill
            img = _PILImg.open(io.BytesIO(jpeg)).rotate(90, expand=True)
            buf = io.BytesIO()
            img.save(buf, format="JPEG", quality=82, optimize=True)
            return buf.getvalue(), img.size
        return jpeg, dim

    # ── Pre-fetch + compress images ──
    img_cache: dict = {}
    for fid, elist in groups:
        if not fid:
            img_cache[fid] = None
            continue
        span   = min(len(elist), N_COLS)
        cw     = cell_inner_w(span) - 2 * PAD
        ch     = ROW_H_CONT - 2 * PAD
        max_px = max(500, int(cell_inner_w(span) * 5))
        raw    = _fetch_drive_image(service, fid) or b""
        comp   = _compress_receipt_image(raw, max_w=max_px, quality=82)
        if comp:
            jpeg, dim = comp
            jpeg, dim = _best_orientation(jpeg, dim, cw, ch)
            img_cache[fid] = (jpeg, dim)
        else:
            img_cache[fid] = None

    # ── Pack groups into grid rows ──
    grid_rows: list = []
    cur_row:   list = []
    col = 0
    for fid, elist in groups:
        span = min(len(elist), N_COLS)
        if col + span > N_COLS:
            grid_rows.append(cur_row)
            cur_row, col = [], 0
        cur_row.append((fid, elist, span))
        col += span
    if cur_row:
        grid_rows.append(cur_row)

    if not grid_rows:
        pdf.add_page()
        pdf.set_font(FONT, "", 10)
        pdf.set_xy(MRG, MRG)
        pdf.cell(0, 10, S("No receipts for the selected filter."))
        out = pdf.output()
        return ("binary", bytes(out), "application/pdf",
                f"receipts_{username}_{date.today().isoformat()}.pdf")

    # ── Draw ──
    def draw_header(first: bool):
        if not first:
            return
        pdf.set_font(FONT, "", 7)
        pdf.set_text_color(130, 130, 130)
        pdf.set_xy(MRG, MRG)
        flabel = {"all": "All"}.get(status) or _PDF_STATUS_LABEL.get(status, status)
        rng = f"{dfrom or '…'} ~ {dto or '…'}"
        pdf.cell(0, HDR_H - 1, S(
            f"Receipt Ledger  ·  {username}  ·  {flabel}  ·  {rng}  ·  "
            f"Total {stats['total']}  Matched {stats['matched']}  "
            f"Unmatched {stats['unmatched']}  Pending {stats['pending_match']}"
        ))
        pdf.set_text_color(0, 0, 0)

    first_page  = True
    row_in_page = 0   # which row on the current page (0 or 1)
    y           = 0.0
    n_rows      = len(grid_rows)

    for row_idx, row in enumerate(grid_rows):
        # Start a new page when both rows are filled
        if row_in_page == 0:
            pdf.add_page()
            draw_header(first_page)
            y = MRG + (HDR_H if first_page else 0)
            first_page = False

        # Determine row height: if this is the only row on this page (last item or
        # next item would start a new page), expand to full usable height.
        is_only_row_on_page = (row_in_page == 0 and (row_idx == n_rows - 1))
        if is_only_row_on_page:
            cur_row_h = PAGE_H - (HDR_H if pdf.page == 1 else 0) - 2 * MRG
        elif row_in_page == 0 and pdf.page == 1:
            cur_row_h = ROW_H
        else:
            cur_row_h = ROW_H_CONT

        x = MRG
        for fid, elist, span in row:
            iw = cell_inner_w(span)

            # Thin border
            pdf.set_draw_color(200, 200, 200)
            pdf.set_line_width(0.15)
            pdf.rect(x, y, iw, cur_row_h)

            # Image — fill the cell as fully as possible
            comp = img_cache.get(fid)
            if comp:
                jpeg, dim = comp
                avail_w = iw - 2 * PAD
                avail_h = cur_row_h - 2 * PAD
                dw = avail_w
                dh = dw * dim[1] / dim[0]
                if dh > avail_h:
                    dh, dw = avail_h, avail_h * dim[0] / dim[1]
                try:
                    pdf.image(io.BytesIO(jpeg),
                              x=x + (iw - dw) / 2,
                              y=y + (cur_row_h - dh) / 2,
                              w=dw, h=dh)
                except Exception:
                    pass
            else:
                pdf.set_xy(x, y)
                pdf.set_font(FONT, "", 6)
                pdf.set_text_color(180, 180, 180)
                pdf.cell(iw, cur_row_h, S("no image"), align="C")
                pdf.set_text_color(0, 0, 0)

            x += iw + GAP

        y += cur_row_h + GAP
        row_in_page = (row_in_page + 1) % N_ROWS

    out  = pdf.output()
    fname = f"receipts_{username}_{date.today().isoformat()}.pdf"
    _add_hist({
        "type":     "pdf_download",
        "date":     datetime.now().strftime("%Y-%m-%d %H:%M"),
        "filename": fname,
        "filter":   flabel if 'flabel' in dir() else status,
        "count":    stats.get("total", 0),
        "user":     username,
    })
    return ("binary", bytes(out), "application/pdf", fname)


# ── HTTP handler ──────────────────────────────────────────────────────────────

def _get_client_info():
    import json as _json
    data = _json.loads(CREDS_FILE.read_text())
    return data.get("installed", data.get("web", {}))


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
    # Eagerly create Wayfinder/Receipts so the user has a place to drop files,
    # and land them on a CTA page instead of straight back to the ledger.
    folder_url = ""
    try:
        service = _get_drive_service(username)
        if service:
            rid = _get_receipts_folder_id(service, username)
            folder_url = f"https://drive.google.com/drive/folders/{rid}"
    except Exception:
        pass
    from services._cardconv_render import _render_drive_connected
    return ("html", _render_drive_connected(folder_url))


import threading as _threading, uuid as _uuid

_sync_jobs: dict = {}   # job_id → {"status": "running"|"done"|"error", "staged": int, "error": str}

def _do_drive_sync_work(username: str, job_id: str):
    """Background worker: scans Drive, OCRs new files, stages for review."""
    try:
        service = _get_drive_service(username)
        if not service:
            _sync_jobs[job_id] = {"status": "error", "staged": 0, "error": "Drive not connected"}
            return

        receipts_id = _get_receipts_folder_id(service, username)
        results = service.files().list(
            q=(f"'{receipts_id}' in parents "
               f"and trashed=false and mimeType!='application/vnd.google-apps.folder'"),
            fields="files(id,name,mimeType,webViewLink)"
        ).execute()
        drive_files = results.get('files', [])

        existing = _load_receipts(username)
        done_fids = {r.get('file_id') for r in existing
                     if (r.get('multi_ocr') and r.get('ocr_amount') is not None)
                     or r.get('matched')}
        # Skip files already in the staging queue.
        staging = _load_ocr_staging(username)
        staged_fids = {e.get("file_id") for e in staging.get("entries", [])}
        skip_fids = done_fids | staged_fids
        supported = {'image/jpeg', 'image/png', 'application/pdf', 'image/gif', 'image/webp'}

        new_staged = []
        now_disp = datetime.now().strftime("%Y-%m-%d %H:%M")
        now_iso  = datetime.now().isoformat()

        for f in drive_files:
            fid = f.get('id')
            mime = f.get('mimeType', '')
            if mime not in supported:
                continue
            if fid in skip_fids:
                continue
            content  = service.files().get_media(fileId=fid).execute()
            ocr_list = _ocr_receipt_auto(content, mime) or [{}]
            url      = f.get('webViewLink') or f'https://drive.google.com/file/d/{fid}/view'
            for sub_index, ocr in enumerate(ocr_list):
                entry = {
                    "id":           _sub_entry_id(fid, sub_index),
                    "file_id":      fid,
                    "sub_index":    sub_index,
                    "filename":     f.get('name', ''),
                    "drive_url":    url,
                    "mime_type":    mime,
                    "match_status": "pending_match",
                    "multi_ocr":    True,
                    "uploaded_at":  now_disp,
                    "synced_at":    now_iso,
                }
                entry.update(_ocr_entry_fields(ocr))
                new_staged.append(entry)

        # Accumulate — append to existing staging queue, never replace.
        if new_staged:
            staging.setdefault("entries", []).extend(new_staged)
            staging["staged_at"] = now_iso
            _save_ocr_staging(username, staging)

        ledger = _load_ledger(username)
        ledger["last_batch_at"] = now_iso
        _save_ledger(username, ledger)

        _sync_jobs[job_id] = {"status": "done", "staged": len(new_staged)}

    except Exception as e:
        _sync_jobs[job_id] = {"status": "error", "staged": 0, "error": str(e)}


def _handle_drive_sync(username: str):
    """POST /cardconv/drive/sync — start background sync, return job_id immediately."""
    if not _get_drive_service(username):
        return ("json", {"error": "Drive not connected"}, 400)
    job_id = _uuid.uuid4().hex
    _sync_jobs[job_id] = {"status": "running", "staged": 0}
    t = _threading.Thread(target=_do_drive_sync_work, args=(username, job_id), daemon=True)
    t.start()
    return ("json", {"job_id": job_id})


def _handle_drive_sync_status(username: str, query: dict):
    """GET /cardconv/drive/sync/status?job=<id> — poll sync progress."""
    job_id = (query.get("job", [""])[0]).strip()
    job = _sync_jobs.get(job_id)
    if not job:
        return ("json", {"status": "not_found"})
    return ("json", job)


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

    staged_entries = []
    now_disp = datetime.now().strftime("%Y-%m-%d %H:%M")
    now_iso  = datetime.now().isoformat()

    for filename, content, mime_type in files:
        if mime_type not in supported:
            continue
        file_id, drive_url = _upload_file_to_drive(username, content, filename, mime_type)
        ocr_list = _ocr_receipt_auto(content, mime_type) or [{}]
        for sub_index, ocr in enumerate(ocr_list):
            entry = {
                "id":           _sub_entry_id(file_id, sub_index),
                "file_id":      file_id,
                "sub_index":    sub_index,
                "filename":     filename,
                "drive_url":    drive_url,
                "mime_type":    mime_type,
                "uploaded_at":  now_disp,
                "synced_at":    now_iso,
                "match_status": "pending_match",
                "multi_ocr":    True,
            }
            entry.update(_ocr_entry_fields(ocr))
            staged_entries.append(entry)

    # Stage for visual review; only confirmed entries go to the ledger.
    existing = _load_ocr_staging(username)
    existing.setdefault("entries", []).extend(staged_entries)
    existing["staged_at"] = now_iso
    _save_ocr_staging(username, existing)
    return ("redirect", "/cardconv/receipts/review")


def _handle_manual_receipt_add(username: str, body: dict):
    """Add a manually-entered receipt sub-entry to an existing Drive image in the ledger."""
    file_id   = (body.get("file_id") or "").strip()
    filename  = (body.get("filename") or "").strip()
    drive_url = (body.get("drive_url") or "").strip()
    mime_type = (body.get("mime_type") or "image/jpeg").strip()

    def _num(v):
        try: return float(v) if v not in (None, "") else None
        except: return None

    ocr_date   = (body.get("ocr_date") or "").strip() or None
    merchant   = (body.get("ocr_merchant") or "").strip() or None
    printed    = _num(body.get("ocr_printed_amount"))
    handw      = _num(body.get("ocr_handwritten_amount"))
    final_amt  = handw if handw is not None else printed

    if not file_id:
        return ("json", {"error": "file_id required"}, 400)

    entries = _load_receipts(username)
    # Assign the next sub_index for this file_id.
    existing_subs = [e.get("sub_index", 0) for e in entries if e.get("file_id") == file_id]
    sub_index = (max(existing_subs) + 1) if existing_subs else 0

    now_disp = datetime.now().strftime("%Y-%m-%d %H:%M")
    now_iso  = datetime.now().isoformat()
    entry = {
        "id":                    _sub_entry_id(file_id, sub_index),
        "file_id":               file_id,
        "sub_index":             sub_index,
        "filename":              filename,
        "drive_url":             drive_url,
        "mime_type":             mime_type,
        "uploaded_at":           now_disp,
        "synced_at":             now_iso,
        "match_status":          "pending_match",
        "multi_ocr":             True,
        "ocr_status":            "manual",
        "ocr_model":             "Manual",
        "ocr_date":              ocr_date,
        "ocr_merchant":          merchant,
        "ocr_printed_amount":    printed,
        "ocr_handwritten_amount": handw,
        "ocr_amount":            final_amt,
        "ocr_bbox":              None,
    }
    entries.append(entry)
    _save_receipts(username, entries)
    return ("json", {"ok": True, "id": entry["id"]})


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
            "type":      "conversion",
            "filename":  out_fn,
            "source":    csv_name,
            "rows":      total,
            "unmatched": unmatched,
            "date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
            "user":      user or "",
        })
        if user:
            _save_uploaded_csv(user, csv_bytes, csv_name, total, out_fn)
        # Conversion result is staged in review_{user}.json; review before download.
        return ("redirect", "/cardconv/review")
    except Exception as e:
        return ("html", f"<p style='color:red;padding:20px'>Error: {e}</p>")


def _handle_upload_rerun(username: str, uid: str):
    """Re-run conversion (re-match receipts) from a previously uploaded CSV."""
    items = _load_uploads(username)
    entry = next((i for i in items if i.get("id") == uid), None)
    if not entry:
        return ("redirect", "/cardconv/convert")
    stored = _uploads_dir(username) / entry.get("stored_name", "")
    if not stored.exists():
        return ("redirect", "/cardconv/convert")
    try:
        csv_bytes = stored.read_bytes()
        fn = entry.get("filename", "upload.csv")
        xlsx_bytes, out_fn, total, unmatched = convert(csv_bytes, fn, username=username)
        _add_hist({
            "filename":  out_fn,
            "source":    fn,
            "rows":      total,
            "unmatched": unmatched,
            "date":      datetime.now().strftime("%Y-%m-%d %H:%M"),
        })
        entry["rows"] = total
        entry["out_filename"] = out_fn
        _save_uploads(username, items)
        return ("redirect", "/cardconv/review")
    except Exception as e:
        return ("html", f"<p style='color:red;padding:20px'>Error: {e}</p>")


def _handle_upload_delete(username: str, uid: str):
    """Delete a stored CSV and its index entry."""
    items = _load_uploads(username)
    entry = next((i for i in items if i.get("id") == uid), None)
    if entry:
        stored = _uploads_dir(username) / entry.get("stored_name", "")
        try:
            if stored.exists():
                stored.unlink()
        except Exception:
            pass
        _save_uploads(username, [i for i in items if i.get("id") != uid])
    return ("redirect", "/cardconv/convert")


# ── Render helpers ─────────────────────────────────────────────────────────────

def _handle_ledger_update(username: str, entry_id: str, body: dict):
    """POST /cardconv/ledger/<id>/update — manually edit OCR fields of an entry."""
    ledger = _load_ledger(username)
    updated = False
    for e in ledger["entries"]:
        if e.get("id") != entry_id:
            continue
        for field in ("ocr_date", "ocr_merchant"):
            raw = body.get(field)
            if raw is not None:
                val = (raw[0] if isinstance(raw, list) else str(raw)).strip()
                e[field] = val or None
        # Card brand: normalize to amex/visa/other, or clear when blank.
        raw = body.get("card_brand")
        if raw is not None:
            val = (raw[0] if isinstance(raw, list) else str(raw)).strip().lower()
            e["card_brand"] = val if val in ("amex", "visa", "other") else None
        # Usage: free-text tag, defaults back to "Regular" when cleared.
        raw = body.get("usage")
        if raw is not None:
            val = (raw[0] if isinstance(raw, list) else str(raw)).strip()
            e["usage"] = val or "Regular"
        for field in ("ocr_printed_amount", "ocr_handwritten_amount"):
            raw = body.get(field)
            if raw is not None:
                val = (raw[0] if isinstance(raw, list) else str(raw)).strip()
                try:
                    e[field] = float(val) if val else None
                except ValueError:
                    pass
        # ocr_amount always reflects handwritten-priority final amount.
        hw = e.get("ocr_handwritten_amount")
        pr = e.get("ocr_printed_amount")
        e["ocr_amount"] = hw if hw is not None else pr
        updated = True
        break
    if not updated:
        return ("json", {"error": "not found"}, 404)
    _save_ledger(username, ledger)
    return ("json", {"ok": True})


def _handle_review_manual_match(username: str, body: dict):
    """POST /cardconv/review/match — manually link an unmatched review row to a receipt."""
    def val(k):
        v = body.get(k, "")
        return (v[0] if isinstance(v, list) else str(v)).strip()
    row_id   = val("row_id")
    rcpt_id  = val("receipt_id")
    if not row_id or not rcpt_id:
        return ("json", {"error": "missing params"}, 400)

    # Find the receipt in the ledger
    receipts = _load_receipts(username)
    receipt  = next((r for r in receipts if r.get("id") == rcpt_id), None)
    if not receipt:
        return ("json", {"error": "receipt not found"}, 404)

    # Update review row
    review = _load_review(username)
    matched_row = None
    for r in review.get("rows", []):
        if r.get("id") == row_id:
            r["matched"] = True
            r["receipt"] = {
                "id":           receipt.get("id"),
                "file_id":      receipt.get("file_id"),
                "drive_url":    receipt.get("drive_url"),
                "ocr_date":     receipt.get("ocr_date"),
                "ocr_merchant": receipt.get("ocr_merchant"),
                "ocr_amount":   receipt.get("ocr_amount"),
                "filename":     receipt.get("filename"),
            }
            matched_row = r
            break
    if not matched_row:
        return ("json", {"error": "row not found"}, 404)

    # Mark receipt as matched in ledger
    receipt["matched"] = True
    receipt["match_status"] = "matched"
    receipt["matched_at"] = datetime.now().isoformat()
    receipt["matched_transaction"] = {
        "date":   matched_row.get("date"),
        "amount": matched_row.get("amount"),
        "vendor": matched_row.get("merchant"),
    }
    # Matched ⇒ AMEX transaction; fill brand only when unknown.
    if not receipt.get("card_brand"):
        receipt["card_brand"] = "amex"
    _save_receipts(username, receipts)
    _save_review(username, review)
    return ("json", {"ok": True, "receipt": matched_row["receipt"]})


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


def _handle_review_download(username: str, query: dict):
    """GET /cardconv/review/download — staged xlsx filtered to a date range.

    from/to are 'YYYY-MM-DD' query params. Rows are filtered by their invoice
    date (column 5). Rows without an invoice date are always kept, matching the
    Ledger/Review filter convention. No range → full file.
    """
    review = _load_review(username)
    out_fn = review.get("out_filename") or ""
    src    = OUT_DIR / out_fn
    if not out_fn or not src.exists():
        return ("html", "<h2 style='padding:40px'>No staged conversion to download.</h2>", 404)

    dfrom = (query.get("from", [""]) or [""])[0]
    dto   = (query.get("to", [""]) or [""])[0]
    if not dfrom and not dto:
        # Unfiltered — serve the original file untouched.
        return ("file", str(src),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", out_fn)

    wb = openpyxl.load_workbook(src)
    ws = wb["sheetMst"]

    def _row_date_str(v):
        if isinstance(v, datetime):
            return v.strftime("%Y-%m-%d")
        if isinstance(v, date):
            return v.strftime("%Y-%m-%d")
        return str(v)[:10] if v else ""

    drop = []
    r = 2
    while ws.cell(r, 1).value is not None:
        d = _row_date_str(ws.cell(r, 5).value)
        keep = (not d) or ((not dfrom or d >= dfrom) and (not dto or d <= dto))
        if not keep:
            drop.append(r)
        r += 1
    for idx in reversed(drop):
        ws.delete_rows(idx, 1)

    buf = io.BytesIO()
    wb.save(buf)
    return ("file_inline", buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", out_fn)


_CARD_BRAND_LABEL = {"amex": "AMEX", "visa": "Visa", "other": "Other"}


def _handle_ledger_xlsx(username: str, query: dict):
    """GET /cardconv/ledger/download.xlsx — filtered ledger rows as a settlement xlsx.

    Maps the currently-filtered Ledger entries onto the same template `convert`
    uses, sourcing date/vendor/amount from each receipt (matched-transaction
    values preferred when present). Card Type and Usage are appended as columns
    28/29 for visibility. Honors all Ledger filters via the shared parser.
    """
    f = _parse_filter_params(query)
    entries = _apply_ledger_filters(_ledger_entries(username),
                                    f["status"], f["dfrom"], f["dto"],
                                    f["card_brand"], f["usage"], f["completed"])
    if TEMPLATE.exists():
        template_path = TEMPLATE
    elif TEMPLATE_FALLBACK.exists():
        template_path = TEMPLATE_FALLBACK
    else:
        return ("html", "<h2 style='padding:40px'>Template file not found.</h2>", 404)

    rules = _load_kw()
    today = date.today()
    posting_dt = datetime(today.year, today.month, today.day)
    wb = openpyxl.load_workbook(template_path)
    ws = wb["sheetMst"]
    # Extra columns for receipt-centric metadata.
    ws.cell(1, 28).value = "Card Type"
    ws.cell(1, 29).value = "Usage"

    start = 2
    while ws.cell(start, 1).value is not None:
        start += 1

    for e in entries:
        mt       = e.get("matched_transaction") or {}
        vendor   = mt.get("vendor") or e.get("ocr_merchant") or ""
        amount   = mt.get("amount")
        if amount is None:
            amount = e.get("ocr_amount") or 0.0
        try:
            amount = float(amount)
        except (ValueError, TypeError):
            amount = 0.0
        date_str = mt.get("date") or e.get("ocr_date")
        inv_dt   = _parse_date(date_str) if date_str else None

        gl, ser, purpose = _classify(vendor, rules)
        if gl is None:
            gl, ser, purpose = 53410177, "160", "Coffee, Snack and meal"

        ws.cell(start,  1).value = FIXED["receipt_type"]
        ws.cell(start,  2).value = FIXED["employee_id"]
        ws.cell(start,  3).value = FIXED["payee"]
        ws.cell(start,  5).value = inv_dt
        ws.cell(start,  6).value = FIXED["domestic"]
        ws.cell(start,  7).value = vendor
        ws.cell(start,  8).value = posting_dt
        ws.cell(start,  9).value = gl
        ws.cell(start, 10).value = ser
        ws.cell(start, 11).value = FIXED["currency"]
        ws.cell(start, 12).value = FIXED["tax_code"]
        ws.cell(start, 14).value = amount
        ws.cell(start, 15).value = FIXED["cost_center"]
        ws.cell(start, 18).value = purpose
        ws.cell(start, 26).value = amount
        ws.cell(start, 28).value = _CARD_BRAND_LABEL.get(e.get("card_brand"), "")
        ws.cell(start, 29).value = e.get("usage") or "Regular"
        start += 1

    buf = io.BytesIO()
    wb.save(buf)
    out_fn = f"ledger_export_{today.strftime('%Y-%m-%d')}.xlsx"
    return ("file_inline", buf.getvalue(),
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", out_fn)


def _esc(s) -> str:
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;")) if s is not None else ""




# Auto re-export every module-level name (incl _underscore) for `import *`.
__all__ = [k for k in list(globals()) if not k.startswith('__')]
