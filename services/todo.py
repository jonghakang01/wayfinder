import json, os
from datetime import datetime, date, timedelta

DATA_ROOT = os.path.expanduser("~/.appdata")

META = {
    "name": "Todo List",
    "path": "/todo",
    "icon": "📋",
    "description": "할 일 관리",
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
        return f'<span class="badge overdue">D+{abs(n)}일 초과</span>'
    if n == 0:
        return '<span class="badge dday">D-Day</span>'
    return f'<span class="badge due">D-{n}</span>'


def early_badge(due_date_str, done_at_str):
    if not due_date_str or not done_at_str:
        return ""
    days_early = (date.fromisoformat(due_date_str) - date.fromisoformat(done_at_str[:10])).days
    if days_early > 0:
        return f'<span class="badge early">🎉 {days_early}일 앞당김!</span>'
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
                if t["id"] == tid and not t.get("habit_id"):
                    habits = load_habits(user)
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

    # ── 습관 섹션 ────────────────────────────────────────────
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
                checkin_html = '<span class="hb-done">✓ 완료</span>'
            elif readonly:
                checkin_html = '<span class="hb-done" style="color:#94a3b8">미완료</span>'
            else:
                checkin_html = (
                    f'<form method="POST" action="/habit/{h["id"]}/checkin" style="display:inline">'
                    f'<input type="hidden" name="next" value="/todo">'
                    f'<button class="btn hb-check">체크인</button></form>'
                )

            habit_rows += f'''
            <div class="habit-item {"habit-checked" if checked else ""}">
              <span class="h-icon">{h.get("icon","✅")}</span>
              <span class="h-name">{h["name"]}</span>
              <span class="h-streak">🔥 {streak}일</span>
              <div class="h-actions">
                {checkin_html}
                <a href="/habit/{h["id"]}" class="btn hb-detail">상세</a>
              </div>
            </div>'''

        habit_section = f'''
        <div class="habits-section">
          <div class="habits-header">
            <span class="habits-title">🔄 오늘의 습관</span>
            <span class="habits-meta">{today_str} &nbsp; {checked_count}/{len(habits)} 완료</span>
          </div>
          <div class="habit-items">{habit_rows}</div>
          <a href="/habit" class="habits-link">+ 습관 관리 →</a>
        </div>'''
    else:
        habit_section = f'''
        <div class="habits-section habits-empty">
          <span>🔄 오늘의 습관</span>
          <a href="/habit" class="habits-link">습관 추가하기 →</a>
        </div>'''

    # ── Todo 아이템 ──────────────────────────────────────────
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
            action_btn = f'<form method="POST" action="/todo/undone" style="display:inline"><input type="hidden" name="id" value="{t["id"]}"><button class="btn btn-undo">되살리기</button></form>'
            actions_html = f'''
              {action_btn}
              <form method="POST" action="/todo/delete" style="display:inline">
                <input type="hidden" name="id" value="{t["id"]}">
                <button class="btn btn-del">삭제</button>
              </form>'''
        else:
            badge = due_badge(due_date, t["done"])
            done_btn = f'<form method="POST" action="/todo/done" style="display:inline"><input type="hidden" name="id" value="{t["id"]}"><button class="btn btn-done">완료</button></form>'
            if habit_id:
                habit_btn = f'<a href="/habit/{habit_id}" class="btn btn-habit linked">🏃 습관 보기</a>'
            else:
                habit_btn = f'<form method="POST" action="/todo/to_habit" style="display:inline"><input type="hidden" name="id" value="{t["id"]}"><button class="btn btn-habit">🏃 습관화</button></form>'
            actions_html = f'''
              {done_btn}
              {habit_btn}
              <form method="POST" action="/todo/delete" style="display:inline">
                <input type="hidden" name="id" value="{t["id"]}">
                <button class="btn btn-del">삭제</button>
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
        items = '<div class="empty">할 일이 없습니다 🎉</div>'

    add_form = "" if readonly else (
        '<form class="add-form" method="POST" action="/todo/add">'
        '<input type="text" name="title" placeholder="새 할 일..." autofocus required>'
        '<input type="date" name="due_date">'
        '<button type="submit">추가</button>'
        '</form>'
    )

    return f'''<!DOCTYPE html>
<html lang="ko"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>📋 Todo List</title>
<link rel="stylesheet" href="/static/style.css">
<style>
/* badges */
.badge {{ font-size: 0.78rem; padding: 2px 6px; border-radius: 4px; font-weight: 500; }}
.badge.due {{ background: #e8f4fd; color: #2980b9; }}
.badge.overdue {{ background: #fdecea; color: #c0392b; font-weight: 600; }}
.badge.dday {{ background: #fff3cd; color: #d35400; font-weight: 600; }}
.badge.early {{ background: #d4edda; color: #155724; font-weight: 600; }}
.btn-undo {{ background: #fef9c3; color: #854d0e; }}
.btn-habit {{ background: #f0fdf4; color: #166534; text-decoration: none; }}
.btn-habit.linked {{ background: #dcfce7; }}

/* habits section */
.habits-section {{
  background: linear-gradient(135deg, #f0fdf4, #ecfdf5);
  border: 1px solid #bbf7d0;
  border-radius: 12px;
  padding: 16px 20px;
  margin-bottom: 20px;
}}
.habits-section.habits-empty {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 14px 20px;
}}
.habits-header {{
  display: flex; align-items: center; justify-content: space-between;
  margin-bottom: 12px;
}}
.habits-title {{ font-weight: 700; font-size: 0.95rem; color: #166534; }}
.habits-meta {{ font-size: 0.78rem; color: #4ade80; font-weight: 500; }}
.habit-items {{ display: flex; flex-direction: column; gap: 8px; }}
.habit-item {{
  display: flex; align-items: center; gap: 10px;
  background: white; padding: 10px 14px; border-radius: 8px;
  border: 1px solid #d1fae5;
}}
.habit-item.habit-checked {{ opacity: 0.6; }}
.h-icon {{ font-size: 1.1rem; flex-shrink: 0; }}
.h-name {{ flex: 1; font-size: 0.9rem; font-weight: 500; color: #1a1a1a; }}
.h-streak {{ font-size: 0.8rem; color: #f97316; font-weight: 600; white-space: nowrap; }}
.h-actions {{ display: flex; gap: 6px; align-items: center; flex-shrink: 0; }}
.hb-check {{ background: #16a34a; color: white; font-size: 0.78rem; padding: 4px 10px; }}
.hb-done {{ font-size: 0.78rem; color: #16a34a; font-weight: 600; padding: 4px 6px; }}
.hb-detail {{ background: #f0fdf4; color: #166534; font-size: 0.78rem; text-decoration: none; padding: 4px 10px; }}
.habits-link {{ display: inline-block; margin-top: 12px; font-size: 0.82rem; color: #16a34a; text-decoration: none; font-weight: 500; }}
.habits-link:hover {{ text-decoration: underline; }}
</style>
</head><body>
<nav>
  <a href="/">← Wayfinder</a>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">로그아웃</a></span>
</nav>
<div class="container">
  <h1>📋 Todo List{" — " + user if readonly else ""}</h1>
  {habit_section}
  {add_form}
  <div class="stats">
    <span>전체 {total}개</span><span class="done-c">완료 {done_count}개</span><span>미완료 {total - done_count}개</span>
  </div>
  <div class="todo-list">{items}</div>
</div>
</body></html>'''
