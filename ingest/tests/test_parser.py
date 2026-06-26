import sys
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import parser  # noqa: E402

KNOWN = ["AAOI", "TSM", "000660.KS", "SOI.PA"]


class TestTickerDetection(unittest.TestCase):
    def test_cashtag_high_confidence(self):
        high, low = parser.detect_tickers("loving $NVTS and $SOI.PA today", KNOWN)
        self.assertIn("NVTS", high)
        self.assertIn("SOI.PA", high)

    def test_known_symbol_without_dollar(self):
        high, _ = parser.detect_tickers("TSM is printing money", KNOWN)
        self.assertIn("TSM", high)

    def test_bareword_is_low_confidence(self):
        _, low = parser.detect_tickers("I think ZXCV looks interesting", KNOWN)
        self.assertIn("ZXCV", low)

    def test_stopwords_and_known_excluded_from_low(self):
        high, low = parser.detect_tickers("THE GPU story for AAOI is strong", KNOWN)
        self.assertNotIn("THE", low)
        self.assertNotIn("GPU", low)
        self.assertNotIn("AAOI", low)  # known -> high, not low
        self.assertIn("AAOI", high)

    def test_cashtag_not_duplicated_in_low(self):
        high, low = parser.detect_tickers("$AAOI to the moon", KNOWN)
        self.assertIn("AAOI", high)
        self.assertNotIn("AAOI", low)


class TestUrlAndId(unittest.TestCase):
    def test_status_url_gives_tweet_id(self):
        text = "big news https://x.com/aleabitoreddit/status/12345 read it"
        thesis, _ = parser.parse_text(text, KNOWN, posted_at="2026-06-26T00:00:00Z")
        self.assertEqual(thesis["sourceUrl"], "https://x.com/aleabitoreddit/status/12345")
        self.assertEqual(thesis["id"], "x_12345")

    def test_hash_id_when_no_url(self):
        thesis, _ = parser.parse_text("no link here", KNOWN, posted_at="2026-06-26T00:00:00Z")
        self.assertTrue(thesis["id"].startswith("h_"))

    def test_same_input_same_id(self):
        a, _ = parser.parse_text("repeat me", KNOWN, posted_at="2026-06-26T00:00:00Z")
        b, _ = parser.parse_text("repeat me", KNOWN, posted_at="2026-06-26T00:00:00Z")
        self.assertEqual(a["id"], b["id"])


class TestConviction(unittest.TestCase):
    def test_high_conviction_phrase(self):
        self.assertEqual(parser.detect_conviction("$AAOI is my top pick"), "high")

    def test_normal_when_no_phrase(self):
        self.assertEqual(parser.detect_conviction("some neutral comment"), "normal")


if __name__ == "__main__":
    unittest.main()
