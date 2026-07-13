/* ============================================================================
   common.js — shared AIE namespace for the multi-page "Private Coverage" app.

   Load order (every page): data.js  →  common.js  →  the page's inline script.
   data.js defines window.AIE_DATA; this file reads it at call time (never
   caches it at load) so it is safe under file:// and across pages.

   Exposes window.AIE:
     STORAGE_KEYS, readJSON(key), seed()          localStorage seeding (aie_*)
     setDrilldownOpen(container, inner, open, cls) JS-measured max-height reveal
     fmtNum, fmtMcap, fmtPct, fmtDate              number / percent / date format
     categoryColor(id, fallback), paintGradientBorder(elId)   category colors
     renderNav(activePage, mount)                  theme.css top nav
     linkForTicker(sym)                            where a ticker chip points
     makeThesisCard(th, opts)                      shared .th-card renderer

   Colors are read from AIE_DATA.categories at runtime — never hardcoded here
   (CLAUDE.md hard rule #4).
   ========================================================================== */
(function (global) {
  "use strict";

  function data() { return global.AIE_DATA || null; }

  /* Tiny DOM builder (kept local; the page has its own el()). */
  function mk(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text != null) node.textContent = text;
    return node;
  }

  /* ==========================================================================
     localStorage seeding — version-aware so the ingest pipeline (regenerates
     data.js + bumps meta.version) surfaces for returning users.
     - tickers: seeded once; on a version bump, NEW tickers from data.js merge
       in while the user's per-ticker rating is preserved.
     - theses: backend-owned — (re)seeded from data.js on a bump.
     Static config (categories/center/countries/priorities) is read directly
     from AIE_DATA, never persisted (CLAUDE.md rule #4).
     ======================================================================== */
  var STORAGE_KEYS = {
    tickers: "aie_tickers",
    theses: "aie_theses",
    settings: "aie_settings"
  };

  function readJSON(key) {
    try {
      var raw = localStorage.getItem(key);
      return raw === null ? null : JSON.parse(raw);
    } catch (err) {
      return null;
    }
  }

  function seed() {
    var DATA = data();
    if (!DATA) {
      console.error("AIE_DATA missing — data.js failed to load before common.js.");
      return;
    }
    try {
      var dataVersion = (DATA.meta && DATA.meta.version) || "1.0";
      var settings = readJSON(STORAGE_KEYS.settings);
      var firstRun = settings === null;
      var seededVersion = settings && settings.version;
      var versionChanged = seededVersion !== dataVersion;

      // tickers: seed on first run; on a version bump, refresh static fields
      // from data.js (the source of truth) while preserving the user's
      // per-ticker rating. Locally-added tickers not in data.js are kept.
      var tickers = readJSON(STORAGE_KEYS.tickers);
      if (tickers === null) {
        tickers = (DATA.tickers || []).slice();
      } else if (versionChanged) {
        var ratingBy = {};
        tickers.forEach(function (t) { if (t.rating) ratingBy[t.ticker] = t.rating; });
        var refreshed = (DATA.tickers || []).map(function (d) {
          if (!ratingBy[d.ticker]) return d;
          var copy = {};
          for (var k in d) { copy[k] = d[k]; }
          copy.rating = ratingBy[d.ticker];   // keep only the user's rating
          return copy;
        });
        var known = {};
        refreshed.forEach(function (t) { known[t.ticker] = true; });
        tickers.forEach(function (t) { if (!known[t.ticker]) refreshed.push(t); });
        tickers = refreshed;
      }
      localStorage.setItem(STORAGE_KEYS.tickers, JSON.stringify(tickers));

      // theses: backend-owned — (re)seed from data.js on first run or bump.
      if (firstRun || versionChanged || readJSON(STORAGE_KEYS.theses) === null) {
        localStorage.setItem(STORAGE_KEYS.theses, JSON.stringify(DATA.theses || []));
      }

      // settings: record the data.js version we have now seeded from.
      localStorage.setItem(STORAGE_KEYS.settings, JSON.stringify({
        version: dataVersion,
        lastUpdated: (DATA.meta && DATA.meta.lastUpdated) || null
      }));
    } catch (err) {
      // Some browsers restrict localStorage under file:// — fail gracefully.
      console.warn("localStorage unavailable; seeding skipped.", err);
    }
  }

  /* ==========================================================================
     Unified drill-down: JS-measured max-height, not CSS grid-template-rows
     0fr->1fr — some ancestors (overflow-constrained cards, flex columns) give
     the grid track a bounded "available space" instead of true auto-sizing,
     silently resolving 1fr to 0. Measuring inner.scrollHeight sidesteps that.
     `container` toggles the opacity/margin class; `inner` is the wrapper whose
     natural height we measure. Open drill-downs re-measure on resize.
     ======================================================================== */
  var openDrilldowns = []; // {container, inner} pairs currently open
  function setDrilldownOpen(container, inner, open, activeClass) {
    if (activeClass) container.classList.toggle(activeClass, open);
    container.style.maxHeight = open ? inner.scrollHeight + "px" : "0px";
    var idx = openDrilldowns.findIndex(function (d) { return d.container === container; });
    if (open && idx === -1) openDrilldowns.push({ container: container, inner: inner });
    else if (!open && idx !== -1) openDrilldowns.splice(idx, 1);
  }
  global.addEventListener("resize", function () {
    openDrilldowns.forEach(function (d) {
      d.container.style.maxHeight = d.inner.scrollHeight + "px";
    });
  });

  /* ==========================================================================
     Formatters — numbers, market cap, percent, dates.
     ======================================================================== */
  function fmtNum(n, dp) {
    return Number(n).toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
  }
  function fmtMcap(v) {
    if (v == null) return null;
    var abs = Math.abs(v), d = v, unit = "";
    if (abs >= 1e12) { d = v / 1e12; unit = "T"; }
    else if (abs >= 1e9) { d = v / 1e9; unit = "B"; }
    else if (abs >= 1e6) { d = v / 1e6; unit = "M"; }
    return "$" + fmtNum(d, d < 10 ? 1 : 0) + unit;
  }
  // Signed percent string, e.g. +1.2% / -0.4% / 0.0%. Matches the legacy inline
  // formatting used in the watchlist pctCell and the map heat label.
  function fmtPct(v, dp) {
    if (v == null) return "—";
    dp = dp == null ? 1 : dp;
    return (v > 0 ? "+" : "") + Number(v).toFixed(dp) + "%";
  }
  // ISO date (or YYYY-MM-DD prefix) -> "06 Jul 2026". Returns the input
  // untouched if it isn't a recognisable date (never throws).
  var MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
  function fmtDate(iso) {
    if (!iso) return "";
    var m = /^(\d{4})-(\d{2})-(\d{2})/.exec(String(iso));
    if (!m) return String(iso);
    var y = m[1], mo = parseInt(m[2], 10), d = parseInt(m[3], 10);
    if (mo < 1 || mo > 12) return String(iso);
    return (d < 10 ? "0" + d : d) + " " + MONTHS[mo - 1] + " " + y;
  }

  /* ==========================================================================
     Category-color helpers. Colors live in data.js (rule #4).
     ======================================================================== */
  function categoryColor(id, fallback) {
    var d = data();
    var c = d && d.categories && d.categories[id];
    return (c && c.color) || fallback || "#94a3b8";
  }
  // No-op since the Phase 6 rebrand: the 3px top border is now pure-CSS brand
  // chrome (theme.css --brand-grad). Kept because every page calls it at boot.
  function paintGradientBorder() {}

  /* ==========================================================================
     Top nav (theme.css .aie-nav). Serif wordmark · PRIVATE COVERAGE small-caps
     · page links. `activePage` is one of the page ids below; `mount` is an
     element or selector (default "#topNav"). No-op if the mount is absent.
     ======================================================================== */
  var NAV_PAGES = [
    { page: "coverage",    label: "Coverage",    href: "index.html" },
    { page: "desk",        label: "Desk",        href: "desk.html" },
    { page: "vault",       label: "Vault",       href: "vault.html" },
    { page: "graph",       label: "Graph",       href: "vault.html?view=graph" },
    { page: "performance", label: "Performance", href: "performance.html", disabled: true }
  ];

  // Performance stays greyed until the calls ledger has a real track record
  // (>=3 stamped calls) — an empty performance page never ships.
  var MIN_CALLS_FOR_NAV = 3;
  function performanceEnabled() {
    var d = data();
    var calls = (d && d.calls && d.calls.calls) || [];
    return calls.length >= MIN_CALLS_FOR_NAV;
  }

  function renderNav(activePage, mount) {
    var host = typeof mount === "string" ? document.querySelector(mount)
             : (mount || document.getElementById("topNav"));

    var masthead = mk("header", "aie-masthead");
    var nav = mk("nav", "aie-nav");
    nav.setAttribute("aria-label", "Site");
    var inner = mk("div", "aie-nav-inner");

    var wordmark = mk("a", "aie-wordmark", "AI Supply Desk");
    wordmark.setAttribute("href", "index.html");
    inner.appendChild(wordmark);

    inner.appendChild(mk("span", "aie-label aie-kicker", "Private Coverage · Not Advice"));
    inner.appendChild(mk("span", "aie-nav-spacer"));

    var links = mk("div", "aie-nav-links");
    NAV_PAGES.forEach(function (p) {
      var disabled = p.disabled && !(p.page === "performance" && performanceEnabled());
      var cls = disabled ? "is-disabled" : (p.page === activePage ? "is-active" : "");
      var a = mk("a", cls || null, p.label);
      if (!disabled) a.setAttribute("href", p.href);
      if (p.page === activePage) a.setAttribute("aria-current", "page");
      links.appendChild(a);
    });
    inner.appendChild(links);

    nav.appendChild(inner);
    masthead.appendChild(nav);
    masthead.appendChild(mk("hr", "aie-rule-double"));

    if (host) { host.textContent = ""; host.appendChild(masthead); }
    return masthead;
  }

  /* ==========================================================================
     Where a ticker chip points (P15). Best available destination, in order:
       1. a coverage memo for the symbol   -> memo.html?ticker=SYM
       2. a knowledge-vault ticker page    -> vault.html?page=<slug>
       3. otherwise the watchlist          -> desk.html#chapter-watchlist
     Reads AIE_DATA live so it stays correct as memos/vault grow.
     ======================================================================== */
  function linkForTicker(sym) {
    var d = data();
    var s = String(sym || "").toUpperCase();
    if (d && s) {
      var memos = (d.memos && d.memos.memos) || [];
      if (memos.some(function (m) { return (m.ticker || "").toUpperCase() === s; })) {
        return "memo.html?ticker=" + encodeURIComponent(s);
      }
      var slug = slugify(s);
      var pages = (d.vault && d.vault.pages) || [];
      if (pages.some(function (p) { return p.type === "ticker" && p.slug === slug; })) {
        return "vault.html?page=" + encodeURIComponent(slug);
      }
    }
    return "desk.html#chapter-watchlist";
  }

  /* ==========================================================================
     Thesis card — shared renderer (moved out of desk.html so the Evidence feed,
     the hero "latest signal", the Brain sources drill-down, and memo.html's
     sources appendix all render one identical card). Styles live in theme.css
     (.th-card family). `opts.compact` clamps long bodies + tints the card.
     ======================================================================== */
  function tickerCategoryColor(sym) {
    var d = data();
    var tk = d && d.tickers && d.tickers.find(function (t) { return t.ticker === sym; });
    if (!tk) return null;
    var c = d.categories && d.categories[tk.category];
    return (c && c.color) || null;
  }

  function makeThesisCard(th, opts) {
    opts = opts || {};
    var card = mk("div", "th-card"
      + (th.conviction === "high" ? " high-conviction" : "")
      + (opts.compact ? " th-card-compact" : ""));

    var meta = mk("div", "th-card-meta");
    var dateStr = th.postedAt || th.ingestedAt || "";
    if (dateStr) meta.appendChild(mk("span", "th-date", String(dateStr).slice(0, 10)));
    meta.appendChild(mk("span", "th-conviction " + (th.conviction === "high" ? "high" : "normal"),
      th.conviction === "high" ? "High conviction" : "Note"));
    if (th.sourceUrl) {
      var link = mk("a", "th-source", "View post ↗");
      link.href = th.sourceUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      meta.appendChild(link);
    }
    card.appendChild(meta);

    var body = th.text || "";
    if (opts.compact && body.length > 280) body = body.slice(0, 280).trim() + "…";
    card.appendChild(mk("p", "th-text", body));

    var tickers = th.tickers || [];
    if (tickers.length) {
      var chips = mk("div", "th-tickers");
      tickers.forEach(function (sym) {
        var chip = mk("a", "th-ticker", sym);
        chip.href = linkForTicker(sym);
        var color = tickerCategoryColor(sym);
        if (color) chip.style.setProperty("--t-color", color);
        chips.appendChild(chip);
      });
      card.appendChild(chips);
    }
    return card;
  }

  /* ==========================================================================
     Inline prose markup — the one parser for the whole app.
     `slugify` matches ingest/vault_sync.slugify() so [[wikilinks]] resolve to
     the right vault page. `renderInline` appends parsed nodes into a container:
       **bold**        -> <strong>
       $TICK           -> ticker chip (href from linkForTicker, category accent)
       [[wikilink]]    -> quiet link to vault.html?page=<slug>
     `renderBody` splits a body on blank lines into <p> nodes (class configurable
     so each page keeps its own paragraph type scale). Shared by memo.html and
     vault.html (CLAUDE.md rule #3 — no duplicated logic).
     ======================================================================== */
  var INLINE_RE = /(\*\*[^*]+\*\*|\$[A-Za-z][A-Za-z0-9.\-]*|\[\[[^\]]+\]\])/g;

  function slugify(s) {
    return String(s).toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "") || "page";
  }

  function renderInline(container, text) {
    INLINE_RE.lastIndex = 0;
    var last = 0, m;
    while ((m = INLINE_RE.exec(text)) !== null) {
      if (m.index > last) container.appendChild(document.createTextNode(text.slice(last, m.index)));
      var tok = m[0];
      if (tok.slice(0, 2) === "**") {
        container.appendChild(mk("strong", null, tok.slice(2, -2)));
      } else if (tok.charAt(0) === "$") {
        var sym = tok.slice(1).toUpperCase();
        var chip = mk("a", "aie-chip aie-chip--ticker aie-tickerchip", sym);
        chip.href = linkForTicker(sym);
        var color = tickerCategoryColor(sym);
        if (color) chip.style.setProperty("--chip-accent", color);
        container.appendChild(chip);
      } else { // [[wikilink]]
        var inner = tok.slice(2, -2).trim();
        var link = mk("a", "aie-wikilink", inner);
        link.href = "vault.html?page=" + encodeURIComponent(slugify(inner));
        container.appendChild(link);
      }
      last = INLINE_RE.lastIndex;
    }
    if (last < text.length) container.appendChild(document.createTextNode(text.slice(last)));
  }

  function renderBody(body, pClass) {
    var out = [];
    String(body || "").split(/\n\s*\n/).forEach(function (para) {
      var trimmed = para.trim();
      if (!trimmed) return;
      var p = mk("p", pClass || "aie-prose-p");
      renderInline(p, trimmed);
      out.push(p);
    });
    return out;
  }

  /* ==========================================================================
     UNPACKED HERO ART — a gem + sparkle cluster as one inline SVG string.
     Pure brand-chrome decoration (blue→violet→teal), file://-safe, no external
     assets. Category colors are untouched (hard rule #4 governs data-driven
     hues, not the illustration). Reused by the index + desk heroes so the
     "Unpacked" visual language lives in one place.
     ======================================================================== */
  function heroArt() {
    return [
'<svg class="unf-art-svg" viewBox="0 0 440 380" fill="none" role="img" aria-label="Abstract gem and sparkle cluster" xmlns="http://www.w3.org/2000/svg">',
  '<defs>',
    '<radialGradient id="unfBokeh" cx="42%" cy="36%" r="64%">',
      '<stop offset="0%" stop-color="#e9edfc"/>',
      '<stop offset="58%" stop-color="#dde4f9"/>',
      '<stop offset="100%" stop-color="#ccd8f3"/>',
    '</radialGradient>',
    '<linearGradient id="unfGemMain" x1="0" y1="0" x2="1" y2="1">',
      '<stop offset="0%" stop-color="#2b6bf3"/>',
      '<stop offset="52%" stop-color="#2aa6d9"/>',
      '<stop offset="100%" stop-color="#16b9c8"/>',
    '</linearGradient>',
    '<linearGradient id="unfGemTeal" x1="0" y1="0" x2="1" y2="1">',
      '<stop offset="0%" stop-color="#3ad0ca"/>',
      '<stop offset="100%" stop-color="#159fbe"/>',
    '</linearGradient>',
    '<linearGradient id="unfGemBlue" x1="0" y1="0" x2="1" y2="1">',
      '<stop offset="0%" stop-color="#2b6bf3"/>',
      '<stop offset="100%" stop-color="#6d92f6"/>',
    '</linearGradient>',
    '<linearGradient id="unfCardA" x1="0" y1="0" x2="1" y2="1">',
      '<stop offset="0%" stop-color="#cabdf8"/>',
      '<stop offset="100%" stop-color="#a086ef"/>',
    '</linearGradient>',
    '<linearGradient id="unfCardB" x1="0" y1="0" x2="1" y2="1">',
      '<stop offset="0%" stop-color="#bac6f9"/>',
      '<stop offset="100%" stop-color="#8ba4f1"/>',
    '</linearGradient>',
    '<filter id="unfSoft" x="-40%" y="-40%" width="180%" height="180%">',
      '<feDropShadow dx="0" dy="12" stdDeviation="16" flood-color="#33408a" flood-opacity="0.22"/>',
    '</filter>',
  '</defs>',
  '<circle cx="252" cy="150" r="150" fill="url(#unfBokeh)"/>',
  '<circle cx="392" cy="70" r="40" fill="#d4ddf6"/>',
  '<circle cx="74" cy="252" r="32" fill="#c0efe7"/>',
  '<g filter="url(#unfSoft)">',
    '<rect x="168" y="120" width="118" height="118" rx="20" fill="url(#unfCardB)" opacity="0.55" transform="rotate(-13 227 179)"/>',
    '<rect x="200" y="150" width="118" height="118" rx="20" fill="url(#unfCardA)" opacity="0.5" transform="rotate(11 259 209)"/>',
  '</g>',
  '<path filter="url(#unfSoft)" fill="url(#unfGemMain)" d="M235,110 C240.6,160.4 254.6,174.4 305,180 C254.6,185.6 240.6,199.6 235,250 C229.4,199.6 215.4,185.6 165,180 C215.4,174.4 229.4,160.4 235,110 Z"/>',
  '<path fill="#ffffff" opacity="0.34" d="M235,150 C237.4,171.6 243.4,177.6 265,180 C243.4,182.4 237.4,188.4 235,210 C232.6,188.4 226.6,182.4 205,180 C226.6,177.6 232.6,171.6 235,150 Z"/>',
  '<path fill="url(#unfGemTeal)" d="M150,86 C152.08,104.72 157.28,109.92 176,112 C157.28,114.08 152.08,119.28 150,138 C147.92,119.28 142.72,114.08 124,112 C142.72,109.92 147.92,104.72 150,86 Z"/>',
  '<path fill="url(#unfGemBlue)" d="M330,157 C331.2,167.8 335.8,170.8 345,172 C335.8,173.2 331.2,176.2 330,187 C328.8,176.2 324.2,173.2 315,172 C324.2,170.8 328.8,167.8 330,157 Z"/>',
'</svg>'
    ].join("");
  }

  /* Small decorative corner shape for a soft-tile (arc | ring | square | none),
     tinted with `color`. Returns an inline SVG string sized to sit in the
     bottom-right of a .unf-tile. */
  function tileShape(kind, color) {
    var c = color || "#94a3b8";
    if (kind === "arc") {
      return '<svg class="tile-shape" viewBox="0 0 120 120" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">' +
        '<path d="M18 108a90 90 0 0 1 90-90" stroke="' + c + '" stroke-width="16" stroke-linecap="round"/>' +
        '</svg>';
    }
    if (kind === "ring") {
      return '<svg class="tile-shape" viewBox="0 0 120 120" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">' +
        '<path d="M104 60a44 44 0 1 1-24-39" stroke="' + c + '" stroke-width="14" stroke-linecap="round"/>' +
        '</svg>';
    }
    if (kind === "square") {
      return '<svg class="tile-shape" viewBox="0 0 120 120" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">' +
        '<rect x="34" y="34" width="72" height="72" rx="16" fill="' + c + '" transform="rotate(18 70 70)"/>' +
        '</svg>';
    }
    return "";
  }

  global.AIE = {
    STORAGE_KEYS: STORAGE_KEYS,
    slugify: slugify,
    renderInline: renderInline,
    renderBody: renderBody,
    readJSON: readJSON,
    seed: seed,
    setDrilldownOpen: setDrilldownOpen,
    fmtNum: fmtNum,
    fmtMcap: fmtMcap,
    fmtPct: fmtPct,
    fmtDate: fmtDate,
    categoryColor: categoryColor,
    paintGradientBorder: paintGradientBorder,
    renderNav: renderNav,
    linkForTicker: linkForTicker,
    makeThesisCard: makeThesisCard,
    heroArt: heroArt,
    tileShape: tileShape
  };
})(window);
