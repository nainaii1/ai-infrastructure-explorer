import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import fetch_prices as fp  # noqa: E402


class TestNum(unittest.TestCase):
    def test_currency_formatting_stripped(self):
        self.assertEqual(fp._num("$1,842,000.00"), 1842000.0)

    def test_plain_number(self):
        self.assertEqual(fp._num("12.5"), 12.5)

    def test_percent_sign_stripped(self):
        self.assertEqual(fp._num("-3.2%"), -3.2)

    def test_na_and_blank_are_none(self):
        for raw in ("#N/A", "N/A", "", "  ", None, "-", "#ERROR!"):
            self.assertIsNone(fp._num(raw), raw)

    def test_garbage_is_none(self):
        self.assertIsNone(fp._num("loading..."))


class TestParseSheetRows(unittest.TestCase):
    HEADER = "Ticker,GoogleFinanceSymbol,Price,MarketCap,Currency,Chg1W,Chg1M,Chg1Y\n"

    def test_full_row(self):
        csv_text = self.HEADER + 'AAOI,AAOI,$109.09,"$8,753,686,758.00",USD,1.234,-5.6789,120.5\n'
        rows = fp._parse_sheet_rows(csv_text)
        snap = rows["AAOI"]
        self.assertEqual(snap["price"], 109.09)
        self.assertEqual(snap["marketCap"], 8753686758.0)
        self.assertEqual(snap["currency"], "USD")
        self.assertEqual(snap["chg7d"], 1.23)   # rounded to 2dp
        self.assertEqual(snap["chg1m"], -5.68)
        self.assertEqual(snap["chg1y"], 120.5)

    def test_missing_currency_column_omitted(self):
        # No Currency column -> no currency stamped (run() keeps the prior
        # snapshot's currency; defaulting USD would mislabel KRW/SEK names).
        csv_text = "Ticker,GoogleFinanceSymbol,Price,MarketCap\nNVDA,NVDA,$212.50,\"$5,142,500,000,000.00\"\n"
        rows = fp._parse_sheet_rows(csv_text)
        self.assertNotIn("currency", rows["NVDA"])
        self.assertNotIn("chg7d", rows["NVDA"])  # no history columns yet

    def test_usd_normalised_returns_parsed_when_present(self):
        # A SEK name: the local 1M move and the USD 1M move are different
        # quantities, and both must survive so the app can prefer the USD one.
        csv_text = ("Ticker,Price,MarketCap,Currency,Chg1M,Chg1MUSD,MarketCapUSD\n"
                    'SIVE,47.28,"13936458401",SEK,-12.6543,-9.8765,"1310000000"\n')
        snap = fp._parse_sheet_rows(csv_text)["SIVE"]
        self.assertEqual(snap["chg1m"], -12.65)
        self.assertEqual(snap["chg1mUSD"], -9.88)
        self.assertEqual(snap["marketCapUSD"], 1310000000.0)

    def test_usd_return_columns_absent_are_omitted_not_defaulted(self):
        # Absent must stay absent: silently copying the local move into the USD
        # field would present a SEK return as if it were a USD one.
        csv_text = ("Ticker,Price,MarketCap,Currency,Chg1M\n"
                    'SIVE,47.28,"13936458401",SEK,-12.65\n')
        snap = fp._parse_sheet_rows(csv_text)["SIVE"]
        self.assertEqual(snap["chg1m"], -12.65)
        self.assertNotIn("chg1mUSD", snap)
        self.assertNotIn("marketCapUSD", snap)

    def test_na_price_row_skipped(self):
        csv_text = "Ticker,GoogleFinanceSymbol,Price,MarketCap\nWLAC,WLAC,#N/A,#N/A\n"
        self.assertEqual(fp._parse_sheet_rows(csv_text), {})

    def test_na_marketcap_kept_as_none(self):
        csv_text = "Ticker,GoogleFinanceSymbol,Price,MarketCap\nBOT,BOT,$31.59,#N/A\n"
        self.assertIsNone(fp._parse_sheet_rows(csv_text)["BOT"]["marketCap"])

    def test_blank_ticker_skipped_and_duplicate_last_wins(self):
        csv_text = ("Ticker,GoogleFinanceSymbol,Price,MarketCap\n"
                    ",X,$1.00,\n"
                    "KLAC,KLAC,$224.50,\"$1\"\n"
                    "KLAC,KLAC,$225.00,\"$2\"\n")
        rows = fp._parse_sheet_rows(csv_text)
        self.assertEqual(list(rows), ["KLAC"])
        self.assertEqual(rows["KLAC"]["price"], 225.0)

    def test_non_usd_currency_kept(self):
        csv_text = self.HEADER + '000660.KS,KRX:000660,"$1,842,000.00","$1,312,798,005,000,000.00",KRW,,,\n'
        rows = fp._parse_sheet_rows(csv_text)
        self.assertEqual(rows["000660.KS"]["currency"], "KRW")
        self.assertEqual(rows["000660.KS"]["price"], 1842000.0)


class TestMergeSnapshot(unittest.TestCase):
    """A sheet-wide GOOGLEFINANCE recalculation hiccup (bulk edits trigger
    exactly this) can return blank Chg1W/Chg1M/Chg1Y for most rows in one
    fetch. The merge must not let that wipe real history — this is the fix
    for a real incident: a refresh landed mid-recalc and dropped chg1m/chg7d
    for 99 of 111 tickers and chg1y for 95, because only `currency` was
    protected before this test was written."""

    def test_optional_fields_carry_forward_when_sheet_goes_blank(self):
        prev = {"price": 100.0, "marketCap": 1e9, "currency": "USD",
                "chg7d": 1.1, "chg1m": 2.2, "chg1y": 3.3, "marketCapUSD": 1e9}
        snap = {"price": 101.0, "marketCap": 1.01e9}  # this fetch has nothing else
        merged = fp._merge_snapshot(prev, snap)
        self.assertEqual(merged["price"], 101.0)       # this fetch's fresh value wins
        self.assertEqual(merged["chg7d"], 1.1)          # carried forward
        self.assertEqual(merged["chg1m"], 2.2)
        self.assertEqual(merged["chg1y"], 3.3)
        self.assertEqual(merged["marketCapUSD"], 1e9)
        self.assertEqual(merged["currency"], "USD")

    def test_fresh_sheet_value_always_wins_over_prior(self):
        prev = {"chg1m": 2.2}
        snap = {"price": 1.0, "marketCap": 1.0, "chg1m": 9.9}
        merged = fp._merge_snapshot(prev, snap)
        self.assertEqual(merged["chg1m"], 9.9)

    def test_no_prior_snapshot_leaves_fields_absent(self):
        merged = fp._merge_snapshot({}, {"price": 1.0, "marketCap": 1.0})
        for field in ("chg7d", "chg1m", "chg1y", "marketCapUSD", "chg1mUSD"):
            self.assertNotIn(field, merged)

    def test_usd_return_fields_carry_forward_too(self):
        prev = {"chg1mUSD": -9.87, "chg7dUSD": 1.2, "chg1yUSD": 40.0}
        merged = fp._merge_snapshot(prev, {"price": 1.0, "marketCap": 1.0})
        self.assertEqual(merged["chg1mUSD"], -9.87)
        self.assertEqual(merged["chg7dUSD"], 1.2)
        self.assertEqual(merged["chg1yUSD"], 40.0)


if __name__ == "__main__":
    unittest.main()
