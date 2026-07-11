# Card Converter — presentation layer (renderers + HTML/CSS/JS consts).
# Split out of cardconv.py so logic edits don't re-read ~2,800 render lines.
from services._cardconv_core import *  # noqa: F401,F403

def _render_drive_connect(username: str, auth_url: str, requested: bool = False) -> str:
    from server import CSS_VER
    requested_banner = (
        '<div style="background:rgba(34,197,94,.12);border:1px solid rgba(34,197,94,.4);'
        'color:#16a34a;border-radius:8px;padding:10px 14px;font-size:.85rem">'
        '✅ Tester registration requested. Try again once the admin approves it.</div>'
        if requested else ''
    )
    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔗 Connect Google Drive · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
</head><body>
<nav>
  <span class="nav-brand">🔗 Connect Google Drive</span>
  <span class="nav-user"><a href="/cardconv/ledger" class="nav-back">← Back to Ledger</a></span>
</nav>
<div class="container" style="max-width:640px">
  <div class="notepad-card">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">Authorize Google Drive Access</span>
    </div>
    <div class="notepad-body" style="padding:28px;display:flex;flex-direction:column;gap:20px">
      {requested_banner}
      <ol style="color:var(--text-muted);font-size:.88rem;line-height:2.2;padding-left:22px">
        <li>Click the button below to open Google authorization page</li>
        <li>Sign in and grant <b style="color:var(--text)">Drive file access</b></li>
        <li>Copy the authorization code shown on that page</li>
        <li>Paste it in the field below and click Confirm</li>
      </ol>
      <a href="{auth_url}" target="_blank" class="btn btn-primary" style="width:fit-content">
        🔗 Open Google Authorization Page
      </a>
      <form method="POST" action="/cardconv/drive/auth" style="display:flex;flex-direction:column;gap:12px">
        <div style="display:flex;flex-direction:column;gap:6px">
          <label style="font-size:.72rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.06em">Authorization Code</label>
          <input type="text" name="code" placeholder="Paste the code from Google here..." required
            style="padding:10px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface-2);color:var(--text);font-size:.88rem;outline:none">
        </div>
        <button type="submit" class="btn btn-accent" style="width:fit-content">✅ Confirm &amp; Connect</button>
      </form>
      <details style="border-top:1px solid var(--border);padding-top:16px">
        <summary style="cursor:pointer;font-size:.82rem;color:var(--text-muted)">
          🚫 Seeing an "Access blocked / has not completed verification" error?
        </summary>
        <div style="margin-top:12px;display:flex;flex-direction:column;gap:10px">
          <p style="font-size:.82rem;color:var(--text-muted);line-height:1.7">
            This app is in Google testing mode, so only registered accounts can connect.
            Leave the <b style="color:var(--text)">Google email</b> you want to connect and the admin will register it as a tester.
          </p>
          <form method="POST" action="/cardconv/drive/request-tester" style="display:flex;gap:8px;flex-wrap:wrap">
            <input type="email" name="tester_email" required placeholder="you@gmail.com"
              style="flex:1;min-width:200px;padding:10px 14px;border:1px solid var(--border);border-radius:8px;background:var(--surface-2);color:var(--text);font-size:.88rem;outline:none">
            <button type="submit" class="btn btn-primary" style="width:fit-content">📩 Request tester access</button>
          </form>
        </div>
      </details>
    </div>
  </div>
</div>
</body></html>'''


def _render_drive_connected(folder_url: str = "") -> str:
    from server import CSS_VER
    folder_cta = (
        f'<a href="{folder_url}" target="_blank" class="btn btn-primary" style="width:fit-content">'
        f'📂 Open your Receipts folder</a>'
        if folder_url else ''
    )
    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>✅ Google Drive Connected · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
</head><body>
<nav>
  <span class="nav-brand">✅ Google Drive Connected</span>
  <span class="nav-user"><a href="/cardconv/ledger" class="nav-back">← Back to Ledger</a></span>
</nav>
<div class="container" style="max-width:640px">
  <div class="notepad-card">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">You're all set</span>
    </div>
    <div class="notepad-body" style="padding:28px;display:flex;flex-direction:column;gap:18px">
      <p style="font-size:1rem;color:var(--text);line-height:1.6">
        🎉 Your <b>Wayfinder &rsaquo; Receipts</b> folder is ready on Google Drive.
      </p>
      <ol style="color:var(--text-muted);font-size:.9rem;line-height:2;padding-left:22px">
        <li>Drop your receipt images or PDFs into the <b style="color:var(--text)">Receipts</b> folder</li>
        <li>Come back here and click <b style="color:var(--text)">Sync</b> to import &amp; OCR them</li>
        <li>Review the results and add them to your Ledger</li>
      </ol>
      <div style="display:flex;gap:12px;flex-wrap:wrap">
        {folder_cta}
        <a href="/cardconv/ledger" class="btn btn-accent" style="width:fit-content">Go to Ledger &amp; Sync →</a>
      </div>
    </div>
  </div>
</div>
</body></html>'''


# ── Shared tab bar ───────────────────────────────────────────────────────────

_CC_TAB_CSS = (
    # top is set by script in _tab_bar to the live nav height, so the pill
    # pins below the sticky site nav instead of sliding over it (nav z=100).
    ".cc-tabbar{position:sticky;top:52px;z-index:90;background:var(--bg-deep);padding:12px 0 10px;margin:-12px 0 10px}"
    # Collapsible section (Register Receipts etc.) — mobile-first, closed by default
    ".cc-collapse{background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);margin-bottom:16px;overflow:hidden}"
    ".cc-collapse>summary{padding:12px 16px;font-size:.82rem;font-weight:700;color:var(--text);cursor:pointer;"
    "user-select:none;list-style:none;display:flex;align-items:center;gap:8px}"
    ".cc-collapse>summary::-webkit-details-marker{display:none}"
    ".cc-collapse>summary::before{content:'▸';font-size:.7rem;color:var(--text-muted);transition:transform .15s}"
    ".cc-collapse[open]>summary::before{transform:rotate(90deg)}"
    ".cc-collapse-body{padding:4px 16px 14px}"
    ".cc-tabs{display:inline-flex;align-items:center;gap:2px;padding:3px;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);flex-wrap:wrap;max-width:100%}"
    ".cc-tab{display:inline-flex;align-items:center;padding:7px 16px;font-size:.82rem;font-weight:600;color:var(--text-muted);border-radius:var(--radius-sm);text-decoration:none;transition:background .15s,color .15s}"
    ".cc-tab:hover{color:var(--text)}"
    ".cc-tab.active{background:var(--accent);color:var(--on-accent)}"
    ".tab-badge{display:inline-flex;align-items:center;justify-content:center;min-width:16px;height:16px;"
    "background:#ef4444;border-radius:8px;font-size:.62rem;font-weight:700;color:#fff;padding:0 4px;"
    "margin-left:5px;vertical-align:middle}"
    # Workflow step bar
    ".cc-wf-bar{display:flex;align-items:center;background:var(--surface-2);"
    "border:1px solid var(--border);border-radius:var(--radius-md);"
    "padding:0 10px 0 8px;margin-bottom:16px;height:36px}"
    ".cc-wf-close{margin-left:auto;flex-shrink:0;background:none;border:none;"
    "color:var(--text-muted);cursor:pointer;font-size:.85rem;"
    "padding:2px 6px;border-radius:4px;line-height:1}"
    ".cc-wf-close:hover{color:var(--text);background:var(--surface-3)}"
    ".cc-wf-steps{display:flex;align-items:center;flex:1;min-width:0;overflow:hidden}"
    ".cc-wf-step{display:flex;align-items:center;gap:5px;padding:0 6px;"
    "font-size:.74rem;color:var(--text-muted);white-space:nowrap;flex-shrink:0}"
    ".cc-wf-step .sn{display:inline-flex;align-items:center;justify-content:center;"
    "width:18px;height:18px;border-radius:50%;border:1.5px solid currentColor;"
    "font-size:.6rem;font-weight:700;flex-shrink:0}"
    ".cc-wf-step.wf-active{color:var(--text);font-weight:600}"
    ".cc-wf-step.wf-active .sn{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}"
    ".cc-wf-step.wf-done .sn{background:#22c55e;border-color:#22c55e;color:#fff}"
    ".cc-wf-step.wf-done{color:var(--text-muted)}"
    ".cc-wf-sep{color:var(--border);font-size:.65rem;flex-shrink:0;padding:0 2px}"
    "@media(max-width:600px){.cc-wf-label{display:none}}"
    # Inline info tooltip
    ".cc-info-wrap{position:relative;display:inline-flex;align-items:center;vertical-align:middle}"
    ".cc-info{display:inline-flex;align-items:center;justify-content:center;"
    "width:14px;height:14px;border-radius:50%;font-size:.6rem;font-weight:700;"
    "color:var(--text-muted);cursor:pointer;border:1px solid var(--border);"
    "margin-left:6px;flex-shrink:0;line-height:1;user-select:none}"
    ".cc-info:hover{color:var(--accent);border-color:var(--accent)}"
    ".cc-tip{display:none;position:absolute;z-index:200;"
    "background:var(--surface-3);border:1px solid var(--border);"
    "border-radius:var(--radius-md);padding:10px 12px;font-size:.78rem;"
    "color:var(--text);max-width:280px;width:max-content;"
    "box-shadow:0 4px 16px rgba(0,0,0,.18);line-height:1.5;"
    "white-space:normal;text-align:left;top:calc(100% + 6px);left:0}"
    ".cc-tip.tip-right{left:auto;right:0}"
)


def _tab_bar(active: str, user: str) -> str:
    """Shared Card Converter tab bar. active ∈ ledger|convert|review|history|keywords."""
    unmatched_n = _ledger_stats(_ledger_entries(user))["unmatched"]
    ledger_badge = f'<span class="tab-badge">{unmatched_n}</span>' if unmatched_n else ''
    staged_n = len(_load_ocr_staging(user).get("entries", []))
    ocr_badge = f'<span class="tab-badge" style="background:#f59e0b;cursor:pointer" onclick="openOcrModal();return false;">{staged_n}</span>' if staged_n else ''
    tabs = [
        ("ledger",   "/cardconv/ledger",   "Receipt Ledger" + ledger_badge + ocr_badge),
        ("convert",  "/cardconv/convert",  "Convert"),
        ("review",   "/cardconv/review",   "Review"),
        ("history",  "/cardconv/history",  "History"),
        ("keywords", "/cardconv/keywords", "Keywords"),
    ]
    out = ['<div class="cc-tabs">']
    for key, href, label in tabs:
        cls = "cc-tab active" if key == active else "cc-tab"
        out.append(f'<a href="{href}" class="{cls}">{label}</a>')
    out.append('</div>')
    # Sticky wrapper: the tab pill stays pinned while the page scrolls, and its
    # full-width ground hides content passing behind it. The script keeps the
    # pin offset equal to the actual nav height (it changes when nav wraps).
    sync_js = (
        '<script>(function(){var n=document.querySelector("nav"),'
        't=document.querySelector(".cc-tabbar");if(!n||!t)return;'
        'var f=function(){t.style.top=n.offsetHeight+"px"};'
        'f();window.addEventListener("resize",f);})();</script>'
    )
    return '<div class="cc-tabbar">' + "".join(out) + '</div>' + sync_js + _workflow_bar(active, user)


def _info_icon(tip: str, right: bool = False) -> str:
    """Inline ℹ icon with click-toggled tooltip."""
    tip_cls = "cc-tip tip-right" if right else "cc-tip"
    return (f'<span class="cc-info-wrap">'
            f'<span class="cc-info" onclick="ccTipToggle(this)">ℹ</span>'
            f'<span class="{tip_cls}">{tip}</span>'
            f'</span>')


def _workflow_bar(active: str, user: str) -> str:
    """5-step onboarding workflow bar shown below the tab bar.
    Hidden for history/keywords tabs and after user dismisses with ×."""
    if active in ("history", "keywords", "ocr_review"):
        return ""

    drive_done = _is_drive_connected(user)

    # (step_num, label, tabs_where_active)
    steps = [
        (1, "Connect Drive",    ["ledger"]),
        (2, "Add Receipts",     ["ledger"]),
        (3, "Review Ledger",    ["ledger"]),
        (4, "Convert CSV",      ["convert"]),
        (5, "Review & Download",["review"]),
    ]

    parts = ['<div class="cc-wf-steps">']
    for i, (num, label, active_tabs) in enumerate(steps):
        if num == 1 and drive_done:
            cls = "cc-wf-step wf-done"
            badge = "✓"
        elif active in active_tabs:
            cls = "cc-wf-step wf-active"
            badge = str(num)
        else:
            cls = "cc-wf-step"
            badge = str(num)
        parts.append(
            f'<span class="{cls}">'
            f'<span class="sn">{badge}</span>'
            f'<span class="cc-wf-label">{label}</span>'
            f'</span>'
        )
        if i < len(steps) - 1:
            parts.append('<span class="cc-wf-sep">›</span>')
    parts.append('</div>')

    js = """<script>
(function(){
  if(localStorage.getItem('cc_guide_hidden')){
    var b=document.getElementById('ccWfBar');
    if(b) b.style.display='none';
  }
  window.ccHideGuide=function(){
    localStorage.setItem('cc_guide_hidden','1');
    document.getElementById('ccWfBar').style.display='none';
  };
  window.ccTipToggle=function(el){
    var tip=el.nextElementSibling;
    var open=tip.style.display==='block';
    document.querySelectorAll('.cc-tip').forEach(function(t){t.style.display='none';});
    if(!open){
      tip.style.display='block';
      var r=tip.getBoundingClientRect();
      if(r.right>window.innerWidth-20) tip.classList.add('tip-right');
      else tip.classList.remove('tip-right');
    }
  };
  document.addEventListener('click',function(e){
    if(!e.target.classList.contains('cc-info')){
      document.querySelectorAll('.cc-tip').forEach(function(t){t.style.display='none';});
    }
  });
})();
</script>"""

    return (
        f'<div class="cc-wf-bar" id="ccWfBar">'
        + "".join(parts)
        + '<button class="cc-wf-close" onclick="ccHideGuide()" title="Hide guide">×</button>'
        + '</div>'
        + js
    )


# Shared upload-zone CSS (used by Convert and Ledger register section)
_UPLOAD_CSS = (
    ".upload-zone{border:2px dashed var(--border);border-radius:var(--radius-lg);padding:40px 20px;"
    "text-align:center;cursor:pointer;transition:.2s;background:var(--surface)}"
    ".upload-zone:hover,.upload-zone.drag-over{border-color:var(--accent);background:var(--surface-2)}"
    ""  # file input now uses opacity:0 overlay instead of display:none
)


# ── Ledger register section (Drive + receipt upload) ───────────────────────────

def _register_section(user: str) -> str:
    """Drive status + receipt upload — moved onto the Ledger page."""
    connected = _is_drive_connected(user)
    meta = _load_drive_meta(user)
    receipts_folder_id = meta.get('receipts_folder_id')
    last_synced = _load_ledger(user).get("last_batch_at") or ""
    if connected:
        folder_link = ""
        if receipts_folder_id:
            folder_link = (f'<a href="https://drive.google.com/drive/folders/{receipts_folder_id}" '
                           f'target="_blank" class="btn btn-ghost btn-sm">📂 Open in Drive →</a>')
        sync_tip = _info_icon(
            'Fetches new receipts from Drive and uses AI (Gemini/Claude) to automatically extract date, amount, and merchant.')
        drive_status_html = f'''
      <span style="font-size:.88rem;font-weight:600;color:var(--success)">✅ Connected</span>
      {folder_link}
      <button class="btn btn-ghost btn-sm" onclick="startDriveSync(this)" style="margin-left:4px">🔄 Sync from Drive</button>{sync_tip}
      <span id="lastSynced" data-ts="{last_synced}" style="font-size:.78rem;color:var(--text-muted);margin-left:4px"></span>'''
        receipt_upload_html = '''
      <form id="rcptForm" method="POST" action="/cardconv/receipts/upload" enctype="multipart/form-data">
        <div class="upload-zone" id="rcptZone" onclick="document.getElementById('rcptFiles').click()">
          <div style="font-size:2rem;margin-bottom:8px">🧾</div>
          <div style="font-weight:700;color:var(--text);margin-bottom:4px">Drop receipts here</div>
          <div style="font-size:.8rem;color:var(--text-muted)">JPG · PNG · PDF &nbsp;·&nbsp; Multiple files supported &nbsp;·&nbsp; OCR runs automatically</div>
          <input type="file" id="rcptFiles" name="files" multiple accept=".jpg,.jpeg,.png,.pdf" onchange="handleRcptFiles(this)">
        </div>
        <div id="rcptInfo" style="display:none;margin-top:12px;padding:12px 16px;background:var(--surface-2);border-radius:var(--radius-md)">
          <div id="rcptFileList" style="font-size:.82rem;color:var(--text);margin-bottom:10px;display:flex;flex-wrap:wrap;gap:6px"></div>
          <button type="submit" class="btn btn-primary">📤 Upload &amp; OCR</button>
        </div>
      </form>'''
    else:
        drive_status_html = (
            '<span style="font-size:.88rem;font-weight:600;color:var(--danger)">❌ Not connected</span>'
            '<a href="/cardconv/drive/connect" class="btn btn-primary btn-sm">Connect Google Drive</a>'
        )
        receipt_upload_html = ('<p style="color:var(--text-muted);font-size:.85rem">'
                               'Connect Google Drive above to enable receipt upload.</p>')
    drive_tip = _info_icon(
        'Links to your Wayfinder/Receipts/ folder in Google Drive. '
        'After connecting, click Sync to automatically OCR all receipts in that folder.')
    # Collapsed by default (mobile-first) — auto-open until Drive is connected.
    open_attr = "" if connected else " open"
    return f'''
  <div id="driveNewBanner" style="display:none;align-items:center;gap:10px;padding:10px 14px;margin-bottom:14px;border:1px solid rgba(245,158,11,.35);background:rgba(245,158,11,.08);border-radius:var(--radius-md)">
    <span style="font-size:1.1rem">🧾</span>
    <span style="font-size:.85rem;color:var(--text)">New receipts in Drive: <b id="driveNewCount" style="color:#f59e0b">0</b> file(s) waiting to be synced</span>
    <button class="btn btn-primary btn-sm" style="margin-left:auto;flex-shrink:0" onclick="startDriveSync(this)">🔄 Sync now</button>
  </div>
  <details class="cc-collapse"{open_attr}>
    <summary>📥 Register Receipts <span style="font-weight:500;color:var(--text-dim)">— Google Drive · Upload</span></summary>
    <div class="cc-collapse-body">
      <div class="notepad-card" style="margin-bottom:16px">
        <div class="notepad-header">
          <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">Google Drive</span>{drive_tip}
        </div>
        <div class="notepad-body" style="padding:14px 20px;display:flex;align-items:center;gap:16px;flex-wrap:wrap">
          {drive_status_html}
        </div>
      </div>
      <div class="notepad-card">
        <div class="notepad-header">
          <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">Upload</span>
        </div>
        <div class="notepad-body" style="padding:20px">
          {receipt_upload_html}
        </div>
      </div>
    </div>
  </details>'''


# Receipt-upload drop-zone JS (injected into the Ledger page)
_RCPT_JS = r'''
const rcptZone = document.getElementById('rcptZone');
const rcptInfo = document.getElementById('rcptInfo');
const rcptList = document.getElementById('rcptFileList');
function handleRcptFiles(input){
  if(input.files.length>0){
    rcptList.innerHTML = Array.from(input.files).map(f =>
      '<span style="background:var(--surface-3);padding:3px 8px;border-radius:4px;font-size:.78rem">'+f.name+'</span>').join('');
    rcptInfo.style.display='block';
    rcptZone.style.borderColor='var(--accent)';
  }
}
if(rcptZone){
  rcptZone.addEventListener('dragover', e => { e.preventDefault(); rcptZone.classList.add('drag-over'); });
  rcptZone.addEventListener('dragleave', () => rcptZone.classList.remove('drag-over'));
  rcptZone.addEventListener('drop', e => {
    e.preventDefault(); rcptZone.classList.remove('drag-over');
    const input = document.getElementById('rcptFiles');
    if(e.dataTransfer.files.length>0){ input.files = e.dataTransfer.files; handleRcptFiles(input); }
  });
}
'''


# ── Convert page ───────────────────────────────────────────────────────────────

def _render_convert(user: str) -> str:
    from server import CSS_VER
    uploads = _load_uploads(user)
    up_rows = ""
    for u in uploads:
        up_rows += (
            '<div style="display:flex;align-items:center;gap:12px;padding:10px 0;border-bottom:1px solid var(--border)">'
            f'<span style="font-size:.8rem;color:var(--text-muted);min-width:130px">{_esc(u.get("uploaded_at"))}</span>'
            f'<span style="flex:1;font-size:.85rem;color:var(--text);font-weight:600">{_esc(u.get("filename"))}</span>'
            f'<span style="font-size:.78rem;color:var(--success)">{u.get("rows", 0)} rows</span>'
            f'<form method="POST" action="/cardconv/upload/rerun" style="display:inline">'
            f'<input type="hidden" name="id" value="{_esc(u.get("id"))}">'
            f'<button class="btn btn-secondary btn-sm">🔄 Re-run</button></form>'
            f'<form method="POST" action="/cardconv/upload/delete" style="display:inline" '
            f'onsubmit="return confirm(\'Delete this CSV?\')">'
            f'<input type="hidden" name="id" value="{_esc(u.get("id"))}">'
            f'<button class="btn btn-danger btn-sm">✕</button></form>'
            '</div>')
    if not up_rows:
        up_rows = '<div style="color:var(--text-muted);font-size:.85rem;padding:16px 0">No uploaded CSVs yet</div>'

    # My Card Names section (moved from Keywords page)
    names = _get_card_member_names(user)
    name_chips = ""
    for n in names:
        name_chips += (
            '<form method="POST" action="/cardconv/cardnames/delete" '
            'style="display:inline-flex;align-items:center;gap:6px;background:var(--surface-2);'
            'border:1px solid var(--border);border-radius:999px;padding:4px 6px 4px 12px;margin:0">'
            f'<span style="font-size:.82rem;font-weight:600;color:var(--accent)">{_esc(n)}</span>'
            f'<input type="hidden" name="name" value="{_esc(n)}">'
            '<button class="btn btn-danger btn-sm" style="padding:0 7px;line-height:1.5">✕</button>'
            '</form>')

    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>💳 Convert · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
<style>{_CC_TAB_CSS}{_UPLOAD_CSS}</style>
</head><body>
<nav>
  <span class="nav-brand">💳 Cheil AMEX Expense Assistant</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container" style="max-width:1100px">
  {_tab_bar("convert", user)}

  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">My Card Names</span>{_info_icon('Only transactions whose Card Member Name matches one of these names will be converted. Enter your name exactly as it appears in the AMEX CSV.')}
    </div>
    <div class="notepad-body" style="padding:12px 16px">
      <p style="font-size:.78rem;color:var(--text-muted);margin-bottom:12px">Only transactions whose CSV 'Card Member Name' matches a name below are converted.</p>
      <form method="POST" action="/cardconv/cardnames/add" style="display:flex;gap:8px;margin-bottom:14px">
        <input name="name" placeholder="e.g. JOHN DOE" required style="flex:1;padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.82rem">
        <button type="submit" class="btn btn-primary btn-sm">+ Add</button>
      </form>
      <div id="cardNamesWrap" style="display:flex;flex-wrap:wrap;gap:8px">{name_chips}</div>
    </div>
  </div>

  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">Upload Statement</span>{_info_icon('Upload the Posted_*.csv downloaded from your AMEX statement, or an AMEX Master xlsx (recon export). Either is matched with receipts and exported as an SAP-ready xlsx.', right=True)}
    </div>
    <div class="notepad-body" style="padding:20px">
      <form id="upForm" method="POST" action="/cardconv/upload" enctype="multipart/form-data">
        <div class="upload-zone" id="dropZone" style="position:relative">
          <input type="file" id="csvFile" name="file" accept=".csv,.xlsx"
            onchange="handleCsvFile(this)"
            style="position:absolute;inset:0;opacity:0;cursor:pointer;width:100%;height:100%;z-index:2">
          <div style="font-size:2rem;margin-bottom:8px">📎</div>
          <div style="font-weight:700;color:var(--text);margin-bottom:4px">Drop Posted_*.csv or AMEX Master xlsx here</div>
          <div style="font-size:.8rem;color:var(--text-muted)">or click to browse</div>
        </div>
        <div id="fileInfo" style="display:none;margin-top:12px;padding:12px 16px;background:var(--surface-2);border-radius:var(--radius-md);align-items:center;gap:12px">
          <span style="font-size:1.2rem">📄</span>
          <span id="fileName" style="flex:1;font-size:.85rem;font-weight:600;color:var(--text)"></span>
          <button type="submit" class="btn btn-primary">Convert → Review</button>
        </div>
      </form>
      <div id="nameSuggest" style="display:none;margin-top:14px;padding:10px 14px;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md)">
        <div style="font-size:.76rem;color:var(--text-muted);margin-bottom:8px">👤 Found in CSV — click to add to My Card Names:</div>
        <div id="nameChips" style="display:flex;flex-wrap:wrap;gap:6px"></div>
      </div>
      <p style="font-size:.78rem;color:var(--text-muted);margin-top:14px">
        Conversion matches receipts from the Ledger and opens the <b>Review</b> page before download.
      </p>
    </div>
  </div>

  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">Uploaded CSVs</span>
    </div>
    <div class="notepad-body" style="padding:8px 16px 12px">
      {up_rows}
    </div>
  </div>
</div>
<script>
const csvZone = document.getElementById('dropZone');
const csvInfo = document.getElementById('fileInfo');
const csvName = document.getElementById('fileName');
const existingNames = new Set({json.dumps(names)});

function parseCsvSuggest(text) {{
  const lines = text.split(/\\r?\\n/);
  if (!lines.length) return;
  const hdr = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g,''));
  const col = hdr.findIndex(h => /cardmember/i.test(h) || /card.?member/i.test(h));
  if (col < 0) return;
  const counts = {{}};
  lines.slice(1).forEach(line => {{
    if (!line.trim()) return;
    const cells = [];
    let cur = '', inQ = false;
    for (const ch of line + ',') {{
      if (ch === '"') {{ inQ = !inQ; }}
      else if (ch === ',' && !inQ) {{ cells.push(cur.trim()); cur = ''; }}
      else cur += ch;
    }}
    const name = (cells[col] || '').trim().toUpperCase();
    if (name && !existingNames.has(name)) counts[name] = (counts[name] || 0) + 1;
  }});
  const PRIORITY = ['EUISUN', 'DAE KIM', 'CHRIS CHO'];
  const sorted = Object.entries(counts).sort((a,b) => b[1]-a[1]).map(e => e[0]);
  const priority = sorted.filter(n => PRIORITY.some(p => n.includes(p)));
  const rest = sorted.filter(n => !PRIORITY.some(p => n.includes(p)));
  const top = [...priority, ...rest].slice(0, 10);
  if (!top.length) return;
  const chips = document.getElementById('nameChips');
  chips.innerHTML = top.map(n =>
    `<button type="button" class="preset-btn" style="font-size:.78rem" onclick="addSuggestedName(this,'${{n.replace(/'/g,"\\'")}}')">+ ${{n}}</button>`
  ).join('');
  document.getElementById('nameSuggest').style.display = 'block';
}}

function addSuggestedName(btn, name) {{
  fetch('/cardconv/cardnames/add', {{
    method:'POST', headers:{{'Content-Type':'application/x-www-form-urlencoded'}},
    body:'name='+encodeURIComponent(name)
  }}).then(r => {{
    if(r.ok) {{
      btn.disabled=true; btn.style.opacity='.4'; existingNames.add(name);
      // Immediately add to the My Card Names section above
      var wrap = document.getElementById('cardNamesWrap');
      if(wrap) {{
        var chip = document.createElement('form');
        chip.method = 'POST'; chip.action = '/cardconv/cardnames/delete';
        chip.style.cssText = 'display:inline-flex;align-items:center;gap:6px;background:var(--surface-2);border:1px solid var(--border);border-radius:999px;padding:4px 6px 4px 12px;margin:0';
        chip.innerHTML = '<span style="font-size:.82rem;font-weight:600;color:var(--accent)">'+name+'</span>'
          + '<input type="hidden" name="name" value="'+name.replace(/"/g,'&quot;')+'">'
          + '<button class="btn btn-danger btn-sm" style="padding:0 7px;line-height:1.5">✕</button>';
        wrap.appendChild(chip);
      }}
    }}
  }});
}}

function handleCsvFile(input) {{
  if (!input.files[0]) return;
  csvName.textContent = input.files[0].name;
  csvInfo.style.display = 'flex';
  csvZone.style.display = 'none';
  if (/[.]xlsx$/i.test(input.files[0].name)) return;  // binary — no name suggest
  const reader = new FileReader();
  reader.onload = e => parseCsvSuggest(e.target.result);
  reader.readAsText(input.files[0]);
}}
csvZone.addEventListener('dragover', e => {{ e.preventDefault(); csvZone.classList.add('drag-over'); }});
csvZone.addEventListener('dragleave', () => csvZone.classList.remove('drag-over'));
csvZone.addEventListener('drop', e => {{
  e.preventDefault(); csvZone.classList.remove('drag-over');
  const f = e.dataTransfer.files[0];
  if (f) {{
    document.getElementById('csvFile').files = e.dataTransfer.files;
    csvName.textContent = f.name;
    csvInfo.style.display = 'flex';
    csvZone.style.display = 'none';
    const reader = new FileReader();
    reader.onload = e2 => parseCsvSuggest(e2.target.result);
    reader.readAsText(f);
  }}
}});
</script>
</body></html>'''


# ── History page (Recent Conversions, moved off Convert) ─────────────────────────

def _render_history(user: str) -> str:
    from server import CSS_VER
    hist = _load_hist()

    rows_html = ""
    for h in hist:
        hid   = _esc(h.get("id", ""))
        htype = h.get("type", "conversion")
        hdate = _esc(h.get("date", ""))
        icon  = {"conversion": "📤", "ingest": "🧾"}.get(htype, "📥")
        type_label = {"conversion": "Conversion", "ingest": "Upload"}.get(htype, "PDF Download")
        type_color = ("color:#38bdf8" if htype == "conversion"
                      else "color:#22c55e" if htype == "ingest" else "color:#a78bfa")

        if htype == "ingest":
            src   = _esc(h.get("source", ""))
            added = h.get("rows", 0)
            dup   = h.get("dup_skipped", 0)
            mtc   = h.get("matched", 0)
            dl    = ""
            detail = (f'<span style="font-size:.8rem;color:var(--text);font-weight:600">{src}</span>'
                      f'<span style="font-size:.74rem;color:var(--success)">+{added} new</span>'
                      f'<span style="font-size:.74rem;color:var(--text-muted)">{mtc} matched</span>')
            if dup:
                detail += f'<span style="font-size:.72rem;color:#38bdf8">{dup} duplicates skipped</span>'
        elif htype == "conversion":
            src  = _esc(h.get("source", ""))
            fn   = _esc(h.get("filename", ""))
            rows = h.get("rows", 0)
            unm  = h.get("unmatched", 0)
            dl   = f'<a href="/cardconv/download/{fn}" class="btn btn-ghost btn-sm" style="font-size:.74rem;padding:3px 10px">⬇ xlsx</a>'
            detail = (f'<span style="font-size:.8rem;color:var(--text);font-weight:600">{fn}</span>'
                      f'<span style="font-size:.74rem;color:var(--text-muted)">from {src}</span>'
                      f'<span style="font-size:.74rem;color:var(--success)">{rows} rows</span>')
            if unm:
                detail += f'<span style="font-size:.72rem;color:var(--warn)">{unm} unmatched</span>'
        else:
            fn     = _esc(h.get("filename", ""))
            count  = h.get("count", 0)
            filt   = _esc(h.get("filter", "All"))
            dl     = ""
            detail = (f'<span style="font-size:.8rem;color:var(--text);font-weight:600">{fn}</span>'
                      f'<span style="font-size:.74rem;color:var(--text-muted)">Filter: {filt} · {count} receipts</span>')

        rows_html += (
            f'<div class="hist-row" data-id="{hid}" style="display:flex;align-items:center;gap:10px;padding:9px 0;border-bottom:1px solid var(--border)">'
            f'<input type="checkbox" class="hist-cb" data-id="{hid}" style="width:14px;height:14px;accent-color:var(--accent);cursor:pointer;flex-shrink:0">'
            f'<span style="font-size:1rem;flex-shrink:0">{icon}</span>'
            f'<span style="font-size:.72rem;font-weight:600;padding:1px 7px;border-radius:8px;background:var(--surface-3);{type_color};flex-shrink:0">{type_label}</span>'
            f'<span style="font-size:.78rem;color:var(--text-muted);min-width:120px;flex-shrink:0">{hdate}</span>'
            f'<div style="display:flex;flex-wrap:wrap;gap:6px;align-items:center;flex:1;min-width:0">{detail}</div>'
            f'{dl}'
            f'</div>')

    if not rows_html:
        rows_html = '<div style="color:var(--text-muted);font-size:.85rem;padding:20px 0;text-align:center">No history yet</div>'

    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🕘 History · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
<style>{_CC_TAB_CSS}</style>
</head><body>
<nav>
  <span class="nav-brand">💳 Cheil AMEX Expense Assistant</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container" style="max-width:1100px">
  {_tab_bar("history", user)}

  <div class="notepad-card" style="margin-bottom:20px">
    <div class="notepad-header" style="display:flex;align-items:center;justify-content:space-between">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">Upload &amp; Download History</span>
      <div style="display:flex;gap:8px">
        <button onclick="delSelected()" class="btn btn-ghost btn-sm" style="font-size:.74rem" id="delSelBtn" disabled>🗑 Delete Selected</button>
        <button onclick="clearAll()" class="btn btn-danger btn-sm" style="font-size:.74rem">✕ Clear All</button>
      </div>
    </div>
    <div class="notepad-body" style="padding:4px 16px 12px">
      <label style="display:flex;align-items:center;gap:6px;padding:6px 0;font-size:.78rem;color:var(--text-muted);cursor:pointer;border-bottom:1px solid var(--border);margin-bottom:2px">
        <input type="checkbox" id="checkAll" style="width:14px;height:14px;accent-color:var(--accent);cursor:pointer"> Select all
      </label>
      <div id="histList">{rows_html}</div>
    </div>
  </div>
</div>
<script>
const checkAll = document.getElementById('checkAll');
const delSelBtn = document.getElementById('delSelBtn');

function updateBtn(){{
  var n = document.querySelectorAll('.hist-cb:checked').length;
  delSelBtn.disabled = n === 0;
  delSelBtn.textContent = n ? '🗑 Delete Selected (' + n + ')' : '🗑 Delete Selected';
}}

checkAll.addEventListener('change', function(){{
  document.querySelectorAll('.hist-cb').forEach(cb => cb.checked = checkAll.checked);
  updateBtn();
}});

document.getElementById('histList').addEventListener('change', function(e){{
  if(e.target.classList.contains('hist-cb')) updateBtn();
}});

function delSelected(){{
  var ids = Array.from(document.querySelectorAll('.hist-cb:checked')).map(cb => cb.dataset.id);
  if(!ids.length) return;
  fetch('/cardconv/history/delete', {{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{ids}}) }})
    .then(() => location.reload());
}}

function clearAll(){{
  if(!confirm('Clear all history?')) return;
  fetch('/cardconv/history/clear', {{method:'POST'}}).then(() => location.reload());
}}
</script>
</body></html>'''


# ── Keywords page ────────────────────────────────────────────────────────────

def _render_keywords(user: str) -> str:
    from server import CSS_VER
    kws = _load_kw()
    kw_rows = ""
    for k in kws:
        kw_rows += f'''<tr>
      <td style="font-weight:600;color:var(--accent)">{k["kw"]}</td>
      <td style="color:var(--text-muted)">{k["gl"]}</td>
      <td style="color:var(--text-muted)">{k["ser"]}</td>
      <td style="flex:1;color:var(--text)">{k["purpose"]}</td>
      <td><form method="POST" action="/cardconv/keyword/delete" style="display:inline">
        <input type="hidden" name="kw" value="{k["kw"]}">
        <button class="btn btn-danger btn-sm">✕</button>
      </form></td>
    </tr>'''

    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔑 Keywords · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
<style>{_CC_TAB_CSS}
.kw-table{{width:100%;border-collapse:collapse;font-size:.82rem}}
.kw-table td{{padding:8px 10px;border-bottom:1px solid var(--border)}}
.kw-table tr:last-child td{{border-bottom:none}}
</style>
</head><body>
<nav>
  <span class="nav-brand">💳 Cheil AMEX Expense Assistant</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container" style="max-width:1100px">
  {_tab_bar("keywords", user)}

  <div class="notepad-card" id="keywords">
    <div class="notepad-header" style="display:flex;align-items:center;justify-content:space-between">
      <span style="font-size:var(--text-xs);font-weight:700;text-transform:uppercase;letter-spacing:.08em;color:var(--accent)">Keywords ({len(kws)})</span>
    </div>
    <div class="notepad-body" style="padding:12px 16px">
      <form method="POST" action="/cardconv/keyword/add" style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;align-items:flex-end">
        <div style="display:flex;flex-direction:column;gap:4px">
          <label style="font-size:.7rem;color:var(--text-muted);font-weight:600">KEYWORD</label>
          <input name="kw" placeholder="e.g. STARBUCKS" required style="padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.82rem;width:160px">
        </div>
        <div style="display:flex;flex-direction:column;gap:4px">
          <label style="font-size:.7rem;color:var(--text-muted);font-weight:600">G/L ACCOUNT</label>
          <input name="gl" placeholder="53410177" required style="padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.82rem;width:110px">
        </div>
        <div style="display:flex;flex-direction:column;gap:4px">
          <label style="font-size:.7rem;color:var(--text-muted);font-weight:600">SER.</label>
          <input name="ser" placeholder="160" style="padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.82rem;width:70px">
        </div>
        <div style="display:flex;flex-direction:column;gap:4px;flex:1;min-width:180px">
          <label style="font-size:.7rem;color:var(--text-muted);font-weight:600">PURPOSE</label>
          <input name="purpose" placeholder="Coffee, Snack and meal" required style="padding:7px 10px;border:1px solid var(--border);border-radius:6px;background:var(--surface-2);color:var(--text);font-size:.82rem;width:100%">
        </div>
        <button type="submit" class="btn btn-primary btn-sm" style="align-self:flex-end">+ Add</button>
      </form>
      <div>
        <table class="kw-table">
          <thead>
            <tr style="border-bottom:1px solid var(--border)">
              <th style="padding:6px 10px;text-align:left;font-size:.7rem;color:var(--text-muted);font-weight:700;text-transform:uppercase">Keyword</th>
              <th style="padding:6px 10px;text-align:left;font-size:.7rem;color:var(--text-muted);font-weight:700;text-transform:uppercase">G/L</th>
              <th style="padding:6px 10px;text-align:left;font-size:.7rem;color:var(--text-muted);font-weight:700;text-transform:uppercase">Ser.</th>
              <th style="padding:6px 10px;text-align:left;font-size:.7rem;color:var(--text-muted);font-weight:700;text-transform:uppercase">Purpose</th>
              <th></th>
            </tr>
          </thead>
          <tbody>{kw_rows}</tbody>
        </table>
      </div>
    </div>
  </div>
</div>
</body></html>'''


# ── Review page ──────────────────────────────────────────────────────────────

def _render_review(user: str) -> str:
    from server import CSS_VER
    pool    = _load_tx_pool(user)
    # Newest transactions first; dateless rows sink to the bottom.
    rows    = sorted(pool.get("entries", []),
                     key=lambda e: (e.get("date") or "0000-00-00", e.get("added_at") or ""),
                     reverse=True)
    open_rows   = [e for e in rows if (e.get("status") or "open") == "open"]
    total       = len(open_rows)
    matched     = sum(1 for e in open_rows if e.get("matched"))
    unmatched   = total - matched
    inprog_n    = sum(1 for e in rows if e.get("status") == "in_progress")
    completed_n = sum(1 for e in rows if e.get("status") == "completed")
    li          = pool.get("last_ingest") or {}
    dup_skipped = li.get("dup_skipped", 0)

    def _money(a):
        return f'${a:,.2f}' if isinstance(a, (int, float)) else (_esc(a) or '–')

    if not rows:
        body_html = ('<div style="text-align:center;color:var(--text-muted);padding:40px">'
                     'No conversion yet — upload a CSV on the '
                     '<a href="/cardconv/convert" style="color:var(--accent)">Convert</a> tab.</div>')
    else:
        items = []
        for r in rows:
            is_matched = r.get("matched")
            st = r.get("status") or "open"
            is_open = st == "open"
            rc = r.get("receipt") or {}
            if st == "completed":
                done_badge = ('<span style="font-size:.62rem;font-weight:700;padding:2px 6px;border-radius:8px;'
                              'background:rgba(34,197,94,.15);color:#22c55e">✔ COMPLETED</span>')
            elif st == "in_progress":
                done_badge = ('<span style="font-size:.62rem;font-weight:700;padding:2px 6px;border-radius:8px;'
                              'background:rgba(245,158,11,.15);color:#f59e0b">⏳ APPROVAL IN PROGRESS</span>')
            else:
                done_badge = ''
            # Transaction (CSV line item) header
            txn = (
                f'<label class="rv-cb-wrap"><input type="checkbox" class="rv-cb" data-id="{_esc(r.get("id",""))}"></label>'
                '<div class="rv-txn">'
                  '<div class="rv-txn-main">'
                    f'<span class="rv-date">{_esc(r.get("date")) or "–"} {done_badge}</span>'
                    f'<span class="rv-merchant">{_esc(r.get("merchant"))}</span>'
                  '</div>'
                  '<div class="rv-txn-meta">'
                    f'<span class="rv-amt">{_money(r.get("amount"))}</span>'
                    f'<span class="rv-gl">G/L {_esc(r.get("gl"))}</span>'
                  '</div>'
                '</div>')
            # Inline matched-receipt mini card, or unmatched + loss-reason input
            if is_matched and rc.get("file_id"):
                fid   = rc["file_id"]
                tn    = f'https://drive.google.com/thumbnail?id={fid}&sz=w240'
                proxy = f'/cardconv/receipts/image/{fid}'
                link  = (f'<a href="{_esc(rc.get("drive_url"))}" target="_blank" '
                         f'class="rv-drive-link">🔗 Drive</a>' if rc.get("drive_url") else '')
                # Payload for the lightbox: full image proxy + bbox of this entry and
                # its siblings (multi-receipt page) so the clicked one can be highlighted.
                rv_data = _esc(json.dumps({
                    "fid":      fid,
                    "id":       rc.get("id"),
                    "merchant": rc.get("ocr_merchant"),
                    "bbox":     rc.get("ocr_bbox"),
                    "siblings": rc.get("siblings") or [],
                    "drive":    rc.get("drive_url"),
                }, ensure_ascii=False))
                comp = (f'<div class="rv-card-line rv-card-comp" title="Handwritten companion note — appended to the SAP purpose">'
                        f'👥 w/ {_esc(rc.get("companions"))}</div>'
                        if rc.get("companions") else '')
                receipt_block = (
                    '<div class="rv-receipt matched">'
                      f'<img class="rv-thumb" src="{tn}" loading="lazy" '
                      f'data-rv="{rv_data}" title="Click to enlarge" '
                      f'onerror="this.onerror=null;this.src=\'{proxy}\'">'
                      '<div class="rv-card-info">'
                        f'<div class="rv-card-line">🗓 {_esc(rc.get("ocr_date")) or "–"}</div>'
                        f'<div class="rv-card-line rv-card-merchant">{_esc(rc.get("ocr_merchant")) or "–"}</div>'
                        f'<div class="rv-card-line rv-card-amt">{_money(rc.get("ocr_amount"))}</div>'
                        f'{comp}{link}'
                      '</div>'
                    '</div>')
            else:
                txn_json   = _esc(json.dumps({
                    "id": r.get("id",""), "date": r.get("date",""),
                    "merchant": r.get("merchant",""), "amount": r.get("amount"),
                }, ensure_ascii=False))
                match_btn = ''
                if is_open:
                    match_btn = (
                        f'<button type="button" '
                        f'onclick="rvOpenMatchPanel(this)" '
                        f'data-txn="{txn_json}" '
                        f'class="btn btn-ghost btn-sm" '
                        f'style="margin-top:6px;font-size:.74rem;color:var(--accent);width:100%">'
                        f'🔗 Match manually</button>')
                receipt_block = (
                    '<div class="rv-receipt unmatched">'
                      '<div class="rv-nomatch">❌ No receipt matched</div>'
                      f'{match_btn}'
                    '</div>')
            item_cls = 'rv-item' + ('' if is_matched else ' unmatched') + ('' if st == "completed" else '')
            if st == "completed":
                item_cls += ' done'
            row_date = _esc(r.get("date")) or ""
            row_merchant = _esc(str(r.get("merchant") or "").lower())
            items.append(
                f'<div class="{item_cls}" data-date="{row_date}" '
                f'data-merchant="{row_merchant}" '
                f'data-status="{st}" '
                f'data-matched="{"1" if is_matched else "0"}">{txn}{receipt_block}</div>')
        body_html = "".join(items)

    download_btn = (('<span class="fb-pop-wrap">'
                     '<button class="fb-more-btn" id="rvExport" aria-expanded="false">⬇ Export <span class="chev">▾</span></button>'
                     '<div class="fb-menu" id="rvExportMenu">'
                     '<button id="rvDownload" class="fb-menu-item" '
                     'title="SAP upload file (for_upload_*.xlsx)">⬇ xlsx (SAP)</button>'
                     '<button id="rvDownloadPdf" class="fb-menu-item" '
                     'title="Receipt images of the matched transactions">⬇ PDF</button>'
                     '<button id="rvDownloadBoth" class="fb-menu-item" '
                     'title="Download the SAP xlsx and the receipt PDF together">⬇ Both <small>xlsx + PDF</small></button>'
                     '</div></span>')
                    if total else '')
    if li:
        li_at = (li.get("at", "") or "")[:16].replace("T", " ")
        meta_line = (f'Last upload: {_esc(li.get("filename",""))} &nbsp;·&nbsp; '
                     f'+{li.get("added",0)} new &nbsp;·&nbsp; {li_at}')
        if dup_skipped:
            meta_line += (f' &nbsp;·&nbsp; <span title="overlapping statement period">'
                          f'⏭ {dup_skipped} duplicates skipped</span>')
    else:
        meta_line = 'No uploads yet'

    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>🔍 Review · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
<style>{_CC_TAB_CSS}
.stat-grid{{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:16px}}
.stat-card{{background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);padding:16px 20px;text-align:center}}
.stat-click{{cursor:pointer;transition:border-color .12s}}
.stat-click:hover{{border-color:var(--accent)}}
.stat-click.active{{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}}
.stat-value{{font-size:1.6rem;font-weight:700;color:var(--text);line-height:1.2}}
.stat-label{{font-size:.73rem;color:var(--text-muted);margin-top:4px;text-transform:uppercase;letter-spacing:.06em}}
.filter-bar{{display:flex;align-items:center;gap:10px;padding:10px 16px;background:var(--surface-2);
  border:1px solid var(--border);border-radius:var(--radius-md);margin-bottom:14px;flex-wrap:wrap}}
.filter-bar input[type=date],.filter-bar input[type=text],.filter-bar select{{background:var(--surface);border:1px solid var(--border);
  border-radius:6px;color:var(--text);font-size:.82rem;padding:5px 8px;outline:none}}
.filter-bar input[type=date]:focus,.filter-bar input[type=text]:focus,.filter-bar select:focus{{border-color:var(--accent)}}
.fb-field{{display:inline-flex;align-items:center;gap:6px}}
.fb-field>span{{font-size:.74rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em}}
.filter-bar [hidden]{{display:none!important}}
.fb-search{{flex:1;min-width:140px;flex-wrap:nowrap!important}}
.fb-search input{{flex:1;width:auto;min-width:0}}
.fb-pop-wrap{{position:relative}}
.fb-more-btn{{background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--text-muted);font-size:.78rem;font-weight:600;padding:5px 11px;cursor:pointer;display:inline-flex;align-items:center;gap:5px}}
.fb-more-btn:hover{{border-color:var(--accent);color:var(--text)}}
.fb-more-btn .chev{{transition:transform .18s}}
.fb-more-btn.open .chev{{transform:rotate(180deg)}}
.fb-menu{{display:none;position:absolute;top:calc(100% + 8px);right:0;z-index:120;background:var(--surface-3);border:1px solid var(--border-bright);border-radius:var(--radius-md);box-shadow:0 12px 34px rgba(0,0,0,.55);padding:6px;min-width:280px;flex-direction:column;gap:2px}}
.fb-menu.open{{display:flex}}
.fb-menu-item{{display:flex;align-items:center;gap:8px;background:none;border:none;border-radius:7px;color:var(--text);font-size:.8rem;font-weight:600;padding:8px 10px;cursor:pointer;text-align:left;white-space:nowrap}}
.fb-menu-item:hover{{background:var(--surface-2)}}
.fb-menu-item small{{color:var(--text-muted);font-weight:500}}
.rv-list{{display:flex;flex-direction:column;gap:10px}}
.rv-item{{display:flex;gap:14px;align-items:stretch;background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);padding:12px 14px}}
.rv-item.unmatched{{border-color:rgba(239,68,68,.35);background:rgba(239,68,68,.06)}}
.rv-item.done{{opacity:.65}}
.rv-cb-wrap{{display:flex;align-items:center;padding-right:2px;cursor:pointer}}
.rv-cb{{width:16px;height:16px;accent-color:var(--accent);cursor:pointer}}
.rv-txn{{flex:1;min-width:0;display:flex;flex-direction:column;justify-content:center;gap:6px}}
.rv-txn-main{{display:flex;flex-direction:column;gap:2px}}
.rv-date{{font-size:.74rem;color:var(--text-muted)}}
.rv-merchant{{font-size:.95rem;font-weight:700;color:var(--text)}}
.rv-txn-meta{{display:flex;gap:12px;align-items:baseline;flex-wrap:wrap}}
.rv-amt{{font-size:1.05rem;font-weight:700;color:var(--text)}}
.rv-gl{{font-size:.74rem;color:var(--text-muted)}}
.rv-receipt{{flex:0 0 230px;border-left:1px solid var(--border);padding-left:14px}}
.rv-receipt.matched{{display:flex;gap:12px;align-items:flex-start}}
.rv-thumb{{width:120px;height:120px;border-radius:8px;object-fit:cover;border:1px solid var(--border);background:var(--surface-3);cursor:zoom-in;transition:border-color .12s}}
.rv-thumb:hover{{border-color:var(--accent)}}
.rv-lb{{position:fixed;inset:0;background:rgba(2,6,23,.82);display:none;align-items:center;justify-content:center;z-index:1000;padding:24px}}
.rv-lb.open{{display:flex}}
.rv-lb-box{{position:relative;max-width:92vw;max-height:92vh;display:flex;flex-direction:column;gap:10px}}
.rv-lb-img-wrap{{position:relative;display:inline-block;max-width:92vw;max-height:80vh}}
.rv-lb-img{{max-width:92vw;max-height:80vh;border-radius:8px;display:block}}
.rv-lb-svg{{position:absolute;top:0;left:0;pointer-events:none;display:none}}
.rv-lb-bar{{display:flex;align-items:center;justify-content:space-between;gap:14px;color:#e2e8f0;font-size:.85rem}}
.rv-lb-close{{position:absolute;top:-12px;right:-12px;width:34px;height:34px;border-radius:50%;border:none;
  background:var(--surface);color:var(--text);font-size:1.1rem;cursor:pointer;box-shadow:0 2px 8px rgba(0,0,0,.4)}}
.rv-lb-open{{color:var(--accent);text-decoration:none;font-size:.82rem}}
.rv-lb-open:hover{{text-decoration:underline}}
.rv-card-info{{display:flex;flex-direction:column;gap:4px;min-width:0}}
.rv-card-line{{font-size:.8rem;color:var(--text-muted)}}
.rv-card-merchant{{font-weight:600;color:var(--text);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}}
.rv-card-comp{{color:var(--accent);font-weight:600}}
.rv-card-amt{{font-size:1rem;font-weight:700;color:#22c55e}}
.rv-drive-link{{font-size:.76rem;color:var(--accent);text-decoration:none;margin-top:2px}}
.rv-drive-link:hover{{text-decoration:underline}}
.rv-nomatch{{color:var(--danger);font-size:.84rem;font-weight:700;margin-bottom:6px}}

@media(max-width:600px){{.rv-item{{flex-direction:column;gap:10px}}.rv-receipt{{flex:none;border-left:none;border-top:1px solid var(--border);padding-left:0;padding-top:10px}}}}
.rv-foot{{display:flex;align-items:center;justify-content:space-between;gap:12px;padding:16px 4px;flex-wrap:wrap}}
@media(max-width:600px){{.stat-grid{{grid-template-columns:1fr 1fr 1fr}}}}
</style>
</head><body>
<nav>
  <span class="nav-brand">💳 Cheil AMEX Expense Assistant</span>
  <span class="nav-user">👤 {user} &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container" style="max-width:1100px">
  {_tab_bar("review", user)}

  <div style="font-size:.8rem;color:var(--text-muted);margin-bottom:12px;display:flex;align-items:center;gap:6px">
    <span>{meta_line}</span>{_info_icon('Shows converted transactions with receipt matching results. Unmatched rows (red) can be linked via 🔗 Match manually, or carried over to the next billing cycle.', right=True)}
  </div>

  <div class="stat-grid">
    <div class="stat-card stat-click active" data-rvview="open" title="Open transactions"><div class="stat-value" id="rvTotal">{total}</div><div class="stat-label">Open</div></div>
    <div class="stat-card stat-click" data-rvview="matched" title="Open + receipt matched"><div class="stat-value" id="rvMatched" style="color:#22c55e">{matched}</div><div class="stat-label">Matched</div></div>
    <div class="stat-card stat-click" data-rvview="unmatched" title="Open + no receipt"><div class="stat-value" id="rvUnmatched" style="color:#ef4444">{unmatched}</div><div class="stat-label">Unmatched</div></div>
    <div class="stat-card stat-click" data-rvview="in_progress" title="Submitted to SAP, awaiting approval"><div class="stat-value" style="color:#f59e0b">{inprog_n}</div><div class="stat-label">⏳ In progress</div></div>
    <div class="stat-card stat-click" data-rvview="completed" title="Settlement completed"><div class="stat-value" style="color:#818cf8">{completed_n}</div><div class="stat-label">✔ Completed</div></div>
  </div>

  <div class="filter-bar">
    <span class="fb-field"><span>Period</span>
      <select id="rvPeriod">
        <option value="all">All time</option>
        <option value="month">This month</option>
        <option value="30d">30 days</option>
        <option value="3m">3 months</option>
        <option value="ytd">YTD</option>
        <option value="custom">Custom…</option>
      </select>
    </span>
    <span class="fb-field" id="rvCustomRange" hidden>
      <input type="date" id="rvFrom"> ~ <input type="date" id="rvTo">
    </span>
    <span class="fb-field fb-search">🔍 <input type="text" id="rvMerchant" placeholder="Search merchant…"></span>
    <span class="fb-field"><span>Sort</span>
      <select id="rvSort">
        <option value="date">Date ↓</option>
        <option value="merchant">Merchant A→Z</option>
      </select>
    </span>
    <button class="btn btn-ghost btn-sm" id="rvReset">↺ Reset</button>
    {download_btn}
  </div>

  <div class="filter-bar" style="gap:10px">
    <label style="display:flex;align-items:center;gap:6px;font-size:.8rem;color:var(--text-muted);cursor:pointer">
      <input type="checkbox" id="rvSelAll" style="width:15px;height:15px;accent-color:var(--accent);cursor:pointer"> Select all
    </label>
    <button class="btn btn-secondary btn-sm" id="rvMarkProg" title="Submitted to SAP, awaiting approval">⏳ Mark in progress</button>
    <button class="btn btn-primary btn-sm" id="rvMarkDone">✔ Mark completed</button>
    <button class="btn btn-ghost btn-sm" id="rvMarkOpen">↩ Reopen</button>
    <button class="btn btn-ghost btn-sm" id="rvRematch" title="Match open transactions against the receipt ledger">↻ Re-match receipts</button>
    <span style="flex:1"></span>
    <span style="font-size:.76rem;color:var(--text-muted)">Click a card above to switch views</span>
  </div>

  <div class="notepad-card">
    <div class="notepad-body" style="padding:12px 14px">
      <div class="rv-list">{body_html}</div>
    </div>
  </div>

  <div class="rv-foot">
    <span style="font-size:.78rem;color:var(--text-muted)">The matched receipt shows next to each transaction. Unmatched transactions are highlighted in red.</span>
  </div>
</div>

<div class="rv-lb" id="rvLb">
  <div class="rv-lb-box">
    <button class="rv-lb-close" id="rvLbClose" title="Close">×</button>
    <div class="rv-lb-img-wrap">
      <img class="rv-lb-img" id="rvLbImg" alt="receipt">
      <svg class="rv-lb-svg" id="rvLbSvg"></svg>
    </div>
    <div class="rv-lb-bar">
      <span id="rvLbCaption"></span>
      <a id="rvLbDrive" class="rv-lb-open" target="_blank" rel="noopener">🔗 Open in Drive</a>
    </div>
  </div>
</div>
<script>
// ── Date filter + presets (mirrors the Ledger page) ──────────────────────────
const $ = id => document.getElementById(id);
function iso(d){{ return d.toISOString().slice(0,10); }}

// View state: 'open' (default) or 'completed'. Date filters keep rows without
// an invoice date always visible, matching Ledger.
let rvView = 'open';
let rvMatchedF = 'all';   // 'all' | '1' | '0' — set by the Matched/Unmatched cards
function applyFilter(){{
  const from = $('rvFrom').value, to = $('rvTo').value;
  const mq = $('rvMerchant').value.trim().toLowerCase();
  document.querySelectorAll('.rv-item').forEach(it => {{
    const d = it.dataset.date || '';
    const show = (it.dataset.status === rvView)
      && (rvMatchedF === 'all' || it.dataset.matched === rvMatchedF)
      && (!from || !d || d >= from) && (!to || !d || d <= to)
      && (!mq || (it.dataset.merchant || '').includes(mq));
    it.style.display = show ? '' : 'none';
    if(!show) it.querySelector('.rv-cb').checked = false;
  }});
  $('rvSelAll').checked = false;
}}

function applySort(){{
  const mode = $('rvSort').value;
  const list = document.querySelector('.rv-list');
  const items = Array.from(list.querySelectorAll('.rv-item'));
  items.sort((a, b) => {{
    if(mode === 'merchant')
      return (a.dataset.merchant || '\\uffff').localeCompare(b.dataset.merchant || '\\uffff');
    return (b.dataset.date || '').localeCompare(a.dataset.date || '');  // date desc
  }});
  items.forEach(it => list.appendChild(it));
}}

// ── Status workflow: open → in_progress (SAP submitted) → completed ─────────
// Stat cards double as view switchers (same UX as the Ledger).
const RV_VIEWS = {{
  open:        {{view: 'open',        matched: 'all'}},
  matched:     {{view: 'open',        matched: '1'}},
  unmatched:   {{view: 'open',        matched: '0'}},
  in_progress: {{view: 'in_progress', matched: 'all'}},
  completed:   {{view: 'completed',   matched: 'all'}},
}};
document.querySelectorAll('.stat-click').forEach(card => card.addEventListener('click', () => {{
  const v = RV_VIEWS[card.dataset.rvview];
  rvView = v.view; rvMatchedF = v.matched;
  document.querySelectorAll('.stat-click').forEach(c => c.classList.toggle('active', c === card));
  applyFilter();
}}));

function rvSetStatus(status, label){{
  const ids = Array.from(document.querySelectorAll('.rv-cb:checked')).map(cb => cb.dataset.id);
  if(!ids.length){{ alert('Select transactions first.'); return; }}
  if(!confirm(label + ' — ' + ids.length + ' transaction(s)?')) return;
  fetch('/cardconv/review/status', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/json'}},
    body: JSON.stringify({{ids: ids, status: status}})
  }}).then(r => r.json()).then(d => {{
    if(d.error){{ alert('Error: ' + d.error); return; }}
    location.reload();
  }}).catch(e => alert('Error: ' + e));
}}
$('rvMarkProg').addEventListener('click', () => rvSetStatus('in_progress', '⏳ Mark in progress'));
$('rvMarkDone').addEventListener('click', () => rvSetStatus('completed', '✔ Mark completed'));
$('rvMarkOpen').addEventListener('click', () => rvSetStatus('open', '↩ Reopen'));

$('rvRematch').addEventListener('click', async () => {{
  const btn = $('rvRematch');
  btn.disabled = true; btn.textContent = '↻ Matching…';
  try {{
    const r = await fetch('/cardconv/review/rematch', {{method:'POST'}});
    const d = await r.json();
    btn.textContent = '↻ ' + (d.matched || 0) + ' matched';
    if (d.matched) setTimeout(() => location.reload(), 700);
    else setTimeout(() => {{ btn.textContent = '↻ Re-match receipts'; btn.disabled = false; }}, 1500);
  }} catch(e) {{
    btn.textContent = '↻ Re-match receipts'; btn.disabled = false;
  }}
}});

$('rvSelAll').addEventListener('change', () => {{
  const on = $('rvSelAll').checked;
  document.querySelectorAll('.rv-item').forEach(it => {{
    if(it.style.display !== 'none') it.querySelector('.rv-cb').checked = on;
  }});
}});

function applyPreset(p){{
  const now = new Date();
  let from = '', to = iso(now);
  if(p==='month')    from = iso(new Date(now.getFullYear(), now.getMonth(), 1));
  else if(p==='30d') from = iso(new Date(now.getTime() - 29*86400000));
  else if(p==='3m')  from = iso(new Date(now.getFullYear(), now.getMonth()-3, now.getDate()));
  else if(p==='ytd') from = iso(new Date(now.getFullYear(), 0, 1));
  else if(p==='all'){{ from = ''; to = ''; }}
  $('rvFrom').value = from;
  $('rvTo').value = to;
  applyFilter();
}}

let _rvmDeb;
$('rvMerchant').addEventListener('input', () => {{ clearTimeout(_rvmDeb); _rvmDeb = setTimeout(applyFilter, 250); }});
$('rvSort').addEventListener('change', applySort);
$('rvFrom').addEventListener('change', applyFilter);
$('rvTo').addEventListener('change', applyFilter);
// Period select drives the date range; Custom… reveals the two date inputs.
$('rvPeriod').addEventListener('change', () => {{
  const v = $('rvPeriod').value;
  $('rvCustomRange').hidden = (v !== 'custom');
  if(v === 'custom') return;
  applyPreset(v);
}});
$('rvReset').addEventListener('click', () => {{
  $('rvFrom').value = ''; $('rvTo').value = ''; $('rvMerchant').value = '';
  $('rvPeriod').value = 'all'; $('rvCustomRange').hidden = true;
  $('rvSort').value = 'date'; applySort();
  rvView = 'open'; rvMatchedF = 'all';
  document.querySelectorAll('.stat-click').forEach(c => c.classList.toggle('active', c.dataset.rvview === 'open'));
  applyFilter();
}});

// Downloads: checked rows take priority (download selected only); otherwise
// the current date filter applies to all open transactions.
function rvDlParams(){{
  const p = new URLSearchParams();
  const ids = Array.from(document.querySelectorAll('.rv-cb:checked')).map(cb => cb.dataset.id);
  if(ids.length){{ p.set('ids', ids.join(',')); return p; }}
  if($('rvFrom').value) p.set('from', $('rvFrom').value);
  if($('rvTo').value)   p.set('to', $('rvTo').value);
  return p;
}}
const rvDl = $('rvDownload');
if(rvDl){{
  const rvCloseExport = () => {{
    $('rvExportMenu').classList.remove('open');
    $('rvExport').classList.remove('open');
    $('rvExport').setAttribute('aria-expanded','false');
  }};
  $('rvExport').addEventListener('click', () => {{
    const open = $('rvExportMenu').classList.toggle('open');
    $('rvExport').classList.toggle('open', open);
    $('rvExport').setAttribute('aria-expanded', open);
  }});
  document.addEventListener('click', e => {{
    if(!$('rvExportMenu').classList.contains('open')) return;
    if($('rvExportMenu').contains(e.target) || $('rvExport').contains(e.target)) return;
    rvCloseExport();
  }});
  document.addEventListener('keydown', e => {{ if(e.key === 'Escape') rvCloseExport(); }});
  rvDl.addEventListener('click', () => {{
    rvCloseExport();
    window.location = '/cardconv/review/download?' + rvDlParams().toString();
  }});
  $('rvDownloadPdf').addEventListener('click', () => {{
    rvCloseExport();
    window.location = '/cardconv/review/download.pdf?' + rvDlParams().toString();
  }});
  // Both at once: hidden iframes so the two attachment downloads don't race.
  $('rvDownloadBoth').addEventListener('click', () => {{
    rvCloseExport();
    const q = rvDlParams().toString();
    ['/cardconv/review/download?', '/cardconv/review/download.pdf?'].forEach(u => {{
      const f = document.createElement('iframe');
      f.style.display = 'none';
      f.src = u + q;
      document.body.appendChild(f);
      setTimeout(() => f.remove(), 60000);
    }});
  }});
  // Reflect the selection count on the download buttons.
  document.addEventListener('change', e => {{
    if(!e.target.classList || (!e.target.classList.contains('rv-cb') && e.target.id !== 'rvSelAll')) return;
    const n = document.querySelectorAll('.rv-cb:checked').length;
    rvDl.textContent = n ? ('⬇ xlsx (SAP · ' + n + ' selected)') : '⬇ xlsx (SAP)';
    $('rvDownloadPdf').textContent = n ? ('⬇ PDF (' + n + ' selected)') : '⬇ PDF';
    $('rvDownloadBoth').innerHTML = '⬇ Both' + (n ? (' (' + n + ' selected)') : '') + ' <small>xlsx + PDF</small>';
  }});
}}

// ── Receipt lightbox ─────────────────────────────────────────────────────────
// Click a thumbnail → full image with bbox overlay (multi-receipt highlights the
// matched entry). ocr_bbox is [ymin,xmin,ymax,xmax] in a 0-1000 coord system.
const rvLb = $('rvLb'), rvLbImg = $('rvLbImg'), rvLbSvg = $('rvLbSvg');

function rvEscSvg(s){{
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}}

function rvPaintBoxes(boxes, curId){{
  const img = rvLbImg, svg = rvLbSvg;
  if(!boxes.length || !img.naturalWidth){{ svg.innerHTML=''; svg.style.display='none'; return; }}
  const cW=img.clientWidth, cH=img.clientHeight, nW=img.naturalWidth, nH=img.naturalHeight;
  const scale=Math.min(cW/nW, cH/nH), dW=nW*scale, dH=nH*scale;
  svg.style.left=((cW-dW)/2)+'px'; svg.style.top=((cH-dH)/2)+'px';
  svg.style.width=dW+'px'; svg.style.height=dH+'px';
  svg.setAttribute('viewBox','0 0 '+dW+' '+dH);
  svg.style.display='block';
  svg.innerHTML = boxes.map(function(x,i){{
    const b=x.ocr_bbox;
    const x0=b[1]/1000*dW, y0=b[0]/1000*dH, x1=b[3]/1000*dW, y1=b[2]/1000*dH;
    const isCur=(x.id===curId);
    const col=isCur?'#38bdf8':'#64748b', sw=isCur?2.5:1.5;
    const ty=Math.max(y0+13,13);
    return '<rect x="'+x0.toFixed(1)+'" y="'+y0.toFixed(1)+'" width="'+(x1-x0).toFixed(1)+
      '" height="'+(y1-y0).toFixed(1)+'" rx="4" fill="'+col+'" fill-opacity="'+(isCur?0.12:0.05)+
      '" stroke="'+col+'" stroke-width="'+sw+'"/>'+
      '<text x="'+(x0+4).toFixed(1)+'" y="'+ty.toFixed(1)+'" fill="'+col+'" font-size="11" '+
      'font-weight="700" style="paint-order:stroke;stroke:rgba(2,6,23,.75);stroke-width:3px">'+
      rvEscSvg(''+(i+1))+'</text>';
  }}).join('');
}}

function rvOpenLightbox(data){{
  // Build the list of boxes to draw: siblings if present, else this entry alone.
  let boxes = (data.siblings && data.siblings.length)
    ? data.siblings.filter(s => Array.isArray(s.ocr_bbox))
    : (Array.isArray(data.bbox) ? [{{id: data.id, ocr_bbox: data.bbox}}] : []);
  rvLbSvg.innerHTML=''; rvLbSvg.style.display='none';
  rvLbImg.src = '/cardconv/receipts/image/' + data.fid;
  $('rvLbCaption').textContent = data.merchant || '';
  const drive = $('rvLbDrive');
  if(data.drive){{ drive.href = data.drive; drive.style.display=''; }}
  else drive.style.display='none';
  const render = () => rvPaintBoxes(boxes, data.id);
  rvLbImg.onload = render;
  if(rvLbImg.complete && rvLbImg.naturalWidth) render();
  rvLb.classList.add('open');
}}

function rvCloseLightbox(){{ rvLb.classList.remove('open'); rvLbImg.src=''; }}

document.querySelectorAll('.rv-thumb[data-rv]').forEach(img => {{
  img.addEventListener('click', () => {{
    try {{ rvOpenLightbox(JSON.parse(img.dataset.rv)); }} catch(e) {{}}
  }});
}});
$('rvLbClose').addEventListener('click', rvCloseLightbox);
rvLb.addEventListener('click', e => {{ if(e.target === rvLb) rvCloseLightbox(); }});
document.addEventListener('keydown', e => {{ if(e.key === 'Escape') rvCloseLightbox(); }});
window.addEventListener('resize', () => {{ if(rvLb.classList.contains('open')) rvLbImg.onload && rvLbImg.onload(); }});
applyPreset('all');

// ── Manual match — right-side panel ──────────────────────────────────────────
var _mmTxn = null;

function rvOpenMatchPanel(btn) {{
  var txnRaw = btn ? btn.getAttribute('data-txn') : '{{}}';
  try {{ _mmTxn = JSON.parse(txnRaw); }} catch(x) {{ _mmTxn = {{}}; }}

  var pop = document.getElementById('rvMatchPop');
  var list = document.getElementById('rvMatchList');

  // Position popover near the button
  var rect = btn.getBoundingClientRect();
  var popW = 320;
  var left = rect.right + 8;
  if (left + popW > window.innerWidth - 8) left = rect.left - popW - 8;
  if (left < 8) left = 8;
  var top = rect.top;
  var maxH = window.innerHeight - top - 16;
  if (maxH < 200) {{ top = Math.max(8, rect.bottom - 300); maxH = Math.min(300, window.innerHeight - top - 8); }}

  pop.style.left  = left + 'px';
  pop.style.top   = top + 'px';
  pop.style.maxHeight = Math.max(200, maxH) + 'px';
  pop.style.display = 'flex';

  document.getElementById('rvPopTitle').textContent =
    (_mmTxn.merchant || '') + (_mmTxn.date ? '  ' + _mmTxn.date : '') +
    (_mmTxn.amount != null ? '  $' + Number(_mmTxn.amount).toFixed(2) : '');

  list.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:.8rem">Loading…</div>';

  fetch('/cardconv/ledger/api?status=all')
    .then(function(r) {{ return r.json(); }})
    .then(function(d) {{ rvRenderMatchList(d.entries || []); }})
    .catch(function() {{ list.innerHTML = '<div style="padding:12px;color:red;font-size:.8rem">Load failed</div>'; }});
}}

function rvCloseMatchPanel() {{
  document.getElementById('rvMatchPop').style.display = 'none';
}}

function rvRenderMatchList(entries) {{
  var list = document.getElementById('rvMatchList');
  var pending = entries.filter(function(e) {{ return e.match_status !== 'matched'; }});
  if (!pending.length) {{
    list.innerHTML = '<div style="padding:16px;text-align:center;color:var(--text-muted);font-size:.8rem">No unmatched receipts</div>';
    return;
  }}
  list.innerHTML = pending.map(function(e) {{
    var fid = e.file_id || '';
    var tn  = fid ? 'https://drive.google.com/thumbnail?id=' + fid + '&sz=w80' : '';
    var img = tn ? '<img src="' + tn + '" width="44" height="44" style="object-fit:cover;border-radius:4px;flex-shrink:0">' : '';
    var badge = e.match_status === 'pending_match' ? 'Pending' : 'Unmatched';
    return '<div style="display:flex;gap:8px;align-items:center;padding:8px 12px;border-bottom:1px solid var(--border);cursor:pointer;font-size:.8rem" '
      + 'onclick="rvDoMatch(this)" data-rcpt="' + e.id.replace(/"/g, '') + '">'
      + img
      + '<div style="flex:1;min-width:0">'
      +   '<div style="font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + (e.ocr_merchant || '–') + '</div>'
      +   '<div style="color:var(--text-muted);font-size:.72rem">' + (e.ocr_date || '–') + '  ' + badge + '</div>'
      + '</div>'
      + '<div style="font-weight:700;color:var(--accent);flex-shrink:0">' + (e.ocr_amount != null ? '$' + Number(e.ocr_amount).toFixed(2) : '–') + '</div>'
      + '</div>';
  }}).join('');
}}

function rvDoMatch(el) {{
  if (!_mmTxn) return;
  var rcptId = el.dataset.rcpt;
  fetch('/cardconv/review/match', {{
    method: 'POST',
    headers: {{'Content-Type': 'application/x-www-form-urlencoded'}},
    body: 'row_id=' + encodeURIComponent(_mmTxn.id || '') + '&receipt_id=' + encodeURIComponent(rcptId)
  }}).then(function(r) {{ return r.json(); }}).then(function(d) {{
    if (d.ok) {{ rvCloseMatchPanel(); location.reload(); }}
    else {{ alert('Match failed: ' + (d.error || 'unknown')); }}
  }});
}}

document.addEventListener('keydown', function(e) {{
  if (e.key === 'Escape') rvCloseMatchPanel();
}});
document.addEventListener('click', function(e) {{
  var pop = document.getElementById('rvMatchPop');
  if (pop && pop.style.display !== 'none' && !pop.contains(e.target) && !e.target.closest('[onclick*="rvOpenMatchPanel"]'))
    rvCloseMatchPanel();
}});
</script>

<!-- Manual match popover -->
<div id="rvMatchPop" style="display:none;position:fixed;width:320px;background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);z-index:9999;flex-direction:column;box-shadow:0 8px 32px rgba(0,0,0,.35);overflow:hidden">
  <div style="display:flex;align-items:center;justify-content:space-between;padding:10px 12px;border-bottom:1px solid var(--border);flex-shrink:0">
    <div id="rvPopTitle" style="font-size:.78rem;font-weight:600;color:var(--text);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;max-width:250px"></div>
    <button onclick="rvCloseMatchPanel()" style="background:none;border:none;color:var(--text-muted);font-size:1.2rem;cursor:pointer;line-height:1;padding:0 2px;flex-shrink:0">&times;</button>
  </div>
  <div id="rvMatchList" style="overflow-y:auto;max-height:inherit"></div>
</div>
</body></html>'''


def _render_ocr_staging_review(user: str) -> str:
    from server import CSS_VER
    staging  = _load_ocr_staging(user)
    entries  = staging.get("entries", [])

    def money(a):
        return f'${a:,.2f}' if isinstance(a, (int, float)) else (_esc(str(a)) if a else '–')

    _FX_SYM = {"KRW": "₩", "INR": "₹", "HKD": "HK$", "EUR": "€", "JPY": "¥"}

    def money_fx(e, a):
        """Foreign receipts show the conversion up-front: '₩45,000 → ~$29.72'."""
        if not isinstance(a, (int, float)):
            return _esc(str(a)) if a else '–'
        cur = e.get("ocr_currency")
        if not cur or cur == "USD":
            return f'${a:,.2f}'
        sym  = _FX_SYM.get(cur, cur + ' ')
        orig = f'{sym}{a:,.0f}' if cur in ("KRW", "JPY") else f'{sym}{a:,.2f}'
        usd  = e.get("usd_estimate")
        return f'{orig} → ~${usd:,.2f}' if isinstance(usd, (int, float)) else orig

    cards = []
    for e in entries:
        eid     = _esc(e.get("id", ""))
        fid     = e.get("file_id", "")
        proxy   = f'/cardconv/receipts/image/{_esc(fid)}' if fid else ''
        fn      = _esc(e.get("filename", ""))
        date_v  = _esc(e.get("ocr_date") or '–')
        merch_v = _esc(e.get("ocr_merchant") or '–')
        amt_v   = money_fx(e, e.get("ocr_amount"))
        hw_v    = money_fx(e, e.get("ocr_handwritten_amount"))
        status  = _esc(e.get("ocr_status", ""))
        # Foreign currency: FX badge + rate row so the conversion is visible
        # before the user confirms the staged receipts into the Ledger.
        fx_cur  = e.get("ocr_currency")
        fx_rate = e.get("fx_rate")
        if fx_cur and fx_cur != "USD":
            fx_badge = f'<span class="stg-badge fx">{_esc(fx_cur)}</span>'
            rate_txt = (f'1 USD ≈ {_FX_SYM.get(fx_cur, "")}{fx_rate:,.2f} (ECB, {date_v})'
                        if isinstance(fx_rate, (int, float)) else 'FX rate lookup failed — rerun OCR')
            fx_row = (f'<div class="stg-row"><span class="stg-lbl">FX</span>'
                      f'<span class="stg-val" style="color:var(--warn)">{rate_txt}</span></div>')
        else:
            fx_badge, fx_row = '', ''

        img_html = (f'<img src="{proxy}" class="stg-thumb" loading="lazy" '
                    f'onerror="this.style.display=\'none\'">'
                    if proxy else '<div class="stg-nophoto">No image</div>')

        ocr_ok = e.get("ocr_status") == "done" and e.get("ocr_merchant")
        badge  = ('<span class="stg-badge ok">OCR OK</span>' if ocr_ok
                  else '<span class="stg-badge warn">OCR partial</span>')

        cards.append(f'''
<div class="stg-card" id="card-{eid}">
  <label class="stg-check-wrap">
    <input type="checkbox" name="confirmed" value="{eid}" {"checked" if ocr_ok else ""}>
    <span class="stg-check-lbl">Include</span>
  </label>
  <div class="stg-img-wrap">{img_html}</div>
  <div class="stg-info">
    <div class="stg-filename">{fn} {badge} {fx_badge}</div>
    <div class="stg-row"><span class="stg-lbl">Date</span><span class="stg-val">{date_v}</span></div>
    <div class="stg-row"><span class="stg-lbl">Merchant</span><span class="stg-val">{merch_v}</span></div>
    <div class="stg-row"><span class="stg-lbl">Printed</span><span class="stg-val">{amt_v}</span></div>
    <div class="stg-row"><span class="stg-lbl">Handwritten</span><span class="stg-val">{hw_v}</span></div>
    {fx_row}
  </div>
</div>''')

    body_html = ''.join(cards) if cards else (
        '<div class="stg-empty">No pending OCR entries. '
        '<a href="/cardconv/ledger">Go to Ledger</a></div>')

    count = len(entries)
    return f'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>OCR Review · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v={CSS_VER}">
<style>
{_CC_TAB_CSS}
.stg-header{{display:flex;align-items:center;justify-content:space-between;margin-bottom:18px;flex-wrap:wrap;gap:10px}}
.stg-title{{font-size:1.2rem;font-weight:700}}
.stg-count{{font-size:.85rem;color:var(--text-muted)}}
.stg-actions{{display:flex;gap:10px;align-items:center;flex-wrap:wrap}}
.stg-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(280px,1fr));gap:16px}}
.stg-card{{background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);
  overflow:hidden;display:flex;flex-direction:column}}
.stg-card:has(input:not(:checked)){{opacity:.55;border-style:dashed}}
.stg-check-wrap{{display:flex;align-items:center;gap:8px;padding:10px 12px;border-bottom:1px solid var(--border);
  cursor:pointer;background:var(--surface)}}
.stg-check-wrap input{{width:16px;height:16px;accent-color:var(--accent);cursor:pointer}}
.stg-check-lbl{{font-size:.82rem;font-weight:600;color:var(--text)}}
.stg-img-wrap{{background:#000;display:flex;align-items:center;justify-content:center;min-height:160px;max-height:260px;overflow:hidden}}
.stg-thumb{{max-width:100%;max-height:260px;object-fit:contain;display:block}}
.stg-nophoto{{color:var(--text-muted);font-size:.8rem;padding:20px}}
.stg-info{{padding:12px}}
.stg-filename{{font-size:.78rem;color:var(--text-muted);margin-bottom:8px;display:flex;align-items:center;gap:6px;flex-wrap:wrap}}
.stg-row{{display:flex;justify-content:space-between;font-size:.83rem;padding:3px 0;border-bottom:1px solid var(--border-faint,var(--border))}}
.stg-row:last-child{{border-bottom:none}}
.stg-lbl{{color:var(--text-muted);font-size:.76rem}}
.stg-val{{font-weight:600}}
.stg-badge{{font-size:.65rem;font-weight:700;padding:2px 7px;border-radius:10px}}
.stg-badge.ok{{background:rgba(34,197,94,.15);color:#22c55e}}
.stg-badge.fx{{background:rgba(251,191,36,.15);color:#fbbf24}}
.stg-badge.warn{{background:rgba(245,158,11,.15);color:#f59e0b}}
.stg-empty{{text-align:center;color:var(--text-muted);padding:60px 20px}}
</style>
</head><body>
{_tab_bar("ocr_review", user)}
<div style="max-width:1100px;margin:0 auto;padding:20px 16px">
  <div class="stg-header">
    <div>
      <div class="stg-title">OCR Review</div>
      <div class="stg-count">{count} receipt(s) pending — check what to add to the ledger</div>
    </div>
    <div class="stg-actions">
      <button type="button" onclick="toggleAll(true)" class="btn btn-secondary" style="font-size:.82rem;padding:6px 14px">Check All</button>
      <button type="button" onclick="toggleAll(false)" class="btn btn-secondary" style="font-size:.82rem;padding:6px 14px">Uncheck All</button>
    </div>
  </div>
  <form method="POST" action="/cardconv/receipts/review/confirm" id="stgForm">
    <div class="stg-grid">
      {body_html}
    </div>
    <div style="display:flex;gap:12px;margin-top:24px;justify-content:flex-end;flex-wrap:wrap">
      <form method="POST" action="/cardconv/receipts/review/discard" style="margin:0">
        <button type="submit" class="btn btn-danger" onclick="return confirm('Discard all staged entries?')"
          style="font-size:.85rem">Discard All</button>
      </form>
      <button type="submit" form="stgForm" class="btn btn-primary" style="font-size:.85rem">
        ✓ Confirm Selected → Add to Ledger
      </button>
    </div>
  </form>
</div>
<script>
function toggleAll(on) {{
  document.querySelectorAll('#stgForm input[type=checkbox]').forEach(cb => cb.checked = on);
}}
</script>
</body></html>'''


def _render_ledger(user: str) -> str:
    from server import CSS_VER
    vapid_pub = os.environ.get("VAPID_PUBLIC_KEY", "")
    return (_LEDGER_HTML
            .replace("__CSSVER__", str(CSS_VER))
            .replace("__USER__", user)
            .replace("__TABS__", _tab_bar("ledger", user))
            .replace("__REGISTER__", _register_section(user))
            .replace("__TABCSS__", _CC_TAB_CSS + _UPLOAD_CSS)
            .replace("__RCPTJS__", _RCPT_JS)
            .replace("__VAPID_PUB__", vapid_pub))


# Raw (non-f) template so CSS/JS braces need no escaping; only __TOKENS__ are filled.
_LEDGER_HTML = r'''<!DOCTYPE html>
<html lang="en"><head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>🧾 Receipt Ledger · Wayfinder</title>
<link rel="stylesheet" href="/static/style.css?v=__CSSVER__">
<style>
__TABCSS__
.stat-grid{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;margin-bottom:16px}
.stat-click{cursor:pointer;transition:border-color .12s}
.stat-click:hover{border-color:var(--accent)}
.stat-click.active{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent) inset}
.stat-card{background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);
  padding:16px 20px;text-align:center}
.stat-value{font-size:1.6rem;font-weight:700;color:var(--text);line-height:1.2}
.stat-label{font-size:.73rem;color:var(--text-muted);margin-top:4px;text-transform:uppercase;letter-spacing:.06em}
.filter-bar{display:flex;align-items:center;gap:14px;padding:9px 16px;background:var(--surface-2);
  border:1px solid var(--border);border-radius:var(--radius-md);margin-bottom:8px;flex-wrap:wrap}
.filter-bar:last-of-type{margin-bottom:14px}
.filter-bar input[type=date],.filter-bar input[type=text],.filter-bar select{background:var(--surface);border:1px solid var(--border);
  border-radius:6px;color:var(--text);font-size:.82rem;padding:5px 8px;outline:none}
.filter-bar input[type=date]:focus,.filter-bar input[type=text]:focus,.filter-bar select:focus{border-color:var(--accent)}
/* label+control bundled so a wrap never separates a label from its input */
.fb-field{display:inline-flex;align-items:center;gap:7px;white-space:nowrap}
.fb-field>span{font-size:.74rem;font-weight:700;color:var(--text-muted);text-transform:uppercase;letter-spacing:.05em}
.fb-dash{color:var(--text-muted);padding:0 2px}
.fb-group{display:inline-flex;align-items:center;gap:6px;flex-wrap:wrap}
.fb-spacer{margin-left:auto}
/* selection-action buttons: color via class, share one disabled treatment */
.fb-act-complete{background:rgba(129,140,248,.15);color:#818cf8;border:1px solid rgba(129,140,248,.3)}
.fb-act-uncomplete{background:rgba(148,163,184,.15);color:#94a3b8;border:1px solid rgba(148,163,184,.3)}
.fb-act-delete{background:rgba(239,68,68,.15);color:#ef4444;border:1px solid rgba(239,68,68,.3)}
.filter-bar .btn[disabled]{opacity:.45;cursor:default}
/* inline usage + card-type editors in the ledger table */
.usage-sel,.card-sel{background:var(--surface);border:1px solid transparent;border-radius:6px;color:var(--text);
  font-size:.8rem;padding:3px 6px;cursor:pointer;max-width:130px}
.usage-sel:hover,.card-sel:hover{border-color:var(--border)}
.usage-sel:focus,.card-sel:focus{border-color:var(--accent);outline:none}
/* transient toast for bulk-action feedback */
.cc-toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%) translateY(20px);
  background:var(--surface);border:1px solid var(--border);border-radius:10px;padding:12px 18px;
  font-size:.84rem;color:var(--text);box-shadow:0 8px 30px rgba(0,0,0,.4);opacity:0;pointer-events:none;
  transition:opacity .2s,transform .2s;z-index:2000;max-width:80vw;text-align:center}
.cc-toast.show{opacity:1;transform:translateX(-50%) translateY(0)}
.cc-toast.warn{border-color:rgba(245,158,11,.5)}
.ledger-table{width:100%;border-collapse:collapse;font-size:.83rem}
.ledger-table th{padding:8px 7px;text-align:left;font-size:.72rem;font-weight:700;text-transform:uppercase;
  letter-spacing:.07em;color:var(--text-muted);border-bottom:1px solid var(--border)}
.ledger-table td{padding:10px 7px;border-bottom:1px solid var(--border);vertical-align:middle}
.ledger-scroll{overflow-x:auto}
.ledger-table tbody tr:hover td{background:var(--surface-2);cursor:pointer}
.ledger-table tr:last-child td{border-bottom:none}
.ledger-table tr.dup-row td{background:rgba(250,204,21,.10)}
.ledger-table tr.dup-row:hover td{background:rgba(250,204,21,.18)}
.dup-tag{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:10px;font-size:.6rem;
  font-weight:700;background:rgba(250,204,21,.22);color:#b45309;white-space:nowrap}
.keep-tag{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:10px;font-size:.6rem;
  font-weight:700;background:rgba(34,197,94,.16);color:#16a34a;white-space:nowrap}
.row-check{width:15px;height:15px;cursor:pointer;accent-color:var(--accent)}
.preset-btn{background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--text);
  font-size:.76rem;padding:4px 9px;cursor:pointer}
.preset-btn:hover{border-color:var(--accent)}
.preset-btn.active{background:rgba(250,204,21,.18);border-color:#facc15;color:#b45309;font-weight:700}
.grp-toggle{display:inline-block;margin-left:6px;padding:1px 7px;border-radius:10px;font-size:.62rem;
  font-weight:700;background:rgba(99,102,241,.18);color:#6366f1;cursor:pointer;white-space:nowrap}
.grp-toggle:hover{background:rgba(99,102,241,.3)}
.ledger-table tr.dup-child{display:none}
.ledger-table tr.dup-child.show{display:table-row}
.del-modal{position:fixed;top:50%;left:50%;transform:translate(-50%,-50%) scale(.96);z-index:120;
  width:380px;max-width:92vw;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-md);padding:22px 22px 18px;opacity:0;pointer-events:none;
  transition:opacity .18s,transform .18s;box-shadow:0 12px 40px rgba(0,0,0,.4)}
.del-modal.open{opacity:1;pointer-events:all;transform:translate(-50%,-50%) scale(1)}
.del-title{font-size:1rem;font-weight:700;margin-bottom:10px}
.del-body{font-size:.86rem;color:var(--text);margin-bottom:14px}
.del-check{display:flex;align-items:center;gap:8px;font-size:.82rem;color:var(--text-muted);
  cursor:pointer;margin-bottom:18px}
.del-check input{width:15px;height:15px;cursor:pointer;accent-color:var(--danger)}
.del-actions{display:flex;justify-content:flex-end;gap:10px}
.receipt-thumb{width:40px;height:40px;border-radius:6px;object-fit:cover;border:1px solid var(--border);
  background:var(--surface-3);cursor:zoom-in}
.receipt-thumb-placeholder{width:40px;height:40px;border-radius:6px;border:1px dashed var(--border);
  display:flex;align-items:center;justify-content:center;font-size:.75rem;color:var(--text-muted)}
.status-badge{display:inline-flex;align-items:center;gap:4px;padding:3px 8px;border-radius:999px;
  font-size:.72rem;font-weight:700;white-space:nowrap}
.status-matched{background:rgba(34,197,94,.15);color:#22c55e}
.status-unmatched{background:rgba(239,68,68,.15);color:#ef4444}
.status-pending_match{background:rgba(245,158,11,.15);color:#f59e0b}
.ai-badge{font-size:.62rem;font-weight:700;padding:1px 6px;border-radius:10px;white-space:nowrap}
.ai-badge.gemini{color:#1a73e8;background:rgba(26,115,232,.1)}
.ai-badge.claude{color:#7c3aed;background:rgba(124,58,237,.1)}
.card-badge{font-size:.66rem;font-weight:700;padding:2px 8px;border-radius:10px;white-space:nowrap}
.card-amex{color:#1e40af;background:rgba(37,99,235,.14)}
.card-visa{color:#6d28d9;background:rgba(124,58,237,.12)}
.card-other{color:#64748b;background:rgba(100,116,139,.14)}
.comp-tag{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:10px;font-size:.6rem;
  font-weight:700;background:rgba(129,140,248,.18);color:#818cf8;white-space:nowrap}
.with-tag{display:inline-block;margin-left:6px;padding:1px 6px;border-radius:10px;font-size:.6rem;
  font-weight:700;background:var(--accent-glow,rgba(56,189,248,.12));color:var(--accent);white-space:nowrap}
.ledger-table tr.completed-row td{opacity:.62}
.ledger-table tr.completed-row:hover td{opacity:.85}
.overlay-bg{position:fixed;inset:0;background:rgba(0,0,0,.55);z-index:100;opacity:0;pointer-events:none;transition:opacity .2s}
.overlay-bg.open{opacity:1;pointer-events:all}
.detail-panel{position:fixed;top:0;right:0;width:420px;max-width:100vw;height:100vh;background:var(--surface);
  border-left:1px solid var(--border);z-index:101;transform:translateX(100%);
  transition:transform .25s cubic-bezier(.4,0,.2,1);overflow-y:auto;display:flex;flex-direction:column}
.detail-panel.open{transform:translateX(0)}
.detail-panel-header{display:flex;align-items:center;justify-content:space-between;padding:16px 20px;
  border-bottom:1px solid var(--border)}
.detail-section{padding:16px 20px;border-bottom:1px solid var(--border)}
.detail-section-title{font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.08em;
  color:var(--text-muted);margin-bottom:10px}
.detail-row{display:flex;justify-content:space-between;font-size:.84rem;padding:4px 0}
.detail-row .key{color:var(--text-muted)}
.detail-row .val{font-weight:600;color:var(--text)}
.receipt-image-full{width:100%;border-radius:var(--radius-md);border:1px solid var(--border);
  object-fit:contain;max-height:320px;background:var(--surface-2)}
.receipt-image-wrap{position:relative;line-height:0}
/* SVG is sized/positioned in JS to overlap the rendered (object-fit:contain) image rect. */
.receipt-bbox-overlay{position:absolute;top:0;left:0;pointer-events:none;display:none}
.detail-actions{padding:16px 20px;display:flex;flex-direction:column;gap:8px;margin-top:auto}
.filter-bar [hidden],.fb-chips[hidden]{display:none!important}
.fb-pop-wrap{position:relative}
.fb-advanced{display:none;position:absolute;top:calc(100% + 8px);right:0;z-index:120;background:var(--surface-3);border:1px solid var(--border-bright);border-radius:var(--radius-md);box-shadow:0 12px 34px rgba(0,0,0,.55);padding:14px;min-width:440px;flex-direction:column;gap:12px}
.fb-advanced.open{display:flex}
.fb-adv-grid{display:grid;grid-template-columns:1fr 1fr;gap:10px 18px}
.fb-adv-grid .fb-field{justify-content:space-between}
.fb-adv-foot{display:flex;justify-content:flex-end;border-top:1px solid var(--border-bright);padding-top:10px}
.fb-badge{display:inline-flex;align-items:center;justify-content:center;min-width:16px;height:16px;border-radius:999px;background:var(--accent);color:var(--on-accent,#080d14);font-size:.65rem;font-weight:800;padding:0 4px}
.fb-menu{display:none;position:absolute;top:calc(100% + 8px);right:0;z-index:120;background:var(--surface-3);border:1px solid var(--border-bright);border-radius:var(--radius-md);box-shadow:0 12px 34px rgba(0,0,0,.55);padding:6px;min-width:280px;flex-direction:column;gap:2px}
.fb-menu.open{display:flex}
.fb-menu-item{display:flex;align-items:center;gap:8px;background:none;border:none;border-radius:7px;color:var(--text);font-size:.8rem;font-weight:600;padding:8px 10px;cursor:pointer;text-align:left;white-space:nowrap}
.fb-menu-item:hover{background:var(--surface-2)}
.fb-menu-item small{color:var(--text-muted);font-weight:500}
.fb-search{flex:1;min-width:140px;flex-wrap:nowrap!important}
.fb-search input{flex:1;width:auto;min-width:0}
.fb-chips{display:flex;align-items:center;gap:8px;flex-wrap:wrap;margin-bottom:10px;padding:0 4px}
.fb-chip{display:inline-flex;align-items:center;gap:7px;background:rgba(56,189,248,.12);border:1px solid rgba(56,189,248,.35);color:var(--accent);border-radius:999px;padding:3px 11px;font-size:.74rem;font-weight:600}
.fb-chip i{font-style:normal;opacity:.7;cursor:pointer}
.fb-chip i:hover{opacity:1}
.fb-chip-reset{background:none;border:none;color:var(--text-muted);font-size:.74rem;text-decoration:underline;text-underline-offset:3px;cursor:pointer}
.th-sort{cursor:pointer;user-select:none}
.th-sort:hover{color:var(--text)}
.th-sort.on{color:var(--accent)}
@media(max-width:640px){.fb-advanced{position:fixed;left:12px;right:12px;top:auto;bottom:84px;min-width:0;max-height:55vh;overflow-y:auto;z-index:220}.fb-adv-grid{grid-template-columns:1fr}}
.fb-more-btn{background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--text-muted);font-size:.78rem;font-weight:600;padding:5px 11px;cursor:pointer;display:inline-flex;align-items:center;gap:5px}
.fb-more-btn:hover{border-color:var(--accent);color:var(--text)}
.fb-more-btn .chev{transition:transform .18s}
.fb-more-btn.open .chev{transform:rotate(180deg)}
.fb-selbar{display:none;align-items:center;gap:10px;padding:9px 16px;background:rgba(129,140,248,.08);border:1px solid rgba(129,140,248,.25);border-radius:var(--radius-md);margin-bottom:8px;flex-wrap:wrap}
.sb-edit-group{display:inline-flex;align-items:center;gap:7px;padding-left:12px;border-left:1px solid rgba(129,140,248,.35)}
.sb-label{font-size:.64rem;font-weight:800;letter-spacing:.09em;text-transform:uppercase;color:#a5b4fc;white-space:nowrap}
.sb-act{background:var(--surface-3);border:1px solid var(--border-bright);border-radius:7px;color:var(--text);
  font-size:.78rem;font-weight:600;padding:6px 11px;cursor:pointer;outline:none;line-height:1.2}
.sb-act:hover,.sb-act:focus{border-color:var(--accent);color:var(--accent)}
select.sb-act{padding:5px 8px}
.fb-selbar.show{display:flex}
.fb-selcount{font-size:.8rem;font-weight:700;color:var(--text)}
@media(max-width:640px){.detail-panel{width:100vw}.stat-grid{grid-template-columns:1fr 1fr}.filter-bar{gap:8px;padding:9px 12px}.filter-bar .fb-field{flex-wrap:wrap}.preset-btn{padding:7px 12px}.row-check,.del-check input{width:20px;height:20px}.usage-sel,.card-sel{padding:6px 8px;max-width:none}.ledger-table,.ledger-table tbody,.ledger-table tr,.ledger-table td{display:block;width:100%}.ledger-table thead{display:none}.ledger-table tr{background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius-md);margin-bottom:10px;padding:10px 12px;position:relative}.ledger-table tr:hover td{background:transparent}.ledger-table td{border-bottom:none!important;padding:5px 0;display:flex;justify-content:space-between;align-items:center;gap:10px;text-align:right}.ledger-table td::before{content:attr(data-label);font-size:.7rem;font-weight:700;text-transform:uppercase;letter-spacing:.05em;color:var(--text-muted);text-align:left}.ledger-table td[data-label=Select]{position:absolute;top:8px;right:10px;padding:0}.ledger-table td[data-label=Select]::before{display:none}.ledger-table td[data-label=Date]{font-weight:700;font-size:.95rem;padding-right:34px}}
</style>
</head><body>
<nav>
  <span class="nav-brand">💳 Cheil AMEX Expense Assistant</span>
  <span class="nav-user">👤 __USER__ &nbsp;·&nbsp; <a href="/logout">Logout</a></span>
</nav>
<div class="container" style="max-width:1100px">

  __TABS__

  __REGISTER__

  <div class="stat-grid">
    <div class="stat-card stat-click" data-statview="total" title="Show all active receipts"><div class="stat-value" id="statTotal">–</div><div class="stat-label">Total</div></div>
    <div class="stat-card stat-click" data-statview="matched" title="Matched receipts only"><div class="stat-value" id="statMatched" style="color:#22c55e">–</div><div class="stat-label">Matched</div></div>
    <div class="stat-card stat-click" data-statview="unmatched" title="No transaction matched yet (includes Pending Match)"><div class="stat-value" id="statUnmatched" style="color:#ef4444">–</div><div class="stat-label">Unmatched</div></div>
    <div class="stat-card stat-click" data-statview="in_progress" title="Settlement submitted, awaiting approval"><div class="stat-value" id="statInProg" style="color:#f59e0b">–</div><div class="stat-label">⏳ In progress</div></div>
    <div class="stat-card stat-click" data-statview="completed" title="Archived receipts"><div class="stat-value" id="statCompleted" style="color:#818cf8">–</div><div class="stat-label">Completed</div></div>
  </div>

  <!-- Toolbar · one row, one job per control: Period / Search / Filters / Export.
       Status filtering lives on the stat cards; fine-grained state in the Filters popover. -->
  <div class="filter-bar">
    <div class="fb-field">
      <span>Period</span>
      <select id="fPeriod">
        <option value="all">All time</option>
        <option value="month">This month</option>
        <option value="30d">30 days</option>
        <option value="3m">3 months</option>
        <option value="ytd">YTD</option>
        <option value="custom">Custom…</option>
      </select>
    </div>
    <div class="fb-field" id="fCustomRange" hidden>
      <input type="date" id="fFrom"><span class="fb-dash">~</span><input type="date" id="fTo">
    </div>
    <div class="fb-field fb-search"><span>🔍</span>
      <input type="text" id="fMerchant" placeholder="Search merchant…">
    </div>
    <select id="fSort" hidden>
      <option value="date">Date ↓</option>
      <option value="merchant">Merchant A→Z</option>
    </select>
    <div class="fb-pop-wrap">
      <button class="fb-more-btn" id="fMore" aria-expanded="false">Filters <span class="chev">▾</span><span class="fb-badge" id="fBadge" hidden>0</span></button>
      <div class="fb-advanced" id="fAdvanced">
        <div class="fb-adv-grid">
          <div class="fb-field"><span>Status</span>
            <select id="fStatus">
              <option value="all">All</option>
              <option value="matched">Matched</option>
              <option value="unmatched_any">Unmatched (any)</option>
              <option value="unmatched">Unmatched only</option>
              <option value="pending_match">Pending Match</option>
            </select>
          </div>
          <div class="fb-field"><span>Card</span>
            <select id="fCard">
              <option value="all">All</option>
              <option value="amex">AMEX</option>
              <option value="visa">Visa</option>
              <option value="other">Cash</option>
              <option value="unknown">Unknown</option>
            </select>
          </div>
          <div class="fb-field"><span>Usage</span>
            <select id="fUsage"><option value="all">All</option></select>
          </div>
          <div class="fb-field"><span>Show</span>
            <select id="fCompleted">
              <option value="hide">Active only</option>
              <option value="only">Completed only</option>
              <option value="all">All</option>
            </select>
          </div>
          <div class="fb-field"><span>Settle</span>
            <select id="fSettle" title="Settlement state of the linked transaction (set on the Review tab)">
              <option value="all">All</option>
              <option value="open">Open</option>
              <option value="in_progress">⏳ In progress</option>
              <option value="completed">✔ Completed</option>
            </select>
          </div>
          <div class="fb-field"><span>Duplicates</span>
            <span style="display:inline-flex;align-items:center;gap:6px">
              <button class="preset-btn" id="viewToggle" title="Collapse duplicate receipts into one row">🔁 Group Duplicates</button>
              <span class="cc-info-wrap"><span class="cc-info" onclick="ccTipToggle(this)">ℹ</span><span class="cc-tip">Groups receipts recognized multiple times from the same image. Delete the redundant duplicates.</span></span>
            </span>
          </div>
        </div>
        <div class="fb-adv-foot">
          <button class="btn btn-ghost btn-sm" id="fReset">↺ Reset all</button>
        </div>
      </div>
    </div>
    <div class="fb-pop-wrap">
      <button class="fb-more-btn" id="fExport" aria-expanded="false">⬇ Export <span class="chev">▾</span></button>
      <div class="fb-menu" id="fExportMenu">
        <button class="fb-menu-item" id="fDownloadXlsx" title="Ledger backup with Card Type/Usage columns — NOT for SAP upload (use Review's xlsx)">⬇ xlsx (ledger) <small>backup · not for SAP</small></button>
        <button class="fb-menu-item" id="fDownload">⬇ PDF <small>receipt report, filtered rows</small></button>
      </div>
    </div>
  </div>

  <!-- Non-default filters stay visible as chips even while the popover is closed -->
  <div class="fb-chips" id="fChips" hidden></div>

  <!-- Bulk-action bar, appears only while rows are selected -->
  <div class="fb-selbar" id="fSelBar">
    <span class="fb-selcount" id="fSelCount">0 selected</span>
    <div class="sb-edit-group" role="group" aria-label="Bulk edits">
      <span class="sb-label">Edit selected</span>
      <select class="sb-act" id="fBulkCard" title="Set card type on all selected">
        <option value="">💳 Card type</option>
        <option value="amex">AMEX</option>
        <option value="visa">Visa</option>
        <option value="other">Cash</option>
        <option value="none">Clear (–)</option>
      </select>
      <select class="sb-act" id="fBulkUsage" title="Set usage tag on all selected">
        <option value="">🏷 Usage tag</option>
      </select>
      <button class="sb-act" id="fBulkWith" title="Set the w/ companion note on all selected">👥 w/ note</button>
      <button class="sb-act" id="fBulkRematch" title="Re-try CSV matching using only the selected receipts">↻ Re-match</button>
    </div>
    <div class="fb-group fb-spacer" role="group" aria-label="Selection actions">
      <button class="btn btn-sm fb-act-complete" id="fComplete" disabled>✓ Complete (0)</button>
      <button class="btn btn-sm fb-act-uncomplete" id="fUncomplete" disabled>↩ Un-complete (0)</button>
      <button class="btn btn-sm fb-act-delete" id="fDelete" disabled>🗑 Delete (0)</button>
    </div>
  </div>

  <div class="notepad-card">
    <div class="notepad-body ledger-scroll" style="padding:8px 16px 4px">
      <table class="ledger-table">
        <thead><tr>
          <th style="width:24px"><input type="checkbox" class="row-check" id="checkAll" title="Select all"></th>
          <th class="th-sort on" id="thDate" title="Sort by date">Date ↓</th><th>Printed</th><th>Handwritten</th><th>Final</th><th class="th-sort" id="thMerchant" title="Sort by merchant A→Z">Merchant</th><th>Card</th><th>Usage</th><th>Receipt</th><th>Status</th><th>Action</th>
        </tr></thead>
        <tbody id="ledgerBody"></tbody>
      </table>
    </div>
  </div>

</div>

<div class="overlay-bg" id="overlay"></div>
<div class="detail-panel" id="panel">
  <div class="detail-panel-header">
    <span style="font-weight:700;font-size:.95rem">Receipt Detail</span>
    <button class="btn btn-ghost btn-sm" id="panelClose">× Close</button>
  </div>
  <div class="detail-section">
    <div class="detail-section-title">Receipt Image <span style="font-size:.7rem;color:var(--text-muted);font-weight:400">(click to enlarge)</span></div>
    <div class="receipt-image-wrap" id="dImageWrap" style="cursor:zoom-in" onclick="openImgLb()">
      <img class="receipt-image-full" id="dImage" alt="receipt">
      <svg class="receipt-bbox-overlay" id="dBboxOverlay"></svg>
    </div>
  </div>
  <div class="detail-section">
    <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:6px">
      <div class="detail-section-title" style="margin-bottom:0">OCR Result</div>
      <button id="dEditBtn" class="btn btn-ghost btn-sm" onclick="togglePanelEdit()" style="font-size:.74rem;padding:3px 10px">✏️ Edit</button>
    </div>
    <div class="detail-row"><span class="key">Date</span>
      <span class="val" id="dDate">–</span>
      <input id="eDate" type="date" style="display:none;width:130px;background:var(--surface);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:.82rem;padding:2px 6px">
    </div>
    <div class="detail-row"><span class="key">Merchant</span>
      <span class="val" id="dMerchant">–</span>
      <input id="eMerchant" type="text" style="display:none;width:100%;background:var(--surface);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:.82rem;padding:2px 6px">
    </div>
    <div class="detail-row" title="Handwritten companion note — appended to the SAP purpose column"><span class="key">With (w/)</span>
      <span class="val" id="dCompanions">–</span>
      <input id="eCompanions" type="text" placeholder="e.g. sds" style="display:none;width:130px;background:var(--surface);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:.82rem;padding:2px 6px">
    </div>
    <div class="detail-row"><span class="key">Printed $</span>
      <span class="val" id="dPrinted">–</span>
      <input id="ePrinted" type="number" step="0.01" style="display:none;width:100px;background:var(--surface);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:.82rem;padding:2px 6px">
    </div>
    <div class="detail-row"><span class="key">Handwritten $</span>
      <span class="val" id="dHand">–</span>
      <input id="eHand" type="number" step="0.01" style="display:none;width:100px;background:var(--surface);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:.82rem;padding:2px 6px">
    </div>
    <div class="detail-row"><span class="key">Amount (final)</span><span class="val" id="dAmount">–</span></div>
    <div class="detail-row"><span class="key">Card Type</span>
      <span class="val" id="dCard">–</span>
      <select id="eCard" style="display:none;width:120px;background:var(--surface);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:.82rem;padding:2px 6px">
        <option value="none">–</option><option value="amex">AMEX</option><option value="visa">Visa</option><option value="other">Cash</option>
      </select>
    </div>
    <div class="detail-row"><span class="key">Usage</span>
      <span class="val" id="dUsage">Regular</span>
      <input id="eUsage" type="text" placeholder="Regular" style="display:none;width:130px;background:var(--surface);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:.82rem;padding:2px 6px">
    </div>
    <div class="detail-row"><span class="key">AI Model</span><span class="val" id="dModel">–</span></div>
    <div id="dSaveRow" style="display:none;margin-top:8px;display:none">
      <button class="btn btn-primary btn-sm" style="width:100%;font-size:.82rem" onclick="savePanelEdit()">💾 Save Changes</button>
    </div>
  </div>
  <div class="detail-section" id="dMatchSection">
    <div class="detail-section-title">Matched CSV Transaction</div>
    <div class="detail-row"><span class="key">Date</span><span class="val" id="dmDate">–</span></div>
    <div class="detail-row"><span class="key">Amount</span><span class="val" id="dmAmount">–</span></div>
    <div class="detail-row"><span class="key">Vendor</span><span class="val" id="dmVendor">–</span></div>
  </div>
  <div class="detail-section">
    <div class="detail-section-title">Status</div>
    <div id="dStatus"></div>
  </div>
  <div class="detail-actions">
    <button class="btn btn-ghost btn-sm" data-set="matched" style="color:#22c55e">✅ Mark Matched</button>
    <button class="btn btn-ghost btn-sm" data-set="unmatched" style="color:#ef4444">❌ Mark Unmatched</button>
    <button class="btn btn-ghost btn-sm" data-set="pending_match" style="color:#f59e0b">⏳ Mark Pending</button>
    <button class="btn btn-ghost btn-sm" id="dCompleteBtn" onclick="togglePanelComplete()" style="color:#818cf8;margin-top:6px;width:100%">✓ Mark Complete</button>
    <button class="btn btn-ghost btn-sm" id="reOcrBtn" onclick="reOCR()" style="color:#818cf8;margin-top:6px;width:100%">🔄 Re-OCR</button>
    <button class="btn btn-ghost btn-sm" id="manualAddBtn" onclick="openManualAdd()" style="color:#34d399;margin-top:2px;width:100%">➕ Manually add a receipt on this image</button>
  </div>
</div>

<!-- Manual Receipt Add Modal -->
<div class="overlay-bg" id="manualOverlay"></div>
<div class="del-modal" id="manualModal" style="width:420px">
  <div class="del-title">➕ Add receipt manually</div>
  <div style="font-size:.82rem;color:var(--text-muted);margin-bottom:14px">Add a receipt on this image that OCR missed.</div>
  <div style="display:flex;flex-direction:column;gap:10px;margin-bottom:16px">
    <div>
      <label style="font-size:.76rem;color:var(--text-muted);display:block;margin-bottom:4px">Date</label>
      <input id="mDate" type="date" style="width:100%;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:.85rem;padding:6px 10px;outline:none;box-sizing:border-box">
    </div>
    <div>
      <label style="font-size:.76rem;color:var(--text-muted);display:block;margin-bottom:4px">Merchant</label>
      <input id="mMerchant" type="text" placeholder="Merchant name" style="width:100%;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:.85rem;padding:6px 10px;outline:none;box-sizing:border-box">
    </div>
    <div style="display:flex;gap:10px">
      <div style="flex:1">
        <label style="font-size:.76rem;color:var(--text-muted);display:block;margin-bottom:4px">Printed amount ($)</label>
        <input id="mPrinted" type="number" step="0.01" min="0" placeholder="0.00" style="width:100%;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:.85rem;padding:6px 10px;outline:none;box-sizing:border-box">
      </div>
      <div style="flex:1">
        <label style="font-size:.76rem;color:var(--text-muted);display:block;margin-bottom:4px">Handwritten amount ✍️</label>
        <input id="mHandw" type="number" step="0.01" min="0" placeholder="Optional" style="width:100%;background:var(--surface);border:1px solid var(--border);border-radius:6px;color:var(--text);font-size:.85rem;padding:6px 10px;outline:none;box-sizing:border-box">
      </div>
    </div>
  </div>
  <div class="del-actions">
    <button class="btn btn-ghost btn-sm" onclick="closeManualAdd()">Cancel</button>
    <button class="btn btn-primary btn-sm" id="manualAddConfirm" onclick="submitManualAdd()">Add</button>
  </div>
</div>

<div class="overlay-bg" id="delOverlay"></div>
<div class="del-modal" id="delModal">
  <div class="del-title">🗑 Delete receipts</div>
  <div class="del-body" id="delBody">Delete the checked receipts from the Ledger?</div>
  <label class="del-check"><input type="checkbox" id="delDrive"> Also move the Drive originals to trash</label>
  <div class="del-actions">
    <button class="btn btn-ghost btn-sm" id="delCancel">Cancel</button>
    <button class="btn btn-sm" id="delConfirm"
      style="background:rgba(239,68,68,.15);color:#ef4444;border:1px solid rgba(239,68,68,.3)">Delete</button>
  </div>
</div>

<script>
let CUR_ID = null, CUR_FILE_ID = null, ENTRIES = [], VIEW_MODE = 'all';
const $ = id => document.getElementById(id);
const STATUS_LABEL = {matched:'✅ Matched', unmatched:'❌ Unmatched', pending_match:'⏳ Pending Match'};

function fmtAmt(a){ return (a===null||a===undefined) ? '–' : '$' + Number(a).toFixed(2); }

// Foreign-currency display: "₩45,000 → ~$33.10" (falls back to fmtAmt for USD).
const FX_SYM = {KRW:'₩', INR:'₹', HKD:'HK$', EUR:'€', JPY:'¥'};
function fmtAmtFx(e, a){
  if(a===null||a===undefined) return '–';
  const cur = e && e.ocr_currency;
  if(!cur || cur === 'USD') return fmtAmt(a);
  const sym = FX_SYM[cur] || (cur + ' ');
  const noDec = (cur === 'KRW' || cur === 'JPY');
  const orig = sym + Number(a).toLocaleString(undefined, {maximumFractionDigits: noDec ? 0 : 2});
  return e.usd_estimate != null ? orig + ' → ~$' + Number(e.usd_estimate).toFixed(2) : orig;
}

function thumb(e){
  if(!e.file_id) return '<div class="receipt-thumb-placeholder">🧾</div>';
  const proxy = '/cardconv/receipts/image/' + e.file_id;
  const tn = 'https://drive.google.com/thumbnail?id=' + e.file_id + '&sz=w80';
  return '<img class="receipt-thumb" src="' + tn + '" loading="lazy" ' +
         'onerror="this.onerror=null;this.src=\'' + proxy + '\'">';
}

const CARD_LABEL = {amex:'AMEX', visa:'Visa', other:'Cash'};
function cardBadge(b){
  if(!b || !CARD_LABEL[b]) return '<span style="color:var(--text-muted);font-size:.72rem">–</span>';
  return '<span class="card-badge card-' + b + '">' + CARD_LABEL[b] + '</span>';
}

function esc1(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

// Transient bottom toast for bulk-action feedback. warn=true tints the border.
function toast(msg, warn){
  let t = document.getElementById('ccToast');
  if(!t){ t = document.createElement('div'); t.id = 'ccToast'; t.className = 'cc-toast'; document.body.appendChild(t); }
  t.textContent = msg;
  t.classList.toggle('warn', !!warn);
  t.classList.add('show');
  clearTimeout(t._h); t._h = setTimeout(function(){ t.classList.remove('show'); }, 3600);
}

// Inline-editable Usage cell: a dropdown of known tags + the current value, plus
// a "+ New…" sentinel that prompts for a fresh tag. Edited straight from the row.
function usageCell(e){
  const cur = e.usage || 'Regular';
  const known = (window.USAGES && window.USAGES.length ? window.USAGES : ['Regular']);
  const opts = Array.from(new Set(['Regular'].concat(known).concat([cur])));
  let html = '<select class="usage-sel" data-id="' + esc1(e.id) + '" title="Change usage">';
  opts.forEach(function(u){
    html += '<option value="' + esc1(u) + '"' + (u===cur?' selected':'') + '>' + esc1(u) + '</option>';
  });
  html += '<option value="__new__">+ New…</option></select>';
  return html;
}

async function changeUsage(sel){
  const id = sel.dataset.id;
  let val = sel.value;
  if(val === '__new__'){
    val = (prompt('New usage tag (leave blank to cancel)', '') || '').trim();
    if(!val){ load(); return; }   // cancelled → revert via reload
  }
  const r = await fetch('/cardconv/ledger/' + id + '/update',
    {method:'POST', body: new URLSearchParams({usage: val})});
  const d = await r.json().catch(function(){ return {}; });
  if(!d.ok){ alert('Usage update failed: ' + (d.error || r.status)); load(); return; }
  const e = ENTRIES.find(function(x){ return x.id===id; }); if(e) e.usage = val;
  load();   // refresh so the Usage filter dropdown picks up any new tag
}

// Inline-editable Card Type cell: dropdown of –/AMEX/Visa/Other, edited from the row.
// The "none" value is an explicit sentinel (empty form values get dropped in
// transit, so they can't clear a field) that the backend maps back to null.
const CARD_OPTS = [['none','–'],['amex','AMEX'],['visa','Visa'],['other','Cash']];
function cardCell(e){
  const cur = e.card_brand || 'none';
  let html = '<select class="card-sel" data-id="' + esc1(e.id) + '" title="Change card type">';
  CARD_OPTS.forEach(function(o){
    html += '<option value="' + o[0] + '"' + (o[0]===cur?' selected':'') + '>' + o[1] + '</option>';
  });
  html += '</select>';
  return html;
}

async function changeCard(sel){
  const id = sel.dataset.id, val = sel.value;
  const r = await fetch('/cardconv/ledger/' + id + '/update',
    {method:'POST', body: new URLSearchParams({card_brand: val})});
  const d = await r.json().catch(function(){ return {}; });
  if(!d.ok){ alert('Card type update failed: ' + (d.error || r.status)); load(); return; }
  const e = ENTRIES.find(function(x){ return x.id===id; }); if(e) e.card_brand = (val==='none' ? null : val);
}

// Settlement state of the linked transaction (managed on the Review tab).
function settleChip(e){
  if(e.settle_status === 'in_progress')
    return '<span style="display:inline-block;margin-left:4px;font-size:.62rem;font-weight:700;padding:1px 6px;' +
           'border-radius:8px;background:rgba(245,158,11,.15);color:#f59e0b" title="Submitted to SAP, awaiting approval">⏳ In progress</span>';
  if(e.settle_status === 'completed')
    return '<span style="display:inline-block;margin-left:4px;font-size:.62rem;font-weight:700;padding:1px 6px;' +
           'border-radius:8px;background:rgba(34,197,94,.15);color:#22c55e" title="Settlement completed">✔ Settled</span>';
  return '';
}

function matchInfo(e){
  const mt = e.matched_transaction;
  if(!mt) return '';
  const parts = [];
  if(mt.vendor) parts.push(mt.vendor);
  if(mt.amount!==null && mt.amount!==undefined) parts.push(fmtAmt(mt.amount));
  if(mt.date) parts.push(mt.date);
  if(!parts.length) return '';
  return '<div style="font-size:.7rem;color:var(--text-muted);margin-top:3px">↳ ' + parts.join(' · ') + '</div>';
}

function fmtAgo(iso){
  if(!iso) return '';
  const t = new Date(iso); if(isNaN(t)) return '';
  const sec = Math.floor((Date.now() - t) / 1000);
  let rel;
  if(sec < 60) rel = 'just now';
  else if(sec < 3600) rel = Math.floor(sec/60) + ' min ago';
  else if(sec < 86400) rel = Math.floor(sec/3600) + ' hr ago';
  else rel = Math.floor(sec/86400) + ' days ago';
  const pad = n => String(n).padStart(2,'0');
  const stamp = t.getFullYear()+'-'+pad(t.getMonth()+1)+'-'+pad(t.getDate())+' '+pad(t.getHours())+':'+pad(t.getMinutes());
  return 'Last synced: ' + stamp + ' (' + rel + ')';
}

function renderLastSynced(iso){
  const el = $('lastSynced');
  if(!el) return;
  const ts = iso || el.dataset.ts;
  if(ts){ el.dataset.ts = ts; }
  el.textContent = fmtAgo(el.dataset.ts);
}

// Build one ledger <tr>. opts.groupHead adds a clickable '+N' badge that toggles
// the group's child rows; opts.groupChild marks a collapsed duplicate row.
function rowHtml(e, i, opts){
  opts = opts || {};
  const h = e.ocr_handwritten_amount;
  const handCell = (h===null||h===undefined)
    ? '<td style="color:var(--text-muted)">–</td>'
    : '<td style="color:#f59e0b;font-weight:600">' + fmtAmt(h) + ' ✍️</td>';
  const actionCell = (e.match_status==='matched')
    ? '<td><button class="btn btn-ghost btn-sm act-undo" data-id="' + e.id +
      '" style="color:#f59e0b;padding:2px 8px" title="Undo match — reset to pending">↩ Undo</button></td>'
    : '<td><button class="btn btn-ghost btn-sm act-rematch" data-id="' + e.id +
      '" style="color:#818cf8;padding:2px 8px" title="Re-try CSV matching for this receipt">🔗 Rematch</button></td>';
  // Duplicate group: non-keeper rows are pre-checked for quick cleanup.
  const preCheck = (e.dup && !e.dup_keep) ? ' checked' : '';
  const checkCell = '<td><input type="checkbox" class="row-check sel" data-id="' +
    e.id + '"' + preCheck + '></td>';
  let dupTag = e.dup
    ? (e.dup_keep ? '<span class="keep-tag">KEEP</span>'
                  : '<span class="dup-tag">🔁 Duplicate</span>')
    : '';
  if(opts.groupHead){
    dupTag = '<span class="grp-toggle" data-gid="' + opts.groupHead + '">+' +
      opts.extra + ' duplicate' + (opts.extra>1?'s':'') + '</span>';
  }
  let cls = e.dup ? 'dup-row' : '';
  if(opts.groupChild) cls += ' dup-child gc-' + opts.groupChild;
  if(e.completed) cls += ' completed-row';
  const compTag = e.completed ? '<span class="comp-tag">✓ Done</span>' : '';
  return '<tr data-i="' + i + '"' + (cls?(' class="'+cls.trim()+'"'):'') + '>' +
    checkCell.replace('<td>','<td data-label="Select">') +
    '<td data-label="Date">' + (e.ocr_date||'–') + dupTag + compTag + '</td>' +
    '<td data-label="Printed" style="color:var(--text-muted)">' + fmtAmt(e.ocr_printed_amount) + '</td>' +
    handCell.replace('<td','<td data-label="Handwritten"') +
    '<td data-label="Final" style="font-weight:700">' + fmtAmtFx(e, e.ocr_amount) + '</td>' +
    '<td data-label="Merchant">' + (e.ocr_merchant||'–') +
      (e.ocr_companions ? '<span class="with-tag" title="Companion note — appended to the SAP purpose">w/ ' + e.ocr_companions + '</span>' : '') + '</td>' +
    '<td data-label="Card">' + cardCell(e) + '</td>' +
    '<td data-label="Usage">' + usageCell(e) + '</td>' +
    '<td data-label="Receipt">' + thumb(e) + '</td>' +
    '<td data-label="Status"><span class="status-badge status-' + (e.match_status||'unmatched') + '">' +
      (STATUS_LABEL[e.match_status]||e.match_status||'–') + '</span>' + settleChip(e) + matchInfo(e) + '</td>' +
    actionCell.replace('<td>','<td data-label="Action">') +
  '</tr>';
}

function renderBody(entries){
  if(VIEW_MODE === 'all') return entries.map((e,i) => rowHtml(e,i)).join('');
  // Group mode: collapse each dup_group_id into a head row + hidden child rows.
  const groups = {}, order = [];
  entries.forEach((e,i) => {
    const gid = e.dup_group_id;
    if(gid){
      if(!groups[gid]){ groups[gid] = []; order.push({type:'group', gid}); }
      groups[gid].push(i);
    } else { order.push({type:'single', i}); }
  });
  // Head index of a group = dup_keep (matched-preferred by backend) entry.
  const headIdx = gid => groups[gid].slice().sort((a, b) =>
    (entries[a].dup_keep ? 0 : 1) - (entries[b].dup_keep ? 0 : 1))[0];
  // Sort all rows (group + single) by head's ocr_date, newest first.
  // None/'unknown' dates sink to the bottom.
  const dateVal = d => {
    if(!d || d === 'unknown') return null;
    const t = Date.parse(d);
    return isNaN(t) ? null : t;
  };
  const headDate = o => dateVal(o.type === 'single'
    ? entries[o.i].ocr_date
    : entries[headIdx(o.gid)].ocr_date);
  order.sort((a, b) => {
    const da = headDate(a), db = headDate(b);
    if(da === null && db === null) return 0;
    if(da === null) return 1;
    if(db === null) return -1;
    return db - da;
  });
  let html = '';
  order.forEach(o => {
    if(o.type==='single'){ html += rowHtml(entries[o.i], o.i); return; }
    // Reorder: dup_keep (matched-preferred by backend) entry becomes head.
    const idxs = groups[o.gid].slice().sort((a, b) => {
      const ka = entries[a].dup_keep ? 0 : 1;
      const kb = entries[b].dup_keep ? 0 : 1;
      return ka - kb;
    });
    const head = idxs[0];
    html += rowHtml(entries[head], head, {groupHead:o.gid, extra:idxs.length-1});
    idxs.slice(1).forEach(ci => { html += rowHtml(entries[ci], ci, {groupChild:o.gid}); });
  });
  return html;
}

function rerender(){
  const body = $('ledgerBody');
  if(!ENTRIES.length){
    body.innerHTML = '<tr><td colspan="11" style="text-align:center;color:var(--text-muted);padding:30px">No receipts</td></tr>';
  } else {
    body.innerHTML = renderBody(ENTRIES);
    body.querySelectorAll('tr[data-i]').forEach(tr =>
      tr.addEventListener('click', () => openPanel(ENTRIES[+tr.dataset.i])));
    body.querySelectorAll('.act-undo').forEach(b =>
      b.addEventListener('click', ev => { ev.stopPropagation(); unmatchRow(b.dataset.id); }));
    body.querySelectorAll('.act-rematch').forEach(b =>
      b.addEventListener('click', ev => { ev.stopPropagation(); quickRematch(b.dataset.id, b); }));
    body.querySelectorAll('.sel').forEach(c =>
      c.addEventListener('click', ev => ev.stopPropagation()));
    body.querySelectorAll('.sel').forEach(c =>
      c.addEventListener('change', updateDeleteBtn));
    body.querySelectorAll('.usage-sel').forEach(s => {
      s.addEventListener('click', ev => ev.stopPropagation());
      s.addEventListener('change', ev => { ev.stopPropagation(); changeUsage(s); });
    });
    body.querySelectorAll('.card-sel').forEach(s => {
      s.addEventListener('click', ev => ev.stopPropagation());
      s.addEventListener('change', ev => { ev.stopPropagation(); changeCard(s); });
    });
    body.querySelectorAll('.grp-toggle').forEach(g =>
      g.addEventListener('click', ev => {
        ev.stopPropagation();
        body.querySelectorAll('.gc-' + g.dataset.gid).forEach(r => r.classList.toggle('show'));
      }));
  }
  $('checkAll').checked = false;
  updateDeleteBtn();
}

// Build the shared filter query string from the current control values.
function filterParams(){
  const p = new URLSearchParams();
  if($('fFrom').value) p.set('from', $('fFrom').value);
  if($('fTo').value)   p.set('to', $('fTo').value);
  p.set('status', $('fStatus').value);
  p.set('card_brand', $('fCard').value);
  p.set('usage', $('fUsage').value);
  p.set('completed', $('fCompleted').value);
  p.set('settle', $('fSettle').value);
  if($('fMerchant').value.trim()) p.set('merchant', $('fMerchant').value.trim());
  p.set('sort', $('fSort').value);
  return p;
}

// Rebuild the Usage dropdown from the distinct tags the API reports, keeping
// the current selection if it still exists.
function syncUsageOptions(usages){
  const sel = $('fUsage'), cur = sel.value;
  const opts = ['<option value="all">All</option>']
    .concat((usages||[]).map(u => '<option value="' + u.replace(/"/g,'&quot;') + '">' + u + '</option>'));
  sel.innerHTML = opts.join('');
  sel.value = (usages||[]).includes(cur) || cur==='all' ? cur : 'all';
  // Bulk selector mirrors the same tags plus a new-tag sentinel.
  const b = $('fBulkUsage');
  if(b){
    b.innerHTML = ['<option value="">🏷 Usage tag</option>']
      .concat((usages||[]).map(u => '<option value="' + u.replace(/"/g,'&quot;') + '">' + u + '</option>'))
      .concat(['<option value="__new__">+ New…</option>']).join('');
  }
}

let _loadSeq = 0;
async function load(){
  const seq = ++_loadSeq;
  const p = filterParams();
  const r = await fetch('/cardconv/ledger/api?' + p.toString());
  const d = await r.json();
  if(seq !== _loadSeq) return;  // superseded by a newer load — drop stale response
  $('statTotal').textContent = d.total;
  $('statMatched').textContent = d.matched;
  $('statUnmatched').textContent = d.unmatched + (d.pending_match || 0);
  $('statInProg').textContent = (d.in_progress!=null ? d.in_progress : '–');
  $('statCompleted').textContent = (d.completed!=null ? d.completed : '–');
  window.USAGES = d.usages || ['Regular'];
  syncUsageOptions(d.usages);
  ENTRIES = d.entries;
  rerender();
  renderLastSynced(d.last_synced);
  updateChips();
}

function escSvg(s){
  return String(s).replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;');
}

// Draw bbox rectangles for every receipt sharing this entry's source image.
// ocr_bbox is [ymin,xmin,ymax,xmax] in a 0-1000 normalized coord system.
function drawBoxes(cur){
  const svg = $('dBboxOverlay'), img = $('dImage');
  if(!svg || !img) return;
  const sibs = (typeof ENTRIES!=='undefined'?ENTRIES:[]).filter(
    x => x.file_id && cur.file_id && x.file_id===cur.file_id && Array.isArray(x.ocr_bbox));
  const render = () => paintBoxes(svg, img, sibs, cur);
  if(img.complete && img.naturalWidth) render();
  // First paint may run before the image has dimensions; redraw on load.
  img.onload = render;
}

function paintBoxes(svg, img, sibs, cur){
  if(!sibs.length || !img.naturalWidth){ svg.innerHTML=''; svg.style.display='none'; return; }
  // object-fit:contain → find the rendered image rect inside the <img> box.
  const cW=img.clientWidth, cH=img.clientHeight, nW=img.naturalWidth, nH=img.naturalHeight;
  const scale=Math.min(cW/nW, cH/nH);
  const dW=nW*scale, dH=nH*scale;
  svg.style.left=(img.offsetLeft+(cW-dW)/2)+'px';
  svg.style.top =(img.offsetTop +(cH-dH)/2)+'px';
  svg.style.width=dW+'px'; svg.style.height=dH+'px';
  svg.setAttribute('viewBox','0 0 '+dW+' '+dH);
  svg.style.display='block';
  svg.innerHTML = sibs.map(function(x,i){
    const b=x.ocr_bbox;                       // [ymin,xmin,ymax,xmax] 0-1000
    const x0=b[1]/1000*dW, y0=b[0]/1000*dH, x1=b[3]/1000*dW, y1=b[2]/1000*dH;
    const isCur=(x.id===cur.id);
    const col=isCur?'#38bdf8':'#64748b';      // selected = bright, others = muted
    const sw=isCur?2.5:1.5;
    const n=(x.sub_index!=null?x.sub_index:i)+1;
    const label=escSvg((x.ocr_merchant ? (n+'. '+x.ocr_merchant) : (''+n)).slice(0,22));
    const ty=Math.max(y0+13, 13);
    return '<rect x="'+x0.toFixed(1)+'" y="'+y0.toFixed(1)+'" width="'+(x1-x0).toFixed(1)+
      '" height="'+(y1-y0).toFixed(1)+'" rx="4" fill="'+col+'" fill-opacity="'+(isCur?0.12:0.05)+
      '" stroke="'+col+'" stroke-width="'+sw+'"/>'+
      '<text x="'+(x0+4).toFixed(1)+'" y="'+ty.toFixed(1)+'" fill="'+col+'" font-size="11" '+
      'font-weight="700" style="paint-order:stroke;stroke:rgba(2,6,23,.75);stroke-width:3px">'+
      label+'</text>';
  }).join('');
}
function openPanel(e){
  CUR_ID = e.id;
  CUR_FILE_ID = e.file_id || null;
  $('dDate').textContent = e.ocr_date || '–';
  $('dAmount').textContent = fmtAmtFx(e, e.ocr_amount);
  $('dPrinted').textContent = fmtAmtFx(e, e.ocr_printed_amount);
  const hand = (e.ocr_handwritten_amount===null||e.ocr_handwritten_amount===undefined);
  $('dHand').textContent = hand ? '–' : (fmtAmt(e.ocr_handwritten_amount) + ' ✍️');
  $('dHand').style.color = hand ? '' : '#f59e0b';
  $('dMerchant').textContent = e.ocr_merchant || '–';
  $('dCompanions').textContent = e.ocr_companions ? ('w/ ' + e.ocr_companions) : '–';
  $('dModel').textContent = e.ocr_model || '–';
  $('dCard').innerHTML = cardBadge(e.card_brand);
  $('dUsage').textContent = e.usage || 'Regular';
  // Pre-fill edit inputs
  $('eDate').value = e.ocr_date || '';
  $('eMerchant').value = e.ocr_merchant || '';
  $('eCompanions').value = e.ocr_companions || '';
  $('ePrinted').value = (e.ocr_printed_amount != null) ? e.ocr_printed_amount : (e.ocr_amount || '');
  $('eHand').value = (e.ocr_handwritten_amount != null) ? e.ocr_handwritten_amount : '';
  $('eCard').value = e.card_brand || 'none';
  $('eUsage').value = (e.usage && e.usage !== 'Regular') ? e.usage : '';
  // Complete toggle button reflects current state.
  var cb = $('dCompleteBtn');
  if(cb){ cb.textContent = e.completed ? '↩ Un-complete' : '✓ Mark Complete'; }
  // Reset edit mode
  exitPanelEdit();

  const img = $('dImage');
  if(e.file_id){
    let url = '/cardconv/receipts/image/' + e.file_id;
    if(Array.isArray(e.ocr_bbox) && e.ocr_bbox.length===4)
      url += '?bbox=' + e.ocr_bbox.join(',');
    img.src = url;
    img.style.display = 'block';
  } else { img.style.display='none'; }
  // SVG overlay not needed — multi-receipt images are cropped per entry
  const svg = $('dBboxOverlay');
  if(svg){ svg.innerHTML=''; svg.style.display='none'; }
  const mt = e.matched_transaction;
  $('dMatchSection').style.display = mt ? 'block' : 'none';
  if(mt){
    $('dmDate').textContent = mt.date || '–';
    $('dmAmount').textContent = fmtAmt(mt.amount);
    $('dmVendor').textContent = mt.vendor || '–';
  }
  $('dStatus').innerHTML = '<span class="status-badge status-' + (e.match_status||'unmatched') + '">' +
    (STATUS_LABEL[e.match_status]||e.match_status||'–') + '</span>';
  $('overlay').classList.add('open');
  $('panel').classList.add('open');
}

function closePanel(){
  $('overlay').classList.remove('open');
  $('panel').classList.remove('open');
  CUR_ID = null;
  CUR_FILE_ID = null;
  exitPanelEdit();
}

const PANEL_EDIT_FIELDS = ['dDate','dMerchant','dCompanions','dPrinted','dHand','dCard','dUsage'];
function exitPanelEdit(){
  PANEL_EDIT_FIELDS.forEach(function(id){
    var s = $(id); var e = $(id.replace('d','e')); if(!s||!e) return;
    s.style.display = ''; e.style.display = 'none';
  });
  var sr = $('dSaveRow'); if(sr) sr.style.display = 'none';
  var eb = $('dEditBtn'); if(eb) eb.textContent = '✏️ Edit';
}

function togglePanelEdit(){
  var editing = $('eDate').style.display !== 'none';
  if(editing){ exitPanelEdit(); return; }
  PANEL_EDIT_FIELDS.forEach(function(id){
    var s = $(id); var e = $(id.replace('d','e')); if(!s||!e) return;
    s.style.display = 'none'; e.style.display = '';
  });
  var sr = $('dSaveRow'); if(sr) sr.style.display = 'block';
  var eb = $('dEditBtn'); if(eb) eb.textContent = '✕ Cancel';
}

async function savePanelEdit(){
  if(!CUR_ID) return;
  var body = new URLSearchParams({
    ocr_date:                 $('eDate').value,
    ocr_merchant:             $('eMerchant').value,
    ocr_companions:           $('eCompanions').value.trim() || '__clear__',
    ocr_printed_amount:       $('ePrinted').value,
    ocr_handwritten_amount:   $('eHand').value,
    card_brand:               $('eCard').value,
    usage:                    $('eUsage').value,
  });
  var r = await fetch('/cardconv/ledger/' + CUR_ID + '/update', {method:'POST', body});
  var d = await r.json();
  if(!d.ok){ alert('Save failed: '+(d.error||r.status)); return; }
  exitPanelEdit();
  load();
  closePanel();
}

async function togglePanelComplete(){
  if(!CUR_ID) return;
  var e = ENTRIES.find(x => x.id === CUR_ID) || {};
  var undo = !!e.completed;
  if(!undo && !confirm('Mark this receipt complete?\n(It leaves the default list, Sync and Mapping; the Drive original moves to the Completed folder)')) return;
  var r = await fetch('/cardconv/ledger/complete', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ids:[CUR_ID], undo: undo})
  });
  var d = await r.json().catch(() => ({}));
  if(!d.ok){ alert('Failed: '+(d && d.error||r.status)); return; }
  toast(undo ? 'Marked incomplete' : 'Marked complete', false);
  if(d.attempted && d.moved < d.attempted){
    toast('Drive file move did not apply. Settlement data was saved correctly.', true);
  }
  closePanel();
  load();
}

async function setStatus(status){
  if(!CUR_ID) return;
  await fetch('/cardconv/ledger/' + CUR_ID + '/status', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({status: status})
  });
  closePanel();
  load();
}

async function reOCR(){
  if(!CUR_ID) return;
  const btn = $('reOcrBtn');
  btn.disabled = true;
  btn.textContent = 'Processing...';
  try {
    const r = await fetch('/cardconv/ledger/' + CUR_ID + '/reocr', {method:'POST'});
    const d = await r.json();
    if(!r.ok || d.error){
      alert('Re-OCR failed: ' + (d.error || r.status));
      return;
    }
    // Update ENTRIES with the returned updated entries
    if(Array.isArray(d.updated)){
      d.updated.forEach(function(u){
        const idx = ENTRIES.findIndex(function(e){ return e.id === u.id; });
        if(idx >= 0) ENTRIES[idx] = u; else ENTRIES.push(u);
      });
      // Remove entries that were replaced (different sub_index count)
      const updIds = new Set(d.updated.map(function(u){ return u.id; }));
      const updFid = d.updated[0] && d.updated[0].file_id;
      if(updFid){
        ENTRIES = ENTRIES.filter(function(e){ return e.file_id !== updFid || updIds.has(e.id); });
      }
    }
    closePanel();
    load();
  } finally {
    btn.disabled = false;
    btn.textContent = '🔄 Re-OCR';
  }
}

// Quick Re-OCR from table row button (no panel needed).
async function quickReOCR(id, btn){
  if(!id) return;
  btn.disabled = true; btn.textContent = '⏳';
  try {
    const r = await fetch('/cardconv/ledger/' + id + '/reocr', {method:'POST'});
    const d = await r.json();
    if(!r.ok || d.error){ btn.textContent = '❌'; setTimeout(()=>{ btn.disabled=false; btn.textContent='🔄 Re-run'; }, 2000); return; }
    if(Array.isArray(d.updated)){
      d.updated.forEach(u => { const idx = ENTRIES.findIndex(e => e.id===u.id); if(idx>=0) ENTRIES[idx]=u; else ENTRIES.push(u); });
    }
    load();
  } catch(e) { btn.disabled=false; btn.textContent='🔄 Re-run'; }
}

// Re-try CSV matching for a pending/unmatched row.
async function quickRematch(id, btn){
  if(!id) return;
  btn.disabled = true; btn.textContent = '⏳';
  try {
    const r = await fetch('/cardconv/ledger/' + id + '/rematch', {method:'POST'});
    const d = await r.json();
    if(!r.ok || d.error){ btn.textContent = '❌'; setTimeout(()=>{ btn.disabled=false; btn.textContent='🔗 Rematch'; }, 2000); return; }
    if(d.matched){
      btn.textContent = '✅';
      setTimeout(()=>{ btn.disabled=false; btn.textContent='🔗 Rematch'; }, 1500);
    } else {
      btn.textContent = '❌ No match';
      setTimeout(()=>{ btn.disabled=false; btn.textContent='🔗 Rematch'; }, 2000);
    }
    load();
  } catch(e) { btn.disabled=false; btn.textContent='🔗 Rematch'; }
}

// Undo Match from the ledger table — reset row to pending_match.
async function unmatchRow(id){
  if(!id) return;
  await fetch('/cardconv/ledger/' + id + '/status', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({status: 'pending_match'})
  });
  load();
}

function selectedIds(){
  return [...document.querySelectorAll('.sel:checked')].map(c => c.dataset.id);
}

function updateDeleteBtn(){
  const ids = selectedIds();
  const n = ids.length;
  $('fDelete').textContent = '🗑 Delete (' + n + ')';
  $('fDelete').disabled = n === 0;
  // Split selection into active vs already-completed to drive the two buttons.
  const sel = new Set(ids);
  let active = 0, done = 0;
  ENTRIES.forEach(e => { if(sel.has(e.id)){ e.completed ? done++ : active++; } });
  $('fComplete').textContent = '✓ Complete (' + active + ')';
  $('fComplete').disabled = active === 0;
  $('fUncomplete').textContent = '↩ Un-complete (' + done + ')';
  $('fUncomplete').disabled = done === 0;
  const sb = $('fSelBar'); if(sb) sb.classList.toggle('show', n > 0);
  const sc = $('fSelCount'); if(sc) sc.textContent = n + ' selected';
}

async function completeSelected(undo){
  const sel = new Set(selectedIds());
  // Only act on entries in the relevant state (active→complete, done→un-complete).
  const ids = ENTRIES.filter(e => sel.has(e.id) && (undo ? e.completed : !e.completed))
                     .map(e => e.id);
  if(!ids.length) return;
  const verb = undo ? 'incomplete' : 'complete';
  if(!confirm('Mark ' + ids.length + ' receipts ' + verb + '?' +
      (undo ? '' : '\n(Completed receipts leave the default list, Sync and Mapping; Drive originals move to the Completed folder)'))) return;
  const r = await fetch('/cardconv/ledger/complete', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ids: ids, undo: !!undo})
  });
  const d = await r.json().catch(() => ({}));
  if(!d.ok){ alert('Failed: ' + (d.error || r.status)); load(); return; }
  toast(ids.length + ' receipts marked ' + verb, false);
  // Warn when some Drive originals couldn't be moved (e.g. Drive offline);
  // the ledger flag is already set so exclusion from Sync/Mapping still holds.
  if(d.attempted && d.moved < d.attempted){
    toast('Some Drive file moves did not apply. Settlement data was saved correctly.', true);
  }
  load();
}

function deleteSelected(){
  const ids = selectedIds();
  if(!ids.length) return;
  $('delBody').textContent = 'Delete ' + ids.length + ' checked receipts from the Ledger?';
  $('delDrive').checked = false;
  $('delOverlay').classList.add('open');
  $('delModal').classList.add('open');
}

function closeDelModal(){
  $('delOverlay').classList.remove('open');
  $('delModal').classList.remove('open');
}

async function confirmDelete(){
  const ids = selectedIds();
  const alsoDrive = $('delDrive').checked;
  closeDelModal();
  if(!ids.length) return;
  await fetch('/cardconv/ledger/delete', {
    method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ids: ids, also_drive: alsoDrive})
  });
  load();
}

function iso(d){ return d.toISOString().slice(0,10); }

function applyPreset(p){
  const now = new Date();
  let from = '', to = iso(now);
  if(p==='month')    from = iso(new Date(now.getFullYear(), now.getMonth(), 1));
  else if(p==='30d') from = iso(new Date(now.getTime() - 29*86400000));
  else if(p==='3m')  from = iso(new Date(now.getFullYear(), now.getMonth()-3, now.getDate()));
  else if(p==='ytd') from = iso(new Date(now.getFullYear(), 0, 1));
  else if(p==='all'){ from = ''; to = ''; }
  $('fFrom').value = from;
  $('fTo').value = to;
  load();
}

function setDefaultDates(){
  // Default: All Time (no date filter)
  $('fFrom').value = '';
  $('fTo').value = '';
}

document.querySelectorAll('.detail-actions button[data-set]').forEach(b =>
  b.addEventListener('click', () => setStatus(b.dataset.set)));
$('panelClose').addEventListener('click', closePanel);
$('overlay').addEventListener('click', closePanel);
document.addEventListener('keydown', e => { if(e.key==='Escape') closePanel(); });
$('fFrom').addEventListener('change', load);
$('fTo').addEventListener('change', load);
$('fStatus').addEventListener('change', load);
$('fCard').addEventListener('change', load);
$('fUsage').addEventListener('change', load);
$('fCompleted').addEventListener('change', load);
$('fSettle').addEventListener('change', load);
$('fSort').addEventListener('change', load);

// Stat cards double as one-click views (Review-style switching).
const STAT_VIEWS = {
  total:       {status:'all',           settle:'all',         completed:'hide'},
  matched:     {status:'matched',       settle:'all',         completed:'hide'},
  unmatched:   {status:'unmatched_any', settle:'all',         completed:'hide'},
  in_progress: {status:'all',           settle:'in_progress', completed:'hide'},
  completed:   {status:'all',           settle:'all',         completed:'only'},
};
document.querySelectorAll('.stat-click').forEach(card => card.addEventListener('click', () => {
  const v = STAT_VIEWS[card.dataset.statview];
  $('fStatus').value = v.status;
  $('fSettle').value = v.settle;
  $('fCompleted').value = v.completed;
  document.querySelectorAll('.stat-click').forEach(c => c.classList.toggle('active', c === card));
  load();
}));
let _mDeb;
$('fMerchant').addEventListener('input', () => { clearTimeout(_mDeb); _mDeb = setTimeout(load, 300); });
$('fMore').addEventListener('click', () => {
  const adv = $('fAdvanced'), open = adv.classList.toggle('open');
  $('fMore').classList.toggle('open', open);
  $('fMore').setAttribute('aria-expanded', open);
});
$('fReset').addEventListener('click', () => {
  $('fStatus').value='all'; $('fCard').value='all'; $('fUsage').value='all';
  $('fCompleted').value='hide'; $('fSettle').value='all';
  $('fMerchant').value=''; setSort('date');
  $('fPeriod').value='all'; $('fCustomRange').hidden = true;
  document.querySelectorAll('.stat-click').forEach(c => c.classList.remove('active'));
  setDefaultDates(); load();
});
// Both downloads respect the currently applied filters.
$('fDownload').addEventListener('click', () => {
  closePops();
  window.location = '/cardconv/ledger/download.pdf?' + filterParams().toString();
});
$('fDownloadXlsx').addEventListener('click', () => {
  closePops();
  window.location = '/cardconv/ledger/download.xlsx?' + filterParams().toString();
});
$('fDelete').addEventListener('click', deleteSelected);
$('fComplete').addEventListener('click', () => completeSelected(false));
$('fUncomplete').addEventListener('click', () => completeSelected(true));
$('checkAll').addEventListener('change', () => {
  document.querySelectorAll('.sel').forEach(c => { c.checked = $('checkAll').checked; });
  updateDeleteBtn();
});

// Bulk edits on the current selection — one action per call.
async function bulkApply(action, value){
  const ids = selectedIds();
  if(!ids.length) return;
  const r = await fetch('/cardconv/ledger/bulk', {
    method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({ids: ids, action: action, value: value})
  });
  const d = await r.json().catch(() => ({}));
  if(!d.ok){ toast('Bulk update failed', true); return; }
  if(action === 'rematch') toast(d.matched + ' of ' + ids.length + ' selected matched' + (d.matched ? '' : ' — no CSV transaction fits'), !d.matched);
  else toast('Updated ' + d.updated + ' receipts');
  load();
}
$('fBulkCard').addEventListener('change', () => {
  const v = $('fBulkCard').value;
  $('fBulkCard').value = '';
  if(v !== '') bulkApply('card', v);
});
$('fBulkUsage').addEventListener('change', () => {
  let v = $('fBulkUsage').value;
  $('fBulkUsage').value = '';
  if(v === '') return;
  if(v === '__new__'){ v = (prompt('New usage tag:') || '').trim(); if(!v) return; }
  bulkApply('usage', v);
});
$('fBulkWith').addEventListener('click', () => {
  const v = prompt('Companions (w/) — leave blank and press OK to clear:');
  if(v === null) return;
  bulkApply('companions', v.trim());
});
$('fBulkRematch').addEventListener('click', () => bulkApply('rematch', null));
// Period select drives the date range; Custom… reveals the two date inputs.
$('fPeriod').addEventListener('change', () => {
  const v = $('fPeriod').value;
  $('fCustomRange').hidden = (v !== 'custom');
  if(v === 'custom') return;  // wait for the date inputs to change
  applyPreset(v);
});

// Sort lives in the column headers (hidden fSort select keeps filterParams intact).
function setSort(key){
  $('fSort').value = key;
  $('thDate').classList.toggle('on', key === 'date');
  $('thMerchant').classList.toggle('on', key === 'merchant');
}
$('thDate').addEventListener('click', () => { setSort('date'); load(); });
$('thMerchant').addEventListener('click', () => { setSort('merchant'); load(); });

// Export dropdown.
$('fExport').addEventListener('click', () => {
  const open = $('fExportMenu').classList.toggle('open');
  $('fExport').classList.toggle('open', open);
  $('fExport').setAttribute('aria-expanded', open);
});

// Click outside / Escape closes both popovers.
function closePops(){
  [['fMore','fAdvanced'],['fExport','fExportMenu']].forEach(([b,p]) => {
    $(p).classList.remove('open'); $(b).classList.remove('open');
    $(b).setAttribute('aria-expanded','false');
  });
}
document.addEventListener('click', e => {
  [['fMore','fAdvanced'],['fExport','fExportMenu']].forEach(([b,p]) => {
    if(!$(p).classList.contains('open')) return;
    if($(p).contains(e.target) || $(b).contains(e.target)) return;
    $(p).classList.remove('open'); $(b).classList.remove('open');
    $(b).setAttribute('aria-expanded','false');
  });
});
document.addEventListener('keydown', e => { if(e.key === 'Escape') closePops(); });

// Active-filter chips: non-default filters stay visible with one-click removal.
function clearStatRing(){ document.querySelectorAll('.stat-click').forEach(c => c.classList.remove('active')); }
function updateChips(){
  const optText = id => { const s = $(id); return s.options[s.selectedIndex] ? s.options[s.selectedIndex].text : s.value; };
  const chips = [];
  if($('fPeriod').value !== 'all'){
    const lbl = $('fPeriod').value === 'custom'
      ? (($('fFrom').value || '…') + ' ~ ' + ($('fTo').value || '…')) : optText('fPeriod');
    chips.push({label:'📅 ' + lbl, clear: () => { $('fPeriod').value='all'; $('fCustomRange').hidden=true; applyPreset('all'); }});
  }
  if($('fStatus').value !== 'all')
    chips.push({label: optText('fStatus'), clear: () => { $('fStatus').value='all'; clearStatRing(); load(); }});
  if($('fCard').value !== 'all')
    chips.push({label:'Card: ' + optText('fCard'), clear: () => { $('fCard').value='all'; load(); }});
  if($('fUsage').value !== 'all')
    chips.push({label:'Usage: ' + $('fUsage').value, clear: () => { $('fUsage').value='all'; load(); }});
  if($('fCompleted').value !== 'hide')
    chips.push({label:'Show: ' + optText('fCompleted'), clear: () => { $('fCompleted').value='hide'; clearStatRing(); load(); }});
  if($('fSettle').value !== 'all')
    chips.push({label:'Settle: ' + optText('fSettle'), clear: () => { $('fSettle').value='all'; clearStatRing(); load(); }});

  const advCount = ['fStatus','fCard','fUsage','fSettle'].filter(id => $(id).value !== 'all').length
                 + ($('fCompleted').value !== 'hide' ? 1 : 0);
  $('fBadge').hidden = advCount === 0;
  $('fBadge').textContent = advCount;

  const bar = $('fChips');
  bar.innerHTML = '';
  if(!chips.length){ bar.hidden = true; return; }
  bar.hidden = false;
  chips.forEach(c => {
    const el = document.createElement('span');
    el.className = 'fb-chip';
    el.appendChild(document.createTextNode(c.label + ' '));
    const x = document.createElement('i'); x.textContent = '×'; x.title = 'Remove filter';
    x.addEventListener('click', c.clear);
    el.appendChild(x);
    bar.appendChild(el);
  });
  const r = document.createElement('button');
  r.className = 'fb-chip-reset'; r.textContent = 'Reset all';
  r.addEventListener('click', () => $('fReset').click());
  bar.appendChild(r);
}

// Group Duplicates toggle — re-renders the current page without refetching.
$('viewToggle').addEventListener('click', () => {
  VIEW_MODE = (VIEW_MODE === 'all') ? 'group' : 'all';
  $('viewToggle').textContent = (VIEW_MODE === 'all') ? '🔁 Group Duplicates' : '☰ Show All';
  $('viewToggle').classList.toggle('active', VIEW_MODE === 'group');
  rerender();
});

// Manual receipt add modal.
let _MANUAL_FILE_ID = null, _MANUAL_META = {};
function openManualAdd(){
  if(!CUR_FILE_ID) return;
  _MANUAL_FILE_ID = CUR_FILE_ID;
  const cur = ENTRIES.find(e => e.id === CUR_ID) || {};
  _MANUAL_META = { filename: cur.filename||'', drive_url: cur.drive_url||'', mime_type: cur.mime_type||'image/jpeg' };
  $('mDate').value = ''; $('mMerchant').value = ''; $('mPrinted').value = ''; $('mHandw').value = '';
  $('manualOverlay').classList.add('open');
  $('manualModal').classList.add('open');
}
function closeManualAdd(){
  $('manualOverlay').classList.remove('open');
  $('manualModal').classList.remove('open');
}
async function submitManualAdd(){
  if(!_MANUAL_FILE_ID) return;
  const btn = $('manualAddConfirm');
  btn.disabled = true; btn.textContent = 'Adding…';
  const body = new URLSearchParams({
    file_id:               _MANUAL_FILE_ID,
    filename:              _MANUAL_META.filename,
    drive_url:             _MANUAL_META.drive_url,
    mime_type:             _MANUAL_META.mime_type,
    ocr_date:              $('mDate').value,
    ocr_merchant:          $('mMerchant').value,
    ocr_printed_amount:    $('mPrinted').value,
    ocr_handwritten_amount: $('mHandw').value,
  });
  try {
    const r = await fetch('/cardconv/receipts/manual-add', {method:'POST', body});
    const d = await r.json();
    if(!d.ok){ alert('Add failed: ' + (d.error||r.status)); return; }
    closeManualAdd();
    closePanel();
    load();
  } catch(e){ alert('Error: '+e); }
  finally { btn.disabled=false; btn.textContent='Add'; }
}
$('manualOverlay').addEventListener('click', closeManualAdd);

// Delete confirmation modal (with optional Drive trashing).
$('delCancel').addEventListener('click', closeDelModal);
$('delOverlay').addEventListener('click', closeDelModal);
$('delConfirm').addEventListener('click', confirmDelete);

setDefaultDates();
load();
</script>
<script>__RCPTJS__</script>
<script>
(function(){
  const VAPID_PUB = '__VAPID_PUB__';
  if(!VAPID_PUB || !('serviceWorker' in navigator) || !('PushManager' in window)) return;
  function urlB64ToUint8Array(b64){
    const pad = '='.repeat((4 - b64.length%4)%4);
    const raw = atob((b64+pad).replace(/-/g,'+').replace(/_/g,'/'));
    return Uint8Array.from(raw, c => c.charCodeAt(0));
  }
  navigator.serviceWorker.ready.then(function(reg){
    reg.pushManager.getSubscription().then(function(existing){
      if(existing) return;  // already subscribed
      if(Notification.permission === 'denied') return;
      return reg.pushManager.subscribe({
        userVisibleOnly: true,
        applicationServerKey: urlB64ToUint8Array(VAPID_PUB)
      }).then(function(sub){
        return fetch('/cardconv/push/subscribe', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify(sub.toJSON())
        });
      });
    });
  });
})();
</script>

<!-- Sync Loading Overlay -->
<div id="syncOverlay" style="display:none;position:fixed;inset:0;background:rgba(2,6,23,.82);z-index:500;flex-direction:column;align-items:center;justify-content:center;gap:20px">
  <style>
  @keyframes spin{to{transform:rotate(360deg)}}
  @keyframes pulse{0%,100%{opacity:.6}50%{opacity:1}}
  .sync-spinner{width:52px;height:52px;border:4px solid rgba(56,189,248,.2);border-top-color:#38bdf8;border-radius:50%;animation:spin .9s linear infinite}
  .sync-dots span{display:inline-block;width:6px;height:6px;border-radius:50%;background:#38bdf8;margin:0 3px;animation:pulse 1.2s ease-in-out infinite}
  .sync-dots span:nth-child(2){animation-delay:.2s}
  .sync-dots span:nth-child(3){animation-delay:.4s}
  </style>
  <div class="sync-spinner"></div>
  <div style="color:#e2e8f0;font-size:1rem;font-weight:600;letter-spacing:.02em">Syncing from Drive…</div>
  <div style="color:#94a3b8;font-size:.82rem">Powered by Google Gemini — OCR is running, this may take a moment ✨</div>
  <div class="sync-dots"><span></span><span></span><span></span></div>
</div>
<script>
function startDriveSync(btn) {
  btn.disabled = true;
  document.getElementById('syncOverlay').style.display = 'flex';
  fetch('/cardconv/drive/sync', {method: 'POST'})
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (d.error) { syncFail(d.error); return; }
      pollSync(d.job_id);
    })
    .catch(function(e) { syncFail(String(e)); });
}

function pollSync(jobId) {
  setTimeout(function() {
    fetch('/cardconv/drive/sync/status?job=' + jobId)
      .then(function(r) { return r.json(); })
      .then(function(d) {
        if (d.status === 'running') { pollSync(jobId); return; }
        document.getElementById('syncOverlay').style.display = 'none';
        if (d.status === 'error') { alert('Sync error: ' + (d.error || 'unknown')); load(); return; }
        // done — pending files are now staged, banner no longer applies
        var nb = document.getElementById('driveNewBanner');
        if (nb) nb.style.display = 'none';
        if (d.staged > 0) {
          openOcrModal();
        } else {
          load();
        }
      })
      .catch(function() { pollSync(jobId); });  // retry on network hiccup
  }, 2500);
}

function syncFail(msg) {
  document.getElementById('syncOverlay').style.display = 'none';
  alert('Sync failed: ' + msg);
}

// New-receipts banner: cheap Drive listing on page load (count only, no OCR).
(function() {
  var banner = document.getElementById('driveNewBanner');
  if (!banner) return;
  fetch('/cardconv/drive/newcount')
    .then(function(r) { return r.json(); })
    .then(function(d) {
      if (!d.connected || !d.new) return;
      document.getElementById('driveNewCount').textContent = d.new;
      banner.style.display = 'flex';
    })
    .catch(function() {});
})();
</script>

<!-- Image Lightbox -->
<div id="imgLb" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.92);z-index:300;align-items:center;justify-content:center;cursor:zoom-out" onclick="closeImgLb()">
  <img id="imgLbImg" style="max-width:95vw;max-height:95vh;object-fit:contain;border-radius:4px;box-shadow:0 0 40px rgba(0,0,0,.8)" alt="receipt">
  <button onclick="closeImgLb()" style="position:fixed;top:16px;right:20px;background:rgba(255,255,255,.15);border:none;color:#fff;font-size:1.6rem;line-height:1;width:36px;height:36px;border-radius:50%;cursor:pointer">&times;</button>
</div>
<script>
function openImgLb(fid){
  var fileId = fid || CUR_FILE_ID;
  if(!fileId) return;
  var url = '/cardconv/receipts/image/' + fileId;
  var lb = document.getElementById('imgLb');
  var img = document.getElementById('imgLbImg');
  img.src = url;
  lb.style.display = 'flex';
  document.addEventListener('keydown', _imgLbKey);
}
function closeImgLb(){
  var lb = document.getElementById('imgLb');
  lb.style.display = 'none';
  document.getElementById('imgLbImg').src = '';
  document.removeEventListener('keydown', _imgLbKey);
}
function _imgLbKey(e){ if(e.key==='Escape') closeImgLb(); }
</script>

<!-- OCR Review Modal -->
<div id="ocrReviewOverlay" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,.65);z-index:200;align-items:flex-start;justify-content:center;overflow-y:auto;padding:30px 16px">
  <div style="background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-md);width:100%;max-width:860px;margin:auto;display:flex;flex-direction:column">
    <div style="display:flex;align-items:center;justify-content:space-between;padding:18px 20px;border-bottom:1px solid var(--border)">
      <div>
        <div style="font-size:1.1rem;font-weight:700">OCR Review</div>
        <div id="ocrReviewCount" style="font-size:.82rem;color:var(--text-muted);margin-top:2px"></div>
      </div>
      <div style="display:flex;gap:8px;align-items:center">
        <button onclick="ocrToggleAll(true)" class="btn btn-secondary" style="font-size:.78rem;padding:5px 12px">Check All</button>
        <button onclick="ocrToggleAll(false)" class="btn btn-secondary" style="font-size:.78rem;padding:5px 12px">Uncheck All</button>
        <button onclick="closeOcrModal()" style="background:none;border:none;color:var(--text-muted);font-size:1.4rem;cursor:pointer;line-height:1">&#x2715;</button>
      </div>
    </div>
    <div id="ocrReviewBody" style="padding:16px;display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;max-height:70vh;overflow-y:auto">
      <div style="grid-column:1/-1;text-align:center;color:var(--text-muted);padding:40px">Loading...</div>
    </div>
    <div style="display:flex;justify-content:flex-end;gap:10px;padding:14px 20px;border-top:1px solid var(--border);flex-wrap:wrap">
      <button onclick="ocrDiscardAll()" class="btn btn-danger" style="font-size:.84rem">Discard All</button>
      <button onclick="ocrConfirmSelected()" class="btn btn-primary" style="font-size:.84rem">&#10003; Confirm Selected &rarr; Add to Ledger</button>
    </div>
  </div>
</div>

<script>
(function() {
  var overlay = document.getElementById('ocrReviewOverlay');
  var body    = document.getElementById('ocrReviewBody');
  var countEl = document.getElementById('ocrReviewCount');
  var _entries = [];

  function money(v) {
    return (v == null) ? '–' : ('$' + parseFloat(v).toFixed(2));
  }

  var INPUT_STYLE = 'width:100%;box-sizing:border-box;background:var(--surface);border:1px solid var(--border);border-radius:4px;color:var(--text);font-size:.8rem;padding:3px 6px;outline:none';
  var LABEL_STYLE = 'font-size:.72rem;color:var(--text-muted);display:block;margin-bottom:2px';

  function renderEntries(entries) {
    _entries = entries;
    countEl.textContent = entries.length + ' receipt(s) — verify and edit before adding to ledger';
    if (!entries.length) {
      body.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--text-muted);padding:40px">No pending entries.</div>';
      return;
    }
    body.innerHTML = entries.map(function(e) {
      var proxy = e.file_id ? '/cardconv/receipts/image/' + encodeURIComponent(e.file_id) : '';
      var fid = e.file_id || '';
      var imgHtml = proxy
        ? '<img src="' + proxy + '" style="width:100%;max-height:200px;object-fit:contain;display:block;background:#000;cursor:zoom-in" loading="lazy" onclick="event.stopPropagation();openImgLb(\'' + fid + '\')" title="Click to enlarge">'
        : '<div style="height:120px;display:flex;align-items:center;justify-content:center;color:var(--text-muted);font-size:.8rem">No image</div>';
      var ocrOk = e.ocr_status === 'done' && e.ocr_merchant;
      var badge = ocrOk
        ? '<span style="font-size:.62rem;font-weight:700;padding:2px 6px;border-radius:8px;background:rgba(34,197,94,.15);color:#22c55e">OCR OK</span>'
        : '<span style="font-size:.62rem;font-weight:700;padding:2px 6px;border-radius:8px;background:rgba(245,158,11,.15);color:#f59e0b">Partial</span>';
      var eid = e.id;
      var amtVal = (e.ocr_amount != null) ? e.ocr_amount : '';
      var hwVal  = (e.ocr_handwritten_amount != null) ? e.ocr_handwritten_amount : '';
      var cur = e.ocr_currency;
      var isFx = cur && cur !== 'USD';
      var curLabel = isFx ? cur : '$';
      var curChip = isFx
        ? '<span style="font-size:.62rem;font-weight:700;padding:2px 6px;border-radius:8px;background:rgba(59,130,246,.15);color:#3b82f6">' + cur + '</span>'
        : '';
      var fxRow = '';
      if (isFx && e.ocr_amount != null) {
        var rateTxt = (e.fx_rate != null)
          ? ' <span style="color:var(--text-muted);font-weight:400">(1 USD ≈ ' + (FX_SYM[cur] || '') + Number(e.fx_rate).toLocaleString(undefined, {maximumFractionDigits: 2}) + ')</span>'
          : ' <span style="color:var(--text-muted);font-weight:400">FX rate lookup failed</span>';
        fxRow = '<div style="font-size:.76rem;padding:5px 8px;border-radius:4px;'
          + 'background:rgba(245,158,11,.12);color:#f59e0b;font-weight:600">💱 '
          + fmtAmtFx(e, e.ocr_amount) + rateTxt + '</div>';
      }
      return '<div class="ocr-card" data-id="' + eid + '" style="border:1px solid var(--border);border-radius:var(--radius-md);overflow:hidden;background:var(--surface-2)">'
        + '<label style="display:flex;align-items:center;gap:8px;padding:8px 10px;border-bottom:1px solid var(--border);cursor:pointer;background:var(--surface)">'
        + '<input type="checkbox" class="ocr-cb" data-id="' + eid + '" ' + (ocrOk ? 'checked' : '') + ' style="width:15px;height:15px;accent-color:var(--accent);cursor:pointer">'
        + '<span style="font-size:.8rem;font-weight:600">Include</span>' + badge + curChip
        + '</label>'
        + '<div style="background:#000;display:flex;align-items:center;justify-content:center;min-height:120px">' + imgHtml + '</div>'
        + '<div style="padding:10px;display:flex;flex-direction:column;gap:7px">'
        + '<div style="color:var(--text-muted);font-size:.7rem;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">' + (e.filename || '') + '</div>'
        + '<div><label style="' + LABEL_STYLE + '">Date</label>'
        +   '<input class="ocr-field" data-field="ocr_date" data-id="' + eid + '" type="date" value="' + (e.ocr_date || '') + '" style="' + INPUT_STYLE + '"></div>'
        + '<div><label style="' + LABEL_STYLE + '">Merchant</label>'
        +   '<input class="ocr-field" data-field="ocr_merchant" data-id="' + eid + '" type="text" value="' + ((e.ocr_merchant || '')).replace(/"/g,'&quot;') + '" placeholder="–" style="' + INPUT_STYLE + '"></div>'
        + '<div style="display:grid;grid-template-columns:1fr 1fr;gap:6px">'
        +   '<div><label style="' + LABEL_STYLE + '">Printed ' + curLabel + '</label>'
        +     '<input class="ocr-field" data-field="ocr_amount" data-id="' + eid + '" type="number" step="0.01" value="' + amtVal + '" placeholder="–" style="' + INPUT_STYLE + '"></div>'
        +   '<div><label style="' + LABEL_STYLE + '">Handwritten ' + curLabel + '</label>'
        +     '<input class="ocr-field" data-field="ocr_handwritten_amount" data-id="' + eid + '" type="number" step="0.01" value="' + hwVal + '" placeholder="–" style="' + INPUT_STYLE + '"></div>'
        + '</div>'
        + fxRow
        + '</div></div>';
    }).join('');
  }

  window.openOcrModal = function() {
    overlay.style.display = 'flex';
    fetch('/cardconv/receipts/review/api')
      .then(function(r) { return r.json(); })
      .then(function(d) { renderEntries(d.entries || []); })
      .catch(function() { body.innerHTML = '<div style="grid-column:1/-1;text-align:center;color:var(--danger);padding:40px">Failed to load.</div>'; });
  };
  var openOcrModal = window.openOcrModal;

  window.closeOcrModal = function() { overlay.style.display = 'none'; };

  window.ocrToggleAll = function(on) {
    document.querySelectorAll('.ocr-cb').forEach(function(cb) { cb.checked = on; });
  };

  function clearOcrBadge() {
    var badge = document.querySelector('a[href="/cardconv/ledger"] .tab-badge[style*="f59e0b"]');
    if (badge) badge.remove();
  }

  window.ocrDiscardAll = function() {
    if (!confirm('Discard all staged entries?')) return;
    fetch('/cardconv/receipts/review/discard', {method:'POST'})
      .then(function() { closeOcrModal(); clearOcrBadge(); });
  };

  window.ocrConfirmSelected = function() {
    var checkedIds = new Set(
      Array.from(document.querySelectorAll('.ocr-cb:checked')).map(function(cb) { return cb.dataset.id; })
    );
    // Collect per-card field values for checked cards only.
    var confirmed = Array.from(document.querySelectorAll('.ocr-card')).reduce(function(acc, card) {
      var id = card.dataset.id;
      if (!checkedIds.has(id)) return acc;
      var item = {id: id};
      card.querySelectorAll('.ocr-field').forEach(function(inp) {
        item[inp.dataset.field] = inp.value;
      });
      acc.push(item);
      return acc;
    }, []);
    fetch('/cardconv/receipts/review/confirm', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({confirmed: confirmed})
    }).then(function() { closeOcrModal(); clearOcrBadge(); load(); });
  };

  overlay.addEventListener('click', function(e) { if (e.target === overlay) closeOcrModal(); });

  // Auto-open if redirected with ?ocr_review=1
  if (new URLSearchParams(location.search).get('ocr_review') === '1') {
    history.replaceState({}, '', location.pathname);
    openOcrModal();
  }

})();
</script>
</body></html>'''


# Auto re-export every module-level name (incl _underscore) for `import *`.
__all__ = [k for k in list(globals()) if not k.startswith('__')]
