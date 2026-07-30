import json, os
from datetime import datetime, date, timedelta

from services._paths import DATA_ROOT

META = {
    "name": "Tasks",
    "path": "/todo",
    "icon": "✅",
    "description": "Task management",
    # Reached through /work now. The route stays so that every form action and
    # phone shortcut pointing at /todo/* keeps resolving.
    "hidden": True,
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


PRIORITIES = {1: ("High", "--group-4"), 2: ("Normal", "--text-muted"), 3: ("Low", "--group-1")}
DEFAULT_PRIORITY = 2


def _priority_of(raw):
    """Form values arrive as strings and may be blank; anything unrecognised
    is Normal rather than an error — priority is never worth a 500."""
    try:
        p = int(raw)
    except (TypeError, ValueError):
        return DEFAULT_PRIORITY
    return p if p in PRIORITIES else DEFAULT_PRIORITY


def _place_options(places, selected):
    opts = f'<option value=""{"" if selected else " selected"}>No place</option>'
    return opts + "".join(
        f'<option value="{pl["id"]}"{" selected" if pl["id"] == selected else ""}>'
        f'📍 {pl["label"]}</option>' for pl in places)


def _prio_options(selected):
    return "".join(
        f'<option value="{p}"{" selected" if p == selected else ""}>{label}</option>'
        for p, (label, _) in PRIORITIES.items()
    )


def projects_of(todos):
    """Distinct project names in use, for the datalist. Free text, so the list
    is whatever has been typed so far."""
    seen = []
    for t in todos:
        pj = (t.get("project") or "").strip()
        if pj and pj not in seen:
            seen.append(pj)
    return sorted(seen)


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
    created_id = None   # set by /todo/add so the caller can open its sheet

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
                created_id = next_id(todos)
                todos.append({
                    "id": created_id,
                    "type": "task",
                    "title": title,
                    "done": False,
                    "created_at": datetime.now().isoformat(),
                    "due_date": due_date,
                    "group": actual_group,
                    "project": body.get("project", [""])[0].strip(),
                    "priority": _priority_of(body.get("priority", [""])[0]),
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
        elif path == "/todo/set_meta":
            # Project / priority / place, edited inline from the task row.
            # Absent fields are left alone so one control can post on its own.
            tid = int(body.get("id", [0])[0])
            for t in todos:
                if t["id"] != tid:
                    continue
                if "project" in body:
                    t["project"] = body["project"][0].strip()
                if "priority" in body:
                    t["priority"] = _priority_of(body["priority"][0])
                if "place_id" in body:
                    t["place_id"] = body["place_id"][0].strip()
                if "due_date" in body:
                    # An empty date field clears the deadline; parse_qs keeps the
                    # key because the form always submits it.
                    t["due_date"] = body["due_date"][0].strip() or None
                if "title" in body and body["title"][0].strip():
                    t["title"] = body["title"][0].strip()
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
        if created_id:
            # A task typed into the quick field has nothing but a title. Hand the
            # new id back so the page can open its sheet and let you finish it.
            next_url += ("&" if "?" in next_url else "?") + f"new={created_id}"
        return ("redirect", next_url)

    # The page itself now lives at /work; this route survives for bookmarks,
    # phone shortcuts and the POST actions above.
    return ("redirect", "/momentum?tab=tasks")

def _attr(v):
    """Quote-safe value for a data-* attribute."""
    return str(v or "").replace("&", "&amp;").replace('"', "&quot;").replace("<", "&lt;")

def _bucket_of(t, today_str, week_str):
    """Which section a task belongs to. Dateless work is 'later' — it is not
    urgent by omission, and putting it up top drowns the things that are."""
    d = t.get("due_date")
    if not d:
        return "later"
    if d <= today_str:
        return "now"
    if d <= week_str:
        return "week"
    return "later"


def _absorb_group(t):
    """Groups and projects said the same thing twice, so groups are gone. A task
    that only ever had a group reads as if that group were its project."""
    if not (t.get("project") or "").strip() and (t.get("group") or "").strip():
        return dict(t, project=t["group"])
    return t


def render(todos, habits, user, readonly=False):
    today = date.today()
    today_str = today.isoformat()
    week_str = (today + timedelta(days=7)).isoformat()
    import services.momentum as momentum_svc
    places = momentum_svc.load_places(user)

    todos = [_absorb_group(t) for t in todos]
    active = [t for t in todos if not t.get("done")]
    done_list = [t for t in todos if t.get("done")]

    # Highest priority first, then soonest deadline. This is the whole answer to
    # "what do I do now", and the old due-date-only sort could not give it.
    def _order(t):
        return (_priority_of(t.get("priority")), t.get("due_date") or "9999-99-99",
                -(t.get("id") or 0))

    buckets = {"now": [], "week": [], "later": []}
    for t in active:
        buckets[_bucket_of(t, today_str, week_str)].append(t)
    for k in buckets:
        buckets[k].sort(key=_order)

    # Today's habits ride in the list as things to do today — that is what the
    # Today tab was for, and a habit is a task you do again tomorrow.
    def _habit_row(h):
        checkins = h.get("checkins", {})
        if isinstance(checkins, list):
            checkins = {d: 1 for d in checkins}
        target = h.get("target", 1) or 1
        got = checkins.get(today_str, 0)
        if isinstance(got, list):
            got = sum(e.get("count", 1) if isinstance(e, dict) else 1 for e in got)
        done = got >= target
        streak = 0
        d = today
        while checkins.get(d.isoformat()):
            streak += 1
            d -= timedelta(days=1)
        chips = '<span class="tk-chip tk-chip--habit">🔁 Habit</span>'
        if target > 1:
            chips += f'<span class="tk-chip">{got}/{target} {h.get("unit","")}</span>'
        if streak:
            chips += f'<span class="tk-chip">🔥 {streak}d</span>'
        check = "" if readonly else (
            f'<form method="POST" action="/habit/{h["id"]}/checkin" class="tk-check-form" '
            f'onclick="event.stopPropagation()">'
            f'<input type="hidden" name="next" value="/momentum?tab=tasks">'
            f'<input type="hidden" name="toggle" value="1">'
            f'<button class="tk-check{" tk-check--on" if done else ""}" type="submit" '
            f'aria-label="{"Undo check-in" if done else "Check in"}">{"✓" if done else ""}</button>'
            f'</form>')
        return (f'<a class="tk-row tk-row--habit{" tk-row--done" if done else ""}" '
                f'href="/habit/{h["id"]}">'
                f'{check}<div class="tk-main"><div class="tk-title">{h.get("name","")}</div>'
                f'<div class="tk-meta">{chips}</div></div>'
                f'<span class="tk-open">›</span></a>')

    def _habit_done_today(h):
        checkins = h.get("checkins", {})
        if isinstance(checkins, list):
            checkins = {d: 1 for d in checkins}
        got = checkins.get(today_str, 0)
        if isinstance(got, list):
            got = sum(e.get("count", 1) if isinstance(e, dict) else 1 for e in got)
        return got >= (h.get("target", 1) or 1)

    habits_today = [h for h in (habits or []) if h.get("freq", "daily") == "daily"]
    habit_open = [h for h in habits_today if not _habit_done_today(h)]
    habit_done = [h for h in habits_today if _habit_done_today(h)]

    n_active = len(active)
    all_projects = projects_of(todos)
    # Controls appear when there is something to control. An empty list showing
    # filters was the single worst thing about the old screen.
    show_filter = n_active >= 8 and len(all_projects) > 1

    def _row(t):
        tid = t["id"]
        is_memo = t.get("type") == "memo"
        prio = _priority_of(t.get("priority"))
        project = (t.get("project") or "").strip()
        due = t.get("due_date") or ""
        place_id = (t.get("place_id") or "").strip()
        place = next((p for p in places if p["id"] == place_id), None)

        chips = ""
        if due:
            n = days_left(due)
            if n is None:
                lbl, cls = due, "tk-due"
            elif n < 0:
                lbl, cls = f"{abs(n)}d overdue", "tk-due tk-due--over"
            elif n == 0:
                lbl, cls = "Today", "tk-due tk-due--today"
            elif n == 1:
                lbl, cls = "Tomorrow", "tk-due tk-due--soon"
            else:
                lbl, cls = f"in {n}d", "tk-due"
            chips += f'<span class="{cls}">{lbl}</span>'
        if project:
            chips += f'<span class="tk-chip">{project}</span>'
        if place:
            chips += f'<span class="tk-chip">📍 {place["label"]}</span>'
        if prio == 1:
            chips += '<span class="tk-chip tk-chip--high">High</span>'

        done = bool(t.get("done"))
        check_action = "/todo/undone" if done else "/todo/done"
        check_cls = "tk-check tk-check--on" if done else "tk-check"
        check = "" if readonly else (
            f'<form method="POST" action="{check_action}" class="tk-check-form" '
            f'onclick="event.stopPropagation()">'
            f'<input type="hidden" name="id" value="{tid}">'
            f'<input type="hidden" name="next" value="/momentum?tab=tasks">'
            f'<button class="{check_cls}" type="submit" '
            f'aria-label="{"Mark not done" if done else "Mark done"}">'
            f'{"✓" if done else ""}</button></form>')
        opener = "" if readonly else f'onclick="tkOpen(this)"'
        return (
            f'<div class="tk-row{" tk-row--done" if done else ""}" {opener} '
            f'data-id="{tid}" data-title="{_attr(t.get("title",""))}" '
            f'data-project="{_attr(project)}" data-prio="{prio}" '
            f'data-due="{due}" data-place="{_attr(place_id)}" '
            f'data-memo="{"1" if is_memo else ""}">'
            f'{check}'
            f'<div class="tk-main">'
            f'<div class="tk-title">{t.get("title","")}</div>'
            f'{f"<div class=\'tk-meta\'>{chips}</div>" if chips else ""}'
            f'</div>'
            f'{"" if readonly else "<span class=\'tk-open\'>›</span>"}'
            f'</div>')

    def _section(key, label, items):
        if not items:
            return ""
        return (f'<div class="tk-section" data-bucket="{key}">'
                f'<div class="tk-section-head"><span>{label}</span>'
                f'<span class="tk-section-n">{len(items)}</span></div>'
                f'{"".join(_row(t) for t in items)}</div>')

    now_html = ("".join(_habit_row(h) for h in habit_open)
                + "".join(_row(t) for t in buckets["now"]))
    now_n = len(habit_open) + len(buckets["now"])
    list_html = ((f'<div class="tk-section" data-bucket="now">'
                  f'<div class="tk-section-head"><span>Today</span>'
                  f'<span class="tk-section-n">{now_n}</span></div>{now_html}</div>'
                  if now_n else "")
                 + _section("week", "This week", buckets["week"])
                 + _section("later", "Later", buckets["later"]))

    if done_list or habit_done:
        done_rows = ("".join(_habit_row(h) for h in habit_done)
                     + "".join(_row(t) for t in sorted(
                         done_list, key=lambda x: x.get("done_at") or "", reverse=True)[:50]))
        list_html += (f'<details class="tk-done"><summary>Completed '
                      f'<span class="tk-section-n">{len(done_list) + len(habit_done)}</span>'
                      f'</summary>{done_rows}</details>')

    if not active and not habit_open:
        list_html = ('<div class="tk-empty">Nothing on the list.<br>'
                     '<span>Type above to add your first task.</span></div>') + list_html

    quick_add = "" if readonly else (
        '<form class="tk-quick" method="POST" action="/todo/add" autocomplete="off">'
        '<input type="hidden" name="next" value="/momentum?tab=tasks">'
        '<input class="tk-quick-input" type="text" name="title" required '
        'placeholder="Add a task…" aria-label="Add a task">'
        '<button class="btn btn-primary" type="submit">Add</button>'
        '</form>')

    project_opts = "".join(f'<option value="{_attr(pj)}">{pj}</option>'
                           for pj in all_projects)
    filter_html = "" if not show_filter else (
        f'<div class="tk-filter">'
        f'<select id="tkFProject" class="wf-input" onchange="tkFilter()" aria-label="Project">'
        f'<option value="">All projects</option>{project_opts}</select>'
        f'<select id="tkFPrio" class="wf-input" onchange="tkFilter()" aria-label="Priority">'
        f'<option value="">Any priority</option>{_prio_options(None)}</select>'
        f'<span id="tkFCount" class="tk-filter-n"></span></div>')

    place_rows = "".join(
        f'<div class="tk-place-row"><span class="tk-place-name">📍 {pl["label"]}</span>'
        f'<span class="tk-place-meta">{sum(1 for t in active if t.get("place_id") == pl["id"])} open</span>'
        f'<form method="POST" action="/momentum/place/delete" style="display:inline">'
        f'<input type="hidden" name="id" value="{pl["id"]}">'
        f'<button class="btn btn-danger btn-sm">Remove</button></form></div>'
        for pl in places)
    places_html = "" if readonly else (
        f'<details class="tk-places"{" open" if not places else ""}>'
        f'<summary>📍 Places <span class="tk-section-n">{len(places)}</span></summary>'
        f'<div class="tk-places-body">'
        f'{place_rows or "<div class=\'tk-place-meta\'>No places yet — stand where you work and save it.</div>"}'
        f'<form method="POST" action="/momentum/place/add" id="tkPlaceForm" class="tk-place-add">'
        f'<input type="hidden" name="lat" id="tkLat"><input type="hidden" name="lon" id="tkLon">'
        f'<input type="text" name="label" id="tkLabel" class="wf-input" placeholder="Place name (e.g. Office)" required>'
        f'<button type="button" class="btn btn-secondary btn-sm" onclick="tkSavePlace()">Use my current location</button>'
        f'<span id="tkGeoMsg" class="tk-place-meta"></span></form>'
        f'<p class="tk-place-note">A browser cannot watch your location in the background. '
        f'Set an arrival automation on your phone to call <code>POST /momentum/arrive</code> '
        f'and the list arrives in Telegram when you get there.</p>'
        f'</div></details>')

    place_opts = _place_options(places, "")
    sheet_html = "" if readonly else f'''
<div class="tk-backdrop" id="tkBackdrop" onclick="tkClose()"></div>
<div class="tk-sheet" id="tkSheet" role="dialog" aria-label="Task details">
  <div class="tk-sheet-grip"></div>
  <form method="POST" action="/todo/set_meta" class="tk-sheet-form">
    <input type="hidden" name="id" id="tkSid">
    <input type="hidden" name="next" value="/momentum?tab=tasks">
    <div class="wf-field"><label class="wf-label">Task</label>
      <input class="wf-input" type="text" name="title" id="tkStitle" required></div>
    <div class="tk-sheet-grid">
      <div class="wf-field"><label class="wf-label">Due</label>
        <input class="wf-input" type="date" name="due_date" id="tkSdue"></div>
      <div class="wf-field"><label class="wf-label">Priority</label>
        <select class="wf-input" name="priority" id="tkSprio">{_prio_options(DEFAULT_PRIORITY)}</select></div>
    </div>
    <div class="tk-sheet-grid">
      <div class="wf-field"><label class="wf-label">Project</label>
        <input class="wf-input" type="text" name="project" id="tkSproject"
               list="tk-projects" placeholder="e.g. Samsung AEO"></div>
      <div class="wf-field"><label class="wf-label">Place</label>
        <select class="wf-input" name="place_id" id="tkSplace" onchange="tkPlacePick()">
          {place_opts}<option value="__new__">＋ Save current location…</option>
        </select></div>
    </div>
    <div class="tk-sheet-actions">
      <button class="btn btn-primary btn-lg" type="submit">Save</button>
      <button class="btn btn-ghost btn-lg" type="button" id="tkCancel" onclick="tkClose()">Cancel</button>
    </div>
  </form>
  <form method="POST" action="/momentum/place/add" id="tkNewPlaceForm" class="tk-newplace" hidden>
    <input type="hidden" name="lat" id="tkNpLat"><input type="hidden" name="lon" id="tkNpLon">
    <input type="hidden" name="task_id" id="tkNpTask">
    <label class="wf-label">New place</label>
    <div class="tk-newplace-row">
      <input class="wf-input" type="text" name="label" id="tkNpLabel"
             placeholder="e.g. Office" required>
      <button class="btn btn-secondary" type="button" onclick="tkAddPlace()">Use my location</button>
    </div>
    <span id="tkNpMsg" class="tk-place-meta"></span>
  </form>
  <form method="POST" action="/todo/delete" class="tk-sheet-delete"
        onsubmit="return confirm('Delete this task?')">
    <input type="hidden" name="id" id="tkDid">
    <input type="hidden" name="next" value="/momentum?tab=tasks">
    <button class="btn btn-danger" type="submit">Delete task</button>
  </form>
</div>
<datalist id="tk-projects">{project_opts}</datalist>'''

    from server import app_tabs
    tabs_html = app_tabs("tasks", user)
    remaining = len(active)
    done_today = sum(1 for t in done_list if (t.get("done_at") or "")[:10] == today_str)
    summary = (f'<div class="tk-summary"><b>{remaining}</b> open'
               f'{f" · <b>{done_today}</b> done today" if done_today else ""}</div>'
               ) if todos else ""

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tasks · Momentum</title>
<link rel="stylesheet" href="/static/style.css">
<style>
.tk-wrap{{max-width:720px;margin:0 auto;padding:18px 16px 90px}}
.tk-quick{{display:flex;gap:8px;margin-bottom:14px}}
.tk-quick-input{{flex:1;min-width:0;padding:12px 14px;font-size:1rem;
  background:var(--surface);border:1px solid var(--border-bright);border-radius:var(--radius-md);
  color:var(--text)}}
.tk-quick-input:focus{{outline:none;border-color:var(--accent);box-shadow:0 0 0 3px var(--accent-glow)}}
.tk-quick .btn{{height:auto;padding:0 18px}}
.tk-summary{{font-size:var(--text-sm);color:var(--text-muted);margin:0 2px 14px}}
.tk-filter{{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-bottom:14px}}
.tk-filter .wf-input{{width:auto;flex:1;min-width:140px;min-height:44px}}
.tk-filter-n{{font-size:var(--text-xs);color:var(--text-muted)}}

.tk-section{{margin-bottom:22px}}
.tk-section-head{{display:flex;align-items:center;gap:8px;margin:0 2px 8px;
  font-size:var(--text-xs);font-weight:var(--fw-bold);letter-spacing:.06em;
  text-transform:uppercase;color:var(--text-muted)}}
.tk-section-n{{background:var(--surface-2);color:var(--text-muted);border-radius:var(--radius-full);
  padding:1px 8px;font-size:var(--text-xs);font-weight:var(--fw-bold)}}

.tk-row{{display:flex;align-items:flex-start;gap:12px;padding:12px 14px;cursor:pointer;
  background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);
  margin-bottom:8px;transition:border-color .15s,background .15s}}
.tk-row:hover{{border-color:var(--border-bright)}}
.tk-row--done{{opacity:.55}}
.tk-row--done .tk-title{{text-decoration:line-through}}
.tk-check-form{{flex-shrink:0;display:flex;position:relative}}
.tk-check{{width:24px;height:24px;border-radius:50%;border:2px solid var(--border-bright);
  background:transparent;color:var(--on-accent);cursor:pointer;font-size:.8rem;font-weight:800;
  display:flex;align-items:center;justify-content:center;padding:0;position:relative;flex-shrink:0}}
/* Circle stays small, tap area does not — the guideline's 44px floor. */
.tk-check::after{{content:"";position:absolute;top:50%;left:50%;translate:-50% -50%;
  width:max(100%,44px);height:max(100%,44px);border-radius:50%}}
.tk-check:hover{{border-color:var(--accent)}}
.tk-check--on{{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}}
.tk-main{{flex:1;min-width:0}}
.tk-title{{font-size:var(--text-base);color:var(--text);line-height:1.4;word-break:break-word}}
.tk-meta{{display:flex;flex-wrap:wrap;gap:6px;margin-top:6px}}
/* Chips carry no fill: a tinted background pushed every one of these under AA
   in the light theme (4.13-4.49). On the card surface the same colors clear it
   in both themes, and the outline still reads as a chip. */
.tk-chip,.tk-due{{display:inline-flex;align-items:center;height:20px;padding:0 8px;
  border-radius:var(--radius-full);background:transparent;
  border:1px solid var(--border-bright);color:var(--text-muted);
  font-size:var(--text-xs);font-weight:var(--fw-semibold)}}
.tk-due{{font-weight:var(--fw-bold)}}
.tk-chip--high{{border-color:var(--group-4);color:var(--group-4)}}
.tk-chip--habit{{border-color:var(--group-3);color:var(--group-3)}}
a.tk-row{{text-decoration:none;color:inherit}}
.tk-due--over{{border-color:var(--danger);color:var(--danger)}}
.tk-due--today{{border-color:var(--warn);color:var(--warn)}}
.tk-due--soon{{border-color:var(--accent);color:var(--accent)}}
.tk-open{{color:var(--text-dim);font-size:1.2rem;line-height:1;flex-shrink:0;align-self:center}}

.tk-empty{{text-align:center;color:var(--text-muted);padding:38px 16px;font-size:var(--text-md)}}
.tk-empty span{{font-size:var(--text-sm);color:var(--text-dim)}}
.tk-done{{margin-top:6px}}
.tk-done>summary{{cursor:pointer;list-style:none;font-size:var(--text-xs);
  font-weight:var(--fw-bold);letter-spacing:.06em;text-transform:uppercase;
  color:var(--text-muted);padding:8px 2px}}
.tk-done>summary::-webkit-details-marker{{display:none}}

.tk-places{{margin-top:20px;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-md);overflow:hidden}}
.tk-places>summary{{cursor:pointer;list-style:none;padding:12px 14px;
  font-size:var(--text-sm);font-weight:var(--fw-semibold);color:var(--text)}}
.tk-places>summary::-webkit-details-marker{{display:none}}
.tk-places-body{{padding:0 14px 14px;display:flex;flex-direction:column;gap:10px}}
.tk-place-row{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  padding-top:10px;border-top:1px solid var(--border)}}
.tk-place-name{{font-size:var(--text-sm);font-weight:var(--fw-semibold);color:var(--text)}}
.tk-place-meta{{font-size:var(--text-xs);color:var(--text-muted)}}
.tk-place-add{{display:flex;gap:8px;flex-wrap:wrap;align-items:center;
  padding-top:10px;border-top:1px solid var(--border)}}
.tk-place-add .wf-input{{flex:1;min-width:160px;min-height:44px}}
.tk-place-note{{font-size:var(--text-xs);color:var(--text-muted);line-height:1.6}}
.tk-place-note code{{background:var(--surface-2);padding:1px 5px;border-radius:var(--radius-sm)}}

.tk-backdrop{{position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:9998;display:none}}
.tk-backdrop.is-on{{display:block}}
.tk-sheet{{position:fixed;left:50%;translate:-50% 0;bottom:0;width:min(560px,100%);
  z-index:9999;background:var(--surface);border:1px solid var(--border-bright);
  border-radius:var(--radius-xl) var(--radius-xl) 0 0;box-shadow:var(--shadow-lg);
  padding:8px 18px calc(20px + env(safe-area-inset-bottom,0px));display:none;
  max-height:88vh;overflow-y:auto}}
.tk-sheet.is-on{{display:block}}
.tk-sheet-grip{{width:40px;height:4px;border-radius:2px;background:var(--border-bright);
  margin:6px auto 14px}}
.tk-sheet-form{{display:flex;flex-direction:column;gap:12px}}
.tk-sheet-grid{{display:grid;grid-template-columns:1fr 1fr;gap:12px}}
.tk-sheet .wf-input{{min-height:44px}}
.tk-sheet-actions{{display:flex;gap:8px;margin-top:4px}}
.tk-sheet-actions .btn{{flex:1}}
.tk-sheet-delete{{margin-top:14px;padding-top:14px;border-top:1px solid var(--border);
  display:flex;justify-content:center}}
.tk-newplace{{margin-top:12px;padding-top:12px;border-top:1px solid var(--border);
  display:flex;flex-direction:column;gap:8px}}
.tk-newplace[hidden]{{display:none}}
.tk-newplace-row{{display:flex;gap:8px;flex-wrap:wrap}}
.tk-newplace-row .wf-input{{flex:1;min-width:150px;min-height:44px}}
@media (min-width:768px){{
  .tk-sheet{{bottom:auto;top:50%;translate:-50% -50%;border-radius:var(--radius-xl)}}
}}
@media (max-width:768px){{
  .tk-sheet-grid{{grid-template-columns:1fr}}
  .tk-quick-input{{font-size:16px}}
  .tk-row{{padding:14px}}
}}
</style>
</head><body>
<nav>
  <a href="/momentum" class="nav-brand">⚡ Momentum</a>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="tk-wrap">
  {quick_add}
  {summary}
  {filter_html}
  <div id="tkList">{list_html}</div>
  {places_html}
</div>
{sheet_html}
{tabs_html}
<script>
function tkOpen(row, isNew) {{
  var $ = function(i) {{ return document.getElementById(i); }};
  // On a task that was just created, "Cancel" would read as "undo the add" —
  // but it is already saved. Nothing is lost by closing, so say that.
  var c = $('tkCancel');
  if (c) c.textContent = isNew ? 'Later' : 'Cancel';
  $('tkSid').value = row.dataset.id;
  $('tkDid').value = row.dataset.id;
  $('tkStitle').value = row.dataset.title || '';
  $('tkSdue').value = row.dataset.due || '';
  $('tkSprio').value = row.dataset.prio || '2';
  $('tkSproject').value = row.dataset.project || '';
  var place = $('tkSplace');
  if (place) place.value = row.dataset.place || '';
  var np = $('tkNewPlaceForm');
  if (np) {{ np.hidden = true; $('tkNpLabel').value = ''; $('tkNpMsg').textContent = ''; }}
  $('tkBackdrop').classList.add('is-on');
  $('tkSheet').classList.add('is-on');
}}
function tkPlacePick() {{
  // "Save current location" is not a place you can pick — it is a place you make.
  var sel = document.getElementById('tkSplace');
  var box = document.getElementById('tkNewPlaceForm');
  var isNew = sel.value === '__new__';
  box.hidden = !isNew;
  if (isNew) {{
    document.getElementById('tkNpTask').value = document.getElementById('tkSid').value;
    document.getElementById('tkNpLabel').focus();
  }}
}}
function tkAddPlace() {{
  var msg = document.getElementById('tkNpMsg');
  var label = document.getElementById('tkNpLabel');
  if (!label.value.trim()) {{ msg.textContent = 'Name it first.'; label.focus(); return; }}
  if (!navigator.geolocation) {{ msg.textContent = 'This browser has no geolocation.'; return; }}
  msg.textContent = 'Locating…';
  navigator.geolocation.getCurrentPosition(function(pos) {{
    document.getElementById('tkNpLat').value = pos.coords.latitude;
    document.getElementById('tkNpLon').value = pos.coords.longitude;
    document.getElementById('tkNewPlaceForm').submit();
  }}, function(err) {{
    msg.textContent = 'Could not get location: ' + err.message;
  }}, {{ enableHighAccuracy: true, timeout: 10000 }});
}}
function tkClose() {{
  document.getElementById('tkBackdrop').classList.remove('is-on');
  document.getElementById('tkSheet').classList.remove('is-on');
}}
document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') tkClose();
}});
// Just added something? Finish setting it up right here, then drop the ?new=
// so a refresh does not reopen the sheet.
(function() {{
  var nid = new URLSearchParams(location.search).get('new');
  if (!nid) return;
  var row = document.querySelector('.tk-row[data-id="' + nid + '"]');
  history.replaceState({{}}, '', location.pathname + '?tab=tasks');
  if (!row) return;
  tkOpen(row, true);
  row.scrollIntoView({{block: 'center'}});
  var t = document.getElementById('tkSdue');
  if (t) t.focus();
}})();
function tkFilter() {{
  var pj = document.getElementById('tkFProject').value;
  var pr = document.getElementById('tkFPrio').value;
  var shown = 0;
  document.querySelectorAll('.tk-row').forEach(function(r) {{
    var ok = (!pj || r.dataset.project === pj) && (!pr || r.dataset.prio === pr);
    r.style.display = ok ? '' : 'none';
    if (ok) shown++;
  }});
  // A section whose rows all filtered out should not leave its heading behind.
  document.querySelectorAll('.tk-section').forEach(function(s) {{
    var vis = [].slice.call(s.querySelectorAll('.tk-row')).some(function(r) {{
      return r.style.display !== 'none';
    }});
    s.style.display = vis ? '' : 'none';
  }});
  var c = document.getElementById('tkFCount');
  if (c) c.textContent = (pj || pr) ? shown + ' shown' : '';
}}
function tkSavePlace() {{
  var msg = document.getElementById('tkGeoMsg');
  var label = document.getElementById('tkLabel');
  if (!label.value.trim()) {{ msg.textContent = 'Name it first.'; label.focus(); return; }}
  if (!navigator.geolocation) {{ msg.textContent = 'This browser has no geolocation.'; return; }}
  msg.textContent = 'Locating…';
  navigator.geolocation.getCurrentPosition(function(pos) {{
    document.getElementById('tkLat').value = pos.coords.latitude;
    document.getElementById('tkLon').value = pos.coords.longitude;
    document.getElementById('tkPlaceForm').submit();
  }}, function(err) {{
    msg.textContent = 'Could not get location: ' + err.message;
  }}, {{ enableHighAccuracy: true, timeout: 10000 }});
}}
</script>
</body></html>'''
