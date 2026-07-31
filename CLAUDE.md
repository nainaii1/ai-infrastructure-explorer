# CLAUDE.md — AI Infrastructure Explorer

## What this is
An interactive, offline-first web tool mapping the **AI hardware supply chain** —
how NVIDIA + the hyperscalers connect to the layers of suppliers beneath them
(photonics, memory, fabs, neoclouds, materials, networking, glass, accelerators,
robotics, hyperscalers), plus a sourced thesis feed, an AI-synthesized "brain"
digest of one analyst's (@aleabitoreddit) views, and a **Desk layer** — Claude's
weekly second opinion + execution suggestion on the highest-conviction names.

**Multi-page site** (v7 "Private Coverage" shipped 2026-07-15; brand unified
as **AI Infrastructure Explorer** 2026-07-18; **v8 "analysis tool, not
product" 2026-07-18**): the **Desk** (`desk.html`) is the front door — a
chaptered scroll that opens on **01 The Watchlist**, then **02 The Map**, then
**03 The Synthesis**, under a compact "desk strip" of live counts (no hero, no
art, no Focus card). Around it: `index.html` (**Coverage** — the memo ledger,
no Focus card), `memo.html` (memo reader), `vault.html` (knowledge vault,
List/Graph views in one nav entry), `performance.html` (Calls + Claims ledgers), `design.html` (design reference, unlinked from main nav). Top
nav: Desk · Coverage · Vault · Performance.
The signal chain is: analyst tweets → captured theses → conviction tiers →
Claude's desk verdicts → operator decision.
**v8 removed** the Evidence chapter (raw thesis feed) — theses still live in the
data and render only where cited: memo sources, vault "Cited theses", and
Synthesis drill-downs (all via `AIE.makeThesisCard`). It also removed the Focus
card everywhere and all hero art (`renderFocusCard`, `artCoverage/Desk/Vault/
Performance`, `tileShape` are gone from `shared/common.js`; `chipSpark` remains
for the memo accent). The week's headline now lives only in the weekly-review
report, not the app.
Vocabulary rule: desk stance `watch` DISPLAYS as "wait" and user rating
`watch` as "following" (`AIE.stanceLabel`/`AIE.ratingLabel` in
`shared/common.js`) — data values stay `watch`; never render them raw.

This is **not** related to any trading desk or market-brief project. Standalone
personal research tool. Single-user, local-first. Not investment advice.

**Commercial intent:** the map is the hook; the real product is structured,
sourced thesis + watchlist data. Treat `data.js` like it's the actual product,
not throwaway config.

## Current status (read this first — it's the fastest way to know where things stand)
- **v1 — Supply Chain Map** ✅ done. Value-chain layer stack (not an SVG arc —
  see "Map rendering" below), grouped into Demand/Chip/Supply flow zones,
  click-to-filter, ticker cards.
- **v2 — Watchlist** ✅ done. Sortable table (Price/7D/1M/1Y/MktCap), ratings
  persist to localStorage. Prices come from the operator's **Google Sheet**
  (GOOGLEFINANCE formulas; CSV export downloaded by `ingest/fetch_prices.py`
  — Yahoo/FMP retired 2026-07-16 after chronic 429s). Refresh: launchd agent
  twice daily, `refresh-prices.command`, or the button via `ingest/serve.py`.
  See `docs/GUIDE.md` §4.
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
  fixed 2026-07-03).
  Since 2026-07-26 the priority *score* is **direction-aware**: each mention is
  signed (`bull`/`neutral` +1, `bear` −1), a present-but-unreadable direction
  is inert (0, so a typo'd `"bearish"` can't become a bull vote), and
  research-sourced theses (`source: "research"`) contribute 0 to both the score
  and `weightedMentions` — outside research can correct a name downward but can
  never inflate its rank or buy it tier coverage. The **conviction multiplier
  is retired** (`CONVICTION_WEIGHT = 0.0`, reversible): keyword-matched rhetoric
  was multiplying scores up to 6×. **Tiers are unaffected** — `assign_tiers`
  reads `convictionHits` and `weightedMentions` directly, never the score.
  The **Map** defaults to **Signal (Core+Watch)**; the
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
- **Expert review seats** ✅ done (2026-07-27, spec Phase 2). Three reviewers —
  `semi-expert` (is the technical claim true?), `fundamental` (do the numbers
  work?), `pm` (is this a good bet at this price?) — research a shortlist of up
  to 12 names before each weekly review and write findings into `theses.json`
  as `source: "research"` theses. Two pure modules: `ingest/seats.py` (what a
  seat is, and what a finding must satisfy) and `ingest/pre_review.py` (one
  pass — select coverage, run the seats, merge the findings). Both take an
  injected `call_fn`, exactly like `synthesize.py`, so they run in a Claude
  Code session with no API key. **The verification rule:** a finding with no citable
  primary source is marked `unverified` and forced to `direction: "neutral"` —
  visible in the brief, and worth exactly 0.0 to any score. Research can correct
  a name downward but can never inflate its rank, buy it tier coverage, add
  conviction hits, or be counted as analyst attention (it is excluded from
  `analystMentions`, `attention` and `lastMentioned`). Findings are pinned to
  the ticker the seat was *asked* about, not the one the answer claims, so a
  forwarded post cannot talk a seat into filing against a different name.
  Shortlist order is stance-changed → 3+ new analyst theses → score, with the
  names the cap dropped always reported. Run via the **`/pre-review` skill**;
  `/weekly-review` stamps `previousStance` on every verdict so a stance
  *change* is detectable at all.
- **Claims ledger** ✅ done (2026-07-28, spec Phase 3), rendered as the
  **Claims** half of `performance.html`. `ingest/store/claims.json` records dated, testable
  predictions from the analyst, the desk and each seat, judged when their date
  arrives. Two pure modules' worth of rules live in `ingest/claims.py`:
  extraction (same injection firewall as the seats), judging, and scoring.
  **`unfalsifiable` is a first-class outcome** — a claim nothing could settle
  is recorded, not dropped, and `score_claims` returns the **unfalsifiable
  share from the same call as the hit rate** so no surface can show the
  flattering number without the honest one. `hitRate` is `None`, never `0.0`,
  when nothing has been judged. A judgement to `correct`/`wrong` requires a
  citable primary source (same rule as a seat finding); without one the claim
  stays `open`. Judging before `judgeBy`, or re-deciding a judged claim,
  raises. **A claim moves no score and no tier** — hit-rate weighting is
  Phase 4, gated on ≥20 judged claims per source, and a test asserts
  `scorer.py` neither imports `claims` nor reads `claims.json`. Run via
  **`/judge-claims`**; `/pre-review` extracts claims from its own findings.
  Seeded 2026-07-28 with 25 analyst claims from 64 focused posts —
  **13 of 25 unfalsifiable (52%)**, 0 judged.
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
- **v7 — "Private Coverage" editorial multi-page upgrade** ✅ ALL SIX PHASES
  DONE (2026-07-15; see README/ROADMAP for the shipped summary — the phase
  notes below are history, kept for context).
  Phase 1 done (2026-07-08). The single-page app split into a multi-page vanilla site with a
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
  hooks) ✅ done (2026-07-13/14).**
  **Phase 6 — "Unpacked" rebrand ✅ done (2026-07-15, U1–U8):** a
  Samsung-Unpacked aesthetic — cool neutral-grey canvas, bold geometric display
  type, ONE blue→violet brand-gradient accent used sparingly, true-black "event
  stage" dark surfaces. **U1** (guide), **U2** (design tokens in
  `shared/theme.css` — palette/fonts/brand/stage; the duplicate `desk.html`
  `:root` deleted; `paintGradientBorder` now a no-op — the border is pure-CSS
  brand chrome), **U3** (4 category hues deepened for the cool canvas),
  **U4** (per-page polish — all page `var(--serif)` → `var(--display)`, pill-ified
  toggles, one gradient-text moment per front-of-house page, dark surfaces on
  `--stage`), **U6** (12 validated, data-owned category icons in the pipeline
  bands and hub), **U5** (2026-07-14 — a desk-authored weekly Focus card:
  `verdicts.json` `meta.focus` = `{headline, dek, updatedAt, tickers[]}`,
  rendered by the shared `AIE.renderFocusCard()` / `.aie-focus` component as
  the full-width lead on `index.html` and the hero's lead card on
  `desk.html`, demoting the raw latest-tweet card to a compact secondary
  slot linking into Chapter 03; absent `meta.focus` → both surfaces render
  exactly as before), **U7** (2026-07-14 — Chapter 01 restructure: `makeCard()`
  split into a compact `makeTile()` grid + an expand-in-place `makeCardDetail()`
  detail row animated by `AIE.setDrilldownOpen`; priority chips folded into the
  Holdings ledger row, glossary behind a drill-down, flow-arrow dashes animated
  via the `aie-flow` keyframes), and **U8** (2026-07-15 — this docs pass: the
  `--serif` alias deleted from `shared/theme.css` and every use switched to
  `var(--display)`; the Design system section + `docs/DESIGN.md` brought current;
  Phase 6 boxes ticked in `docs/EXECUTION.md`).
- **Live counts** (measured 2026-07-27; check `ingest/store/*.json` for current):
  120 tickers tracked (28 core / 17 watch / 75 radar after focus-weighting),
  10 categorized layers + an `unsorted` triage bucket holding 55 names — one
  Core (RDDT, which doesn't cleanly fit any of the 10 categories), 7 Watch, and
  a 47-name Radar tail of one-off name-drops not worth triaging by hand.
  258 ingested theses, all still analyst-sourced — no research theses written
  yet, so every `researchMentions` is 0 and the seats have not been run.
  17 desk verdicts (reviewed 2026-07-22, 9 accumulate / 8 watch; roster is
  "top 15 by score + sticky act/accumulate holdovers"), 10 brain digests
  (generated 2026-07-22 — 9 re-synthesized that day via Claude Code per the v4
  workaround above, `robotics` carried forward from 2026-07-16).
- **Symbol canonicalization** (2026-07-16): `base.json` carries
  `tickerAliases` (e.g. `SIVEF → SIVE`, mentions merge) and `themeTags`
  (e.g. `DRAM`, `SPCX` — theme markers, never ticker records).
  `scorer.canonicalize_theses()` applies both before any
  priority/tier computation, and `bot.py` skips auto-creating ticker stubs
  for them.
- **X watcher (auto-discovery)** ✅ done (2026-07-30). `ingest/watcher.py` +
  `docs/WATCHER.md`. **Tweet discovery is no longer manual.** A headless
  Playwright browser loads the PUBLIC (logged-out) `x.com/aleabitoreddit`
  profile every 4h via `com.aie.watch-x.plist`, collects permalinks, and
  queues them into `store/pending_posts.json`. Delivery is batched to the
  `DELIVERY_HOURS` ({0, 12} local) so the operator gets two Telegram batches a
  day, each post carrying ✅ Ingest / ❌ Skip inline buttons; `bot.handle_callback`
  acts on the tap. **Nothing auto-ingests** — a post reaches `theses.json` only
  on a tap. Three invariants, all load-bearing:
  (1) **The browser supplies URLs only.** Post text always comes from
  `fetcher.py`/fxtwitter, and `verify_post()` drops anything it can't confirm
  (fail closed) — so no scraped DOM text and no model output can ever enter
  the store. It also re-checks authorship against X and drops mismatches.
  (2) **Foreign permalinks need a positive repost marker.** X renders
  strangers' replies on his profile as thread context (observed live:
  `/stockprodigyman/status/…` asking *him* a question); admitting those would
  file another person's words as his thesis. Quote-posts are his own permalink
  and are unaffected. Genuine reposts pass through with `author` set to the
  ORIGINAL author — hence the new `author` kwarg on `ingest_message`.
  (3) **The logged-out page is hard-capped at 6 posts** (measured; scrolling
  cannot pass the "Sign up / Log in" wall). That cap, not preference, sets the
  4-hourly poll: at ~11 posts/day a 12-hourly poll would sit at the ceiling and
  lose posts silently. Hitting the cap raises an explicit overflow warning, and
  24h with no posts found raises a staleness alarm — a broken watcher must
  never look like a quiet week.
  Playwright is the project's only heavy dependency and is needed ONLY by
  `watcher.py`; the plist must call the python.org interpreter by absolute path
  (Apple's `/usr/bin/python3` does not have it and launchd ignores shell PATH).
- **Signal Digest** ⛔ superseded (2026-07-06) by the **Coverage memo** feature
  in the v7 upgrade (`docs/EXECUTION.md` Phase 2). The memo
  (`ingest/store/memos.json` → `memo.html`, authored via the weekly review /
  `/coverage-note` skill) is the successor: a longer per-Core-name research note
  rather than a one-line-per-ticker digest. The old design doc
  (`docs/superpowers/specs/2026-07-03-signal-digest-design.md`) is kept for
  history only — do not build it. Tweet discovery still stays fully manual
  (Telegram bots can't read other bots' messages).
- **Expert review team programme** (spec Phase 1 shipped, Phase 2 in
  progress): the live to-do doc with per-session prompts and the list of
  hard-won invariants is `docs/EXECUTION-EXPERT-REVIEW.md`. Read its
  "Invariants" section before touching `ingest/scorer.py` or
  `ingest/seats.py` or `ingest/pre_review.py`.
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

## Design system (current — v9 "soft two-tone", shipped 2026-07-31; supersedes v7 "Unpacked"). `docs/DESIGN.md` is the full reference and is current as of this version.
Defined once in `shared/theme.css` (`:root` tokens + `.aie-*` components); every
page consumes them directly. The language is phantom.com / aave.com — soft
lavender canvas, big near-black display type, generous air, large soft radii —
applied to a dense research tool: reading surfaces get the air and the big
numbers, working surfaces (11-column watchlist, map, graph) keep their density.
- Canvas: viewport-anchored lavender gradient `#fbfaff → #eeeafc` over
  `--bg #faf9fe` · Card `#ffffff` · Border `#e6e2f2` / `--border-strong #d5cfe8`
- Text: Ink `#1b1436` (16.7:1) · Text `#3b3557` (10.9:1) · Muted `#6a6484` (5.3:1)
- Brand is a LAVENDER RAMP, not one purple: `--violet #6a4ee8` (5.43:1, text-safe
  — links, active fills, every CTA) · `--violet-soft #8775ec` (3.05:1,
  DECORATIVE only — icons, fills, large display type) · `--violet-wash #f0ecfe`.
  Secondary `--teal #0f776f` (text-safe) / `--teal-ui #15a59a` (fills only).
- **Accessibility contract (load-bearing, see `docs/DESIGN.md` §2):** text pairs
  clear 4.5:1, UI/fill pairs 3:1. **No gradient text and no white-on-gradient** —
  `--brand-grad` runs 6.5:1 → 3.05:1, so it paints text-free chrome ONLY (the 3px
  top border, two 2px hub hairlines). A category hue never carries white text;
  active category chips tint 20% into `--card` and keep `--ink`.
  `--fs-2xs` (11px) is the type floor. One `:focus-visible` ring site-wide.
  **All of this is enforced by `ingest/tests/test_contrast.py`** — a token change
  that breaks AA fails the test run.
- Scales (new in v9 — the app previously had 30 ad-hoc sizes and no spacing
  tokens): `--fs-3xl 44 / 2xl 34 / xl 26 / lg 20 / md 17 / sm 15 / xs 13 /
  2xs 11` + `--fs-stat clamp(38px,6vw,64px)`; `--s-1 4 … --s-8 72` (section
  rhythm `--s-8`).
- Shape/motion: `--r-card 28px` · `--r-tile 18px` · `--r-chip 999px`;
  violet-tinted two-layer shadows; motion unchanged (`--dur 240ms`, `--spring`),
  all entrance motion gated on `prefers-reduced-motion`.
- Fonts: `--display` (Avenir Next / Futura / SF Pro Display) for headings AND
  body, `--sans` for data-dense surfaces, `--mono` (SF Mono) for tickers,
  numbers and small-caps labels. **No CDN fonts** — `file://` must work.
- Signature component: **`.aie-stat` big-number block** (huge figure, quiet mono
  label), used on the desk hero, the Notes front page and Performance.
- Category colors stay data-owned in `base.json` (all ten clear 3:1; fabs,
  materials and accelerators were darkened in v9 to `#c97c00` / `#ec6406` /
  `#649d00`). Tier/stance badges use the `--sem-*` pairs, all ≥5.3:1.
- Dark "stage" surfaces (map hub, cross-section, vault graph) have their own
  measured text tokens: `--on-stage` 15.8:1, `--on-stage-dim` 8.0:1,
  `--pos-stage` / `--neg-stage` / `--flat-stage`.
- **Nav labels are Today · Notes · Vault · Record.** "Coverage" was retired in
  v9; the internal page ids are unchanged (`index.html` is still `coverage`).
  Voice is short, plain, first person — no jargon in any heading, button, column
  header or empty state. Analytical prose is untouched.

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
                  priority: { score, net, attention, mentions, analystMentions,
                              researchMentions, bullMentions,
                              bearMentions, convictionHits, lastMentioned },
                  // optional, stamped from verdicts.json (Core names only):
                  verdict: { ticker, stance, previousStance, view, execution,
                             changesMind, basedOnThesisIds[], updatedAt } } ],
  theses:     [ { id, source, author, sourceUrl, postedAt, ingestedAt, text,
                  tickers[], conviction, tags[],
                  // optional, since 2026-07-26 — read by scorer.py:
                  direction,        // "bull" | "bear" | "neutral", LOWERCASE
                  verification } ], // "verified" | "unverified" (research only)
  priorities: [ { ticker, score, net, attention, mentions, analystMentions,
                  bullMentions, bearMentions, researchMentions,
                  weightedMentions, convictionHits, lastMentioned } ],
  brain:      { meta: { generatedAt, model, thesesConsidered,
                        categoriesSynthesized, schemaVersion, failures? },
                digests: [ { category, narrative, conviction, keyPoints[],
                             tickers[], sourceThesisIds[], thesesCount,
                             lastSynthesized } ] },
  claims:     { meta: { schemaVersion, updatedAt, disclaimer },
                claims: [ { id, source: "analyst"|"desk"|<seat>, ticker|null,
                            claim, testableBy, madeAt, judgeBy|null, thesisId,
                            status: "open"|"correct"|"wrong"|"unfalsifiable",
                            judgedAt, evidence } ] },
  desk:       { meta: { reviewedAt, reviewer, thesesConsidered, coverage,
                        cadence, disclaimer },
                verdicts: [ { ticker, stance: "act"|"accumulate"|"watch"|"pass",
                              view, execution, changesMind,
                              basedOnThesisIds[], updatedAt } ] }
}
```
- `direction` → **exactly** `bull`, `bear` or `neutral`, lowercase. Omit the key
  entirely for an undirected post — absent reads as `neutral` and carries full
  weight, which is how all pre-2026-07-26 theses score. **Anything else scores
  0.0 and is silently ignored**, so a typo like `"bearish"` or `"BEAR"` throws
  the bear case away rather than counting it backwards. Nothing validates this
  at write time yet — get it right when authoring. A thesis written with
  `source: "research"` contributes 0 to the score and to `weightedMentions`
  regardless of direction unless it is `bear`: outside research can only
  correct a name downward, never inflate its rank or buy it tier coverage.
- `verification` → `verified` | `unverified`, on research theses only. A
  finding the seat could not tie to a citable primary source is stamped
  `unverified` and forced to `direction: "neutral"`, so it is visible in the
  brief but worth exactly 0.0 to any number.
- `analystMentions` → `mentions` minus `researchMentions`, derived once in
  `scorer.compute_priorities`. **Anything the UI labels "@aleabitoreddit" must
  read this, never `mentions`** — the raw total counts the desk's own research
  findings, so using it credits our work to him. `attention` and
  `lastMentioned` exclude research for the same reason (and because `attention`
  is an aggregate, which research may subtract from but never add to).
- `previousStance` → the stance a verdict carried before the current weekly
  pass overwrote it, written by `/weekly-review`. It is the only record that a
  stance *changed*: `updatedAt` cannot tell you, because the weekly pass
  rewrites it on every Core name whether or not the call moved. `/pre-review`
  picks stance-changed names first, and a verdict missing this field simply
  does not qualify (fail inert) rather than matching everything.
- `claims[].status` → `unfalsifiable` is an OUTCOME, not a parse failure. A
  claim with no `judgeBy`, no `testableBy`, or a `judgeBy` on or before
  `madeAt` is recorded as unfalsifiable rather than dropped: a source whose
  predictions cannot be tested is telling the operator something, and the
  share of them is reported next to the hit rate for exactly that reason.
  `ticker` may be `null` for a macro claim. Ids are a content hash, so
  re-extraction is idempotent. Nothing in `scorer.py` may read this block
  until Phase 4.
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
  `.layer-band[data-cat]` and `.mc-col[data-cat]`), filters the ticker tiles
  below (`renderCards`), and (Pipeline only) expands a `.layer-detail` panel
  showing `investorAngle` ("What to watch").
- "Show All" clears the filter. Switching the view toggle calls `renderMap()`,
  which re-renders whichever view is active and keeps the intro line in sync.
- **Ticker tiles + expand-in-place** (Section B, Phase 6, U7). The tickers below
  the map render as a compact `.tk-tile` grid (`repeat(auto-fill, minmax(168px,
  1fr))` on `--r-tile`): category icon, mono ticker, one-line company, tier +
  stance micro-badges, sparkline — built by `makeTile()`. Clicking a tile (or
  Enter/Space; `aria-expanded` tracks state) inserts a full-width
  `grid-column: 1 / -1` `.tk-detail-row` right after the clicked tile's visual
  row, holding the full dossier card (`makeCardDetail()` — the old `makeCard()`
  badges/prose/verdict markup). One open at a time; Esc or a re-click closes;
  the row reseats + re-measures on resize. Animated by `AIE.setDrilldownOpen`
  (JS-measured `max-height`, NOT the `grid-template-rows: 0fr→1fr` trick — that
  silently resolves to 0 inside overflow-constrained/flex ancestors; see the
  `.layer-detail` comment). The priority mention-chips ride the Holdings ledger
  row as a horizontal scroller and the "Jargon, translated" glossary sits behind
  a drill-down, both to keep Chapter 01 short. `makeFlowArrow()` dashes scroll
  via the shared `aie-flow` keyframes (reduced-motion gated).

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
│   ├── WATCHER.md               the X watcher — how it works, daily use, when it breaks
│   ├── PRD.md                   product requirements
│   ├── ROADMAP.md               what's built / open issues / next steps (living doc)
│   ├── DESIGN.md                design-system reference (tokens/components) for redesign work
│   ├── TELEGRAM_SETUP.md        pointer into GUIDE.md
│   └── images/
└── ingest/                     THE BACKEND — Python tooling that regenerates data.js
    ├── bot.py                   Telegram ingest (forward a post -> thesis) + approve buttons
    ├── watcher.py                X timeline watcher — discovers posts, queues them for approval
    ├── synthesize.py            the "Brain" — Claude-synthesized theme digests (needs ANTHROPIC_API_KEY)
    ├── seats.py                  the three expert seats: prompts + finding validation (pure)
    ├── pre_review.py             one review pass: select coverage, run the seats, merge findings (pure)
    ├── fetch_prices.py          price fetch from the operator's Google Sheet (GOOGLEFINANCE)
    ├── serve.py                 tiny local server (the Fetch-prices button needs http://, not file://)
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
