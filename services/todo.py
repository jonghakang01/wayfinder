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
    followup_id = None  # set by /todo/done so the caller can offer a next step

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
                    # A follow-up inherits where its parent was done; the quick
                    # add field simply leaves this empty.
                    "place_id": body.get("place_id", [""])[0].strip(),
                })
                save(todos, user)
        elif path == "/todo/done":
            tid = int(body.get("id", [0])[0])
            for t in todos:
                if t["id"] == tid and not t["done"]:
                    t["done"] = True
                    t["done_at"] = datetime.now().isoformat()
                    # Finishing something is when the next step is clearest —
                    # ask now, while the context is still in your head. Memos
                    # are notes, not work, so they get no follow-up.
                    if t.get("type", "task") != "memo":
                        followup_id = tid
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
                        import services.habits as habits_svc
                        freq, freq_days = habits_svc.parse_freq(body)
                        try:
                            target = max(1, int(body.get("target", ["1"])[0]))
                        except (TypeError, ValueError):
                            target = 1
                        hid = next_id(habits)
                        habits.append({
                            "id": hid,
                            "name": body.get("name", [""])[0].strip() or t["title"],
                            "icon": body.get("icon", [""])[0].strip()[:4] or "✅",
                            "freq": freq,
                            "days": freq_days,
                            "target": target,
                            "unit": "times",
                            "track": "count",
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
        elif followup_id:
            next_url += ("&" if "?" in next_url else "?") + f"followup={followup_id}"
        return ("redirect", next_url)

    # The page itself now lives at /work; this route survives for bookmarks,
    # phone shortcuts and the POST actions above.
    return ("redirect", "/momentum?tab=tasks")

def _copy_row(label, value, eid):
    """A value you are meant to paste into a phone, with a button that copies it.

    Typing a shared secret by hand off a screen is where this setup dies."""
    return (f'<div class="tk-copy"><span class="tk-copy-label">{label}</span>'
            f'<code class="tk-copy-val" id="tk{eid}">{_attr(value)}</code>'
            f'<button type="button" class="btn btn-secondary btn-sm" '
            f'onclick="tkCopy(\'tk{eid}\',this)">Copy</button></div>')


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


def render(todos, habits, user, readonly=False, group_by="date"):
    today = date.today()
    today_str = today.isoformat()
    week_str = (today + timedelta(days=7)).isoformat()
    import services.habits as habits_svc
    habit_freq_picker = habits_svc.freq_picker('daily', (), 'hfTask')
    FREQ_PICKER_CSS = habits_svc.FREQ_PICKER_CSS
    FREQ_PICKER_JS = habits_svc.FREQ_PICKER_JS
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
            f'<input type="hidden" name="next" value="{back}">'
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

    # "Today" is the habit's own answer now — weekdays, weekends and chosen
    # days all decide for themselves instead of only daily counting.
    habits_today = [h for h in (habits or []) if habits_svc.due_today(h)]
    habit_open = [h for h in habits_today if not _habit_done_today(h)]
    habit_done = [h for h in habits_today if _habit_done_today(h)]

    n_active = len(active)
    all_projects = projects_of(todos)
    # Controls appear when there is something to control. An empty list showing
    # filters was the single worst thing about the old screen.
    show_filter = n_active >= 8 and len(all_projects) > 1
    # Grouping by project needs a project to group by, and two rows to reorder.
    # Two pills cost almost no room, and a control that quietly disappears reads
    # as a broken feature, not a tidy one — the toggle vanishing below two open
    # tasks is what made it look deleted. Projects existing is reason enough.
    show_group = bool(all_projects)
    by_project = group_by == "project" and show_group
    back = "/momentum?tab=tasks" + ("&by=project" if by_project else "")

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
            f'<input type="hidden" name="next" value="{back}">'
            f'<button class="{check_cls}" type="submit" '
            f'aria-label="{"Mark not done" if done else "Mark done"}">'
            f'{"✓" if done else ""}</button></form>')
        opener = "" if readonly else f'onclick="tkOpen(this)"'
        return (
            f'<div class="tk-row{" tk-row--done" if done else ""}" {opener} '
            f'data-id="{tid}" data-title="{_attr(t.get("title",""))}" '
            f'data-project="{_attr(project)}" data-prio="{prio}" '
            f'data-due="{due}" data-place="{_attr(place_id)}" '
            f'data-group="{_attr(t.get("group") or "")}" '
            f'data-habit="{"1" if t.get("habit_id") else ""}" '
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

    if by_project:
        # The list's spine becomes the project. Dates do not disappear — they
        # stay on each row as the due chip, which is where a date belongs once
        # it is no longer the thing you are sorting by.
        by_pj = {}
        for t in active:
            by_pj.setdefault((t.get("project") or "").strip(), []).append(t)
        # Busiest project first; ties alphabetical. "No project" always last —
        # it is a leftover bin, not a project, and habits live there because a
        # habit belongs to no project.
        named = sorted((pj for pj in by_pj if pj),
                       key=lambda pj: (-len(by_pj[pj]), pj.lower()))
        list_html = "".join(
            f'<div class="tk-section" data-project="{_attr(pj)}">'
            f'<div class="tk-section-head tk-section-head--project"><span>{pj}</span>'
            f'<span class="tk-section-n">{len(by_pj[pj])}</span></div>'
            f'{"".join(_row(t) for t in sorted(by_pj[pj], key=_order))}</div>'
            for pj in named)
        loose = sorted(by_pj.get("", []), key=_order)
        if loose or habit_open:
            list_html += (
                f'<div class="tk-section" data-project="">'
                f'<div class="tk-section-head tk-section-head--project">'
                f'<span>No project</span>'
                f'<span class="tk-section-n">{len(loose) + len(habit_open)}</span></div>'
                f'{"".join(_habit_row(h) for h in habit_open)}'
                f'{"".join(_row(t) for t in loose)}</div>')
    else:
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
        f'<input type="hidden" name="next" value="{back}">'
        '<input class="tk-quick-input" type="text" name="title" required '
        'placeholder="Add a task…" aria-label="Add a task">'
        '<button class="btn btn-primary" type="submit">Add</button>'
        '</form>')

    # Pill toggle, the same shape cardconv uses for its view tabs. Links, not
    # script, so the choice survives a reload and can be bookmarked.
    group_html = "" if not show_group else (
        f'<div class="tk-group" role="group" aria-label="Group tasks by">'
        f'<a class="tk-gtab{"" if by_project else " active"}" href="/momentum?tab=tasks"'
        f'{"" if by_project else " aria-current=\'true\'"}>By date</a>'
        f'<a class="tk-gtab{" active" if by_project else ""}" '
        f'href="/momentum?tab=tasks&amp;by=project"'
        f'{" aria-current=\'true\'" if by_project else ""}>By project</a>'
        f'</div>')

    project_opts = "".join(f'<option value="{_attr(pj)}">{pj}</option>'
                           for pj in all_projects)
    # Grouped by project, a project dropdown says the same thing the headings
    # already say — so it steps aside and only the priority filter remains.
    project_sel = "" if by_project else (
        f'<select id="tkFProject" class="wf-input" onchange="tkFilter()" aria-label="Project">'
        f'<option value="">All projects</option>{project_opts}</select>')
    filter_html = "" if not show_filter else (
        f'<div class="tk-filter">{project_sel}'
        f'<select id="tkFPrio" class="wf-input" onchange="tkFilter()" aria-label="Priority">'
        f'<option value="">Any priority</option>{_prio_options(None)}</select>'
        f'<span id="tkFCount" class="tk-filter-n"></span></div>')

    place_rows = "".join(
        f'<div class="tk-place-row"><span class="tk-place-name">📍 {pl["label"]}</span>'
        f'<span class="tk-place-meta">{sum(1 for t in active if t.get("place_id") == pl["id"])} open</span>'
        f'<form method="POST" action="/momentum/place/delete" style="display:inline">'
        f'<input type="hidden" name="next" value="{back}">'
        f'<input type="hidden" name="id" value="{pl["id"]}">'
        f'<button class="btn btn-danger btn-sm">Remove</button></form></div>'
        for pl in places)
    # Everything the nearby banner needs, so it can answer "am I there?" without
    # a round trip. Only places with open work — the rest cannot say anything.
    nearby_data = json.dumps([
        {"id": pl["id"], "label": pl["label"], "lat": pl["lat"], "lon": pl["lon"],
         "r": pl.get("radius_m") or 200,
         "n": sum(1 for t in active if t.get("place_id") == pl["id"])}
        for pl in places
        if any(t.get("place_id") == pl["id"] for t in active)
    ])
    # The setup guide differs per phone OS and is useless on the wrong one, so
    # the page shows one and hides the other. The shared secret is the whole
    # authentication for /momentum/arrive, so only the account that owns the
    # Telegram chat the alert lands in ever sees it.
    from services import auth as _auth
    _is_owner = user == getattr(_auth, "ADMIN_USERNAME", user)
    _secret = os.environ.get("MOMENTUM_ARRIVE_SECRET", "") if _is_owner else ""
    _origin_note = ("" if _secret else
                    '<p class="tk-place-note">Ask the owner of this Wayfinder '
                    'for the arrival key to finish this.</p>')
    _first_place = places[0]["id"] if places else "home"
    arrive_guide = "" if not places else (
        '<details class="tk-guide"><summary>📱 Alert me the moment I arrive</summary>'
        '<div class="tk-guide-body">'
        '<p class="tk-place-note">Your phone is the only thing that knows you '
        'arrived. Set this once and it keeps working.</p>'
        '<div id="tkGuideIos" hidden>'
        '<ol class="tk-guide-steps">'
        '<li>Open the <b>Shortcuts</b> app (it comes with iPhone)</li>'
        '<li><b>Automation</b> → <b>+</b> → <b>Arrive</b>, pick the place</li>'
        '<li>Turn <b>Run Immediately</b> on, <b>Notify When Run</b> off</li>'
        '<li>Add action <b>Get Contents of URL</b>, then paste below</li>'
        '</ol></div>'
        '<div id="tkGuideAndroid" hidden>'
        '<ol class="tk-guide-steps">'
        '<li>Install <b>MacroDroid</b> (free) from Play Store</li>'
        '<li><b>Add Macro</b> → Trigger: <b>Geofence → Entry</b>, pick the place</li>'
        '<li>Action: <b>Connectivity → HTTP Request</b>, method <b>POST</b></li>'
        '<li>Paste the values below into that request</li>'
        '</ol></div>'
        '<div class="tk-guide-fields">'
        f'{_copy_row("URL", "https://wayfindar.duckdns.org/momentum/arrive", "gU")}'
        f'{_copy_row("Method", "POST", "gM")}'
        f'{_copy_row("Header", f"X-Arrive-Secret: {_secret}", "gH") if _secret else ""}'
        f'{_copy_row("Body (JSON)", json.dumps({"place": _first_place, "user": user}), "gB")}'
        '</div>'
        f'{_origin_note}'
        '<p class="tk-place-note">One automation per place — change '
        '<code>place</code> in the body to match.</p>'
        '</div></details>')

    places_html = "" if readonly else (
        f'<details class="tk-places"{" open" if not places else ""}>'
        f'<summary>📍 Places <span class="tk-section-n">{len(places)}</span></summary>'
        f'<div class="tk-places-body">'
        f'{place_rows or "<div class=\'tk-place-meta\'>No places yet — stand where you work and save it.</div>"}'
        f'<form method="POST" action="/momentum/place/add" id="tkPlaceForm" class="tk-place-add">'
        f'<input type="hidden" name="next" value="{back}">'
        f'<input type="hidden" name="lat" id="tkLat"><input type="hidden" name="lon" id="tkLon">'
        f'<input type="text" name="label" id="tkLabel" class="wf-input" placeholder="Place name (e.g. Office)" required>'
        f'<button type="button" class="btn btn-secondary btn-sm" onclick="tkSavePlace()">Use my current location</button>'
        f'<span id="tkGeoMsg" class="tk-place-meta"></span></form>'
        f'<button type="button" class="btn btn-secondary btn-sm tk-near-ask" '
        f'id="tkNearAskBtn" onclick="tkNearAsk()" hidden>'
        f'📍 Check what is near me</button>'
        f'<p class="tk-place-note">Opening this page checks where you are. '
        f'A browser cannot do that in the background — for an alert the moment '
        f'you arrive, set up your phone below.</p>'
        f'{arrive_guide}'
        f'</div></details>')

    place_opts = _place_options(places, "")
    sheet_html = "" if readonly else f'''
<div class="tk-backdrop" id="tkBackdrop" onclick="tkClose()"></div>
<div class="tk-sheet" id="tkSheet" role="dialog" aria-label="Task details">
  <div class="tk-sheet-grip"></div>
  <form method="POST" action="/todo/set_meta" class="tk-sheet-form">
    <input type="hidden" name="id" id="tkSid">
    <input type="hidden" name="next" value="{back}">
    <div class="wf-field"><label class="wf-label">Task</label>
      <input class="wf-input" type="text" name="title" id="tkStitle" required></div>
    <div class="tk-sheet-grid tk-sheet-grid--tight">
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
    <input type="hidden" name="next" value="{back}">
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
  <div class="tk-sheet-habit">
    <button class="btn btn-secondary" type="button" id="tkHabitBtn"
            onclick="tkHabitOpen()">🔁 Also track as a habit</button>
  </div>
  <form method="POST" action="/todo/delete" class="tk-sheet-delete"
        onsubmit="return confirm('Delete this task?')">
    <input type="hidden" name="id" id="tkDid">
    <input type="hidden" name="next" value="{back}">
    <button class="btn btn-danger" type="submit">Delete task</button>
  </form>
</div>
<div class="tk-sheet" id="tkHabitSheet" role="dialog" aria-label="Track as habit">
  <div class="tk-sheet-grip"></div>
  <form method="POST" action="/todo/to_habit" class="tk-sheet-form">
    <input type="hidden" name="id" id="tkHid">
    <input type="hidden" name="next" value="{back}">
    <div class="wf-field"><label class="wf-label">Habit name</label>
      <input class="wf-input" type="text" name="name" id="tkHbName" required></div>
    <div class="tk-sheet-grid tk-sheet-grid--tight">
      <div class="wf-field"><label class="wf-label">Icon</label>
        <input class="wf-input" type="text" name="icon" id="tkHbIcon" value="✅" maxlength="4"></div>
      <div class="wf-field"><label class="wf-label">Goal per day</label>
        <input class="wf-input" type="number" name="target" value="1" min="1" max="999"></div>
    </div>
    <div class="wf-field tk-hb-freq">{habit_freq_picker}</div>
    <div class="tk-sheet-actions">
      <button class="btn btn-primary btn-lg" type="submit">Create habit</button>
      <button class="btn btn-ghost btn-lg" type="button" onclick="tkHabitClose()">Cancel</button>
    </div>
  </form>
</div>
<div class="tk-sheet" id="tkFup" role="dialog" aria-label="Follow-up task">
  <div class="tk-sheet-grip"></div>
  <div class="tk-fup-done">✓ <span id="tkFupTitle"></span></div>
  <form method="POST" action="/todo/add" class="tk-sheet-form">
    <input type="hidden" name="next" value="{back}">
    <input type="hidden" name="project" id="tkFupProject">
    <input type="hidden" name="place_id" id="tkFupPlace">
    <input type="hidden" name="group" id="tkFupGroup">
    <input type="hidden" name="priority" id="tkFupPrio">
    <div class="wf-field"><label class="wf-label">Anything follow from this?</label>
      <input class="wf-input" type="text" name="title" id="tkFupInput"
             placeholder="Next step — leave empty if none" autocomplete="off"></div>
    <div class="tk-sheet-actions">
      <button class="btn btn-primary btn-lg" type="submit">Add follow-up</button>
      <button class="btn btn-ghost btn-lg" type="button" onclick="tkFupClose()">Nothing follows</button>
    </div>
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

/* Pill toggle — cardconv's view tabs, same tokens and same active treatment. */
.tk-group{{display:inline-flex;align-items:center;gap:2px;padding:3px;margin-bottom:14px;
  max-width:100%;overflow-x:auto;scrollbar-width:none;
  background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md)}}
.tk-group::-webkit-scrollbar{{display:none}}
.tk-gtab{{display:inline-flex;align-items:center;flex:0 0 auto;min-height:38px;
  padding:7px 16px;font-size:var(--text-sm);font-weight:var(--fw-semibold);
  color:var(--text-muted);border-radius:var(--radius-sm);text-decoration:none;
  transition:background .15s,color .15s}}
.tk-gtab:hover{{color:var(--text)}}
.tk-gtab.active{{background:var(--accent);color:var(--on-accent)}}

.tk-section{{margin-bottom:22px}}
.tk-section-head{{display:flex;align-items:center;gap:8px;margin:0 2px 8px;
  font-size:var(--text-xs);font-weight:var(--fw-bold);letter-spacing:.06em;
  text-transform:uppercase;color:var(--text-muted)}}
/* A project name is something the user typed — shouting it back in caps is not
   ours to do, so this heading keeps the case it was written in. */
.tk-section-head--project{{text-transform:none;letter-spacing:0;
  font-size:var(--text-sm);color:var(--text)}}
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
/* A class selector beats the browser's own [hidden]{{display:none}}, so this
   box kept its border and margin while holding nothing — an empty strip at the
   top of the page that looks like a bug because it is one. */
.tk-near[hidden]{{display:none}}
.tk-near{{display:flex;align-items:center;gap:10px;flex-wrap:wrap;
  background:var(--surface-2);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:10px 14px;margin-bottom:12px}}
.tk-near-txt{{flex:1;min-width:0;font-size:var(--text-sm)}}
.tk-near-ask{{align-self:flex-start;min-height:44px}}
.tk-near-ask[hidden]{{display:none}}
.tk-near .btn{{min-height:36px}}
.tk-row--hit{{outline:2px solid var(--accent);outline-offset:-2px}}
.tk-guide{{margin-top:14px;border-top:1px solid var(--border);padding-top:12px}}
.tk-guide summary{{cursor:pointer;font-size:var(--text-sm);font-weight:var(--fw-bold)}}
.tk-guide-body{{padding-top:10px;display:flex;flex-direction:column;gap:10px}}
.tk-guide-steps{{margin:0;padding-left:20px;font-size:var(--text-sm);
  color:var(--text-muted);display:flex;flex-direction:column;gap:6px}}
.tk-guide-fields{{display:flex;flex-direction:column;gap:8px}}
.tk-copy{{display:flex;align-items:center;gap:8px;flex-wrap:wrap}}
.tk-copy-label{{font-size:var(--text-xs);font-weight:var(--fw-bold);
  text-transform:uppercase;letter-spacing:.06em;color:var(--text-muted);
  min-width:92px}}
.tk-copy-val{{flex:1;min-width:0;overflow-x:auto;white-space:nowrap;
  background:var(--surface-3);border:1px solid var(--border);
  border-radius:var(--radius-md);padding:6px 10px;font-size:var(--text-xs)}}
.tk-copy .btn{{min-height:36px}}
@media (max-width:768px){{
  .tk-copy-label{{min-width:100%}}
}}
.tk-sheet-habit{{margin-top:12px}}
.tk-hb-freq select{{width:100%;min-height:44px}}
{FREQ_PICKER_CSS}
.tk-sheet-habit .btn{{width:100%;min-height:44px}}
.tk-sheet-habit .btn:disabled{{opacity:.55;cursor:default}}
.tk-fup-done{{font-size:var(--text-sm);color:var(--text-muted);margin-bottom:12px;
  padding-bottom:12px;border-bottom:1px solid var(--border);
  overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
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
/* A date field and a two-word select do not need a row each. Stretched to the
   full sheet width a date input is mostly empty box with its calendar icon
   stranded at the far end — it reads as broken layout, not a spacious form.
   min-width:0 lets them actually shrink into their tracks. */
.tk-sheet-grid--tight>*{{min-width:0}}
.tk-sheet-grid--tight .wf-input{{width:100%;min-width:0}}
@media (max-width:768px){{
  .tk-sheet-grid:not(.tk-sheet-grid--tight){{grid-template-columns:1fr}}
  .tk-quick-input{{font-size:16px}}
  .tk-row{{padding:14px}}
  .tk-group{{display:flex;width:100%}}
  .tk-gtab{{flex:1;justify-content:center;min-height:44px;padding:10px 14px}}
}}
</style>
</head><body>
<nav>
  <a href="/momentum" class="nav-brand">⚡ Momentum</a>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="tk-wrap">
  <div id="tkNear" class="tk-near" hidden></div>
  {quick_add}
  {summary}
  {group_html}
  {filter_html}
  <div id="tkList">{list_html}</div>
  {places_html}
</div>
{sheet_html}
{tabs_html}
{FREQ_PICKER_JS}
<script>
function tkOpen(row, isNew) {{
  var $ = function(i) {{ return document.getElementById(i); }};
  // On a task that was just created, "Cancel" would read as "undo the add" —
  // but it is already saved. Nothing is lost by closing, so say that.
  var c = $('tkCancel');
  if (c) c.textContent = isNew ? 'Later' : 'Cancel';
  $('tkSid').value = row.dataset.id;
  $('tkDid').value = row.dataset.id;
  $('tkHid').value = row.dataset.id;
  // Already recurring? Then the offer is nonsense — say what is true instead.
  var hb = $('tkHabitBtn');
  if (hb) {{
    var linked = row.dataset.habit === '1';
    hb.disabled = linked;
    hb.textContent = linked ? '🔁 Tracked as a habit' : '🔁 Also track as a habit';
  }}
  $('tkStitle').value = row.dataset.title || '';
  // New tasks start due today (local date — toISOString alone is UTC and lags KST at night)
  var localToday = new Date(Date.now() - new Date().getTimezoneOffset()*60000).toISOString().slice(0,10);
  $('tkSdue').value = row.dataset.due || (isNew ? localToday : '');
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
  tkFupClose();
  tkHabitClose();
}}
// Becoming a habit is a decision with settings attached — how often, what to
// call it, what counts as a day's worth. Creating one silently on a tap gave
// you a daily habit you never agreed to and had to go elsewhere to fix.
function tkHabitOpen() {{
  var $ = function(i) {{ return document.getElementById(i); }};
  $('tkHbName').value = $('tkStitle').value || '';
  $('tkSheet').classList.remove('is-on');
  $('tkHabitSheet').classList.add('is-on');
  $('tkBackdrop').classList.add('is-on');
  $('tkHbName').focus();
}}
function tkHabitClose() {{
  document.getElementById('tkHabitSheet').classList.remove('is-on');
  document.getElementById('tkBackdrop').classList.remove('is-on');
}}
function tkFupClose() {{
  var f = document.getElementById('tkFup');
  if (f) f.classList.remove('is-on');
  document.getElementById('tkBackdrop').classList.remove('is-on');
}}
// A finished task carries the context its successor should start with — same
// project, same place, same list. Only the deadline is left blank: a follow-up
// inherits the work, not the date the work was due.
function tkFupOpen(row) {{
  var $ = function(i) {{ return document.getElementById(i); }};
  $('tkFupTitle').textContent = row.dataset.title || '';
  $('tkFupProject').value = row.dataset.project || '';
  $('tkFupPlace').value = row.dataset.place || '';
  $('tkFupGroup').value = row.dataset.group || '';
  $('tkFupPrio').value = row.dataset.prio || '2';
  $('tkFupInput').value = '';
  $('tkBackdrop').classList.add('is-on');
  $('tkFup').classList.add('is-on');
  $('tkFupInput').focus();
}}
document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') tkClose();
}});
// Just added something? Finish setting it up right here, then drop the ?new=
// so a refresh does not reopen the sheet.
(function() {{
  var qs = new URLSearchParams(location.search);
  var nid = qs.get('new');
  if (!nid) return;
  var row = document.querySelector('.tk-row[data-id="' + nid + '"]');
  // Drop only ?new= — anything else in the URL (the grouping choice) stays.
  qs.delete('new');
  if (!qs.get('tab')) qs.set('tab', 'tasks');
  history.replaceState({{}}, '', location.pathname + '?' + qs.toString());
  if (!row) return;
  tkOpen(row, true);
  row.scrollIntoView({{block: 'center'}});
  var t = document.getElementById('tkSdue');
  if (t) t.focus();
}})();
// Just finished something? Offer the next step before the context fades. The
// row is inside the collapsed Completed section, which querySelector still
// reaches — no need to open it.
(function() {{
  var qs = new URLSearchParams(location.search);
  var fid = qs.get('followup');
  if (!fid) return;
  var row = document.querySelector('.tk-row[data-id="' + fid + '"]');
  qs.delete('followup');
  if (!qs.get('tab')) qs.set('tab', 'tasks');
  history.replaceState({{}}, '', location.pathname + '?' + qs.toString());
  if (row) tkFupOpen(row);
}})();
// Show the guide for the phone you are holding. A stranger's instructions are
// worse than none — they read as "this app does not know what it is doing".
(function() {{
  var ua = navigator.userAgent || '';
  var ios = /iPhone|iPad|iPod/.test(ua) ||
            (/Mac/.test(ua) && navigator.maxTouchPoints > 1);
  var el = document.getElementById(ios ? 'tkGuideIos' : 'tkGuideAndroid');
  if (el) el.hidden = false;
}})();
function tkCopy(id, btn) {{
  var el = document.getElementById(id);
  if (!el) return;
  var txt = el.textContent;
  var done = function() {{
    var was = btn.textContent;
    btn.textContent = 'Copied';
    setTimeout(function() {{ btn.textContent = was; }}, 1400);
  }};
  if (navigator.clipboard) {{
    navigator.clipboard.writeText(txt).then(done, function() {{}});
  }} else {{
    var r = document.createRange();
    r.selectNodeContents(el);
    var s = window.getSelection();
    s.removeAllRanges(); s.addRange(r);
    try {{ document.execCommand('copy'); done(); }} catch (e) {{}}
  }}
}}
// Opening the page is the one moment the browser may ask where you are, so use
// it: if a saved place with open work is within its radius, say so up top.
// Never prompt unasked — an unexplained location dialog on every load is worse
// than the banner is useful, so ask only after a tap.
(function() {{
  var places = {nearby_data};
  var box = document.getElementById('tkNear');
  if (!box || !places.length || !navigator.geolocation) return;

  function km(a, b, c, d) {{  // haversine, metres
    var R = 6371000, p = Math.PI / 180;
    var dLat = (c - a) * p, dLon = (d - b) * p;
    var x = Math.sin(dLat / 2) * Math.sin(dLat / 2) +
            Math.cos(a * p) * Math.cos(c * p) *
            Math.sin(dLon / 2) * Math.sin(dLon / 2);
    return 2 * R * Math.atan2(Math.sqrt(x), Math.sqrt(1 - x));
  }}
  function locate() {{
    navigator.geolocation.getCurrentPosition(function(pos) {{
      var here = null;
      places.forEach(function(pl) {{
        var d = km(pos.coords.latitude, pos.coords.longitude, pl.lat, pl.lon);
        if (d <= pl.r && (!here || d < here.d)) {{ here = pl; here.d = d; }}
      }});
      if (!here) {{ box.hidden = true; return; }}
      box.innerHTML = '<span class="tk-near-txt">📍 You are at <b>' +
        here.label + '</b> — ' + here.n + ' here</span>' +
        '<button type="button" class="btn btn-secondary btn-sm" ' +
        'onclick="tkShowPlace(\\'' + here.id + '\\')">Show</button>';
      box.hidden = false;
    }}, function() {{ box.hidden = true; }}, {{ timeout: 8000, maximumAge: 120000 }});
  }}
  // The banner speaks only when it has something to say. Before permission is
  // granted it has nothing, and a standing "shall I check?" strip is just a
  // border with a question in it — that ask lives in Places instead.
  window.tkNearAsk = locate;
  var ask = document.getElementById('tkNearAskBtn');
  if (ask) ask.hidden = false;
  if (navigator.permissions && navigator.permissions.query) {{
    navigator.permissions.query({{name: 'geolocation'}}).then(function(p) {{
      if (p.state === 'granted') locate();
    }}, function() {{}});
  }}
}})();
function tkShowPlace(pid) {{
  var first = null;
  document.querySelectorAll('.tk-row').forEach(function(r) {{
    var hit = r.dataset.place === pid && !r.classList.contains('tk-row--done');
    r.classList.toggle('tk-row--hit', hit);
    if (hit && !first) first = r;
  }});
  if (first) first.scrollIntoView({{block: 'center', behavior: 'smooth'}});
}}
function tkFilter() {{
  // The project select is absent while the list is grouped by project.
  var pjEl = document.getElementById('tkFProject');
  var pj = pjEl ? pjEl.value : '';
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
