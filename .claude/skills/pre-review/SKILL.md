---
name: pre-review
description: Run the three expert review seats over this week's shortlist before the weekly desk review, writing checked outside research into the thesis feed. Use when the operator says "/pre-review", "run the seats", "pre-review", or "research before the weekly".
---

# Pre-Review — the three expert seats

The desk follows one long-only analyst, so `theses.json` contains no bear case
and nothing outside his field of view. This pass brings in what he missed. Run
it BEFORE `/weekly-review`, so the verdicts are written with both sides on the
table.

## What the seats are

| Seat | The one question it answers |
|---|---|
| `semi-expert` | Is the technical claim true? Ramp timelines, process and packaging limits, yields, qualification status, capacity assumptions. |
| `fundamental` | Do the numbers work? Revenue maths, dilution, margins, customer concentration, valuation against peers. |
| `pm` | Is this a good bet at this price? What is priced in, what the downside is, what would force an exit. |

**A seat is not an expert.** It is this same model with a different instruction
and web access. What the structure buys is three separate passes so three
different questions actually get asked, and forced outside research so new
facts enter the store. Never present a finding as though a domain engineer
reviewed it.

## Where the code lives

Two pure modules, split on 2026-07-27 when one file got too long to read:

- `ingest/seats.py` — what a seat IS and what a finding must satisfy:
  `SEATS`, `build_seat_prompt`, `validate_finding`, `finding_to_thesis`.
- `ingest/pre_review.py` — what happens on a run: `select_coverage`,
  `run_seats`, `merge_research_theses`. This is the one you call.
- `ingest/claims.py` — the claims ledger: `extract_claims`, `merge_claims`.
  Judging the claims later is a separate pass, `/judge-claims`.

None of them touch the network or the filesystem. You supply the intelligence
through `call_fn`, and you do the reading and writing of the store yourself.

## Procedure

1. **Refresh prices** (needs network): `python3 ingest/fetch_prices.py`.
   Continue if it fails — prices are context here, not the point.

2. **Pick the shortlist.** `pre_review.select_coverage` has a caller contract and
   will not silently paper over a breach of it:

   - `theses` must already be canonicalized —
     `scorer.canonicalize_theses(theses, base["tickerAliases"], base["themeTags"])`.
     Skip it and posts tagged `SIVEF` never count toward `SIVE`.
   - `priorities` must already be filtered to the candidate set you want
     reviewed — the **Core-tier rows**. The function has no tier awareness, so
     passing the full ranking lets one-off Radar name-drops into an expensive
     three-seat review, and makes the `dropped` list ~100 names of noise
     instead of the handful the cap actually cut.
   - `since` must be a non-empty date or ISO timestamp string. Use
     `verdicts.json` `meta.reviewedAt`. Passing `None` raises, deliberately —
     there is no safe reading of "no cutoff".

   Then call
   `pre_review.select_coverage(core_priorities, verdicts, canonical_theses, since, cap=12)`.
   Report the returned `dropped` list to the operator — never let a cap read as
   full coverage.

   **On the first tier of that selection.** Names whose desk stance *moved* are
   picked first, which requires each verdict to carry a `previousStance`. Until
   `/weekly-review` has written that field at least once, no name qualifies on
   that route and the shortlist is driven by new-thesis volume and score
   instead. That is the intended fail-inert behaviour, not a bug — do not
   "fix" it by falling back to `updatedAt`, which matches every verdict the
   weekly pass rewrites and would silently consume the whole cap.

3. **Run the seats.** Build the per-ticker context as
   `{ticker: [theses mentioning it]}` from the **canonicalized** theses, then
   call:

   ```
   pre_review.run_seats(selected, theses_by_ticker, call_fn,
                        allowed_tickers=<every symbol in tickers.json>,
                        now=<ISO timestamp you stamp once for the run>)
   ```

   `call_fn(system, user) -> dict` is where you do the work: search for primary
   sources, read them, and answer the seat's one question, returning the
   finding dict. This is the same injected-`call_fn` pattern `docs/GUIDE.md`
   section 3 describes for the Brain, so no API key is needed.

   The prompt names the ticker under review on its first line, and the finding
   is validated against **that** ticker, not the one your answer claims. A
   finding filed against a different name is dropped and counted in
   `meta.rejected`. This is deliberate: the context sheet is full of forwarded
   third-party posts, and a post that talks a seat into reporting on another
   name must not be able to move that name's numbers.

   **The basis rule is absolute.** Cite SEC filings, earnings-call
   transcripts, company IR material, exchange notices, or established industry
   data providers (TrendForce, SEMI, Counterpoint). Content aggregators and
   SEO summaries do not qualify. If you cannot cite one, return an empty
   `basis` — the finding is then recorded unverified and forced to neutral so
   it cannot move a number. **That is the correct outcome. Never invent a
   citation to avoid it.**

4. **Write the findings.** Merge with
   `pre_review.merge_research_theses(existing, out["theses"])`, save `theses.json`,
   bump `base.json` `meta.version` and `meta.lastUpdated`, and regenerate:
   `python3 ingest/generate_data_js.py`.

   The merge refuses anything that is not research-sourced, and anything
   without a non-empty id, by raising. Both mean a bug upstream — do not catch
   and continue past either.

5. **Extract claims from this run's findings.** A finding that predicts
   something dated and testable belongs in the claims ledger, so it can be
   checked later. Build one item per finding —
   `{"ticker", "text", "madeAt", "thesisId"}`, where `madeAt` is the run date
   and `text` is the finding — and call:

   ```
   claims.extract_claims(items, call_fn, allowed_tickers=..., source=<seat>)
   ```

   `source` is the seat that made the finding, so a seat that is reliably
   wrong can be told apart from one that is not. Merge with
   `claims.merge_claims(existing, out["claims"])` and save `claims.json`.

   A finding with no dated prediction in it yields no claim — that is normal.
   Do not manufacture a `judgeBy` to make one: the unfalsifiable share is a
   measurement, and padding it corrupts the thing being measured.

6. **Report to the operator**, in this order:
   - Anything the seats found that CONTRADICTS the analyst — this is the
     entire reason the pass exists, so it leads.
   - Which names were covered, and which the cap dropped.
   - How many findings came back unverified, and on what.
   - Any seat that failed and on which name (`meta.failures`).

## Hard rules

- The seats write ONLY research theses into `theses.json`. They never touch
  `verdicts.json`, `memos.json`, `calls.json`, or an analyst thesis.
- Every finding is at most 60 words. The whole report is one page. Three
  essays the operator skims are worse than one page he finishes.
- `direction` is exactly `bull`, `bear` or `neutral`, lowercase. Anything else
  scores 0.0 and the bear case is thrown away.
- Research corrects a score downward but never inflates one, never buys a name
  tier coverage, and is never counted as analyst attention — it is excluded
  from `analystMentions`, `attention` and `lastMentioned`. That asymmetry is
  deliberate — do not work around it.
- Never hand-edit `data.js` (CLAUDE.md rule 6).
- Research support, not investment advice.
