import json, os
from datetime import date, timedelta, datetime

DATA_ROOT = os.path.expanduser("~/.appdata")

META = {
    "name": "Overview",
    "path": "/dashboard",
    "icon": "📊",
    "description": "Today at a glance",
}


def _load_todos(user):
    f = os.path.join(DATA_ROOT, user or "guest", "todo.json")
    if not os.path.exists(f):
        return []
    try:
        with open(f) as fp:
            return json.load(fp)
    except Exception:
        return []


def _load_habits(user):
    f = os.path.join(DATA_ROOT, user or "guest", "habits.json")
    if not os.path.exists(f):
        return []
    try:
        with open(f) as fp:
            data = json.load(fp)
            if isinstance(data, dict):
                data["id"] = 1
                data = [data]
            for h in data:
                if isinstance(h.get("checkins"), list):
                    h["checkins"] = {d: 1 for d in h["checkins"]}
                elif not isinstance(h.get("checkins"), dict):
                    h["checkins"] = {}
                h.setdefault("target", 1)
                h.setdefault("icon", "✅")
                h.setdefault("freq", "daily")
            return data
    except Exception:
        return []


def _day_total(checkins, ds):
    v = checkins.get(ds, 0)
    if isinstance(v, dict):
        return v.get("total", 0)
    return v if isinstance(v, (int, float)) else 0


def _streak(checkins, target=1):
    today = date.today()
    streak, d = 0, today
    t = max(1, target)
    while _day_total(checkins, d.isoformat()) >= t:
        streak += 1
        d -= timedelta(days=1)
    return streak


def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user")
    if not user:
        return ("redirect", "/login")
    return ("html", render(user))


def render(user):
    today = date.today()
    today_str = today.isoformat()
    week_dates = [today - timedelta(days=i) for i in range(6, -1, -1)]

    todos = _load_todos(user)
    habits = _load_habits(user)

    # Todo stats
    total_active = sum(1 for t in todos if not t.get("done"))
    done_today = sum(1 for t in todos if t.get("done") and (t.get("done_at") or "").startswith(today_str))
    total_done = sum(1 for t in todos if t.get("done"))

    # Todo weekly: done per day for last 7 days
    todo_weekly = []
    for d in week_dates:
        ds = d.isoformat()
        count = sum(1 for t in todos if t.get("done") and (t.get("done_at") or "").startswith(ds))
        todo_weekly.append((d, count))

    max_todo_week = max((c for _, c in todo_weekly), default=1) or 1

    # Habit stats
    total_habits = len(habits)
    done_habits_today = sum(
        1 for h in habits
        if _day_total(h.get("checkins", {}), today_str) >= max(1, h.get("target", 1))
    )

    # Habit weekly grid
    habit_rows = []
    for h in habits:
        checkins = h.get("checkins", {})
        target = max(1, h.get("target", 1))
        streak = _streak(checkins, target)
        week_status = []
        for d in week_dates:
            ds = d.isoformat()
            val = _day_total(checkins, ds)
            if val >= target:
                week_status.append("done")
            elif val > 0:
                week_status.append("partial")
            else:
                week_status.append("empty")
        habit_rows.append({
            "icon": h.get("icon", "✅"),
            "name": h.get("name", ""),
            "streak": streak,
            "week": week_status,
        })

    # Render todo bar chart
    todo_bars = ""
    day_labels = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    for i, (d, count) in enumerate(todo_weekly):
        height = int((count / max_todo_week) * 60) if count else 4
        is_today = d == today
        label = "Today" if is_today else day_labels[d.weekday()]
        bar_cls = "bar today" if is_today else "bar"
        todo_bars += f'''<div class="bar-col">
          <div class="bar-val">{count if count else ""}</div>
          <div class="{bar_cls}" style="height:{height}px"></div>
          <div class="bar-label">{label}</div>
        </div>'''

    # Render habit grid rows
    habit_grid_html = ""
    for row in habit_rows:
        cells = ""
        for status in row["week"]:
            cells += f'<div class="hcell {status}"></div>'
        streak_html = f'<span class="streak">🔥 {row["streak"]}d</span>' if row["streak"] >= 2 else ""
        habit_grid_html += f'''<div class="habit-row-d">
          <div class="habit-name-d">{row["icon"]} {row["name"]} {streak_html}</div>
          <div class="hcells">{cells}</div>
        </div>'''

    if not habit_grid_html:
        habit_grid_html = '<div class="empty-hint">No habits yet</div>'

    todo_rate = int(done_today / (done_today + total_active) * 100) if (done_today + total_active) > 0 else 0
    habit_rate = int(done_habits_today / total_habits * 100) if total_habits > 0 else 0

    week_label_html = "".join(
        f'<div class="wlabel {"today-lbl" if d == today else ""}">'
        + ("T" if d == today else ["M","Tu","W","Th","F","Sa","Su"][d.weekday()])
        + "</div>"
        for d in week_dates
    )

    from server import app_tabs
    tabs_html = app_tabs("/dashboard")

    now_hour = datetime.now().hour
    if now_hour < 6:
        greeting = "Good night"
    elif now_hour < 12:
        greeting = "Good morning"
    elif now_hour < 18:
        greeting = "Hello"
    else:
        greeting = "Good evening"

    return f'''<!DOCTYPE html>
<html lang="ko"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📊 Overview · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.db-hero{{background:var(--surface);background-image:radial-gradient(at 0% 0%,rgba(56,189,248,.18) 0,transparent 55%),radial-gradient(at 100% 100%,rgba(129,140,248,.18) 0,transparent 55%);border-radius:var(--radius-xl);padding:32px 36px;color:var(--text);margin-bottom:28px;border:1px solid var(--border)}}
.db-hero h2{{font-size:1.5rem;font-weight:800;letter-spacing:-.03em;margin-bottom:4px}}
.db-hero p{{color:var(--text-muted);font-size:.9rem}}
.db-grid{{display:grid;grid-template-columns:1fr 1fr;gap:20px;margin-bottom:28px}}
.big-num{{font-size:3rem;font-weight:800;letter-spacing:-.04em;line-height:1;color:var(--text)}}
.big-num span{{font-size:1rem;font-weight:500;color:var(--text-muted);margin-left:4px}}
.rate-bar{{background:var(--surface-2);border-radius:99px;height:8px;margin-top:12px;overflow:hidden}}
.rate-fill{{height:100%;border-radius:99px;background:linear-gradient(90deg,var(--accent),var(--info));transition:width .6s ease}}
.rate-label{{font-size:.78rem;color:var(--text-muted);margin-top:6px}}
.bar-chart{{display:flex;align-items:flex-end;gap:8px;height:80px;padding-bottom:0}}
.bar-col{{display:flex;flex-direction:column;align-items:center;gap:4px;flex:1}}
.bar-val{{font-size:.7rem;color:var(--text-muted);height:16px;display:flex;align-items:center}}
.bar{{width:100%;background:var(--surface-2);border-radius:4px 4px 0 0;transition:.3s}}
.bar.today{{background:linear-gradient(180deg,var(--accent),var(--info))}}
.bar-label{{font-size:.68rem;color:var(--text-muted);font-weight:600}}
.bar-label.today{{color:var(--accent)}}
.week-labels{{display:flex;justify-content:flex-end;gap:4px;margin-bottom:8px}}
.wlabel{{width:28px;text-align:center;font-size:.65rem;color:var(--text-muted);font-weight:600}}
.wlabel.today-lbl{{color:var(--accent)}}
.habit-row-d{{display:flex;align-items:center;gap:12px;padding:8px 0;border-bottom:1px solid var(--border)}}
.habit-row-d:last-child{{border-bottom:none}}
.habit-name-d{{flex:1;font-size:.85rem;font-weight:600;color:var(--text);display:flex;align-items:center;gap:6px;min-width:0}}
.streak{{font-size:.72rem;color:var(--warn);font-weight:700;white-space:nowrap}}
.hcells{{display:flex;gap:4px}}
.hcell{{width:28px;height:28px;border-radius:6px;background:var(--surface-2)}}
.hcell.done{{background:linear-gradient(135deg,var(--accent),var(--info))}}
.hcell.partial{{background:rgba(56,189,248,0.25)}}
.empty-hint{{color:var(--text-muted);font-size:.85rem;padding:16px 0;text-align:center}}
.notepad-card{{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);overflow:hidden;box-shadow:var(--shadow-sm)}}
.notepad-header{{background:var(--surface-2);padding:10px 16px 12px;border-bottom:1px solid var(--border)}}
.notepad-title-row{{display:flex;align-items:center;gap:10px}}
.notepad-body{{padding:16px}}
@media(max-width:600px){{
  .db-grid{{grid-template-columns:1fr;gap:12px}}
  .db-hero{{padding:20px}}
  .big-num{{font-size:2.2rem}}
  .hcell{{width:24px;height:24px}}
  .wlabel{{width:24px}}
}}
</style>
</head><body>
<nav>
  <span class="nav-brand">📊 Overview</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container">
  <div class="db-hero">
    <h2>{greeting}, {user}</h2>
    <p>{today.strftime("%B %d, %Y")} &nbsp;·&nbsp; Today at a glance</p>
  </div>

  <div class="db-grid">
    <div class="notepad-card">
<div class="notepad-header"><div class="notepad-title-row"><span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Tasks Today</span></div></div>
      <div class="notepad-body">
        <div class="big-num">{done_today}<span>/ {done_today + total_active}</span></div>
        <div class="rate-bar"><div class="rate-fill" style="width:{todo_rate}%"></div></div>
        <div class="rate-label">{todo_rate}% complete &nbsp;·&nbsp; {total_active} remaining</div>
      </div>
    </div>
    <div class="notepad-card">
<div class="notepad-header"><div class="notepad-title-row"><span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Habits Today</span></div></div>
      <div class="notepad-body">
        <div class="big-num">{done_habits_today}<span>/ {total_habits}</span></div>
        <div class="rate-bar"><div class="rate-fill" style="width:{habit_rate}%"></div></div>
        <div class="rate-label">{habit_rate}% done &nbsp;·&nbsp; {total_habits} total</div>
      </div>
    </div>
  </div>

  <div class="notepad-card" style="margin-bottom:20px">
<div class="notepad-header"><div class="notepad-title-row"><span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Tasks This Week</span></div></div>
    <div class="notepad-body">
      <div class="bar-chart">{todo_bars}</div>
    </div>
  </div>

  <div class="notepad-card" style="margin-bottom:28px">
<div class="notepad-header"><div class="notepad-title-row"><span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Habits This Week</span></div></div>
    <div class="notepad-body">
      <div class="week-labels"><div style="flex:1"></div>{week_label_html}</div>
      {habit_grid_html}
    </div>
  </div>

</div>
{tabs_html}
</body></html>'''
