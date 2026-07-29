"""Build the Claude Design project bundle from the live webapp source.

    python3 sync/build.py            # -> sync/dist/

Everything here is derived: tokens and base CSS come from `server.py STYLE`,
the pattern layer from `services/design.py DEMO_CSS`, and the guideline text
from the `/design` page. Re-run after any design-system change, then upload
with the DesignSync tool.
"""
import re
import shutil
from pathlib import Path

import extract
from components import CARDS

HERE = Path(__file__).parent
DIST = HERE / "dist"

# Preview-only chrome. Prefixed dsx- so it can never collide with product
# classes; the demos themselves use the product's real class names.
PREVIEW_CSS = """
/* ---- preview frame (not part of the design system) ---- */
body{margin:0;font-family:'Pretendard Variable',Pretendard,-apple-system,system-ui,sans-serif}
.dsx-frame{display:grid;gap:14px;padding:14px;align-items:start;
  grid-template-columns:repeat(auto-fit,minmax(360px,1fr))}
.dsx-frame.dsx-phone{grid-template-columns:repeat(auto-fit,minmax(340px,390px));justify-content:start}
.dsx-pane{background:var(--bg-deep);color:var(--text);border:1px solid var(--border);
  border-radius:var(--radius-lg);overflow:hidden;min-width:0}
.dsx-pane>header{font-size:11px;font-weight:700;letter-spacing:.08em;text-transform:uppercase;
  color:var(--text-muted);padding:8px 14px;border-bottom:1px solid var(--border)}
.dsx-demo{padding:16px}
.dsx-demo>nav{margin:-16px -16px 0}
.dsx-stack{display:flex;flex-direction:column;gap:12px}
.dsx-row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.dsx-grid2{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.dsx-sp{display:inline-block;height:14px;background:var(--accent);border-radius:2px}
.dsx-box{display:inline-flex;align-items:center;justify-content:center;width:56px;height:44px;
  background:var(--surface);border:1px solid var(--border);color:var(--text-muted);
  font-size:var(--text-xs);font-weight:700}
/* Form controls, empty state, modal, sheet and the card table are PRODUCT
   classes now (server.py STYLE, promoted 2026-07-28) — the preview only has to
   stage the fixed-position ones and fake a focus ring. */
.dsx-focus{border-color:var(--accent)!important}
.dsx-stage{position:relative;background:var(--bg-deep);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:16px;overflow:hidden}
.dsx-stage .wf-modal-backdrop,.dsx-stage .wf-sheet{position:static}
.dsx-stage .wf-modal-backdrop{padding:0;background:none}
.dsx-stage .wf-sheet{border:1px solid var(--border-bright)}
.dsx-pad{padding:26px 20px;text-align:center}
.wf-empty-icon{font-size:1.8rem}
/* toggle — not a promoted component yet, drawn here for the form-controls card */
.dsx-toggle{display:inline-flex;align-items:center;width:38px;height:22px;padding:2px;
  background:var(--surface-3);border:1px solid var(--border);border-radius:var(--radius-full)}
.dsx-toggle i{width:16px;height:16px;border-radius:50%;background:var(--text-dim);transition:.15s}
.dsx-toggle.dsx-on{background:var(--accent-glow);border-color:var(--accent)}
.dsx-toggle.dsx-on i{background:var(--accent);margin-left:16px}
/* tooltip — forced open so the card shows the tip */
.dsx-tip-open{display:block!important;position:static!important;margin-top:8px}
/* nav demo */
.dsx-nav{position:static;background:var(--surface-2)}
/* the card table only transforms below 768px — force it so the mobile card shows it */
.dsx-phone .wf-cardtable thead{display:none}
.dsx-phone .wf-cardtable tr{display:block;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:10px 12px;margin-bottom:10px}
.dsx-phone .wf-cardtable td{display:flex;justify-content:space-between;gap:12px;align-items:center;
  padding:5px 0;border:0}
.dsx-phone .wf-cardtable td::before{content:attr(data-label);font-size:var(--text-xs);
  font-weight:var(--fw-bold);letter-spacing:.06em;text-transform:uppercase;color:var(--text-muted)}
/* mobile: filter bar */
.dsx-fbar{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.dsx-fbar .dsx-full{grid-column:1/-1}
.dsx-fbar .wf-input{min-height:44px;font-size:16px}
/* token swatches */
.dsx-toks{display:grid;grid-template-columns:repeat(auto-fill,minmax(190px,1fr));gap:8px}
.dsx-tok{display:flex;align-items:center;gap:10px;background:var(--surface);
  border:1px solid var(--border);border-radius:var(--radius-md);padding:8px 10px;min-width:0}
.dsx-tok .sw{width:34px;height:34px;border-radius:var(--radius-sm);
  border:1px solid var(--border-bright);flex-shrink:0}
.dsx-tok .nm{font-size:var(--text-xs);font-weight:var(--fw-semibold);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.dsx-tok .ds{font-size:10px;color:var(--text-muted);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
"""

PAGE = """<!-- @dsCard group="__GROUP__" -->
<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__ · Wayfinder</title>
<link rel="stylesheet" href="../../styles.css">
<link rel="stylesheet" href="../../patterns.css">
<link rel="stylesheet" href="../../preview.css">
</head>
<body>
<div class="dsx-frame__PHONE__">
  <section class="dsx-pane"><header>Dark (default)</header><div class="dsx-demo">__BODY__</div></section>
  <section class="dsx-pane theme-light"><header>Light</header><div class="dsx-demo">__BODY__</div></section>
</div>
</body>
</html>
"""

README = """# Wayfinder Design System

The UX/UI standard for every Wayfinder app. **The reference implementation is
the AMEX Expense Assistant (cardconv)** — before building any UI, check how it
solves the same problem and reuse that pattern.

This project is generated from the running app, not hand-maintained:

| Here | Comes from |
|---|---|
| `styles.css` | `webapp/server.py STYLE` — tokens + nav + base components |
| `patterns.css` | `webapp/services/design.py DEMO_CSS` — the cardconv pattern layer |
| `components/*/` | `sync/components.py` in the `wayfinder-ds` repo |

Regenerate with `python3 sync/build.py` and re-upload. Editing files here
directly means the next sync overwrites you — change the app instead.

## Non-negotiables

1. **Colors are `var(--token)`, always.** A hex literal fails the lint gate,
   because the light theme re-points every token.
2. **Accent discipline** — `--accent` on buttons, links, active tabs and
   badges only, never body text.
3. **English UI copy.** US colleagues use these tools. User-entered data may
   be Korean.
4. **Both themes.** Dark is default; light overrides via
   `:root[data-theme="light"]`.
5. **Mobile is not optional.** Tables become cards, popovers become bottom
   sheets, intake sections collapse.
6. **Design system first.** If no existing pattern fits, don't invent one
   inside an app — add it to the system, then use it.
"""

MOBILE_MD = """# Mobile UX standard

Breakpoint is **768px** for every new rule; 480px is density-only. Assume
touch from 768 down — any hover affordance needs a visible non-hover twin.

- **Chrome budget ≤ 25% of viewport.** Nav is one line and ellipsises. Pill
  tabs never wrap (`flex-wrap:nowrap; overflow-x:auto`, scrollbar hidden,
  active tab auto-centered). Workflow, filter and intake bars scroll away
  rather than sticking.
- **Touch targets ≥ 44px.** Grow the hit area with padding, not the glyph.
  Checkboxes need a global `min-width/min-height:20px` guardrail, which beats
  any per-element `width:Npx`. Everything tappable gets
  `touch-action:manipulation` and a visible `:active` state.
- **Inputs are 16px at ≤768px**, enforced globally with `!important`. Anything
  computed under 16px triggers iOS focus auto-zoom. Never "fix" that with
  `maximum-scale`. Money fields: `type=text inputmode=decimal`, tabular-nums.
- **Tables** — transactional rows become cards (`td[data-label]`), capped at
  ~6 visible fields, with deep edits in a full-width detail panel. Reference
  tables keep their shape inside an `overflow-x:auto` wrapper. The page body
  never scrolls horizontally.
- **Bulk action bars** hide until selection > 0, then fix to the bottom thumb
  zone with `env(safe-area-inset-bottom)` padding; the container gets matching
  bottom padding and floating pills hide via `body:has(...)`.
- **Filter bars** are a strict 2-column grid, search leading full-width, each
  field stacking its label over a full-width control.
- **Popovers never render off-screen** — anchored menus and tooltips become
  fixed bottom sheets at ≤768px.
- **Typing never rebuilds the input under the cursor.** Input events update
  data and computed cells in place; full re-renders only on structural change.
"""

PITFALLS_MD = """# Rules and pitfalls

Hard-won, each from a real bug.

- **JS binds to IDs and classes.** When restyling, preserve IDs, classes and
  row structure so existing bindings survive. The cardconv pill-tab redesign
  kept 113 interactions working by obeying this.
- **`hidden` loses to an author `display`.** Any stylesheet that sets
  `display` on a hideable element needs `[hidden]{display:none!important}`.
- **Empty form values are dropped** by `parse_qs`, so clearing a field needs a
  sentinel (`__clear__`, `none`) that the server maps back to null.
- **No emoji escape sequences in Python strings** — paste the actual
  character; `\\ud83c…` crashes on encode.
- **Stale-render guard** — sequence-check async list renders so a slow
  response can't overwrite a newer filter click.
- **Buttons say what they download** — `⬇ xlsx (SAP)` vs `⬇ xlsx (ledger)`,
  never two identical labels.
- **Every new shared pattern lands in the design system in the same change.**
  The system is the living contract, not an afterthought.
"""


def light_scope(style: str) -> str:
    """Re-emit the light-theme tokens under a class so a pane can opt in."""
    decls = extract.light_theme_block(style)
    return ".theme-light{\n" + decls.strip() + "\n}\n"


def token_demo(tokens) -> str:
    cells = "".join(
        '<div class="dsx-tok"><span class="sw" style="background:var(%s)"></span>'
        '<span style="min-width:0"><div class="nm"><code>%s</code></div>'
        '<div class="ds">%s</div></span></div>' % (name, name, desc)
        for name, desc in tokens
    )
    return '<div class="dsx-toks">' + cells + "</div>"


def build():
    style = extract.global_style()
    # The Pretendard @import is a network fetch the design pane will block —
    # drop it and let the body font-family fall through to system-ui.
    style = re.sub(r"@import url\([^)]*\);\s*", "/* webfont @import dropped for the design pane */\n", style)

    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)

    (DIST / "styles.css").write_text(
        "/* Wayfinder global stylesheet — generated from webapp/server.py STYLE.\n"
        "   Source of truth is the app; edit there, then re-run sync/build.py. */\n"
        + style + "\n" + light_scope(style))
    (DIST / "patterns.css").write_text(
        "/* Wayfinder pattern layer — generated from webapp/services/design.py DEMO_CSS.\n"
        "   These are the cardconv-derived patterns shown on /design. */\n"
        + extract.demo_css())
    (DIST / "preview.css").write_text(PREVIEW_CSS)

    tokens = extract.color_tokens()
    comp_dir = DIST / "components"
    for card in CARDS:
        name = card["name"]
        slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
        body = token_demo(tokens) if card["frame"] == "tokens" else card["html"].strip()
        d = comp_dir / slug
        d.mkdir(parents=True)
        page = (PAGE.replace("__GROUP__", card["group"]).replace("__TITLE__", name)
                    .replace("__PHONE__", " dsx-phone" if card["frame"] == "phone" else "")
                    .replace("__BODY__", body))
        (d / (slug + ".html")).write_text(page)
        (d / (slug + ".md")).write_text(
            "# %s\n\n_%s · %s_\n\n%s\n" % (name, card["group"], card["subtitle"], card["notes"].strip()))

    (DIST / "README.md").write_text(README)
    g = DIST / "guidelines"
    g.mkdir()
    (g / "mobile.md").write_text(MOBILE_MD)
    (g / "pitfalls.md").write_text(PITFALLS_MD)

    print("built %d cards -> %s" % (len(CARDS), DIST))
    return DIST


if __name__ == "__main__":
    build()
