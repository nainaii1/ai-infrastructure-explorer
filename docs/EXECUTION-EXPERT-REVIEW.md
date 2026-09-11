# Execution Guide — Expert Review Team

> **Mostly complete, historical build record.** Phases 1-3 shipped 26-28 Jul
> 2026. Phases 4-5 are genuinely still open (see the table below) but are not
> active work — Phase 4 is blocked on having enough judged claims, Phase 5 needs
> a decision on paid API access. The **"Invariants" section below is still live
> reference** — read it before touching `scorer.py`, `seats.py` or
> `pre_review.py`, same as always. For current status, `docs/ROADMAP.md`.

_Created 2026-07-26. This is the to-do doc for the expert-review-team programme:
tick boxes as sessions land. One prompt = one Claude Code session = one commit._

**Goal:** stop the desk being downstream of exactly one analyst. All 258 captured
theses come from one long-only investor, so the store contains no bear case and
nothing outside his field of view can enter. Three expert seats research a
shortlist each week and write checked findings back into the thesis feed; over
time a claims ledger measures who has actually been right.

**Spec:** `docs/superpowers/specs/2026-07-26-expert-review-team-design.md`
**Plans:** `docs/superpowers/plans/2026-07-26-direction-aware-scoring.md` (Phase 1),
`docs/superpowers/plans/2026-07-26-expert-review-seats.md` (Phase 2),
`docs/superpowers/plans/2026-07-28-claims-ledger.md` (Phase 3)

For the v7 "Private Coverage" upgrade — a separate, completed programme — see
`docs/EXECUTION.md`.

## How to use this doc

1. Work top to bottom; each session assumes the previous one landed.
2. Open a fresh Claude Code session per prompt and paste the prompt verbatim.
3. After each session run its verification checklist, tick the box, commit.
4. **Read "Invariants" below before touching `scorer.py`, `seats.py`,
   `pre_review.py` or `claims.py`.** Every
   one of them was found by a review catching a defect that passed its own
   tests. They are cheap to break and expensive to notice.

---

## Status

| Phase | What | State |
|---|---|---|
| 1 | Direction-aware scoring, retired conviction multiplier, `data.js` guard | ✅ shipped 2026-07-26 |
| 2 | The three seats, verification rule, research theses in the feed | ✅ shipped 2026-07-27 |
| 3 | `claims.json`, claim judging, performance-page split | ✅ shipped 2026-07-28 |
| 4 | Hit-rate weighting | ⬜ blocked on 20+ judged claims per source |
| 5 | Scheduled overnight run | ⬜ not started |

**Branch:** `feat/claims-ledger`, 9 commits, not pushed.
**Tests:** 306 passing.

### Phase 2 detail

- [x] **P2-1** — research theses cannot buy tier coverage via `convictionHits`;
      `researchMentions` exposed; the `source` check fails inert, not open.
      Commits `76b7102`, `933f9db`.
- [x] **P2-2** — `ingest/seats.py` core: `SEATS`, `build_seat_prompt`,
      `validate_finding` (the verification rule), `finding_to_thesis`. Plus the
      security round: injection firewall, ticker pinning, real-host citations,
      `r_` id namespace. Commits `caf090f`, `49006ef`, `31402a4`, `eb8c6d1`.
- [x] **P2-3** — orchestration: `select_coverage`, `run_seats`,
      `merge_research_theses`. Plan Tasks 5–7. Commits `5834022`, `5d961d9`,
      `66f2189`, `cfafed1`, `0e5308c`, `de1de7f`.
- [x] **P2-4** — stop crediting research findings to the analyst. Plan Task 8,
      plus three surfaces the plan did not name: the priority strip, the
      watchlist ordering, and `vault_sync.py`. Commit `5b69cf2`.
- [x] **P2-5** — the `/pre-review` skill and docs. Plan Tasks 9–10.
      Commit `a15a7ce` + this docs pass.

---

## Invariants — do not regress these

Each of these was a live defect at some point in Phase 1 or 2. They are listed
in the order they were found, which is roughly the order of how easy they are to
reintroduce.

1. **`assign_tiers` never reads `score`.** It gates on `weightedMentions` and
   `convictionHits` only. Retiring the conviction multiplier therefore moved no
   ticker between tiers, and that is intentional.
2. **Research can subtract but never add.** Four paths are guarded now: the
   score (`_direction_weight` returns 0.0 for a research bull),
   `weightedMentions` (skipped entirely), `convictionHits` (skipped entirely),
   and `netAnalyst`/`analystScore` (research excluded outright). The second and
   third were each found *after* the first was fixed — if you add a fifth
   aggregate, guard it too.

   **2b. Research must not REMOVE coverage either** (added 11 Sep 2026). The
   rule above is only half the asymmetry, and the other half went unwritten for
   six weeks. Because the verdict roster and the pre-review shortlist were
   ranked by `score`, and `score` carries research's downward correction, a
   bearish finding could push a name off the list the desk writes verdicts on.
   The desk stopped covering exactly the name it had just found a problem with:
   MTSI went from rank 13 to 148 on 1 Sep from the desk's own findings, with no
   analyst input at all.

   `analystScore` exists for this and nothing else. Coverage ranks on it;
   everything else still ranks on `score`, so the corrective asymmetry is
   untouched. Do **not** "fix" a future version of this by letting research
   raise `score` — that breaks invariant 2 and is the trap the original wording
   invited. `select_coverage` sorts on `analystScore` itself rather than
   trusting the caller's list order, because a caller ordering the list wrongly
   is how this happened.

   The regression test is `BearResearchMustNotRemoveCoverage`. Its first draft
   was worthless and passed against the unfixed code: with fewer names than the
   cap, the remainder fill takes them all and ordering cannot matter. The
   committed version supplies more names than the cap and carries a
   `test_the_cap_actually_bites` guard. **Any test of ranking behaviour here
   must make the cap bite, and must be checked against the unfixed code.**
3. **An unreadable value fails inert, never toward a vote.** A typo'd
   `"bearish"` scores 0.0 rather than falling back to `neutral` (+1.0). A
   miscased `"Research"` still counts as research rather than reverting to full
   analyst weight. Both records are hand-authored by an agent, so typos are the
   expected case.
4. **An uncited finding cannot move a number.** Empty or unciteable `basis` →
   `verification: "unverified"` → `direction` forced to `"neutral"` → weight
   exactly 0.0. Visible in the brief, inert in the maths.
5. **Forwarded posts are untrusted input.** They are third-party social media
   text, and the seat reading them has web access and writes to the rankings.
   The thesis block is delimited, clipped to `MAX_THESIS_CHARS`, and the system
   prompt says to ignore instructions inside it. The ticker is pinned from the
   caller so an injection is inert even if the model falls for it.
6. **`seats.py`, `pre_review.py`, `claims.py` and `synthesize.py` are pure.** No network, no file I/O, no API
   client. Intelligence arrives through an injected `call_fn(system, user)`,
   because the operator has no API key. Adding an SDK import breaks the whole
   pattern.
7. **No test may write anything under `ingest/store/`.** Those are real
   financial records. A Phase 1 test overwrote the hand-authored
   `verdicts.json` and restored it non-atomically; a crash mid-test would have
   destroyed it. Monkeypatch `gen.STORE` to a `TemporaryDirectory` instead.
8. **Restart `bot.py` after editing anything under `ingest/`.** A long-running
   bot holds stale modules and silently rewrote `data.js` without six
   top-level blocks for four days. `write_data_js` now refuses to run from
   stale source, but only by raising.
9. **Clear `__pycache__` between mutation runs.** Stale bytecode has produced a
   false "the guard still works" reading in this repo.
10. **Research is not the analyst's attention either.** Invariant 2 covers the
    maths; this covers attribution. `analystMentions`, `attention` and
    `lastMentioned` all exclude research, and every UI label that names
    @aleabitoreddit reads `analystMentions`, never the raw `mentions` total.
    The split is derived once in `compute_priorities` rather than subtracted at
    each call site, because four call sites is four chances to forget. Found
    2026-07-27: the ticker tooltip, the priority strip, the watchlist ordering
    and the vault ticker pages were all crediting desk findings to him, and
    `attention` was being incremented by research outright.
11. **A timestamp being rewritten is not a change.** `/weekly-review` stamps a
    fresh `updatedAt` on every Core verdict whether or not the call moved, so
    "stance changed since `since`" cannot be inferred from it — on the live
    store that matched 13 of 17 names and would have silently consumed the
    entire coverage cap, leaving the other two selection tiers unreachable. A
    real change is detected from `previousStance`, and a verdict missing that
    field does not qualify rather than matching everything.
12. **A cutoff has no inert reading, so it must raise.** On a *record*, an
    unreadable date fails inert and the record is excluded. On the `since`
    argument, "unreadable" would open every gate — `select_coverage` raises
    instead. This regressed once: normalizing dates for comparison turned a
    loud `TypeError` on `since=None` into silent selection of a 2019 thesis.
    Guard the inputs a caller controls differently from the data it passes.
13. **A guard no mutation can make bite is decorative — delete it or fix the
    test.** Three tests in this phase passed for the wrong reason and were
    caught only by mutation: a count assertion that one seat running six times
    would also satisfy, a `cap <= 0` test that passed because the loop broke
    before the leak, and an id-collision guard that was simply unreachable.
    Two were fixed; the third was removed as dead code.
14. **A claim moves no number until Phase 4.** Hit-rate weighting is gated on
    ≥20 judged claims per source, so until then `claims.json` is observed and
    never read by `scorer.py`. Two tests hold the line: one asserts scorer
    neither imports `claims` nor names `claims.json`, the other proves
    priorities and tiers are byte-identical with a populated ledger present.
    This is invariant 2's shape again — a new aggregate arrived, so it got a
    guard before anything could read it.
15. **`unfalsifiable` is an outcome, not a parse failure.** A claim nothing
    could settle is recorded, never dropped, and `score_claims` returns the
    unfalsifiable share from the same call as the hit rate so no surface can
    show the flattering number alone. The extraction prompt explicitly forbids
    inventing a `judgeBy`: a manufactured settlement date understates how vague
    a source is, which is the one thing this ledger measures.
16. **An absent number must not look like a bad one.** `hitRate` is `None`, not
    `0.0`, when nothing has been judged — zero reads as "always wrong". Same
    family as invariant 3: an absent value never gets to masquerade as a real
    one.
17. **Judging is where a citation gets invented.** `correct`/`wrong` require a
    citable primary source by exactly `seats.clean_basis`'s rule; without one
    the claim stays `open`. Judging before `judgeBy` or re-deciding a judged
    claim raises — a silently flipped verdict destroys the only record of what
    the desk believed at the time, which is the entire asset.

---

## Remaining sessions

### P2-3, P2-4, P2-5 — shipped 2026-07-27

The per-session prompts that stood here have been removed now that the work is
done; the commits and what each one covered are in the Phase 2 detail list
above, and the durable lessons are in **Invariants** 10–13. Two corrections
worth carrying forward, because the plan text still has the older versions:

- `validate_finding` takes `(raw, seat, ticker, allowed_tickers)`. The ticker is
  pinned from the caller, so a prompt injection cannot land a finding on a
  different name. The plan's Task 6 body calls it with three arguments.
- `select_coverage` has a caller contract the plan does not state: `theses`
  must be canonicalized, `priorities` must be pre-filtered to the candidate
  (Core) set, and `since` must be a non-empty date string.

### Phase 3 — The memory

Plan: `docs/superpowers/plans/2026-07-28-claims-ledger.md`.

- [x] Plan written
- [x] **Backend landed 2026-07-28** — `claims.json`, `ingest/claims.py`
      (extract / judge / score), `/judge-claims`, extraction inside
      `/pre-review`, `source` on every call, C1 guard.
- [x] **Bounded backfill** — 25 analyst claims from 64 of 126 focused posts.
      **52% unfalsifiable share**, 0 judged (all deadlines future).
- [ ] **The remaining 62 focused posts.** Work list and batches were in the
      session scratchpad and are gone; regenerate by filtering theses to Core
      names with ≤3 tickers and skipping the ids already in `claims.json`.
- [x] **`performance.html` split into Calls and Claims** (2026-07-28). Per-
      source scorecards + a claims table sorted soonest-deadline-first. The
      hit rate and the untestable share are precomputed together in Python and
      travel in one object, so the page cannot render one without the other.

Invariants C1-C4 for this phase are in the plan; the four general ones earned
here are 10-13 above.

### Phase 4 — Hit-rate weighting

**Blocked, deliberately.** `source_weight = clamp(0.5 + hit_rate, 0.5, 1.5)`,
applied per thesis by author, and gated so a source keeps a weight of exactly
1.0 until it has **at least 20 judged claims**. Expect three to six months of
Phase 3 running before this does anything real. Do not start early — three
lucky calls must not reweight the book.

- [ ] Unblocked (20+ judged claims exist)
- [ ] Landed

### Phase 5 — Scheduled run

The seats run unattended the night before the weekly review, covering at most 12
names, logging whatever the cap dropped.

- [ ] Landed

---

## What is deliberately not built

- **Claims in the seat output.** The spec's seat shape includes a `claims`
  array; Phase 2 drops it because `claims.json` does not exist until Phase 3.
  Capturing predictions with nowhere to put them is speculative.
- **Practice 9.0 — daily kill-trigger monitoring.** Only worth building if the
  operator starts acting on the tool, which he currently does not.
- **A real tenth out of ten.** Every seat is the same model with a different
  instruction. A genuine 10 needs humans with different incentives, expert
  network calls, channel checks, proprietary data. 9 is the honest ceiling for
  a one-person desk.
