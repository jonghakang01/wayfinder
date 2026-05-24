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
body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; background: #f8fafc; min-height: 100vh; }

/* Nav */
nav { background: #0f172a; padding: 14px 28px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; box-shadow: 0 1px 3px rgba(0,0,0,0.3); }
nav a { color: #94a3b8; text-decoration: none; font-size: 0.875rem; transition: color 0.15s; }
nav a:hover { color: white; }
.nav-brand { color: white; font-weight: 700; font-size: 1rem; letter-spacing: -0.01em; }
.nav-user { color: #64748b; font-size: 0.82rem; display: flex; align-items: center; gap: 10px; }
.nav-user a { color: #64748b; }
.nav-user a:hover { color: #94a3b8; }
.nav-back { color: #94a3b8; font-size: 0.82rem; text-decoration: none; display: flex; align-items: center; gap: 4px; }
.nav-back:hover { color: white; }

/* Layout */
.container { max-width: 860px; margin: 0 auto; padding: 40px 24px 80px; }
h1 { font-size: 1.75rem; color: #0f172a; margin-bottom: 6px; font-weight: 700; letter-spacing: -0.02em; }

/* Dashboard widget */
.dashboard { background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 100%); border-radius: 16px; padding: 28px 32px; margin-bottom: 40px; color: white; display: flex; justify-content: space-between; align-items: center; gap: 16px; flex-wrap: wrap; }
.dashboard-greeting h2 { font-size: 1.4rem; font-weight: 700; margin-bottom: 4px; }
.dashboard-greeting p { color: #94a3b8; font-size: 0.875rem; }
.dashboard-stats { display: flex; gap: 16px; flex-wrap: wrap; }
.stat-card { background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.12); border-radius: 10px; padding: 12px 20px; text-align: center; min-width: 80px; }
.stat-card .stat-num { font-size: 1.6rem; font-weight: 700; line-height: 1; }
.stat-card .stat-label { font-size: 0.72rem; color: #94a3b8; margin-top: 4px; }
.stat-card.highlight .stat-num { color: #38bdf8; }

/* Category */
.category-section { margin-bottom: 36px; }
.category-title { font-size: 0.72rem; font-weight: 600; color: #94a3b8; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 12px; padding-left: 2px; }

/* Wayfinder cards */
.service-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
.service-card { background: white; border-radius: 12px; padding: 20px; border: 1px solid #e2e8f0; text-decoration: none; color: inherit; transition: box-shadow 0.15s, transform 0.15s, border-color 0.15s; display: block; }
.service-card:hover { box-shadow: 0 8px 24px rgba(0,0,0,0.08); transform: translateY(-2px); border-color: #cbd5e1; }
.service-icon { font-size: 1.75rem; margin-bottom: 10px; }
.service-name { font-weight: 600; font-size: 0.9rem; color: #0f172a; margin-bottom: 3px; }
.service-desc { font-size: 0.78rem; color: #94a3b8; line-height: 1.4; }

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

CATEGORIES = {
    "생산성": ["/todo", "/habit"],
    "팀 도구": ["/terminals", "/workspace"],
    "분석": ["/aeo", "/llm-check"],
    "관리": ["/admin"],
}

def wayfinder(user):
    from datetime import datetime
    import services.todo as todo_svc

    user_is_admin = auth.is_admin(user)

    # 대시보드 통계
    todos = todo_svc.load(user)
    todo_total = len([t for t in todos if not t.get("done")])
    todo_done_today = len([t for t in todos if t.get("done") and t.get("done_at", "").startswith(datetime.now().strftime("%Y-%m-%d"))])

    hour = datetime.now().hour
    if hour < 12:
        greeting = "좋은 아침이에요"
    elif hour < 18:
        greeting = "안녕하세요"
    else:
        greeting = "좋은 저녁이에요"

    today_str = datetime.now().strftime("%Y년 %m월 %d일")

    # 서비스 path → META 매핑
    svc_map = {}
    for path, svc in SERVICES.items():
        m = svc.META
        if m.get("hidden"):
            continue
        if m.get("admin_only") and not user_is_admin:
            continue
        svc_map[path] = m

    # 카테고리별 렌더링
    sections_html = ""
    rendered = set()
    for cat_name, paths in CATEGORIES.items():
        cards = ""
        for p in paths:
            if p in svc_map:
                m = svc_map[p]
                cards += f'''<a class="service-card" href="{m["path"]}">
          <div class="service-icon">{m["icon"]}</div>
          <div class="service-name">{m["name"]}</div>
          <div class="service-desc">{m["description"]}</div>
        </a>'''
                rendered.add(p)
        if cards:
            sections_html += f'''<div class="category-section">
      <div class="category-title">{cat_name}</div>
      <div class="service-grid">{cards}</div>
    </div>'''

    # 카테고리 미분류 서비스
    extra = ""
    for p, m in svc_map.items():
        if p not in rendered:
            extra += f'''<a class="service-card" href="{m["path"]}">
          <div class="service-icon">{m["icon"]}</div>
          <div class="service-name">{m["name"]}</div>
          <div class="service-desc">{m["description"]}</div>
        </a>'''
    if extra:
        sections_html += f'''<div class="category-section">
      <div class="category-title">기타</div>
      <div class="service-grid">{extra}</div>
    </div>'''

    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🧭 Wayfinder</title>
<link rel="stylesheet" href="/static/style.css">
</head><body>
<nav>
  <span class="nav-brand">🧭 Wayfinder</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">로그아웃</a></span>
</nav>
<div class="container">
  <div class="dashboard">
    <div class="dashboard-greeting">
      <h2>{greeting}, {user}님</h2>
      <p>{today_str}</p>
    </div>
    <div class="dashboard-stats">
      <div class="stat-card highlight">
        <div class="stat-num">{todo_total}</div>
        <div class="stat-label">남은 할 일</div>
      </div>
      <div class="stat-card">
        <div class="stat-num">{todo_done_today}</div>
        <div class="stat-label">오늘 완료</div>
      </div>
    </div>
  </div>
  {sections_html}
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
