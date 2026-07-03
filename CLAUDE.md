# CLAUDE.md — AI Infrastructure Explorer

## What this is
An interactive, offline-first web tool mapping the **AI hardware supply chain** —
how NVIDIA + the hyperscalers connect to the layers of suppliers beneath them
(photonics, memory, fabs, neoclouds, materials, networking, glass, accelerators,
robotics, hyperscalers), plus a sourced thesis feed, an AI-synthesized "brain"
digest of one analyst's (@aleabitoreddit) views, and a **Desk layer** — Claude's
weekly second opinion + execution suggestion on the highest-conviction names.
**One continuous "Field Guide" page** (v6 redesign): a hero prologue (signal
chain + live counts + latest thesis) then four chapters — 01 The Map, 02 The
Watchlist, 03 The Evidence (thesis feed), 04 The Synthesis (Brain) — navigated
by a floating frosted-glass capsule nav with a sliding pill (scrollspy;
bottom-floating on mobile). The signal chain is: analyst tweets → captured
theses → conviction tiers → Claude's desk verdicts → operator decision.

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
  gets a tier from `scorer.assign_tiers()` — `core` (repeat mentions or 2+
  high-conviction hits) / `watch` / `radar` (one-off name-drops). The app
  defaults to **Signal (Core+Watch)** everywhere; Radar hides behind a toggle.
  On top sits the **Desk** layer: `ingest/store/verdicts.json` holds Claude's
  weekly second opinion per Core name (stance `act|accumulate|watch|pass`,
  view, execution suggestion, what-changes-my-mind, source thesis ids) —
  rendered as a "Desk" column on the Watchlist and a full verdict block on
  ticker cards. Refreshed weekly via the **`/weekly-review` project skill**
  (`.claude/skills/weekly-review/SKILL.md`) in a Claude Code session — no
  API key needed. Verdicts are capped at the top 12–15 Core names by design
  (token budget).
- **v6 — "Field Guide" redesign** ✅ done (2026-07-03). Tabs dissolved into one
  chaptered scroll: hero prologue (signal-chain stat nodes with count-up,
  Core/Watch/Radar barbell bar, "Latest signal" card), numbered chapter heads,
  floating glass capsule nav (sliding pill, scrollspy, bottom-floating ≤768px),
  cool "cleanroom" palette (see Design system), scroll-triggered staggered
  reveals, one unified grid-rows drill-down animation (map detail + brain
  sources), "Jargon, translated" glossary (`AIE_DATA.glossary`, sourced from
  `base.json`), "New this week" strip on the Watchlist, heat-aware cross-section
  legend, caveats colophon. All old tab classes (`.tab-panel`, `.tab-btn`,
  `initTabs`) are gone — chapters render eagerly at boot.
- **Live counts** (approximate, check `ingest/store/*.json` for current):
  ~83 tickers tracked (20 core / 26 watch / 37 radar), 10 categorized layers
  + an `unsorted` triage bucket (all Core names are classified; remaining
  unsorted are Watch/Radar tier), ~72 ingested theses, 13 desk verdicts,
  brain digests synthesized for every category that has theses.
- **For full history / open issues / next steps:** see `docs/ROADMAP.md`
  (living doc, update it whenever status changes).
- **For a full design-system reference** (color tokens, type scale, spacing,
  every component + its states, known inconsistencies) before doing any
  visual redesign work: see `docs/DESIGN.md`.

## Hard rules (do not break these)
1. **Vanilla HTML / CSS / JS only** in the app. No React, no Tailwind, no
   frameworks, no CDN libraries. Everything hand-written.
2. **Must work by double-clicking `index.html`** (file:// protocol). Data
   lives in `data.js` (loaded via `<script>`), NOT `data.json` (fetch is
   blocked under file://). Do not introduce `fetch()` of local files in the app.
3. **App code lives in exactly two files:** `index.html` (CSS inside
   `<style>`, logic inside `<script>`) and `data.js` (data + config). Do not
   split the *app* into more files. (The Python `ingest/` backend is a
   separate concern and is expected to have many files — see below.)
4. **All colors, labels, tooltips, and tickers come from `data.js`.** Never
   hardcode them inside `index.html`. E.g. a category color is read from
   `AIE_DATA.categories[id].color`, zone labels from `AIE_DATA.zones`, the map
   intro line from `AIE_DATA.mapIntro`.
5. All hover/click transitions **200–300ms ease**. Mobile breakpoint **768px**.
   Fully responsive.
6. **`data.js` is generated, never hand-edited.** Source of truth is
   `ingest/store/*.json`; regenerate with `python3 ingest/generate_data_js.py`
   (or any ingest script that calls `write_data_js()`) after editing the store.
7. **Ticker/category counts are NOT fixed** (unlike the original v1 spec) —
   the ingest pipeline grows both over time. Don't assume a specific count in
   code or docs; read it from the store.

## Design system (current — v6 "cleanroom" light theme; supersedes the cream theme)
- Background `#f5f5f7` (cool near-white) · Card `#ffffff` · Border `#e3e3e8`
- Primary text `#333336` · Muted text `#86868b` · Ink (high-contrast) `#1d1d1f`
- Shadows: two-layer tokens `--shadow-sm` / `--shadow-lg`. Card radius `--r-card: 16px`.
- Motion: `--ease: 240ms ease` + `--spring: cubic-bezier(.32,.72,.28,1.15)`
  (capsule pill, drill-downs, reveals). Reveals/count-up are entrance effects
  gated on `prefers-reduced-motion`.
- Font: Apple system stack (`-apple-system` → SF Pro on Macs); data/tickers use
  a genuine system monospace stack (`--mono`, e.g. SF Mono) — no CDN fonts.
- Category colors live in `data.js` (`categories[].color`) — see
  `ingest/store/base.json` for the current 10: Photonics `#3b82f6`, Memory
  `#8b5cf6`, Fabs `#f59e0b`, Neoclouds `#22c55e`, Materials `#f97316`,
  Networking `#14b8a6`, Glass `#0ea5e9`, Robotics `#e11d48`, Accelerators
  `#76b900`, Hyperscalers `#6366f1`.
- Tier badges: core `#dcfce7/#15803d`, watch `#fef3c7/#b45309`, radar muted.
  Desk stances: act green, accumulate sky, watch amber, pass muted.
- **3px gradient top border** spanning all category colors, left → right,
  across the full app width (`.gradient-border`).
- ⚡ favicon via inline SVG data URI in `<head>` (no external request, `file://`-safe).
- Transitions: `--ease: 250ms ease` (within the 200–300ms rule).

## Architecture — two data layers
**Static config** (categories, center node, countries, zones, mapIntro) → read
directly from `window.AIE_DATA`. Never written to localStorage.
**User data** (tickers, theses, settings) → seeded into localStorage on first
load, then read/written there so user edits persist.

**Script load order in `index.html`:** `<script src="data.js"></script>` must
come FIRST, then the app `<script>`.

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
The Supply Chain Map (Tab 1) has two HTML-div views, toggled by a pill button
(`mapState.view`, `"pipeline" | "cross"`) next to "Show All" — not SVG:
- **Pipeline** (default) — `renderPipeline()` in `index.html` builds three
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
├── index.html                  THE APP — HTML + <style> + <script>, offline-first
├── data.js                     window.AIE_DATA — GENERATED, never hand-edit
├── CLAUDE.md                   this file — build spec + current status
├── README.md                   quick start + project map
├── .claude/skills/weekly-review/SKILL.md   the /weekly-review desk procedure
├── docs/
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
   `ingest/store/base.json`), **trust the code** and fix this file — it drifts.
