import json, os, subprocess, urllib.request, urllib.error, re
from urllib.parse import parse_qs

LAB_DIR = os.path.expanduser("~/labs/pov-news")
PROMPT_FILE = os.path.join(LAB_DIR, "pov_analysis_prompt.md")
SCHEMA_FILE = os.path.join(LAB_DIR, "pov_schema.json")
EXAMPLE_FILE = os.path.join(LAB_DIR, "pov_example_thiel.json")

META = {
    "name": "POV News",
    "path": "/pov",
    "icon": "🗞",
    "description": "뉴스를 다양한 관점으로 분석",
}

DEFAULT_POVS = [
    {"id": "thiel",   "name": "Peter Thiel",    "desc": "Tech contrarian, PayPal co-founder"},
    {"id": "altman",  "name": "Sam Altman",      "desc": "OpenAI CEO, effective altruist"},
    {"id": "musk",    "name": "Elon Musk",       "desc": "Tesla/SpaceX/X CEO"},
    {"id": "ycomb",   "name": "YC Partner",      "desc": "Startup investor perspective"},
    {"id": "custom",  "name": "Custom",          "desc": "직접 입력"},
]

_DEFAULT_PROMPT = (
    "You are analyzing a news article from the perspective of {persona}.\n"
    "Provide a structured analysis including:\n"
    "1. Initial reaction and overall take\n"
    "2. Key concerns or risks identified\n"
    "3. Opportunities or positives seen\n"
    "4. What {persona} would likely do or say about this\n"
    "5. A memorable one-liner quote {persona} might say\n\n"
    "Be direct and opinionated in the style of {persona}. Write in English.\n\n"
    "Article:\n{article}"
)


def _load_prompt():
    if os.path.exists(PROMPT_FILE):
        try:
            with open(PROMPT_FILE) as f:
                return f.read()
        except Exception:
            pass
    return _DEFAULT_PROMPT


def _load_schema():
    if os.path.exists(SCHEMA_FILE):
        try:
            with open(SCHEMA_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _load_example():
    if os.path.exists(EXAMPLE_FILE):
        try:
            with open(EXAMPLE_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def _fetch_url(url):
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; Wayfinder/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            html = r.read().decode("utf-8", errors="replace")
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"\s+", " ", text).strip()
        return text[:10000]
    except urllib.error.URLError as e:
        return f"URL fetch error: {e}"
    except Exception as e:
        return f"Error: {e}"


def _resolve_persona(persona_id, custom=""):
    if persona_id == "custom":
        return custom.strip() or "a thoughtful observer"
    return next((p["name"] for p in DEFAULT_POVS if p["id"] == persona_id), persona_id)


def _run_analysis(article_text, persona_name):
    template = _load_prompt()
    if "{persona}" in template or "{article}" in template:
        prompt = (
            template
            .replace("{persona}", persona_name)
            .replace("{article}", article_text[:6000])
        )
    else:
        prompt = f"{template}\n\nPersona: {persona_name}\n\nArticle:\n{article_text[:6000]}"

    try:
        result = subprocess.run(
            ["claude", "-p", prompt],
            capture_output=True, text=True, timeout=120,
            cwd=os.path.expanduser("~"),
        )
        output = result.stdout.strip()
        if not output:
            output = result.stderr.strip() or "분석 결과가 없습니다."
        return output
    except subprocess.TimeoutExpired:
        return "분석 시간이 초과되었습니다 (120초). 다시 시도해 주세요."
    except FileNotFoundError:
        return "claude CLI를 찾을 수 없습니다."
    except Exception as e:
        return f"오류: {e}"


def _get(body, key):
    v = body.get(key, "")
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""


# Inlined APP_TAB_CSS for bottom navigation (matches server.py definition)
_TAB_CSS = """<style>
.app-tabs{position:fixed!important;bottom:0!important;left:0;right:0;background:rgba(8,13,20,0.97);backdrop-filter:blur(20px);border-top:1px solid rgba(255,255,255,0.06);display:flex!important;justify-content:stretch;z-index:200;padding:8px 8px calc(8px + env(safe-area-inset-bottom,0));gap:4px}
.app-tab{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;padding:8px 4px;color:rgba(100,116,139,0.8);text-decoration:none;font-size:0.6rem;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;border-radius:12px;transition:all 0.2s}
.app-tab:hover{color:rgba(255,255,255,0.7);background:rgba(255,255,255,0.04)}
.app-tab.active{color:#38bdf8;background:rgba(56,189,248,0.12)}
.app-tab-icon{font-size:1.3rem;line-height:1;transition:transform 0.2s}
.app-tab.active .app-tab-icon{filter:drop-shadow(0 0 8px rgba(56,189,248,0.7));transform:translateY(-2px)}
body{padding-bottom:calc(72px + env(safe-area-inset-bottom,0px))!important}
</style>"""

_TABS = [
    ("/todo",      "✅", "Tasks"),
    ("/habit",     "🏃", "Habits"),
    ("/dashboard", "📊", "Overview"),
    ("/pov",       "🗞", "POV"),
]


def _nav_tabs(active):
    html = _TAB_CSS + '<nav class="app-tabs">'
    for path, icon, label in _TABS:
        cls = "app-tab active" if active == path else "app-tab"
        html += f'<a href="{path}" class="{cls}"><span class="app-tab-icon">{icon}</span>{label}</a>'
    html += "</nav>"
    return html


def _page(user, url="", persona="thiel", analysis="", error=""):
    options = "".join(
        f'<option value="{p["id"]}" {"selected" if p["id"] == persona else ""}>'
        f'{p["name"]} — {p["desc"]}</option>'
        for p in DEFAULT_POVS
    )
    analysis_html = ""
    if analysis:
        safe = analysis.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        analysis_html = f"""
<div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:24px;margin-top:24px">
  <div style="font-size:.75rem;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px">분석 결과</div>
  <div style="white-space:pre-wrap;line-height:1.75;color:var(--text);font-size:.92rem">{safe}</div>
</div>"""

    error_html = ""
    if error:
        safe_err = error.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        error_html = f'<div style="padding:12px 16px;border-radius:var(--radius-md);background:rgba(248,113,113,0.1);border:1px solid rgba(248,113,113,0.3);color:var(--danger);margin-bottom:16px">{safe_err}</div>'

    return f"""<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🗞 POV News</title>
<link rel="stylesheet" href="/static/style.css">
</head><body>
<nav>
  <a href="/" class="nav-back">← Wayfinder</a>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container">
  <h1>🗞 POV News</h1>
  <p style="color:var(--text-muted);margin-bottom:28px;font-size:.9rem">뉴스 기사를 특정 인물의 관점으로 분석합니다</p>

  {error_html}

  <div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:24px">
    <form id="pov-form" style="display:flex;flex-direction:column;gap:12px">
      <div>
        <label style="font-size:.78rem;font-weight:600;color:var(--text-muted);display:block;margin-bottom:6px">뉴스 기사 URL</label>
        <input type="url" id="url-input" name="url" value="{url}" placeholder="https://..."
          style="width:100%;padding:10px 14px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--surface-2);color:var(--text);font-size:.92rem" required>
      </div>
      <div>
        <label style="font-size:.78rem;font-weight:600;color:var(--text-muted);display:block;margin-bottom:6px">관점 (Perspective)</label>
        <select id="persona-select" name="persona"
          style="width:100%;padding:10px 14px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--surface-2);color:var(--text)">
          {options}
        </select>
      </div>
      <div id="custom-wrap" style="display:none">
        <label style="font-size:.78rem;font-weight:600;color:var(--text-muted);display:block;margin-bottom:6px">커스텀 관점 입력</label>
        <input type="text" id="custom-persona" name="custom_persona" placeholder="예: Warren Buffett"
          style="width:100%;padding:10px 14px;border:1px solid var(--border);border-radius:var(--radius-md);background:var(--surface-2);color:var(--text)">
      </div>
      <button type="submit" class="btn btn-primary btn-lg" id="submit-btn" style="margin-top:4px">분석하기</button>
    </form>
  </div>

  {analysis_html}
</div>

{_nav_tabs("/pov")}

<script>
const sel = document.getElementById('persona-select');
const wrap = document.getElementById('custom-wrap');
sel.addEventListener('change', () => {{
  wrap.style.display = sel.value === 'custom' ? 'block' : 'none';
}});
if (sel.value === 'custom') wrap.style.display = 'block';

document.getElementById('pov-form').addEventListener('submit', async (e) => {{
  e.preventDefault();
  const btn = document.getElementById('submit-btn');
  btn.disabled = true;
  btn.textContent = '분석 중... (최대 2분)';
  const payload = {{
    url: document.getElementById('url-input').value,
    persona: sel.value,
    custom_persona: document.getElementById('custom-persona').value,
  }};
  try {{
    const res = await fetch('/pov/analyze', {{
      method: 'POST',
      headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify(payload),
    }});
    const data = await res.json();
    if (data.error) {{
      alert('오류: ' + data.error);
    }} else {{
      const analysisEl = document.querySelector('.container');
      let el = document.getElementById('analysis-result');
      if (!el) {{
        el = document.createElement('div');
        el.id = 'analysis-result';
        el.style.cssText = 'background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:24px;margin-top:24px';
        analysisEl.appendChild(el);
      }}
      const safe = data.analysis.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
      el.innerHTML = '<div style="font-size:.75rem;font-weight:700;color:var(--accent);text-transform:uppercase;letter-spacing:.08em;margin-bottom:12px">분석 결과</div>' +
        '<div style="white-space:pre-wrap;line-height:1.75;color:var(--text);font-size:.92rem">' + safe + '</div>';
      el.scrollIntoView({{behavior:'smooth'}});
    }}
  }} catch(err) {{
    alert('요청 실패: ' + err.message);
  }} finally {{
    btn.disabled = false;
    btn.textContent = '분석하기';
  }}
}});
</script>
</body></html>"""


def handle(method, path, body, ctx):
    user = ctx.get("user")
    if not user:
        return ("redirect", "/login")

    if method == "GET":
        if path == "/pov/fetch":
            url = _get(body, "url")
            if not url:
                return ("json", {"error": "url parameter required"})
            text = _fetch_url(url)
            return ("json", {"text": text[:4000], "length": len(text), "truncated": len(text) >= 10000})

        # GET /pov — main page
        url = _get(body, "url")
        persona = _get(body, "persona") or "thiel"
        return ("html", _page(user, url=url, persona=persona))

    if method == "POST" and path == "/pov/analyze":
        if isinstance(body, dict) and "__raw__" not in body:
            url = body.get("url", "")
            if isinstance(url, list):
                url = url[0] if url else ""
            persona = body.get("persona", "thiel")
            if isinstance(persona, list):
                persona = persona[0] if persona else "thiel"
            custom = body.get("custom_persona", "")
            if isinstance(custom, list):
                custom = custom[0] if custom else ""
        else:
            return ("json", {"error": "Invalid request"})

        if not url:
            return ("json", {"error": "URL이 필요합니다."})

        article = _fetch_url(url)
        if article.startswith(("URL fetch error", "Error")):
            return ("json", {"error": article})

        persona_name = _resolve_persona(persona, custom)
        analysis = _run_analysis(article, persona_name)
        return ("json", {"analysis": analysis, "persona": persona_name, "url": url})

    return ("html", "<h2>404</h2>", 404)
