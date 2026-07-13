"""POV News — 'What does it mean to me?' (WDIMTM).

Replaces the old persona-based POV service. Produces structured discernment:
- fact_check (verified_core / overstated / disputed)
- framing_spectrum
- relevance (5 layers)

Data (collected by the batch pipeline) lives in ~/.appdata/pov/.
Reference prompt/schema/example live in services/pov_assets/.
"""

import html
import json
import os
import pathlib
import re
import traceback
import urllib.parse
import urllib.request
import uuid
from html.parser import HTMLParser

META = {
    "name": "POV News",
    "path": "/pov",
    "icon": "🗞",
    "description": "뉴스를 사실·프레이밍·나와의 관련도로 분석",
}

ASSETS_DIR = pathlib.Path(__file__).parent / "pov_assets"
DATA_DIR = pathlib.Path.home() / ".appdata" / "pov"
RESULTS_FILE = DATA_DIR / "pov_results.json"

ANALYSIS_MODEL = "claude-sonnet-4-6"


# ─── Analysis core ───────────────────────────────────────────────────────────

def load_assets():
    prompt = (ASSETS_DIR / "pov_analysis_prompt.md").read_text()
    schema = json.loads((ASSETS_DIR / "pov_schema.json").read_text())
    example = json.loads((ASSETS_DIR / "pov_example_thiel.json").read_text())
    return prompt, schema, example


def validate_pov(data, schema):
    for field in schema.get("required", []):
        if field not in data:
            raise ValueError(f"Missing required field: {field}")
    fc = data.get("fact_check", {})
    for sub in ["verified_core", "overstated", "disputed"]:
        if sub not in fc:
            raise ValueError(f"Missing fact_check.{sub}")
    rel = data.get("relevance", {})
    for sub in ["direct_score", "score_rationale", "layers"]:
        if sub not in rel:
            raise ValueError(f"Missing relevance.{sub}")
    layers = rel.get("layers", {})
    for layer in ["direct_impact", "second_order", "values_identity", "good_to_know", "horizon"]:
        if layer not in layers:
            raise ValueError(f"Missing relevance.layers.{layer}")


def analyze_pov(user_input: dict, output_language: str) -> dict:
    """Run one WDIMTM analysis call. Grounds only in provided articles."""
    import anthropic

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set")

    prompt_template, schema, example = load_assets()
    system_prompt = prompt_template.replace("{{output_language}}", output_language)

    client = anthropic.Anthropic(api_key=api_key)
    messages = [
        {"role": "user", "content": json.dumps(example["input"], ensure_ascii=False)},
        {"role": "assistant", "content": json.dumps(example["expected_output"], ensure_ascii=False)},
        {"role": "user", "content": json.dumps(user_input, ensure_ascii=False)},
    ]

    response = client.messages.create(
        model=ANALYSIS_MODEL,
        max_tokens=4000,
        system=system_prompt,
        messages=messages,
    )

    text = response.content[0].text.strip()
    text = re.sub(r"^```(?:json)?\s*\n?", "", text)
    text = re.sub(r"\n?```\s*$", "", text)

    result = json.loads(text)
    validate_pov(result, schema)
    return result


# ─── URL meta fetch (metadata + snippet only) ────────────────────────────────

class _MetaParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.og_title = ""
        self.og_desc = ""
        self._title_buf = []
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if tag == "meta":
            prop = a.get("property", "") or a.get("name", "")
            content = a.get("content", "")
            if prop == "og:title" and not self.og_title:
                self.og_title = content
            elif prop in ("og:description", "description") and not self.og_desc:
                self.og_desc = content
        elif tag == "title":
            self._in_title = True

    def handle_data(self, data):
        if self._in_title:
            self._title_buf.append(data)

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False

    @property
    def title(self):
        return self.og_title or "".join(self._title_buf).strip()


def fetch_url_meta(url: str) -> dict:
    """Fetch og:title + og:description only. Returns partial result on failure."""
    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0 (compatible; POVNewsBot/1.0)"},
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            charset = resp.headers.get_content_charset() or "utf-8"
            raw = resp.read(65536)
        parser = _MetaParser()
        parser.feed(raw.decode(charset, errors="replace"))
        return {
            "url": url,
            "title": parser.title[:200] or url,
            "snippet": parser.og_desc[:400],
            "ok": True,
        }
    except Exception as e:
        return {"url": url, "title": url, "snippet": "", "ok": False, "error": str(e)}


# ─── Card rendering ──────────────────────────────────────────────────────────

def _s(v) -> str:
    if isinstance(v, list):
        return " ".join(str(x) for x in v)
    return str(v) if v is not None else ""


def lean_badge(lean: str) -> str:
    colors = {
        "neutral": "#6b7280", "corrective": "#3b82f6", "sensational": "#ef4444",
        "left": "#8b5cf6", "right": "#f97316", "mixed": "#f59e0b",
    }
    color = colors.get(lean.lower(), "#6b7280")
    return f'<span class="badge" style="background:{color}">{html.escape(lean)}</span>'


def confidence_badge(level: str) -> str:
    colors = {"high": "var(--success)", "medium": "var(--warn)", "low": "var(--danger)"}
    color = colors.get(level, "var(--text-dim)")
    return f'<span class="badge" style="background:{color}">{html.escape(level)}</span>'


def score_gauge(score: int) -> str:
    pct = score * 10
    color = "var(--success)" if score >= 7 else "var(--warn)" if score >= 4 else "var(--text-dim)"
    return (
        f'<div class="gauge-wrap">'
        f'<div class="gauge-bar"><div class="gauge-fill" style="width:{pct}%;background:{color}"></div></div>'
        f'<span class="gauge-label">{score}/10</span>'
        f"</div>"
    )


def render_who_what(items: list) -> str:
    rows = "".join(
        f'<tr><td class="ww-name">{html.escape(_s(i.get("name", "")))}</td>'
        f'<td>{html.escape(_s(i.get("one_line", "")))}</td></tr>'
        for i in items
    )
    return f'<table class="ww-table">{rows}</table>'


def render_fact_check(fc: dict) -> str:
    parts = []
    if fc.get("verified_core"):
        items = "".join(
            f'<li><span class="badge badge-green">✓ verified</span> '
            f'{html.escape(_s(c.get("claim", "")))}'
            + (f'<span class="src"> [{", ".join(str(s) for s in c["sources"])}]</span>' if c.get("sources") else "")
            + (f'<span class="origin"> · {html.escape(_s(c["primary_origin"]))}</span>' if c.get("primary_origin") else "")
            + "</li>"
            for c in fc["verified_core"]
        )
        parts.append(f'<ul class="fact-list">{items}</ul>')
    if fc.get("overstated"):
        items = "".join(
            f'<li><span class="badge badge-yellow">⚠ overstated</span> '
            f'<em>{html.escape(_s(c.get("headline_claim", "")))}</em>'
            f' → {html.escape(_s(c.get("what_sources_support", "")))}</li>'
            for c in fc["overstated"]
        )
        parts.append(f'<ul class="fact-list">{items}</ul>')
    if fc.get("disputed"):
        status_colors = {"denied": "var(--danger)", "uncorroborated": "var(--warn)", "contested": "#f97316"}
        items = "".join(
            f'<li><span class="badge" style="background:{status_colors.get(c.get("status"), "var(--text-dim)")}">'
            f'{html.escape(_s(c.get("status", "")))}</span> {html.escape(_s(c.get("claim", "")))}</li>'
            for c in fc["disputed"]
        )
        parts.append(f'<ul class="fact-list">{items}</ul>')
    return "".join(parts) or "<p class='empty'>No fact-check data.</p>"


def render_framing(framing: dict) -> str:
    positions = "".join(
        f'<div class="position-item">'
        f'<span class="pos-idx">[{p.get("source_index", "")}]</span>'
        f'{lean_badge(_s(p.get("lean", "")))}'
        f'<span>{html.escape(_s(p.get("spin", "")))}</span>'
        f"</div>"
        for p in framing.get("positions", [])
    )
    return (
        f'<p class="shared-facts">{html.escape(_s(framing.get("shared_facts", "")))}</p>'
        f'<div class="positions">{positions}</div>'
    )


def render_relevance(rel: dict) -> str:
    score = rel.get("direct_score", 0)
    layers = rel.get("layers", {})
    layer_defs = [
        ("direct_impact", "Direct Impact"),
        ("second_order", "Second Order"),
        ("values_identity", "Values & Identity"),
        ("good_to_know", "Good to Know"),
        ("horizon", "Horizon"),
    ]
    layer_html = ""
    for key, label in layer_defs:
        layer = layers.get(key, {})
        applies = layer.get("applies")
        note = layer.get("note", "")
        outside = layer.get("outside_profile", False)
        badges = ""
        if applies is True:
            badges += '<span class="badge badge-green">applies</span>'
        elif applies is False:
            badges += '<span class="badge badge-gray">skip</span>'
        if outside:
            badges += '<span class="badge badge-purple">outside profile</span>'
        layer_html += (
            f'<div class="layer-item">'
            f'<div class="layer-header">{label} {badges}</div>'
            f'<div class="layer-note">{html.escape(_s(note))}</div>'
            f"</div>"
        )
    return (
        f'<div class="score-row">'
        f'{score_gauge(score)}'
        f'<span class="score-rationale">{html.escape(_s(rel.get("score_rationale", "")))}</span>'
        f"</div>"
        f'<div class="layers">{layer_html}</div>'
    )


def render_pov_card(pov: dict) -> str:
    return f"""
<div class="pov-card">
  <div class="card-header">
    <div class="event-id">{html.escape(_s(pov.get("event_id", "")))}</div>
    <p class="event-summary">{html.escape(_s(pov.get("event_summary", "")))}</p>
    {render_who_what(pov.get("who_what", []))}
  </div>
  <details open>
    <summary>Fact Check</summary>
    <div class="section-body">{render_fact_check(pov.get("fact_check", {}))}</div>
  </details>
  <details open>
    <summary>Framing Spectrum</summary>
    <div class="section-body">{render_framing(pov.get("framing_spectrum", {}))}</div>
  </details>
  <details open>
    <summary>Relevance to You</summary>
    <div class="section-body">{render_relevance(pov.get("relevance", {}))}</div>
  </details>
  <details>
    <summary>Meta</summary>
    <div class="section-body">
      <div class="meta-row">
        <span>Confidence</span>{confidence_badge(pov.get("confidence", ""))}
      </div>
      <p class="coverage-gaps">{html.escape(_s(pov.get("coverage_gaps", "")))}</p>
    </div>
  </details>
</div>"""


# ─── Data loading ────────────────────────────────────────────────────────────

def load_pov_results() -> dict:
    if not RESULTS_FILE.exists():
        return {}
    try:
        return json.loads(RESULTS_FILE.read_text())
    except Exception:
        return {}


def _fmt_time(iso: str) -> str:
    if not iso:
        return "—"
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        return dt.strftime("%Y-%m-%d %H:%M UTC")
    except Exception:
        return iso[:19]


# ─── Shared page chrome ──────────────────────────────────────────────────────

PAGE_CSS = """
.container { max-width: 680px; margin: 0 auto; padding: 1.5rem 1rem 6rem; }
.topbar { display: flex; align-items: center; justify-content: space-between; margin-bottom: 1.25rem; font-size: 0.8rem; }
.topbar a { color: var(--accent); text-decoration: none; }
.topbar .nav-user { color: var(--text-muted); }
.app-header { margin-bottom: 1.5rem; }
h1 { font-size: 1.5rem; font-weight: 700; color: var(--text); }
.subtitle { color: var(--text-muted); font-size: 0.8rem; margin-top: 0.2rem; }
.nav-links { display: flex; gap: 1.5rem; margin-bottom: 1.5rem; }
.nav-links a { color: var(--accent); font-size: 0.82rem; font-weight: 600; text-decoration: none; border-bottom: 1px solid transparent; padding-bottom: 0.1rem; }
.nav-links a:hover { border-bottom-color: var(--accent); }
.nav-links a.active { color: var(--accent); border-bottom-color: var(--accent); }
.badge { display: inline-block; font-size: 0.68rem; font-weight: 600; padding: 0.15rem 0.45rem; border-radius: 4px; color: #fff; vertical-align: middle; }
.badge-green { background: var(--success); } .badge-yellow { background: var(--warn); } .badge-gray { background: var(--text-dim); } .badge-purple { background: var(--info); }
.gauge-wrap { display: flex; align-items: center; gap: 0.5rem; flex-shrink: 0; padding-top: 0.1rem; }
.gauge-bar { width: 100px; height: 5px; background: var(--surface-3); border-radius: 3px; overflow: hidden; }
.gauge-fill { height: 100%; border-radius: 3px; }
.gauge-label { font-size: 0.9rem; font-weight: 700; color: var(--text); }
.pov-card { margin-top: 0; }
.card-header { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; margin-bottom: 0.75rem; }
.event-id { font-size: 0.7rem; color: var(--text-dim); font-family: monospace; margin-bottom: 0.5rem; }
.event-summary { font-size: 1rem; line-height: 1.65; color: var(--text); margin-bottom: 0.875rem; }
.ww-table { width: 100%; border-collapse: collapse; font-size: 0.8rem; }
.ww-table tr + tr td { border-top: 1px solid var(--border); }
.ww-table td { padding: 0.4rem 0.25rem; color: var(--text-muted); }
.ww-name { font-weight: 600; color: var(--accent); width: 28%; padding-right: 0.75rem; }
details { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; margin-bottom: 0.75rem; overflow: hidden; }
summary { padding: 0.875rem 1.25rem; font-size: 0.8rem; font-weight: 600; color: var(--text-muted); cursor: pointer; user-select: none; display: flex; align-items: center; gap: 0.5rem; list-style: none; }
summary::-webkit-details-marker { display: none; }
summary::before { content: "▶"; font-size: 0.55rem; transition: transform 0.15s; color: var(--text-dim); }
details[open] summary::before { transform: rotate(90deg); }
details[open] summary { color: var(--text); }
.section-body { padding: 0 1.25rem 1rem; }
.fact-list { list-style: none; display: flex; flex-direction: column; gap: 0.7rem; }
.fact-list li { font-size: 0.82rem; color: var(--text-muted); line-height: 1.55; }
.src { color: var(--text-dim); font-family: monospace; font-size: 0.72rem; }
.origin { color: var(--accent); font-size: 0.72rem; }
.fact-list em { color: var(--warn); font-style: normal; }
.empty { color: var(--text-dim); font-size: 0.8rem; }
.shared-facts { font-size: 0.82rem; color: var(--text-muted); font-style: italic; margin-bottom: 0.75rem; line-height: 1.55; border-left: 2px solid var(--border); padding-left: 0.75rem; }
.positions { display: flex; flex-direction: column; gap: 0.6rem; }
.position-item { font-size: 0.82rem; color: var(--text-muted); display: flex; align-items: baseline; gap: 0.4rem; flex-wrap: wrap; line-height: 1.5; }
.pos-idx { color: var(--text-dim); font-family: monospace; font-size: 0.72rem; }
.score-row { display: flex; align-items: flex-start; gap: 1rem; margin-bottom: 1rem; flex-wrap: wrap; }
.score-rationale { font-size: 0.8rem; color: var(--text-muted); flex: 1; min-width: 180px; line-height: 1.55; }
.layers { display: flex; flex-direction: column; gap: 0.4rem; }
.layer-item { background: var(--surface-2); border-radius: 8px; padding: 0.6rem 0.75rem; }
.layer-header { font-size: 0.72rem; font-weight: 600; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.3rem; display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; }
.layer-note { font-size: 0.8rem; color: var(--text-muted); line-height: 1.5; }
.meta-row { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.75rem; font-size: 0.8rem; color: var(--text-muted); }
.coverage-gaps { font-size: 0.8rem; color: var(--text-muted); line-height: 1.55; }
"""

FEED_CSS = """
.feed-header { margin-bottom: 1.5rem; display: flex; align-items: baseline; justify-content: space-between; flex-wrap: wrap; gap: 0.5rem; }
.feed-meta { font-size: 0.72rem; color: var(--text-dim); }
.feed-grid { display: flex; flex-direction: column; gap: 0.75rem; }
.feed-card { display: block; text-decoration: none; color: inherit; }
.feed-card-inner { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1rem 1.25rem; transition: border-color 0.15s; }
.feed-card:hover .feed-card-inner { border-color: var(--accent); }
.feed-label { font-size: 0.72rem; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 0.4rem; }
.feed-summary { font-size: 0.9rem; color: var(--text); line-height: 1.55; margin-bottom: 0.75rem; }
.feed-footer { display: flex; align-items: center; gap: 0.75rem; }
.empty-feed { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 2rem; text-align: center; color: var(--text-muted); font-size: 0.875rem; line-height: 1.7; }
.empty-feed pre { color: var(--accent); margin-top: 0.5rem; }
"""


def _topbar(user: str) -> str:
    return (
        f'<div class="topbar">'
        f'<a href="/" class="nav-back">← Wayfinder</a>'
        f'<span class="nav-user">👤 {html.escape(user)} · <a href="/logout">Logout</a></span>'
        f"</div>"
    )


def _bottom_tabs(user=None) -> str:
    try:
        from server import app_tabs
        return app_tabs("/pov", user)
    except Exception:
        return ""


# ─── Feed + detail pages ─────────────────────────────────────────────────────

def render_feed_card(pov: dict) -> str:
    score = pov.get("relevance", {}).get("direct_score", 0)
    label = html.escape(_s(pov.get("_event_label") or pov.get("event_summary", "")))
    summary = html.escape(_s(pov.get("event_summary", "")))
    eid_enc = urllib.parse.quote(pov.get("event_id", ""))
    return f"""
<a class="feed-card" href="/pov/feed/{eid_enc}">
  <div class="feed-card-inner">
    <div class="feed-label">{label[:100]}</div>
    <p class="feed-summary">{summary[:200]}</p>
    <div class="feed-footer">{score_gauge(score)}</div>
  </div>
</a>"""


def build_feed_html(user: str, data: dict) -> str:
    results = data.get("results", [])
    collected_at = _fmt_time(data.get("collected_at", "") or data.get("analyzed_at", ""))

    if results:
        cards = "".join(render_feed_card(r) for r in results)
        feed_body = f'<div class="feed-grid">{cards}</div>'
    else:
        feed_body = """<div class="empty-feed">
          <p>피드가 비어 있습니다.</p>
          <p style="margin-top:0.5rem;">파이프라인을 실행해서 뉴스를 수집하세요:</p>
          <pre>bash scripts/pov-pipeline.sh</pre>
        </div>"""

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/style.css">
<title>POV News — 피드</title>
<style>{PAGE_CSS}{FEED_CSS}</style>
</head>
<body>
<div class="container">
  {_topbar(user)}
  <div class="app-header">
    <h1>🗞 POV News</h1>
    <p class="subtitle">이 뉴스가 나에게 무슨 의미인가?</p>
  </div>
  <div class="nav-links">
    <a href="/pov/feed" class="active">피드</a>
    <a href="/pov">수동 분석</a>
  </div>
  <div class="feed-header">
    <span style="font-size:0.8rem;font-weight:600;color:#64748b;">{len(results)}개 이벤트</span>
    <span class="feed-meta">마지막 수집: {collected_at}</span>
  </div>
  {feed_body}
</div>
{_bottom_tabs(user)}
</body>
</html>"""


def build_detail_html(user: str, pov: dict) -> str:
    card = render_pov_card(pov)
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/style.css">
<title>POV News — {html.escape(_s(pov.get('event_summary',''))[:60])}</title>
<style>{PAGE_CSS}</style>
</head>
<body>
<div class="container">
  {_topbar(user)}
  <div class="app-header">
    <h1>🗞 POV News</h1>
    <p class="subtitle">이 뉴스가 나에게 무슨 의미인가?</p>
  </div>
  <div class="nav-links">
    <a href="/pov/feed">← 피드로</a>
    <a href="/pov">수동 분석</a>
  </div>
  {card}
</div>
{_bottom_tabs(user)}
</body>
</html>"""


# ─── Main (manual analysis) page ─────────────────────────────────────────────

def build_main_html(user: str) -> str:
    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="stylesheet" href="/static/style.css">
<title>POV News — 수동 분석</title>
<style>{PAGE_CSS}{MANUAL_CSS}</style>
</head>
<body>
<div class="container">
  {_topbar(user)}
  <div class="app-header">
    <h1>🗞 POV News</h1>
    <p class="subtitle">이 뉴스가 나에게 무슨 의미인가?</p>
  </div>
  <div class="nav-links">
    <a href="/pov/feed">피드</a>
    <a href="/pov" class="active">수동 분석</a>
  </div>

  <div class="section-card">
    <div class="section-title">My Profile <span class="saved-badge" id="profileSavedBadge" style="display:none">saved</span></div>
    <div class="field-row">
      <div class="field"><label>Location</label><input type="text" id="profileLocation" placeholder="e.g. Seoul, Korea"></div>
      <div class="field"><label>Occupation</label><input type="text" id="profileOccupation" placeholder="e.g. Software Engineer"></div>
    </div>
    <div class="field-row single">
      <div class="field"><label>Wealth Stage</label>
        <select id="profileWealth">
          <option value="student">Student</option>
          <option value="salaried professional" selected>Salaried Professional</option>
          <option value="self-employed">Self-Employed</option>
          <option value="high net worth">High Net Worth</option>
          <option value="other">Other</option>
        </select>
      </div>
    </div>
    <div class="field-row single">
      <div class="field"><label>Interests (Enter to add)</label>
        <div class="tag-wrap" id="tagWrap" onclick="document.getElementById('tagInput').focus()">
          <input class="tag-input" id="tagInput" placeholder="Add interest..." autocomplete="off">
        </div>
      </div>
    </div>
    <div class="profile-actions"><button class="btn-save" onclick="saveProfile()">Save Profile</button></div>
  </div>

  <div class="section-card">
    <div class="section-title">News Articles</div>
    <div class="tabs">
      <div class="tab active" onclick="switchTab('url')">URL Paste</div>
      <div class="tab" onclick="switchTab('text')">Direct Text</div>
    </div>
    <div class="tab-panel active" id="tab-url">
      <textarea id="urlInput" placeholder="기사 URL을 한 줄에 하나씩, 최대 5개:&#10;https://example.com/article-1&#10;https://example.com/article-2" rows="5"></textarea>
      <div class="url-previews" id="urlPreviews"></div>
    </div>
    <div class="tab-panel" id="tab-text">
      <textarea id="textInput" placeholder="기사 본문을 붙여넣으세요..." rows="8"></textarea>
      <div class="source-row">
        <div class="field"><label>Source Name</label><input type="text" id="textSource" placeholder="e.g. Reuters"></div>
        <div class="field"><label>Headline (optional)</label><input type="text" id="textHeadline" placeholder="Article headline"></div>
      </div>
    </div>
  </div>

  <div class="section-card" style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:0.75rem;">
    <div>
      <div class="section-title" style="margin-bottom:0.5rem;">Output Language</div>
      <div class="lang-toggle">
        <button class="lang-btn" onclick="setLang('en', this)">English</button>
        <button class="lang-btn active" onclick="setLang('ko', this)">한국어</button>
      </div>
    </div>
  </div>

  <div class="analyze-wrap">
    <button class="btn-analyze" id="analyzeBtn" onclick="analyze()">Analyze</button>
    <div class="loading-msg" id="loadingMsg"><span class="spinner-icon">⟳</span> Claude로 분석 중...</div>
  </div>

  <div id="errorBox"></div>
  <div id="result"></div>
</div>
{_bottom_tabs(user)}

<script>
let interests = [];
let outputLang = 'ko';
let activeTab = 'url';

function loadProfile() {{
  try {{
    const saved = JSON.parse(localStorage.getItem('pov_profile') || 'null');
    if (!saved) return;
    document.getElementById('profileLocation').value = saved.location || '';
    document.getElementById('profileOccupation').value = saved.occupation || '';
    document.getElementById('profileWealth').value = saved.wealth_stage || 'salaried professional';
    interests = saved.interests || [];
    renderTags();
    document.getElementById('profileSavedBadge').style.display = 'inline';
  }} catch(e) {{}}
}}
function saveProfile() {{
  const profile = buildProfile();
  if (!profile) return;
  localStorage.setItem('pov_profile', JSON.stringify(profile));
  document.getElementById('profileSavedBadge').style.display = 'inline';
}}
function buildProfile() {{
  const loc = document.getElementById('profileLocation').value.trim();
  const occ = document.getElementById('profileOccupation').value.trim();
  if (!loc && !occ && interests.length === 0) {{ showError('프로필을 최소 한 항목 이상 입력하세요.'); return null; }}
  return {{ location: loc, occupation: occ, wealth_stage: document.getElementById('profileWealth').value, interests }};
}}
function renderTags() {{
  const wrap = document.getElementById('tagWrap');
  const inp = document.getElementById('tagInput');
  wrap.querySelectorAll('.tag').forEach(el => el.remove());
  interests.forEach((tag, i) => {{
    const span = document.createElement('span');
    span.className = 'tag';
    span.innerHTML = escHtml(tag) + ' <span class="tag-x" onclick="removeTag(' + i + ')">×</span>';
    wrap.insertBefore(span, inp);
  }});
}}
function removeTag(i) {{ interests.splice(i, 1); renderTags(); }}
document.getElementById('tagInput').addEventListener('keydown', e => {{
  if (e.key === 'Enter' || e.key === ',') {{
    e.preventDefault();
    const val = e.target.value.trim().replace(/,$/, '');
    if (val && !interests.includes(val)) {{ interests.push(val); renderTags(); }}
    e.target.value = '';
  }} else if (e.key === 'Backspace' && e.target.value === '' && interests.length > 0) {{
    interests.pop(); renderTags();
  }}
}});
function switchTab(tab) {{
  activeTab = tab;
  document.querySelectorAll('.tab').forEach((el, i) => {{
    el.classList.toggle('active', (i === 0 && tab === 'url') || (i === 1 && tab === 'text'));
  }});
  document.getElementById('tab-url').classList.toggle('active', tab === 'url');
  document.getElementById('tab-text').classList.toggle('active', tab === 'text');
}}
function setLang(lang, btn) {{
  outputLang = lang;
  document.querySelectorAll('.lang-btn').forEach(b => b.classList.remove('active'));
  btn.classList.add('active');
}}
async function fetchOneMeta(url) {{
  const res = await fetch('/pov/fetch?url=' + encodeURIComponent(url));
  return await res.json();
}}
async function analyze() {{
  const btn = document.getElementById('analyzeBtn');
  const loadingMsg = document.getElementById('loadingMsg');
  const resultDiv = document.getElementById('result');
  const previewDiv = document.getElementById('urlPreviews');
  clearError();
  resultDiv.innerHTML = '';
  const profile = buildProfile();
  if (!profile) return;
  let articles = [];

  if (activeTab === 'url') {{
    const raw = document.getElementById('urlInput').value.trim();
    if (!raw) {{ showError('기사 URL을 최소 1개 붙여넣으세요.'); return; }}
    const urls = raw.split('\\n').map(s => s.trim()).filter(s => s.startsWith('http')).slice(0, 5);
    if (urls.length === 0) {{ showError('유효한 URL이 없습니다. http로 시작해야 합니다.'); return; }}
    btn.disabled = true; loadingMsg.style.display = 'block';
    previewDiv.innerHTML = '<div style="color:#475569;font-size:0.78rem;">기사 메타데이터 가져오는 중...</div>';
    try {{
      const metas = [];
      for (const u of urls) {{ metas.push(await fetchOneMeta(u)); }}
      previewDiv.innerHTML = metas.map((a, i) => `
        <div class="url-preview-item ${{a.ok ? '' : 'failed'}}">
          <div class="preview-title">[${{i}}] ${{escHtml(a.title)}}</div>
          ${{a.snippet ? '<div class="preview-snippet">' + escHtml(a.snippet.slice(0, 180)) + '…</div>' : ''}}
          <div class="preview-url">${{escHtml(a.url)}}</div>
        </div>`).join('');
      articles = metas.map((a, i) => {{
        let host = a.url; try {{ host = new URL(a.url).hostname.replace(/^www\\./, ''); }} catch(e) {{}}
        return {{ index: i, source: host, headline: a.title, snippet: a.snippet || '', url: a.url, published: new Date().toISOString().slice(0, 10) }};
      }});
    }} catch(e) {{
      btn.disabled = false; loadingMsg.style.display = 'none';
      showError('URL fetch 실패: ' + e.message); return;
    }}
  }} else {{
    const text = document.getElementById('textInput').value.trim();
    if (!text) {{ showError('기사 본문을 붙여넣으세요.'); return; }}
    const source = document.getElementById('textSource').value.trim() || 'Unknown';
    const headline = document.getElementById('textHeadline').value.trim() || text.slice(0, 80);
    articles = [{{ index: 0, source, headline, snippet: text.slice(0, 800), url: '', published: new Date().toISOString().slice(0, 10) }}];
    btn.disabled = true; loadingMsg.style.display = 'block';
  }}

  try {{
    const res = await fetch('/pov/analyze', {{
      method: 'POST', headers: {{'Content-Type': 'application/json'}},
      body: JSON.stringify({{ user_profile: profile, articles, output_language: outputLang }}),
    }});
    const data = await res.json();
    if (data.error) {{ showError(data.error); }}
    else {{
      resultDiv.innerHTML = '<div class="results-section"><div class="results-label">Analysis Result</div>' + data.card_html + '</div>';
      resultDiv.scrollIntoView({{ behavior: 'smooth', block: 'start' }});
    }}
  }} catch(e) {{ showError('요청 실패: ' + e.message); }}
  finally {{ btn.disabled = false; loadingMsg.style.display = 'none'; }}
}}
function showError(msg) {{ document.getElementById('errorBox').innerHTML = '<div class="error-box">' + escHtml(msg) + '</div>'; }}
function clearError() {{ document.getElementById('errorBox').innerHTML = ''; }}
function escHtml(s) {{ return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;'); }}
loadProfile();
</script>
</body>
</html>"""


MANUAL_CSS = """
.section-card { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.25rem; margin-bottom: 1rem; }
.section-title { font-size: 0.7rem; font-weight: 700; color: var(--text-muted); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 1rem; display: flex; align-items: center; gap: 0.5rem; }
.section-title .saved-badge { background: var(--success); color: #fff; padding: 0.1rem 0.4rem; border-radius: 4px; font-size: 0.65rem; font-weight: 600; letter-spacing: 0; }
.field-row { display: grid; gap: 0.75rem; grid-template-columns: 1fr 1fr; margin-bottom: 0.75rem; }
.field-row.single { grid-template-columns: 1fr; }
.field { display: flex; flex-direction: column; gap: 0.3rem; }
label { font-size: 0.72rem; font-weight: 600; color: var(--text-muted); }
input[type="text"], select { background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 0.875rem; padding: 0.55rem 0.75rem; outline: none; transition: border-color 0.2s; width: 100%; }
input[type="text"]:focus, select:focus { border-color: var(--accent); }
select { cursor: pointer; }
.tag-wrap { background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 0.4rem 0.5rem; display: flex; flex-wrap: wrap; gap: 0.35rem; cursor: text; min-height: 42px; transition: border-color 0.2s; }
.tag-wrap:focus-within { border-color: var(--accent); }
.tag { background: var(--accent-glow); color: var(--accent); font-size: 0.75rem; padding: 0.2rem 0.5rem; border-radius: 4px; display: flex; align-items: center; gap: 0.3rem; }
.tag-x { cursor: pointer; color: var(--accent); font-size: 0.9rem; line-height: 1; }
.tag-x:hover { color: var(--text); }
.tag-input { background: none; border: none; outline: none; color: var(--text); font-size: 0.875rem; flex: 1; min-width: 80px; padding: 0.15rem 0.25rem; }
.profile-actions { display: flex; justify-content: flex-end; margin-top: 0.75rem; }
.btn-save { background: var(--accent-glow); color: var(--accent); border: none; border-radius: 8px; padding: 0.45rem 1rem; font-size: 0.8rem; font-weight: 600; cursor: pointer; transition: background 0.2s; }
.btn-save:hover { background: var(--surface-3); }
.tabs { display: flex; gap: 0; margin-bottom: 1rem; border-bottom: 1px solid var(--border); }
.tab { padding: 0.55rem 1rem; font-size: 0.8rem; font-weight: 600; color: var(--text-muted); cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -1px; transition: color 0.15s, border-color 0.15s; }
.tab.active { color: var(--accent); border-bottom-color: var(--accent); }
.tab-panel { display: none; }
.tab-panel.active { display: block; }
textarea { width: 100%; background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 0.875rem; padding: 0.75rem; resize: vertical; min-height: 110px; outline: none; transition: border-color 0.2s; font-family: inherit; }
textarea:focus { border-color: var(--accent); }
.url-previews { margin-top: 0.75rem; display: flex; flex-direction: column; gap: 0.4rem; }
.url-preview-item { background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; padding: 0.55rem 0.75rem; font-size: 0.78rem; }
.url-preview-item .preview-title { color: var(--accent); font-weight: 600; margin-bottom: 0.15rem; }
.url-preview-item .preview-snippet { color: var(--text-muted); line-height: 1.45; }
.url-preview-item .preview-url { color: var(--text-dim); font-size: 0.7rem; margin-top: 0.2rem; word-break: break-all; }
.url-preview-item.failed .preview-title { color: var(--danger); }
.source-row { display: grid; grid-template-columns: 1fr 2fr; gap: 0.75rem; margin-top: 0.75rem; }
.lang-toggle { display: flex; gap: 0; background: var(--surface-2); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; width: fit-content; }
.lang-btn { padding: 0.45rem 1rem; font-size: 0.8rem; font-weight: 600; cursor: pointer; background: none; border: none; color: var(--text-muted); transition: background 0.15s, color 0.15s; }
.lang-btn.active { background: var(--accent); color: var(--on-accent); }
.analyze-wrap { margin-top: 1.5rem; }
.btn-analyze { width: 100%; background: var(--accent); color: var(--on-accent); border: none; border-radius: 10px; padding: 0.875rem; font-size: 1rem; font-weight: 700; cursor: pointer; transition: filter 0.2s; letter-spacing: 0.01em; }
.btn-analyze:hover { filter: brightness(1.08); }
.btn-analyze:disabled { background: var(--surface-3); color: var(--text-dim); cursor: not-allowed; filter: none; }
.loading-msg { display: none; text-align: center; color: var(--text-muted); font-size: 0.82rem; margin-top: 0.6rem; }
.spinner-icon { display: inline-block; animation: spin 1s linear infinite; margin-right: 0.3rem; }
@keyframes spin { to { transform: rotate(360deg); } }
.error-box { background: transparent; border: 1px solid var(--danger); border-radius: 8px; color: var(--danger); padding: 0.875rem 1rem; margin-top: 1rem; font-size: 0.8rem; white-space: pre-wrap; }
.results-section { margin-top: 2rem; }
.results-label { font-size: 0.7rem; font-weight: 700; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 1rem; }
@media (max-width: 480px) { .field-row { grid-template-columns: 1fr; } .source-row { grid-template-columns: 1fr; } }
"""


# ─── Request handler ─────────────────────────────────────────────────────────

def _get(body, key):
    v = body.get(key, "") if isinstance(body, dict) else ""
    if isinstance(v, list):
        return v[0] if v else ""
    return v or ""


def handle(method, path, body, ctx):
    user = ctx.get("user")
    if not user:
        return ("redirect", "/login")

    if method == "GET":
        if path == "/pov/fetch":
            url = _get(body, "url")
            if not url:
                return ("json", {"error": "url parameter required"})
            return ("json", fetch_url_meta(url))

        if path == "/pov/feed":
            return ("html", build_feed_html(user, load_pov_results()))

        if path.startswith("/pov/feed/"):
            eid = urllib.parse.unquote(path[len("/pov/feed/"):])
            data = load_pov_results()
            found = next((r for r in data.get("results", []) if r.get("event_id") == eid), None)
            if found:
                return ("html", build_detail_html(user, found))
            return ("html", "<h2>404 — event not found</h2>", 404)

        # GET /pov — manual analysis main page
        return ("html", build_main_html(user))

    if method == "POST" and path == "/pov/analyze":
        if not isinstance(body, dict) or "__raw__" in body:
            return ("json", {"error": "Invalid request"})
        try:
            user_profile = body.get("user_profile")
            articles = body.get("articles")
            output_language = body.get("output_language", "ko")
            if not user_profile:
                return ("json", {"error": "user_profile is required"})
            if not articles:
                return ("json", {"error": "articles is required"})

            user_input = {
                "event_id": f"manual-{uuid.uuid4().hex[:8]}",
                "user_profile": user_profile,
                "articles": articles,
                "output_language": output_language,
            }
            pov = analyze_pov(user_input, output_language)
            return ("json", {"card_html": render_pov_card(pov)})
        except Exception as e:
            traceback.print_exc()
            return ("json", {"error": str(e)})

    return ("html", "<h2>404</h2>", 404)
