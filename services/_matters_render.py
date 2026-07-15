"""Matter Tracker page — ported from labs/matter-tracker static UI.

Uses the global design-system tokens (dark + light themes) via alias vars.
"""

PAGE_CSS = """
:root{
  --bg:var(--bg-deep); --muted:var(--text-muted); --dim:var(--text-dim);
  --me:var(--danger); --joint:var(--warn); --them:var(--info); --good:var(--success);
  --radius:var(--radius-lg);
}
*{box-sizing:border-box;margin:0;padding:0}
.mt-wrap{font-size:14px;padding:24px 20px 80px;max-width:1200px;margin:0 auto}
.mt-wrap h1{font-size:1.25rem;font-weight:800;letter-spacing:-.02em}
.sub{color:var(--muted);font-size:.78rem;margin:4px 0 20px}
/* KPI */
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(140px,1fr));gap:10px;margin-bottom:22px}
.kpi{background:var(--surface-2);border:1px solid var(--border);border-radius:var(--radius);padding:14px 16px;cursor:default}
.kpi .num{font-size:1.7rem;font-weight:800;line-height:1.2;font-variant-numeric:tabular-nums}
.kpi .lbl{font-size:.68rem;font-weight:700;letter-spacing:.07em;text-transform:uppercase;color:var(--muted);margin-top:3px}
.kpi.red .num{color:var(--me)} .kpi.amber .num{color:var(--joint)}
.kpi.blue .num{color:var(--them)} .kpi.green .num{color:var(--good)}
/* Drafts */
.drafts{background:rgba(251,191,36,.07);border:1px solid rgba(251,191,36,.3);border-radius:var(--radius);padding:12px 16px;margin-bottom:22px}
.drafts h2{font-size:.8rem;color:var(--joint);margin-bottom:8px}
.drafts li{list-style:none;font-size:.82rem;color:var(--text);padding:3px 0;display:flex;gap:10px}
.drafts li .d{color:var(--muted);font-size:.74rem;white-space:nowrap}
/* Sections */
.sect{margin-bottom:24px}
.sect h2{font-size:.78rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);
  margin-bottom:10px;display:flex;align-items:center;gap:8px}
.sect h2::before{content:"";width:4px;height:1em;border-radius:99px;flex-shrink:0}
.sect.s-now h2::before{background:var(--me)}
.sect h2 .cnt{color:var(--dim);font-weight:600}
/* ⚡ Needs You Now — the hero band */
.sect.s-now{background:var(--surface);border:1px solid var(--border);border-radius:var(--radius);
  padding:14px 16px 18px;margin-bottom:26px}
.sect.s-now h2{margin-bottom:12px}
.allclear{color:var(--good);font-size:.9rem;font-weight:700;padding:22px;text-align:center;
  background:rgba(52,211,153,.06);border-radius:var(--radius)}
/* Collapsed reference tiers */
details.sect{margin-bottom:14px}
details.sect>summary{font-size:.78rem;font-weight:800;letter-spacing:.06em;text-transform:uppercase;
  color:var(--muted);cursor:pointer;padding:8px 0;list-style:none;display:flex;align-items:center;gap:8px}
details.sect>summary::-webkit-details-marker{display:none}
details.sect>summary::before{content:"▸";color:var(--dim);font-size:.9rem}
details.sect[open]>summary::before{content:"▾"}
details.sect .grid2{margin-top:10px}
.sect .cnt{color:var(--dim);font-weight:600}
/* SLA clock chip */
.clk{font-size:.68rem;font-weight:700;border-radius:99px;padding:2px 9px;white-space:nowrap;
  background:var(--surface-3);color:var(--muted)}
.clk.overdue{background:rgba(248,113,113,.16);color:var(--me)}
.card.overdue{border-left-color:var(--me);box-shadow:inset 3px 0 0 var(--me)}
/* 🤖 AI auto-applied marker */
.ai-mark{font-size:.72rem;opacity:.85;cursor:help}
select.sm.ai-set{border-color:var(--them);box-shadow:0 0 0 1px rgba(56,189,248,.4)}
/* 🔎 deep recheck */
.rc-row{display:flex;align-items:center;gap:8px;margin-top:10px}
.rc-btn{border:1px solid var(--border-bright);background:var(--surface);color:var(--text);
  font-size:.74rem;font-weight:700;border-radius:7px;padding:4px 10px;cursor:pointer}
.rc-btn:hover{border-color:var(--them);color:var(--them)}
.rc-input{flex:1;min-width:120px;border:1px solid var(--border-bright);border-radius:7px;
  padding:4px 9px;font-size:.74rem;background:var(--surface);color:var(--text)}
.rc-input::placeholder{color:var(--dim)}
.rc-input:focus{outline:none;border-color:var(--them)}
.recheck:empty{display:none}
.recheck{margin-top:8px;font-size:.76rem;line-height:1.7}
.rc-load{color:var(--muted)} .rc-err{color:var(--me)}
.rc-res{color:var(--text)} .rc-res b{color:var(--them)}
.rc-sugg{margin-top:4px;color:var(--muted)}
.rc-chip{border:1px dashed var(--border-bright);background:transparent;color:var(--them);
  font-size:.72rem;border-radius:99px;padding:2px 9px;cursor:pointer;margin:2px}
.rc-chip:hover{background:rgba(56,189,248,.12)}
.rc-more{margin-top:4px;color:var(--dim);font-size:.72rem}
.rc-more a{color:var(--them);cursor:pointer;text-decoration:underline;margin:0 2px}
.grid2{display:grid;grid-template-columns:repeat(auto-fill,minmax(460px,1fr));gap:12px}
@media(max-width:1000px){.grid2{grid-template-columns:1fr}}
.card{background:var(--surface-2);border:1px solid var(--border);border-left:4px solid var(--border-bright);
  border-radius:var(--radius);padding:14px 16px;position:relative}
.card.b-나{border-left-color:var(--me)} .card.b-공동{border-left-color:var(--joint)}
.card.b-상대{border-left-color:var(--them)} .card.done{opacity:.5}
.row1{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap;padding-right:24px}
.title-input{font-size:.95rem;font-weight:700;border:none;background:transparent;flex:1;min-width:180px;
  color:var(--text);padding:2px 4px;border-radius:6px}
.title-input:hover,.title-input:focus{background:var(--surface-3);outline:none}
select.sm{border:1px solid var(--border-bright);border-radius:6px;padding:3px 6px;font-size:.74rem;
  background:var(--surface);color:var(--text);cursor:pointer}
.stale-badge{background:rgba(248,113,113,.15);color:var(--me);font-size:.68rem;font-weight:700;
  border-radius:99px;padding:2px 9px;white-space:nowrap}
.fgrid{display:grid;grid-template-columns:76px 1fr;gap:4px 8px;align-items:start}
.fgrid label{color:var(--dim);font-size:.7rem;padding-top:6px;text-transform:uppercase;letter-spacing:.04em;font-weight:700}
.fgrid input[type=text],.fgrid textarea,.fgrid input[type=date]{width:100%;border:1px solid transparent;
  background:transparent;padding:4px 6px;border-radius:6px;font-size:.82rem;font-family:inherit;
  color:var(--text);resize:vertical}
.fgrid input:hover,.fgrid textarea:hover{background:var(--surface-3)}
.fgrid input:focus,.fgrid textarea:focus{background:var(--surface);border-color:var(--border-bright);outline:none}
.next-action input{font-weight:var(--fw-semibold)}
.lastrow{display:flex;align-items:center;gap:8px}
.ago{color:var(--muted);font-size:.72rem;white-space:nowrap}
.touch-btn{border:1px solid var(--border-bright);background:var(--surface);border-radius:6px;padding:3px 9px;
  font-size:.7rem;cursor:pointer;color:var(--text);white-space:nowrap}
.touch-btn:hover{border-color:var(--accent);color:var(--accent)}
.del{position:absolute;top:10px;right:10px;border:none;background:none;color:var(--dim);cursor:pointer;font-size:.95rem;padding:3px}
.del:hover{color:var(--me)}
.add-btn{width:100%;padding:12px;border:2px dashed var(--border-bright);border-radius:var(--radius);
  background:none;color:var(--muted);font-size:.85rem;cursor:pointer;margin-top:4px}
.add-btn:hover{border-color:var(--accent);color:var(--accent)}
/* Threads on a card */
.threads{margin-top:10px;border-top:1px solid var(--border);padding-top:8px;display:flex;flex-direction:column;gap:5px}
.thread{display:flex;align-items:baseline;gap:7px;font-size:.76rem}
.thread a{color:var(--accent);text-decoration:none;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1}
.thread a:hover{text-decoration:underline}
.thread .who{color:var(--muted);white-space:nowrap;font-size:.7rem}
.thread.inbound .who{color:var(--them)}
.thread.side{margin-left:20px;opacity:.88}
.thread-more{color:var(--dim);font-size:.72rem}
/* latest communication line — leads the card, click opens the mail */
.latest-comm{margin:8px 0 2px;padding:8px 11px;background:var(--surface);border:1px solid var(--border);
  border-radius:8px;font-size:.78rem;color:var(--muted);overflow:hidden;text-overflow:ellipsis;
  white-space:nowrap}
.latest-comm:hover{border-color:var(--accent)}
.latest-comm b{color:var(--text)}
/* people role chips */
.people-cell{display:flex;flex-direction:column;gap:5px}
.pchips{display:flex;flex-wrap:wrap;gap:5px}
.pchip{display:inline-flex;align-items:baseline;gap:5px;background:var(--surface);border:1px solid var(--border);
  border-radius:999px;padding:2px 9px;font-size:.73rem;color:var(--text)}
.pchip i{font-style:normal;color:var(--muted);font-size:.67rem}
.pchip em{font-style:normal;color:#f5b642;font-size:.65rem;font-weight:700}
.pchip.pic{border-color:rgba(245,182,66,.5)}
.people-cell input{font-size:.72rem;color:var(--muted)}
/* top bar */
.topbar{display:flex;align-items:center;justify-content:space-between;gap:12px;flex-wrap:wrap;margin-bottom:4px}
.scan-btn{border:1px solid var(--accent);background:var(--accent-glow);color:var(--accent);border-radius:8px;
  padding:7px 14px;font-size:.82rem;font-weight:700;cursor:pointer}
.scan-btn:hover{background:rgba(56,189,248,.2)}
.scan-btn:disabled{opacity:.5;cursor:default}
/* new-matter candidates */
.cands{background:rgba(56,189,248,.06);border:1px solid rgba(56,189,248,.25);border-radius:var(--radius);
  padding:12px 16px;margin-bottom:22px}
.cands h2{font-size:.8rem;color:var(--accent);margin-bottom:8px}
.cands li{list-style:none;font-size:.82rem;padding:3px 0;color:var(--text)}
.cands .who{color:var(--them);font-size:.72rem;margin-right:6px}
/* AI briefing + suggestions (L3) */
.briefing{background:linear-gradient(135deg,rgba(56,189,248,.09),rgba(52,211,153,.06));
  border:1px solid rgba(56,189,248,.3);border-radius:var(--radius);padding:12px 16px;margin-bottom:22px}
.briefing h2{font-size:.8rem;color:var(--accent);margin-bottom:6px}
.briefing p{font-size:.86rem;line-height:1.55}
.briefing .when{color:var(--muted);font-size:.7rem;margin-left:8px;font-weight:400}
.suggs{margin-top:10px;border-top:1px dashed var(--border-bright);padding-top:8px;display:flex;flex-direction:column;gap:6px}
.sugg{display:flex;align-items:center;gap:8px;font-size:.78rem;flex-wrap:wrap;
  background:rgba(56,189,248,.07);border:1px solid rgba(56,189,248,.2);border-radius:8px;padding:6px 10px}
.sugg .tag{font-size:.64rem;font-weight:800;letter-spacing:.05em;color:var(--accent);text-transform:uppercase;white-space:nowrap}
.sugg .val{font-weight:700}
.sugg .why{color:var(--muted);font-size:.72rem;flex:1;min-width:120px}
.sugg button{border:1px solid var(--border-bright);background:var(--surface);color:var(--text);
  border-radius:6px;padding:2px 9px;font-size:.72rem;cursor:pointer;white-space:nowrap}
.sugg button.ok{border-color:var(--good);color:var(--good)}
.sugg button.ok:hover{background:rgba(52,211,153,.15)}
.sugg button:not(.ok):hover{border-color:var(--me);color:var(--me)}
.nm-sugg li{list-style:none;display:flex;align-items:center;gap:10px;padding:5px 0;font-size:.82rem;flex-wrap:wrap}
.nm-sugg .why{color:var(--muted);font-size:.72rem}
/* bridge map (structure tree) */
.struct-toggle{border:1px solid var(--border-bright);background:var(--surface);color:var(--muted);
  border-radius:6px;padding:3px 9px;font-size:.7rem;cursor:pointer;white-space:nowrap}
.struct-toggle:hover{border-color:var(--accent);color:var(--accent)}
.struct{margin-top:10px;border-top:1px dashed var(--border-bright);padding-top:10px;
  display:flex;align-items:stretch;gap:0;flex-wrap:wrap}
.snode{background:var(--surface-3);border:1px solid var(--border-bright);border-radius:10px;
  padding:8px 11px;flex:1;min-width:130px;font-size:.76rem;position:relative}
.snode .org{font-size:.66rem;font-weight:800;letter-spacing:.05em;text-transform:uppercase;color:var(--muted)}
.snode .pic{font-weight:800;font-size:.84rem;margin-top:2px}
.snode .pic .star{color:var(--joint);font-size:.7rem}
.snode .mem{color:var(--muted);font-size:.7rem;margin-top:1px}
.snode .st{margin-top:5px;color:var(--text);font-size:.72rem;line-height:1.4}
.snode.me{background:rgba(56,189,248,.1);border-color:rgba(56,189,248,.45)}
.snode.me .org{color:var(--accent)}
.snode.ball{border-color:var(--me);box-shadow:0 0 0 1px var(--me)}
.snode .ball-chip{position:absolute;top:-9px;right:8px;background:var(--me);color:#fff;
  font-size:.62rem;font-weight:800;border-radius:99px;padding:1px 8px}
.snode .next{margin-top:6px;background:rgba(56,189,248,.12);border-radius:6px;padding:4px 7px;
  font-size:.7rem;color:var(--accent);font-weight:700;line-height:1.35}
.slink{display:flex;align-items:center;color:var(--dim);font-size:.9rem;padding:0 4px;align-self:center}
@media(max-width:640px){.struct{flex-direction:column}.slink{transform:rotate(90deg);align-self:flex-start;margin-left:20px}}
.save-dot{position:fixed;bottom:18px;right:20px;font-size:.72rem;color:var(--muted);opacity:0;transition:opacity .3s}
.save-dot.show{opacity:1}
/* ---- to-do list rows ---- */
.colhead,.lrow{display:grid;grid-template-columns:14px minmax(180px,1.05fr) 64px minmax(160px,1.25fr) minmax(140px,1fr) 64px 30px;
  align-items:center;gap:12px}
.colhead{padding:0 12px 6px;font-size:.62rem;color:var(--dim);text-transform:uppercase;letter-spacing:.06em}
.lrow{padding:10px 12px;border-bottom:1px solid var(--border);cursor:pointer;border-radius:8px}
.lrow:hover{background:var(--surface)}
.lrow.done{opacity:.45}
.ldot{width:9px;height:9px;border-radius:50%}
.ldot.overdue{background:var(--me);box-shadow:0 0 6px var(--me)}
.ldot.normal{background:#f5b642}
.ldot.low{background:var(--dim)}
.ltitle{font-weight:700;font-size:.88rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lrow:hover .ltitle{color:var(--accent)}
.lbadge{font-size:.68rem;font-weight:700;border-radius:999px;padding:2px 0;text-align:center;white-space:nowrap}
.lbadge.me{background:rgba(248,113,113,.12);color:var(--me);border:1px solid rgba(248,113,113,.35)}
.lbadge.them{background:rgba(74,222,128,.10);color:var(--them);border:1px solid rgba(74,222,128,.3)}
.lbadge.both{background:rgba(245,182,66,.1);color:#f5b642;border:1px solid rgba(245,182,66,.3)}
.lnext{font-size:.78rem;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lcomm{font-size:.72rem;color:var(--muted);overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.lclock{font-size:.7rem;color:var(--muted);text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
.lclock.over{color:var(--me);font-weight:700}
.ldone{border:1px solid var(--border);background:none;color:var(--dim);border-radius:6px;width:26px;height:24px;
  cursor:pointer;font-size:.7rem;opacity:0;transition:opacity .12s}
.lrow:hover .ldone,.lrow.done .ldone{opacity:1}
.ldone:hover{border-color:var(--them);color:var(--them)}
@media (max-width:760px){
  .colhead{display:none}
  .lrow{grid-template-columns:12px 1fr 56px 30px;row-gap:3px}
  .lnext{grid-column:2/5}
  .lcomm,.lclock{display:none}
}
/* ---- deep-dive panel (design A) ---- */
.poverlay{position:fixed;inset:0;background:rgba(5,8,13,.55);opacity:0;pointer-events:none;transition:opacity .18s;z-index:110}
.panel{position:fixed;top:0;right:0;bottom:0;width:min(620px,100%);background:var(--surface);z-index:120;
  border-left:1px solid var(--border-bright);transform:translateX(102%);transition:transform .2s ease;
  overflow-y:auto;padding:48px 28px 64px;box-shadow:-18px 0 42px rgba(0,0,0,.45)}
body.panel-open .poverlay{opacity:1;pointer-events:auto}
body.panel-open .panel{transform:none}
@media (prefers-reduced-motion:reduce){.panel,.poverlay{transition:none}}
.pclose{position:absolute;top:14px;right:18px;background:none;border:none;color:var(--muted);
  font-size:1.15rem;cursor:pointer;z-index:2}
.pclose:hover{color:var(--me)}
/* the full card renders inside the panel — flatten its chrome, breathe more */
.panel .card{background:none;border:none;border-left:none;padding:0}
.panel .row1{margin-bottom:18px}
.panel .fgrid{row-gap:14px}
.panel .latest-comm{margin:16px 0 8px;padding:12px 14px}
.panel .rc-row{margin-top:20px}
.panel .threads{margin-top:18px;padding-top:16px}
.panel .struct{margin-top:18px}
button,select,input,textarea{font-family:inherit}
:focus-visible{outline:2px solid var(--accent);outline-offset:1px}
"""

PAGE_BODY = """<div class="mt-wrap">
<div class="topbar">
  <h1>🧭 Matter Tracker</h1>
  <span style="display:flex;gap:8px">
    <button class="scan-btn" id="structBtn" onclick="refreshStructures()" title="AI가 사안별 관계도를 다시 그립니다">🌳 관계도 갱신</button>
    <button class="scan-btn" id="scanBtn" onclick="runScan()">↻ 지금 스캔</button>
  </span>
</div>
<div class="sub" id="sub">loading…</div>
<div class="briefing" id="briefing" hidden></div>
<div class="kpis" id="kpis"></div>
<div id="sections"></div>
<div id="addPanel">
  <button class="add-btn" onclick="toggleAdd()">＋ 새 사안 추가</button>
  <div class="cands nm-sugg" id="addBody" hidden style="margin-top:10px"></div>
</div>
<div class="save-dot" id="saveDot">✓ 저장됨</div>
<div class="poverlay" onclick="closePanel()"></div>
<aside class="panel" aria-label="사안 딥다이브">
  <button class="pclose" onclick="closePanel()" title="닫기 (Esc)">✕</button>
  <div id="panelBody"></div>
</aside>

<script>
const BALLS = ['나','공동','상대'];
const STATUSES = ['진행중','회신대기','보류','완료'];
const URGENCIES = [['urgent','🔴 긴급 (4h)'],['normal','🟡 보통 (24h)'],['low','⚪ 레퍼런스']];
let DATA = {matters:[]};

// hours on my plate → human chip; overdue reads loud.
function clockChip(att){
  if(!att || att.tier !== 'action') return '';
  const h = att.hours_on_plate;
  if(h === null || h === undefined) return '';
  const txt = h < 1 ? '방금' : h < 24 ? Math.round(h)+'h' : Math.floor(h/24)+'d';
  if(att.overdue){
    const over = att.sla_hours ? Math.round(h - att.sla_hours) : 0;
    return `<span class="clk overdue">⚠ ${over}h 초과</span>`;
  }
  return `<span class="clk">⏱ ${txt} 경과</span>`;
}

function esc(s){ return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'); }
function daysAgo(iso){
  if(!iso) return null;
  const d = new Date(iso + 'T00:00:00'); if(isNaN(d)) return null;
  return Math.floor((new Date().setHours(0,0,0,0) - d) / 86400000);
}

async function load(){
  const d = await (await fetch('/matters/api')).json();
  DATA = d;
  renderKpis(d.kpis); renderSections(d.matters);
  renderBriefing(d.briefing); renderAddPanel(); refreshPanel();
  const ls = d.last_scan;
  document.getElementById('sub').textContent =
    (ls ? `마지막 스캔: ${ls.finished_at} (${ls.source})${ls.changes_summary ? ' — ' + ls.changes_summary : ''}` : '스캔 이력 없음')
    + ` · 사안 ${d.matters.length}건`;
}

async function runScan(){
  const btn = document.getElementById('scanBtn');
  btn.disabled = true; btn.textContent = '스캔 중…';
  try {
    await (await fetch('/matters/api/scan', {method:'POST'})).json();
  } finally {
    btn.disabled = false; btn.textContent = '↻ 지금 스캔';
    load();
  }
}

function renderBriefing(b){
  const el = document.getElementById('briefing');
  if(!b || !b.text){ el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = `<h2>🤖 AI 브리핑<span class="when">${esc(b.created_at || '')}</span></h2><p>${esc(b.text)}</p>`;
}

function renderAddPanel(){
  const body = document.getElementById('addBody');
  if(body.hidden) return;               // closed — render on open
  const suggs = DATA.new_matter_suggestions || [];
  let html = '<h2>🤖 AI가 메일에서 감지한 사안 후보 ' + suggs.length + '건</h2>';
  if(suggs.length){
    html += '<ul>' + suggs.map(s => {
      let d = {}; try { d = JSON.parse(s.proposed_value); } catch(e){}
      const watch = (d.urgency === 'low') ? ' <span class="why">📡 모니터링</span>' : '';
      return `<li><b>${esc(d.title || '?')}</b>${watch}<span class="why">${esc(s.reason || '')}</span>
        <button class="touch-btn" onclick="resolveSugg(${s.id}, true)">＋ 사안으로 추가</button>
        <button class="touch-btn" onclick="resolveSugg(${s.id}, false)">무시</button></li>`;
    }).join('') + '</ul>';
  } else {
    html += '<div style="color:var(--muted);font-size:.8rem;padding:4px 0">후보가 없습니다 — ↻ 지금 스캔을 돌리면 AI가 메일에서 후보를 찾습니다.</div>';
  }
  const raw = DATA.last_candidates || [];
  if(raw.length){
    html += `<details style="margin-top:10px">
      <summary style="cursor:pointer;font-size:.78rem;color:var(--muted)">🔍 최근 스캔 원시 후보 ${raw.length}건 (AI 필터 전 — 참고용)</summary>
      <ul style="margin:6px 0 0;padding-left:18px;max-height:220px;overflow-y:auto">`
      + raw.map(s => `<li style="font-size:.75rem;color:var(--muted);padding:1px 0">${esc(s)}</li>`).join('')
      + '</ul></details>';
  }
  html += `<div style="display:flex;gap:8px;margin-top:12px">
    <input id="proposeQuery" type="text" placeholder="검색어로 제안받기: 제목 키워드 또는 from:주소..."
      style="flex:1;background:var(--surface);border:1px solid var(--border-bright);border-radius:8px;color:var(--text);padding:8px 10px;font-size:.82rem">
    <button class="touch-btn" id="proposeBtn" onclick="proposeFromQuery()">🔍 AI 제안</button></div>
  <div style="color:var(--dim);font-size:.7rem;margin-top:4px">메일함을 검색해 AI가 사안 카드를 만들어 후보에 올립니다 (약 1분)</div>
  <div style="display:flex;gap:8px;margin-top:10px">
    <input id="manualTitle" type="text" placeholder="직접 입력: 새 사안 제목..."
      style="flex:1;background:var(--surface);border:1px solid var(--border-bright);border-radius:8px;color:var(--text);padding:8px 10px;font-size:.82rem">
    <button class="touch-btn" onclick="addManual()">추가</button></div>`;
  body.innerHTML = html;
}

function toggleAdd(){
  const body = document.getElementById('addBody');
  body.hidden = !body.hidden;
  if(!body.hidden) renderAddPanel();
}

async function proposeFromQuery(){
  const q = document.getElementById('proposeQuery').value.trim();
  if(!q) return;
  const btn = document.getElementById('proposeBtn');
  btn.disabled = true; btn.textContent = '메일 검색 + AI 분석 중…';
  try {
    const r = await (await fetch('/matters/api/propose', {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({query: q})})).json();
    if(r.error){ alert(r.error); }
  } finally {
    await load();                       // refresh DATA with the new candidate
    const body = document.getElementById('addBody');
    body.hidden = false; renderAddPanel();
  }
}

async function addManual(){
  const title = document.getElementById('manualTitle').value.trim();
  if(!title) return;
  await fetch('/matters/api/matters', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({title: title, ball: '나', status: '진행중'})});
  load();
}

async function refreshStructures(){
  const btn = document.getElementById('structBtn');
  btn.disabled = true; btn.textContent = '관계도 생성 중…';
  try {
    const r = await (await fetch('/matters/api/structures', {method:'POST'})).json();
    if(r.error) alert('관계도 생성 실패: ' + r.error);
  } finally {
    btn.disabled = false; btn.textContent = '🌳 관계도 갱신';
    load();
  }
}

async function resolveSugg(id, accept){
  await fetch('/matters/api/suggestions/' + id, {method:'POST',
    headers:{'Content-Type':'application/json'},
    body: JSON.stringify({action: accept ? 'accept' : 'dismiss'})});
  load();
}

function renderKpis(k){
  document.getElementById('kpis').innerHTML = [
    ['red',   k.needs_now,  '지금 내 액션'],
    ['amber', k.overdue,    'SLA 초과'],
    ['amber', k.drafts,     '미발송 초안'],
    ['blue',  k.waiting,    '상대 대기'],
    ['green', k.reference,  '레퍼런스'],
  ].map(([c,n,l]) => `<div class="kpi ${c}"><div class="num">${n}</div><div class="lbl">${l}</div></div>`).join('');
}


function card(m){
  const att = m.att || {};
  const ago = daysAgo(m.last_contact);
  const ai = new Set(m.ai_updated || []);
  const mark = field => ai.has(field) ? ' <span class="ai-mark" title="AI가 지난 스캔에서 갱신함">🤖</span>' : '';
  const f = (label, field, val, opts={}) => `
    <label>${label}${mark(field)}</label>
    ${opts.area
      ? `<textarea rows="${opts.rows||1}" data-f="${field}" data-id="${m.id}">${esc(val)}</textarea>`
      : `<input type="${opts.type||'text'}" value="${esc(val)}" data-f="${field}" data-id="${m.id}">`}`;
  return `<div class="card b-${m.ball}${m.status==='완료' ? ' done' : ''}${att.overdue ? ' overdue' : ''}">
    <button class="del" title="보관 (archive)" onclick="archive(${m.id})">✕</button>
    <div class="row1">
      <input class="title-input" value="${esc(m.title)}" data-f="title" data-id="${m.id}">
      ${clockChip(att)}
      <select class="sm${ai.has('status')?' ai-set':''}" data-f="status" data-id="${m.id}">${STATUSES.map(s=>`<option${s===m.status?' selected':''}>${s}</option>`).join('')}</select>
      <select class="sm${ai.has('ball')?' ai-set':''}" data-f="ball" data-id="${m.id}">${BALLS.map(b=>`<option${b===m.ball?' selected':''}>${b}</option>`).join('')}</select>
      <select class="sm" data-f="urgency" data-id="${m.id}" title="긴급도 (SLA)">${URGENCIES.map(([v,l])=>`<option value="${v}"${v===(m.urgency||'normal')?' selected':''}>${l}</option>`).join('')}</select>
    </div>
    ${latestComm(m.threads)}
    <div class="fgrid">
      ${f('Waiting','waiting',m.waiting)}
      <label>Next${mark('next_action')}</label><span class="next-action"><input type="text" value="${esc(m.next_action)}" data-f="next_action" data-id="${m.id}"></span>
      <label>People${mark('people')}</label>
      <span class="people-cell">${peopleChips(m)}<input type="text" value="${esc(m.people)}" data-f="people" data-id="${m.id}"></span>
      <label>Last${mark('last_contact')}</label>
      <span class="lastrow">
        <input type="date" value="${esc(m.last_contact)}" data-f="last_contact" data-id="${m.id}" style="width:150px">
        <button class="touch-btn" onclick="touch(${m.id})">↻ 오늘</button>
        ${ago !== null ? `<span class="ago">${ago === 0 ? '오늘' : ago + '일 전'}</span>` : ''}
      </span>
      ${f('Notes','notes',m.notes,{area:true,rows:2})}
    </div>
    <div class="rc-row">
      <button class="rc-btn" onclick="recheckMatter(${m.id},3)" title="아래 칸에 사람/키워드를 넣으면 그 기준으로, 비우면 People 전원+제목으로 최근 메일(내 발신 포함)을 다시 훑어 재판단합니다">🔎 재점검</button>
      <button class="rc-btn" onclick="splitMatter(${m.id})" title="여러 건이 한 사안에 뭉쳐 있으면 AI가 분리안을 제안합니다 (실행 전 확인)">✂ 분리</button>
      <input class="rc-input" id="rcq-${m.id}" placeholder="사람·키워드 (예: Ram, SOW) — 비우면 People 전원"
        onkeydown="if(event.key==='Enter'){event.preventDefault();recheckMatter(${m.id},3);}">
    </div>
    <div class="recheck" id="rc-${m.id}"></div>
    ${structTree(m)}
    ${threadList(m.threads)}
  </div>`;
}

const SPLIT_PLANS = {};

async function splitMatter(id){
  const box = document.getElementById('rc-' + id);
  if(box) box.innerHTML = '<span class="rc-load">✂ 분리안 분석 중… (AI가 스레드를 검토합니다)</span>';
  let r;
  try {
    r = await (await fetch('/matters/api/matters/' + id + '/split', {method:'POST',
      headers:{'Content-Type':'application/json'}, body:'{}'})).json();
  } catch(e){ if(box) box.innerHTML = '<span class="rc-err">⚠ 요청 실패</span>'; return; }
  if(!box) return;
  if(r.error){ box.innerHTML = `<span class="rc-err">⚠ ${esc(r.error)}</span>`; return; }
  if(!r.split || !r.split.length){
    box.innerHTML = '<div class="rc-res">✓ 하나의 사안으로 판단됨 — 분리할 항목이 없습니다</div>';
    return;
  }
  SPLIT_PLANS[id] = r;
  const items = r.split.map(it =>
    `<li><b>${esc(it.title)}</b> <span class="why">${esc(it.reason)}</span>
      <span class="why">· 스레드 ${it.thread_ids.length}개 · ${esc(it.ball)}/${esc(it.urgency)}</span></li>`).join('');
  const keep = r.keep && r.keep.title
    ? `<div class="why" style="margin-top:4px">원 사안 제목 → «${esc(r.keep.title)}»</div>` : '';
  box.innerHTML = `<div class="rc-res">✂ ${r.split.length}개 사안으로 분리 제안:
    <ul style="margin:6px 0 0;padding-left:18px">${items}</ul>${keep}
    <div style="margin-top:8px;display:flex;gap:8px">
      <button class="touch-btn" onclick="applySplit(${id})">✂ 분리 실행</button>
      <button class="touch-btn" onclick="document.getElementById('rc-${id}').innerHTML=''">닫기</button>
    </div></div>`;
}

async function applySplit(id){
  const plan = SPLIT_PLANS[id];
  if(!plan) return;
  const box = document.getElementById('rc-' + id);
  if(box) box.innerHTML = '<span class="rc-load">분리 적용 중…</span>';
  try {
    const r = await (await fetch('/matters/api/matters/' + id + '/split_apply', {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify(plan)})).json();
    if(!r.ok){ if(box) box.innerHTML = `<span class="rc-err">⚠ ${esc(r.error || '실패')}</span>`; return; }
  } catch(e){ if(box) box.innerHTML = '<span class="rc-err">⚠ 요청 실패</span>'; return; }
  delete SPLIT_PLANS[id];
  load();
}

async function recheckMatter(id, days){
  const box = document.getElementById('rc-'+id);
  const inp = document.getElementById('rcq-'+id);
  const terms = inp ? inp.value.trim() : '';
  const scope = terms ? `"${esc(terms)}"` : 'People 전원';
  if(box) box.innerHTML = `<span class="rc-load">🔎 재점검 중… (최근 ${days}일 · ${scope})</span>`;
  let r;
  try {
    r = await (await fetch('/matters/api/matters/'+id+'/recheck',{method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({days, terms})})).json();
  } catch(e){ if(box) box.innerHTML = '<span class="rc-err">⚠ 요청 실패</span>'; return; }
  if(!box) return;
  if(r.error){ box.innerHTML = `<span class="rc-err">⚠ ${esc(r.error)}</span>`; return; }
  let html = `<div class="rc-res">✓ 새 스레드 ${r.found}개 · ${r.threads_total}개 검토${r.scoped ? ' · 지정 기준' : ''}`;
  html += (r.applied && r.applied.length)
    ? ' · 갱신: ' + r.applied.map(a=>`<b>${esc(a.field)}→${esc(a.value)}</b>`).join(', ')
    : ' · 변경 없음';
  html += '</div>';
  if(r.suggested_queries && r.suggested_queries.length)
    html += '<div class="rc-sugg">🔑 검색어 제안: ' + r.suggested_queries.map(q=>
      `<button class="rc-chip" onclick="addQuery(${id},this.dataset.q,this)" data-q="${esc(q)}">＋ ${esc(q)}</button>`).join(' ') + '</div>';
  html += `<div class="rc-more">더 넓게: <a onclick="recheckMatter(${id},7)">7일</a> · <a onclick="recheckMatter(${id},30)">30일</a>`
        + (r.applied && r.applied.length ? ` · <a onclick="load()">🔄 반영 보기</a>` : '') + '</div>';
  box.innerHTML = html;
}

async function addQuery(id, q, btn){
  const m = DATA.matters.find(x=>x.id===id); if(!m) return;
  const qs = (m.search_queries||[]).concat([q]);
  await fetch('/matters/api/matters/'+id,{method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify({search_queries: qs})});
  m.search_queries = qs;
  btn.disabled = true; btn.style.opacity = .4; btn.textContent = '✓ '+q;
}

function structTree(m){
  if(!m.structure) return '';
  let s = {}; try { s = JSON.parse(m.structure); } catch(e){ return ''; }
  if(!s.sides || !s.sides.length) return '';
  const ball = s.ball || '';
  const nextWho = (s.next_step || {}).who || '';
  const node = (title, pic, members, state, isMe, holdsBall, next) => `
    <div class="snode${isMe ? ' me' : ''}${holdsBall ? ' ball' : ''}">
      ${holdsBall ? '<span class="ball-chip">⚑ 공</span>' : ''}
      <div class="org">${esc(title)}</div>
      ${pic ? `<div class="pic">${esc(pic)} <span class="star">★PIC</span></div>` : ''}
      ${members && members.length ? `<div class="mem">+ ${esc(members.join(', '))}</div>` : ''}
      ${state ? `<div class="st">${esc(state)}</div>` : ''}
      ${next ? `<div class="next">▶ ${esc(next)}</div>` : ''}
    </div>`;
  const nextFor = who => (s.next_step && (s.next_step.who === who ||
      (who === '나' && ['나','me','Jongha'].includes(s.next_step.who))))
      ? s.next_step.what : '';
  const meNext = (ball === 'me') ? (s.next_step || {}).what : nextFor('나');
  const meNode = node('나 · 브릿지', '', [], (s.me || {}).role || '', true,
                      ball === 'me', meNext);
  const sideNode = sd => node(sd.label, sd.pic, sd.members, sd.state, false,
                              ball === sd.label,
                              ball === sd.label ? (s.next_step || {}).what : '');
  const arrow = '<span class="slink">⟷</span>';
  const sides = s.sides;
  let inner;
  if(sides.length === 1){
    inner = meNode + arrow + sideNode(sides[0]);
  } else {
    inner = sideNode(sides[0]) + arrow + meNode + arrow + sideNode(sides[1]);
    for(let i = 2; i < sides.length; i++) inner += arrow + sideNode(sides[i]);
  }
  return `<div class="struct">${inner}</div>`;
}

// Per-matter field suggestions are auto-applied now (no manual 반영 gate); the
// card badges AI-touched fields with 🤖 instead. new_matter proposals still get
// an explicit accept/dismiss in the add panel (renderAddPanel).

const ME_EMAIL = 'jongha.kang@cheil.com';

async function openMail(eid){
  try {
    const r = await (await fetch('/matters/api/open_mail', {method:'POST',
      headers:{'Content-Type':'application/json'}, body: JSON.stringify({entryid: eid})})).json();
    if(!r.ok) alert('Outlook 열기 실패: ' + (r.error || ''));
  } catch(e){ alert('요청 실패 — 서버/Outlook 상태를 확인하세요'); }
}

function threadWho(t){
  return (t.last_sender || '').toLowerCase() !== ME_EMAIL
    ? (t.last_sender || '').split('@')[0] : '나';
}

// Mirror of the server-side _norm_subject: peel RE:/FW:/[EXTERNAL EMAIL] shells.
function normSubj(s){
  s = (s || '').trim(); let prev = null;
  const re = /^\s*((re|fw|fwd|회신|전달)\s*:|\[external\s*email\]|\[외부\s*메일\])\s*/i;
  while (s !== prev){ prev = s; s = s.replace(re, '').trim(); }
  return s;
}

// Latest communication across every attached thread: who · when — what.
// Clicking opens that mail in desktop Outlook (link carries the newest
// message's EntryID since the collector tracks it per conversation).
function latestComm(threads){
  if(!threads || !threads.length) return '';
  const t = threads.slice().sort((a,b)=>(b.last_message_at||'').localeCompare(a.last_message_at||''))[0];
  const when = (t.last_message_at || '').slice(5, 16).replace('T', ' ');
  const snip = (t.snippet || '').slice(0, 140);
  const eid = (t.outlook_link || '').startsWith('outlook:') ? t.outlook_link.slice(8) : '';
  const open = eid ? ` onclick="openMail('${eid}')" style="cursor:pointer"` : '';
  return `<div class="latest-comm"${open} title="${esc(t.subject)}${eid ? ' — 클릭하면 Outlook에서 열립니다' : ''}">📨 <b>${esc(threadWho(t))}</b> · ${when} — ${esc(snip)}</div>`;
}

// People as per-person role chips: roles come from the bridge map (structure
// sides — PIC vs member per org); people-field entries outside the map fall
// back to their (소속) annotation. The raw input below stays editable.
function peopleChips(m){
  let s = {};
  try { s = JSON.parse(m.structure || '{}'); } catch(e){}
  const chips = [], seen = [];
  (s.sides || []).forEach(side => {
    if(side.pic){ chips.push({name: side.pic, role: side.label || '', pic: true}); seen.push(side.pic.toLowerCase()); }
    (side.members || []).forEach(mb => { chips.push({name: mb, role: side.label || '', pic: false}); seen.push(mb.toLowerCase()); });
  });
  (m.people || '').split(',').map(p => p.trim()).filter(Boolean).forEach(p => {
    const mm = p.match(/^(.*?)\((.*?)\)\s*$/);
    const nm = (mm ? mm[1] : p).trim();
    const lo = nm.toLowerCase();
    if(seen.some(sn => lo.includes(sn) || sn.includes(lo))) return;
    chips.push({name: nm, role: mm ? mm[2] : '', pic: false});
  });
  if(!chips.length) return '';
  return `<div class="pchips">` + chips.map(c =>
    `<span class="pchip${c.pic ? ' pic' : ''}">${esc(c.name)}${c.pic ? ' <em>★PIC</em>' : ''}${c.role ? `<i>${esc(c.role)}</i>` : ''}</span>`
  ).join('') + '</div>';
}

// Threads grouped into conversation families: the direct thread as parent and
// forks that spawned separate conversations (my FW to a new person, split
// RE: chains) indented under it as ↳ side threads.
function threadList(threads){
  if(!threads || !threads.length) return '';
  const fams = {};
  threads.forEach(t => {
    const k = normSubj(t.subject).toLowerCase() || t.id;
    (fams[k] = fams[k] || []).push(t);
  });
  const famList = Object.values(fams).map(list => {
    list.sort((a,b) => a.subject.length - b.subject.length);  // fewest shells = the direct thread
    const [main, ...side] = list;
    side.sort((a,b)=>(b.last_message_at||'').localeCompare(a.last_message_at||''));
    const latest = list.reduce((mx,t)=> (t.last_message_at||'') > mx ? t.last_message_at : mx, '');
    return {main, side, latest};
  }).sort((a,b)=> b.latest.localeCompare(a.latest));

  const row = (t, child) => {
    const inbound = (t.last_sender || '').toLowerCase() !== ME_EMAIL;
    const when = (t.last_message_at || '').slice(5, 10);
    const eid = (t.outlook_link || '').startsWith('outlook:') ? t.outlook_link.slice(8) : '';
    const link = eid
      ? `<a href="#" onclick="openMail('${eid}');return false" title="${esc(t.subject)} — 데스크톱 Outlook에서 열기">${esc(t.subject)}</a>`
      : `<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(t.subject)}</span>`;
    return `<div class="thread ${inbound ? 'inbound' : ''}${child ? ' side' : ''}">${child ? '↳' : '📧'} ${link}<span class="who">${esc(threadWho(t))} · ${when}</span></div>`;
  };
  const rows = [];
  famList.forEach(fam => {
    rows.push(row(fam.main, false));
    fam.side.forEach(t => rows.push(row(t, true)));
  });
  const shown = rows.slice(0, 6).join('');
  const more = rows.length > 6 ? `<div class="thread-more">+${rows.length - 6} more</div>` : '';
  return `<div class="threads">${shown}${more}</div>`;
}

function tierOf(m){ return (m.att || {}).tier || 'reference'; }

function latestOf(threads){
  if(!threads || !threads.length) return null;
  return threads.slice().sort((a,b)=>(b.last_message_at||'').localeCompare(a.last_message_at||''))[0];
}

// One matter = one to-do row; everything else lives in the deep-dive panel.
function rowHtml(m){
  const att = m.att || {};
  const dot = att.overdue ? 'overdue' : ((m.urgency||'normal') === 'low' ? 'low' : 'normal');
  const ballCls = m.ball === '나' ? 'me' : (m.ball === '상대' ? 'them' : 'both');
  const lt = latestOf(m.threads);
  const comm = lt ? `${threadWho(lt)} · ${(lt.last_message_at||'').slice(5,10)} — ${(lt.snippet||'').slice(0,70)}` : '';
  let clock = '—';
  if(att.tier === 'action' && att.hours_on_plate != null){
    const h = Math.round(att.hours_on_plate);
    clock = att.overdue ? `⚠ ${h}h` : `⏱ ${h}h`;
  } else {
    const ago = daysAgo(m.last_contact);
    if(ago !== null) clock = ago === 0 ? '오늘' : ago + '일';
  }
  const done = m.status === '완료';
  return `<div class="lrow${done ? ' done' : ''}" onclick="openPanel(${m.id})">
    <span class="ldot ${dot}"></span>
    <span class="ltitle">${esc(m.title)}</span>
    <span class="lbadge ${ballCls}">${esc(m.ball)}</span>
    <span class="lnext">${esc(m.next_action || '')}</span>
    <span class="lcomm">${esc(comm)}</span>
    <span class="lclock${att.overdue ? ' over' : ''}">${clock}</span>
    <button class="ldone" title="${done ? '완료됨 — 되돌리기' : '완료 처리'}"
      onclick="event.stopPropagation();save(${m.id},{status:'${done ? '진행중' : '완료'}'},true)">✔</button>
  </div>`;
}

const COLHEAD = `<div class="colhead"><span></span><span>사안</span><span>공</span>
  <span>Next — 누가·무엇</span><span>최신 소통</span><span>경과</span><span></span></div>`;

function renderSections(ms){
  const root = document.getElementById('sections');
  const action = ms.filter(m => tierOf(m) === 'action').sort(attSort);
  const waiting = ms.filter(m => tierOf(m) === 'waiting');
  const reference = ms.filter(m => tierOf(m) === 'reference');
  let html = '';

  html += `<div class="sect s-now"><h2>⚡ 지금 내 액션 <span class="cnt">${action.length}</span></h2>`;
  html += action.length
    ? COLHEAD + action.map(rowHtml).join('')
    : `<div class="allclear">✓ 막힌 것 없음 — 지금 당장 할 액션이 없습니다.</div>`;
  html += `</div>`;

  if(waiting.length)
    html += `<div class="sect s-wait"><h2>⏳ 상대 대기 <span class="cnt">${waiting.length}</span></h2>
      ${waiting.map(rowHtml).join('')}</div>`;

  if(reference.length)
    html += `<div class="sect s-ref"><h2>📡 모니터링·레퍼런스 <span class="cnt">${reference.length}</span></h2>
      ${reference.map(rowHtml).join('')}</div>`;

  root.innerHTML = html;
}

// --- deep-dive panel (design A: right slide-in; full card content) ------------
let PANEL_ID = null;

function openPanel(id){
  const m = (DATA.matters || []).find(x => x.id === id);
  if(!m) return;
  PANEL_ID = id;
  document.getElementById('panelBody').innerHTML = card(m);
  document.body.classList.add('panel-open');
}

function closePanel(){
  PANEL_ID = null;
  document.body.classList.remove('panel-open');
}

function refreshPanel(){
  if(PANEL_ID === null) return;
  const m = (DATA.matters || []).find(x => x.id === PANEL_ID);
  if(!m || m.archived){ closePanel(); return; }
  document.getElementById('panelBody').innerHTML = card(m);
}

document.addEventListener('keydown', e => { if(e.key === 'Escape') closePanel(); });

// overdue first (most-breached on top), then urgency, then longest on plate.
function attSort(a, b){
  const A = a.att || {}, B = b.att || {};
  if(!!A.overdue !== !!B.overdue) return A.overdue ? -1 : 1;
  const rank = u => ({urgent:0, normal:1, low:2}[u] ?? 1);
  if(rank(A.urgency) !== rank(B.urgency)) return rank(A.urgency) - rank(B.urgency);
  return (B.hours_on_plate || 0) - (A.hours_on_plate || 0);
}

// Debounced autosave per field; select/date save immediately and re-render.
let _deb = {};
document.addEventListener('input', e => {
  const t = e.target, f = t.dataset.f, id = t.dataset.id;
  if(!f || !id) return;
  clearTimeout(_deb[id + f]);
  _deb[id + f] = setTimeout(() => save(id, {[f]: t.value}, t.tagName === 'SELECT' || t.type === 'date'), 500);
});
document.addEventListener('change', e => {
  const t = e.target, f = t.dataset.f, id = t.dataset.id;
  if(!f || !id) return;
  if(t.tagName === 'SELECT' || t.type === 'date'){ clearTimeout(_deb[id + f]); save(id, {[f]: t.value}, true); }
});

async function save(id, patch, rerender){
  const r = await fetch('/matters/api/matters/' + id, {method:'POST',
    headers:{'Content-Type':'application/json'}, body: JSON.stringify(patch)});
  if((await r.json()).ok){
    const dot = document.getElementById('saveDot');
    dot.classList.add('show'); clearTimeout(dot._h);
    dot._h = setTimeout(() => dot.classList.remove('show'), 1400);
    if(rerender) load();
  }
}

function touch(id){ save(id, {last_contact: new Date().toISOString().slice(0,10)}, true); }
function archive(id){
  if(!confirm('이 사안을 보관할까요? (목록에서 숨겨집니다)')) return;
  save(id, {archived: 1}, true);
}

load();
</script>
</div>"""


def render_page():
    return ("<!doctype html><html lang=\"ko\"><head>"
            "<meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>Matter Tracker · Wayfinder</title>"
            "<link rel=\"stylesheet\" href=\"/static/style.css\">"
            f"<style>{PAGE_CSS}</style></head><body>"
            "<nav><span class=\"nav-brand\">🗂 Matter Tracker</span>"
            "<span class=\"nav-user\"><a class=\"nav-back\" href=\"/\">← Home</a></span></nav>"
            f"{PAGE_BODY}</body></html>")


def render_local_only():
    return ("<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">"
            "<title>Matter Tracker · Wayfinder</title>"
            "<link rel=\"stylesheet\" href=\"/static/style.css\"></head><body>"
            "<nav><span class=\"nav-brand\">🗂 Matter Tracker</span>"
            "<span class=\"nav-user\"><a class=\"nav-back\" href=\"/\">← Home</a></span></nav>"
            "<div style=\"max-width:560px;margin:80px auto;text-align:center;padding:0 20px\">"
            "<div style=\"font-size:2.4rem\">🔒</div>"
            "<h1 style=\"font-size:1.2rem;margin:12px 0\">This app runs locally only</h1>"
            "<p style=\"color:var(--text-muted);font-size:var(--text-sm);line-height:1.7\">"
            "Matter Tracker reads the local Outlook mailbox, so it works only on "
            "Jongha's machine. Mail data never leaves that PC.<br><br>"
            "Open it from the local Wayfinder: "
            "<a href=\"http://localhost:8080/matters\" style=\"color:var(--accent)\">localhost:8080/matters</a>"
            "</p></div></body></html>")
