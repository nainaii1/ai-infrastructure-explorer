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

  // `deco` (map lenses) is { cls, badge } added to the chip.
  function chip(c, small, deco) {
    const label = c.listed === false ? esc(c.name) : esc(c.ticker);
    return `<button class="chip${small ? ' sm' : ''}${c.listed === false ? ' private' : ''}${deco && deco.cls ? ' ' + deco.cls : ''}" data-t="${esc(c.ticker)}" title="${esc(c.name)}"><b>${label}</b>${c.listed === false ? '' : `<span>${esc(c.name)}</span>`}${deco && deco.badge ? `<i class="lb">${deco.badge}</i>` : ''}</button>`;
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

  // ---------- map, with lenses that lay the desk over the chain ----------
  // plain: the guide · desk: what the desk holds or watches · mood: analysts' live stances · news: logged developments
  const LENSES = {
    plain: { label: 'Plain', note: 'The chain as the guide describes it.' },
    desk: { label: 'My book', note: 'Names on the latest memo: green ring = accumulate call, blue = holding, dashed = watch. Shows where the book is concentrated.' },
    mood: { label: 'Analyst mood', note: `Live stances from the roster (seen in the last ${45} days): ▲ bull, ▼ bear. Green = net bull, red = net bear, amber = split.` },
    news: { label: 'News flow', note: 'Dated developments logged in the last 90 days. Darker = busier.' }
  };
  if (!(window.DESK && DESK.memos && DESK.memos.length)) { delete LENSES.desk; delete LENSES.mood; } // public site: no desk data
  let lens = 'plain';
  try { lens = localStorage.getItem('aie-lens') || 'plain'; } catch (e) { /* storage blocked: default lens */ }
  if (!LENSES[lens]) lens = 'plain';
  function daysAgo(n) { return new Date(Date.now() - n * 864e5).toISOString().slice(0, 10); }
  let lensData = null;
  function lensIndex() {
    if (lensData) return lensData;
    const act = {}, mood = {}, news = {};
    if (window.DESK && DESK.memos && DESK.memos.length) {
      DESK.memos[0].accumulate.forEach(a => { act[a.ticker] = a.action; });
      const cut = daysAgo(45);
      (DESK.track || []).forEach(a => a.rows.forEach(r => {
        if (r.ended || r.lastSeen < cut) return;
        const m = mood[r.ticker] = mood[r.ticker] || { bull: 0, bear: 0, mixed: 0, who: [] };
        m[r.stance]++; m.who.push(`@${r.handle} ${r.stance}`);
      }));
    }
    const cut90 = daysAgo(90);
    devs.forEach(d => { if (d.date >= cut90 && d.date <= today) d.companies.forEach(t => { news[t] = (news[t] || 0) + 1; }); });
    return (lensData = { act, mood, news });
  }
  const ACT_SHORT = { accumulate: 'call', holding: 'holding', watch: 'watch', trim: 'trim', avoid: 'avoid' };
  function lensDeco(t) {
    const L = lensIndex();
    if (lens === 'desk' && L.act[t]) return { cls: 'lz-' + L.act[t], badge: ACT_SHORT[L.act[t]] };
    if (lens === 'mood' && L.mood[t]) {
      const m = L.mood[t], net = m.bull - m.bear;
      return { cls: net > 0 ? 'lm-bull' : net < 0 ? 'lm-bear' : 'lm-split', badge: `${m.bull ? m.bull + '▲' : ''}${m.bear ? ' ' + m.bear + '▼' : ''}${m.mixed ? ' ' + m.mixed + '◆' : ''}`.trim() };
    }
    if (lens === 'news' && L.news[t]) { const n = L.news[t]; return { cls: 'ln-' + (n >= 6 ? 3 : n >= 3 ? 2 : 1), badge: String(n) }; }
    return lens === 'plain' ? null : { cls: 'l-dim' };
  }
  // One number per layer for the strip and the layer header.
  function layerStat(l) {
    const L = lensIndex(), ts = D.companies.filter(c => c.layer === l.id).map(c => c.ticker);
    if (lens === 'desk') {
      const n = { accumulate: 0, holding: 0, watch: 0 }; ts.forEach(t => { if (n[L.act[t]] != null) n[L.act[t]]++; });
      const parts = [n.accumulate && `${n.accumulate} call${n.accumulate > 1 ? 's' : ''}`, n.holding && `${n.holding} holding${n.holding > 1 ? 's' : ''}`, n.watch && `${n.watch} watch`].filter(Boolean);
      return { v: n.accumulate + n.holding, text: parts.join(' · ') || 'nothing on the book' };
    }
    if (lens === 'mood') {
      let b = 0, r = 0; ts.forEach(t => { if (L.mood[t]) { b += L.mood[t].bull; r += L.mood[t].bear; } });
      return { v: b + r, net: b - r, text: b + r ? `${b}▲ ${r}▼` : 'no live stances' };
    }
    if (lens === 'news') { const n = ts.reduce((s, t) => s + (L.news[t] || 0), 0); return { v: n, text: `${n} in 90 days` }; }
    return { v: ts.length, text: `${ts.length} companies` };
  }

  // ---------- pictograms, flow map and motion (Nov 2026) ----------
  const REDUCED = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  const ICON = {
    demand: '<path d="M7 18h10a4 4 0 0 0 .5-7.97A5.5 5.5 0 0 0 7 9.5 4.25 4.25 0 0 0 7 18z"/>',
    neoclouds: '<rect x="4" y="5" width="16" height="5" rx="1"/><rect x="4" y="14" width="16" height="5" rx="1"/><path d="M7 7.5h.01M7 16.5h.01"/>',
    accelerators: '<rect x="7" y="7" width="10" height="10" rx="1"/><rect x="10" y="10" width="4" height="4"/><path d="M9 3v4M15 3v4M9 17v4M15 17v4M3 9h4M3 15h4M17 9h4M17 15h4"/>',
    systems: '<rect x="4" y="4" width="16" height="16" rx="1.5"/><path d="M4 9h16M4 14h16M7 6.5h.01M7 11.5h.01M7 16.5h.01"/>',
    networking: '<circle cx="12" cy="5" r="2"/><circle cx="5" cy="18" r="2"/><circle cx="19" cy="18" r="2"/><path d="M12 7v4M12 11l-6 5M12 11l6 5"/>',
    optics: '<path d="M3 12h8M13 12l8-6M13 12h8M13 12l8 6"/><circle cx="12" cy="12" r="1.6"/>',
    memory: '<rect x="4" y="4" width="16" height="4" rx="1"/><rect x="4" y="10" width="16" height="4" rx="1"/><rect x="4" y="16" width="16" height="4" rx="1"/>',
    foundry: '<circle cx="12" cy="12" r="8.5"/><path d="M12 3.5v17M3.5 12h17M6 6l12 12"/>',
    equipment: '<path d="M12 3v6M8 9h8l-2 4h-4zM12 13v8M8 21h8"/>',
    materials: '<path d="M12 3l7 6-3 12H8L5 9z"/><path d="M5 9h14M12 3l-3 6 3 12 3-12z"/>',
    power: '<path d="M13 3L5 14h6l-1 7 8-11h-6z"/>'
  };
  const icon = (id, size) => `<svg class="ico" width="${size || 20}" height="${size || 20}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">${ICON[id] || ''}</svg>`;
  const FLOW_NODES = {
    demand: [100, 110, 'Labs & hyperscalers'], neoclouds: [100, 250, 'Neoclouds'],
    accelerators: [380, 70, 'Accelerators'], systems: [380, 180, 'Systems'], networking: [380, 290, 'Networking'],
    foundry: [640, 70, 'Foundry & packaging'], memory: [640, 180, 'Memory'], optics: [640, 290, 'Optics & lasers'],
    equipment: [830, 70, 'Fab equipment'], materials: [830, 180, 'Substrates'], power: [830, 290, 'Power & cooling']
  };
  const FLOW_EDGES = [['demand', 'accelerators'], ['demand', 'networking'], ['neoclouds', 'accelerators'], ['neoclouds', 'systems'],
    ['accelerators', 'foundry'], ['accelerators', 'memory'], ['systems', 'memory'], ['networking', 'optics'], ['systems', 'power'],
    ['foundry', 'equipment'], ['foundry', 'materials'], ['memory', 'materials'], ['optics', 'power']];
  function flowMap(stats, heat) {
    const R = 27;
    const paths = FLOW_EDGES.map(([a, b], i) => {
      const [x1, y1] = FLOW_NODES[a], [x2, y2] = FLOW_NODES[b], mx = (x1 + x2) / 2;
      return { d: `M${x1 + R} ${y1} C${mx} ${y1} ${mx} ${y2} ${x2 - R} ${y2}`, i, st: (D.layers.find(l => l.id === b) || {}).stage };
    });
    const edges = paths.map(p => `<path class="fedge" id="fe${p.i}" d="${p.d}"/>`).join('');
    const dots = REDUCED ? '' : paths.map(p => `<circle class="fdot" r="2.6"><animateMotion dur="${(5 + (p.i % 4) * 1.1).toFixed(1)}s" begin="-${(p.i * 0.9).toFixed(1)}s" repeatCount="indefinite"><mpath href="#fe${p.i}"/></animateMotion></circle>`).join('');
    const nodes = D.layers.map(l => {
      const n = FLOW_NODES[l.id]; if (!n) return '';
      const s = stats[l.id], h = heat(s), tone = lens === 'mood' && s.v ? (s.net > 0 ? 'bull' : s.net < 0 ? 'bear' : 'split') : '';
      return `<g class="fnode${tone ? ' t-' + tone : ''}" data-layer="${esc(l.id)}" data-stage="${esc(l.stage)}" tabindex="0" role="button" aria-label="${esc(l.name)}: ${esc(s.text)}" transform="translate(${n[0]} ${n[1]})">
        ${lens !== 'plain' ? `<circle class="fheat" r="${(R + 5 + h * 15).toFixed(1)}" style="opacity:${(0.15 + h * 0.55).toFixed(2)}"/>` : ''}
        <circle class="fbody" r="${R}"/><g transform="translate(-12 -12)" class="fico" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">${ICON[l.id] || ''}</g>
        <text class="fname" y="${R + 15}" text-anchor="middle">${esc(n[2])}</text><text class="fstat" y="${R + 28}" text-anchor="middle">${esc(s.text)}</text></g>`;
    }).join('');
    const cols = [['DEMAND', 100, 'demand'], ['COMPUTE', 380, 'compute'], ['SUPPLY', 735, 'supply']].map(([t, x, st]) => `<text class="fcol" data-stage="${st}" x="${x}" y="16" text-anchor="middle">${t}</text>`).join('');
    return `<div class="flowmap"><svg viewBox="0 0 940 372" role="group" aria-label="Flow map of the AI supply chain: spending flows from demand through compute to supply">
      ${cols}${edges}${dots}${nodes}</svg>
      <div class="flow-cap" id="flow-cap" aria-live="polite"><span class="muted">Dots show capex flowing from the buyers of compute down to the physical inputs. Hover or focus a layer to read its constraint; click to jump to it.</span></div></div>`;
  }
  // Reveal on scroll and draw price lines in as they come into view. Everything is visible without JS motion.
  let revealIO = null, drawIO = null;
  function motion(root) {
    if (REDUCED || !('IntersectionObserver' in window)) return;
    if (revealIO) revealIO.disconnect(); if (drawIO) drawIO.disconnect();
    revealIO = new IntersectionObserver(es => es.forEach(e => { if (e.isIntersecting) { e.target.classList.add('in'); revealIO.unobserve(e.target); } }), { rootMargin: '0px 0px -8% 0px' });
    const below = [];
    root.querySelectorAll('.dsec, .idea, .event, .layer, .cp-row').forEach(el => { if (el.getBoundingClientRect().top > window.innerHeight * 0.9) { el.classList.add('rv'); below.push(el); revealIO.observe(el); } });
    setTimeout(() => below.forEach(el => el.classList.add('in')), 2500);
    drawIO = new IntersectionObserver(es => es.forEach(e => {
      if (!e.isIntersecting) return; const p = e.target; drawIO.unobserve(p);
      let len = 0; try { len = p.getTotalLength(); } catch (err) { return; }
      if (!len) return;
      p.style.transition = 'none'; p.style.strokeDasharray = len; p.style.strokeDashoffset = len; p.getBoundingClientRect();
      p.style.transition = 'stroke-dashoffset 1.3s cubic-bezier(.25,.6,.2,1)'; p.style.strokeDashoffset = 0;
      setTimeout(() => { p.style.strokeDasharray = ''; p.style.strokeDashoffset = ''; p.style.transition = ''; }, 1500);
    }), { threshold: 0.2 });
    root.querySelectorAll('svg path.pl, svg path.cl').forEach(p => drawIO.observe(p));
  }
  // The tape: every name on the list, its last price and its zone, scrolling slowly.
  function tape(m) {
    const items = m.accumulate.map(a => {
      const lv = LV[a.ticker] || (a.levels && Object.assign({ action: a.action }, a.levels)), q = (K.quotes || {})[a.ticker];
      if (!lv || !q || q.price == null) return '';
      const watch = a.action === 'watch', z = watch ? (q.price <= lv.buyBelow ? 'buy' : 'hold') : zoneOf(q.price, lv);
      return `<span class="tp act-${esc(a.action)} z-${z}"><b>${esc(shortT(a.ticker))}</b> ${num(q.price)} <i>${watch ? (z === 'buy' ? 'at revisit' : 'watch') : ZSHORT[z]}</i></span>`;
    }).join('');
    return items ? `<div class="tape" aria-hidden="true"><div class="tape-in">${items}${items}</div></div>` : '';
  }

  function renderMap(q) {
    const stats = {}; let max = 1;
    D.layers.forEach(l => { stats[l.id] = layerStat(l); max = Math.max(max, stats[l.id].v); });
    const heat = s => lens === 'plain' ? 0 : s.v / max;
    const bar = `<div class="lens-bar" role="group" aria-label="Map lens">${Object.keys(LENSES).map(k => `<button data-lens="${k}" class="${lens === k ? 'on' : ''}">${LENSES[k].label}</button>`).join('')}<span class="lens-note">${esc(LENSES[lens].note)}</span></div>`;
    const strip = q ? '' : `<div class="strip">${['demand', 'compute', 'supply'].map(st => `<div class="strip-stage" data-stage="${st}"><div class="strip-label">${st}</div><div class="strip-cells">${D.layers.filter(l => l.stage === st).map(l => {
      const s = stats[l.id], tone = lens === 'mood' && s.v ? (s.net > 0 ? 'bull' : s.net < 0 ? 'bear' : 'split') : '';
      return `<button class="cell${tone ? ' t-' + tone : ''}" data-layer="${esc(l.id)}" style="--h:${heat(s).toFixed(2)}" title="${esc(l.constraint)}"><b>${esc(l.name)}</b><span>${esc(s.text)}</span></button>`;
    }).join('')}</div></div>`).join('<div class="strip-arrow" aria-hidden="true">→</div>')}</div>`;
    const flow = q ? '' : flowMap(stats, heat);
    const out = [];
    let lastStage = null;
    D.layers.forEach(l => {
      const cos = D.companies.filter(c => c.layer === l.id && matches(c, q));
      if (q && !cos.length) return;
      if (lastStage && lastStage !== l.stage && !q) out.push('<div class="flow">▼ feeds into ▼</div>');
      lastStage = l.stage;
      out.push(`<section class="layer" data-stage="${esc(l.stage)}" id="layer-${esc(l.id)}">
        <div class="layer-head">${icon(l.id, 22)}<h2>${esc(l.name)}</h2><span class="stage-tag">${esc(l.stage)}</span>${lens !== 'plain' ? `<span class="layer-stat">${esc(stats[l.id].text)}</span>` : ''}</div>
        <p class="layer-summary">${esc(l.summary)}</p>
        <p class="layer-constraint"><b>Constraint.</b> ${esc(l.constraint)}</p>
        <div class="chips">${cos.map(c => chip(c, false, lensDeco(c.ticker))).join('')}</div>
        <p class="layer-watch"><b>Watch:</b> ${esc(l.watch)}</p>
      </section>`);
    });
    $('#map').innerHTML = bar + flow + strip + (out.join('') || '<p class="empty">No company matches.</p>');
    motion($('#map'));
  }

  // ---------- narratives ----------
  // Pulse: developments per week over the last 12 weeks, for one narrative.
  const dayN = iso => Math.floor(Date.parse(iso) / 864e5);
  function pulse(id) {
    const t = dayN(today), wk = Array(12).fill(0);
    devs.forEach(d => { if (!d.narratives.includes(id)) return; const k = Math.floor((t - dayN(d.date)) / 7); if (k >= 0 && k < 12) wk[11 - k]++; });
    const mx = Math.max(1, ...wk), total = wk.reduce((a, b) => a + b, 0), last4 = wk.slice(8).reduce((a, b) => a + b, 0), prev4 = wk.slice(4, 8).reduce((a, b) => a + b, 0);
    const bars = wk.map((v, i) => `<rect x="${i * 9}" y="${(26 - (v / mx) * 24).toFixed(1)}" width="6" height="${Math.max(v ? 2 : 1, (v / mx) * 24).toFixed(1)}" rx="1.5" class="${v ? 'pb' : 'pb0'}"/>`).join('');
    const dir = last4 > prev4 ? 'up' : last4 < prev4 ? 'down' : 'flat';
    return { total, dir, svg: `<svg class="pulse" width="106" height="28" viewBox="0 0 106 28" role="img" aria-label="${total} developments in the last 12 weeks">${bars}</svg>`, last4, prev4 };
  }
  const SHORTN = { 'memory-squeeze': 'Memory squeeze', 'laser-shortage': 'Laser shortage', 'copper-to-optics': 'Copper to optics', 'custom-silicon': 'Custom silicon', financing: 'Financing', 'power-constraint': 'Power', packaging: 'Packaging', 'gpu-residual': 'GPU residuals', china: 'China' };
  function overlap() {
    const cols = D.narratives, rows = D.companies.map(c => ({ c, ns: cols.filter(n => n.companies.includes(c.ticker)) })).filter(r => r.ns.length >= 2).sort((a, b) => b.ns.length - a.ns.length || a.c.name.localeCompare(b.c.name));
    if (!rows.length) return '';
    return `<section class="overlap"><h2>Who sits in several storylines</h2>
      <p class="muted small">A company in many columns is exposed to many of these bets at once, so one development can move several stories. Click a name for its dossier.</p>
      <div class="scroll"><table class="ovt"><thead><tr><th></th>${cols.map(n => `<th class="ovh"><span>${esc(SHORTN[n.id] || n.title)}</span></th>`).join('')}<th class="ovn">#</th></tr></thead>
      <tbody>${rows.map(r => `<tr><td>${chip(r.c, true)}</td>${cols.map(n => `<td class="ovc">${r.ns.includes(n) ? `<i class="dot s-${esc(n.status)}" title="${esc(n.title)} · ${esc(n.status)}"></i>` : ''}</td>`).join('')}<td class="ovn">${r.ns.length}</td></tr>`).join('')}</tbody></table></div></section>`;
  }
  function renderNarratives(openId) {
    $('#narratives').innerHTML = `<p class="muted small ngrid-note">Bars count developments <b>this guide has logged</b> per week over 12 weeks. They show how much the guide has recorded on each storyline, not how much news exists; the latest entry is ${esc(fmtDate(devs[0].date))}.</p><div class="ngrid">${D.narratives.map(n => {
      const p = pulse(n.id), lastDev = devs.find(d => d.narratives.includes(n.id));
      return `<button class="ncard s-${esc(n.status)}" data-narr="${esc(n.id)}"><span class="pill ${esc(n.status)}">${esc(n.status)}</span><b>${esc(SHORTN[n.id] || n.title)}</b>${p.svg}<small>${p.total} logged in 12 weeks · ${p.dir === 'up' ? '▲ more logged lately' : p.dir === 'down' ? '▼ fewer logged lately' : '● steady'}</small><small class="muted">${n.companies.length} companies${lastDev ? ' · last ' + fmtDate(lastDev.date) : ''}</small></button>`;
    }).join('')}</div>` + D.narratives.map(n => {
      const recent = devs.filter(d => d.narratives.includes(n.id)).slice(0, 6), p = pulse(n.id);
      return `<details class="narr" id="narr-${esc(n.id)}"${openId === n.id ? ' open' : ''}>
        <summary><h2>${esc(n.title)}</h2><span class="pill ${esc(n.status)}">${esc(n.status)}</span><p>${esc(n.summary)}</p><div class="npulse">${p.svg}<span class="muted small">${p.total} logged in the last 12 weeks (${p.last4} in the last 4, ${p.prev4} in the 4 before)</span></div></summary>
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
    }).join('') + overlap();
  }

  // ---------- timeline ----------
  let tlNarr = '';
  // Lanes: one row per narrative, one dot per development, on a shared time axis. Click a dot to jump to it.
  function lanes() {
    const NS = D.narratives, W = 940, L = 150, R = 16, T = 22, ROW = 28, H = T + NS.length * ROW + 24;
    const t0 = dayN(devs[devs.length - 1].date), tN = dayN(today), t1 = Math.max(tN, dayN(devs[0].date)) + 4;
    const x = iso => L + (dayN(iso) - t0) / (t1 - t0) * (W - L - R);
    let months = '';
    for (let d = new Date(Date.UTC(+devs[devs.length - 1].date.slice(0, 4), +devs[devs.length - 1].date.slice(5, 7) - 1, 1)); dayN(d.toISOString().slice(0, 10)) <= t1; d.setUTCMonth(d.getUTCMonth() + 1)) {
      const iso = d.toISOString().slice(0, 10), xx = x(iso); if (xx < L) continue;
      months += `<line class="lg" x1="${xx.toFixed(1)}" x2="${xx.toFixed(1)}" y1="${T - 6}" y2="${H - 22}"/><text class="lm" x="${(xx + 4).toFixed(1)}" y="${T - 8}">${MONTHS[d.getUTCMonth()]}</text>`;
    }
    const rows = NS.map((n, i) => {
      const y = T + i * ROW + ROW / 2, col = `var(--s${(i % 8) + 1})`, on = !tlNarr || tlNarr === n.id;
      const mine = devs.map((d, k) => [d, k]).filter(([d]) => d.narratives.includes(n.id));
      return `<g class="lane${on ? '' : ' dim'}"><text class="ll" x="${L - 10}" y="${y + 4}" text-anchor="end" data-n="${esc(n.id)}" role="button" tabindex="0">${esc(SHORTN[n.id] || n.title)}</text>
        <line class="lrow" x1="${L}" x2="${W - R}" y1="${y}" y2="${y}"/>
        ${mine.map(([d, k]) => `<circle class="ldot${d.date > today ? ' fut' : ''}" cx="${x(d.date).toFixed(1)}" cy="${y}" r="5" style="--c:${col}" data-dev="${k}" tabindex="0" role="button" aria-label="${esc(d.date + ': ' + d.title)}"><title>${esc(fmtDate(d.date) + ': ' + d.title)}</title></circle>`).join('')}</g>`;
    }).join('');
    const tx = x(today).toFixed(1);
    return `<div class="scroll"><svg class="lanes" viewBox="0 0 ${W} ${H}" role="group" aria-label="Developments by narrative over time">${months}${rows}<line class="ltoday" x1="${tx}" x2="${tx}" y1="${T - 6}" y2="${H - 22}"/><text class="lm" x="${tx}" y="${H - 8}" text-anchor="middle">today</text></svg></div>
      <p class="muted small lanes-note">Each dot is one dated development. Click a dot to jump to it, or a storyline name to filter the list.</p>`;
  }
  function renderTimeline(q) {
    $('#tl-lanes').innerHTML = q ? '' : lanes();
    $('#tl-filters').innerHTML = [`<button data-n="" class="${tlNarr ? '' : 'on'}">All</button>`]
      .concat(D.narratives.map(n => `<button data-n="${esc(n.id)}" class="${tlNarr === n.id ? 'on' : ''}">${esc(n.title)}</button>`)).join('');
    const list = devs.filter(d => (!tlNarr || d.narratives.includes(tlNarr)) &&
      (!q || d.companies.some(t => byTicker[t] && matches(byTicker[t], q)) || d.title.toLowerCase().includes(q.toLowerCase())));
    const out = []; let month = null;
    list.forEach(d => {
      const m = d.date.slice(0, 7);
      if (m !== month) { month = m; out.push(`<div class="month">${d.date > today ? 'Upcoming · ' : ''}${fmtMonth(d.date)}</div>`); }
      out.push(`<article class="dev${d.date > today ? ' future' : ''}" id="dev-${devs.indexOf(d)}">
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
  function tick(t) { return byTicker[t] ? chip(byTicker[t], true) : `<button class="chip sm desk-only" data-t="${esc(t)}" title="${esc(nameOf(t))}"><b>${esc(t)}</b></button>`; }
  function pct(v) { return v == null ? '—' : `<span class="${v >= 0 ? 'up' : 'dn'}">${v >= 0 ? '+' : ''}${v.toFixed(1)}%</span>`; }
  function num(v) { return v == null ? '—' : v.toLocaleString('en-US', { maximumFractionDigits: 2 }); }
  function link(url, label) { return url ? `<a href="${esc(url)}" target="_blank" rel="noopener">${esc(label || host(url))} ↗</a>` : ''; }
  function paras(list) { return (list || []).map(p => `<p>${esc(p)}</p>`).join(''); }

  const ZONE = { add: 'In the add zone', buy: 'In the zone', hold: 'Above the zone: hold', above: "Above the zone: don't add", trim: 'Above the trim level' };
  function zoneOf(price, lv) {
    const top = lv.stopAbove || lv.buyBelow;
    if (lv.addBelow != null && price <= lv.addBelow) return 'add';
    if (price <= lv.buyBelow) return 'buy';
    if (price <= top) return 'hold';
    return lv.trimAbove != null && price > lv.trimAbove ? 'trim' : 'above';
  }
  // ---------- desk charts (daily closes from desk.js `history`, written by build.py) ----------
  const HIST = (K && K.history) || {};
  const LV = (K && K.levels) || {};
  const MYT = 8 * 3600e3;
  const todayMYT = new Date(Date.now() + MYT).toISOString().slice(0, 10);
  function fmtMYT(iso) {
    if (!iso) return '';
    const d = new Date(Date.parse(iso) + MYT), p = n => String(n).padStart(2, '0');
    return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]}, ${p(d.getUTCHours())}:${p(d.getUTCMinutes())} MYT`;
  }
  function dayDiff(a, b) { return Math.round((Date.parse(b) - Date.parse(a)) / 864e5); }
  function nameOf(t) {
    if (byTicker[t]) return byTicker[t].name;
    if (LV[t]) return LV[t].name;
    const a = K && K.memos && K.memos.length && K.memos[0].accumulate.find(x => x.ticker === t);
    return a ? a.name : t;
  }
  function shortT(t) { return t.replace(/\.(KS|HK)$/, ''); }
  // Closes for a ticker, with the latest sheet quote appended when it is newer than the last bar.
  function closes(t, days) {
    const h = (HIST[t] || []).slice(-(days || 9999));
    const q = K && (K.quotes || {})[t], qd = K && K.pricesAsOf && K.pricesAsOf.slice(0, 10);
    if (h.length && q && q.price != null && qd > h[h.length - 1][0]) h.push([qd, q.price]);
    return h;
  }
  const STRETCH = 8; // % in five sessions, the same rule as desk/support.py
  function stretchOf(t) {
    const h = HIST[t] || [], s = HIST[K.bench] || [];
    if (h.length < 7) return null;
    const m5 = (h[h.length - 1][1] / h[h.length - 6][1] - 1) * 100;
    const b5 = s.length > 6 ? (s[s.length - 1][1] / s[s.length - 6][1] - 1) * 100 : null;
    return { m5, b5, stretched: m5 > STRETCH };
  }

  // Hover layer: every chart registers its series; one tooltip serves them all.
  const CHARTS = {}; let chartSeq = 0;
  function regChart(spec) { const id = 'ch' + (++chartSeq); CHARTS[id] = spec; return id; }
  function onChartMove(e) {
    const svg = e.target.closest && e.target.closest('svg[data-ch]');
    const tip = $('#tip');
    if (!svg) { if (!tip.hidden) { tip.hidden = true; document.querySelectorAll('.hair').forEach(h => h.setAttribute('opacity', 0)); } return; }
    const c = CHARTS[svg.dataset.ch]; if (!c) return;
    const r = svg.getBoundingClientRect(), vx = (e.clientX - r.left) / r.width * c.W;
    const tm = c.t0 + (Math.max(c.x0, Math.min(c.x1, vx)) - c.x0) / (c.x1 - c.x0) * (c.t1 - c.t0);
    const rows = c.series.map(s => {
      let best = null; s.pts.forEach(p => { if (!best || Math.abs(p[0] - tm) < Math.abs(best[0] - tm)) best = p; });
      return best && Math.abs(best[0] - tm) < 6 * 864e5 ? { s, p: best } : null;
    }).filter(Boolean);
    if (!rows.length) { tip.hidden = true; return; }
    const at = rows[0].p[0], hx = c.x0 + (at - c.t0) / (c.t1 - c.t0) * (c.x1 - c.x0);
    const hair = svg.querySelector('.hair'); if (hair) { hair.setAttribute('x1', hx); hair.setAttribute('x2', hx); hair.setAttribute('opacity', 1); }
    tip.innerHTML = `<div class="tip-d">${fmtDate(new Date(at).toISOString().slice(0, 10))}</div>` +
      rows.map(({ s, p }) => `<div>${s.color ? `<span class="sw" style="background:${s.color}"></span>` : ''}${esc(s.label)} <b>${c.fmt(p[1])}</b></div>`).join('');
    tip.hidden = false;
    const tw = tip.offsetWidth, left = e.clientX + 14 + tw > window.innerWidth ? e.clientX - tw - 14 : e.clientX + 14;
    tip.style.left = left + 'px'; tip.style.top = (e.clientY + 14) + 'px';
  }

  // Price against the desk's zones: bands for add / buy / hold / stop adding / trim, the close as a line.
  // o = { w, h, days, labels, call, tight } · tight: scale to the closes and the buy line only (sparklines)
  function zoneChart(t, lv, o) {
    const bars = closes(t, o.days || 130);
    if (bars.length < 5 || !lv) return '';
    const watch = lv.action === 'watch' || lv.stopAbove == null;
    const W = o.w, H = o.h, L = 2, R = o.labels ? 96 : 3, T = 6, B = o.labels ? 18 : 3;
    const ts = bars.map(b => Date.parse(b[0])), vs = bars.map(b => b[1]);
    const buy = lv.buyBelow, add = lv.addBelow != null ? lv.addBelow : buy, top = lv.stopAbove || buy, trim = lv.trimAbove;
    let lo = o.tight ? Math.min(...vs, buy) : Math.min(...vs, add), hi = o.tight ? Math.max(...vs) : Math.max(...vs, top);
    if (o.call && o.call.refPrice) { lo = Math.min(lo, o.call.refPrice); hi = Math.max(hi, o.call.refPrice); }
    const trimIn = !o.tight && trim != null && trim <= hi * 1.2;
    if (trimIn) hi = Math.max(hi, trim);   // never let the line leave the frame
    const TA = o.labels && K && K.ta && K.ta.names ? K.ta.names[t] : null;
    const d0 = bars[0][0];
    const maRows = TA ? TA.support.concat(TA.resistance).filter(r => r.series && /^SMA (50|200)d$/.test(r.label)) : [];
    const tested = TA ? TA.support.filter(r => r.n > 0).slice(0, 2) : [];
    if (TA) {
      maRows.forEach(r => r.series.forEach(([d, v]) => { if (d >= d0) { lo = Math.min(lo, v); hi = Math.max(hi, v); } }));
      tested.forEach(r => { lo = Math.min(lo, r.value); hi = Math.max(hi, r.value); });
    }
    const pad = (hi - lo) * 0.07; lo -= pad; hi += pad;
    const t0 = ts[0], t1 = ts[ts.length - 1];
    const x = tm => L + (tm - t0) / (t1 - t0 || 1) * (W - L - R);
    const y = v => T + (hi - v) / (hi - lo) * (H - T - B);
    const cy = v => Math.max(T, Math.min(H - B, y(v)));
    const band = (a, b, cls) => { const y1 = cy(b), y2 = cy(a); return y2 - y1 > 0.4 ? `<rect class="${cls}" x="${L}" y="${y1.toFixed(1)}" width="${(W - L - R).toFixed(1)}" height="${(y2 - y1).toFixed(1)}"/>` : ''; };
    const bands = watch ? band(lo, buy, 'z-buy')
      : band(lo, add, 'z-add') + band(add, buy, 'z-buy') + band(buy, top, 'z-hold') + band(top, trim != null ? trim : hi, 'z-above') + (trim != null ? band(trim, hi, 'z-trim') : '');
    const line = vs.map((v, i) => `${i ? 'L' : 'M'}${x(ts[i]).toFixed(1)} ${y(v).toFixed(1)}`).join('');
    const last = vs[vs.length - 1];
    let labels = '', ticks = '', callMark = '';
    if (o.labels) {
      const lvls = (watch ? [['revisit', buy]] : [['add', add], ['buy', buy], ['stop', top]].concat(trimIn ? [['trim', trim]] : []))
        .filter((v, i, arr) => arr.findIndex(z => z[1] === v[1]) === i)
        .map(([k, v]) => ({ k, v, y: y(v) })).sort((a, b) => a.y - b.y);
      for (let i = 1; i < lvls.length; i++) if (lvls[i].y - lvls[i - 1].y < 12) lvls[i].y = lvls[i - 1].y + 12;
      labels = lvls.map(l => `<line class="lvl" x1="${L}" x2="${W - R}" y1="${y(l.v).toFixed(1)}" y2="${y(l.v).toFixed(1)}"/><text class="lt" x="${W - R + 6}" y="${(l.y + 3.5).toFixed(1)}">${esc(l.k)} ${num(l.v)}</text>`).join('') +
        (trim != null && !trimIn ? `<text class="lt" x="${W - R + 6}" y="${T + 8}">trim ${num(trim)} ↑</text>` : '');
      let mo = '';
      bars.forEach((b, i) => { const m = b[0].slice(0, 7); if (m !== mo) { mo = m; if (i > 2) ticks += `<line class="mt" x1="${x(ts[i]).toFixed(1)}" x2="${x(ts[i]).toFixed(1)}" y1="${T}" y2="${H - B}"/><text class="xt" x="${x(ts[i]).toFixed(1)}" y="${H - 4}">${MONTHS[+m.slice(5) - 1]}</text>`; } });
      if (o.call && o.call.refPrice && Date.parse(o.call.opened) >= t0) {
        const ox = x(Date.parse(o.call.opened));
        callMark = `<line class="cm" x1="${ox.toFixed(1)}" x2="${ox.toFixed(1)}" y1="${T}" y2="${H - B}"/><circle class="cmd" cx="${ox.toFixed(1)}" cy="${y(o.call.refPrice).toFixed(1)}" r="4"/><text class="lt cmt" x="${(ox + 6).toFixed(1)}" y="${H - B - 5}">call opened ${num(o.call.refPrice)}</text>`;
      }
    }
    function taOverlay() {
      if (!TA) return '';
      const mas = maRows.map(r => { const pts = r.series.filter(([d]) => d >= d0); return pts.length > 1 ? `<path class="ma ma${r.label.match(/\d+/)[0]}" d="${pts.map(([d, v], i) => `${i ? 'L' : 'M'}${x(Date.parse(d)).toFixed(1)} ${y(v).toFixed(1)}`).join('')}"/><text class="mal" x="${(x(Date.parse(pts[pts.length - 1][0])) - 4).toFixed(1)}" y="${(y(pts[pts.length - 1][1]) - 5).toFixed(1)}" text-anchor="end">${esc(r.label.replace('SMA ', ''))} MA</text>` : ''; }).join('');
      const tl = tested.map(r => `<line class="tl" x1="${L}" x2="${W - R}" y1="${y(r.value).toFixed(1)}" y2="${y(r.value).toFixed(1)}"/><text class="tlt" x="${L + 6}" y="${(y(r.value) - 5).toFixed(1)}">${esc(r.label)} ${num(r.value)} · held ${r.held}/${r.n}</text>`).join('');
      return mas + tl;
    }
    const id = regChart({ W, x0: L, x1: W - R, t0, t1, fmt: v => num(v) + ' ' + (lv.currency || ''), series: [{ label: shortT(t), pts: ts.map((tm, i) => [tm, vs[i]]) }] });
    return `<svg class="zc${o.labels ? ' big' : ''}" data-ch="${id}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(nameOf(t))}: ${bars.length} daily closes against the desk's zones; last ${num(last)}">
      ${bands}${ticks}${labels}${callMark}${taOverlay()}<path class="pl" d="${line}"/><circle class="pd" cx="${x(t1).toFixed(1)}" cy="${y(last).toFixed(1)}" r="${o.labels ? 4 : 3}"/>
      <line class="hair" x1="0" x2="0" y1="${T}" y2="${H - B}" opacity="0"/></svg>`;
  }

  // Each accumulate call's return minus SMH's, from the call's own reference prices, over daily closes.
  const SERIES = ['var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--s4)', 'var(--s5)', 'var(--s6)', 'var(--s7)', 'var(--s8)'];
  function callsChart() {
    const smh = closes(K.bench); if (!smh.length || !K.calls.length) return '';
    const smhAt = d => { let v = null; for (const [sd, sv] of smh) { if (sd > d) break; v = sv; } return v; };
    const series = K.calls.map((c, i) => {
      if (!c.refPrice || !c.benchRef) return null;
      const end = c.closed ? c.closed.date : '9999-12-31';
      const pts = closes(c.ticker).filter(([d]) => d >= c.opened && d <= end).map(([d, v]) => {
        const b = smhAt(d); return b ? [Date.parse(d), ((v / c.refPrice) - (b / c.benchRef)) * 100] : null;
      }).filter(Boolean);
      return pts.length > 1 ? { c, pts, color: SERIES[i % SERIES.length], label: shortT(c.ticker) + (c.closed ? ' (closed)' : '') } : null;
    }).filter(Boolean);
    if (!series.length) return '';
    const W = 420, H = 220, L = 30, R = 84, T = 10, B = 18;
    const all = series.flatMap(s => s.pts);
    const t0 = Math.min(...all.map(p => p[0])), t1 = Math.max(...all.map(p => p[0]));
    let lo = Math.min(0, ...all.map(p => p[1])), hi = Math.max(0, ...all.map(p => p[1]));
    const pad = (hi - lo) * 0.08; lo -= pad; hi += pad;
    const x = tm => L + (tm - t0) / (t1 - t0) * (W - L - R), y = v => T + (hi - v) / (hi - lo) * (H - T - B);
    const step = (hi - lo) > 40 ? 10 : 5; let grid = '';
    for (let g = Math.ceil(lo / step) * step; g <= hi; g += step) grid += `<line class="${g === 0 ? 'zero' : 'gl'}" x1="${L}" x2="${W - R}" y1="${y(g).toFixed(1)}" y2="${y(g).toFixed(1)}"/><text class="yt" x="${L - 5}" y="${(y(g) + 3.5).toFixed(1)}">${g > 0 ? '+' : ''}${g}</text>`;
    let mo = '', ticks = '';
    for (let tm = t0; tm <= t1; tm += 864e5) { const d = new Date(tm).toISOString().slice(0, 10), m = d.slice(0, 7); if (m !== mo && d.slice(8) === '01') { mo = m; ticks += `<text class="xt" x="${x(tm).toFixed(1)}" y="${H - 5}">${MONTHS[+m.slice(5) - 1]}</text>`; } }
    const ends = series.map(s => { const p = s.pts[s.pts.length - 1]; return { s, v: p[1], x: x(p[0]), y: y(p[1]) }; }).sort((a, b) => a.y - b.y);
    for (let i = 1; i < ends.length; i++) if (ends[i].y - ends[i - 1].y < 13) ends[i].y = ends[i - 1].y + 13;
    const lines = series.map(s => `<path class="cl${s.c.closed ? ' closed' : ''}" style="stroke:${s.color}" d="${s.pts.map((p, i) => `${i ? 'L' : 'M'}${x(p[0]).toFixed(1)} ${y(p[1]).toFixed(1)}`).join('')}"/>`).join('');
    const labels = ends.map(e => `<circle cx="${e.x.toFixed(1)}" cy="${y(e.v).toFixed(1)}" r="3.5" style="fill:${e.s.color}" class="ring"/><text class="el" x="${(W - R + 8).toFixed(1)}" y="${(e.y + 4).toFixed(1)}">${esc(shortT(e.s.c.ticker))} ${e.v >= 0 ? '+' : ''}${e.v.toFixed(1)}</text>`).join('');
    const id = regChart({ W, x0: L, x1: W - R, t0, t1, fmt: v => `${v >= 0 ? '+' : ''}${v.toFixed(1)} pts`, series: series.map(s => ({ label: s.label, color: s.color, pts: s.pts })) });
    return `<svg class="rc" data-ch="${id}" viewBox="0 0 ${W} ${H}" role="img" aria-label="Each call's return minus ${esc(K.bench)}'s since it opened, in percentage points">${grid}${ticks}${lines}${labels}<line class="hair" x1="0" x2="0" y1="${T}" y2="${H - B}" opacity="0"/><text class="zl" x="${L + 4}" y="${(y(0) - 4).toFixed(1)}">= ${esc(K.bench)}</text></svg>
      <div class="legend">${series.map(s => `<span><i style="background:${s.color}"></i>${esc(nameOf(s.c.ticker))}${s.c.closed ? ' · closed' : ''}</span>`).join('')}</div>`;
  }

  // The top of the Desk: every name against its zones, the calls against SMH, what is next, where the book sits.
  const ZSHORT = { add: 'Add zone', buy: 'Buy zone', hold: 'Hold', above: 'No adding', trim: 'Trim zone' };
  const GROUPS = [['accumulate', 'Calls'], ['holding', 'Holdings'], ['watch', 'Watch']];
  function cockpit(m) {
    const rows = m.accumulate.map(a => {
      const lv = LV[a.ticker] || (a.levels && Object.assign({ action: a.action, currency: '' }, a.levels));
      const q = (K.quotes || {})[a.ticker], price = q && q.price;
      if (!lv || price == null) return { a, html: '', d: 1e9 };
      const watch = a.action === 'watch', z = zoneOf(price, lv), d = (price / lv.buyBelow - 1) * 100, st = stretchOf(a.ticker);
      const zl = watch ? (price <= lv.buyBelow ? 'At revisit' : 'Above revisit') : ZSHORT[z];
      const zc = watch ? (price <= lv.buyBelow ? 'buy' : 'hold') : z;
      return { a, d, html: `<a class="cp-row act-${esc(a.action)}" href="#c/${encodeURIComponent(a.ticker)}">
        <div class="cp-id"><b>${esc(shortT(a.ticker))}</b><span>${esc(a.name)}</span></div>
        <div class="cp-chart">${zoneChart(a.ticker, lv, { w: 200, h: 44, days: 66, tight: true })}</div>
        <div class="cp-now"><b>${num(price)}</b><span class="zn ${zc}">${zl}</span></div>
        <div class="cp-dist"><span class="${d <= 0 ? 'up' : ''}">${d <= 0 ? 'in zone' : '+' + d.toFixed(1) + '%'}</span><small>${watch ? 'revisit' : 'buy line'} ${num(lv.buyBelow)}</small></div>
        <div class="cp-5d">${st ? `<span class="${st.m5 >= 0 ? 'up' : 'dn'}">${st.m5 >= 0 ? '+' : ''}${st.m5.toFixed(1)}%</span><small>5 sessions${st.stretched ? ' · <em class="flag">stretched</em>' : ''}</small>` : '<small>no history</small>'}</div>
      </a>` };
    });
    const zones = GROUPS.map(([act, label]) => {
      const g = rows.filter(r => r.a.action === act && r.html).sort((p, q) => p.d - q.d);
      return g.length ? `<div class="cp-group g-${act}">${label}</div>${g.map(r => r.html).join('')}` : '';
    }).join('');
    const bench = stretchOf(K.bench);

    const up = [];
    (m.market.calendar || []).forEach(x => { if (x.date >= todayMYT) up.push({ date: x.date, text: x.event, t: x.ticker, src: x.source }); });
    m.accumulate.forEach(a => { if (a.test && a.test.by && a.test.by >= todayMYT) up.push({ date: a.test.by, text: `Test due: ${a.test.metric}`, t: a.ticker, src: a.test.source }); });
    up.sort((p, q) => p.date.localeCompare(q.date));
    const listed = new Set(m.accumulate.map(a => a.ticker));
    const held = new Set(m.accumulate.filter(a => a.action === 'holding').map(a => a.ticker));
    const next = up.length ? `<ol class="next">${up.slice(0, 7).map(x => { const n = dayDiff(todayMYT, x.date); return `<li class="${x.t && listed.has(x.t) ? 'mine' : ''}${x.t && held.has(x.t) ? ' h' : ''}"><span class="cd"><b>${n === 0 ? 'today' : n === 1 ? '1 day' : n + ' days'}</b>${fmtDate(x.date)}</span><span>${x.t ? `<b class="tkr">${esc(shortT(x.t))}</b> ` : ''}${esc(x.text)} ${link(x.src)}</span></li>`; }).join('')}</ol>`
      : '<p class="muted small">Nothing dated after today in this memo. The next memo sets the calendar.</p>';

    const book = {};
    m.accumulate.filter(a => a.action === 'accumulate' || a.action === 'holding').forEach(a => {
      const l = byTicker[a.ticker] ? byTicker[a.ticker].layer : '_';
      (book[l] = book[l] || []).push(a);
    });
    const total = Object.values(book).reduce((s, v) => s + v.length, 0);
    const bookRows = D.layers.filter(l => book[l.id]).concat(book._ ? [{ id: '_', name: 'Outside the map', stage: 'none' }] : [])
      .sort((p, q) => book[q.id].length - book[p.id].length)
      .map(l => `<div class="bk" data-stage="${esc(l.stage)}"><span class="bk-l">${esc(l.name)}</span><span class="bk-u">${book[l.id].map(a => `<i class="u-${esc(a.action)}" title="${esc(a.name)} (${esc(a.action)})">${esc(shortT(a.ticker))}</i>`).join('')}</span><span class="bk-n">${Math.round(book[l.id].length / total * 100)}%</span></div>`).join('');

    return `<section class="cockpit" id="d-cockpit">
      <div class="cp-main dsec"><div class="cp-title"><h2>Where every name sits</h2><span class="muted small">Last ${66} sessions against the memo's zones · closest to its buy line first · prices ${esc(fmtMYT(K.pricesAsOf))}</span><button class="hold-toggle" data-hold aria-pressed="${hideHold}">${hideHold ? 'Show holdings' : 'Hide holdings'}</button></div>
        <div class="cp-key"><span><i class="k z-add"></i>add</span><span><i class="k z-buy"></i>buy</span><span><i class="k z-hold"></i>hold</span><span><i class="k z-above"></i>stop adding</span><span><i class="k z-trim"></i>trim</span>${bench ? `<span class="muted">${esc(K.bench)} 5 sessions ${bench.m5 >= 0 ? '+' : ''}${bench.m5.toFixed(1)}%</span>` : ''}</div>
        ${zones}</div>
      <div class="cp-side">
        <div class="dsec"><h2>Calls vs ${esc(K.bench)}</h2><p class="muted small">Each call's return minus ${esc(K.bench)}'s since it opened, in points. Above the line = beating the index. Daily closes.</p>${callsChart() || '<p class="muted small">No price history yet.</p>'}</div>
        <div class="dsec"><h2>Next up</h2>${next}</div>
        <div class="dsec"><h2>Where the book sits</h2><p class="muted small">Calls and holdings by layer of the chain, by count of names (not money). <span class="u-key u-accumulate">call</span> <span class="u-key u-holding">holding</span></p>${bookRows}</div>
      </div></section>`;
  }

  // ---------- command centre (desk.js `brain`, written by desk/build.py from desk/plan.py, money.py, setups.py) ----------
  // Money, tide, one card per name with its state and room to add, the trade lab and the voices. Amounts are private:
  // every RM figure sits in .amt and holdings carry .h, so "Hide holdings" removes both.
  const B = (K && K.brain) || {};
  const rm = v => v == null ? '—' : `<span class="amt">RM ${Math.round(v).toLocaleString('en-US')}</span>`;
  const TIDE = { in: 'Tide in', turning: 'Tide turning', out: 'Tide out', unknown: 'Tide unknown' };
  function ccCard(r) {
    const lv = LV[r.ticker], L = r.levels || {}, held = !!r.pos, cur = r.currency || '';
    let where = '';
    if (r.state === 'frozen') where = `Closed at ${num(r.frozen.close)} on ${fmtDate(r.frozen.since)}, below the break line ${num(r.frozen.line)}. No buying until it closes back above.`;
    else if (r.state === 'trigger') where = `Closed above the trigger ${num(L.buyAbove)}: the plan's buy-on-strength step.`;
    else if (r.state === 'exit1' || r.state === 'exit2') where = `Closed below your exit step ${r.state.slice(-1)} line ${num(L[r.state])}.`;
    else if (r.distBuy != null) where = r.distBuy <= 0 ? `In the zone: buy line ${num(L.buyBelow)}${L.addBelow != null ? `, add line ${num(L.addBelow)}` : ''}` : `${r.distBuy.toFixed(1)}% above its ${r.action === 'watch' ? 'revisit level' : 'buy line'} ${num(L.buyBelow)}`;
    const room = r.room ? (r.room.now > 0
      ? `<div class="nc-room go">Room now ${rm(r.room.now)} <span class="amt">· ${r.room.units} share${r.room.units === 1 ? '' : 's'}</span><small>step ${r.room.allowed} of ${r.room.steps} · ${esc(r.room.pot)} pot${r.room.ifBreaks ? ` · if it breaks: ${rm(r.room.ifBreaks)}` : ''}</small></div>`
      : `<div class="nc-room"><small>${r.state === 'frozen' ? 'Frozen: no room until it thaws' : `One step is ${rm(r.room.step)} from the ${esc(r.room.pot)} pot, when it reaches the buy line`}</small></div>`) : '';
    const pos = held ? `<div class="nc-pos amt">You hold ${num(r.pos.units)} at ${num(r.pos.avgCost)} · ${pct(r.pos.pl)} · worth ${rm(r.pos.value)}${r.pos.ofNetWorth != null ? ` (${r.pos.ofNetWorth}% of net worth)` : ''}${r.pos.toCost > 0 ? ` · needs +${r.pos.toCost}% to get back to cost` : ''}${r.pos.atUpside ? ` · at the upside case ${rm(r.pos.atUpside)} (+${r.pos.addsToNetWorth}% of net worth)` : ''}</div>` : '';
    return `<a class="nc st-${esc(r.state)}${held || r.action === 'holding' ? ' h' : ''}" href="#c/${encodeURIComponent(r.ticker)}">
      <div class="nc-top"><b>${esc(shortT(r.ticker))}</b><span>${esc(r.name.split(' (')[0])}</span><em class="stt">${esc(r.stateText)}</em></div>
      <div class="nc-px"><b>${r.price == null ? 'no price' : num(r.price) + ' ' + esc(cur)}</b>${r.swing ? `<small>typical day ±${r.swing}%</small>` : ''}${r.priceFrom && r.priceFrom !== 'sheet' ? `<small>${esc(r.priceFrom)}</small>` : ''}</div>
      ${lv && lv.buyBelow != null ? `<div class="nc-chart">${zoneChart(r.ticker, lv, { w: 280, h: 46, days: 66, tight: true })}</div>` : ''}
      <div class="nc-where">${where}${L.breakBelow != null && r.state !== 'frozen' ? ` · break line ${num(L.breakBelow)}` : ''}</div>
      ${room}${pos}
      ${r.note ? `<div class="nc-note">${esc(r.note)}</div>` : ''}
      ${r.next ? `<div class="nc-next"><b>${dayDiff(todayMYT, r.next.date) <= 0 ? 'today' : dayDiff(todayMYT, r.next.date) + 'd'}</b> ${esc(r.next.text)}</div>` : ''}
    </a>`;
  }
  function commandCentre() {
    if (!B.plan) return '';
    const cap = B.capital, td = B.tide || {}, S = B.setups || {}, P = B.plan;
    const pot = (k, label) => { const p = cap.pots[k], w = p.budget ? Math.round(p.free / p.budget * 100) : 0; return `<div class="pot"><span>${label}</span><b>${rm(p.free)}</b><i class="meter"><i style="width:${w}%"></i></i><small class="amt">free of ${Math.round(p.budget).toLocaleString('en-US')} · ${p.share}%</small></div>`; };
    const nexts = P.filter(r => r.next).map(r => Object.assign({ t: r.ticker }, r.next)).sort((a, b) => a.date.localeCompare(b.date));
    const bar = `<div class="cc-bar">
      <div class="tide t-${esc(td.state)}"><b>${TIDE[td.state] || 'Tide'}</b><small>${esc(td.rule || '')}</small></div>
      ${cap ? `<div class="pot wide"><span>Deployable</span><b>${rm(cap.deployable)}</b><small class="amt">liquid ${Math.round(cap.liquid).toLocaleString('en-US')} − ${cap.reserveMonths}-month reserve ${Math.round(cap.reserve).toLocaleString('en-US')} · runway ${cap.runwayMonths} months${cap.stale ? ' · <em class="flag">old figures</em>' : ''}</small></div>
      ${pot('fund', 'Fund pot')}${pot('shots', 'Shots pot')}${pot('trades', 'Quick-trade pot')}` : '<div class="pot wide"><span>Money</span><small>No portfolio summary yet (desk/money.py).</small></div>'}
      ${nexts.length ? `<div class="pot"><span>Next event</span><b>${dayDiff(todayMYT, nexts[0].date) <= 0 ? 'today' : dayDiff(todayMYT, nexts[0].date) + (dayDiff(todayMYT, nexts[0].date) === 1 ? ' day' : ' days')}</b><small>${esc(shortT(nexts[0].t))} · ${esc(nexts[0].text.slice(0, 60))}</small></div>` : ''}
      <button class="hold-toggle" data-hold aria-pressed="${hideHold}">${hideHold ? 'Show holdings' : 'Hide holdings'}</button>
    </div><p class="muted small cc-tide">${esc(td.text || '')}</p>`;

    const act = P.filter(r => ['exit2', 'exit1', 'frozen', 'trigger', 'add', 'buy'].includes(r.state));
    const soon = P.filter(r => r.next && dayDiff(todayMYT, r.next.date) <= 2);
    const today = `<section class="dsec cc-sec" id="cc-today"><h2>Today</h2>
      ${act.length || soon.length ? `<ul class="today">${act.map(r => `<li class="st-${esc(r.state)}${r.pos || r.action === 'holding' ? ' h' : ''}"><em class="stt">${esc(r.stateText)}</em> <b>${esc(r.name.split(' (')[0])}</b> at ${num(r.price)}${r.room && r.room.now ? ` · room ${rm(r.room.now)}` : ''}</li>`).join('')}
        ${soon.map(r => `<li class="ev${r.pos || r.action === 'holding' ? ' h' : ''}"><em class="stt">${dayDiff(todayMYT, r.next.date) <= 0 ? 'Today' : 'In ' + dayDiff(todayMYT, r.next.date) + 'd'}</em> <b>${esc(r.name.split(' (')[0])}</b> ${esc(r.next.text)}</li>`).join('')}</ul>` : '<p class="muted">Nothing needs you today. Every name is waiting above its line.</p>'}
      ${(B.bookFlags || []).map(f => `<p class="small amt cc-flag">${esc(f)}</p>`).join('')}</section>`;

    const lane = (id, title, blurb, rows, extra) => `<section class="dsec cc-sec" id="${id}"><h2>${title}</h2><p class="muted small">${blurb}</p>
      ${rows.length ? `<div class="cards">${rows.map(ccCard).join('')}</div>` : '<p class="muted small">No names in this lane yet. The next memo assigns them.</p>'}${extra || ''}</section>`;
    const fundLab = (S.fund || []).map(f => `<div class="scroll"><table class="tat"><thead><tr><th>${esc(f.ticker)}: one unit of cash a month since ${esc(fmtDate(f.from))}</th><th>Return on money set aside</th><th>Share invested</th><th>Worst drop</th></tr></thead><tbody>
      ${[['monthly', 'Buy every month, whatever happens'], ['above200', 'Buy only while above the 200-day'], ['washout', 'Buy only after a washout reversal']].map(([k, l]) => `<tr><td>${l}</td><td class="num">${pct(f.modes[k].ret)}</td><td class="num">${f.modes[k].invested}%</td><td class="num">${f.modes[k].worst}%</td></tr>`).join('')}</tbody></table></div>`).join('');
    const others = (B.others || []);
    const oth = others.length ? `<details class="zone-text h"><summary>Other holdings the desk does not cover (${others.length})</summary><div class="scroll"><table class="tat"><tbody>${others.map(o => `<tr><td><b>${esc(o.name)}</b></td><td class="num">${num(o.units)} at ${num(o.avgCost)} ${esc(o.currency)}</td><td class="num">now ${num(o.price)} <small>(${esc(o.priced)})</small></td><td class="num">${pct(o.pl)}</td><td class="num">${rm(o.value)}</td></tr>`).join('')}</tbody></table></div></details>` : '';

    const lab = (S.lab || {}).rows || [], tk = S.lab ? S.lab.tide : 'out';
    const good = lab.filter(r => r.tradable);
    const orders = (S.orders || []).slice(0, 8), rec = S.record || {};
    const trades = `<section class="dsec cc-sec" id="cc-trades"><h2>Quick trades</h2>
      <div class="watch"><b>${good.length ? `${good.length} setup${good.length > 1 ? 's are' : ' is'} tradable today: ${good.map(r => esc(r.label)).join(', ')}.` : 'No setup is tradable today.'}</b> ${good.length ? '' : `With entries you can really get (an order resting at the line, or the next morning's open) none of the six setups beat simply buying on any day, over ${lab.length ? lab[lab.length - 1].all.n : 0} baseline trades on ${(S.lab || { pool: [] }).pool.length} names. The quick-trade pot stays unspent until one earns it.`} Every fill is logged to the paper record below so a setup can prove itself first.</div>
      <div class="scroll"><table class="tat lab"><thead><tr><th>Setup</th><th>Entry</th><th>Trades</th><th>Wins</th><th>Average result</th><th>vs any day</th><th>Tide ${esc(tk)}</th><th>Verdict</th></tr></thead><tbody>
      ${lab.map(r => `<tr class="${r.tradable ? 'ok' : r.setup === 'anyday' ? 'base' : 'no'}"><td title="${esc(r.what)}"><b>${esc(r.label)}</b></td><td>${esc(r.how)}</td><td class="num">${r.all.n}</td><td class="num">${r.all.winRate}%</td><td class="num">${r.all.avgR >= 0 ? '+' : ''}${r.all.avgR.toFixed(2)}R</td><td class="num">${r.all.edge == null ? '—' : (r.all.edge >= 0 ? '+' : '') + r.all.edge.toFixed(2) + 'R'}</td><td class="num">${r[tk] && r[tk].n ? (r[tk].avgR >= 0 ? '+' : '') + r[tk].avgR.toFixed(2) + 'R <small>of ' + r[tk].n + '</small>' : '—'}</td><td>${r.setup === 'anyday' ? 'the bar to beat' : r.tradable ? (r.thin ? 'tradable, thin edge' : 'tradable') : 'no edge'}</td></tr>`).join('')}</tbody></table></div>
      <p class="muted small">One trade: stop one typical daily range below the entry, target two above (2 for 1), out after 15 sessions. R is the amount risked, so +0.10R means ten sen earned per ringgit risked, on average. A 2-for-1 trade needs to win more than 33% of the time just to break even. Four years of daily bars, no look-ahead, no costs.</p>
      ${orders.length ? `<h4 class="sub">Order sheet: where a limit order would rest</h4><div class="scroll"><table class="tat"><thead><tr><th>Name</th><th>Limit at</th><th>From price</th><th>Stop</th><th>Target</th><th>Size for ${rm(cap ? cap.riskPerTrade : null)} at risk</th><th>Status</th></tr></thead><tbody>
      ${orders.map(o => `<tr class="${o.tradable && !o.blocked ? 'ok' : 'no'}${(P.find(r => r.ticker === o.ticker) || {}).pos ? ' h' : ''}"><td><b>${esc(shortT(o.ticker))}</b> <small>${esc(o.kind)}</small></td><td class="num">${num(o.entry)}</td><td class="num">${o.away == null ? '—' : o.away + '%'}</td><td class="num">${num(o.stop)}</td><td class="num">${num(o.target)}</td><td class="num amt">${o.shares == null ? '—' : o.shares + ' sh · RM ' + o.sizeMYR.toLocaleString('en-US')}</td><td>${o.blocked ? 'blocked: ' + esc(o.blocked) : o.tradable ? 'tradable' : 'watch only: no edge'}</td></tr>`).join('')}</tbody></table></div>` : ''}
      <p class="small"><b>Paper record</b> since ${rec.since ? esc(fmtDate(rec.since)) : 'today'}: ${rec.closed || 0} closed trade${rec.closed === 1 ? '' : 's'} on tradable setups (${rec.wins || 0} won, ${(rec.totalR || 0) >= 0 ? '+' : ''}${(rec.totalR || 0).toFixed(2)}R), ${rec.open || 0} open.</p></section>`;

    const V = B.voices || [], ch = B.chatter || [], RH = B.rosterHealth || { seats: [], cited: [] };
    const role = h => { const a = K.analysts.find(x => x.handle === h); return a && a.role ? a.role : ''; };
    const mx = Math.max(1, ...ch.map(c => c.share));
    const voices = `<section class="dsec cc-sec" id="cc-voices"><h2>Voices</h2>
      ${V.length ? `<div class="cards v">${V.map(v => `<div class="vc"><div class="nc-top"><b>@${esc(v.handle)}</b><span>${esc(role(v.handle))}</span><em class="stt d-${esc(v.doing.replace(' ', '-'))}">${esc(v.doing)}</em></div><p>${esc(v.note)} ${link(v.url, 'post')}</p>${v.change ? `<p class="small"><b>Changed ${v.change.date ? fmtDate(v.change.date) : ''}:</b> ${esc(v.change.text)}</p>` : ''}${v.conflict ? `<p class="small flag">Conflict of interest: ${esc(v.conflict)}</p>` : ''}</div>`).join('')}</div>` : '<p class="muted small">What each seat is doing (long, hedged, adding, raising cash), with changes and conflicts of interest, is written by the weekly memo. The first one under the new rules is due 14 Nov 2026.</p>'}
      <h4 class="sub">Hedge chatter</h4><p class="muted small">Share of the roster's own posts each week that talk about hedges, shorts or raising cash. A rising bar means the voices are getting defensive.</p>
      <div class="chat">${ch.map(c => `<div title="${c.hedge} of ${c.posts} posts"><i style="height:${Math.round(c.share / mx * 100)}%"></i><b>${c.share}%</b><small>${esc(fmtDate(c.week).replace(/ \d{4}$/, ''))}</small></div>`).join('')}</div>
      <h4 class="sub">Roster health, last 31 days</h4>
      <div class="scroll"><table class="tat"><thead><tr><th>Seat</th><th>Role</th><th>Posts</th><th>Replies</th><th>Median length</th><th>On your names</th><th>Hedge talk</th><th>Hit rate</th><th>Edge vs ${esc(K.bench)}</th></tr></thead><tbody>
      ${RH.seats.map(x => `<tr><td>@${esc(x.handle)}</td><td>${esc(role(x.handle))}</td><td class="num">${x.posts}</td><td class="num">${x.replies}</td><td class="num">${x.medianLen}</td><td class="num">${x.onYourNames}</td><td class="num">${x.hedgeTalk}</td><td class="num">${x.hitRate == null ? '—' : x.hitRate + '%'}</td><td class="num">${pct(x.avgEdge)}</td></tr>`).join('')}</tbody></table></div>
      ${RH.cited.length ? `<p class="small muted">Outside accounts your roster cites most: ${RH.cited.map(c => `@${esc(c.handle)} (${c.bySeats} seats, ${c.times}×)`).join(' · ')}.</p>` : ''}</section>`;

    const hunt = (B.hunt || []).length ? `<h4 class="sub">Hunt list: names you do not own yet</h4><div class="cards v">${B.hunt.map(h => `<div class="vc"><div class="nc-top"><b>${esc(h.ticker)}</b><span>${esc(h.name)}</span></div><p>${esc(h.why)}</p><p class="small"><b>Becomes a shot when:</b> ${esc(h.trigger)}</p><p class="small muted">${Object.entries(h.checks).map(([k, v]) => `<b>${esc(k)}</b>: ${esc(v)}`).join(' · ')}</p></div>`).join('')}</div>` : '';
    return `<div class="cc" id="d-command">${bar}${today}
      ${lane('cc-fund', 'Fund', 'The long-term ETF sleeve, bought in steps from the fund pot. The lab below it compares three ways of stepping in on the same history.', P.filter(r => r.sleeve === 'fund'), fundLab)}
      ${lane('cc-shots', 'Shots', 'Names that could multiply. Each add is one of three steps: at the buy line, at the add line, and the last only after a milestone passes.', P.filter(r => r.sleeve === 'shot'), hunt + oth)}
      ${lane('cc-core', 'Core list', 'The desk’s scored calls and large caps, sized from the fund pot.', P.filter(r => r.sleeve === 'core' || !r.sleeve))}
      ${trades}${voices}
      <nav class="cc-tabs" aria-label="Command centre">${[['cc-today', 'Today'], ['cc-fund', 'Fund'], ['cc-shots', 'Shots'], ['cc-trades', 'Trades'], ['cc-voices', 'Voices']].map(([id, l]) => `<button data-jump="${id}">${l}</button>`).join('')}</nav></div>`;
  }

  // "Hide holdings": one switch for screen sharing; remembered per browser.
  let hideHold = false;
  try { hideHold = localStorage.getItem('aie-hide-holdings') === '1'; } catch (e) { /* storage blocked */ }
  function applyHold() { document.body.classList.toggle('hide-holdings', hideHold); }

  // A horizontal ladder: add zone, accumulate zone, hold band, stop-adding, trim, with today's price marked.
  // With `chartOpt` the bar becomes a real price chart (zoneChart) above the same legend.
  function ladder(t, lv, action, chartOpt) {
    const watch = action && action !== 'accumulate' && action !== 'holding';
    const q = (K.quotes || {})[t]; const price = q && q.price;
    const top = lv.stopAbove || lv.buyBelow;
    const trim = lv.trimAbove;
    const pts = [lv.addBelow, lv.buyBelow, top, trim, price].filter(v => v != null);
    const lo = Math.min(...pts) * 0.92, hi = Math.max(...pts) * 1.08, w = v => ((v - lo) / (hi - lo) * 100).toFixed(2);
    const seg = (a, b, cls, label) => b > a ? `<span class="lz ${cls}" style="left:${w(a)}%;width:${(w(b) - w(a)).toFixed(2)}%" title="${esc(label)}"></span>` : '';
    const add = lv.addBelow != null ? lv.addBelow : lv.buyBelow;
    const z = price != null ? zoneOf(price, lv) : null;
    const chart = chartOpt ? zoneChart(t, Object.assign({ action }, lv), chartOpt) : '';
    return `<div class="ladder${chart ? ' with-chart' : ''}" role="img" aria-label="Price ${price != null ? num(price) : 'unknown'} against the zones">
      ${chart || `<div class="lbar">${seg(lo, add, 'z-add', 'add zone')}${seg(add, lv.buyBelow, 'z-buy', 'accumulate zone')}${seg(lv.buyBelow, top, 'z-hold', 'hold')}${seg(top, trim != null ? trim : hi, 'z-above', 'stop adding')}${trim != null ? seg(trim, hi, 'z-trim', 'trim') : ''}
        ${[add, lv.buyBelow, top, trim].filter(v => v != null).map(v => `<span class="ltick" style="left:${w(v)}%"></span>`).join('')}
        ${price != null ? `<span class="lmark" style="left:${w(price)}%"></span>` : ''}</div>`}
      <div class="llegend">${watch ? `<span class="k z-buy"></span>revisit ≤ ${num(lv.buyBelow)}` : `<span class="k z-add"></span>add ≤ ${num(add)} <span class="k z-buy"></span>buy ≤ ${num(lv.buyBelow)} <span class="k z-above"></span>stop adding &gt; ${num(top)}${trim != null ? ` <span class="k z-trim"></span>trim &gt; ${num(trim)}` : ''}`}</div>
      <div class="lnow">${price != null ? `Now ${num(price)} ${esc(lv.currency)} · <b class="zn ${watch ? (z === 'add' || z === 'buy' ? 'buy' : 'hold') : z}">${watch ? (z === 'add' || z === 'buy' ? 'At the revisit level' : 'Above the revisit level') : ZONE[z]}</b> · alerts on` : 'No price in the sheet'}</div>
    </div>`;
  }


  // Zone history: where every name stood on each memo date, judged against that memo's own lines.
  function zoneHistory(m) {
    const memos = K.memos.slice().reverse();
    if (memos.length < 2) return '';
    const closeOn = (t, d) => { let v = null; for (const [hd, hv] of (HIST[t] || [])) { if (hd > d) break; v = hv; } return v; };
    const short = d => `${+d.slice(8)} ${MONTHS[+d.slice(5, 7) - 1]}`;
    const rows = m.accumulate.filter(a => a.levels).map(a => {
      const cells = memos.map(mm => {
        const b = mm.accumulate.find(x => x.ticker === a.ticker), p = b && b.levels ? closeOn(a.ticker, mm.date) : null;
        if (!b || !b.levels) return '<span class="zc0" title="not on the list that week">·</span>';
        if (p == null) return `<span class="zc0" title="no price history">${num(b.levels.buyBelow)}</span>`;
        const watch = b.action === 'watch', z = watch ? (p <= b.levels.buyBelow ? 'buy' : 'hold') : zoneOf(p, b.levels);
        return `<button class="zcell z-${z}${mm.date === m.date ? ' now' : ''}" data-memo="${memos.length - 1 - memos.indexOf(mm)}" title="${esc(shortT(a.ticker))} on ${esc(fmtDate(mm.date))}: ${num(p)}, ${esc(watch ? 'revisit ' : 'buy line ')}${num(b.levels.buyBelow)}, ${esc(ZSHORT[z])}">${num(b.levels.buyBelow)}</button>`;
      }).join('');
      return `<div class="zrow act-${esc(a.action)}"><span class="zname">${tick(a.ticker)}</span>${cells}</div>`;
    }).join('');
    return `<section class="dsec" id="d-history"><h2>Zone history</h2>
      <p class="muted small">Where each name stood on each memo date, coloured by its zone against <b>that week's</b> lines. The number is that week's buy line, so you can see the lines move. Click a column to open that memo.</p>
      <div class="zh" style="--cols:${memos.length}"><div class="zrow zhead"><span></span>${memos.map(mm => `<button class="zdate" data-memo="${memos.length - 1 - memos.indexOf(mm)}">${short(mm.date)}</button>`).join('')}</div>${rows}</div>
      <div class="cp-key"><span class="k z-add"></span>add <span class="k z-buy"></span>buy <span class="k z-hold"></span>hold <span class="k z-above"></span>no adding <span class="k z-trim"></span>trim</div>
    </section>`;
  }

  // The back-tested lines for one name (desk/ta.py): what held, how often, what followed.
  function taBlock(t, compact) {
    const TA = K && K.ta && K.ta.names ? K.ta.names[t] : null;
    if (!TA) return '';
    const rec = h => h.map(x => `<i class="tk ${x.held ? 'ok' : 'no'}" title="${esc(fmtDate(x.d))}: ${x.held ? 'held' : 'broke'} · 10 sessions later ${x.fwd == null ? 'n/a' : (x.fwd >= 0 ? '+' : '') + x.fwd + '%'} · worst ${x.mae}%">${x.held ? '✓' : '✗'}</i>`).join('');
    const row = (r, side) => `<tr class="${side}"><td>${esc(r.label)}${r.kind === 'floor' && r.formed ? `<small>formed ${esc(r.formed.slice(-2).map(fmtDate).join(', '))}</small>` : ''}</td>
      <td class="num">${num(r.value)}</td><td class="num">${r.dist > 0 ? '+' : ''}${r.dist}%</td>
      <td>${r.n ? `<b>${r.held}/${r.n}</b> ${rec(r.hist || [])}${r.recent && r.recent.n ? `<small>last year ${r.recent.held}/${r.recent.n}</small>` : '<small>last year: not tested</small>'}` : '<span class="muted" title="No touch old enough to judge: a touch needs 5 sessions after it">no judged test</span>'}</td>
      <td class="num">${side === 'sup' ? r.shrunk + '%' : ''}</td>
      <td class="num">${r.fwd == null ? '—' : pct(r.fwd)}${r.edge == null ? '' : `<small>${r.edge >= 0 ? '+' : ''}${r.edge} vs trend</small>`}</td>
      <td>${r.last ? fmtDate(r.last) : '—'}</td></tr>`;
    const sup = TA.support.slice(0, compact ? 3 : 5), res = TA.resistance.slice(0, 2);
    return `<div class="ta"><div class="ta-head"><b>Tested lines</b><span class="muted small">Every time the price came down to each line since ${esc(fmtDate(TA.from))} (${TA.bars} sessions; ✓✗ shows the latest eight). ✓ held: no close more than 2% below it in the next 5 sessions. Score: the hold rate, pulled towards the all-names rate for that kind of line when the sample is small.</span></div>
      <div class="scroll"><table class="tat"><thead><tr><th>Line</th><th>Level</th><th>From price</th><th>Record</th><th>Score</th><th>10 sessions after</th><th>Last test</th></tr></thead>
      <tbody>${sup.map(r => row(r, 'sup')).join('')}${res.map(r => row(r, 'res')).join('')}</tbody></table></div>
      ${TA.best ? `<p class="small">Best-tested support with two or more tests: <b>${esc(TA.best)}</b>.</p>` : '<p class="small muted">No line below the price has been tested twice in this window, so the chart cannot vouch for any floor here.</p>'}</div>`;
  }
  function labVerdict(rows) {
    const best = rows[0], ma200 = (rows.find(r => r[0] === 'SMA 200d') || [])[1];
    const coin = rows.every(([, v]) => (v.rate || 0) < 60);
    const shift = ma200 && ma200.recent && ma200.recent.n ? `The 200-day average held ${ma200.rate}% of ${ma200.n} touches over the whole history but only ${ma200.recent.rate}% of ${ma200.recent.n} in the last year: the line that worked in 2023-25 has not worked in this market.` : '';
    return `<div class="watch"><b>What it says.</b> ${coin ? 'No kind of line held much more often than a coin flip.' : ''} The best record is <b>${esc(best[0])}</b> at ${best[1].rate}% of ${best[1].n} touches. ${shift} So a line on its own is not a reason to buy. A tested line is worth more when it has held before on this name, is still holding in the last year, and the stock's own named test still passes.</div>`;
  }
  // Level lab: the pooled record of each kind of line across every name, and what it means.
  function levelLab() {
    const P = K && K.ta && K.ta.pooled; if (!P) return '';
    const rows = Object.entries(P).sort((a, b) => (b[1].rate || 0) - (a[1].rate || 0));
    const rf = s => s && s.n ? `${s.rate}% of ${s.n}` : '—';
    return `<section class="dsec" id="d-lab"><h2>Level lab</h2>
      <p class="muted small">Do moving averages and chart floors actually hold? Every touch of every line on every name in the sheet's price history (about four years of daily bars), tested with no look-ahead. A touch holds if there is no close more than 2% below the line in the next 5 sessions. "vs trend" is the 10-session return after the touch minus that stock's own average 10-session return, so a positive number means the touch added something beyond the trend.</p>
      <div class="scroll"><table class="tat lab"><thead><tr><th>Line</th><th>Touches</th><th>Held</th><th>Last year</th><th>10 sessions after</th><th>vs trend</th><th>Worst dip below</th><th>Line rising</th><th>Line falling</th></tr></thead>
      <tbody>${rows.map(([k, s]) => `<tr><td><b>${esc(k)}</b></td><td class="num">${s.n}</td><td class="num"><span class="bar"><i style="width:${s.rate || 0}%"></i></span>${s.rate}%</td><td class="num">${rf(s.recent)}</td><td class="num">${pct(s.fwd)}</td><td class="num">${pct(s.edge)}</td><td class="num">${s.mae}%</td><td class="num">${rf(s.rising)}</td><td class="num">${rf(s.falling)}</td></tr>`).join('')}</tbody></table></div>
      ${labVerdict(rows)}
      <p class="muted small">Limits: about four years of daily bars (from late 2022; names listed more recently have less). Results are pooled across names that move together, so touches are not independent. Older years may not repeat: compare the "Last year" column with the full record.</p>
    </section>`;
  }
  let stressId = null;
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
          <dt>Accumulate zone</dt><dd>${a.levels ? ladder(a.ticker, a.levels, a.action, { w: 600, h: 190, days: 130, labels: true, call: c }) : ''}${taBlock(a.ticker)}<details class="zone-text"><summary>The memo's reasoning behind the lines</summary>${esc(a.zone)}</details></dd>
          <dt>Kills the idea</dt><dd>${esc(a.invalidation)}</dd>
          ${a.premortem ? `<dt>How it loses money</dt><dd class="premortem">${esc(a.premortem)}</dd>` : ''}
          ${a.test ? `<dt>${a.action === 'watch' ? 'Re-entry test' : 'What decides it'}</dt><dd>${esc(a.test.metric)}: ${esc(a.test.threshold)}${a.test.by ? ' · by ' + fmtDate(a.test.by) : ''} ${link(a.test.source, a.test.sourceName)}</dd>` : ''}
          ${c ? `<dt>Scorecard</dt><dd>Opened ${fmtDate(c.opened)} at ${num(c.refPrice)} ${esc(c.currency || '')} · now ${num(c.lastPrice)} · ${pct(c.ret)} vs ${esc(K.bench)} ${pct(c.benchRet)}</dd>` : ''}
        </dl>
        <div class="idea-foot">${(a.analysts || []).map(h => `<span class="who">@${esc(h)}</span>`).join('')}${(a.sources || []).map(u => link(u)).join(' ')}</div>
      </article>`;
    }).join('') || '<p class="muted">Nothing meets the bar this week.</p>';

    // Trust weight: 1 until an analyst has 8+ scored calls, then 1 + average edge/20, held between 0.25 and 1.5.
    const W8 = {}; (K.track || []).forEach(a => { W8[a.handle] = a.scored >= 8 && a.avgEdge != null ? Math.min(1.5, Math.max(0.25, 1 + a.avgEdge / 20)) : 1; });
    const lean = b => {
      let n = 0, w = 0, bu = 0, be = 0;
      b.views.forEach(v => { const s = v.stance === 'bull' ? 1 : v.stance === 'bear' ? -1 : 0; n += s; w += s * (W8[v.handle] == null ? 1 : W8[v.handle]); bu += s > 0; be += s < 0; });
      return { n, w, bu, be };
    };
    const leanCell = b => {
      const l = lean(b), cls = l.w > 0.4 ? 'bull' : l.w < -0.4 ? 'bear' : 'mixed';
      return `<td class="lean"><span class="st ${cls}">${l.bu}▲ ${l.be}▼</span><div class="note">record-weighted ${l.w >= 0 ? '+' : ''}${l.w.toFixed(1)}${l.n !== 0 && Math.sign(l.n) !== Math.sign(Math.round(l.w * 10) / 10) ? ' · <em class="flag">flips the headcount</em>' : ''}</div></td>`;
    };
    const cols = handles.filter(h => m.board.some(b => b.views.some(v => v.handle === h)));
    const board = m.board.length ? `<div class="scroll"><table class="board">
      <thead><tr><th>Ticker</th>${cols.map(h => `<th>@${esc(h)}</th>`).join('')}<th>Lean</th><th>Desk read</th></tr></thead>
      <tbody>${m.board.map(b => `<tr><td>${tick(b.ticker)}</td>${cols.map(h => {
        const v = b.views.find(x => x.handle === h);
        return v ? `<td><a class="st ${esc(v.stance)}" href="${esc(v.url)}" target="_blank" rel="noopener" title="${esc(v.note)}">${STANCE[v.stance]}</a><div class="note">${esc(v.note)}</div></td>` : '<td class="muted">·</td>';
      }).join('')}${leanCell(b)}<td class="read">${esc(b.read)}</td></tr>`).join('')}</tbody></table></div>` : '<p class="muted">No stances this week.</p>';

    const TR = (K.track || []).filter(a => a.calls);
    const track = TR.length ? `<div class="scroll"><table class="track"><thead><tr><th>Analyst</th><th>Stances</th><th>Scored</th><th>Avg edge vs ${esc(K.bench)}</th><th>Hit rate</th><th>Best / worst call so far</th></tr></thead><tbody>${
      TR.map(a => {
        const sc = a.rows.filter(r => r.edge != null).sort((x, y) => y.edge - x.edge);
        const bw = sc.length ? `${esc(sc[0].ticker)} ${pct(sc[0].edge)}${sc.length > 1 ? ` · ${esc(sc[sc.length - 1].ticker)} ${pct(sc[sc.length - 1].edge)}` : ''}` : '<span class="muted">—</span>';
        return `<tr><td>@${esc(a.handle)}</td><td class="num">${a.calls}</td><td class="num">${a.scored}</td><td class="num">${pct(a.avgEdge)}</td><td class="num">${a.hitRate == null ? '—' : a.hitRate + '%'}</td><td>${bw}</td></tr>`;
      }).join('')}</tbody></table></div>` : '<p class="muted">No stances recorded yet.</p>';
    const young = !TR.some(a => a.rows.some(r => r.since < m.date));

    // Stress test: the desk's 0-3 exposure of each name to one shock, with the room each has before its buy line.
    const EX = K.exposures || {}, SH = EX.shocks || [];
    if (stressId == null || !SH.some(x => x.id === stressId)) stressId = SH.length ? SH[0].id : null;
    const stress = SH.length && deskIdx === 0 ? (() => {
      const sh = SH.find(x => x.id === stressId);
      const rows = m.accumulate.map(a => {
        const e = (EX.rows || {})[a.ticker], lv = LV[a.ticker] || a.levels, p = ((K.quotes || {})[a.ticker] || {}).price;
        if (!e) return null;
        const d = lv && p != null ? (p / lv.buyBelow - 1) * 100 : null;
        return { a, x: e[stressId] || 0, d, z: lv && p != null ? zoneOf(p, lv) : null };
      }).filter(Boolean).sort((p, q) => q.x - p.x || (p.d == null) - (q.d == null) || p.d - q.d);
      const hit = rows.filter(r => r.x >= 2 && r.a.action !== 'watch'), safe = rows.filter(r => r.x === 0 && r.a.action !== 'watch');
      const calls = hit.filter(r => r.a.action === 'accumulate').length, openCalls = rows.filter(r => r.a.action === 'accumulate').length;
      return `<section class="dsec" id="d-stress"><h2>Stress test</h2>
        <p class="muted small">Pick a shock. Names are ordered by how directly it hits them (the desk's judgement, 0 to 3, not measured) and then by how close they already sit to their buy line. No return is forecast: it shows where the book is exposed and which named test would tell you first.</p>
        <div class="shocks" role="tablist">${SH.map(x => `<button role="tab" data-shock="${esc(x.id)}" aria-selected="${x.id === stressId}">${esc(x.label)}</button>`).join('')}</div>
        <p class="shock-text">${esc(sh.text)}</p>
        <p class="shock-sum"><b>${calls} of ${openCalls}</b> open call${calls === 1 ? ' is' : 's are'} directly exposed (2 or 3), and <b>${safe.length}</b> row${safe.length === 1 ? '' : 's'} on the list ${safe.length === 1 ? 'is' : 'are'} untouched.</p>
        <div class="scroll"><table class="stress"><tbody>${rows.map(r => `<tr class="st-row act-${esc(r.a.action)}"><td>${tick(r.a.ticker)}</td><td>${esc(r.a.name)}</td><td class="exp x${r.x}" title="exposure ${r.x} of 3">${'●'.repeat(r.x)}${'○'.repeat(3 - r.x)}</td><td class="num">${r.d == null ? '<span class="muted">no price</span>' : r.d <= 0 ? 'in zone' : '+' + r.d.toFixed(1) + '% to buy line'}</td><td class="muted small">${r.a.test ? esc(r.a.test.metric) : esc(r.a.invalidation)}</td></tr>`).join('')}</tbody></table></div>
      </section>`;
    })() : '';

    const next = K.memos[Math.max(deskIdx - 1, 0)];
    const evs = (K.events || []).filter(e => e.date >= m.date && (deskIdx === 0 || e.date < next.date)).sort((x, y) => y.date.localeCompare(x.date));
    const VER = { confirms: 'Confirms the call', mixed: 'Mixed', breaks: 'Breaks the call' };
    const heldNow = new Set(m.accumulate.filter(a => a.action === 'holding').map(a => a.ticker));
    const events = evs.map(e => `<article class="event ${esc(e.verdict)}${heldNow.has(e.ticker) ? ' ev-holding' : ''}">
        <div class="idea-head">${tick(e.ticker)}<h3>${esc(e.event)}</h3><span class="pill ver-${esc(e.verdict)}">${VER[e.verdict]}</span><time>${fmtDate(e.date)}</time></div>
        <p class="thesis">${esc(e.headline)}</p>${paras(e.summary)}
        ${(e.numbers || []).length ? `<ul class="nums">${e.numbers.map(n => `<li>${esc(n.text)} ${link(n.source)}</li>`).join('')}</ul>` : ''}
        ${e.callImpact ? `<p><b>Call:</b> ${esc(e.callImpact)}</p>` : ''}
        ${e.levels ? ladder(e.ticker, e.levels, 'accumulate', { w: 600, h: 170, days: 90, labels: true }) : ''}
        <div class="idea-foot">${(e.sources || []).map(u => link(u)).join(' ')}</div></article>`).join('');

    const alerts = deskIdx === 0 ? (K.alerts || []).slice(0, 6) : [];
    // A change line mentions a holding if it names one (ticker or name) or says "holding".
    const heldNames = m.accumulate.filter(a => a.action === 'holding').flatMap(a => [a.ticker, a.name.split(' (')[0]]);
    const heldText = t => /holding/i.test(t) || heldNames.some(n => t.includes(n));
    const kinds = {}; (K.changes || []).forEach(c => { kinds[c.kind] = (kinds[c.kind] || 0) + 1; });
    const KIND = { open: 'opened', close: 'closed', new: 'new', drop: 'dropped', move: 'level moves', flip: 'flips', event: 'event updates' };
    const changes = deskIdx === 0 && (K.changes || []).length ? `<details class="dsec changed" id="d-changed"><summary><h2>What changed</h2><span class="chg-sum">${Object.keys(kinds).map(k => `<b class="k-${esc(k)}">${kinds[k]} ${KIND[k] || k}</b>`).join('')}${alerts.length ? `<b class="k-alert">${alerts.length} price alerts</b>` : ''}</span></summary>
        <ul class="chg">${K.changes.map(c => `<li class="k-${esc(c.kind)}${heldText(c.text) ? ' h' : ''}">${esc(c.text)}</li>`).join('')}</ul>
        ${alerts.length ? `<h4 class="sub">Price alerts</h4><ul class="chg">${alerts.map(a => `<li class="k-alert${heldNow.has(a.ticker) ? ' h' : ''}"><time>${esc(fmtMYT(a.at))}</time> ${esc(a.text)}</li>`).join('')}</ul>` : ''}
      </details>` : '';

    const mk = m.market;
    const movers = (mk.movers || []).length ? `<table class="movers"><tbody>${mk.movers.map(x => `<tr><td>${tick(x.ticker)}</td><td class="num">${pct(x.chg1w)}</td><td>${esc(x.why || '')} ${link(x.source)}</td></tr>`).join('')}</tbody></table>` : '';
    const posn = (mk.positioning || []).length ? `<ul class="devlist">${mk.positioning.map(x => `<li>${esc(x.text)} ${link(x.source)}</li>`).join('')}</ul>` : '';
    const cal = (mk.calendar || []).length ? `<ul class="devlist">${mk.calendar.map(x => `<li><time>${fmtDate(x.date)}</time>${esc(x.event)} ${link(x.source)}</li>`).join('')}</ul>` : '';

    const score = K.calls.length ? `<div class="scroll"><table class="score"><thead><tr><th>Ticker</th><th>Opened</th><th>Ref</th><th>Now / exit</th><th>Return</th><th>${esc(K.bench)}</th><th>Status</th></tr></thead><tbody>${
      K.calls.slice().reverse().map(c => `<tr><td>${tick(c.ticker)}</td><td>${fmtDate(c.opened)}</td><td class="num">${num(c.refPrice)} ${esc(c.currency || '')}</td><td class="num">${num(c.lastPrice)}</td><td class="num">${pct(c.ret)}</td><td class="num">${pct(c.benchRet)}</td><td>${c.closed ? 'closed ' + fmtDate(c.closed.date) : 'open'}</td></tr>`).join('')}</tbody></table></div>` : '<p class="muted">No calls yet.</p>';

    $('#memo').innerHTML = `
      <div class="memo-meta">Weekly memo · ${fmtDate(m.date)} · posts ${fmtDate(m.window.from)} to ${fmtDate(m.window.to)} ${pick}</div>
      ${deskIdx === 0 ? tape(m) : ''}
      <h1 class="headline">${esc(m.headline)}</h1>
      <nav class="dnav" aria-label="Memo sections">${[deskIdx === 0 && B.plan && ['d-command', 'Command centre'], deskIdx === 0 && ['d-cockpit', 'Charts'], deskIdx === 0 && ['d-history', 'History'], changes && ['d-changed', 'Changes'], events && ['d-since', 'Since'], ['d-picture', 'Picture'], ['d-list', 'List'], ['d-board', 'Board'], stress && ['d-stress', 'Stress test'], deskIdx === 0 && K.ta && ['d-lab', 'Level lab'], ['d-track', 'Track record'], ['d-wrap', 'Market'], ['d-pushback', 'Pushback'], ['d-score', 'Scorecard']].filter(Boolean).map(([id, l]) => `<button data-jump="${id}">${l}</button>`).join('')}</nav>
      ${deskIdx === 0 ? commandCentre() : ''}
      ${deskIdx === 0 && B.plan ? '<p class="fold-note muted small">The weekly memo and its records are below. Tap a heading to open it.</p>' : ''}
      ${deskIdx === 0 ? cockpit(m) : ''}
      ${deskIdx === 0 ? zoneHistory(m) : ''}
      ${changes}
      ${events ? `<section class="dsec" id="d-since"><h2>Since this memo</h2><p class="muted small">Event updates between weekly memos. They can move the alert levels; only the weekly memo opens or closes calls.</p>${events}</section>` : ''}
      <section class="dsec" id="d-picture"><h2>1 · The supply-chain picture</h2>
        <div class="two"><div><h4>Now</h4>${paras(m.picture.now)}</div><div><h4>Next</h4>${paras(m.picture.next)}</div></div></section>
      <section class="dsec" id="d-list"><h2>2 · Accumulate list</h2>
        <p class="muted small">Research support, not advice. Prices from your Google Sheet${K.pricesAsOf ? ' as of ' + esc(K.pricesAsOf.slice(0, 10)) : ''}.</p>${acc}</section>
      <section class="dsec" id="d-board"><h2>3 · Analyst board</h2><p class="muted small">Each cell links to the post. <b>Lean</b> counts the heads, then re-weights each by that analyst's record against ${esc(K.bench)}: weight 1 until 8 scored calls, then 1 + average edge ÷ 20, held between 0.25 and 1.5. A lean that flips the headcount means the track record disagrees with the crowd. It is a rule of thumb, not a forecast.</p>${board}</section>
      ${stress}
      ${deskIdx === 0 ? levelLab() : ''}
      <section class="dsec" id="d-track"><h2>Analyst track record</h2><p class="muted small">Every stance on the board, from the day it was first recorded, against ${esc(K.bench)}. A bull call earns the stock's move minus ${esc(K.bench)}'s; a bear call the reverse; mixed calls are not scored. Local-currency returns.${young ? ' Everything was recorded this week, so it all reads 0% for now; it fills in as prices move.' : ''}</p>${track}</section>
      <section class="dsec" id="d-wrap"><h2>4 · Market wrap</h2>${paras(mk.summary)}${movers}${posn ? '<h4 class="sub">Positioning: squeeze or re-rating?</h4>' + posn : ''}${cal ? '<h4 class="sub">Coming up</h4>' + cal : ''}</section>
      <section class="dsec pushback" id="d-pushback"><h2>The desk's pushback</h2><p class="muted small">Every analyst on the roster leans bullish. This is the other side.</p>${paras(m.pushback)}</section>
      <section class="dsec" id="d-score"><h2>Scorecard</h2><p class="muted small">Every accumulate call, marked to the latest price against ${esc(K.bench)}. Calls are never edited after the fact.</p>${score}</section>
      ${m.flags.length ? `<section class="dsec"><h2>Flags</h2><ul>${m.flags.map(f => `<li>${esc(f)}</li>`).join('')}</ul></section>` : ''}
      <p class="muted small">Collector last ran ${K.collectorLastRun ? esc(fmtMYT(K.collectorLastRun)) : 'never'} · following ${K.analysts.map(a => '@' + esc(a.handle)).join(', ')}</p>`;
    // With the command centre on top, the memo's own sections start folded: tap a heading to open one.
    if (deskIdx === 0 && B.plan) document.querySelectorAll('#memo > section.dsec:not(.cc-sec), #memo > .cockpit .dsec').forEach(el => {
      const h = el.querySelector('h2'); if (!h) return;
      el.classList.add('fold'); h.setAttribute('role', 'button'); h.setAttribute('tabindex', '0'); h.setAttribute('aria-expanded', 'false');
    });
    motion($('#memo'));
    const sel = $('#memo-pick');
    if (sel) sel.addEventListener('change', () => { deskIdx = +sel.value; renderDesk(); window.scrollTo(0, 0); });
  }

  // ---------- drawer ----------
  // Everything the desk knows about one ticker: call, zones on a price chart, live stances, event verdicts.
  function deskBlock(t) {
    if (!K || !K.memos || !K.memos.length) return '';
    const m = K.memos[0];
    const a = m.accumulate.find(x => x.ticker === t);
    const lv = LV[t] || (a && a.levels && Object.assign({ action: a.action }, a.levels));
    const calls = K.calls.filter(c => c.ticker === t);
    const open = calls.find(c => !c.closed);
    const evs = (K.events || []).filter(e => e.ticker === t).slice(0, 6);
    const views = (K.track || []).flatMap(x => x.rows).filter(r => r.ticker === t && !r.ended).sort((p, q) => q.lastSeen.localeCompare(p.lastSeen));
    const b = m.board.find(x => x.ticker === t);
    if (!a && !lv && !calls.length && !evs.length && !views.length && !b) return '';
    const VER = { confirms: 'confirms', mixed: 'mixed', breaks: 'breaks' };
    const hasHist = (HIST[t] || []).length > 4;
    return `<section class="desk-block">
      <div class="db-head"><h4>On the desk</h4>${a ? `<span class="pill act-${esc(a.action)}">${esc(a.action)}</span><span class="conf">${esc(a.confidence)} confidence · memo ${fmtDate(m.date)}</span>` : '<span class="conf">not on the latest list</span>'}</div>
      ${a ? `<p class="thesis">${esc(a.thesis)}</p>` : ''}
      ${lv ? (hasHist ? ladder(t, lv, lv.action || (a && a.action), { w: 520, h: 200, days: 190, labels: true, call: open }) : ladder(t, lv, lv.action || (a && a.action))) : ''}
      ${taBlock(t, true)}
      ${calls.map(c => `<p class="db-call">Call opened ${fmtDate(c.opened)} at ${num(c.refPrice)} ${esc(c.currency || '')}${c.closed ? `, closed ${fmtDate(c.closed.date)} at ${num(c.closed.price)}` : `, now ${num(c.lastPrice)}`} · ${pct(c.ret)} vs ${esc(K.bench)} ${pct(c.benchRet)}</p>`).join('')}
      ${a && a.test ? `<p class="db-call"><b>${a.action === 'watch' ? 'Re-entry test' : 'What decides it'}:</b> ${esc(a.test.metric)}: ${esc(a.test.threshold)} ${link(a.test.source, a.test.sourceName)}</p>` : ''}
      ${b ? `<div class="watch"><b>Desk read.</b> ${esc(b.read)}</div>` : ''}
      ${views.length ? `<div class="block"><h4>Analysts' live stances (${views.length})</h4><ul class="devlist">${views.map(r => `<li><a class="st ${esc(r.stance)}" href="${esc(r.url)}" target="_blank" rel="noopener">${STANCE[r.stance]}</a> <span class="who">@${esc(r.handle)}</span> ${esc(r.note)} <span class="muted small">since ${fmtDate(r.since)}${r.edge != null && r.stance !== 'mixed' ? ` · edge ${pct(r.edge)}` : ''}</span></li>`).join('')}</ul></div>` : ''}
      ${evs.length ? `<div class="block"><h4>Event updates</h4><ul class="devlist">${evs.map(e => `<li><time>${fmtDate(e.date)}</time><span class="pill ver-${esc(e.verdict)}">${VER[e.verdict]}</span> ${esc(e.headline)}</li>`).join('')}</ul></div>` : ''}
    </section>`;
  }
  function openDeskOnly(t) {
    $('#drawer').innerHTML = `
      <div class="drawer-head" style="--stage: var(--muted)">
        <div><div class="t">${esc(t)} · desk only</div><h2>${esc(nameOf(t))}</h2>
          <div class="sub">Not in the guide: it sits on the desk's list but on no constraint layer.</div></div>
        <button class="close" aria-label="Close">×</button>
      </div>${deskBlock(t) || '<p class="muted">Nothing on the desk for this ticker.</p>'}`;
    $('#drawer').hidden = false; $('#backdrop').hidden = false;
    $('#drawer').scrollTop = 0;
    document.body.style.overflow = 'hidden';
  }
  function openCompany(t) {
    const c = byTicker[t]; if (!c) { openDeskOnly(t); return; }
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
      ${deskBlock(t)}
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

  function jumpDev(k) {
    let el = document.getElementById('dev-' + k);
    if (!el) { tlNarr = ''; renderTimeline($('#q').value.trim()); el = document.getElementById('dev-' + k); }
    if (!el) return;
    el.scrollIntoView({ block: 'center', behavior: REDUCED ? 'auto' : 'smooth' });
    el.classList.remove('flash'); void el.offsetWidth; el.classList.add('flash');
  }
  // ---------- events ----------
  document.addEventListener('click', e => {
    const nc = e.target.closest('[data-narr]');
    if (nc) { const el = document.getElementById('narr-' + nc.dataset.narr); if (el) { el.open = true; el.scrollIntoView({ block: 'start', behavior: 'smooth' }); } return; }
    const dd = e.target.closest('[data-dev]');
    if (dd) { jumpDev(dd.dataset.dev); return; }
    const dm = e.target.closest('[data-memo]');
    if (dm) { deskIdx = +dm.dataset.memo; renderDesk(); window.scrollTo(0, 0); return; }
    const shk = e.target.closest('[data-shock]');
    if (shk) { stressId = shk.dataset.shock; const y = window.scrollY; renderDesk(); window.scrollTo(0, y); return; }
    if (e.target.closest('[data-hold]')) { hideHold = !hideHold; try { localStorage.setItem('aie-hide-holdings', hideHold ? '1' : '0'); } catch (err) { /* not remembered */ } applyHold(); render(); return; }
    const lb = e.target.closest('[data-lens]');
    if (lb) { lens = lb.dataset.lens; try { localStorage.setItem('aie-lens', lens); } catch (err) { /* not remembered */ } render(); return; }
    const cell = e.target.closest('.cell[data-layer], .fnode[data-layer]');
    if (cell) { const el = $('#layer-' + CSS.escape(cell.dataset.layer)); if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); return; }
    const fh = e.target.closest('.fold > h2, .fold > .cp-title');
    if (fh && !e.target.closest('button')) { const f = fh.parentElement; f.classList.toggle('open'); const h2 = f.querySelector('h2'); if (h2) h2.setAttribute('aria-expanded', f.classList.contains('open')); return; }
    const jump = e.target.closest('[data-jump]');
    if (jump) { const el = document.getElementById(jump.dataset.jump); if (el) { if (el.tagName === 'DETAILS') el.open = true; el.classList.add('open'); el.querySelectorAll('.fold').forEach(f => f.classList.add('open')); el.scrollIntoView({ block: 'start', behavior: 'smooth' }); } return; }
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
  function flowCap(e) {
    const n = e.target.closest && e.target.closest('.fnode'), cap = $('#flow-cap'); if (!cap || !n) return;
    const l = D.layers.find(x => x.id === n.dataset.layer); if (!l) return;
    cap.innerHTML = `<b>${esc(l.name)}.</b> ${esc(l.constraint)}`;
  }
  document.addEventListener('mouseover', flowCap);
  document.addEventListener('focusin', flowCap);
  document.addEventListener('keydown', e => {
    if (e.key === 'Enter' && e.target.classList && e.target.classList.contains('fnode')) { const el = $('#layer-' + CSS.escape(e.target.dataset.layer)); if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); }
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
  document.addEventListener('mousemove', onChartMove);
  window.addEventListener('scroll', () => { $('#tip').hidden = true; }, { passive: true });
  const setHdr = () => document.documentElement.style.setProperty('--hdr', $('.top').offsetHeight + 'px');
  window.addEventListener('resize', setHdr); setHdr();

  // ---------- boot ----------
  $('#meta').textContent = `${D.companies.length} companies · ${D.layers.length} layers · ${D.narratives.length} narratives · ${D.developments.length} dated developments · updated ${fmtDate(D.meta.updated)}${K && K.pricesAsOf ? ` · desk prices ${fmtMYT(K.pricesAsOf)}` : ''}`;
  $('#foot').textContent = D.meta.disclaimer;
  document.title = D.meta.title;
  applyHold();
  route();
})();
