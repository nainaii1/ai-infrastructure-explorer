"""Tests for the SEC XBRL revenue parser (PROJECT.md Step 2).

Fixtures are real `companyfacts` payloads trimmed to the revenue concepts, so
these exercise the actual filing shape — including the two traps that make a
naive reader wrong: NVDA's migrated revenue tag and TSM's dual currency.
No network (invariant 6: fundamentals.py is pure).
"""

import json
import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import fundamentals as fund  # noqa: E402

FIXTURES = pathlib.Path(__file__).resolve().parent / "fixtures"


def fixture(name):
    return json.loads((FIXTURES / ("companyfacts_%s.json" % name)).read_text())


class TestAnnualRowDetection(unittest.TestCase):
    def test_a_full_year_from_a_10k_counts(self):
        self.assertTrue(fund.is_annual_row(
            {"form": "10-K", "start": "2025-01-27", "end": "2026-01-25"}))

    def test_a_quarter_does_not(self):
        self.assertFalse(fund.is_annual_row(
            {"form": "10-K", "start": "2025-10-27", "end": "2026-01-25"}))

    def test_a_two_year_span_does_not(self):
        self.assertFalse(fund.is_annual_row(
            {"form": "10-K", "start": "2024-01-29", "end": "2026-01-25"}))

    def test_a_quarterly_form_does_not(self):
        self.assertFalse(fund.is_annual_row(
            {"form": "10-Q", "start": "2025-01-27", "end": "2026-01-25"}))

    def test_a_53_week_retail_year_still_counts(self):
        self.assertTrue(fund.is_annual_row(
            {"form": "10-K", "start": "2025-01-26", "end": "2026-01-25"}))

    def test_junk_rows_are_rejected_not_raised_on(self):
        for row in (None, {}, {"form": "10-K"}, "nope",
                    {"form": "10-K", "start": "x", "end": "y"}):
            self.assertFalse(fund.is_annual_row(row))


class TestFiscalYear(unittest.TestCase):
    def test_year_comes_from_the_period_end(self):
        self.assertEqual(fund.fiscal_year("2026-01-25"), 2026)
        self.assertEqual(fund.fiscal_year("2024-12-31"), 2024)

    def test_unparseable_end_returns_none(self):
        self.assertIsNone(fund.fiscal_year(None))
        self.assertIsNone(fund.fiscal_year("later"))


class TestTagSelection(unittest.TestCase):
    def test_nvda_picks_the_tag_that_is_still_maintained(self):
        """The trap: NVDA migrated to `Revenues`, but the older
        RevenueFromContractWithCustomerExcludingAssessedTax is still in the
        payload and stops at FY2022. A fixed priority order returns a series
        four years stale."""
        taxonomy, tag, unit, rows = fund.pick_series(fixture("NVDA"))
        self.assertEqual((taxonomy, tag, unit), ("us-gaap", "Revenues", "USD"))
        self.assertEqual(rows[-1]["fy"], 2026)

    def test_the_stale_tag_really_is_stale(self):
        """Guards the guard — if this stops being true the test above is vacuous."""
        stale = fund.series_for(
            fixture("NVDA"), "us-gaap",
            "RevenueFromContractWithCustomerExcludingAssessedTax", "USD")
        self.assertTrue(stale)
        self.assertLess(stale[-1]["fy"], 2026)

    def test_a_revenue_shaped_but_wrong_concept_is_never_picked(self):
        """`BusinessAcquisitionsProFormaRevenue` sorts earlier alphabetically
        than the real tag; an allowlist beats a substring search."""
        _tax, tag, _unit, _rows = fund.pick_series(fixture("NVDA"))
        self.assertNotIn("ProForma", tag)

    def test_tsm_prefers_usd_over_the_filing_currency(self):
        taxonomy, tag, unit, rows = fund.pick_series(fixture("TSM"))
        self.assertEqual((taxonomy, tag, unit), ("ifrs-full", "Revenue", "USD"))
        self.assertTrue(all(r["revenue"] < 1e12 for r in rows),
                        "a TWD figure leaked into the USD series")

    def test_twd_series_exists_so_the_preference_is_a_real_choice(self):
        twd = fund.series_for(fixture("TSM"), "ifrs-full", "Revenue", "TWD")
        self.assertTrue(twd)

    def test_empty_payload_picks_nothing(self):
        self.assertIsNone(fund.pick_series({}))
        self.assertIsNone(fund.pick_series(None))
        self.assertIsNone(fund.pick_series({"facts": {"us-gaap": {}}}))


class TestRestatementDedupe(unittest.TestCase):
    def test_one_row_per_period_keeping_the_latest_filing(self):
        payload = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            {"form": "10-K", "start": "2024-01-29", "end": "2025-01-26",
             "val": 100, "filed": "2025-02-26"},
            {"form": "10-K", "start": "2024-01-29", "end": "2025-01-26",
             "val": 130497000000, "filed": "2026-02-25"},
        ]}}}}}
        rows = fund.series_for(payload, "us-gaap", "Revenues", "USD")
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["revenue"], 130497000000)

    def test_row_fy_is_ignored_in_favour_of_the_period(self):
        """NVDA's FY2021 revenue carries "fy": 2022 because a later 10-K
        restated it. Trusting `fy` mislabels the whole series by a year."""
        payload = {"facts": {"us-gaap": {"Revenues": {"units": {"USD": [
            {"form": "10-K", "start": "2020-01-27", "end": "2021-01-31",
             "val": 16675000000, "fy": 2022, "fp": "FY", "filed": "2022-03-18"},
        ]}}}}}
        rows = fund.series_for(payload, "us-gaap", "Revenues", "USD")
        self.assertEqual(rows[0]["fy"], 2021)


class TestGrowth(unittest.TestCase):
    def test_yoy_and_cagr_off_the_real_series(self):
        rec = fund.summarize(fixture("NVDA"), "NVDA")
        self.assertAlmostEqual(rec["growth"]["yoy"], 215938 / 130497 - 1, places=4)
        self.assertIsNotNone(rec["growth"]["cagr3y"])

    def test_too_little_history_returns_none_not_zero(self):
        self.assertEqual(fund.growth([]), {"yoy": None, "cagr3y": None})
        self.assertEqual(fund.growth([{"revenue": 5}]),
                         {"yoy": None, "cagr3y": None})

    def test_a_non_positive_base_year_yields_no_rate(self):
        g = fund.growth([{"revenue": 0}, {"revenue": 100}])
        self.assertIsNone(g["yoy"])
        g = fund.growth([{"revenue": -10}, {"revenue": 100}])
        self.assertIsNone(g["yoy"])


class TestNameGuard(unittest.TestCase):
    """A ticker symbol is not a stable key across venues."""

    def test_the_ccxi_collision_is_rejected(self):
        self.assertFalse(fund.names_match(
            "Agility Robotics", "Churchill Capital Corp XI", "CCXI"))

    def test_a_rename_to_the_ticker_is_accepted(self):
        self.assertTrue(fund.names_match("Iris Energy", "IREN Limited", "IREN"))

    def test_the_rename_would_fail_without_the_ticker_evidence(self):
        self.assertFalse(fund.names_match("Iris Energy", "IREN Limited"))

    def test_legal_suffixes_do_not_block_a_match(self):
        self.assertTrue(fund.names_match("Micron Technology", "MICRON TECHNOLOGY INC"))
        self.assertTrue(fund.names_match("Nokia", "Nokia Corporation"))

    def test_generic_words_alone_are_not_a_match(self):
        """Two unrelated companies both called "... Technology Inc" must not
        match on the noise words."""
        self.assertFalse(fund.names_match("Alpha Technology Inc",
                                          "Beta Technology Inc"))

    def test_unknown_is_not_a_match(self):
        self.assertFalse(fund.names_match("", "Nokia Corporation"))
        self.assertFalse(fund.names_match("Nokia", ""))
        self.assertFalse(fund.names_match(None, None))

    def test_summarize_refuses_a_mismatched_payload(self):
        self.assertIsNone(fund.summarize(fixture("NVDA"), "CCXI",
                                         tracked_name="Agility Robotics"))

    def test_summarize_still_returns_when_the_name_agrees(self):
        rec = fund.summarize(fixture("NVDA"), "NVDA", tracked_name="NVIDIA")
        self.assertIsNotNone(rec)
        self.assertEqual(rec["latest"]["fy"], 2026)

    def test_guard_is_opt_in_so_an_identified_caller_is_not_blocked(self):
        self.assertIsNotNone(fund.summarize(fixture("NVDA"), "NVDA"))


class TestSummarize(unittest.TestCase):
    def test_record_shape(self):
        rec = fund.summarize(fixture("TSM"), "TSM", cik="0001046179",
                             fetched_at="2026-08-21T00:00:00Z")
        for key in ("ticker", "cik", "entityName", "taxonomy", "tag",
                    "currency", "years", "latest", "growth", "fetchedAt"):
            self.assertIn(key, rec)
        self.assertEqual(rec["ticker"], "TSM")
        self.assertEqual(rec["currency"], "USD")
        self.assertEqual(rec["latest"], rec["years"][-1])

    def test_history_is_capped_and_ordered_oldest_first(self):
        rec = fund.summarize(fixture("NVDA"), "NVDA")
        self.assertLessEqual(len(rec["years"]), fund.MAX_YEARS)
        years = [r["fy"] for r in rec["years"]]
        self.assertEqual(years, sorted(years))

    def test_nothing_filed_returns_none_rather_than_a_zero(self):
        self.assertIsNone(fund.summarize({"entityName": "X", "facts": {}}, "X"))


class TestPurity(unittest.TestCase):
    def test_module_does_no_network_or_file_io(self):
        """Invariant 6 — the parsing must stay testable without a network."""
        src = (pathlib.Path(fund.__file__)).read_text()
        for banned in ("urllib", "requests", "socket", "open(", "pathlib"):
            self.assertNotIn(banned, src, "fundamentals.py must stay pure")


if __name__ == "__main__":
    unittest.main()
