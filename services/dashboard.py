import json, os
from datetime import date, timedelta, datetime

ADMIN_USER = "jongha.kang"
PROJECTS_FILE = os.path.join(os.path.expanduser("~/.appdata"), "projects.json")

STATUS_META = {
    "active":   {"label": "Active",    "color": "#34d399", "bg": "rgba(52,211,153,0.12)",  "border": "rgba(52,211,153,0.3)"},
    "planning": {"label": "Planning",  "color": "#fbbf24", "bg": "rgba(251,191,36,0.12)",  "border": "rgba(251,191,36,0.3)"},
    "paused":   {"label": "Paused",    "color": "#94a3b8", "bg": "rgba(148,163,184,0.12)", "border": "rgba(148,163,184,0.3)"},
    "done":     {"label": "Done",      "color": "#818cf8", "bg": "rgba(129,140,248,0.12)", "border": "rgba(129,140,248,0.3)"},
}

DEFAULT_PROJECTS = [
    {"id": 1, "emoji": "🧭", "name": "Wayfinder · Task/Habit", "desc": "Personal productivity hub — Task & Habit tracker, ongoing improvement", "status": "active",   "started": "2026-05-01", "url": "/todo"},
    {"id": 2, "emoji": "💳", "name": "Corporate Card Automation", "desc": "Auto-process corporate card receipts and generate expense reports", "status": "planning", "started": "2026-05-28", "url": ""},
]

def _load_projects():
    if not os.path.exists(PROJECTS_FILE):
        _save_projects(DEFAULT_PROJECTS)
        return DEFAULT_PROJECTS
    try:
        with open(PROJECTS_FILE) as f:
            return json.load(f)
    except Exception:
        return DEFAULT_PROJECTS

def _save_projects(projects):
    os.makedirs(os.path.dirname(PROJECTS_FILE), exist_ok=True)
    with open(PROJECTS_FILE, "w") as f:
        json.dump(projects, f, ensure_ascii=False, indent=2)

def _next_proj_id(projects):
    return max((p["id"] for p in projects), default=0) + 1

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

    if method == "POST" and user == ADMIN_USER:
        projects = _load_projects()
        if path == "/dashboard/project/add":
            name  = (body.get("name",  [""])[0]).strip()
            desc  = (body.get("desc",  [""])[0]).strip()
            emoji = (body.get("emoji", ["📌"])[0]).strip() or "📌"
            url   = (body.get("url",   [""])[0]).strip()
            status = body.get("status", ["planning"])[0]
            if name:
                projects.append({"id": _next_proj_id(projects), "emoji": emoji, "name": name, "desc": desc, "status": status, "started": date.today().isoformat(), "url": url})
                _save_projects(projects)
        elif path == "/dashboard/project/delete":
            pid = int(body.get("id", [0])[0])
            _save_projects([p for p in projects if p["id"] != pid])
        elif path == "/dashboard/project/status":
            pid    = int(body.get("id", [0])[0])
            status = body.get("status", ["active"])[0]
            for p in projects:
                if p["id"] == pid:
                    p["status"] = status
            _save_projects(projects)
        return ("redirect", "/dashboard")

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
            "id": h.get("id"),
            "icon": h.get("icon", "✅"),
            "name": h.get("name", ""),
            "streak": streak,
            "week": week_status,
            "checked": _day_total(checkins, today_str) >= target,
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
    tabs_html = app_tabs("/dashboard", user)

    # Projects section (admin only)
    projects_html = ""
    if user == ADMIN_USER:
        projects = _load_projects()
        proj_cards = ""
        for p in projects:
            sm = STATUS_META.get(p.get("status", "planning"), STATUS_META["planning"])
            link_btn = f'<a href="{p["url"]}" class="btn btn-ghost btn-sm" style="font-size:0.72rem">Open →</a>' if p.get("url") else ""
            status_opts = "".join(
                f'<option value="{s}" {"selected" if s == p.get("status") else ""}>{STATUS_META[s]["label"]}</option>'
                for s in STATUS_META
            )
            proj_cards += f'''
<div class="proj-card">
  <div class="proj-top">
    <span class="proj-emoji">{p.get("emoji","📌")}</span>
    <div class="proj-info">
      <div class="proj-name">{p["name"]}</div>
      <div class="proj-desc">{p.get("desc","")}</div>
    </div>
    <div class="proj-actions">
      <span class="proj-badge" style="color:{sm["color"]};background:{sm["bg"]};border:1px solid {sm["border"]}">{sm["label"]}</span>
      {link_btn}
    </div>
  </div>
  <div class="proj-footer">
    <span class="proj-date">Started {p.get("started","")}</span>
    <form method="POST" action="/dashboard/project/status" style="display:inline-flex;align-items:center;gap:6px">
      <input type="hidden" name="id" value="{p["id"]}">
      <select name="status" onchange="this.form.submit()" class="proj-status-sel">{status_opts}</select>
    </form>
    <form method="POST" action="/dashboard/project/delete" style="display:inline" onsubmit="return confirm('Delete project?')">
      <input type="hidden" name="id" value="{p["id"]}">
      <button class="btn btn-danger btn-sm" style="font-size:0.72rem">✕</button>
    </form>
  </div>
</div>'''

        add_form = '''
<details class="proj-add-details">
  <summary class="btn btn-ghost btn-sm" style="list-style:none;cursor:pointer;display:inline-flex;align-items:center;gap:4px">＋ Add Project</summary>
  <form method="POST" action="/dashboard/project/add" class="proj-add-form">
    <input type="text" name="emoji" placeholder="Emoji" style="width:60px">
    <input type="text" name="name" placeholder="Project name" required style="flex:1;min-width:160px">
    <select name="status">
      <option value="planning">Planning</option>
      <option value="active">Active</option>
      <option value="paused">Paused</option>
      <option value="done">Done</option>
    </select>
    <input type="text" name="url" placeholder="URL (optional)" style="width:140px">
    <input type="text" name="desc" placeholder="Description" style="flex:2;min-width:200px">
    <button type="submit" class="btn btn-primary btn-sm">Add</button>
  </form>
</details>'''

        projects_html = f'''
<div class="notepad-card" style="margin-bottom:28px">
  <div class="notepad-header">
    <div class="notepad-title-row">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">🗂 Projects</span>
      <span style="font-size:var(--text-xs);color:var(--text-muted);margin-left:auto">{len(projects)} projects</span>
    </div>
  </div>
  <div class="notepad-body" style="padding:12px 16px;display:flex;flex-direction:column;gap:10px">
    {proj_cards}
    <div style="margin-top:4px">{add_form}</div>
  </div>
</div>
<style>
.proj-card{{background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);padding:14px 16px;display:flex;flex-direction:column;gap:10px}}
.proj-top{{display:flex;align-items:flex-start;gap:12px}}
.proj-emoji{{font-size:1.5rem;flex-shrink:0;width:36px;text-align:center;margin-top:2px}}
.proj-info{{flex:1;min-width:0}}
.proj-name{{font-size:.95rem;font-weight:700;color:var(--text);margin-bottom:3px}}
.proj-desc{{font-size:.78rem;color:var(--text-muted);line-height:1.4}}
.proj-actions{{display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex-shrink:0}}
.proj-badge{{font-size:.7rem;font-weight:700;padding:3px 10px;border-radius:var(--radius-full);white-space:nowrap}}
.proj-footer{{display:flex;align-items:center;gap:8px;flex-wrap:wrap;border-top:1px solid var(--border);padding-top:8px}}
.proj-date{{font-size:.72rem;color:var(--text-muted);flex:1}}
.proj-status-sel{{font-size:.72rem;padding:3px 6px;border-radius:6px;border:1px solid var(--border);background:var(--surface);color:var(--text-muted);cursor:pointer}}
.proj-add-details summary::marker,.proj-add-details summary::-webkit-details-marker{{display:none}}
.proj-add-form{{display:flex;flex-wrap:wrap;gap:8px;align-items:center;margin-top:10px;padding:12px;background:var(--surface-3);border-radius:var(--radius-md)}}
.proj-add-form input,.proj-add-form select{{padding:7px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);background:var(--surface-2);color:var(--text);font-size:.82rem}}
.proj-add-form input:focus{{outline:none;border-color:var(--accent)}}
@media(max-width:600px){{.proj-top{{flex-wrap:wrap}}.proj-actions{{flex-direction:row;flex-wrap:wrap}}.proj-add-form{{flex-direction:column}}.proj-add-form input,.proj-add-form select{{width:100%}}}}
</style>'''

    now_hour = datetime.now().hour
    if now_hour < 6:
        greeting = "Good night"
    elif now_hour < 12:
        greeting = "Good morning"
    elif now_hour < 18:
        greeting = "Hello"
    else:
        greeting = "Good evening"

    # ── Adaptive Today Hub ──────────────────────────────────────
    max_streak = max((r["streak"] for r in habit_rows), default=0)
    engagement = total_active + total_habits

    def _todo_item(t):
        done = t.get("done")
        cls = "wf-today-item wf-done" if done else "wf-today-item"
        action = "/todo/undone" if done else "/todo/done"
        check = ('<button type="submit" class="wf-check wf-check--on" aria-label="되돌리기">✓</button>'
                 if done else '<button type="submit" class="wf-check" aria-label="완료"></button>')
        return (f'<form method="POST" action="{action}" class="{cls}">'
                f'<input type="hidden" name="id" value="{t["id"]}">'
                f'<input type="hidden" name="next" value="/dashboard">'
                f'{check}<span class="wf-today-text">{t.get("title","")}</span></form>')

    def _habit_item(r):
        done = r["checked"]
        cls = "wf-today-item wf-done" if done else "wf-today-item"
        check = ('<button type="submit" class="wf-check wf-check--on" aria-label="체크 해제">✓</button>'
                 if done else '<button type="submit" class="wf-check" aria-label="습관 체크"></button>')
        chip = f'<span class="wf-streak-chip">🔥 {r["streak"]}d</span>' if r["streak"] >= 1 else ""
        return (f'<form method="POST" action="/habit/{r["id"]}/checkin" class="{cls}">'
                f'<input type="hidden" name="toggle" value="1">'
                f'<input type="hidden" name="next" value="/dashboard">'
                f'{check}<span class="wf-today-text">{r["icon"]} {r["name"]}</span>{chip}</form>')

    active_todos = [t for t in todos if not t.get("done")]
    done_todos_today = [t for t in todos if t.get("done") and (t.get("done_at") or "").startswith(today_str)]

    if total_active == 0 and total_habits == 0 and len(todos) == 0:
        stage = "empty"
    elif engagement <= 5:
        stage = "light"
    else:
        stage = "heavy"

    if stage == "empty":
        body_html = '''<div class="wf-home-empty">
  <div class="notepad-card wf-empty-card">
    <div class="wf-empty-icon">✅</div>
    <div class="wf-empty-title">첫 할일 추가</div>
    <form method="POST" action="/todo/add" class="wf-empty-form">
      <input type="hidden" name="next" value="/dashboard">
      <input type="text" name="title" placeholder="예: 이메일 정리하기" required class="wf-empty-input">
      <button type="submit" class="btn btn-primary">추가</button>
    </form>
  </div>
  <div class="notepad-card wf-empty-card">
    <div class="wf-empty-icon">🔄</div>
    <div class="wf-empty-title">첫 습관 추가</div>
    <form method="POST" action="/habit/add" class="wf-empty-form">
      <input type="text" name="name" placeholder="예: 물 2L 마시기" required class="wf-empty-input">
      <input type="hidden" name="freq" value="daily">
      <input type="hidden" name="target" value="1">
      <button type="submit" class="btn btn-primary">추가</button>
    </form>
  </div>
</div>'''
    elif stage == "light":
        items = "".join(_todo_item(t) for t in active_todos)
        items += "".join(_habit_item(r) for r in habit_rows if not r["checked"])
        items += "".join(_todo_item(t) for t in done_todos_today)
        items += "".join(_habit_item(r) for r in habit_rows if r["checked"])
        if not items:
            items = '<div class="wf-next-cta">오늘 할 일이 비었어요 — 위 탭에서 할일이나 습관을 추가해볼까요?</div>'
        body_html = f'''<div class="notepad-card" style="padding:18px 20px;margin-bottom:24px">
  <div class="wf-today-head">
    <span class="wf-today-title">☀️ 오늘 할 것</span>
    <span class="badge">{done_today + done_habits_today} 완료</span>
  </div>
  <div class="wf-today-list">{items}</div>
</div>'''
    else:  # heavy
        unchecked_habits = [r for r in habit_rows if not r["checked"]]
        focus = ("".join(_todo_item(t) for t in active_todos[:3])
                 + "".join(_habit_item(r) for r in unchecked_habits[:3]))
        if not focus:
            focus = '<div class="wf-next-cta">오늘 할 일을 다 했어요! 🎉</div>'
        body_html = f'''<div class="wf-stat-grid">
  <div class="wf-stat"><div class="wf-stat-value">{total_active}</div><div class="wf-stat-label">남은 할일</div></div>
  <div class="wf-stat"><div class="wf-stat-value">{done_today}</div><div class="wf-stat-label">오늘 완료</div></div>
  <div class="wf-stat"><div class="wf-stat-value">{done_habits_today}<span class="wf-stat-sub">/{total_habits}</span></div><div class="wf-stat-label">오늘 습관</div></div>
  <div class="wf-stat"><div class="wf-stat-value">🔥{max_streak}<span class="wf-stat-sub">d</span></div><div class="wf-stat-label">최장 연속</div></div>
</div>
<div class="notepad-card" style="padding:18px 20px;margin-bottom:20px">
  <div class="wf-today-head">
    <span class="wf-today-title">🎯 오늘 포커스</span>
    <a href="/todo" class="btn btn-ghost btn-sm">전체 보기 →</a>
  </div>
  <div class="wf-today-list">{focus}</div>
</div>
<div class="notepad-card" style="margin-bottom:20px">
<div class="notepad-header"><div class="notepad-title-row"><span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Tasks This Week</span></div></div>
  <div class="notepad-body"><div class="bar-chart">{todo_bars}</div></div>
</div>
<div class="notepad-card" style="margin-bottom:28px">
<div class="notepad-header"><div class="notepad-title-row"><span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--slate-400)">Habits This Week</span></div></div>
  <div class="notepad-body">
    <div class="week-labels"><div style="flex:1"></div>{week_label_html}</div>
    {habit_grid_html}
  </div>
</div>'''

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

  {body_html}

  {projects_html}

</div>
{tabs_html}
</body></html>'''
