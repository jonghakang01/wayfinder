import json, os, subprocess
from datetime import date, timedelta, datetime

DATA_ROOT = os.path.expanduser("~/.appdata")
REPO_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ALLOWED_USER = "jongha.kang"

META = {
    "name": "Dev Log",
    "path": "/report",
    "icon": "📓",
    "description": "Daily development report",
    "hidden": True,
}


def _log_path():
    return os.path.join(DATA_ROOT, ALLOWED_USER, "daily_log.json")


def _load_log():
    f = _log_path()
    if not os.path.exists(f):
        return {}
    try:
        with open(f) as fp:
            return json.load(fp)
    except Exception:
        return {}


def _save_log(data):
    f = _log_path()
    os.makedirs(os.path.dirname(f), exist_ok=True)
    with open(f, "w") as fp:
        json.dump(data, fp, ensure_ascii=False, indent=2)


def _git_commits(days=60):
    """Returns {date_str: [msg, ...]} for the last N days."""
    since = (date.today() - timedelta(days=days)).isoformat()
    try:
        out = subprocess.check_output(
            ["git", "-C", REPO_PATH, "log",
             f"--since={since}", "--format=%ad|%s", "--date=short"],
            stderr=subprocess.DEVNULL, text=True
        )
        result = {}
        for line in out.strip().splitlines():
            if "|" not in line:
                continue
            d, msg = line.split("|", 1)
            result.setdefault(d, []).append(msg)
        return result
    except Exception:
        return {}


def _todo_stats(user, day_str):
    f = os.path.join(DATA_ROOT, user, "todo.json")
    if not os.path.exists(f):
        return 0
    try:
        todos = json.load(open(f))
        return sum(1 for t in todos if (t.get("done_at") or "").startswith(day_str))
    except Exception:
        return 0


def _habit_stats(user, day_str):
    f = os.path.join(DATA_ROOT, user, "habits.json")
    if not os.path.exists(f):
        return 0, 0
    try:
        data = json.load(open(f))
        if isinstance(data, dict):
            data = [data]
        total = len(data)
        done = sum(1 for h in data if isinstance(h.get("checkins"), dict) and h["checkins"].get(day_str, 0) >= max(1, h.get("target", 1)))
        return done, total
    except Exception:
        return 0, 0


def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user")
    if user != ALLOWED_USER:
        return ("redirect", "/")

    log = _load_log()

    if method == "POST":
        if path == "/report/note/add":
            day = body.get("day", [""])[0].strip()
            note = body.get("note", [""])[0].strip()
            if day and note:
                log.setdefault(day, {}).setdefault("notes", []).append(note)
                _save_log(log)
        elif path == "/report/note/delete":
            day = body.get("day", [""])[0].strip()
            idx_str = body.get("idx", [""])[0].strip()
            try:
                idx = int(idx_str)
                notes = log.get(day, {}).get("notes", [])
                if 0 <= idx < len(notes):
                    notes.pop(idx)
                    log[day]["notes"] = notes
                    _save_log(log)
            except (ValueError, KeyError):
                pass
        return ("redirect", "/report")

    return ("html", render(log, user))


def render(log, user):
    today = date.today()
    commits = _git_commits(days=60)

    # Build list of days that have activity (last 60 days)
    active_days = set()
    for d_str in commits:
        active_days.add(d_str)
    for d_str in log:
        active_days.add(d_str)
    # Always include last 14 days
    for i in range(14):
        active_days.add((today - timedelta(days=i)).isoformat())

    sorted_days = sorted(active_days, reverse=True)

    days_html = ""
    for day_str in sorted_days:
        d = date.fromisoformat(day_str)
        is_today = d == today
        day_commits = commits.get(day_str, [])
        day_notes = log.get(day_str, {}).get("notes", [])
        todos_done = _todo_stats(user, day_str)
        habits_done, habits_total = _habit_stats(user, day_str)

        if not day_commits and not day_notes and not todos_done and not habits_done and not is_today:
            continue

        label = "Today" if is_today else d.strftime("%b %d, %Y")
        weekday = d.strftime("%A")

        # Commits html
        commits_html = ""
        for msg in day_commits:
            commits_html += f'<div class="commit-item"><span class="commit-dot">●</span><span class="commit-msg">{msg}</span></div>'
        if not commits_html:
            commits_html = ""

        # Notes html
        notes_html = ""
        for i, note in enumerate(day_notes):
            notes_html += f'''<div class="note-item">
              <span class="note-text">{note}</span>
              <form method="POST" action="/report/note/delete" style="display:inline">
                <input type="hidden" name="day" value="{day_str}">
                <input type="hidden" name="idx" value="{i}">
                <button class="note-del" title="Delete">×</button>
              </form>
            </div>'''

        # Stats badges
        stats_badges = ""
        if todos_done:
            stats_badges += f'<span class="stat-badge todo-badge">✅ {todos_done} tasks done</span>'
        if habits_total:
            stats_badges += f'<span class="stat-badge habit-badge">🏃 {habits_done}/{habits_total} habits</span>'

        # Add note form (only for today and recent days)
        note_form = f'''
        <form class="note-form" method="POST" action="/report/note/add">
          <input type="hidden" name="day" value="{day_str}">
          <input type="text" name="note" placeholder="Add a note for {label}..." class="note-input">
          <button type="submit" class="note-add-btn">+</button>
        </form>'''

        has_content = bool(day_commits or day_notes or todos_done or habits_done)
        day_cls = "day-block today-block" if is_today else ("day-block" if has_content else "day-block empty-day")

        days_html += f'''
        <div class="{day_cls}" id="day-{day_str}">
          <div class="day-header">
            <div class="day-date-wrap">
              <span class="day-label {"today-label" if is_today else ""}">{label}</span>
              <span class="day-weekday">{weekday}</span>
            </div>
            <div class="day-stats">{stats_badges}</div>
          </div>
          {"<div class='section-title'>Dev</div>" + commits_html if commits_html else ""}
          {"<div class='section-title'>Notes</div>" if day_notes else ""}
          {notes_html}
          {note_form}
        </div>'''

    if not days_html:
        days_html = '<div class="empty-hint">No activity yet.</div>'

    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📓 Dev Log · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.report-hero{{background:var(--slate-900);background-image:radial-gradient(at 0% 0%,rgba(56,189,248,.15) 0,transparent 55%),radial-gradient(at 100% 100%,rgba(99,102,241,.18) 0,transparent 55%);border-radius:var(--radius-xl);padding:28px 32px;color:white;margin-bottom:28px;border:1px solid rgba(255,255,255,.05)}}
.report-hero h2{{font-size:1.4rem;font-weight:800;letter-spacing:-.03em;margin-bottom:4px}}
.report-hero p{{color:var(--slate-400);font-size:.85rem}}
.day-block{{background:white;border:1px solid var(--slate-200);border-radius:var(--radius-lg);padding:20px 24px;margin-bottom:16px;transition:.2s}}
.today-block{{border-color:#3b82f6;box-shadow:0 0 0 3px rgba(59,130,246,.08)}}
.empty-day{{opacity:.5}}
.day-header{{display:flex;align-items:flex-start;justify-content:space-between;margin-bottom:14px;gap:12px;flex-wrap:wrap}}
.day-date-wrap{{display:flex;flex-direction:column;gap:2px}}
.day-label{{font-size:1rem;font-weight:800;color:var(--slate-900);letter-spacing:-.02em}}
.today-label{{color:#3b82f6}}
.day-weekday{{font-size:.75rem;color:var(--slate-400);font-weight:500}}
.day-stats{{display:flex;gap:8px;flex-wrap:wrap}}
.stat-badge{{font-size:.72rem;font-weight:600;padding:3px 10px;border-radius:99px}}
.todo-badge{{background:#f0fdf4;color:#166534}}
.habit-badge{{background:#eff6ff;color:#1d4ed8}}
.section-title{{font-size:.65rem;font-weight:700;color:var(--slate-400);text-transform:uppercase;letter-spacing:.08em;margin:10px 0 6px}}
.commit-item{{display:flex;align-items:flex-start;gap:8px;padding:5px 0;border-bottom:1px solid var(--slate-100)}}
.commit-item:last-child{{border-bottom:none}}
.commit-dot{{color:#3b82f6;font-size:.5rem;margin-top:5px;flex-shrink:0}}
.commit-msg{{font-size:.82rem;color:var(--slate-700);line-height:1.4}}
.note-item{{display:flex;align-items:center;gap:8px;padding:5px 0;border-bottom:1px solid var(--slate-100)}}
.note-item:last-child{{border-bottom:none}}
.note-text{{flex:1;font-size:.85rem;color:var(--slate-800)}}
.note-del{{background:none;border:none;color:var(--slate-300);cursor:pointer;font-size:1rem;padding:0 4px;line-height:1;transition:.15s}}
.note-del:hover{{color:#ef4444}}
.note-form{{display:flex;gap:8px;margin-top:12px}}
.note-input{{flex:1;padding:7px 12px;border:1px solid var(--slate-200);border-radius:8px;font-size:.85rem;outline:none;transition:.2s}}
.note-input:focus{{border-color:#3b82f6}}
.note-add-btn{{padding:7px 14px;background:var(--slate-900);color:white;border:none;border-radius:8px;font-size:.95rem;font-weight:700;cursor:pointer;transition:.2s}}
.note-add-btn:hover{{opacity:.8}}
.empty-hint{{color:var(--slate-400);text-align:center;padding:40px;font-size:.9rem}}
@media(max-width:600px){{
  .day-block{{padding:14px 16px}}
  .report-hero{{padding:20px}}
}}
</style>
</head><body>
<nav>
  <span class="nav-brand">📓 Dev Log</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container">
  <div class="report-hero">
    <h2>Development Log</h2>
    <p>{today.strftime("%B %d, %Y")} &nbsp;·&nbsp; Git commits + daily notes</p>
  </div>
  {days_html}
</div>
<script>
document.addEventListener('keydown', function(e) {{
  if (e.key !== 'Enter' || e.target.tagName !== 'INPUT') return;
  e.preventDefault();
  e.target.closest('form').querySelector('button[type=submit]').click();
}});
</script>
</body></html>'''
