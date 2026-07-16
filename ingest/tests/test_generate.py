import sys
import re
import json
import pathlib
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent))
import generate_data_js as gen  # noqa: E402


def reparse(js_text):
    m = re.search(r"window\.AIE_DATA\s*=\s*(\{.*\});\s*$", js_text, re.S)
    return json.loads(m.group(1))


class TestBuild(unittest.TestCase):
    def test_core_structure(self):
        # Assert structural invariants, not exact counts: the store grows with
        # every ingest, so hardcoded counts are brittle by design.
        d = gen.build_data()
        self.assertIsInstance(d["tickers"], list)
        self.assertGreaterEqual(len(d["tickers"]), 1)
        self.assertGreaterEqual(len(d["categories"]), 6)
        self.assertTrue(all("layer" in c for c in d["categories"].values()))
        self.assertIsInstance(d["theses"], list)
        self.assertIsInstance(d["priorities"], list)
        self.assertEqual(d["center"]["title"], "NVIDIA + Hyperscalers")

    def test_brain_key_present(self):
        # build_data always exposes a `brain` key; {} until synthesize.py runs.
        d = gen.build_data()
        self.assertIn("brain", d)
        self.assertIsInstance(d["brain"], dict)


class TestIconValidation(unittest.TestCase):
    def test_valid_icon_passes(self):
        gen._validate_icon('<path d="M3 12h18" fill="none" stroke="currentColor" stroke-width="1.5"/>')

    def test_onload_is_rejected(self):
        with self.assertRaises(ValueError):
            gen._validate_icon('<path d="M3 12h18" onload="alert(1)"/>')

    def test_script_is_rejected(self):
        with self.assertRaises(ValueError):
            gen._validate_icon('<script>alert(1)</script>')

    def test_href_is_rejected(self):
        with self.assertRaises(ValueError):
            gen._validate_icon('<path d="M3 12h18" href="https://example.com"/>')

    def test_missing_icon_is_tolerated(self):
        gen._validate_icon(None)


class TestRenderSafety(unittest.TestCase):
    def test_render_roundtrips(self):
        d = gen.build_data()
        out = gen.render(d)
        self.assertIn("window.AIE_DATA =", out)
        self.assertTrue(out.rstrip().endswith(";"))
        reparse(out)  # must be valid JSON

    def test_injection_is_neutralized(self):
        hostile = '"}; </script><script>alert(1)</script>'
        d = gen.build_data()
        d["theses"] = [{"id": "x_1", "text": hostile, "tickers": []}]
        out = gen.render(d)
        # No raw closing tag can appear in the emitted JS source.
        self.assertNotIn("</script>", out)
        # ...yet the value is preserved exactly after JSON/JS unescaping.
        parsed = reparse(out)
        self.assertEqual(parsed["theses"][0]["text"], hostile)


class TestTiersAndDesk(unittest.TestCase):
    def test_every_ticker_has_a_tier(self):
        d = gen.build_data()
        for t in d["tickers"]:
            self.assertIn(t.get("tier"), ("core", "watch", "radar"), t["ticker"])

    def test_desk_key_present(self):
        # build_data always exposes a `desk` key; {} until verdicts.json exists.
        d = gen.build_data()
        self.assertIn("desk", d)
        self.assertIsInstance(d["desk"], dict)

    def test_desk_verdicts_stamped_onto_tickers(self):
        d = gen.build_data()
        verdicts = (d["desk"].get("verdicts") or [])
        if not verdicts:
            self.skipTest("no verdicts in store yet")
        by_sym = {t["ticker"]: t for t in d["tickers"]}
        for v in verdicts:
            if v["ticker"] in by_sym:
                self.assertEqual(by_sym[v["ticker"]].get("verdict"), v)


class TestMemos(unittest.TestCase):
    def test_memos_key_absent_defaults_to_empty(self):
        # When memos.json is missing, build_data still exposes a `memos` key
        # as {} (same optional-load contract as brain/desk).
        orig = gen._load_optional

        def fake(name, default):
            if name == "memos.json":
                return default  # simulate file absent
            return orig(name, default)

        gen._load_optional = fake
        try:
            d = gen.build_data()
        finally:
            gen._load_optional = orig
        self.assertIn("memos", d)
        self.assertEqual(d["memos"], {})

    def test_memos_passthrough_intact(self):
        # When memos.json is present, it is passed through verbatim.
        payload = {
            "meta": {"schemaVersion": 1, "author": "claude-desk"},
            "memos": [{"id": "m_TEST_2026w28", "ticker": "TEST", "rating": "watch"}],
        }
        orig = gen._load_optional

        def fake(name, default):
            if name == "memos.json":
                return payload
            return orig(name, default)

        gen._load_optional = fake
        try:
            d = gen.build_data()
        finally:
            gen._load_optional = orig
        self.assertEqual(d["memos"], payload)


class TestCalls(unittest.TestCase):
    def _with_fake(self, calls_payload, prices_payload=None):
        orig = gen._load_optional

        def fake(name, default):
            if name == "calls.json":
                return default if calls_payload is None else calls_payload
            if name == "prices.json" and prices_payload is not None:
                return prices_payload
            return orig(name, default)

        gen._load_optional = fake
        try:
            return gen.build_data()
        finally:
            gen._load_optional = orig

    def test_calls_key_absent_defaults_to_empty(self):
        # calls.json missing -> `calls` key still present as {} (same
        # optional-load contract as brain/desk/memos/vault).
        d = self._with_fake(None)
        self.assertIn("calls", d)
        self.assertEqual(d["calls"], {})

    def test_calls_passthrough_intact(self):
        payload = {
            "meta": {"schemaVersion": 1, "benchmark": "SMH"},
            "calls": [{
                "id": "c_AAOI_2026-07-12", "ticker": "AAOI",
                "kind": "add-on-dip", "calledAt": "2026-07-12",
                "entryPrice": 113.84, "entryCurrency": "USD",
                "stanceAtCall": "accumulate", "memoId": "m_AAOI_2026w28",
                "thesisIds": [], "closedAt": None, "exitPrice": None,
                "outcome": "open",
                "benchmark": {"symbol": "SMH", "priceAtCall": 300.0},
            }],
        }
        d = self._with_fake(payload)
        self.assertEqual(d["calls"], payload)

    def test_benchmark_quote_from_prices(self):
        # When prices.json carries the benchmark symbol, its quote is exposed
        # top-level so performance.html can compute vs-SMH without fetch().
        prices = {"SMH": {"price": 301.5, "currency": "USD", "asOf": "2026-07-12T00:00:00Z"}}
        d = self._with_fake({"meta": {"benchmark": "SMH"}, "calls": []}, prices)
        self.assertEqual(d["benchmarkQuote"]["price"], 301.5)

    def test_price_fields_merged_onto_ticker(self):
        d = gen.build_data()
        sym = d["tickers"][0]["ticker"]
        prices = {sym: {"price": 10.5, "currency": "USD", "chg7d": 1.1,
                        "chg1m": 2.2, "chg1y": 33.3, "marketCap": 999,
                        "asOf": "2026-07-16T00:00:00Z"}}
        d2 = self._with_fake({"meta": {}, "calls": []}, prices)
        t = next(t for t in d2["tickers"] if t["ticker"] == sym)
        for f in gen.PRICE_FIELDS:
            self.assertEqual(t[f], prices[sym][f], f)

    def test_benchmark_quote_none_when_unpriced(self):
        d = self._with_fake({"meta": {"benchmark": "SMH"}, "calls": []}, {})
        self.assertIsNone(d["benchmarkQuote"])


if __name__ == "__main__":
    unittest.main()
