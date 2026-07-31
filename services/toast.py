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
              ("audience_scope", "execs", "age_mix", "my_role", "lang_mix", "tone", "round")]
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
