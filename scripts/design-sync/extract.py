"""Pull the live Wayfinder stylesheet + pattern CSS out of the webapp source.

The webapp is the source of truth, not this repo: tokens live in
`server.py STYLE` and the cardconv-derived pattern CSS lives in
`services/design.py DEMO_CSS`. Re-run this whenever either moves.
"""
import re
from pathlib import Path

# Resolve from this file, not $HOME — the sync lives inside the repo it reads.
WEBAPP = Path(__file__).resolve().parents[2]


def _triple_quoted(path: Path, name: str) -> str:
    src = path.read_text()
    i = src.index(name)
    start = src.index('"""', i) + 3
    return src[start:src.index('"""', start)]


def global_style() -> str:
    """server.py STYLE — tokens + nav + base components, served as /static/style.css."""
    return _triple_quoted(WEBAPP / "server.py", "STYLE = ")


def demo_css() -> str:
    """services/design.py DEMO_CSS — the cardconv pattern layer shown on /design."""
    return _triple_quoted(WEBAPP / "services" / "design.py", "DEMO_CSS = ")


def color_tokens() -> list:
    """The documented color tokens (name, purpose) from services/design.py."""
    src = (WEBAPP / "services" / "design.py").read_text()
    block = src[src.index("COLOR_TOKENS = ["):src.index("]", src.index("COLOR_TOKENS = ["))]
    return re.findall(r'\("(--[a-z0-9-]+)",\s*"([^"]+)"\)', block)


def light_theme_block(style: str) -> str:
    """The `:root[data-theme=light]` declarations, so previews can scope a light pane."""
    m = re.search(r':root\[data-theme="light"\]\s*\{(.*?)\n\}', style, re.S)
    return m.group(1) if m else ""


def scalar_tokens(style: str, prefix: str) -> list:
    """Every `--<prefix>*` declaration in the dark :root block, in source order."""
    root = re.search(r':root\s*\{(.*?)\n\}', style, re.S).group(1)
    return re.findall(r'(--' + prefix + r'[a-z0-9-]*)\s*:\s*([^;]+);', root)
