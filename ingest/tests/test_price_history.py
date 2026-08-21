"""Tests for the append-only daily price record.

The record exists so the desk can eventually answer "what happened AFTER he
argued this" — so most of these are about not corrupting it: no zero prices,
no double-counting a day, no silently mixing an approximate anchor with an
observed close.

Invariant 7: nothing here writes under ingest/store/ — the file path is
monkeypatched to a temp dir.
"""

import sys
import json
import pathlib
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import price_history as ph  # noqa: E402
import record_prices as rec  # noqa: E402


SNAPSHOT = {
    "NVDA": {"price": 200.0, "currency": "USD", "chg7d": 0.0,
             "chg1m": 100.0, "chg1y": 300.0, "asOf": "2026-08-21T13:00:00Z"},
    "SIVE": {"price": 50.0, "currency": "SEK", "chg1m": -50.0},
    "DEAD": {"price": 0, "currency": "USD"},
    "JUNK": {"price": "n/a", "currency": "USD"},
    "NOTADICT": "nope",
}


class TestRowBuilding(unittest.TestCase):
    def test_a_good_row(self):
        r = ph.make_row("2026-08-21T13:00:00Z", "nvda", 200.0, "usd")
        self.assertEqual(r, {"date": "2026-08-21", "ticker": "NVDA",
                             "close": 200.0, "currency": "USD",
                             "source": ph.SOURCE_OBSERVED})

    def test_a_zero_or_negative_close_is_dropped(self):
        """A stored 0 would silently poison every return computed through it."""
        self.assertIsNone(ph.make_row("2026-08-21", "X", 0))
        self.assertIsNone(ph.make_row("2026-08-21", "X", -5))

    def test_junk_is_dropped_not_raised_on(self):
        for bad in (None, "n/a", "", float("nan"), float("inf")):
            self.assertIsNone(ph.make_row("2026-08-21", "X", bad))
        self.assertIsNone(ph.make_row("2026-08-21", "", 10))
        self.assertIsNone(ph.make_row("", "X", 10))


class TestSnapshotRows(unittest.TestCase):
    def test_only_usable_names_are_recorded(self):
        rows = ph.rows_from_snapshot(SNAPSHOT, "2026-08-21T13:00:00Z")
        self.assertEqual(sorted(r["ticker"] for r in rows), ["NVDA", "SIVE"])

    def test_currency_is_carried(self):
        rows = {r["ticker"]: r for r in
                ph.rows_from_snapshot(SNAPSHOT, "2026-08-21")}
        self.assertEqual(rows["SIVE"]["currency"], "SEK")


class TestDerivedAnchors(unittest.TestCase):
    def test_back_computes_from_the_percentage_change(self):
        rows = {(r["ticker"], r["date"]): r
                for r in ph.derive_anchors(SNAPSHOT, "2026-08-21")}
        # NVDA is +100% over 1m, so a month ago it was half of 200.
        self.assertAlmostEqual(rows[("NVDA", "2026-07-22")]["close"], 100.0)
        # -50% over 1m means it was double.
        self.assertAlmostEqual(rows[("SIVE", "2026-07-22")]["close"], 100.0)

    def test_anchors_are_stamped_approximate(self):
        for r in ph.derive_anchors(SNAPSHOT, "2026-08-21"):
            self.assertEqual(r["source"], ph.SOURCE_DERIVED)

    def test_a_total_wipeout_does_not_divide_by_zero(self):
        rows = ph.derive_anchors({"X": {"price": 10.0, "chg1m": -100.0}},
                                 "2026-08-21")
        self.assertEqual(rows, [])

    def test_a_bad_asof_yields_nothing_rather_than_raising(self):
        self.assertEqual(ph.derive_anchors(SNAPSHOT, "later"), [])
        self.assertEqual(ph.derive_anchors(SNAPSHOT, ""), [])


class TestRoundTrip(unittest.TestCase):
    def test_csv_survives_a_round_trip(self):
        rows = ph.rows_from_snapshot(SNAPSHOT, "2026-08-21")
        back = ph.parse_csv_lines(ph.to_csv_lines(rows))
        self.assertEqual(back, rows)

    def test_the_header_and_corrupt_lines_are_skipped(self):
        lines = ["date,ticker,close,currency,source", "", "garbage",
                 "2026-08-21,NVDA,200,USD,sheet", "2026-08-21,BAD,0,USD,sheet"]
        rows = ph.parse_csv_lines(lines)
        self.assertEqual([r["ticker"] for r in rows], ["NVDA"])


class TestDedupe(unittest.TestCase):
    def test_one_row_per_ticker_per_day(self):
        rows = ph.dedupe([
            ph.make_row("2026-08-21", "NVDA", 100),
            ph.make_row("2026-08-21", "NVDA", 200),
        ])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["close"], 200)

    def test_an_observed_close_always_beats_a_derived_one(self):
        """Order must not decide this — a real close is never overwritten by a
        back-computed approximation."""
        obs = ph.make_row("2026-08-21", "NVDA", 200, "USD", ph.SOURCE_OBSERVED)
        der = ph.make_row("2026-08-21", "NVDA", 111, "USD", ph.SOURCE_DERIVED)
        for pair in ([obs, der], [der, obs]):
            out = ph.dedupe(pair)
            self.assertEqual(out[0]["close"], 200)
            self.assertEqual(out[0]["source"], ph.SOURCE_OBSERVED)


class TestLookups(unittest.TestCase):
    ROWS = [
        ph.make_row("2026-01-01", "NVDA", 100),
        ph.make_row("2026-02-01", "NVDA", 150),
        ph.make_row("2026-03-01", "NVDA", 300),
    ]

    def test_close_on_or_before(self):
        got = ph.close_on_or_before(self.ROWS, "NVDA", "2026-02-03",
                                    max_gap_days=10)
        self.assertEqual(got["date"], "2026-02-01")

    def test_a_lookup_will_not_silently_reach_back_months(self):
        """Without the gap cap this would happily return the January row for a
        March question, and call the result a return."""
        self.assertIsNone(ph.close_on_or_before(self.ROWS, "NVDA",
                                                "2026-06-01", max_gap_days=10))

    def test_forward_return_is_what_happened_after(self):
        got = ph.forward_return(self.ROWS, "NVDA", "2026-01-01", 31,
                                max_gap_days=10)
        self.assertAlmostEqual(got["pct"], 50.0)
        self.assertEqual((got["from"], got["to"]), ("2026-01-01", "2026-02-01"))

    def test_a_half_measured_return_is_no_return(self):
        self.assertIsNone(ph.forward_return(self.ROWS, "NVDA", "2020-01-01", 30))
        self.assertIsNone(ph.forward_return(self.ROWS, "MISSING", "2026-01-01", 31))

    def test_an_approximate_leg_is_flagged(self):
        rows = self.ROWS + [ph.make_row("2026-04-01", "NVDA", 600, "USD",
                                        ph.SOURCE_DERIVED)]
        got = ph.forward_return(rows, "NVDA", "2026-03-01", 31, max_gap_days=10)
        self.assertTrue(got["approximate"])

    def test_an_unreadable_date_returns_none(self):
        self.assertIsNone(ph.close_on_or_before(self.ROWS, "NVDA", "soon"))
        self.assertIsNone(ph.forward_return(self.ROWS, "NVDA", "soon", 30))


class TestCoverage(unittest.TestCase):
    def test_empty_record(self):
        self.assertEqual(ph.coverage([])["rows"], 0)

    def test_counts_and_span(self):
        rows = ph.rows_from_snapshot(SNAPSHOT, "2026-08-21") + \
            ph.derive_anchors(SNAPSHOT, "2026-08-21")
        cov = ph.coverage(rows)
        self.assertEqual(cov["tickers"], 2)
        self.assertEqual(cov["lastDate"], "2026-08-21")
        self.assertGreater(cov["derived"], 0)
        self.assertGreater(cov["observed"], 0)


class TestAppendFile(unittest.TestCase):
    """Invariant 7 — a temp dir, never ingest/store/."""

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self._orig = rec.HISTORY_PATH
        rec.HISTORY_PATH = pathlib.Path(self._tmp.name) / "price_history.csv"

    def tearDown(self):
        rec.HISTORY_PATH = self._orig
        self._tmp.cleanup()

    def test_appending_twice_in_a_day_adds_nothing_the_second_time(self):
        """The launchd schedule and a manual refresh must not double-count."""
        first = rec.append_snapshot(SNAPSHOT, "2026-08-21")
        self.assertEqual(first, 2)
        self.assertEqual(rec.append_snapshot(SNAPSHOT, "2026-08-21"), 0)
        self.assertEqual(len(rec.load_rows()), 2)

    def test_a_new_day_appends(self):
        rec.append_snapshot(SNAPSHOT, "2026-08-21")
        self.assertEqual(rec.append_snapshot(SNAPSHOT, "2026-08-22"), 2)
        self.assertEqual(len(rec.load_rows()), 4)

    def test_the_file_gets_a_header_once(self):
        rec.append_snapshot(SNAPSHOT, "2026-08-21")
        rec.append_snapshot(SNAPSHOT, "2026-08-22")
        text = rec.HISTORY_PATH.read_text()
        self.assertEqual(text.count("date,ticker,close"), 1)

    def test_seed_adds_the_derived_anchors_too(self):
        added = rec.append_snapshot(SNAPSHOT, "2026-08-21", seed=True)
        self.assertGreater(added, 2)
        self.assertGreater(ph.coverage(rec.load_rows())["derived"], 0)

    def test_a_later_observed_close_replaces_a_seeded_anchor_on_read(self):
        rec.append_snapshot(SNAPSHOT, "2026-08-21", seed=True)
        # The 1m anchor lands on 2026-07-22; a real close for that day wins.
        rec._append([ph.make_row("2026-07-22", "NVDA", 123.0, "USD",
                                 ph.SOURCE_OBSERVED)])
        row = [r for r in rec.load_rows()
               if r["ticker"] == "NVDA" and r["date"] == "2026-07-22"]
        self.assertEqual(len(row), 1)
        self.assertEqual(row[0]["source"], ph.SOURCE_OBSERVED)

    def test_reading_a_file_that_does_not_exist_yet(self):
        self.assertEqual(rec.load_rows(), [])


class TestPurity(unittest.TestCase):
    def test_price_history_module_does_no_io(self):
        src = pathlib.Path(ph.__file__).read_text()
        for banned in ("urllib", "requests", "socket", "open(", "pathlib"):
            self.assertNotIn(banned, src, "price_history.py must stay pure")


class TestNotInDataJs(unittest.TestCase):
    def test_the_history_never_rides_in_data_js(self):
        """It is an analysis substrate. Baking a growing CSV into data.js would
        bloat every page load for no benefit."""
        import generate_data_js as gen
        self.assertNotIn("price_history", gen.REQUIRED_KEYS)
        self.assertNotIn("price_history.csv", json.dumps(gen.STORE_BACKED))


if __name__ == "__main__":
    unittest.main()
