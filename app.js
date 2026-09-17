// AI Infrastructure Explorer — all page logic. Reads window.DATA (data.js), renders
// three views (map, narratives, timeline) and a company drawer. Hash-routed so
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
  let view = 'map';
  function showView(v) {
    if (v !== view) window.scrollTo(0, 0);
    view = v;
    ['map', 'narratives', 'timeline'].forEach(id => { $('#view-' + id).hidden = id !== v; });
    document.querySelectorAll('.tabs a').forEach(a => a.classList.toggle('on', a.dataset.view === v));
    render();
  }
  function render() {
    const q = $('#q').value.trim();
    if (view === 'map') renderMap(q);
    else if (view === 'narratives') renderNarratives(pendingNarr);
    else renderTimeline(q);
  }
  let pendingNarr = '';
  function route() {
    const h = location.hash.replace(/^#/, '');
    if (h.startsWith('c/')) { if ($('#view-' + view).hidden) showView('map'); openCompany(decodeURIComponent(h.slice(2))); return; }
    closeDrawer(true);
    if (h.startsWith('n/')) { pendingNarr = decodeURIComponent(h.slice(2)); showView('narratives'); pendingNarr = ''; const el = $('#narr-' + CSS.escape(h.slice(2))); if (el) el.scrollIntoView({ block: 'start' }); return; }
    if (h.startsWith('timeline')) { tlNarr = h.includes('/') ? decodeURIComponent(h.split('/')[1]) : ''; showView('timeline'); return; }
    if (h === 'narratives') { showView('narratives'); return; }
    showView('map');
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
  $('#q').addEventListener('input', () => { if (view === 'narratives') showView('map'); else render(); });
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
