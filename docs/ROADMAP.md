# Roadmap & Status — AI Infrastructure Explorer

_Last updated: 2026-08-10 (v9 "soft two-tone" redesign, X watcher, symbol canonicalization shipped). Living document — update as things ship or change._

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

**3. SSL certificate verification globally disabled in `bot.py`**
Swap the blanket `ssl._create_unverified_context` for the `_ssl_context()`
pattern already in `fetch_prices.py`. Still open.

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
**7. Desk verdict on watchlist is tooltip-only** — consider an expandable
row so verdicts are readable without hovering (mobile especially).

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

1. **Backfill via signal-bot forwarding** — operator task, no code: forward
   the existing @aleabitoreddit alert-bot history into the ingest bot
   (GUIDE.md §9). Priority: most recent months first.
2. **First real `/weekly-review` cycle** (next week) — proves the loop and
   produces the first stance *changes*, which is where the value is.
3. **`start_bot.sh`** + **SSL fix in `bot.py`** (issues 1 & 3).
4. **List-post mention weighting** in `scorer.py` (issue 4) — makes tiers
   trustworthy enough to stop second-guessing counts.
5. ~~**Telethon watcher (`ingest/watcher.py`)**~~ — ✅ **done 2026-07-30**, but
   built against **X directly** rather than the signal-bot chats, which turned
   out to be unnecessary: the public logged-out profile page renders fine in a
   headless browser, so discovery costs nothing and needs no account. See
   `docs/WATCHER.md`. Approve-first by design — posts queue into
   `store/pending_posts.json` and reach `theses.json` only on a Telegram
   button tap. **Tweet discovery is no longer manual.**
6. **Radar-tier triage, gradually** — `review.py classify` a few per week;
   no urgency since Radar is hidden by default.
7. **Watchlist verdict expandable rows** (issue 7).
8. **View extraction, remaining posts** — 44 radar/unsorted-only posts left
   unread after the Core/Watch pass (2026-08-19); re-run
   `extract_views.py --emit` without `--core-only` whenever there's time, or
   whenever a name's tier changes and its back-catalog becomes worth reading.
9. **Wire `views[]` into the UI** — `views.summarize_ticker_views()` already
   returns the per-ticker argument feed, newest first; nothing renders it yet.
   Natural fit: a ticker card section that reads "what he's said about this
   name" instead of a mention count.
10. **Decide on Step 1b (scoring) and Step 2 (SEC EDGAR fundamentals)** — both
    spec'd and ready in `PROJECT.md`, neither started. Step 1b needs a
    deliberate before/after review since it moves real rankings; Step 2 is
    free (`data.sec.gov`, no key) and covers ~40 of 49 Core+Watch names.

---

## Discussed but not yet built

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
- **"Since mention" receipts** (from reviewing semiconstocks.com — the Serenity
  tracker of the same analyst): stamp a baseline price in `bot.py` at
  thesis-capture time so future theses can show % return since the call.
  Impossible retroactively — the sooner it lands, the sooner receipts accrue.
- **Rotation arc**: a "where the analyst's attention is moving" phase timeline
  in the Synthesis chapter, driven by the Brain's mention-trend data.

- **Self-serve Brain/verdict refresh via API key** — `synthesize.py` already
  supports it; verdicts could get the same `call_fn` treatment for a
  fully-unattended weekly cron once a paid key exists.
- **Make.com auto-forward** — superseded in spirit by the Telethon watcher
  plan (item 5 above); keep as fallback.
- **Real price history sparklines** — replace the synthetic "Trend (sample)"
  lines once `fetch_prices.py` stores dailies.

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
