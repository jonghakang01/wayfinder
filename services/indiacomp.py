"""India Comp — an offer written in LPA, read all the way through to USD.

An India offer arrives in units the reviewer does not think in (lakh per annum,
CTC) and is reviewed in a currency it was never quoted in. Three things get
added on the way from the number on the offer to the number in the budget:
employer burden, the transfer-pricing markup the US entity pays, and the
exchange rate. Each one is a multiplication anybody could do; the reason this
page exists is that doing all three in your head, every time, is where the
mistakes come from.

So the four stages are laid out as stages, with the arithmetic written next to
each one — the page is meant to be checkable, not just trusted. The assumptions
live in one place and apply to every saved candidate, which is what makes "what
if the rate moves" a single edit rather than a spreadsheet full of them.
"""
import json
import os
from datetime import date

from services._paths import DATA_ROOT

META = {
    "name": "India Comp",
    "path": "/indiacomp",
    "icon": "🧮",
    "description": "An LPA offer read through to the USD it costs",
    "hidden": False,
}

# 1 lakh = ₹100,000. The unit the offer is written in, and the whole reason
# stage 1 exists rather than starting from a rupee figure.
LAKH = 100_000

# Defaults confirmed by 강프로 2026-08-08. Burden is an approximation until a
# real onboarding gives us the measured number, which is why it is editable and
# labelled as insurance & extras rather than as a statutory rate.
DEFAULTS = {"tp_pct": 18.0, "burden_pct": 10.0, "fx_rate": 88.0, "fx_updated": ""}

# Hiring is in Chennai for now. Carried on the candidate for the record only —
# no part of the calculation reads it.
DEFAULT_LOCATION = "Chennai"

# A rate nobody has touched in a month is the quiet way this page goes wrong,
# so it says so rather than letting an old number pass as current.
FX_STALE_DAYS = 30

LIMITS = {          # (low, high) — a typo should not render an absurd page
    "lpa": (0.0, 10_000.0),
    "burden_pct": (0.0, 200.0),
    "tp_pct": (0.0, 500.0),
    "fx_rate": (1.0, 10_000.0),
}


# --- data ---------------------------------------------------------------------

def _file(user):
    d = os.path.join(DATA_ROOT, "indiacomp")
    os.makedirs(d, exist_ok=True)
    return os.path.join(d, f"{user or 'guest'}.json")


def load(user):
    """Settings and candidates, always in the shape the renderer expects.

    Anything unreadable falls back to defaults rather than raising: a hand-edited
    or half-written file should cost you your saved candidates, not the page.
    """
    try:
        with open(_file(user)) as f:
            raw = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        raw = {}
    if not isinstance(raw, dict):
        raw = {}
    settings = dict(DEFAULTS)
    for k, v in (raw.get("settings") or {}).items():
        if k in settings:
            settings[k] = v
    for k in ("tp_pct", "burden_pct", "fx_rate"):
        settings[k] = _clamp(_float(settings[k], DEFAULTS[k]), k)
    cands = [c for c in (raw.get("candidates") or []) if isinstance(c, dict)]
    return settings, cands


def save(user, settings, candidates):
    with open(_file(user), "w") as f:
        json.dump({"settings": settings, "candidates": candidates},
                  f, ensure_ascii=False, indent=2)


def _float(v, default=0.0):
    try:
        return float(str(v).replace(",", "").strip())
    except (TypeError, ValueError):
        return default


def _clamp(v, key):
    low, high = LIMITS[key]
    return min(max(v, low), high)


def _next_id(cands):
    n = 0
    for c in cands:
        try:
            n = max(n, int(str(c.get("id", "0")).lstrip("c") or 0))
        except ValueError:
            continue
    return f"c{n + 1}"


def _first(body, key, default=""):
    v = (body or {}).get(key, default)
    if isinstance(v, list):
        v = v[0] if v else default
    return (str(v) if v is not None else "").strip()


def add(user, fields):
    settings, cands = load(user)
    lpa = _clamp(_float(fields.get("lpa")), "lpa")
    if lpa <= 0:
        return None                      # nothing to compute from; not an error
    cand = {
        "id": _next_id(cands),
        "name": (fields.get("name") or "").strip() or "Unnamed candidate",
        "role": (fields.get("role") or "").strip(),
        "location": (fields.get("location") or "").strip() or DEFAULT_LOCATION,
        "lpa": lpa,
        "burden_override": _override(fields.get("burden_override")),
        "note": (fields.get("note") or "").strip(),
        "created": date.today().isoformat(),
    }
    cands.append(cand)
    save(user, settings, cands)
    return cand["id"]


def _override(raw):
    """A blank burden override means "use the shared assumption", and has to
    survive as None — 0.0 is a real answer (a candidate with no burden at all)."""
    if raw is None or str(raw).strip() == "":
        return None
    return _clamp(_float(raw), "burden_pct")


def update(user, cid, fields):
    settings, cands = load(user)
    for c in cands:
        if c.get("id") != cid:
            continue
        if "name" in fields:
            c["name"] = (fields.get("name") or "").strip() or c.get("name", "")
        if "role" in fields:
            c["role"] = (fields.get("role") or "").strip()
        if "location" in fields:
            c["location"] = (fields.get("location") or "").strip() or DEFAULT_LOCATION
        if "lpa" in fields:
            lpa = _clamp(_float(fields.get("lpa")), "lpa")
            if lpa > 0:
                c["lpa"] = lpa
        if "burden_override" in fields:
            c["burden_override"] = _override(fields.get("burden_override"))
        if "note" in fields:
            c["note"] = (fields.get("note") or "").strip()
        save(user, settings, cands)
        return True
    return False


def delete(user, cid):
    settings, cands = load(user)
    kept = [c for c in cands if c.get("id") != cid]
    if len(kept) != len(cands):
        save(user, settings, kept)
        return True
    return False


def save_settings(user, fields):
    """The shared assumptions. The FX date is stamped when the rate itself moves,
    so "updated" means somebody looked the rate up — not that they opened the
    form and saved the same number back."""
    settings, cands = load(user)
    was = settings["fx_rate"]
    for key in ("tp_pct", "burden_pct", "fx_rate"):
        if key in fields:
            settings[key] = _clamp(_float(fields[key], settings[key]), key)
    if settings["fx_rate"] != was or not settings.get("fx_updated"):
        settings["fx_updated"] = date.today().isoformat()
    save(user, settings, cands)
    return settings


# --- the calculation ----------------------------------------------------------

def compute(lpa, burden_pct, tp_pct, fx_rate):
    """The four stages, annual and monthly, in rupees and dollars.

    Multiplications in this order and no rounding in between: rounding stage 2
    before stage 3 is how a page ends up disagreeing with the same sum done on
    a calculator, and this one is meant to be checked against one.
    """
    offer = lpa * LAKH
    india = offer * (1 + burden_pct / 100.0)
    us = india * (1 + tp_pct / 100.0)
    fx = fx_rate if fx_rate > 0 else DEFAULTS["fx_rate"]
    return {
        "offer_yr": offer, "offer_mo": offer / 12.0,
        "india_yr": india, "india_mo": india / 12.0,
        "us_yr": us, "us_mo": us / 12.0,
        "usd_offer_yr": offer / fx,
        "usd_india_yr": india / fx,
        "usd_yr": us / fx, "usd_mo": us / 12.0 / fx,
        "burden_pct": burden_pct, "tp_pct": tp_pct, "fx_rate": fx,
    }


def burden_for(cand, settings):
    """A candidate's own burden if it has one, otherwise the shared assumption."""
    ov = cand.get("burden_override")
    return _clamp(_float(ov, settings["burden_pct"]), "burden_pct") \
        if ov is not None else settings["burden_pct"]


def compute_for(cand, settings):
    return compute(_float(cand.get("lpa")), burden_for(cand, settings),
                   settings["tp_pct"], settings["fx_rate"])


def fx_age_days(settings):
    """How old the rate is, or None if it has never been stamped."""
    stamp = settings.get("fx_updated") or ""
    try:
        y, m, d = (int(x) for x in stamp.split("-"))
        return (date.today() - date(y, m, d)).days
    except (ValueError, TypeError):
        return None


# --- formatting ---------------------------------------------------------------

def _inr(v):
    return f"₹{v:,.0f}"


def _usd(v):
    return f"${v:,.0f}"


def _pct(v):
    return f"{v:g}%"


def _rate(v):
    return f"{v:,.2f}".rstrip("0").rstrip(".")


def _esc(s):
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


# --- rendering ----------------------------------------------------------------

STYLE = """
.ic-wrap{max-width:1100px;margin:0 auto;padding:20px 16px 90px}
.ic-head{margin-bottom:18px}
.ic-title{font-size:1.5rem;font-weight:var(--fw-extrabold);color:var(--text);
  letter-spacing:-.02em}
.ic-lede{margin-top:6px;color:var(--text-muted);font-size:var(--text-sm);
  font-weight:var(--fw-medium);max-width:62ch}

/* Collapsible intake — the cardconv shape: a heading that stays on one line,
   a caret that turns, body padded away from the summary. */
.ic-fold{background:var(--surface-2);border:1px solid var(--border);
  border-radius:var(--radius-md);margin-bottom:14px;overflow:hidden}
.ic-fold>summary{padding:12px 16px;font-size:var(--text-sm);
  font-weight:var(--fw-bold);color:var(--text);cursor:pointer;user-select:none;
  list-style:none;display:flex;align-items:center;gap:8px;white-space:nowrap}
.ic-fold>summary::-webkit-details-marker{display:none}
.ic-fold>summary::before{content:'▸';font-size:.7rem;color:var(--text-muted);
  transition:transform .15s}
.ic-fold[open]>summary::before{transform:rotate(90deg)}
.ic-fold-note{color:var(--text-muted);font-weight:var(--fw-medium);flex:1;
  min-width:0;overflow:hidden;text-overflow:ellipsis}
.ic-fold-body{padding:4px 16px 16px}

/* Fields stretch and their contents start at the top, so the inputs line up
   across a row whether or not a field carries a hint underneath — bottom
   alignment pushed the hinted ones up out of line (QA 2026-08-08). */
.ic-form{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;
  align-items:stretch}
.ic-form .wf-field{justify-content:flex-start}
.ic-submit{justify-content:flex-end}
.ic-form--wide{grid-template-columns:1.4fr 1.4fr 1fr 1fr}
.ic-form .ic-span2{grid-column:span 2}
.ic-actions{display:flex;gap:8px;flex-wrap:wrap;margin-top:14px}
.ic-hint{font-size:var(--text-xs);color:var(--text-muted);margin-top:4px}
.ic-warn{color:var(--warn);font-weight:var(--fw-bold)}

/* Stage cards. The shared .wf-stat shape, with the value dialled down: a full
   rupee figure is ten characters, and 2.2rem breaks it across two lines. */
/* minmax(0,1fr), not 1fr: a plain 1fr track will not shrink below its content's
   min-width, so one ₹27,005,000 at a narrow width pushes the whole page
   sideways instead of the card getting smaller (QA 2026-08-08, 320px). */
.ic-stats{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;
  margin:18px 0 6px}
.ic-stat{display:block;text-decoration:none;background:var(--surface);
  border:1px solid var(--border);border-radius:var(--radius-lg);
  padding:16px 16px;box-shadow:var(--shadow-sm);transition:.15s}
.ic-stat:hover{border-color:var(--accent);transform:translateY(-2px)}
.ic-step{font-size:var(--text-xs);font-weight:var(--fw-bold);color:var(--accent);
  letter-spacing:.08em}
.ic-stat-value{margin-top:8px;font-size:1.45rem;font-weight:var(--fw-extrabold);
  letter-spacing:-.02em;line-height:1.1;color:var(--text);
  font-variant-numeric:tabular-nums}
.ic-stat-sub{margin-top:4px;font-size:var(--text-sm);color:var(--text-muted);
  font-weight:var(--fw-semibold);font-variant-numeric:tabular-nums}
.ic-stat-label{margin-top:10px;font-size:var(--text-xs);color:var(--text-muted);
  font-weight:var(--fw-bold);text-transform:uppercase;letter-spacing:.05em}

/* The derivation. Every stage says what was multiplied by what, so the page can
   be checked against a calculator instead of believed. */
.ic-ladder{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);overflow:hidden;margin-bottom:22px}
.ic-rung{display:flex;gap:14px;padding:13px 16px;
  border-bottom:1px solid var(--border);align-items:baseline}
.ic-rung:last-child{border-bottom:none}
.ic-rung:target{background:var(--accent-glow)}
.ic-rung-n{flex:0 0 22px;font-size:var(--text-xs);font-weight:var(--fw-bold);
  color:var(--accent)}
.ic-rung-main{flex:1;min-width:0}
.ic-rung-name{font-size:var(--text-sm);font-weight:var(--fw-bold);color:var(--text)}
.ic-rung-math{margin-top:3px;font-size:var(--text-sm);color:var(--text-muted);
  font-variant-numeric:tabular-nums}
.ic-rung-why{margin-top:3px;font-size:var(--text-xs);color:var(--text-muted)}
.ic-rung-out{flex:0 0 auto;text-align:right;font-size:var(--text-md);
  font-weight:var(--fw-bold);color:var(--text);font-variant-numeric:tabular-nums}

.ic-section-head{display:flex;align-items:baseline;justify-content:space-between;
  gap:12px;flex-wrap:wrap;margin:0 0 10px}
.ic-h2{font-size:var(--text-md);font-weight:var(--fw-bold);color:var(--text)}
.ic-who{font-size:var(--text-sm);color:var(--text-muted);font-weight:var(--fw-semibold)}
.ic-table-card{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:6px 12px 4px;overflow-x:auto}
/* Outranks the global `.wf-cardtable tr` that paints every mobile card
   --surface, which would otherwise erase the focused row exactly where the
   ladder above it is hardest to tie back to a row. */
.wf-cardtable tr.ic-row--on{background:var(--accent-glow)}
.ic-name{font-weight:var(--fw-bold);color:var(--text)}
.ic-sub{font-size:var(--text-xs);color:var(--text-muted);margin-top:2px}
.ic-num{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.ic-acts{display:flex;gap:6px;justify-content:flex-end;flex-wrap:wrap}
.ic-empty{background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:34px 22px;text-align:center}
.ic-empty-icon{font-size:2.2rem}
.ic-empty-title{margin-top:8px;font-size:var(--text-md);
  font-weight:var(--fw-bold);color:var(--text)}
.ic-empty-sub{margin-top:6px;font-size:var(--text-sm);color:var(--text-muted)}
.ic-sheet-grid{display:grid;grid-template-columns:1fr 1fr;gap:12px}
/* Delete sits away from Save, and on the left — the floating theme toggle owns
   the bottom-right corner at a z-index no modal beats, so a destructive button
   parked there on a phone is half-covered by a sun icon. */
.ic-danger-row{margin-top:10px;justify-content:flex-start}
.ic-sheet-grid .ic-span2{grid-column:span 2}

@media (max-width:768px){
  .ic-wrap{padding:16px 14px 90px}
  .ic-title{font-size:1.25rem}
  .ic-form .ic-span2{grid-column:span 2}
  .ic-stats{grid-template-columns:repeat(2,minmax(0,1fr));gap:10px}
  .ic-stat{padding:13px 12px}
  .ic-stat-value{font-size:1.25rem}
  .ic-actions .btn{flex:1;min-height:44px}
  /* Cells label themselves on a phone (.wf-cardtable), so the money columns
     stop being right-aligned against a label on the same line. */
  .ic-table-card{padding:0;background:transparent;border:0;overflow:visible}
  .ic-num{text-align:right}
  .ic-rung{flex-wrap:wrap;gap:8px}
  .ic-rung-out{flex-basis:100%;text-align:left}
  .ic-form,.ic-form--wide{grid-template-columns:repeat(2,minmax(0,1fr))}
  .ic-sheet-grid{grid-template-columns:1fr}
  /* A span-2 child in a one-column grid does not stop spanning — it makes grid
     invent a second implicit column, and the sheet goes back to two cramped
     ones (caught in QA 2026-08-08: a 40px-wide Name box beside Role). */
  .ic-sheet-grid .ic-span2{grid-column:span 1}
  /* Both bottom corners belong to fixed global controls (wf-back left, the
     theme toggle right) at a z-index no sheet outranks, so the sheet keeps its
     last row clear of that band rather than putting a button under one. */
  .wf-modal{padding-bottom:calc(72px + env(safe-area-inset-bottom,0px))}
}

/* Below 360px two stage cards side by side cannot hold a large rupee figure at
   any readable size, so they stack rather than shrink into unreadability. */
@media (max-width:360px){
  .ic-stats{grid-template-columns:1fr}
  .ic-form,.ic-form--wide{grid-template-columns:1fr}
}
"""


def _field(scope, label, name, value, *, kind="text", placeholder="", span=False,
           hint="", step="", required=False):
    """One labelled input. `scope` keeps the id unique per form on the page.

    Three forms here carry the same field names (burden_override appears in the
    assumptions, the intake and the edit sheet), and a duplicated id sends every
    label to whichever input the browser found first — the label in the edit
    sheet would focus the intake's box.
    """
    cls = "wf-field" + (" ic-span2" if span else "")
    extra = f' step="{step}"' if step else ""
    num = " wf-num" if kind == "number" else ""
    eid = f"ic-{scope}-{name}"
    return (
        f'<div class="{cls}">'
        f'<label class="wf-label" for="{eid}">{label}</label>'
        f'<input class="wf-input{num}" id="{eid}" name="{name}" type="{kind}"'
        f'{extra} value="{_esc(value)}" placeholder="{_esc(placeholder)}"'
        f'{" required" if required else ""} autocomplete="off">'
        + (f'<div class="ic-hint">{hint}</div>' if hint else "")
        + '</div>')


def _assumptions(settings, open_it):
    age = fx_age_days(settings)
    stamp = settings.get("fx_updated") or ""
    if age is None:
        fx_note = "rate never stamped"
    elif age >= FX_STALE_DAYS:
        fx_note = f'<span class="ic-warn">rate {age} days old ({stamp})</span>'
    elif age == 0:
        fx_note = "rate updated today"
    else:
        fx_note = f"rate updated {age} day{'s' if age != 1 else ''} ago"
    summary = (f'TP {_pct(settings["tp_pct"])} · burden '
               f'{_pct(settings["burden_pct"])} · ₹{_rate(settings["fx_rate"])}/USD')
    return (
        f'<details class="ic-fold"{" open" if open_it else ""}>'
        f'<summary>⚙️ Assumptions'
        f'<span class="ic-fold-note">{summary} — {fx_note}</span></summary>'
        f'<div class="ic-fold-body">'
        f'<form method="POST" action="/indiacomp/settings" class="ic-form">'
        + _field("set", "TP markup %", "tp_pct", f'{settings["tp_pct"]:g}',
                 kind="number", step="0.1",
                 hint="What the US entity pays the India entity on top of cost")
        + _field("set", "Employer burden %", "burden_pct", f'{settings["burden_pct"]:g}',
                 kind="number", step="0.1",
                 hint="Insurance &amp; extras above CTC — approximate until measured")
        + _field("set", "FX rate ₹/USD", "fx_rate", f'{settings["fx_rate"]:g}',
                 kind="number", step="0.01", hint="Entered by hand; last value is kept")
        + '<div class="wf-field ic-submit">'
          '<button class="btn btn-primary" type="submit">Save assumptions</button></div>'
        + '</form>'
        + '<div class="ic-hint">These apply to every saved candidate — change one '
          'and the whole list is recalculated.</div>'
        + '</div></details>')


def _intake(open_it, settings):
    return (
        f'<details class="ic-fold"{" open" if open_it else ""}>'
        f'<summary>➕ Add a candidate'
        f'<span class="ic-fold-note">name, role and the offer in LPA</span></summary>'
        f'<div class="ic-fold-body">'
        f'<form method="POST" action="/indiacomp/add" class="ic-form ic-form--wide">'
        + _field("add", "Name", "name", "", placeholder="Candidate name")
        + _field("add", "Role", "role", "", placeholder="e.g. Senior Analyst")
        + _field("add", "Offer LPA", "lpa", "", kind="number", step="0.1",
                 placeholder="24", required=True,
                 hint="Lakh per annum, taken as CTC")
        + _field("add", "Location", "location", DEFAULT_LOCATION)
        + _field("add", "Burden % override", "burden_override", "", kind="number",
                 step="0.1", placeholder=f'{settings["burden_pct"]:g}',
                 hint="Blank uses the shared assumption")
        + _field("add", "Note", "note", "", span=True, placeholder="Anything worth remembering")
        + '<div class="ic-actions ic-span2">'
          '<button class="btn btn-primary" type="submit">Add candidate</button>'
          '</div>'
        + '</form>'
        + '</div></details>')


def _stage_cards(m):
    cards = [
        ("STEP 1", "Offer (CTC)", _inr(m["offer_yr"]),
         f'{_inr(m["offer_mo"])} / mo', "step-1"),
        ("STEP 2", f'India cost (+{_pct(m["burden_pct"])})', _inr(m["india_yr"]),
         f'{_inr(m["india_mo"])} / mo', "step-2"),
        ("STEP 3", f'US charge (+{_pct(m["tp_pct"])} TP)', _inr(m["us_yr"]),
         f'{_inr(m["us_mo"])} / mo', "step-3"),
        ("STEP 4", f'USD @ ₹{_rate(m["fx_rate"])}', _usd(m["usd_yr"]),
         f'{_usd(m["usd_mo"])} / mo', "step-4"),
    ]
    return '<div class="ic-stats">' + "".join(
        f'<a class="ic-stat" href="#{anchor}">'
        f'<div class="ic-step">{step}</div>'
        f'<div class="ic-stat-value">{value}</div>'
        f'<div class="ic-stat-sub">{sub}</div>'
        f'<div class="ic-stat-label">{label}</div></a>'
        for step, label, value, sub, anchor in cards) + '</div>'


def _ladder(c, m):
    lpa = _float(c.get("lpa"))
    rungs = [
        ("step-1", "1", "Offer (CTC)",
         f'{lpa:g} LPA × {_inr(LAKH)} = {_inr(m["offer_yr"])} / yr',
         "One lakh is ₹100,000. Taken as CTC, the India convention.",
         _inr(m["offer_yr"])),
        ("step-2", "2", "India entity cost",
         f'{_inr(m["offer_yr"])} × {1 + m["burden_pct"] / 100:.4g} '
         f'= {_inr(m["india_yr"])} / yr',
         f'Insurance &amp; extras at {_pct(m["burden_pct"])} — what the India '
         f'entity actually spends.',
         _inr(m["india_yr"])),
        ("step-3", "3", "US charge (transfer pricing)",
         f'{_inr(m["india_yr"])} × {1 + m["tp_pct"] / 100:.4g} '
         f'= {_inr(m["us_yr"])} / yr',
         f'The {_pct(m["tp_pct"])} markup the US entity pays the India entity.',
         _inr(m["us_yr"])),
        ("step-4", "4", "USD view",
         f'{_inr(m["us_yr"])} ÷ {_rate(m["fx_rate"])} = {_usd(m["usd_yr"])} / yr',
         f'{_usd(m["usd_mo"])} a month. The offer itself is '
         f'{_usd(m["usd_offer_yr"])}, the India cost {_usd(m["usd_india_yr"])}.',
         _usd(m["usd_yr"])),
    ]
    return '<div class="ic-ladder">' + "".join(
        f'<div class="ic-rung" id="{anchor}">'
        f'<div class="ic-rung-n">{n}</div>'
        f'<div class="ic-rung-main">'
        f'<div class="ic-rung-name">{name}</div>'
        f'<div class="ic-rung-math">{math}</div>'
        f'<div class="ic-rung-why">{why}</div></div>'
        f'<div class="ic-rung-out">{out}</div></div>'
        for anchor, n, name, math, why, out in rungs) + '</div>'


def _table(cands, settings, focus_id):
    head = ('<tr><th>Candidate</th><th>Offer</th><th>India cost</th>'
            '<th>US charge</th><th>USD / yr</th><th>USD / mo</th><th></th></tr>')
    rows = ""
    for c in cands:
        m = compute_for(c, settings)
        on = c.get("id") == focus_id
        role = _esc(c.get("role") or "")
        loc = _esc(c.get("location") or DEFAULT_LOCATION)
        bits = " · ".join(x for x in (role, loc) if x)
        ov = c.get("burden_override")
        if ov is not None:
            bits += f' · burden {_pct(_float(ov))}'
        rows += (
            f'<tr class="{"ic-row--on" if on else ""}">'
            f'<td data-label="Candidate"><div>'
            f'<div class="ic-name">{_esc(c.get("name", ""))}</div>'
            f'<div class="ic-sub">{bits}</div></div></td>'
            # One block, not two loose children: on a phone the cell is a flex
            # row with its own label, and a bare "24 LPA" beside a div lands in
            # the middle of the card instead of against the right edge.
            f'<td data-label="Offer" class="ic-num"><div>'
            f'{_float(c.get("lpa")):g} LPA'
            f'<div class="ic-sub">{_inr(m["offer_yr"])}</div></div></td>'
            f'<td data-label="India cost" class="ic-num">{_inr(m["india_yr"])}</td>'
            f'<td data-label="US charge" class="ic-num">{_inr(m["us_yr"])}</td>'
            f'<td data-label="USD / yr" class="ic-num">{_usd(m["usd_yr"])}</td>'
            f'<td data-label="USD / mo" class="ic-num">{_usd(m["usd_mo"])}</td>'
            f'<td data-label=""><div class="ic-acts">'
            + ('' if on else
               f'<a class="btn btn-sm btn-ghost" href="/indiacomp?focus={c["id"]}">'
               f'Break down</a>')
            + f'<a class="btn btn-sm btn-secondary" '
              f'href="/indiacomp?focus={c["id"]}&amp;edit={c["id"]}">Edit</a>'
            f'</div></td></tr>')
    return (f'<div class="ic-table-card"><table class="wf-cardtable">'
            f'<thead>{head}</thead><tbody>{rows}</tbody></table></div>')


def _edit_sheet(c, settings):
    """The shared modal, which the global stylesheet turns into a bottom sheet
    below 768px — the same treatment every popover in Wayfinder gets."""
    ov = c.get("burden_override")
    return (
        f'<div class="wf-modal-backdrop">'
        f'<div class="wf-modal">'
        f'<div class="wf-modal-title">Edit {_esc(c.get("name", "candidate"))}</div>'
        f'<form method="POST" action="/indiacomp/update">'
        f'<input type="hidden" name="id" value="{c["id"]}">'
        f'<div class="ic-sheet-grid">'
        + _field("edit", "Name", "name", c.get("name", ""))
        + _field("edit", "Role", "role", c.get("role", ""))
        + _field("edit", "Offer LPA", "lpa", f'{_float(c.get("lpa")):g}',
                 kind="number", step="0.1")
        + _field("edit", "Location", "location", c.get("location", DEFAULT_LOCATION))
        + _field("edit", "Burden % override", "burden_override",
                 "" if ov is None else f"{_float(ov):g}", kind="number", step="0.1",
                 placeholder=f'{settings["burden_pct"]:g}',
                 hint="Blank uses the shared assumption")
        + _field("edit", "Note", "note", c.get("note", ""), span=True)
        + '</div>'
        + '<div class="wf-modal-actions" style="margin-top:16px">'
          '<a class="btn btn-ghost" href="/indiacomp">Cancel</a>'
          '<button class="btn btn-primary" type="submit">Save</button>'
          '</div></form>'
        + f'<div class="wf-modal-actions ic-danger-row">'
          f'<form method="POST" action="/indiacomp/delete">'
          f'<input type="hidden" name="id" value="{c["id"]}">'
          f'<button class="btn btn-sm btn-danger" type="submit">'
          f'Delete this candidate</button></form></div>'
        + '</div></div>')


def render(user, focus="", edit=""):
    settings, cands = load(user)
    by_id = {c.get("id"): c for c in cands}
    focused = by_id.get(focus) or (cands[-1] if cands else None)

    if focused:
        m = compute_for(focused, settings)
        who = _esc(focused.get("name", ""))
        role = _esc(focused.get("role") or "")
        loc = _esc(focused.get("location") or DEFAULT_LOCATION)
        meta = " · ".join(x for x in (role, loc) if x)
        body = (
            f'<div class="ic-section-head">'
            f'<div class="ic-h2">Cost ladder</div>'
            f'<div class="ic-who">{who}{" — " + meta if meta else ""}</div></div>'
            + _stage_cards(m)
            + _ladder(focused, m)
            + f'<div class="ic-section-head"><div class="ic-h2">'
              f'Candidates ({len(cands)})</div>'
              f'<div class="ic-who">Every row uses the assumptions above</div></div>'
            + _table(cands, settings, focused.get("id")))
    else:
        body = (
            '<div class="ic-empty">'
            '<div class="ic-empty-icon">🧮</div>'
            '<div class="ic-empty-title">No candidates yet</div>'
            # The intake is already open on an empty page, so this points at the
            # form rather than telling you to open what is open (QA 2026-08-08).
            '<div class="ic-empty-sub">Enter a name and the offer in LPA in the '
            'form above — the four stages appear as soon as you add it.</div>'
            '</div>')

    sheet = _edit_sheet(by_id[edit], settings) if edit in by_id else ""

    return f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<title>India Comp · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css">
<style>{STYLE}</style></head>
<body>
<nav>
  <a href="/indiacomp" class="nav-brand">🧮 India Comp</a>
</nav>
<div class="ic-wrap">
  <div class="ic-head">
    <div class="ic-title">India Comp</div>
    <div class="ic-lede">An offer quoted in LPA, carried through employer burden
      and the transfer-pricing markup to the dollar figure a review actually
      needs. The arithmetic is written out at every step.</div>
  </div>
  {_assumptions(settings, not cands)}
  {_intake(not cands, settings)}
  {body}
</div>
{sheet}
</body></html>'''


def handle(method, path, body, ctx=None):
    user = (ctx or {}).get("user", "guest")

    if method == "POST":
        if path == "/indiacomp/add":
            cid = add(user, {k: _first(body, k) for k in
                             ("name", "role", "location", "lpa",
                              "burden_override", "note")})
            return ("redirect", f"/indiacomp?focus={cid}" if cid else "/indiacomp")
        if path == "/indiacomp/update":
            cid = _first(body, "id")
            update(user, cid, {k: _first(body, k) for k in
                               ("name", "role", "location", "lpa",
                                "burden_override", "note")})
            return ("redirect", f"/indiacomp?focus={cid}")
        if path == "/indiacomp/delete":
            delete(user, _first(body, "id"))
            return ("redirect", "/indiacomp")
        if path == "/indiacomp/settings":
            save_settings(user, {k: _first(body, k)
                                 for k in ("tp_pct", "burden_pct", "fx_rate")})
            return ("redirect", "/indiacomp")
        return ("redirect", "/indiacomp")

    if path == "/indiacomp":
        return ("html", render(user, _first(body, "focus"), _first(body, "edit")))

    return ("html", "<h2>404 Not Found</h2>")
