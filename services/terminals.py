META = {
    "name": "Team Terminal",
    "path": "/terminals",
    "icon": "🖥️",
    "description": "팀원 터미널 접속",
    "bucket": True,
}

MEMBERS = [
    {"name": "나의 터미널", "role": "현재 세션",  "port": 7680, "color": "#334155", "icon": "💻"},
    {"name": "쭌",          "role": "팀장",        "port": 7681, "color": "#1e40af", "icon": "👑"},
    {"name": "민준",        "role": "아키텍트",    "port": 7682, "color": "#065f46", "icon": "🏗️"},
    {"name": "지훈",        "role": "개발자",      "port": 7683, "color": "#7c2d12", "icon": "💻"},
    {"name": "수아",        "role": "UI/UX",       "port": 7684, "color": "#4c1d95", "icon": "🎨"},
    {"name": "서연",        "role": "리서쳐",      "port": 7685, "color": "#831843", "icon": "🔍"},
    {"name": "태양",        "role": "QA·리뷰어",   "port": 7686, "color": "#134e4a", "icon": "✅"},
]

def handle(method, path, body, ctx=None):
    if path == "/terminals/all":
        return ("html", render_overview())
    return ("html", render_list())

def render_list():
    cards = ""
    for m in MEMBERS:
        url = f"http://localhost:{m['port']}"
        cards += f'''
        <a class="term-card" href="{url}" target="_blank" style="border-top: 3px solid {m["color"]}">
          <div class="term-icon">{m["icon"]}</div>
          <div class="term-name">{m["name"]}</div>
          <div class="term-role">{m["role"]}</div>
          <div class="term-port">:{m["port"]}</div>
          <div class="term-open">터미널 열기 →</div>
        </a>'''

    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🖥️ Team Terminal</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.top-bar {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:24px; }}
.btn-all {{ padding:10px 20px; background:#1e293b; color:white; border-radius:8px; text-decoration:none; font-size:0.9rem; font-weight:600; }}
.btn-all:hover {{ background:#334155; }}
.term-grid {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(170px,1fr)); gap:16px; }}
.term-card {{ background:white; border-radius:10px; padding:20px; border:1px solid #e2e8f0; text-decoration:none; color:inherit; display:block; transition:box-shadow 0.15s,transform 0.15s; }}
.term-card:hover {{ box-shadow:0 4px 16px rgba(0,0,0,0.1); transform:translateY(-2px); }}
.term-icon {{ font-size:1.6rem; margin-bottom:8px; }}
.term-name {{ font-size:1.1rem; font-weight:700; color:#1a1a1a; margin-bottom:4px; }}
.term-role {{ font-size:0.78rem; color:#64748b; margin-bottom:10px; }}
.term-port {{ font-size:0.72rem; color:#cbd5e1; font-family:monospace; margin-bottom:6px; }}
.term-open {{ font-size:0.8rem; color:#0ea5e9; font-weight:500; }}
</style>
</head><body>
<nav><a href="/">← Wayfinder</a></nav>
<div class="container">
  <div class="top-bar">
    <h1>🖥️ Team Terminal</h1>
    <a class="btn-all" href="/terminals/all">⊞ 전체보기</a>
  </div>
  <div class="term-grid">{cards}</div>
</div>
</body></html>'''

def render_overview():
    buttons = ""
    for i, m in enumerate(MEMBERS):
        active = "active" if i == 0 else ""
        buttons += f'''
        <button class="member-btn {active}" onclick="loadTerminal({m['port']}, this)"
          style="border-left:3px solid {m['color']}">
          <span class="mb-icon">{m['icon']}</span>
          <span class="mb-info">
            <span class="mb-name">{m['name']}</span>
            <span class="mb-role">{m['role']}</span>
          </span>
          <span class="mb-port">:{m['port']}</span>
        </button>'''

    first_port = MEMBERS[0]["port"]

    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>⊞ 전체 터미널</title>
<style>
*,*::before,*::after{{box-sizing:border-box;margin:0;padding:0}}
html,body{{height:100%;overflow:hidden;background:#0d1117;color:#e6edf3;font-family:-apple-system,sans-serif}}
.layout{{display:flex;height:100vh}}
/* sidebar */
.sidebar{{width:220px;flex-shrink:0;background:#161b22;border-right:1px solid #30363d;display:flex;flex-direction:column}}
.sidebar-header{{padding:14px 16px;border-bottom:1px solid #30363d;display:flex;align-items:center;justify-content:space-between}}
.sidebar-title{{font-size:13px;font-weight:600;color:#8b949e;text-transform:uppercase;letter-spacing:.5px}}
.back-link{{font-size:12px;color:#58a6ff;text-decoration:none}}
.back-link:hover{{text-decoration:underline}}
.member-list{{flex:1;overflow-y:auto;padding:8px}}
.member-btn{{width:100%;display:flex;align-items:center;gap:10px;padding:10px 12px;background:transparent;border:none;border-radius:6px;cursor:pointer;text-align:left;color:#e6edf3;margin-bottom:2px;transition:background .15s;border-left:3px solid transparent}}
.member-btn:hover{{background:#21262d}}
.member-btn.active{{background:#21262d}}
.mb-icon{{font-size:16px;flex-shrink:0}}
.mb-info{{flex:1;display:flex;flex-direction:column;gap:1px;min-width:0}}
.mb-name{{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}
.mb-role{{font-size:11px;color:#8b949e}}
.mb-port{{font-size:10px;color:#484f58;font-family:monospace;flex-shrink:0}}
/* terminal area */
.term-area{{flex:1;display:flex;flex-direction:column;overflow:hidden}}
.term-topbar{{padding:10px 16px;background:#161b22;border-bottom:1px solid #30363d;display:flex;align-items:center;gap:12px}}
#current-label{{font-size:14px;font-weight:600}}
#current-port{{font-size:12px;color:#8b949e;font-family:monospace}}
.btn-newwin{{margin-left:auto;padding:5px 12px;background:#238636;color:#fff;border:none;border-radius:6px;font-size:12px;font-weight:600;cursor:pointer;text-decoration:none}}
.btn-newwin:hover{{background:#2ea043}}
#term-frame{{flex:1;width:100%;border:none;background:#0d1117}}
</style>
</head><body>
<div class="layout">
  <div class="sidebar">
    <div class="sidebar-header">
      <span class="sidebar-title">팀 터미널</span>
      <a class="back-link" href="/terminals">목록</a>
    </div>
    <div class="member-list">{buttons}</div>
  </div>
  <div class="term-area">
    <div class="term-topbar">
      <span id="current-label">나의 터미널</span>
      <span id="current-port">:7680</span>
      <a id="btn-newwin" class="btn-newwin" href="http://localhost:{first_port}" target="_blank">새 탭에서 열기 ↗</a>
    </div>
    <iframe id="term-frame" src="http://localhost:{first_port}"
      tabindex="0" allowfullscreen
      onload="this.focus()"></iframe>
  </div>
</div>
<script>
const frame = document.getElementById('term-frame');

// iframe 영역 클릭 시 항상 포커스
document.querySelector('.term-area').addEventListener('click', () => frame.focus());

// 포커스 안내 오버레이
const overlay = document.createElement('div');
overlay.id = 'focus-hint';
overlay.textContent = '클릭하면 터미널에 포커스됩니다';
overlay.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#58a6ff;font-size:13px;pointer-events:none;opacity:0;transition:opacity .2s;';
document.querySelector('.term-area').style.position = 'relative';
document.querySelector('.term-area').appendChild(overlay);

document.addEventListener('click', e => {{
  const inTermArea = e.target.closest('.term-area');
  overlay.style.opacity = inTermArea ? '0' : '0.9';
}});

function loadTerminal(port, btn) {{
  document.querySelectorAll('.member-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
  const name = btn.querySelector('.mb-name').textContent;
  document.getElementById('current-label').textContent = name;
  document.getElementById('current-port').textContent = ':' + port;
  document.getElementById('btn-newwin').href = 'http://localhost:' + port;
  frame.src = 'http://localhost:' + port;
  frame.onload = () => frame.focus();
}}
</script>
</body></html>'''
