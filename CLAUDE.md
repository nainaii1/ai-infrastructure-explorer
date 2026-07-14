# CLAUDE.md — AI Infrastructure Explorer

## What this is
An interactive, offline-first web tool mapping the **AI hardware supply chain** —
how NVIDIA + the hyperscalers connect to the layers of suppliers beneath them
(photonics, memory, fabs, neoclouds, materials, networking, glass, accelerators,
robotics, hyperscalers), plus a sourced thesis feed, an AI-synthesized "brain"
digest of one analyst's (@aleabitoreddit) views, and a **Desk layer** — Claude's
weekly second opinion + execution suggestion on the highest-conviction names.

**Multi-page editorial site** (v7 "Private Coverage" upgrade — supersedes the
single-page v6): a warm serif front page (`index.html`, the coverage index) leads
into the **Field Guide** (`desk.html`) — one continuous chaptered scroll: a hero
prologue (signal chain + live counts + latest thesis) then four chapters — 01 The
Map, 02 The Watchlist, 03 The Evidence (thesis feed), 04 The Synthesis (Brain) —
navigated by a floating frosted-paper capsule nav with a sliding pill (scrollspy;
bottom-floating on mobile), under a shared top masthead. Later pages (`memo.html`,
`vault.html`, `performance.html`) are on the roadmap — see `docs/EXECUTION.md`.
The signal chain is: analyst tweets → captured theses → conviction tiers →
Claude's desk verdicts → operator decision.

This is **not** related to any trading desk or market-brief project. Standalone
personal research tool. Single-user, local-first. Not investment advice.

**Commercial intent:** the map is the hook; the real product is structured,
sourced thesis + watchlist data. Treat `data.js` like it's the actual product,
not throwaway config.

## Current status (read this first — it's the fastest way to know where things stand)
- **v1 — Supply Chain Map** ✅ done. Value-chain layer stack (not an SVG arc —
  see "Map rendering" below), grouped into Demand/Chip/Supply flow zones,
  click-to-filter, ticker cards.
- **v2 — Watchlist** ✅ done. Sortable table, weekly Yahoo price fetch via a
  local server (`ingest/serve.py`), ratings persist to localStorage.
- **v3 — Thesis tab + ingest pipeline** ✅ done. Telegram bot (`ingest/bot.py`)
  captures posts → `theses.json`, auto-grows `tickers.json`, computes a
  priority ranking (`scorer.py`).
- **v4 — Brain (AI theme digests)** ✅ done. `ingest/synthesize.py` reads
  theses grouped by category and produces one narrative digest per theme.
  **Requires a paid Anthropic API key** the operator doesn't currently have —
  when that's the case, refresh the brain **manually**: read
  `ingest/store/theses.json` grouped by category, author digests in the same
  shape the schema expects, and run them through `synthesize.synthesize_all()`
  with an injected `call_fn` (see `docs/GUIDE.md` §3) instead of hand-writing
  `brain.json`. This keeps output byte-identical to a real API run
  (`sourceThesisIds`, `thesesCount`, ticker-universe filtering, `meta` are all
  stamped by the pipeline, not by hand).
- **v5 — Conviction tiers + Desk verdicts** ✅ done (2026-07-03). Every ticker
  gets a tier from `scorer.assign_tiers()` — `core` (repeat *focus-weighted*
  mentions or 2+ high-conviction hits) / `watch` / `radar` (one-off
  name-drops). Mentions are focus-weighted by `1/√(tickers-in-post)` so a name
  buried in a 12-ticker digest dump can't inflate the tiers (ROADMAP issue #4,
  fixed 2026-07-03). The **Map** defaults to **Signal (Core+Watch)**; the
  **Watchlist** opens focused on **Core** only (it's the decision surface —
  keeps the table short); Watch/Radar/All/Signal are one chip away everywhere,
  Radar always hidden until asked for.
  On top sits the **Desk** layer: `ingest/store/verdicts.json` holds Claude's
  weekly second opinion per Core name (stance `act|accumulate|watch|pass`,
  view, execution suggestion, what-changes-my-mind, source thesis ids) —
  rendered as a "Desk" column on the Watchlist and a full verdict block on
  ticker cards. Refreshed weekly via the **`/weekly-review` project skill**
  (`.claude/skills/weekly-review/SKILL.md`) in a Claude Code session — no
  API key needed. Verdicts are capped at the top 12–15 Core names by design
  (token budget). Latest pass: 2026-07-06, 15 Core names covered.
- **v6 — "Field Guide" redesign** ✅ done (2026-07-03). Tabs dissolved into one
  chaptered scroll: hero prologue (signal-chain stat nodes with count-up,
  Core/Watch/Radar barbell bar, "Latest signal" card), numbered chapter heads,
  floating glass capsule nav (sliding pill, scrollspy, bottom-floating ≤768px),
  cool "cleanroom" palette (see Design system), scroll-triggered staggered
  reveals, one unified JS-measured max-height drill-down animation (map detail + brain
  sources), "Jargon, translated" glossary (`AIE_DATA.glossary`, sourced from
  `base.json`), "New this week" strip on the Watchlist, heat-aware cross-section
  legend, caveats colophon. All old tab classes (`.tab-panel`, `.tab-btn`,
  `initTabs`) are gone — chapters render eagerly at boot.
- **Evidence chapter cap** ✅ done (2026-07-03). The raw thesis feed shows only
  the most recent 10 posts by default (a backfill can make this feed
  100+ full-text cards — ~90,000px tall uncapped); the rest sit behind a
  "Show N earlier theses" drill-down, never deleted. Fixing this surfaced a
  real bug in the CSS `grid-template-rows: 0fr->1fr` drill-down technique:
  it silently resolves to 0 height whenever an ancestor (`.bd-card`'s
  `overflow: hidden`, `.th-feed`'s flex column) gives the grid track a
  bounded "available space" instead of true content-based auto-sizing. All
  three drill-downs (map layer detail, Brain sources, this new one) now use
  a JS-measured `max-height` (see `AIE.setDrilldownOpen()` in
  `shared/common.js`) — robust regardless of ancestor layout, with a resize
  listener to re-measure anything currently open.
- **v7 — "Private Coverage" editorial multi-page upgrade** 🚧 Phase 1 done
  (2026-07-08). The single-page app split into a multi-page vanilla site with a
  shared design system, all still `file://`-safe and framework-free. Shipped in
  Phase 1 (`docs/EXECUTION.md` P1–P5): (1) `shared/theme.css` — warm editorial
  "paper" design tokens + shared components (top masthead, ledger table, chips,
  tier/stance badges, colophon, gradient border); (2) `shared/common.js` — a
  global `AIE` namespace holding everything used by 2+ pages (localStorage
  seeding, `setDrilldownOpen`, `fmtNum/fmtMcap/fmtPct/fmtDate`, category-color
  helpers, `renderNav(activePage)`, `linkForTicker(sym)` stub); (3) the Field
  Guide moved `index.html` → `desk.html` and now loads the shared assets;
  (4) `desk.html` retokenized to the warm editorial theme (serif hero +
  chapter heads; frosted-paper capsule); (5) a new editorial `index.html`
  front page (masthead, serif standfirst sourced from `AIE_DATA` counts,
  latest-desk meta strip, chapter links, reserved coverage-ledger empty state).
  **Phase 2 — Coverage memos ✅ done (2026-07-12, P6–P10):** `memos.json`
  store + `data.js` passthrough; `memo.html` renderer (?id/?ticker routing,
  live snapshot strip, right-rail TOC with scrollspy, sources appendix via a
  shared `AIE.makeThesisCard`, `**bold**`/`$TICK`/`[[wikilink]]` body markup);
  coverage ledger on `index.html` (memo rows + "verdict only" stubs, kind/
  rating filters); authoring rules added to the weekly-review skill (step 4b)
  plus a new `/coverage-note TICKER` skill; first 5 memos seeded (SIVE, LITE,
  NVDA, AAOI, JBL — rating always mirrors the desk stance). `.claude/skills/`
  is now tracked in git (gitignore exception).
  **Phases 3–5 (knowledge Vault + graph, cross-linking, performance
  hooks) are the remaining roadmap — see `docs/EXECUTION.md`.**
  **Phase 6 — "Unpacked" rebrand 🚧 in progress (started 2026-07-13):** a
  Samsung-Unpacked aesthetic — cool neutral-grey canvas, bold geometric display
  type, ONE blue→violet brand-gradient accent used sparingly, true-black "event
  stage" dark surfaces. Shipped: **U1** (guide), **U2** (design tokens in
  `shared/theme.css` — palette/fonts/brand/stage; the duplicate `desk.html`
  `:root` deleted; `paintGradientBorder` now a no-op — the border is pure-CSS
  brand chrome), **U3** (4 category hues deepened for the cool canvas).
  Shipped: **U6** (12 validated, data-owned category icons in the pipeline
  bands and hub). Remaining: **U5** focus card, **U7** map tiles +
  expand-in-place, **U8** docs + `--serif`-alias cleanup —
  see `docs/EXECUTION.md` Phase 6. The Design system section below carries the
  shipped U2/U3 token values; its comprehensive rewrite (and `docs/DESIGN.md`'s)
  lands in U8.
- **Live counts** (approximate, check `ingest/store/*.json` for current):
  ~109 tickers tracked (23 core / 21 watch / 65 radar after focus-weighting),
  10 categorized layers + an `unsorted` triage bucket (one Core name, RDDT,
  is still unsorted — it doesn't cleanly fit any of the 10 categories;
  remaining unsorted are Watch/Radar tier), 170 ingested theses, 15 desk
  verdicts (reviewed 2026-07-06), 10 brain digests synthesized (8
  re-synthesized 2026-07-06 via Claude Code per the v4 workaround above;
  materials/glass carried forward — no new theses that pass).
- **Signal Digest** ⛔ superseded (2026-07-06) by the **Coverage memo** feature
  in the v7 upgrade (`docs/EXECUTION.md` Phase 2). The memo
  (`ingest/store/memos.json` → `memo.html`, authored via the weekly review /
  `/coverage-note` skill) is the successor: a longer per-Core-name research note
  rather than a one-line-per-ticker digest. The old design doc
  (`docs/superpowers/specs/2026-07-03-signal-digest-design.md`) is kept for
  history only — do not build it. Tweet discovery still stays fully manual
  (Telegram bots can't read other bots' messages).
- **For full history / open issues / next steps:** see `docs/ROADMAP.md`
  (living doc, update it whenever status changes).
- **For a full design-system reference** (color tokens, type scale, spacing,
  every component + its states, known inconsistencies) before doing any
  visual redesign work: see `docs/DESIGN.md`.

## Hard rules (do not break these)
1. **Vanilla HTML / CSS / JS only** in the app. No React, no Tailwind, no
   frameworks, no CDN libraries. Everything hand-written.
2. **Every page must work by double-click** (file:// protocol). ALL app data —
   tickers, theses, brain, desk verdicts, and the v7 additions (memos, vault) —
   rides inside `data.js` (loaded via `<script>`, exposes `window.AIE_DATA`),
   NOT `data.json` (fetch is blocked under file://). Do not introduce `fetch()`
   of local files in any page. Cross-page navigation is plain relative-href
   links (`desk.html#chapter-map`), never client-side routing.
3. **App code = the page files + exactly two shared files, nothing else.**
   Pages: `index.html` (coverage front page), `desk.html` (Field Guide), and
   the roadmap pages `memo.html` / `vault.html` / `performance.html` — each a
   self-contained HTML file with page-specific CSS in its `<style>` and
   page-specific logic in its `<script>`. Shared: `shared/theme.css` (design
   tokens + components) and `shared/common.js` (the `window.AIE` namespace).
   **Anything used by 2+ pages goes in `shared/`, never duplicated** (tokens,
   masthead, seeding, formatters, drill-down, category-color helpers all live
   there). No other `.js`/`.css` files, no framework, no build step. `data.js`
   stays the single generated datastore. (The Python `ingest/` backend is a
   separate concern and is expected to have many files — see below.)
4. **All colors, labels, tooltips, and tickers come from `data.js`.** Never
   hardcode them inside a page or `shared/`. E.g. a category color is read from
   `AIE_DATA.categories[id].color` (via `AIE.categoryColor()`), zone labels from
   `AIE_DATA.zones`, the map intro line from `AIE_DATA.mapIntro`. Per-chip and
   map-band accents are painted at runtime from category colors; the 3px top
   border is now brand chrome (`--brand-grad`, pure CSS) — not category-painted
   (Phase 6, U2).
5. All hover/click transitions **200–300ms ease**. Mobile breakpoint **768px**.
   Fully responsive.
6. **`data.js` is generated, never hand-edited.** Source of truth is
   `ingest/store/*.json`; regenerate with `python3 ingest/generate_data_js.py`
   (or any ingest script that calls `write_data_js()`) after editing the store.
7. **Ticker/category counts are NOT fixed** (unlike the original v1 spec) —
   the ingest pipeline grows both over time. Don't assume a specific count in
   code or docs; read it from the store.

## Design system (migrating — v7 "Unpacked" cool theme, Phase 6; supersedes the warm "editorial paper" theme, which superseded the v6 cleanroom / original cream themes). Values below are the shipped U2/U3 state; the full section + `docs/DESIGN.md` rewrite lands in U8.
Defined once in `shared/theme.css` (`:root` tokens + `.aie-*` components); every
page (including `desk.html`) consumes them directly — U2 deleted the duplicate
`desk.html` `:root`. Data-dense surfaces (watchlist table, map bands) stay
system-sans; the display voice (hero + chapter heads, standfirst, ledger titles)
is a bold geometric sans (`--display`).
- Background `#f4f5f7` (cool neutral grey) · Card `#ffffff` · Border `#e2e5ea`
- Text `#2a2e35` · Muted `#7c828c` · Ink (display) `#0b0d12`
- Brand accent: ONE blue→violet gradient `--brand-grad` (`#2b6bf3`→`#7a3bf0`;
  solid fallback `--brand-ink` `#3d55f2`), used sparingly — paints the 3px top
  border and (from U4) at most one gradient-text moment per page. True-black
  "event stage" dark surfaces: `--stage` `#0a0a0c` / `--stage-hi` `#16161a`
  (cross-section, NVIDIA hub, vault graph).
- Shadows: cool-tinted (`rgba(15,23,42,…)`) two-layer `--shadow-sm` /
  `--shadow-lg`. Radii: `--r-card: 20px` · `--r-tile: 14px` · `--r-chip: 999px`.
- Motion (unchanged, 200–300ms): `--ease: 240ms ease` + `--spring:
  cubic-bezier(.32,.72,.28,1.15)` (capsule pill, drill-downs, reveals).
  Reveals/count-up are entrance effects gated on `prefers-reduced-motion`.
- Fonts: bold geometric display stack `--display: "Avenir Next", "Futura",
  -apple-system, "SF Pro Display", …` (hero + chapter heads, standfirst; weight
  700 / -0.02em at use sites). `--serif` is a transitional alias of `--display`
  (pages still say `var(--serif)`; renamed in U4, alias deleted in U8). Apple
  system sans for body/data-dense surfaces; genuine system monospace `--mono`
  (e.g. SF Mono) for tickers, numbers, and small-caps labels (uppercase, 0.08em,
  ~11px) — no CDN fonts.
- Category colors live in `data.js` (`categories[].color`) — see
  `ingest/store/base.json` for the current 10 (deepened for the cool canvas in
  U3): Photonics `#3b82f6`, Memory `#8b5cf6`, Fabs `#e08a00`, Neoclouds
  `#16a34a`, Materials `#f97316`, Networking `#0d9488`, Glass `#0284c7`,
  Robotics `#e11d48`, Accelerators `#76b900`, Hyperscalers `#6366f1`.
- Tier/stance badges are cool-tinted (`--sem-*` tokens), same hue semantics:
  core/act green, accumulate sky, watch amber, radar/pass muted.
- **Top masthead** (`AIE.renderNav(activePage)`): serif wordmark · `PRIVATE
  COVERAGE · NOT ADVICE` small-caps · page links (Coverage / Desk / Vault /
  Graph / Performance-greyed) · double-hairline rule. On `desk.html` the
  masthead scrolls away and the capsule chapter nav pins near the top.
- **3px brand-gradient top border** (blue→violet `--brand-grad`), full width,
  pure CSS (`.gradient-border`). `AIE.paintGradientBorder()` is a
  kept-for-boot-order no-op since U2 — category colors no longer paint the chrome.
- ⚡ favicon via inline SVG data URI in `<head>` (no external request, `file://`-safe).
- The true-black `--stage` (`#0a0a0c`) cross-section "blueprint" + NVIDIA hub
  are intentional dark "event stage" surfaces kept against the cool canvas
  (Phase 6, U2 — was the `#0f1b2e` blueprint navy).

## Architecture — two data layers
**Static config** (categories, center node, countries, zones, mapIntro) → read
directly from `window.AIE_DATA`. Never written to localStorage.
**User data** (tickers, theses, settings) → seeded into localStorage on first
load, then read/written there so user edits persist.

**Script load order (every page):** `<script src="data.js"></script>` FIRST
(defines `window.AIE_DATA`), then `<script src="shared/common.js"></script>`
(defines `window.AIE`), then the page's own inline `<script>`. Each page boots
with `AIE.seed()` → `AIE.paintGradientBorder()` → `AIE.renderNav(activePage)`.

### Seeding logic (runs once on load, version-aware)
```
if localStorage "aie_tickers"  is missing  -> set to AIE_DATA.tickers
if localStorage "aie_theses"   is missing  -> set to []
if localStorage "aie_settings" is missing  -> set to { version:"1.0", lastUpdated:null }
```
When the ingest tooling bumps `AIE_DATA.meta.version`, the app re-seeds/merges
so newly-ingested tickers and theses surface. Categories / center / countries
/ zones / mapIntro always read live from `AIE_DATA` (never user-edited).

**localStorage keys:** `aie_tickers`, `aie_theses`, `aie_settings`.

## Data schema (window.AIE_DATA — see ingest/generate_data_js.py `build_data()` for the exact assembly)
```
{
  meta:       { version, schemaVersion, lastUpdated, source },
  countries:  { US|KR|TW|SE|FR|DE: { flag, label } },
  categories: { <id>: { id, label, subtitle, color, layer, tooltip,
                        flowRole: "demand"|"chip"|"supply", investorAngle } },
  center:     { title, subtitle, tooltip },           // the NVIDIA + Hyperscalers demand hub
  mapIntro:   "one-line 'how to read this map' copy",
  zones:      [ { id, label }, ... ],                 // ordered Demand -> Chip -> Supply groups
  tickers:    [ { ticker, company, category, market, exchange, whatTheyDo,
                  whyNVDA, marketCapTier, rating, sourceTweetUrl, addedDate,
                  tier: "core"|"watch"|"radar",   // stamped from scorer.assign_tiers()
                  // optional, merged from prices.json:
                  price, currency, chg7d, chg1m, marketCap, asOf,
                  // optional, merged from scorer.py:
                  priority: { score, mentions, convictionHits, lastMentioned },
                  // optional, stamped from verdicts.json (Core names only):
                  verdict: { ticker, stance, view, execution, changesMind,
                             basedOnThesisIds[], updatedAt } } ],
  theses:     [ { id, source, author, sourceUrl, postedAt, ingestedAt, text,
                  tickers[], conviction, tags[] } ],
  priorities: [ { ticker, score, mentions, convictionHits, lastMentioned } ],
  brain:      { meta: { generatedAt, model, thesesConsidered,
                        categoriesSynthesized, schemaVersion, failures? },
                digests: [ { category, narrative, conviction, keyPoints[],
                             tickers[], sourceThesisIds[], thesesCount,
                             lastSynthesized } ] },
  desk:       { meta: { reviewedAt, reviewer, thesesConsidered, coverage,
                        cadence, disclaimer },
                verdicts: [ { ticker, stance: "act"|"accumulate"|"watch"|"pass",
                              view, execution, changesMind,
                              basedOnThesisIds[], updatedAt } ] }
}
```
- `category` → a key in `AIE_DATA.categories` (currently: `photonics | memory |
  fabs | neoclouds | materials | networking | glass | robotics | accelerators
  | hyperscalers | unsorted`). `unsorted` is a triage bucket, not a real
  theme — excluded from Brain synthesis.
- `tier` → conviction tier from `scorer.assign_tiers()`. The UI treats
  `radar` as hidden-by-default (map card grid, watchlist "Signal" filter).
- `desk` → Claude's weekly per-ticker verdicts (`store/verdicts.json`,
  authored by the `/weekly-review` skill; the only store file authored
  directly rather than through a pipeline script).
- `market` → a key in `AIE_DATA.countries`; render the flag via
  `countries[market].flag`.
- `marketCapTier` → `Mega | Large | Mid | Small`.
- `flowRole` groups a category into the map's flow pipeline: `demand` (buys
  compute), `chip` (NVIDIA + who builds it), `supply` (feeds the chip).
  `unsorted` has no `flowRole` and renders in a separate triage footer.
- New tickers ingested from an unrecognized symbol land in `category:
  "unsorted"` with mostly-empty fields — triage with
  `python3 ingest/review.py classify <SYM> --category <id> --company "..." ...`
  (regenerates `data.js` automatically).

## Map rendering (current — Pipeline / Cross Section toggle, NOT an SVG arc or
## the original single vertical stack; both superseded)
The Supply Chain Map (chapter 01 in `desk.html`) has two HTML-div views, toggled
by a pill button (`mapState.view`, `"pipeline" | "cross"`) next to "Show All" — not SVG:
- **Pipeline** (default) — `renderPipeline()` in `desk.html` builds three
  flex columns (Supply → Chip → Demand, left to right) from
  `AIE_DATA.categories`, each a vertical stack of `.layer-band` cards (reusing
  `makeLayerBand()`) sorted by `layer` descending within the column. A dashed
  SVG arrow (`makeFlowArrow()`) sits between columns. The NVIDIA + Hyperscalers
  hub renders as a centered dark card below the row. `unsorted` categories
  (no `flowRole`) drop into a muted "Triage" footer below the hub (reusing
  `makeZoneDivider()` for the footer label).
- **Cross Section** — `renderCrossSection()` builds one flex row of bar divs
  (`.mc-bar`) on a dark blueprint background, bar height proportional to
  ticker count per category (`counts[id]/maxCount * 170px`).
- Click a band or bar → `setFilter(id)` toggles `.is-active` (on both
  `.layer-band[data-cat]` and `.mc-col[data-cat]`), filters the ticker cards
  below (`renderCards`), and (Pipeline only) expands a `.layer-detail` panel
  showing `investorAngle` ("What to watch").
- "Show All" clears the filter. Switching the view toggle calls `renderMap()`,
  which re-renders whichever view is active and keeps the intro line in sync.

## File structure
```
ai-supply-desk/
├── index.html                  THE FRONT PAGE — coverage index, offline-first
├── desk.html                   THE FIELD GUIDE — Map/Watchlist/Evidence/Synthesis
├── shared/
│   ├── theme.css               design tokens + shared components (masthead, ledger, chips, badges)
│   └── common.js               window.AIE — seeding, drill-down, formatters, nav, ticker links
├── data.js                     window.AIE_DATA — GENERATED, never hand-edit
├── CLAUDE.md                   this file — build spec + current status
├── README.md                   quick start + project map
├── .claude/skills/weekly-review/SKILL.md   the /weekly-review desk procedure
├── docs/
│   ├── EXECUTION.md             v7 "Private Coverage" upgrade — phased prompt guide (the to-do doc)
│   ├── GUIDE.md                 how to run everything + FAQ / troubleshooting (read first if stuck)
│   ├── PRD.md                   product requirements
│   ├── ROADMAP.md               what's built / open issues / next steps (living doc)
│   ├── DESIGN.md                design-system reference (tokens/components) for redesign work
│   ├── TELEGRAM_SETUP.md        pointer into GUIDE.md
│   └── images/
└── ingest/                     THE BACKEND — Python tooling that regenerates data.js
    ├── bot.py                   Telegram ingest (forward a post -> thesis)
    ├── synthesize.py            the "Brain" — Claude-synthesized theme digests (needs ANTHROPIC_API_KEY)
    ├── fetch_prices.py          weekly Yahoo price fetch
    ├── serve.py                 tiny local server (Yahoo fetch needs http://, not file://)
    ├── parser.py / scorer.py / fetcher.py / review.py / generate_data_js.py
    ├── store/*.json             source of truth (base, tickers, theses, brain, verdicts, pending_tickers, prices)
    ├── tests/                   unittest suite — python3 -m unittest discover -s ingest/tests
    ├── .env.example              copy to .env, fill in tokens/keys (gitignored)
    └── requirements.txt
```

## When starting a fresh session on this project
1. Read this file's **Current status** section above.
2. Skim `docs/ROADMAP.md` for open issues and next steps.
3. Check `git log --oneline -10` for what's landed since the roadmap was last touched.
4. If something in this file conflicts with the actual code (`index.html`,
   `desk.html`, `shared/*`, `ingest/store/base.json`), **trust the code** and fix
   this file — it drifts. For the v7 upgrade's remaining phases, `docs/EXECUTION.md`
   is the authoritative to-do doc.
