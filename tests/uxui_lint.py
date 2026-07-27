"""Static lint for the Wayfinder UX/UI standard (see /design, docs/mobile_ux_guideline.md).

Machine-checkable slice of the standard. It cannot see layout, so it targets the
rules that reliably break a page when violated:

  token-color     a raw hex that duplicates a design token -> light theme breaks
  viewport        page shell without the mobile viewport meta
  global-css      page shell that does not link /static/style.css (no tokens)
  mobile-bp       an app stylesheet with no @media(max-width:768px) rules
  english-ui      Korean copy in a UI control (labels/headers/buttons/options)

Counts are ratcheted against tests/uxui_baseline.json: existing debt is frozen,
new violations fail the build, and fixes must lower the baseline.
"""
import json
import pathlib
import re

ROOT = pathlib.Path(__file__).resolve().parent.parent
SERVICES = ROOT / "services"
BASELINE = pathlib.Path(__file__).resolve().parent / "uxui_baseline.json"

RULES = ("token-color", "viewport", "global-css", "mobile-bp", "english-ui")

HANGUL = re.compile(r"[가-힣]")
# UI controls whose text is user-facing chrome (data may be Korean, chrome may not)
CONTROL = re.compile(
    r"<(th|button|label|option)\b[^>]*>([^<]{0,120}?)</\1>", re.I | re.S)


def _norm_hex(h):
    h = h.lower().lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h[:6]


def token_map():
    """{normalized hex: token name} from the dark :root block in server.py STYLE."""
    src = (ROOT / "server.py").read_text(encoding="utf-8")
    root = re.search(r":root \{(.+?)\n\}", src, re.S)
    out = {}
    for name, val in re.findall(r"(--[a-z0-9-]+)\s*:\s*(#[0-9a-fA-F]{3,6})\b",
                                root.group(1) if root else ""):
        out.setdefault(_norm_hex(val), name)
    return out


def _strip_noise(src):
    """Blank out Python line comments. Triple-quoted blocks are kept — most
    markup and every app stylesheet lives in one."""
    return re.sub(r"(?m)^[ \t]*#(?![0-9a-fA-F]{3}\b|[0-9a-fA-F]{6}\b)(?![^\n]*\{).*$", "", src)


def lint_source(src, toks):
    """-> list of (rule, line_no, snippet)."""
    src = _strip_noise(src)
    lines = src.splitlines()
    hits = []

    def at(pos):
        return src.count("\n", 0, pos) + 1

    for m in re.finditer(r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{3})?\b", src):
        tok = toks.get(_norm_hex(m.group(0)))
        if tok:
            hits.append(("token-color", at(m.start()),
                         f"{m.group(0)} duplicates {tok} — use var({tok})"))

    for m in re.finditer(r"<!doctype html>(.{0,900})", src, re.I | re.S):
        head = m.group(1)
        if "name=\"viewport\"" not in head:
            hits.append(("viewport", at(m.start()), "page shell has no viewport meta"))
        if "/static/style.css" not in head:
            hits.append(("global-css", at(m.start()), "page shell does not link /static/style.css"))

    css_lines = sum(1 for ln in lines if re.match(r"\s*[.#@:a-z][^\s]*\{", ln))
    if css_lines >= 30 and "max-width:768px" not in src.replace(" ", ""):
        hits.append(("mobile-bp", 1,
                     f"{css_lines} CSS rules but no @media(max-width:768px)"))

    for m in CONTROL.finditer(src):
        text = re.sub(r"\{[^{}]*\}", "", m.group(2))  # drop f-string expressions
        if HANGUL.search(text):
            hits.append(("english-ui", at(m.start()),
                         f"Korean UI copy: {' '.join(text.split())[:48]}"))
    return hits


def lint_module(path, toks=None):
    return lint_source(path.read_text(encoding="utf-8"), toks or token_map())


def ui_modules():
    """Service modules that render pages (private helpers included)."""
    out = []
    for p in sorted(SERVICES.glob("*.py")):
        if p.name == "__init__.py":
            continue
        src = p.read_text(encoding="utf-8")
        if "<!doctype" in src.lower() or re.search(r"^_?[A-Z_]*CSS\s*=", src, re.M):
            out.append(p)
    return out


def scan():
    """-> {module: {rule: count}} for every page-rendering service."""
    toks = token_map()
    return {p.name: _tally(lint_module(p, toks)) for p in ui_modules()}


def _tally(hits):
    out = {}
    for rule, _, _ in hits:
        out[rule] = out.get(rule, 0) + 1
    return out


def load_baseline():
    return json.loads(BASELINE.read_text(encoding="utf-8")) if BASELINE.exists() else {}


def save_baseline(data):
    BASELINE.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


if __name__ == "__main__":  # `python3 tests/uxui_lint.py [--write]` for the report
    import sys
    toks = token_map()
    total = 0
    for p in ui_modules():
        hits = lint_module(p, toks)
        total += len(hits)
        if hits:
            print(f"\n{p.relative_to(ROOT)}  ({len(hits)})")
            for rule, ln, msg in hits:
                print(f"  {ln:>5}  {rule:<12} {msg}")
    print(f"\ntotal: {total}")
    if "--write" in sys.argv:
        save_baseline(scan())
        print(f"baseline written -> {BASELINE.relative_to(ROOT)}")
