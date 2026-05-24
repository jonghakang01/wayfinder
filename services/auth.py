import hashlib, json, os, secrets, shutil

DATA_ROOT    = os.path.expanduser("~/.appdata")
USERS_FILE   = os.path.join(DATA_ROOT, "users.json")
SESSIONS_FILE = os.path.join(DATA_ROOT, "sessions.json")
SESSIONS = {}  # token -> username  (persisted to SESSIONS_FILE)

ADMIN_USERNAME = "jongha.kang"


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


def _migrate_format(data):
    changed = False
    for k, v in list(data.items()):
        if isinstance(v, str):
            data[k] = {"pw": v, "role": "admin" if k == ADMIN_USERNAME else "user"}
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
        username = body.get("username", [""])[0].strip().lower()
        password = body.get("password", [""])[0]
        if not username or not password:
            return ("html", render_login("아이디와 비밀번호를 입력하세요."))

        users = load_users()
        pw_hash = hash_pw(password)

        if username in users:
            if users[username]["pw"] != pw_hash:
                return ("html", render_login("비밀번호가 틀렸습니다."))
        else:
            role = "admin" if username == ADMIN_USERNAME else "user"
            users[username] = {"pw": pw_hash, "role": role}
            save_users(users)

        data_dir(username)
        token = secrets.token_urlsafe(32)
        SESSIONS[token] = username
        _save_sessions()
        cookie = f"session={token}; HttpOnly; Path=/; SameSite=Lax"
        return ("set_cookie_redirect", "/", cookie)

    return ("html", render_login())


def render_login(error=""):
    err = f'<div class="error">{error}</div>' if error else ""
    return f'''<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>로그인 · Wayfinder</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
body{{background:#0d1117;color:#e6edf3;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:flex;align-items:center;justify-content:center;min-height:100vh}}
.box{{background:#161b22;border:1px solid #30363d;border-radius:12px;padding:40px;width:100%;max-width:380px}}
h1{{font-size:22px;font-weight:700;margin-bottom:6px;text-align:center}}
.sub{{font-size:13px;color:#8b949e;text-align:center;margin-bottom:28px}}
.field{{margin-bottom:16px}}
label{{display:block;font-size:13px;color:#8b949e;margin-bottom:6px}}
input{{width:100%;padding:10px 14px;background:#0d1117;border:1px solid #30363d;border-radius:8px;color:#e6edf3;font-size:14px;outline:none;transition:border-color .15s}}
input:focus{{border-color:#58a6ff}}
button{{width:100%;padding:11px;background:linear-gradient(135deg,#238636,#2ea043);color:#fff;border:none;border-radius:8px;font-size:15px;font-weight:600;cursor:pointer;margin-top:8px;transition:filter .15s}}
button:hover{{filter:brightness(1.1)}}
.error{{background:rgba(248,81,73,.12);border:1px solid rgba(248,81,73,.4);color:#f85149;border-radius:6px;padding:10px 14px;font-size:13px;margin-bottom:16px}}
.hint{{font-size:12px;color:#8b949e;text-align:center;margin-top:16px;line-height:1.5}}
</style>
</head><body>
<div class="box">
  <h1>🧭 Wayfinder</h1>
  <p class="sub">로그인하거나 새 계정을 만드세요</p>
  {err}
  <form method="POST" action="/login">
    <div class="field"><label>아이디</label><input name="username" autofocus autocomplete="username" placeholder="username"></div>
    <div class="field"><label>비밀번호</label><input name="password" type="password" autocomplete="current-password" placeholder="••••••••"></div>
    <button type="submit">로그인 / 가입</button>
  </form>
  <p class="hint">처음 입력하는 아이디는 자동으로 계정이 생성됩니다</p>
</div>
</body></html>'''
