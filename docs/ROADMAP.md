# Roadmap & Status — AI Infrastructure Explorer

_Last updated: 2026-08-22 (per-ticker views, SEC fundamentals, AI-exposure plumbing, daily price record, first judged claims). Living document — update as things ship or change._

> **Expert review team, Phase 1 — direction-aware scoring (✅ 2026-07-26).**
> Theses carry an optional `direction` (`bull`/`bear`/`neutral`), and
> `scorer.compute_priorities` now sums a **signed** contribution per mention, so
> a bear thesis lowers a score instead of raising it. A present-but-unreadable
> direction is inert rather than defaulting to a bull vote. Research-sourced
> theses (`source: "research"`) contribute 0 to both the score and
> `weightedMentions` — outside research can correct a name downward but can
> never inflate its rank or buy it tier coverage.
> The **conviction multiplier is retired** (`CONVICTION_WEIGHT = 0.0`,
> reversible by restoring 0.5): keyword-matched rhetoric was multiplying scores
> by up to 6×. Real effect — SIVE falls **91.11 → 14.99**, its lead over the
> next name drops from 2.7× to 1.6×, the top 15 loses GFS/JBL/MRVL/POET and
> gains AXTI/CCXI/COHR/SNDK. **Tiers are unchanged** (28 core / 17 watch /
> 75 radar) because `assign_tiers` reads `convictionHits` and
> `weightedMentions` directly, never the score.
> `write_data_js` now refuses to write a payload missing an expected top-level
> block, and checks that the running process is not holding stale source — see
> **Fixed** below.
> Spec: `docs/superpowers/specs/2026-07-26-expert-review-team-design.md`.
> Plan: `docs/superpowers/plans/2026-07-26-direction-aware-scoring.md`.
> Phase 2 shipped 2026-07-27 — see the entry directly below.
>
> **Expert review team, Phase 2 — the three seats (✅ 2026-07-27).**
> `ingest/pre_review.py` runs the `ingest/seats.py` seats — `semi-expert`,
> `fundamental` and `pm` — over a shortlist of up to 12 names (stance changes
> first, then names with 3+ new analyst theses, then by score — drops are
> reported, never silent). Findings become `source: "research"` theses. Both
> modules are pure and take an injected `call_fn`, so no API key is needed;
> driven by the new `/pre-review` skill. `seats.py` was split in two on
> 2026-07-27 when it passed the ~350-line threshold: it now holds only what a
> seat is and what a finding must satisfy, while `pre_review.py` holds the pass.
> **The verification rule:** no citable primary source means `unverified` and a
> forced `neutral` direction, which scores exactly 0.0 — visible but inert.
> Findings are pinned to the ticker the seat was *asked* about, so a forwarded
> third-party post cannot talk a seat into filing a finding against a different
> name in the book.
> Also closed three holes found in review: two research theses marked
> `conviction: "high"` promoted a name to Core past the `weightedMentions`
> guard; research counted as the analyst's own `mentions`, `attention` and
> `lastMentioned` on the ticker tooltip, the priority strip, the watchlist
> ordering and the vault ticker pages; and the shortlist's "stance changed"
> tier matched any verdict the weekly pass had rewritten, which on live data
> was 13 of 17 names and would have consumed the entire cap. Stance changes are
> now detected from a `previousStance` field that `/weekly-review` stamps.
> Phase 3's backend shipped 2026-07-28 — see the entry directly below.
>
> **Expert review team, Phase 3 — the claims ledger (✅ 2026-07-28).**
> `ingest/store/claims.json` + `ingest/claims.py` record dated, testable
> predictions from the analyst, the desk and each seat, and judge them when
> their date arrives. `unfalsifiable` is a first-class outcome: a claim nothing
> could settle is recorded, not dropped, and the **unfalsifiable share comes
> back from the same call as the hit rate** so no surface can show the
> flattering number alone. `hitRate` is `None`, never `0.0`, when nothing has
> been judged. Judging to correct/wrong needs a citable primary source; judging
> early or re-deciding a judged claim raises. **A claim moves no score and no
> tier** — a test asserts `scorer.py` never reads the ledger.
> **Seeded 2026-07-28:** 25 analyst claims from 64 focused posts (list-dumps of
> >3 tickers excluded), **13 of 25 unfalsifiable — a 52% unfalsifiable share**,
> 0 judged because every deadline is still in the future. Over half of what
> this desk's only source says cannot be tested. That is the number the ledger
> was built to surface.
> `performance.html` now carries both ledgers: **Calls** (position actions vs
> SMH, as before) and **Claims** (per-source scorecards + every prediction,
> soonest deadline first). The hit rate and the untestable share are computed
> together in Python and travel in one object, so no surface can show the
> flattering figure alone; with nothing judged the card reads "No judged claims
> yet" rather than 0%.
> **Still to do in Phase 3:** the remaining 62 focused posts of the backfill.
> **Not yet built — Phases 4–5:** hit-rate weighting (gated on 20+ judged
> claims per source) and the scheduled overnight run.
>
> **Fixed 2026-07-26 — `data.js` was being silently truncated.** A `bot.py`
> process running since 30 June held a stale generator module in memory and
> rewrote `data.js` on every ingest using June-era code, dropping `glossary`,
> `desk`, `memos`, `vault`, `calls` and `benchmarkQuote`. The memo reader,
> vault, glossary and performance page were broken for four days with no
> signal, because ticker-level verdicts are stamped onto ticker records and
> survived — so the watchlist still looked healthy. `write_data_js` now hashes
> its own source modules at import and refuses to write if they have changed on
> disk. **Restart `bot.py` after editing anything under `ingest/`.**

> **v8 — "analysis tool, not product" (✅ 2026-07-18).** Deliberate
> de-productization after an operator review: the site is a personal analysis
> desk, not a landing page. Changes: the **Desk opens on the Watchlist** (order
> is now Watchlist → Map → Synthesis) under a one-line "desk strip" of live
> counts — the whole hero (H1, tagline, art, count-up animation) is gone. The
> **Evidence chapter was removed**; theses stay in the data and render only
> where cited (memo sources, vault "Cited theses", Synthesis drill-downs). The
> **Focus card was removed everywhere** (Desk + Coverage); its weekly headline
> now lives only in the weekly-review report. All **page hero art removed**
> (`renderFocusCard` + `art*` + `tileShape` deleted from `shared/common.js`;
> `chipSpark` kept). Density pass on chapter/page headers. Color system, memo
> reading surface, and the vault graph untouched. Dead `.unf-*`/`.aie-focus`
> rules remain in `theme.css` (harmless; optional future cleanup).
>
> **Private Coverage upgrade (v7) — ✅ all six phases shipped.** Multi-page split,
> memo-style coverage notes, Obsidian-style knowledge Vault + graph, minimal
> performance hooks, and the "Unpacked" cool rebrand. The authoritative **phase
> table + step-by-step prompt guide is [EXECUTION.md](EXECUTION.md)** — check the
> boxes there for live status.
> - **Phase 1 ✅ (2026-07-08)** — multi-page editorial foundation: `shared/theme.css`,
>   `shared/common.js` (`window.AIE`), `index.html` → `desk.html`, new front page.
> - **Phase 2 ✅ (2026-07-12)** — coverage memos (`memos.json` → `memo.html`, ledger, skills).
> - **Phase 3 ✅ (2026-07-12)** — knowledge Vault + graph (`vault.json`, index/page/graph views).
> - **Phase 4 ✅** — site-wide cross-linking (`AIE.linkForTicker`, `$TICK` / `[[wikilink]]` markup).
> - **Phase 5 ✅ (2026-07-12)** — performance hooks (`calls.json` + minimal page). The nav link was greyed until 3+ calls existed; that threshold was lowered to 1 on 2026-07-26 (`MIN_CALLS_FOR_NAV` in `shared/common.js`), so Performance is live.
> - **Phase 6 ✅ (2026-07-15)** — "Unpacked" cool rebrand (U1–U8): cool neutral-grey canvas,
>   geometric display type, ONE blue→violet brand gradient, true-black stage surfaces, data-owned
>   category icons, the weekly Focus card, Chapter 01 ticker-tile grid + expand-in-place, and the
>   docs/alias cleanup (`--serif` retired for `--display`).
>
> (This upgrade superseded the Signal Digest spec — coverage memos replaced it.)

> **Per-ticker view extraction, Step 1 of the mention-to-argument rework (✅
> 2026-08-19, Core/Watch complete).** Two things measured on the live store
> triggered this: analyst mentions have ρ=0.17 correlation with 1-month return
> (i.e. none), and 0 of 331 analyst posts carried a `direction` — every
> bull/bear figure in the system came from the desk's own research seats, not
> from him. `ingest/views.py` (pure, invariant-6 compliant) + the
> `ingest/extract_views.py` runner read every `source: "x"` post touching a
> Core/Watch ticker — 312 of 356 posts — and stamped a `views[]` array per
> thesis: `{ticker, direction, why, numbers?, horizon?}` per name in that post,
> because one post routinely argues opposite things about different tickers in
> the same paragraph. **1,179 views across 114 tickers, 581 bull / 580 neutral
> / 18 bear.** Purely additive — `scorer.py`, tiers and rankings are
> untouched. Usage: `docs/GUIDE.md` §10. Full rationale, the "argued vs
> mentioned" ranking divergence, and next steps (SEC EDGAR fundamentals,
> operator-judgement `aiExposure` fields, re-pointing the chart mockups at real
> variables): **`PROJECT.md`**, the live tracker for this initiative.

> **"What he's argued" on the ticker card, Step 4a (✅ 2026-08-20).** Step 1's
> 1,179 views were riding inside `data.js` and no page read them. They now
> render on the ticker dossier card in `desk.html`, above Claude's verdict —
> his evidence first, the desk's call second. Three additions to
> `shared/common.js`: `viewsForTicker(sym)` (the JS mirror of
> `views.summarize_ticker_views()` — same `source: "x"` filter, same
> newest-first order, verified to return identical counts to the Python),
> `viewStats(rows)` (bull / bear / bare split; anything not literally `bull` or
> `bear` reads as a bare mention — fail inert, invariant 3), and
> `makeViewsBlock(sym)`, styled by `.aie-views*` in `shared/theme.css` §7c.
> The header carries **signal density** — `SIVE 103 / 112 argued` against
> `NVDA 11 / 71` — which is the whole finding on the card instead of in a
> document. A name he has never named (GEV and the rest of Power & Cooling)
> renders no block; a name he names without ever arguing shows its bare
> references instead, so "0 of 2" is legible rather than blank. New
> `--sem-bear-*` token pair (5.74:1), registered in `test_contrast.py`.
> Read-only over generated data — no ingest, score, tier or ranking change.
> Known gap it surfaced: ticker **aliases never get a view** (a `$SIVEF` post
> counts as a SIVE mention but is dropped at extraction) — 21 posts across 7
> aliases, logged as known issue 3 in `PROJECT.md`.

> **`Argued` as a sortable watchlist column, Step 4b (✅ 2026-08-20).** 4a put
> the block on the chain-tab tile card only — three clicks and a tab switch
> from the default view, and the watchlist row detail is a *separate* renderer
> (`makeRowDetailRow`), so the feature was effectively invisible where the
> operator works. Fixed both ways: the block now renders in the watchlist row
> detail directly under "My call" (capped at 3 arguments, vs 6 on the card),
> and **`Argued` is an 11th sortable column** showing `103/112`, `11/71`,
> `0/5`. It is the first surface in the app that ranks on something other than
> posting frequency. Backed by `AIE.viewDensity(sym)` — one memoised pass over
> all theses, because per-row `viewsForTicker` would rescan the corpus 135
> times per render. Sorts on the argument COUNT, not the ratio (a name argued
> 1-of-1 is 100% dense and says nothing); a name he has never mentioned renders
> `—` and sorts last in both directions rather than tying with a real zero.
> Core tier descending: `SIVE 103/112 · AAOI 57/81 · LITE 43/79 · XFAB 29/29`.
> Ascending: `NOK 0/5 · AAPL 2/11 · AVGO 2/13 · MSFT 3/11`. The table already
> scrolled horizontally on mobile at 10 columns; page layout is unchanged.

> **`His case` + the bear flag, Step 4c (✅ 2026-08-20).** Operator review of
> 4b: "Argued" was jargon (against v9's own no-jargon-in-headers rule), and the
> column showed how MUCH he said while hiding WHICH WAY — so a name he is net
> negative on looked identical to one he is bullish on. Renamed **`His case`**
> (`data-key` stays `argued`, an internal id). Direction now renders as an
> **exception flag**: measured on live data, 28 of 34 Core names are 100% bull
> when argued and only 5 carry any bear view (`IREN 4/5`, `TSM 8/1`, `TSLA 3/1`,
> `MTSI 3/1`, `AVGO 1/1`), so those 5 get a red `N bear` chip and the other 29
> get nothing — flagging "all bull" on 28 rows only teaches the eye to skip the
> column. The word, never an arrow: the sort indicators are already `▲`/`▼`.
> **IREN is the only Core name he is net negative on**, and it is now visible
> without opening anything. Fixed alongside: the 3-row cap could hide every
> bear view (IREN's three newest are bull), so the column's flag contradicted
> the panel it opened — `makeViewsBlock` now guarantees his most recent bear
> view is among the rows shown, which cannot disturb the date order because a
> bear outside the slice is always older than every row inside it.

> **The ticker-alias gap, Step 5 (✅ 2026-08-21).** `mentions` is counted AFTER
> `scorer.canonicalize_theses` folds `base.json` `tickerAliases` in, so a
> `$SIVEF` post counted as a SIVE mention — but extraction pinned to the post's
> raw `tickers[]`, the alias is not in the ticker universe, and the post
> therefore produced **no view at all**. Counted and never read.
> `views._post_ticker_scope` now canonicalizes through an **injected** alias
> map (`views.py` stays pure; `extract_views._aliases()` does the I/O) and the
> prompt gains a note line telling the model this post spells SIVE as `$SIVEF`.
> The firewall is unchanged and tested: the map rewrites symbols the post
> already contains, it never adds one.
> **Two more instances of the same bug surfaced while fixing it** —
> `_pending(core_only=True)` intersected RAW symbols with the core set (a
> `$LPK`-only post never matched `LPK.DE`), and `_core_symbols` canonicalized
> with **no maps at all**, computing a different tier table than the app:
> `000660.KS` read radar (really watch), `SOI.PA` watch (really core), `SPCX`
> core (really radar — a `themeTag`, not a ticker). Together these let
> `--status` report **"0 Core/Watch pending"** while four Core/Watch posts were
> unread. Both fixed, both covered by regression tests, and `--status` gains an
> `aliasGap` counter so the class of gap is visible rather than rediscovered.
> **29 views recovered across 22 posts.** SK Hynix (`000660.KS`) went from *no
> block at all* — the app said he had never mentioned it — to `4 / 6`. `SIVE`
> 103/112 → 105/115, `LPK.DE` 5/11 → 10/16, `SOI.PA` 7/9 → 11/13, `CXMT` 0/5 →
> 1/6 with the one being a bear. **Every Core/Watch name's view total now
> equals its `analystMentions` exactly.** Zero tier changes, zero mention-count
> changes; the only score movement is one day of uniform time decay (all 131
> ratios inside 0.960–0.969). Suite 386 → 407.

---

## Current snapshot

| | |
|---|---|
_Measured from `ingest/store/*.json` and `data.js` on 2026-07-27._

| | |
|---|---|
| Tickers tracked | **120** — tiered **28 Core / 17 Watch / 75 Radar** (after focus-weighting and canonicalization) |
| Categorized layers | 10 (`photonics, memory, fabs, neoclouds, materials, networking, glass, robotics, accelerators, hyperscalers`) |
| Unsorted (needs triage) | **55** names in the `unsorted` bucket: **1 Core (RDDT)**, 7 Watch (ASTS, CRCL, EWY, HOOD, NVTS, RKLB, VPG), 47 Radar. RDDT is the only one that matters — it doesn't cleanly fit any of the 10 categories (Reddit/AI-training-data play), so it's left in triage rather than misclassified. The Radar tail is mostly one-off name-drops and is not worth triaging by hand. Note `DRAM` and `SPCX` are `themeTags` in `base.json`, not tickers — they no longer count toward any name's mentions, though a stale `SPCX` ticker record still exists at Radar |
| Theses ingested | **258** — all `source: "x"`, author `aleabitoreddit`. No research theses written yet; the seats have not been run |
| Brain digests | 10 themes, generated 2026-07-22 — 9 re-synthesized that day, `robotics` carried forward from 2026-07-16 |
| **Desk verdicts** | **17 Core names** (`ingest/store/verdicts.json`, reviewed 2026-07-22): 9 `accumulate`, 8 `watch`. Roster rule is "top 15 by score + sticky act/accumulate holdovers". Stance *moves* are not recoverable for this pass — `previousStance` did not exist when it was written; the next `/weekly-review` starts recording them |
| GitHub repo | Public — github.com/nainaii1/ai-infrastructure-explorer, working branch `feat/expert-review-seats` |

Counts drift constantly as posts get ingested — trust `ingest/store/*.json` /
`git log` over this file when they disagree. Regenerate the tier split with
`python3 ingest/generate_data_js.py` and read it back from `data.js`.

---

## The operating loop (v5 — this is the product now)

```
He tweets → you forward to the Telegram bot (or backfill from signal bots)
     → theses.json grows, tickers auto-added
     → scorer tiers everything: Core / Watch / Radar   (noise ignored by default)
     → weekly: "run the weekly review" in Claude Code
         → prices refreshed, Brain digests updated,
           Claude's desk verdict per Core name:
           stance (act/accumulate/watch/pass) + execution + what-changes-my-mind
     → you decide, using his conviction AND Claude's second opinion
```

---

## What's built

| Area | Status | Notes |
|---|---|---|
| **v6 "Field Guide" redesign** | ✅ Done (2026-07-03) | Tabs → one chaptered scroll (hero prologue + 4 numbered chapters + colophon); frosted-glass capsule nav w/ sliding pill + scrollspy (bottom-floating on mobile); cool cleanroom palette; spring motion tokens; scroll reveals; unified drill-down animation; glossary strip (`AIE_DATA.glossary` from `base.json`); "New this week" strip; heat-aware cross-section legend; all DESIGN.md §7 inconsistencies resolved |
| Supply Chain Map — flow-pipeline layout | ✅ Done | 10 layers incl. new **Hyperscalers** demand layer; click-to-filter; investor angle per layer |
| **Conviction tiers (Core/Watch/Radar)** | ✅ Done (2026-07-03) | `scorer.assign_tiers()` — mentions + conviction-language thresholds; stamped on every ticker; unit-tested |
| **Map/Watchlist default to Signal (Core+Watch)** | ✅ Done (2026-07-03) | Radar (one-off mentions) hidden behind a "Show N radar names" toggle / Radar chip |
| **Desk verdicts (Claude's weekly view)** | ✅ Done (2026-07-03) | `store/verdicts.json` → `AIE_DATA.desk`, stamped per ticker; Watchlist "Desk" column + full verdict block on Core ticker cards |
| **`/weekly-review` project skill** | ✅ Done (2026-07-03) | `.claude/skills/weekly-review/SKILL.md` — the whole weekly pass in one command, no API key needed |
| Watchlist tab (sortable table, 7D/1M, rating) | ✅ Done | + tier chips, Desk column, review provenance line |
| Yahoo price fetcher / local server | ✅ Done | `fetch_prices.py` / `serve.py` (port 8765) |
| Telegram ingest bot + fxtwitter auto-fetch | ✅ Done | `bot.py` / `fetcher.py` |
| Thesis tab | ✅ Done | Date, conviction badge, source link, ticker chips |
| Brain tab (per-theme AI digests) | ✅ Done | `synthesize.py`; refreshed via the weekly review when no API key |
| Ticker triage CLI (`review.py`) | ✅ Done | Documented in GUIDE.md §5 |
| Backfill & auto-capture guide | ✅ Done (2026-07-03) | GUIDE.md §9 — forward from existing signal bots; Telethon watcher documented as the future automation path |

---

## Current issues to fix

### HIGH — affects daily use

**1. Bot must be started from the project directory** — ✅ FIXED 18 Jul 2026
`desk.command` (double-clickable menu: start bot / refresh prices / serve /
status) handles cd + env + launch. Supersedes the planned `start_bot.sh`.

**2. `ingest/.env` iCloud sync**
`.env` can hit sync conflicts under iCloud Drive. Workaround: `export
TELEGRAM_BOT_TOKEN=...` in-session, or exclude the folder from sync.

### MEDIUM — affects ingest quality

**3. SSL certificate verification globally disabled in `bot.py`** — ✅ FIXED
`bot.py` and `watcher.py` both use the shared `store_io.ssl_context()` now
("verified — never disable certificate checks globally"). Verified 2026-08-22.

**4. Mention-count inflation from list-posts** ✅ FIXED (2026-07-03)
`scorer.py` now focus-weights each mention by `1/√(tickers-in-post)`, so a name
in a 12-ticker digest dump counts ~0.29 vs. 1.0 for a dedicated post. Tiers are
assigned on `weightedMentions`; raw `mentions` is kept for display. This
dropped Core from an inflated 35 back to a meaningful 21 after the backfill.

### NEW — biggest scroll problem (2026-07-03)

**Evidence chapter (03) is ~90,000px tall.** After the June-July backfill the
raw thesis feed is 154 full-text digest cards. This is the real "too long to
scroll" surface (the Watchlist, chapter 02, is now a tidy ~1,500px). The proper
fix is the **Signal Digest** feature (spec'd in
`docs/superpowers/specs/2026-07-03-signal-digest-design.md`) — replace the raw
feed with short per-ticker digests, raw posts behind a drill-down. Cheap
interim option if Signal Digest isn't built soon: line-clamp each `.th-text` to
~5 lines with a "show full" expander (reuses the grid drill-down).

### LOW — polish

**5. Watchlist sticky header z-index** ✅ RESOLVED (2026-07-03) — the Watchlist
now opens on Core with natural page flow (no nested scroll / sticky header), so
the bleed-through issue is gone.
**6. "Note" conviction badge is ambiguous** — rename to "Normal" or drop.
**7. Desk verdict on watchlist is tooltip-only** — ✅ FIXED. Watchlist rows
expand in place (`makeRowDetailRow`) and now carry the verdict, his argued
views, and the SEC revenue block. Verified 2026-08-22.

### Decisions taken (2026-07-03) — deliberate non-actions

**No "Power / 800V DC" category (yet).** Names like NVTS, BE, FCEL, EOS, VRT
recur but mostly as *followers'* recommendations the analyst explicitly
disclaims ("these are follower recommendations, not my own") — thin personal
conviction. Adding an 11th map layer for a weak theme would dilute the map's
honesty. Revisit if he posts dedicated 800V-DC conviction; the names stay
radar/unsorted until then.

**Foreign / numeric-symbol names are intentionally not tracked.** Recurring
names like LeaderDrive (688017), Foosung (093370), Etron, Win Semi, Ayar,
O-Net, Shunsin, VisEra live only in thesis prose. They're mostly
untradeable-from-a-US-brokerage (Korea/Taiwan/China listings) or private
companies — promoting them to tracked ticker cards would add noise to a
US-retail Watchlist/Map without actionable value. The prose context is
preserved in the theses; the `parser.py` cashtag regex stays letter-only by
design.

---

## Next up (build order)

_Rewritten 2026-08-22. Items 1-7 and 9-10 of the previous list are done or
superseded; what remains is below._

1. **"Since he argued it" receipts** — **newly unblocked.** `price_history.csv`
   now records daily closes, so a view dated 13 Aug can finally be scored
   against what the price did next. `price_history.forward_return()` already
   computes it. This is the feature that makes the desk unlike any TradFi
   screen: not "here is the revenue", but "here is what happened after he made
   the case". Needs a few weeks of observed closes before the numbers are
   worth rendering — the seeded anchors are approximate.
2. **Step 3 — record the AI-exposure judgements.** Plumbing shipped; **0 of 46
   assessed**. Operator input, one name at a time, via `/assess-exposure`.
   Blocks item 3.
3. ~~**Step 4 — re-point the charts.**~~ **Done 29 Aug 2026.** The parked
   mockups turned out not to exist — never tracked, in no commit, nowhere on
   disk — so this shipped as one real chart instead: AI exposure against price
   vs SMH, in the Watchlist chapter of `desk.html`. See PROJECT.md "Step 4 —
   what shipped" for the provenance handling and for why the predicted
   hunting-ground quadrant is empty on a 1-month view.
4. **Step 1b — wire direction into scoring.** Still a deliberate decision, and
   still low-value: only 19 bear views out of 1,208 would move anything, and
   the per-post vs per-ticker mismatch has to be resolved first. See
   PROJECT.md "Scoring impact".
5. **View extraction, the last 11 posts** — radar/unsorted only; `--emit`
   without `--core-only` whenever convenient.
6. **Short-symbol parser false positives** — `$GM` from "Elazr GM at their
   investor conference" is still tagged and still counts as a mention. Worth a
   pass over symbols that double as English words (GM, ON, ARM, ALL, KEY).
   PROJECT.md known issue 1.
7. **Radar-tier triage, gradually** — `review.py classify` a few per week.

## Discussed but not yet built

- ~~**Signal Digest**~~ — **obsolete.** v8 removed the Evidence chapter it was
  designed to replace, and the per-ticker argument feed (`views[]`, shipped
  2026-08-20) delivers what it was actually for. Spec kept for history only.
  Original description follows.
- **Signal Digest** (full design spec, ready to plan+implement) — replaces the
  raw thesis feed in the Evidence chapter with short, Claude-authored
  per-ticker digests (AI Signal Watch style: one overview paragraph + one
  stance line per ticker), generated on demand from theses ingested since the
  last digest. Raw posts become an expandable "receipts" drill-down under
  each ticker line, reusing the same grid animation as the Brain's source
  reveal. Tweet discovery stays fully manual — Telegram bots can't read
  other bots' channel messages, so forwarding is unchanged; only the
  *authoring* step is new (mirrors the no-API-key `/weekly-review` pattern).
  See `docs/superpowers/specs/2026-07-03-signal-digest-design.md` for the
  full schema (`ingest/store/signal_digests.json`), the `ingest/digest.py`
  module design, and the rendering plan.
- ~~**"Since mention" receipts**~~ — **substrate shipped 2026-08-21**, promoted
  to "Next up" item 1. Rather than stamping a baseline in `bot.py`, every price
  refresh appends the day's closes to `price_history.csv`, which scores ALL
  1,200 existing views rather than only theses captured from here on.
- **Rotation arc**: a "where the analyst's attention is moving" phase timeline
  in the Synthesis chapter, driven by the Brain's mention-trend data.

- **Self-serve Brain/verdict refresh via API key** — `synthesize.py` already
  supports it; verdicts could get the same `call_fn` treatment for a
  fully-unattended weekly cron once a paid key exists.
- **Make.com auto-forward** — superseded in spirit by the Telethon watcher
  plan (item 5 above); keep as fallback.
- **Real price history sparklines** — **unblocked 2026-08-21**: `fetch_prices.py`
  now stores dailies to `price_history.csv`. Needs a few weeks of observed
  closes before a sparkline shows anything the seeded anchors do not.

---

## Guides available

| Guide | Location | Covers |
|---|---|---|
| Operating guide + FAQ | `docs/GUIDE.md` | Bot setup, Brain refresh, prices, triage, **weekly review (§6)**, **backfill/auto-capture (§7)** |
| Weekly review procedure | `.claude/skills/weekly-review/SKILL.md` | The exact steps Claude Code runs each week |
| Product requirements | `docs/PRD.md` | Problem, jobs, success criteria, architecture, data model |
| Design system reference | `docs/DESIGN.md` | Tokens, components, states |
| Engineering rules + status | `CLAUDE.md` | **Read first in a new session** |
| Ingest backend reference | `ingest/README.md` | Pipeline file-by-file |

---

## Architecture reminder

```
You open index.html (file://, no server needed)
       ↓
data.js loaded first (window.AIE_DATA — single source of truth)
       ↓
App reads tickers / theses / settings from localStorage
(tiers + desk verdicts arrive stamped on tickers, radar hidden by default)

─── Ingest pipeline (runs separately, locally) ──────────────────
  Telegram bot  →  bot.py → fetcher.py → parser.py
                      ↓
                  store/*.json  (theses, tickers, pending)
                      ↓
                  scorer.py  (priorities + Core/Watch/Radar tiers)
                      ↓          ↘
                      ↓        synthesize.py  (Brain — per-theme digests)
                      ↓        verdicts.json  (Desk — Claude's weekly per-name view)
                      ↓          ↙
                  generate_data_js.py  →  data.js
─────────────────────────────────────────────────────────────────
       ↓
Hard refresh app → data.js re-seeded into localStorage → UI updates

Weekly: open Claude Code → "run the weekly review" → the right side of
this diagram executes end-to-end.
```
