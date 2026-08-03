"""Daily-visit usage log + the admin Usage page.

One line per (day, user, app) — written at the service dispatch point in
server.py, so no app module knows this exists. Granularity is deliberately
"opened the app that day", nothing finer (spec 2026-08-03-usage-dashboard).
"""
import html
import json
import os
import threading
from datetime import date, timedelta

from services._paths import DATA_ROOT

USAGE_DIR = os.path.join(DATA_ROOT, "usage")
EXCLUDED = {"/admin"}  # admin's own visits are noise (spec Q2)

_lock = threading.Lock()
_seen = set()          # (day, user, app) already on disk for _seen_month
_seen_month = None


def _month_file(month):
    return os.path.join(USAGE_DIR, f"{month}.jsonl")


def _read_file(path):
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    out.append((r["d"], r["u"], r["a"]))
                except Exception:
                    continue
    except OSError:
        pass
    return out


def record(user, app_path):
    if not user or app_path in EXCLUDED:
        return
    today = date.today().isoformat()
    month = today[:7]
    key = (today, user, app_path)
    global _seen, _seen_month
    # This sits in the dispatch path of every request — a logging failure must
    # never take the app down with it.
    try:
        with _lock:
            if _seen_month != month:
                _seen = set(_read_file(_month_file(month)))
                _seen_month = month
            if key in _seen:
                return
            _seen.add(key)
            os.makedirs(USAGE_DIR, exist_ok=True)
            with open(_month_file(month), "a", encoding="utf-8") as f:
                f.write(json.dumps({"d": today, "u": user, "a": app_path}) + "\n")
    except Exception:
        pass


def visits(days=30):
    """[(day, user, app)] within the last `days` days, oldest month first."""
    cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
    months = sorted({cutoff[:7], date.today().isoformat()[:7]})
    out = []
    for m in months:
        out.extend(r for r in _read_file(_month_file(m)) if r[0] >= cutoff)
    return out


def _app_meta():
    """{path: "icon name"} from each service module's META (already imported
    in the running server, so this is a cache lookup, not real work)."""
    import importlib
    out = {}
    services_dir = os.path.dirname(os.path.abspath(__file__))
    for f in sorted(os.listdir(services_dir)):
        if not f.endswith(".py") or f.startswith("_") or f == "auth.py":
            continue
        try:
            mod = importlib.import_module(f"services.{f[:-3]}")
            meta = getattr(mod, "META", None)
            if meta:
                out[meta["path"]] = f'{meta["icon"]} {meta["name"]}'
        except Exception:
            continue
    return out


def render_page(current_user, query=None):
    rows = visits(30)
    today = date.today().isoformat()
    labels = _app_meta()
    q_app = (query or {}).get("app", [""])[0]

    def label(app):
        return html.escape(labels.get(app, app))

    # ---- aggregate ----------------------------------------------------
    by_app, by_user = {}, {}
    for d, u, a in rows:
        by_app.setdefault(a, []).append((d, u))
        by_user.setdefault(u, []).append((d, a))

    active_30 = len(by_user)
    active_today = len({u for d, u, a in rows if d == today})
    top_app = max(by_app, key=lambda a: len({u_ for _, u_ in by_app[a]}),
                  default=None)
    visit_days = len(rows)

    stat_cards = f'''
    <div class="dashboard-stats usage-stats">
      <div class="stat-card highlight"><div class="stat-num">{active_30}</div>
        <div class="stat-label">Active users · 30d</div></div>
      <div class="stat-card"><div class="stat-num">{active_today}</div>
        <div class="stat-label">Active today</div></div>
      <div class="stat-card"><div class="stat-num">{visit_days}</div>
        <div class="stat-label">Visit-days · 30d</div></div>
      <div class="stat-card"><div class="stat-num" style="font-size:1.1rem;line-height:1.4">{label(top_app) if top_app else "—"}</div>
        <div class="stat-label">Top app · 30d</div></div>
    </div>'''

    # ---- by app -------------------------------------------------------
    app_rows = ""
    for a in sorted(by_app, key=lambda a: len(by_app[a]), reverse=True):
        recs = by_app[a]
        users_n = len({u for _, u in recs})
        last = max(d for d, _ in recs)
        sel = ' class="usage-row-sel"' if a == q_app else ""
        app_rows += f'''<tr{sel}>
          <td><a class="usage-app-link" href="/admin/usage?app={html.escape(a)}">{label(a)}</a></td>
          <td class="usage-num">{users_n}</td>
          <td class="usage-num">{len(recs)}</td>
          <td class="usage-dim">{last}</td></tr>'''
    if not app_rows:
        app_rows = '<tr><td colspan="4" class="usage-dim">No visits recorded yet.</td></tr>'

    # ---- drilldown for one app ---------------------------------------
    drill = ""
    if q_app and q_app in by_app:
        d_rows = ""
        per_user = {}
        for d, u in by_app[q_app]:
            per_user.setdefault(u, []).append(d)
        for u in sorted(per_user, key=lambda u: len(per_user[u]), reverse=True):
            ds = per_user[u]
            d_rows += (f'<tr><td>{html.escape(u)}</td>'
                       f'<td class="usage-num">{len(ds)}</td>'
                       f'<td class="usage-dim">{max(ds)}</td></tr>')
        drill = f'''
  <div class="card usage-card">
    <h2>{label(q_app)} — by user (30d)
      <a class="usage-clear" href="/admin/usage">✕ Clear</a></h2>
    <div class="usage-tbl-wrap"><table>
      <thead><tr><th>User</th><th>Visit-days</th><th>Last visit</th></tr></thead>
      <tbody>{d_rows}</tbody></table></div>
  </div>'''

    # ---- by user ------------------------------------------------------
    user_rows = ""
    for u in sorted(by_user, key=lambda u: max(d for d, _ in by_user[u]),
                    reverse=True):
        recs = by_user[u]
        per_app = {}
        for d, a in recs:
            per_app.setdefault(a, 0)
            per_app[a] += 1
        top3 = sorted(per_app, key=per_app.get, reverse=True)[:3]
        top3_txt = " · ".join(f"{label(a)} ({per_app[a]})" for a in top3)
        user_rows += f'''<tr>
          <td>{html.escape(u)}{' <span class="usage-dim">(you)</span>' if u == current_user else ''}</td>
          <td class="usage-num">{len({d for d, _ in recs})}</td>
          <td class="usage-dim">{max(d for d, _ in recs)}</td>
          <td>{top3_txt}</td></tr>'''
    if not user_rows:
        user_rows = '<tr><td colspan="4" class="usage-dim">No visits recorded yet.</td></tr>'

    empty_note = "" if rows else '''
  <div class="card wf-empty-card usage-card">
    <div class="wf-empty-icon">📊</div>
    <div class="wf-empty-title">No usage data yet</div>
    <p class="wf-empty-sub">Visits are recorded from the moment this feature
      went live — open any app while signed in and it will appear here.</p>
  </div>'''

    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>📊 Usage · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.usage-stats{{margin:20px 0 24px;display:flex;gap:12px;flex-wrap:wrap}}
.usage-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);padding:20px 24px;margin-bottom:20px}}
.usage-card h2{{font-size:1rem;font-weight:800;color:var(--text);margin:0 0 14px;display:flex;justify-content:space-between;align-items:center}}
.usage-tbl-wrap{{overflow-x:auto}}
.usage-card table{{width:100%;border-collapse:collapse;min-width:480px}}
.usage-card th{{text-align:left;padding:8px 12px;font-size:.72rem;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid var(--border);white-space:nowrap}}
.usage-card td{{padding:10px 12px;border-bottom:1px solid var(--border);font-size:.88rem;color:var(--text)}}
.usage-card tr:last-child td{{border-bottom:none}}
.usage-num{{font-variant-numeric:tabular-nums;font-weight:700}}
.usage-dim{{color:var(--text-muted);font-size:.82rem}}
.usage-app-link{{color:var(--text);text-decoration:none;font-weight:600}}
.usage-app-link:hover{{color:var(--accent)}}
.usage-row-sel td{{background:var(--surface-2)}}
.usage-clear{{font-size:.78rem;font-weight:600;color:var(--text-muted);text-decoration:none}}
@media(max-width:768px){{
  .usage-card{{padding:14px 14px}}
  .usage-card td,.usage-card th{{padding:8px 8px}}
}}
</style>
</head><body>
<nav>
  <a href="/admin/usage" class="nav-brand">📊 Usage</a>
  <span class="nav-user"><a class="nav-back" href="/admin">← Admin</a></span>
</nav>
<div class="container">
  <h1 style="margin-top:0;padding-top:32px">📊 Usage</h1>
  <p class="usage-dim" style="margin-top:-6px">Daily visits per app and user, last 30 days.
    A day counts once per app, no matter how many times it was opened.</p>
  {stat_cards}
  {empty_note}
  {drill}
  <div class="card usage-card">
    <h2>By app · 30d</h2>
    <div class="usage-tbl-wrap"><table>
      <thead><tr><th>App</th><th>Active users</th><th>Visit-days</th><th>Last activity</th></tr></thead>
      <tbody>{app_rows}</tbody></table></div>
  </div>
  <div class="card usage-card">
    <h2>By user · 30d</h2>
    <div class="usage-tbl-wrap"><table>
      <thead><tr><th>User</th><th>Active days</th><th>Last active</th><th>Top apps</th></tr></thead>
      <tbody>{user_rows}</tbody></table></div>
  </div>
</div>
</body></html>'''
