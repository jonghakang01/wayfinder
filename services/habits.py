import json, os
from datetime import date, timedelta

DATA_ROOT = os.path.expanduser("~/.appdata")

META = {
    "name": "Habits",
    "path": "/habit",
    "icon": "🏃",
    "description": "Build lasting habits",
}

FREQ_LABEL = {"daily": "Daily", "weekly": "Weekly"}


def _habits_file(user):
    d = os.path.join(DATA_ROOT, user or "guest")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "habits.json")


def load(user):
    f = _habits_file(user)
    if not os.path.exists(f):
        return []
    try:
        with open(f) as fp:
            data = json.load(fp)
            if isinstance(data, dict):
                data["id"] = 1
                data.setdefault("freq", "daily")
                data.setdefault("icon", "✅")
                data = [data]
            for h in data:
                # migrate checkins list → dict
                if isinstance(h.get("checkins"), list):
                    h["checkins"] = {d: 1 for d in h["checkins"]}
                elif not isinstance(h.get("checkins"), dict):
                    h["checkins"] = {}
                h.setdefault("target", 1)
                h.setdefault("unit", "times")
                h.setdefault("track", "count")
                h.setdefault("categories", [])
            return data
    except Exception:
        return []


def save(habits, user):
    with open(_habits_file(user), "w") as fp:
        json.dump(habits, fp, ensure_ascii=False, indent=2)


def next_id(habits):
    return max((h["id"] for h in habits), default=0) + 1


def find_habit(habits, hid):
    return next((h for h in habits if h["id"] == hid), None)


def _day_total(checkins, ds):
    v = checkins.get(ds, 0)
    return v.get("total", 0) if isinstance(v, dict) else (v or 0)


def _day_entries(checkins, ds):
    v = checkins.get(ds)
    return v.get("entries", []) if isinstance(v, dict) else []


def _flat_checkins(checkins):
    """Return {date: number} normalizing rich entries to totals."""
    result = {}
    for ds, v in (checkins or {}).items():
        result[ds] = v.get("total", 0) if isinstance(v, dict) else (v or 0)
    return result


def _category_stats(checkins):
    today = date.today()
    week_start = today - timedelta(days=6)
    month_start = today - timedelta(days=29)
    by_label = {}
    for ds, v in (checkins or {}).items():
        if not isinstance(v, dict):
            continue
        try:
            d = date.fromisoformat(ds)
        except Exception:
            continue
        for entry in v.get("entries", []):
            lbl = (entry.get("label") or "Other").strip() or "Other"
            val = float(entry.get("value") or 0)
            if lbl not in by_label:
                by_label[lbl] = {"week": 0.0, "month": 0.0, "all": 0.0}
            by_label[lbl]["all"] += val
            if d >= week_start:
                by_label[lbl]["week"] += val
            if d >= month_start:
                by_label[lbl]["month"] += val
    return by_label


def is_done(checkins, ds, target):
    return _day_total(checkins, ds) >= max(1, target)


def compute_stats(checkins, target=1):
    today = date.today()
    cs = _flat_checkins(checkins)
    t = max(1, target)

    streak, d = 0, today
    while cs.get(d.isoformat(), 0) >= t:
        streak += 1
        d -= timedelta(days=1)

    longest, cur, prev_d = 0, 0, None
    for ds in sorted(k for k, v in cs.items() if v >= t):
        d = date.fromisoformat(ds)
        cur = cur + 1 if prev_d and (d - prev_d).days == 1 else 1
        longest = max(longest, cur)
        prev_d = d

    total = sum(1 for v in cs.values() if v >= t)
    start_12w = today - timedelta(weeks=12)
    days_12w = (today - start_12w).days + 1
    done_12w = sum(1 for ds, v in cs.items() if date.fromisoformat(ds) >= start_12w and v >= t)
    rate_12w = round(done_12w / days_12w * 100) if days_12w else 0

    return streak, longest, total, rate_12w, done_12w, days_12w


def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user", "guest")
    habits = load(user)
    parts = path.rstrip("/").split("/")

    if method == "POST":
        if path == "/habit/add":
            name = body.get("name", [""])[0].strip()
            freq = body.get("freq", ["daily"])[0]
            if freq not in ("daily", "weekly"):
                freq = "daily"
            try:
                target = max(1, int(body.get("target", ["1"])[0]))
            except ValueError:
                target = 1
            unit = body.get("unit", ["times"])[0].strip() or "times"
            track = body.get("track", ["count"])[0]
            if track not in ("count", "detail"):
                track = "count"
            cats_raw = body.get("categories", [""])[0].strip()
            categories = [c.strip() for c in cats_raw.split(",") if c.strip()]
            if name:
                habits.append({
                    "id": next_id(habits),
                    "name": name,
                    "icon": "✅",
                    "freq": freq,
                    "target": target,
                    "unit": unit,
                    "track": track,
                    "categories": categories,
                    "started": date.today().isoformat(),
                    "checkins": {},
                })
                save(habits, user)
            return ("redirect", "/habit")

        if len(parts) >= 4:
            try:
                hid = int(parts[2])
            except ValueError:
                return ("redirect", "/habit")
            action = parts[3]
            habit = find_habit(habits, hid)
            if habit:
                if action == "checkin":
                    target_date = body.get("date", [date.today().isoformat()])[0]
                    track = habit.get("track", "count")
                    try:
                        target_d = date.fromisoformat(target_date)
                        if target_d <= date.today():
                            habit_target = habit.get("target", 1)
                            current = habit["checkins"].get(target_date, 0)
                            current_total = _day_total(habit["checkins"], target_date)

                            if track == "detail" and body.get("toggle", ["0"])[0] != "1":
                                # Rich check-in: receive label[] and value[] arrays
                                labels = body.get("label", [])
                                values = body.get("value", [])
                                if body.get("clear", ["0"])[0] == "1":
                                    habit["checkins"].pop(target_date, None)
                                else:
                                    entries = []
                                    for lbl, val_str in zip(labels, values):
                                        lbl = lbl.strip()
                                        try:
                                            val = max(0.0, float(val_str))
                                        except (ValueError, TypeError):
                                            val = 0.0
                                        if lbl and val > 0:
                                            entries.append({"label": lbl, "value": val})
                                    if entries:
                                        existing = current if isinstance(current, dict) else {}
                                        all_entries = existing.get("entries", []) + entries
                                        habit["checkins"][target_date] = {
                                            "total": sum(e["value"] for e in all_entries),
                                            "entries": all_entries,
                                        }
                                save(habits, user)
                            else:
                                toggle = body.get("toggle", ["0"])[0] == "1"
                                if toggle:
                                    new_count = 0 if current_total >= habit_target else habit_target
                                else:
                                    delta = int(body.get("delta", ["1"])[0])
                                    new_count = max(0, current_total + delta)
                                if new_count <= 0:
                                    habit["checkins"].pop(target_date, None)
                                else:
                                    habit["checkins"][target_date] = new_count
                                save(habits, user)
                    except (ValueError, KeyError):
                        pass
                    next_url = body.get("next", [f"/habit/{hid}"])[0]
                    return ("redirect", next_url)
                elif action == "edit":
                    name = body.get("name", [""])[0].strip()
                    freq = body.get("freq", ["daily"])[0]
                    if freq not in ("daily", "weekly"):
                        freq = "daily"
                    try:
                        target = max(1, int(body.get("target", ["1"])[0]))
                    except ValueError:
                        target = habit.get("target", 1)
                    unit = body.get("unit", ["times"])[0].strip() or "times"
                    track = body.get("track", ["count"])[0]
                    if track not in ("count", "detail"):
                        track = habit.get("track", "count")
                    cats_raw = body.get("categories", [""])[0].strip()
                    categories = [c.strip() for c in cats_raw.split(",") if c.strip()]
                    if name:
                        habit["name"] = name
                        habit["freq"] = freq
                        habit["target"] = target
                        habit["unit"] = unit
                        habit["track"] = track
                        habit["categories"] = categories
                        save(habits, user)
                    return ("redirect", f"/habit/{hid}")
                elif action == "delete":
                    save([h for h in habits if h["id"] != hid], user)
            return ("redirect", "/habit")

    if len(parts) >= 3 and parts[2].isdigit():
        habit = find_habit(habits, int(parts[2]))
        return ("html", render_detail(habit, user)) if habit else ("redirect", "/habit")

    return ("html", render_list(habits, user))


_CSS = """
:root {
  --bg:#f8fafc; --surface:#ffffff; --border:#e2e8f0;
  --text:#0f172a; --text-muted:#64748b;
  --accent:#3b82f6; --streak:#f59e0b;
  --cell-0:#f1f5f9; --cell-2:#bae6fd; --cell-4:#38bdf8;
  --radius:16px; --gap:4px; --cell:16px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:'Pretendard Variable',Pretendard,-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;min-height:100vh}
.container{width:100%;max-width:720px;margin:0 auto;padding:32px 24px 80px;display:flex;flex-direction:column;gap:24px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:24px;box-shadow:0 4px 20px rgba(0,0,0,0.03)}
nav{position:sticky;top:0;left:0;right:0;padding:13px 32px;background:rgba(15,23,42,0.92);backdrop-filter:blur(12px);border-bottom:1px solid rgba(255,255,255,0.07);display:flex;align-items:center;justify-content:space-between;z-index:100}
nav a{color:#94a3b8;text-decoration:none;font-weight:500;font-size:0.875rem;transition:color 0.15s}
nav a:hover{color:white}
.nav-brand{color:white;font-weight:800;font-size:1.05rem;letter-spacing:-0.02em}
.nav-user{color:#64748b;font-size:0.82rem;display:flex;align-items:center;gap:10px}
.nav-user a{color:#94a3b8;padding:5px 11px;border-radius:8px;background:rgba(255,255,255,0.05);transition:0.2s}
.nav-user a:hover{color:white;background:rgba(255,255,255,0.1)}
h2{font-size:18px;font-weight:700;margin-bottom:16px;color:var(--text)}
.add-form{display:flex;gap:10px;flex-wrap:wrap;align-items:flex-start}
.add-form label{display:flex;flex-direction:column;gap:4px;font-size:12px;color:var(--text-muted);font-weight:600}
.add-form input[type=text],.add-form input[type=number]{padding:9px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:14px;transition:border-color 0.2s}
.add-form input[type=text]{flex:1;min-width:140px}
.add-form input[type=number]{width:72px}
.add-form input:focus{border-color:var(--accent);outline:none}
.add-form select{padding:9px 12px;background:var(--bg);border:1px solid var(--border);border-radius:8px;color:var(--text);font-size:14px}
.add-form button{padding:9px 18px;background:var(--text);color:white;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;transition:opacity 0.2s;align-self:flex-end}
.add-form button:hover{opacity:0.85}
.habit-row{display:flex;align-items:center;gap:14px;padding:14px 0;border-bottom:1px solid var(--border);transition:transform 0.2s}
.habit-row:last-child{border-bottom:none}
.habit-row:hover{transform:translateX(4px)}
.habit-icon-sm{font-size:22px;width:36px;text-align:center;flex-shrink:0}
.habit-info{flex:1}
.habit-name{font-size:15px;font-weight:700;color:var(--text)}
.habit-meta{font-size:12px;color:var(--text-muted);margin-top:2px;display:flex;gap:8px;align-items:center}
.habit-actions{display:flex;gap:8px;align-items:center}
.tag-freq{font-size:11px;padding:2px 8px;border-radius:12px;background:var(--border);color:var(--text-muted)}
.tag-target{font-size:11px;padding:2px 8px;border-radius:12px;background:#eff6ff;color:var(--accent);font-weight:600}
.today-entries.list-entries{display:flex;flex-wrap:wrap;gap:4px;margin-top:4px}
.entry-pill{font-size:11px;padding:2px 8px;border-radius:99px;background:#eff6ff;color:var(--accent);font-weight:600;white-space:nowrap}
.inline-log-panel{background:var(--bg);border:1px solid var(--border);border-top:none;border-radius:0 0 12px 12px;padding:12px 16px;margin-top:-4px;margin-bottom:8px}
.inline-log-form{display:flex;flex-direction:column;gap:8px}
.inline-log-row{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.log-label-inp{flex:1;min-width:100px;padding:7px 10px;border:1px solid var(--border);border-radius:8px;font-size:13px;background:white;color:var(--text)}
.log-val-inp{width:80px;padding:7px 10px;border:1px solid var(--border);border-radius:8px;font-size:13px;background:white;color:var(--text)}
.btn-log-ok{background:var(--accent);color:white;border:none;border-radius:8px;padding:7px 14px;font-size:13px;font-weight:600;cursor:pointer;white-space:nowrap}
.btn-log-ok:hover{opacity:.88}
.log-clear-form{margin-top:6px}
.btn-log-clear{background:none;border:1px solid var(--border);color:var(--text-muted);border-radius:8px;padding:5px 12px;font-size:12px;cursor:pointer}
.btn-log-clear:hover{border-color:#ef4444;color:#ef4444}
@media(max-width:600px){.inline-log-row{flex-direction:column}.log-label-inp,.log-val-inp{width:100%}.btn-log-ok{width:100%;min-height:44px}}
.streak-sm{font-size:13px;color:var(--streak);font-weight:600}
.today-count{font-size:12px;color:var(--text-muted);font-weight:600}
.today-count.done{color:#10b981}
.btn-sm{padding:6px 14px;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer;transition:0.2s}
.btn-detail{background:var(--bg);color:var(--text-muted);text-decoration:none;padding:6px 14px;border-radius:6px;font-size:13px;font-weight:600;border:1px solid var(--border)}
.btn-detail:hover{border-color:var(--accent);color:var(--accent)}
.btn-checkin-sm{background:var(--text);color:white}
.btn-checkin-sm:hover{opacity:0.85}
.btn-checkin-sm.checked{background:var(--bg);color:var(--text-muted);border:1px solid var(--border);cursor:default}
.btn-del-sm{background:transparent;color:var(--text-muted);font-size:12px;border:1px solid var(--border)}
.btn-del-sm:hover{color:#ef4444;border-color:#fecaca;background:#fef2f2}
.header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.habit-title{display:flex;align-items:center;gap:10px}
.habit-icon-lg{width:38px;height:38px;background:linear-gradient(135deg,#1f6feb,#388bfd);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px}
h1{font-size:20px;font-weight:700;color:var(--text)}
.habit-sub{font-size:13px;color:var(--text-muted);margin-top:2px}
.streak-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);color:var(--streak);border-radius:20px;padding:6px 14px;font-size:14px;font-weight:600}
.stats{display:flex;gap:16px;flex-wrap:wrap}
.stat{display:flex;flex-direction:column;gap:4px}
.stat-value{font-size:28px;font-weight:700;line-height:1;color:var(--text)}
.stat-value.streak-c{color:var(--streak)}
.stat-value.accent{color:var(--accent)}
.stat-label{font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px}
.stat-divider{width:1px;background:var(--border);margin:4px 8px}
.heatmap-wrap{overflow-x:auto;padding-bottom:4px}
.heatmap-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:14px}
.heatmap-title{font-size:14px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.6px}
.legend{display:flex;align-items:center;gap:4px;font-size:11px;color:var(--text-muted)}
.legend-cell{width:11px;height:11px;border-radius:2px}
.heatmap-grid-wrap{display:flex;gap:6px}
.dow-labels{display:flex;flex-direction:column;gap:var(--gap);padding-top:18px}
.dow-label{height:var(--cell);font-size:10px;color:var(--text-muted);display:flex;align-items:center;white-space:nowrap;width:20px}
.dow-label:nth-child(even){visibility:hidden}
.weeks-wrap{display:flex;flex-direction:column;gap:4px}
.month-labels{display:flex;gap:var(--gap);margin-bottom:4px}
.month-label{font-size:10px;color:var(--text-muted);width:var(--cell);text-align:center;white-space:nowrap}
.weeks{display:flex;gap:var(--gap)}
.week-col{display:flex;flex-direction:column;gap:var(--gap)}
.day-cell{width:var(--cell);height:var(--cell);border-radius:2px;cursor:pointer;transition:outline .1s}
.day-cell:hover{outline:1px solid rgba(0,0,0,0.25);z-index:1}
.day-cell[data-level="0"]{background:var(--cell-0);border:1px solid var(--border)}
.day-cell[data-level="1"]{background:#e0f2fe}
.day-cell[data-level="2"]{background:#bae6fd}
.day-cell[data-level="3"]{background:#7dd3fc}
.day-cell[data-level="4"]{background:var(--cell-4);box-shadow:0 0 8px rgba(56,189,248,0.3)}
.day-cell.today{outline:2px solid var(--text);outline-offset:1px}
.tooltip{position:fixed;background:var(--surface);border:1px solid var(--border);border-radius:6px;padding:6px 10px;font-size:12px;color:var(--text);pointer-events:none;opacity:0;transition:opacity .15s;z-index:100;white-space:nowrap;box-shadow:0 4px 12px rgba(0,0,0,0.08)}
.tooltip.show{opacity:1}
.checkin-wrap{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.btn-checkin{display:inline-flex;align-items:center;gap:8px;padding:12px 28px;background:var(--text);color:white;font-size:15px;font-weight:600;border:none;border-radius:var(--radius);cursor:pointer;transition:opacity .15s,transform .1s;user-select:none}
.btn-checkin:hover{opacity:0.85;transform:translateY(-1px)}
.btn-checkin.checked{background:var(--bg);color:var(--text-muted);border:1px solid var(--border);cursor:default;box-shadow:none}
.checkin-note{font-size:13px;color:var(--text-muted)}
/* Counter UI for multi-metric */
.counter-wrap{display:flex;align-items:center;gap:20px;flex-wrap:wrap}
.counter-display{display:flex;align-items:baseline;gap:6px}
.counter-num{font-size:3rem;font-weight:800;line-height:1;color:var(--text)}
.counter-num.done{color:var(--accent)}
.counter-sep{font-size:1.5rem;color:var(--text-muted)}
.counter-target{font-size:1.1rem;color:var(--text-muted);font-weight:600}
.counter-btns{display:flex;gap:8px}
.btn-counter{width:44px;height:44px;border:2px solid var(--border);border-radius:12px;background:var(--bg);color:var(--text);font-size:1.4rem;font-weight:700;cursor:pointer;transition:0.15s;display:flex;align-items:center;justify-content:center}
.btn-counter:hover{border-color:var(--accent);color:var(--accent);background:#eff6ff}
.counter-progress{height:6px;background:var(--border);border-radius:9999px;overflow:hidden;width:180px;margin-top:8px}
.counter-fill{height:100%;border-radius:9999px;background:linear-gradient(90deg,#bae6fd,var(--cell-4));transition:width .4s ease}
/* Calendar */
.cal-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:16px}
.cal-title{font-size:15px;font-weight:700;color:var(--text)}
.cal-grid{display:grid;grid-template-columns:repeat(7,1fr);gap:4px}
.cal-dow{text-align:center;font-size:11px;font-weight:600;color:var(--text-muted);padding:4px 0;text-transform:uppercase}
.cal-day{aspect-ratio:1;display:flex;flex-direction:column;align-items:center;justify-content:center;border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;transition:0.15s;border:1px solid transparent;position:relative;gap:2px}
.cal-day:hover{border-color:var(--accent);background:#eff6ff}
.cal-day.empty{cursor:default;background:transparent;border:none}
.cal-day.done{background:#eff6ff;border-color:#bae6fd}
.cal-day.done .cal-count{color:var(--accent)}
.cal-day.today{font-weight:800;border-color:var(--text)}
.cal-day.future{opacity:0.3;cursor:default;pointer-events:none}
.cal-count{font-size:10px;font-weight:600;color:var(--text-muted)}
/* Trend chart */
.trend-wrap{display:flex;gap:6px;align-items:flex-end;height:80px;padding-bottom:20px;position:relative}
.trend-bar-wrap{display:flex;flex-direction:column;align-items:center;gap:4px;flex:1}
.trend-bar{width:100%;border-radius:4px 4px 0 0;background:var(--cell-4);transition:height .4s ease;min-height:2px}
.trend-bar.empty{background:var(--border)}
.trend-label{font-size:9px;color:var(--text-muted);white-space:nowrap;transform:rotate(-30deg);transform-origin:top center;margin-top:4px}
.trend-zero{position:absolute;bottom:20px;left:0;right:0;height:1px;background:var(--border)}
.section-title{font-size:13px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:16px}
.progress-wrap{margin-top:20px}
.progress-label{display:flex;justify-content:space-between;font-size:12px;color:var(--text-muted);margin-bottom:6px}
.progress-bar{height:6px;background:var(--border);border-radius:9999px;overflow:hidden}
.progress-fill{height:100%;border-radius:9999px;background:linear-gradient(90deg,var(--cell-2),var(--cell-4));transition:width .6s ease}
.empty{color:var(--text-muted);font-size:14px;text-align:center;padding:20px 0}
.tab-row{display:flex;gap:4px;margin-bottom:20px}
.tab-btn{padding:6px 14px;border:1px solid var(--border);border-radius:8px;background:var(--bg);color:var(--text-muted);font-size:13px;font-weight:600;cursor:pointer;transition:0.15s}
.tab-btn.active{background:var(--text);color:white;border-color:var(--text)}
.btn-cal-nav{background:none;border:1px solid var(--border);border-radius:8px;cursor:pointer;font-size:18px;color:var(--text-muted);width:44px;height:44px;display:inline-flex;align-items:center;justify-content:center;transition:0.15s}
.btn-cal-nav:hover{border-color:var(--accent);color:var(--accent)}
/* Rich check-in */
.rich-checkin{display:flex;flex-direction:column;gap:14px}
.today-entries{display:flex;flex-direction:column;gap:6px;margin-bottom:4px}
.today-entry{display:flex;justify-content:space-between;align-items:center;padding:8px 12px;background:var(--bg);border-radius:8px;font-size:14px;border:1px solid var(--border)}
.today-entry-label{font-weight:600;color:var(--text)}
.today-entry-val{color:var(--accent);font-weight:700}
.today-total{font-size:14px;font-weight:700;color:var(--text);padding:8px 4px;border-top:1px solid var(--border)}
.entry-rows{display:flex;flex-direction:column;gap:8px}
.entry-row{display:flex;align-items:center;gap:8px;flex-wrap:wrap}
.entry-label-inp{flex:1;min-width:120px;padding:9px 12px;border:1px solid var(--border);border-radius:8px;font-size:14px;background:var(--bg);color:var(--text);transition:.2s}
.entry-label-inp:focus{border-color:var(--accent);outline:none}
.entry-val-inp{width:80px;padding:9px 12px;border:1px solid var(--border);border-radius:8px;font-size:14px;background:var(--bg);color:var(--text);transition:.2s}
.entry-val-inp:focus{border-color:var(--accent);outline:none}
.entry-unit-lbl{font-size:13px;color:var(--text-muted);font-weight:600;min-width:28px}
.entry-del-btn{background:none;border:none;color:var(--text-muted);cursor:pointer;font-size:18px;line-height:1;padding:4px;transition:.15s}
.entry-del-btn:hover{color:#ef4444}
.rich-actions{display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.btn-add-row{padding:8px 16px;background:var(--bg);border:1px solid var(--border);border-radius:8px;font-size:13px;font-weight:600;cursor:pointer;color:var(--text-muted);transition:.2s}
.btn-add-row:hover{border-color:var(--accent);color:var(--accent)}
.btn-save-rich{padding:10px 24px;background:var(--text);color:white;border:none;border-radius:8px;font-size:14px;font-weight:600;cursor:pointer;transition:opacity .15s}
.btn-save-rich:hover{opacity:.85}
.btn-clear-rich{padding:8px 14px;background:transparent;border:1px solid #fecaca;border-radius:8px;font-size:12px;font-weight:600;cursor:pointer;color:#ef4444;transition:.2s}
.btn-clear-rich:hover{background:#fef2f2}
/* By Category */
.cat-period-row{display:flex;gap:4px;margin-bottom:16px}
.cat-period-btn{padding:5px 14px;border:1px solid var(--border);border-radius:20px;background:var(--bg);color:var(--text-muted);font-size:12px;font-weight:600;cursor:pointer;transition:.15s}
.cat-period-btn.active{background:var(--text);color:white;border-color:var(--text)}
.cat-bars{display:flex;flex-direction:column;gap:10px}
.cat-bar-row{display:flex;align-items:center;gap:10px}
.cat-bar-lbl{font-size:13px;font-weight:600;color:var(--text);width:90px;text-align:right;flex-shrink:0;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.cat-bar-track{flex:1;height:20px;background:var(--cell-0);border-radius:6px;overflow:hidden}
.cat-bar-fill{height:100%;background:linear-gradient(90deg,#bae6fd,var(--cell-4));border-radius:6px;min-width:4px;transition:width .5s ease}
.cat-bar-val{font-size:12px;font-weight:700;color:var(--text-muted);min-width:52px}
.tag-pill-wrap{display:flex;flex-wrap:wrap;gap:6px;padding:8px 10px;border:1px solid var(--border);border-radius:8px;background:var(--bg);min-height:42px;cursor:text;align-items:center;width:100%}
.tag-pill-wrap:focus-within{border-color:var(--accent)}
.tag-pill{display:inline-flex;align-items:center;gap:4px;background:#eff6ff;color:var(--accent);border-radius:20px;padding:3px 10px;font-size:13px;font-weight:600}
.tag-pill-del{background:none;border:none;color:var(--accent);cursor:pointer;font-size:15px;line-height:1;padding:0 2px;opacity:.7;transition:.15s}
.tag-pill-del:hover{opacity:1}
.tag-pill-inp{border:none;outline:none;background:transparent;font-size:13px;color:var(--text);min-width:80px;flex:1;padding:2px 0}
.add-form .tag-pill-inp{min-width:0;flex:1}
.field-hint{font-size:11px;color:var(--text-muted);margin-top:3px}
.btn-add-new{padding:6px 16px;background:var(--text);color:white;border:none;border-radius:8px;font-size:13px;font-weight:700;cursor:pointer;transition:opacity .15s;white-space:nowrap}
.btn-add-new:hover{opacity:.8}
@media (max-width:600px){
  .container{padding:12px 12px calc(80px + env(safe-area-inset-bottom,0px))}
  nav{padding:8px 14px}
  .nav-user{font-size:11px}
  .nav-user a{min-height:44px;display:inline-flex;align-items:center;padding:8px 10px}
  .card{padding:16px}
  .header{flex-direction:column;align-items:flex-start;gap:12px}
  h1{font-size:17px}
  h2{font-size:16px}
  .habit-row{flex-wrap:wrap;gap:8px;padding:12px 0}
  .habit-actions{width:100%;justify-content:flex-end;margin-top:4px}
  .btn-sm,.btn-checkin-sm,.btn-del-sm{min-height:40px;padding:8px 14px;font-size:13px}
  .btn-detail{min-height:40px;padding:8px 14px;font-size:13px}
  .add-form{flex-direction:column}
  .add-form label{width:100%}
  .add-form input[type=text]{width:100%;min-height:44px}
  .add-form input[type=number]{width:80px;min-height:44px}
  .add-form select{min-height:44px}
  .add-form button{min-height:44px;font-size:15px}
  .counter-num{font-size:2.2rem}
  .counter-progress{width:100%}
  .counter-wrap{gap:14px}
  .stats{gap:8px;flex-wrap:wrap}
  .stat-divider{display:none}
  .stat-value{font-size:22px}
  .tab-row{gap:6px}
  .tab-btn{flex:1;text-align:center;padding:10px 4px;min-height:44px;font-size:13px}
  .heatmap-wrap{overflow-x:auto;-webkit-overflow-scrolling:touch}
  .streak-badge{font-size:12px;padding:5px 10px}
  #editToggle{min-height:40px;padding:8px 12px}
}
"""

_HEATMAP_JS = """
const MONTH_EN=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const DAY_EN=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const DAY_SHORT=['Sun','Mon','Tue','Wed','Thu','Fri','Sat'];
const WEEKS=12;
const today=new Date();today.setHours(0,0,0,0);
const todayKey=today.toISOString().slice(0,10);
function addDays(d,n){const r=new Date(d);r.setDate(r.getDate()+n);return r;}
function levelOf(key){
  const c=DATA[key]??0;
  if(c<=0)return 0;
  const r=c/TARGET;
  if(r>=1)return 4;
  if(r>=0.75)return 3;
  if(r>=0.5)return 2;
  return 1;
}
const startSunday=addDays(today,-(today.getDay()+(WEEKS-1)*7));
const grid=document.getElementById('heatmapGrid');
const monthLabels=document.getElementById('monthLabels');
const tooltip=document.getElementById('tooltip');
let lastMonth=-1;
for(let w=0;w<WEEKS;w++){
  const col=document.createElement('div');col.className='week-col';
  const ws=addDays(startSunday,w*7);const m=ws.getMonth();
  const ml=document.createElement('div');ml.className='month-label';
  ml.textContent=m!==lastMonth?MONTH_EN[m]:'';monthLabels.appendChild(ml);lastMonth=m;
  for(let d=0;d<7;d++){
    const dt=addDays(startSunday,w*7+d);const key=dt.toISOString().slice(0,10);
    const cell=document.createElement('div');cell.className='day-cell';
    const count=DATA[key]??0;
    if(dt>today){cell.dataset.level=0;cell.style.opacity='0.15';}
    else{cell.dataset.level=levelOf(key);cell.style.cursor='pointer';}
    if(key===todayKey)cell.classList.add('today');
    cell.dataset.date=key;
    const isDone=count>=TARGET;
    const countLabel=TARGET>1?` (${count}/${TARGET})`:'';
    cell.dataset.done=isDone?`✓ Done${countLabel}`:(dt>today?'—':`Not done${countLabel} · click to toggle`);
    cell.addEventListener('mouseenter',e=>{
      const d2=new Date(key+'T00:00:00');
      tooltip.textContent=`${MONTH_EN[d2.getMonth()]} ${d2.getDate()} (${DAY_EN[d2.getDay()]}) · ${cell.dataset.done}`;
      tooltip.classList.add('show');
      tooltip.style.left=(e.clientX+14)+'px';tooltip.style.top=(e.clientY-28)+'px';
    });
    cell.addEventListener('mousemove',e=>{tooltip.style.left=(e.clientX+14)+'px';tooltip.style.top=(e.clientY-28)+'px';});
    cell.addEventListener('mouseleave',()=>tooltip.classList.remove('show'));
    cell.addEventListener('click',()=>{
      if(dt>today)return;
      tooltip.classList.remove('show');
      const form=document.createElement('form');
      form.method='POST';form.action=`/habit/${HID}/checkin`;
      [['date',key],['toggle','1'],['next',window.location.pathname]].forEach(([n,v])=>{
        const i=document.createElement('input');i.type='hidden';i.name=n;i.value=v;form.appendChild(i);
      });
      document.body.appendChild(form);form.submit();
    });
    col.appendChild(cell);
  }
  grid.appendChild(col);
}

// ── Calendar ──────────────────────────────────────────────
function renderCalendar(monthOffset){
  const calEl=document.getElementById('monthCalendar');
  if(!calEl)return;
  calEl.innerHTML='';
  const yr=today.getFullYear(), mo=today.getMonth()+monthOffset;
  const ref=new Date(yr,mo,1);
  const year=ref.getFullYear(), month=ref.getMonth();
  const firstDow=new Date(year,month,1).getDay();
  const daysInMonth=new Date(year,month+1,0).getDate();
  const titleEl=document.getElementById('calTitle');
  if(titleEl)titleEl.textContent=`${MONTH_EN[month]} ${year}`;
  const header=document.createElement('div');header.className='cal-grid';
  ['Su','Mo','Tu','We','Th','Fr','Sa'].forEach(d=>{
    const el=document.createElement('div');el.className='cal-dow';el.textContent=d;header.appendChild(el);
  });
  calEl.appendChild(header);
  const grid=document.createElement('div');grid.className='cal-grid';
  for(let i=0;i<firstDow;i++){
    const el=document.createElement('div');el.className='cal-day empty';grid.appendChild(el);
  }
  for(let d=1;d<=daysInMonth;d++){
    const key=`${year}-${String(month+1).padStart(2,'0')}-${String(d).padStart(2,'0')}`;
    const dt=new Date(year,month,d);dt.setHours(0,0,0,0);
    const count=DATA[key]??0;
    const isDone=count>=TARGET;
    const isFuture=dt>today;
    const isToday=key===todayKey;
    const el=document.createElement('div');
    el.className='cal-day'+(isDone?' done':'')+(isToday?' today':'')+(isFuture?' future':'');
    const dNum=document.createElement('span');dNum.textContent=d;el.appendChild(dNum);
    if(TARGET>1&&count>0){
      const cEl=document.createElement('span');cEl.className='cal-count';cEl.textContent=`${count}/${TARGET}`;el.appendChild(cEl);
    }
    el.title=`${month+1}/${d} · ${isDone?`Done (${count})`:isFuture?'—':`Not done (${count}/${TARGET})`}`;
    if(!isFuture){
      el.addEventListener('click',()=>{
        const form=document.createElement('form');
        form.method='POST';form.action=`/habit/${HID}/checkin`;
        [['date',key],['toggle','1'],['next',window.location.pathname]].forEach(([n,v])=>{
          const i=document.createElement('input');i.type='hidden';i.name=n;i.value=v;form.appendChild(i);
        });
        document.body.appendChild(form);form.submit();
      });
    }
    grid.appendChild(el);
  }
  calEl.appendChild(grid);
}
let calOffset=0;
renderCalendar(calOffset);
document.getElementById('calPrev')?.addEventListener('click',()=>{calOffset--;renderCalendar(calOffset);});
document.getElementById('calNext')?.addEventListener('click',()=>{if(calOffset<0){calOffset++;renderCalendar(calOffset);}});

// ── Trend bars ────────────────────────────────────────────
const trendEl=document.getElementById('trendChart');
if(trendEl){
  for(let w=0;w<WEEKS;w++){
    const ws=addDays(startSunday,w*7);
    let done=0;
    for(let d=0;d<7;d++){
      const key=addDays(ws,d).toISOString().slice(0,10);
      if((DATA[key]??0)>=TARGET)done++;
    }
    const rate=done/7;
    const wrap=document.createElement('div');wrap.className='trend-bar-wrap';
    const bar=document.createElement('div');bar.className='trend-bar'+(done===0?' empty':'');
    bar.style.height=`${Math.max(2,Math.round(rate*64))}px`;
    bar.title=`Week of ${ws.getMonth()+1}/${ws.getDate()} · ${done} days done`;
    const lbl=document.createElement('div');lbl.className='trend-label';
    lbl.textContent=`${ws.getMonth()+1}/${ws.getDate()}`;
    wrap.appendChild(bar);wrap.appendChild(lbl);
    trendEl.appendChild(wrap);
  }
}

// ── Tab switching ─────────────────────────────────────────
document.querySelectorAll('.tab-btn').forEach(btn=>{
  btn.addEventListener('click',()=>{
    const target=btn.dataset.tab;
    document.querySelectorAll('.tab-btn').forEach(b=>b.classList.remove('active'));
    btn.classList.add('active');
    document.querySelectorAll('.tab-panel').forEach(p=>{
      p.style.display=p.id===target?'':'none';
    });
  });
});
"""


def render_list(habits, user, readonly=False):
    today_str = date.today().isoformat()
    rows = ""
    for h in habits:
        target = h.get("target", 1)
        unit = h.get("unit", "times")
        streak, *_ = compute_stats(h.get("checkins", {}), target)
        today_count = _day_total(h.get("checkins", {}), today_str)
        checked = today_count >= target
        freq_lbl = FREQ_LABEL.get(h.get("freq", "daily"), "Daily")
        started = h.get("started", "")[:7]
        target_tag = f'<span class="tag-target">Goal: {target} {unit}</span>' if target > 1 else ""

        del_btn = "" if readonly else (
            f'<form method="POST" action="/habit/{h["id"]}/delete" style="display:inline"'
            f' onsubmit="return confirm(\'Delete habit: {h["name"]}?\')">'
            f'<button class="btn-sm btn-del-sm" type="submit">Delete</button></form>'
        )

        hid = h["id"]
        inline_log_html = ""
        if readonly:
            checkin_btn = f'<span class="btn-sm btn-checkin-sm {"checked" if checked else ""}">{"✓ Done" if checked else "Not done"}</span>'
        elif h.get("track") == "detail":
            count_label = f'<span class="today-count {"done" if checked else ""}">{today_count}/{target}{unit}</span>'
            log_label = "✓ Logged" if checked else "+ Log"
            checkin_btn = (
                f'{count_label}'
                f'<button type="button" class="btn-sm btn-checkin-sm" onclick="toggleLog({hid})">'
                f'{log_label}'
                f'</button>'
            )
            cats = h.get("categories", [])
            if cats:
                label_inp = (
                    '<select name="label[]" class="log-label-inp">'
                    + "".join(f'<option value="{c}">{c}</option>' for c in cats)
                    + '</select>'
                )
            else:
                label_inp = f'<input type="text" name="label[]" placeholder="Activity" class="log-label-inp">'
            clear_btn = (
                f'<form method="POST" action="/habit/{hid}/checkin" class="log-clear-form">'
                f'<input type="hidden" name="clear" value="1">'
                f'<input type="hidden" name="next" value="/habit">'
                f'<button type="submit" class="btn-sm btn-log-clear">Clear today</button></form>'
            ) if today_count > 0 else ""
            inline_log_html = (
                f'<div class="inline-log-panel" id="log-{hid}" style="display:none">'
                f'<form method="POST" action="/habit/{hid}/checkin" class="inline-log-form">'
                f'<input type="hidden" name="next" value="/habit">'
                f'<div class="inline-log-row">'
                f'{label_inp}'
                f'<input type="number" name="value[]" placeholder="{unit}" class="log-val-inp" min="0" step="0.1" required>'
                f'<button type="submit" class="btn-sm btn-log-ok">+ Add</button>'
                f'</div></form>'
                f'{clear_btn}'
                f'</div>'
            )
        elif target > 1:
            count_label = f'<span class="today-count {"done" if checked else ""}">{today_count}/{target}{unit}</span>'
            checkin_btn = (
                f'{count_label}'
                f'<form method="POST" action="/habit/{h["id"]}/checkin" style="display:inline">'
                f'<input type="hidden" name="delta" value="1">'
                f'<input type="hidden" name="next" value="/habit">'
                f'<button class="btn-sm btn-checkin-sm" type="submit">+1{unit}</button></form>'
            )
        else:
            checkin_btn = (
                f'<form method="POST" action="/habit/{h["id"]}/checkin" style="display:inline">'
                f'<input type="hidden" name="toggle" value="1">'
                f'<input type="hidden" name="next" value="/habit">'
                f'<button class="btn-sm btn-checkin-sm{"  checked" if checked else ""}" '
                f'{"type=button" if checked else "type=submit"}>{"✓ Done" if checked else "Check in"}</button></form>'
            )
        # Sub-activity entries for today
        today_entries = _day_entries(h.get("checkins", {}), today_str)
        entries_html = ""
        if today_entries:
            pills = "".join(
                f'<span class="entry-pill">{e.get("label", "")}: {e.get("value", "")}</span>'
                for e in today_entries if e.get("label") or e.get("value")
            )
            if pills:
                entries_html = f'<div class="today-entries list-entries">{pills}</div>'

        rows += f'''
        <div class="habit-row">
          <div class="habit-icon-sm">{h.get("icon", "✅")}</div>
          <div class="habit-info">
            <div class="habit-name">{h["name"]}</div>
            <div class="habit-meta"><span class="tag-freq">{freq_lbl}</span>{target_tag}  {started}</div>
            {entries_html}
          </div>
          <div class="habit-actions">
            <span class="streak-sm">🔥 {streak}d</span>
            {checkin_btn}
            <a class="btn-detail" href="/habit/{h["id"]}">Detail</a>
            {del_btn}
          </div>
        </div>
        {inline_log_html}'''

    if not habits:
        rows = '<div class="empty">No habits yet. Add your first habit!</div>'

    _add_display = 'block' if not habits else 'none'
    add_card = "" if readonly else (
        f'<div class="card" id="addHabitCard" style="display:{_add_display}">'
        '<div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">'
        '<h2 style="margin:0">Add New Habit</h2>'
        '<button type="button" onclick="toggleAddForm()" style="background:none;border:none;cursor:pointer;font-size:22px;color:var(--text-muted);padding:0 4px;line-height:1">×</button>'
        '</div>'
        '<form class="add-form" method="POST" action="/habit/add">'
        '<label>Habit name<input type="text" name="name" placeholder="e.g. Exercise, Read, Drink water" required></label>'
        '<label>Frequency<select name="freq"><option value="daily">Daily</option><option value="weekly">Weekly</option></select></label>'
        '<label>Goal<input type="number" name="target" value="1" min="1" max="999"></label>'
        '<label>Unit'
        '<input type="hidden" name="unit" id="unitHiddenAdd" value="times">'
        '<select id="unitSelAdd" onchange="unitSelChange(this,\'unitHiddenAdd\',\'unitCustomAdd\')">'
        '<option value="times" selected>times</option>'
        '<option value="cups">cups</option><option value="min">min</option>'
        '<option value="km">km</option><option value="pages">pages</option>'
        '<option value="sets">sets</option><option value="hrs">hrs</option>'
        '<option value="__custom">Custom...</option>'
        '</select>'
        '<input type="text" id="unitCustomAdd" placeholder="e.g. reps" style="display:none;width:90px;min-width:0;margin-top:4px" oninput="document.getElementById(\'unitHiddenAdd\').value=this.value">'
        '<span class="field-hint">type your own</span>'
        '</label>'
        '<label style="width:100%">Tracking<select name="track">'
        '<option value="count">Simple (done / count)</option>'
        '<option value="detail">Detailed (log each activity)</option>'
        '</select></label>'
        '<label style="width:100%">Activity Labels'
        '<span style="font-size:11px;color:var(--text-muted);margin-left:6px">(optional — press Enter or , to add)</span>'
        '<input type="hidden" name="categories" id="catsHiddenAdd" value="">'
        '<div class="tag-pill-wrap" id="catPillsAdd"><input type="text" id="catInpAdd" class="tag-pill-inp" placeholder="e.g. Running, Walking..."></div>'
        '</label>'
        '<button type="submit">Add</button>'
        '</form></div>'
    )

    from server import app_tabs
    tabs_html = app_tabs("/habit")
    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🏃 Habits</title>
<link rel="stylesheet" href="/static/style.css">
<style>{_CSS}</style>
</head>
<body>
<nav>
  <span class="nav-brand">🏃 Habits</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container">

  {add_card}

  <div class="card">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:16px">
      <h2 style="margin:0">{"🏃 " + user + "'s " if readonly else ""}Habits</h2>
      {"" if readonly else '<button type="button" onclick="toggleAddForm()" class="btn-add-new">＋ New Habit</button>'}
    </div>
    {rows}
  </div>

</div>
{tabs_html}
<script>
document.addEventListener('keydown', function(e) {{
  if (e.key !== 'Enter' || e.target.tagName !== 'INPUT') return;
  var t = e.target.type;
  if (t === 'submit' || t === 'button' || t === 'checkbox' || t === 'radio') return;
  if (e.target.classList.contains('tag-pill-inp')) return;
  e.preventDefault();
  var form = e.target.closest('form');
  if (!form) return;
  var inputs = Array.from(form.querySelectorAll('input:not([type=hidden]):not([type=submit]):not([type=button]), select, textarea'));
  var idx = inputs.indexOf(e.target);
  if (idx < inputs.length - 1) inputs[idx + 1].focus();
}});
function initTagPills(pillsId, textId, hiddenId) {{
  var pillsEl = document.getElementById(pillsId);
  var textEl = document.getElementById(textId);
  var hiddenEl = document.getElementById(hiddenId);
  if (!pillsEl || !textEl || !hiddenEl) return;
  function getTags() {{
    return hiddenEl.value ? hiddenEl.value.split(',').map(function(s){{return s.trim();}}).filter(Boolean) : [];
  }}
  function setTags(tags) {{
    hiddenEl.value = tags.join(',');
    render();
  }}
  function render() {{
    var tags = getTags();
    while (pillsEl.firstChild) pillsEl.removeChild(pillsEl.firstChild);
    tags.forEach(function(t, i) {{
      var pill = document.createElement('span');
      pill.className = 'tag-pill';
      var txt = document.createElement('span'); txt.textContent = t;
      var del = document.createElement('button');
      del.type = 'button'; del.className = 'tag-pill-del'; del.textContent = '×';
      (function(idx) {{
        del.addEventListener('click', function() {{
          var arr = getTags(); arr.splice(idx, 1); setTags(arr);
        }});
      }})(i);
      pill.appendChild(txt); pill.appendChild(del);
      pillsEl.appendChild(pill);
    }});
    pillsEl.appendChild(textEl);
  }}
  textEl.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter' || e.key === ',') {{
      e.preventDefault(); e.stopPropagation();
      var val = textEl.value.trim().replace(/,$/, '');
      if (val) {{
        var tags = getTags();
        if (tags.indexOf(val) === -1) tags.push(val);
        setTags(tags); textEl.value = '';
      }}
    }} else if (e.key === 'Backspace' && textEl.value === '') {{
      var tags = getTags();
      if (tags.length > 0) {{ tags.pop(); setTags(tags); }}
    }}
  }});
  pillsEl.addEventListener('click', function() {{ textEl.focus(); }});
  render();
}}
function unitSelChange(sel, hiddenId, customId) {{
  var hidden = document.getElementById(hiddenId);
  var custom = document.getElementById(customId);
  if (!hidden || !custom) return;
  if (sel.value === '__custom') {{
    custom.style.display = 'inline-block';
    custom.focus();
  }} else {{
    custom.style.display = 'none';
    hidden.value = sel.value;
  }}
}}
function initUnitSel(selId, hiddenId, customId) {{
  var presets = ['times','cups','min','km','pages','sets','hrs'];
  var hidden = document.getElementById(hiddenId);
  var sel = document.getElementById(selId);
  var custom = document.getElementById(customId);
  if (!hidden || !sel || !custom) return;
  var val = hidden.value;
  if (presets.indexOf(val) >= 0) {{
    sel.value = val;
  }} else {{
    sel.value = '__custom';
    custom.style.display = 'inline-block';
    custom.value = val;
  }}
}}
initTagPills('catPillsAdd', 'catInpAdd', 'catsHiddenAdd');
initUnitSel('unitSelAdd', 'unitHiddenAdd', 'unitCustomAdd');
function toggleAddForm() {{
  var card = document.getElementById('addHabitCard');
  if (!card) return;
  if (card.style.display === 'none') {{
    card.style.display = 'block';
    card.scrollIntoView({{behavior:'smooth', block:'nearest'}});
    setTimeout(function() {{
      var inp = card.querySelector('input[name=name]');
      if (inp) inp.focus();
    }}, 250);
  }} else {{
    card.style.display = 'none';
  }}
}}
function toggleLog(id) {{
  var panel = document.getElementById('log-' + id);
  if (!panel) return;
  var open = panel.style.display !== 'none';
  document.querySelectorAll('.inline-log-panel').forEach(function(p) {{ p.style.display = 'none'; }});
  if (!open) {{
    panel.style.display = 'block';
    var inp = panel.querySelector('input[type=text],input[type=number],select');
    if (inp) setTimeout(function() {{ inp.focus(); }}, 50);
  }}
}}
</script>
</body>
</html>'''


def render_detail(habit, user):
    today = date.today()
    cs = habit.get("checkins", {})
    target = habit.get("target", 1)
    unit = habit.get("unit", "times")
    track = habit.get("track", "count")
    categories = habit.get("categories", [])
    today_str = today.isoformat()
    today_count = _day_total(cs, today_str)
    today_done = today_count >= target
    today_entries = _day_entries(cs, today_str)
    hid = habit["id"]

    streak, longest, total, rate_12w, done_12w, days_12w = compute_stats(cs, target)

    WEEKS = 12
    days_since_sun = today.weekday() + 1 if today.weekday() != 6 else 0
    start_sunday = today - timedelta(days=days_since_sun + (WEEKS - 1) * 7)
    heatmap = {}
    d = start_sunday
    while d <= today:
        ds = d.isoformat()
        count = _day_total(cs, ds)
        if count > 0:
            ratio = count / target
            level = 4 if ratio >= 1 else (3 if ratio >= 0.75 else (2 if ratio >= 0.5 else 1))
        else:
            level = 0
        heatmap[ds] = level
        d += timedelta(days=1)
    heatmap_json = json.dumps(heatmap)
    # Normalize checkins to totals for JS (heatmap/calendar use numbers)
    checkins_json = json.dumps(_flat_checkins(cs))

    started = habit.get("started", "")
    started_display = (
        f"Since {date.fromisoformat(started).strftime('%b %Y')}"
        if started else "No start date"
    )
    habit_name = habit.get("name", "")
    habit_icon = habit.get("icon", "✅")
    freq_lbl = FREQ_LABEL.get(habit.get("freq", "daily"), "Daily")

    # ── Check-in section ─────────────────────────────────────
    if track == "detail":
        # Rich mode: entry log
        cat_options = "".join(f'<option value="{c}">' for c in categories)
        today_entries_html = ""
        if today_entries:
            rows_html = "".join(
                f'<div class="today-entry"><span class="today-entry-label">{e.get("label","—")}</span>'
                f'<span class="today-entry-val">{e.get("value",0):g} {unit}</span></div>'
                for e in today_entries
            )
            total_pct = min(100, round(today_count / target * 100)) if target > 0 else 0
            today_entries_html = f'''
            <div class="today-entries">
              {rows_html}
              <div class="today-total">Total today: {today_count:g} / {target} {unit} ({total_pct}%)</div>
            </div>'''
        clear_btn = (
            f'<form method="POST" action="/habit/{hid}/checkin" style="display:inline">'
            f'<input type="hidden" name="clear" value="1">'
            f'<input type="hidden" name="next" value="/habit/{hid}">'
            f'<button class="btn-clear-rich" type="submit">Clear today</button></form>'
        ) if today_entries else ""
        if categories:
            initial_rows_html = "".join(
                f'<div class="entry-row">'
                f'<input type="text" name="label" value="{c}" list="cats-{hid}" class="entry-label-inp">'
                f'<input type="number" name="value" value="" min="0" step="any" class="entry-val-inp" placeholder="0">'
                f'<span class="entry-unit-lbl">{unit}</span>'
                f'<button type="button" class="entry-del-btn" onclick="this.closest(\'.entry-row\').remove()">×</button>'
                f'</div>'
                for c in categories
            )
        else:
            initial_rows_html = (
                f'<div class="entry-row">'
                f'<input type="text" name="label" placeholder="e.g. {habit_name}" list="cats-{hid}" class="entry-label-inp">'
                f'<input type="number" name="value" value="" min="0" step="any" class="entry-val-inp" placeholder="0">'
                f'<span class="entry-unit-lbl">{unit}</span>'
                f'</div>'
            )
        checkin_section = f'''
        <div class="rich-checkin">
          {today_entries_html}
          <form method="POST" action="/habit/{hid}/checkin" id="richForm">
            <input type="hidden" name="next" value="/habit/{hid}">
            <datalist id="cats-{hid}">{cat_options}</datalist>
            <div class="entry-rows" id="entryRows">
              {initial_rows_html}
            </div>
            <div class="rich-actions" style="margin-top:10px">
              <button type="button" class="btn-add-row" onclick="addEntryRow()">+ Add entry</button>
              <button type="submit" class="btn-save-rich">Save</button>
              {clear_btn}
            </div>
          </form>
        </div>'''
    elif target == 1:
        if not today_done:
            checkin_block = (
                f'<form method="POST" action="/habit/{hid}/checkin" style="display:inline">'
                f'<input type="hidden" name="toggle" value="1">'
                f'<button class="btn-checkin" type="submit">✓ Complete {habit_name} today!</button></form>'
            )
        else:
            checkin_block = '<button class="btn-checkin checked" type="button">✓ Done today!</button>'
        checkin_note = (
            f"Great job completing {habit_name} today! {habit_icon}"
            if today_done else
            f"Not checked in yet today. Press the button when you finish {habit_name}."
        )
        checkin_section = f'''
        <div class="checkin-wrap">
          {checkin_block}
          <div class="checkin-note">{checkin_note}</div>
        </div>'''
    else:
        pct = min(100, round(today_count / target * 100))
        minus_btn = (
            f'<form method="POST" action="/habit/{hid}/checkin" style="display:inline">'
            f'<input type="hidden" name="delta" value="-1">'
            f'<input type="hidden" name="next" value="/habit/{hid}">'
            f'<button class="btn-counter" type="submit">−</button></form>'
        )
        plus_btn = (
            f'<form method="POST" action="/habit/{hid}/checkin" style="display:inline">'
            f'<input type="hidden" name="delta" value="1">'
            f'<input type="hidden" name="next" value="/habit/{hid}">'
            f'<button class="btn-counter" type="submit">＋</button></form>'
        )
        note = f"Goal reached: {target} {unit}! Well done {habit_icon}" if today_done else f"Today: {today_count}/{target} {unit}. {target - today_count} {unit} to go."
        checkin_section = f'''
        <div class="counter-wrap">
          <div>
            <div class="counter-display">
              <span class="counter-num {"done" if today_done else ""}">{today_count}</span>
              <span class="counter-sep">/</span>
              <span class="counter-target">{target}{unit}</span>
            </div>
            <div class="counter-progress">
              <div class="counter-fill" style="width:{pct}%"></div>
            </div>
          </div>
          <div class="counter-btns">{minus_btn}{plus_btn}</div>
          <div class="checkin-note">{note}</div>
        </div>'''

    # ── By Category stats ─────────────────────────────────────
    cat_stats = _category_stats(cs)
    if cat_stats and track == "detail":
        # Build JSON for JS rendering
        import json as _json
        cat_json = _json.dumps(cat_stats)
        by_cat_section = f'''
  <div class="card">
    <div class="section-title">By Activity Label</div>
    <div class="cat-period-row">
      <button class="cat-period-btn active" onclick="showCatPeriod(this,'week')">This week</button>
      <button class="cat-period-btn" onclick="showCatPeriod(this,'month')">This month</button>
      <button class="cat-period-btn" onclick="showCatPeriod(this,'all')">All time</button>
    </div>
    <div class="cat-bars" id="catBars"></div>
  </div>
  <script>
  (function(){{
    const CAT={cat_json};
    const UNIT="{unit}";
    function showCatPeriod(btn,period){{
      document.querySelectorAll('.cat-period-btn').forEach(b=>b.classList.remove('active'));
      btn.classList.add('active');
      renderCat(period);
    }}
    function renderCat(period){{
      const el=document.getElementById('catBars');
      if(!el)return;
      const entries=Object.entries(CAT).sort((a,b)=>b[1][period]-a[1][period]);
      const maxVal=entries.reduce((m,[,v])=>Math.max(m,v[period]),0)||1;
      el.innerHTML=entries.map(([lbl,v])=>{{
        const val=v[period];
        const pct=Math.max(2,Math.round(val/maxVal*100));
        const disp=Number.isInteger(val)?val:val.toFixed(1);
        return `<div class="cat-bar-row">
          <div class="cat-bar-lbl" title="${{lbl}}">${{lbl}}</div>
          <div class="cat-bar-track"><div class="cat-bar-fill" style="width:${{pct}}%"></div></div>
          <div class="cat-bar-val">${{disp}} ${{UNIT}}</div>
        </div>`;
      }}).join('');
    }}
    renderCat('week');
  }})();
  </script>'''
    else:
        by_cat_section = ""

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{habit_icon} {habit_name}</title>
<link rel="stylesheet" href="/static/style.css">
<style>{_CSS}</style>
</head>
<body>
<nav>
  <a href="/habit">← Habits</a>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container">

  <div class="card">
    <div class="header">
      <div class="habit-title">
        <div class="habit-icon-lg">{habit_icon}</div>
        <div>
          <h1>{habit_name}</h1>
          <div class="habit-sub">{started_display} · {freq_lbl} · Goal: {target} {unit}</div>
        </div>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <div class="streak-badge">🔥 {streak} streak</div>
        <button id="editToggle" onclick="var f=document.getElementById('editForm');f.style.display=f.style.display==='none'?'block':'none';this.textContent=f.style.display==='none'?'Edit':'Cancel'" class="btn-cal-nav" style="font-size:13px;width:auto;padding:0 14px">Edit</button>
      </div>
    </div>
    <form id="editForm" method="POST" action="/habit/{hid}/edit" style="display:none;margin-top:20px;padding-top:20px;border-top:1px solid var(--border)">
      <div class="add-form">
        <label>Name<input type="text" name="name" value="{habit_name}" required></label>
        <label>Frequency<select name="freq">
          <option value="daily" {"selected" if habit.get("freq","daily")=="daily" else ""}>Daily</option>
          <option value="weekly" {"selected" if habit.get("freq","daily")=="weekly" else ""}>Weekly</option>
        </select></label>
        <label>Goal<input type="number" name="target" value="{target}" min="1" max="999"></label>
        <label>Unit
        <input type="hidden" name="unit" id="unitHiddenEdit" value="{unit}">
        <select id="unitSelEdit" onchange="unitSelChange(this,'unitHiddenEdit','unitCustomEdit')">
          <option value="times">times</option><option value="cups">cups</option>
          <option value="min">min</option><option value="km">km</option>
          <option value="pages">pages</option><option value="sets">sets</option>
          <option value="hrs">hrs</option><option value="__custom">Custom...</option>
        </select>
        <input type="text" id="unitCustomEdit" placeholder="e.g. reps" style="display:none;width:90px;min-width:0;margin-top:4px" oninput="document.getElementById('unitHiddenEdit').value=this.value">
        <span class="field-hint">type your own</span>
        </label>
        <label style="width:100%">Tracking mode<select name="track">
          <option value="count" {"selected" if track=="count" else ""}>Simple (count / done)</option>
          <option value="detail" {"selected" if track=="detail" else ""}>Detailed (log entries per activity)</option>
        </select></label>
        <label style="width:100%">Activity Labels
        <span style="font-size:11px;color:var(--text-muted);margin-left:6px">(press Enter or , to add)</span>
        <input type="hidden" name="categories" id="catsHiddenEdit" value="{", ".join(categories)}">
        <div class="tag-pill-wrap" id="catPillsEdit"><input type="text" id="catInpEdit" class="tag-pill-inp" placeholder="e.g. Running, Walking..."></div>
        </label>
        <button type="submit">Save</button>
      </div>
    </form>
    <div style="height:20px"></div>
    <div class="stats">
      <div class="stat"><span class="stat-value streak-c">{streak}</span><span class="stat-label">Current streak</span></div>
      <div class="stat-divider"></div>
      <div class="stat"><span class="stat-value accent">{longest}</span><span class="stat-label">Longest streak</span></div>
      <div class="stat-divider"></div>
      <div class="stat"><span class="stat-value">{total}</span><span class="stat-label">Total days</span></div>
      <div class="stat-divider"></div>
      <div class="stat"><span class="stat-value">{rate_12w}%</span><span class="stat-label">Rate (12w)</span></div>
    </div>
    <div class="progress-wrap">
      <div class="progress-label"><span>12-week rate</span><span>{done_12w} / {days_12w} days</span></div>
      <div class="progress-bar"><div class="progress-fill" style="width:{rate_12w}%"></div></div>
    </div>
  </div>

  <div class="card">
    <div class="heatmap-header">
      <span class="heatmap-title">Activity — Last 12 weeks</span>
      <div class="legend">
        <span>0</span>
        <div class="legend-cell" style="background:var(--cell-0);border:1px solid var(--border)"></div>
        <div class="legend-cell" style="background:#e0f2fe"></div>
        <div class="legend-cell" style="background:#bae6fd"></div>
        <div class="legend-cell" style="background:var(--cell-4)"></div>
        <span>Goal</span>
      </div>
    </div>
    <div class="heatmap-wrap">
      <div class="heatmap-grid-wrap">
        <div class="dow-labels">
          <div class="dow-label">Su</div><div class="dow-label">Mo</div>
          <div class="dow-label">Tu</div><div class="dow-label">We</div>
          <div class="dow-label">Th</div><div class="dow-label">Fr</div>
          <div class="dow-label">Sa</div>
        </div>
        <div class="weeks-wrap">
          <div class="month-labels" id="monthLabels"></div>
          <div class="weeks" id="heatmapGrid"></div>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="section-title">Today's Check-in</div>
    {checkin_section}
  </div>

  <div class="card">
    <div class="tab-row">
      <button class="tab-btn active" data-tab="tabCalendar">📅 Calendar</button>
      <button class="tab-btn" data-tab="tabTrend">📈 Trend</button>
    </div>

    <div id="tabCalendar" class="tab-panel">
      <div class="cal-header">
        <button id="calPrev" class="btn-cal-nav">‹</button>
        <span class="cal-title" id="calTitle"></span>
        <button id="calNext" class="btn-cal-nav">›</button>
      </div>
      <div id="monthCalendar"></div>
    </div>

    <div id="tabTrend" class="tab-panel" style="display:none">
      <div class="section-title" style="margin-bottom:8px">Weekly Trend (12 weeks)</div>
      <div style="position:relative">
        <div class="trend-zero"></div>
        <div class="trend-wrap" id="trendChart"></div>
      </div>
    </div>
  </div>

  {by_cat_section}

</div>
<div class="tooltip" id="tooltip"></div>
<script>
const DATA = {checkins_json};
const HID = {hid};
const TARGET = {target};
const TRACK = "{track}";
{_HEATMAP_JS}
// Tag pill widget
function initTagPills(pillsId, textId, hiddenId) {{
  var pillsEl = document.getElementById(pillsId);
  var textEl = document.getElementById(textId);
  var hiddenEl = document.getElementById(hiddenId);
  if (!pillsEl || !textEl || !hiddenEl) return;
  function getTags() {{
    return hiddenEl.value ? hiddenEl.value.split(',').map(function(s){{return s.trim();}}).filter(Boolean) : [];
  }}
  function setTags(tags) {{ hiddenEl.value = tags.join(','); render(); }}
  function render() {{
    var tags = getTags();
    while (pillsEl.firstChild) pillsEl.removeChild(pillsEl.firstChild);
    tags.forEach(function(t, i) {{
      var pill = document.createElement('span'); pill.className = 'tag-pill';
      var txt = document.createElement('span'); txt.textContent = t;
      var del = document.createElement('button');
      del.type = 'button'; del.className = 'tag-pill-del'; del.textContent = '×';
      (function(idx) {{
        del.addEventListener('click', function() {{ var a=getTags(); a.splice(idx,1); setTags(a); }});
      }})(i);
      pill.appendChild(txt); pill.appendChild(del); pillsEl.appendChild(pill);
    }});
    pillsEl.appendChild(textEl);
  }}
  textEl.addEventListener('keydown', function(e) {{
    if (e.key === 'Enter' || e.key === ',') {{
      e.preventDefault(); e.stopPropagation();
      var val = textEl.value.trim().replace(/,$/, '');
      if (val) {{ var t=getTags(); if(t.indexOf(val)===-1) t.push(val); setTags(t); textEl.value=''; }}
    }} else if (e.key === 'Backspace' && textEl.value === '') {{
      var t=getTags(); if(t.length>0){{ t.pop(); setTags(t); }}
    }}
  }});
  pillsEl.addEventListener('click', function() {{ textEl.focus(); }});
  render();
}}
function unitSelChange(sel, hiddenId, customId) {{
  var hidden = document.getElementById(hiddenId);
  var custom = document.getElementById(customId);
  if (!hidden || !custom) return;
  if (sel.value === '__custom') {{ custom.style.display='inline-block'; custom.focus(); }}
  else {{ custom.style.display='none'; hidden.value=sel.value; }}
}}
function initUnitSel(selId, hiddenId, customId) {{
  var presets=['times','cups','min','km','pages','sets','hrs'];
  var hidden=document.getElementById(hiddenId), sel=document.getElementById(selId), custom=document.getElementById(customId);
  if(!hidden||!sel||!custom) return;
  var val=hidden.value;
  if(presets.indexOf(val)>=0){{ sel.value=val; }}
  else{{ sel.value='__custom'; custom.style.display='inline-block'; custom.value=val; }}
}}
initTagPills('catPillsEdit','catInpEdit','catsHiddenEdit');
initUnitSel('unitSelEdit','unitHiddenEdit','unitCustomEdit');
// Rich check-in: add entry row
function addEntryRow(){{
  const rows = document.getElementById('entryRows');
  if(!rows)return;
  const first = rows.querySelector('.entry-row');
  if(!first)return;
  const clone = first.cloneNode(true);
  clone.querySelector('.entry-label-inp').value='';
  clone.querySelector('.entry-val-inp').value='';
  // add delete button if not present
  if(!clone.querySelector('.entry-del-btn')){{
    const del=document.createElement('button');
    del.type='button'; del.className='entry-del-btn'; del.textContent='×';
    del.onclick=function(){{clone.remove();}};
    clone.appendChild(del);
  }}
  rows.appendChild(clone);
  clone.querySelector('.entry-label-inp').focus();
}}
</script>
</body>
</html>'''
