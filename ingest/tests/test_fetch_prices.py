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


if __name__ == "__main__":
    unittest.main()
