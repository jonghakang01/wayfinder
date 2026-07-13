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
<nav><span class="nav-brand">🎨 Design System</span>
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

    <h3>Workflow stepper</h3>
    <p>Shows where the user is in the end-to-end flow; steps are labels, not buttons.</p>
    <div class="ds-steps">
      <span class="ds-step done"><span class="b">1</span>Connect Drive</span>
      <span class="ds-step done"><span class="b">2</span>Add Receipts</span>
      <span class="ds-step now"><span class="b">3</span>Review Ledger</span>
      <span class="ds-step"><span class="b">4</span>Convert CSV</span>
      <span class="ds-step"><span class="b">5</span>Review &amp; Download</span></div>
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
    </ul>
  </div>

  <div class="ds-sect"><h2>5 · Extending the system</h2>
    <ul class="ds-rules">
      <li>Add/adjust tokens in <code>server.py STYLE</code> (dark + light theme both).</li>
      <li>Add the component demo to this page (<code>services/design.py</code>) with usage rules.</li>
      <li>Check existing apps for retrofit — the goal is one Look&amp;Feel across Wayfinder.</li>
      <li>Component library (React, for claude.ai/design): <code>~/labs/wayfinder-ds</code>.</li>
    </ul>
  </div>
</div></body></html>"""


def handle(method, path, body, ctx):
    if method == "GET" and path == "/design":
        return ("html", render(ctx.get("user", "guest")))
    return ("html", "<h2>404 Not Found</h2>")
