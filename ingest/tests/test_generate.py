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


if __name__ == "__main__":
    unittest.main()
