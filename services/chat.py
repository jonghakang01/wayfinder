import json, os, subprocess
from datetime import datetime

META = {
    "name": "쭌과 대화",
    "path": "/chat",
    "icon": "💬",
    "description": "AI 팀장에게 지시 & 협의",
    "hidden": True,
}

DATA_ROOT = os.path.expanduser("~/.appdata")

SYSTEM_PROMPT = """당신은 쭌입니다. AI 개발팀의 팀장으로, 사용자의 요청을 분석하고 실행 방향을 안내합니다.
- 한국어로 응답
- 간결하고 명확하게
- 개발 요청 시: 무엇을 어떻게 할지 설명하고 실행 의사 표현
- 비개발자가 상대방이므로 쉽게 설명"""


def _history_file(user):
    d = os.path.join(DATA_ROOT, user or "guest")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "chat_history.json")


def load_history(user):
    f = _history_file(user)
    if not os.path.exists(f):
        return []
    try:
        with open(f) as fp:
            return json.load(fp)
    except Exception:
        return []


def save_history(user, history):
    f = _history_file(user)
    with open(f, "w") as fp:
        json.dump(history[-60:], fp, ensure_ascii=False, indent=2)


def call_claude(history, new_message):
    parts = [SYSTEM_PROMPT, ""]
    if history:
        parts.append("이전 대화:")
        for msg in history[-12:]:
            role = "사용자" if msg["role"] == "user" else "쭌"
            parts.append(f"{role}: {msg['content']}")
        parts.append("")
    parts.append(f"사용자: {new_message}")
    parts.append("쭌:")
    prompt = "\n".join(parts)

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=120,
            cwd=os.path.expanduser("~"),
        )
        response = result.stdout.strip()
        if not response:
            response = result.stderr.strip() or "응답을 가져오지 못했습니다."
        return response
    except subprocess.TimeoutExpired:
        return "응답 시간이 초과되었습니다. 다시 시도해 주세요."
    except Exception as e:
        return f"오류: {e}"


def _get(body, key):
    v = body.get(key, "")
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""


def handle(method, path, body, ctx):
    user = ctx.get("user", "guest")

    if method == "GET" and path == "/chat":
        return ("html", render_chat(user))

    if method == "POST" and path == "/chat":
        message = _get(body, "message").strip()
        if not message:
            return ("json", {"error": "메시지를 입력해 주세요."})
        history = load_history(user)
        response = call_claude(history, message)
        history.append({"role": "user", "content": message, "time": datetime.now().isoformat()})
        history.append({"role": "assistant", "content": response, "time": datetime.now().isoformat()})
        save_history(user, history)
        return ("json", {"response": response})

    if method == "POST" and path == "/chat/clear":
        save_history(user, [])
        return ("json", {"ok": True})

    return ("html", "<h2>404</h2>", 404)


def render_chat(user):
    history = load_history(user)
    msgs_html = ""
    for msg in history:
        content = msg["content"].replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("\n", "<br>")
        if msg["role"] == "user":
            msgs_html += f'<div class="msg user"><div class="bubble">{content}</div></div>\n'
        else:
            msgs_html += f'<div class="msg bot"><div class="name">쭌</div><div class="bubble">{content}</div></div>\n'

    empty = '' if msgs_html else '<div class="empty">안녕하세요! 무엇이든 말씀해 주세요.</div>'

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>💬 쭌과 대화</title>
<style>
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:-apple-system,sans-serif;background:#f0f4f8;height:100dvh;display:flex;flex-direction:column}}
nav{{background:#1e293b;padding:12px 20px;display:flex;align-items:center;justify-content:space-between;flex-shrink:0}}
nav .title{{color:white;font-weight:600;font-size:1rem}}
nav a{{color:#94a3b8;text-decoration:none;font-size:0.85rem}}
nav a:hover{{color:white}}
.nav-right{{display:flex;gap:16px;align-items:center}}
.clear-btn{{background:none;border:none;color:#64748b;cursor:pointer;font-size:0.8rem;padding:4px 8px;border-radius:6px}}
.clear-btn:hover{{color:#ef4444;background:#fee2e2}}
.chat{{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:14px}}
.empty{{text-align:center;color:#94a3b8;margin-top:60px;font-size:0.95rem}}
.msg{{display:flex;flex-direction:column;max-width:78%}}
.msg.user{{align-self:flex-end;align-items:flex-end}}
.msg.bot{{align-self:flex-start;align-items:flex-start}}
.name{{font-size:0.75rem;color:#64748b;margin-bottom:4px;padding:0 4px}}
.bubble{{padding:12px 16px;border-radius:16px;font-size:0.95rem;line-height:1.6;word-break:break-word}}
.msg.user .bubble{{background:#0ea5e9;color:white;border-bottom-right-radius:4px}}
.msg.bot .bubble{{background:white;color:#1a1a1a;border:1px solid #e2e8f0;border-bottom-left-radius:4px}}
.thinking .bubble{{color:#94a3b8;font-style:italic}}
.input-area{{padding:14px 16px;background:white;border-top:1px solid #e2e8f0;flex-shrink:0}}
.input-row{{display:flex;gap:10px;align-items:flex-end;max-width:800px;margin:0 auto}}
textarea{{flex:1;padding:11px 14px;border:1.5px solid #e2e8f0;border-radius:12px;font-size:0.95rem;resize:none;outline:none;font-family:inherit;min-height:46px;max-height:120px;line-height:1.5}}
textarea:focus{{border-color:#0ea5e9}}
.send{{padding:0 20px;background:#0ea5e9;color:white;border:none;border-radius:12px;cursor:pointer;font-size:0.95rem;height:46px;white-space:nowrap;font-weight:500}}
.send:disabled{{background:#cbd5e1;cursor:not-allowed}}
</style>
</head>
<body>
<nav>
  <span class="title">💬 쭌과 대화</span>
  <div class="nav-right">
    <button class="clear-btn" onclick="clearChat()">대화 초기화</button>
    <a href="/">← 홈</a>
  </div>
</nav>
<div class="chat" id="chat">
  {empty}{msgs_html}
  <div class="msg bot thinking" id="thinking" style="display:none">
    <div class="name">쭌</div>
    <div class="bubble">생각 중...</div>
  </div>
</div>
<div class="input-area">
  <div class="input-row">
    <textarea id="inp" placeholder="쭌에게 메시지 입력... (Enter: 전송 / Shift+Enter: 줄바꿈)" rows="1"></textarea>
    <button class="send" id="sendBtn" onclick="send()">전송</button>
  </div>
</div>
<script>
const chat = document.getElementById('chat');
const inp = document.getElementById('inp');
const btn = document.getElementById('sendBtn');
const thinking = document.getElementById('thinking');

chat.scrollTop = chat.scrollHeight;
inp.focus();

inp.addEventListener('keydown', e => {{
  if (e.key === 'Enter' && !e.shiftKey) {{ e.preventDefault(); send(); }}
}});
inp.addEventListener('input', () => {{
  inp.style.height = 'auto';
  inp.style.height = Math.min(inp.scrollHeight, 120) + 'px';
}});

function esc(s) {{
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/\\n/g,'<br>');
}}

function addMsg(role, content) {{
  const d = document.createElement('div');
  d.className = 'msg ' + (role === 'user' ? 'user' : 'bot');
  if (role === 'user') {{
    d.innerHTML = '<div class="bubble">' + esc(content) + '</div>';
  }} else {{
    d.innerHTML = '<div class="name">쭌</div><div class="bubble">' + esc(content) + '</div>';
  }}
  chat.insertBefore(d, thinking);
  chat.scrollTop = chat.scrollHeight;
}}

async function send() {{
  const msg = inp.value.trim();
  if (!msg || btn.disabled) return;
  inp.value = ''; inp.style.height = 'auto';
  btn.disabled = true;
  addMsg('user', msg);
  thinking.style.display = 'flex';
  chat.scrollTop = chat.scrollHeight;
  try {{
    const r = await fetch('/chat', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{message: msg}})
    }});
    const d = await r.json();
    thinking.style.display = 'none';
    addMsg('bot', d.response || d.error || '오류가 발생했습니다.');
  }} catch(e) {{
    thinking.style.display = 'none';
    addMsg('bot', '연결 오류가 발생했습니다.');
  }}
  btn.disabled = false;
  inp.focus();
}}

async function clearChat() {{
  if (!confirm('대화 내역을 초기화할까요?')) return;
  await fetch('/chat/clear', {{method:'POST', headers:{{'Content-Type':'application/json'}}, body:'{{}}'}});
  location.reload();
}}
</script>
</body>
</html>'''
