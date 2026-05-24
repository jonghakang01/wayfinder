import json, os
from datetime import date, timedelta

DATA_ROOT = os.path.expanduser("~/.appdata")

META = {
    "name": "Habit Tracker",
    "path": "/habit",
    "icon": "🏃",
    "description": "습관 추적기",
}

FREQ_LABEL = {"daily": "매일", "weekly": "주간"}


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


def compute_stats(checkins):
    today = date.today()
    cs = set(checkins)

    streak, d = 0, today
    while d.isoformat() in cs:
        streak += 1
        d -= timedelta(days=1)

    longest, cur, prev_d = 0, 0, None
    for ds in sorted(cs):
        d = date.fromisoformat(ds)
        cur = cur + 1 if prev_d and (d - prev_d).days == 1 else 1
        longest = max(longest, cur)
        prev_d = d

    total = len(cs)
    start_12w = today - timedelta(weeks=12)
    days_12w = (today - start_12w).days + 1
    done_12w = sum(1 for c in cs if date.fromisoformat(c) >= start_12w)
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
            if name:
                habits.append({
                    "id": next_id(habits),
                    "name": name,
                    "icon": "✅",
                    "freq": freq,
                    "started": date.today().isoformat(),
                    "checkins": [],
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
                    today_str = date.today().isoformat()
                    if today_str not in habit["checkins"]:
                        habit["checkins"].append(today_str)
                        save(habits, user)
                    next_url = body.get("next", ["/habit"])[0]
                    return ("redirect", next_url)
                elif action == "delete":
                    save([h for h in habits if h["id"] != hid], user)
            return ("redirect", "/habit")

    if len(parts) >= 3 and parts[2].isdigit():
        habit = find_habit(habits, int(parts[2]))
        return ("html", render_detail(habit, user)) if habit else ("redirect", "/habit")

    return ("html", render_list(habits, user))


_CSS = """
:root {
  --bg:#0d1117; --surface:#161b22; --border:#30363d;
  --text:#e6edf3; --text-muted:#8b949e;
  --accent:#58a6ff; --streak:#f78166;
  --cell-0:#161b22; --cell-2:#006d32; --cell-4:#39d353;
  --radius:8px; --gap:3px; --cell:14px;
}
*,*::before,*::after{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",sans-serif;display:flex;justify-content:center;padding:60px 16px;min-height:100vh}
.container{width:100%;max-width:720px;display:flex;flex-direction:column;gap:24px}
.card{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);padding:24px}
nav{position:fixed;top:0;left:0;right:0;padding:10px 20px;font-size:13px;background:rgba(13,17,23,.9);backdrop-filter:blur(8px);border-bottom:1px solid var(--border);display:flex;align-items:center;justify-content:space-between;z-index:10}
nav a{color:var(--accent);text-decoration:none}
.nav-user{color:var(--text-muted);font-size:12px}
h2{font-size:18px;font-weight:600;margin-bottom:16px}
.add-form{display:flex;gap:10px;flex-wrap:wrap}
.add-form input[type=text]{flex:1;min-width:160px;padding:9px 12px;background:#0d1117;border:1px solid var(--border);border-radius:var(--radius);color:var(--text);font-size:14px}
.add-form select{padding:9px 12px;background:#0d1117;border:1px solid var(--border);border-radius:var(--radius);color:var(--text);font-size:14px}
.add-form button{padding:9px 18px;background:var(--accent);color:#000;border:none;border-radius:var(--radius);font-size:14px;font-weight:600;cursor:pointer}
.habit-row{display:flex;align-items:center;gap:14px;padding:14px 0;border-bottom:1px solid var(--border)}
.habit-row:last-child{border-bottom:none}
.habit-icon-sm{font-size:22px;width:36px;text-align:center;flex-shrink:0}
.habit-info{flex:1}
.habit-name{font-size:15px;font-weight:600}
.habit-meta{font-size:12px;color:var(--text-muted);margin-top:2px}
.habit-actions{display:flex;gap:8px;align-items:center}
.tag-freq{font-size:11px;padding:2px 8px;border-radius:12px;background:#1f2937;color:var(--text-muted)}
.streak-sm{font-size:13px;color:var(--streak);font-weight:600}
.btn-sm{padding:6px 14px;border:none;border-radius:6px;font-size:13px;font-weight:600;cursor:pointer}
.btn-detail{background:var(--border);color:var(--text);text-decoration:none;padding:6px 14px;border-radius:6px;font-size:13px;font-weight:600}
.btn-checkin-sm{background:linear-gradient(135deg,#238636,#2ea043);color:#fff}
.btn-checkin-sm.checked{background:#1b4332;cursor:default}
.btn-del-sm{background:transparent;color:#8b949e;font-size:12px;border:1px solid var(--border)}
.header{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:12px}
.habit-title{display:flex;align-items:center;gap:10px}
.habit-icon-lg{width:38px;height:38px;background:linear-gradient(135deg,#1f6feb,#388bfd);border-radius:10px;display:flex;align-items:center;justify-content:center;font-size:18px}
h1{font-size:20px;font-weight:600}
.habit-sub{font-size:13px;color:var(--text-muted);margin-top:2px}
.streak-badge{display:inline-flex;align-items:center;gap:6px;background:rgba(247,129,102,.12);border:1px solid rgba(247,129,102,.35);color:var(--streak);border-radius:20px;padding:6px 14px;font-size:14px;font-weight:600}
.stats{display:flex;gap:16px;flex-wrap:wrap}
.stat{display:flex;flex-direction:column;gap:4px}
.stat-value{font-size:28px;font-weight:700;line-height:1}
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
.day-cell:hover{outline:1px solid rgba(255,255,255,.4);z-index:1}
.day-cell[data-level="0"]{background:var(--cell-0);border:1px solid rgba(255,255,255,.05)}
.day-cell[data-level="4"]{background:var(--cell-4)}
.day-cell.today{outline:2px solid var(--accent);outline-offset:1px}
.tooltip{position:fixed;background:#1c2128;border:1px solid var(--border);border-radius:6px;padding:6px 10px;font-size:12px;color:var(--text);pointer-events:none;opacity:0;transition:opacity .15s;z-index:100;white-space:nowrap}
.tooltip.show{opacity:1}
.checkin-wrap{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
.btn-checkin{display:inline-flex;align-items:center;gap:8px;padding:12px 28px;background:linear-gradient(135deg,#238636,#2ea043);color:#fff;font-size:15px;font-weight:600;border:none;border-radius:var(--radius);cursor:pointer;transition:filter .15s,transform .1s;user-select:none}
.btn-checkin:hover{filter:brightness(1.12);transform:translateY(-1px)}
.btn-checkin.checked{background:linear-gradient(135deg,#1b4332,#2d6a4f);cursor:default}
.checkin-note{font-size:13px;color:var(--text-muted)}
.activity-list{display:flex;flex-direction:column;gap:10px}
.activity-item{display:flex;align-items:center;gap:12px;font-size:13px}
.activity-dot{width:8px;height:8px;border-radius:50%;flex-shrink:0}
.activity-dot.done{background:var(--cell-4)}
.activity-dot.miss{background:var(--border)}
.activity-date{color:var(--text-muted);width:88px;flex-shrink:0}
.activity-status{font-weight:500}
.activity-status.done{color:var(--cell-4)}
.activity-status.miss{color:var(--text-muted)}
.section-title{font-size:13px;font-weight:600;color:var(--text-muted);text-transform:uppercase;letter-spacing:.5px;margin-bottom:16px}
.progress-wrap{margin-top:20px}
.progress-label{display:flex;justify-content:space-between;font-size:12px;color:var(--text-muted);margin-bottom:6px}
.progress-bar{height:6px;background:var(--border);border-radius:9999px;overflow:hidden}
.progress-fill{height:100%;border-radius:9999px;background:linear-gradient(90deg,var(--cell-2),var(--cell-4));transition:width .6s ease}
.empty{color:var(--text-muted);font-size:14px;text-align:center;padding:20px 0}
"""

_HEATMAP_JS = """
const MONTH_KO=['1월','2월','3월','4월','5월','6월','7월','8월','9월','10월','11월','12월'];
const DAY_KO=['일','월','화','수','목','금','토'];
const WEEKS=12;
const today=new Date();today.setHours(0,0,0,0);
const todayKey=today.toISOString().slice(0,10);
function addDays(d,n){const r=new Date(d);r.setDate(r.getDate()+n);return r;}
const startSunday=addDays(today,-(today.getDay()+(WEEKS-1)*7));
const grid=document.getElementById('heatmapGrid');
const monthLabels=document.getElementById('monthLabels');
const tooltip=document.getElementById('tooltip');
let lastMonth=-1;
for(let w=0;w<WEEKS;w++){
  const col=document.createElement('div');col.className='week-col';
  const ws=addDays(startSunday,w*7);const m=ws.getMonth();
  const ml=document.createElement('div');ml.className='month-label';
  ml.textContent=m!==lastMonth?MONTH_KO[m]:'';monthLabels.appendChild(ml);lastMonth=m;
  for(let d=0;d<7;d++){
    const dt=addDays(startSunday,w*7+d);const key=dt.toISOString().slice(0,10);
    const cell=document.createElement('div');cell.className='day-cell';
    if(dt>today){cell.dataset.level=0;cell.style.opacity='0.15';}
    else{cell.dataset.level=DATA[key]??0;}
    if(key===todayKey)cell.classList.add('today');
    cell.dataset.date=key;
    cell.dataset.done=(DATA[key]??0)>0?'✓ 완료':(dt>today?'—':'미완료');
    cell.addEventListener('mouseenter',e=>{
      const d2=new Date(key+'T00:00:00');
      tooltip.textContent=`${d2.getMonth()+1}월 ${d2.getDate()}일 (${DAY_KO[d2.getDay()]}) · ${cell.dataset.done}`;
      tooltip.classList.add('show');
      tooltip.style.left=(e.clientX+14)+'px';tooltip.style.top=(e.clientY-28)+'px';
    });
    cell.addEventListener('mousemove',e=>{tooltip.style.left=(e.clientX+14)+'px';tooltip.style.top=(e.clientY-28)+'px';});
    cell.addEventListener('mouseleave',()=>tooltip.classList.remove('show'));
    col.appendChild(cell);
  }
  grid.appendChild(col);
}
const list=document.getElementById('activityList');
for(let i=6;i>=0;i--){
  const d=addDays(today,-i);const key=d.toISOString().slice(0,10);
  const done=(DATA[key]??0)>0;
  const label=i===0?'오늘':i===1?'어제':`${d.getMonth()+1}월 ${d.getDate()}일 (${DAY_KO[d.getDay()]})`;
  const item=document.createElement('div');item.className='activity-item';
  item.innerHTML=`
    <div class="activity-dot ${done?'done':'miss'}"></div>
    <span class="activity-date">${label}</span>
    <span class="activity-status ${done?'done':'miss'}">${done?'✓ 완료':'— 미완료'}</span>`;
  list.appendChild(item);
}
"""


def render_list(habits, user, readonly=False):
    today_str = date.today().isoformat()
    rows = ""
    for h in habits:
        streak, *_ = compute_stats(h.get("checkins", []))
        checked = today_str in h.get("checkins", [])
        freq_lbl = FREQ_LABEL.get(h.get("freq", "daily"), "매일")
        started = h.get("started", "")[:7]

        if readonly:
            checkin_btn = (
                f'<span class="btn-sm btn-checkin-sm checked">{"✓ 완료" if checked else "미완료"}</span>'
            )
            del_btn = ""
        else:
            checkin_btn = (
                f'<form method="POST" action="/habit/{h["id"]}/checkin" style="display:inline">'
                f'<button class="btn-sm btn-checkin-sm{"  checked" if checked else ""}" '
                f'{"type=button" if checked else "type=submit"}>{"✓ 완료" if checked else "체크인"}</button></form>'
            )
            del_btn = (
                f'<form method="POST" action="/habit/{h["id"]}/delete" style="display:inline"'
                f' onsubmit="return confirm(\'{h["name"]} 습관을 삭제할까요?\')">'
                f'<button class="btn-sm btn-del-sm" type="submit">삭제</button></form>'
            )
        rows += f'''
        <div class="habit-row">
          <div class="habit-icon-sm">{h.get("icon", "✅")}</div>
          <div class="habit-info">
            <div class="habit-name">{h["name"]}</div>
            <div class="habit-meta"><span class="tag-freq">{freq_lbl}</span>  {started} 시작</div>
          </div>
          <div class="habit-actions">
            <span class="streak-sm">🔥 {streak}일</span>
            {checkin_btn}
            <a class="btn-detail" href="/habit/{h["id"]}">상세</a>
            {del_btn}
          </div>
        </div>'''

    if not habits:
        rows = '<div class="empty">등록된 습관이 없습니다. 첫 습관을 추가해보세요!</div>'

    add_card = "" if readonly else (
        '<div class="card"><h2>새 습관 추가</h2>'
        '<form class="add-form" method="POST" action="/habit/add">'
        '<input type="text" name="name" placeholder="습관 이름..." required autofocus>'
        '<select name="freq"><option value="daily">매일</option><option value="weekly">주간</option></select>'
        '<button type="submit">추가</button>'
        '</form></div>'
    )

    return f'''<!DOCTYPE html>
<html lang="ko">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🏃 Habit Tracker</title>
<link rel="stylesheet" href="/static/style.css">
<style>{_CSS}</style>
</head>
<body>
<nav>
  <a href="/">← Wayfinder</a>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">로그아웃</a></span>
</nav>
<div class="container">

  {add_card}

  <div class="card">
    <h2>{"🏃 " + user + "님의 " if readonly else ""}습관 목록</h2>
    {rows}
  </div>

</div>
</body>
</html>'''


def render_detail(habit, user):
    today = date.today()
    cs = set(habit.get("checkins", []))
    today_checked = today.isoformat() in cs
    hid = habit["id"]

    streak, longest, total, rate_12w, done_12w, days_12w = compute_stats(habit.get("checkins", []))

    WEEKS = 12
    days_since_sun = today.weekday() + 1 if today.weekday() != 6 else 0
    start_sunday = today - timedelta(days=days_since_sun + (WEEKS - 1) * 7)
    heatmap = {}
    d = start_sunday
    while d <= today:
        ds = d.isoformat()
        heatmap[ds] = 4 if ds in cs else 0
        d += timedelta(days=1)
    heatmap_json = json.dumps(heatmap)

    started = habit.get("started", "")
    started_display = (
        f"{date.fromisoformat(started).year}년 {date.fromisoformat(started).month}월부터"
        if started else "시작일 미설정"
    )
    habit_name = habit.get("name", "")
    habit_icon = habit.get("icon", "✅")
    freq_lbl = FREQ_LABEL.get(habit.get("freq", "daily"), "매일")

    checkin_block = (
        f'<form method="POST" action="/habit/{hid}/checkin" style="display:inline">'
        f'<button class="btn-checkin" type="submit">✓ 오늘 {habit_name} 완료!</button></form>'
        if not today_checked else
        '<button class="btn-checkin checked" type="button">✓ 오늘 완료!</button>'
    )
    checkin_note = (
        f"오늘 {habit_name}을 완료했어요. 내일도 화이팅! {habit_icon}"
        if today_checked else
        f"오늘 아직 체크인하지 않았어요. {habit_name}을 마쳤다면 버튼을 누르세요."
    )

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
  <a href="/habit">← 목록</a>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">로그아웃</a></span>
</nav>
<div class="container">

  <div class="card">
    <div class="header">
      <div class="habit-title">
        <div class="habit-icon-lg">{habit_icon}</div>
        <div>
          <h1>{habit_name}</h1>
          <div class="habit-sub">{started_display} · {freq_lbl}</div>
        </div>
      </div>
      <div class="streak-badge">🔥 {streak}일 연속</div>
    </div>
    <div style="height:20px"></div>
    <div class="stats">
      <div class="stat"><span class="stat-value streak-c">{streak}</span><span class="stat-label">현재 스트릭</span></div>
      <div class="stat-divider"></div>
      <div class="stat"><span class="stat-value accent">{longest}</span><span class="stat-label">최장 스트릭</span></div>
      <div class="stat-divider"></div>
      <div class="stat"><span class="stat-value">{total}</span><span class="stat-label">총 달성일</span></div>
      <div class="stat-divider"></div>
      <div class="stat"><span class="stat-value">{rate_12w}%</span><span class="stat-label">달성률 (12주)</span></div>
    </div>
    <div class="progress-wrap">
      <div class="progress-label"><span>12주 달성률</span><span>{done_12w} / {days_12w}일</span></div>
      <div class="progress-bar"><div class="progress-fill" style="width:{rate_12w}%"></div></div>
    </div>
  </div>

  <div class="card">
    <div class="heatmap-header">
      <span class="heatmap-title">Activity — 최근 12주</span>
      <div class="legend">
        <span>적음</span>
        <div class="legend-cell" style="background:var(--cell-0);border:1px solid rgba(255,255,255,.08)"></div>
        <div class="legend-cell" style="background:var(--cell-2)"></div>
        <div class="legend-cell" style="background:var(--cell-4)"></div>
        <span>많음</span>
      </div>
    </div>
    <div class="heatmap-wrap">
      <div class="heatmap-grid-wrap">
        <div class="dow-labels">
          <div class="dow-label">일</div><div class="dow-label">월</div>
          <div class="dow-label">화</div><div class="dow-label">수</div>
          <div class="dow-label">목</div><div class="dow-label">금</div>
          <div class="dow-label">토</div>
        </div>
        <div class="weeks-wrap">
          <div class="month-labels" id="monthLabels"></div>
          <div class="weeks" id="heatmapGrid"></div>
        </div>
      </div>
    </div>
  </div>

  <div class="card">
    <div class="section-title">오늘 체크인</div>
    <div class="checkin-wrap">
      {checkin_block}
      <div class="checkin-note">{checkin_note}</div>
    </div>
  </div>

  <div class="card">
    <div class="section-title">최근 7일</div>
    <div class="activity-list" id="activityList"></div>
  </div>

</div>
<div class="tooltip" id="tooltip"></div>
<script>
const DATA = {heatmap_json};
{_HEATMAP_JS}
</script>
</body>
</html>'''
