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
  function renderMap(q) {
    const stats = {}; let max = 1;
    D.layers.forEach(l => { stats[l.id] = layerStat(l); max = Math.max(max, stats[l.id].v); });
    const heat = s => lens === 'plain' ? 0 : s.v / max;
    const bar = `<div class="lens-bar" role="group" aria-label="Map lens">${Object.keys(LENSES).map(k => `<button data-lens="${k}" class="${lens === k ? 'on' : ''}">${LENSES[k].label}</button>`).join('')}<span class="lens-note">${esc(LENSES[lens].note)}</span></div>`;
    const strip = q ? '' : `<div class="strip">${['demand', 'compute', 'supply'].map(st => `<div class="strip-stage" data-stage="${st}"><div class="strip-label">${st}</div><div class="strip-cells">${D.layers.filter(l => l.stage === st).map(l => {
      const s = stats[l.id], tone = lens === 'mood' && s.v ? (s.net > 0 ? 'bull' : s.net < 0 ? 'bear' : 'split') : '';
      return `<button class="cell${tone ? ' t-' + tone : ''}" data-layer="${esc(l.id)}" style="--h:${heat(s).toFixed(2)}" title="${esc(l.constraint)}"><b>${esc(l.name)}</b><span>${esc(s.text)}</span></button>`;
    }).join('')}</div></div>`).join('<div class="strip-arrow" aria-hidden="true">→</div>')}</div>`;
    const out = [];
    let lastStage = null;
    D.layers.forEach(l => {
      const cos = D.companies.filter(c => c.layer === l.id && matches(c, q));
      if (q && !cos.length) return;
      if (lastStage && lastStage !== l.stage && !q) out.push('<div class="flow">▼ feeds into ▼</div>');
      lastStage = l.stage;
      out.push(`<section class="layer" data-stage="${esc(l.stage)}" id="layer-${esc(l.id)}">
        <div class="layer-head"><h2>${esc(l.name)}</h2><span class="stage-tag">${esc(l.stage)}</span>${lens !== 'plain' ? `<span class="layer-stat">${esc(stats[l.id].text)}</span>` : ''}</div>
        <p class="layer-summary">${esc(l.summary)}</p>
        <p class="layer-constraint"><b>Constraint.</b> ${esc(l.constraint)}</p>
        <div class="chips">${cos.map(c => chip(c, false, lensDeco(c.ticker))).join('')}</div>
        <p class="layer-watch"><b>Watch:</b> ${esc(l.watch)}</p>
      </section>`);
    });
    $('#map').innerHTML = bar + strip + (out.join('') || '<p class="empty">No company matches.</p>');
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
    if (trimIn) hi = trim;
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
    const id = regChart({ W, x0: L, x1: W - R, t0, t1, fmt: v => num(v) + ' ' + (lv.currency || ''), series: [{ label: shortT(t), pts: ts.map((tm, i) => [tm, vs[i]]) }] });
    return `<svg class="zc${o.labels ? ' big' : ''}" data-ch="${id}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(nameOf(t))}: ${bars.length} daily closes against the desk's zones; last ${num(last)}">
      ${bands}${ticks}${labels}${callMark}<path class="pl" d="${line}"/><circle class="pd" cx="${x(t1).toFixed(1)}" cy="${y(last).toFixed(1)}" r="${o.labels ? 4 : 3}"/>
      <line class="hair" x1="0" x2="0" y1="${T}" y2="${H - B}" opacity="0"/></svg>`;
  }

  // Each accumulate call's return minus SMH's, from the call's own reference prices, over daily closes.
  const SERIES = ['var(--s1)', 'var(--s2)', 'var(--s3)', 'var(--s4)', 'var(--s5)', 'var(--s6)', 'var(--s7)', 'var(--s8)'];
  function callsChart() {
    const smh = HIST[K.bench]; if (!smh || !K.calls.length) return '';
    const smhAt = d => { let v = null; for (const [sd, sv] of smh) { if (sd > d) break; v = sv; } return v; };
    const series = K.calls.map((c, i) => {
      if (!c.refPrice || !c.benchRef) return null;
      const end = c.closed ? c.closed.date : '9999-12-31';
      const pts = (HIST[c.ticker] || []).filter(([d]) => d >= c.opened && d <= end).map(([d, v]) => {
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
      return { a, d, html: `<a class="cp-row" href="#c/${encodeURIComponent(a.ticker)}">
        <div class="cp-id"><b>${esc(shortT(a.ticker))}</b><span>${esc(a.name)}</span></div>
        <div class="cp-chart">${zoneChart(a.ticker, lv, { w: 200, h: 44, days: 66, tight: true })}</div>
        <div class="cp-now"><b>${num(price)}</b><span class="zn ${zc}">${zl}</span></div>
        <div class="cp-dist"><span class="${d <= 0 ? 'up' : ''}">${d <= 0 ? 'in zone' : '+' + d.toFixed(1) + '%'}</span><small>${watch ? 'revisit' : 'buy line'} ${num(lv.buyBelow)}</small></div>
        <div class="cp-5d">${st ? `<span class="${st.m5 >= 0 ? 'up' : 'dn'}">${st.m5 >= 0 ? '+' : ''}${st.m5.toFixed(1)}%</span><small>5 sessions${st.stretched ? ' · <em class="flag">stretched</em>' : ''}</small>` : '<small>no history</small>'}</div>
      </a>` };
    });
    const zones = GROUPS.map(([act, label]) => {
      const g = rows.filter(r => r.a.action === act && r.html).sort((p, q) => p.d - q.d);
      return g.length ? `<div class="cp-group">${label}</div>${g.map(r => r.html).join('')}` : '';
    }).join('');
    const bench = stretchOf(K.bench);

    const up = [];
    (m.market.calendar || []).forEach(x => { if (x.date >= todayMYT) up.push({ date: x.date, text: x.event, t: x.ticker, src: x.source }); });
    m.accumulate.forEach(a => { if (a.test && a.test.by && a.test.by >= todayMYT) up.push({ date: a.test.by, text: `Test due: ${a.test.metric}`, t: a.ticker, src: a.test.source }); });
    up.sort((p, q) => p.date.localeCompare(q.date));
    const listed = new Set(m.accumulate.map(a => a.ticker));
    const next = up.length ? `<ol class="next">${up.slice(0, 7).map(x => { const n = dayDiff(todayMYT, x.date); return `<li${x.t && listed.has(x.t) ? ' class="mine"' : ''}><span class="cd"><b>${n === 0 ? 'today' : n === 1 ? '1 day' : n + ' days'}</b>${fmtDate(x.date)}</span><span>${x.t ? `<b class="tkr">${esc(shortT(x.t))}</b> ` : ''}${esc(x.text)} ${link(x.src)}</span></li>`; }).join('')}</ol>`
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
      <div class="cp-main dsec"><div class="cp-title"><h2>Where every name sits</h2><span class="muted small">Last ${66} sessions against the memo's zones · closest to its buy line first · prices ${esc(fmtMYT(K.pricesAsOf))}</span></div>
        <div class="cp-key"><span><i class="k z-add"></i>add</span><span><i class="k z-buy"></i>buy</span><span><i class="k z-hold"></i>hold</span><span><i class="k z-above"></i>stop adding</span><span><i class="k z-trim"></i>trim</span>${bench ? `<span class="muted">${esc(K.bench)} 5 sessions ${bench.m5 >= 0 ? '+' : ''}${bench.m5.toFixed(1)}%</span>` : ''}</div>
        ${zones}</div>
      <div class="cp-side">
        <div class="dsec"><h2>Calls vs ${esc(K.bench)}</h2><p class="muted small">Each call's return minus ${esc(K.bench)}'s since it opened, in points. Above the line = beating the index. Daily closes.</p>${callsChart() || '<p class="muted small">No price history yet.</p>'}</div>
        <div class="dsec"><h2>Next up</h2>${next}</div>
        <div class="dsec"><h2>Where the book sits</h2><p class="muted small">Calls and holdings by layer of the chain, by count of names (not money). <span class="u-key u-accumulate">call</span> <span class="u-key u-holding">holding</span></p>${bookRows}</div>
      </div></section>`;
  }

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
          <dt>Accumulate zone</dt><dd>${a.levels ? ladder(a.ticker, a.levels, a.action, { w: 600, h: 190, days: 130, labels: true, call: c }) : ''}<details class="zone-text"><summary>The reasoning behind the lines</summary>${esc(a.zone)}</details></dd>
          <dt>Kills the idea</dt><dd>${esc(a.invalidation)}</dd>
          ${a.test ? `<dt>${a.action === 'watch' ? 'Re-entry test' : 'What decides it'}</dt><dd>${esc(a.test.metric)}: ${esc(a.test.threshold)}${a.test.by ? ' · by ' + fmtDate(a.test.by) : ''} ${link(a.test.source, a.test.sourceName)}</dd>` : ''}
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
        ${e.levels ? ladder(e.ticker, e.levels, 'accumulate', { w: 600, h: 170, days: 90, labels: true }) : ''}
        <div class="idea-foot">${(e.sources || []).map(u => link(u)).join(' ')}</div></article>`).join('');

    const alerts = deskIdx === 0 ? (K.alerts || []).slice(0, 6) : [];
    const kinds = {}; (K.changes || []).forEach(c => { kinds[c.kind] = (kinds[c.kind] || 0) + 1; });
    const KIND = { open: 'opened', close: 'closed', new: 'new', drop: 'dropped', move: 'level moves', flip: 'flips', event: 'event updates' };
    const changes = deskIdx === 0 && (K.changes || []).length ? `<details class="dsec changed" id="d-changed"><summary><h2>What changed</h2><span class="chg-sum">${Object.keys(kinds).map(k => `<b class="k-${esc(k)}">${kinds[k]} ${KIND[k] || k}</b>`).join('')}${alerts.length ? `<b class="k-alert">${alerts.length} price alerts</b>` : ''}</span></summary>
        <ul class="chg">${K.changes.map(c => `<li class="k-${esc(c.kind)}">${esc(c.text)}</li>`).join('')}</ul>
        ${alerts.length ? `<h4 class="sub">Price alerts</h4><ul class="chg">${alerts.map(a => `<li class="k-alert"><time>${esc(fmtMYT(a.at))}</time> ${esc(a.text)}</li>`).join('')}</ul>` : ''}
      </details>` : '';

    const mk = m.market;
    const movers = (mk.movers || []).length ? `<table class="movers"><tbody>${mk.movers.map(x => `<tr><td>${tick(x.ticker)}</td><td class="num">${pct(x.chg1w)}</td><td>${esc(x.why || '')} ${link(x.source)}</td></tr>`).join('')}</tbody></table>` : '';
    const posn = (mk.positioning || []).length ? `<ul class="devlist">${mk.positioning.map(x => `<li>${esc(x.text)} ${link(x.source)}</li>`).join('')}</ul>` : '';
    const cal = (mk.calendar || []).length ? `<ul class="devlist">${mk.calendar.map(x => `<li><time>${fmtDate(x.date)}</time>${esc(x.event)} ${link(x.source)}</li>`).join('')}</ul>` : '';

    const score = K.calls.length ? `<div class="scroll"><table class="score"><thead><tr><th>Ticker</th><th>Opened</th><th>Ref</th><th>Now / exit</th><th>Return</th><th>${esc(K.bench)}</th><th>Status</th></tr></thead><tbody>${
      K.calls.slice().reverse().map(c => `<tr><td>${tick(c.ticker)}</td><td>${fmtDate(c.opened)}</td><td class="num">${num(c.refPrice)} ${esc(c.currency || '')}</td><td class="num">${num(c.lastPrice)}</td><td class="num">${pct(c.ret)}</td><td class="num">${pct(c.benchRet)}</td><td>${c.closed ? 'closed ' + fmtDate(c.closed.date) : 'open'}</td></tr>`).join('')}</tbody></table></div>` : '<p class="muted">No calls yet.</p>';

    $('#memo').innerHTML = `
      <div class="memo-meta">Weekly memo · ${fmtDate(m.date)} · posts ${fmtDate(m.window.from)} to ${fmtDate(m.window.to)} ${pick}</div>
      <h1 class="headline">${esc(m.headline)}</h1>
      <nav class="dnav" aria-label="Memo sections">${[deskIdx === 0 && ['d-cockpit', 'Cockpit'], changes && ['d-changed', 'Changes'], events && ['d-since', 'Since'], ['d-picture', 'Picture'], ['d-list', 'List'], ['d-board', 'Board'], ['d-track', 'Track record'], ['d-wrap', 'Market'], ['d-pushback', 'Pushback'], ['d-score', 'Scorecard']].filter(Boolean).map(([id, l]) => `<button data-jump="${id}">${l}</button>`).join('')}</nav>
      ${deskIdx === 0 ? cockpit(m) : ''}
      ${changes}
      ${events ? `<section class="dsec" id="d-since"><h2>Since this memo</h2><p class="muted small">Event updates between weekly memos. They can move the alert levels; only the weekly memo opens or closes calls.</p>${events}</section>` : ''}
      <section class="dsec" id="d-picture"><h2>1 · The supply-chain picture</h2>
        <div class="two"><div><h4>Now</h4>${paras(m.picture.now)}</div><div><h4>Next</h4>${paras(m.picture.next)}</div></div></section>
      <section class="dsec" id="d-list"><h2>2 · Accumulate list</h2>
        <p class="muted small">Research support, not advice. Prices from your Google Sheet${K.pricesAsOf ? ' as of ' + esc(K.pricesAsOf.slice(0, 10)) : ''}.</p>${acc}</section>
      <section class="dsec" id="d-board"><h2>3 · Analyst board</h2><p class="muted small">Each cell links to the post. Hover or read the note for the reason.</p>${board}</section>
      <section class="dsec" id="d-track"><h2>Analyst track record</h2><p class="muted small">Every stance on the board, from the day it was first recorded, against ${esc(K.bench)}. A bull call earns the stock's move minus ${esc(K.bench)}'s; a bear call the reverse; mixed calls are not scored. Local-currency returns.${young ? ' Everything was recorded this week, so it all reads 0% for now; it fills in as prices move.' : ''}</p>${track}</section>
      <section class="dsec" id="d-wrap"><h2>4 · Market wrap</h2>${paras(mk.summary)}${movers}${posn ? '<h4 class="sub">Positioning: squeeze or re-rating?</h4>' + posn : ''}${cal ? '<h4 class="sub">Coming up</h4>' + cal : ''}</section>
      <section class="dsec pushback" id="d-pushback"><h2>The desk's pushback</h2><p class="muted small">Every analyst on the roster leans bullish. This is the other side.</p>${paras(m.pushback)}</section>
      <section class="dsec" id="d-score"><h2>Scorecard</h2><p class="muted small">Every accumulate call, marked to the latest price against ${esc(K.bench)}. Calls are never edited after the fact.</p>${score}</section>
      ${m.flags.length ? `<section class="dsec"><h2>Flags</h2><ul>${m.flags.map(f => `<li>${esc(f)}</li>`).join('')}</ul></section>` : ''}
      <p class="muted small">Collector last ran ${K.collectorLastRun ? esc(fmtMYT(K.collectorLastRun)) : 'never'} · following ${K.analysts.map(a => '@' + esc(a.handle)).join(', ')}</p>`;
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

  // ---------- events ----------
  document.addEventListener('click', e => {
    const lb = e.target.closest('[data-lens]');
    if (lb) { lens = lb.dataset.lens; try { localStorage.setItem('aie-lens', lens); } catch (err) { /* not remembered */ } render(); return; }
    const cell = e.target.closest('.cell[data-layer]');
    if (cell) { const el = $('#layer-' + CSS.escape(cell.dataset.layer)); if (el) el.scrollIntoView({ block: 'start', behavior: 'smooth' }); return; }
    const jump = e.target.closest('[data-jump]');
    if (jump) { const el = document.getElementById(jump.dataset.jump); if (el) { if (el.tagName === 'DETAILS') el.open = true; el.scrollIntoView({ block: 'start', behavior: 'smooth' }); } return; }
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
  document.addEventListener('mousemove', onChartMove);
  window.addEventListener('scroll', () => { $('#tip').hidden = true; }, { passive: true });
  const setHdr = () => document.documentElement.style.setProperty('--hdr', $('.top').offsetHeight + 'px');
  window.addEventListener('resize', setHdr); setHdr();

  // ---------- boot ----------
  $('#meta').textContent = `${D.companies.length} companies · ${D.layers.length} layers · ${D.narratives.length} narratives · ${D.developments.length} dated developments · updated ${fmtDate(D.meta.updated)}${K && K.pricesAsOf ? ` · desk prices ${fmtMYT(K.pricesAsOf)}` : ''}`;
  $('#foot').textContent = D.meta.disclaimer;
  document.title = D.meta.title;
  route();
})();
