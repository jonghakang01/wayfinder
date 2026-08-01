"""Design System — the living UX/UI reference for every Wayfinder app.

Standard (2026-07-13): all Wayfinder solutions follow the AMEX Expense
Assistant (cardconv) UX/UI. When a new pattern is needed, update THIS design
system first, then apply it everywhere. Tokens live in server.py STYLE; the
component demos below mirror cardconv's reference implementation.
"""

META = {
    "name": "Design System",
    "path": "/design",
    "icon": "🎨",
    "description": "Wayfinder UX/UI 표준 — 토큰·컴포넌트·패턴 레퍼런스",
    "admin_only": True,
}

COLOR_TOKENS = [
    ("--bg-deep", "Page / deep background"),
    ("--surface", "Card / panel surface"),
    ("--border", "Default border"),
    ("--border-bright", "Emphasized border, input focus"),
    ("--text", "Body text"),
    ("--text-muted", "Secondary text, captions"),
    ("--text-dim", "Tertiary text, disabled"),
    ("--accent", "Point color — buttons, links, active tab, badge ONLY"),
    ("--on-accent", "Text on accent background"),
    ("--success", "Positive state"),
    ("--warn", "Warning / in-progress state"),
    ("--danger", "Error / unmatched state"),
    ("--info", "Informational state"),
    ("--group-1", "Category / group accent 1 — sky"),
    ("--group-2", "Category / group accent 2 — indigo"),
    ("--group-3", "Category / group accent 3 — green"),
    ("--group-4", "Category / group accent 4 — orange (Deal Desk vendor side)"),
    ("--group-5", "Category / group accent 5 — pink"),
]

DEMO_CSS = """
.ds-wrap{max-width:1100px;margin:0 auto;padding:24px 20px 80px}
.ds-wrap h1{font-size:1.4rem;font-weight:var(--fw-extrabold);letter-spacing:-.02em}
.ds-sub{color:var(--text-muted);font-size:var(--text-sm);margin:6px 0 26px}
.ds-sect{margin-top:38px}
.ds-sect>h2{font-size:var(--text-md);font-weight:var(--fw-bold);color:var(--accent);
  border-bottom:1px solid var(--border);padding-bottom:8px;margin-bottom:14px}
.ds-sect h3{font-size:var(--text-base);font-weight:var(--fw-bold);margin:20px 0 8px}
.ds-sect p{font-size:var(--text-sm);color:var(--text-muted);max-width:76ch;line-height:1.65;margin:0 0 10px}
.ds-sect p b, .ds-rules li b{color:var(--text)}
.ds-code{background:var(--bg-deep);border:1px solid var(--border);border-radius:var(--radius-md);
  padding:12px 14px;font-size:var(--text-xs);color:var(--text);overflow-x:auto;line-height:1.7;
  font-family:ui-monospace,SFMono-Regular,Menlo,monospace;margin:0 0 10px}
.ds-rules{font-size:var(--text-sm);line-height:1.7;padding-left:20px;color:var(--text-muted)}
.ds-rules li{margin-bottom:6px}
code{background:var(--bg-deep);border:1px solid var(--border);border-radius:5px;
  padding:1px 6px;font-size:.85em}
/* token swatches */
.tok-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(230px,1fr));gap:10px}
.tok{display:flex;align-items:center;gap:12px;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-md);padding:10px 12px}
.tok .sw{width:44px;height:44px;border-radius:var(--radius-sm);border:1px solid var(--border-bright);flex-shrink:0}
.tok .nm{font-size:var(--text-sm);font-weight:var(--fw-semibold)}
.tok .ds{font-size:var(--text-xs);color:var(--text-muted)}
/* pill tabs (cardconv .cc-tab) */
.ds-tabs{display:inline-flex;gap:4px;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-full);padding:4px}
.ds-tab{padding:7px 16px;border-radius:var(--radius-full);font-size:var(--text-sm);
  font-weight:var(--fw-semibold);color:var(--text-muted);cursor:pointer;border:0;background:none}
.ds-tab.active{background:var(--accent);color:var(--on-accent)}
/* stat cards */
.ds-stats{display:grid;grid-template-columns:repeat(auto-fit,minmax(130px,1fr));gap:10px}
.ds-stat{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);
  padding:14px;text-align:center;cursor:pointer}
.ds-stat.active{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.ds-stat .n{font-size:1.5rem;font-weight:var(--fw-extrabold)}
.ds-stat .l{font-size:var(--text-xs);font-weight:var(--fw-bold);letter-spacing:.06em;
  text-transform:uppercase;color:var(--text-muted);margin-top:2px}
.ds-stat.ok .n{color:var(--success)} .ds-stat.bad .n{color:var(--danger)} .ds-stat.warn .n{color:var(--warn)}
/* toolbar */
.ds-toolbar{display:flex;align-items:center;gap:10px;flex-wrap:wrap;background:var(--surface);
  border:1px solid var(--border);border-radius:var(--radius-lg);padding:10px 14px}
.ds-toolbar label{font-size:var(--text-xs);font-weight:var(--fw-bold);letter-spacing:.05em;
  text-transform:uppercase;color:var(--text-muted)}
.ds-toolbar select,.ds-toolbar input{background:var(--bg-deep);border:1px solid var(--border);
  border-radius:var(--radius-md);color:var(--text);padding:7px 10px;font-size:var(--text-sm)}
.ds-toolbar input{flex:1;min-width:140px}
.ds-btn{background:var(--surface);border:1px solid var(--border-bright);border-radius:var(--radius-md);
  color:var(--text);padding:7px 14px;font-size:var(--text-sm);font-weight:var(--fw-semibold);cursor:pointer}
.ds-btn:hover{border-color:var(--accent);color:var(--accent)}
.ds-btn.primary{background:var(--accent);border-color:var(--accent);color:var(--on-accent)}
/* bulk bar */
.ds-bulk{display:flex;align-items:center;gap:8px;flex-wrap:wrap;background:var(--bg-deep);
  border:1px solid var(--border-bright);border-radius:var(--radius-lg);padding:9px 14px;font-size:var(--text-sm)}
.ds-bulk .hint{margin-left:auto;color:var(--text-dim);font-size:var(--text-xs)}
/* chips */
.ds-chip{display:inline-block;font-size:var(--text-xs);font-weight:var(--fw-bold);
  border-radius:var(--radius-full);padding:3px 11px;margin-right:6px}
.ds-chip.open{background:rgba(56,189,248,.14);color:var(--accent)}
.ds-chip.prog{background:rgba(251,191,36,.15);color:var(--warn)}
.ds-chip.done{background:rgba(52,211,153,.15);color:var(--success)}
.ds-chip.bad{background:rgba(248,113,113,.14);color:var(--danger)}
/* collapsible intake */
details.ds-intake{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius-lg);
  padding:12px 16px}
details.ds-intake summary{cursor:pointer;font-weight:var(--fw-bold);font-size:var(--text-sm);list-style:none}
details.ds-intake summary::-webkit-details-marker{display:none}
details.ds-intake summary::before{content:"▸ ";color:var(--text-muted)}
details.ds-intake[open] summary::before{content:"▾ "}
details.ds-intake .body{margin-top:10px;color:var(--text-muted);font-size:var(--text-sm)}
/* inline-editable table cell */
.ds-inline{border-collapse:collapse;font-size:var(--text-sm)}
.ds-inline td{border:1px solid var(--border);padding:7px 9px}
.ds-inline td:has(.ds-cell){padding:0}
.ds-cell{width:130px;background:transparent;border:1px solid transparent;border-radius:var(--radius-sm);
  color:var(--text);font:inherit;padding:7px 9px}
.ds-cell.num{text-align:right;font-variant-numeric:tabular-nums}
.ds-cell:hover{border-color:var(--border-bright)}
.ds-cell:focus{outline:none;border-color:var(--accent);background:var(--bg-deep)}
/* stepper */
.ds-steps{display:flex;gap:14px;flex-wrap:wrap;background:var(--surface);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:10px 16px;font-size:var(--text-sm)}
.ds-step{display:flex;align-items:center;gap:7px;color:var(--text-dim)}
.ds-step .b{width:20px;height:20px;border-radius:50%;display:inline-flex;align-items:center;
  justify-content:center;font-size:var(--text-xs);font-weight:var(--fw-bold);
  border:1px solid var(--border-bright)}
.ds-step.done{color:var(--text-muted)} .ds-step.done .b{background:var(--accent);color:var(--on-accent);border:0}
.ds-step.now{color:var(--text);font-weight:var(--fw-bold)}
.ds-step.now .b{border-color:var(--accent);color:var(--accent)}
/* demo staging — the shared modal/sheet are position:fixed in the real app, so
   the page pins them into a box instead of letting them cover this page */
.ds-stage{position:relative;background:var(--bg-deep);border:1px solid var(--border);
  border-radius:var(--radius-lg);padding:18px;overflow:hidden}
.ds-stage .wf-modal-backdrop,.ds-stage .wf-sheet{position:static}
.ds-stage .wf-modal-backdrop{padding:0}
.ds-stage .wf-sheet{border:1px solid var(--border-bright)}
.ds-phone{max-width:390px}
@media(max-width:640px){ .ds-toolbar{flex-direction:column;align-items:stretch} }
"""


def render(user):
    toks = "".join(
        f'<div class="tok"><span class="sw" style="background:var({t})"></span>'
        f'<span><div class="nm"><code>{t}</code></div><div class="ds">{d}</div></span></div>'
        for t, d in COLOR_TOKENS
    )
    return f"""<!doctype html><html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Design System · Wayfinder</title><link rel="stylesheet" href="/static/style.css">
<style>{DEMO_CSS}</style></head>
<body>
<nav><a href="/design" class="nav-brand">🎨 Design System</a>
<span class="nav-user"><a class="nav-back" href="/">← Home</a></span></nav>
<div class="ds-wrap">
  <h1>Wayfinder Design System</h1>
  <div class="ds-sub">The UX/UI standard for every Wayfinder app. Reference implementation:
  <a href="/cardconv/ledger">AMEX Expense Assistant</a>. Standard adopted 2026-07-13.</div>

  <div class="ds-sect"><h2>1 · Principles</h2>
    <ul class="ds-rules">
      <li><b>cardconv is the reference.</b> Before building any UI, check how the Expense
          Assistant solves the same problem and reuse that pattern.</li>
      <li><b>Design system first.</b> If no existing pattern fits, don't invent one inside an
          app — add it here (tokens in <code>server.py STYLE</code>, demo on this page), then use it.</li>
      <li><b>Accent discipline.</b> <code>--accent</code> goes on buttons, links, active tabs and
          badges only — never body text. Text on accent uses <code>--on-accent</code>.</li>
      <li><b>English UI copy.</b> Labels, confirmations and prompts are English (US colleagues
          use these tools). User-entered data may be Korean.</li>
      <li><b>Mobile is not optional.</b> Tables become cards (<code>td[data-label]</code>),
          popovers become bottom sheets, intake sections collapse by default.</li>
      <li><b>Both themes.</b> Dark is default; light theme overrides via
          <code>:root[data-theme="light"]</code> tokens. Never hardcode colors — always <code>var(--*)</code>.</li>
    </ul>
  </div>

  <div class="ds-sect"><h2>2 · Color tokens</h2>
    <p>Live from the global stylesheet — these swatches follow the active theme (try the 🌙/☀️ toggle).</p>
    <div class="tok-grid">{toks}</div>
  </div>

  <div class="ds-sect"><h2>3 · Components</h2>

    <h3>Pill tabs</h3>
    <p>App-level navigation inside a solution. One row, active = accent pill.</p>
    <div class="ds-tabs"><button class="ds-tab active">Receipt Ledger</button>
      <button class="ds-tab">Convert</button><button class="ds-tab">Review</button>
      <button class="ds-tab">History</button></div>

    <h3>Clickable stat cards = view switcher</h3>
    <p>Stat cards are the <b>only</b> status filter — clicking a card switches the view
    (active card gets an accent ring). Numbers use semantic colors.</p>
    <div class="ds-stats">
      <div class="ds-stat active"><div class="n">5</div><div class="l">Open</div></div>
      <div class="ds-stat ok"><div class="n">3</div><div class="l">Matched</div></div>
      <div class="ds-stat bad"><div class="n">2</div><div class="l">Unmatched</div></div>
      <div class="ds-stat warn"><div class="n">1</div><div class="l">In progress</div></div>
      <div class="ds-stat"><div class="n">0</div><div class="l">Completed</div></div>
    </div>

    <h3>Toolbar — one place per role</h3>
    <p>Period select (+ Custom…), search takes the flex space, advanced filters live in a
    <b>Filters ▾ popover</b> with an active-count badge, exports in an <b>Export ▾ dropdown</b>.
    Sorting belongs on column headers, not in the toolbar.</p>
    <div class="ds-toolbar">
      <label>Period</label><select><option>All time</option><option>This month</option><option>Custom…</option></select>
      <input placeholder="Search merchant...">
      <button class="ds-btn">Filters ▾</button><button class="ds-btn primary">⬇ Export ▾</button>
    </div>

    <h3>Bulk action bar</h3>
    <p>Appears only when rows are selected; actions are verbs, exports honor the selection.</p>
    <div class="ds-bulk"><input type="checkbox" checked> Select all
      <button class="ds-btn">Mark in progress</button><button class="ds-btn primary">✔ Mark completed</button>
      <button class="ds-btn">↩ Reopen</button><span class="hint">Click a card above to switch views</span></div>

    <h3>Status chips</h3>
    <p><span class="ds-chip open">OPEN</span><span class="ds-chip prog">⏳ IN PROGRESS</span>
    <span class="ds-chip done">✔ COMPLETED</span><span class="ds-chip bad">✕ UNMATCHED</span></p>

    <h3>Collapsible intake</h3>
    <p>Setup/input zones fold away once configured (<code>&lt;details&gt;</code>) — auto-open only
    when action is required (e.g. Drive not connected).</p>
    <details class="ds-intake"><summary>Register Receipts — Google Drive · Upload</summary>
      <div class="body">Intake body: connect CTA, upload zone. Collapsed by default on return visits.</div></details>

    <h3>Inline table edit</h3>
    <p>Reference grids people retype into (Deal Desk roster) make the cell itself the
    input: transparent until hovered, accent on focus, <b>saves on blur</b> to a
    single-field endpoint, and the border flashes <span style="color:var(--success)">green</span>
    on success. Enter commits and moves down the column. Two rules that are not optional —
    <b>typing never re-renders</b> (the caret must not jump), and the server takes a
    <b>whitelist</b> of editable fields so identity/linkage columns stay in the form.</p>
    <table class="ds-inline"><tr><td>Sr. Data Analyst</td>
      <td class="num"><input class="ds-cell num" value="$6,720"></td>
      <td class="num"><input class="ds-cell num" value="$20,496"></td></tr></table>

    <h3>Workflow stepper</h3>
    <p>Shows where the user is in the end-to-end flow; steps are labels, not buttons.</p>
    <div class="ds-steps">
      <span class="ds-step done"><span class="b">1</span>Connect Drive</span>
      <span class="ds-step done"><span class="b">2</span>Add Receipts</span>
      <span class="ds-step now"><span class="b">3</span>Review Ledger</span>
      <span class="ds-step"><span class="b">4</span>Convert CSV</span>
      <span class="ds-step"><span class="b">5</span>Review &amp; Download</span></div>

    <h3>Form controls</h3>
    <p>Controls sit on <code>--bg-deep</code> inside a <code>--surface</code> container, so they
    read as recessed; focus moves the border to <code>--accent</code>, never a browser glow.
    Money uses <code>type=text inputmode=decimal</code> with <code>.wf-num</code> — the number
    spinner is useless and the mobile keypad is worse. Remember that
    <b>clearing a field needs a sentinel</b>: <code>parse_qs</code> drops empty values.</p>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;max-width:520px">
      <label class="wf-field"><span class="wf-label">Merchant</span>
        <input class="wf-input" type="text" value="JANG TU RESTAURANT"></label>
      <label class="wf-field"><span class="wf-label">Card type</span>
        <select class="wf-input"><option>AMEX</option><option>Cash</option></select></label>
      <label class="wf-field"><span class="wf-label">Amount (USD)</span>
        <input class="wf-input wf-num" type="text" inputmode="decimal" value="157.98"></label>
      <label class="wf-field"><span class="wf-label">Usage</span>
        <input class="wf-input" type="text" value="Regular" disabled></label>
    </div>
    <p style="margin-top:10px"><label class="wf-checkbox"><input type="checkbox" checked> Select all</label></p>

    <h3>Empty state</h3>
    <p>Name <b>why</b> it's empty and offer the one action that fills it — "No data" is not a
    message. Nothing-yet and filter-matched-nothing read differently; the second must not
    look like failure.</p>
    <div class="wf-empty-card" style="padding:26px 20px;text-align:center;max-width:420px">
      <div class="wf-empty-icon">🔍</div>
      <div class="wf-empty-title">No rows match these filters</div>
      <p class="wf-empty-sub">3 filters are active — 113 receipts are hidden.</p>
      <div class="wf-empty-actions"><button class="btn btn-secondary">↺ Reset all</button></div>
    </div>

    <h3>Modal</h3>
    <p>State the <b>consequence</b>, not the mechanism. Buttons are verbs that match the title,
    the destructive one is <code>.btn-danger</code> and never the default focus. Anything
    undoable shouldn't be a modal at all — do it and offer an undo. At ≤768px the modal
    becomes a bottom sheet automatically, same as every other popover.</p>
    <div class="ds-stage">
      <div class="wf-modal-backdrop"><div class="wf-modal">
        <h3 class="wf-modal-title">🗑 Delete card profile</h3>
        <p class="wf-modal-body">This removes the profile and <b>all of its app data</b> —
        statements, ledger, OCR queue and card names. Files already in Google Drive stay in Drive.</p>
        <div class="wf-modal-actions"><button class="btn btn-secondary">Cancel</button>
          <button class="btn btn-danger">Delete profile</button></div>
      </div></div>
    </div>

    <h3>Bottom sheet</h3>
    <p>An anchored menu clips off-screen on a narrow viewport, so at ≤768px it stops being
    anchored and becomes a fixed sheet in the thumb zone, padded for
    <code>env(safe-area-inset-bottom)</code>. Same click-to-toggle behavior as the desktop
    popover — don't invent a drag gesture nothing else in the app uses.</p>
    <div class="ds-stage ds-phone">
      <div class="wf-sheet">
        <div class="wf-sheet-title">Filters</div>
        <label class="wf-field" style="margin-bottom:10px"><span class="wf-label">Card</span>
          <select class="wf-input"><option>All</option><option>AMEX</option><option>Cash</option></select></label>
        <div style="display:flex;gap:8px"><button class="btn btn-secondary">↺ Reset</button>
          <button class="btn btn-primary" style="flex:1">Apply</button></div>
      </div>
    </div>

    <h3>Table that becomes cards</h3>
    <p>Transactional rows (ones people act on) use <code>.wf-cardtable</code>: a normal table on
    desktop, one card per row below 768px, where <b>every <code>td</code> carries
    <code>data-label</code></b>. Cap the card at ~6 visible fields — deeper edits belong in the
    detail panel. Reference tables you only read keep their shape inside an
    <code>overflow-x:auto</code> wrapper instead. Either way the page body never scrolls sideways.</p>
    <table class="wf-cardtable" style="max-width:640px">
      <thead><tr><th>Date</th><th>Merchant</th><th>Final</th><th>Card</th><th>Status</th></tr></thead>
      <tbody>
        <tr><td data-label="Date">2026-07-15</td><td data-label="Merchant">JANG TU RESTAURANT</td>
          <td data-label="Final">$157.98</td><td data-label="Card">AMEX</td>
          <td data-label="Status"><span class="ds-chip prog">⏳ IN PROGRESS</span></td></tr>
        <tr><td data-label="Date">2026-07-15</td><td data-label="Merchant">STARBUCKS Store #5217</td>
          <td data-label="Final">$15.85</td><td data-label="Card">Cash</td>
          <td data-label="Status"><span class="ds-chip open">OPEN</span></td></tr>
      </tbody>
    </table>

    <h3>List row + detail sheet</h3>
    <p>A row people scan is <b>not a form</b>. Momentum Tasks used to put every editable
    field inline — fourteen controls per row, over a hundred on one screen, with the project
    and the priority printed twice: once as a chip to read, once as a control to change.
    The list became unreadable and the width went to controls nobody was using.</p>
    <p>The row carries a <b>checkbox, a title and its chips</b>. Tapping anywhere else opens a
    sheet that edits everything — including the title. Bottom sheet under 768px, centred dialog
    above. Reference: <code>services/todo.py</code> (<code>.tk-row</code> / <code>.tk-sheet</code>).</p>
    <div class="ds-demo" style="flex-direction:column;align-items:stretch;gap:10px">
      <div style="display:flex;align-items:flex-start;gap:12px;padding:12px 14px;background:var(--surface);
                  border:1px solid var(--border);border-radius:var(--radius-md)">
        <span style="width:24px;height:24px;border-radius:50%;border:2px solid var(--border-bright);flex-shrink:0"></span>
        <span style="flex:1">
          <span style="display:block;color:var(--text)">Client feedback pass</span>
          <span style="display:flex;gap:6px;margin-top:6px">
            <span class="ds-chip" style="border:1px solid var(--danger);color:var(--danger);background:transparent">1d overdue</span>
            <span class="ds-chip" style="border:1px solid var(--border-bright);color:var(--text-muted);background:transparent">Samsung AEO</span>
          </span>
        </span>
        <span style="color:var(--text-dim)">›</span>
      </div>
    </div>
    <p><b>Chips carry no fill.</b> A tinted background put every one of ours under AA in the light
    theme (measured 4.13–4.49). On the card surface the same colors clear it in both themes, and
    an outline still reads as a chip.</p>

    <h3>Adaptive disclosure — and its trap</h3>
    <p>Controls appear when there is something to control. An empty Tasks screen used to show
    six blocks of management furniture — stats, a group button, two filters, a reset — before it
    showed any way to add a task. Filters now appear at eight open items, the completed list when
    something is completed.</p>
    <p><b>The trap: never hide the way to create the thing you have none of.</b> Places was hidden
    when the list was empty, which is exactly the state where you need to add one — the only route
    to a first place had been removed. Hide the <i>management</i> of a set, never its <i>entry point</i>.</p>
    <p>And the primary action gets the primary button. Ours was <code>+ New Group</code> — big and
    blue and making a folder — while <code>+ Task</code> sat at the bottom in small grey.</p>

    <h3>Progress — work that runs long</h3>
    <p>Anything that keeps the user waiting past roughly two seconds says so.
    <b>Never leave a still screen</b>: a receipt PDF takes about a second per receipt, so a
    hundred of them is over a minute in which nothing on screen moves and the page reads as
    broken — that is exactly what produced a 504 report from the field.</p>
    <p>The indicator is <b>indeterminate on purpose</b>. Most of our slow work cannot report a
    percentage honestly, and a bar that invents one is worse than no bar. Show a thin top rail
    plus a one-line note saying what is being built and, where it is knowable, the rough rate
    (&ldquo;about a second per receipt&rdquo;).</p>
    <p>Downloads are the awkward case: the browser owns them, so JS never sees them finish.
    The server stamps a <code>wf_dl</code> cookie onto the response and the helper watches for
    it — do not buffer a file into memory just to draw a bar.</p>
    <div class="ds-demo" style="flex-direction:column;align-items:stretch;gap:14px">
      <div class="wf-progress is-on" style="position:relative;top:auto"></div>
      <div class="wf-progress-note is-on" style="position:relative;top:auto;left:auto;translate:none">
        <span class="wf-spinner"></span><span>Building your expense report — receipt images take about a second each…</span>
      </div>
      <div><button class="btn btn-primary is-busy">Downloading</button></div>
    </div>
    <p><b>How to use it.</b> Every page already has the helper injected — there is nothing to
    import. Pick the call that matches how the download is triggered, and never wire one by
    hand:</p>
    <pre class="ds-code">wfProgress.downloadUrl(url, 'Building your receipt PDF…')  // window.location style
wfProgress.download(linkEl, 'Preparing…')                  // a real &lt;a&gt; link
wfProgress.downloadAll([urlA, urlB], 'Building both files…')  // several attachments
wfProgress.start('Working…') / wfProgress.stop()            // anything else that is slow</pre>
    <p>The watcher gives up after 15 minutes so a failed download never leaves the page
    spinning, and <code>prefers-reduced-motion</code> stops the animation without hiding the
    indicator.</p>

    <h3>External feed summary card <span style="font-size:.7rem;color:var(--text-muted);font-weight:500">(2026-08-01 · first use: Toast 광고주 뉴스)</span></h3>
    <p>For content pulled from an outside feed (news, mail, RSS) and digested by AI. One card =
    <b>①source label + ↻ refresh</b> in the header row, <b>②one-line situation summary</b> (serif,
    larger), <b>③3–5 point rows</b> (bold what happened + muted why it matters), <b>④original links
    folded in a &lt;details&gt;</b>, <b>⑤footer: collected-at time + stale warning</b> when a refresh
    failed and an old result is shown. Never render fetched text as fact without the collected-at
    stamp — freshness is part of the data. Refresh policy: background warm on app open, manual ↻
    forces, everything else serves cache.</p>
    <div class="ds-card" style="max-width:420px">
      <div style="display:flex;justify-content:space-between;align-items:baseline">
        <span style="font-size:.72rem;font-weight:700;color:var(--accent)">CLIENT · UNIT</span>
        <button class="ds-btn" style="font-size:.72rem">↻ Refresh</button></div>
      <div style="font-style:italic;font-size:1.05rem;margin:.4rem 0">One-line situation summary.</div>
      <div style="border-top:1px solid var(--border);padding:.45rem 0">
        <div style="font-weight:600">What happened, one sentence.</div>
        <div style="color:var(--text-muted);font-size:.85rem">Why it matters / how to bring it up.</div></div>
      <details style="margin-top:.4rem"><summary style="font-size:.8rem;color:var(--text-muted);cursor:pointer">Original headlines (10)</summary></details>
      <div style="font-size:.75rem;color:var(--text-muted);margin-top:.4rem">Collected 2026-08-01 09:00</div>
    </div>

  </div>

  <div class="ds-sect"><h2>4 · Rules &amp; pitfalls</h2>
    <ul class="ds-rules">
      <li><b>JS binds to IDs/classes</b> — when restyling, preserve IDs, classes and row structure
          so existing bindings survive (cardconv: 113 interactions untouched in the pill-tab redesign).</li>
      <li><b><code>hidden</code> loses to author <code>display</code></b> — any stylesheet that sets
          <code>display</code> on a hideable element needs <code>[hidden]{{display:none!important}}</code>.</li>
      <li><b>Empty form values are dropped</b> by <code>parse_qs</code> — clearing a field needs a
          sentinel (e.g. <code>__clear__</code>, <code>none</code>).</li>
      <li><b>No emoji escapes in Python strings</b> (<code>\\ud83c…</code> crashes on encode) — paste
          the actual emoji character.</li>
      <li><b>Stale-render guard</b> — sequence-check async list renders so a slow response can't
          overwrite a newer filter click.</li>
      <li><b>Buttons say what they download</b> — <code>⬇ xlsx (SAP)</code> vs
          <code>⬇ xlsx (ledger)</code>, never two identical labels.</li>
      <li><b>Wording follows state</b> — on a task that was just created, "Cancel" claims to undo
          an add that already happened. It reads "Later" there. A label that lies about what a
          button does costs more than a longer label.</li>
      <li><b>One axis of classification</b> — groups and projects were two names for the same
          thing, so every new task made you choose which one to use. Collapse them; a second axis
          has to earn itself.</li>
      <li><b>Sort answers "what now"</b> — due-date-only ordering puts a Low above a High.
          Bucket by urgency (overdue/today → this week → later), then priority inside each.</li>
      <li><b>Fixed elements at the bottom compete</b> — tab bar, back pill, theme toggle and any
          sheet all want <code>bottom:0</code>. Decide the stack once: the pill and toggle lift
          above the tab bar and hide entirely while a sheet is open.</li>
      <li><b>A hex inline on an element cannot be themed</b> — the toggle and the back pill were
          inline-styled, so no media query or theme rule could reach them. Anything that might
          move or change color needs a class.</li>
    </ul>
  </div>

  <div class="ds-sect"><h2>5 · Mobile UX standard <span style="font-size:.7rem;color:var(--text-muted);font-weight:500">(2026-07-22 · full spec: docs/mobile_ux_guideline.md · reference impl: cardconv)</span></h2>
    <ul class="ds-rules">
      <li><b>Check at 425px, not 390</b> — that is the width this is actually used at, and the
          narrower one hides problems rather than exposing them. <b>Check the empty state too</b>:
          "the management UI fills a screen with nothing in it" is invisible when you only ever
          look at a screen with data.</li>
      <li><b><code>viewport-fit=cover</code> or safe-area is zero</b> — without it iOS reports
          <code>env(safe-area-inset-*)</code> as 0, so a bar pinned to <code>bottom:0</code> sits
          under Safari's toolbar and only appears once you scroll and the toolbar shrinks. The
          meta is normalised for every page in <code>send_html</code>; do not hand-write it.</li>
      <li><b>Tap area ≠ visual size</b> — keep the 24px circle and grow the hit box to 44 with a
          pseudo element (<code>::after</code> at <code>width:max(100%,44px)</code>). Rows keep
          their spacing and the target still passes. Verify by clicking 20px off-centre;
          <code>getBoundingClientRect</code> does not see the pseudo element.</li>
      <li><b>Breakpoints</b> — mobile <code>@media(max-width:768px)</code> (standard for all new rules),
          small <code>480px</code> density-only. Assume touch from 768 down; hover needs a visible non-hover twin.</li>
      <li><b>Chrome budget ≤ 25% of viewport</b> — nav is one line (<code>.nav-brand</code> ellipsis, never wraps);
          pill tabs never wrap: <code>flex-wrap:nowrap; overflow-x:auto</code>, scrollbar hidden, active tab auto-centered.
          Workflow/filter/intake bars scroll away, they don't stick.</li>
      <li><b>Touch targets</b> — primary controls ≥44px hit area (grow with padding, not glyph);
          checkboxes: global <code>min-width/min-height:20px</code> guardrail beats any <code>width:Npx</code>.
          All tappables get <code>touch-action:manipulation</code> + a visible <code>:active</code> state.</li>
      <li><b>Inputs</b> — global guardrail: every input/select/textarea gets <code>font-size:16px!important</code>
          at ≤768px (computed &lt;16px triggers iOS focus auto-zoom; never "fix" with maximum-scale).
          Money: <code>type=text inputmode=decimal</code>, tabular-nums.</li>
      <li><b>Tables</b> — transactional rows → card transform, ≤6 visible fields (deep edits live in the
          detail panel, full-width on mobile); reference tables → own <code>overflow-x:auto</code> wrapper.
          The page body never scrolls horizontally.</li>
      <li><b>Bulk action bars</b> — hidden until selection &gt; 0, then fixed to the bottom thumb zone
          (<code>env(safe-area-inset-bottom)</code> padding, container gets matching bottom padding,
          floating pills hide via <code>body:has(...)</code>).</li>
      <li><b>Filter bars</b> — strict 2-col grid: search leads full-width, each field stacks its label
          over a full-width control; watch <code>.fb-field{{flex-wrap:wrap}}</code> unfolding row fields.</li>
      <li><b>Popovers never render off-screen</b> — anchored menus (<code>.fb-menu</code>) and tooltips
          (<code>.cc-tip</code>) become fixed bottom sheets at ≤768px.</li>
      <li><b>Typing never rebuilds the input under the cursor</b> — input events update data + computed
          cells in place; full re-renders only on structural changes (add/remove/mode switch).</li>
    </ul>
  </div>

  <div class="ds-sect"><h2>6 · Extending the system</h2>
    <ul class="ds-rules">
      <li>Add/adjust tokens in <code>server.py STYLE</code> (dark + light theme both).</li>
      <li>Add the component demo to this page (<code>services/design.py</code>) with usage rules.</li>
      <li><b>Every new shared pattern lands here in the same change</b> — this page is the living
          contract, not an afterthought (강프로 standing rule, 2026-07-22).</li>
      <li>Check existing apps for retrofit — the goal is one Look&amp;Feel across Wayfinder.</li>
      <li>Component library (React, for claude.ai/design): <code>~/labs/wayfinder-ds</code>.</li>
    </ul>
  </div>
</div></body></html>"""


def handle(method, path, body, ctx):
    if method == "GET" and path == "/design":
        return ("html", render(ctx.get("user", "guest")))
    return ("html", "<h2>404 Not Found</h2>")
