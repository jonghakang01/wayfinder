import hashlib, json, os, secrets, shutil

DATA_ROOT     = os.path.expanduser("~/.appdata")
USERS_FILE    = os.path.join(DATA_ROOT, "users.json")
SESSIONS_FILE = os.path.join(DATA_ROOT, "sessions.json")
SETTINGS_FILE = os.path.join(DATA_ROOT, "settings.json")
SESSIONS = {}  # token -> username  (persisted to SESSIONS_FILE)

# Identity model: users are keyed by an internal id ("data_key") that also names
# their on-disk data (data_dir, cardconv receipts_<id>.json, …). New users' key
# IS their email; the admin keeps the legacy key "jongha.kang" so existing data is
# never moved. Login is by email — _resolve_login maps an email to its key.
ADMIN_USERNAME    = "jongha.kang"          # admin's data_key (legacy, preserves data)
ADMIN_EMAIL       = "jongha.kang01@gmail.com"
CONTROLLED_SERVICES = {"todo", "cardconv", "aeo", "llm-check"}
APP_LABELS = {
    "todo":      "📋 Daily Task",
    "cardconv":  "💳 Cheil USA AMEX Converter",
    "aeo":       "🔍 AEO Analysis",
    "llm-check": "🤖 AEO 페이지 진단",
}


def _load_sessions():
    global SESSIONS
    os.makedirs(DATA_ROOT, exist_ok=True)
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE) as f:
                SESSIONS = json.load(f)
        except Exception:
            SESSIONS = {}

def _save_sessions():
    with open(SESSIONS_FILE, "w") as f:
        json.dump(SESSIONS, f)

_load_sessions()


def data_dir(username):
    d = os.path.join(DATA_ROOT, username)
    os.makedirs(d, exist_ok=True)
    flag = os.path.join(d, ".migrated")
    if not os.path.exists(flag):
        for fname in ["todo.json", "habits.json"]:
            src = os.path.expanduser(f"~/.{fname}")
            dst = os.path.join(d, fname)
            if os.path.exists(src) and not os.path.exists(dst):
                shutil.copy2(src, dst)
        open(flag, "w").close()
    return d


def load_settings():
    os.makedirs(DATA_ROOT, exist_ok=True)
    defaults = {"available_services": sorted(CONTROLLED_SERVICES)}
    if not os.path.exists(SETTINGS_FILE):
        save_settings(defaults)
        return defaults
    try:
        with open(SETTINGS_FILE) as f:
            return json.load(f)
    except Exception:
        return defaults


def save_settings(settings):
    os.makedirs(DATA_ROOT, exist_ok=True)
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, ensure_ascii=False, indent=2)


def live_services():
    """Services the admin has marked live (selectable in the bare-signup picker).
    Admin toggles these via /admin → 전역 서비스 제어 (settings.available_services)."""
    avail = load_settings().get("available_services", [])
    return [s for s in avail if s in CONTROLLED_SERVICES]


def _migrate_format(data):
    changed = False
    for k, v in list(data.items()):
        if isinstance(v, str):
            data[k] = {
                "pw": v, "role": "admin" if k == ADMIN_USERNAME else "user",
                "email": "", "services": sorted(CONTROLLED_SERVICES), "blocked": False,
            }
            changed = True
        else:
            if "email" not in v:
                v["email"] = ""; changed = True
            if "blocked" not in v:
                v["blocked"] = False; changed = True
            if "services" not in v:
                v["services"] = sorted(CONTROLLED_SERVICES); changed = True
            else:
                # Migrate old "habit" service → "cardconv" if applicable
                svcs = v["services"]
                new_svcs = [s for s in svcs if s in CONTROLLED_SERVICES]
                if set(new_svcs) != set(svcs):
                    v["services"] = new_svcs; changed = True
    # Email-as-ID migration. Give the admin its known email so it can log in by
    # email, and prune legacy email-less accounts (the old test users) — every
    # real account now carries an email at registration.
    for k, v in list(data.items()):
        if not isinstance(v, dict):
            continue
        if v.get("role") == "admin" or k == ADMIN_USERNAME:
            if not v.get("email"):
                v["email"] = ADMIN_EMAIL; changed = True
        elif not (v.get("email") or "").strip():
            del data[k]; changed = True
    return data, changed


def _resolve_login(email: str):
    """Map a login email to its internal user key, or None.

    New accounts are keyed directly by email; legacy/admin accounts are matched
    on their stored email field. The raw key is also accepted as a fallback so
    the admin can still log in with the legacy id.
    """
    email = (email or "").strip().lower()
    if not email:
        return None
    users = load_users()
    if email in users:
        return email
    for k, v in users.items():
        if isinstance(v, dict) and (v.get("email") or "").strip().lower() == email:
            return k
    return None


def load_users():
    os.makedirs(DATA_ROOT, exist_ok=True)
    if not os.path.exists(USERS_FILE):
        return {}
    try:
        with open(USERS_FILE) as f:
            data = json.load(f)
        data, changed = _migrate_format(data)
        if changed:
            save_users(data)
        return data
    except Exception:
        return {}


def save_users(users):
    os.makedirs(DATA_ROOT, exist_ok=True)
    with open(USERS_FILE, "w") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)


def hash_pw(password):
    return hashlib.sha256(password.encode()).hexdigest()


def get_user(cookie_str):
    if not cookie_str:
        return None
    for part in cookie_str.split(";"):
        k, _, v = part.strip().partition("=")
        if k.strip() == "session":
            return SESSIONS.get(v.strip())
    return None


def get_role(username):
    if not username:
        return "user"
    return load_users().get(username, {}).get("role", "user")


def is_admin(username):
    return get_role(username) == "admin"


def is_blocked(username):
    if not username:
        return False
    return load_users().get(username, {}).get("blocked", False)


def has_service_access(username, service_path):
    service_name = service_path.lstrip("/").split("/")[0]
    # Admin sees everything; everyone else only reaches explicitly granted services.
    if is_admin(username):
        return True
    users = load_users()
    if users.get(username, {}).get("blocked"):
        return False
    return service_name in users.get(username, {}).get("services", [])


def block_user(username):
    users = load_users()
    if username in users:
        users[username]["blocked"] = True
        save_users(users)
        # Invalidate all sessions for this user
        for token, uname in list(SESSIONS.items()):
            if uname == username:
                del SESSIONS[token]
        _save_sessions()


def unblock_user(username):
    users = load_users()
    if username in users:
        users[username]["blocked"] = False
        save_users(users)


def delete_user(username):
    users = load_users()
    if username in users and users[username].get("role") != "admin":
        del users[username]
        save_users(users)
        for token, uname in list(SESSIONS.items()):
            if uname == username:
                del SESSIONS[token]
        _save_sessions()


def set_role(username, role):
    if role not in ("admin", "user"):
        return
    users = load_users()
    if username in users:
        users[username]["role"] = role
        save_users(users)


def handle(method, path, body, ctx=None):
    if path == "/logout":
        cookie = (ctx or {}).get("cookie", "")
        for part in (cookie or "").split(";"):
            k, _, v = part.strip().partition("=")
            if k.strip() == "session":
                SESSIONS.pop(v.strip(), None)
        _save_sessions()
        return ("set_cookie_redirect", "/login", "session=; Max-Age=0; Path=/; HttpOnly")

    if method == "POST":
        action   = body.get("action", ["login"])[0]
        email    = body.get("email", [""])[0].strip().lower()
        password = body.get("password", [""])[0]
        # Optional app scope from the per-app signup/login link (/login?app=cardconv).
        app = body.get("app", [""])[0].strip()
        if app not in CONTROLLED_SERVICES:
            app = ""

        if not email or not password:
            return ("html", render_login("이메일과 비밀번호를 입력하세요.", app=app))
        if "@" not in email or "." not in email.split("@")[-1]:
            return ("html", render_login("올바른 이메일을 입력하세요.", app=app))

        users   = load_users()
        pw_hash = hash_pw(password)

        if action == "register":
            if _resolve_login(email):
                return ("html", render_login(
                    register_error="이미 가입된 이메일입니다. 로그인하세요.", app=app))
            role = "admin" if email == ADMIN_EMAIL else "user"
            # All signups are auto-approved (open). An app link fixes the one
            # service; a bare signup grants whichever live services were ticked.
            if app:
                services_list = [app]
            else:
                picked = body.get("svc", [])
                services_list = [s for s in picked if s in live_services()]
            key = email  # new accounts are keyed by their email
            users[key] = {
                "pw": pw_hash, "role": role,
                "email": email, "services": services_list, "blocked": False,
            }
            save_users(users)
        else:
            key = _resolve_login(email)
            if not key:
                return ("html", render_login("존재하지 않는 계정입니다.", app=app))
            if users[key]["pw"] != pw_hash:
                return ("html", render_login("비밀번호가 틀렸습니다.", app=app))
            # Accumulate: logging in through an app link grants that app (password
            # was just verified, so this is safe self-service access).
            if app and app not in users[key].get("services", []):
                users[key].setdefault("services", []).append(app)
                save_users(users)

        data_dir(key)
        token = secrets.token_urlsafe(32)
        SESSIONS[token] = key
        _save_sessions()
        cookie = f"session={token}; HttpOnly; Path=/; SameSite=Lax"
        return ("set_cookie_redirect", "/", cookie)

    # GET — render the login/signup page, scoped to ?app= when present.
    app = body.get("app", [""])[0].strip() if isinstance(body, dict) else ""
    if app not in CONTROLLED_SERVICES:
        app = ""
    return ("html", render_login(app=app))


def render_login(error="", register_error="", app=""):
    svc_labels = APP_LABELS
    app = app if app in CONTROLLED_SERVICES else ""

    # App-scoped signup: the link (/login?app=cardconv) fixes which service the new
    # account gets, so we drop the service picker and show the app name instead.
    if app:
        app_label = svc_labels.get(app, app)
        svc_html = (f'<input type="hidden" name="app" value="{app}">'
                    f'<div class="app-scope">가입 서비스: <b>{app_label}</b></div>')
        signup_title = f"{app_label} 가입"
        app_hidden = f'<input type="hidden" name="app" value="{app}">'
    else:
        # Bare signup: let the user pick which live service(s) to join.
        # Live set is admin-controlled (/admin → 전역 서비스 제어).
        live = live_services()
        if live:
            checks = "".join(
                f'<label class="svc-check"><input type="checkbox" name="svc" '
                f'value="{s}" checked> {svc_labels.get(s, s)}</label>'
                for s in live
            )
            svc_html = ('<label style="margin-top:6px">가입할 서비스</label>'
                        f'<div class="svc-checks">{checks}</div>')
        else:
            svc_html = ('<div class="app-scope" style="color:#6e7681">'
                        '서비스별 가입 링크로 들어오면 해당 서비스 권한이 부여됩니다.</div>')
        signup_title = "새 계정 만들기"
        app_hidden = ""

    err = f'<div class="error">{error}</div>' if error else ""
    reg_err = f'<div class="error">{register_error}</div>' if register_error else ""

    return f'''<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>로그인 · Wayfinder</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh;padding:40px 16px}}
.wrap{{width:100%;max-width:380px;display:flex;flex-direction:column;gap:16px}}
.box{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:32px}}
h1{{font-size:22px;font-weight:700;margin-bottom:24px;text-align:center}}
h2{{font-size:15px;font-weight:600;color:#8b949e;margin-bottom:20px}}
.field{{margin-bottom:14px}}
label{{display:block;font-size:13px;color:#8b949e;margin-bottom:6px}}
input[type=text],input[type=password],input[type=email]{{width:100%;padding:10px 14px;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#e6edf3;font-size:14px;outline:none;transition:border-color .15s}}
input[type=text]:focus,input[type=password]:focus,input[type=email]:focus{{border-color:#58a6ff}}
.btn-login{{width:100%;padding:11px;background:linear-gradient(135deg,#1f6feb,#388bfd);color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-top:4px;transition:filter .15s}}
.btn-register{{width:100%;padding:11px;background:#21262d;color:#e6edf3;border:1px solid #30363d;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-top:4px;transition:filter .15s}}
.btn-login:hover,.btn-register:hover{{filter:brightness(1.15)}}
.error{{background:rgba(248,81,73,.12);border:1px solid rgba(248,81,73,.4);color:#f85149;border-radius:6px;padding:10px 14px;font-size:13px;margin-bottom:14px}}
.divider{{border:none;border-top:1px solid #21262d;margin:0}}
.svc-checks{{display:flex;gap:12px;flex-wrap:wrap;margin-top:6px}}
.svc-check{{display:flex;align-items:center;gap:6px;font-size:13px;color:#c9d1d9;cursor:pointer}}
.svc-check input{{width:auto}}
.app-scope{{font-size:13px;color:#c9d1d9;background:#0d1117;border:1px solid #30363d;border-radius:8px;padding:10px 14px;margin-bottom:14px}}
.app-scope b{{color:#58a6ff}}
</style>
</head><body>
<!--wf-root-->
<div class="wrap">
  <div class="box">
    <h1>🧭 Wayfinder</h1>
    {err}
    <form method="POST" action="/login">
      <input type="hidden" name="action" value="login">
      {app_hidden}
      <div class="field"><label>이메일</label><input type="email" name="email" autofocus autocomplete="email" placeholder="you@example.com"></div>
      <div class="field"><label>비밀번호</label><input type="password" name="password" autocomplete="current-password" placeholder="••••••••"></div>
      <button class="btn-login" type="submit">로그인</button>
    </form>
  </div>
  <hr class="divider">
  <div class="box">
    <h2>{signup_title}</h2>
    {reg_err}
    <form method="POST" action="/login">
      <input type="hidden" name="action" value="register">
      <div class="field"><label>이메일</label><input type="email" name="email" autocomplete="email" placeholder="you@example.com"></div>
      <div class="field"><label>비밀번호</label><input type="password" name="password" autocomplete="new-password" placeholder="••••••••"></div>
      {svc_html}
      <button class="btn-register" type="submit">가입</button>
    </form>
  </div>
</div>
</body></html>'''
