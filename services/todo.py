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


def _groups_file(user):
    d = os.path.join(DATA_ROOT, user or "guest")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "task_groups.json")


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


def load_groups(user):
    f = _groups_file(user)
    if not os.path.exists(f):
        return []
    try:
        with open(f) as fp:
            return json.load(fp)
    except Exception:
        return []


def save_groups(groups, user):
    with open(_groups_file(user), "w") as f:
        json.dump(groups, f, ensure_ascii=False)


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
            new_group = body.get("new_group", [""])[0].strip()
            group = body.get("group", [""])[0].strip()
            actual_group = new_group if new_group else (group if group else None)
            if new_group:
                groups = load_groups(user)
                if new_group not in groups:
                    groups.append(new_group)
                    save_groups(groups, user)
            if title:
                todos.append({
                    "id": next_id(todos),
                    "title": title,
                    "done": False,
                    "created_at": datetime.now().isoformat(),
                    "due_date": due_date,
                    "group": actual_group,
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
        elif path == "/todo/reorder":
            ids_str = body.get("ids", [""])[0]
            if ids_str:
                try:
                    ordered_ids = [int(i) for i in ids_str.split(",") if i.strip()]
                    id_map = {t["id"]: t for t in todos}
                    reordered = [id_map[i] for i in ordered_ids if i in id_map]
                    rest = [t for t in todos if t["id"] not in set(ordered_ids)]
                    save(reordered + rest, user)
                except (ValueError, KeyError):
                    pass
            return ("json", {"ok": True})
        elif path == "/todo/group/add":
            name = body.get("name", [""])[0].strip()
            if name:
                groups = load_groups(user)
                if name not in groups:
                    groups.append(name)
                    save_groups(groups, user)
        elif path == "/todo/group/delete":
            name = body.get("name", [""])[0].strip()
            groups = load_groups(user)
            save_groups([g for g in groups if g != name], user)
            for t in todos:
                if t.get("group") == name:
                    t["group"] = None
            save(todos, user)
        elif path == "/todo/set_group":
            tid = int(body.get("id", [0])[0])
            g = body.get("group", [""])[0].strip() or None
            for t in todos:
                if t["id"] == tid:
                    t["group"] = g
            save(todos, user)
        return ("redirect", "/todo")

    return ("html", render(load(user), load_habits(user), user))


def render(todos, habits, user, readonly=False):
    today_str = date.today().isoformat()
    groups = load_groups(user)

    # Sort active tasks: soonest due first, no due date → bottom
    def _due_key(t):
        d = t.get("due_date")
        return d if d else "9999-99-99"

    active = sorted([t for t in todos if not t.get("done")], key=_due_key)
    done_list = [t for t in todos if t.get("done")]
    total = len(todos)
    done_count = len(done_list)

    # Group active tasks
    task_by_group = {}
    ungrouped = []
    seen_groups = []
    for t in active:
        g = t.get("group") or ""
        if g:
            if g not in task_by_group:
                task_by_group[g] = []
                if g not in seen_groups:
                    seen_groups.append(g)
            task_by_group[g].append(t)
        else:
            ungrouped.append(t)

    all_groups = groups + [g for g in seen_groups if g not in groups]

    # ── Habit section (at BOTTOM of page) ─────────────────────
    habit_index = {h["id"]: h for h in habits}
    if habits:
        habit_rows = ""
        checked_count = sum(1 for h in habits if today_str in h.get("checkins", []))
        for h in habits:
            checked = today_str in h.get("checkins", [])
            streak = 0
            d = date.today()
            cs = set(h.get("checkins", []) if isinstance(h.get("checkins"), list) else h.get("checkins", {}).keys())
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
        <details class="habits-accordion">
          <summary class="habits-header">
            <span class="habits-title">🔄 Today\'s Habits</span>
            <span class="habits-meta">{today_str} &nbsp;·&nbsp; {checked_count}/{len(habits)} done</span>
          </summary>
          <div class="habit-items">{habit_rows}</div>
          <a href="/habit" class="habits-link">+ Manage Habits →</a>
        </details>'''
    else:
        habit_section = f'''
        <div class="habits-section habits-empty">
          <span>🔄 Today\'s Habits</span>
          <a href="/habit" class="habits-link">Add Habit →</a>
        </div>'''

    # ── Item renderer ──────────────────────────────────────────
    def item_html(t):
        created = t.get("created_at", "")[:10]
        due_date = t.get("due_date")
        due_str = due_date or ""
        done_at = t.get("done_at")
        habit_id = t.get("habit_id")
        t_group = t.get("group") or ""

        if readonly:
            badge = early_badge(due_date, done_at) if t["done"] else due_badge(due_date, t["done"])
            actions_html = ""
        elif t["done"]:
            badge = early_badge(due_date, done_at)
            actions_html = f'''
              <form method="POST" action="/todo/undone" style="display:inline"><input type="hidden" name="id" value="{t["id"]}"><button class="btn btn-undo">Restore</button></form>
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
            group_opts = '<option value="">No group</option>' + "".join(
                f'<option value="{g}" {"selected" if g == t_group else ""}>{g}</option>'
                for g in all_groups
            )
            t_group_label = t_group if t_group else "No group"
            group_sel = (
                f'<form method="POST" action="/todo/set_group" class="group-sel-form">'
                f'<input type="hidden" name="id" value="{t["id"]}">'
                f'<select name="group" onchange="this.form.submit()" class="group-select-inline" title="Move to group">'
                f'{group_opts}'
                f'</select></form>'
            )
            actions_html = f'''
              {done_btn}
              {habit_btn}
              {group_sel}
              <form method="POST" action="/todo/delete" style="display:inline">
                <input type="hidden" name="id" value="{t["id"]}">
                <button class="btn btn-del">Delete</button>
              </form>'''

        drag_attr = 'draggable="true"' if not t["done"] else ""
        drag_handle = '<span class="drag-handle" title="Drag to reorder">⠿</span>' if not t["done"] else ""
        return f'''
        <div class="todo-item {"done" if t["done"] else ""}" data-id="{t["id"]}" {drag_attr}>
          {drag_handle}
          <span class="tid">#{t["id"]}</span>
          <span class="title">{t["title"]}</span>
          <span class="date">{created}</span>
          <span class="due-date">{due_str}</span>
          {badge}
          <div class="actions">{actions_html}</div>
        </div>'''

    # ── Build task sections ────────────────────────────────────
    todo_sections = ""

    # Ungrouped tasks (no accordion wrapper)
    if ungrouped:
        items_html = "".join(item_html(t) for t in ungrouped)
        todo_sections += f'<div class="todo-list" data-group="">{items_html}</div>'
    elif not active and not done_list and not all_groups:
        todo_sections += '<div class="empty">No tasks yet 🎉</div>'

    # Named groups
    for g in all_groups:
        tasks = task_by_group.get(g, [])
        count = len(tasks)
        count_badge = f'<span class="group-count-badge">{count}</span>' if count else '<span class="group-count-badge empty">0</span>'
        items_html = "".join(item_html(t) for t in tasks) if tasks else '<div class="group-empty">No tasks in this group</div>'
        del_form = "" if readonly else (
            f'<form method="POST" action="/todo/group/delete" style="display:inline;margin-left:auto" '
            f'onsubmit="return confirm(\'Delete group &quot;{g}&quot;?\')">'
            f'<input type="hidden" name="name" value="{g}">'
            f'<button class="group-del-btn" type="submit" title="Delete group">×</button></form>'
        )
        todo_sections += f'''
        <details open class="group-accordion">
          <summary class="group-summary">
            <span class="group-chevron">▶</span>
            <span class="group-name-lbl">{g}</span>
            {count_badge}
            {del_form}
          </summary>
          <div class="todo-list group-body" data-group="{g}">{items_html}</div>
        </details>'''

    # Done section (collapsed by default)
    if done_list:
        done_items = "".join(item_html(t) for t in done_list)
        todo_sections += f'''
        <details class="group-accordion done-accordion">
          <summary class="group-summary done-summary">
            <span class="group-chevron">▶</span>
            <span class="group-name-lbl">✓ Completed</span>
            <span class="group-count-badge">{done_count}</span>
          </summary>
          <div class="todo-list group-body">{done_items}</div>
        </details>'''

    # ── Add form ───────────────────────────────────────────────
    if not readonly:
        group_options = '<option value="">No group</option>' + "".join(
            f'<option value="{g}">{g}</option>' for g in all_groups
        ) + '<option value="__new__">+ New group...</option>'
        add_form = f'''
        <div id="addTaskCard" style="display:none">
          <form class="add-form" method="POST" action="/todo/add" id="addTaskForm">
            <input type="text" name="title" placeholder="Task name..." id="taskTitleInput" required>
            <input type="date" name="due_date">
            <select name="group" id="groupSelect" onchange="toggleNewGroup(this)">
              {group_options}
            </select>
            <input type="text" name="new_group" id="newGroupInput" placeholder="Group name" style="display:none;flex:0 0 120px">
            <button type="submit">Add</button>
            <button type="button" onclick="toggleAddTask()" class="btn-cancel-task">✕</button>
          </form>
        </div>'''
    else:
        add_form = ""

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
.todo-item.dragging {{ opacity: 0.4; box-shadow: 0 8px 24px rgba(0,0,0,0.15); transform: scale(1.02); border-color: var(--blue-500); }}
.drag-handle {{ cursor: grab; color: var(--slate-300); font-size: 1rem; padding: 0 2px; flex-shrink: 0; user-select: none; touch-action: none; }}
.drag-handle:hover {{ color: var(--slate-500); }}
.drag-handle:active {{ cursor: grabbing; }}
.tid {{ font-size: 0.75rem; color: var(--slate-300); min-width: 28px; }}
.title {{ flex: 1; font-size: 0.95rem; }}
.date {{ font-size: 0.75rem; color: var(--slate-300); }}
.due-date {{ font-size: 0.75rem; color: var(--slate-400); }}
.actions {{ display: flex; gap: 6px; align-items: center; flex-wrap: wrap; }}
.group-sel-form {{ display: inline-flex; align-items: center; }}
.group-select-inline {{
  font-size: 0.75rem; padding: 3px 6px; border-radius: 6px;
  border: 1px solid var(--slate-200); background: var(--slate-50);
  color: var(--slate-500); cursor: pointer;
}}

/* Group accordion */
.group-accordion {{
  background: white; border: 1px solid var(--slate-200);
  border-radius: var(--radius-lg); margin-bottom: 12px;
  overflow: hidden;
}}
.group-accordion[open] > .group-summary .group-chevron {{ transform: rotate(90deg); }}
.group-summary {{
  display: flex; align-items: center; gap: 10px;
  padding: 14px 20px; cursor: pointer; list-style: none;
  user-select: none; background: var(--slate-50);
  border-bottom: 1px solid transparent;
}}
.group-accordion[open] > .group-summary {{ border-bottom-color: var(--slate-100); }}
.group-summary::-webkit-details-marker {{ display: none; }}
.group-chevron {{ font-size: 0.7rem; color: var(--slate-400); transition: transform 0.2s; display: inline-block; }}
.group-name-lbl {{ font-weight: 700; font-size: 0.9rem; color: var(--slate-700); flex: 1; }}
.group-count-badge {{
  font-size: 0.72rem; font-weight: 700; padding: 2px 8px;
  background: var(--blue-500); color: white; border-radius: 99px; min-width: 20px; text-align: center;
}}
.group-count-badge.empty {{ background: var(--slate-200); color: var(--slate-500); }}
.group-del-btn {{
  background: transparent; border: none; color: var(--slate-300);
  font-size: 1.1rem; cursor: pointer; padding: 0 4px; line-height: 1;
  transition: color 0.2s;
}}
.group-del-btn:hover {{ color: #ef4444; }}
.group-body {{ padding: 12px 12px 4px; }}
.group-empty {{ color: var(--slate-400); font-size: 0.85rem; padding: 12px 8px; text-align: center; }}
.done-accordion {{ opacity: 0.9; }}
.done-summary {{ background: var(--slate-50); }}
.done-summary .group-name-lbl {{ color: var(--slate-500); }}
.done-summary .group-count-badge {{ background: var(--slate-300); }}

.btn-add-new {{
  padding: 6px 16px; background: var(--slate-900); color: white;
  border: none; border-radius: 8px; font-size: 13px; font-weight: 700;
  cursor: pointer; transition: opacity .15s; white-space: nowrap;
}}
.btn-add-new:hover {{ opacity: .8; }}
.btn-cancel-task {{
  padding: 6px 12px; background: transparent; color: var(--slate-400);
  border: 1px solid var(--slate-200); border-radius: 8px; font-size: 0.85rem;
  cursor: pointer; transition: 0.2s;
}}
.btn-cancel-task:hover {{ color: #ef4444; border-color: #ef4444; }}
.task-list-header {{
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 16px;
}}
#addTaskCard {{
  background: white; border: 1px solid var(--slate-200); border-radius: var(--radius-lg);
  padding: 20px; margin-bottom: 16px; box-shadow: 0 4px 12px rgba(0,0,0,0.06);
}}

/* Habits accordion (at bottom) */
.habits-accordion {{
  background: white; border: 1px solid var(--slate-200);
  border-radius: var(--radius-lg); margin-top: 24px; overflow: hidden;
}}
.habits-accordion > .habits-header {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px; cursor: pointer; list-style: none;
  background: var(--slate-50); user-select: none;
}}
.habits-accordion > .habits-header::-webkit-details-marker {{ display: none; }}
.habits-accordion[open] > .habits-header {{ border-bottom: 1px solid var(--slate-100); }}
.habits-accordion .habit-items {{ display: flex; flex-direction: column; gap: 8px; padding: 12px 20px; }}
.habits-section.habits-empty {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px; background: white; border: 1px solid var(--slate-200);
  border-radius: var(--radius-lg); margin-top: 24px;
}}
.habits-title {{ font-weight: 800; font-size: 1rem; color: var(--slate-900); }}
.habits-meta {{ font-size: 0.85rem; color: var(--slate-500); }}
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
.habits-link {{ display: inline-block; margin: 8px 20px 16px; font-size: 0.82rem; color: var(--blue-500); text-decoration: none; font-weight: 500; }}
.habits-link:hover {{ text-decoration: underline; }}

@media (max-width: 600px) {{
  .todo-item {{ flex-wrap: wrap; padding: 10px 12px; gap: 8px; }}
  .actions {{ width: 100%; justify-content: flex-start; margin-top: 4px; flex-wrap: wrap; gap: 6px; }}
  .title {{ font-size: 0.9rem; min-width: 0; word-break: break-word; }}
  .date {{ display: none; }}
  .due-date {{ font-size: 0.72rem; }}
  .tid {{ display: none; }}
  .btn {{ min-height: 44px; padding: 8px 14px; display: inline-flex; align-items: center; justify-content: center; }}
  .btn-habit:not(.linked) {{ display: none; }}
  .btn-habit.linked {{ font-size: 0.78rem; padding: 6px 10px; min-height: 36px; }}
  .group-sel-form {{ order: 10; width: 100%; margin-top: 2px; display: flex; }}
  .group-select-inline {{ width: 100%; min-height: 40px; font-size: 0.88rem; padding: 8px 10px; border-radius: 8px; }}
  .habit-item {{ flex-wrap: wrap; gap: 8px; padding: 10px 12px; }}
  .h-actions {{ width: 100%; justify-content: flex-end; margin-top: 4px; flex-wrap: wrap; gap: 6px; }}
  .hb-check, .hb-detail {{ min-height: 40px; padding: 8px 12px; font-size: 0.8rem; }}
  .add-form {{ flex-direction: column; gap: 8px; }}
  .add-form input, .add-form select {{ width: 100%; min-height: 44px; font-size: 1rem; }}
  .add-form button {{ min-height: 44px; font-size: 1rem; }}
  .btn-add-new {{ min-height: 40px; padding: 8px 16px; }}
  .group-summary {{ padding: 12px 14px; }}
  .group-body {{ padding: 8px 8px 4px; }}
}}
</style>
</head><body>
<nav>
  <span class="nav-brand">✅ Tasks</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container">
  {add_form}
  <div class="task-list-header">
    <div class="stats">
      <span>Total {total}</span><span class="done-c">Done {done_count}</span><span>Remaining {total - done_count}</span>
    </div>
    {"" if readonly else '<button type="button" onclick="toggleAddTask()" class="btn-add-new">＋ New Task</button>'}
  </div>
  {todo_sections}
  {habit_section}
</div>
{tabs_html}
<script>
function toggleAddTask() {{
  var card = document.getElementById('addTaskCard');
  if (!card) return;
  var open = card.style.display !== 'none';
  card.style.display = open ? 'none' : 'block';
  if (!open) {{
    card.scrollIntoView({{behavior:'smooth', block:'nearest'}});
    setTimeout(function() {{
      var inp = document.getElementById('taskTitleInput');
      if (inp) inp.focus();
    }}, 100);
  }}
}}

function toggleNewGroup(sel) {{
  var inp = document.getElementById('newGroupInput');
  if (!inp) return;
  if (sel.value === '__new__') {{
    inp.style.display = 'block';
    inp.required = true;
    inp.focus();
    sel.value = '';
  }} else {{
    inp.style.display = 'none';
    inp.required = false;
    inp.value = '';
  }}
}}

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

(function() {{
  var dragged = null;
  var clone = null;
  var offsetY = 0;

  function getList(el) {{
    return el.closest('.todo-list');
  }}

  function saveOrder(list) {{
    var ids = Array.from(list.querySelectorAll('.todo-item[draggable]')).map(function(el) {{ return el.dataset.id; }});
    if (ids.length > 0) {{
      fetch('/todo/reorder', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
        body: 'ids=' + ids.join(',')
      }});
    }}
  }}

  function insertAt(list, clientY) {{
    var items = Array.from(list.querySelectorAll('.todo-item[draggable]')).filter(function(el) {{ return el !== dragged; }});
    var after = null;
    for (var i = 0; i < items.length; i++) {{
      var rect = items[i].getBoundingClientRect();
      if (clientY < rect.top + rect.height / 2) {{ after = items[i]; break; }}
    }}
    list.insertBefore(dragged, after);
  }}

  document.addEventListener('dragstart', function(e) {{
    dragged = e.target.closest('.todo-item[draggable]');
    if (!dragged) return;
    dragged.classList.add('dragging');
    e.dataTransfer.effectAllowed = 'move';
  }});
  document.addEventListener('dragend', function() {{
    if (!dragged) return;
    dragged.classList.remove('dragging');
    var list = getList(dragged);
    if (list) saveOrder(list);
    dragged = null;
  }});
  document.addEventListener('dragover', function(e) {{
    e.preventDefault();
    if (!dragged) return;
    var list = getList(e.target.closest('.todo-item') || e.target);
    if (list) insertAt(list, e.clientY);
  }});

  document.addEventListener('touchstart', function(e) {{
    var handle = e.target.closest('.drag-handle');
    if (!handle) return;
    dragged = handle.closest('.todo-item[draggable]');
    if (!dragged) return;
    var touch = e.touches[0];
    var rect = dragged.getBoundingClientRect();
    offsetY = touch.clientY - rect.top;
    clone = dragged.cloneNode(true);
    clone.style.cssText = 'position:fixed;left:' + rect.left + 'px;width:' + rect.width + 'px;top:' + rect.top + 'px;z-index:9999;opacity:.85;pointer-events:none;box-shadow:0 8px 24px rgba(0,0,0,.18);border-radius:14px;background:white;';
    document.body.appendChild(clone);
    dragged.style.opacity = '.25';
    e.preventDefault();
  }}, {{passive: false}});

  document.addEventListener('touchmove', function(e) {{
    if (!dragged || !clone) return;
    var touch = e.touches[0];
    clone.style.top = (touch.clientY - offsetY) + 'px';
    clone.style.display = 'none';
    var under = document.elementFromPoint(touch.clientX, touch.clientY);
    clone.style.display = '';
    if (under) {{
      var list = getList(under.closest('.todo-item') || under);
      if (list) insertAt(list, touch.clientY);
    }}
    e.preventDefault();
  }}, {{passive: false}});

  document.addEventListener('touchend', function() {{
    if (!dragged) return;
    dragged.style.opacity = '';
    if (clone) {{ clone.remove(); clone = null; }}
    var list = getList(dragged);
    if (list) saveOrder(list);
    dragged = null;
  }});
}})();
</script>
</body></html>'''
