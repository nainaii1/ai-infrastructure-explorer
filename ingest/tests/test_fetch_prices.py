import sys
import pathlib
import unittest
import urllib.error

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import fetch_prices as fp  # noqa: E402


class TestPct(unittest.TestCase):
    def test_pct_up(self):
        self.assertEqual(fp._pct(110, 100), 10.0)

    def test_pct_down(self):
        self.assertEqual(fp._pct(90, 100), -10.0)

    def test_pct_missing_values_is_none(self):
        self.assertIsNone(fp._pct(None, 100))
        self.assertIsNone(fp._pct(100, None))
        self.assertIsNone(fp._pct(100, 0))


class TestRetryDelay(unittest.TestCase):
    def test_honors_retry_after_header(self):
        self.assertEqual(fp._retry_delay(0, retry_after="7"), 7.0)

    def test_ignores_garbage_retry_after(self):
        # A non-numeric Retry-After must not crash the backoff — fall back
        # to the exponential schedule instead.
        self.assertEqual(fp._retry_delay(0, retry_after="soon"), fp._retry_delay(0))

    def test_exponential_backoff_grows_with_attempt(self):
        d0 = fp._retry_delay(0)
        d1 = fp._retry_delay(1)
        d2 = fp._retry_delay(2)
        self.assertLess(d0, d1)
        self.assertLess(d1, d2)

    def test_backoff_is_capped(self):
        self.assertLessEqual(fp._retry_delay(10), fp.MAX_BACKOFF_SECONDS)


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def read(self):
        import json
        return json.dumps(self._payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FlakyOpener:
    """Raises HTTPError 429 `fail_times` times, then returns `payload`."""

    def __init__(self, fail_times, payload, retry_after=None):
        self.fail_times = fail_times
        self.payload = payload
        self.calls = 0
        self.retry_after = retry_after

    def open(self, req, timeout=None):
        self.calls += 1
        if self.calls <= self.fail_times:
            hdrs = {"Retry-After": self.retry_after} if self.retry_after else {}
            raise urllib.error.HTTPError(req.full_url, 429, "Too Many Requests", hdrs, None)
        return FakeResponse(self.payload)


class TestHttpJsonRetries(unittest.TestCase):
    def test_recovers_after_transient_429s(self):
        opener = FlakyOpener(fail_times=2, payload={"ok": True})
        result = fp._http_json("https://example.test/x", opener=opener, retries=3, sleep_fn=lambda s: None)
        self.assertEqual(result, {"ok": True})
        self.assertEqual(opener.calls, 3)

    def test_gives_up_after_exhausting_retries(self):
        opener = FlakyOpener(fail_times=99, payload={"ok": True})
        with self.assertRaises(urllib.error.HTTPError):
            fp._http_json("https://example.test/x", opener=opener, retries=2, sleep_fn=lambda s: None)


class TestBatchMarketCapParsing(unittest.TestCase):
    def test_maps_symbol_to_marketcap(self):
        data = {"quoteResponse": {"result": [
            {"symbol": "AAOI", "marketCap": 12_800_000_000},
            {"symbol": "LITE", "marketCap": 65_000_000_000},
        ]}}
        self.assertEqual(fp._parse_quote_batch(data), {
            "AAOI": 12_800_000_000,
            "LITE": 65_000_000_000,
        })

    def test_missing_marketcap_field_is_omitted(self):
        data = {"quoteResponse": {"result": [{"symbol": "ZZZZ"}]}}
        self.assertEqual(fp._parse_quote_batch(data), {})

    def test_empty_result_is_empty_dict(self):
        self.assertEqual(fp._parse_quote_batch({}), {})


class TestParseFmpProfile(unittest.TestCase):
    """FMP's /stable/profile response, as actually observed from a live free-tier
    key (2026-07): a list with one row containing price/marketCap/currency."""

    def test_extracts_price_marketcap_currency(self):
        data = [{
            "symbol": "AAOI", "price": 120.95, "marketCap": 9_705_362_669,
            "currency": "USD", "companyName": "Applied Optoelectronics, Inc.",
        }]
        self.assertEqual(fp._parse_fmp_profile(data), {
            "price": 120.95, "marketCap": 9_705_362_669, "currency": "USD",
        })

    def test_empty_list_is_none(self):
        self.assertIsNone(fp._parse_fmp_profile([]))

    def test_non_list_is_none(self):
        # FMP returns a plain dict (e.g. an error message) on failure, not a list.
        self.assertIsNone(fp._parse_fmp_profile({"Error Message": "nope"}))


class TestFetchFmpProfile(unittest.TestCase):
    def test_success_returns_parsed_profile(self):
        opener = FlakyOpener(fail_times=0, payload=[
            {"price": 49.0, "marketCap": 12_445_397_398, "currency": "SEK"},
        ])
        result = fp.fetch_fmp_profile("SIVE.ST", "fake-key", opener=opener, sleep_fn=lambda s: None)
        self.assertEqual(result, {"price": 49.0, "marketCap": 12_445_397_398, "currency": "SEK"})

    def test_unmatched_symbol_returns_none(self):
        opener = FlakyOpener(fail_times=0, payload=[])  # e.g. SIVEF — no FMP coverage
        result = fp.fetch_fmp_profile("SIVEF", "fake-key", opener=opener, sleep_fn=lambda s: None)
        self.assertIsNone(result)

    def test_premium_402_is_treated_as_unavailable_not_a_crash(self):
        class PremiumBlockedOpener:
            def open(self, req, timeout=None):
                raise urllib.error.HTTPError(req.full_url, 402, "Payment Required", {}, None)
        result = fp.fetch_fmp_profile("AAOI", "fake-key", opener=PremiumBlockedOpener(), sleep_fn=lambda s: None)
        self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main()
