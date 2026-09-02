# Roadmap & Status — AI Infrastructure Explorer

_Last updated: 2026-08-29 (weekly review run, view extraction complete, exposure filled, exposure-vs-price chart shipped). Living document — update as things ship or change._

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

_Read live from `ingest/store/*.json` and `data.js` on **1 Sep 2026**. These
numbers move every week — when this file and the store disagree, the store is
right._

| | |
|---|---|
| Companies tracked | **148** — 37 Core / 9 Watch / 102 Radar |
| Captured posts | **612** — 420 from the analyst, 192 from the desk's own expert seats |
| Arguments extracted | **1,330** — what he actually argued, per post per company. **Extraction is complete: 0 pending** |
| Desk verdicts | **21** names, reviewed **1 Sep** (7 accumulate / 11 wait / 3 pass) |
| Coverage memos | 78 · **Vault** 65 pages, 31 with written notes · **Brain** 11 theme digests |
| Calls ledger | **16** — 12 open, 4 closed (1 win / 2 losses / 1 wash). Oldest call 12 Jul |
| Claims ledger | **77** — 3 judged correct, **13 unfalsifiable**, 61 open (2 ripe, awaiting `/judge-claims`) |
| SEC revenue | 37 companies covered, 9 gaps recorded with reasons |
| AI exposure | 45 assessed — **4 from company disclosure, 41 desk estimates**. AXTI and AMD bases now stale (see issue 2) |
| Telegram queue | **0 pending** |
| Tests | 506, green |
| GitHub | Public — github.com/nainaii1/ai-infrastructure-explorer, branch `main` |

**1 Sep pass in one line:** `/pre-review` and `/weekly-review` ran the same
day for the first time — 36 seat findings, all verified against primary
sources, drove both stance moves (AXTI accumulate→wait on China export-permit
risk, MTSI wait→pass on MACOM's own later laser date). MRVL and AVGO
initiated. 14 names triaged out of the unsorted backlog, `GM` rejected, and
three out-of-scope names (RDDT, RKLB, RPI) removed from the universe.

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

_Rewritten 29 Aug 2026, re-cut 1 Sep 2026. Only genuinely open items are
listed; everything that was fixed has been removed rather than left ticked._

**0. Bear research de-ranks a name out of its own coverage.** THE ONE TO
DECIDE FIRST. Direction-aware scoring is built so outside research can only
correct a name downward — that asymmetry is deliberate and must not be
reversed. But `/weekly-review` picks the verdict roster by *score*, so the
moment the seats find a problem with a name, that name falls out of the list
the desk writes verdicts on. Measured on the 1 Sep pass, from that day's own
findings with no analyst input: **MTSI #13 → #148** (score 2.52 → 0.00),
POET #18 → #151, SNDK #16 → #49, AXTI #7 → #13. No tier moved, so the
`assign_tiers` guard held and nothing shifted in the UI. The roster was fixed
by hand that week — Core-tier *membership* rather than rank decided who
stayed. Needs a written rule so it stops being a manual override. Do **not**
fix it by letting research raise a score.

**1. Recorded daily closes are stamped one day late.** `record_prices` takes
the row's date from the FETCH timestamp, and both scheduled fetches run outside
US market hours, so every observed row holds the previous session's close.
Proved by a Saturday row carrying a value that differs from Friday's. Live
prices in `prices.json` are unaffected — only the saved history. Blocks the
"since he argued it" feature.

**2. Two AI-exposure bases are stale and understate their names.** AXTI's
basis still reads "revenue is $0.09bn and shrinking" against a filed half-year
of $74.5m with gross margin up from 8.0% to 44.9%; AMD's records Data Center
at 47.9% on FY2025 against a filed quarterly 58.2%. Both were caught by the
1 Sep seat research. Fix with `/assess-exposure`.

**3. The parser invents tickers from jargon.** Candidate symbols pile up in
`pending_tickers.json` and the most frequent are not companies: `CW`, `MC`,
`CEST`, `UTC`, `EML`, `NAND`, `NPO`, `DRAM`, `MLCC`, most seen once. Same
cause as `$GM` from "Elazr GM" and `$ASX` from "SRL (ASX)". Harmless —
nothing auto-promotes — but it is why every symbol needs hand-triage. Partly
mitigated 1 Sep: `themeTags` and the new `outOfScope` list now block the known
offenders from ever re-adding themselves.

**4. A removed ticker survives in the browser.** `AIE.seed()` merges on a
version bump and deliberately keeps any localStorage ticker absent from
`data.js`, so a name deleted from the store lingers in an already-seeded
browser. Verified inert on 1 Sep — `GM` is in localStorage but renders in no
view, because the watchlist is Core-only and the map hides Radar. One-line fix
in `shared/common.js`; left alone because it changes seeding for every page.

**5. 41 of 45 AI-exposure figures are desk estimates, not research.** They
render an `est.` chip and sit at low or medium confidence so they cannot be
mistaken for measurements, but they are guesses. The four sourced from company
disclosure (NVDA, AMD, AVGO, MU) show a `reported` chip instead.

**6. `ingest/.env` and iCloud sync.** The file can hit sync conflicts under
iCloud Drive. Workaround: `export TELEGRAM_BOT_TOKEN=...` in-session, or
exclude the folder from sync.

**7. "Note" conviction badge is ambiguous** — rename to "Normal" or drop it.
Cosmetic, open since July.

**8. Eight orphan views** point at tickers no longer in the universe (ASTS 5,
MELI 3). They render nowhere because the ticker cards that would show them do
not exist. Deleting them is a decision nobody has taken.

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

_Rewritten 29 Aug 2026 after the weekly review. Items 2, 3 and 5 of the
previous list shipped; the rest is below._

**The main focus is not on this list.** It is to run the weekly loop and let
the calls ledger fill. 14 calls, 1 closed. Until roughly 20 have closed there
is no evidence this desk beats simply buying the index, and that single fact
gates every larger question — publishing, product, all of it. Nothing below is
more valuable than letting a few months pass.

Small jobs, if there is appetite for one:

1. **Fix the price-history date bug.** Every recorded close is stamped one day
   late: the row takes the FETCH date, and both scheduled fetches run outside
   US market hours, so each row holds the previous session's close. Live prices
   are unaffected. This blocks item 2. Two decisions attached — how to map a
   fetch to a trading day, and whether to relabel the 8 existing days or start
   clean.
2. **"Since he argued it" receipts** — blocked on item 1. Scoring 1,330 dated
   arguments against a date-shifted price series would be wrong by a trading
   day, and by three across a weekend. This is still the feature that would
   make the desk unlike any screen you can buy.
3. **Upgrade the hyperscaler exposures.** AMZN, MSFT and GOOGL are still desk
   estimates and *are* derivable from segment reporting, the way NVDA, AMD,
   AVGO and MU were on 29 Aug.
4. **Parser stop-list.** 306 candidate symbols have accumulated and the most
   frequent are jargon, not companies: `CW` 50x, `MC` 39x, `CEST` 35x, `UTC`
   29x, `EML`, `NAND`, `NPO`, `DRAM`, `MLCC`. Same root cause as `$GM` from
   "Elazr GM" and `$ASX` from "SRL (ASX)". Cosmetic but it is the source of
   every hand-triage so far.
5. **Step 1b — wire direction into scoring.** Still deliberately not done, and
   still low-value: only 30 bear views out of 1,330 would move anything, and
   the per-post vs per-ticker mismatch has to be resolved first. See
   PROJECT.md "Scoring impact".
6. **Radar-tier triage, gradually** — `review.py classify` a few per week.

### Considered and rejected (29 Aug 2026)

- **A fourth expert seat for positioning and flows.** Proposed after the
  upstream selloff, then withdrawn on inspection: the desk holds price, market
  cap, three percentage changes and revenue. No volume, no float, no short
  interest, no ownership. A positioning analyst with no positioning data would
  cite nothing, be marked unverified, and score exactly zero by the desk's own
  rules. Revisit only if a data source appears first.
- **More roles generally** (macro, PM, ops, investors). The tool has one user
  and already produces 78 memos, 65 vault pages, 21 verdicts and 192 research
  findings. Output already exceeds one person's reading. Adding producers makes
  that worse, not better.

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
| Posting on X (draft idea) | `docs/X-CONTENT.md` | The content plan — not built, for review |
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
