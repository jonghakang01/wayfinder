"""Screenshot every generated preview and flag the ones that render wrong.

    LD_LIBRARY_PATH=$HOME/.local/chromium-libs python3 sync/rendercheck.py

Catches the two failure modes that matter: a card that came out blank (CSS
didn't resolve) and a card whose light pane is identical to its dark pane
(the theme scope didn't take).
"""
import glob
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).parent
DIST = HERE / "dist"
SHOTS = HERE / "shots"


def main():
    exe = glob.glob(os.path.expanduser(
        "~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome"))[0]
    SHOTS.mkdir(exist_ok=True)
    pages = sorted(DIST.glob("components/*/*.html"))
    bad = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe)
        ctx = b.new_context(viewport={"width": 900, "height": 700},
                            device_scale_factor=1)
        pg = ctx.new_page()
        errors = []
        pg.on("pageerror", lambda e: errors.append(str(e)))
        for f in pages:
            errors.clear()
            pg.goto("file://" + str(f), wait_until="load")
            pg.wait_for_timeout(120)
            panes = pg.eval_on_selector_all(
                ".dsx-pane", "els => els.map(e => e.getBoundingClientRect().height)")
            # A pane that never got the stylesheet collapses to near-nothing.
            thin = [h for h in panes if h < 60]
            colors = pg.eval_on_selector_all(
                ".dsx-pane", "els => els.map(e => getComputedStyle(e).backgroundColor)")
            same_theme = len(set(colors)) < 2
            shot = SHOTS / (f.parent.name + ".png")
            pg.screenshot(path=str(shot), full_page=True)
            size = shot.stat().st_size
            flag = []
            if len(panes) != 2:
                flag.append("panes=%d" % len(panes))
            if thin:
                flag.append("thin")
            if same_theme:
                flag.append("theme-not-scoped(%s)" % colors)
            if size < 6000:
                flag.append("blank?%dB" % size)
            if errors:
                flag.append("js:" + errors[0][:60])
            status = "FAIL " + ",".join(flag) if flag else "ok"
            if flag:
                bad.append(f.parent.name)
            print("%-28s %8dB  %s" % (f.parent.name, size, status))
        b.close()
    print("\n%d/%d clean" % (len(pages) - len(bad), len(pages)))
    if bad:
        print("needs attention:", ", ".join(bad))
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
