# Card Converter service entry point.
# Logic lives in _cardconv_core, presentation in _cardconv_render; this file keeps
# the public surface (META, ADMIN, handle) and the router that wires both layers.
from services._cardconv_core import *  # noqa: F401,F403
from services._cardconv_render import *  # noqa: F401,F403

def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user")
    # Service-level access is already enforced by server.py (has_service_access);
    # the batch endpoint injects user=ADMIN. Each user works on their own per-user
    # ledger/Drive (receipts_<user>.json), so cardconv is multi-tenant by data_key.
    if not user:
        return ("html", "<h2 style='padding:40px;color:#f87171'>Access denied</h2>")

    # Tab pages: Ledger (main) | Convert | Review | Keywords
    if method == "GET" and path == "/cardconv":
        return ("redirect", "/cardconv/ledger")
    if method == "GET" and path == "/cardconv/convert":
        return ("html", _render_convert(user))
    if method == "GET" and path == "/cardconv/review":
        return ("html", _render_review(user))
    if method == "GET" and path == "/cardconv/history":
        return ("html", _render_history(user))
    if method == "POST" and path == "/cardconv/history/delete":
        ids = body.get("ids", [])
        if isinstance(ids, str): ids = [ids]
        hist = [h for h in _load_hist() if h.get("id") not in ids]
        _save_hist(hist)
        return ("json", {"ok": True})
    if method == "POST" and path == "/cardconv/history/clear":
        _save_hist([])
        return ("json", {"ok": True})
    if method == "GET" and path == "/cardconv/keywords":
        return ("html", _render_keywords(user))
    if method == "POST" and path == "/cardconv/review/reason":
        return _handle_review_reason(user, body)
    if method == "POST" and path == "/cardconv/review/match":
        return _handle_review_manual_match(user, body)
    if method == "POST" and path == "/cardconv/review/complete":
        return _handle_review_complete(user, body)
    if method == "POST" and path == "/cardconv/review/status":
        return _handle_review_set_status(user, body)
    if method == "POST" and path == "/cardconv/review/rematch":
        return ("json", _rematch_pool(user))
    if method == "GET" and path == "/cardconv/review/download":
        return _handle_review_download(user, body)  # GET passes query dict as body
    if method == "GET" and path == "/cardconv/review/download.pdf":
        return _handle_review_pdf(user, body)

    # Ledger
    if method == "GET" and path == "/cardconv/ledger":
        return ("html", _render_ledger(user))
    if method == "GET" and path == "/cardconv/ledger/api":
        return _handle_ledger_api(user, body)  # GET passes query dict as body
    if method == "GET" and path == "/cardconv/ledger/download.pdf":
        return _handle_ledger_pdf(user, body)  # GET passes query dict as body
    if method == "POST" and path == "/cardconv/ledger/delete":
        return _handle_ledger_delete(user, body)
    if method == "POST" and path == "/cardconv/ledger/complete":
        return _handle_ledger_complete(user, body)
    if method == "POST" and path == "/cardconv/ledger/bulk":
        return _handle_ledger_bulk(user, body)
    if method == "GET" and path == "/cardconv/ledger/download.xlsx":
        return _handle_ledger_xlsx(user, body)  # GET passes query dict as body
    if method == "POST" and path.startswith("/cardconv/ledger/") and path.endswith("/status"):
        entry_id = path[len("/cardconv/ledger/"):-len("/status")]
        return _handle_status_change(user, entry_id, body)
    if method == "POST" and path.startswith("/cardconv/ledger/") and path.endswith("/update"):
        entry_id = path[len("/cardconv/ledger/"):-len("/update")]
        return _handle_ledger_update(user, entry_id, body)
    if method == "POST" and path.startswith("/cardconv/ledger/") and path.endswith("/reocr"):
        entry_id = path[len("/cardconv/ledger/"):-len("/reocr")]
        return _handle_reocr(user, entry_id)
    if method == "POST" and path.startswith("/cardconv/ledger/") and path.endswith("/rematch"):
        entry_id = path[len("/cardconv/ledger/"):-len("/rematch")]
        return _handle_rematch(user, entry_id)
    if method == "GET" and path.startswith("/cardconv/receipts/image/"):
        file_id = path[len("/cardconv/receipts/image/"):]
        bbox = None
        raw_bbox = (ctx.get("query") or {}).get("bbox")
        if raw_bbox:
            try:
                bbox = [float(v) for v in raw_bbox.split(",")]
            except Exception:
                bbox = None
        return _handle_image_proxy(user, file_id, bbox)
    if method == "POST" and path == "/cardconv/batch/run":
        return _handle_batch_run(user, ctx)

    # Drive OAuth
    if method == "GET" and path == "/cardconv/drive/connect":
        return _handle_drive_connect(user, body)
    if method == "POST" and path == "/cardconv/drive/auth":
        return _handle_drive_auth(user, body)
    if method == "POST" and path == "/cardconv/drive/request-tester":
        from services import auth as _auth
        _auth.add_tester_request(body.get("tester_email", [""])[0], requested_by=user)
        return ("redirect", "/cardconv/drive/connect?requested=1")

    # Drive sync (background)
    if method == "POST" and path == "/cardconv/drive/sync":
        return _handle_drive_sync(user)
    if method == "GET" and path == "/cardconv/drive/sync/status":
        return _handle_drive_sync_status(user, body)  # GET passes query as body
    if method == "GET" and path == "/cardconv/drive/newcount":
        return _handle_drive_newcount(user)

    # Receipt upload
    if method == "POST" and path == "/cardconv/receipts/upload":
        return _handle_receipt_upload(user, body)

    # Manual receipt addition (for OCR-missed sub-receipts on an existing image)
    if method == "POST" and path == "/cardconv/receipts/manual-add":
        return _handle_manual_receipt_add(user, body)

    # Web Push subscription management
    if method == "POST" and path == "/cardconv/push/subscribe":
        sub = body if isinstance(body, dict) else {}
        if not sub.get("endpoint"):
            return ("json", {"error": "invalid subscription"}, 400)
        subs = _load_push_subs(user)
        endpoints = {s.get("endpoint") for s in subs}
        if sub["endpoint"] not in endpoints:
            subs.append(sub)
            _save_push_subs(user, subs)
        return ("json", {"ok": True})
    if method == "POST" and path == "/cardconv/push/unsubscribe":
        endpoint = (body or {}).get("endpoint", "")
        subs = [s for s in _load_push_subs(user) if s.get("endpoint") != endpoint]
        _save_push_subs(user, subs)
        return ("json", {"ok": True})

    # OCR staging review
    if method == "GET" and path == "/cardconv/receipts/review":
        return ("html", _render_ocr_staging_review(user))
    if method == "GET" and path == "/cardconv/receipts/review/api":
        staging = _load_ocr_staging(user)
        return ("json", {"entries": staging.get("entries", [])})
    if method == "POST" and path == "/cardconv/receipts/review/confirm":
        return _handle_ocr_staging_confirm(user, body)
    if method == "POST" and path == "/cardconv/receipts/review/discard":
        _clear_ocr_staging(user)
        return ("redirect", "/cardconv/ledger")

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
        res = _handle_upload(body, user)
        # Still-encrypted NASCA DRM file — show a guided notice, not an error.
        if isinstance(res, tuple) and res and res[0] == "drm_blocked":
            return ("html", _render_drm_alert(user, res[1]))
        return res

    # Uploaded CSV reuse (re-run / delete)
    if method == "POST" and path == "/cardconv/upload/rerun":
        uid = (body.get("id", [""])[0]).strip()
        return _handle_upload_rerun(user, uid)
    if method == "POST" and path == "/cardconv/upload/delete":
        uid = (body.get("id", [""])[0]).strip()
        return _handle_upload_delete(user, uid)

    # Card member names (My Card Names)
    if method == "POST" and path == "/cardconv/cardnames/add":
        # Section moved from Keywords to Convert page; redirect there.
        name = (body.get("name", [""])[0]).strip().upper()
        if name:
            s = _load_user_settings(user)
            names = s.get("card_member_names") or list(DEFAULT_CARD_NAMES)
            if name not in [n.strip().upper() for n in names]:
                names.append(name)
            s["card_member_names"] = names
            _save_user_settings(user, s)
        return ("redirect", "/cardconv/convert")
    if method == "POST" and path == "/cardconv/cardnames/delete":
        name = (body.get("name", [""])[0]).strip().upper()
        s = _load_user_settings(user)
        names = s.get("card_member_names") or list(DEFAULT_CARD_NAMES)
        s["card_member_names"] = [n for n in names if n.strip().upper() != name]
        _save_user_settings(user, s)
        return ("redirect", "/cardconv/convert")

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


def _handle_drive_connect(username: str, body=None):
    requested = bool(body and body.get("requested"))
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
        return ("html", _render_drive_connect(username, auth_url, requested=requested))
    except Exception as e:
        return ("html", f"<p style='padding:20px;color:var(--danger)'>Drive connect error: {e}</p>")


