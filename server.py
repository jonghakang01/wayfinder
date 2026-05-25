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
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');
:root {
  --slate-50: #f8fafc; --slate-100: #f1f5f9; --slate-200: #e2e8f0;
  --slate-400: #94a3b8; --slate-500: #64748b; --slate-900: #0f172a;
  --blue-500: #3b82f6; --sky-400: #38bdf8;
  --radius-xl: 20px; --radius-lg: 16px; --radius-md: 12px;
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0/0.1), 0 4px 6px -4px rgb(0 0 0/0.1);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Pretendard Variable', Pretendard, -apple-system, system-ui, sans-serif; background: var(--slate-50); color: var(--slate-900); line-height: 1.5; -webkit-font-smoothing: antialiased; min-height: 100vh; }

/* Nav */
nav { background: rgba(15,23,42,0.92); backdrop-filter: blur(12px); padding: 13px 32px; display: flex; align-items: center; justify-content: space-between; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid rgba(255,255,255,0.07); }
nav a { color: var(--slate-400); text-decoration: none; font-size: 0.875rem; transition: color 0.15s; }
nav a:hover { color: white; }
.nav-brand { color: white; font-weight: 800; font-size: 1.05rem; letter-spacing: -0.02em; }
.nav-user { color: var(--slate-500); font-size: 0.82rem; display: flex; align-items: center; gap: 10px; }
.nav-user a { color: var(--slate-400); padding: 5px 11px; border-radius: 8px; background: rgba(255,255,255,0.05); transition: 0.2s; }
.nav-user a:hover { color: white; background: rgba(255,255,255,0.1); }
.nav-back { color: var(--slate-400); font-size: 0.82rem; text-decoration: none; display: flex; align-items: center; gap: 4px; }
.nav-back:hover { color: white; }

/* Layout */
.container { max-width: 880px; margin: 0 auto; padding: 44px 24px 80px; }
h1 { font-size: 1.75rem; color: var(--slate-900); margin-bottom: 6px; font-weight: 800; letter-spacing: -0.03em; }

/* Dashboard widget */
.dashboard { background: var(--slate-900); background-image: radial-gradient(at 0% 0%, rgba(56,189,248,0.15) 0, transparent 50%), radial-gradient(at 100% 100%, rgba(59,130,246,0.15) 0, transparent 50%); border-radius: var(--radius-xl); padding: 36px 40px; margin-bottom: 48px; color: white; display: flex; justify-content: space-between; align-items: center; gap: 24px; flex-wrap: wrap; box-shadow: var(--shadow-lg); border: 1px solid rgba(255,255,255,0.05); }
.dashboard-greeting h2 { font-size: 1.6rem; font-weight: 800; margin-bottom: 6px; letter-spacing: -0.03em; }
.dashboard-greeting p { color: var(--slate-400); font-size: 0.95rem; font-weight: 500; }
.dashboard-stats { display: flex; gap: 14px; flex-wrap: wrap; }
.stat-card { background: rgba(255,255,255,0.04); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius-lg); padding: 16px 24px; text-align: center; min-width: 100px; transition: 0.2s; }
.stat-card:hover { transform: translateY(-3px); background: rgba(255,255,255,0.07); }
.stat-card .stat-num { font-size: 2rem; font-weight: 800; line-height: 1; margin-bottom: 6px; }
.stat-card .stat-label { font-size: 0.7rem; color: var(--slate-400); font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }
.stat-card.highlight .stat-num { color: var(--sky-400); text-shadow: 0 0 20px rgba(56,189,248,0.3); }

/* App entry card */
.app-entry-card { display:flex; align-items:center; gap:20px; background:white; border:1px solid var(--slate-200); border-radius:var(--radius-xl); padding:24px 28px; text-decoration:none; color:inherit; transition:all .25s; margin-bottom:32px; position:relative; overflow:hidden; }
.app-entry-card::before { content:""; position:absolute; top:0; left:0; right:0; height:4px; background:linear-gradient(90deg,#3b82f6,#38bdf8); }
.app-entry-card:hover { box-shadow:var(--shadow-lg); transform:translateY(-3px); border-color:var(--blue-500); }
.app-entry-icon { font-size:2.5rem; filter:drop-shadow(0 2px 6px rgba(0,0,0,0.1)); }
.app-entry-text { flex:1; }
.app-entry-name { font-size:1.1rem; font-weight:800; color:var(--slate-900); margin-bottom:4px; letter-spacing:-.02em; }
.app-entry-tabs { font-size:0.8rem; color:var(--slate-400); font-weight:500; }
.app-entry-arrow { font-size:1.4rem; color:var(--slate-300); transition:.2s; }
.app-entry-card:hover .app-entry-arrow { color:var(--blue-500); transform:translateX(4px); }
@media(max-width:600px) { .app-entry-card { padding:18px 20px; gap:14px; } .app-entry-icon { font-size:2rem; } }

/* Category */
.category-section { margin-bottom: 40px; }
.category-title { font-size: 0.7rem; font-weight: 700; color: var(--slate-400); text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: 14px; padding-left: 2px; }

/* Wayfinder cards */
.service-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(185px, 1fr)); gap: 14px; }
.service-card { background: white; border-radius: var(--radius-lg); padding: 24px; border: 1px solid var(--slate-200); text-decoration: none; color: inherit; transition: all 0.25s cubic-bezier(0.4,0,0.2,1); display: flex; flex-direction: column; position: relative; overflow: hidden; }
.service-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--blue-500); opacity: 0; transition: 0.2s; }
.service-card:hover { box-shadow: var(--shadow-lg); transform: translateY(-4px); border-color: var(--blue-500); }
.service-card:hover::before { opacity: 1; }
.service-icon { font-size: 2rem; margin-bottom: 14px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.08)); }
.service-name { font-weight: 700; font-size: 0.95rem; color: var(--slate-900); margin-bottom: 5px; }
.service-desc { font-size: 0.78rem; color: var(--slate-400); line-height: 1.5; }

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

/* Mobile responsive */
@media (max-width: 600px) {
  .container { padding: 24px 16px calc(60px + env(safe-area-inset-bottom, 0px)); }
  nav { padding: 10px 16px; }
  .nav-user { gap: 6px; }
  .nav-user a { padding: 8px 12px; min-height: 44px; display: inline-flex; align-items: center; }
  .dashboard { padding: 24px 20px; flex-direction: column; gap: 16px; }
  .dashboard-greeting h2 { font-size: 1.25rem; }
  .service-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .service-card { padding: 16px; }
  .service-icon { font-size: 1.5rem; margin-bottom: 8px; }
  .service-name { font-size: 0.85rem; }
  .service-desc { display: none; }
  .add-form { flex-direction: column; }
  .add-form input, .add-form button { width: 100%; }
  .add-form input { font-size: 1rem; min-height: 44px; }
  .add-form button { min-height: 44px; font-size: 1rem; }
  .todo-item { flex-wrap: wrap; padding: 12px 14px; }
  .actions { width: 100%; justify-content: flex-end; margin-top: 8px; flex-wrap: wrap; gap: 6px; }
  .btn { padding: 10px 14px; font-size: 0.85rem; min-height: 44px; display: inline-flex; align-items: center; justify-content: center; }
  .stat-card { padding: 12px 16px; min-width: 80px; }
  .stat-card .stat-num { font-size: 1.6rem; }
  h1 { font-size: 1.4rem; }
  /* PWA Install Banner */
  .pwa-banner { display: none; background: white; border: 1px solid var(--slate-200); border-radius: var(--radius-lg); padding: 16px; margin-bottom: 24px; box-shadow: var(--shadow-lg); position: relative; align-items: center; gap: 16px; }
  .pwa-banner.show { display: flex; }
  .pwa-icon { font-size: 2rem; }
  .pwa-text { flex: 1; }
  .pwa-title { font-weight: 700; font-size: 0.95rem; color: var(--slate-900); margin-bottom: 4px; }
  .pwa-desc { font-size: 0.8rem; color: var(--slate-500); line-height: 1.4; }
  .pwa-close { position: absolute; top: 12px; right: 12px; background: none; border: none; color: var(--slate-400); font-size: 1.2rem; cursor: pointer; padding: 4px; line-height: 1; min-height: 32px; min-width: 32px; display: flex; align-items: center; justify-content: center; }
  .pwa-close:hover { color: var(--slate-900); }
}
@media (max-width: 400px) {
  .service-grid { grid-template-columns: 1fr 1fr; }
  .dashboard-stats { gap: 8px; }
}
"""

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
  <rect width="192" height="192" rx="40" fill="#0f172a"/>
  <circle cx="96" cy="96" r="56" fill="none" stroke="#38bdf8" stroke-width="4"/>
  <polygon points="96,44 104,96 96,90 88,96" fill="#38bdf8"/>
  <polygon points="96,148 88,96 96,102 104,96" fill="#64748b"/>
  <circle cx="96" cy="96" r="8" fill="white"/>
</svg>"""

MANIFEST = json.dumps({
    "name": "Wayfinder",
    "short_name": "Wayfinder",
    "description": "개인 생산성 허브",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#f8fafc",
    "theme_color": "#0f172a",
    "orientation": "portrait-primary",
    "icons": [
        {"src": "/icons/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}
    ],
    "shortcuts": [
        {"name": "Todo List", "url": "/todo", "description": "할 일 관리"},
        {"name": "Habit Tracker", "url": "/habit", "description": "습관 추적"}
    ]
}, ensure_ascii=False, indent=2)

SW_JS = """
const CACHE = 'wayfinder-v1';
const STATIC = ['/static/style.css', '/manifest.json', '/icons/icon.svg'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
  self.skipWaiting();
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (STATIC.includes(url.pathname)) {
    e.respondWith(caches.match(e.request).then(c => c || fetch(e.request)));
    return;
  }
  e.respondWith(
    fetch(e.request).catch(() =>
      new Response('<h2 style="font-family:sans-serif;padding:40px">오프라인 상태입니다. 인터넷 연결을 확인해주세요.</h2>',
        {headers: {'Content-Type': 'text/html; charset=utf-8'}})
    )
  );
});
"""

APP_TAB_CSS = """
<style>
.app-tabs{position:fixed!important;top:auto!important;bottom:0!important;left:0;right:0;height:auto;background:rgba(15,23,42,0.96);backdrop-filter:blur(16px);border-top:1px solid rgba(255,255,255,0.08);border-bottom:none;display:flex!important;justify-content:stretch;z-index:200;padding:0 0 env(safe-area-inset-bottom,0)}
.app-tab{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;padding:10px 4px 8px;color:rgba(148,163,184,0.7);text-decoration:none;font-size:0.65rem;font-weight:600;letter-spacing:0.04em;text-transform:uppercase;transition:.15s}
.app-tab:hover{color:rgba(255,255,255,0.8)}
.app-tab.active{color:#38bdf8}
.app-tab-icon{font-size:1.3rem;line-height:1}
.app-tab.active .app-tab-icon{filter:drop-shadow(0 0 6px rgba(56,189,248,0.6))}
body{padding-bottom:calc(64px + env(safe-area-inset-bottom,0px))!important}
</style>
"""

def app_tabs(active):
    tabs = [
        ("/todo",      "✅", "Tasks"),
        ("/habit",     "🏃", "Habits"),
        ("/dashboard", "📊", "Overview"),
    ]
    html = APP_TAB_CSS + '<nav class="app-tabs">'
    for path, icon, label in tabs:
        cls = "app-tab active" if active == path else "app-tab"
        html += f'<a href="{path}" class="{cls}"><span class="app-tab-icon">{icon}</span>{label}</a>'
    html += "</nav>"
    return html


PWA_INJECT = (
    '<link rel="manifest" href="/manifest.json">'
    '<meta name="theme-color" content="#0f172a">'
    '<meta name="apple-mobile-web-app-capable" content="yes">'
    '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
    '<meta name="apple-mobile-web-app-title" content="Wayfinder">'
    '<link rel="apple-touch-icon" href="/icons/icon.svg">'
    "<script>if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js');</script>"
)

CATEGORIES = {
    "생산성": [],
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
    if hour < 6:
        greeting, greeting_icon = "늦은 밤이에요", "🌙"
    elif hour < 12:
        greeting, greeting_icon = "좋은 아침이에요", "☀️"
    elif hour < 18:
        greeting, greeting_icon = "안녕하세요", "🌤️"
    else:
        greeting, greeting_icon = "좋은 저녁이에요", "🌙"

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
      <h2>{greeting_icon} {greeting}, {user}님</h2>
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
  
  <a href="/todo" class="app-entry-card">
    <div class="app-entry-icon">🧭</div>
    <div class="app-entry-text">
      <div class="app-entry-name">My Productivity App</div>
      <div class="app-entry-tabs">✅ Tasks &nbsp;·&nbsp; 🏃 Habits &nbsp;·&nbsp; 📊 Overview</div>
    </div>
    <div class="app-entry-arrow">→</div>
  </a>

  <div id="pwa-banner" class="pwa-banner">
    <div class="pwa-icon">📱</div>
    <div class="pwa-text">
      <div class="pwa-title">앱으로 설치하기</div>
      <div id="pwa-desc" class="pwa-desc">바탕화면에 추가하여 빠르게 접속하세요.</div>
    </div>
    <button class="pwa-close" onclick="closePwaBanner()">×</button>
  </div>
  
  {sections_html}
</div>
<script>
  function closePwaBanner() {{
    document.getElementById('pwa-banner').classList.remove('show');
    localStorage.setItem('pwa-banner-closed', 'true');
  }}

  document.addEventListener('DOMContentLoaded', () => {{
    const isStandalone = window.matchMedia('(display-mode: standalone)').matches || window.navigator.standalone;
    const isClosed = localStorage.getItem('pwa-banner-closed') === 'true';
    const isMobile = window.innerWidth <= 600;

    if (isMobile && !isStandalone && !isClosed) {{
      const banner = document.getElementById('pwa-banner');
      const desc = document.getElementById('pwa-desc');
      const isIOS = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;
      
      if (isIOS) {{
        desc.innerHTML = 'Safari 하단의 <b>공유</b> 버튼을 누르고<br><b>홈 화면에 추가</b>를 선택하세요.';
      }} else {{
        desc.innerHTML = 'Chrome 메뉴(⋮)를 누르고<br><b>홈 화면에 추가</b>를 선택하세요.';
      }}
      banner.classList.add('show');
    }}
  }});
</script>
</body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def send_html(self, html, code=200):
        html = html.replace('</head>', PWA_INJECT + '</head>', 1)
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

    def send_text(self, text, mime):
        b = text.strip().encode()
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(b))
        self.send_header("Cache-Control", "public, max-age=86400")
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
        if path == "/manifest.json":
            return self.send_text(MANIFEST, "application/manifest+json")
        if path == "/sw.js":
            return self.send_text(SW_JS, "application/javascript")
        if path == "/icons/icon.svg":
            return self.send_text(ICON_SVG, "image/svg+xml")
        if path in ("/login", "/logout"):
            return self.dispatch(auth.handle("GET", path, {}, ctx))
        if not ctx["user"]:
            return self.redirect("/login")
        if path == "/":
            return self.send_html(wayfinder(ctx["user"]))
        for svc_path, svc in SERVICES.items():
            if path == svc_path or path.startswith(svc_path + "/"):
                if not auth.has_service_access(ctx["user"], svc_path):
                    return self.redirect("/")
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
                if not auth.has_service_access(ctx["user"], svc_path):
                    return self.redirect("/")
                return self.dispatch(svc.handle("POST", path, body, ctx))
        self.send_html("<h2>404</h2>", 404)


if __name__ == "__main__":
    port = 8080
    os.system("pkill -f todo_web.py 2>/dev/null; pkill -f 'server.py' 2>/dev/null; sleep 0.5")
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"🧭 Wayfinder running → http://localhost:{port}")
    server.serve_forever()
