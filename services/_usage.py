"""Hourly-visit usage log + the admin Usage page.

One line per (day, user, app, hour) — written at the service dispatch point in
server.py, so no app module knows this exists. The hour is the finest grain
worth keeping: record() sits in front of every request including cardconv's
polling, so a line per request would be mostly noise by volume
(specs 2026-08-03-usage-dashboard, 2026-08-04-admin-tabs-usage-charts).

Rows written before 2026-08-04 carry no hour or device; readers treat those as
unknown rather than dropping them.
"""
import html
import json
import os
import threading
from datetime import date, datetime, timedelta

from services._paths import DATA_ROOT

USAGE_DIR = os.path.join(DATA_ROOT, "usage")
EXCLUDED = {"/admin"}  # admin's own visits are noise (spec Q2)

_lock = threading.Lock()
_seen = set()          # (day, user, app, hour) already on disk for _seen_month
_seen_month = None

MOBILE_HINTS = ("iphone", "android", "ipad", "mobile", "ipod")


def _month_file(month):
    return os.path.join(USAGE_DIR, f"{month}.jsonl")


def _read_file(path):
    """[(day, user, app, hour|None, mobile|None)] — hour and device are absent
    on rows written before they were tracked, and stay None rather than being
    guessed."""
    out = []
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    r = json.loads(line)
                    h = r.get("h")
                    out.append((r["d"], r["u"], r["a"],
                                h if isinstance(h, int) else None,
                                bool(r["m"]) if "m" in r else None))
                except Exception:
                    continue
    except OSError:
        pass
    return out


def _seen_keys(path):
    return {(d, u, a, h) for d, u, a, h, _ in _read_file(path)}


def is_mobile_agent(user_agent):
    ua = (user_agent or "").lower()
    return any(h in ua for h in MOBILE_HINTS)


def record(user, app_path, user_agent=None):
    if not user or app_path in EXCLUDED:
        return
    now = datetime.now()
    today = now.date().isoformat()
    month = today[:7]
    hour = now.hour
    key = (today, user, app_path, hour)
    global _seen, _seen_month
    # This sits in the dispatch path of every request — a logging failure must
    # never take the app down with it.
    try:
        with _lock:
            if _seen_month != month:
                _seen = _seen_keys(_month_file(month))
                _seen_month = month
            if key in _seen:
                return
            _seen.add(key)
            # Always written, even for desktop: a missing "m" means "this row
            # predates device tracking", and a desktop visit must not be filed
            # under unknown.
            row = {"d": today, "u": user, "a": app_path, "h": hour,
                   "m": 1 if is_mobile_agent(user_agent) else 0}
            os.makedirs(USAGE_DIR, exist_ok=True)
            with open(_month_file(month), "a", encoding="utf-8") as f:
                f.write(json.dumps(row) + "\n")
    except Exception:
        pass


def visits(days=30):
    """[(day, user, app, hour, mobile)] within the last `days` days."""
    cutoff = (date.today() - timedelta(days=days - 1)).isoformat()
    months = sorted({cutoff[:7], date.today().isoformat()[:7]})
    out = []
    for m in months:
        out.extend(r for r in _read_file(_month_file(m)) if r[0] >= cutoff)
    return out


def visit_days(rows):
    """Distinct (day, user, app) — one app opened at 09:00 and again at 14:00
    is one visit-day, not two. Every count that used to be len(rows) must come
    through here now that a day can hold several rows."""
    return {(d, u, a) for d, u, a, _, _ in rows}


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




USAGE_CSS = """
.usage-stats{margin:0 0 20px;display:flex;gap:12px;flex-wrap:wrap}
.usage-card{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:20px 24px;margin-bottom:20px}
.usage-card h2{font-size:1rem;font-weight:800;color:var(--text);margin:0 0 4px;
  display:flex;justify-content:space-between;align-items:center;gap:12px}
.usage-sub{font-size:.78rem;color:var(--text-muted);margin:0 0 16px}
.usage-tbl-wrap{overflow-x:auto}
.usage-card table{width:100%;border-collapse:collapse;min-width:480px}
.usage-card th{text-align:left;padding:8px 12px;font-size:.72rem;color:var(--text-muted);
  text-transform:uppercase;letter-spacing:.05em;border-bottom:1px solid var(--border);white-space:nowrap}
.usage-card td{padding:10px 12px;border-bottom:1px solid var(--border);font-size:.88rem;color:var(--text)}
.usage-card tr:last-child td{border-bottom:none}
.usage-num{font-variant-numeric:tabular-nums;font-weight:700}
.usage-dim{color:var(--text-muted);font-size:.82rem}
.usage-app-link{color:var(--text);text-decoration:none;font-weight:600}
.usage-app-link:hover{color:var(--accent)}
.usage-row-sel td{background:var(--surface-2)}
.usage-clear{font-size:.78rem;font-weight:600;color:var(--text-muted);text-decoration:none}
/* Daily / hourly column charts */
.uchart{display:flex;align-items:flex-end;gap:3px;height:120px}
.ucol{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:flex-end;
  align-items:center;gap:4px;height:100%}
.ubar{width:100%;min-height:2px;border-radius:3px 3px 0 0;background:var(--accent)}
.ubar.is-zero{background:var(--border);min-height:2px}
.uaxis{display:flex;gap:3px;margin-top:6px}
/* Labels sit on every Nth column but are free to spill into the blank spans
   that follow — clipping them to one column width shows "0" and nothing else. */
.uaxis span{flex:1;min-width:0;text-align:left;font-size:.62rem;color:var(--text-muted);
  white-space:nowrap;overflow:visible}
/* Horizontal share bars */
.ubars{display:flex;flex-direction:column;gap:10px}
.ubar-row{display:grid;grid-template-columns:minmax(90px,26%) 1fr auto;gap:10px;align-items:center}
.ubar-name{font-size:.84rem;font-weight:600;color:var(--text);overflow:hidden;
  text-overflow:ellipsis;white-space:nowrap}
.ubar-track{background:var(--surface-2);border-radius:var(--radius-full);height:14px;overflow:hidden}
.ubar-fill{height:100%;border-radius:var(--radius-full);background:var(--accent)}
.ubar-val{font-size:.8rem;font-weight:700;color:var(--text-muted);font-variant-numeric:tabular-nums}
/* Heatmap */
.uheat-scroll{overflow-x:auto}
.uheat{display:flex;flex-direction:column;gap:4px;min-width:420px}
.uheat-row{display:grid;grid-template-columns:minmax(110px,180px) auto 1fr;gap:10px;align-items:center}
.uheat-name{font-size:.8rem;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.uheat-cells{display:flex;gap:2px}
.uheat-cell{width:9px;height:16px;border-radius:2px;background:var(--surface-2)}
.uheat-cell.lv1{background:var(--accent-glow)}
.uheat-cell.lv2{background:var(--accent);opacity:.55}
.uheat-cell.lv3{background:var(--accent)}
.usplit{display:flex;gap:20px;flex-wrap:wrap}
.usplit>div{flex:1;min-width:220px}
@media(max-width:768px){
  .usage-card{padding:14px}
  .usage-card td,.usage-card th{padding:8px}
  .uchart{height:96px}
  .ubar-row{grid-template-columns:minmax(70px,34%) 1fr auto}
  /* A three-app list squeezed into a phone-width column wraps into a wall and
     drags every row's height with it. The same names are one tap away in the
     app table above. */
  .col-top{display:none}
}
"""


def _pct(part, whole):
    return round(100 * part / whole) if whole else 0


def _bar_chart(pairs, height_of, label_every=1):
    """pairs = [(label, value)] rendered as columns. Zero days still draw a
    stub so a quiet stretch reads as quiet, not as missing data."""
    cols, axis = "", ""
    for i, (lab, val) in enumerate(pairs):
        h = height_of(val)
        cls = "ubar is-zero" if not val else "ubar"
        cols += (f'<div class="ucol" title="{html.escape(str(lab))}: {val}">'
                 f'<div class="{cls}" style="height:{h}%"></div></div>')
        axis += f'<span>{html.escape(lab) if i % label_every == 0 else ""}</span>'
    return f'<div class="uchart">{cols}</div><div class="uaxis">{axis}</div>'


def _share_bars(items, total):
    rows = ""
    for name, val in items:
        rows += (f'<div class="ubar-row"><div class="ubar-name">{name}</div>'
                 f'<div class="ubar-track"><div class="ubar-fill" '
                 f'style="width:{max(2, _pct(val, total))}%"></div></div>'
                 f'<div class="ubar-val">{val}</div></div>')
    return f'<div class="ubars">{rows}</div>'


def render_body(current_user, query=None):
    """The Usage tab's body — markup only, no page shell. The admin page owns
    the shell so both tabs share one nav, one container, one theme."""
    from services import auth

    rows = visits(30)
    today = date.today()
    today_s = today.isoformat()
    labels = _app_meta()
    q_app = (query or {}).get("app", [""])[0]

    def label(app):
        return html.escape(labels.get(app, app))

    days = [(today - timedelta(days=i)).isoformat() for i in range(29, -1, -1)]

    # ---- aggregate ----------------------------------------------------
    by_app, by_user, by_day = {}, {}, {}
    hours = [0] * 24
    hour_unknown = 0
    mobile_hits = desktop_hits = device_unknown = 0
    for d, u, a, h, m in rows:
        by_app.setdefault(a, set()).add((d, u))
        by_user.setdefault(u, set()).add((d, a))
        by_day.setdefault(d, set()).add(u)
        if h is None:
            hour_unknown += 1
        else:
            hours[h] += 1
        if m is None:
            device_unknown += 1
        elif m:
            mobile_hits += 1
        else:
            desktop_hits += 1

    vdays = visit_days(rows)
    active_30 = len(by_user)
    active_today = len(by_day.get(today_s, ()))
    stickiness = _pct(active_today, active_30)
    top_app = max(by_app, key=lambda a: len({u for _, u in by_app[a]}), default=None)

    stat_cards = f'''
    <div class="dashboard-stats usage-stats">
      <div class="stat-card highlight"><div class="stat-num">{active_30}</div>
        <div class="stat-label">Active users · 30d</div></div>
      <div class="stat-card"><div class="stat-num">{active_today}</div>
        <div class="stat-label">Active today</div></div>
      <div class="stat-card"><div class="stat-num">{len(vdays)}</div>
        <div class="stat-label">Visit-days · 30d</div></div>
      <div class="stat-card"><div class="stat-num">{stickiness}%</div>
        <div class="stat-label">Stickiness · today/30d</div></div>
    </div>'''

    if not rows:
        return f'''
  <div class="card usage-card wf-empty-card">
    <div class="wf-empty-icon">📊</div>
    <div class="wf-empty-title">No usage data yet</div>
    <p class="wf-empty-sub">Visits are recorded from the moment this feature
      went live — open any app while signed in and it will appear here.</p>
  </div>{stat_cards}'''

    # ---- daily activity ------------------------------------------------
    per_day = [(d, len({(u, a) for du, u, a, _, _ in rows if du == d})) for d in days]
    day_max = max(v for _, v in per_day) or 1
    daily = _bar_chart([(d[5:], v) for d, v in per_day],
                       lambda v: max(2, round(100 * v / day_max)), label_every=5)

    # ---- app share -----------------------------------------------------
    app_order = sorted(by_app, key=lambda a: len(by_app[a]), reverse=True)
    share = _share_bars([(label(a), len(by_app[a])) for a in app_order], len(vdays))

    # ---- hour of day ---------------------------------------------------
    hour_total = sum(hours)
    hour_max = max(hours) or 1
    hourly = _bar_chart([(f"{h}", hours[h]) for h in range(24)],
                        lambda v: max(2, round(100 * v / hour_max)), label_every=3)
    hour_note = (f"{hour_unknown} older record(s) carry no hour and sit outside this chart."
                 if hour_unknown else
                 f"{hour_total} record(s), each one an app opened in that hour.")

    # ---- device split ---------------------------------------------------
    device_known = mobile_hits + desktop_hits
    if device_known:
        device = _share_bars([("📱 Mobile", mobile_hits), ("🖥 Desktop", desktop_hits)],
                             device_known)
        device_note = (f"{device_unknown} older record(s) predate device tracking."
                       if device_unknown else "Every record carries a device.")
    else:
        device = '<p class="usage-dim">No device data yet — older records predate it.</p>'
        device_note = f"{device_unknown} record(s) with no device."

    # ---- heatmap --------------------------------------------------------
    heat_days = days[-21:]
    heat_rows = ""
    for u in sorted(by_user, key=lambda u: len(by_user[u]), reverse=True):
        per = {}
        for d, uu, a, _, _ in rows:
            if uu == u:
                per.setdefault(d, set()).add(a)
        cells = ""
        for d in heat_days:
            n = len(per.get(d, ()))
            lv = "lv3" if n >= 3 else "lv2" if n == 2 else "lv1" if n == 1 else ""
            cells += (f'<div class="uheat-cell {lv}" '
                      f'title="{html.escape(u)} · {d}: {n} app(s)"></div>')
        heat_rows += (f'<div class="uheat-row"><div class="uheat-name">{html.escape(u)}</div>'
                      f'<div class="uheat-cells">{cells}</div><div></div></div>')
    heatmap = f'<div class="uheat-scroll"><div class="uheat">{heat_rows}</div></div>'

    # ---- app table ------------------------------------------------------
    app_rows = ""
    for a in app_order:
        recs = by_app[a]
        users_of = {u for _, u in recs}
        per_user_days = {}
        for d, u in recs:
            per_user_days.setdefault(u, set()).add(d)
        returning = sum(1 for u in per_user_days if len(per_user_days[u]) >= 2)
        last = max(d for d, _ in recs)
        sel = ' class="usage-row-sel"' if a == q_app else ""
        app_rows += f'''<tr{sel}>
          <td><a class="usage-app-link" href="/admin?tab=usage&amp;app={html.escape(a)}">{label(a)}</a></td>
          <td class="usage-num">{len(users_of)}</td>
          <td class="usage-num">{len(recs)}</td>
          <td class="usage-num">{_pct(returning, len(users_of))}%</td>
          <td class="usage-dim">{last}</td></tr>'''

    # ---- drilldown ------------------------------------------------------
    drill = ""
    if q_app and q_app in by_app:
        per_user = {}
        for d, u in by_app[q_app]:
            per_user.setdefault(u, set()).add(d)
        d_rows = "".join(
            f'<tr><td>{html.escape(u)}</td><td class="usage-num">{len(per_user[u])}</td>'
            f'<td class="usage-dim">{max(per_user[u])}</td></tr>'
            for u in sorted(per_user, key=lambda u: len(per_user[u]), reverse=True))
        drill = f'''
  <div class="card usage-card">
    <h2>{label(q_app)} — by user (30d)
      <a class="usage-clear" href="/admin?tab=usage">✕ Clear</a></h2>
    <div class="usage-tbl-wrap"><table>
      <thead><tr><th>User</th><th>Visit-days</th><th>Last visit</th></tr></thead>
      <tbody>{d_rows}</tbody></table></div>
  </div>'''

    # ---- user table -----------------------------------------------------
    user_rows = ""
    for u in sorted(by_user, key=lambda u: max(d for d, _ in by_user[u]), reverse=True):
        recs = by_user[u]
        per_app = {}
        for d, a in recs:
            per_app[a] = per_app.get(a, 0) + 1
        top3 = sorted(per_app, key=per_app.get, reverse=True)[:3]
        top3_txt = " · ".join(f"{label(a)} ({per_app[a]})" for a in top3)
        active_hours = len({(d, h) for d, uu, a, h, _ in rows if uu == u and h is not None})
        user_rows += f'''<tr>
          <td>{html.escape(u)}{' <span class="usage-dim">(you)</span>' if u == current_user else ''}</td>
          <td class="usage-num">{len({d for d, _ in recs})}</td>
          <td class="usage-num">{len(per_app)}</td>
          <td class="usage-num">{active_hours}</td>
          <td class="usage-dim">{max(d for d, _ in recs)}</td>
          <td class="col-top">{top3_txt}</td></tr>'''

    # ---- dormant --------------------------------------------------------
    try:
        all_users = set(auth.load_users())
    except Exception:
        all_users = set()
    dormant = sorted(all_users - set(by_user))
    if dormant:
        dormant_html = ('<div class="ubars">' + "".join(
            f'<div class="usage-dim">{html.escape(u)}</div>' for u in dormant) + "</div>")
    else:
        dormant_html = '<p class="usage-dim">Everyone with an account showed up in the last 30 days.</p>'

    apps_per_user = round(sum(len({a for _, a in by_user[u]}) for u in by_user) / len(by_user), 1)

    return f'''{stat_cards}
  {drill}
  <div class="card usage-card">
    <h2>Daily activity · 30d</h2>
    <p class="usage-sub">App-opens per day, counted once per app per user.
      Quiet days draw a flat stub, not a gap.</p>
    {daily}
  </div>
  <div class="card usage-card">
    <h2>Share by app · 30d</h2>
    <p class="usage-sub">Visit-days per app. Average apps used per person: {apps_per_user}.</p>
    {share}
  </div>
  <div class="card usage-card">
    <div class="usplit">
      <div>
        <h2>Hour of day</h2>
        <p class="usage-sub">{hour_note}</p>
        {hourly}
      </div>
      <div>
        <h2>Device</h2>
        <p class="usage-sub">{device_note}</p>
        {device}
      </div>
    </div>
  </div>
  <div class="card usage-card">
    <h2>Who showed up · last 21 days</h2>
    <p class="usage-sub">One cell per person per day; darker means more apps opened.</p>
    {heatmap}
  </div>
  <div class="card usage-card">
    <h2>By app · 30d</h2>
    <div class="usage-tbl-wrap"><table>
      <thead><tr><th>App</th><th>Active users</th><th>Visit-days</th>
        <th>Returning</th><th>Last activity</th></tr></thead>
      <tbody>{app_rows}</tbody></table></div>
  </div>
  <div class="card usage-card">
    <h2>By user · 30d</h2>
    <div class="usage-tbl-wrap"><table>
      <thead><tr><th>User</th><th>Active days</th><th>Apps</th><th>Active hours</th>
        <th>Last active</th><th class="col-top">Top apps</th></tr></thead>
      <tbody>{user_rows}</tbody></table></div>
  </div>
  <div class="card usage-card">
    <h2>Dormant accounts</h2>
    <p class="usage-sub">Signed up, no visit in the last 30 days.</p>
    {dormant_html}
  </div>'''
