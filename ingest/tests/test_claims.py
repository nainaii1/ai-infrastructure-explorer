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


if __name__ == "__main__":
    unittest.main()
