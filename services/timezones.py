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
# The third field is what people call the zone — PST, KST, IST — because "what
# do they call it there" is part of the question (강프로 2026-08-07). Curated,
# not computed: Intl gives Seoul "GMT+9", and nobody calls it that. The common
# name is used even where DST technically renames it half the year.
ZONES = [
    ("Americas", [
        # The US cities are the ones actually scheduled against (강프로
        # 2026-08-07): Mountain View for Pacific, Dallas for Central, New York
        # for Eastern. Same IANA zones as the cities they replaced.
        ("America/Los_Angeles", "Mountain View", "PST"),
        ("America/Chicago", "Dallas", "CST"),
        ("America/New_York", "New York", "EST"),
        ("America/Toronto", "Toronto", "EST"),
        ("America/Mexico_City", "Mexico City", "CST"),
        ("America/Bogota", "Bogotá", "COT"),
        ("America/Sao_Paulo", "São Paulo", "BRT"),
        ("America/Argentina/Buenos_Aires", "Buenos Aires", "ART"),
    ]),
    ("Europe & Africa", [
        ("Europe/London", "London", "GMT"),
        ("Europe/Dublin", "Dublin", "GMT"),
        ("Europe/Lisbon", "Lisbon", "WET"),
        ("Europe/Madrid", "Madrid", "CET"),
        ("Europe/Paris", "Paris", "CET"),
        ("Europe/Berlin", "Berlin", "CET"),
        ("Europe/Amsterdam", "Amsterdam", "CET"),
        ("Europe/Zurich", "Zurich", "CET"),
        ("Europe/Stockholm", "Stockholm", "CET"),
        ("Europe/Warsaw", "Warsaw", "CET"),
        ("Europe/Athens", "Athens", "EET"),
        ("Europe/Istanbul", "Istanbul", "TRT"),
        ("Europe/Moscow", "Moscow", "MSK"),
        ("Africa/Lagos", "Lagos", "WAT"),
        ("Africa/Cairo", "Cairo", "EET"),
        ("Africa/Nairobi", "Nairobi", "EAT"),
        ("Africa/Johannesburg", "Johannesburg", "SAST"),
    ]),
    ("Middle East & Asia", [
        ("Asia/Dubai", "Dubai", "GST"),
        ("Asia/Riyadh", "Riyadh", "AST"),
        ("Asia/Karachi", "Karachi", "PKT"),
        # India is +5:30 and Nepal +5:45 — the zones that make an hour-only grid
        # lie, and the reason cells print minutes when the offset is not whole.
        # Chennai and Hyderabad share IST, so they share the row (강프로
        # 2026-08-07) — two rows of the same zone would just repeat each other.
        ("Asia/Kolkata", "Chennai / Hyderabad", "IST"),
        ("Asia/Kathmandu", "Kathmandu", "NPT"),
        ("Asia/Dhaka", "Dhaka", "BST"),
        ("Asia/Bangkok", "Bangkok", "ICT"),
        ("Asia/Jakarta", "Jakarta", "WIB"),
        ("Asia/Singapore", "Singapore", "SGT"),
        ("Asia/Kuala_Lumpur", "Kuala Lumpur", "MYT"),
        ("Asia/Manila", "Manila", "PHT"),
        ("Asia/Ho_Chi_Minh", "Ho Chi Minh City", "ICT"),
        ("Asia/Hong_Kong", "Hong Kong", "HKT"),
        ("Asia/Shanghai", "Shanghai", "CST"),
        ("Asia/Taipei", "Taipei", "CST"),
        ("Asia/Seoul", "Seoul", "KST"),
        ("Asia/Tokyo", "Tokyo", "JST"),
    ]),
    ("Oceania", [
        ("Australia/Perth", "Perth", "AWST"),
        ("Australia/Adelaide", "Adelaide", "ACST"),
        ("Australia/Brisbane", "Brisbane", "AEST"),
        ("Australia/Sydney", "Sydney", "AEST"),
        ("Pacific/Auckland", "Auckland", "NZST"),
        ("Pacific/Honolulu", "Honolulu", "HST"),
    ]),
    ("Reference", [
        ("UTC", "UTC", "UTC"),
    ]),
]

VALID = {tz for _, group in ZONES for tz, _, _ in group}
LABELS = {tz: label for _, group in ZONES for tz, label, _ in group}
ABBRS = {tz: abbr for _, group in ZONES for tz, _, abbr in group}

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


def move(user, tz, direction):
    """Swap a city one step up or down the list (강프로 2026-08-07).

    The order is the whole point of a comparison strip — the rows you read
    together belong next to each other. Ends clamp: moving the top row up is
    a no-op, not an error and not a wrap-around.
    """
    zones = load(user)
    if tz not in zones:
        return zones
    i = zones.index(tz)
    j = i - 1 if direction == "up" else i + 1
    if 0 <= j < len(zones):
        zones[i], zones[j] = zones[j], zones[i]
        save(user, zones)
    return zones


def _first(body, key):
    v = (body or {}).get(key, "")
    if isinstance(v, list):
        v = v[0] if v else ""
    return (v or "").strip()


# The strip can be anchored to somebody else's day: "9am Tuesday in Seoul, what
# is that here" is the question people actually arrive with. HOME is the browser
# reading its own zone, and stays the default.
HOME = "__home__"


def read_base(body):
    """Which zone the 24 columns belong to. Anything unrecognised falls home."""
    b = _first(body, "base")
    return b if b in VALID else HOME


def read_date(body):
    """The day being looked at, as YYYY-MM-DD, or "" for whatever today is.

    Validated rather than trusted: the value is handed to the browser's date
    arithmetic, and a malformed one would render 24 cells of "Invalid Date".
    """
    d = _first(body, "date")
    if len(d) == 10 and d[4] == "-" and d[7] == "-":
        try:
            y, m, day = int(d[0:4]), int(d[5:7]), int(d[8:10])
        except ValueError:
            return ""
        if 1 <= m <= 12 and 1 <= day <= 31 and 1900 <= y <= 2999:
            return d
    return ""


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
.tz-more{margin:0 0 14px}
.tz-more-head{cursor:pointer;list-style:none;display:inline-flex;align-items:center;
  gap:8px;min-height:40px;padding:0 14px;border-radius:var(--radius-full);
  background:var(--surface);border:1px solid var(--border-bright);
  color:var(--text-muted);font-size:var(--text-xs);font-weight:var(--fw-bold)}
.tz-more-head::-webkit-details-marker{display:none}
.tz-more-head::after{content:"⌄";font-size:1rem;line-height:1;margin-top:-3px}
.tz-more[open] .tz-more-head::after{content:"⌃";margin-top:3px}
.tz-more-head:hover{border-color:var(--accent);color:var(--accent)}
.tz-controls{display:flex;gap:8px;align-items:center;flex-wrap:wrap;
  margin:10px 0 0}
.tz-controls label{font-size:var(--text-xs);font-weight:var(--fw-bold);
  color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em}
.tz-date{min-height:40px;padding:0 12px;background:var(--surface);
  border:1px solid var(--border-bright);border-radius:var(--radius-md);
  color:var(--text);font-size:var(--text-sm);font-family:inherit}
.tz-date:focus{outline:none;border-color:var(--accent);
  box-shadow:0 0 0 3px var(--accent-glow)}
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
/* Wide enough that a half-hour zone still reads: 24 columns of "20:30" need
   about 33px each, and anything narrower runs the numbers together. */
.tz-grid{min-width:980px}
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
.tz-drop{display:flex;gap:4px;flex-wrap:wrap;margin-top:6px}
.tz-mv{padding:0 9px;min-width:34px}
.tz-mv[disabled]{opacity:.35;cursor:default}
/* The zone's everyday name — KST, PST — beside the city that carries it. */
.tz-abbr{margin-left:6px;font-size:var(--text-xs);font-weight:var(--fw-bold);
  color:var(--accent);letter-spacing:.03em}

.tz-hours{display:flex;flex:1}
.tz-cell{flex:1 0 24px;display:flex;flex-direction:column;align-items:center;
  justify-content:center;padding:8px 0;font-size:var(--text-xs);
  font-weight:var(--fw-bold);color:var(--text-muted);
  font-variant-numeric:tabular-nums;border-left:1px solid var(--border)}
.tz-cell--work{background:var(--accent-glow);color:var(--text)}
.tz-cell--sleep{color:var(--text-dim);opacity:.55}
.tz-cell--now{box-shadow:inset 0 0 0 2px var(--accent);border-radius:var(--radius-sm)}
/* The date is written under the column where it changes, and under the first
   column so a row never leaves you counting back to find which day you are on. */
.tz-daymark{font-size:9px;font-weight:var(--fw-bold);color:var(--warn);
  letter-spacing:.03em;margin-top:2px;height:11px;white-space:nowrap}
.tz-daymark--first{color:var(--text-muted)}
/* The hour you are in carries its date too — it is the column the eye lands on
   first, and it should not send you hunting left for the day. */
.tz-daymark--now{color:var(--accent)}
/* Where the clocks actually move. Twice a year this column is the difference
   between a call at 9 and a call at 8. */
.tz-cell--shift{box-shadow:inset 1px 0 0 var(--warn)}
/* A half-hour zone needs "14:30", not "14" — India is the whole reason this
   grid cannot just print an hour number (강프로 2026-08-07). */
.tz-cell--split{font-size:10px;letter-spacing:-.02em}

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
  .tz-date{flex:1;min-height:44px}
  /* Label above its control, both full width, so "Anchor" never ends up on one
     line and its dropdown on the next. */
  .tz-controls{display:grid;grid-template-columns:auto 1fr;gap:8px 10px;
    align-items:center}
  .tz-controls .btn{grid-column:2}
  .tz-label{flex:0 0 132px;padding:10px}
  .tz-grid{min-width:940px}
}
"""

SCRIPT = """
(function(){
  var grid = document.getElementById('tzGrid');
  if (!grid) return;
  var HOME = 'UTC';
  try { HOME = Intl.DateTimeFormat().resolvedOptions().timeZone || 'UTC'; } catch (e) {}

  var pad = function(n){ return (n < 10 ? '0' : '') + n; };
  var cityOf = function(tz){ return tz.split('/').pop().replace(/_/g, ' '); };

  // The strip belongs to this zone and this day. Both can be somebody else's:
  // "9am Tuesday in Seoul" is the question people arrive with.
  var BASE = grid.dataset.base === '__home__' ? HOME : grid.dataset.base;
  var PICKED = grid.dataset.date || '';

  // Fill in the parts of the page only the browser can know.
  document.querySelectorAll('[data-home-city]').forEach(function(e){
    e.textContent = cityOf(HOME); });
  document.querySelectorAll('[data-home-zone]').forEach(function(e){
    e.textContent = HOME; });
  // The home zone's everyday name is the browser's to know. Intl's short form
  // is a real abbreviation where one exists (PDT, GMT) and a plain offset
  // (GMT+9) where the world never coined one — both are honest.
  try {
    var homeAbbr = new Intl.DateTimeFormat('en-US', {timeZone: HOME, timeZoneName: 'short'})
      .formatToParts(new Date()).filter(function(p){ return p.type === 'timeZoneName'; })
      .map(function(p){ return p.value; })[0] || '';
    document.querySelectorAll('[data-home-abbr]').forEach(function(e){
      e.textContent = homeAbbr; });
  } catch (e) {}
  var homeOpt = document.getElementById('tzHomeOption');
  if (homeOpt) homeOpt.textContent = 'Your time zone — ' + cityOf(HOME);

  // Wall-clock parts for an instant in a zone. Intl is the only thing in the
  // browser that knows a zone's rules, so every number on this page comes
  // through here rather than from an offset we worked out ourselves.
  function parts(date, tz){
    var f = new Intl.DateTimeFormat('en-CA', {timeZone: tz, hour12: false,
      year:'numeric', month:'2-digit', day:'2-digit',
      hour:'2-digit', minute:'2-digit'});
    var o = {};
    f.formatToParts(date).forEach(function(p){ o[p.type] = p.value; });
    var h = parseInt(o.hour, 10) % 24;   // some engines render midnight as 24
    return {ymd: o.year+'-'+o.month+'-'+o.day, hour: h,
            minute: parseInt(o.minute, 10),
            y: +o.year, mo: +o.month, d: +o.day};
  }

  // How far a zone's wall clock is from UTC at a given instant, in minutes.
  function offsetMin(date, tz){
    var p = parts(date, tz);
    return (Date.UTC(p.y, p.mo - 1, p.d, p.hour, p.minute) - date.getTime()) / 60000;
  }

  // The instant at which a zone's clock reads this wall time. Solved by
  // iteration rather than arithmetic: the offset we need depends on the instant
  // we are looking for, and near a DST change the first guess is an hour out.
  function instantOf(y, mo, d, tz){
    var guess = Date.UTC(y, mo - 1, d, 0, 0);
    for (var i = 0; i < 3; i++){
      guess = Date.UTC(y, mo - 1, d, 0, 0) - offsetMin(new Date(guess), tz) * 60000;
    }
    return new Date(guess);
  }

  function offsetLabel(date, tz){
    var mins = offsetMin(date, tz) - offsetMin(date, BASE);
    if (mins === 0) return 'same time';
    var sign = mins > 0 ? '+' : '\\u2212', m = Math.abs(mins);
    var h = Math.floor(m / 60), r = m % 60;
    return sign + h + (r ? ':' + pad(r) : '') + 'h';
  }

  // timeZone:'UTC' is not decoration — the date is built as a UTC midnight, and
  // formatting it in the viewer's own zone renders the day before for anyone
  // west of Greenwich. That is exactly the off-by-one this label exists to stop.
  var SHORT = new Intl.DateTimeFormat('en-US',
    {timeZone:'UTC', month:'short', day:'numeric'});
  function shortDate(p){ return SHORT.format(new Date(Date.UTC(p.y, p.mo-1, p.d))); }

  function paint(){
    var now = new Date();

    // Column 0 is midnight of the chosen day in the base zone. With no day
    // chosen that is simply today, which keeps the default behaviour.
    var anchor;
    if (PICKED){
      anchor = instantOf(+PICKED.slice(0,4), +PICKED.slice(5,7), +PICKED.slice(8,10), BASE);
    } else {
      var t = parts(now, BASE);
      anchor = instantOf(t.y, t.mo, t.d, BASE);
    }
    // Only a strip showing today can have a "right now" column in it.
    var basePartsNow = parts(now, BASE);
    var showNow = parts(anchor, BASE).ymd === basePartsNow.ymd;

    var headEl = document.getElementById('tzHeadDate');
    if (headEl){
      headEl.textContent = new Intl.DateTimeFormat('en-US',
        {timeZone: BASE, weekday:'long', month:'long', day:'numeric', year:'numeric'})
        .format(anchor) + ' in ' + cityOf(BASE);
    }
    var clock = document.getElementById('tzNow');
    if (clock) clock.textContent = pad(basePartsNow.hour) + ':' + pad(basePartsNow.minute);

    var nowCol = -1;

    grid.querySelectorAll('.tz-row').forEach(function(row){
      var tz = row.dataset.tz === '__home__' ? HOME : row.dataset.tz;
      var hours = row.querySelector('.tz-hours');
      if (!hours) return;

      // Read the whole row first, then decide how to print it. A clock shift
      // lands inside these 24 hours twice a year, so the offset is not one
      // number for the row — on 1 Nov 2026 Chicago is UTC-5 for part of this
      // strip and UTC-6 for the rest, and anything decided from the anchor
      // alone is wrong after the change (강프로 2026-08-07).
      var col = [];
      for (var i = 0; i < 24; i++){
        var at = new Date(anchor.getTime() + i * 3600000);
        col.push({at: at, p: parts(at, tz), off: offsetMin(at, tz)});
      }
      // Minutes are printed when any hour in the row needs them, so the row
      // keeps one shape instead of changing width halfway along.
      var split = col.some(function(c){ return c.p.minute !== 0; });

      hours.innerHTML = '';
      var prevDay = null, prevOff = null;
      col.forEach(function(c, i){
        var p = c.p;
        var isNow = showNow && c.at <= now && now < new Date(c.at.getTime() + 3600000);
        if (isNow) nowCol = i;
        var cell = document.createElement('div');
        cell.className = 'tz-cell'
          + (p.hour >= 9 && p.hour < 18 ? ' tz-cell--work' : '')
          + (p.hour < 7 || p.hour >= 22 ? ' tz-cell--sleep' : '')
          + (split ? ' tz-cell--split' : '')
          + (isNow ? ' tz-cell--now' : '');
        cell.textContent = pad(p.hour) + (split ? ':' + pad(p.minute) : '');

        // The date is written under the first column, under whichever column it
        // changes on, and under the hour you are in — the one column you look
        // at first should never make you hunt for its day.
        var mark = document.createElement('div');
        mark.className = 'tz-daymark'
          + (i === 0 ? ' tz-daymark--first' : '')
          + (isNow ? ' tz-daymark--now' : '');
        if (i === 0 || p.ymd !== prevDay || isNow) mark.textContent = shortDate(p);

        // And where the clocks actually move, the column says so.
        if (prevOff !== null && c.off !== prevOff){
          cell.classList.add('tz-cell--shift');
          cell.title = (c.off > prevOff ? 'Clocks go forward here' : 'Clocks go back here');
          mark.textContent = shortDate(p) + ' ⤴';
        }
        prevDay = p.ymd;
        prevOff = c.off;
        cell.appendChild(mark);
        hours.appendChild(cell);
      });

      var sub = row.querySelector('.tz-sub');
      if (sub){
        var p0 = parts(now, tz);
        sub.textContent = 'now ' + pad(p0.hour) + ':' + pad(p0.minute)
          + (row.dataset.tz === grid.dataset.base ? '' : ' · ' + offsetLabel(anchor, tz));
      }
    });

    // Bring the current hour into view rather than leaving it off the right
    // edge of a phone: it lands third from the left, so the hours just gone are
    // still readable beside it (강프로 2026-08-07).
    var sc = document.getElementById('tzScroll');
    if (sc && nowCol > -1 && !sc.dataset.userScrolled){
      var cell0 = grid.querySelector('.tz-cell');
      if (cell0){
        var w = cell0.getBoundingClientRect().width;
        sc.dataset.painting = '1';          // our own scroll is not the user's
        sc.scrollLeft = Math.max(0, (nowCol - 2) * w);
        setTimeout(function(){ delete sc.dataset.painting; }, 60);
      }
    }
  }

  // Once you have scrolled the strip yourself, the half-minute repaint stops
  // dragging you back to the current hour.
  var scroller = document.getElementById('tzScroll');
  if (scroller){
    scroller.addEventListener('scroll', function(){
      if (scroller.dataset.painting) return;
      scroller.dataset.userScrolled = '1';
    }, {passive: true});
  }

  paint();
  setInterval(paint, 30000);
})();
"""


def render(user, base=HOME, picked=""):
    zones = load(user)
    options = ""
    for group, entries in ZONES:
        opts = "".join(
            f'<option value="{tz}"{" disabled" if tz in zones else ""}>{label} ({abbr})</option>'
            for tz, label, abbr in entries)
        options += f'<optgroup label="{group}">{opts}</optgroup>'

    def row(tz, label, anchor=False, idx=None, count=0):
        # The anchor row is the day everything else is read against, so it is
        # never removable — dropping it would leave the strip measuring nothing.
        acts = ""
        if not anchor:
            def _mv(direction, glyph, dead):
                # A dead arrow still renders, disabled — buttons that appear and
                # vanish as rows move make the column jitter under the thumb.
                return (
                    f'<form method="POST" action="/timezones/move" style="display:inline-flex">'
                    f'<input type="hidden" name="tz" value="{tz}">'
                    f'<input type="hidden" name="dir" value="{direction}">'
                    f'<input type="hidden" name="base" value="{base}">'
                    f'<input type="hidden" name="date" value="{picked}">'
                    f'<button class="btn btn-sm btn-ghost tz-mv" type="submit" '
                    f'{"disabled " if dead else ""}title="Move {label} {direction}">'
                    f'{glyph}</button></form>')
            acts = (
                f'<div class="tz-drop">'
                + _mv("up", "▲", idx == 0) + _mv("down", "▼", idx == count - 1)
                + f'<form method="POST" action="/timezones/remove" style="display:inline-flex">'
                f'<input type="hidden" name="tz" value="{tz}">'
                f'<input type="hidden" name="base" value="{base}">'
                f'<input type="hidden" name="date" value="{picked}">'
                # Deliberately not .chip-action: accent is the invitation to act,
                # and dropping a city is neither the invitation nor the point.
                f'<button class="btn btn-sm btn-ghost" type="submit" '
                f'title="Remove {label}">Remove</button></form></div>')
        is_home = tz == HOME
        name = ('<span data-home-city>Your time zone</span>' if is_home else label)
        # What the zone is called rides beside the city — the home row's is the
        # browser's to fill, like everything else about the home zone.
        abbr = ('<span class="tz-abbr" data-home-abbr></span>' if is_home
                else f'<span class="tz-abbr">{ABBRS.get(tz, "")}</span>')
        zone_note = ('<span data-home-zone></span>' if is_home else tz)
        return (
            f'<div class="tz-row{" tz-row--home" if anchor else ""}" data-tz="{tz}">'
            f'<div class="tz-label">'
            f'<div class="tz-city">{"⚓ " if anchor else ""}{name}{abbr}</div>'
            f'<div class="tz-sub">—</div>'
            f'<div class="tz-sub" style="opacity:.7">{zone_note}</div>'
            f'{acts}</div>'
            f'<div class="tz-hours"></div></div>')

    # The anchor leads, and never appears twice — picking a city you already
    # compare against promotes that row rather than duplicating it.
    listed = [z for z in zones if z != base]
    rows = row(base, LABELS.get(base, ""), anchor=True) + "".join(
        row(z, LABELS[z], idx=i, count=len(listed)) for i, z in enumerate(listed))

    base_opts = (f'<option value="{HOME}"{" selected" if base == HOME else ""} '
                 f'id="tzHomeOption">Your time zone</option>')
    for group, entries in ZONES:
        opts = "".join(
            f'<option value="{tz}"{" selected" if tz == base else ""}>{label} ({abbr})</option>'
            for tz, label, abbr in entries)
        base_opts += f'<optgroup label="{group}">{opts}</optgroup>'

    # Folded away by default: the strip is what you came for, and two selects
    # standing permanently above it are furniture (강프로 2026-08-07). It opens
    # itself whenever the view is not the plain "my zone, today", because then
    # the controls are the explanation for what you are looking at.
    custom = base != HOME or bool(picked)
    summary = ("Anchored to " + LABELS.get(base, "your time zone")
               + (" · " + picked if picked else " · today")) if custom else \
              "Compare another city's day"
    controls = (
        f'<details class="tz-more"{" open" if custom else ""}>'
        f'<summary class="tz-more-head">🗓 {summary}</summary>'
        f'<form method="GET" action="/timezones" class="tz-controls">'
        f'<label for="tzBase">Anchor</label>'
        f'<select id="tzBase" name="base" class="tz-select" '
        f'onchange="this.form.submit()">{base_opts}</select>'
        f'<label for="tzDate">Day</label>'
        f'<input id="tzDate" name="date" type="date" class="tz-date" '
        f'value="{picked}" onchange="this.form.submit()">'
        f'<button class="btn btn-sm btn-secondary" type="submit">Show</button>'
        + (f'<a class="btn btn-sm btn-ghost" href="/timezones?base={base}">Today</a>'
           if picked else '')
        + f'</form></details>')

    full = len(zones) >= MAX_ZONES
    picker = (
        f'<form method="POST" action="/timezones/add" class="tz-add">'
        f'<input type="hidden" name="base" value="{base}">'
        f'<input type="hidden" name="date" value="{picked}">'
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
      <div class="tz-now-meta" id="tzHeadDate">&nbsp;</div>
    </div>
    {picker}
  </div>
  {controls}
  <div class="tz-scroll" id="tzScroll"><div class="tz-grid" id="tzGrid"
       data-base="{base}" data-date="{picked}">{rows}</div></div>
  {limit_note}
  <div class="tz-legend">
    <span class="tz-key"><span class="tz-swatch"
      style="background:var(--accent-glow)"></span>09:00–18:00 local</span>
    <span class="tz-key"><span class="tz-swatch"
      style="background:var(--surface-2);opacity:.55"></span>22:00–07:00 local</span>
    <span class="tz-key"><span class="tz-swatch"
      style="background:transparent;box-shadow:inset 0 0 0 2px var(--accent)"></span>right now</span>
    <span class="tz-key">Each column carries its own date; a half-hour zone
      shows minutes (Mumbai reads 14:30, not 14).</span>
  </div>
</div>
<script>{SCRIPT}</script>
</body></html>'''


def _view_query(body):
    """Carry the anchor and the day back through a redirect, so adding a city
    does not throw you back to today."""
    base, picked = read_base(body), read_date(body)
    bits = []
    if base != HOME:
        bits.append("base=" + base)
    if picked:
        bits.append("date=" + picked)
    return ("?" + "&".join(bits)) if bits else ""


def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user", "guest")

    if method == "POST":
        if path == "/timezones/add":
            add(user, _first(body, "tz"))
        elif path == "/timezones/remove":
            remove(user, _first(body, "tz"))
        elif path == "/timezones/move":
            direction = _first(body, "dir")
            if direction in ("up", "down"):
                move(user, _first(body, "tz"), direction)
        return ("redirect", "/timezones" + _view_query(body))

    return ("html", render(user, read_base(body), read_date(body)))
