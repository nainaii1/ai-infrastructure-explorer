---
name: judge-claims
description: Judge the claims whose deadline has arrived — check each against primary sources, record correct/wrong/unfalsifiable, and report hit rate alongside the unfalsifiable share. Use when the operator says "/judge-claims", "judge the claims", "score the predictions", or "who was right".
---

# Judge Claims — the ledger's day of reckoning

`ingest/store/claims.json` records dated, testable predictions from the
analyst, from the desk, and from each of the three seats. This pass checks the
ones whose date has arrived and writes down what actually happened.

Run it whenever `/weekly-review` reports that claims are ripe. Most weeks
nothing is due, and that is fine — this is a date-driven pass, not a weekly one.

## Where the code lives

`ingest/claims.py`, a pure module — no network, no file I/O, no API client. You
supply the research through an injected `call_fn` and do the reading and
writing of the store yourself, exactly like `/pre-review`.

## Procedure

1. **Find what is ripe.** Load `claims.json` and call
   `claims.ripe_claims(ledger, today)` with today's date as `YYYY-MM-DD`. It
   returns the `open` claims whose `judgeBy` has passed, oldest first. An
   unreadable `judgeBy` is deliberately never ripe — it would only invite a
   guess. Passing an unreadable `today` raises.

   If nothing is ripe, say so and stop. Do not go looking for work.

2. **Research each claim.** Take `claim` and `testableBy` and go and find out.
   The bar is the same as the seats': SEC filings, earnings-call transcripts,
   company IR material, exchange notices, or established industry data
   providers. Aggregators and SEO summaries do not qualify.

3. **Judge it.** Build `{"verdict": ..., "basis": [urls], "evidenceNote": "..."}`
   and call `claims.apply_judgement(claim, raw, today)`.

   - `correct` / `wrong` **require** at least one citable URL. Without one the
     claim stays `open` and you try again another day. **This is the correct
     outcome — never invent a citation to close a claim.** You are judging
     predictions this desk made itself, which is exactly when the temptation
     is strongest and the check least likely to happen.
   - `unfalsifiable` needs no citation, because nothing could settle it. Use
     it when the claim turns out not to be checkable in practice, and say why
     in the report.
   - A verdict outside those three leaves the claim open.
   - Judging before `judgeBy`, or re-judging a decided claim, raises. Do not
     work around either: a re-decided claim erases the only record of what the
     desk believed at the time.

4. **Write it back.** `claims.merge_claims(existing, judged)` will NOT
   overwrite what is already in the ledger, so write judged records by
   replacing them in place by `id`, then save `claims.json`, bump
   `base.json` `meta.version` and `meta.lastUpdated`, and regenerate:
   `python3 ingest/generate_data_js.py`.

5. **Report**, in this order:
   - What was judged and how it came out, one line each, with the citation.
   - **Hit rate AND unfalsifiable share per source** — always both, from
     `claims.score_claims(ledger, source=...)`. A hit rate shown alone lets a
     source look good by never saying anything testable.
   - Which claims stayed `open` because you could not cite a source, and what
     you looked at. This is not a failure to hide; it is the honest state.
   - `hitRate` of `None` means nothing has been judged for that source yet.
     Report it as "no judged claims yet", never as 0%.

## Hard rules

- This pass writes ONLY `claims.json`. It never touches `theses.json`,
  `verdicts.json`, `memos.json` or `calls.json`.
- A claim's hit rate moves no score and no tier. Hit-rate weighting is Phase 4
  and is gated on ≥20 judged claims per source. Until then the ledger observes
  and does not vote — do not wire it into `scorer.py`.
- Never hand-edit `data.js` (CLAUDE.md rule 6).
- Small samples lie. With fewer than ~20 judged claims for a source, report the
  raw counts and say the rate is not yet meaningful, rather than presenting a
  percentage that rests on three data points.
- Research support, not investment advice.
