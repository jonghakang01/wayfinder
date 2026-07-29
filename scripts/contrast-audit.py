#!/usr/bin/env python3
"""WCAG contrast audit that composites alpha against the real ancestor chain.

Two earlier hand-rolled versions of this got the answer wrong, in both
directions, and the reason each time was the background:

  1. reading document.body instead of the element's own ancestors, so text on
     a colored hero was scored against the page background;
  2. treating rgba() as if it were opaque, so `rgb(2,105,166)` on
     `rgba(2,105,166,0.1)` scored 1.0 — a violation that does not exist.

So the background here is resolved by walking up from the element, compositing
every translucent layer in order until an opaque one is reached. Anything the
method genuinely cannot decide (a gradient or image behind the text) is
reported as UNKNOWN rather than guessed — an audit that quietly guesses is
what produced the 277 phantom findings.

Usage:
    LD_LIBRARY_PATH=$HOME/.local/chromium-libs \
        python3 scripts/contrast-audit.py /llm-check /aeo --theme light
    ... --user jongha.kang --base http://localhost:8080 --json out.json
"""
import argparse
import glob
import json
import os
import sys

JS_AUDIT = r"""() => {
  const parse = (s) => {
    const m = s && s.match(/rgba?\(([^)]+)\)/);
    if (!m) return null;
    const p = m[1].split(',').map(x => parseFloat(x.trim()));
    return {r: p[0], g: p[1], b: p[2], a: p.length > 3 ? p[3] : 1};
  };
  // src over dst, both premultiplied out to an opaque result when dst is opaque
  const over = (src, dst) => ({
    r: src.r * src.a + dst.r * (1 - src.a),
    g: src.g * src.a + dst.g * (1 - src.a),
    b: src.b * src.a + dst.b * (1 - src.a),
    a: 1,
  });
  const lum = (c) => {
    const f = (v) => {
      v /= 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b);
  };
  const ratio = (a, b) => {
    const l1 = lum(a), l2 = lum(b);
    return (Math.max(l1, l2) + 0.05) / (Math.min(l1, l2) + 0.05);
  };

  // Walk ancestors collecting translucent layers until something opaque.
  // Returns {bg} or {unknown: reason} — never a guess.
  const backdrop = (el) => {
    const layers = [];
    for (let n = el; n; n = n.parentElement) {
      const cs = getComputedStyle(n);
      if (cs.backgroundImage && cs.backgroundImage !== 'none') {
        return {unknown: 'background-image on ' + n.tagName.toLowerCase() +
                          (n.className ? '.' + String(n.className).split(' ')[0] : '')};
      }
      const c = parse(cs.backgroundColor);
      if (c && c.a > 0) {
        layers.push(c);
        if (c.a >= 1) break;
      }
    }
    let bg = {r: 255, g: 255, b: 255, a: 1};   // canvas default
    for (let i = layers.length - 1; i >= 0; i--) bg = over(layers[i], bg);
    return {bg};
  };

  // Color emoji render from the font's own palette, so `color` says nothing
  // about what is on screen — scoring them produces confident nonsense
  // (a 1.10 on '📊'). Only text with an actual letter or digit is judged.
  const JUDGEABLE = /[\p{Letter}\p{Number}]/u;
  const ownText = (el) => {
    let s = '';
    for (const n of el.childNodes) if (n.nodeType === 3) s += n.textContent;
    return s.trim();
  };
  const hasOwnText = (el) => JUDGEABLE.test(ownText(el));

  const sel = (el) => {
    const cls = String(el.className || '').trim().split(/\s+/).filter(Boolean).slice(0, 2);
    return el.tagName.toLowerCase() + (cls.length ? '.' + cls.join('.') : '');
  };

  const out = [];
  for (const el of document.querySelectorAll('*')) {
    if (!hasOwnText(el)) continue;
    const cs = getComputedStyle(el);
    if (cs.visibility === 'hidden' || cs.display === 'none' || parseFloat(cs.opacity) === 0) continue;
    const rect = el.getBoundingClientRect();
    if (rect.width < 1 || rect.height < 1) continue;

    const back = backdrop(el);
    const px = parseFloat(cs.fontSize);
    const weight = parseInt(cs.fontWeight, 10) || 400;
    // WCAG "large text": >=18pt, or >=14pt when bold. 1pt = 4/3 px.
    const large = px >= 24 || (px >= 18.66 && weight >= 700);
    const need = large ? 3.0 : 4.5;
    const sample = el.textContent.trim().replace(/\s+/g, ' ').slice(0, 42);

    if (back.unknown) {
      out.push({sel: sel(el), sample, need, unknown: back.unknown, color: cs.color});
      continue;
    }
    let fg = parse(cs.color);
    if (!fg) continue;
    if (fg.a < 1) fg = over(fg, back.bg);       // translucent text over its own backdrop
    const r = ratio(fg, back.bg);
    if (r < need) {
      const hex = (c) => '#' + [c.r, c.g, c.b].map(v =>
        Math.round(v).toString(16).padStart(2, '0')).join('');
      out.push({sel: sel(el), sample, ratio: Math.round(r * 100) / 100, need,
                fg: hex(fg), bg: hex(back.bg), px: Math.round(px), weight});
    }
  }
  return out;
}"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("paths", nargs="+", help="paths to audit, e.g. /llm-check")
    ap.add_argument("--base", default="http://localhost:8080")
    ap.add_argument("--theme", default="both", choices=["light", "dark", "both"])
    ap.add_argument("--user", default="jongha.kang")
    ap.add_argument("--width", type=int, default=1280)
    ap.add_argument("--json", help="write full findings here")
    args = ap.parse_args()

    from playwright.sync_api import sync_playwright

    exe = glob.glob(os.path.expanduser(
        "~/.cache/ms-playwright/chromium-*/chrome-linux*/chrome"))
    if not exe:
        sys.exit("chromium not found under ~/.cache/ms-playwright")

    token = None
    sess = os.path.expanduser("~/.appdata/sessions.json")
    if os.path.exists(sess):
        for t, v in json.load(open(sess)).items():
            if (v if isinstance(v, str) else v.get("user")) == args.user:
                token = t
                break

    themes = ["light", "dark"] if args.theme == "both" else [args.theme]
    report, total, unknown = {}, 0, 0

    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=exe[0])
        for theme in themes:
            ctx = b.new_context(viewport={"width": args.width, "height": 900})
            ctx.add_init_script(
                f"try{{localStorage.setItem('wf-theme','{theme}')}}catch(e){{}}")
            if token and args.base.startswith("http"):
                ctx.add_cookies([{"name": "session", "value": token, "url": args.base}])
            for path in args.paths:
                pg = ctx.new_page()
                pg.goto(args.base + path, wait_until="domcontentloaded")
                pg.wait_for_timeout(1500)
                found = pg.evaluate(JS_AUDIT)
                report[f"{theme} {path}"] = found
                bad = [f for f in found if "ratio" in f]
                unk = [f for f in found if "unknown" in f]
                total += len(bad)
                unknown += len(unk)
                print(f"\n=== {theme} {path} — {len(bad)} below AA, {len(unk)} undecidable")
                for f in sorted(bad, key=lambda x: x["ratio"])[:12]:
                    print(f"  {f['ratio']:5.2f} (need {f['need']})  {f['sel']:28} "
                          f"{f['fg']} on {f['bg']}  {f['px']}px/{f['weight']}  "
                          f"{f['sample']!r}")
                if len(bad) > 12:
                    print(f"  … {len(bad) - 12} more (use --json for all)")
                for f in unk[:5]:
                    print(f"  UNKNOWN  {f['sel']:28} {f['unknown']}  {f['sample']!r}")
                pg.close()
            ctx.close()
        b.close()

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(report, fh, indent=2)
        print(f"\nfull findings → {args.json}")
    print(f"\nTOTAL: {total} below AA, {unknown} undecidable "
          f"(undecidable = text over a gradient/image; judge those by eye)")
    return 1 if total else 0


if __name__ == "__main__":
    sys.exit(main())
