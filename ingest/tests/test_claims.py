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


if __name__ == "__main__":
    unittest.main()
