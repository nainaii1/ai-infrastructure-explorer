import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import claims  # noqa: E402

MADE = "2026-07-22"
ALLOWED = {"SIVE", "MU", "AAOI"}

RAW = {
    "claim": "AAOI reaches $1.4B quarterly revenue.",
    "testableBy": "Reported quarterly revenue >= $1.4B on or before judgeBy.",
    "judgeBy": "2027-10-31",
    "thesisId": "h_abc123",
}


def raw(**kw):
    r = dict(RAW)
    r.update(kw)
    return r


class TestValidateClaim(unittest.TestCase):
    def test_a_good_claim_passes_through_and_opens(self):
        c = claims.validate_claim(RAW, "pm", "AAOI", ALLOWED, MADE)
        self.assertEqual(c["status"], "open")
        self.assertEqual(c["source"], "pm")
        self.assertEqual(c["ticker"], "AAOI")
        self.assertEqual(c["madeAt"], MADE)
        self.assertEqual(c["judgeBy"], "2027-10-31")
        self.assertIsNone(c["judgedAt"])
        self.assertIsNone(c["evidence"])

    def test_source_and_ticker_come_from_the_caller_not_the_model(self):
        # The text being read is untrusted. A claim filed against the wrong
        # source corrupts the exact measurement this ledger exists to produce.
        c = claims.validate_claim(
            raw(source="analyst", ticker="MU"), "pm", "AAOI", ALLOWED, MADE)
        self.assertEqual(c["source"], "pm")
        self.assertEqual(c["ticker"], "AAOI")

    def test_a_model_supplied_status_is_ignored(self):
        c = claims.validate_claim(
            raw(status="correct", judgedAt="2026-07-22", evidence=["x"]),
            "pm", "AAOI", ALLOWED, MADE)
        self.assertEqual(c["status"], "open")
        self.assertIsNone(c["judgedAt"])
        self.assertIsNone(c["evidence"])

    def test_a_macro_claim_may_have_no_ticker(self):
        c = claims.validate_claim(RAW, "analyst", None, ALLOWED, MADE)
        self.assertIsNone(c["ticker"])
        self.assertEqual(c["status"], "open")

    def test_a_ticker_outside_the_universe_is_rejected(self):
        self.assertIsNone(
            claims.validate_claim(RAW, "pm", "TSLA", ALLOWED, MADE))

    def test_empty_claim_text_is_rejected(self):
        self.assertIsNone(
            claims.validate_claim(raw(claim="   "), "pm", "AAOI", ALLOWED, MADE))

    def test_a_non_dict_is_rejected(self):
        for bad in ("nope", None, 7, []):
            self.assertIsNone(
                claims.validate_claim(bad, "pm", "AAOI", ALLOWED, MADE))

    # --- the falsifiability rule: recorded, not discarded -----------------

    def test_a_missing_judge_by_is_unfalsifiable_not_rejected(self):
        # "We're close to the bottom" is a real thing a source says. It must
        # be counted, not dropped — the unfalsifiable share is the point.
        c = claims.validate_claim(raw(judgeBy=None), "analyst", "AAOI",
                                  ALLOWED, MADE)
        self.assertEqual(c["status"], "unfalsifiable")
        self.assertIsNone(c["judgeBy"])

    def test_an_unparseable_judge_by_is_unfalsifiable(self):
        c = claims.validate_claim(raw(judgeBy="soon"), "analyst", "AAOI",
                                  ALLOWED, MADE)
        self.assertEqual(c["status"], "unfalsifiable")
        self.assertIsNone(c["judgeBy"])

    def test_a_judge_by_not_after_made_at_is_unfalsifiable(self):
        # A prediction that settles on or before the day it was made is not a
        # prediction. Both the same-day and the backwards case.
        for bad in (MADE, "2026-07-01"):
            c = claims.validate_claim(raw(judgeBy=bad), "pm", "AAOI",
                                      ALLOWED, MADE)
            self.assertEqual(c["status"], "unfalsifiable", bad)
            self.assertIsNone(c["judgeBy"], bad)

    def test_an_empty_testable_by_is_unfalsifiable(self):
        c = claims.validate_claim(raw(testableBy="  "), "pm", "AAOI",
                                  ALLOWED, MADE)
        self.assertEqual(c["status"], "unfalsifiable")

    def test_a_full_iso_judge_by_is_accepted_and_normalized(self):
        c = claims.validate_claim(raw(judgeBy="2027-10-31T00:00:00Z"), "pm",
                                  "AAOI", ALLOWED, MADE)
        self.assertEqual(c["status"], "open")
        self.assertEqual(c["judgeBy"], "2027-10-31")

    # --- caller-controlled arguments raise rather than fail quietly -------

    def test_an_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            claims.validate_claim(RAW, "chief-vibes-officer", "AAOI",
                                  ALLOWED, MADE)

    def test_an_unreadable_made_at_raises(self):
        # Same reasoning as select_coverage's `since`: the caller controls
        # this, and there is no inert reading of "no date" for the day a
        # prediction was made.
        for bad in (None, "", "yesterday", 20260722):
            with self.assertRaises(ValueError):
                claims.validate_claim(RAW, "pm", "AAOI", ALLOWED, bad)


class TestClaimId(unittest.TestCase):
    def test_the_same_claim_extracted_twice_gets_the_same_id(self):
        a = claims.validate_claim(RAW, "pm", "AAOI", ALLOWED, MADE)
        b = claims.validate_claim(RAW, "pm", "AAOI", ALLOWED, MADE)
        self.assertEqual(a["id"], b["id"])

    def test_id_changes_with_source_ticker_text_and_date(self):
        base = claims.validate_claim(RAW, "pm", "AAOI", ALLOWED, MADE)["id"]
        variants = [
            claims.validate_claim(RAW, "fundamental", "AAOI", ALLOWED, MADE),
            claims.validate_claim(RAW, "pm", "MU", ALLOWED, MADE),
            claims.validate_claim(raw(claim="Something else entirely."),
                                  "pm", "AAOI", ALLOWED, MADE),
            claims.validate_claim(RAW, "pm", "AAOI", ALLOWED, "2026-07-23"),
        ]
        for v in variants:
            self.assertNotEqual(v["id"], base)

    def test_a_macro_claim_id_is_stable(self):
        a = claims.validate_claim(RAW, "analyst", None, ALLOWED, MADE)
        b = claims.validate_claim(RAW, "analyst", None, ALLOWED, MADE)
        self.assertEqual(a["id"], b["id"])


class TestMergeClaims(unittest.TestCase):
    def _claim(self, **kw):
        c = claims.validate_claim(RAW, "pm", "AAOI", ALLOWED, MADE)
        c.update(kw)
        return c

    def test_a_new_claim_is_appended(self):
        merged = claims.merge_claims([], [self._claim()])
        self.assertEqual(len(merged), 1)

    def test_re_extraction_is_idempotent(self):
        c = self._claim()
        merged = claims.merge_claims([c], [self._claim()])
        self.assertEqual(len(merged), 1)

    def test_a_judged_claim_survives_re_extraction_intact(self):
        # The whole reason the ledger is re-runnable. A re-extraction that
        # reset a decided claim to "open" would erase the only record of what
        # the desk actually believed and how it turned out.
        judged = self._claim(status="correct", judgedAt="2027-11-01",
                             evidence=["https://www.sec.gov/x.htm"])
        merged = claims.merge_claims([judged], [self._claim()])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["status"], "correct")
        self.assertEqual(merged[0]["judgedAt"], "2027-11-01")
        self.assertEqual(merged[0]["evidence"], ["https://www.sec.gov/x.htm"])

    def test_a_different_claim_is_added_alongside(self):
        other = claims.validate_claim(raw(claim="A different prediction."),
                                      "pm", "AAOI", ALLOWED, MADE)
        merged = claims.merge_claims([self._claim()], [other])
        self.assertEqual(len(merged), 2)

    def test_an_incoming_claim_without_an_id_raises(self):
        for bad in (None, "", 7):
            with self.assertRaises(ValueError):
                claims.merge_claims([], [self._claim(id=bad)])

    def test_an_incoming_claim_with_an_unknown_source_raises(self):
        with self.assertRaises(ValueError):
            claims.merge_claims([], [self._claim(source="chief-vibes-officer")])

    def test_the_input_list_and_its_records_are_not_mutated(self):
        existing = [self._claim()]
        merged = claims.merge_claims(existing, [])
        merged[0]["status"] = "tampered"
        self.assertEqual(len(existing), 1)
        self.assertEqual(existing[0]["status"], "open")


def item(ticker="AAOI", text="AAOI guides to $1.4B by Q4 2027.",
         made_at=MADE, thesis_id="h_abc123"):
    return {"ticker": ticker, "text": text, "madeAt": made_at,
            "thesisId": thesis_id}


class TestBuildExtractPrompt(unittest.TestCase):
    def test_prompt_names_the_source_and_ticker(self):
        system, user = claims.build_extract_prompt("analyst", "AAOI", "text here")
        self.assertIn("AAOI", user)
        self.assertIn("text here", user)

    def test_prompt_wraps_the_text_in_delimiters_and_calls_it_untrusted(self):
        system, user = claims.build_extract_prompt("analyst", "AAOI", "hello")
        self.assertIn("<<<POST>>>", user)
        self.assertIn("<<<END POST>>>", user)
        self.assertIn("untrusted", system.lower())

    def test_prompt_clips_a_long_post(self):
        system, user = claims.build_extract_prompt("analyst", "AAOI", "x" * 9000)
        self.assertIn("x" * claims.MAX_POST_CHARS, user)
        self.assertNotIn("x" * (claims.MAX_POST_CHARS + 1), user)

    def test_prompt_forbids_inventing_a_settlement_date(self):
        # If the model manufactures a judgeBy for a vague statement, the
        # unfalsifiable share silently understates how vague a source is,
        # which is the one number this ledger exists to keep honest.
        system, _ = claims.build_extract_prompt("analyst", "AAOI", "x")
        self.assertIn("judgeBy", system)
        self.assertIn("do not invent", system.lower())

    def test_a_macro_item_has_no_ticker(self):
        _, user = claims.build_extract_prompt("analyst", None, "macro take")
        self.assertIn("macro take", user)


class TestExtractClaims(unittest.TestCase):
    def _call_fn(self, n=1):
        def call_fn(system, user):
            return {"claims": [dict(RAW, claim="Prediction {}.".format(i))
                               for i in range(n)]}
        return call_fn

    def test_one_call_per_item(self):
        calls_made = []

        def spy(system, user):
            calls_made.append(user)
            return {"claims": []}

        claims.extract_claims([item(), item(ticker="MU")], spy,
                              allowed_tickers=ALLOWED, source="analyst")
        self.assertEqual(len(calls_made), 2)

    def test_every_claim_carries_the_pinned_source(self):
        out = claims.extract_claims([item()], self._call_fn(2),
                                    allowed_tickers=ALLOWED, source="pm")
        self.assertEqual(len(out["claims"]), 2)
        for c in out["claims"]:
            self.assertEqual(c["source"], "pm")

    def test_the_ticker_and_date_come_from_the_item_not_the_model(self):
        def wrong_name(system, user):
            return {"claims": [dict(RAW, ticker="MU", madeAt="1999-01-01")]}

        out = claims.extract_claims([item(ticker="AAOI")], wrong_name,
                                    allowed_tickers=ALLOWED, source="analyst")
        self.assertEqual(out["claims"][0]["ticker"], "AAOI")
        self.assertEqual(out["claims"][0]["madeAt"], MADE)

    def test_a_failing_call_does_not_abort_the_run(self):
        state = {"n": 0}

        def flaky(system, user):
            state["n"] += 1
            if state["n"] == 1:
                raise RuntimeError("boom")
            return {"claims": [dict(RAW)]}

        out = claims.extract_claims([item(), item(ticker="MU")], flaky,
                                    allowed_tickers=ALLOWED, source="analyst")
        self.assertEqual(len(out["claims"]), 1)
        self.assertEqual(len(out["meta"]["failures"]), 1)
        self.assertIn("boom", out["meta"]["failures"][0]["error"])

    def test_a_rejected_claim_is_counted_not_written(self):
        def empty_text(system, user):
            return {"claims": [dict(RAW, claim="   ")]}

        out = claims.extract_claims([item()], empty_text,
                                    allowed_tickers=ALLOWED, source="analyst")
        self.assertEqual(out["claims"], [])
        self.assertEqual(out["meta"]["rejected"], 1)

    def test_a_malformed_response_is_survived(self):
        for bad in ({"claims": "not a list"}, {}, None, "nope", {"claims": [7]}):
            out = claims.extract_claims([item()], lambda s, u: bad,
                                        allowed_tickers=ALLOWED,
                                        source="analyst")
            self.assertEqual(out["claims"], [], repr(bad))

    def test_an_unfalsifiable_claim_is_kept_and_counted(self):
        def vague(system, user):
            return {"claims": [dict(RAW, judgeBy=None)]}

        out = claims.extract_claims([item()], vague,
                                    allowed_tickers=ALLOWED, source="analyst")
        self.assertEqual(len(out["claims"]), 1)
        self.assertEqual(out["claims"][0]["status"], "unfalsifiable")
        self.assertEqual(out["meta"]["rejected"], 0)

    def test_meta_counts_agree_with_what_was_written(self):
        out = claims.extract_claims([item(), item(ticker="MU")],
                                    self._call_fn(2),
                                    allowed_tickers=ALLOWED, source="analyst")
        self.assertEqual(out["meta"]["written"], len(out["claims"]))
        self.assertEqual(out["meta"]["itemsProcessed"], 2)
        self.assertEqual(out["meta"]["source"], "analyst")

    def test_an_unknown_source_raises_before_any_call(self):
        def boom(system, user):
            raise AssertionError("must not be called")

        with self.assertRaises(ValueError):
            claims.extract_claims([item()], boom, allowed_tickers=ALLOWED,
                                  source="chief-vibes-officer")


CITE = "https://www.sec.gov/Archives/edgar/data/1/x.htm"


def open_claim(**kw):
    c = claims.validate_claim(RAW, "pm", "AAOI", ALLOWED, MADE)
    c.update(kw)
    return c


class TestRipeClaims(unittest.TestCase):
    def test_a_claim_is_ripe_on_and_after_its_judge_by(self):
        c = open_claim(judgeBy="2027-10-31")
        for today in ("2027-10-31", "2027-11-01"):
            self.assertEqual(claims.ripe_claims([c], today), [c], today)

    def test_a_claim_is_not_ripe_before_its_judge_by(self):
        c = open_claim(judgeBy="2027-10-31")
        self.assertEqual(claims.ripe_claims([c], "2027-10-30"), [])

    def test_an_unfalsifiable_claim_is_never_ripe(self):
        c = open_claim(status="unfalsifiable", judgeBy=None)
        self.assertEqual(claims.ripe_claims([c], "2099-01-01"), [])

    def test_an_already_judged_claim_is_not_ripe(self):
        c = open_claim(status="correct", judgedAt="2027-11-01")
        self.assertEqual(claims.ripe_claims([c], "2099-01-01"), [])

    def test_an_unreadable_judge_by_is_not_ripe(self):
        # Fails inert: an unreadable date must not drag a claim into a
        # judging pass that would then guess at it.
        for bad in (None, "", "soon", 20271031):
            c = open_claim(judgeBy=bad)
            self.assertEqual(claims.ripe_claims([c], "2099-01-01"), [], repr(bad))

    def test_an_unreadable_today_raises(self):
        with self.assertRaises(ValueError):
            claims.ripe_claims([open_claim()], "whenever")


class TestApplyJudgement(unittest.TestCase):
    def _judge(self, verdict, basis=(CITE,), today="2027-11-01", claim=None):
        return claims.apply_judgement(
            claim or open_claim(judgeBy="2027-10-31"),
            {"verdict": verdict, "basis": list(basis), "evidenceNote": "n"},
            today)

    def test_a_cited_correct_verdict_is_recorded(self):
        c = self._judge("correct")
        self.assertEqual(c["status"], "correct")
        self.assertEqual(c["judgedAt"], "2027-11-01")
        self.assertEqual(c["evidence"], [CITE])

    def test_a_cited_wrong_verdict_is_recorded(self):
        self.assertEqual(self._judge("wrong")["status"], "wrong")

    def test_an_uncited_correct_verdict_leaves_the_claim_open(self):
        # C3. The desk is judging its own predictions, which is exactly when
        # an invented citation is most tempting and least likely to be checked.
        for basis in ([], ["not a url"], ["https://"], ["https://x"]):
            c = self._judge("correct", basis=basis)
            self.assertEqual(c["status"], "open", repr(basis))
            self.assertIsNone(c["judgedAt"], repr(basis))

    def test_an_uncited_wrong_verdict_also_leaves_it_open(self):
        self.assertEqual(self._judge("wrong", basis=[])["status"], "open")

    def test_unfalsifiable_needs_no_citation(self):
        # Nothing could settle it, so there is nothing to cite. Recording it
        # is the point (C2).
        c = self._judge("unfalsifiable", basis=[])
        self.assertEqual(c["status"], "unfalsifiable")
        self.assertEqual(c["judgedAt"], "2027-11-01")

    def test_an_unknown_verdict_leaves_the_claim_open(self):
        for bad in ("right", "CORRECT", "", None, 7, "true"):
            c = self._judge(bad)
            self.assertEqual(c["status"], "open", repr(bad))

    def test_judging_before_the_judge_by_date_raises(self):
        with self.assertRaises(ValueError):
            self._judge("correct", today="2027-10-30")

    def test_re_judging_a_decided_claim_raises(self):
        # C4. A silently flipped verdict destroys the only record of what the
        # desk believed and how it turned out.
        decided = open_claim(judgeBy="2027-10-31", status="correct",
                             judgedAt="2027-11-01")
        with self.assertRaises(ValueError):
            self._judge("wrong", claim=decided)

    def test_the_input_claim_is_not_mutated(self):
        c = open_claim(judgeBy="2027-10-31")
        self._judge("correct", claim=c)
        self.assertEqual(c["status"], "open")
        self.assertIsNone(c["judgedAt"])


class TestScoreClaims(unittest.TestCase):
    def _set(self):
        return [
            open_claim(status="correct"), open_claim(status="correct"),
            open_claim(status="wrong"),
            open_claim(status="open"),
            open_claim(status="unfalsifiable"),
        ]

    def test_hit_rate_excludes_open_and_unfalsifiable(self):
        s = claims.score_claims(self._set())
        self.assertEqual(s["correct"], 2)
        self.assertEqual(s["wrong"], 1)
        self.assertEqual(s["judged"], 3)
        self.assertAlmostEqual(s["hitRate"], 2 / 3)

    def test_unfalsifiable_share_is_over_the_whole_set(self):
        s = claims.score_claims(self._set())
        self.assertEqual(s["total"], 5)
        self.assertAlmostEqual(s["unfalsifiableShare"], 1 / 5)

    def test_no_judged_claims_gives_a_null_hit_rate_not_zero(self):
        # 0.0 reads as "always wrong". Nothing judged is not a bad record,
        # it is no record, and the two must not look the same.
        s = claims.score_claims([open_claim(status="open")])
        self.assertIsNone(s["hitRate"])

    def test_an_empty_set_is_all_null(self):
        s = claims.score_claims([])
        self.assertEqual(s["total"], 0)
        self.assertIsNone(s["hitRate"])
        self.assertIsNone(s["unfalsifiableShare"])

    def test_a_source_that_only_says_untestable_things_scores_no_hit_rate(self):
        s = claims.score_claims([open_claim(status="unfalsifiable")] * 4)
        self.assertIsNone(s["hitRate"])
        self.assertEqual(s["unfalsifiableShare"], 1.0)

    def test_filtering_by_source(self):
        mixed = [open_claim(status="correct"),
                 open_claim(source="analyst", status="wrong")]
        s = claims.score_claims(mixed, source="analyst")
        self.assertEqual(s["source"], "analyst")
        self.assertEqual(s["total"], 1)
        self.assertEqual(s["wrong"], 1)
        self.assertEqual(s["hitRate"], 0.0)

    def test_the_share_always_comes_back_with_the_rate(self):
        # C2: no caller can render a hit rate without the honesty figure.
        self.assertIn("unfalsifiableShare", claims.score_claims(self._set()))


class TestRateMeaningfulness(unittest.TestCase):
    """Small samples lie. A rate resting on three data points is not a rate."""

    def _n(self, correct, wrong):
        return ([open_claim(status="correct")] * correct +
                [open_claim(status="wrong")] * wrong)

    def test_a_rate_below_the_threshold_is_flagged_not_meaningful(self):
        s = claims.score_claims(self._n(2, 1))
        self.assertEqual(s["judged"], 3)
        self.assertIsNotNone(s["hitRate"])
        self.assertFalse(s["rateIsMeaningful"])

    def test_a_rate_at_the_threshold_is_meaningful(self):
        n = claims.MIN_JUDGED_FOR_RATE
        s = claims.score_claims(self._n(n - 2, 2))
        self.assertEqual(s["judged"], n)
        self.assertTrue(s["rateIsMeaningful"])

    def test_nothing_judged_is_never_meaningful(self):
        s = claims.score_claims([open_claim(status="open")])
        self.assertIsNone(s["hitRate"])
        self.assertFalse(s["rateIsMeaningful"])


class TestClaimsMoveNoNumber(unittest.TestCase):
    """C1 — in Phase 3 the ledger observes; it does not vote.

    Hit-rate weighting is Phase 4 and is gated on real judged outcomes. Until
    then a claim must not reach any score or tier, by any route. This is
    invariant 2 in claims clothing: a new aggregate arrived, so it gets a
    guard before anything can read it.
    """

    def test_the_scorer_does_not_import_or_read_claims(self):
        import scorer
        self.assertFalse(hasattr(scorer, "claims"))
        src = pathlib.Path(scorer.__file__).read_text()
        self.assertNotIn("import claims", src)
        self.assertNotIn("claims.json", src)

    def test_priorities_and_tiers_are_identical_with_and_without_claims(self):
        import json
        import scorer
        import generate_data_js as gen

        theses = json.loads((gen.STORE / "theses.json").read_text())
        base = json.loads((gen.STORE / "base.json").read_text())
        tickers = json.loads((gen.STORE / "tickers.json").read_text())
        syms = [t["ticker"] for t in tickers]
        canon = scorer.canonicalize_theses(
            theses, base.get("tickerAliases"), base.get("themeTags"))

        from datetime import datetime, timezone
        fixed = datetime(2026, 7, 28, tzinfo=timezone.utc)
        before = scorer.compute_priorities(canon, now=fixed)
        before_tiers = scorer.assign_tiers(syms, before)

        # A populated ledger, including judged claims, must change nothing.
        ledger = [
            claims.validate_claim(RAW, "pm", "AAOI", set(syms), MADE),
            claims.validate_claim(raw(claim="Another one."), "analyst",
                                  "SIVE", set(syms), MADE),
        ]
        ledger[0]["status"] = "correct"
        self.assertTrue(all(ledger))

        after = scorer.compute_priorities(canon, now=fixed)
        self.assertEqual(before, after)
        self.assertEqual(before_tiers, scorer.assign_tiers(syms, after))


if __name__ == "__main__":
    unittest.main()
