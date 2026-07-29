"""The card list for the Claude Design project.

Each entry becomes one preview card in the Design System pane plus a `.md`
usage note. Markup uses the product's real class names so anything Claude
generates from these pastes straight into a Wayfinder page.

frame:
  "dual"  — dark + light side by side (default; the guideline demands both)
  "phone" — a single 390px column, for the mobile-only patterns
"""

CARDS = [
    # ------------------------------------------------------------------ Foundations
    dict(
        name="Colors", group="Foundations", frame="tokens",
        subtitle="Surface, text, semantic and group accents — dark + light",
        notes="""Colors are **only** ever referenced as `var(--token)`. A hex literal in an app
stylesheet is a lint failure (`tests/uxui_lint.py`), because the light theme
re-points every token and a hardcoded color simply doesn't follow.

**Accent discipline** — `--accent` belongs on buttons, links, active tabs and
badges. Never on body text. Text sitting on an accent fill uses `--on-accent`.

**Status is a separate axis** from accent: `--success` / `--warn` / `--danger`
/ `--info` carry meaning, so don't reach for them decoratively.

**Group accents** (`--group-1` … `--group-5`) label categories that have no
inherent status — home menu sections, Deal Desk vendor vs SEA side. They keep
their hue in light theme but darken, because the dark-theme values wash out on
white.""",
    ),
    dict(
        name="Typography", group="Foundations", frame="dual",
        subtitle="4 sizes, 4 weights, Pretendard Variable",
        notes="""The type scale is deliberately short — four sizes cover every screen. If a
new size feels necessary, the layout is usually the thing that's wrong.

Numbers in tables and money columns get `font-variant-numeric: tabular-nums`
so digits line up between rows.

`--text-xs` with `font-weight:700`, `letter-spacing:.06em` and
`text-transform:uppercase` is the standard field-label treatment (toolbars,
stat cards, detail rows).""",
        html="""
<div class="dsx-stack">
  <div style="font-size:var(--text-md);font-weight:var(--fw-extrabold)">--text-md · 800 — page title</div>
  <div style="font-size:var(--text-base);font-weight:var(--fw-bold)">--text-base · 700 — section heading</div>
  <div style="font-size:var(--text-base)">--text-base · 400 — body copy, table cells</div>
  <div style="font-size:var(--text-sm);color:var(--text-muted)">--text-sm · muted — secondary text, captions</div>
  <div style="font-size:var(--text-xs);font-weight:var(--fw-bold);letter-spacing:.06em;
              text-transform:uppercase;color:var(--text-muted)">--text-xs · 700 caps — field label</div>
  <div style="font-size:var(--text-sm);font-variant-numeric:tabular-nums">
    tabular-nums &nbsp; $1,234.56 &nbsp; $987.10 &nbsp; $11,090.00</div>
</div>""",
    ),
    dict(
        name="Spacing, radius, elevation", group="Foundations", frame="dual",
        subtitle="--sp-1…6, --radius-sm…full, three shadows",
        notes="""Spacing steps are 4/8/12/16/20/24. Radius climbs with the size of the thing:
`--radius-sm` on cells and swatches, `--radius-md` on inputs and buttons,
`--radius-lg` on cards and bars, `--radius-full` on pills and chips.

Elevation is used sparingly — `--shadow-md` for popovers and modals,
`--shadow-lg` for bottom sheets. Cards sit flat on the surface and separate
with a border instead.""",
        html="""
<div class="dsx-stack">
  <div class="dsx-row">
    <span class="dsx-sp" style="width:var(--sp-1)"></span><code>--sp-1</code>
    <span class="dsx-sp" style="width:var(--sp-2)"></span><code>--sp-2</code>
    <span class="dsx-sp" style="width:var(--sp-3)"></span><code>--sp-3</code>
    <span class="dsx-sp" style="width:var(--sp-4)"></span><code>--sp-4</code>
    <span class="dsx-sp" style="width:var(--sp-5)"></span><code>--sp-5</code>
    <span class="dsx-sp" style="width:var(--sp-6)"></span><code>--sp-6</code>
  </div>
  <div class="dsx-row">
    <span class="dsx-box" style="border-radius:var(--radius-sm)">sm</span>
    <span class="dsx-box" style="border-radius:var(--radius-md)">md</span>
    <span class="dsx-box" style="border-radius:var(--radius-lg)">lg</span>
    <span class="dsx-box" style="border-radius:var(--radius-xl)">xl</span>
    <span class="dsx-box" style="border-radius:var(--radius-full);width:74px">full</span>
  </div>
  <div class="dsx-row">
    <span class="dsx-box" style="box-shadow:var(--shadow-sm)">sm</span>
    <span class="dsx-box" style="box-shadow:var(--shadow-md)">md</span>
    <span class="dsx-box" style="box-shadow:var(--shadow-lg)">lg</span>
  </div>
</div>""",
    ),

    # ------------------------------------------------------------------ Core
    dict(
        name="Buttons", group="Core", frame="dual",
        subtitle=".btn + primary / secondary / ghost / accent / success / danger / warn, 3 sizes",
        notes="""`.btn` is the base; a variant class carries the color. Sizes are
`.btn-sm` (28px), default (32px) and `.btn-lg` (40px).

**The label says what happens.** Two buttons that both read "Download" is a
bug — write `⬇ xlsx (SAP)` and `⬇ xlsx (ledger)`. Destructive actions say the
noun they destroy.

**Touch** — at ≤768px every button needs a ≥44px hit area. Grow it with
padding, not by scaling the glyph, and give it a visible `:active` state plus
`touch-action:manipulation`.""",
        html="""
<div class="dsx-stack">
  <div class="dsx-row">
    <button class="btn btn-primary">Primary</button>
    <button class="btn btn-secondary">Secondary</button>
    <button class="btn btn-ghost">Ghost</button>
    <button class="btn btn-accent">Accent</button>
  </div>
  <div class="dsx-row">
    <button class="btn btn-success">✔ Mark completed</button>
    <button class="btn btn-warn">⏳ Mark in progress</button>
    <button class="btn btn-danger">🗑 Delete profile</button>
  </div>
  <div class="dsx-row">
    <button class="btn btn-primary btn-sm">Small</button>
    <button class="btn btn-primary">Base</button>
    <button class="btn btn-primary btn-lg">Large</button>
    <button class="btn btn-secondary" disabled>Disabled</button>
  </div>
</div>""",
    ),
    dict(
        name="Form controls", group="Core", frame="dual",
        subtitle="Text, select, money, textarea, checkbox, toggle",
        notes="""Controls sit on `--bg-deep` inside a `--surface` container, so they read as
recessed. Focus moves the border to `--accent` — never a browser outline glow.

**Money** uses `type=text inputmode=decimal` with tabular-nums, not
`type=number`: the spinner is useless and the mobile keypad is worse.

**iOS zoom** — at ≤768px every input/select/textarea gets
`font-size:16px !important`. Anything computed under 16px makes Safari
auto-zoom on focus. Never "fix" that with `maximum-scale`.

**Clearing a field needs a sentinel.** `parse_qs` drops empty form values, so
an empty string never reaches the server — send `__clear__` or `none` and map
it back to null.""",
        html="""
<div class="dsx-stack">
  <div class="dsx-grid2">
    <label class="wf-field"><span class="wf-label">Merchant</span>
      <input class="wf-input" type="text" value="JANG TU RESTAURANT"></label>
    <label class="wf-field"><span class="wf-label">Card type</span>
      <select class="wf-input"><option>AMEX</option><option>Cash</option></select></label>
    <label class="wf-field"><span class="wf-label">Amount (USD)</span>
      <input class="wf-input wf-num" type="text" inputmode="decimal" value="157.98"></label>
    <label class="wf-field"><span class="wf-label">Focused</span>
      <input class="wf-input dsx-focus" type="text" value="Border goes accent"></label>
  </div>
  <label class="wf-field"><span class="wf-label">Reason for Cash</span>
    <textarea class="wf-input" rows="2">Vendor does not accept cards</textarea></label>
  <div class="dsx-row">
    <label class="wf-checkbox"><input type="checkbox" checked> Select all</label>
    <label class="wf-checkbox"><input type="checkbox"> Not a duplicate</label>
    <span class="dsx-toggle dsx-on"><i></i></span><span class="wf-label">Dark</span>
    <span class="dsx-toggle"><i></i></span><span class="wf-label">Light</span>
  </div>
</div>""",
    ),
    dict(
        name="Status chips", group="Core", frame="dual",
        subtitle="Open / in progress / completed / unmatched",
        notes="""A chip is a **state**, not a button — it never takes a click. Filtering
happens on the stat cards above the table.

The fill is the status color at 14–15% alpha with the solid color as text, so
chips stay legible in both themes without a second palette.

Keep the vocabulary closed. `OPEN`, `⏳ IN PROGRESS`, `✔ COMPLETED`,
`✕ UNMATCHED` — a new status means a new rule, not a new color.""",
        html="""
<div class="dsx-row">
  <span class="ds-chip open">OPEN</span>
  <span class="ds-chip prog">⏳ IN PROGRESS</span>
  <span class="ds-chip done">✔ COMPLETED</span>
  <span class="ds-chip bad">✕ UNMATCHED</span>
  <span class="ds-chip">💳 AMEX</span>
  <span class="ds-chip">💵 Cash</span>
</div>""",
    ),
    dict(
        name="Empty state", group="Core", frame="dual",
        subtitle="Icon, one line of cause, one action",
        notes="""An empty state names **why** it's empty and offers the one action that fills
it. "No data" is not a message.

Distinguish the two cases: nothing exists yet (offer the create action) versus
the filter matched nothing (offer to reset the filter). They read differently
and the second one must not look like failure.""",
        html="""
<div class="dsx-stack">
  <div class="wf-empty-card dsx-pad">
    <div class="wf-empty-icon">🧾</div>
    <div class="wf-empty-title">No receipts registered yet</div>
    <p class="wf-empty-sub">Connect Google Drive or upload images to start the ledger.</p>
    <button class="btn btn-primary">Connect Google Drive</button>
  </div>
  <div class="wf-empty-card dsx-pad">
    <div class="wf-empty-icon">🔍</div>
    <div class="wf-empty-title">No rows match these filters</div>
    <p class="wf-empty-sub">3 filters are active — 113 receipts are hidden.</p>
    <button class="btn btn-secondary">↺ Reset all</button>
  </div>
</div>""",
    ),
    dict(
        name="Tooltip", group="Core", frame="dual",
        subtitle="Inline ⓘ affordance, bottom sheet on mobile",
        notes="""The trigger is a 14px `ⓘ` next to the label it explains — never a hover on
the label itself, because at ≤768px there is no hover.

The tip is **click-to-toggle**, not hover-only, for exactly that reason. At
≤768px it stops being anchored and becomes a fixed card pinned above
`env(safe-area-inset-bottom)`, because an anchored popover clips off-screen on
a narrow viewport.

Use `.tip-right` when the trigger sits in the right half of the container.""",
        html="""
<div class="dsx-stack">
  <div class="dsx-row"><span class="wf-label">Duplicates</span>
    <span class="cc-info-wrap"><span class="cc-info">i</span>
      <span class="cc-tip dsx-tip-open">Receipts scanned twice land in the same duplicate group.
      Delete the redundant copy, or mark them ✂ Not dup when they really are two purchases.</span>
    </span>
  </div>
  <div style="height:70px"></div>
</div>""",
    ),
    dict(
        name="Modal", group="Core", frame="dual",
        subtitle="Title, consequence, verb-labelled actions",
        notes="""A modal states the **consequence**, not the mechanism. "Delete this card
profile and ALL its app data" beats "Are you sure?".

Buttons are verbs that match the title. The destructive one is
`.btn-danger` and is never the default focus.

Confirmations that can be undone shouldn't be modals at all — do the thing and
offer an undo.""",
        html="""
<div class="dsx-stage"><div class="wf-modal-backdrop">
  <div class="wf-modal">
    <h3 class="wf-modal-title">🗑 Delete card profile</h3>
    <p class="wf-modal-body">This removes the profile and <b>all of its app data</b> —
      statements, ledger, OCR queue and card names. Files already in Google Drive stay in Drive.</p>
    <div class="wf-modal-actions">
      <button class="btn btn-secondary">Cancel</button>
      <button class="btn btn-danger">Delete profile</button>
    </div>
  </div>
</div></div>""",
    ),

    # ------------------------------------------------------------------ Patterns
    dict(
        name="Pill tabs", group="Patterns", frame="dual",
        subtitle="App-level navigation inside a solution",
        notes="""One row of pills, active one filled with `--accent`. This is navigation
*within* a solution — the home menu handles moving between solutions.

**They never wrap.** At ≤768px the row becomes
`flex-wrap:nowrap; overflow-x:auto` with the scrollbar hidden and the active
pill auto-centered; the last pill peeking at the edge is the scroll cue.

A count badge on a tab means work is waiting there. It's clickable when the
badge itself opens the queue.""",
        html="""
<div class="ds-tabs">
  <button class="ds-tab active">Receipt Ledger</button>
  <button class="ds-tab">Convert</button>
  <button class="ds-tab">Review</button>
  <button class="ds-tab">History</button>
  <button class="ds-tab">Keywords</button>
</div>""",
    ),
    dict(
        name="Stat cards", group="Patterns", frame="dual",
        subtitle="The status filter — clicking a card switches the view",
        notes="""Stat cards are the **only** status filter in a Wayfinder app. There is no
duplicate status dropdown in the toolbar; clicking a card switches the view and
the active card takes an accent ring.

Numbers carry semantic color — matched is `--success`, unmatched is
`--danger`, in-progress is `--warn`. A neutral count stays `--text`.

Labels are uppercase `--text-xs`, 700 weight. The number is 1.5rem / 800.""",
        html="""
<div class="ds-stats">
  <div class="ds-stat active"><div class="n">113</div><div class="l">Total</div></div>
  <div class="ds-stat ok"><div class="n">93</div><div class="l">Matched</div></div>
  <div class="ds-stat bad"><div class="n">10</div><div class="l">Unmatched</div></div>
  <div class="ds-stat warn"><div class="n">3</div><div class="l">In progress</div></div>
  <div class="ds-stat"><div class="n">6</div><div class="l">Completed</div></div>
</div>""",
    ),
    dict(
        name="Toolbar", group="Patterns", frame="dual",
        subtitle="One place per role — period, search, filters, export",
        notes="""Each control has exactly one home. Period select on the left (with a
`Custom…` option), search takes the flex space, everything advanced hides
behind a **Filters ▾** popover carrying an active-count badge, and downloads
live in an **Export ▾** dropdown.

**Sorting belongs on column headers**, not in the toolbar. **Status filtering
belongs on the stat cards**, not here.

At ≤640px the bar stacks to `flex-direction:column`; at ≤768px filter fields
become a strict 2-column grid with search leading full-width.""",
        html="""
<div class="ds-toolbar">
  <label>Period</label>
  <select><option>All time</option><option>This month</option><option>Custom…</option></select>
  <input placeholder="Search merchant…">
  <button class="ds-btn">Filters ▾ <span class="ds-chip open" style="margin:0 0 0 4px">3</span></button>
  <button class="ds-btn primary">⬇ Export ▾</button>
</div>""",
    ),
    dict(
        name="Bulk action bar", group="Patterns", frame="dual",
        subtitle="Appears only when rows are selected",
        notes="""Hidden at zero selection — it appears the moment a row is checked, so it
never occupies space it hasn't earned.

Actions are **verbs**, and exports honor the current selection rather than
silently exporting everything.

At ≤768px it fixes to the bottom thumb zone with
`env(safe-area-inset-bottom)` padding; the scroll container gets matching
bottom padding and any floating pill hides via `body:has(...)` so the two never
stack.""",
        html="""
<div class="ds-bulk">
  <input type="checkbox" checked> <b>4 selected</b>
  <button class="ds-btn">⏳ Mark in progress</button>
  <button class="ds-btn primary">✔ Mark completed</button>
  <button class="ds-btn">↩ Reopen</button>
  <span class="hint">Click a card above to switch views</span>
</div>""",
    ),
    dict(
        name="Collapsible intake", group="Patterns", frame="dual",
        subtitle="Setup zones fold away once configured",
        notes="""Input and setup zones are a `<details>` that collapses once the user is set
up — the ledger, not the uploader, is what people come back for.

**Auto-open only when action is required** (Drive not connected, credentials
expired). Otherwise it stays shut on return visits.

The summary line carries the state, so a collapsed section still tells you
whether it's healthy.""",
        html="""
<details class="ds-intake" open>
  <summary>Register Receipts — Google Drive · Upload</summary>
  <div class="body">Connect CTA and upload dropzone live here. Collapsed by default
  on return visits; force-opened while Drive is disconnected.</div>
</details>
<details class="ds-intake" style="margin-top:10px">
  <summary>Discarded — 1 rejected receipt, never re-queued</summary>
  <div class="body">Tombstoned rows with a Restore action.</div>
</details>""",
    ),
    dict(
        name="Inline edit table", group="Patterns", frame="dual",
        subtitle="The cell is the input — saves on blur",
        notes="""Reference grids people retype into (the Deal Desk roster) make the cell
itself the input: transparent until hovered, `--accent` border on focus,
**saves on blur** to a single-field endpoint, border flashing `--success` on
success. Enter commits and moves down the column.

Two rules that are not optional:

1. **Typing never re-renders.** Input events update data and computed cells in
   place. A full re-render steals the caret. Structural changes (add/remove
   row, mode switch) are the only thing allowed to rebuild.
2. **The server takes a whitelist** of editable fields, so identity and
   linkage columns can't be written through the grid.""",
        html="""
<table class="ds-inline">
  <tr><td>Sr. Data Analyst</td>
    <td class="num"><input class="ds-cell num" value="$6,720"></td>
    <td class="num"><input class="ds-cell num" value="$20,496"></td></tr>
  <tr><td>Project Manager</td>
    <td class="num"><input class="ds-cell num dsx-focus" value="$8,150"></td>
    <td class="num"><input class="ds-cell num" value="$24,450"></td></tr>
</table>""",
    ),
    dict(
        name="Workflow stepper", group="Patterns", frame="dual",
        subtitle="Where you are in the end-to-end flow",
        notes="""Steps are **labels, not buttons** — the stepper reports position, it doesn't
navigate. Done steps fill their badge, the current one outlines in accent.

It scrolls away with the page rather than sticking; on mobile the chrome
budget is 25% of the viewport and a sticky stepper eats it.

At ≤600px the labels drop and only the numbered badges remain.""",
        html="""
<div class="ds-steps">
  <span class="ds-step done"><span class="b">1</span>Connect Drive</span>
  <span class="ds-step done"><span class="b">2</span>Add Receipts</span>
  <span class="ds-step now"><span class="b">3</span>Review Ledger</span>
  <span class="ds-step"><span class="b">4</span>Convert CSV</span>
  <span class="ds-step"><span class="b">5</span>Review &amp; Download</span>
</div>""",
    ),
    dict(
        name="App entry card", group="Patterns", frame="dual",
        subtitle="Home menu tile — icon, name, tabs, arrow",
        notes="""The home tile shows the solution's icon, name and its tab names, so people
can jump straight to the sub-page they meant.

Category sections use the group accents (`--group-1` … `--group-5`) on the
left rule — categories aren't statuses, so they never borrow status colors.

The arrow slides on hover; on touch the whole card is the target.""",
        html="""
<div class="dsx-stack">
  <div class="category-title cat-c1">Cheil Track</div>
  <a class="app-entry-card" href="#">
    <span class="app-entry-icon">💳</span>
    <span class="app-entry-text">
      <span class="app-entry-name">AMEX Expense Assistant</span>
      <span class="app-entry-tabs">Receipt Ledger · Convert · Review · History</span>
    </span>
    <span class="app-entry-arrow">›</span>
  </a>
  <a class="app-entry-card" href="#">
    <span class="app-entry-icon">🤝</span>
    <span class="app-entry-text">
      <span class="app-entry-name">Deal Desk</span>
      <span class="app-entry-tabs">Contracts · People · Vendors · Home</span>
    </span>
    <span class="app-entry-arrow">›</span>
  </a>
</div>""",
    ),
    dict(
        name="Nav bar", group="Patterns", frame="dual",
        subtitle="One line, brand ellipsis, never wraps",
        notes="""The nav is **one line, always**. `.nav-brand` ellipsises rather than
wrapping — a two-line nav on a phone spends the chrome budget before the page
has said anything.

It's sticky with a blur backdrop. Anything scoped to the app (tab bar, profile
switcher) sits below it, pinned to the actual nav height rather than a
hardcoded offset, because that height changes.""",
        html="""
<nav class="dsx-nav">
  <span class="nav-brand">💳 Cheil AMEX Expense Assistant</span>
  <span class="nav-user">jongha.kang · <a class="nav-back" href="#">← Home</a></span>
</nav>""",
    ),

    # ------------------------------------------------------------------ Mobile
    dict(
        name="Table → cards", group="Mobile", frame="phone",
        subtitle="Transactional rows become cards at ≤768px",
        notes="""Transactional tables (rows people act on) transform into cards below
768px. Each `td` carries `data-label` and the CSS renders it as a
label/value line.

**Cap the card at ~6 visible fields.** Deeper edits belong in the detail panel,
which goes full-width on mobile. A card that reproduces all 14 columns is just
a table with extra steps.

Reference tables — ones you read rather than act on — keep their table shape
inside an `overflow-x:auto` wrapper instead. Either way **the page body never
scrolls horizontally**.""",
        html="""
<table class="wf-cardtable">
  <tr>
    <td data-label="Date">2026-07-15</td>
    <td data-label="Merchant">JANG TU RESTAURANT</td>
    <td data-label="Final">$157.98</td>
    <td data-label="Card">AMEX</td>
    <td data-label="Status"><span class="ds-chip prog">⏳ IN PROGRESS</span></td>
  </tr>
  <tr>
    <td data-label="Date">2026-07-15</td>
    <td data-label="Merchant">STARBUCKS Store #5217</td>
    <td data-label="Final">$15.85</td>
    <td data-label="Card">Cash</td>
    <td data-label="Status"><span class="ds-chip open">OPEN</span></td>
  </tr>
</table>""",
    ),
    dict(
        name="Bottom sheet", group="Mobile", frame="phone",
        subtitle="Anchored popovers become sheets at ≤768px",
        notes="""Any anchored menu — filter popover, tooltip, card picker — clips off-screen
on a narrow viewport. At ≤768px it stops being anchored and becomes a fixed
sheet in the thumb zone.

Padding respects `env(safe-area-inset-bottom)`. The sheet gets
`--shadow-lg` because it genuinely floats above the page, unlike a card.

Same click-to-toggle behavior as the desktop popover — don't invent a
drag-to-dismiss gesture that nothing else in the app uses.""",
        html="""
<div class="dsx-stage">
  <div class="wf-sheet">
    <div class="wf-sheet-title">Filters</div>
    <label class="wf-field"><span class="wf-label">Status</span>
      <select class="wf-input"><option>All</option></select></label>
    <label class="wf-field"><span class="wf-label">Card</span>
      <select class="wf-input"><option>All</option><option>AMEX</option><option>Cash</option></select></label>
    <div class="dsx-row" style="margin-top:12px">
      <button class="btn btn-secondary">↺ Reset</button>
      <button class="btn btn-primary" style="flex:1">Apply</button>
    </div>
  </div>
</div>""",
    ),
    dict(
        name="Filter bar", group="Mobile", frame="phone",
        subtitle="Strict 2-column grid, search leads full-width",
        notes="""Search takes the full first row. Every other field stacks its label over a
full-width control in a strict 2-column grid.

Watch out for `.fb-field{flex-wrap:wrap}` on the desktop rule — it unfolds row
fields into a ragged stack at narrow widths and quietly breaks the grid.

Every control here is ≥44px tall and 16px type, which is what stops iOS from
zooming on focus.""",
        html="""
<div class="dsx-fbar">
  <label class="wf-field dsx-full"><span class="wf-label">Search</span>
    <input class="wf-input" placeholder="Search merchant…"></label>
  <label class="wf-field"><span class="wf-label">Period</span>
    <select class="wf-input"><option>All time</option></select></label>
  <label class="wf-field"><span class="wf-label">Status</span>
    <select class="wf-input"><option>All</option></select></label>
  <label class="wf-field"><span class="wf-label">Card</span>
    <select class="wf-input"><option>All</option></select></label>
  <label class="wf-field"><span class="wf-label">Usage</span>
    <select class="wf-input"><option>All</option></select></label>
</div>""",
    ),
]
