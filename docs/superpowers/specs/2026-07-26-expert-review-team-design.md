# Expert Review Team — Design Spec ("Practice 8.5")

_Written 2026-07-26. Status: **Phase 1 shipped 2026-07-26; Phases 2–5 not yet
built.** The "Problem" section below describes the state before Phase 1 and is
kept as the historical record — the scoring formula it quotes is no longer what
`scorer.py` computes. Plan:
`docs/superpowers/plans/2026-07-26-direction-aware-scoring.md`._

**What shipped (Phase 1):** the `direction` field and its neutral default,
direction-aware signed scoring, the research-source asymmetry, the retired
conviction multiplier, and a `data.js` completeness + source-freshness guard.

**What has not (Phases 2–5):** the three review seats, `claims.json` and claim
judging, the performance-page split, hit-rate weighting, and the scheduled run.

## Problem

The desk is downstream of exactly one person. All 258 theses in
`ingest/store/theses.json` carry `source: "x"` and `author: "aleabitoreddit"`.
That analyst is structurally long AI infrastructure and, by his own post on
2026-07-22, down 49.4% on the month.

Three consequences follow, and none of them can be fixed by analysing the
existing data more carefully:

1. **No bear case exists anywhere in the store.** Nothing in the tool ever
   argues the other side.
2. **Nothing outside the analyst's field of view can ever enter.** Power and
   grid constraints, transformer lead times, neocloud debt loads, export
   controls, depreciation schedules — none of it is reachable.
3. **Rank measures volume, not accuracy.** `scorer.py` computes
   `score = Σ(recency × focus) × (1 + CONVICTION_WEIGHT × conviction_hits)`.
   There is no price term, no outcome term, and no direction term. A name the
   analyst defends while it falls gets promoted, because defending it means
   posting about it more.

The desk's own record is consistent with this. Both stamped calls are open and
losing to a passive index buy: SIVE −33.8% against SMH −8.2% (−25.6pp), SNDK
−11.0% against SMH −5.0% (−6.0pp).

This spec adds a second, checked source of information and gives the system a
memory of who has been right.

## Scope

**In scope:** a three-seat expert review that runs before each weekly review;
outside research entering the thesis feed as a second source; a direction
signal on theses; a direction-aware scorer; a claims ledger that records dated
predictions and judges them later; a self-check guard on data generation.

**Out of scope (deliberately):** live/continuous monitoring and daily
kill-trigger checks (that is "Practice 9.0", a later decision); any change to
how the operator captures posts; any new app page; any framework, build step,
or `fetch()` of local files.

**Unchanged on the operator's side:** he forwards posts to the Telegram bot
exactly as today, and runs one command before the weekly review instead of
zero. That is the entire change to his habit.

## The three seats

Each seat is an agent with a distinct mandate. They are differentiated by the
**question they must answer**, not by an information diet.

| Seat | Mandate — the question it must answer |
|---|---|
| `semi-expert` | Is the technical claim true? Ramp timelines, process and packaging limits, yields, qualification status, capacity assumptions. |
| `fundamental` | Do the numbers work? Revenue maths, dilution, margins, customer concentration, valuation against peers. |
| `pm` | Is this a good bet at this price? What is already priced in, what the downside is, what would force an exit. |

### Honest limitation, recorded on purpose

Naming a seat `semi-expert` does not create semiconductor expertise. Each seat
is the same model with a different instruction and web access. The gains are
narrower than the labels imply, and are:

1. Three separate passes, so three different questions genuinely get asked
   instead of one blended question that skips the hard parts.
2. Forced outside research, so new facts enter the system. **This is the real
   prize.**
3. A written disagreement the operator can read and judge.

The output must never be presented as though a domain engineer reviewed it.

### Seat output shape

Each seat returns at most **150 words** in this fixed structure. Prose beyond
the `finding` field is not accepted.

```json
{
  "seat": "semi-expert",
  "ticker": "SIVE",
  "direction": "bear",
  "finding": "≤60 words, one claim, no hedging",
  "basis": ["https://…", "https://…"],
  "verification": "verified",
  "confidence": "high",
  "claims": [
    { "claim": "…", "judgeBy": "2027-03-31", "testableBy": "…" }
  ]
}
```

`claims` holds 0–2 entries. `confidence` is one of `high | medium | low`.

## Verification rule (the central guard against fabrication)

> A finding with an empty `basis` is marked `verification: "unverified"` and
> **may not set `direction` to `bull` or `bear`.** Its direction is forced to
> `neutral`.

Because a `neutral` direction carries a scoring weight of exactly 1.0,
unverified findings are **visible but inert**. They appear in the brief, the
operator can read them, and they cannot move a single score.

`basis` entries must be primary or near-primary: SEC filings, earnings-call
transcripts, company IR material, exchange notices, or established industry
data providers (TrendForce, SEMI, Counterpoint). Content aggregators and
SEO-farm summaries do not qualify.

## Data shapes

### 1. `theses.json` — two new fields

```json
{
  "direction": "bull" | "bear" | "neutral",
  "verification": "verified" | "unverified" | null
}
```

Defaults for the 258 existing records: `direction: "neutral"`,
`verification: null`. Existing fields are untouched.

Analyst and research theses are distinguished by the **existing** `source`
field — `"x"` for forwarded posts, `"research"` for seat findings — with
`author` naming the producing seat and `sourceUrl` carrying the strongest
entry in `basis`. No separate classifier field is introduced.

### 2. `claims.json` — new file, the system's memory

```json
{
  "meta": { "schemaVersion": 1, "updatedAt": "…", "disclaimer": "…" },
  "claims": [
    {
      "id": "cl_AAOI_2026-07-22_01",
      "source": "analyst" | "desk" | "semi-expert" | "fundamental" | "pm",
      "ticker": "AAOI",
      "claim": "AAOI reaches $1.4B quarterly revenue",
      "madeAt": "2026-07-22",
      "judgeBy": "2027-10-31",
      "testableBy": "Reported quarterly revenue ≥ $1.4B on or before judgeBy",
      "thesisId": "h_…",
      "status": "open" | "correct" | "wrong" | "unfalsifiable",
      "judgedAt": null,
      "evidence": null
    }
  ]
}
```

`ticker` may be `null` for macro claims. `unfalsifiable` is a first-class
outcome — a claim like "we're close to the bottom" cannot be judged, and a
source whose claims are mostly unfalsifiable is telling the operator something
worth measuring.

**Hit rate** = `correct / (correct + wrong)`. `open` and `unfalsifiable` are
excluded from the denominator, and the **unfalsifiable share is reported
alongside** the hit rate so a source cannot score well by being vague.

### 3. `calls.json` — one new field

Add `"source": "desk" | "analyst"` to each call, defaulting existing records to
`"desk"`. Everything else about the file, including the forward-only rule,
stays as it is.

## Scorer changes (`ingest/scorer.py`)

### Direction weighting

Weight depends on **both** direction and source:

```
weight(thesis):
    if thesis.direction == "bear":                 return -1.0
    if thesis.source    == "research":             return  0.0
    return 1.0                                     # analyst bull / neutral

attention = Σ(recency × focus)                     # every thesis, unsigned
net       = Σ(recency × focus × weight)
score     = max(net, 0.0)
```

Two deliberate asymmetries:

- **`neutral` weighs 1.0**, so the direction migration on its own is
  score-neutral: 258 theses defaulting to `neutral` produce exactly today's
  numbers. The **only** thing that re-ranks in Phase 1 is the retirement of
  the conviction multiplier, below. Keeping those two effects separable
  matters — if the rankings shift, there is exactly one cause to point at.
- **Research findings can subtract but never add.** A bear finding corrects a
  score; a bull finding is recorded, displayed and citable but contributes
  0.0. Without this, the same model that writes the verdict could agree with
  itself three times and inflate the rank — a self-reinforcing loop. The team
  exists to catch what the analyst missed, not to second the motion. This rule
  is revisitable once hit-rate weighting is live and the seats have a measured
  track record.

The floor at zero keeps `assign_tiers` working on its current assumptions; a
name driven negative by bear findings sits at zero while `net` retains the
true value.

The priority record gains four fields for the UI:

```json
{ "attention": 0.0, "net": 0.0, "bullMentions": 0, "bearMentions": 0 }
```

so a ticker card can render "93 mentions · 3 against".

### Conviction multiplier — RETIRED (signed off 2026-07-26)

`CONVICTION_WEIGHT` is `0.5` per hit, and `conviction` is assigned by keyword
match in `parser.py` against phrases such as "top pick", "high conviction",
"core position" and "all in". It fires on 17 of 258 posts, and its effect is
large — SIVE's 10 hits produce a 6× multiplier.

Removing it is a **significant one-time re-rank, not a cleanup**:

| Ticker | Now | Without multiplier | Hits | Rank now → new |
|---|---|---|---|---|
| SIVE | 91.11 | 15.19 | 10 | 1 → 1 |
| LITE | 34.00 | 9.72 | 5 | 2 → 2 |
| META | 9.99 | 6.66 | 1 | 9 → 5 |
| AMD | 6.41 | 6.41 | 0 | 15 → 6 |
| GFS | 10.25 | 3.42 | 4 | 7 → 16 |

Leaves the top 15: GFS, JBL, MRVL, POET. Enters: AXTI, CCXI, COHR, SNDK.

**Decision: retired.** A keyword match on rhetoric should not multiply a score
sixfold, and the direction signal plus later hit-rate weighting are strictly
better instruments. The re-rank is best read as a correction — the four
departing names were riding conviction phrasing rather than evidence.

Implementation: set `CONVICTION_WEIGHT = 0.0` rather than deleting the code
path, so the decision is reversible by changing one constant. The re-rank
lands the moment Phase 1 ships, and the operator should expect his top 15 to
look different that week.

**The `conviction` field itself is kept as captured data.** Only its role as a
score multiplier is retired. This decision is reversible by restoring one
constant.

### Hit-rate weighting (deferred to Phase 4)

```
source_weight = clamp(0.5 + hit_rate, 0.5, 1.5)
```

Applied per thesis by its author. **Gated: a source keeps a weight of exactly
1.0 until it has at least 20 judged claims.** This prevents an early run of
three lucky calls from reweighting the whole book. Expect three to six months
before this does anything; everything else in the spec works from week one.

## Schedule

The review runs unattended the night before the operator's weekly review, via
the scheduled-task capability, and falls back to a manual `/pre-review`
command.

**Coverage per run** is capped at 12 names, selected in this priority order
until the cap is reached:

1. Any name whose stance changed at the last review.
2. Any name with 3 or more new theses since the last review.
3. The remaining highest-scoring names, descending.

Running all 28 Core names weekly is explicitly rejected — it is roughly three
times the cost for names where no decision is pending. When the cap truncates
the list, the run logs which names were dropped, so silent under-coverage
never reads as full coverage.

## Self-check guard

The spec adds moving parts, and the failure mode is already proven. On
2026-07-26 a `bot.py` process running since 30 June held a stale module in
memory and silently rewrote `data.js` without `glossary`, `desk`, `memos`,
`vault`, `calls` or `benchmarkQuote` on every ingest — breaking the memo
reader, vault, glossary and performance page for four days with no signal.

`generate_data_js.py` gains a post-assembly assertion: every expected
top-level key must be present, and keys backed by a non-empty store file must
be non-empty. A failure raises loudly rather than writing a truncated file.

## App changes

- **`performance.html`** splits into two sections: **Calls** (position actions,
  return versus SMH — as today) and **Claims** (predictions, hit rate and
  unfalsifiable share, grouped by source). No new page.
- **Ticker detail** shows the mention split and any research findings against
  the name, rendered through the existing `AIE.makeThesisCard`.
- **Brain digests** carry both sides; `synthesize.py` prompt updated to require
  a bear paragraph where bear theses exist.
- Nav gating is already resolved: `MIN_CALLS_FOR_NAV` was lowered from 3 to 1
  on 2026-07-26, so Performance is live.

## Testing

New cases in `ingest/tests`, alongside the existing 112 which must continue to
pass:

- a `bear` thesis lowers a score; a `neutral` thesis reproduces today's value
- migration: absent `direction` reads as `neutral`; with `CONVICTION_WEIGHT`
  held at its old `0.5`, re-scoring the current 258 theses returns
  byte-identical priorities — proving the direction change alone is inert
- conviction retirement: unit-tested against synthetic fixtures — a `high`
  conviction thesis scores identically to a `normal` one, while
  `convictionHits` is still counted and still drives tiers. The real-store
  re-rank (SIVE 91.11 → 14.99; GFS/JBL/MRVL/POET out, AXTI/CCXI/COHR/SNDK in)
  is a one-time manual verification, not a permanent assertion — the store
  grows weekly and pinned counts would rot
- an `unverified` finding cannot set a non-neutral direction
- a `bull` thesis with `source: "research"` contributes 0.0, while the same
  thesis with `source: "x"` contributes its full weight
- `score` floors at zero while `net` retains the negative value
- hit-rate weighting stays at 1.0 below the 20-claim gate
- claim judging moves `open` to `correct`/`wrong` and recomputes hit rate
- `generate_data_js` raises when an expected top-level key is missing

## Phasing

| Phase | Content | Depends on |
|---|---|---|
| 1 | Direction fields, migration, direction-aware scorer, tests, self-check guard | — |
| 2 | The three seats, verification rule, research theses entering the feed | 1 |
| 3 | `claims.json`, claim extraction, performance page split | 2 |
| 4 | Hit-rate weighting switched on | 3, plus ≥20 judged claims per source |
| 5 | Scheduled overnight run | 2 |

Phase 1 is useful on its own and changes nothing the operator sees except the
re-rank. Phase 4 cannot be rushed — it is gated on real judged outcomes.

## Decisions already taken

- House view on contested premises: write both sides, then take an explicit
  view. Do not hedge or average.
- The sticky act/accumulate holdover rule stays exactly as designed.
- All 258 existing theses migrate to `neutral`. No retroactive rewriting.
- Every seat output is capped at 150 words; the synthesis is one page.
- Practice 9.0 (daily kill-trigger monitoring) is deferred, and is only worth
  building if the operator begins acting on the tool.
- **The conviction multiplier is retired** (operator sign-off 2026-07-26),
  accepting the one-time re-rank of four names in and four out of the top 15.
  Implemented as `CONVICTION_WEIGHT = 0.0` so it stays reversible.

No open questions remain. This design is approved and ready for
`writing-plans`.

---

_Not investment advice. This is a personal research tool._
