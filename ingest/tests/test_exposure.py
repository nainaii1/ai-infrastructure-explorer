"""Tests for the AI-exposure judgement store (PROJECT.md Step 3).

This is the one field in the system that is neither fetched nor computed, so
most of these tests are about what it REFUSES. A percentage that cannot be
attributed must not reach the datastore.
"""

import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import exposure as exp  # noqa: E402


GOOD = {
    "ticker": "NVDA",
    "aiExposure": 88,
    "confidence": "high",
    "basis": "data centre segment dominates the revenue mix",
    "sources": ["FY2026 10-K segment note"],
}


class TestRefusals(unittest.TestCase):
    """A number with no reasoning is indistinguishable from a guess."""

    def test_a_bare_percentage_is_refused(self):
        with self.assertRaises(exp.AssessmentError) as ctx:
            exp.validate_assessment({"ticker": "NVDA", "aiExposure": 88,
                                     "confidence": "high"})
        self.assertIn("basis", str(ctx.exception))

    def test_a_basis_that_says_nothing_is_refused(self):
        for thin in ("obvious", "", "   ", "yes", "high AI"):
            with self.assertRaises(exp.AssessmentError):
                exp.validate_assessment(dict(GOOD, basis=thin))

    def test_missing_confidence_is_refused(self):
        with self.assertRaises(exp.AssessmentError) as ctx:
            exp.validate_assessment({k: v for k, v in GOOD.items()
                                     if k != "confidence"})
        self.assertIn("confidence", str(ctx.exception))

    def test_an_invented_confidence_level_is_refused(self):
        with self.assertRaises(exp.AssessmentError):
            exp.validate_assessment(dict(GOOD, confidence="pretty sure"))

    def test_missing_exposure_is_refused(self):
        with self.assertRaises(exp.AssessmentError):
            exp.validate_assessment({k: v for k, v in GOOD.items()
                                     if k != "aiExposure"})

    def test_missing_ticker_is_refused(self):
        with self.assertRaises(exp.AssessmentError):
            exp.validate_assessment({k: v for k, v in GOOD.items()
                                     if k != "ticker"})

    def test_a_non_dict_is_refused(self):
        for junk in (None, [], "88%", 88):
            with self.assertRaises(exp.AssessmentError):
                exp.validate_assessment(junk)


class TestExposureNormalisation(unittest.TestCase):
    def test_percent_sign_and_strings_are_accepted(self):
        self.assertEqual(exp.normalize_exposure("88%"), 88.0)
        self.assertEqual(exp.normalize_exposure(" 45 "), 45.0)
        self.assertEqual(exp.normalize_exposure(45), 45.0)

    def test_a_fraction_is_refused_rather_than_guessed(self):
        """0.45 could be 45% or half a percent. Guessing on the operator's
        behalf is the kind of quiet decision this project does not make."""
        with self.assertRaises(exp.AssessmentError) as ctx:
            exp.normalize_exposure(0.45)
        self.assertIn("fraction", str(ctx.exception))

    def test_zero_and_one_hundred_are_legal(self):
        self.assertEqual(exp.normalize_exposure(0), 0.0)
        self.assertEqual(exp.normalize_exposure(100), 100.0)

    def test_out_of_range_is_refused(self):
        for bad in (-1, 101, 1000):
            with self.assertRaises(exp.AssessmentError):
                exp.normalize_exposure(bad)

    def test_nonsense_is_refused(self):
        with self.assertRaises(exp.AssessmentError):
            exp.normalize_exposure("lots")

    def test_absent_reads_as_absent_not_zero(self):
        self.assertIsNone(exp.normalize_exposure(None))
        self.assertIsNone(exp.normalize_exposure(""))


class TestAcceptedRecord(unittest.TestCase):
    def test_shape_and_defaults(self):
        rec = exp.validate_assessment(GOOD)
        self.assertEqual(rec["ticker"], "NVDA")
        self.assertEqual(rec["aiExposure"], 88.0)
        self.assertEqual(rec["confidence"], "high")
        self.assertEqual(rec["assessedBy"], "operator")
        self.assertEqual(rec["sources"], ["FY2026 10-K segment note"])

    def test_ticker_is_upper_cased(self):
        self.assertEqual(exp.validate_assessment(dict(GOOD, ticker="nvda"))["ticker"],
                         "NVDA")

    def test_confidence_is_case_insensitive(self):
        self.assertEqual(exp.validate_assessment(dict(GOOD, confidence="HIGH"))["confidence"],
                         "high")

    def test_a_single_source_string_becomes_a_list(self):
        rec = exp.validate_assessment(dict(GOOD, sources="one place"))
        self.assertEqual(rec["sources"], ["one place"])

    def test_optional_fields_only_appear_when_given(self):
        rec = exp.validate_assessment(GOOD)
        self.assertNotIn("contentPerRack", rec)
        rec2 = exp.validate_assessment(dict(GOOD, revenueInflection="H2 2027"))
        self.assertEqual(rec2["revenueInflection"], "H2 2027")

    def test_long_text_is_clipped_not_rejected(self):
        rec = exp.validate_assessment(dict(GOOD, basis="word " * 500))
        self.assertLessEqual(len(rec["basis"]), exp.MAX_BASIS_CHARS)


class TestDerivedAIRevenue(unittest.TestCase):
    FUND = {"currency": "USD", "latest": {"fy": 2026, "revenue": 200e9}}

    def test_revenue_times_exposure(self):
        got = exp.ai_revenue(exp.validate_assessment(GOOD), self.FUND)
        self.assertAlmostEqual(got["value"], 176e9)
        self.assertEqual(got["currency"], "USD")
        self.assertEqual(got["fy"], 2026)

    def test_confidence_travels_with_the_derived_number(self):
        """It multiplies an audited figure by an unaudited one, so no caller
        may render it without knowing how sure the operator was."""
        got = exp.ai_revenue(exp.validate_assessment(GOOD), self.FUND)
        self.assertEqual(got["confidence"], "high")

    def test_half_the_inputs_yields_nothing_rather_than_a_number(self):
        self.assertIsNone(exp.ai_revenue(None, self.FUND))
        self.assertIsNone(exp.ai_revenue(exp.validate_assessment(GOOD), None))
        self.assertIsNone(exp.ai_revenue(exp.validate_assessment(GOOD),
                                         {"currency": "USD"}))

    def test_falls_back_to_the_last_year_when_latest_is_absent(self):
        got = exp.ai_revenue(exp.validate_assessment(GOOD),
                             {"currency": "USD",
                              "years": [{"fy": 2025, "revenue": 100e9}]})
        self.assertAlmostEqual(got["value"], 88e9)

    def test_a_non_numeric_revenue_yields_nothing(self):
        self.assertIsNone(exp.ai_revenue(exp.validate_assessment(GOOD),
                                         {"latest": {"revenue": "lots"}}))


class TestCoverage(unittest.TestCase):
    def test_splits_assessed_from_unassessed(self):
        cov = exp.coverage({"NVDA": {}}, ["NVDA", "AMD", "TSM"])
        self.assertEqual(cov["assessed"], ["NVDA"])
        self.assertEqual(cov["unassessed"], ["AMD", "TSM"])
        self.assertEqual(cov["total"], 3)

    def test_is_stable_between_runs(self):
        a = exp.coverage({}, ["TSM", "AMD", "NVDA"])
        b = exp.coverage({}, ["NVDA", "TSM", "AMD"])
        self.assertEqual(a["unassessed"], b["unassessed"])

    def test_empty_inputs_do_not_raise(self):
        self.assertEqual(exp.coverage(None, None),
                         {"assessed": [], "unassessed": [], "total": 0})


class TestConfidenceRank(unittest.TestCase):
    def test_worst_first_ordering(self):
        self.assertLess(exp.confidence_rank("low"), exp.confidence_rank("high"))
        self.assertEqual(exp.confidence_rank("nonsense"), -1)


class TestPurity(unittest.TestCase):
    def test_module_does_no_network_or_file_io(self):
        src = pathlib.Path(exp.__file__).read_text()
        for banned in ("urllib", "requests", "socket", "open(", "pathlib", "json"):
            self.assertNotIn(banned, src, "exposure.py must stay pure")


class TestNothingIsInvented(unittest.TestCase):
    """The module must never supply a value the operator did not give."""

    def test_no_default_exposure_anywhere_in_the_source(self):
        src = pathlib.Path(exp.__file__).read_text()
        self.assertNotIn("aiExposure=", src)
        self.assertNotIn('"aiExposure": 0', src)

    def test_an_unassessed_name_stays_absent_rather_than_zero(self):
        cov = exp.coverage({}, ["NVDA"])
        self.assertEqual(cov["assessed"], [])
        self.assertIsNone(exp.ai_revenue({}, {"latest": {"revenue": 1e9}}))


if __name__ == "__main__":
    unittest.main()
