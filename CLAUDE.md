# CLAUDE.md — AI Infrastructure Explorer

## What this is
An interactive web tool mapping the **AI hardware supply chain** — how NVIDIA + the hyperscalers connect to the layers of suppliers beneath them (photonics, memory, fabs, neoclouds, materials, networking). Click a category node → the tickers in that category appear below. Three tabs: **Supply Chain Map**, **Watchlist**, **Thesis**.

This is **not** related to any trading desk or market-brief project. Standalone product.

**Commercial intent:** the map is the hook; the real product is structured, sourced thesis + watchlist data. Treat `data.js` like it's the actual product, not throwaway config.

## Current status / roadmap
- [ ] **v1 — Tab 1 (Supply Chain Map):** SVG node map + ticker cards + click-to-filter. ← BUILDING NOW
- [ ] Tabs 2 & 3 — placeholder cards only ("Coming soon — built in next step").
- [ ] v2 — Watchlist tab live (rate/sort tickers, persist to localStorage).
- [ ] v3 — Thesis tab + Python ingest pipeline that regenerates `data.js` (prices + theses from external sources).

## Hard rules (do not break these)
1. **Vanilla HTML / CSS / JS only.** No React, no Tailwind, no frameworks, no CDN libraries. Everything hand-written.
2. **Must work by double-clicking `index.html`** (file:// protocol). This is exactly why data lives in `data.js` (loaded via `<script>`), NOT `data.json` (fetch is blocked under file://). Do not introduce `fetch()` of local files.
3. **Only two files hold app code:** `index.html` (CSS inside `<style>`, logic inside `<script>`) and `data.js` (data + config). Do not split into more files in v1.
4. **All colors, labels, tooltips, and tickers come from `data.js`.** Never hardcode them inside `index.html`. If the map needs a category color, read it from `AIE_DATA.categories[id].color`.
5. All hover/click transitions **200–300ms ease**. Mobile breakpoint **768px**. Fully responsive.
6. **Do not invent, add, or remove tickers.** There are exactly **16**. See data notes below.

## Design system
- Background `#0d0f14` · Card background `#161b27` · Border `#1e2535`
- Primary text `#e2e8f0` · Muted text `#64748b`
- Font: `Inter, system-ui, sans-serif`
- Category colors: live in `data.js` (`categories[].color`) — Photonics `#3b82f6`, Memory `#8b5cf6`, Fabs `#f59e0b`, Neoclouds `#22c55e`, Materials `#f97316`, Networking `#14b8a6`
- **3px gradient top border** spanning all 6 category colors, left → right, across the full app width.
- ⚡ favicon via inline SVG data URI in `<head>`.

## Architecture — two data layers
**Static config** (categories, center node, countries) → read directly from `window.AIE_DATA`. Never written to localStorage.
**User data** (tickers, theses, settings) → seeded into localStorage on first load, then read/written there so user edits persist.

**Script load order in `index.html`:** `<script src="data.js"></script>` must come FIRST, then the app `<script>`.

### Seeding logic (runs once on load)
```
if localStorage "aie_tickers"  is missing  -> set to AIE_DATA.tickers
if localStorage "aie_theses"   is missing  -> set to []
if localStorage "aie_settings" is missing  -> set to { version:"1.0", lastUpdated:null }
```
After seeding: the app reads **tickers from localStorage** (so future edits stick) but reads **categories / center / countries from `AIE_DATA`** (static config, never user-edited).

**localStorage keys:** `aie_tickers`, `aie_theses`, `aie_settings`.

## Data schema
**Ticker object:**
```
{ ticker, company, category, market, exchange,
  whatTheyDo, whyNVDA, marketCapTier,
  rating, sourceTweetUrl, addedDate }
```
- `category` → a key in `AIE_DATA.categories` (`photonics|memory|fabs|neoclouds|materials|networking`)
- `market` → a key in `AIE_DATA.countries` (`US|KR|TW|SE|FR|DE`); render the flag via `countries[market].flag`
- `marketCapTier` → `Mega | Large | Mid | Small`
- `rating` → `watch` (default in v1)

**Thesis object** (Tab 3, v3): not defined yet. Keep `aie_theses` as `[]`.

## Data notes (read before touching the map)
- **Networking has ZERO tickers in v1.** It still renders as a node on the map. Clicking it shows an empty state ("No tickers tracked yet"). **Do not fabricate networking tickers.**
- **NVDA is both the conceptual center AND a normal ticker in the `fabs` category.** The center node uses `AIE_DATA.center` (separate object). The NVDA card appears under the Fabs filter like any other ticker.
- Exact ticker count: **16**.

## Build tickets (build in this order, one at a time)
- **T1 — App shell.** 3-tab top nav (Supply Chain / Watchlist / Thesis), active tab has white bottom border, fade transition between tabs. Gradient top border + favicon. Run the seeding logic. Tabs 2 & 3 = "Coming soon" placeholder cards. **No map yet.**
- **T2 — Supply chain map (Tab 1, Section A).** SVG ~380px tall: center node (NVDA + Hyperscalers) + 6 category nodes in a wide arc below, connected by SVG lines. Hover node → connecting line glows in that category color + floating tooltip (a div, not SVG `<title>`). Click node → glowing ring on node + filter the cards below. "Show All" button top-right clears the filter.
- **T3 — Ticker cards grid (Tab 1, Section B).** 4 per row desktop / 2 tablet / 1 mobile. Each card: ticker (large bold monospace, category color), company name (muted), category badge (color pill), market badge (flag + exchange), "What they do:", "Why NVDA needs them:", market-cap tier badge. Cards fade in when the filter changes.

## File structure
```
ai-infrastructure-explorer/
├── index.html                  app: HTML + <style> + <script>
├── data.js                     seed data + config (window.AIE_DATA)
├── CLAUDE.md                   this file
└── ai-supplychain-prompt.txt   original detailed build spec (reference)
```
