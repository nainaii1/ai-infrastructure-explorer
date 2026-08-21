# PROJECT.md — from mention-counting to reading what he actually said

**Opened 19 Aug 2026.** Active plan. When a step ships, move its detail to
`docs/ROADMAP.md` and leave the one-line outcome here.

---

## The problem

The desk reduces a 700-character argument to `+1 mention`. Every quantitative
surface in the app — tiers, priority score, the watchlist ordering, all five
chart mockups — is built on *how often* the analyst names a ticker. That is a
measure of his posting behaviour, not of the company.

Two things were measured on the live store and both say the same thing:

1. **Mentions do not predict returns.** Spearman ρ = 0.17 (t = 1.43, n = 72)
   between analyst mentions and 1-month return vs SMH. No relationship.
2. **Mentions cannot express direction.** All 331 of his posts carry no
   `direction`. Every `bullMentions` / `bearMentions` figure in the system today
   comes from the desk's own research seats, not from him.

Meanwhile the thing actually worth having is sitting unread in the store:

| His 354 posts | |
|---|---|
| median length | 721 chars (p90 1,786, max 4,000) |
| contain revenue / $ figures | 54% |
| contain capacity / bottleneck reasoning | 54% |
| contain timing (quarter / year) | 53% |
| contain competitive positioning | 39% |
| contain valuation | 27% |

**The operator follows this analyst because he explains *why*, not because he
posts often.** The system throws that away.

### The specific failure

One real post (27 Jun 2026) names 17 tickers. The counter credits all 17
equally. What he actually wrote:

- LITE / AXTI / AAOI — "ran up too much", expects range-bound chop
- AEHR — "more priced in after the 100% rally"
- Sivers / ASE — "a lot of re-rating to do"

Three different stances in one post. A per-post `direction` field cannot
represent this; the view is **per (post, ticker)**, not per post.

---

## The plan

Four steps, in order. Each is independently useful; none depends on a paid API.

### Step 1 — Extract per-ticker views from his posts *(in progress)*

Turn `SIVE: 113 mentions` into `SIVE — bull, CPO re-rating, $1B→$10B, H2 2027`.

Adds to each analyst thesis:

```
views: [ { ticker, direction, why, numbers?, horizon? } ]
viewsExtractedAt: <iso>          // set = processed, so re-runs are idempotent
```

- `direction` ∈ `bull | bear | neutral`. Unreadable → `neutral` (inert), per
  scorer invariant 3.
- `ticker` is **pinned to the post's own `tickers[]`** and the live universe.
  A model-invented symbol is dropped, never added (invariant 5).
- `why` / `numbers` / `horizon` are short strings, length-capped.

Uses data already in the store. No new dependency, no key, no cost.

**Deliberately NOT in this step:** `scorer.py` is untouched. Views are additive
and move no score, tier or ranking. Wiring direction into scoring is Step 1b, a
separate decision — see "Scoring impact" below.

### Step 2 — Fundamentals from SEC EDGAR

`data.sec.gov` XBRL: **free, no API key, no daily limit**, official filings,
10 req/sec, requires a User-Agent with a contact email.

Verified live on 19 Aug 2026:
- `NVDA` → revenue by fiscal year from 10-Ks ✓
- `TSM` → works as a foreign private issuer (20-F) under the `ifrs-full`
  taxonomy, 334 concepts including `Revenue` ✓

So US filers **and** US-listed foreign issuers are covered: roughly **40 of the
49 Core + Watch names**, including TSM, ASML, ARM, NOK, GFS.

Genuine gaps — no US listing, need a manual quarterly pass (~7 names):
`SIVE` (Stockholm), `IQE` (LSE), `XFAB` (Brussels), `LPK.DE` (XETRA),
`SOI.PA` (Paris), `000660.KS` (Korea), `CATL` (Shenzhen). `CXMT` is private.

Known wrinkle: the revenue concept name varies — `Revenues`,
`RevenueFromContractWithCustomerExcludingAssessedTax`, IFRS `Revenue` — so the
extractor must try several tags rather than assume one.

*Note:* `www.sec.gov` (the ticker→CIK map) rate-limits harder than
`data.sec.gov`. Cache the CIK map locally; don't fetch it per run.

### Step 3 — `aiExposure`, the field no API sells

Per name, the operator's own judgement:

- `aiExposure` — % of revenue tied to AI datacenter buildout
- `contentPerRack` — $ content per GPU rack / per 100k GPUs
- `revenueInflection` — the quarter the AI revenue actually lands

Revenue is commodity data. *"How much of this company is genuinely AI versus
legacy telecom"* is the question the supply-chain map implies on every page and
has never answered with a number. This is the instrument.

### Step 4 — Re-point the charts at real variables

Chart C (scatter) keeps its shape; its x-axis changes from *mentions* to
*AI exposure* or *revenue growth*. High exposure sitting bottom-left
(underperforming) becomes a hunting ground rather than a coincidence.

The five existing mockups (`mockup-charts*.html`) stay parked until Steps 1–3
land. They were the best available when mention-count was the only numeric
field in the store.

---

## Scoring impact (read before Step 1b)

`scorer._direction_weight`: `bull` = +1.0, `neutral` = +1.0, `bear` = −1.0,
unreadable = 0.0. Absent reads as `neutral`.

Therefore, if views are ever wired into scoring:
- posts extracted **bull** or **neutral** → no score change
- posts extracted **bear** → a 2.0 swing per mention

Only bear findings move anything, which is the correct asymmetry — but it is a
real change to live rankings and must be made deliberately, with the before/after
counted, not as a side effect of Step 1.

`direction` is also per-thesis in the scorer, while a view is per-ticker. A post
that is bull on one name and bear on another cannot be expressed by the current
field. Step 1b has to resolve that before any wiring.

---

## Invariants this work must not regress

From `docs/EXECUTION-EXPERT-REVIEW.md`:

- **#6 — purity.** `views.py` takes an injected `call_fn(system, user)`. No
  network, no file I/O, no SDK import inside the module.
- **#5 — untrusted input.** Posts are third-party social media. Delimit the
  text, clip to `MAX_THESIS_CHARS`, instruct the model to ignore instructions
  inside it, and pin tickers from the caller so an injection is inert.
- **#3 — fail inert.** An unreadable direction becomes `neutral`, never a vote.
- **#7 — no test writes under `ingest/store/`.** Monkeypatch to a temp dir.
- **#10 — research is not his attention.** Only `source: "x"` posts get views.

---

## Status

| Step | State |
|---|---|
| 1 — per-ticker view extraction | **done for Core/Watch** — 316 of 356 posts read, 0 Core/Watch pending (and now honestly 0, see Step 5) |
| 1b — wire direction into scoring | not started, needs a decision |
| 2 — SEC EDGAR fundamentals | **shipped 21 Aug 2026** — 37 of 46 Core+Watch, on the card and the watchlist row |
| 3 — `aiExposure` judgement fields | not started — **unblocked**, Step 2 is in |
| 4 — re-point charts | blocked on 3 only |
| 4a — surface `views[]` in the app | **shipped 20 Aug 2026** — see below |
| 4b — density as a sortable watchlist column | **shipped 20 Aug 2026** — see below |
| 4c — plain label + bear flag on the column | **shipped 20 Aug 2026** — see below |
| 5 — close the ticker-alias gap | **shipped 21 Aug 2026** — see below |

### Step 4a — what shipped (20 Aug 2026)

The 1,179 extracted views were riding inside `data.js` and nothing read them.
They now render on the ticker dossier card in `desk.html`, above Claude's
verdict — his evidence first, then the desk's call on it.

- `AIE.viewsForTicker(sym)` in `shared/common.js` — the JS mirror of
  `views.summarize_ticker_views()`: same `source: "x"` filter (invariant 10),
  same newest-first order. Verified to return identical counts to the Python
  on SIVE (112) and IREN (16).
- `AIE.viewStats(rows)` — bull / bear / bare split. Anything not literally
  `bull` or `bear` counts as a bare mention (invariant 3, fail inert).
- `AIE.makeViewsBlock(sym)` — the `.aie-views` renderer. Shows the arguments
  newest-first, capped at 6, each with its direction badge, date, `numbers`,
  `horizon` and a link to the post. Returns `null` for a name he has never
  named, so the block simply does not appear (GEV, the desk-research names).
- **Signal density in the header** — `103 / 112 argued`. This is the number the
  whole document is about, and it is now on the card.
- **Zero-argued names show their references instead**, because "6 mentions,
  0 arguments" only lands when you can see what a bare mention looks like.
  43 tracked names read `0 / n`; ASML is `0 / 2`.
- New `--sem-bear-bg/-fg` token pair (5.74:1), registered in
  `test_contrast.py` so the AA guard covers it.

Read live off `data.js`, on the desk page:

| | argued / mentioned | |
|---|---|---|
| SIVE | 103 / 112 | his real conviction name |
| AAOI | 57 / 81 | |
| IREN | 9 / 16 | 4 bull **and** 5 bear on one card — the thing a per-post `direction` cannot express |
| SPCX | 5 / 24 | |
| TSLA | 4 / 21 | recorded `pass` 2026-08-12 for exactly this reason |
| **NVDA** | **11 / 71** | named constantly, argued rarely — the ranking-noise finding, now visible |
| GEV | no block | he has never named it; the card says nothing rather than implying silence is a view |

Nothing in `ingest/` changed. No score, tier or ranking moved — the block is
read-only over data that was already generated.

### Step 4b — what shipped (20 Aug 2026)

4a put the block on the chain-tab tile card only. That is three clicks and a
tab switch from the default view, and the watchlist row detail is a *separate*
renderer (`makeRowDetailRow`), so in practice the feature was invisible where
the operator actually works. Two fixes:

1. **The block now renders in the watchlist row detail**, directly under "My
   call" — his case and the desk's call adjacent, capped at 3 arguments so a
   table row stays scannable (the card keeps 6).
2. **`Argued` is now a sortable watchlist column**, so the number needs no
   click at all and the whole list can be ranked by it. This is the first time
   any surface in the app ranks on something other than posting frequency.

`AIE.viewDensity(sym)` backs the column: one pass over all theses, memoised on
the theses array identity, because calling `viewsForTicker` per row would
rescan the corpus 135 times per render.

Sorting is on the **count** of arguments, not the ratio — a name argued once
out of one mention is 100% dense and says nothing, while SIVE at 103 is the
signal. A name he has never mentioned renders `—` and sorts last in both
directions rather than tying with a genuine zero.

Sorted descending, the Core tier now reads:
`SIVE 103/112 · AAOI 57/81 · LITE 43/79 · XFAB 29/29 · CCXI 25/30 · MU 25/32`.
Ascending surfaces the opposite end — `NOK 0/5, AAPL 2/11, AVGO 2/13,
GFS 3/23, MSFT 3/11` — the names he name-drops and never argues.
**XFAB at 29/29 is the case mention-count can never find:** every single time
he has named it, he made an argument.

### Step 4c — what shipped (20 Aug 2026)

Operator feedback on 4b, both points fair:

1. **"Argued" was jargon** — and `CLAUDE.md`'s own v9 voice rule bans jargon in
   column headers. Renamed **`His case`** (the `data-key` stays `argued`; it is
   an internal id, not a label).
2. **"good or bad, and on what?"** — the column counted how much he said and
   showed nothing about which way he said it, so a name he is net NEGATIVE on
   looked identical to one he is bullish on.

Measured before deciding: of 34 Core names, **28 are 100% bull when argued**;
only 5 carry any bear view at all — `IREN 4 bull / 5 bear`, `TSM 8/1`,
`TSLA 3/1`, `MTSI 3/1`, `AVGO 1/1`. **IREN is the only Core name he is net
negative on.**

So direction renders as an **exception flag, not a split**: a red `N bear` chip
on the 5, nothing on the other 29. Marking "all bull" on 28 rows would only
teach the eye to skip the column. The word `bear`, never an arrow — the sort
indicators are already `▲`/`▼` and a second triangle would read as one.

One bug this surfaced and fixed: the watchlist panel caps at 3 views,
newest-first, and IREN's three newest are bull — so the column flagged
"5 bear" and the panel it opened showed three BULL badges. `makeViewsBlock`
now swaps the oldest shown row for his most recent bear view whenever the cap
would hide the disagreement. It cannot break date order: a bear missing from
the slice is by definition older than every row in it.

### Step 1 — what shipped (19 Aug 2026)

- `ingest/views.py` — pure module (invariant 6): prompt builder, validator,
  `extract_views`, `summarize_ticker_views`. No network, no I/O, injected
  `call_fn`.
- `ingest/extract_views.py` — the runner. API path if a key exists; otherwise
  `--emit` / `--apply` for the in-session Claude Code path. **Both routes run
  the same validation**, so the manual route cannot bypass the firewall.
- `ingest/tests/test_views.py` — 34 tests. Suite total 386, green.

**24 batches, done.** 312 of 356 posts read → **1,179 views, 581 bull / 580 neutral / 18 bear**,
across **114 unique tickers**. The 15 posts still unread touch only `unsorted`/radar-tier
names outside Core+Watch — extraction stops here for this pass; re-run
`--emit --core-only` (drop the flag to cover the rest) whenever tiers shift or
new posts land.

**Signal density, final numbers.** SIVE 103 bull / 112 views (92%) — genuinely
his highest-conviction name, not just his most-mentioned. AAOI 57/81 (70%).
LITE 43/79 (54%). By contrast NVDA appears constantly across the corpus but
is argued directly only a handful of times — almost always present as
context (a backer, a customer, a counterparty), exactly the pattern flagged
after the first 38 posts.

**18 bear views, spread thin, each one specific:**
IREN ×5 (dilution, ATM offerings, GPU pivot from colo — the most-repeated
bear thesis in the corpus), SPCX ×2 (a mocked aggressive PT; a criticized
pre-IPO valuation hike), then one bear each on TSLA, TSM, AVGO, LWLG, HIMX,
MTSI, CBRS, BOT, CRWV, UBER, PYPL — each tied to a distinct, specific
concern (dilution, a real supply disruption, a valuation mismatch, an export
exposure), never a generic "market's down" call. Confirms he is not
long-only in substance even though the vast majority of what he posts is
bullish — bear cases exist, they're just rarer and more targeted than bull
ones.

**What this replaces.** Every ticker's page can now show *why* he's bullish or
skeptical, dated and sourced, instead of a bare mention count. `summarize_ticker_views()`
in `views.py` returns exactly that feed, newest first, ready for the UI.

### Step 5 — what shipped (21 Aug 2026)

Known issue 3 closed, plus the two further instances of the same bug it was
hiding (see the Known issues section above for the mechanics).

**Recovered 29 views across 22 posts**, none of which the old scope could
express. Every Core/Watch name's view total now equals its `analystMentions`
exactly — the density denominator and the mention badge finally agree.

| name | before | after |
|---|---|---|
| `000660.KS` (SK Hynix) | **no block at all** — read as never mentioned | `4 / 6` |
| `LPK.DE` | 5 / 11 | `10 / 16` |
| `SOI.PA` | 7 / 9 | `11 / 13` |
| `IQE` | 10 / 13 | `11 / 14` |
| `CXMT` | 0 / 5 | `1 / 6`, and the 1 is a **bear** |
| `SIVE` | 103 / 112 | `105 / 115` |

SK Hynix is the one that matters: a Watch-tier name in the memory bottleneck
he argues constantly, and the app showed `—` for it, meaning "he has never
mentioned this". It now carries four bull views.

Two new bears, both specific: **CXMT** (mocks the day-one IPO valuation,
+469.98% to ~$487B) and nothing else — the LPK glass-substrate delay posts
were read **neutral**, because he flags the slip while holding the structural
view and bought the drop five days later. Direction records HIS stance, not
the sentiment of the news he relays, which is how the corpus already reads a
factually-relayed negative.

`--status` gains an `aliasGap` counter so this class of gap is visible rather
than needing to be rediscovered.

### What the first 38 posts already show

**Only 40% of his mentions carry an argument.** Across those posts: 137 mentions,
55 of them an actual case. The other 60% are references — a backer, a customer,
a valuation comparator, a name in a list of feed noise.

Ranking by mentions versus by arguments is a different book:

| by mentions (what the desk ranks on today) | | by arguments |
|---|---|---|
| AAOI 14 → 5 argued | | LITE 6 |
| LITE 14 → 6 argued | | AAOI 5 |
| **NVDA 8 → 1 argued** | | SIVE 5 |
| SIVE 7 → 5 argued | | **SMCI 4 (of 4 mentions)** |
| **SPCX 6 → 0 argued** | | **SNDK 4 (of 4 mentions)** |

- **NVDA** is his third most-mentioned name and he argued it once. The rest are
  references — Nvidia as a backer, a customer, a counterparty.
- **SPCX**: six mentions, zero arguments. Pure ranking noise.
- **SMCI and SNDK**: every single mention is a case. Perfect signal density,
  invisible to a counter.
- **18 of 43 names with views have never been argued at all.**

**0 bear so far is an ordering artifact, not a property of the source.** The
extraction runs newest-first, and 79 of the 326 unread posts contain bearish
language — clustered in late June ("*trimming some longs*", "*$AXTI... more
priced in now*", "*personally not adding more*"). Bears will appear on the way
back; do not read the current bull/neutral split as final.

Verified along the way:
- **Scores and tiers unmoved.** 0 tier changes. Score drift is time decay in
  `compute_priorities`, not this work — regenerating with *no* data edit at all
  moves 35 scores in the 4th decimal.
- **Firewall holds on live data.** A hostile answer naming NVDA/TSLA/FAKE
  against a post that mentions only AAOI/LITE: 3 of 4 dropped, none remapped.
- **`bullMentions` still research-only** (SIVE: 0 bull / 11 bear / 12 research),
  confirming views feed nothing numeric yet.

### Known issues found by doing the work

1. **The ticker parser has false positives.** A post citing "Elazr GM at their
   investor conference" tagged `$GM` (General Motors) — "GM" was a job title.
   The extraction omitted it rather than inventing a neutral view, but the bad
   tag is still in that thesis's `tickers[]` and still counts as a mention.
   Worth a pass over short all-caps symbols that double as English words
   (GM, ON, ARM, ALL, KEY).
2. **`tier` is not in `tickers.json`** — it is computed at generate time by
   `scorer.assign_tiers`. Any tool filtering on `t["tier"]` from the store
   silently matches nothing. `extract_views._core_symbols` now derives it and
   refuses to run on an empty set rather than reporting a successful pass that
   read zero posts.
3. **Ticker aliases never get a view.** ~~Open~~ **FIXED 21 Aug 2026.**
   `mentions` was counted *after* `scorer.canonicalize_theses` folded
   `base.json` `tickerAliases` in, while extraction pinned to the post's raw
   `tickers[]` — so a `$SIVEF` post counted as a SIVE mention and yielded zero
   views. `views._post_ticker_scope` now canonicalizes through an **injected**
   alias map (`views.py` stays pure — `extract_views._aliases()` does the I/O),
   and the prompt gains a note line telling the model the post spells SIVE as
   `$SIVEF`. 17 posts re-read, 26 views recovered. The firewall is unchanged:
   the map rewrites symbols the post already contains, it never adds one, and
   a test asserts that.

   **Two more instances of the same bug, found by fixing it:**
   - `_pending(core_only=True)` intersected raw `tickers[]` with the core set,
     so a post whose only symbol was `$LPK` never matched `LPK.DE`.
   - `_core_symbols` called `canonicalize_theses(theses)` with **no maps**,
     computing a different tier table than the app: `000660.KS` read radar
     (really watch), `SOI.PA` read watch (really core), `SPCX` read core
     (really radar — it is a `themeTag`, not a ticker).

   Together these made `--status` report **"0 Core/Watch pending"** while four
   Core/Watch posts were unread. It now reports honestly, and both are covered
   by regression tests.

4. **The extraction sometimes omits a bare mention instead of recording it
   neutral.** Found while reconciling density against `analystMentions`: five
   already-extracted posts had fewer views than tickers in scope. Nine were
   genuine references the pass simply skipped (six names listed in a Morgan
   Stanley CPO note, an X-Fab validator mention of NVDA, a name he "passed on",
   a laser name in a grouped sentence) and were filled in as neutral. **The
   tenth was correct to omit:** `$GM` in "Elazr GM at their investor
   conference" — known issue 1, still live in that post's `tickers[]`.
   So the omissions cannot be auto-filled; each needs an eye on the post. All
   Core/Watch names now reconcile exactly: views total == `analystMentions`.

5. **JBL contradicts the momentum read.** Mockup E flagged JBL as a stale
   `accumulate` because mentions fell 16 → 4. But the 17 Aug post lists JBL
   among names he likes, on a 1.6T LRO margin argument. The count said "gone
   quiet"; the text says otherwise. This is the whole thesis of this document in
   one name.

---

## Where this is referenced elsewhere

This file is the live tracker — the others point here rather than duplicate
the numbers, which drift every batch:

- `CLAUDE.md` "Current status" has a one-paragraph summary + pointer here.
- `docs/ROADMAP.md` has a changelog entry (search "Step 1 of the
  mention-to-argument rework") + three "Next up" build-order items (§8-10).
- `docs/GUIDE.md` §10 is the actual operator how-to for
  `ingest/extract_views.py` — `--status` / `--emit` / `--apply`, the
  answers-file shape, and what a nonzero "dropped" count means.

If those drift from this file, trust this file and fix them — same rule
`CLAUDE.md` states for itself.

## Next session should start by

1. Reading `python3 ingest/extract_views.py --status` — confirms nothing
   changed underneath since this was written. It now also reports `aliasGap`,
   which must stay 0.
2. Deciding: grind the remaining 11 radar/unsorted posts, start Step 2
   (SEC EDGAR), or open the Step 1b scoring decision. No correctness item is
   open — known issue 3 is closed, and 4 is a data-quality note, not a bug.
3. Steps 1 and 4a are committed (`dca8bf3`, and the follow-up carrying this
   file). The three `mockup-charts*.html` files are still untracked on purpose
   — they are parked until Steps 2–3 give them real variables to plot.
