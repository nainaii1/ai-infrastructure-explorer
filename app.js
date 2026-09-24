// AI Infrastructure Explorer — all page logic. Reads window.DATA (data.js) and
// window.DESK (desk.js), renders four views (desk, map, narratives, timeline) and a company drawer. Hash-routed so
// every company and narrative has a link that works from file://.
(function () {
  'use strict';
  const D = window.DATA;
  const $ = (s, r) => (r || document).querySelector(s);
  const esc = s => String(s == null ? '' : s).replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));

  const byTicker = {}; D.companies.forEach(c => { byTicker[c.ticker] = c; });
  const byLayer = {}; D.layers.forEach(l => { byLayer[l.id] = l; });
  const byNarr = {}; D.narratives.forEach(n => { byNarr[n.id] = n; });
  const devs = D.developments.slice().sort((a, b) => b.date.localeCompare(a.date));
  const today = new Date().toISOString().slice(0, 10);

  const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  function fmtDate(iso) {
    const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso);
    if (!m) return iso; // period strings like "Q2 2026" pass through
    return `${+m[3]} ${MONTHS[+m[2] - 1]} ${m[1]}`;
  }
  function fmtMonth(iso) { return `${MONTHS[+iso.slice(5, 7) - 1]} ${iso.slice(0, 4)}`; }
  function host(url) { try { return new URL(url).hostname.replace(/^www\./, ''); } catch (e) { return ''; } }
  const SRC = { filing: 'Filing', company: 'Company', press: 'Press', analyst: 'X post' };
  function srcLabel(d) { return `${SRC[d.sourceType] || 'Source'} · ${host(d.source)}`; }

  function chip(c, small) {
    const label = c.listed === false ? esc(c.name) : esc(c.ticker);
    return `<button class="chip${small ? ' sm' : ''}${c.listed === false ? ' private' : ''}" data-t="${esc(c.ticker)}" title="${esc(c.name)}"><b>${label}</b>${c.listed === false ? '' : `<span>${esc(c.name)}</span>`}</button>`;
  }
  function chipsFor(tickers, small) {
    return `<div class="chips">${tickers.map(t => byTicker[t]).filter(Boolean).map(c => chip(c, small)).join('')}</div>`;
  }
  function matches(c, q) {
    if (!q) return true;
    q = q.toLowerCase();
    return c.ticker.toLowerCase().includes(q) || c.name.toLowerCase().includes(q);
  }
  function devsFor(ticker) { return devs.filter(d => d.companies.includes(ticker)); }

  // ---------- map ----------
  function renderMap(q) {
    const out = [];
    let lastStage = null;
    D.layers.forEach(l => {
      const cos = D.companies.filter(c => c.layer === l.id && matches(c, q));
      if (q && !cos.length) return;
      if (lastStage && lastStage !== l.stage && !q) out.push('<div class="flow">▼ feeds into ▼</div>');
      lastStage = l.stage;
      out.push(`<section class="layer" data-stage="${esc(l.stage)}" id="layer-${esc(l.id)}">
        <div class="layer-head"><h2>${esc(l.name)}</h2><span class="stage-tag">${esc(l.stage)}</span></div>
        <p class="layer-summary">${esc(l.summary)}</p>
        <p class="layer-constraint"><b>Constraint.</b> ${esc(l.constraint)}</p>
        <div class="chips">${cos.map(c => chip(c)).join('')}</div>
        <p class="layer-watch"><b>Watch:</b> ${esc(l.watch)}</p>
      </section>`);
    });
    $('#map').innerHTML = out.join('') || '<p class="empty">No company matches.</p>';
  }

  // ---------- narratives ----------
  function renderNarratives(openId) {
    $('#narratives').innerHTML = D.narratives.map(n => {
      const recent = devs.filter(d => d.narratives.includes(n.id)).slice(0, 6);
      return `<details class="narr" id="narr-${esc(n.id)}"${openId === n.id ? ' open' : ''}>
        <summary><h2>${esc(n.title)}</h2><span class="pill ${esc(n.status)}">${esc(n.status)}</span><p>${esc(n.summary)}</p></summary>
        <div class="narr-body">
          <div class="two">
            <div class="case"><h4>The case</h4><p>${esc(n.case)}</p></div>
            <div class="counter"><h4>The counter</h4><p>${esc(n.counter)}</p></div>
          </div>
          <div class="block"><h4>Signposts</h4><ul>${n.signposts.map(s => `<li>${esc(s)}</li>`).join('')}</ul></div>
          <div class="block"><h4>Companies</h4>${chipsFor(n.companies)}</div>
          <div class="block"><h4>Recent developments</h4><ul class="devlist">${recent.map(d => `<li><time>${fmtDate(d.date)}</time>${esc(d.title)} <a href="${esc(d.source)}" target="_blank" rel="noopener">↗</a></li>`).join('') || '<li class="muted">None logged yet.</li>'}</ul>
          <p style="margin-top:8px"><a href="#timeline/${esc(n.id)}">All developments in this narrative →</a></p></div>
        </div>
      </details>`;
    }).join('');
  }

  // ---------- timeline ----------
  let tlNarr = '';
  function renderTimeline(q) {
    $('#tl-filters').innerHTML = [`<button data-n="" class="${tlNarr ? '' : 'on'}">All</button>`]
      .concat(D.narratives.map(n => `<button data-n="${esc(n.id)}" class="${tlNarr === n.id ? 'on' : ''}">${esc(n.title)}</button>`)).join('');
    const list = devs.filter(d => (!tlNarr || d.narratives.includes(tlNarr)) &&
      (!q || d.companies.some(t => byTicker[t] && matches(byTicker[t], q)) || d.title.toLowerCase().includes(q.toLowerCase())));
    const out = []; let month = null;
    list.forEach(d => {
      const m = d.date.slice(0, 7);
      if (m !== month) { month = m; out.push(`<div class="month">${d.date > today ? 'Upcoming · ' : ''}${fmtMonth(d.date)}</div>`); }
      out.push(`<article class="dev${d.date > today ? ' future' : ''}">
        <time datetime="${esc(d.date)}">${fmtDate(d.date)}</time>
        <div><h3>${esc(d.title)}</h3><p>${esc(d.summary)}</p>
          <div class="dev-meta">${d.companies.map(t => byTicker[t]).filter(Boolean).map(c => chip(c, true)).join('')}
            ${d.narratives.map(id => byNarr[id] ? `<button class="tag" data-n="${esc(id)}">${esc(byNarr[id].title)}</button>` : '').join('')}
            <a class="src" href="${esc(d.source)}" target="_blank" rel="noopener">${esc(srcLabel(d))} ↗</a></div>
        </div></article>`);
    });
    $('#timeline').innerHTML = out.join('') || '<p class="empty">Nothing matches.</p>';
  }

  // ---------- desk (weekly memo, generated into desk.js by desk/build.py) ----------
  const K = window.DESK || null;
  let deskIdx = 0;
  const STANCE = { bull: '▲ Bull', bear: '▼ Bear', mixed: '◆ Mixed' };
  function tick(t) { return byTicker[t] ? chip(byTicker[t], true) : `<span class="tkr">${esc(t)}</span>`; }
  function pct(v) { return v == null ? '—' : `<span class="${v >= 0 ? 'up' : 'dn'}">${v >= 0 ? '+' : ''}${v.toFixed(1)}%</span>`; }
  function num(v) { return v == null ? '—' : v.toLocaleString('en-US', { maximumFractionDigits: 2 }); }
  function link(url, label) { return url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label || host(url))} ↗</a>` : ''; }
  function paras(list) { return (list || []).map(p => `<p>${esc(p)}</p>`).join(''); }

  const ZONE = { add: 'In the add zone', buy: 'In the zone', hold: 'Above the zone: hold', above: "Above the zone: don't add" };
  function zoneOf(price, lv) {
    const top = lv.stopAbove || lv.buyBelow;
    if (lv.addBelow != null && price <= lv.addBelow) return 'add';
    if (price <= lv.buyBelow) return 'buy';
    return price <= top ? 'hold' : 'above';
  }
  // A horizontal ladder: add zone, accumulate zone, hold band, stop-adding, with today's price marked.
  function ladder(t, lv, action) {
    const watch = action && action !== 'accumulate';
    const q = (K.quotes || {})[t]; const price = q && q.price;
    const top = lv.stopAbove || lv.buyBelow;
    const pts = [lv.addBelow, lv.buyBelow, top, price].filter(v => v != null);
    const lo = Math.min(...pts) * 0.92, hi = Math.max(...pts) * 1.08, w = v => ((v - lo) / (hi - lo) * 100).toFixed(2);
    const seg = (a, b, cls, label) => b > a ? `<span class="lz ${cls}" style="left:${w(a)}%;width:${(w(b) - w(a)).toFixed(2)}%" title="${esc(label)}"></span>` : '';
    const add = lv.addBelow != null ? lv.addBelow : lv.buyBelow;
    const z = price != null ? zoneOf(price, lv) : null;
    return `<div class="ladder" role="img" aria-label="Price ${price != null ? num(price) : 'unknown'} against the zones">
      <div class="lbar">${seg(lo, add, 'z-add', 'add zone')}${seg(add, lv.buyBelow, 'z-buy', 'accumulate zone')}${seg(lv.buyBelow, top, 'z-hold', 'hold')}${seg(top, hi, 'z-above', 'stop adding')}
        ${[add, lv.buyBelow, top].map(v => `<span class="ltick" style="left:${w(v)}%"></span>`).join('')}
        ${price != null ? `<span class="lmark" style="left:${w(price)}%"></span>` : ''}</div>
      <div class="llegend">${watch ? `<span class="k z-buy"></span>revisit ≤ ${num(lv.buyBelow)}` : `<span class="k z-add"></span>add ≤ ${num(add)} <span class="k z-buy"></span>buy ≤ ${num(lv.buyBelow)} <span class="k z-above"></span>stop adding &gt; ${num(top)}`}</div>
      <div class="lnow">${price != null ? `Now ${num(price)} ${esc(lv.currency)} · <b class="zn ${watch ? (z === 'add' || z === 'buy' ? 'buy' : 'hold') : z}">${watch ? (z === 'add' || z === 'buy' ? 'At the revisit level' : 'Above the revisit level') : ZONE[z]}</b> · alerts on` : 'No price in the sheet'}</div>
    </div>`;
  }

  function renderDesk() {
    if (!K || !K.memos || !K.memos.length) {
      $('#memo').innerHTML = '<p class="empty">No desk memo yet. The collector is gathering posts; the first memo appears after the weekly run.</p>';
      return;
    }
    const m = K.memos[Math.min(deskIdx, K.memos.length - 1)];
    const open = {}; K.calls.filter(c => !c.closed).forEach(c => { open[c.ticker] = c; });
    const handles = K.analysts.map(a => a.handle);
    const pick = K.memos.length > 1 ? `<select id="memo-pick" aria-label="Memo date">${K.memos.map((x, i) => `<option value="${i}"${i === deskIdx ? ' selected' : ''}>${fmtDate(x.date)}</option>`).join('')}</select>` : '';

    const acc = m.accumulate.map(a => {
      const c = open[a.ticker];
      return `<article class="idea ${esc(a.action)}">
        <div class="idea-head">${tick(a.ticker)}<h3>${esc(a.name)}</h3><span class="pill act-${esc(a.action)}">${esc(a.action)}</span><span class="conf">${esc(a.confidence)} confidence</span></div>
        <p class="thesis">${esc(a.thesis)}</p>
        <dl class="kv">
          <dt>Why it's cheap</dt><dd>${esc(a.whyCheap)}</dd>
          <dt>Valuation</dt><dd>${esc(a.valuation.text)} ${link(a.valuation.source)}</dd>
          <dt>Catalyst</dt><dd>${esc(a.catalyst)}</dd>
          <dt>Accumulate zone</dt><dd>${esc(a.zone)}${a.levels ? ladder(a.ticker, a.levels, a.action) : ''}</dd>
          <dt>Kills the idea</dt><dd>${esc(a.invalidation)}</dd>
          ${c ? `<dt>Scorecard</dt><dd>Opened ${fmtDate(c.opened)} at ${num(c.refPrice)} ${esc(c.currency || '')} · now ${num(c.lastPrice)} · ${pct(c.ret)} vs ${esc(K.bench)} ${pct(c.benchRet)}</dd>` : ''}
        </dl>
        <div class="idea-foot">${(a.analysts || []).map(h => `<span class="who">@${esc(h)}</span>`).join('')}${(a.sources || []).map(u => link(u)).join(' ')}</div>
      </article>`;
    }).join('') || '<p class="muted">Nothing meets the bar this week.</p>';

    const cols = handles.filter(h => m.board.some(b => b.views.some(v => v.handle === h)));
    const board = m.board.length ? `<div class="scroll"><table class="board">
      <thead><tr><th>Ticker</th>${cols.map(h => `<th>@${esc(h)}</th>`).join('')}<th>Desk read</th></tr></thead>
      <tbody>${m.board.map(b => `<tr><td>${tick(b.ticker)}</td>${cols.map(h => {
        const v = b.views.find(x => x.handle === h);
        return v ? `<td><a class="st ${esc(v.stance)}" href="${esc(v.url)}" target="_blank" rel="noopener" title="${esc(v.note)}">${STANCE[v.stance]}</a><div class="note">${esc(v.note)}</div></td>` : '<td class="muted">·</td>';
      }).join('')}<td class="read">${esc(b.read)}</td></tr>`).join('')}</tbody></table></div>` : '<p class="muted">No stances this week.</p>';

    const TR = (K.track || []).filter(a => a.calls);
    const track = TR.length ? `<div class="scroll"><table class="track"><thead><tr><th>Analyst</th><th>Stances</th><th>Scored</th><th>Avg edge vs ${esc(K.bench)}</th><th>Hit rate</th><th>Best / worst call so far</th></tr></thead><tbody>${
      TR.map(a => {
        const sc = a.rows.filter(r => r.edge != null).sort((x, y) => y.edge - x.edge);
        const bw = sc.length ? `${esc(sc[0].ticker)} ${pct(sc[0].edge)}${sc.length > 1 ? ` · ${esc(sc[sc.length - 1].ticker)} ${pct(sc[sc.length - 1].edge)}` : ''}` : '<span class="muted">—</span>';
        return `<tr><td>@${esc(a.handle)}</td><td class="num">${a.calls}</td><td class="num">${a.scored}</td><td class="num">${pct(a.avgEdge)}</td><td class="num">${a.hitRate == null ? '—' : a.hitRate + '%'}</td><td>${bw}</td></tr>`;
      }).join('')}</tbody></table></div>` : '<p class="muted">No stances recorded yet.</p>';
    const young = !TR.some(a => a.rows.some(r => r.since < m.date));

    const next = K.memos[Math.max(deskIdx - 1, 0)];
    const evs = (K.events || []).filter(e => e.date >= m.date && (deskIdx === 0 || e.date < next.date)).sort((x, y) => y.date.localeCompare(x.date));
    const VER = { confirms: 'Confirms the call', mixed: 'Mixed', breaks: 'Breaks the call' };
    const events = evs.map(e => `<article class="event ${esc(e.verdict)}">
        <div class="idea-head">${tick(e.ticker)}<h3>${esc(e.event)}</h3><span class="pill ver-${esc(e.verdict)}">${VER[e.verdict]}</span><time>${fmtDate(e.date)}</time></div>
        <p class="thesis">${esc(e.headline)}</p>${paras(e.summary)}
        ${(e.numbers || []).length ? `<ul class="nums">${e.numbers.map(n => `<li>${esc(n.text)} ${link(n.source)}</li>`).join('')}</ul>` : ''}
        ${e.callImpact ? `<p><b>Call:</b> ${esc(e.callImpact)}</p>` : ''}
        ${e.levels ? ladder(e.ticker, e.levels, 'accumulate') : ''}
        <div class="idea-foot">${(e.sources || []).map(u => link(u)).join(' ')}</div></article>`).join('');

    const alerts = deskIdx === 0 ? (K.alerts || []).slice(0, 6) : [];
    const changes = deskIdx === 0 && (K.changes || []).length ? `<section class="dsec changed"><h2>What changed</h2>
        <ul class="chg">${K.changes.map(c => `<li class="k-${esc(c.kind)}">${esc(c.text)}</li>`).join('')}</ul>
        ${alerts.length ? `<h4 class="sub">Price alerts</h4><ul class="chg">${alerts.map(a => `<li class="k-alert"><time>${esc((a.at || '').slice(0, 10))}</time> ${esc(a.text)}</li>`).join('')}</ul>` : ''}
      </section>` : '';

    const mk = m.market;
    const movers = (mk.movers || []).length ? `<table class="movers"><tbody>${mk.movers.map(x => `<tr><td>${tick(x.ticker)}</td><td class="num">${pct(x.chg1w)}</td><td>${esc(x.why || '')} ${link(x.source)}</td></tr>`).join('')}</tbody></table>` : '';
    const cal = (mk.calendar || []).length ? `<ul class="devlist">${mk.calendar.map(x => `<li><time>${fmtDate(x.date)}</time>${esc(x.event)} ${link(x.source)}</li>`).join('')}</ul>` : '';

    const score = K.calls.length ? `<div class="scroll"><table class="score"><thead><tr><th>Ticker</th><th>Opened</th><th>Ref</th><th>Now / exit</th><th>Return</th><th>${esc(K.bench)}</th><th>Status</th></tr></thead><tbody>${
      K.calls.slice().reverse().map(c => `<tr><td>${tick(c.ticker)}</td><td>${fmtDate(c.opened)}</td><td class="num">${num(c.refPrice)} ${esc(c.currency || '')}</td><td class="num">${num(c.lastPrice)}</td><td class="num">${pct(c.ret)}</td><td class="num">${pct(c.benchRet)}</td><td>${c.closed ? 'closed ' + fmtDate(c.closed.date) : 'open'}</td></tr>`).join('')}</tbody></table></div>` : '<p class="muted">No calls yet.</p>';

    $('#memo').innerHTML = `
      <div class="memo-meta">Weekly memo · ${fmtDate(m.date)} · posts ${fmtDate(m.window.from)} to ${fmtDate(m.window.to)} ${pick}</div>
      <h1 class="headline">${esc(m.headline)}</h1>
      ${changes}
      ${events ? `<section class="dsec"><h2>Since this memo</h2><p class="muted small">Event updates between weekly memos. They can move the alert levels; only the weekly memo opens or closes calls.</p>${events}</section>` : ''}
      <section class="dsec"><h2>1 · The supply-chain picture</h2>
        <div class="two"><div><h4>Now</h4>${paras(m.picture.now)}</div><div><h4>Next</h4>${paras(m.picture.next)}</div></div></section>
      <section class="dsec"><h2>2 · Accumulate list</h2>
        <p class="muted small">Research support, not advice. Prices from your Google Sheet${K.pricesAsOf ? ' as of ' + esc(K.pricesAsOf.slice(0, 10)) : ''}.</p>${acc}</section>
      <section class="dsec"><h2>3 · Analyst board</h2><p class="muted small">Each cell links to the post. Hover or read the note for the reason.</p>${board}</section>
      <section class="dsec"><h2>Analyst track record</h2><p class="muted small">Every stance on the board, from the day it was first recorded, against ${esc(K.bench)}. A bull call earns the stock's move minus ${esc(K.bench)}'s; a bear call the reverse; mixed calls are not scored. Local-currency returns.${young ? ' Everything was recorded this week, so it all reads 0% for now; it fills in as prices move.' : ''}</p>${track}</section>
      <section class="dsec"><h2>4 · Market wrap</h2>${paras(mk.summary)}${movers}${cal ? '<h4 class="sub">Coming up</h4>' + cal : ''}</section>
      <section class="dsec pushback"><h2>The desk's pushback</h2><p class="muted small">Every analyst on the roster leans bullish. This is the other side.</p>${paras(m.pushback)}</section>
      <section class="dsec"><h2>Scorecard</h2><p class="muted small">Every accumulate call, marked to the latest price against ${esc(K.bench)}. Calls are never edited after the fact.</p>${score}</section>
      ${m.flags.length ? `<section class="dsec"><h2>Flags</h2><ul>${m.flags.map(f => `<li>${esc(f)}</li>`).join('')}</ul></section>` : ''}
      <p class="muted small">Collector last ran ${K.collectorLastRun ? esc(K.collectorLastRun.replace('T', ' ').slice(0, 16)) + ' UTC' : 'never'} · following ${K.analysts.map(a => '@' + esc(a.handle)).join(', ')}</p>`;
    const sel = $('#memo-pick');
    if (sel) sel.addEventListener('change', () => { deskIdx = +sel.value; renderDesk(); window.scrollTo(0, 0); });
  }

  // ---------- drawer ----------
  function openCompany(t) {
    const c = byTicker[t]; if (!c) return;
    const l = byLayer[c.layer] || {};
    const narrs = D.narratives.filter(n => n.companies.includes(t));
    const dl = devsFor(t);
    $('#drawer').innerHTML = `
      <div class="drawer-head" style="--stage: var(--${esc(l.stage || 'supply')})">
        <div><div class="t">${c.listed === false ? 'PRIVATE' : esc(c.ticker)} · ${esc(c.hq)}</div><h2>${esc(c.name)}</h2>
          <div class="sub"><a href="#map" data-layer="${esc(l.id)}">${esc(l.name)}</a></div></div>
        <button class="close" aria-label="Close">×</button>
      </div>
      <p class="what">${esc(c.what)}</p>
      <p class="role">${esc(c.role)}</p>
      <div class="two">
        <div class="case"><h4>Bull</h4><p>${esc(c.bull)}</p></div>
        <div class="counter"><h4>Bear</h4><p>${esc(c.bear)}</p></div>
      </div>
      <div class="watch"><b>What would change the picture.</b> ${esc(c.watch)}</div>
      <div class="block"><h4>Sourced facts</h4>
        <ul class="facts">${c.facts.map(f => `<li><span class="asof">${esc(fmtDate(f.asOf))}</span>${esc(f.text)}<a href="${esc(f.source)}" target="_blank" rel="noopener">${esc(host(f.source))} ↗</a></li>`).join('') || '<li class="muted">No sourced facts logged yet. The dossier above is context, not evidence.</li>'}</ul></div>
      <div class="block"><h4>Narratives</h4><div class="narrlinks">${narrs.map(n => `<a href="#n/${esc(n.id)}">${esc(n.title)}</a>`).join('') || '<span class="muted">None.</span>'}</div></div>
      <div class="block"><h4>Developments (${dl.length})</h4>
        <ul class="devlist">${dl.slice(0, 12).map(d => `<li><time>${fmtDate(d.date)}</time>${esc(d.title)} <a href="${esc(d.source)}" target="_blank" rel="noopener">↗</a></li>`).join('') || '<li class="muted">None logged.</li>'}</ul>
        ${dl.length > 12 ? `<p style="margin-top:8px"><a href="#timeline" data-q="${esc(t)}">All ${dl.length} →</a></p>` : ''}</div>`;
    $('#drawer').hidden = false; $('#backdrop').hidden = false;
    $('#drawer').scrollTop = 0;
    document.body.style.overflow = 'hidden';
  }
  function closeDrawer(silent) {
    $('#drawer').hidden = true; $('#backdrop').hidden = true;
    document.body.style.overflow = '';
    if (!silent && location.hash.startsWith('#c/')) history.replaceState(null, '', '#' + view);
  }

  // ---------- routing ----------
  let view = 'desk';
  function showView(v) {
    if (v !== view) window.scrollTo(0, 0);
    view = v;
    ['desk', 'map', 'narratives', 'timeline'].forEach(id => { $('#view-' + id).hidden = id !== v; });
    document.querySelectorAll('.tabs a').forEach(a => a.classList.toggle('on', a.dataset.view === v));
    render();
  }
  function render() {
    const q = $('#q').value.trim();
    if (view === 'desk') renderDesk();
    else if (view === 'map') renderMap(q);
    else if (view === 'narratives') renderNarratives(pendingNarr);
    else renderTimeline(q);
  }
  let pendingNarr = '';
  function route() {
    const h = location.hash.replace(/^#/, '');
    if (h.startsWith('c/')) { if ($('#view-' + view).hidden) showView(view); openCompany(decodeURIComponent(h.slice(2))); return; }
    closeDrawer(true);
    if (h.startsWith('n/')) { pendingNarr = decodeURIComponent(h.slice(2)); showView('narratives'); pendingNarr = ''; const el = $('#narr-' + CSS.escape(h.slice(2))); if (el) el.scrollIntoView({ block: 'start' }); return; }
    if (h.startsWith('timeline')) { tlNarr = h.includes('/') ? decodeURIComponent(h.split('/')[1]) : ''; showView('timeline'); return; }
    if (h === 'narratives') { showView('narratives'); return; }
    if (h === 'map') { showView('map'); return; }
    showView('desk');
  }

  // ---------- events ----------
  document.addEventListener('click', e => {
    const chipEl = e.target.closest('.chip');
    if (chipEl) { location.hash = 'c/' + encodeURIComponent(chipEl.dataset.t); return; }
    const tag = e.target.closest('[data-n]');
    if (tag) { tlNarr = tag.dataset.n; if (view !== 'timeline') location.hash = 'timeline' + (tlNarr ? '/' + tlNarr : ''); else { history.replaceState(null, '', '#timeline' + (tlNarr ? '/' + tlNarr : '')); render(); } return; }
    if (e.target.closest('.close') || e.target === $('#backdrop')) { closeDrawer(); return; }
    const ql = e.target.closest('a[data-q]');
    if (ql) { $('#q').value = ql.dataset.q; }
    const ll = e.target.closest('a[data-layer]');
    if (ll) { closeDrawer(true); setTimeout(() => { const el = $('#layer-' + CSS.escape(ll.dataset.layer)); if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); }, 0); }
  });
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape' && !$('#drawer').hidden) closeDrawer();
    if (e.key === '/' && document.activeElement !== $('#q')) { e.preventDefault(); $('#q').focus(); }
  });
  $('#q').addEventListener('input', () => { if (view === 'narratives' || view === 'desk') showView('map'); else render(); });
  $('#q').addEventListener('keydown', e => {
    if (e.key !== 'Enter') return;
    const q = $('#q').value.trim(); if (!q) return;
    const hits = D.companies.filter(c => matches(c, q));
    const exact = hits.find(c => c.ticker.toLowerCase() === q.toLowerCase());
    if (exact || hits.length === 1) location.hash = 'c/' + encodeURIComponent((exact || hits[0]).ticker);
  });
  window.addEventListener('hashchange', route);

  // ---------- boot ----------
  $('#meta').textContent = `${D.companies.length} companies · ${D.layers.length} layers · ${D.narratives.length} narratives · ${D.developments.length} dated developments · updated ${fmtDate(D.meta.updated)}`;
  $('#foot').textContent = D.meta.disclaimer;
  document.title = D.meta.title;
  route();
})();
