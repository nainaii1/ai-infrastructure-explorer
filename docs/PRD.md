# PRD — AI Infrastructure Explorer

_Status: living document. Personal research tool. Last updated 2026-08-29._

## 1. Overview & problem
On the surface, AI-hardware investing looks like just one name — NVIDIA. The real signal lives in the **layered supply chain beneath it**: photonics, memory (HBM), fabs & foundries, materials & packaging, networking, neoclouds, glass substrates, accelerators, and (emerging) robotics/humanoids. That landscape is opaque and scattered across tweets, filings, and brokerage tabs. A trusted analyst (**@aleabitoreddit**) posts high-signal ideas about these "picks and shovels" names — but tweets scroll away and conviction is hard to track over time.

**AI Infrastructure Explorer** is a single, offline research cockpit that makes the supply chain legible, captures that analyst's conviction durably, and monitors the names with weekly prices.

## 2. Primary user
The operator (me). **Single-user, local-first.** The public GitHub repo exists for backup/portfolio — there is no external audience to serve, no onboarding, no accounts.

## 3. Jobs to be done (equal weight)
1. **Understand** — see how suppliers connect to NVIDIA + the hyperscalers, organized bottom→top by value-chain layer; click a layer to filter the companies in it.
2. **Conviction** — capture @aleabitoreddit's ideas over time and rank what they actually prioritize (composite score = mention **frequency** + **recency** + **conviction language**), each linked back to the source post.
3. **Monitor** — a watchlist of the names with price, **7D / 1M %**, market cap, and my own rating, refreshed weekly.
4. **Decide** — turn captured conviction into action: every ticker is auto-tiered (**Core / Watch / Radar**) so one-off name-drops don't clutter the desk, and each Core name carries **Claude's weekly desk verdict** — a second opinion on the analyst's take (agree or push back), a stance (`act / accumulate / watch / pass`), a concrete execution suggestion, and "what changes my mind". The analyst provides conviction; Claude provides challenge; the operator decides.

No single job dominates; the value is having all four in one offline place.

## 4. Success criteria
1. **Completeness — nothing slips through.** Every ticker/idea @aleabitoreddit posts is captured and categorized: clean `$CASHTAGS` are auto-added, ambiguous mentions are queued for review. The corpus stays complete.
2. **Decision impact.** The priority ranking + watchlist actually change what I watch or buy. The tool earns its place by informing decisions, not by looking polished.

## 5. Scope by version
| Version | Scope | Status |
|---|---|---|
| **v1** | Supply Chain Map: value-chain layer stack (grouped into Demand/Chip/Supply flow zones), click-to-filter, ticker cards | ✅ Done |
| **v2** | Watchlist: sortable table (category / price / 7D / 1M / mkt cap / rating), weekly Yahoo price fetch via local server button, rating persists | ✅ Done |
| **v3** | Telegram ingest → theses + auto-grown tickers + priority ranking | ✅ Done |
| **v3** | Thesis tab UI (render the ingested theses + sources) | ✅ Done |
| **v4** | Brain tab: `synthesize.py` groups theses by category, one AI-narrative digest per theme (narrative, conviction, key points, tickers, drill-down to source theses) | ✅ Done — but needs a paid `ANTHROPIC_API_KEY`; refreshed manually otherwise (see `docs/GUIDE.md` §3) |
| **v5** | Conviction tiers (Core/Watch/Radar, radar hidden by default) + Desk verdicts (Claude's weekly per-ticker stance + execution note, top 12–15 Core names) + `/weekly-review` project skill + Hyperscalers demand layer | ✅ Done — runs in a weekly Claude Code session, no API key needed (see `docs/GUIDE.md` §7) |
| **v7** | "Private Coverage": multi-page split, coverage memos, knowledge vault + graph, cross-linking, the calls ledger, and the "Unpacked" visual rebrand | ✅ Done (2026-07-15) |
| **v8** | "Analysis tool, not product": Desk opens on the Watchlist, Evidence chapter and all hero art removed | ✅ Done (2026-07-18) |
| **Expert review 1** | Direction-aware scoring — a bearish thesis lowers a score instead of raising it; conviction-keyword multiplier retired | ✅ Done (2026-07-26) |
| **Expert review 2** | The three review seats (semi-expert / fundamental / PM) research the top names before each weekly review and file cited findings; uncited findings are recorded but worth zero | ✅ Done (2026-07-27) — `/pre-review`, no API key needed (see `docs/GUIDE.md` §6) |
| **Expert review 3** | The claims ledger: dated predictions recorded and judged when their date arrives, hit rate always shown beside the untestable share | ✅ Done (2026-07-28) — `/judge-claims` (see `docs/GUIDE.md` §8) |
| **Expert review 4** | Feed a source's track record back into the rankings | ⬜ Waiting on data — needs 20+ judged claims per source; earliest deadline Dec 2026 |
| **Expert review 5** | Run the review seats unattended overnight | ⬜ Needs a decision on API access |
| **v6** | "Field Guide" redesign: tabs dissolved into one continuous scroll (hero summary + four numbered chapters — Map, Watchlist, Evidence, Synthesis) with a floating nav bar; conviction scoring now discounts names buried in list-heavy posts (`1/√tickers-in-post`) so tiers reflect real conviction; Evidence chapter caps the raw feed to the 10 most recent posts, older ones behind a "show more" click | ✅ Done (2026-07-03) |
| **v9** | "Soft two-tone" visual redesign — lavender canvas, big display type, accessibility-audited (`test_contrast.py`). Nav renamed Today/Notes/Vault/Record | ✅ Done (2026-07-31) |
| **PROJECT.md, Step 1-1b** | Per-ticker views: read what the analyst actually argued about each name in each post, not just how often he named it (`views[]`, 1,330 arguments as of 29 Aug) | ✅ Extraction complete (2026-08-29). Wiring `direction` into scoring is a deliberate later decision, not done |
| **PROJECT.md, Step 2** | Real revenue from SEC EDGAR filings, six years per company, rendered on the ticker card | ✅ Done (2026-08-21) — 37 of 46 covered, gaps recorded with reasons |
| **PROJECT.md, Step 3** | `aiExposure` — the operator's judgement of how much of a company is genuinely AI, since no filing discloses it | ✅ Instrument shipped 21 Aug; **45 of 49 filled 28-29 Aug** (4 sourced from company disclosure, 41 desk estimates, each labelled which) |
| **PROJECT.md, Step 4** | Chart: AI exposure against price performance vs SMH | ✅ Done (2026-08-29), in the Watchlist chapter of `desk.html` |
| **Weekly desk review** | `/weekly-review` (+ `/pre-review` first): prices, tiers, Brain digests and desk verdicts refreshed every week; a calls ledger and a claims ledger track whether the desk and the analyst are actually right over time | ✅ Running weekly since July 2026 |

## 6. Data model
Single global `window.AIE_DATA` in `data.js` (generated by the ingest tooling, see `ingest/generate_data_js.py`):
- `meta` — version, schemaVersion, lastUpdated, source
- `claims` — the claims ledger: dated predictions with their source, deadline, and outcome (`open` / `correct` / `wrong` / `unfalsifiable`), plus precomputed per-source scores. Nothing here feeds any ranking yet — that is a later phase, gated on having enough judged claims for a rate to mean anything.
- `countries` — `{ code: { flag, label } }`
- `categories` — `{ id: { id, label, subtitle, color, layer, tooltip, flowRole, investorAngle } }` (the value-chain layers; `layer` = bottom→top order, `flowRole` = `demand|chip|supply` groups it into a map zone, `investorAngle` = the one-line "what to watch" shown when a layer is selected)
- `center` — the NVIDIA + Hyperscalers demand hub copy
- `mapIntro` — one-line "how to read this map" copy shown atop the Supply Chain Map tab
- `zones[]` — ordered `{ id, label }`, e.g. Demand → Chip → Supply, driving the map's zone dividers
- `tickers[]` — `{ ticker, company, category, market, exchange, whatTheyDo, whyNVDA, marketCapTier, rating, sourceTweetUrl, addedDate, tier }` + optional `price, currency, chg7d, chg1m, marketCap, asOf` (weekly) + optional `priority` + optional `verdict` (stamped from `verdicts.json`, Core names only)
- `theses[]` — `{ id, source, author, sourceUrl, postedAt, ingestedAt, text, tickers[], conviction, tags[] }`
- `priorities[]` — ranked `{ ticker, score, mentions, convictionHits, lastMentioned }`
- `brain` — `{ meta: { generatedAt, model, thesesConsidered, categoriesSynthesized, schemaVersion }, digests[]: { category, narrative, conviction, keyPoints[], tickers[], sourceThesisIds[], thesesCount, lastSynthesized } }`
- `desk` — `{ meta: { reviewedAt, reviewer, thesesConsidered, coverage, cadence, disclaimer }, verdicts[]: { ticker, stance, view, execution, changesMind, basedOnThesisIds[], updatedAt } }` — Claude's weekly verdict layer (`ingest/store/verdicts.json`)

**User state** persists in `localStorage`: `aie_tickers`, `aie_theses`, `aie_settings`. Seeding is version-aware: when the ingest tooling bumps `meta.version`, the app re-seeds theses and merges newly-added tickers so updates surface.

## 7. Architecture (two layers)
- **Static app** — `index.html` + `data.js`. Vanilla HTML/CSS/JS, offline (`file://`), no frameworks/CDN/build. This is what the operator opens.
- **Ingest tooling** — `ingest/` (Python standard library). Telegram bot, Yahoo price fetcher, and a generator that regenerates `data.js`. Runs locally/weekly; **never shipped to the browser**.

Why this split: browsers block local `fetch()` under `file://` and block Yahoo via CORS, so all data acquisition is server-side and baked into `data.js`.

## 8. Non-goals
- No live in-browser quote fetching (offline + CORS → server-side only).
- No framework, bundler, or build step.
- No multi-user, accounts, auth, or hosting.
- Not investment advice; not a trading platform.

## 9. Principles & constraints
- Offline-first; the app must work by double-clicking `index.html`.
- `data.js` is the single source of truth, regenerated by tooling — never hand-edited for ingested data.
- Colors / labels / tooltips come from `data.js`, never hardcoded in the app.
- Secrets via a gitignored `ingest/.env`; the bot only obeys the operator's Telegram id.
- 200–300ms transitions; responsive at a 768px breakpoint.
