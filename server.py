#!/usr/bin/env python3
import importlib, os, re, sys, json, hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs, quote


def _content_disposition(fname, disp="attachment"):
    """Build a header-safe Content-Disposition. Strips CR/LF/quotes (header
    injection) and adds an RFC 5987 filename* so non-Latin-1 names (e.g.
    Korean) survive — a bare filename="…" is latin-1-encoded and would 500."""
    fname = (fname or "download").replace("\r", "").replace("\n", "").replace('"', "")
    ascii_name = fname.encode("ascii", "ignore").decode("ascii").strip() or "download"
    return f"{disp}; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(fname)}"

SERVICES_DIR = os.path.join(os.path.dirname(__file__), "services")
sys.path.insert(0, os.path.dirname(__file__))

# .env 파일 자동 로드
_env_path = os.path.join(os.path.dirname(__file__), ".env")
if os.path.exists(_env_path):
    with open(_env_path) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and not _line.startswith("#") and "=" in _line:
                _k, _, _v = _line.partition("=")
                os.environ.setdefault(_k.strip(), _v.strip())

from services import auth
from services import _usage

def load_services():
    services = {}
    for f in sorted(os.listdir(SERVICES_DIR)):
        if f.endswith(".py") and not f.startswith("_") and f != "auth.py":
            name = f[:-3]
            mod = importlib.import_module(f"services.{name}")
            if hasattr(mod, "META"):
                services[mod.META["path"]] = mod
    return services

SERVICES = load_services()
# Every app that ships is something the admin can switch on or off, without
# anyone having to remember to list it. See auth.register_services.
auth.register_services([m.META for m in SERVICES.values()])

STYLE = """
@import url('https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable.min.css');
:root {
  /* Dark foundation */
  --bg-deep:#080d14; --surface:#111827; --surface-2:#1a2537; --surface-3:#243044;
  --border:#1e293b; --border-bright:#334155;
  /* --text-muted lands on every surface from --bg-deep to --surface-3; the old
     #64748b only reached 2.79 against the lightest of them. */
  --text:#f1f5f9; --text-muted:#94a3b8; --text-dim:#334155;
  /* Semantic */
  --accent:#38bdf8; --accent-glow:rgba(56,189,248,0.12);
  --on-accent:#080d14;
  --success:#34d399; --warn:#fbbf24; --danger:#f87171; --info:#818cf8;
  /* Legacy aliases (기존 코드 호환) */
  --slate-50:#f8fafc; --slate-100:#f1f5f9; --slate-200:#e2e8f0;
  --slate-300:#cbd5e1; --slate-400:#94a3b8; --slate-500:#64748b;
  --slate-700:#334155; --slate-900:#0f172a;
  --blue-50:#eff6ff; --blue-500:#3b82f6; --sky-400:#38bdf8;
  --green-50:#f0fdf4; --green-500:#22c55e; --green-600:#16a34a;
  --amber-50:#fffbeb; --amber-400:#fbbf24; --amber-500:#f59e0b;
  --red-50:#fef2f2; --red-500:#ef4444;
  /* Group accent colors */
  --group-1:#38bdf8; --group-2:#818cf8; --group-3:#34d399; --group-4:#fb923c; --group-5:#f472b6;
  /* Typography */
  --text-xs:0.72rem; --text-sm:0.82rem; --text-base:0.9rem; --text-md:1rem;
  --fw-medium:500; --fw-semibold:600; --fw-bold:700; --fw-extrabold:800;
  --sp-1:4px; --sp-2:8px; --sp-3:12px; --sp-4:16px; --sp-5:20px; --sp-6:24px;
  --radius-sm:6px; --radius-md:10px; --radius-lg:14px; --radius-xl:18px; --radius-full:9999px;
  --shadow-sm:0 1px 4px rgba(0,0,0,0.4);
  --shadow-md:0 4px 16px rgba(0,0,0,0.5);
  --shadow-lg:0 8px 32px rgba(0,0,0,0.6);
  --btn-h-sm:28px; --btn-h-base:32px; --btn-h-lg:40px;
  --notepad-header:var(--surface-2); --notepad-line:var(--border);
}
/* Light theme — activated by data-theme="light" on <html> (toggle, localStorage) */
:root[data-theme="light"] {
  /* Guide v2, direction A "Deep Sky" — accent only on buttons/links/active
     tabs/badges, never body text. Status colors are a separate axis. */
  --bg-deep:#F6F7F9; --surface:#FFFFFF; --surface-2:#EFF1F4; --surface-3:#E6EAF0;
  --border:#E2E6EC; --border-bright:#CBD5E1;
  --text:#1B2330; --text-muted:#5F6B7A; --text-dim:#98A2B0;
  --accent:#0269A6; --accent-glow:rgba(2,105,166,0.10);
  --on-accent:#FFFFFF;
  --success:#177E42; --warn:#B45309; --danger:#D33A3A; --info:#4F46E5;
  /* Group accents keep their hue but darken — the dark-theme values wash out
     on white (Deal Desk vendor chips, home category bars). */
  --group-1:#0369A1; --group-2:#4F46E5; --group-3:#177E42; --group-4:#C2410C; --group-5:#BE185D;
  --slate-50:#111827; --slate-100:#1C2430; --slate-200:#334155;
  --slate-300:#475569; --slate-400:#66707E; --slate-500:#5A6472;
  --slate-700:#CBD5E1;
  --shadow-sm:0 1px 4px rgba(28,36,48,0.08);
  --shadow-md:0 4px 16px rgba(28,36,48,0.10);
  --shadow-lg:0 8px 32px rgba(28,36,48,0.14);
}
* { box-sizing: border-box; margin: 0; padding: 0; }
/* Reserve the scrollbar gutter so short views (0-item filters etc.) don't
   shift the layout sideways when the vertical scrollbar disappears. */
html { scrollbar-gutter: stable; }
input, textarea, select, button { font-family: inherit; font-size: inherit; }
body { font-family: 'Pretendard Variable', Pretendard, -apple-system, system-ui, sans-serif; background: var(--bg-deep); color: var(--text); line-height: 1.5; -webkit-font-smoothing: antialiased; min-height: 100vh; }

/* Nav */
nav { background: rgba(15,23,42,0.92); backdrop-filter: blur(12px); padding: 13px 32px; display: flex; align-items: center; justify-content: space-between; gap: 12px; position: sticky; top: 0; z-index: 100; border-bottom: 1px solid rgba(255,255,255,0.07); }
/* The bar stays dark in both themes, so the palette inside it does too — under
   the light theme the text tokens darken and disappear into their own bar
   (.nav-user fell to 2.42). Scoped overrides, not new global values. */
/* :not(.app-tabs) — the Momentum tab bar is also a <nav>, but its desktop
   form sits on --surface and has to follow the theme, not this override. */
nav:not(.app-tabs) { --text:#f1f5f9; --text-muted:#94a3b8; --slate-400:#94a3b8; --slate-500:#94a3b8; }
nav a { color: var(--slate-400); text-decoration: none; font-size: 0.875rem; transition: color 0.15s; }
nav a:hover { color: white; }
.nav-brand { color: white; font-weight: 800; font-size: 1.05rem; letter-spacing: -0.02em; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; }
.nav-user { color: var(--slate-500); font-size: 0.82rem; display: flex; align-items: center; gap: 10px; flex-shrink: 0; }
.nav-user a { color: var(--slate-400); padding: 5px 11px; border-radius: 8px; background: rgba(255,255,255,0.05); transition: 0.2s; }
.nav-user a:hover { color: white; background: rgba(255,255,255,0.1); }
.nav-back { color: var(--slate-400); font-size: 0.82rem; text-decoration: none; display: flex; align-items: center; gap: 4px; }
.nav-back:hover { color: white; }

/* Layout */
.container { max-width: 880px; margin: 0 auto; padding: 44px 24px 80px; }
h1 { font-size: 1.75rem; color: var(--text); margin-bottom: 6px; font-weight: 800; letter-spacing: -0.03em; }

/* Dashboard widget */
.dashboard { background: var(--slate-900); background-image: radial-gradient(at 0% 0%, rgba(56,189,248,0.15) 0, transparent 50%), radial-gradient(at 100% 100%, rgba(59,130,246,0.15) 0, transparent 50%); border-radius: var(--radius-xl); padding: 36px 40px; margin-bottom: 48px; color: white; display: flex; justify-content: space-between; align-items: center; gap: 24px; flex-wrap: wrap; box-shadow: var(--shadow-lg); border: 1px solid rgba(255,255,255,0.05); }
/* The hero is a clock: the greeting told you nothing you did not know, and the
   time where you actually are is the one fact a landing page can offer that is
   different every time you look (강프로 2026-08-07). It doubles as the door to
   Time Zones, so it carries a real affordance rather than being a secretly
   clickable block. Colours are literal to the hero, which is dark in both
   themes by design — theme tokens would fight its gradient. */
.dashboard-clock { display:block; text-decoration:none; color:inherit;
  margin:-10px -14px; padding:10px 14px; border-radius:var(--radius-lg);
  transition:background .2s; }
a.dashboard-clock:hover { background:rgba(255,255,255,0.06); }
.dash-time { font-size:2.9rem; font-weight:800; line-height:1; letter-spacing:-0.03em;
  font-variant-numeric:tabular-nums; }
.dash-where { margin-top:9px; color:var(--slate-400); font-size:0.95rem; font-weight:500; }
.dash-cta { margin-top:12px; display:inline-flex; align-items:center; gap:6px;
  font-size:0.72rem; font-weight:700; color:var(--sky-400);
  text-transform:uppercase; letter-spacing:0.07em; }
.dash-arrow { transition:transform .2s; }
a.dashboard-clock:hover .dash-arrow { transform:translateX(4px); }

/* "Add to Home Screen" — a phone-only offer, because on a desktop it is noise.
   Hidden until the browser says it can be installed (or until we recognise iOS,
   which has no such API and needs the two taps spelled out instead). The
   [hidden] pair is not redundant: a class with display would otherwise beat the
   attribute and the link would show on every desktop. */
.wf-install { display:none; margin-top:16px; }
@media (max-width:768px) { .wf-install { display:block; } }
.wf-install[hidden] { display:none; }
.wf-install-btn { display:inline-flex; align-items:center; gap:8px; min-height:44px;
  padding:0 16px; border-radius:var(--radius-full); cursor:pointer;
  background:rgba(255,255,255,0.06); border:1px solid rgba(255,255,255,0.16);
  color:inherit; font-family:inherit; font-size:0.82rem; font-weight:700; }
.wf-install-btn:hover { border-color:var(--sky-400); color:var(--sky-400); }
.wf-install-tip { margin-top:10px; color:var(--slate-400); font-size:0.82rem;
  font-weight:500; line-height:1.5; }
.wf-install-tip[hidden] { display:none; }
.dashboard-stats { display: flex; gap: 14px; flex-wrap: wrap; }
.stat-card { background: rgba(255,255,255,0.04); backdrop-filter: blur(8px); border: 1px solid rgba(255,255,255,0.08); border-radius: var(--radius-lg); padding: 16px 24px; text-align: center; min-width: 100px; transition: 0.2s; }
.stat-card:hover { transform: translateY(-3px); background: rgba(255,255,255,0.07); }
.stat-card .stat-num { font-size: 2rem; font-weight: 800; line-height: 1; margin-bottom: 6px; }
.stat-card .stat-label { font-size: 0.7rem; color: var(--slate-400); font-weight: 600; text-transform: uppercase; letter-spacing: 0.06em; }
.stat-card.highlight .stat-num { color: var(--sky-400); text-shadow: 0 0 20px rgba(56,189,248,0.3); }

/* Category */
.category-section { margin-bottom: 40px; }
.category-title { display:flex; align-items:center; gap:8px; font-size:var(--text-sm); font-weight:var(--fw-bold); color:var(--text); text-transform:none; letter-spacing:.01em; margin-bottom:14px; padding-left:2px; }
.category-title::before { content:""; width:4px; height:1em; border-radius:var(--radius-full); background:var(--slate-500); flex-shrink:0; }
details.bucket-section summary { cursor:pointer; list-style:none; }
details.bucket-section summary::-webkit-details-marker { display:none; }
details.bucket-section:not([open]) .category-title { color:var(--text-muted); }
details.bucket-section .bucket-hint { font-size:var(--text-xs); font-weight:var(--fw-medium); color:var(--text-muted); }
details.bucket-section[open] .service-grid { margin-top:14px; }
.cat-c1::before { background:var(--group-1); }
.cat-c2::before { background:var(--group-2); }
.cat-c3::before { background:var(--group-3); }
.cat-c4::before { background:var(--group-4); }
.cat-c5::before { background:var(--group-5); }

/* Wayfinder cards */
.service-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(185px, 1fr)); gap: 14px; }
.service-card { background: var(--surface); border-radius: var(--radius-lg); padding: 24px; border: 1px solid var(--border); text-decoration: none; color: var(--text); transition: all 0.25s cubic-bezier(0.4,0,0.2,1); display: flex; flex-direction: column; position: relative; overflow: hidden; }
.service-card::before { content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px; background: var(--accent); opacity: 0; transition: 0.2s; }
.service-card:hover { box-shadow: var(--shadow-lg); transform: translateY(-4px); border-color: var(--accent); }
.service-card:hover::before { opacity: 1; }
.service-icon { font-size: 2rem; margin-bottom: 14px; filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3)); }
.service-name { font-weight: 700; font-size: 0.95rem; color: var(--text); margin-bottom: 5px; }
.service-desc { font-size: 0.78rem; color: var(--text-muted); line-height: 1.5; }

/* Todo */
.add-form { display: flex; gap: 8px; margin-bottom: 20px; }
.add-form input { flex: 1; padding: 10px 14px; border: 1px solid #ddd; border-radius: 8px; font-size: 1rem; outline: none; }
.add-form input:focus { border-color: #0ea5e9; }
.add-form button { padding: 10px 18px; background: #0ea5e9; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 0.95rem; }
.stats { display: flex; gap: 10px; margin-bottom: 16px; flex-wrap: wrap; }
.stats span { background: white; padding: 5px 12px; border-radius: 20px; border: 1px solid #e2e8f0; font-size: 0.85rem; color: #64748b; }
.stats .done-c { color: #16a34a; }
/* .todo-list is still worn by the notepad body; the row rules that used to go
   with it (.todo-item/.tid/.title/.date/.actions) had no wearer left — the
   notepad markup names its own — and were pre-dark-theme anyway. */
.todo-list { display: flex; flex-direction: column; gap: 8px; }
.btn {
  display:inline-flex; align-items:center; justify-content:center;
  height:var(--btn-h-base); padding:0 12px; border:none;
  border-radius:var(--radius-sm); font-size:var(--text-sm);
  font-weight:var(--fw-semibold); cursor:pointer;
  transition:background 0.15s,opacity 0.15s,transform 0.1s,color 0.15s,border-color 0.15s;
  white-space:nowrap; text-decoration:none; flex-shrink:0;
}
.btn-sm { height:var(--btn-h-sm); padding:0 8px; font-size:var(--text-xs); }
.btn-lg { height:var(--btn-h-lg); padding:0 20px; font-size:var(--text-base); font-weight:var(--fw-bold); }
.btn-primary   { background:var(--accent); color:var(--on-accent); font-weight:700; }
.btn-secondary { background:var(--surface-2); color:var(--text); border:1px solid var(--border); }
.btn-ghost     { background:transparent; color:var(--text-muted); border:1px solid var(--border); }
.btn-success   { background:rgba(52,211,153,0.12); color:var(--success); border:1px solid rgba(52,211,153,0.3); }
/* A destructive action has to read as destructive without being hovered —
   there is no hover on touch, and muted grey reads as disabled. */
.btn-danger    { background:transparent; color:var(--danger); }
.btn-accent    { background:var(--accent); color:var(--on-accent); font-weight:700; }
.btn-warn      { background:rgba(251,191,36,0.12); color:var(--warn); border:1px solid rgba(251,191,36,0.3); }
.btn-primary:hover   { opacity:0.88; transform:translateY(-1px); box-shadow:0 4px 12px rgba(56,189,248,0.3); }
.btn-secondary:hover { border-color:var(--accent); color:var(--accent); }
.btn-ghost:hover     { border-color:var(--accent); color:var(--accent); background:var(--accent-glow); }
.btn-success:hover   { background:var(--success); color:var(--on-accent); border-color:transparent; }
.btn-danger:hover    { color:var(--danger); background:rgba(248,113,113,0.12); }
.btn-accent:hover    { opacity:0.88; transform:translateY(-1px); box-shadow:0 4px 12px rgba(56,189,248,0.3); }
@media (max-width:600px) {
  .btn { height:40px; padding:0 14px; }
  .btn-sm { height:36px; padding:0 10px; }
  .btn-lg { height:48px; }
}
/* An action that lives inside a strip of label chips — "→ Today" on an overdue
   task, and anything else that answers a chip instead of describing one.
   Three rules make it work, and they are the whole pattern:
     1. Fill is the signal. Every label chip in these strips is an outline
        (a tinted label loses AA in the light theme), so the one filled pill is
        the only thing you can press, and nothing else has to change to say so.
     2. Accent means pressable. Status colors describe — danger is "you missed
        this" — so an action tinted danger would melt back into the chip it
        answers. Accent is reserved for the invitation.
     3. Size is constant. It is exactly the chips' 20px in every viewport, so
        the strip stays one line; touch comfort comes from the invisible hit
        box below, never from a bigger pill. */
.chip-action {
  display:inline-flex; align-items:center; gap:4px; position:relative;
  height:20px; padding:0 9px; border:none; border-radius:var(--radius-full);
  background:var(--accent-glow); color:var(--accent); font-family:inherit;
  font-size:var(--text-xs); font-weight:var(--fw-bold); line-height:1;
  cursor:pointer; white-space:nowrap; transition:background .15s,color .15s;
}
/* Grows down and sideways, not up: a hit box centred on a 20px pill would
   overhang the task title above it and steal its taps. Below the strip is the
   row's own bottom padding, which is dead space. 42px tall — under the 44px
   floor by 2, which is the floor for primary controls; this is a shortcut for
   something the detail sheet still does in full. */
.chip-action::after {
  content:""; position:absolute; left:-8px; right:-8px; top:-8px; bottom:-14px;
}
.chip-action:hover { background:var(--accent); color:var(--on-accent); }
.chip-action:active { transform:scale(0.96); }

.empty { text-align: center; color: var(--text-muted); padding: 48px 0; }

/* Tap ergonomics (all viewports — harmless on desktop) */
a, button, select, label, input[type=checkbox], input[type=radio] { touch-action: manipulation; }
.btn:active { transform: scale(0.97); }

/* Progress — for work that runs long enough that a still screen reads as broken.
   A receipt PDF takes ~0.7s per receipt, so a hundred of them is over a minute
   of nothing happening. Indeterminate by design: most of our slow work cannot
   report a percentage honestly, and a fake bar is worse than none. */
.wf-progress { position:fixed; left:0; right:0; top:0; z-index:10000; height:3px;
  background:var(--surface-3); overflow:hidden; display:none; }
.wf-progress.is-on { display:block; }
.wf-progress::after { content:""; position:absolute; inset:0 auto 0 0; width:40%;
  background:linear-gradient(90deg,transparent,var(--accent),transparent);
  animation:wf-progress-slide 1.1s ease-in-out infinite; }
@keyframes wf-progress-slide { 0% { left:-40%; } 100% { left:100%; } }
.wf-progress-note { position:fixed; left:50%; translate:-50% 0; top:16px; z-index:10000;
  display:none; align-items:center; gap:10px; max-width:min(92vw,420px);
  padding:10px 16px; background:var(--surface); color:var(--text);
  border:1px solid var(--border-bright); border-radius:var(--radius-full);
  box-shadow:var(--shadow-lg); font-size:var(--text-sm); font-weight:var(--fw-semibold); }
.wf-progress-note.is-on { display:flex; }
.wf-spinner { width:14px; height:14px; flex-shrink:0; border-radius:50%;
  border:2px solid var(--border-bright); border-top-color:var(--accent);
  animation:wf-spin .7s linear infinite; }
@keyframes wf-spin { to { transform:rotate(360deg); } }
/* A button that kicked off long work says so and stops taking second clicks. */
.btn.is-busy { pointer-events:none; opacity:.72; }
.btn.is-busy::before { content:""; width:13px; height:13px; margin-right:7px;
  border-radius:50%; border:2px solid currentColor; border-top-color:transparent;
  animation:wf-spin .7s linear infinite; }
@media (prefers-reduced-motion:reduce) {
  .wf-progress::after, .wf-spinner, .btn.is-busy::before { animation:none; }
  .wf-progress::after { left:0; width:100%; opacity:.5; }
}

/* Floating "back to Wayfinder" pill, injected into every app page (server.py).
   Tokens, not fixed colors — a dark pill on a light page was the whole bug. */
.wf-back { position:fixed; left:16px; bottom:16px; z-index:9999; display:inline-flex;
  align-items:center; gap:6px; padding:8px 14px; background:var(--surface);
  color:var(--text-muted); border:1px solid var(--border-bright);
  border-radius:var(--radius-full); font-size:var(--text-xs); font-weight:var(--fw-semibold);
  text-decoration:none; backdrop-filter:blur(6px); box-shadow:var(--shadow-md); }
.wf-back:hover { color:var(--accent); border-color:var(--accent); }
/* Same corner problem as .wf-back: inline styles could not be moved out of the
   way of the tab bar, so the toggle is a class now too. */
.wf-theme-btn { position:fixed; right:16px; bottom:16px; z-index:9999; width:40px; height:40px;
  border-radius:50%; border:1px solid var(--border-bright); cursor:pointer;
  background:var(--surface); color:var(--text); font-size:1.02rem; line-height:1;
  box-shadow:var(--shadow-md); }
.wf-theme-btn:hover { border-color:var(--accent); }
@media (max-width: 768px) { .wf-back { min-height:44px; padding:8px 16px; } }

/* Mobile guardrails — docs/mobile_ux_guideline.md. 768px = standard mobile breakpoint.
   16px input floor kills iOS focus auto-zoom; min-width beats any width:Npx on
   undersized checkboxes without touching per-component CSS. */
@media (max-width: 768px) {
  input:not([type=checkbox]):not([type=radio]):not([type=file]):not([type=range]),
  select, textarea { font-size: 16px !important; min-height: 44px; }
  input[type=checkbox], input[type=radio] { min-width: 20px; min-height: 20px; }
  .nav-brand { font-size: 0.95rem; }
}

/* Mobile responsive */
@media (max-width: 600px) {
  .container { padding: 24px 16px calc(60px + env(safe-area-inset-bottom, 0px)); }
  nav { padding: 10px 16px; }
  .nav-user { gap: 6px; }
  .nav-user a { padding: 8px 12px; min-height: 44px; display: inline-flex; align-items: center; }
  .dashboard { padding: 24px 20px; flex-direction: column; gap: 16px; }
  .dashboard-clock { align-self:flex-start; }
  .dash-time { font-size: 2.3rem; }
  .service-grid { grid-template-columns: repeat(2, 1fr); gap: 10px; }
  .service-card { padding: 16px; }
  .service-icon { font-size: 1.5rem; margin-bottom: 8px; }
  .service-name { font-size: 0.85rem; }
  .service-desc { display: none; }
  .add-form { flex-direction: column; }
  .add-form input, .add-form button { width: 100%; }
  .add-form input { font-size: 1rem; min-height: 44px; }
  .add-form button { min-height: 44px; font-size: 1rem; }
  .todo-item { flex-wrap: wrap; padding: 12px 14px; }
  .actions { width: 100%; justify-content: flex-end; margin-top: 8px; flex-wrap: wrap; gap: 6px; }
  .btn { padding: 10px 14px; font-size: 0.85rem; min-height: 44px; display: inline-flex; align-items: center; justify-content: center; }
  .stat-card { padding: 12px 16px; min-width: 80px; }
  .stat-card .stat-num { font-size: 1.6rem; }
  h1 { font-size: 1.4rem; }
}
@media (max-width: 400px) {
  .service-grid { grid-template-columns: 1fr 1fr; }
  .dashboard-stats { gap: 8px; }
}

/* === Adaptive Today Hub (dashboard) === */
.wf-stat-grid{display:grid;grid-template-columns:repeat(4,1fr);gap:16px;margin-bottom:24px}
.wf-stat{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px 18px;box-shadow:var(--shadow-sm)}
.wf-stat-value{font-size:2.2rem;font-weight:800;letter-spacing:-.03em;line-height:1;color:var(--text)}
.wf-stat-sub{font-size:1rem;font-weight:500;color:var(--text-muted);margin-left:2px}
.wf-stat-label{font-size:.78rem;color:var(--text-muted);font-weight:600;margin-top:8px;text-transform:uppercase;letter-spacing:.05em}
.wf-today-head{display:flex;align-items:center;justify-content:space-between;margin-bottom:12px}
.wf-today-title{font-size:1rem;font-weight:800;color:var(--text)}
.wf-today-list{display:flex;flex-direction:column;gap:8px}
.wf-today-item{display:flex;align-items:center;gap:12px;padding:12px 14px;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);transition:.15s;margin:0}
.wf-today-item:hover{border-color:var(--accent);background:var(--surface-3)}
.wf-today-item.wf-done{opacity:.5}
.wf-today-text{flex:1;font-size:.92rem;font-weight:600;color:var(--text);text-align:left}
.wf-today-item.wf-done .wf-today-text{text-decoration:line-through;color:var(--text-muted)}
.wf-check{width:26px;height:26px;flex-shrink:0;border-radius:50%;border:2px solid var(--border);background:transparent;cursor:pointer;color:var(--on-accent);font-size:.85rem;font-weight:800;display:flex;align-items:center;justify-content:center;transition:.15s;padding:0;position:relative}
/* The circle stays 26px; the tap area is extended to 44 with a pseudo
   element so rows keep their spacing. */
.wf-check::after{content:'';position:absolute;top:50%;left:50%;translate:-50% -50%;width:max(100%,44px);height:max(100%,44px);border-radius:50%}
.wf-check:hover{border-color:var(--accent)}
.wf-check--on{background:linear-gradient(135deg,var(--accent),var(--info));border-color:transparent}
.wf-streak-chip{font-size:.72rem;color:var(--warn);font-weight:700;white-space:nowrap;background:rgba(251,191,36,.1);padding:2px 8px;border-radius:var(--radius-full);border:1px solid rgba(251,191,36,.3)}
.wf-next-cta{display:flex;align-items:center;gap:10px;margin-top:14px;padding:12px 14px;border:1px dashed var(--border);border-radius:var(--radius-md);color:var(--text-muted);font-size:.86rem}
.wf-home-empty{display:grid;grid-template-columns:1fr 1fr;gap:16px}
.wf-empty-card{padding:28px 24px;text-align:center}
.wf-empty-icon{font-size:2.4rem;margin-bottom:10px}
.wf-empty-title{font-size:1rem;font-weight:800;color:var(--text);margin-bottom:14px}
.wf-empty-form{display:flex;flex-direction:column;gap:10px}
.wf-empty-input{padding:10px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--surface-2);color:var(--text);font-size:.9rem}
.wf-empty-input:focus{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-glow)}
@media(max-width:600px){
  .wf-stat-grid{grid-template-columns:1fr 1fr;gap:10px}
  .wf-stat{padding:14px 12px}.wf-stat-value{font-size:1.7rem}
  .wf-home-empty{grid-template-columns:1fr}
}

/* === Shared components (2026-07-28) ==========================================
   Promoted out of cardconv so apps stop re-inventing them. Demos and the rules
   that go with each one live on /design §3. The mobile guardrails above already
   cover type size and tap targets — these only add shape. */

/* Form controls — recessed on --bg-deep inside a --surface container */
.wf-field{display:flex;flex-direction:column;gap:4px;min-width:0}
.wf-label{font-size:var(--text-xs);font-weight:var(--fw-bold);letter-spacing:.06em;
  text-transform:uppercase;color:var(--text-muted)}
.wf-input{background:var(--bg-deep);border:1px solid var(--border);border-radius:var(--radius-md);
  color:var(--text);padding:8px 10px;font-size:var(--text-sm);font-family:inherit;width:100%}
.wf-input:focus{outline:none;border-color:var(--accent)}
.wf-input:disabled{color:var(--text-dim);background:var(--surface-2)}
/* Money and any other column that has to line up between rows. */
.wf-input.wf-num{text-align:right;font-variant-numeric:tabular-nums}
.wf-checkbox{display:inline-flex;align-items:center;gap:6px;font-size:var(--text-sm);
  color:var(--text-muted);cursor:pointer}

/* Empty state — self-sufficient on its own, transparent when a card wraps it */
.wf-empty-card:not(.notepad-card){background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg)}
.wf-empty-sub{font-size:var(--text-sm);color:var(--text-muted);margin:-6px 0 14px}
.wf-empty-actions{display:flex;gap:8px;justify-content:center;flex-wrap:wrap}

/* Modal — states the consequence; the destructive action is never the default */
/* The scrim stays dark in both themes — a light scrim doesn't read as "the
   page behind is inert", which is the one job a scrim has. */
.wf-modal-backdrop{position:fixed;inset:0;z-index:300;background:rgba(8,13,20,.6);
  display:flex;align-items:center;justify-content:center;padding:20px}
.wf-modal{background:var(--surface);border:1px solid var(--border-bright);
  border-radius:var(--radius-lg);box-shadow:var(--shadow-lg);padding:18px 20px;
  width:100%;max-width:440px;max-height:85vh;overflow-y:auto}
.wf-modal-title{font-size:var(--text-base);font-weight:var(--fw-bold);margin:0 0 8px}
.wf-modal-body{font-size:var(--text-sm);color:var(--text-muted);line-height:1.6;margin:0 0 16px}
.wf-modal-actions{display:flex;gap:8px;justify-content:flex-end;flex-wrap:wrap}

/* Bottom sheet — what an anchored popover becomes on a narrow viewport */
.wf-sheet{position:fixed;left:0;right:0;bottom:0;z-index:250;background:var(--surface);
  border-top:1px solid var(--border-bright);border-radius:var(--radius-xl) var(--radius-xl) 0 0;
  box-shadow:var(--shadow-lg);padding:16px 16px calc(16px + env(safe-area-inset-bottom,0px));
  max-height:80vh;overflow-y:auto}
.wf-sheet-title{font-size:var(--text-base);font-weight:var(--fw-bold);margin-bottom:12px}

/* Transactional table that becomes cards on mobile — every td needs data-label */
.wf-cardtable{width:100%;border-collapse:collapse;font-size:var(--text-sm)}
.wf-cardtable th{text-align:left;font-size:var(--text-xs);font-weight:var(--fw-bold);
  letter-spacing:.06em;text-transform:uppercase;color:var(--text-muted);
  padding:8px 10px;border-bottom:1px solid var(--border)}
.wf-cardtable td{padding:9px 10px;border-bottom:1px solid var(--border)}

@media (max-width: 768px){
  /* A modal at phone width is a bottom sheet — same rule as every popover. */
  .wf-modal-backdrop{align-items:flex-end;padding:0}
  .wf-modal{max-width:none;border-radius:var(--radius-xl) var(--radius-xl) 0 0;
    border-left:0;border-right:0;border-bottom:0;
    padding-bottom:calc(18px + env(safe-area-inset-bottom,0px))}
  .wf-modal-actions .btn{flex:1}
  /* Rows become cards: the header goes away and each cell labels itself. */
  .wf-cardtable thead{display:none}
  .wf-cardtable tr{display:block;background:var(--surface);border:1px solid var(--border);
    border-radius:var(--radius-lg);padding:10px 12px;margin-bottom:10px}
  .wf-cardtable td{display:flex;justify-content:space-between;align-items:center;gap:12px;
    padding:5px 0;border:0}
  .wf-cardtable td::before{content:attr(data-label);font-size:var(--text-xs);
    font-weight:var(--fw-bold);letter-spacing:.06em;text-transform:uppercase;
    color:var(--text-muted);flex-shrink:0}
  .wf-cardtable td[data-label=""]::before{content:none}
}
"""

CSS_VER = hashlib.md5(STYLE.encode()).hexdigest()[:8]

ICON_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 192 192">
  <rect width="192" height="192" rx="40" fill="#0f172a"/>
  <circle cx="96" cy="96" r="56" fill="none" stroke="#38bdf8" stroke-width="4"/>
  <polygon points="96,44 104,96 96,90 88,96" fill="#38bdf8"/>
  <polygon points="96,148 88,96 96,102 104,96" fill="#64748b"/>
  <circle cx="96" cy="96" r="8" fill="white"/>
</svg>"""

MANIFEST = json.dumps({
    "name": "Wayfinder",
    "short_name": "Wayfinder",
    "description": "Personal productivity hub",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#f8fafc",
    "theme_color": "#0f172a",
    "orientation": "portrait-primary",
    "icons": [
        {"src": "/icons/icon.svg", "sizes": "any", "type": "image/svg+xml", "purpose": "any"}
    ],
    "shortcuts": [
        {"name": "Tasks", "url": "/momentum?tab=tasks", "description": "Task management"},
        {"name": "Habits", "url": "/momentum?tab=habits", "description": "Habit tracking"}
    ]
}, ensure_ascii=False, indent=2)

SW_JS = f"""
const CACHE = 'wayfinder-{CSS_VER}';
const STATIC = ['/static/style.css?v={CSS_VER}', '/manifest.json', '/icons/icon.svg'];

self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(STATIC)));
  self.skipWaiting();
}});
self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
}});
self.addEventListener('fetch', e => {{
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== location.origin) return;
  if (url.pathname === '/static/style.css') {{
    e.respondWith(caches.match('/static/style.css?v={CSS_VER}').then(c => c || fetch(e.request)));
    return;
  }}
  if (STATIC.includes(url.pathname + url.search) || STATIC.includes(url.pathname)) {{
    e.respondWith(caches.match(e.request).then(c => c || fetch(e.request)));
    return;
  }}
  e.respondWith(
    fetch(e.request).catch(() =>
      new Response('<h2 style="font-family:sans-serif;padding:40px">You are offline. Please check your internet connection.</h2>',
        {{headers: {{'Content-Type': 'text/html; charset=utf-8'}}}})
    )
  );
}});

self.addEventListener('push', function(event) {{
  const data = event.data ? event.data.json() : {{}};
  event.waitUntil(self.registration.showNotification(data.title || 'Wayfinder', {{
    body: data.body || '',
    icon: '/icons/icon.svg',
    badge: '/icons/icon.svg',
    data: {{ url: data.url || '/cardconv/ledger' }}
  }}));
}});

self.addEventListener('notificationclick', function(event) {{
  event.notification.close();
  event.waitUntil(clients.openWindow(event.notification.data.url || '/cardconv/ledger'));
}});
"""

APP_TAB_CSS = """
<style>
/* bottom is the visible bottom, not the document's. A fixed element anchors to
   the layout viewport, which on a phone stays tall while the browser's own
   address bar and toolbar cover the screen — so the bar sat under them until
   you scrolled and the chrome collapsed. --tabs-vv-gap is the difference, kept
   current by the script below. */
.app-tabs{--tab-ink:#94a3b8;--tab-accent:#38bdf8;position:fixed!important;top:auto!important;bottom:var(--tabs-vv-gap,0px)!important;left:0;right:0;transition:bottom .15s ease;height:auto;background:rgba(8,13,20,0.97);backdrop-filter:blur(20px);border-top:1px solid rgba(255,255,255,0.06);border-bottom:none;display:flex!important;justify-content:stretch;z-index:200;padding:8px 8px calc(8px + env(safe-area-inset-bottom,0));gap:4px}
.app-tab{flex:1;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;padding:8px 4px;color:var(--tab-ink);text-decoration:none;font-size:0.6rem;font-weight:700;letter-spacing:0.05em;text-transform:uppercase;border-radius:12px;transition:all 0.2s}
.app-tab:hover{color:rgba(255,255,255,0.7);background:rgba(255,255,255,0.04)}
.app-tab.active{color:var(--tab-accent);background:rgba(56,189,248,0.12)}
.app-tab-icon{font-size:1.3rem;line-height:1;transition:transform 0.2s}
.app-tab.active .app-tab-icon{filter:drop-shadow(0 0 8px rgba(56,189,248,0.7));transform:translateY(-2px)}
body{padding-bottom:calc(72px + env(safe-area-inset-bottom,0px))!important}
/* The floating pill and the theme toggle sit at bottom:16px, which on mobile is
   inside the tab bar — they were covering the first and last tab. Lift them
   above it wherever the bar exists. */
body:has(.app-tabs) .wf-back,body:has(.app-tabs) .wf-theme-btn{bottom:calc(80px + env(safe-area-inset-bottom,0px))}
/* A sheet owns the bottom of the screen while it is open — the pill and the
   toggle sat on top of its Save button. */
body:has(.tk-sheet.is-on) .wf-back,body:has(.tk-sheet.is-on) .wf-theme-btn{display:none}
@media(min-width:768px){
  body:has(.app-tabs) .wf-back,body:has(.app-tabs) .wf-theme-btn{bottom:16px}
  .app-tabs{--tab-ink:var(--text-muted);--tab-accent:var(--accent);position:sticky!important;top:0!important;bottom:auto!important;height:auto;flex-direction:row;justify-content:center;gap:6px;background:var(--surface);border-top:none;border-bottom:1px solid var(--border);padding:10px 16px;box-shadow:var(--shadow-sm)}
  .app-tab{flex:0 0 auto;flex-direction:row;gap:8px;padding:8px 18px;border-radius:var(--radius-full);font-size:.82rem;text-transform:none;letter-spacing:0}
  .app-tab-icon{font-size:1.05rem}
  .app-tab.active{background:var(--accent);color:var(--on-accent)}
  .app-tab.active .app-tab-icon{transform:none;filter:none}
  body{padding-bottom:0!important;padding-top:0!important}
}
</style>
"""

def app_tabs(active, user=None):
    """Tab bar for the Work Hub.

    `active` is a tab key, but the old routes still pass their own path (and
    pov.py passes something that is not a tab at all), so those are accepted
    and mapped. The three tabs are one service now — a single access check.
    """
    import services.auth as auth
    tabs = [("tasks", "✅", "Tasks"), ("habits", "🏃", "Habits")]
    active = {"/dashboard": "tasks", "/todo": "tasks", "/habit": "habits"}.get(active, active)
    if not (auth.is_admin(user) or auth.has_service_access(user, "/momentum")):
        return ""
    html = APP_TAB_CSS + '<nav class="app-tabs">'
    for key, icon, label in tabs:
        cls = "app-tab active" if active == key else "app-tab"
        html += (f'<a href="/momentum?tab={key}" class="{cls}">'
                 f'<span class="app-tab-icon">{icon}</span>{label}</a>')
    html += "</nav>" + APP_TAB_VV_JS
    return html


# Keep the tab bar on the part of the screen you can actually see. Samsung
# Internet (and every other mobile browser) reports the visible box through
# visualViewport; the gap between that and the layout viewport is exactly how
# far the bar has to rise. When the gap is large the keyboard is up, and a tab
# bar riding on top of the keyboard would cover the field you are typing in —
# so it stands down until the keyboard closes.
APP_TAB_VV_JS = """
<script>
(function () {
  var vv = window.visualViewport;
  if (!vv) return;
  var nav = document.querySelector('.app-tabs');
  if (!nav) return;
  var KEYBOARD = 200;
  function fit() {
    var gap = document.documentElement.clientHeight - (vv.height + vv.offsetTop);
    if (!(gap > 0)) gap = 0;
    if (gap > KEYBOARD) { nav.style.visibility = 'hidden'; return; }
    nav.style.visibility = '';
    document.documentElement.style.setProperty('--tabs-vv-gap', Math.round(gap) + 'px');
  }
  vv.addEventListener('resize', fit);
  vv.addEventListener('scroll', fit);
  window.addEventListener('orientationchange', function () { setTimeout(fit, 250); });
  fit();
})();
</script>"""


VIEWPORT_META = ('<meta name="viewport" content="width=device-width,'
                'initial-scale=1,viewport-fit=cover">')
_VIEWPORT_RE = re.compile(r'<meta\s+name="viewport"[^>]*>', re.I)

PWA_INJECT = (
    '<link rel="manifest" href="/manifest.json">'
    '<meta name="theme-color" content="#0f172a">'
    '<meta name="apple-mobile-web-app-capable" content="yes">'
    '<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">'
    '<meta name="apple-mobile-web-app-title" content="Wayfinder">'
    '<link rel="apple-touch-icon" href="/icons/icon.svg">'
    "<script>if('serviceWorker'in navigator)navigator.serviceWorker.register('/sw.js');</script>"
    "<script>try{var _t=localStorage.getItem('wf-theme');if(_t)document.documentElement.dataset.theme=_t;}catch(e){}</script>"
)

# Small floating "back to home" link injected into every app page (not the home/login,
# which carry the <!--wf-root--> sentinel).
WAYFINDER_BACK = (
    '<a href="/" class="wf-back" title="Back to Wayfinder">🧭 Wayfinder</a>'
)

# Progress bar + the helper that drives it. Downloads are the awkward case:
# the browser handles them, so JS never sees them finish. The server stamps a
# cookie on the response and we watch for it — the standard trick, and the only
# one that works without buffering the whole file in memory.
PROGRESS_INJECT = (
    '<div class="wf-progress" id="wfProgress"></div>'
    '<div class="wf-progress-note" id="wfProgressNote">'
    '<span class="wf-spinner"></span><span id="wfProgressText"></span></div>'
    "<script>"
    "window.wfProgress={"
    "start:function(msg){var b=document.getElementById('wfProgress'),"
    "n=document.getElementById('wfProgressNote'),t=document.getElementById('wfProgressText');"
    "if(b)b.classList.add('is-on');"
    "if(n&&msg){t.textContent=msg;n.classList.add('is-on');}},"
    "stop:function(){var b=document.getElementById('wfProgress'),"
    "n=document.getElementById('wfProgressNote');"
    "if(b)b.classList.remove('is-on');if(n)n.classList.remove('is-on');"
    "document.querySelectorAll('.btn.is-busy').forEach(function(e){e.classList.remove('is-busy')});},"
    # Watch for the server's cookie, then clear the progress UI.
    "_watch:function(id,msg){wfProgress.start(msg||'Preparing your download\u2026');"
    "var t0=Date.now();var iv=setInterval(function(){"
    "if(document.cookie.indexOf('wf_dl='+id)>-1){clearInterval(iv);"
    "document.cookie='wf_dl=;path=/;max-age=0';wfProgress.stop();}"
    # Never leave the page stuck spinning if a download died silently.
    "else if(Date.now()-t0>900000){clearInterval(iv);wfProgress.stop();}},400);},"
    # For a real link.
    "download:function(el,msg){var id='d'+Date.now();"
    "var u=new URL(el.href,location.href);u.searchParams.set('dl',id);el.href=u.toString();"
    "el.classList.add('is-busy');wfProgress._watch(id,msg);return true;},"
    # For code that navigates to a download itself (window.location = ...).
    "downloadUrl:function(url,msg){var id='d'+Date.now();"
    "var sep=url.indexOf('?')>-1?'&':'?';wfProgress._watch(id,msg);"
    "window.location=url+sep+'dl='+id;return id;},"
    # Several attachments at once: one watcher, iframes share the token.
    "downloadAll:function(urls,msg){var id='d'+Date.now();wfProgress._watch(id,msg);"
    "urls.forEach(function(u){var sep=u.indexOf('?')>-1?'&':'?';"
    "var f=document.createElement('iframe');f.style.display='none';"
    "f.src=u+sep+'dl='+id;document.body.appendChild(f);"
    "setTimeout(function(){f.remove()},900000);});return id;}};"
    "</script>"
)

THEME_TOGGLE = (
    '<button id="wfThemeBtn" class="wf-theme-btn" title="Toggle light/dark" '
    'onclick="wfToggleTheme()"></button>'
    "<script>function wfThemeIcon(){var l=document.documentElement.dataset.theme==='light';"
    "var b=document.getElementById('wfThemeBtn');if(b)b.textContent=l?'🌙':'☀️';}"
    "function wfToggleTheme(){var r=document.documentElement;"
    "r.dataset.theme=(r.dataset.theme==='light')?'dark':'light';"
    "try{localStorage.setItem('wf-theme',r.dataset.theme)}catch(e){}wfThemeIcon();}"
    "wfThemeIcon();</script>"
)

CATEGORIES = {
    "💼 업무":    ["/momentum", "/toast", "/cardconv", "/sow", "/matters", "/aeo",
                  "/llm-check", "/timezones"],
    "🏠 개인":    [],
    "🛠 팀 도구": ["/design"],
    "⚙️ 관리":    ["/admin"],
}

def wayfinder(user):
    user_is_admin = auth.is_admin(user)

    # The hero is a clock now, and the clock is the door to Time Zones — but
    # only for someone who can walk through it. Sending a user without access to
    # a login redirect is worse than not offering the link.
    has_timezones = user_is_admin or auth.has_service_access(user, "/timezones")

    # 서비스 path → META 매핑 (일반 유저는 권한 있는 서비스만)
    svc_map = {}
    for path, svc in SERVICES.items():
        m = svc.META
        if m.get("hidden"):
            continue
        if path == "/pov":  # POV inactive — show in dormant bucket (pov.py WIP stays uncommitted)
            m = dict(m, bucket=True)
        if m.get("admin_only") and not user_is_admin:
            continue
        if not user_is_admin and not auth.has_service_access(user, path):
            continue
        svc_map[path] = m

    # Bucket: dormant initiatives — routes stay alive, home shows them collapsed
    bucket_map = {p: m for p, m in svc_map.items() if m.get("bucket")}
    svc_map = {p: m for p, m in svc_map.items() if not m.get("bucket")}

    def _svc_card(m):
        return (f'<a class="service-card" href="{m.get("home_href", m["path"])}">'
                f'<div class="service-icon">{m["icon"]}</div>'
                f'<div class="service-name">{m["name"]}</div>'
                f'<div class="service-desc">{m["description"]}</div>'
                f'</a>')

    # 2-Track 그룹 렌더링 (admin·일반 공통 — svc_map이 이미 권한 필터링함)
    sections_html = ""
    rendered = set()
    for i, (cat_name, paths) in enumerate(CATEGORIES.items(), start=1):
        cards = "".join(_svc_card(svc_map[p]) for p in paths if p in svc_map)
        if cards:
            sections_html += f'<div class="category-section"><div class="category-title cat-c{i}">{cat_name}</div><div class="service-grid">{cards}</div></div>'
            rendered.update(p for p in paths if p in svc_map)
    extra = "".join(_svc_card(m) for p, m in svc_map.items() if p not in rendered)
    if extra:
        sections_html += f'<div class="category-section"><div class="category-title cat-c5">기타</div><div class="service-grid">{extra}</div></div>'
    if not sections_html:
        sections_html = '<div style="padding:40px;text-align:center;color:var(--text-muted)">접근 가능한 서비스가 없습니다. 관리자에게 문의하세요.</div>'
    if bucket_map:
        b_cards = "".join(_svc_card(m) for m in bucket_map.values())
        sections_html += (
            '<details class="category-section bucket-section">'
            f'<summary><div class="category-title">🗄 Bucket <span class="bucket-hint">휴면 이니셔티브 {len(bucket_map)}개 — 클릭해서 열기</span></div></summary>'
            f'<div class="service-grid">{b_cards}</div></details>'
        )

    # Projects section (admin only)
    projects_html = ""
    if user_is_admin:
        try:
            from services.dashboard import _load_projects, STATUS_META
            projects = _load_projects()
            proj_cards = ""
            for p in projects:
                sm = STATUS_META.get(p.get("status", "planning"), STATUS_META["planning"])
                link = p.get("url", "")
                link_btn = f'<a href="{link}" style="font-size:.72rem;color:var(--accent);text-decoration:none;font-weight:600">Open →</a>' if link else ""
                status_opts = "".join(
                    f'<option value="{s}" {"selected" if s == p.get("status") else ""}>{STATUS_META[s]["label"]}</option>'
                    for s in STATUS_META
                )
                proj_cards += f'''<div style="background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);padding:14px 16px;display:flex;align-items:center;gap:12px">
  <span style="font-size:1.4rem">{p.get("emoji","📌")}</span>
  <div style="flex:1;min-width:0">
    <div style="font-size:.9rem;font-weight:700;color:var(--text)">{p["name"]}</div>
    <div style="font-size:.75rem;color:var(--text-muted);margin-top:2px">{p.get("desc","")}</div>
  </div>
  <div style="display:flex;align-items:center;gap:8px;flex-shrink:0">
    <span style="font-size:.7rem;font-weight:700;padding:3px 10px;border-radius:99px;color:{sm["color"]};background:{sm["bg"]};border:1px solid {sm["border"]}">{sm["label"]}</span>
    <form method="POST" action="/dashboard/project/status" style="display:inline"><input type="hidden" name="id" value="{p["id"]}"><select name="status" onchange="this.form.submit()" style="font-size:.7rem;padding:2px 4px;border-radius:4px;border:1px solid var(--border);background:var(--surface);color:var(--text-muted)">{status_opts}</select></form>
    {link_btn}
  </div>
</div>'''
            add_form = '''<form method="POST" action="/dashboard/project/add" style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;margin-top:4px">
  <input type="text" name="emoji" placeholder="📌" style="width:44px;padding:6px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.8rem">
  <input type="text" name="name" placeholder="Project name" required style="flex:1;min-width:140px;padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.8rem">
  <select name="status" style="padding:6px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.8rem"><option value="planning">Planning</option><option value="active">Active</option><option value="paused">Paused</option><option value="done">Done</option></select>
  <input type="text" name="url" placeholder="URL" style="width:100px;padding:6px 8px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.8rem">
  <input type="text" name="desc" placeholder="Description" style="flex:2;min-width:180px;padding:6px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.8rem">
  <button type="submit" class="btn btn-primary btn-sm">Add</button>
</form>'''
            projects_html = f'''<div class="category-section">
  <div class="category-title" style="color:var(--accent)">🗂 Projects</div>
  <div style="display:flex;flex-direction:column;gap:8px">
    {proj_cards}
    {add_form}
  </div>
</div>'''
        except Exception:
            pass

    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🧭 Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
</head><body>
<!--wf-root-->
<nav>
  <span class="nav-brand">🧭 Wayfinder</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container">
  <div class="dashboard">
    <{'a href="/timezones"' if has_timezones else 'div'} class="dashboard-clock">
      <div class="dash-time" id="wf-time">--:--:--</div>
      <div class="dash-where" id="wf-where">&nbsp;</div>
      {'<div class="dash-cta">Compare time zones <span class="dash-arrow">&rarr;</span></div>' if has_timezones else ''}
    </{'a' if has_timezones else 'div'}>
    <div class="wf-install" id="wfInstall" hidden>
      <button type="button" class="wf-install-btn" id="wfInstallBtn">
        📲 Add Wayfinder to your home screen</button>
      <p class="wf-install-tip" id="wfInstallTip" hidden></p>
    </div>
  </div>
  <script>
  (function(){{
    // Where you are is the browser's answer, never the server's: this box is
    // served from a machine in another country, and a laptop that travels
    // changes the answer without telling anybody.
    var zone = '';
    try {{ zone = Intl.DateTimeFormat().resolvedOptions().timeZone || ''; }} catch (e) {{}}
    var city = zone ? zone.split('/').pop().replace(/_/g, ' ') : '';
    var abbr = '';
    try {{
      abbr = new Intl.DateTimeFormat(undefined, {{timeZoneName: 'short'}})
        .formatToParts(new Date())
        .filter(function(p){{ return p.type === 'timeZoneName'; }})
        .map(function(p){{ return p.value; }})[0] || '';
    }} catch (e) {{}}

    function pad(n){{ return (n < 10 ? '0' : '') + n; }}
    function tick(){{
      var d = new Date();
      var te = document.getElementById('wf-time');
      var we = document.getElementById('wf-where');
      if (te) te.textContent =
        pad(d.getHours()) + ':' + pad(d.getMinutes()) + ':' + pad(d.getSeconds());
      if (we) we.textContent =
        d.toLocaleDateString(undefined, {{weekday:'long', month:'long', day:'numeric'}})
        + (city ? ' · ' + city : '') + (abbr ? ' (' + abbr + ')' : '');
    }}
    tick(); setInterval(tick, 1000);

    // Add to home screen. Chrome hands us an event we can fire on demand; iOS
    // Safari has no such API at all, so there the same link spells out the two
    // taps instead of pretending it can do it for you. Either way it is never
    // offered to someone already running the installed app.
    var box = document.getElementById('wfInstall');
    var btn = document.getElementById('wfInstallBtn');
    var tip = document.getElementById('wfInstallTip');
    var deferred = null;
    var installed = (window.matchMedia &&
                     window.matchMedia('(display-mode: standalone)').matches) ||
                    window.navigator.standalone === true;
    var iOS = /iPad|iPhone|iPod/.test(navigator.userAgent) ||
              (navigator.platform === 'MacIntel' && navigator.maxTouchPoints > 1);

    window.addEventListener('beforeinstallprompt', function(e){{
      e.preventDefault();
      deferred = e;
      if (box && !installed) box.hidden = false;
    }});
    if (box && iOS && !installed) box.hidden = false;

    if (btn) btn.addEventListener('click', function(){{
      if (deferred) {{ deferred.prompt(); deferred = null; if (box) box.hidden = true; return; }}
      if (tip) {{
        tip.textContent = iOS
          ? 'Tap the Share button below, then choose "Add to Home Screen".'
          : 'Open your browser menu, then choose "Add to Home screen".';
        tip.hidden = false;
      }}
    }});
    window.addEventListener('appinstalled', function(){{ if (box) box.hidden = true; }});
  }})();
  </script>

  {sections_html}
  {projects_html}
</div>
</body></html>'''


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a): pass

    def handle(self):
        # A client hanging up mid-response is routine (health checks, page
        # navigations) — swallow it here so journalctl isn't flooded with
        # BrokenPipe tracebacks that bury real errors.
        try:
            super().handle()
        except (BrokenPipeError, ConnectionResetError):
            pass

    def send_html(self, html, code=200):
        # Normalise the viewport meta for every page. Without viewport-fit=cover
        # iOS reports env(safe-area-inset-*) as 0, so the bottom tab bar sits
        # under Safari's toolbar and only appears once you scroll and it shrinks.
        html = _VIEWPORT_RE.sub(VIEWPORT_META, html, count=1)
        html = html.replace('</head>', PWA_INJECT + '</head>', 1)
        if '</body>' in html:
            html = html.replace('</body>', PROGRESS_INJECT + '</body>', 1)
        if '</body>' in html:
            html = html.replace('</body>', THEME_TOGGLE + '</body>', 1)
        if '<!--wf-root-->' not in html and '</body>' in html:
            html = html.replace('</body>', WAYFINDER_BACK + '</body>', 1)
        b = html.encode()
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def send_json(self, data, code=200):
        b = json.dumps(data, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def send_css(self):
        b = STYLE.encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/css")
        self.send_header("Content-Length", len(b))
        self.end_headers()
        self.wfile.write(b)

    def send_text(self, text, mime, code=200):
        b = text.strip().encode()
        self.send_response(code)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", len(b))
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        self.end_headers()
        self.wfile.write(b)

    def redirect(self, url):
        self.send_response(302)
        self.send_header("Location", url)
        self.end_headers()

    def _dl_cookie(self):
        """Echo the ?dl=<id> token back as a cookie so wfProgress can stop.
        A file response carries no JS, so this is how the page learns the work
        is over. Only a token that looks like one we issued is reflected."""
        tok = (parse_qs(urlparse(self.path).query).get("dl") or [""])[0]
        if tok and tok.isalnum() and len(tok) <= 32:
            self.send_header("Set-Cookie", f"wf_dl={tok}; Path=/; Max-Age=60")

    def dispatch_agent(self, method, path, body, ctx):
        """Dispatch the SAP agent's own endpoints.

        The agent runs on the user's PC with no browser session, so it carries a
        purpose-scoped token in a header instead (same shape as the batch
        endpoint's shared secret). Pairing is session-authed and lives on the
        normal path — only these three are token-authed. Usage is not recorded:
        a heartbeat every few seconds is not a visit."""
        from services import cardconv as _cc
        user = _cc.resolve_agent_token(self.headers.get("X-Agent-Token", ""))
        if not user:
            return self.send_json({"error": "unauthorized"}, 401)
        if not auth.has_service_access(user, "/cardconv"):
            return self.send_json({"error": "forbidden"}, 403)
        return self.dispatch(_cc.handle(method, path, body, dict(ctx, user=user)))

    def dispatch(self, result):
        t = result[0]
        if t == "html":
            self.send_html(result[1])
        elif t == "json":
            self.send_json(result[1])
        elif t == "redirect":
            self.redirect(result[1])
        elif t == "set_cookie_redirect":
            self.send_response(302)
            self.send_header("Location", result[1])
            self.send_header("Set-Cookie", result[2])
            self.end_headers()
        elif t == "sse":
            self.send_response(200)
            self.send_header("Content-Type", "text/event-stream; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Accel-Buffering", "no")
            self.end_headers()
            try:
                for chunk in result[1]:
                    self.wfile.write(chunk.encode() if isinstance(chunk, str) else chunk)
                    self.wfile.flush()
            except (BrokenPipeError, ConnectionResetError):
                pass
        elif t == "file":
            # Serve a file from disk for download
            import os as _os
            fpath, mime, fname = result[1], result[2], result[3]
            data = open(fpath, "rb").read()
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Disposition", _content_disposition(fname))
            self.send_header("Content-Length", len(data))
            self._dl_cookie()
            self.end_headers()
            self.wfile.write(data)
        elif t == "file_inline":
            # Serve in-memory bytes for download
            data, mime, fname = result[1], result[2], result[3]
            self.send_response(200)
            self.send_header("Content-Type", mime)
            self.send_header("Content-Disposition", _content_disposition(fname))
            self.send_header("Content-Length", len(data))
            self._dl_cookie()
            self.end_headers()
            self.wfile.write(data)
        elif t == "binary":
            # Serve in-memory bytes inline (filename=None) or as attachment
            data, mime = result[1], result[2]
            fname = result[3] if len(result) > 3 else None
            code = result[4] if len(result) > 4 else 200
            self.send_response(code)
            self.send_header("Content-Type", mime)
            if fname:
                self.send_header("Content-Disposition", _content_disposition(fname))
            else:
                self.send_header("Content-Disposition", "inline")
            self.send_header("Content-Length", len(data))
            self.end_headers()
            self.wfile.write(data)

    def get_ctx(self):
        cookie = self.headers.get("Cookie", "")
        return {"cookie": cookie, "user": auth.get_user(cookie), "headers": self.headers}

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        ctx = self.get_ctx()
        query = parse_qs(parsed.query)

        if path == "/static/style.css":
            return self.send_css()
        if path == "/manifest.json":
            return self.send_text(MANIFEST, "application/manifest+json")
        if path == "/sw.js":
            return self.send_text(SW_JS, "application/javascript")
        if path == "/icons/icon.svg":
            return self.send_text(ICON_SVG, "image/svg+xml")
        if path == "/health":
            return self.send_text('{"status":"ok"}', "application/json")
        if path in ("/login", "/logout", "/signup"):
            return self.dispatch(auth.handle("GET", path, query, ctx))
        if path.startswith("/cardconv/agent/"):
            return self.dispatch_agent("GET", path, query, ctx)
        if not ctx["user"]:
            return self.redirect("/login")
        if path == "/":
            return self.send_html(wayfinder(ctx["user"]))
        for svc_path, svc in SERVICES.items():
            if path == svc_path or path.startswith(svc_path + "/"):
                if not auth.has_service_access(ctx["user"], svc_path):
                    return self.redirect("/")
                _usage.record(ctx["user"], svc_path,
                              self.headers.get("User-Agent"))
                return self.dispatch(svc.handle("GET", path, query, ctx))
        self.send_html("<h2>404 Not Found</h2>", 404)

    def do_POST(self):
        path = urlparse(self.path).path
        ctx = self.get_ctx()
        length = int(self.headers.get("Content-Length", 0))
        content_type = self.headers.get("Content-Type", "")

        if "multipart/form-data" in content_type:
            body = {"__raw__": self, "__raw_handler__": self}
        elif "application/json" in content_type:
            try:
                body = json.loads(self.rfile.read(length).decode())
            except Exception:
                body = {}
        else:
            body = parse_qs(self.rfile.read(length).decode())

        if path == "/login":
            return self.dispatch(auth.handle("POST", path, body, ctx))
        if path == "/momentum/arrive":
            # Called by the phone's own arrival automation, which has no session
            # cookie — a shared secret stands in for one. Absent secret = closed.
            from services import momentum as _mom
            _secret = os.environ.get("MOMENTUM_ARRIVE_SECRET", "")
            if not _secret or self.headers.get("X-Arrive-Secret", "") != _secret:
                return self.send_text('{"error":"forbidden"}', "application/json", 403)
            _place = (body.get("place") or body.get("place_id") or [""])
            _place = _place[0] if isinstance(_place, list) else _place
            _user = (body.get("user") or [auth.ADMIN_USERNAME])
            _user = _user[0] if isinstance(_user, list) else _user
            n, label = _mom.arrive(_user, _place)
            if n is None:
                return self.send_text('{"error":"unknown place"}', "application/json", 404)
            return self.send_text(json.dumps({"place": label, "tasks": n}),
                                  "application/json")
        if path == "/cardconv/batch/run":
            import os as _os
            from services import cardconv as _cc
            _secret = _os.environ.get("CARDCONV_BATCH_SECRET", "")
            _provided = self.headers.get("X-Batch-Secret", "")
            if _secret and _provided == _secret:
                return self.dispatch(_cc.handle("POST", path, body, dict(ctx, user=_cc.ADMIN)))
        if path.startswith("/cardconv/agent/"):
            return self.dispatch_agent("POST", path, body, ctx)
        if not ctx["user"]:
            return self.redirect("/login")
        for svc_path, svc in SERVICES.items():
            if path.startswith(svc_path):
                if not auth.has_service_access(ctx["user"], svc_path):
                    return self.redirect("/")
                _usage.record(ctx["user"], svc_path,
                              self.headers.get("User-Agent"))
                return self.dispatch(svc.handle("POST", path, body, ctx))
        self.send_html("<h2>404</h2>", 404)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    # Kill only the process occupying this specific port
    os.system(f"lsof -ti:{port} | xargs kill -9 2>/dev/null; sleep 0.3")
    server = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"🧭 Wayfinder running → http://localhost:{port}")
    server.serve_forever()
