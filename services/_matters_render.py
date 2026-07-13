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
.sect.s-me h2::before{background:var(--me)} .sect.s-joint h2::before{background:var(--joint)}
.sect.s-them h2::before{background:var(--them)} .sect.s-done h2::before{background:var(--dim)}
.sect h2 .cnt{color:var(--dim);font-weight:600}
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
.next-action input{font-weight:700;color:var(--accent)}
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
.thread-more{color:var(--dim);font-size:.72rem}
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
<div class="cands nm-sugg" id="nmsuggs" hidden></div>
<div class="cands" id="cands" hidden></div>
<div class="drafts" id="drafts" hidden></div>
<div id="sections"></div>
<button class="add-btn" onclick="addMatter()">＋ 새 사안 추가</button>
<div class="save-dot" id="saveDot">✓ 저장됨</div>

<script>
const BALLS = ['나','공동','상대'];
const STATUSES = ['진행중','회신대기','보류','완료'];
const SECTS = [
  {key:'나',   cls:'s-me',    label:'🔴 공: 나 — 내 액션 필요'},
  {key:'공동', cls:'s-joint', label:'🟠 공: 공동'},
  {key:'상대', cls:'s-them',  label:'🔵 공: 상대 — 회신 대기'},
];
let DATA = {matters:[]};

function esc(s){ return String(s??'').replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/"/g,'&quot;'); }
function daysAgo(iso){
  if(!iso) return null;
  const d = new Date(iso + 'T00:00:00'); if(isNaN(d)) return null;
  return Math.floor((new Date().setHours(0,0,0,0) - d) / 86400000);
}

async function load(){
  const d = await (await fetch('/matters/api')).json();
  DATA = d;
  renderKpis(d.kpis); renderDrafts(d.drafts); renderSections(d.matters);
  renderBriefing(d.briefing); renderNMSuggs(d.new_matter_suggestions || []);
  const ls = d.last_scan;
  document.getElementById('sub').textContent =
    (ls ? `마지막 스캔: ${ls.finished_at} (${ls.source})${ls.changes_summary ? ' — ' + ls.changes_summary : ''}` : '스캔 이력 없음')
    + ` · 사안 ${d.matters.length}건`;
}

async function runScan(){
  const btn = document.getElementById('scanBtn');
  btn.disabled = true; btn.textContent = '스캔 중…';
  try {
    const r = await (await fetch('/matters/api/scan', {method:'POST'})).json();
    renderCandidates(r.candidates || []);
  } finally {
    btn.disabled = false; btn.textContent = '↻ 지금 스캔';
    load();
  }
}

function renderCandidates(cands){
  const el = document.getElementById('cands');
  if(!cands.length){ el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = '<h2>🔍 신규 사안 후보 ' + cands.length + '건 (검토 필요)</h2><ul>'
    + cands.map(c => `<li>${esc(c)}</li>`).join('') + '</ul>';
}

function renderBriefing(b){
  const el = document.getElementById('briefing');
  if(!b || !b.text){ el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = `<h2>🤖 AI 브리핑<span class="when">${esc(b.created_at || '')}</span></h2><p>${esc(b.text)}</p>`;
}

function renderNMSuggs(suggs){
  const el = document.getElementById('nmsuggs');
  if(!suggs.length){ el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = '<h2>🤖 AI가 감지한 신규 사안 ' + suggs.length + '건</h2><ul>'
    + suggs.map(s => {
        let d = {}; try { d = JSON.parse(s.proposed_value); } catch(e){}
        return `<li><b>${esc(d.title || '?')}</b><span class="why">${esc(s.reason || '')}</span>
          <button class="touch-btn" onclick="resolveSugg(${s.id}, true)">＋ 사안으로 추가</button>
          <button class="touch-btn" onclick="resolveSugg(${s.id}, false)">무시</button></li>`;
      }).join('') + '</ul>';
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
    ['red',   k.my_action,     '내 액션 필요'],
    ['blue',  k.waiting_reply, '상대 회신 대기'],
    ['amber', k.drafts,        '미발송 초안'],
    ['red',   k.stale,         '5일+ 무응답'],
    ['green', k.in_progress,   '진행 중'],
  ].map(([c,n,l]) => `<div class="kpi ${c}"><div class="num">${n}</div><div class="lbl">${l}</div></div>`).join('');
}

function renderDrafts(ds){
  const el = document.getElementById('drafts');
  if(!ds || !ds.length){ el.hidden = true; return; }
  el.hidden = false;
  el.innerHTML = '<h2>📝 미발송 초안 ' + ds.length + '건</h2><ul>'
    + ds.map(d => `<li><span>${esc(d.subject)}</span><span class="d">${esc(d.saved_at)}</span></li>`).join('')
    + '</ul>';
}

function card(m){
  const ago = daysAgo(m.last_contact);
  const stale = ago !== null && ago >= 5 && m.status !== '완료';
  const f = (label, field, val, opts={}) => `
    <label>${label}</label>
    ${opts.area
      ? `<textarea rows="${opts.rows||1}" data-f="${field}" data-id="${m.id}">${esc(val)}</textarea>`
      : `<input type="${opts.type||'text'}" value="${esc(val)}" data-f="${field}" data-id="${m.id}">`}`;
  return `<div class="card b-${m.ball}${m.status==='완료' ? ' done' : ''}">
    <button class="del" title="보관 (archive)" onclick="archive(${m.id})">✕</button>
    <div class="row1">
      <input class="title-input" value="${esc(m.title)}" data-f="title" data-id="${m.id}">
      <select class="sm" data-f="status" data-id="${m.id}">${STATUSES.map(s=>`<option${s===m.status?' selected':''}>${s}</option>`).join('')}</select>
      <select class="sm" data-f="ball" data-id="${m.id}">${BALLS.map(b=>`<option${b===m.ball?' selected':''}>${b}</option>`).join('')}</select>
      ${stale ? `<span class="stale-badge">⏰ ${ago}일 무응답</span>` : ''}
    </div>
    <div class="fgrid">
      ${f('People','people',m.people)}
      ${f('Waiting','waiting',m.waiting)}
      <label>Next</label><span class="next-action"><input value="${esc(m.next_action)}" data-f="next_action" data-id="${m.id}"></span>
      <label>Last</label>
      <span class="lastrow">
        <input type="date" value="${esc(m.last_contact)}" data-f="last_contact" data-id="${m.id}" style="width:150px">
        <button class="touch-btn" onclick="touch(${m.id})">↻ 오늘</button>
        ${ago !== null ? `<span class="ago">${ago === 0 ? '오늘' : ago + '일 전'}</span>` : ''}
      </span>
      ${f('Notes','notes',m.notes,{area:true,rows:2})}
    </div>
    ${suggList(m.suggestions)}
    ${structTree(m)}
    ${threadList(m.threads)}
  </div>`;
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

function suggList(suggs){
  if(!suggs || !suggs.length) return '';
  const rows = suggs.map(s => `
    <div class="sugg">
      <span class="tag">🤖 ${esc(s.field)}</span>
      <span class="val">${esc(s.proposed_value)}</span>
      <span class="why">${esc(s.reason || '')}</span>
      <button class="ok" onclick="resolveSugg(${s.id}, true)">✓ 반영</button>
      <button onclick="resolveSugg(${s.id}, false)">✕ 무시</button>
    </div>`).join('');
  return `<div class="suggs">${rows}</div>`;
}

function threadList(threads){
  if(!threads || !threads.length) return '';
  const me = 'jongha.kang@cheil.com';
  const show = threads.slice(0, 4);
  const rows = show.map(t => {
    const inbound = (t.last_sender || '').toLowerCase() !== me;
    const who = inbound ? (t.last_sender || '').split('@')[0] : '나';
    const when = (t.last_message_at || '').slice(5, 10);
    const link = t.outlook_link
      ? `<a href="${esc(t.outlook_link)}" target="_blank" title="${esc(t.subject)}">${esc(t.subject)}</a>`
      : `<span style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${esc(t.subject)}</span>`;
    return `<div class="thread ${inbound ? 'inbound' : ''}">📧 ${link}<span class="who">${esc(who)} · ${when}</span></div>`;
  }).join('');
  const more = threads.length > 4 ? `<div class="thread-more">+${threads.length - 4} more</div>` : '';
  return `<div class="threads">${rows}${more}</div>`;
}

function renderSections(ms){
  const root = document.getElementById('sections');
  let html = '';
  for(const s of SECTS){
    const list = ms.filter(m => m.ball === s.key && m.status !== '완료');
    if(list.length)
      html += `<div class="sect ${s.cls}"><h2>${s.label} <span class="cnt">${list.length}</span></h2>
        <div class="grid2">${list.map(card).join('')}</div></div>`;
  }
  const done = ms.filter(m => m.status === '완료');
  if(done.length)
    html += `<div class="sect s-done"><h2>✅ 완료 <span class="cnt">${done.length}</span></h2>
      <div class="grid2">${done.map(card).join('')}</div></div>`;
  root.innerHTML = html || '<div style="color:var(--muted);padding:30px;text-align:center">사안이 없습니다 — 아래에서 추가하세요.</div>';
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
async function addMatter(){
  const title = prompt('새 사안 제목:'); if(!title) return;
  await fetch('/matters/api/matters', {method:'POST', headers:{'Content-Type':'application/json'},
    body: JSON.stringify({title: title, ball: '나', status: '진행중'})});
  load();
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
