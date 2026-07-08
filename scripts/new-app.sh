#!/bin/bash
# Scaffold a new Wayfinder app: service module + test + smoke-test entry.
# Usage: bash scripts/new-app.sh <slug> "<Display Name>" "<icon-emoji>"
# Example: bash scripts/new-app.sh notes "빠른 메모" "🗒️"
set -e

SLUG="$1"
NAME="$2"
ICON="${3:-🧩}"

if [ -z "$SLUG" ] || [ -z "$NAME" ]; then
    echo "Usage: bash scripts/new-app.sh <slug> \"<Display Name>\" \"<icon>\""
    echo "Example: bash scripts/new-app.sh notes \"빠른 메모\" \"🗒️\""
    exit 1
fi
if ! echo "$SLUG" | grep -qE '^[a-z][a-z0-9_]*$'; then
    echo "❌ slug must be lowercase [a-z0-9_], start with a letter: '$SLUG'"
    exit 1
fi

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
SVC="$ROOT/services/$SLUG.py"
TEST="$ROOT/tests/test_$SLUG.py"

if [ -e "$SVC" ]; then echo "❌ $SVC already exists"; exit 1; fi

# ---- 1. Service module -------------------------------------------------
cat > "$SVC" <<'TEMPLATE'
import json, os
from datetime import datetime

DATA_ROOT = os.path.expanduser("~/.appdata")

META = {
    "name": "__NAME__",
    "path": "/__SLUG__",
    "icon": "__ICON__",
    "description": "__NAME__",
    "hidden": False,
}


def _data_path(user):
    return os.path.join(DATA_ROOT, user, "__SLUG__.json")


def _load(user):
    f = _data_path(user)
    if not os.path.exists(f):
        return []
    try:
        with open(f) as fp:
            return json.load(fp)
    except Exception:
        return []


def _save(user, data):
    f = _data_path(user)
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def render(user):
    items = _load(user)
    rows = "".join(
        f"<li style='padding:12px 16px;background:var(--surface);border:1px solid var(--border);border-radius:10px'>{i.get('text','')}</li>"
        for i in items
    ) or "<li style='color:var(--text-muted)'>아직 항목이 없습니다.</li>"
    return f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>__NAME__</title><link rel="stylesheet" href="/static/style.css"></head>
<body>
<nav><span class="nav-brand">__ICON__ __NAME__</span>
<span class="nav-user"><a class="nav-back" href="/">← 홈</a></span></nav>
<div class="container">
  <h1>__ICON__ __NAME__</h1>
  <form method="post" action="/__SLUG__/add" style="display:flex;gap:8px;margin:20px 0">
    <input name="text" placeholder="새 항목..." autocomplete="off"
      style="flex:1;padding:11px 14px;border-radius:10px;border:1px solid var(--border);background:var(--surface);color:var(--text)">
    <button type="submit"
      style="padding:11px 20px;border-radius:10px;border:0;background:var(--accent);color:#04121f;font-weight:700;cursor:pointer">추가</button>
  </form>
  <ul style="list-style:none;display:flex;flex-direction:column;gap:8px">{rows}</ul>
</div></body></html>"""


def handle(method, path, body, ctx):
    user = ctx.get("user", "guest")

    if method == "GET" and path == "/__SLUG__":
        return ("html", render(user))

    if method == "POST" and path == "/__SLUG__/add":
        raw = body.get("text", "")
        text = (raw[0] if isinstance(raw, list) else raw).strip()
        if text:
            items = _load(user)
            items.append({"text": text, "at": datetime.now().isoformat()})
            _save(user, items)
        return ("redirect", "/__SLUG__")

    return ("html", "<h2>404 Not Found</h2>")
TEMPLATE

# ---- 2. Test file ------------------------------------------------------
mkdir -p "$ROOT/tests"
cat > "$TEST" <<'TEMPLATE'
import importlib

MOD = "services.__SLUG__"


def test_meta_is_valid():
    m = importlib.import_module(MOD).META
    assert m["path"] == "/__SLUG__"
    assert m["name"] and isinstance(m["name"], str)


def test_get_renders_html():
    mod = importlib.import_module(MOD)
    kind, html = mod.handle("GET", "/__SLUG__", {}, {"user": "__testuser__"})
    assert kind == "html"
    assert "__NAME__" in html


def test_post_add_redirects():
    mod = importlib.import_module(MOD)
    kind, target = mod.handle(
        "POST", "/__SLUG__/add", {"text": [""]}, {"user": "__testuser__"}
    )
    assert kind == "redirect"
    assert target == "/__SLUG__"
TEMPLATE

# ---- 3. Substitute placeholders ---------------------------------------
for F in "$SVC" "$TEST"; do
    sed -i "s|__SLUG__|$SLUG|g; s|__NAME__|$NAME|g; s|__ICON__|$ICON|g" "$F"
done

# ---- 4. Add smoke-test entry (before the final Result echo) -----------
SMOKE="$ROOT/scripts/smoke-test.sh"
if ! grep -q "\$BASE/$SLUG\"" "$SMOKE"; then
    LINE="check \"$NAME (auth required)\"    \"\$BASE/$SLUG\"    \"302\""
    # insert before the blank echo that precedes the Result summary
    awk -v ins="$LINE" '/^echo ""$/ && !done {print ins; done=1} {print}' "$SMOKE" > "$SMOKE.tmp" && mv "$SMOKE.tmp" "$SMOKE"
fi

echo "✅ Created new app '$SLUG'"
echo "   • services/$SLUG.py   (META + handle)"
echo "   • tests/test_$SLUG.py  (3 tests)"
echo "   • smoke-test.sh entry added"
echo ""
echo "Next:"
echo "   1) bash scripts/dev-restart.sh"
echo "   2) open http://localhost:8080/$SLUG  (홈 메뉴에도 자동 노출)"
echo "   3) python3 -m pytest tests/test_$SLUG.py -q"
