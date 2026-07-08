import json, os
from datetime import datetime, date, timedelta

from services._paths import DATA_ROOT

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
        return f'<span class="badge badge-overdue">D+{abs(n)}</span>'
    if n == 0:
        return '<span class="badge badge-dday">D-Day</span>'
    return f'<span class="badge badge-due">D-{n}</span>'


def early_badge(due_date_str, done_at_str):
    if not due_date_str or not done_at_str:
        return ""
    days_early = (date.fromisoformat(due_date_str) - date.fromisoformat(done_at_str[:10])).days
    if days_early > 0:
        return f'<span class="badge badge-early">🎉 {days_early}d ahead!</span>'
    return ""


def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user", "guest")
    todos = load(user)

    if method == "POST":
        if path == "/todo/memo/add":
            group = (body.get("group") or [""])[0].strip() or None
            body_text = (body.get("body") or [""])[0].strip()
            if body_text:
                todos.append({
                    "id": next_id(todos),
                    "type": "memo",
                    "title": body_text[:80],
                    "body": body_text,
                    "done": False,
                    "created_at": datetime.now().isoformat(),
                    "group": group,
                })
                save(todos, user)
            return ("redirect", "/todo")
        elif path == "/todo/memo/edit":
            tid = int((body.get("id") or [0])[0])
            body_text = (body.get("body") or [""])[0].strip()
            for t in todos:
                if t["id"] == tid and t.get("type") == "memo":
                    t["body"] = body_text
                    t["title"] = body_text[:80]
            save(todos, user)
            return ("redirect", "/todo")
        elif path == "/todo/add":
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
                    "type": "task",
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
        next_url = (body.get("next") or ["/todo"])[0]
        if not next_url.startswith("/"):
            next_url = "/todo"
        return ("redirect", next_url)

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

    # Separate done tasks: group-members go inside their group, rest go to global done
    done_by_group = {}
    ungrouped_done = []
    for t in done_list:
        g = t.get("group") or ""
        if g and g in all_groups:
            done_by_group.setdefault(g, []).append(t)
        else:
            ungrouped_done.append(t)

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
                    f'<button class="btn btn-primary btn-sm">Check in</button></form>'
                )
            habit_rows += f'''
            <div class="habit-item {"habit-checked" if checked else ""}">
              <span class="h-icon">{h.get("icon","✅")}</span>
              <span class="h-name">{h["name"]}</span>
              <span class="h-streak">🔥 {streak}d</span>
              <div class="h-actions">
                {checkin_html}
                <a href="/habit/{h["id"]}" class="btn btn-ghost btn-sm">Detail</a>
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
        t.setdefault("type", "task")
        item_type = t["type"]
        item_id = t["id"]

        if item_type == "memo":
            body_text = t.get("body", t.get("title", ""))
            if readonly:
                actions_html = ""
            else:
                actions_html = (
                    f'<button class="btn btn-ghost btn-sm" '
                    f'onclick="openMemoEdit({item_id},this)" type="button">Edit</button>'
                    f'<form method="POST" action="/todo/delete" style="display:inline">'
                    f'<input type="hidden" name="id" value="{item_id}">'
                    f'<button class="btn btn-danger btn-sm">x</button></form>'
                )
            return f'''
        <div class="notepad-item notepad-memo" data-id="{t["id"]}">
          <div class="item-left"><span class="item-type-dot memo-dot"></span></div>
          <div class="item-content">
            <span class="memo-text" id="memo-text-{t["id"]}">{body_text}</span>
            <form method="POST" action="/todo/memo/edit" class="memo-edit-form" id="memo-edit-{t["id"]}" style="display:none;margin-top:6px">
              <input type="hidden" name="id" value="{t["id"]}">
              <textarea name="body" class="memo-textarea" rows="2">{body_text}</textarea>
              <div style="display:flex;gap:4px;margin-top:4px">
                <button type="submit" class="btn btn-primary btn-sm">Save</button>
                <button type="button" class="btn btn-ghost btn-sm" onclick="closeMemoEdit({t["id"]})">Cancel</button>
              </div>
            </form>
          </div>
          <div class="item-actions">{actions_html}</div>
        </div>'''

        # task type
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
            actions_html = (
                f'<form method="POST" action="/todo/undone" style="display:inline">'
                f'<input type="hidden" name="id" value="{t["id"]}">'
                f'<button class="btn btn-warn">Restore</button></form>'
                f'<form method="POST" action="/todo/delete" style="display:inline">'
                f'<input type="hidden" name="id" value="{t["id"]}">'
                f'<button class="btn btn-danger">x</button></form>'
            )
        else:
            badge = due_badge(due_date, t["done"])
            done_btn = (
                f'<form method="POST" action="/todo/done" style="display:inline">'
                f'<input type="hidden" name="id" value="{t["id"]}">'
                f'<button class="btn btn-secondary">Done</button></form>'
            )
            habit_exists = habit_id and habit_id in habit_index
            if habit_exists:
                habit_btn = f'<a href="/habit/{habit_id}" class="btn btn-ghost linked">🏃 View</a>'
            else:
                habit_btn = (
                    f'<form method="POST" action="/todo/to_habit" style="display:inline">'
                    f'<input type="hidden" name="id" value="{t["id"]}">'
                    f'<button class="btn btn-ghost">Habit</button></form>'
                )
            group_opts = '<option value="">No group</option>' + "".join(
                f'<option value="{g}" {"selected" if g == t_group else ""}>{g}</option>'
                for g in all_groups
            )
            group_sel = (
                f'<form method="POST" action="/todo/set_group" class="group-sel-form">'
                f'<input type="hidden" name="id" value="{t["id"]}">'
                f'<select name="group" onchange="this.form.submit()" class="group-select-inline" title="Move to group">'
                f'{group_opts}'
                f'</select></form>'
            )
            actions_html = (
                f'{done_btn}{habit_btn}{group_sel}'
                f'<form method="POST" action="/todo/delete" style="display:inline">'
                f'<input type="hidden" name="id" value="{t["id"]}">'
                f'<button class="btn btn-danger">x</button></form>'
            )

        drag_attr = 'draggable="true"' if not t["done"] else ""
        drag_handle = '<span class="drag-handle" title="Drag to reorder">⠿</span>' if not t["done"] else ""
        done_cls = " done" if t["done"] else ""
        meta_html = ""
        if badge or due_str:
            meta_html = f'<div class="item-meta">{badge}<span class="item-date">{due_str}</span></div>'
        return f'''
        <div class="notepad-item notepad-task{done_cls}" data-id="{t["id"]}" {drag_attr}>
          <div class="item-left">{drag_handle}<span class="item-type-dot task-dot"></span></div>
          <div class="item-content">
            <span class="item-title">{t["title"]}</span>
            {meta_html}
          </div>
          <div class="item-actions">{actions_html}</div>
        </div>'''

    # ── Build task sections ────────────────────────────────────
    todo_sections = ""

    def _notepad_card(g, tasks, done_tasks, group_id="", group_idx=-1):
        count = len(tasks)
        add_btns = "" if readonly else (
            f'<div class="notepad-footer">'
            f'<button type="button" class="btn btn-ghost btn-sm" onclick="openAddTask(this)">+ Task</button>'
            f'<button type="button" class="btn btn-ghost btn-sm" onclick="openAddMemo(this)">+ Memo</button>'
            f'</div>'
            f'<div class="inline-task-form inline-add-form" style="display:none;padding:10px 12px;background:var(--surface-2);border-top:1px solid var(--notepad-line)">'
            f'<form method="POST" action="/todo/add">'
            f'<input type="hidden" name="group" value="{g}">'
            f'<div style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">'
            f'<input type="text" name="title" placeholder="Task name..." required style="flex:1;min-width:150px;padding:7px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:var(--text-sm);background:var(--surface);color:var(--text)">'
            f'<input type="date" name="due_date" style="padding:7px 8px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:var(--text-sm);background:var(--surface);color:var(--text)">'
            f'<button type="submit" class="btn btn-primary btn-sm">Add</button>'
            f'<button type="button" class="btn btn-ghost btn-sm" onclick="closeInlineForm(this)">Cancel</button>'
            f'</div></form></div>'
            f'<div class="inline-memo-form inline-add-form" style="display:none;padding:10px 12px;background:var(--surface-2);border-top:1px solid var(--notepad-line)">'
            f'<form method="POST" action="/todo/memo/add">'
            f'<input type="hidden" name="group" value="{g}">'
            f'<div style="display:flex;gap:8px;align-items:flex-start;flex-wrap:wrap">'
            f'<textarea name="body" placeholder="Memo..." rows="2" required style="flex:1;min-width:150px;padding:7px 10px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:var(--text-sm);resize:vertical;background:var(--surface);color:var(--text)"></textarea>'
            f'<div style="display:flex;gap:4px">'
            f'<button type="submit" class="btn btn-primary btn-sm">Add</button>'
            f'<button type="button" class="btn btn-ghost btn-sm" onclick="closeInlineForm(this)">Cancel</button>'
            f'</div></div></form></div>'
        )
        del_btn = "" if readonly else (
            f'<form method="POST" action="/todo/group/delete" style="display:inline" '
            f'onsubmit="return confirm(\'Delete group &quot;{g}&quot;?\')">'
            f'<input type="hidden" name="name" value="{g}">'
            f'<button class="notepad-del-btn" type="submit" title="Delete group">x</button></form>'
        )
        active_html = "".join(item_html(t) for t in tasks)
        done_html = ""
        if done_tasks:
            done_items_g = "".join(item_html(t) for t in done_tasks)
            done_html = (
                f'<details class="sub-done-accordion">'
                f'<summary class="sub-done-summary"><span class="sub-done-chevron">▶</span>'
                f' ✓ Completed ({len(done_tasks)})</summary>'
                f'<div class="sub-done-body">{done_items_g}</div>'
                f'</details>'
            )
        body_content = active_html + done_html
        if not body_content:
            body_content = '<div class="group-empty">No items in this group</div>'
        data_attr = f'data-group="{g}"'
        group_color = f"var(--group-{(group_idx % 5) + 1})" if group_idx >= 0 else "var(--text-muted)"
        return f'''
        <div class="notepad-card" style="--group-color:{group_color}">
          <div class="notepad-header">
            <div class="notepad-title-row">
              <span class="notepad-chevron" onclick="toggleNotepad(this)">▼</span>
              <span class="notepad-name">{g if g else "Ungrouped"}</span>
              <span class="notepad-count">{count}</span>
              <div class="notepad-header-actions">{del_btn}</div>
            </div>
          </div>
          <div class="notepad-body todo-list" {data_attr}>{body_content}</div>
          {add_btns}
        </div>'''

    # Ungrouped tasks
    if ungrouped or ungrouped_done or (not active and not done_list and not all_groups):
        if not ungrouped and not ungrouped_done:
            todo_sections += '<div class="empty">No tasks yet 🎉</div>'
        else:
            todo_sections += _notepad_card("", ungrouped, ungrouped_done)

    # Named groups
    for idx, g in enumerate(all_groups):
        tasks = task_by_group.get(g, [])
        done_tasks = done_by_group.get(g, [])
        todo_sections += _notepad_card(g, tasks, done_tasks, group_idx=idx)

    # ── Add form ───────────────────────────────────────────────
    add_form = ""

    from server import app_tabs
    tabs_html = app_tabs("/todo", user)

    todo_add_group_card = "" if readonly else (
        '<div id="addGroupCard" style="display:none;background:var(--surface);border:1px solid var(--border);'
        'border-radius:var(--radius-lg);padding:16px;margin-bottom:12px;box-shadow:var(--shadow-md)">'
        '<form method="POST" action="/todo/group/add" style="display:flex;gap:8px;align-items:center;flex-wrap:wrap">'
        '<input type="text" name="name" id="newGroupNameInput" placeholder="Group name..." '
        'style="flex:1;min-width:160px;padding:9px 12px;border:1px solid var(--border);border-radius:var(--radius-sm);font-size:14px;background:var(--surface-2);color:var(--text)">'
        '<button type="submit" class="btn btn-primary">Add</button>'
        '<button type="button" onclick="toggleAddGroupCard()" class="btn btn-ghost">✕</button>'
        '</form></div>'
    )
    todo_header_btns = "" if readonly else (
        '<div style="display:flex;gap:8px">'
        '<button type="button" onclick="toggleAddGroupCard()" class="btn btn-primary btn-lg">＋ New Group</button>'
        '</div>'
    )

    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>✅ Tasks</title>
<link rel="stylesheet" href="/static/style.css">
<style>
/* Badge */
.badge {{ display:inline-flex; align-items:center; height:20px; padding:0 8px; border-radius:var(--radius-full); font-size:var(--text-xs); font-weight:var(--fw-bold); }}
.badge-due     {{ background:rgba(56,189,248,0.1);   color:var(--accent); }}
.badge-overdue {{ background:rgba(248,113,113,0.12); color:var(--danger); border:1px solid rgba(248,113,113,0.3); }}
.badge-dday    {{ background:rgba(251,191,36,0.1);   color:var(--warn); border:1px solid rgba(251,191,36,0.3); }}
.badge-early   {{ background:rgba(52,211,153,0.1);   color:var(--success); }}

/* Notepad card */
.notepad-card {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg); margin-bottom:16px; box-shadow:var(--shadow-sm); overflow:hidden; }}
.notepad-tab {{ background:var(--notepad-header); border-bottom:1px solid var(--border); display:flex; align-items:center; padding:5px 20px; gap:8px; }}
.notepad-tab-dot {{ width:10px; height:10px; border-radius:50%; border:2px solid var(--accent); background:transparent; }}
.notepad-header {{ background:var(--notepad-header); padding:10px 16px 12px; }}
.notepad-title-row {{ display:flex; align-items:center; gap:10px; }}
.notepad-chevron {{ font-size:0.7rem; color:var(--text-muted); cursor:pointer; transition:transform 0.2s; user-select:none; }}
.notepad-card.collapsed .notepad-chevron {{ transform:rotate(-90deg); }}
.notepad-name {{ font-weight:var(--fw-bold); font-size:var(--text-md); color:var(--text); flex:1; }}
.notepad-count {{ font-size:var(--text-xs); font-weight:var(--fw-bold); padding:2px 9px; background:var(--accent); color:#080d14; border-radius:var(--radius-full); min-width:22px; text-align:center; }}
.notepad-del-btn {{ background:transparent; border:none; color:var(--text-dim); font-size:1.1rem; cursor:pointer; padding:0 4px; transition:color 0.15s; }}
.notepad-del-btn:hover {{ color:var(--danger); }}
.notepad-body {{ padding:8px 12px 4px; }}
.notepad-card.collapsed .notepad-body, .notepad-card.collapsed .notepad-footer {{ display:none; }}
.notepad-item {{ display:flex; align-items:flex-start; gap:10px; padding:10px 8px; border-bottom:1px solid var(--notepad-line); border-radius:var(--radius-md); transition:background 0.15s; }}
.notepad-item:last-child {{ border-bottom:none; }}
.notepad-item:hover {{ background:var(--surface-3); }}
.item-left {{ display:flex; align-items:center; gap:6px; padding-top:4px; flex-shrink:0; }}
.item-type-dot {{ width:8px; height:8px; border-radius:50%; flex-shrink:0; }}
.task-dot {{ background:var(--accent); }}
.memo-dot {{ background:var(--warn); }}
.item-content {{ flex:1; min-width:0; }}
.item-title {{ font-size:var(--text-md); font-weight:var(--fw-semibold); color:var(--text); line-height:1.4; }}
.item-meta {{ display:flex; align-items:center; gap:6px; margin-top:3px; }}
.item-date {{ font-size:var(--text-xs); color:var(--text-muted); }}
.item-actions {{ display:flex; align-items:center; gap:4px; flex-shrink:0; }}
.notepad-task.done .item-title {{ text-decoration:line-through; color:var(--text-muted); }}
.notepad-task.done {{ opacity:0.5; }}
.memo-text {{ font-size:var(--text-base); color:var(--text-muted); font-style:italic; line-height:1.5; }}
.memo-textarea {{ width:100%; padding:8px 12px; border:1px solid var(--border); border-radius:var(--radius-sm); font-size:var(--text-base); resize:vertical; background:var(--surface-2); color:var(--text); }}
.notepad-footer {{ display:flex; gap:8px; padding:8px 12px 10px; background:var(--surface-2); border-top:1px solid var(--notepad-line); }}

/* drag */
.drag-handle {{ cursor:grab; color:var(--slate-300); font-size:1rem; padding:0 2px; flex-shrink:0; user-select:none; touch-action:none; }}
.drag-handle:hover {{ color:var(--slate-500); }}
.drag-handle:active {{ cursor:grabbing; }}
.notepad-task.dragging {{ opacity:0.4; box-shadow:0 8px 24px rgba(0,0,0,0.15); border:1px solid var(--blue-500); }}

/* group select inline */
.group-sel-form {{ display:inline-flex; align-items:center; }}
.group-select-inline {{ font-size:0.75rem; padding:3px 6px; border-radius:6px; border:1px solid var(--border); background:var(--surface-2); color:var(--text-muted); cursor:pointer; }}

/* sub-done */
.sub-done-accordion {{ margin-top:8px; border-radius:8px; border:1px solid var(--border); overflow:hidden; }}
.sub-done-accordion[open] > .sub-done-summary .sub-done-chevron {{ transform:rotate(90deg); }}
.sub-done-summary {{ display:flex; align-items:center; gap:8px; padding:8px 12px; cursor:pointer; list-style:none; background:var(--surface-2); font-size:0.82rem; font-weight:600; color:var(--text-muted); user-select:none; }}
.sub-done-summary::-webkit-details-marker {{ display:none; }}
.sub-done-chevron {{ font-size:0.65rem; color:var(--text-muted); transition:transform 0.2s; display:inline-block; }}
.sub-done-body {{ padding:8px 8px 4px; }}
.group-empty {{ color:var(--text-muted); font-size:0.85rem; padding:12px 8px; text-align:center; }}

/* header & stats */
.task-list-header {{ display:flex; align-items:center; justify-content:space-between; margin-bottom:16px; }}
.stats {{ display:flex; gap:8px; margin-bottom:16px; flex-wrap:wrap; }}
.stats span {{ background:var(--surface-2); padding:5px 14px; border-radius:var(--radius-full); border:1px solid var(--border); font-size:0.82rem; color:var(--text-muted); font-weight:600; }}
.stats .done-c {{ color:var(--success); background:rgba(52,211,153,0.1); border-color:rgba(52,211,153,0.3); }}
.add-form {{ display:flex; gap:8px; flex-wrap:wrap; align-items:flex-start; }}
.add-form input, .add-form select {{ padding:9px 12px; border:1px solid var(--border); border-radius:var(--radius-sm); font-size:var(--text-base); background:var(--surface-2); color:var(--text); }}
.add-form input[type=text], .add-form input[type=date] {{ flex:1; min-width:140px; }}
.add-form input:focus, .add-form select:focus {{ outline:none; border-color:var(--accent); box-shadow:0 0 0 3px var(--accent-glow); }}

/* Habits section */
.habits-accordion {{ background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg); margin-top:24px; overflow:hidden; box-shadow:var(--shadow-sm); }}
.habits-accordion > .habits-header {{ display:flex; align-items:center; justify-content:space-between; padding:14px 20px; cursor:pointer; list-style:none; background:var(--surface-2); user-select:none; }}
.habits-accordion > .habits-header::-webkit-details-marker {{ display:none; }}
.habits-accordion[open] > .habits-header {{ border-bottom:1px solid var(--border); }}
.habits-accordion .habit-items {{ display:flex; flex-direction:column; gap:8px; padding:12px 20px; }}
.habits-section.habits-empty {{ display:flex; align-items:center; justify-content:space-between; padding:14px 20px; background:var(--surface); border:1px solid var(--border); border-radius:var(--radius-lg); margin-top:24px; }}
.habits-title {{ font-weight:800; font-size:1rem; color:var(--text); }}
.habits-meta {{ font-size:0.85rem; color:var(--text-muted); }}
.habit-item {{ display:flex; align-items:center; gap:12px; background:var(--surface-2); padding:12px 16px; border-radius:12px; border:1px solid var(--border); transition:0.2s; }}
.habit-item:hover {{ border-color:var(--accent); background:var(--surface-3); transform:translateY(-1px); }}
.habit-item.habit-checked {{ opacity:0.5; }}
.h-icon {{ font-size:1.1rem; flex-shrink:0; width:32px; height:32px; background:var(--surface-3); border-radius:8px; display:flex; align-items:center; justify-content:center; }}
.h-name {{ flex:1; font-size:0.9rem; font-weight:600; color:var(--text); }}
.h-streak {{ font-size:0.75rem; color:var(--warn); font-weight:700; white-space:nowrap; background:rgba(251,191,36,0.1); padding:2px 8px; border-radius:var(--radius-full); border:1px solid rgba(251,191,36,0.3); }}
.h-actions {{ display:flex; gap:6px; align-items:center; flex-shrink:0; }}
.hb-check {{ background:var(--accent); color:#080d14; font-size:0.78rem; padding:4px 12px; border-radius:6px; border:none; cursor:pointer; font-weight:700; transition:0.2s; }}
.hb-check:hover {{ opacity:0.88; transform:translateY(-1px); box-shadow:0 4px 10px rgba(56,189,248,0.3); }}
.hb-done {{ font-size:0.78rem; color:var(--success); font-weight:700; padding:4px 8px; background:rgba(52,211,153,0.1); border-radius:6px; border:1px solid rgba(52,211,153,0.3); }}
.hb-detail {{ background:var(--surface-2); color:var(--text-muted); font-size:0.78rem; text-decoration:none; padding:4px 10px; border-radius:6px; border:1px solid var(--border); transition:0.2s; }}
.hb-detail:hover {{ border-color:var(--accent); color:var(--accent); }}
.habits-link {{ display:inline-block; margin:8px 20px 16px; font-size:0.82rem; color:var(--accent); text-decoration:none; font-weight:600; }}
.habits-link:hover {{ text-decoration:underline; }}

@media (max-width:600px) {{
  .notepad-item {{ flex-wrap:wrap; }}
  .item-actions {{ width:100%; justify-content:flex-end; margin-top:6px; }}
  .group-sel-form {{ order:10; width:100%; }}
  .group-select-inline {{ width:100%; min-height:40px; font-size:0.88rem; padding:8px 10px; }}
  .habit-item {{ flex-wrap:wrap; gap:8px; padding:10px 12px; }}
  .h-actions {{ width:100%; justify-content:flex-end; margin-top:4px; flex-wrap:wrap; gap:6px; }}
  .add-form {{ flex-direction:column; gap:8px; }}
  .add-form input, .add-form select, .add-form textarea {{ width:100%; min-height:44px; font-size:1rem; }}
}}
</style>
</head><body>
<nav>
  <span class="nav-brand">✅ Tasks</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container">
  {add_form}
  {todo_add_group_card}
  <div class="task-list-header">
    <div class="stats">
      <span>Total {total}</span><span class="done-c">Done {done_count}</span><span>Remaining {total - done_count}</span>
    </div>
    {todo_header_btns}
  </div>
  {todo_sections}
  {habit_section}
</div>
{tabs_html}
<script>
function toggleAddGroupCard() {{
  var card = document.getElementById('addGroupCard');
  if (!card) return;
  var open = card.style.display !== 'none';
  card.style.display = open ? 'none' : 'block';
  if (!open) {{
    card.scrollIntoView({{behavior:'smooth', block:'nearest'}});
    setTimeout(function() {{
      var inp = document.getElementById('newGroupNameInput');
      if (inp) inp.focus();
    }}, 100);
  }}
}}
function closeAddForms() {{
  var taskCard = document.getElementById('addTaskCard');
  var memoCard = document.getElementById('addMemoCard');
  if (taskCard) taskCard.style.display = 'none';
  if (memoCard) memoCard.style.display = 'none';
}}

function openAddTask(btn) {{
  closeAllInlineForms();
  var card = btn.closest('.notepad-card');
  if (!card) return;
  var form = card.querySelector('.inline-task-form');
  if (!form) return;
  form.style.display = 'block';
  setTimeout(function() {{
    var inp = form.querySelector('input[name="title"]');
    if (inp) inp.focus();
  }}, 50);
}}

function openAddMemo(btn) {{
  closeAllInlineForms();
  var card = btn.closest('.notepad-card');
  if (!card) return;
  var form = card.querySelector('.inline-memo-form');
  if (!form) return;
  form.style.display = 'block';
  setTimeout(function() {{
    var ta = form.querySelector('textarea');
    if (ta) ta.focus();
  }}, 50);
}}

function closeInlineForm(btn) {{
  var form = btn.closest('.inline-add-form');
  if (form) form.style.display = 'none';
}}

function closeAllInlineForms() {{
  document.querySelectorAll('.inline-add-form').forEach(function(el) {{
    el.style.display = 'none';
  }});
}}

function toggleNotepad(el) {{
  var card = el.closest('.notepad-card');
  if (card) card.classList.toggle('collapsed');
}}

function openMemoEdit(id, btn) {{
  var text = document.getElementById('memo-text-' + id);
  var form = document.getElementById('memo-edit-' + id);
  if (!text || !form) return;
  text.style.display = 'none';
  form.style.display = 'block';
  var item = form.closest('.notepad-item');
  if (item) {{
    var actions = item.querySelector('.item-actions');
    if (actions) actions.style.display = 'none';
  }}
  var ta = form.querySelector('textarea');
  if (ta) ta.focus();
}}

function closeMemoEdit(id) {{
  var text = document.getElementById('memo-text-' + id);
  var form = document.getElementById('memo-edit-' + id);
  if (!text || !form) return;
  text.style.display = '';
  form.style.display = 'none';
  var item = form.closest('.notepad-item');
  if (item) {{
    var actions = item.querySelector('.item-actions');
    if (actions) actions.style.display = '';
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
    var ids = Array.from(list.querySelectorAll('.notepad-task[draggable]')).map(function(el) {{ return el.dataset.id; }});
    if (ids.length > 0) {{
      fetch('/todo/reorder', {{
        method: 'POST',
        headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
        body: 'ids=' + ids.join(',')
      }});
    }}
  }}

  function insertAt(list, clientY) {{
    var items = Array.from(list.querySelectorAll('.notepad-task[draggable]')).filter(function(el) {{ return el !== dragged; }});
    var after = null;
    for (var i = 0; i < items.length; i++) {{
      var rect = items[i].getBoundingClientRect();
      if (clientY < rect.top + rect.height / 2) {{ after = items[i]; break; }}
    }}
    list.insertBefore(dragged, after);
  }}

  document.addEventListener('dragstart', function(e) {{
    dragged = e.target.closest('.notepad-task[draggable]');
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
    dragged = handle.closest('.notepad-task[draggable]');
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
