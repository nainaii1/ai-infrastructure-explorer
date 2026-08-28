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
     viewsForTicker(sym), viewStats(rows)          the analyst's per-ticker views
     viewDensity(sym)                              cached {argued,total} for one name
     makeViewsBlock(sym, opts)                     shared .aie-views renderer
     fundamentalsFor(sym), makeRevenueBlock(sym)   SEC revenue, as filed
     exposureFor(sym), aiRevenue(sym)              AI exposure (operator judgement)
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
    settings: "aie_settings",
    // Watchlist view state (sort key/direction + the two filters). A VIEW
    // preference, not data — seeding never touches it.
    wlView: "aie_wl_view"
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
    USD: "$", KRW: "₩", EUR: "€", GBP: "£", GBX: "p", JPY: "¥", CNY: "¥",
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
  // v9 labels. "Coverage" is retired — it read as trade jargon and said
  // nothing about what the page holds. The page id stays "coverage" so every
  // renderNav("coverage") call site and #anchor keeps working.
  var NAV_PAGES = [
    { page: "desk",        label: "Today",  href: "desk.html" },
    { page: "coverage",    label: "Notes",  href: "index.html" },
    { page: "vault",       label: "Vault",  href: "vault.html" },
    { page: "performance", label: "Record", href: "performance.html", disabled: true }
  ];

  // Performance is nav-live as soon as there is ANY stamped call (operator
  // decision, 2026-07-26). The page is the desk's scorecard — hiding a losing
  // record behind a threshold is exactly the feedback loop it exists to close.
  var MIN_CALLS_FOR_NAV = 1;
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

    inner.appendChild(mk("span", "aie-label aie-kicker", "My own research · Not advice"));
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
     Analyst views — what he ARGUED about one ticker, not how often he named it.

     ingest/views.py reads every one of his posts and records a view per
     (post, ticker), because one post routinely holds opposing stances on
     different names. These three functions are the read side of that work:
     viewsForTicker mirrors views.summarize_ticker_views() exactly (same filter,
     same newest-first order), viewStats counts the split, and makeViewsBlock
     renders it. Markup is styled by .aie-views* in theme.css.

     Only `source: "x"` posts count — a desk research finding is not his
     attention (invariant 10), the same rule analystMentions follows.
     ======================================================================== */
  var VIEW_MAX_ROWS = 6;          /* keep the card short; the footer owns the rest */
  var DIR_LABELS = { bull: "bull", bear: "bear" };

  /* Signal density for EVERY ticker in one pass, cached.
     The watchlist sorts and renders a density cell per row; calling
     viewsForTicker() once per row would rescan all theses 135 times per
     render. This walks them once and memoises, keyed on the theses array
     identity so a regenerated data.js invalidates it naturally. */
  var _densityCache = null;
  var _densityFor = null;
  function viewDensity(sym) {
    var d = data();
    var theses = (d && d.theses) || [];
    if (_densityFor !== theses) {
      _densityFor = theses;
      _densityCache = {};
      theses.forEach(function (th) {
        if (th.source !== "x") return;
        (th.views || []).forEach(function (v) {
          var k = String(v.ticker || "").toUpperCase();
          if (!k) return;
          var row = _densityCache[k]
            || (_densityCache[k] = { argued: 0, total: 0, bull: 0, bear: 0 });
          row.total++;
          if (v.direction === "bull" || v.direction === "bear") {
            row.argued++;
            row[v.direction]++;
          }
        });
      });
    }
    return _densityCache[String(sym || "").toUpperCase()] || null;
  }

  function viewsForTicker(sym) {
    var d = data();
    var want = String(sym || "").toUpperCase();
    if (!d || !d.theses || !want) return [];
    var rows = [];
    d.theses.forEach(function (th) {
      if (th.source !== "x") return;
      (th.views || []).forEach(function (v) {
        if (String(v.ticker || "").toUpperCase() !== want) return;
        rows.push({
          postedAt: th.postedAt || th.ingestedAt || "",
          thesisId: th.id,
          sourceUrl: th.sourceUrl,
          direction: v.direction,
          why: v.why,
          numbers: v.numbers,
          horizon: v.horizon
        });
      });
    });
    rows.sort(function (a, b) {
      return String(b.postedAt).localeCompare(String(a.postedAt));
    });
    return rows;
  }

  /* Anything that is not literally "bull" or "bear" counts as a bare mention.
     Fail inert (invariant 3): an unreadable direction must never be read as a
     case he made. */
  function viewStats(rows) {
    var s = { total: rows.length, argued: 0, bull: 0, bear: 0, bare: 0, lastArgued: null };
    rows.forEach(function (r) {
      if (r.direction === "bull" || r.direction === "bear") {
        s.argued++;
        s[r.direction]++;
        if (!s.lastArgued) s.lastArgued = r.postedAt;   /* rows are newest-first */
      } else {
        s.bare++;
      }
    });
    return s;
  }

  function makeViewRow(r) {
    var row = mk("div", "aie-view");
    var meta = mk("div", "aie-view-meta");
    var dir = DIR_LABELS[r.direction] || "neutral";
    meta.appendChild(mk("span", "aie-badge aie-dir--" + dir,
      DIR_LABELS[r.direction] || "mentioned"));
    if (r.postedAt) {
      meta.appendChild(mk("span", "aie-view-date", fmtDate(String(r.postedAt).slice(0, 10))));
    }
    if (r.sourceUrl) {
      var link = mk("a", "aie-view-source", "post ↗");
      link.href = r.sourceUrl;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      meta.appendChild(link);
    }
    row.appendChild(meta);
    row.appendChild(mk("p", "aie-view-why", r.why || "—"));

    /* Figures and timing — the two things a mention count can never carry. */
    var facts = [];
    if (r.numbers) facts.push(String(r.numbers));
    if (r.horizon) facts.push(String(r.horizon));
    if (facts.length) row.appendChild(mk("p", "aie-view-facts", facts.join("  ·  ")));
    return row;
  }

  /* Posts of his that name this ticker but have not been through views.py yet.
     Reported in the footer so the density's denominator is never mistaken for
     the mention count on the badge above it: they legitimately differ, because
     `mentions` is counted AFTER scorer.canonicalize_theses folds in the
     tickerAliases (a $SIVEF post counts toward SIVE) while a view is pinned to
     the post's own raw tickers[] (invariant 5) and so has no SIVE to attach to.
     See PROJECT.md "Known issues" — the fix belongs in extraction, not here. */
  function unreadPostCount(sym) {
    var d = data();
    var want = String(sym || "").toUpperCase();
    if (!d || !d.theses || !want) return 0;
    var n = 0;
    d.theses.forEach(function (th) {
      if (th.source !== "x" || th.viewsExtractedAt) return;
      if ((th.tickers || []).indexOf(want) >= 0) n++;
    });
    return n;
  }

  function makeViewsBlock(sym, opts) {
    opts = opts || {};
    var rows = viewsForTicker(sym);
    if (!rows.length) return null;               /* never argued, never mentioned */
    var st = viewStats(rows);
    var max = opts.max != null ? opts.max : VIEW_MAX_ROWS;

    var box = mk("div", "aie-views");
    var head = mk("div", "aie-views-head");
    head.appendChild(mk("span", "aie-views-label", "What he's argued"));
    var density = mk("span", "aie-views-density");
    density.appendChild(mk("b", null, String(st.argued)));
    density.appendChild(document.createTextNode(" / " + st.total + " argued"));
    density.title = "Of the " + st.total + " posts of his that name "
      + String(sym).toUpperCase() + " and have been read, " + st.argued
      + " make a case for it"
      + (st.bull ? " · " + st.bull + " bull" : "")
      + (st.bear ? " · " + st.bear + " bear" : "")
      + ". Not the same base as the mention count above, which also counts "
      + "desk research findings and ticker aliases.";
    head.appendChild(density);
    box.appendChild(head);

    /* Show the arguments. When there are none, show a couple of the bare
       mentions instead — "six mentions, zero arguments" is itself the finding,
       and seeing what a reference looks like is what makes it land. */
    var shown = rows.filter(function (r) {
      return r.direction === "bull" || r.direction === "bear";
    });
    var showingBare = false;
    if (!shown.length) {
      shown = rows.slice(0, 2);
      showingBare = true;
    }
    var hidden = Math.max(0, shown.length - max);
    var visible = shown.slice(0, max);

    /* Never let the cap hide that he argued AGAINST the name. The watchlist
       shows 3 rows and flags "5 bear" in the column; if the three newest
       happen to be bull, clicking through to three BULL badges contradicts the
       flag. Swap the oldest shown row for his most recent bear view.
       This cannot break the date ordering: any bear missing from the slice is
       older than every row in it, or it would have been in the slice already. */
    if (visible.length && st.bear) {
      var hasBear = visible.some(function (r) { return r.direction === "bear"; });
      if (!hasBear) {
        var newestBear = shown.filter(function (r) { return r.direction === "bear"; })[0];
        if (newestBear) visible[visible.length - 1] = newestBear;
      }
    }
    visible.forEach(function (r) { box.appendChild(makeViewRow(r)); });

    var foot = [];
    if (hidden) foot.push(hidden + " earlier argument" + (hidden === 1 ? "" : "s") + " not shown");
    if (st.bare) {
      foot.push(st.bare + (showingBare ? " mention" : " other mention")
        + (st.bare === 1 ? "" : "s") + " carried no argument");
    }
    var unread = unreadPostCount(sym);
    if (unread) foot.push(unread + " post" + (unread === 1 ? "" : "s") + " not read yet");
    if (foot.length) box.appendChild(mk("p", "aie-views-foot", foot.join("  ·  ")));
    return box;
  }

  /* ==========================================================================
     Revenue, as filed with the SEC (PROJECT.md Step 2).

     `ingest/fundamentals.py` writes AIE_DATA.fundamentals; this renders it.
     The first block on a ticker card that describes the COMPANY rather than
     the analyst's attention, so it deliberately sits next to his case.

     A name with no filing renders a one-line reason instead of nothing:
     SIVE is the highest-conviction name in the book and is listed in
     Stockholm, so silence there would read as "no revenue" rather than
     "not a US filer".
     ======================================================================== */
  function fundamentalsFor(sym) {
    var d = data();
    var f = (d && d.fundamentals) || {};
    var want = String(sym || "").toUpperCase();
    return (f.companies || {})[want] || null;
  }

  function fundamentalsGap(sym) {
    var d = data();
    var f = (d && d.fundamentals) || {};
    return (f.unavailable || {})[String(sym || "").toUpperCase()] || null;
  }

  /* Plain-English version of the machine reason recorded by the fetcher. */
  var GAP_WORDS = [
    [/not US-listed|no SEC filer/i, "Not a US filer, so nothing to read"],
    [/no annual revenue concept/i, "Registered with the SEC but files no revenue figures"],
    [/symbol collision/i, "Ticker clashes with a different company at the SEC"]
  ];
  function gapLabel(reason) {
    for (var i = 0; i < GAP_WORDS.length; i++) {
      if (GAP_WORDS[i][0].test(reason)) return GAP_WORDS[i][1];
    }
    return "No SEC filing on record";
  }

  var REV_BAR_PX = 34;    /* tallest bar; the tick label sits below it */

  /* AI exposure — the operator's judgement (PROJECT.md Step 3). Not filed and
     not derivable: SEC companyfacts carries no segment dimension. It therefore
     NEVER renders as a bare number — the confidence level and the stated basis
     travel with it, and an unassessed name says so rather than showing 0%. */
  function exposureFor(sym) {
    var d = data();
    var e = (d && d.exposure) || {};
    return (e.companies || {})[String(sym || "").toUpperCase()] || null;
  }

  /* Filed revenue x judged exposure. An estimate by construction: it
     multiplies an audited number by an unaudited one, so it is only ever
     rendered next to its confidence. */
  function aiRevenue(sym) {
    var a = exposureFor(sym), f = fundamentalsFor(sym);
    if (!a || !f) return null;
    var latest = f.latest || (f.years || [])[(f.years || []).length - 1];
    if (!latest || typeof latest.revenue !== "number"
        || typeof a.aiExposure !== "number") return null;
    return {
      value: latest.revenue * (a.aiExposure / 100),
      currency: f.currency, fy: latest.fy,
      exposure: a.aiExposure, confidence: a.confidence
    };
  }

  function makeExposureRow(sym) {
    var a = exposureFor(sym);
    var row = mk("div", "aie-exp");
    row.appendChild(mk("span", "aie-exp-label", "AI exposure"));
    if (!a) {
      var none = mk("span", "aie-exp-none", "Not assessed yet");
      none.title = "Nobody publishes this. It is a judgement call, recorded "
        + "with ingest/assess_exposure.py once you have made it.";
      row.appendChild(none);
      return row;
    }
    row.appendChild(mk("span", "aie-exp-pct", fmtNum(a.aiExposure, 0) + "%"));
    var est = aiRevenue(sym);
    if (est) {
      var e = mk("span", "aie-exp-est",
                 "\u2248 " + fmtMcap(est.value, est.currency) + " of FY" + est.fy);
      e.title = "Estimated: filed revenue \u00d7 your exposure judgement. Not a "
        + "filed figure.";
      row.appendChild(e);
    }
    /* Whose call this was. Absent/"operator" renders nothing — the field is
       only interesting when the judgement was NOT the operator's own, and a
       chip on every row would teach the eye to skip it. */
    var by = a.assessedBy;
    if (by && by !== "operator") {
      var byChip = mk("span", "aie-exp-by", by === "claude-estimate" ? "est." : by);
      byChip.title = "Not your own researched judgement — recorded by " + by
        + ". Treat it as a placeholder until you have checked it.";
      row.appendChild(byChip);
    }
    var conf = mk("span", "aie-exp-conf conf-" + a.confidence, a.confidence);
    conf.title = by && by !== "operator"
      ? "How sure the estimate is — not a measurement"
      : "How sure you were when you recorded this";
    row.appendChild(conf);
    if (a.basis) {
      var basis = mk("p", "aie-exp-basis", a.basis);
      if ((a.sources || []).length) basis.title = "Sources: " + a.sources.join(" \u00b7 ");
      row.appendChild(basis);
    }
    return row;
  }

  function makeRevenueBlock(sym) {
    var rec = fundamentalsFor(sym);
    if (!rec) {
      var reason = fundamentalsGap(sym);
      /* No filing AND no judgement is genuinely nothing to say. But a name
         with an exposure call and no filing still has something worth
         showing — SIVE is the clearest case in the book. */
      if (!reason && !exposureFor(sym)) return null;
      var miss = mk("div", "aie-rev");
      var mh = mk("div", "aie-rev-head");
      mh.appendChild(mk("span", "aie-rev-label", "Revenue"));
      mh.appendChild(mk("span", "aie-rev-gap",
                        reason ? gapLabel(reason) : "No SEC filing on record"));
      if (reason) mh.title = reason;
      miss.appendChild(mh);
      miss.appendChild(makeExposureRow(sym));
      return miss;
    }

    var years = rec.years || [];
    if (!years.length) return null;
    var latest = rec.latest || years[years.length - 1];
    var box = mk("div", "aie-rev");

    var head = mk("div", "aie-rev-head");
    head.appendChild(mk("span", "aie-rev-label", "Revenue"));
    var src = mk("span", "aie-rev-src", "SEC filings");
    src.title = "As filed: " + rec.taxonomy + " " + rec.tag
      + (rec.entityName ? " \u00b7 " + rec.entityName : "");
    head.appendChild(src);
    box.appendChild(head);

    var top = mk("div", "aie-rev-top");
    top.appendChild(mk("span", "aie-rev-figure", fmtMcap(latest.revenue, rec.currency)));
    top.appendChild(mk("span", "aie-rev-fy", "FY" + latest.fy));
    var yoy = (rec.growth || {}).yoy;
    if (yoy != null) {
      var cls = yoy > 0 ? "pos" : (yoy < 0 ? "neg" : "flat");
      // A near-flat year rounds to "-0%" at zero decimals, which reads as a
      // typo. Sub-1% moves keep a decimal; everything else stays clean.
      var pct = yoy * 100;
      var g = mk("span", "aie-rev-yoy " + cls,
                 fmtPct(pct, Math.abs(pct) < 1 ? 1 : 0) + " vs last year");
      var cagr = (rec.growth || {}).cagr3y;
      if (cagr != null) g.title = "3-year CAGR " + fmtPct(cagr * 100, 0);
      top.appendChild(g);
    }
    box.appendChild(top);

    /* Six bars beat six numbers: the shape of the ramp is the whole point,
       and a reader should not have to divide in their head to see it. */
    var max = years.reduce(function (m, y) { return Math.max(m, y.revenue || 0); }, 0);
    var bars = mk("div", "aie-rev-bars");
    years.forEach(function (y) {
      var col = mk("span", "aie-rev-col");
      var bar = mk("span", "aie-rev-bar");
      /* Pixels, not percent. A percentage height inside a flex column
         resolves against a parent the tick label is also competing for, and
         both 60% and 100% clamped to the same 25px — the same class of bug as
         the grid-template-rows drill-down noted above. Measuring in JS is what
         this codebase already does when CSS sizing is ambiguous. */
      var frac = max > 0 ? (y.revenue / max) : 0;
      bar.style.height = Math.max(2, Math.round(frac * REV_BAR_PX)) + "px";
      col.appendChild(bar);
      col.appendChild(mk("span", "aie-rev-tick", "\u2019" + String(y.fy).slice(2)));
      col.title = "FY" + y.fy + "  " + fmtMcap(y.revenue, rec.currency);
      bars.appendChild(col);
    });
    box.appendChild(bars);
    box.appendChild(makeExposureRow(sym));
    return box;
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
    // Inline SVG resolves CSS custom properties in fill/stroke, so the
    // fallback stays a token rather than a stale copy of the old palette.
    var c = color || "var(--muted)";
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
      '<rect x="9" y="9" width="22" height="22" rx="5" fill="var(--card)" stroke="' + c + '" stroke-width="2"/>' +
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
    viewsForTicker: viewsForTicker,
    viewDensity: viewDensity,
    viewStats: viewStats,
    makeViewsBlock: makeViewsBlock,
    fundamentalsFor: fundamentalsFor,
    makeRevenueBlock: makeRevenueBlock,
    exposureFor: exposureFor,
    aiRevenue: aiRevenue,
    chipSpark: chipSpark
  };
})(window);
