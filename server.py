#!/usr/bin/env python3
import importlib, os, sys, json
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

SERVICES_DIR = os.path.join(os.path.dirname(__file__), "services")
sys.path.insert(0, os.path.dirname(__file__))

# .env 파일 자동 로드
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

from services import auth

def load_services():
    services = {}
    for f in sorted(os.listdir(SERVICES_DIR)):
        if f.endswith(".py") and not f.startswith("_") and f != "auth.py":
            name = f[:-3]
            mod = importlib.import_module(f"services.{name}")
            if hasattr(mod, "META"):
                services[mod.META["path"]] = mod
    return services

SERVICES = load_services()

STYLE = """
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, sans-serif; background: #f5f5f5; min-height: 100vh; }
nav { background: #1e293b; padding: 12px 24px; display: flex; align-items: center; justify-content: space-between; }
nav a { color: #94a3b8; text-decoration: none; font-size: 0.9rem; }
nav a:hover { color: white; }
.nav-user { color: #94a3b8; font-size: 0.85rem; }
.container { max-width: 640px; margin: 40px auto; padding: 0 16px; }
h1 { font-size: 1.8rem; color: #1a1a1a; margin-bottom: 24px; }

/* Wayfinder */
.service-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 16px; }
.service-card { background: white; border-radius: 12px; padding: 24px; border: 1px solid #e2e8f0; text-decoration: none; color: inherit; transition: box-shadow 0.15s, transform 0.15s; display: block; }
.service-card:hover { box-shadow: 0 4px 16px rgba(0,0,0,0.1); transform: translateY(-2px); }
.service-icon { font-size: 2rem; margin-bottom: 12px; }
.service-name { font-weight: 600; font-size: 1rem; color: #1a1a1a; margin-bottom: 4px; }
.service-desc { font-size: 0.85rem; color: #64748b; }

/* Todo */
.add-form { display: flex; gap: 8px; margin-bottom: 20px; }
.add-form input { flex: 1; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 1rem; outline: none; }
.add-form input:focus { border-color: #0ea5e9; }
.add-form button { padding: 10px 18px; background: #0ea5e9; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 0.95rem; }
.stats { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.stats span { background: white; padding: 5px 12px; border-radius: 20px; border: 1px solid #e2e8f0; font-size: 0.85rem; color: #64748b; }
.stats .done-c { color: #16a34a; }
.todo-list { display: flex; flex-direction: column; gap: 8px; }
.todo-item { display: flex; align-items: center; gap: 12px; background: white; padding: 12px 16px; border-radius: 10px; border: 1px solid #e2e8f0; }
.todo-item.done { opacity: 0.5; }
.todo-item.done .title { text-decoration: line-through; color: #94a3b8; }
.tid { font-size: 0.75rem; color: #cbd5e1; min-width: 28px; }
.title { flex: 1; font-size: 0.95rem; }
.date { font-size: 0.75rem; color: #cbd5e1; }
.actions { display: flex; gap: 6px; }
.btn { padding: 4px 10px; border: none; border-radius: 6px; font-size: 0.8rem; cursor: pointer; }
.btn-done { background: #dcfce7; color: #16a34a; }
.btn-del { background: #fee2e2; color: #dc2626; }
.empty { text-align: center; color: #94a3b8; padding: 48px 0; }
"""

def wayfinder(user):
    user_is_admin = auth.is_admin(user)
    cards = ""
    for path, svc in SERVICES.items():
        m = svc.META
        if m.get("admin_only") and not user_is_admin:
            continue
        if m.get("hidden"):
            continue
        cards += f'''
        <a class="service-card" href="{m["path"]}">
          <div class="service-icon">{m["icon"]}</div>
          <div class="service-name">{m["name"]}</div>
          <div class="service-desc">{m["description"]}</div>
        </a>'''
    if not cards:
        cards = '<p style="color:#94a3b8">등록된 서비스가 없습니다.</p>'
    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🧭 Wayfinder</title>
<link rel="stylesheet" href="/static/style.css">
</head><body>
<nav>
  <span style="color:white;font-weight:600">🧭 Wayfinder</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">로그아웃</a></span>
</nav>
<div class="container">
  <h1 style="margin-top:0;padding-top:40px">서비스</h1>
  <div class="service-grid">{cards}</div>
</div>
</body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send_html(self, html, code=200):
        b = html.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def send_json(self, data, code=200):
        b = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def send_css(self):
        b = STYLE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/css")
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def dispatch(self, result):
        t = result[0]
        if t == "html":
            self.send_html(result[1])
        elif t == "json":
            self.send_json(result[1])
        elif t == "redirect":
            self.redirect(result[1])
        elif t == "set_cookie_redirect":
            self.send_response(302)
            self.send_header("Location", result[1])
            self.send_header("Set-Cookie", result[2])
            self.end_headers()
        elif t == "sse":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            try:
                for chunk in result[1]:
                    self.wfile.write(chunk.encode() if isinstance(chunk, str) else chunk)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass

    def get_ctx(self):
        cookie = self.headers.get("Cookie", "")
        return {"cookie": cookie, "user": auth.get_user(cookie)}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        ctx = self.get_ctx()
        query = parse_qs(parsed.query)

        if path == "/static/style.css":
            return self.send_css()
        if path in ("/login", "/logout"):
            return self.dispatch(auth.handle("GET", path, {}, ctx))
        if not ctx["user"]:
            return self.redirect("/login")
        if path == "/":
            return self.send_html(wayfinder(ctx["user"]))
        for svc_path, svc in SERVICES.items():
            if path == svc_path or path.startswith(svc_path + "/"):
                return self.dispatch(svc.handle("GET", path, query, ctx))
        self.send_html("<h2>404 Not Found</h2>", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        ctx = self.get_ctx()
        length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")

        if "multipart/form-data" in content_type:
            body = {"__raw__": self}
        elif "application/json" in content_type:
            try:
                body = json.loads(self.rfile.read(length).decode())
            except Exception:
                body = {}
        else:
            body = parse_qs(self.rfile.read(length).decode())

        if path == "/login":
            return self.dispatch(auth.handle("POST", path, body, ctx))
        if not ctx["user"]:
            return self.redirect("/login")
        for svc_path, svc in SERVICES.items():
            if path.startswith(svc_path):
                return self.dispatch(svc.handle("POST", path, body, ctx))
        self.send_html("<h2>404</h2>", 404)


if __name__ == "__main__":
    port = 8080
    os.system("pkill -f todo_web.py 2>/dev/null; pkill -f 'server.py' 2>/dev/null; sleep 0.5")
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"🧭 Wayfinder running → http://localhost:{port}")
    server.serve_forever()
