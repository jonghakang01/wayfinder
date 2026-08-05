"""Handle a wayfinder-agent:// link — the click-to-pair half of the agent.

Nobody should open a terminal or edit JSON to pair a PC (강프로 2026-08-05).
Review shows a link, Windows hands the whole URL here, and this writes the
config the agent reads. Same shape as the wayfinder-robot:// launcher that
already works from that page.

  wayfinder-agent://pair?token=<token>&base=<http://host:port>

Called by agent-pair.bat as:
  wsl.exe -e python3 <this file> "<the full URL>"
"""
import json
import sys
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlparse

CONFIG = Path.home() / ".wayfinder-agent.json"
LOG = Path.home() / ".wayfinder-agent-pair.log"


def _say(msg):
    print(msg)
    try:
        with LOG.open("a") as f:
            f.write(msg + "\n")
    except OSError:
        pass


def parse_link(url: str) -> dict:
    """{base_url, token} from the link, or {} when it is not a pairing link.

    Windows hands the URL through a couple of layers that like to add a
    trailing slash and percent-encode the query, so both are undone here."""
    url = (url or "").strip().strip('"')
    if not url.lower().startswith("wayfinder-agent:"):
        return {}
    # urlparse only treats //host/path shapes as netloc, and the link may
    # arrive as wayfinder-agent://pair?... or wayfinder-agent:pair?...
    rest = url.split(":", 1)[1].lstrip("/")
    action, _, query = rest.partition("?")
    if action.rstrip("/").lower() != "pair":
        return {}
    q = parse_qs(query)
    token = unquote((q.get("token") or [""])[0]).strip()
    base = unquote((q.get("base") or [""])[0]).strip().rstrip("/")
    if not token or not base:
        return {}
    if not base.startswith(("http://", "https://")):
        return {}
    return {"base_url": base, "token": token}


def main():
    url = sys.argv[1] if len(sys.argv) > 1 else ""
    cfg = parse_link(url)
    if not cfg:
        _say(f"not a pairing link: {url[:120]!r}")
        return 1
    CONFIG.write_text(json.dumps(cfg, indent=2))
    # The token is the one secret here — never log it.
    _say(f"paired with {cfg['base_url']} — config written to {CONFIG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
