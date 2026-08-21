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

## Current status (read this first — full phase-by-phase history lives in docs/ROADMAP.md, not here)
Everything below is shipped and live:
- **Map + Watchlist** — flow-pipeline map (click-to-filter), sortable watchlist
  (Price/7D/1M/1Y/MktCap). Prices from the operator's **Google Sheet**
  (GOOGLEFINANCE; CSV pulled by `ingest/fetch_prices.py` — Yahoo/FMP retired
  2026-07-16, chronic 429s). Refresh: launchd twice daily, `refresh-prices.command`,
  or the button via `ingest/serve.py`. See `docs/GUIDE.md` §4.
- **Ingest pipeline** — Telegram bot (`ingest/bot.py`) captures posts →
  `theses.json`, auto-grows tickers, `scorer.py` computes priority + tiers.
- **Brain (theme digests)** — `ingest/synthesize.py`. No paid API key yet —
  refresh manually through Claude Code per `docs/GUIDE.md` §3 (output stays
  byte-identical to a real API run).
- **Conviction tiers + Desk verdicts** — `scorer.assign_tiers()` gives every
  ticker Core/Watch/Radar. Scoring is **direction-aware** (bull/bear/neutral;
  unreadable direction is inert; research theses score 0 unless bearish — see
  Data schema below for the exact rule). Map defaults to Signal (Core+Watch);
  Watchlist opens on Core only. Claude's weekly per-ticker verdict lives in
  `ingest/store/verdicts.json`, refreshed via **`/weekly-review`**, capped at
  the top 12–15 Core names.
- **Expert review seats** — `semi-expert`/`fundamental`/`pm` research a
  shortlist before each weekly review (`ingest/seats.py` + `ingest/pre_review.py`,
  run via **`/pre-review`**), writing `source: "research"` findings. Unverified
  findings are forced `neutral` — visible but worth 0 to any score, and can
  never inflate rank, tier, or analyst-attention counts.
- **Claims ledger** — `ingest/claims.py` + `claims.json` record dated, testable
  predictions, judged via **`/judge-claims`**. `unfalsifiable` is a first-class
  outcome reported alongside the hit rate, never hidden. No score/tier impact
  until Phase 4 (gated on ≥20 judged claims/source).
- **v7 "Private Coverage" multi-page** — `index.html`/`desk.html`/`memo.html`/
  `vault.html`/`performance.html` + shared `theme.css`/`common.js`. Coverage
  memos, knowledge vault + graph, site-wide cross-linking, performance ledgers.
- **v8 "analysis tool, not product"** — Focus card and all hero art removed;
  Desk opens on the Watchlist; Evidence chapter removed (theses render only
  where cited — memo sources, vault, Synthesis drill-downs).
- **v9 "soft two-tone" design** — current visual language; see Design system
  section below and `docs/DESIGN.md` for the full reference.
- **X watcher (auto-discovery)** — `ingest/watcher.py` polls the public
  logged-out X profile every 4h, queues candidate posts to Telegram for a
  ✅/❌ tap — **nothing auto-ingests without approval**. Details, invariants,
  and failure modes: `docs/WATCHER.md`.
- **Symbol canonicalization** — `base.json` `tickerAliases`/`themeTags`,
  applied by `scorer.canonicalize_theses()` before any priority/tier math.
- **Per-ticker view extraction** — `ingest/views.py` + `ingest/extract_views.py`
  read what the analyst actually argued about each ticker in each post, not
  just how often he named it. Every `source: "x"` thesis touching a Core/Watch
  name has been read (312 of 356 posts as of 2026-08-19) and now carries a
  `views[]` array: `{ticker, direction, why, numbers?, horizon?}` per name in
  that post, since one post routinely holds different stances on different
  tickers (see `PROJECT.md` for why this exists — mention-count has ρ=0.17
  correlation with returns, i.e. none). **Additive only** — `scorer.py` is
  untouched, no score/tier moved. Manual two-step workflow documented in
  `docs/GUIDE.md` §10. Full status, numbers, and the next steps (SEC EDGAR
  fundamentals, `aiExposure` fields, re-pointing the chart mockups at real
  variables instead of mention-count) live in **`PROJECT.md`** — read that
  first for anything touching this work.
- **"What he's argued" block (2026-08-20)** — those `views[]` now render on the
  ticker dossier card in `desk.html`, above Claude's verdict: his case first,
  then the desk's call on it. `AIE.viewsForTicker` / `AIE.viewStats` /
  `AIE.makeViewsBlock` in `shared/common.js`, styled by `.aie-views*` in
  `shared/theme.css` (§7c) — shared, not page-local, because a renderer in
  `shared/` may not depend on one page's CSS (rule #3). The header shows
  **signal density** (`103 / 112 argued`), which is the point: NVDA reads
  `11 / 71`. A name he has never named renders no block at all. Read-only over
  `data.js` — no ingest, score or tier change.
  It also renders in the **watchlist row detail** (under "My call", capped at 3),
  and signal density is a **`His case` column in the watchlist table** — sortable,
  backed by `AIE.viewDensity(sym)` (one memoised pass over all theses; never call
  `viewsForTicker` per row). It sorts on the argument COUNT, not the ratio, and a
  name he has never mentioned renders `—` and sorts last. This is the only column
  in the app that ranks on something other than posting frequency.
  **Direction shows as an exception flag, not a split**: 28 of 34 Core names are
  100% bull when argued, so only the 5 carrying any bear view render a red
  `N bear` chip (IREN, TSM, TSLA, MTSI, AVGO). The word, never an arrow — the
  sort indicators are already `▲`/`▼`. `makeViewsBlock` guarantees the capped
  row list includes his most recent bear view when one exists, so the column's
  flag can never be contradicted by the panel it opens.

- **SEC fundamentals (2026-08-21, PROJECT.md Step 2)** — `ingest/fundamentals.py`
  (pure parser) + `ingest/fetch_fundamentals.py` (the runner) pull annual revenue
  from **SEC EDGAR XBRL** (`data.sec.gov/api/xbrl/companyfacts`) into
  `store/fundamentals.json`, which rides in `data.js` as a new top-level block.
  Free, no API key, no daily limit. 37 of 46 Core+Watch names covered; the gaps
  are recorded with reasons, never silent. Rendered by `AIE.makeRevenueBlock` /
  `.aie-rev*` (theme.css §7d) on the **ticker card and the watchlist row**,
  between his case and the desk verdict — evidence, numbers, call.
  **Three SEC traps the parser exists to handle**, all verified live: there is
  no single revenue tag (NVDA migrated to `Revenues`; the old tag is still in
  the payload and stops at FY2022, so `pick_series` ranks by RECENCY, not a
  fixed priority order); a row's `fy` is the FILING's year, not the period's,
  so periods come from `start`/`end` only; and a filer can report the same
  concept in two currencies (TSM files TWD **and** USD — USD wins).
  **A ticker symbol is not identity**: EDGAR's `CCXI` is Churchill Capital
  Corp XI, this desk's is Agility Robotics, so `fundamentals.names_match()`
  gates every write against the company name already on file (and accepts a
  filing renamed to its ticker, e.g. Iris Energy -> "IREN Limited").
  Bar heights are computed in **px in JS**, never a CSS `%` — a percentage
  height inside the flex column collapsed 60% and 100% to the same 25px, the
  same class of bug as the `grid-template-rows` drill-down note above.

**Ticker/thesis/verdict counts change constantly — read `ingest/store/*.json`
or `data.js`, never assume a number from this file.**

Read `docs/EXECUTION-EXPERT-REVIEW.md` "Invariants" before touching
`ingest/scorer.py`, `ingest/seats.py`, or `ingest/pre_review.py`.
For open issues, next steps, and shipped-phase history: **`docs/ROADMAP.md`**.

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
numbers, working surfaces (the watchlist, map, graph) keep their density.
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
  `#649d00`). Tier/stance badges use the `--sem-*` pairs, all ≥5.3:1 — plus
  `--sem-bear-*` (5.74:1), used only by the analyst-views block, since no tier,
  stance or rating is ever "bear".
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
  | hyperscalers | power | unsorted`). `unsorted` is a triage bucket, not a real
  theme — excluded from Brain synthesis.
  **`power` (Power & Cooling, layer 11, flowRole `supply`) was added 2026-08-12**
  — grid interconnection, transformers/switchgear, on-site generation and
  liquid cooling. It is the first category built from the desk's own research
  rather than grown from the analyst's feed, so most of its names carry zero
  analyst mentions and therefore sit at `radar` no matter how load-bearing they
  are (see the tiering caveat under `tier` below).
- `tier` → conviction tier from `scorer.assign_tiers()`. The UI treats
  `radar` as hidden-by-default (map card grid, watchlist "Signal" filter).
  **Tiering is mention-driven, which cuts both ways.** A name the analyst never
  mentions can never rise above `radar` however important it is (GEV, CEG), and
  a name he name-drops inside multi-ticker recap posts can rank top-15 on no
  conviction at all (TSLA, recorded `pass` 2026-08-12 for exactly this reason).
  The score measures his posting behaviour, not the desk's judgement — do not
  read tier as importance.
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
