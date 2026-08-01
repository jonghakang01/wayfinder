import json
import os
import threading

from services._paths import DATA_ROOT

# Toast Companion — ported from ~/labs/toast-companion (2026-07-31).
# All user-facing copy and prompt text live in toast_assets/ (the app keeps
# its own approved Korean UI and visual language — an owner-approved
# exception to the cardconv DS; see project memory).

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toast_assets")

META = {
    "name": "Toast Companion",
    "path": "/toast",
    "icon": "🥂",
    "description": "Toast scripts for client dinners",
    "hidden": False,
}

MODEL = "claude-opus-5"
_cache_lock = threading.Lock()
_asset_cache = {}


def _asset_json(name):
    if name not in _asset_cache:
        with open(os.path.join(ASSETS, name), encoding="utf-8") as f:
            _asset_cache[name] = json.load(f)
    return _asset_cache[name]


def _app_html():
    with open(os.path.join(ASSETS, "app.html"), encoding="utf-8") as f:
        return f.read()


SCHEMA = {
    "type": "object",
    "properties": {
        "toasts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "lang": {"type": "string", "enum": ["ko", "en", "bridge"]},
                    "track": {"type": "string", "enum": ["classic", "witty", "restrained", "custom", "natural", "bridge"]},
                    "lead_in": {"type": "string"},
                    "call_word": {"type": "string"},
                    "response_word": {"type": "string"},
                    "buildup": {"type": "string"},
                    "note": {"type": "string"},
                    "duration_sec": {"type": "integer"},
                },
                "required": ["lang", "track", "lead_in", "call_word", "response_word", "buildup", "note", "duration_sec"],
                "additionalProperties": False,
            },
        }
    },
    "required": ["toasts"],
    "additionalProperties": False,
}


# ---- preload cache (per settings combo, shared across users) ----
def _cache_path():
    return os.path.join(DATA_ROOT, "toast", "preload_cache.json")


def _occasions(p):
    o = p.get("occasion", [])
    return [o] if isinstance(o, str) else list(o)


def cache_key(p):
    parts = ["+".join(sorted(_occasions(p)))]
    parts += [str(p.get(k, "")) for k in
              ("audience_scope", "execs", "age_mix", "my_role", "lang_mix", "tone", "round",
               "occasion_note")]
    return "|".join(parts)


def _load_cache():
    try:
        with open(_cache_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def cache_get(p):
    return _load_cache().get(cache_key(p))


def cache_put(p, toasts):
    from datetime import datetime
    with _cache_lock:
        c = _load_cache()
        c[cache_key(p)] = {"toasts": toasts, "at": datetime.now().isoformat(timespec="minutes")}
        os.makedirs(os.path.dirname(_cache_path()), exist_ok=True)
        with open(_cache_path(), "w", encoding="utf-8") as f:
            json.dump(c, f, ensure_ascii=False)


# ---- per-account state (events/people/saved/settings sync across devices) ----
_state_lock = threading.Lock()


def _state_path(user):
    d = os.path.join(DATA_ROOT, user or "guest")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "toast.json")


def load_state(user):
    try:
        with open(_state_path(user), encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def save_state(user, blob):
    from datetime import datetime
    # a blob without "state" is a malformed client push — never wipe real data with it
    if not isinstance(blob, dict) or not isinstance(blob.get("state"), dict):
        return {"error": "bad state"}
    blob["updated_at"] = datetime.now().isoformat(timespec="seconds")
    with _state_lock:
        with open(_state_path(user), "w", encoding="utf-8") as f:
            json.dump(blob, f, ensure_ascii=False)
    return {"ok": True, "updated_at": blob["updated_at"]}


# ---- client news (v2.1): Google News RSS -> Claude summary, disk cache ----
_news_lock = threading.Lock()
NEWS_TTL = 12 * 3600          # a served card may be this old
NEWS_WARM_TTL = 30 * 60       # app-open warming re-collects anything older

NEWS_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "points": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "point": {"type": "string"},
                    "why": {"type": "string"},
                },
                "required": ["point", "why"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["headline", "points"],
    "additionalProperties": False,
}


def _news_cache_path():
    return os.path.join(DATA_ROOT, "toast", "news_cache.json")


def _news_key(q, hl, gl):
    return f"{q}|{hl}|{gl}"


def _load_news_cache():
    try:
        with open(_news_cache_path(), encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def fetch_headlines(q, hl="ko", gl="KR", limit=10):
    """Top headlines from Google News RSS. Parser stays lenient — title, link,
    date and source only — because the endpoint is unofficial."""
    import urllib.parse
    import urllib.request
    import xml.etree.ElementTree as ET
    lang = hl.split("-")[0]
    url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q)
           + f"&hl={hl}&gl={gl}&ceid={gl}:{lang}")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=10) as r:
        root = ET.fromstring(r.read())
    items = []
    for it in root.iter("item"):
        title = it.findtext("title") or ""
        if not title:
            continue
        items.append({
            "title": title,
            "link": it.findtext("link") or "",
            "date": (it.findtext("pubDate") or "")[:16],
            "source": it.findtext("{https://news.google.com/rss}source")
                      or it.findtext("source") or "",
        })
        if len(items) >= limit:
            break
    return items


def summarize_headlines(label, items):
    prompts = _asset_json("prompts.json")
    lines = [f"- {i['title']} ({i.get('source','')}, {i.get('date','')})" for i in items]
    user = (f"광고주 '{label}'의 최근 뉴스 헤드라인이다. 이 회사와 저녁 자리를 앞둔 "
            "대행사 담당자에게 브리핑하라. headline=지금 상황 한 줄. points=3~5개, "
            "각각 point=무슨 일인지 한 문장, why=술자리 대화에서 어떻게 꺼낼지/왜 아는 게 "
            "중요한지 한 문장. 헤드라인에 없는 사실을 지어내지 마라.\n\n" + "\n".join(lines))
    import anthropic  # lazy: CI/test collection must not require the SDK
    client = anthropic.Anthropic()
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=8000,
        system=prompts["system"],
        messages=[{"role": "user", "content": user}],
        betas=["server-side-fallback-2026-07-01"],
        extra_body={
            "fallbacks": "default",
            "output_config": {"format": {"type": "json_schema", "schema": NEWS_SCHEMA}},
        },
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("summary refused")
    return json.loads(next(b.text for b in resp.content if b.type == "text"))


def news_get(q, hl, gl, label="", max_age=NEWS_TTL):
    """Cached briefing for one client unit. Falls back to a stale card rather
    than an error when collection fails — the dinner still happens offline."""
    import time
    key = _news_key(q, hl, gl)
    cache = _load_news_cache()
    hit = cache.get(key)
    now = time.time()
    if hit and now - hit.get("ts", 0) < max_age:
        return {**hit["card"], "cached": True}
    try:
        items = fetch_headlines(q, hl, gl)
        if not items:
            raise RuntimeError("no headlines")
        summary = summarize_headlines(label or q, items)
        from datetime import datetime
        card = {"summary": summary, "items": items,
                "at": datetime.now().isoformat(timespec="minutes")}
        with _news_lock:
            cache = _load_news_cache()
            cache[key] = {"ts": now, "card": card}
            os.makedirs(os.path.dirname(_news_cache_path()), exist_ok=True)
            with open(_news_cache_path(), "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False)
        return card
    except Exception as e:
        if hit:
            return {**hit["card"], "cached": True, "stale": True}
        return {"error": str(e)}


# ---- generation ----
def _hangul_syllables(w):
    return sum(1 for ch in w if "가" <= ch <= "힣")


def _valid_toast(t):
    """Spec 6.1-2: a long Korean response word scatters the room. Upper bound
    4 syllables; floor relaxed to 1 (a one-syllable shout echoes best)."""
    if t.get("lang") != "ko":
        return True
    return 1 <= _hangul_syllables(t.get("response_word", "")) <= 4


def generate(params):
    prompts = _asset_json("prompts.json")
    mix = params.get("lang_mix", "all_korean")
    plans = prompts["mix_plans"]
    tpl = prompts["user_lines"]
    lines = [
        tpl["occasion"].format(v=", ".join(_occasions(params)) or tpl["occasion_default"]),
        tpl["crowd"].format(a=params.get("audience_scope") or tpl["crowd_default"],
                            b=params.get("execs") or tpl["execs_default"]),
        tpl["age"].format(v=params.get("age_mix") or tpl["age_default"]),
        tpl["role"].format(v=params.get("my_role") or tpl["role_default"]),
        tpl["mix"].format(v=mix),
        tpl["tone"].format(v=params.get("tone") or tpl["tone_default"]),
        tpl["round"].format(v=params.get("round") or tpl["round_default"]),
    ]
    note = (params.get("occasion_note") or "").strip()
    if note:
        lines.append(f"자리 성격 한 줄 메모(가장 구체적인 재료 — 우선 반영): {note}")
    names = (params.get("org_names") or "").strip()
    if names:
        lines.append(tpl["orgs"].format(v=names))
    scene = (params.get("scene") or "").strip()
    if scene:
        lines.append(tpl["scene"].format(v=scene))
    lines.append("")
    lines.append(tpl["ask"] + plans.get(mix, plans["all_korean"]))

    import anthropic  # lazy: CI/test collection must not require the SDK
    client = anthropic.Anthropic()
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=prompts["system"],
        messages=[{"role": "user", "content": "\n".join(lines)}],
        betas=["server-side-fallback-2026-07-01"],
        extra_body={
            "fallbacks": "default",
            "output_config": {"format": {"type": "json_schema", "schema": SCHEMA}},
        },
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("generation refused")
    text = next(b.text for b in resp.content if b.type == "text")
    data = json.loads(text)
    for t in data.get("toasts", []):
        if t.get("track") == "natural":
            t["lead_in"] = ""  # natural's script lives in buildup only
    data["toasts"] = [t for t in data.get("toasts", []) if _valid_toast(t)]
    return data


def handle(method, path, body, ctx):
    if method == "GET" and path == "/toast":
        return ("html", _app_html())

    if method == "GET" and path == "/toast/api/canon":
        return ("json", _asset_json("canon.json"))

    if method == "GET" and path == "/toast/api/state":
        return ("json", load_state((ctx or {}).get("user")))

    if method == "GET" and path == "/toast/api/news":
        g = (lambda k, d="": (body.get(k, [d]) or [d])[0] if isinstance(body, dict) else d)
        q = g("q")
        if not q:
            return ("json", {"error": "q required"})
        mode = g("mode", "view")
        max_age = {"force": 0, "warm": NEWS_WARM_TTL}.get(mode, NEWS_TTL)
        return ("json", news_get(q, g("hl", "ko"), g("gl", "KR"),
                                 label=g("label"), max_age=max_age))

    if method == "POST" and path == "/toast/api/state":
        return ("json", save_state((ctx or {}).get("user"), body))

    if method == "POST" and path == "/toast/api/preload":
        hit = cache_get(body if isinstance(body, dict) else {})
        if hit:
            return ("json", {**hit, "src": "recent"})
        col = _asset_json("collection.json")
        if col.get("toasts"):
            return ("json", {**col, "src": "collection"})
        return ("json", {"toasts": []})

    if method == "POST" and path == "/toast/api/generate":
        try:
            params = body if isinstance(body, dict) else {}
            result = generate(params)
            cache_put(params, result.get("toasts", []))
            return ("json", result)
        except Exception as e:
            return ("json", {"error": str(e)})

    return ("html", "<h2>404 Not Found</h2>")
