import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import pre_review  # noqa: E402
import seats  # noqa: E402
import scorer  # noqa: E402

NOW = "2026-07-26T12:00:00Z"


def thesis(text, tickers, posted_at="2026-07-20T00:00:00Z"):
    """Build a thesis fixture."""
    return {"id": "h_" + text[:8], "text": text, "tickers": tickers,
            "postedAt": posted_at, "source": "x", "author": "aleabitoreddit"}


GOOD = {
    "seat": "semi-expert",
    "ticker": "SIVE",
    "direction": "bear",
    "finding": "Fab-light capacity assumes an unsigned Win Semi allocation.",
    "basis": ["https://www.sec.gov/Archives/edgar/data/1/x.htm"],
    "confidence": "high",
}
ALLOWED = {"SIVE", "MU", "LITE"}



class TestSelectCoverage(unittest.TestCase):
    def _pri(self, pairs):
        return [{"ticker": t, "score": s} for t, s in pairs]

    def _verdict(self, ticker, updated_at="2026-07-25T00:00:00Z",
                 stance="act", previous="watch"):
        """A verdict whose stance genuinely moved, unless told otherwise.

        `previous=None` omits previousStance entirely — the shape of all 17
        records in the live store today.
        """
        v = {"ticker": ticker, "updatedAt": updated_at, "stance": stance}
        if previous is not None:
            v["previousStance"] = previous
        return v

    def test_stance_changes_come_first(self):
        pri = self._pri([("AAA", 90), ("BBB", 80), ("CCC", 1)])
        picked, _ = pre_review.select_coverage(
            pri, [self._verdict("CCC")], [], since="2026-07-20", cap=2)
        self.assertEqual(picked[0], "CCC")

    def test_an_unchanged_stance_does_not_qualify(self):
        # The live failure mode: the weekly-review skill rewrites updatedAt on
        # every Core verdict whether or not the stance moved, so a fresh
        # timestamp alone must not buy a review slot.
        pri = self._pri([("AAA", 90), ("CCC", 1)])
        verdicts = [self._verdict("CCC", stance="act", previous="act")]
        picked, _ = pre_review.select_coverage(
            pri, verdicts, [], since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

    def test_a_previous_stance_differing_only_in_case_does_not_qualify(self):
        # verdicts.json is agent-authored, so "act" vs "Act" is a realistic
        # typo. Without .lower() the same word reads as a stance change and
        # buys a review slot — failing open on exactly the input invariant 3
        # exists for.
        pri = self._pri([("AAA", 90), ("CCC", 1)])
        verdicts = [self._verdict("CCC", stance="act", previous="Act")]
        picked, _ = pre_review.select_coverage(
            pri, verdicts, [], since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

    def test_a_missing_since_is_rejected_rather_than_failing_open(self):
        # An unreadable date on a RECORD excludes that record. An unreadable
        # `since` would open every gate, so there is no inert answer and the
        # caller has to be told. run_seats reads this from verdicts.json
        # meta.reviewedAt, where .get() yields None if the key is ever
        # renamed — that must not silently review everything ever posted.
        pri = self._pri([("AAA", 90), ("OLD", 1)])
        theses = [thesis("t%d" % i, ["OLD"], "2019-01-01T00:00:00Z")
                  for i in range(pre_review.NEW_THESIS_TRIGGER)]
        for bad in (None, "", 20260720):
            with self.assertRaises(ValueError, msg=repr(bad)) as ctx:
                pre_review.select_coverage(pri, [], theses, since=bad, cap=1)
            self.assertIn("since", str(ctx.exception))

    def test_a_missing_previous_stance_does_not_qualify(self):
        # Fails inert until the weekly-review skill starts stamping the field:
        # no history recorded means no *known* change, not an assumed one.
        # Every record in the live store has this shape today.
        pri = self._pri([("AAA", 90), ("CCC", 1)])
        verdicts = [self._verdict("CCC", previous=None)]
        picked, _ = pre_review.select_coverage(
            pri, verdicts, [], since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

    def test_names_with_enough_new_theses_come_next(self):
        pri = self._pri([("AAA", 90), ("DDD", 2)])
        theses = [thesis("t%d" % i, ["DDD"], "2026-07-24T00:00:00Z")
                  for i in range(3)]
        picked, _ = pre_review.select_coverage(
            pri, [], theses, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["DDD"])

    def test_remainder_fills_by_score(self):
        pri = self._pri([("AAA", 90), ("BBB", 80), ("CCC", 70)])
        picked, _ = pre_review.select_coverage(pri, [], [], since="2026-07-20", cap=2)
        self.assertEqual(picked, ["AAA", "BBB"])

    def test_cap_is_respected_and_drops_are_reported(self):
        pri = self._pri([("A%d" % i, 100 - i) for i in range(20)])
        picked, dropped = pre_review.select_coverage(
            pri, [], [], since="2026-07-20", cap=12)
        self.assertEqual(len(picked), 12)
        self.assertEqual(len(dropped), 8)
        self.assertNotIn(picked[0], dropped)

    def test_no_duplicates_when_a_name_qualifies_twice(self):
        pri = self._pri([("AAA", 90)])
        theses = [thesis("t%d" % i, ["AAA"], "2026-07-24T00:00:00Z")
                  for i in range(5)]
        picked, _ = pre_review.select_coverage(
            pri, [self._verdict("AAA")], theses, since="2026-07-20", cap=12)
        self.assertEqual(picked, ["AAA"])

    def test_a_stance_change_outranks_a_different_busy_name(self):
        # The docstring's central ordering claim. CCC (stance moved) and DDD
        # (3 new posts) both qualify, but by different routes and from the
        # bottom of the ranking; cap=1 means only one can win and it must be
        # the stance change. Without a busy name that is NOT the changed name,
        # swapping the group order goes undetected.
        pri = self._pri([("AAA", 90), ("CCC", 2), ("DDD", 1)])
        theses = [thesis("t%d" % i, ["DDD"], "2026-07-24T00:00:00Z")
                  for i in range(3)]
        picked, _ = pre_review.select_coverage(
            pri, [self._verdict("CCC")], theses, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["CCC"])

    def test_a_verdict_for_a_dropped_ticker_is_ignored(self):
        # verdicts.json outlives the ranking: a name re-tiered out of
        # priorities still has a verdict record. It must neither KeyError in
        # the rank sort nor appear in the selection.
        # The verdict must otherwise fully qualify (fresh + a real stance
        # change), or the membership guard is never reached and this test
        # would pass for the wrong reason.
        pri = self._pri([("AAA", 90)])
        picked, dropped = pre_review.select_coverage(
            pri, [self._verdict("GONE")], [], since="2026-07-20", cap=12)
        self.assertEqual(picked, ["AAA"])
        self.assertNotIn("GONE", picked)
        self.assertNotIn("GONE", dropped)

    def test_research_theses_never_qualify_a_name_as_busy(self):
        # Invariant 2 applied to the coverage aggregate. run_seats writes
        # exactly NEW_THESIS_TRIGGER research theses per covered name, so
        # counting them would make every reviewed name self-qualify forever
        # and ratchet itself into the cap. Same count of analyst posts must
        # still qualify, or this test would pass on a broken trigger.
        pri = self._pri([("AAA", 90), ("RRR", 1)])
        n = pre_review.NEW_THESIS_TRIGGER
        research = [dict(thesis("t%d" % i, ["RRR"], "2026-07-24T00:00:00Z"),
                         source=scorer.RESEARCH_SOURCE) for i in range(n)]
        picked, _ = pre_review.select_coverage(
            pri, [], research, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

        analyst = [thesis("t%d" % i, ["RRR"], "2026-07-24T00:00:00Z")
                   for i in range(n)]
        picked, _ = pre_review.select_coverage(
            pri, [], analyst, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["RRR"])

    def test_miscased_research_source_still_does_not_qualify(self):
        # Fails inert, via scorer.is_research: a hand-authored "Research"
        # must not buy coverage that lowercase "research" is denied.
        pri = self._pri([("AAA", 90), ("RRR", 1)])
        research = [dict(thesis("t%d" % i, ["RRR"], "2026-07-24T00:00:00Z"),
                         source="Research")
                    for i in range(pre_review.NEW_THESIS_TRIGGER)]
        picked, _ = pre_review.select_coverage(
            pri, [], research, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

    def test_old_verdicts_and_old_theses_do_not_qualify(self):
        # The verdict carries a real stance change, so only its stale date
        # keeps it out — otherwise the cutoff would go untested.
        pri = self._pri([("AAA", 90), ("ZZZ", 1)])
        verdicts = [self._verdict("ZZZ", updated_at="2026-07-01T00:00:00Z")]
        theses = [thesis("t%d" % i, ["ZZZ"], "2026-07-01T00:00:00Z")
                  for i in range(9)]
        picked, _ = pre_review.select_coverage(
            pri, verdicts, theses, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

    def test_date_only_timestamps_compare_against_a_full_iso_since(self):
        # XFAB really has updatedAt "2026-07-06" while the rest are full ISO,
        # and scorer._parse_dt accepts both. Lexically "2026-07-22" sorts BELOW
        # "2026-07-22T00:00:00Z", so a same-day date-only record would be
        # silently dropped if the two sides were not made commensurable.
        pri = self._pri([("AAA", 90), ("CCC", 1)])
        verdicts = [self._verdict("CCC", updated_at="2026-07-22")]
        picked, _ = pre_review.select_coverage(
            pri, verdicts, [], since="2026-07-22T00:00:00Z", cap=1)
        self.assertEqual(picked, ["CCC"])

    def test_a_date_only_since_still_admits_full_iso_records(self):
        # The mirror image: date-only on the `since` side, full ISO in the
        # store. Same-day must still qualify.
        pri = self._pri([("AAA", 90), ("CCC", 1)])
        theses = [thesis("t%d" % i, ["CCC"], "2026-07-20T09:30:00Z")
                  for i in range(pre_review.NEW_THESIS_TRIGGER)]
        picked, _ = pre_review.select_coverage(
            pri, [], theses, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["CCC"])

    def test_one_short_of_the_trigger_does_not_qualify(self):
        # Pins the lower boundary: >= 3 and >= 2 are otherwise
        # indistinguishable, since every other test uses exactly the trigger.
        pri = self._pri([("AAA", 90), ("DDD", 1)])
        theses = [thesis("t%d" % i, ["DDD"], "2026-07-24T00:00:00Z")
                  for i in range(pre_review.NEW_THESIS_TRIGGER - 1)]
        picked, _ = pre_review.select_coverage(
            pri, [], theses, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

    def test_a_non_positive_cap_selects_nothing(self):
        # A qualifying name in the FIRST group is what makes this bite: with
        # every group empty the loop's own `len(selected) >= cap` check breaks
        # on 0 >= 0 before appending, so the bug hides. With a stance change
        # present, the append precedes the length check and one name leaks out.
        pri = self._pri([("AAA", 90), ("BBB", 80)])
        verdicts = [self._verdict("AAA")]
        for cap in (0, -1):
            picked, dropped = pre_review.select_coverage(
                pri, verdicts, [], since="2026-07-20", cap=cap)
            self.assertEqual(picked, [], cap)
            self.assertEqual(dropped, ["AAA", "BBB"], cap)


class TestRunSeats(unittest.TestCase):
    def _call_fn(self, direction="bear"):
        """A stand-in model that answers about whatever ticker it was asked."""
        def call_fn(system, user):
            sym = user.split("\n")[0].split(": ")[1].strip()
            return dict(GOOD, ticker=sym, direction=direction)
        return call_fn

    def test_one_thesis_per_seat_per_ticker(self):
        out = pre_review.run_seats(["SIVE", "MU"], {}, self._call_fn(),
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(len(out["theses"]), 6)
        self.assertEqual(out["meta"]["seatsRun"], 3)
        self.assertEqual(out["meta"]["tickersCovered"], 2)
        # A bare count of 6 would also pass if one seat ran six times, which is
        # what the test name actually claims does not happen.
        self.assertEqual(
            sorted((t["author"], t["tickers"][0]) for t in out["theses"]),
            sorted((seat, sym) for seat in seats.SEATS for sym in ("SIVE", "MU")))

    def test_a_failing_seat_does_not_abort_the_run(self):
        calls = {"n": 0}

        def flaky(system, user):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("boom")
            sym = user.split("\n")[0].split(": ")[1].strip()
            return dict(GOOD, ticker=sym)

        out = pre_review.run_seats(["SIVE"], {}, flaky,
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(len(out["theses"]), 2)
        self.assertEqual(len(out["meta"]["failures"]), 1)
        self.assertEqual(out["meta"]["failures"][0]["ticker"], "SIVE")
        self.assertIn("boom", out["meta"]["failures"][0]["error"])

    def test_a_rejected_finding_is_dropped_not_written(self):
        def bad(system, user):
            return {"finding": "", "ticker": "SIVE"}

        out = pre_review.run_seats(["SIVE"], {}, bad,
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(out["theses"], [])
        self.assertEqual(out["meta"]["rejected"], 3)

    def test_a_finding_about_another_ticker_is_never_written(self):
        # The injection this closes end to end: a seat asked about SIVE reads a
        # forwarded post that talks it into reporting on MU instead. Both names
        # are in-universe, so only the caller's ticker pin catches it. The
        # finding must be dropped and counted, never written against MU.
        def wrong_name(system, user):
            return dict(GOOD, ticker="MU", direction="bear")

        out = pre_review.run_seats(["SIVE"], {}, wrong_name,
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(out["theses"], [])
        self.assertEqual(out["meta"]["rejected"], 3)
        self.assertEqual(out["meta"]["written"], 0)

    def test_every_written_thesis_is_research_sourced(self):
        out = pre_review.run_seats(["SIVE"], {}, self._call_fn(),
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertTrue(out["theses"])
        for t in out["theses"]:
            self.assertEqual(t["source"], scorer.RESEARCH_SOURCE)

    def test_theses_by_ticker_reaches_the_prompt(self):
        seen = {}

        def spy(system, user):
            seen["user"] = user
            return dict(GOOD, ticker="SIVE")

        pre_review.run_seats(["SIVE"],
                        {"SIVE": [thesis("fab-light ramp", ["SIVE"])]},
                        spy, allowed_tickers=ALLOWED, now=NOW)
        self.assertIn("fab-light ramp", seen["user"])

    def test_a_ticker_with_no_context_still_gets_reviewed(self):
        # theses_by_ticker is keyed by canonical symbol; a name the analyst has
        # never posted about is exactly the case the seats exist for.
        out = pre_review.run_seats(["LITE"], {"SIVE": []}, self._call_fn(),
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(len(out["theses"]), 3)
        self.assertEqual(out["meta"]["rejected"], 0)

    def test_only_seats_restricts_the_run(self):
        out = pre_review.run_seats(["SIVE"], {}, self._call_fn(),
                              allowed_tickers=ALLOWED, now=NOW,
                              only_seats=["pm"])
        self.assertEqual(out["meta"]["seatsRun"], 1)
        self.assertEqual(len(out["theses"]), 1)
        self.assertEqual(out["theses"][0]["author"], "pm")

    def test_written_theses_are_stamped_with_the_caller_s_now(self):
        # `now` is not cosmetic: it lands in postedAt, ingestedAt AND the
        # thesis id, and merge_research_theses dedupes on that id. A run that
        # stamped its own clock instead of the caller's would write records
        # that re-merge as new every week.
        out = pre_review.run_seats(["SIVE"], {}, self._call_fn(),
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertTrue(out["theses"])
        for t in out["theses"]:
            self.assertEqual(t["postedAt"], NOW)
            self.assertEqual(t["ingestedAt"], NOW)
        expected = seats.finding_to_thesis(
            seats.validate_finding(dict(GOOD, ticker="SIVE"), "pm", "SIVE",
                                   ALLOWED), NOW)
        self.assertIn(expected["id"], [t["id"] for t in out["theses"]])

    def test_meta_counts_agree_with_what_was_written(self):
        out = pre_review.run_seats(["SIVE", "MU"], {}, self._call_fn(),
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(out["meta"]["written"], len(out["theses"]))
        self.assertEqual(out["meta"]["generatedAt"], NOW)
        self.assertEqual(out["meta"]["failures"], [])


class TestMerge(unittest.TestCase):
    def _research(self, text="x", ident="r1", **kw):
        rec = {"id": ident, "source": "research", "author": "pm",
               "text": text, "tickers": ["MU"], "postedAt": NOW,
               "direction": "bear", "verification": "verified"}
        rec.update(kw)
        return rec

    def test_new_research_is_appended(self):
        existing = [thesis("analyst post", ["MU"])]
        merged = pre_review.merge_research_theses(existing, [self._research()])
        self.assertEqual(len(merged), 2)

    def test_analyst_theses_are_never_modified(self):
        analyst = thesis("analyst post", ["MU"])
        merged = pre_review.merge_research_theses([analyst], [self._research()])
        self.assertEqual(merged[0], analyst)

    def test_duplicate_research_id_replaces_not_duplicates(self):
        existing = [self._research(text="old")]
        merged = pre_review.merge_research_theses(existing, [self._research(text="new")])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["text"], "new")

    def test_research_cannot_overwrite_an_analyst_thesis_with_the_same_id(self):
        analyst = dict(thesis("analyst post", ["MU"]), id="clash")
        incoming = dict(self._research(ident="clash"), text="research")
        merged = pre_review.merge_research_theses([analyst], [incoming])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["text"], "analyst post")

    def test_input_list_is_not_mutated(self):
        existing = [thesis("analyst post", ["MU"])]
        pre_review.merge_research_theses(existing, [self._research()])
        self.assertEqual(len(existing), 1)

    def test_the_existing_records_themselves_are_not_mutated(self):
        # Copying the list but sharing the dicts would let a later edit of the
        # merged output reach back into the caller's store objects.
        existing = [thesis("analyst post", ["MU"])]
        merged = pre_review.merge_research_theses(existing, [self._research()])
        merged[0]["text"] = "tampered"
        self.assertEqual(existing[0]["text"], "analyst post")

    def test_a_miscased_research_source_is_still_replaceable(self):
        # The guard must ask scorer.is_research, not compare the string. A
        # record written "Research" is still ours, so re-running a review has
        # to replace it rather than treat it as an untouchable analyst post
        # and silently drop the fresh finding.
        existing = [self._research(text="old", source="Research")]
        merged = pre_review.merge_research_theses(existing, [self._research(text="new")])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["text"], "new")

    def test_a_non_research_incoming_thesis_is_refused(self):
        # This function is the only door research findings use to reach the
        # store. An incoming record that is not research-sourced would land in
        # the analyst feed at full score and tier weight — invariant 2 in
        # reverse. A caller passing one has a bug, so say so.
        analyst_shaped = dict(self._research(), source="x")
        with self.assertRaises(ValueError):
            pre_review.merge_research_theses([], [analyst_shaped])

    def test_incoming_without_an_id_is_refused(self):
        # Dedupe is by id. A record with no id cannot be matched on a re-run,
        # so it would stack a fresh duplicate into the store every week.
        for bad in (None, ""):
            with self.assertRaises(ValueError):
                pre_review.merge_research_theses([], [self._research(ident=bad)])

    def test_id_less_existing_records_are_left_alone(self):
        # They cannot be matched (incoming ids are required non-empty strings)
        # so they must simply survive the merge untouched, in order.
        a = dict(thesis("first", ["MU"])); a.pop("id")
        b = dict(thesis("second", ["MU"])); b.pop("id")
        merged = pre_review.merge_research_theses([a, b], [self._research()])
        self.assertEqual([t["text"] for t in merged], ["first", "second", "x"])


if __name__ == "__main__":
    unittest.main()
