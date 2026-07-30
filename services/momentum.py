"""Momentum — one route for tasks, habits and today.

The three were separate services with separate home cards even though they
already shared a tab bar and read each other's files. This module is the single
entry point. The tab renderers stay in todo.py / habits.py / dashboard.py, which
keep their own POST routes — every form action already in the wild (and on
someone's phone home screen) keeps working untouched.

It also owns places and the arrival webhook. A browser cannot watch your
location in the background — the Geofencing API is gone and a service worker
has no access to position — so nothing here pretends to. The phone's own
"when I arrive" automation calls POST /momentum/arrive, and the server answers with
whatever is waiting at that place.
"""
import json
import os
import urllib.parse
import urllib.request

# dashboard.py is no longer rendered — Today folded into Tasks — but the file
# stays: the home page still reads its projects, and its weekly charts are
# worth reusing somewhere else.
import services.habits as habits
import services.todo as todo
from services._paths import DATA_ROOT

META = {
    "name": "Momentum",
    "path": "/momentum",
    "icon": "⚡",
    "description": "Tasks you finish and habits you keep, in one place",
}

# tab key -> the old path it replaced, used for both rendering and redirects
# Today is gone: habits now appear inside the task list as things to do today,
# which is what a "today" screen was for. /dashboard still redirects here.
TABS = {
    "tasks": "/todo",
    "habits": "/habit",
}
DEFAULT_TAB = "tasks"

# How far from a saved point still counts as "here", when the caller does not say.
DEFAULT_RADIUS_M = 200


def tab_for_path(path):
    """Which tab an old URL should land on. Unknown paths land on the default."""
    for tab, old in TABS.items():
        if path == old or path.startswith(old + "/"):
            return tab
    return DEFAULT_TAB


# --- places -------------------------------------------------------------------

def _places_file(user):
    d = os.path.join(DATA_ROOT, user or "guest")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "work_places.json")


def load_places(user):
    try:
        with open(_places_file(user)) as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def save_places(places, user):
    with open(_places_file(user), "w") as f:
        json.dump(places, f, ensure_ascii=False, indent=2)


def _slug(label, existing):
    """Readable id from the label, falling back to place-N.

    ASCII only on purpose: the id is typed into a phone automation and travels
    in a URL, and `"오피스".isalnum()` is True in Python — a Korean label would
    otherwise become a percent-encoded id that nobody can type.
    """
    base = "".join(c if (c.isascii() and c.isalnum()) else "-"
                   for c in (label or "").lower()).strip("-")
    base = "-".join(p for p in base.split("-") if p) or "place"
    if base not in existing:
        return base
    n = 2
    while f"{base}-{n}" in existing:
        n += 1
    return f"{base}-{n}"


def add_place(user, label, lat, lon, radius_m=DEFAULT_RADIUS_M):
    places = load_places(user)
    pid = _slug(label, {p["id"] for p in places})
    places.append({"id": pid, "label": label or pid, "lat": float(lat),
                   "lon": float(lon), "radius_m": int(radius_m or DEFAULT_RADIUS_M)})
    save_places(places, user)
    return pid


def find_place(user, place_id):
    for p in load_places(user):
        if p["id"] == place_id:
            return p
    return None


def tasks_at(user, place_id):
    """Open tasks pinned to a place."""
    return [t for t in todo.load(user)
            if not t.get("done") and (t.get("place_id") or "") == place_id]


# --- arrival ------------------------------------------------------------------

def _telegram(text):
    """Best effort — an arrival with no Telegram configured is a no-op, not an
    error, so the phone automation never sees a failure it cannot act on."""
    tok = os.environ.get("TELEGRAM_TOKEN", "")
    chat = os.environ.get("TG_ADMIN_CHAT_ID", "")
    if not (tok and chat):
        return False
    try:
        data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
        urllib.request.urlopen(
            f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=10)
        return True
    except Exception:
        return False


def arrive(user, place_id):
    """Announce what is waiting at a place. Returns (count, label)."""
    place = find_place(user, place_id)
    if not place:
        return (None, None)
    tasks = tasks_at(user, place_id)
    if not tasks:
        return (0, place["label"])
    lines = [f"📍 {place['label']} — 여기서 할 일 {len(tasks)}건"]
    for t in tasks[:10]:
        due = f" (~{t['due_date']})" if t.get("due_date") else ""
        prio = todo.PRIORITIES[todo._priority_of(t.get("priority"))][0]
        lines.append(f"• {t['title']}{due} [{prio}]")
    if len(tasks) > 10:
        lines.append(f"… 외 {len(tasks) - 10}건")
    _telegram("\n".join(lines))
    return (len(tasks), place["label"])


def _next_of(body):
    """Where a place action returns to — the task list, keeping whichever
    grouping was on screen. Same-site paths only, so a posted `next` cannot
    bounce the user off to another host."""
    nxt = (body.get("next") or [""])[0].strip()
    if nxt.startswith("/") and not nxt.startswith("//"):
        return nxt
    return "/momentum?tab=tasks"


def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user", "guest")
    body = body or {}

    if method == "POST":
        if path == "/momentum/place/add":
            label = (body.get("label") or [""])[0].strip()
            lat = (body.get("lat") or [""])[0].strip()
            lon = (body.get("lon") or [""])[0].strip()
            if label and lat and lon:
                try:
                    pid = add_place(user, label, lat, lon,
                                    (body.get("radius_m") or [DEFAULT_RADIUS_M])[0])
                except ValueError:
                    pid = None    # a non-numeric coordinate just does not save
                # Created from a task's detail sheet: pin that task to it, or the
                # place exists and the task still has nowhere.
                task_id = (body.get("task_id") or [""])[0].strip()
                if pid and task_id:
                    ts = todo.load(user)   # module-level import; a local one here
                    # would shadow it and break the whole handler
                    for t in ts:
                        if str(t.get("id")) == task_id:
                            t["place_id"] = pid
                    todo.save(ts, user)
            return ("redirect", _next_of(body))

        if path == "/momentum/place/delete":
            pid = (body.get("id") or [""])[0]
            save_places([p for p in load_places(user) if p["id"] != pid], user)
            return ("redirect", _next_of(body))

        return ("redirect", "/momentum")

    tab = (body.get("tab") or [DEFAULT_TAB])[0]
    if tab == "habits":
        return ("html", habits.render_list(habits.load(user), user))
    group_by = (body.get("by") or ["date"])[0]
    return ("html", todo.render(todo.load(user), habits.load(user), user,
                                group_by=group_by))
