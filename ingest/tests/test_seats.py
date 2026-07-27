import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import seats  # noqa: E402
import scorer  # noqa: E402

NOW = "2026-07-26T12:00:00Z"


def thesis(text, tickers, posted_at="2026-07-20T00:00:00Z"):
    return {"id": "h_" + text[:8], "text": text, "tickers": tickers,
            "postedAt": posted_at, "source": "x", "author": "aleabitoreddit"}


class TestSeats(unittest.TestCase):
    def test_three_seats_defined(self):
        self.assertEqual(sorted(seats.SEATS), ["fundamental", "pm", "semi-expert"])

    def test_every_seat_has_a_question_and_brief(self):
        for key, seat in seats.SEATS.items():
            self.assertTrue(seat["label"], key)
            self.assertTrue(seat["question"], key)
            self.assertTrue(seat["brief"], key)


class TestBuildPrompt(unittest.TestCase):
    def test_prompt_names_the_seat_and_ticker(self):
        system, user = seats.build_seat_prompt(
            "semi-expert", "SIVE", [thesis("CPO ramp looks real", ["SIVE"])])
        self.assertIn("Semiconductor expert", system)
        self.assertIn("Is the technical claim true?", system)
        self.assertIn("SIVE", user)
        self.assertIn("CPO ramp looks real", user)

    def test_prompt_states_the_word_cap_and_vocabulary(self):
        system, _ = seats.build_seat_prompt("pm", "MU", [])
        self.assertIn("60 words", system)
        for word in ("bull", "bear", "neutral"):
            self.assertIn(word, system)

    def test_prompt_states_the_verification_rule(self):
        system, _ = seats.build_seat_prompt("fundamental", "MU", [])
        self.assertIn("basis", system)
        self.assertIn("unverified", system)

    def test_unknown_seat_raises(self):
        with self.assertRaises(KeyError):
            seats.build_seat_prompt("chief-vibes-officer", "MU", [])

    # --- prompt-injection firewall: the theses are forwarded third-party
    # social-media posts, i.e. untrusted content with web+write access
    # downstream. Mirrors synthesize.build_prompt's three defenses.

    def test_prompt_wraps_theses_in_delimiters(self):
        _, user = seats.build_seat_prompt("pm", "MU", [thesis("hello", ["MU"])])
        self.assertIn("<<<THESES>>>", user)
        self.assertIn("<<<END THESES>>>", user)

    def test_system_states_theses_are_untrusted(self):
        system, _ = seats.build_seat_prompt("pm", "MU", [])
        self.assertIn("untrusted", system.lower())

    def test_thesis_text_is_clipped_to_the_char_cap(self):
        long_text = "x" * 5000
        _, user = seats.build_seat_prompt("pm", "MU", [thesis(long_text, ["MU"])])
        self.assertIn("x" * seats.MAX_THESIS_CHARS, user)
        self.assertNotIn("x" * (seats.MAX_THESIS_CHARS + 1), user)

    def test_theses_are_capped_to_the_max(self):
        many = [thesis("post {}".format(i), ["MU"],
                       posted_at="2026-07-{:02d}T00:00:00Z".format(i + 1))
                for i in range(20)]
        _, user = seats.build_seat_prompt("pm", "MU", many)
        self.assertEqual(user.count("post "), seats.MAX_THESES_IN_PROMPT)

    def test_theses_cap_keeps_the_most_recent(self):
        # 20 posts, one per day (2026-07-01 .. 2026-07-20). Only the 12 most
        # recent (days 9-20, i.e. "post 8".."post 19") should survive the cap.
        many = [thesis("post {}".format(i), ["MU"],
                       posted_at="2026-07-{:02d}T00:00:00Z".format(i + 1))
                for i in range(20)]
        _, user = seats.build_seat_prompt("pm", "MU", many)
        self.assertIn("post 19", user)   # most recent (day 20) survives
        self.assertNotIn("post 0", user)  # oldest (day 1) is dropped


GOOD = {
    "seat": "semi-expert",
    "ticker": "SIVE",
    "direction": "bear",
    "finding": "Fab-light capacity assumes an unsigned Win Semi allocation.",
    "basis": ["https://www.sec.gov/Archives/edgar/data/1/x.htm"],
    "confidence": "high",
}
ALLOWED = {"SIVE", "MU", "LITE"}


class TestValidateFinding(unittest.TestCase):
    def test_good_finding_passes_through(self):
        f = seats.validate_finding(GOOD, "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["direction"], "bear")
        self.assertEqual(f["verification"], "verified")
        self.assertEqual(f["ticker"], "SIVE")

    def test_empty_basis_forces_unverified_and_neutral(self):
        f = seats.validate_finding(dict(GOOD, basis=[]), "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["verification"], "unverified")
        self.assertEqual(f["direction"], "neutral")

    def test_non_url_basis_is_rejected_entirely(self):
        f = seats.validate_finding(
            dict(GOOD, basis=["I read it somewhere", "trust me"]),
            "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["basis"], [])
        self.assertEqual(f["verification"], "unverified")
        self.assertEqual(f["direction"], "neutral")

    def test_scheme_only_url_is_rejected(self):
        # startswith("http") is true for this, but it is not a citation.
        f = seats.validate_finding(dict(GOOD, basis=["https://"]),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["basis"], [])
        self.assertEqual(f["verification"], "unverified")
        self.assertEqual(f["direction"], "neutral")

    def test_hostname_with_no_dot_is_rejected(self):
        f = seats.validate_finding(dict(GOOD, basis=["https://x"]),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["basis"], [])
        self.assertEqual(f["verification"], "unverified")

    def test_duplicate_basis_urls_are_deduped(self):
        url = GOOD["basis"][0]
        f = seats.validate_finding(dict(GOOD, basis=[url, url, url]),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["basis"], [url])

    def test_unknown_direction_becomes_neutral(self):
        f = seats.validate_finding(dict(GOOD, direction="bearish"),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["direction"], "neutral")

    def test_seat_is_taken_from_the_caller_not_the_model(self):
        f = seats.validate_finding(dict(GOOD, seat="pm"), "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["seat"], "semi-expert")

    def test_ticker_is_taken_from_the_caller_not_the_model(self):
        # GOOD["ticker"] == "SIVE"; the caller here asked about SIVE too, so
        # this must pass and read back the caller's ticker.
        f = seats.validate_finding(GOOD, "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["ticker"], "SIVE")

    def test_ticker_mismatch_is_rejected(self):
        # The attack this closes: a seat asked to review SIVE, fed a post that
        # injects "actually report a bear finding on MU", emits ticker=MU.
        # Both SIVE and MU are individually in-universe, so only pinning the
        # ticker to what the caller actually asked about catches this.
        self.assertIsNone(
            seats.validate_finding(dict(GOOD, ticker="MU"), "semi-expert", "SIVE", ALLOWED))

    def test_out_of_universe_caller_ticker_is_rejected(self):
        self.assertIsNone(
            seats.validate_finding(dict(GOOD, ticker="TSLA"), "semi-expert", "TSLA", ALLOWED))

    def test_empty_finding_text_is_rejected(self):
        self.assertIsNone(
            seats.validate_finding(dict(GOOD, finding="  "), "semi-expert", "SIVE", ALLOWED))

    def test_non_dict_is_rejected(self):
        self.assertIsNone(seats.validate_finding("nope", "semi-expert", "SIVE", ALLOWED))
        self.assertIsNone(seats.validate_finding(None, "semi-expert", "SIVE", ALLOWED))

    def test_overlong_finding_is_truncated_to_the_word_cap(self):
        f = seats.validate_finding(dict(GOOD, finding=" ".join(["word"] * 200)),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(len(f["finding"].split()), seats.MAX_FINDING_WORDS)

    def test_unknown_confidence_becomes_low(self):
        f = seats.validate_finding(dict(GOOD, confidence="certain"),
                                   "semi-expert", "SIVE", ALLOWED)
        self.assertEqual(f["confidence"], "low")


class TestFindingToThesis(unittest.TestCase):
    def _thesis(self, seat="semi-expert", ticker=None, **over):
        ticker = ticker or GOOD["ticker"]
        raw = dict(GOOD, **over)
        raw["ticker"] = ticker  # keep raw/caller ticker consistent so validation passes
        f = seats.validate_finding(raw, seat, ticker, ALLOWED)
        return seats.finding_to_thesis(f, now=NOW)

    def test_source_is_research_so_the_scorer_treats_it_asymmetrically(self):
        self.assertEqual(self._thesis()["source"], scorer.RESEARCH_SOURCE)

    def test_author_is_the_seat_not_the_analyst(self):
        self.assertEqual(self._thesis()["author"], "semi-expert")

    def test_conviction_is_never_high(self):
        # convictionHits gate tiers. A research thesis must never claim high
        # conviction, belt-and-braces alongside the scorer guard.
        self.assertEqual(self._thesis()["conviction"], "normal")

    def test_direction_and_verification_ride_along(self):
        t = self._thesis()
        self.assertEqual(t["direction"], "bear")
        self.assertEqual(t["verification"], "verified")

    def test_ticker_list_is_exactly_the_reviewed_name(self):
        self.assertEqual(self._thesis()["tickers"], ["SIVE"])

    def test_source_url_is_the_first_basis_entry(self):
        self.assertEqual(self._thesis()["sourceUrl"], GOOD["basis"][0])

    def test_id_has_a_distinct_namespace_from_analyst_ids(self):
        # Never routed through parser.derive_source_id: that can return
        # "x_<tweet id>" and collide with the analyst's own captured thesis
        # for that tweet. Research ids live in their own "r_" namespace.
        self.assertTrue(self._thesis()["id"].startswith("r_"))

    def test_id_is_stable_across_irrelevant_inputs(self):
        # confidence and verification do not participate in the id — the
        # same finding, differing only in confidence, must hash identically.
        a = self._thesis(confidence="high")
        b = self._thesis(confidence="low")
        self.assertEqual(a["id"], b["id"])
        # calling twice with identical inputs must also agree
        self.assertEqual(self._thesis()["id"], self._thesis()["id"])

    def test_id_differs_for_a_different_finding_text(self):
        self.assertNotEqual(self._thesis()["id"],
                            self._thesis(finding="Something else entirely.")["id"])

    def test_id_differs_across_ticker(self):
        # This is exactly the bug that was found: identical seat + identical
        # (often boilerplate, uncited) finding text on two different tickers
        # must not collide, or merge_research_theses drops the second one.
        self.assertNotEqual(self._thesis(ticker="SIVE")["id"],
                            self._thesis(ticker="MU")["id"])

    def test_id_differs_across_seat(self):
        self.assertNotEqual(self._thesis(seat="semi-expert")["id"],
                            self._thesis(seat="pm")["id"])

    def test_text_names_the_seat_so_the_feed_is_readable(self):
        self.assertIn("Semiconductor expert", self._thesis()["text"])

    def test_a_research_thesis_scores_zero_when_bullish(self):
        self.assertEqual(scorer._direction_weight(self._thesis(direction="bull")), 0.0)

    def test_a_research_thesis_subtracts_when_bearish(self):
        self.assertEqual(scorer._direction_weight(self._thesis()), -1.0)

    def test_an_uncited_finding_is_visible_but_inert(self):
        # The verification rule end to end: no basis -> unverified -> forced
        # neutral -> research neutral weighs 0.0. It reaches the brief and
        # cannot move a single number.
        t = self._thesis(basis=[])
        self.assertEqual(t["verification"], "unverified")
        self.assertEqual(t["direction"], "neutral")
        self.assertEqual(scorer._direction_weight(t), 0.0)


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
        picked, _ = seats.select_coverage(
            pri, [self._verdict("CCC")], [], since="2026-07-20", cap=2)
        self.assertEqual(picked[0], "CCC")

    def test_an_unchanged_stance_does_not_qualify(self):
        # The live failure mode: the weekly-review skill rewrites updatedAt on
        # every Core verdict whether or not the stance moved, so a fresh
        # timestamp alone must not buy a review slot.
        pri = self._pri([("AAA", 90), ("CCC", 1)])
        verdicts = [self._verdict("CCC", stance="act", previous="act")]
        picked, _ = seats.select_coverage(
            pri, verdicts, [], since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

    def test_a_previous_stance_differing_only_in_case_does_not_qualify(self):
        # verdicts.json is agent-authored, so "act" vs "Act" is a realistic
        # typo. Without .lower() the same word reads as a stance change and
        # buys a review slot — failing open on exactly the input invariant 3
        # exists for.
        pri = self._pri([("AAA", 90), ("CCC", 1)])
        verdicts = [self._verdict("CCC", stance="act", previous="Act")]
        picked, _ = seats.select_coverage(
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
                  for i in range(seats.NEW_THESIS_TRIGGER)]
        for bad in (None, "", 20260720):
            with self.assertRaises(ValueError, msg=repr(bad)) as ctx:
                seats.select_coverage(pri, [], theses, since=bad, cap=1)
            self.assertIn("since", str(ctx.exception))

    def test_a_missing_previous_stance_does_not_qualify(self):
        # Fails inert until the weekly-review skill starts stamping the field:
        # no history recorded means no *known* change, not an assumed one.
        # Every record in the live store has this shape today.
        pri = self._pri([("AAA", 90), ("CCC", 1)])
        verdicts = [self._verdict("CCC", previous=None)]
        picked, _ = seats.select_coverage(
            pri, verdicts, [], since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

    def test_names_with_enough_new_theses_come_next(self):
        pri = self._pri([("AAA", 90), ("DDD", 2)])
        theses = [thesis("t%d" % i, ["DDD"], "2026-07-24T00:00:00Z")
                  for i in range(3)]
        picked, _ = seats.select_coverage(
            pri, [], theses, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["DDD"])

    def test_remainder_fills_by_score(self):
        pri = self._pri([("AAA", 90), ("BBB", 80), ("CCC", 70)])
        picked, _ = seats.select_coverage(pri, [], [], since="2026-07-20", cap=2)
        self.assertEqual(picked, ["AAA", "BBB"])

    def test_cap_is_respected_and_drops_are_reported(self):
        pri = self._pri([("A%d" % i, 100 - i) for i in range(20)])
        picked, dropped = seats.select_coverage(
            pri, [], [], since="2026-07-20", cap=12)
        self.assertEqual(len(picked), 12)
        self.assertEqual(len(dropped), 8)
        self.assertNotIn(picked[0], dropped)

    def test_no_duplicates_when_a_name_qualifies_twice(self):
        pri = self._pri([("AAA", 90)])
        theses = [thesis("t%d" % i, ["AAA"], "2026-07-24T00:00:00Z")
                  for i in range(5)]
        picked, _ = seats.select_coverage(
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
        picked, _ = seats.select_coverage(
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
        picked, dropped = seats.select_coverage(
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
        n = seats.NEW_THESIS_TRIGGER
        research = [dict(thesis("t%d" % i, ["RRR"], "2026-07-24T00:00:00Z"),
                         source=scorer.RESEARCH_SOURCE) for i in range(n)]
        picked, _ = seats.select_coverage(
            pri, [], research, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

        analyst = [thesis("t%d" % i, ["RRR"], "2026-07-24T00:00:00Z")
                   for i in range(n)]
        picked, _ = seats.select_coverage(
            pri, [], analyst, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["RRR"])

    def test_miscased_research_source_still_does_not_qualify(self):
        # Fails inert, via scorer.is_research: a hand-authored "Research"
        # must not buy coverage that lowercase "research" is denied.
        pri = self._pri([("AAA", 90), ("RRR", 1)])
        research = [dict(thesis("t%d" % i, ["RRR"], "2026-07-24T00:00:00Z"),
                         source="Research")
                    for i in range(seats.NEW_THESIS_TRIGGER)]
        picked, _ = seats.select_coverage(
            pri, [], research, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

    def test_old_verdicts_and_old_theses_do_not_qualify(self):
        # The verdict carries a real stance change, so only its stale date
        # keeps it out — otherwise the cutoff would go untested.
        pri = self._pri([("AAA", 90), ("ZZZ", 1)])
        verdicts = [self._verdict("ZZZ", updated_at="2026-07-01T00:00:00Z")]
        theses = [thesis("t%d" % i, ["ZZZ"], "2026-07-01T00:00:00Z")
                  for i in range(9)]
        picked, _ = seats.select_coverage(
            pri, verdicts, theses, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["AAA"])

    def test_date_only_timestamps_compare_against_a_full_iso_since(self):
        # XFAB really has updatedAt "2026-07-06" while the rest are full ISO,
        # and scorer._parse_dt accepts both. Lexically "2026-07-22" sorts BELOW
        # "2026-07-22T00:00:00Z", so a same-day date-only record would be
        # silently dropped if the two sides were not made commensurable.
        pri = self._pri([("AAA", 90), ("CCC", 1)])
        verdicts = [self._verdict("CCC", updated_at="2026-07-22")]
        picked, _ = seats.select_coverage(
            pri, verdicts, [], since="2026-07-22T00:00:00Z", cap=1)
        self.assertEqual(picked, ["CCC"])

    def test_a_date_only_since_still_admits_full_iso_records(self):
        # The mirror image: date-only on the `since` side, full ISO in the
        # store. Same-day must still qualify.
        pri = self._pri([("AAA", 90), ("CCC", 1)])
        theses = [thesis("t%d" % i, ["CCC"], "2026-07-20T09:30:00Z")
                  for i in range(seats.NEW_THESIS_TRIGGER)]
        picked, _ = seats.select_coverage(
            pri, [], theses, since="2026-07-20", cap=1)
        self.assertEqual(picked, ["CCC"])

    def test_one_short_of_the_trigger_does_not_qualify(self):
        # Pins the lower boundary: >= 3 and >= 2 are otherwise
        # indistinguishable, since every other test uses exactly the trigger.
        pri = self._pri([("AAA", 90), ("DDD", 1)])
        theses = [thesis("t%d" % i, ["DDD"], "2026-07-24T00:00:00Z")
                  for i in range(seats.NEW_THESIS_TRIGGER - 1)]
        picked, _ = seats.select_coverage(
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
            picked, dropped = seats.select_coverage(
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
        out = seats.run_seats(["SIVE", "MU"], {}, self._call_fn(),
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

        out = seats.run_seats(["SIVE"], {}, flaky,
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(len(out["theses"]), 2)
        self.assertEqual(len(out["meta"]["failures"]), 1)
        self.assertEqual(out["meta"]["failures"][0]["ticker"], "SIVE")
        self.assertIn("boom", out["meta"]["failures"][0]["error"])

    def test_a_rejected_finding_is_dropped_not_written(self):
        def bad(system, user):
            return {"finding": "", "ticker": "SIVE"}

        out = seats.run_seats(["SIVE"], {}, bad,
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

        out = seats.run_seats(["SIVE"], {}, wrong_name,
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(out["theses"], [])
        self.assertEqual(out["meta"]["rejected"], 3)
        self.assertEqual(out["meta"]["written"], 0)

    def test_every_written_thesis_is_research_sourced(self):
        out = seats.run_seats(["SIVE"], {}, self._call_fn(),
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertTrue(out["theses"])
        for t in out["theses"]:
            self.assertEqual(t["source"], scorer.RESEARCH_SOURCE)

    def test_theses_by_ticker_reaches_the_prompt(self):
        seen = {}

        def spy(system, user):
            seen["user"] = user
            return dict(GOOD, ticker="SIVE")

        seats.run_seats(["SIVE"],
                        {"SIVE": [thesis("fab-light ramp", ["SIVE"])]},
                        spy, allowed_tickers=ALLOWED, now=NOW)
        self.assertIn("fab-light ramp", seen["user"])

    def test_a_ticker_with_no_context_still_gets_reviewed(self):
        # theses_by_ticker is keyed by canonical symbol; a name the analyst has
        # never posted about is exactly the case the seats exist for.
        out = seats.run_seats(["LITE"], {"SIVE": []}, self._call_fn(),
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(len(out["theses"]), 3)
        self.assertEqual(out["meta"]["rejected"], 0)

    def test_only_seats_restricts_the_run(self):
        out = seats.run_seats(["SIVE"], {}, self._call_fn(),
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
        out = seats.run_seats(["SIVE"], {}, self._call_fn(),
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
        out = seats.run_seats(["SIVE", "MU"], {}, self._call_fn(),
                              allowed_tickers=ALLOWED, now=NOW)
        self.assertEqual(out["meta"]["written"], len(out["theses"]))
        self.assertEqual(out["meta"]["generatedAt"], NOW)
        self.assertEqual(out["meta"]["failures"], [])


if __name__ == "__main__":
    unittest.main()
