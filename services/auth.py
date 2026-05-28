import hashlib, json, os, secrets, shutil

DATA_ROOT     = os.path.expanduser("~/.appdata")
USERS_FILE    = os.path.join(DATA_ROOT, "users.json")
SESSIONS_FILE = os.path.join(DATA_ROOT, "sessions.json")
SETTINGS_FILE = os.path.join(DATA_ROOT, "settings.json")
SESSIONS = {}  # token -> username  (persisted to SESSIONS_FILE)

ADMIN_USERNAME    = "jongha.kang"
CONTROLLED_SERVICES = {"todo", "habit"}


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


def _migrate_format(data):
    changed = False
    for k, v in list(data.items()):
        if isinstance(v, str):
            data[k] = {
                "pw": v, "role": "admin" if k == ADMIN_USERNAME else "user",
                "email": "", "services": sorted(CONTROLLED_SERVICES),
            }
            changed = True
        else:
            if "email" not in v:
                v["email"] = ""
                changed = True
            if "services" not in v:
                v["services"] = sorted(CONTROLLED_SERVICES)
                changed = True
    return data, changed


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


def has_service_access(username, service_path):
    service_name = service_path.lstrip("/").split("/")[0]
    if service_name not in CONTROLLED_SERVICES:
        return True
    if is_admin(username):
        return True
    users = load_users()
    return service_name in users.get(username, {}).get("services", [])


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
        action = body.get("action", ["login"])[0]
        username = body.get("username", [""])[0].strip().lower()
        password = body.get("password", [""])[0]

        if not username or not password:
            return ("html", render_login("아이디와 비밀번호를 입력하세요."))

        users = load_users()
        pw_hash = hash_pw(password)

        if action == "register":
            if username in users:
                return ("html", render_login(register_error="이미 존재하는 아이디입니다."))
            role = "admin" if username == ADMIN_USERNAME else "user"
            email = body.get("email", [""])[0].strip()
            services_raw = body.get("services", [])
            services_list = [s for s in services_raw if s in CONTROLLED_SERVICES]
            users[username] = {
                "pw": pw_hash, "role": role,
                "email": email, "services": services_list,
            }
            save_users(users)
        else:
            if username not in users:
                return ("html", render_login("존재하지 않는 아이디입니다."))
            if users[username]["pw"] != pw_hash:
                return ("html", render_login("비밀번호가 틀렸습니다."))

        data_dir(username)
        token = secrets.token_urlsafe(32)
        SESSIONS[token] = username
        _save_sessions()
        cookie = f"session={token}; HttpOnly; Path=/; SameSite=Lax"
        return ("set_cookie_redirect", "/", cookie)

    return ("html", render_login())


def render_login(error="", register_error=""):
    settings = load_settings()
    available = settings.get("available_services", [])
    svc_labels = {"todo": "📋 Todo", "habit": "🏃 습관 트래커"}

    svc_html = ""
    if available:
        checks = "".join(
            f'<label class="svc-check"><input type="checkbox" name="services" value="{s}" checked> {svc_labels.get(s, s)}</label>'
            for s in available
        )
        svc_html = f'''<div class="field">
      <label>서비스 선택</label>
      <div class="svc-checks">{checks}</div>
    </div>'''

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
</style>
</head><body>
<div class="wrap">
  <div class="box">
    <h1>🧭 Wayfinder</h1>
    {err}
    <form method="POST" action="/login">
      <input type="hidden" name="action" value="login">
      <div class="field"><label>아이디</label><input type="text" name="username" autofocus autocomplete="username" placeholder="username"></div>
      <div class="field"><label>비밀번호</label><input type="password" name="password" autocomplete="current-password" placeholder="••••••••"></div>
      <button class="btn-login" type="submit">로그인</button>
    </form>
  </div>
  <hr class="divider">
  <div class="box">
    <h2>새 계정 만들기</h2>
    {reg_err}
    <form method="POST" action="/login">
      <input type="hidden" name="action" value="register">
      <div class="field"><label>아이디</label><input type="text" name="username" autocomplete="username" placeholder="username"></div>
      <div class="field"><label>비밀번호</label><input type="password" name="password" autocomplete="new-password" placeholder="••••••••"></div>
      <div class="field"><label>이메일 <span style="font-size:11px;color:#6e7681">(선택)</span></label><input type="email" name="email" autocomplete="email" placeholder="you@example.com"></div>
      {svc_html}
      <button class="btn-register" type="submit">가입</button>
    </form>
  </div>
</div>
</body></html>'''
