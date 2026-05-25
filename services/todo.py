import json, os
from datetime import datetime, date, timedelta

DATA_ROOT = os.path.expanduser("~/.appdata")

META = {
    "name": "Tasks",
    "path": "/todo",
    "icon": "✅",
    "description": "Task management",
}


def _files(user):
    d = os.path.join(DATA_ROOT, user or "guest")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "todo.json"), os.path.join(d, "habits.json")


def load(user):
    todo_file, _ = _files(user)
    if not os.path.exists(todo_file):
        return []
    try:
        with open(todo_file) as f:
            return json.load(f)
    except Exception:
        return []


def save(todos, user):
    todo_file, _ = _files(user)
    with open(todo_file, "w") as f:
        json.dump(todos, f, ensure_ascii=False, indent=2)


def load_habits(user):
    _, habits_file = _files(user)
    if not os.path.exists(habits_file):
        return []
    try:
        with open(habits_file) as f:
            data = json.load(f)
            if isinstance(data, dict):
                data["id"] = 1
                data = [data]
            return data
    except Exception:
        return []


def save_habits(habits, user):
    _, habits_file = _files(user)
    with open(habits_file, "w") as f:
        json.dump(habits, f, ensure_ascii=False, indent=2)


def next_id(items):
    return max((t["id"] for t in items), default=0) + 1


def days_left(due_date_str):
    if not due_date_str:
        return None
    return (date.fromisoformat(due_date_str) - date.today()).days


def due_badge(due_date_str, done):
    if done or not due_date_str:
        return ""
    n = days_left(due_date_str)
    if n < 0:
        return f'<span class="badge overdue">D+{abs(n)} overdue</span>'
    if n == 0:
        return '<span class="badge dday">D-Day</span>'
    return f'<span class="badge due">D-{n}</span>'


def early_badge(due_date_str, done_at_str):
    if not due_date_str or not done_at_str:
        return ""
    days_early = (date.fromisoformat(due_date_str) - date.fromisoformat(done_at_str[:10])).days
    if days_early > 0:
        return f'<span class="badge early">🎉 {days_early}d ahead!</span>'
    return ""


def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user", "guest")
    todos = load(user)

    if method == "POST":
        if path == "/todo/add":
            title = body.get("title", [""])[0].strip()
            due_date_raw = body.get("due_date", [""])[0].strip()
            due_date = due_date_raw if due_date_raw else None
            if title:
                todos.append({
                    "id": next_id(todos),
                    "title": title,
                    "done": False,
                    "created_at": datetime.now().isoformat(),
                    "due_date": due_date,
                })
                save(todos, user)
        elif path == "/todo/done":
            tid = int(body.get("id", [0])[0])
            for t in todos:
                if t["id"] == tid and not t["done"]:
                    t["done"] = True
                    t["done_at"] = datetime.now().isoformat()
            save(todos, user)
        elif path == "/todo/undone":
            tid = int(body.get("id", [0])[0])
            for t in todos:
                if t["id"] == tid and t["done"]:
                    t["done"] = False
                    t.pop("done_at", None)
            save(todos, user)
        elif path == "/todo/delete":
            tid = int(body.get("id", [0])[0])
            save([t for t in todos if t["id"] != tid], user)
        elif path == "/todo/to_habit":
            tid = int(body.get("id", [0])[0])
            for t in todos:
                if t["id"] == tid:
                    habits = load_habits(user)
                    existing_hid = t.get("habit_id")
                    if not existing_hid or not any(h["id"] == existing_hid for h in habits):
                        hid = next_id(habits)
                        habits.append({
                            "id": hid,
                            "name": t["title"],
                            "icon": "✅",
                            "freq": "daily",
                            "started": date.today().isoformat(),
                            "checkins": [],
                        })
                        save_habits(habits, user)
                        t["habit_id"] = hid
            save(todos, user)
        return ("redirect", "/todo")

    return ("html", render(load(user), load_habits(user), user))


def render(todos, habits, user, readonly=False):
    today_str = date.today().isoformat()
    total = len(todos)
    done_count = sum(1 for t in todos if t["done"])

    # ── Habit section ────────────────────────────────────────
    habit_index = {h["id"]: h for h in habits}
    if habits:
        habit_rows = ""
        checked_count = sum(1 for h in habits if today_str in h.get("checkins", []))
        for h in habits:
            checked = today_str in h.get("checkins", [])
            streak = 0
            d = date.today()
            cs = set(h.get("checkins", []))
            while d.isoformat() in cs:
                streak += 1
                d -= timedelta(days=1)

            if checked:
                checkin_html = '<span class="hb-done">✓ Done</span>'
            elif readonly:
                checkin_html = '<span class="hb-done" style="color:#94a3b8">Not done</span>'
            else:
                checkin_html = (
                    f'<form method="POST" action="/habit/{h["id"]}/checkin" style="display:inline">'
                    f'<input type="hidden" name="next" value="/todo">'
                    f'<button class="btn hb-check">Check in</button></form>'
                )

            habit_rows += f'''
            <div class="habit-item {"habit-checked" if checked else ""}">
              <span class="h-icon">{h.get("icon","✅")}</span>
              <span class="h-name">{h["name"]}</span>
              <span class="h-streak">🔥 {streak}d</span>
              <div class="h-actions">
                {checkin_html}
                <a href="/habit/{h["id"]}" class="btn hb-detail">Detail</a>
              </div>
            </div>'''

        habit_section = f'''
        <div class="habits-section">
          <div class="habits-header">
            <span class="habits-title">🔄 Today's Habits</span>
            <span class="habits-meta">{today_str} &nbsp; {checked_count}/{len(habits)} done</span>
          </div>
          <div class="habit-items">{habit_rows}</div>
          <a href="/habit" class="habits-link">+ Manage Habits →</a>
        </div>'''
    else:
        habit_section = f'''
        <div class="habits-section habits-empty">
          <span>🔄 Today's Habits</span>
          <a href="/habit" class="habits-link">Add Habit →</a>
        </div>'''

    # ── Todo items ───────────────────────────────────────────
    items = ""
    for t in todos:
        created = t.get("created_at", "")[:10]
        due_date = t.get("due_date")
        due_str = due_date or ""
        done_at = t.get("done_at")
        habit_id = t.get("habit_id")

        if readonly:
            badge = early_badge(due_date, done_at) if t["done"] else due_badge(due_date, t["done"])
            actions_html = ""
        elif t["done"]:
            badge = early_badge(due_date, done_at)
            action_btn = f'<form method="POST" action="/todo/undone" style="display:inline"><input type="hidden" name="id" value="{t["id"]}"><button class="btn btn-undo">Restore</button></form>'
            actions_html = f'''
              {action_btn}
              <form method="POST" action="/todo/delete" style="display:inline">
                <input type="hidden" name="id" value="{t["id"]}">
                <button class="btn btn-del">Delete</button>
              </form>'''
        else:
            badge = due_badge(due_date, t["done"])
            done_btn = f'<form method="POST" action="/todo/done" style="display:inline"><input type="hidden" name="id" value="{t["id"]}"><button class="btn btn-done">Done</button></form>'
            habit_exists = habit_id and habit_id in habit_index
            if habit_exists:
                habit_btn = f'<a href="/habit/{habit_id}" class="btn btn-habit linked">🏃 View Habit</a>'
            else:
                habit_btn = f'<form method="POST" action="/todo/to_habit" style="display:inline"><input type="hidden" name="id" value="{t["id"]}"><button class="btn btn-habit">🏃 Make Habit</button></form>'
            actions_html = f'''
              {done_btn}
              {habit_btn}
              <form method="POST" action="/todo/delete" style="display:inline">
                <input type="hidden" name="id" value="{t["id"]}">
                <button class="btn btn-del">Delete</button>
              </form>'''

        items += f'''
        <div class="todo-item {"done" if t["done"] else ""}">
          <span class="tid">#{t["id"]}</span>
          <span class="title">{t["title"]}</span>
          <span class="date">{created}</span>
          <span class="due-date">{due_str}</span>
          {badge}
          <div class="actions">{actions_html}</div>
        </div>'''

    if not todos:
        items = '<div class="empty">No tasks yet 🎉</div>'

    add_form = "" if readonly else (
        '<form class="add-form" method="POST" action="/todo/add">'
        '<input type="text" name="title" placeholder="New task..." autofocus required>'
        '<input type="date" name="due_date">'
        '<button type="submit">Add</button>'
        '</form>'
    )

    from server import app_tabs
    tabs_html = app_tabs("/todo")
    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>✅ Tasks</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.badge {{ font-size: 0.75rem; padding: 4px 8px; border-radius: 6px; font-weight: 600; letter-spacing: -0.02em; }}
.badge.due {{ background: var(--slate-100); color: var(--blue-500); }}
.badge.overdue {{ background: #fef2f2; color: #ef4444; border: 1px solid #fecaca; }}
.badge.dday {{ background: #fffbeb; color: #f59e0b; border: 1px solid #fde68a; }}
.badge.early {{ background: #f0fdf4; color: #10b981; }}

.btn {{ padding: 6px 12px; border: none; border-radius: 8px; font-size: 0.85rem; font-weight: 600; cursor: pointer; transition: 0.2s; }}
.btn-done {{ background: var(--slate-100); color: var(--slate-500); }}
.btn-done:hover {{ background: var(--blue-500); color: white; }}
.btn-undo {{ background: #fef9c3; color: #854d0e; }}
.btn-habit {{ background: var(--slate-50); color: var(--slate-500); border: 1px solid var(--slate-200); text-decoration: none; }}
.btn-habit.linked {{ background: #dcfce7; color: #166534; }}
.btn-del {{ background: transparent; color: var(--slate-400); font-weight: 500; }}
.btn-del:hover {{ color: #ef4444; background: #fef2f2; }}

.todo-item {{
  display: flex; align-items: center; gap: 16px;
  background: white; padding: 16px 20px; border-radius: var(--radius-lg);
  border: 1px solid var(--slate-200); margin-bottom: 8px;
  transition: box-shadow 0.2s, transform 0.2s;
  position: relative; overflow: hidden;
}}
.todo-item:hover {{ box-shadow: 0 4px 12px rgba(0,0,0,0.05); transform: translateY(-2px); }}
.todo-item::before {{ content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 4px; background: var(--blue-500); }}
.todo-item.done::before {{ background: var(--slate-200); }}
.todo-item.done {{ opacity: 0.6; background: var(--slate-50); box-shadow: none; transform: none; }}
.todo-item.done .title {{ text-decoration: line-through; color: var(--slate-400); }}
.tid {{ font-size: 0.75rem; color: var(--slate-300); min-width: 28px; }}
.title {{ flex: 1; font-size: 0.95rem; }}
.date {{ font-size: 0.75rem; color: var(--slate-300); }}
.due-date {{ font-size: 0.75rem; color: var(--slate-400); }}
.actions {{ display: flex; gap: 6px; }}

.habits-section {{
  background: white; border: 1px solid var(--slate-200);
  border-radius: var(--radius-lg); padding: 20px; margin-bottom: 32px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.02);
}}
.habits-section.habits-empty {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px;
}}
.habits-header {{
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
}}
.habits-title {{ font-weight: 800; font-size: 1.1rem; color: var(--slate-900); }}
.habits-meta {{ font-size: 0.85rem; color: var(--slate-500); }}
.habit-items {{ display: flex; flex-direction: column; gap: 8px; }}
.habit-item {{
  display: flex; align-items: center; gap: 12px;
  background: var(--slate-50); padding: 12px 16px; border-radius: 12px;
  border: 1px solid transparent; transition: 0.2s;
}}
.habit-item:hover {{ border-color: var(--slate-200); background: white; }}
.habit-item.habit-checked {{ opacity: 0.6; }}
.h-icon {{ font-size: 1.1rem; flex-shrink: 0; }}
.h-name {{ flex: 1; font-size: 0.9rem; font-weight: 500; color: var(--slate-900); }}
.h-streak {{ font-size: 0.8rem; color: #f59e0b; font-weight: 700; white-space: nowrap; }}
.h-actions {{ display: flex; gap: 6px; align-items: center; flex-shrink: 0; }}
.hb-check {{ background: var(--slate-900); color: white; font-size: 0.78rem; padding: 4px 10px; border-radius: 6px; border: none; cursor: pointer; font-weight: 600; transition: 0.2s; }}
.hb-check:hover {{ opacity: 0.85; }}
.hb-done {{ font-size: 0.78rem; color: #10b981; font-weight: 600; padding: 4px 6px; }}
.hb-detail {{ background: var(--slate-50); color: var(--slate-600); font-size: 0.78rem; text-decoration: none; padding: 4px 10px; border-radius: 6px; border: 1px solid var(--slate-200); transition: 0.2s; }}
.hb-detail:hover {{ border-color: var(--blue-500); color: var(--blue-500); }}
.habits-link {{ display: inline-block; margin-top: 12px; font-size: 0.82rem; color: var(--blue-500); text-decoration: none; font-weight: 500; }}
.habits-link:hover {{ text-decoration: underline; }}

@media (max-width: 600px) {{
  .todo-item {{ flex-wrap: wrap; padding: 10px 12px; gap: 10px; }}
  .actions {{ width: 100%; justify-content: flex-end; margin-top: 6px; flex-wrap: wrap; gap: 6px; }}
  .title {{ font-size: 0.9rem; }}
  .date, .due-date {{ font-size: 0.72rem; }}
  .tid {{ display: none; }}
  .btn {{ min-height: 44px; padding: 8px 12px; display: inline-flex; align-items: center; justify-content: center; }}
  .habit-item {{ flex-wrap: wrap; gap: 8px; padding: 10px 12px; }}
  .h-actions {{ width: 100%; justify-content: flex-end; margin-top: 4px; flex-wrap: wrap; gap: 6px; }}
  .hb-check, .hb-detail {{ min-height: 40px; padding: 8px 12px; font-size: 0.8rem; }}
  .habits-section {{ padding: 14px 16px; }}
  .habits-title {{ font-size: 1rem; }}
  .h-name {{ font-size: 0.85rem; }}
  .h-streak {{ font-size: 0.78rem; }}
  .add-form {{ flex-direction: column; gap: 8px; }}
  .add-form input, .add-form button {{ width: 100%; min-height: 44px; font-size: 1rem; }}
}}
</style>
</head><body>
<nav>
  <span class="nav-brand">✅ Tasks</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container">
  {habit_section}
  {add_form}
  <div class="stats">
    <span>Total {total}</span><span class="done-c">Done {done_count}</span><span>Remaining {total - done_count}</span>
  </div>
  <div class="todo-list">{items}</div>
</div>
{tabs_html}
<script>
document.addEventListener('keydown', function(e) {{
  if (e.key !== 'Enter' || e.target.tagName !== 'INPUT') return;
  var t = e.target.type;
  if (t === 'submit' || t === 'button' || t === 'checkbox' || t === 'radio') return;
  e.preventDefault();
  var form = e.target.closest('form');
  if (!form) return;
  var inputs = Array.from(form.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea'));
  var idx = inputs.indexOf(e.target);
  if (idx < inputs.length - 1) inputs[idx + 1].focus();
}});
</script>
</body></html>'''
