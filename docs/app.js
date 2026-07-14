/* ===== 패시브 ETF 구성비중 트래커 - SPA ===== */
const MGR = {
  SOL:   {label:"SOL",   color:"#3d7bff", company:"신한자산운용"},
  RISE:  {label:"RISE",  color:"#ffc02e", company:"KB자산운용"},
  TIGER: {label:"TIGER", color:"#ff7a33", company:"미래에셋자산운용"},
};
const app = document.getElementById('app');
const crumbsEl = document.getElementById('crumbs');
const asofEl = document.getElementById('asof');

/* ---- utils ---- */
const api = (p) => fetch(p).then(r => r.json());
const esc = (s) => String(s??'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]));
const nf = (x, d=0) => (x==null||isNaN(x)) ? '–' : Number(x).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});

function pct(x, d=2){ return (x==null||isNaN(x)) ? '–' : Number(x).toFixed(d)+'%'; }
function shares(x){
  if(x==null||isNaN(x)) return '–';
  return (Math.abs(x%1)>1e-6) ? nf(x,2) : nf(Math.round(x),0);
}
function amountKR(x){
  if(!x) return '–';
  if(x>=1e8) return (x/1e8).toFixed(1)+'억';
  if(x>=1e4) return Math.round(x/1e4).toLocaleString('ko-KR')+'만';
  return nf(x,0);
}
function deltaHTML(x, unit='%p', d=2){
  if(x==null||isNaN(x)) return '<span class="delta flat">–</span>';
  const v = Number(x);
  if(Math.abs(v) < (d===2?0.005:0.5)) return `<span class="delta flat">0.00${unit}</span>`;
  const up = v>0;
  const ar = up?'▲':'▼';
  return `<span class="delta ${up?'up':'down'}"><span class="ar">${ar}</span> ${up?'+':''}${v.toFixed(d)}${unit}</span>`;
}
function sharesDeltaHTML(x){
  if(x==null||isNaN(x)||Math.abs(x)<1e-6) return '<span class="delta flat">–</span>';
  const up=x>0; return `<span class="delta ${up?'up':'down'}">${up?'+':''}${shares(x)}</span>`;
}
function pill(m){ const c=MGR[m]?.color||'#7c8cff'; return `<span class="mgr-pill" style="--mc:${c}">${esc(MGR[m]?.label||m)}</span>`; }

/* ---- crumbs ---- */
function setCrumbs(parts){
  crumbsEl.innerHTML = parts.map((p,i)=> i<parts.length-1
    ? `<a href="${p.href}">${esc(p.label)}</a><span class="sep">›</span>`
    : `<span class="cur">${esc(p.label)}</span>`).join('');
}

/* ============ HOME ============ */
async function viewHome(){
  app.innerHTML = '<div class="loading">불러오는 중…</div>';
  const d = await api('data/home.json');
  asofEl.innerHTML = d.as_of ? `기준일 <b>${esc(d.as_of)}</b>` : '';
  setCrumbs([{label:'홈'}]);

  const movers = d.rebalanced.map(c => rebalCard(c)).join('');
  const mgrs = d.managers.map(m => mgrCard(m)).join('');
  const emptyMsg = d.n_no_prev >= d.n_total
    ? '아직 직전 영업일 데이터가 축적되지 않았습니다. 다음 갱신부터 표시됩니다.'
    : '오늘은 CU 보유주수가 바뀐(리밸런싱) ETF가 없습니다. 구성비중 변화는 대부분 보유종목의 가격 변동에 따른 것입니다.';

  app.innerHTML = `
    <div class="page-head">
      <h1>패시브 ETF 구성비중 트래커</h1>
      <div class="desc">SOL · RISE · TIGER 주요 테마 ETF ${d.n_total}종의 CU 구성종목 · 보유수량 변화를 추적합니다.</div>
    </div>
    <div class="section-title"><h2>오늘의 보유수량 변화</h2><span class="sub">CU 내 개별 종목 보유주수가 실제로 바뀐(리밸런싱) ETF · 편입/편출/증감</span></div>
    ${d.rebalanced.length ? `<div class="mover-grid">${movers}</div>`
      : `<div class="empty">${emptyMsg}</div>`}
    <div class="section-title" style="margin-top:36px"><h2>운용사</h2><span class="sub">운용사를 선택해 개별 ETF를 확인하세요</span></div>
    <div class="mgr-grid">${mgrs}</div>
  `;
}

function mgrCard(m){
  const c = MGR[m.id]?.color || '#7c8cff';
  return `<a class="mgr-card" href="#/manager/${m.id}" style="--mc:${c}">
    <div class="glow"></div>
    <div class="mtag"><span class="dot"></span>${esc(m.name)}</div>
    <div class="company">${esc(m.company)}</div>
    <div class="stats">
      <div class="stat"><div class="n">${m.n_etf}</div><div class="l">추적 ETF</div></div>
      <div class="stat ${m.n_rebalanced?'big':''}"><div class="n">${m.n_rebalanced}</div><div class="l">리밸런싱</div></div>
    </div>
    <div class="go">→</div>
  </a>`;
}

function sharesChip(t){
  const up = t.shares_delta >= 0;
  if(t.status==='new')      return `<span class="chip new">${esc(t.name)} 편입</span>`;
  if(t.status==='removed')  return `<span class="chip out">${esc(t.name)} 편출</span>`;
  return `<span class="chip ${up?'up':'down'}">${esc(t.name)} ${up?'+':''}${shares(t.shares_delta)}주</span>`;
}

function rebalCard(c){
  const s = c.summary, col = MGR[c.manager]?.color || '#7c8cff';
  const chips = (s.top_changes||[]).slice(0,4).map(sharesChip).join('');
  const sub = [];
  if(s.n_new)          sub.push(`편입 ${s.n_new}`);
  if(s.n_removed)      sub.push(`편출 ${s.n_removed}`);
  if(s.n_share_changed)sub.push(`주수변경 ${s.n_share_changed}`);
  sub.push(`거래비중 ${pct(s.share_turnover)}`);
  return `<a class="mover" href="#/etf/${c.etf_id}" style="--mc:${col}">
    <div class="top"><div class="nm">${esc(c.name)}</div>${pill(c.manager)}</div>
    <div class="turn"><span class="v">${s.n_rebalanced}</span><span class="u">종목 보유수량 변경</span></div>
    <div class="submeta">${sub.join(' · ')}</div>
    <div class="chips">${chips}</div>
    <div class="dates">${esc(c.prev_date||'?')} → ${esc(c.latest_date||'?')}</div>
  </a>`;
}

/* ============ MANAGER ============ */
async function viewManager(mid){
  app.innerHTML = '<div class="loading">불러오는 중…</div>';
  const d = await api('data/managers/'+mid+'.json');
  const minfo = MGR[mid] || {label:mid,color:'#7c8cff',company:''};
  setCrumbs([{label:'홈',href:'#/'},{label:minfo.label}]);

  const rows = d.etfs.map((c,i)=> etfRow(c,i+1)).join('');
  app.innerHTML = `
    <div class="back" onclick="location.hash='#/'">← 홈</div>
    <div class="page-head">
      <h1 style="display:flex;align-items:center;gap:12px">
        <span class="dot" style="width:16px;height:16px;border-radius:5px;background:${minfo.color};display:inline-block"></span>
        ${esc(minfo.label)} ETF</h1>
      <div class="desc">${esc(minfo.company)} · ${d.etfs.length}종 · 회전율(전일 대비 구성 변화) 큰 순</div>
    </div>
    <div class="etf-list">${rows}</div>
  `;
}

function topChangeText(t){
  if(!t) return '';
  if(t.status==='new') return `${t.name} 편입`;
  if(t.status==='removed') return `${t.name} 편출`;
  const up=t.shares_delta>=0; return `${t.name} ${up?'+':''}${shares(t.shares_delta)}주`;
}
function etfRow(c, rank){
  const s=c.summary;
  const reb = s.is_rebalanced;
  const badge = reb ? '<span class="badge-big">리밸런싱</span>':'';
  const metaMid = !c.has_prev ? '비교 대기'
    : (reb ? ('최다 '+esc(topChangeText(s.top_changes[0]))) : '보유수량 변동 없음');
  return `<a class="etf-row" href="#/etf/${c.etf_id}">
    <div class="rank">${rank}</div>
    <div class="info">
      <div class="nm">${esc(c.name)}${badge}</div>
      <div class="meta">${esc(c.ticker||'')} · ${c.n_holdings}종목 · ${metaMid}</div>
    </div>
    <div class="turnwrap">
      <div class="v" ${reb?'style="color:var(--up)"':''}>${!c.has_prev?'–':(reb?s.n_rebalanced:'0')}</div>
      <div class="l">수량변경</div>
    </div>
  </a>`;
}

/* ============ ETF DETAIL ============ */
async function viewEtf(id){
  app.innerHTML = '<div class="loading">불러오는 중…</div>';
  const d = await api('data/etfs/'+id+'.json');
  const minfo = MGR[d.manager] || {label:d.manager,color:'#7c8cff'};
  setCrumbs([{label:'홈',href:'#/'},{label:minfo.label,href:'#/manager/'+d.manager},{label:d.name}]);

  const s = d.summary;
  const maxW = Math.max(...d.rows.map(r=>r.weight||0), 1);

  const head = `
    <div class="back" onclick="location.hash='#/manager/${d.manager}'">← ${esc(minfo.label)} 목록</div>
    <div class="detail-head">
      ${pill(d.manager)}
      <h1>${esc(d.name)}</h1>
      <span class="tk">${esc(d.ticker||'')}</span>
      <div class="date-note">
        <span class="lg">${esc(d.latest_date||'-')}</span>
        ${d.has_prev?`<span class="arrow"> vs </span><span>${esc(d.prev_date)}</span>`:''}
        <div style="color:var(--txt-mute);margin-top:2px">최신 기준일${d.has_prev?' · 전영업일 대비':''}</div>
      </div>
    </div>`;

  if(!d.has_prev){
    app.innerHTML = head + infoCard(d) + `
      <div class="nochange">직전 영업일 스냅샷이 아직 없어 <b>보유수량 변화 비교</b>는 다음 갱신부터 제공됩니다. 아래는 최신 구성종목입니다.</div>
      ${statStrip(d,false)}
      ${holdingsTable(d, maxW, false)}`;
    return;
  }

  app.innerHTML = head + infoCard(d) + statStrip(d,true) + holdingsTable(d, maxW, true);
}

function infoCard(d){
  const i = d.info || {};
  const rows = [];
  if(i.index_name) rows.push(['기초지수', esc(i.index_name)]);
  if(i.method)     rows.push(['구성 방식', esc(i.method)]);
  if(i.fee)        rows.push(['총보수', '연 '+esc(i.fee)+'%']);
  if(i.listing)    rows.push(['상장일', esc(i.listing)]);
  if(i.aum)        rows.push(['순자산', esc(i.aum)]);
  if(i.cu)         rows.push(['설정단위(CU)', esc(i.cu)]);
  if(!rows.length && !i.index_desc) return '';
  const grid = rows.map(([k,v])=>`<div class="info-item"><span class="k">${k}</span><span class="v">${v}</span></div>`).join('');
  const desc = i.index_desc ? `<div class="info-desc"><span class="k">지수 설명</span> ${esc(i.index_desc)}</div>` : '';
  return `<div class="info-card"><div class="info-title">ETF 개요</div><div class="info-grid">${grid}</div>${desc}</div>`;
}

function statStrip(d, hasPrev){
  const s=d.summary;
  return `<div class="stat-strip">
    <div class="stat-box"><div class="l">구성종목 수</div><div class="v">${d.n_holdings}<small> 종목</small></div></div>
    ${hasPrev?`
    <div class="stat-box ${s.n_rebalanced?'warn':''}"><div class="l">보유수량 변경</div><div class="v">${s.n_rebalanced}<small> 종목</small></div></div>
    <div class="stat-box"><div class="l">편입 / 편출</div><div class="v">${s.n_new} <small>/</small> ${s.n_removed}</div></div>
    <div class="stat-box"><div class="l">거래비중 <small>수량변동</small></div><div class="v">${pct(s.share_turnover)}</div></div>
    <div class="stat-box"><div class="l">비중 회전율 <small>가격영향 포함</small></div><div class="v">${pct(s.turnover)}</div></div>
    `:''}
  </div>`;
}

function holdingsTable(d, maxW, hasPrev){
  const color = MGR[d.manager] ? MGR[d.manager].color : '#7c8cff';
  const rows = d.rows.map((r,i)=>{
    const cls = hasPrev ? (r.status==='new' ? 'row-new' : (r.status==='removed' ? 'row-out' : '')) : '';
    const tag = !hasPrev ? '' : (r.status==='new' ? '<span class="tag new">신규</span>'
             : (r.status==='removed' ? '<span class="tag out">편출</span>' : ''));
    const barW = Math.max(2, (r.weight/maxW)*100);
    const rk = r.status==='removed' ? '–' : (i+1);

    let prevCells = '';
    if(hasPrev){
      const prevW = r.status==='new' ? '–' : pct(r.weight_prev);
      let dcell;
      if(r.status==='new') dcell = '<span class="delta up"><span class="ar">▲</span> 신규</span>';
      else if(r.status==='removed') dcell = '<span class="delta down"><span class="ar">▼</span> 편출</span>';
      else dcell = deltaHTML(r.weight_delta);
      prevCells = '<td style="color:var(--txt-dim)">'+prevW+'</td><td>'+dcell+'</td>';
    }
    const shDelta = hasPrev ? '<td>'+sharesDeltaHTML(r.shares_delta)+'</td>' : '';

    return '<tr class="'+cls+'">'
      + '<td class="rk">'+rk+'</td>'
      + '<td class="l"><span class="nm">'+esc(r.stock_name)+'</span> '+tag+'<div class="cd">'+esc(r.stock_code)+'</div></td>'
      + '<td><span class="wt">'+pct(r.weight)+'</span><div class="bar"><i style="width:'+barW+'%;background:'+color+'"></i></div></td>'
      + prevCells
      + '<td>'+shares(r.shares)+'</td>'
      + shDelta
      + '<td style="color:var(--txt-mute)">'+amountKR(r.amount)+'</td>'
      + '</tr>';
  }).join('');

  const prevHead = hasPrev ? '<th>전일비중</th><th>비중변화</th>' : '';
  const shHead = hasPrev ? '<th>수량변화</th>' : '';
  return '<div class="tbl-wrap"><div class="tbl-scroll"><table class="holdings">'
    + '<thead><tr><th class="rk">#</th><th class="l">종목</th><th>구성비중</th>'
    + prevHead + '<th>보유수량</th>' + shHead + '<th>평가금액</th></tr></thead>'
    + '<tbody>' + rows + '</tbody></table></div></div>';
}

/* ============ refresh ============ */
const refreshBtn = document.getElementById('refreshBtn');
const IS_LOCAL = /^(127\.0\.0\.1|localhost|\[?::1\]?)$/.test(location.hostname);
if(!IS_LOCAL) refreshBtn.style.display = 'none';   // 정적 배포(Pages)에선 서버 재수집 불가
refreshBtn.addEventListener('click', async ()=>{
  if(refreshBtn.classList.contains('spin')) return;
  refreshBtn.classList.add('spin');
  toast('최신 영업일 데이터를 재수집합니다…');
  let ok = false;
  try{
    const r = await fetch('/api/refresh', {method:'POST'});
    if(r.ok){
      ok = true;
      await new Promise(res=>{
        const poll = setInterval(async ()=>{
          try{
            const st = await api('/api/status');
            if(!st.running){ clearInterval(poll); toast(st.log==='ok'?'갱신 완료':'갱신 오류: '+st.log); res(); }
          }catch(e){ clearInterval(poll); res(); }
        }, 1500);
      });
    }
  }catch(e){}
  refreshBtn.classList.remove('spin');
  if(!ok) toast('정적 버전입니다 · 데이터는 매일 자동 갱신됩니다');
  route();
});
let toastT;
function toast(msg){
  let el = document.querySelector('.toast');
  if(!el){ el=document.createElement('div'); el.className='toast'; document.body.appendChild(el); }
  el.textContent = msg; el.classList.add('show');
  clearTimeout(toastT); toastT=setTimeout(()=>el.classList.remove('show'), 3200);
}

/* ============ router ============ */
function route(){
  const h = location.hash || '#/';
  const m = h.match(/^#\/manager\/([^/]+)/);
  const e = h.match(/^#\/etf\/([^/]+)/);
  window.scrollTo(0,0);
  if(e) return viewEtf(decodeURIComponent(e[1]));
  if(m) return viewManager(decodeURIComponent(m[1]));
  return viewHome();
}
window.addEventListener('hashchange', route);
route();
