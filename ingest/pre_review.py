"""One pre-review pass: choose the names, run the seats, merge the findings.

Split out of seats.py on 2026-07-27 when that file passed the ~350-line
threshold the plan set. The seam is deliberate: `seats.py` answers "what is a
seat, and what must a finding satisfy to be recorded at all", while this module
answers "what happens on a review run". Everything here composes the pieces
seats.py defines and adds no new rules about a single finding.

PURE, exactly like seats.py and synthesize.py: no network, no file I/O, no API
client. Intelligence arrives through an injected `call_fn(system, user) -> dict`
so a Claude Code session can drive the run without an API key (the operator does
not have one — see CLAUDE.md, v4). The only side effect is a stderr warning when
one seat call fails, which mirrors synthesize.synthesize_all.

Driven by the /pre-review skill (.claude/skills/pre-review/SKILL.md). Read the
caller contracts on select_coverage and run_seats before wiring anything new to
them — this module validates the arguments a caller controls and raises rather
than guessing, because a bad cutoff or an unmarked research record has no safe
default.
"""

import sys

import scorer
import seats


MAX_COVERAGE = 12
NEW_THESIS_TRIGGER = 3


def _day(value):
    """The date portion of a timestamp, so mixed store formats compare.

    verdicts.json carries both "2026-07-06" and "2026-07-22T00:00:00Z", and
    scorer._parse_dt accepts both, so both are legitimate. A lexical compare
    between the two shapes is wrong: date-only "2026-07-22" sorts BELOW
    "2026-07-22T00:00:00Z" and would be silently excluded. Coverage runs
    weekly, so intra-day precision is irrelevant.

    A missing, empty or non-string value yields "". What that means depends
    entirely on which side of the comparison it lands on, and the two are NOT
    symmetric — see select_coverage, which rejects an empty `since` outright:

      * on a RECORD's date, "" sorts below every real cutoff, so the record is
        excluded. That is the inert direction and the correct one.
      * on the `since` cutoff, "" sorts below every record, so EVERY record
        passes. That is failing open, and there is no inert reading of a
        missing cutoff, so the caller must be told instead.
    """
    return value[:10] if isinstance(value, str) else ""


def select_coverage(priorities, verdicts, theses, since, cap=MAX_COVERAGE):
    """Pick which names the seats review this run. Returns (selected, dropped).

    CALLER CONTRACT — both inputs must be pre-processed, because this module is
    pure and can load neither base.json nor the tier assignments:

    * `priorities` must ALREADY be filtered to the candidate set you want
      reviewed (in practice the Core-tier rows). This function has no tier
      awareness, so handing it the full ~110-name ranking would let the
      remainder fill pull `radar` one-off name-drops into an expensive
      three-seat review. It also defines `dropped`: the names that genuinely
      lost the cap, which is what the caller reports to the operator. Pass the
      whole ranking and `dropped` becomes ~98 names of noise instead.
    * `theses` must ALREADY be canonicalized via scorer.canonicalize_theses().
      Un-canonicalized, three posts tagged SIVEF do not trigger `busy` for
      SIVE, and a post tagged with both double-counts.

    Priority order, because the cap is tight and decisions matter more than
    coverage: names whose stance actually moved at the last review, then names
    the analyst has posted about at least NEW_THESIS_TRIGGER times since, then
    the highest-ranked remainder.

    A stance change is only detectable when a verdict carries `previousStance`
    differing from its current `stance`. That field is OPTIONAL and not yet
    written — the weekly-review skill is expected to start stamping it. Until
    it does, no verdict qualifies and `busy`/`ranked` do the work. This is
    deliberate: verdicts.json stores only the current stance with no history,
    and the skill rewrites `updatedAt` on every Core verdict whether or not the
    stance moved, so keying off `updatedAt` alone selected 13 of 17 names and
    silently ate the entire cap, making `busy` and `ranked` unreachable.

    Reviewing every Core name weekly is deliberately rejected — roughly three
    times the cost for names where no decision is pending. `dropped` is
    returned so the caller can log what the cap cut; silent truncation reads
    as full coverage when it is not.
    """
    ranked = [p["ticker"] for p in priorities]
    rank_of = {t: i for i, t in enumerate(ranked)}

    since_day = _day(since)
    if not since_day:
        # Deliberately loud, and deliberately NOT the inert treatment the
        # record side gets. An unreadable date on a record excludes that
        # record; an unreadable `since` opens every gate, so failing quietly
        # here would review everything ever posted and call it a weekly run.
        # A caller with no cutoff is a bug in the caller: run_seats reads this
        # from verdicts.json meta.reviewedAt, and .get() yields None the day
        # that key is absent or renamed.
        raise ValueError(
            "select_coverage: `since` must be a non-empty date or ISO "
            "timestamp string, got {!r}".format(since))

    if cap <= 0:
        return [], list(ranked)

    changed = []
    for v in verdicts:
        if _day(v.get("updatedAt")) < since_day:
            continue
        # Absent/empty/non-string on either side reads as "no known change"
        # and does not qualify — the field is optional, so it must fail inert.
        current = seats.coerce_str(v.get("stance")).lower()
        previous = seats.coerce_str(v.get("previousStance")).lower()
        if not current or not previous or current == previous:
            continue
        if v.get("ticker") in rank_of:
            changed.append(v["ticker"])

    # Research findings never buy coverage: one research thesis per seat per
    # covered name lands in the feed stamped with the run's timestamp, so
    # counting them would make every reviewed name qualify as busy on the next
    # run forever — ratcheting itself into a tight cap and crowding out names
    # nobody has looked at. This is the coverage aggregate's version of the
    # scorer asymmetry: research can correct a name, never promote it.
    # scorer.is_research (not a source == "research" comparison) so a miscased
    # "Research" still reads as research rather than failing back to full
    # analyst treatment.
    counts = {}
    for th in theses:
        if scorer.is_research(th):
            continue
        if _day(th.get("postedAt")) < since_day:
            continue
        for sym in th.get("tickers", []):
            counts[sym] = counts.get(sym, 0) + 1
    busy = [t for t, n in counts.items()
            if n >= NEW_THESIS_TRIGGER and t in rank_of]

    selected = []
    for group in (changed, busy, ranked):
        for sym in sorted(group, key=lambda s: rank_of[s]):
            if sym not in selected:
                selected.append(sym)
            if len(selected) >= cap:
                break
        if len(selected) >= cap:
            break

    dropped = [t for t in ranked if t not in selected]
    return selected, dropped


def run_seats(tickers, theses_by_ticker, call_fn, *, allowed_tickers, now,
              only_seats=None):
    """Run every seat over every ticker. Returns {theses, meta}.

    `call_fn(system, user) -> dict` is injected so this module never touches
    the network — a Claude Code session supplies it (see synthesize.py for the
    same pattern and docs/GUIDE.md section 3).

    CALLER CONTRACT, same as select_coverage: `theses_by_ticker` must be keyed
    by CANONICAL symbols, i.e. built from theses already run through
    scorer.canonicalize_theses(). Un-canonicalized, the posts an analyst tagged
    "SIVEF" sit under a key no reviewed ticker matches, and the seat reviews
    SIVE with an empty context sheet while believing it has seen everything the
    analyst said.

    One seat failing on one ticker is isolated: it is recorded in
    meta.failures and the run continues. A run is three seats over up to a
    dozen names, so aborting on the first bad response throws away every
    finding after it; recording the gap keeps the rest and still tells the
    operator exactly which questions went unanswered.

    A typo in `only_seats` matches no seat rather than raising, which fails
    inert in the safe direction — nothing is written, and meta.seatsRun shows
    the shortfall.

    A finding that fails validation is counted in meta.rejected and simply not
    written — a bad finding must never become a thesis. Note that validation is
    given the CALLER's ticker, never the model's: a seat asked about one name
    cannot file a finding against another, however persuasive the forwarded
    posts in its prompt were (see seats.validate_finding's TICKER PIN note).
    """
    seat_keys = [s for s in seats.SEATS if not only_seats or s in only_seats]
    out = []
    failures = []
    rejected = 0

    for ticker in tickers:
        context = theses_by_ticker.get(ticker, [])
        for seat in seat_keys:
            system, user = seats.build_seat_prompt(seat, ticker, context)
            try:
                raw = call_fn(system, user)
            except Exception as exc:  # noqa: BLE001 — isolate this one call
                failures.append({"seat": seat, "ticker": ticker,
                                 "error": str(exc)})
                print("WARN seat {} failed on {}: {}".format(seat, ticker, exc),
                      file=sys.stderr)
                continue
            finding = seats.validate_finding(raw, seat, ticker, allowed_tickers)
            if finding is None:
                rejected += 1
                continue
            out.append(seats.finding_to_thesis(finding, now))

    return {
        "theses": out,
        "meta": {
            "generatedAt": now,
            "seatsRun": len(seat_keys),
            "tickersCovered": len(tickers),
            "written": len(out),
            "rejected": rejected,
            "failures": failures,
        },
    }


def merge_research_theses(existing, incoming):
    """Return a new list with `incoming` research theses merged into `existing`.

    Re-running a review replaces that run's own findings rather than stacking
    duplicates, because seats.finding_to_thesis derives a stable id from the seat,
    the ticker and the finding text.

    An analyst thesis is never modified or replaced, even on an id collision:
    the analyst feed is the operator's captured record and this module has no
    business editing it. On a clash the incoming research finding is dropped.

    Two guards beyond that, because this function is the only door research
    findings use to reach the store:

    - Incoming records must be research-sourced. One that is not would land in
      the analyst feed carrying full score and tier weight, which is the
      research asymmetry running backwards. A caller passing one has a bug
      rather than untrusted data, so it raises instead of failing quietly.
    - Incoming records must carry a non-empty id, because dedupe is by id. An
      id-less finding cannot be matched on a re-run, so it would stack a fresh
      copy into the store every week.

    Because of that second guard the incoming id is always a non-empty string,
    so an id-less record on the existing side can never be matched against one
    and needs no guard of its own.
    """
    out = [dict(t) for t in existing]
    by_id = {t.get("id"): i for i, t in enumerate(out)}

    for th in incoming:
        if not scorer.is_research(th):
            raise ValueError(
                "merge_research_theses: incoming thesis {!r} is not "
                "research-sourced (source={!r})".format(
                    th.get("id"), th.get("source")))
        tid = th.get("id")
        if not isinstance(tid, str) or not tid:
            raise ValueError(
                "merge_research_theses: incoming thesis needs a non-empty "
                "string id for dedupe, got {!r}".format(tid))
        idx = by_id.get(tid)
        if idx is None:
            by_id[tid] = len(out)
            out.append(dict(th))
        elif scorer.is_research(out[idx]):
            out[idx] = dict(th)
    return out
