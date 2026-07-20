"""Notebot — Teams meeting recorder & minutes (LOCAL ONLY).

Recording runs on this machine (WASAPI loopback + mic via a Windows-side
python), audio chunks land on the local C: drive and transcripts/minutes in
~/labs/teams-notebot. On any non-WSL host every route renders a notice —
meeting audio must never reach the server.
"""
import html
import os
import re
import shutil
import subprocess
from datetime import datetime

META = {
    "name": "Notebot",
    "path": "/notebot",
    "icon": "🎙️",
    "description": "Teams 회의 녹음·전사·회의록 (로컬 전용)",
    "admin_only": True,
}

LAB = os.path.expanduser("~/labs/teams-notebot")
MEETINGS = os.path.join(LAB, "meetings")
WAV_BASE = "/mnt/c/Users/Jongha Kang/AppData/Local/Notebot"
STATE_FILE = os.path.join(LAB, ".current")
PROC_FILE = os.path.join(LAB, ".processing")
SID_RE = re.compile(r"^\d{8}_\d{4}$")
WAV_RE = re.compile(r"^(chunk|mic)_\d{3}\.wav$")
BYTES_PER_SEC = 48000 * 2 * 2  # 48kHz stereo 16-bit


def _is_local() -> bool:
    return os.path.exists("/mnt/c")


if not _is_local():
    META["home_href"] = "http://localhost:8080/notebot"


def esc(s):
    return html.escape(str(s or ""))


def _read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError:
        return ""


def _state():
    """idle | (recording, sid) | (processing, sid)

    The processing marker wins over .current: stop click writes the marker
    immediately, while the background stop script only clears .current after
    the recorder confirms — without this order the UI would keep showing
    "recording" for up to ~30s after the user hit Stop."""
    sid = _read(PROC_FILE).strip()
    if sid:
        if os.path.exists(os.path.join(MEETINGS, sid, "minutes.md")):
            os.remove(PROC_FILE)
            return ("idle", None)
        # Orphan marker: stop crashed before any session data landed, so
        # nothing will ever produce minutes — clear instead of spinning.
        if not os.path.isdir(os.path.join(MEETINGS, sid)):
            os.remove(PROC_FILE)
            return ("idle", None)
        return ("processing", sid)
    sid = _read(STATE_FILE).strip()
    if sid:
        return ("recording", sid)
    return ("idle", None)


def _wavs(sid):
    d = os.path.join(WAV_BASE, sid)
    out = []
    if os.path.isdir(d):
        for f in sorted(os.listdir(d)):
            if WAV_RE.match(f):
                out.append((f, os.path.getsize(os.path.join(d, f))))
    return out


def _sessions():
    sids = set()
    if os.path.isdir(MEETINGS):
        sids.update(x for x in os.listdir(MEETINGS) if SID_RE.match(x))
    if os.path.isdir(WAV_BASE):
        sids.update(x for x in os.listdir(WAV_BASE) if SID_RE.match(x))
    out = []
    for sid in sorted(sids, reverse=True):
        mdir = os.path.join(MEETINGS, sid)
        wavs = _wavs(sid)
        out.append({
            "sid": sid,
            "title": _read(os.path.join(mdir, "title.txt")).strip() or "meeting",
            "when": datetime.strptime(sid, "%Y%m%d_%H%M"),
            "minutes": os.path.exists(os.path.join(mdir, "minutes.md")),
            "transcript": os.path.exists(os.path.join(mdir, "transcript.txt")),
            "wav_bytes": sum(s for _, s in wavs),
            "wav_n": len(wavs),
        })
    return out


def _fmt_size(b):
    if b >= 1 << 30:
        return f"{b / (1 << 30):.1f} GB"
    if b >= 1 << 20:
        return f"{b / (1 << 20):.0f} MB"
    return f"{b // 1024} KB" if b else "—"


def _fmt_dur(b):
    secs = b // BYTES_PER_SEC
    return f"~{secs // 60}m" if secs >= 60 else f"~{secs}s" if secs else ""


def _md_html(md):
    """Tiny markdown renderer: headings, bold, bullet lists, paragraphs."""
    out, in_list = [], False
    for line in md.splitlines():
        s = esc(line.rstrip())
        s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
        m = re.match(r"^(#{1,4})\s+(.*)", s)
        if m:
            if in_list:
                out.append("</ul>")
                in_list = False
            lvl = min(len(m.group(1)) + 1, 5)
            out.append(f"<h{lvl}>{m.group(2)}</h{lvl}>")
        elif re.match(r"^\s*[-*]\s+", s):
            if not in_list:
                out.append("<ul>")
                in_list = True
            out.append("<li>" + re.sub(r"^\s*[-*]\s+", "", s) + "</li>")
        elif s.strip():
            if in_list:
                out.append("</ul>")
                in_list = False
            out.append(f"<p>{s}</p>")
    if in_list:
        out.append("</ul>")
    return "\n".join(out)


_TR_LINE = re.compile(r"^\[c(\d+)\s+([\d.]+)s (나|상대)\] ?(.*)$")


def _transcript_html(transcript):
    """Speaker-labelled transcript: '[cN <sec>s 나|상대] text' lines become
    badge rows (나 = mic track, 상대 = speaker loopback — physically separate
    recordings, so the attribution is exact). Unparsable lines pass through."""
    rows = []
    for ln in transcript.splitlines():
        if not ln.strip():
            continue
        m = _TR_LINE.match(ln)
        if not m:
            rows.append(f'<div class="nb-tr"><span class="nb-tr-txt">{esc(ln)}</span></div>')
            continue
        chunk, start, who, text = m.groups()
        secs = int(float(start))
        cls, icon = ("me", "🎤 나") if who == "나" else ("other", "🔊 상대")
        rows.append(
            f'<div class="nb-tr {cls}"><span class="nb-tr-who">{icon}</span>'
            f'<span class="nb-tr-t">c{chunk}·{secs // 60}:{secs % 60:02d}</span>'
            f'<span class="nb-tr-txt">{esc(text)}</span></div>')
    return "".join(rows)


CSS = """
.nb-wrap{max-width:860px;margin:0 auto}
.nb-stats{display:grid;grid-template-columns:repeat(3,1fr);gap:10px;margin:18px 0}
.stat-card{background:var(--surface-2,var(--surface));border:1px solid var(--border);border-radius:12px;padding:14px 18px;text-align:center}
.stat-value{font-size:1.5rem;font-weight:700}
.stat-label{color:var(--text-muted);font-size:.8rem;margin-top:2px}
.nb-rec{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:18px;margin-bottom:22px}
.nb-rec form{display:flex;gap:8px;flex-wrap:wrap}
.nb-rec input[name=title]{flex:1;min-width:180px;padding:11px 14px;border-radius:10px;border:1px solid var(--border);background:var(--surface-2,var(--surface));color:var(--text)}
.nb-btn{padding:11px 22px;border-radius:10px;border:0;font-weight:700;cursor:pointer}
.nb-start{background:var(--accent);color:#04121f}
.nb-stop{background:#ef4444;color:#fff}
.nb-ghost{background:transparent;border:1px solid var(--border);color:var(--text-muted)}
.nb-danger{background:transparent;border:1px solid #ef444455;color:#ef4444}
.nb-live{display:flex;align-items:center;gap:12px;flex-wrap:wrap}
.nb-dot{width:12px;height:12px;border-radius:50%;background:#ef4444;animation:nbp 1.2s infinite}
@keyframes nbp{50%{opacity:.25}}
.nb-list{list-style:none;padding:0;display:flex;flex-direction:column;gap:8px}
.nb-row{display:flex;align-items:center;gap:12px;background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:12px 16px;flex-wrap:wrap}
.nb-row a.nb-title{font-weight:600;color:var(--text);text-decoration:none;flex:1;min-width:150px}
.nb-meta{color:var(--text-muted);font-size:.82rem;display:flex;gap:10px;flex-wrap:wrap;align-items:center}
.nb-badge{font-size:.72rem;padding:2px 8px;border-radius:999px;border:1px solid var(--border);color:var(--text-muted)}
.nb-badge.ok{border-color:#22c55e55;color:#22c55e}
.nb-audio{display:flex;flex-direction:column;gap:8px;margin:10px 0}
.nb-audio .row{display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.nb-audio audio{height:36px;max-width:100%}
.nb-doc{background:var(--surface);border:1px solid var(--border);border-radius:12px;padding:18px 22px;margin:14px 0;overflow-x:auto}
.nb-doc pre{white-space:pre-wrap;font-size:.85rem;color:var(--text-muted)}
.nb-tr{display:flex;gap:8px;align-items:baseline;padding:3px 0;font-size:.85rem}
.nb-tr-who{flex:0 0 56px;font-weight:700;font-size:.72rem;white-space:nowrap}
.nb-tr.me .nb-tr-who{color:var(--accent)}
.nb-tr.other .nb-tr-who{color:var(--text-muted)}
.nb-tr-t{flex:0 0 60px;color:var(--text-muted);opacity:.7;font-size:.7rem;white-space:nowrap}
.nb-tr-txt{flex:1;min-width:0}
.nb-tr.other .nb-tr-txt{color:var(--text-muted)}
@media(max-width:640px){.nb-tr{flex-wrap:wrap}.nb-tr-t{display:none}}
@media(max-width:640px){.nb-stats{grid-template-columns:repeat(3,1fr)}.nb-row{align-items:flex-start;flex-direction:column;gap:6px}}
"""


def _page(title, body, poll=False):
    js = ""
    if poll:
        js = """<script>
setInterval(async()=>{try{const r=await fetch('/notebot/state');const j=await r.json();
if(j.state!==document.body.dataset.nbstate)location.reload();}catch(e){}},4000);
</script>"""
    return f"""<!doctype html><html lang="ko"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(title)}</title><link rel="stylesheet" href="/static/style.css">
<style>{CSS}</style></head>
<body data-nbstate="{body[0]}">
<nav><span class="nav-brand">🎙️ Notebot</span>
<span class="nav-user"><a class="nav-back" href="/">← Home</a></span></nav>
<div class="container nb-wrap">{body[1]}</div>{js}</body></html>"""


def _recorder_card(state, sid):
    if state == "recording":
        started = datetime.strptime(sid, "%Y%m%d_%H%M")
        mins = int((datetime.now() - started).total_seconds() // 60)
        return f"""<div class="nb-rec"><div class="nb-live">
<span class="nb-dot"></span><b>Recording…</b>
<span class="nb-meta">{esc(_read(os.path.join(MEETINGS, sid, 'title.txt')).strip() or 'meeting')} · started {started:%H:%M} ({mins} min)</span>
<form method="post" action="/notebot/stop" style="margin-left:auto">
<button class="nb-btn nb-stop">⏹ Stop &amp; make minutes</button></form></div></div>"""
    if state == "processing":
        return f"""<div class="nb-rec"><div class="nb-live">
<span class="nb-dot" style="background:#f59e0b"></span><b>Processing…</b>
<span class="nb-meta">transcribing + writing minutes for {esc(sid)} — this page refreshes itself</span>
<form method="post" action="/notebot/reset" style="margin-left:auto"
 onsubmit="return confirm('Clear the processing state? Only do this if it looks stuck.')">
<button class="nb-btn nb-ghost">reset</button></form></div></div>"""
    return """<div class="nb-rec"><form method="post" action="/notebot/start">
<input name="title" placeholder="Meeting title…" autocomplete="off" maxlength="80">
<button class="nb-btn nb-start">⏺ Start recording</button></form></div>"""


def render_home():
    state, sid = _state()
    sess = _sessions()
    total_wav = sum(s["wav_bytes"] for s in sess)
    rows = []
    for s in sess:
        badges = []
        badges.append('<span class="nb-badge ok">minutes</span>' if s["minutes"]
                      else '<span class="nb-badge">no minutes</span>')
        if s["transcript"]:
            badges.append('<span class="nb-badge ok">transcript</span>')
        wav = (f'{_fmt_size(s["wav_bytes"])} · {_fmt_dur(s["wav_bytes"])}'
               if s["wav_n"] else "no audio")
        rows.append(f"""<li class="nb-row">
<a class="nb-title" href="/notebot/s/{s['sid']}">{esc(s['title'])}</a>
<span class="nb-meta">{s['when']:%b %d %H:%M} · {wav} {' '.join(badges)}</span>
<form method="post" action="/notebot/delete" onsubmit="return confirm('Delete this session — audio, transcript and minutes? This cannot be undone.')">
<input type="hidden" name="sid" value="{s['sid']}">
<button class="nb-btn nb-danger" style="padding:6px 12px">Delete</button></form></li>""")
    body = f"""
<h1>🎙️ Notebot</h1>
<p style="color:var(--text-muted);margin-top:-6px">One-click Teams meeting recorder — audio stays on this machine.</p>
<div class="nb-stats">
<div class="stat-card"><div class="stat-value">{len(sess)}</div><div class="stat-label">Sessions</div></div>
<div class="stat-card"><div class="stat-value">{_fmt_size(total_wav)}</div><div class="stat-label">Audio on disk</div></div>
<div class="stat-card"><div class="stat-value">{'🔴' if state == 'recording' else '⏳' if state == 'processing' else '🟢'}</div><div class="stat-label">{state.title()}</div></div>
</div>
{_recorder_card(state, sid)}
<ul class="nb-list">{''.join(rows) or '<li class="nb-row" style="color:var(--text-muted)">No sessions yet — hit Start when your meeting begins.</li>'}</ul>"""
    return _page("Notebot", (state, body), poll=state in ("recording", "processing"))


def render_session(sid):
    state, cur = _state()
    mdir = os.path.join(MEETINGS, sid)
    title = _read(os.path.join(mdir, "title.txt")).strip() or "meeting"
    when = datetime.strptime(sid, "%Y%m%d_%H%M")
    minutes = _read(os.path.join(mdir, "minutes.md"))
    transcript = _read(os.path.join(mdir, "transcript.txt"))
    wavs = _wavs(sid)

    audio = ""
    if wavs:
        rows = "".join(
            f"""<div class="row"><span class="nb-meta" style="min-width:110px">{'🔊 others' if f.startswith('chunk') else '🎤 me'} · {f.split('_')[1].split('.')[0]} · {_fmt_size(size)}</span>
<audio controls preload="none" src="/notebot/audio/{sid}/{f}"></audio></div>"""
            for f, size in wavs)
        audio = f"""<h3>Audio ({_fmt_size(sum(s for _, s in wavs))})</h3>
<div class="nb-audio">{rows}</div>
<form method="post" action="/notebot/delete_wav" onsubmit="return confirm('Delete the audio files only? Transcript and minutes are kept.')">
<input type="hidden" name="sid" value="{sid}">
<button class="nb-btn nb-danger" style="padding:6px 12px">Delete audio only</button></form>"""

    minutes_html = (f'<div class="nb-doc">{_md_html(minutes)}</div>' if minutes
                    else '<p style="color:var(--text-muted)">No minutes yet.</p>')
    tr_html = (f'<details><summary style="cursor:pointer;color:var(--text-muted)">Transcript ({len(transcript.splitlines())} lines)</summary>'
               f'<div class="nb-doc">{_transcript_html(transcript)}</div></details>' if transcript else "")

    body = f"""
<p><a href="/notebot" style="color:var(--text-muted);text-decoration:none">← All sessions</a></p>
<h1>{esc(title)}</h1>
<p style="color:var(--text-muted);margin-top:-6px">{when:%Y-%m-%d %H:%M} · {sid}</p>
<h3>Minutes</h3>{minutes_html}
{tr_html}
{audio}
<form method="post" action="/notebot/delete" style="margin-top:18px" onsubmit="return confirm('Delete this whole session — audio, transcript and minutes?')">
<input type="hidden" name="sid" value="{sid}">
<button class="nb-btn nb-danger">Delete session</button></form>"""
    return _page(f"Notebot · {title}", (state, body))


def render_local_only():
    return _page("Notebot", ("idle", """
<h1>🎙️ Notebot</h1>
<div class="nb-rec"><b>Local-only app.</b>
<p style="color:var(--text-muted)">Recording and meeting audio live on Jongha's machine and never reach this server.
Open <a href="http://localhost:8080/notebot">localhost:8080/notebot</a> on that machine instead.</p></div>"""))


def _one(body, key):
    v = body.get(key, "")
    return (v[0] if isinstance(v, list) else v).strip()


def handle(method, path, body, ctx):
    if not _is_local():
        if method != "GET":
            return ("json", {"error": "local-only app"})
        return ("html", render_local_only())

    if method == "GET" and path == "/notebot":
        return ("html", render_home())

    if method == "GET" and path == "/notebot/state":
        state, sid = _state()
        return ("json", {"state": state, "sid": sid})

    m = re.match(r"^/notebot/s/(\d{8}_\d{4})$", path)
    if method == "GET" and m:
        return ("html", render_session(m.group(1)))

    m = re.match(r"^/notebot/audio/(\d{8}_\d{4})/((?:chunk|mic)_\d{3}\.wav)$", path)
    if method == "GET" and m:
        fpath = os.path.join(WAV_BASE, m.group(1), m.group(2))
        if os.path.exists(fpath):
            with open(fpath, "rb") as f:
                return ("binary", f.read(), "audio/wav")
        return ("html", "<h2>404 Not Found</h2>")

    if method == "POST" and path == "/notebot/start":
        state, _sid = _state()
        if state == "idle":
            title = _one(body, "title") or "meeting"
            from services._wsl_interop import interop_env
            subprocess.run(["bash", os.path.join(LAB, "notebot.sh"), "start", title],
                           capture_output=True, timeout=60, env=interop_env())
        return ("redirect", "/notebot")

    if method == "POST" and path == "/notebot/stop":
        state, sid = _state()
        if state == "recording":
            with open(PROC_FILE, "w") as f:
                f.write(sid)
            os.makedirs(os.path.join(MEETINGS, sid), exist_ok=True)
            log = open(os.path.join(MEETINGS, sid, "process.log"), "w")
            from services._wsl_interop import interop_env
            subprocess.Popen(["bash", os.path.join(LAB, "notebot.sh"), "stop"],
                             stdout=log, stderr=subprocess.STDOUT,
                             start_new_session=True, env=interop_env())
        return ("redirect", "/notebot")

    if method == "POST" and path == "/notebot/reset":
        if os.path.exists(PROC_FILE):
            os.remove(PROC_FILE)
        return ("redirect", "/notebot")

    if method == "POST" and path in ("/notebot/delete", "/notebot/delete_wav"):
        sid = _one(body, "sid")
        if SID_RE.match(sid):
            state, cur = _state()
            if cur != sid:  # never delete the live session
                shutil.rmtree(os.path.join(WAV_BASE, sid), ignore_errors=True)
                if path == "/notebot/delete":
                    shutil.rmtree(os.path.join(MEETINGS, sid), ignore_errors=True)
        return ("redirect", "/notebot")

    return ("html", "<h2>404 Not Found</h2>")
