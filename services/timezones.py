"""Time Zones — your own day, with other people's hours laid over it.

The one thing a server cannot know here is which time zone you are in: the
machine's zone is the machine's, and a phone that travels changes its answer
without telling anybody. So the split is deliberate — the server owns the list
of zones you care about, and the browser owns every clock on the page. That
also means the strip is correct the moment you cross a border, with no setting
to remember to change.
"""
import json
import os

from services._paths import DATA_ROOT

META = {
    "name": "Time Zones",
    "path": "/timezones",
    "icon": "🌏",
    "description": "Your 24 hours, with other cities lined up against it",
    "hidden": False,
}

# A picker of 400 IANA names is a worse tool than a short list of the places
# people actually schedule against. Grouped the way the eye scans a world map.
ZONES = [
    ("Americas", [
        ("America/Los_Angeles", "Los Angeles"),
        ("America/Denver", "Denver"),
        ("America/Chicago", "Chicago"),
        ("America/New_York", "New York"),
        ("America/Toronto", "Toronto"),
        ("America/Mexico_City", "Mexico City"),
        ("America/Bogota", "Bogotá"),
        ("America/Sao_Paulo", "São Paulo"),
        ("America/Argentina/Buenos_Aires", "Buenos Aires"),
    ]),
    ("Europe & Africa", [
        ("Europe/London", "London"),
        ("Europe/Dublin", "Dublin"),
        ("Europe/Lisbon", "Lisbon"),
        ("Europe/Madrid", "Madrid"),
        ("Europe/Paris", "Paris"),
        ("Europe/Berlin", "Berlin"),
        ("Europe/Amsterdam", "Amsterdam"),
        ("Europe/Zurich", "Zurich"),
        ("Europe/Stockholm", "Stockholm"),
        ("Europe/Warsaw", "Warsaw"),
        ("Europe/Athens", "Athens"),
        ("Europe/Istanbul", "Istanbul"),
        ("Europe/Moscow", "Moscow"),
        ("Africa/Lagos", "Lagos"),
        ("Africa/Cairo", "Cairo"),
        ("Africa/Nairobi", "Nairobi"),
        ("Africa/Johannesburg", "Johannesburg"),
    ]),
    ("Middle East & Asia", [
        ("Asia/Dubai", "Dubai"),
        ("Asia/Riyadh", "Riyadh"),
        ("Asia/Karachi", "Karachi"),
        ("Asia/Kolkata", "Mumbai / Delhi"),
        ("Asia/Dhaka", "Dhaka"),
        ("Asia/Bangkok", "Bangkok"),
        ("Asia/Jakarta", "Jakarta"),
        ("Asia/Singapore", "Singapore"),
        ("Asia/Kuala_Lumpur", "Kuala Lumpur"),
        ("Asia/Manila", "Manila"),
        ("Asia/Ho_Chi_Minh", "Ho Chi Minh City"),
        ("Asia/Hong_Kong", "Hong Kong"),
        ("Asia/Shanghai", "Shanghai"),
        ("Asia/Taipei", "Taipei"),
        ("Asia/Seoul", "Seoul"),
        ("Asia/Tokyo", "Tokyo"),
    ]),
    ("Oceania", [
        ("Australia/Perth", "Perth"),
        ("Australia/Brisbane", "Brisbane"),
        ("Australia/Sydney", "Sydney"),
        ("Pacific/Auckland", "Auckland"),
        ("Pacific/Honolulu", "Honolulu"),
    ]),
    ("Reference", [
        ("UTC", "UTC"),
    ]),
]

VALID = {tz for _, group in ZONES for tz, _ in group}
LABELS = {tz: label for _, group in ZONES for tz, label in group}

# Enough to be useful on the first visit, few enough to still read as a choice.
DEFAULT_ZONES = ["America/New_York", "Europe/London", "Asia/Seoul"]

MAX_ZONES = 8


def _file(user):
    d = os.path.join(DATA_ROOT, user or "guest")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, "timezones.json")


def load(user):
    """The saved zones, always a clean list of names this build still knows.

    A zone dropped from ZONES between releases would otherwise render a row the
    browser cannot resolve, so unknown names are filtered rather than trusted.
    """
    try:
        with open(_file(user)) as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return list(DEFAULT_ZONES)
    zones = raw.get("zones") if isinstance(raw, dict) else raw
    if not isinstance(zones, list):
        return list(DEFAULT_ZONES)
    out = []
    for z in zones:
        if isinstance(z, str) and z in VALID and z not in out:
            out.append(z)
    return out


def save(user, zones):
    with open(_file(user), "w") as f:
        json.dump({"zones": zones}, f, ensure_ascii=False, indent=2)


def add(user, tz):
    zones = load(user)
    if tz in VALID and tz not in zones and len(zones) < MAX_ZONES:
        zones.append(tz)
        save(user, zones)
    return zones


def remove(user, tz):
    zones = [z for z in load(user) if z != tz]
    save(user, zones)
    return zones


def _first(body, key):
    v = (body or {}).get(key, "")
    if isinstance(v, list):
        v = v[0] if v else ""
    return (v or "").strip()


# --- rendering ----------------------------------------------------------------

STYLE = """
.tz-wrap{max-width:1100px;margin:0 auto;padding:18px 16px 90px}
.tz-head{display:flex;align-items:flex-end;justify-content:space-between;
  gap:16px;flex-wrap:wrap;margin-bottom:18px}
.tz-now{font-size:2.6rem;font-weight:var(--fw-extrabold);color:var(--text);
  line-height:1;letter-spacing:-.02em;font-variant-numeric:tabular-nums}
.tz-now-meta{margin-top:6px;color:var(--text-muted);font-size:var(--text-sm);
  font-weight:var(--fw-semibold)}
.tz-add{display:flex;gap:8px;align-items:center}
.tz-select{min-height:40px;padding:0 12px;background:var(--surface);
  border:1px solid var(--border-bright);border-radius:var(--radius-md);
  color:var(--text);font-size:var(--text-sm);font-family:inherit;max-width:210px}
.tz-select:focus{outline:none;border-color:var(--accent);
  box-shadow:0 0 0 3px var(--accent-glow)}

/* The strip is the whole app, so it gets the horizontal scroll rather than the
   page: 24 columns never fit a phone, and a body that slides sideways is the
   one thing the guideline will not have. */
.tz-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch;
  border:1px solid var(--border);border-radius:var(--radius-lg);
  background:var(--surface)}
.tz-grid{min-width:760px}
.tz-row{display:flex;align-items:stretch;background:var(--surface);
  border-bottom:1px solid var(--border)}
.tz-row:last-child{border-bottom:none}
/* Your own row is the one everything else is measured against, so it is lifted
   off the others rather than left to be found by the 🏠. */
.tz-row--home{background:var(--surface-2)}

/* Sticky so the city stays readable while the hours scroll under your thumb. */
.tz-label{position:sticky;left:0;z-index:2;flex:0 0 168px;padding:10px 14px;
  background:inherit;border-right:1px solid var(--border);min-width:0}
.tz-city{font-size:var(--text-sm);font-weight:var(--fw-bold);color:var(--text);
  white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tz-sub{margin-top:3px;font-size:var(--text-xs);color:var(--text-muted);
  font-weight:var(--fw-semibold);font-variant-numeric:tabular-nums}
.tz-drop{margin-left:6px}

.tz-hours{display:flex;flex:1}
.tz-cell{flex:1 0 24px;display:flex;flex-direction:column;align-items:center;
  justify-content:center;padding:8px 0;font-size:var(--text-xs);
  font-weight:var(--fw-bold);color:var(--text-muted);
  font-variant-numeric:tabular-nums;border-left:1px solid var(--border)}
.tz-cell--work{background:var(--accent-glow);color:var(--text)}
.tz-cell--sleep{color:var(--text-dim);opacity:.55}
.tz-cell--now{box-shadow:inset 0 0 0 2px var(--accent);border-radius:var(--radius-sm)}
.tz-daymark{font-size:9px;font-weight:var(--fw-bold);color:var(--warn);
  letter-spacing:.04em;margin-top:2px;height:11px}

.tz-legend{display:flex;gap:16px;flex-wrap:wrap;margin-top:12px;
  font-size:var(--text-xs);color:var(--text-muted);font-weight:var(--fw-semibold)}
.tz-key{display:inline-flex;align-items:center;gap:6px}
.tz-swatch{width:14px;height:14px;border-radius:4px;border:1px solid var(--border-bright)}
.tz-empty{text-align:center;color:var(--text-muted);padding:38px 16px;
  font-size:var(--text-md)}

@media (max-width:768px){
  .tz-now{font-size:2.1rem}
  .tz-head{align-items:stretch}
  .tz-add{width:100%}
  .tz-select{flex:1;max-width:none;min-height:44px}
  .tz-label{flex:0 0 132px;padding:10px}
  .tz-grid{min-width:680px}
}
"""

SCRIPT = """
(function(){
  var HOME = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC';
  var homeCell = document.getElementById('tzHomeName');
  if (homeCell) homeCell.textContent = HOME.split('/').pop().replace(/_/g,' ');
  var homeTz = document.getElementById('tzHomeZone');
  if (homeTz) homeTz.textContent = HOME;

  // Wall-clock parts for an instant in a zone. Intl is the only thing in the
  // browser that knows a zone's rules, so every number on this page comes
  // through here rather than from an offset we worked out ourselves.
  function parts(date, tz){
    var f = new Intl.DateTimeFormat('en-CA', {timeZone: tz, hour12: false,
      year:'numeric', month:'2-digit', day:'2-digit',
      hour:'2-digit', minute:'2-digit'});
    var o = {};
    f.formatToParts(date).forEach(function(p){ o[p.type] = p.value; });
    // 'en-CA' renders midnight as 24 in some engines; normalise it to 0.
    var h = parseInt(o.hour, 10) % 24;
    return {ymd: o.year+'-'+o.month+'-'+o.day, hour: h, minute: o.minute};
  }

  function offsetLabel(date, tz){
    var a = parts(date, HOME), b = parts(date, tz);
    var mins = (Date.parse(b.ymd+'T00:00:00Z') - Date.parse(a.ymd+'T00:00:00Z')) / 60000
             + (b.hour - a.hour) * 60 + (parseInt(b.minute,10) - parseInt(a.minute,10));
    if (mins === 0) return 'same time';
    var sign = mins > 0 ? '+' : '−', m = Math.abs(mins);
    var h = Math.floor(m / 60), r = m % 60;
    return sign + h + (r ? ':' + String(r).padStart(2,'0') : '') + 'h';
  }

  function paint(){
    var now = new Date();
    var home = parts(now, HOME);
    var clock = document.getElementById('tzNow');
    if (clock) clock.textContent = String(home.hour).padStart(2,'0') + ':' + home.minute;
    var meta = document.getElementById('tzNowMeta');
    if (meta) meta.textContent = new Intl.DateTimeFormat('en-US',
      {timeZone: HOME, weekday:'long', month:'long', day:'numeric'}).format(now);

    // Midnight of the home day, so column 0 is the start of *your* today and
    // every other row is read against it. That is the whole point of the strip.
    var base = new Date(now.getTime() - home.hour*3600000
                        - parseInt(home.minute,10)*60000);

    document.querySelectorAll('.tz-row').forEach(function(row){
      var tz = row.dataset.tz === '__home__' ? HOME : row.dataset.tz;
      var hours = row.querySelector('.tz-hours');
      if (!hours) return;
      hours.innerHTML = '';
      var thisDay = null;
      for (var i = 0; i < 24; i++){
        var at = new Date(base.getTime() + i*3600000);
        var p = parts(at, tz);
        var cell = document.createElement('div');
        cell.className = 'tz-cell'
          + (p.hour >= 9 && p.hour < 18 ? ' tz-cell--work' : '')
          + (p.hour < 7 || p.hour >= 22 ? ' tz-cell--sleep' : '')
          + (i === home.hour ? ' tz-cell--now' : '');
        cell.textContent = String(p.hour).padStart(2,'0');
        // A date change is the thing people actually get wrong, so it is marked
        // on the column where it happens rather than left to be inferred.
        var mark = document.createElement('div');
        mark.className = 'tz-daymark';
        if (thisDay !== null && p.ymd !== thisDay){
          mark.textContent = p.ymd > thisDay ? 'next' : 'prev';
        }
        thisDay = p.ymd;
        cell.appendChild(mark);
        hours.appendChild(cell);
      }
      var sub = row.querySelector('.tz-sub');
      if (sub){
        var p0 = parts(now, tz);
        sub.textContent = String(p0.hour).padStart(2,'0') + ':' + p0.minute
          + (row.dataset.tz === '__home__' ? '' : ' · ' + offsetLabel(now, tz));
      }
    });
  }

  paint();
  setInterval(paint, 30000);
})();
"""


def render(user):
    zones = load(user)
    options = ""
    for group, entries in ZONES:
        opts = "".join(
            f'<option value="{tz}"{" disabled" if tz in zones else ""}>{label}</option>'
            for tz, label in entries)
        options += f'<optgroup label="{group}">{opts}</optgroup>'

    def row(tz, label, sub_id="", home=False):
        drop = "" if home else (
            f'<form method="POST" action="/timezones/remove" class="tz-drop" '
            f'style="display:inline-flex">'
            f'<input type="hidden" name="tz" value="{tz}">'
            # Deliberately not .chip-action: accent is the invitation to act, and
            # dropping a city is neither the invitation nor what you came for.
            f'<button class="btn btn-sm btn-ghost" type="submit" '
            f'title="Remove {label}">Remove</button></form>')
        name = ('<span id="tzHomeName">Your time zone</span>' if home
                else label)
        zone_note = ('<span id="tzHomeZone"></span>' if home else tz)
        return (
            f'<div class="tz-row{" tz-row--home" if home else ""}" '
            f'data-tz="{"__home__" if home else tz}">'
            f'<div class="tz-label">'
            f'<div class="tz-city">{"🏠 " if home else ""}{name}</div>'
            f'<div class="tz-sub">—</div>'
            f'<div class="tz-sub" style="opacity:.7">{zone_note}</div>'
            f'{drop}</div>'
            f'<div class="tz-hours"></div></div>')

    rows = row("", "", home=True) + "".join(row(z, LABELS[z]) for z in zones)
    full = len(zones) >= MAX_ZONES
    picker = (
        f'<form method="POST" action="/timezones/add" class="tz-add">'
        f'<select name="tz" class="tz-select" aria-label="City to compare"'
        f'{" disabled" if full else ""}>{options}</select>'
        f'<button class="btn btn-primary" type="submit"'
        f'{" disabled" if full else ""}>Add city</button></form>')
    limit_note = (f'<p class="tz-legend">Eight cities is the limit — remove one '
                  f'to add another.</p>' if full else "")

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>Time Zones · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css">
<style>{STYLE}</style></head>
<body>
<nav>
  <a href="/timezones" class="nav-brand">🌏 Time Zones</a>
</nav>
<div class="tz-wrap">
  <div class="tz-head">
    <div>
      <div class="tz-now" id="tzNow">--:--</div>
      <div class="tz-now-meta" id="tzNowMeta">&nbsp;</div>
    </div>
    {picker}
  </div>
  <div class="tz-scroll"><div class="tz-grid">{rows}</div></div>
  {limit_note}
  <div class="tz-legend">
    <span class="tz-key"><span class="tz-swatch"
      style="background:var(--accent-glow)"></span>09:00–18:00 local</span>
    <span class="tz-key"><span class="tz-swatch"
      style="background:var(--surface-2);opacity:.55"></span>22:00–07:00 local</span>
    <span class="tz-key"><span class="tz-swatch"
      style="background:transparent;box-shadow:inset 0 0 0 2px var(--accent)"></span>right now</span>
    <span class="tz-key"><b style="color:var(--warn)">next</b> — the date changes here</span>
  </div>
</div>
<script>{SCRIPT}</script>
</body></html>'''


def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user", "guest")

    if method == "POST":
        if path == "/timezones/add":
            add(user, _first(body, "tz"))
        elif path == "/timezones/remove":
            remove(user, _first(body, "tz"))
        return ("redirect", "/timezones")

    return ("html", render(user))
