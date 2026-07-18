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
     chipSpark(color)                              memo accent glyph

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

  /* Store icons are validated by generate_data_js.py before reaching data.js.
     This helper provides the trusted outer SVG shell and keeps icon colour/
     sizing consistent wherever a category mark appears. */
  function iconSVG(markup, color, size) {
    if (!markup) return null;
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    var iconSize = size || 24;
    svg.setAttribute("viewBox", "0 0 24 24");
    svg.setAttribute("fill", "none");
    svg.setAttribute("stroke", "currentColor");
    svg.setAttribute("stroke-width", "1.5");
    svg.setAttribute("stroke-linecap", "round");
    svg.setAttribute("stroke-linejoin", "round");
    svg.setAttribute("aria-hidden", "true");
    svg.setAttribute("width", iconSize);
    svg.setAttribute("height", iconSize);
    svg.innerHTML = markup;
    if (color) svg.style.color = color;
    return svg;
  }

  /* ==========================================================================
     Formatters — numbers, market cap, percent, dates.
     ======================================================================== */
  function fmtNum(n, dp) {
    return Number(n).toLocaleString(undefined, { minimumFractionDigits: dp, maximumFractionDigits: dp });
  }
  // Currency prefix for money formatting. USD (or unknown/absent) stays "$";
  // a non-USD listing uses its own symbol so a KRW/SEK figure isn't mislabeled
  // with a dollar sign (e.g. SK Hynix's cap reads ₩1312T, not $1312T). Falls
  // back to a "<CODE> " prefix for currencies without a known symbol.
  var MCAP_CURRENCY_SYMBOLS = {
    USD: "$", KRW: "₩", EUR: "€", GBP: "£", JPY: "¥", CNY: "¥",
    TWD: "NT$", HKD: "HK$", SGD: "S$", CAD: "C$", AUD: "A$", SEK: "kr "
  };
  function mcapCurrencyPrefix(currency) {
    if (!currency || currency === "USD") return "$";
    return MCAP_CURRENCY_SYMBOLS[currency] || (currency + " ");
  }
  function fmtMcap(v, currency) {
    if (v == null) return null;
    var abs = Math.abs(v), d = v, unit = "";
    if (abs >= 1e12) { d = v / 1e12; unit = "T"; }
    else if (abs >= 1e9) { d = v / 1e9; unit = "B"; }
    else if (abs >= 1e6) { d = v / 1e6; unit = "M"; }
    return mcapCurrencyPrefix(currency) + fmtNum(d, d < 10 ? 1 : 0) + unit;
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
     Display labels for desk stances and user ratings. The DATA VALUES stay
     "watch" (verdicts.json / localStorage untouched); only the on-screen word
     changes, so the three meanings of "watch" (conviction tier / desk stance /
     user rating) never collide on one card. CSS classes keep the data value.
     ======================================================================== */
  var STANCE_LABELS = { watch: "wait" };
  function stanceLabel(stance) { return STANCE_LABELS[stance] || stance; }
  var RATING_LABELS = { watch: "following" };
  function ratingLabel(rating) { return RATING_LABELS[rating] || rating; }

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
    { page: "desk",        label: "Desk",        href: "desk.html" },
    { page: "coverage",    label: "Coverage",    href: "index.html" },
    { page: "vault",       label: "Vault",       href: "vault.html" },
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

    var wordmark = mk("a", "aie-wordmark", "AI Infrastructure Explorer");
    wordmark.setAttribute("href", "desk.html");
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
     MEMO accent glyph — the one bit of illustration that survives the v8
     de-productization. The page hero art (artCoverage/Desk/Vault/Performance)
     and the soft-tile decorations (tileShape) were removed 18 Jul 2026 when the
     site became a dense analysis tool rather than an editorial product.
     ======================================================================== */

  // MEMO accent — a small chip glyph tinted with the ticker's category color.
  function chipSpark(color) {
    var c = color || "#7c828c";
    var pins = "", i, s;
    for (i = 0; i < 4; i++) {
      s = 11 + i * 6;                       // pin position along an edge
      pins += '<rect x="' + s + '" y="4" width="3" height="5" rx="1" fill="' + c + '"/>';   // top
      pins += '<rect x="' + s + '" y="31" width="3" height="5" rx="1" fill="' + c + '"/>';  // bottom
      pins += '<rect x="4" y="' + s + '" width="5" height="3" rx="1" fill="' + c + '"/>';    // left
      pins += '<rect x="31" y="' + s + '" width="5" height="3" rx="1" fill="' + c + '"/>';   // right
    }
    return '<svg class="memo-chip" viewBox="0 0 40 40" fill="none" aria-hidden="true" xmlns="http://www.w3.org/2000/svg">' +
      pins +
      '<rect x="9" y="9" width="22" height="22" rx="5" fill="#ffffff" stroke="' + c + '" stroke-width="2"/>' +
      '<rect x="15" y="15" width="10" height="10" rx="2.5" fill="' + c + '"/></svg>';
  }

  global.AIE = {
    STORAGE_KEYS: STORAGE_KEYS,
    slugify: slugify,
    renderInline: renderInline,
    renderBody: renderBody,
    readJSON: readJSON,
    seed: seed,
    setDrilldownOpen: setDrilldownOpen,
    iconSVG: iconSVG,
    fmtNum: fmtNum,
    fmtMcap: fmtMcap,
    fmtPct: fmtPct,
    fmtDate: fmtDate,
    categoryColor: categoryColor,
    stanceLabel: stanceLabel,
    ratingLabel: ratingLabel,
    paintGradientBorder: paintGradientBorder,
    renderNav: renderNav,
    linkForTicker: linkForTicker,
    makeThesisCard: makeThesisCard,
    chipSpark: chipSpark
  };
})(window);
